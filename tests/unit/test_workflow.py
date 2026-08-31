from __future__ import annotations

import pytest
from paper2proof.agents import FixtureAgentSuite
from paper2proof.schemas import DecisionSubmission, JobRequest, JobStatus, Verdict
from paper2proof.store import InMemoryJobStore
from paper2proof.workflow import Paper2ProofWorkflow

from tests.unit.helpers import StubExecutor


def workflow(executor: StubExecutor | None = None) -> Paper2ProofWorkflow:
    return Paper2ProofWorkflow(
        store=InMemoryJobStore(),
        agents=FixtureAgentSuite(),
        executor=executor or StubExecutor(),
        allowed_hosts=frozenset({"github.com"}),
    )


async def create_and_run(
    selected: Paper2ProofWorkflow,
    fixture_id: str,
    idempotency_key: str = "test-key-123",
):
    job, created = await selected.create_job(
        JobRequest(fixture_id=fixture_id, idempotency_key=idempotency_key)
    )
    assert created is True
    return await selected.run(job.job_id)


@pytest.mark.asyncio
async def test_golden_path_reaches_completed_pass_with_full_evidence() -> None:
    selected = workflow()
    job = await create_and_run(selected, "reproducible-mean")
    assert job.status == JobStatus.COMPLETED
    assert job.report is not None
    assert job.report.verdict == Verdict.PASS
    assert job.report.evidence_sha256 is not None
    assert [transition.to_status for transition in job.transitions] == [
        JobStatus.INTAKE,
        JobStatus.CLAIMS_EXTRACTED,
        JobStatus.PLAN_READY,
        JobStatus.EXECUTING,
        JobStatus.VERIFYING,
        JobStatus.COMPLETED,
    ]
    assert any(event.role == "Claim Extraction Agent" for event in job.trace)
    assert any(event.role == "Execution Agent" for event in job.trace)


@pytest.mark.asyncio
async def test_successful_execution_can_produce_mismatch() -> None:
    selected = workflow()
    job = await create_and_run(selected, "parameter-drift")
    assert job.status == JobStatus.COMPLETED
    assert job.execution is not None and job.execution.status == "SUCCESS"
    assert job.report is not None and job.report.verdict == Verdict.MISMATCH


@pytest.mark.asyncio
async def test_ambiguous_claim_stops_before_execution() -> None:
    executor = StubExecutor()
    selected = workflow(executor)
    job = await create_and_run(selected, "ambiguous-spread")
    assert job.status == JobStatus.AWAITING_APPROVAL
    assert job.decision is not None
    assert job.decision.recommended_option_id == "modify"
    assert executor.calls == 0
    assert job.report is not None and job.report.verdict == Verdict.INCONCLUSIVE


@pytest.mark.asyncio
async def test_rejecting_ambiguous_plan_records_blocked_report() -> None:
    selected = workflow()
    job = await create_and_run(selected, "ambiguous-spread")
    decided = await selected.decide(
        job.job_id, DecisionSubmission(option_id="reject", note="Use sample definition instead.")
    )
    assert decided.status == JobStatus.BLOCKED
    assert decided.report is not None and decided.report.verdict == Verdict.BLOCKED


@pytest.mark.asyncio
async def test_approving_ambiguous_plan_runs_once() -> None:
    executor = StubExecutor(observed=0.816496580927726)
    selected = workflow(executor)
    job = await create_and_run(selected, "ambiguous-spread")
    decided = await selected.decide(job.job_id, DecisionSubmission(option_id="approve"))
    assert decided.status == JobStatus.COMPLETED
    assert executor.calls == 1
    assert decided.report is not None and decided.report.verdict == Verdict.MISMATCH


@pytest.mark.asyncio
async def test_idempotency_returns_same_job_without_duplicate() -> None:
    selected = workflow()
    request = JobRequest(fixture_id="reproducible-mean", idempotency_key="stable-key")
    first, first_created = await selected.create_job(request)
    second, second_created = await selected.create_job(request)
    assert first_created is True
    assert second_created is False
    assert second.job_id == first.job_id


@pytest.mark.asyncio
async def test_execution_error_is_structured_failure() -> None:
    selected = workflow(StubExecutor(fail=True))
    job = await create_and_run(selected, "reproducible-mean")
    assert job.status == JobStatus.FAILED
    assert job.report is not None
    assert job.report.verdict == Verdict.INCONCLUSIVE


@pytest.mark.asyncio
@pytest.mark.parametrize("fixture_id", ["missing-numpy", "missing-pandas", "dangerous-host-access"])
async def test_deterministic_policy_violation_is_auditable_block(
    fixture_id: str,
) -> None:
    executor = StubExecutor()
    selected = workflow(executor)

    job = await create_and_run(selected, fixture_id, f"blocked-{fixture_id}")

    assert job.status == JobStatus.BLOCKED
    assert job.error_code == "SecurityViolation"
    assert job.report is not None and job.report.verdict == Verdict.BLOCKED
    assert job.execution is None
    assert executor.calls == 0
    assert any(event.name == "deterministic-policy-block" for event in job.trace)
