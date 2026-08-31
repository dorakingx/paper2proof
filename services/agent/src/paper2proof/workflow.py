"""Explicit, auditable Paper2Proof state machine."""

from __future__ import annotations

import hashlib
import uuid
from urllib.parse import urlsplit

from pydantic import AnyHttpUrl, TypeAdapter

from paper2proof.agents import AgentSuite
from paper2proof.comparison import compare_claim
from paper2proof.executors.base import ExecutionBackend
from paper2proof.fixtures import Fixture, load_fixture
from paper2proof.schemas import (
    CriticAssessment,
    DecisionOption,
    DecisionRequest,
    DecisionSubmission,
    EvidenceReport,
    ExecutionStatus,
    IntakeAssessment,
    JobRecord,
    JobRequest,
    JobStatus,
    StatusTransition,
    TraceEventType,
    Verdict,
    assert_transition,
    utc_now,
)
from paper2proof.security import detect_prompt_injection, normalize_public_url, validate_python_code
from paper2proof.store import InMemoryJobStore
from paper2proof.tracing import TraceRecorder


class WorkflowInvariantError(RuntimeError):
    """Raised when persisted state violates an internal workflow contract."""


class Paper2ProofWorkflow:
    def __init__(
        self,
        *,
        store: InMemoryJobStore,
        agents: AgentSuite,
        executor: ExecutionBackend,
        allowed_hosts: frozenset[str],
    ) -> None:
        self.store = store
        self.agents = agents
        self.executor = executor
        self.allowed_hosts = allowed_hosts

    async def create_job(self, request: JobRequest) -> tuple[JobRecord, bool]:
        job = JobRecord(
            job_id=f"job_{uuid.uuid4().hex}",
            trace_id=f"trace_{uuid.uuid4().hex}",
            request=request,
        )
        return await self.store.create(job)

    async def run(self, job_id: str) -> JobRecord:
        job = await self.store.get(job_id)
        if job.status != JobStatus.QUEUED:
            return job
        trace = TraceRecorder(job.trace_id)
        try:
            if not job.request.fixture_id:
                raise NotImplementedError("public paper ingestion is not enabled in this build yet")
            fixture = load_fixture(job.request.fixture_id)
            await self._transition(job, trace, JobStatus.INTAKE, "Started source and risk intake.")
            job.intake = self._assess_fixture(fixture)
            await self.agents.review_intake(job.intake, fixture.note, trace)
            await self._checkpoint(job, trace)
            if not job.intake.accepted:
                await self._transition(
                    job, trace, JobStatus.BLOCKED, job.intake.decision_reason or "Blocked"
                )
                return job

            job.claim_extraction = await self.agents.extract_claims(fixture, trace)
            await self._transition(
                job,
                trace,
                JobStatus.CLAIMS_EXTRACTED,
                "A structured, source-linked numerical claim was selected.",
            )
            claim = job.claim_extraction.selected_claim
            job.plan = await self.agents.plan(fixture, claim, trace)
            if job.plan.claim_id != claim.claim_id:
                raise ValueError("plan does not reference the selected claim")
            validate_python_code(job.plan.code)
            await self._transition(
                job,
                trace,
                JobStatus.PLAN_READY,
                "A bounded reproduction plan passed policy validation.",
            )

            if job.claim_extraction.needs_human_judgment or job.plan.requires_approval:
                reason = (
                    job.plan.approval_reason
                    or job.claim_extraction.judgment_reason
                    or "Scientific judgment is required."
                )
                job.decision = DecisionRequest(
                    reason=reason,
                    options=[
                        DecisionOption(
                            option_id="approve",
                            label="Approve bounded run",
                            impact="Run the displayed interpretation once in the selected sandbox.",
                        ),
                        DecisionOption(
                            option_id="reject",
                            label="Reject plan",
                            impact=(
                                "Stop without executing code and preserve the reason in evidence."
                            ),
                        ),
                        DecisionOption(
                            option_id="modify",
                            label="Modify plan",
                            impact="Return the plan for a clarified scientific interpretation.",
                        ),
                    ],
                    recommended_option_id="modify",
                )
                await self._transition(job, trace, JobStatus.AWAITING_APPROVAL, reason)
                job.report = self._approval_report(job)
                await self._checkpoint(job, trace)
                return job

            return await self._execute_and_verify(job, trace)
        except Exception as exc:
            job.error_code = exc.__class__.__name__
            job.error_message = str(exc)
            trace.add(
                TraceEventType.ERROR,
                "Workflow",
                exc.__class__.__name__,
                output_value={"message": str(exc)},
            )
            if job.status not in {
                JobStatus.COMPLETED,
                JobStatus.PARTIAL,
                JobStatus.BLOCKED,
                JobStatus.FAILED,
            }:
                await self._transition(job, trace, JobStatus.FAILED, "Workflow failed safely.")
            await self._checkpoint(job, trace)
            return job

    async def decide(self, job_id: str, decision: DecisionSubmission) -> JobRecord:
        job = await self.store.get(job_id)
        if job.status != JobStatus.AWAITING_APPROVAL or job.plan is None:
            raise ValueError("job is not awaiting a decision")
        trace = TraceRecorder(job.trace_id)
        trace.events = list(job.trace)
        if decision.option_id == "reject":
            await self._transition(
                job, trace, JobStatus.BLOCKED, decision.note or "Plan rejected by human."
            )
            job.report = self._blocked_report(job, decision.note or "Plan rejected by human.")
            job.decision = None
            await self._checkpoint(job, trace)
            return job
        if decision.option_id == "modify":
            if job.decision is None:
                raise WorkflowInvariantError("awaiting-approval job has no decision request")
            job.error_code = "PLAN_MODIFICATION_REQUIRED"
            job.error_message = decision.note or "A clarified interpretation is required."
            job.decision = job.decision.model_copy(
                update={
                    "reason": decision.note
                    or "Provide a clarified scientific interpretation before approval."
                }
            )
            trace.add(
                TraceEventType.STATE,
                "Decision Center",
                "modify-requested",
                output_value={"note": job.error_message},
            )
            await self._checkpoint(job, trace)
            return job

        job.plan = job.plan.model_copy(update={"requires_approval": False, "approval_reason": None})
        job.decision = None
        return await self._execute_and_verify(job, trace)

    async def _execute_and_verify(self, job: JobRecord, trace: TraceRecorder) -> JobRecord:
        if job.plan is None or job.claim_extraction is None:
            raise WorkflowInvariantError("execution requires a plan and selected claim")
        claim = job.claim_extraction.selected_claim
        await self._transition(job, trace, JobStatus.EXECUTING, "Started one bounded sandbox run.")
        job.execution = await self.executor.execute(job.plan, trace)
        await self._checkpoint(job, trace)
        if job.execution.status == ExecutionStatus.BLOCKED:
            await self._transition(
                job, trace, JobStatus.BLOCKED, "Execution policy blocked the plan."
            )
            job.report = self._blocked_report(
                job, job.execution.failure_reason or "Execution policy blocked the plan."
            )
            await self._checkpoint(job, trace)
            return job

        await self._transition(
            job, trace, JobStatus.VERIFYING, "Comparing reported and observed values."
        )
        comparison, verdict = compare_claim(claim, job.execution)
        critic: CriticAssessment = await self.agents.critique(
            claim, job.execution, comparison, verdict, trace
        )
        narrative = await self.agents.report(
            claim, job.plan, job.execution, comparison, critic, trace
        )
        terminal = (
            JobStatus.COMPLETED
            if job.execution.status == ExecutionStatus.SUCCESS
            else JobStatus.FAILED
        )
        await self._transition(
            job, trace, terminal, "Evidence report generated from observed results."
        )
        report = EvidenceReport(
            job_id=job.job_id,
            terminal_status=terminal,
            claim=claim,
            plan=job.plan,
            execution=job.execution,
            comparison=comparison,
            verdict=critic.verdict,
            confidence=critic.confidence,
            limitations=narrative.limitations,
            next_decision=narrative.next_decision,
            trace_id=job.trace_id,
        )
        canonical = report.model_dump_json(exclude={"evidence_sha256"})
        job.report = report.model_copy(
            update={"evidence_sha256": hashlib.sha256(canonical.encode()).hexdigest()}
        )
        await self._checkpoint(job, trace)
        return job

    def _assess_fixture(self, fixture: Fixture) -> IntakeAssessment:
        normalized = normalize_public_url(
            str(fixture.metadata.source_url),
            allowed_hosts=self.allowed_hosts,
            resolve_dns=False,
        )
        injection_markers = detect_prompt_injection(fixture.note)
        risks = [f"Prompt-injection marker ignored as data: {item}" for item in injection_markers]
        if fixture.metadata.ambiguity:
            risks.append("The source admits multiple scientifically valid interpretations.")
        return IntakeAssessment(
            accepted=True,
            normalized_source_url=TypeAdapter(AnyHttpUrl).validate_python(normalized),
            source_host=urlsplit(normalized).hostname or "unknown",
            source_license=fixture.metadata.license,
            risk_level=fixture.metadata.risk_level,
            risks=risks,
            prompt_injection_detected=bool(injection_markers),
            requires_approval=fixture.metadata.requires_approval,
            decision_reason=fixture.metadata.approval_reason,
        )

    async def _transition(
        self,
        job: JobRecord,
        trace: TraceRecorder,
        target: JobStatus,
        reason: str,
    ) -> None:
        current = job.status
        assert_transition(current, target)
        job.status = target
        job.updated_at = utc_now()
        job.transitions.append(
            StatusTransition(
                ordinal=len(job.transitions) + 1,
                from_status=current,
                to_status=target,
                reason=reason,
            )
        )
        trace.add(
            TraceEventType.STATE,
            "Workflow",
            f"{current}->{target}",
            output_value={"reason": reason},
        )
        await self._checkpoint(job, trace)

    async def _checkpoint(self, job: JobRecord, trace: TraceRecorder) -> None:
        job.trace = list(trace.events)
        job.updated_at = utc_now()
        await self.store.save(job)

    @staticmethod
    def _approval_report(job: JobRecord) -> EvidenceReport:
        if job.claim_extraction is None:
            raise WorkflowInvariantError("approval report requires a selected claim")
        reason = job.decision.reason if job.decision else "Human judgment is required."
        return EvidenceReport(
            job_id=job.job_id,
            terminal_status=JobStatus.AWAITING_APPROVAL,
            claim=job.claim_extraction.selected_claim,
            plan=job.plan,
            verdict=Verdict.INCONCLUSIVE,
            confidence=0.0,
            limitations=[reason],
            next_decision=reason,
            trace_id=job.trace_id,
        )

    @staticmethod
    def _blocked_report(job: JobRecord, reason: str) -> EvidenceReport:
        if job.claim_extraction is None:
            raise WorkflowInvariantError("blocked report requires a selected claim")
        return EvidenceReport(
            job_id=job.job_id,
            terminal_status=JobStatus.BLOCKED,
            claim=job.claim_extraction.selected_claim,
            plan=job.plan,
            execution=job.execution,
            verdict=Verdict.BLOCKED,
            confidence=1.0,
            limitations=[reason],
            next_decision="Clarify or replace the blocked plan before creating a new job.",
            trace_id=job.trace_id,
        )
