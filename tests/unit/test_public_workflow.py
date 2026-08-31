from __future__ import annotations

import pytest
from paper2proof.agents import FixtureAgentSuite
from paper2proof.ingestion import SourceDocument
from paper2proof.schemas import (
    AgentReview,
    Claim,
    ClaimExtraction,
    DecisionSubmission,
    ExperimentPlan,
    JobRequest,
    JobStatus,
    RiskLevel,
    SourceReference,
    Tolerance,
)
from paper2proof.store import InMemoryJobStore
from paper2proof.workflow import Paper2ProofWorkflow

from tests.unit.helpers import StubExecutor


def public_source() -> SourceDocument:
    return SourceDocument(
        source=SourceReference(
            url="https://arxiv.org/abs/2401.12345",
            title="Controlled public paper",
            license="Publicly accessible; article license not verified",
            locator="PDF pages 1-2",
            excerpt="The reported bounded arithmetic mean is 5.0 units.",
            content_sha256="a" * 64,
        ),
        document_text="The reported bounded arithmetic mean is 5.0 units. " * 10,
        claim_hint="Check the mean.",
        timeout_seconds=30,
    )


class FakeIngestor:
    async def ingest(self, _request: JobRequest) -> SourceDocument:
        return public_source()


class PublicAgentSuite(FixtureAgentSuite):
    async def review_intake(self, intake, source_text, trace) -> AgentReview:
        return AgentReview(
            accepted=intake.accepted,
            findings=["Public source requires approval."],
            requires_human_judgment=True,
            judgment_reason=intake.decision_reason,
        )

    async def extract_claims(self, source, trace) -> ClaimExtraction:
        claim = Claim(
            claim_id="claim_public_mean",
            statement="The bounded arithmetic mean is 5.0 units.",
            reported_value=5.0,
            unit="units",
            tolerance=Tolerance(absolute=0.001),
            conditions=["Use the four declared observations."],
            source=source.source,
        )
        return ClaimExtraction(claims=[claim], selected_claim_id=claim.claim_id)

    async def plan(self, source, claim, trace) -> ExperimentPlan:
        return ExperimentPlan(
            plan_id="plan_public_mean",
            claim_id=claim.claim_id,
            code=(
                "import json\nimport statistics\n"
                "print('PAPER2PROOF_RESULT=' + json.dumps({'observed': "
                "statistics.fmean([2, 4, 6, 8])}))"
            ),
            command_display="python -I - < approved_experiment.py",
            success_criteria=["Return one finite observation."],
            timeout_seconds=20,
            risk_level=RiskLevel.LOW,
            estimated_cost_usd=0.001,
        )


def workflow() -> tuple[Paper2ProofWorkflow, StubExecutor]:
    executor = StubExecutor()
    selected = Paper2ProofWorkflow(
        store=InMemoryJobStore(),
        agents=PublicAgentSuite(),
        executor=executor,
        allowed_hosts=frozenset({"arxiv.org"}),
        ingestor=FakeIngestor(),  # type: ignore[arg-type]
    )
    return selected, executor


@pytest.mark.asyncio
async def test_public_paper_always_stops_for_human_approval_before_execution() -> None:
    selected, executor = workflow()
    job, _created = await selected.create_job(
        JobRequest(
            paper_url="https://arxiv.org/abs/2401.12345",
            idempotency_key="public-workflow-test",
        )
    )
    gated = await selected.run(job.job_id)

    assert gated.status == JobStatus.AWAITING_APPROVAL
    assert gated.plan is not None and gated.plan.requires_approval is True
    assert gated.intake is not None and gated.intake.source_license.startswith("Publicly")
    assert executor.calls == 0

    completed = await selected.decide(
        gated.job_id,
        DecisionSubmission(option_id="approve", note="Interpretation and license reviewed."),
    )
    assert completed.status == JobStatus.COMPLETED
    assert executor.calls == 1


@pytest.mark.asyncio
async def test_public_claim_cannot_replace_ingested_provenance() -> None:
    class TamperingAgents(PublicAgentSuite):
        async def extract_claims(self, source, trace) -> ClaimExtraction:
            result = await super().extract_claims(source, trace)
            claim = result.selected_claim.model_copy(
                update={
                    "source": result.selected_claim.source.model_copy(
                        update={"content_sha256": "b" * 64}
                    )
                }
            )
            return ClaimExtraction(claims=[claim], selected_claim_id=claim.claim_id)

    selected = Paper2ProofWorkflow(
        store=InMemoryJobStore(),
        agents=TamperingAgents(),
        executor=StubExecutor(),
        allowed_hosts=frozenset({"arxiv.org"}),
        ingestor=FakeIngestor(),  # type: ignore[arg-type]
    )
    job, _created = await selected.create_job(
        JobRequest(
            paper_url="https://arxiv.org/abs/2401.12345",
            idempotency_key="public-provenance-test",
        )
    )
    failed = await selected.run(job.job_id)

    assert failed.status == JobStatus.BLOCKED
    assert failed.error_code == "SecurityViolation"
    assert failed.claim_extraction is None
    assert failed.report is None
