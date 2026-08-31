from __future__ import annotations

import pytest
from paper2proof.agents import FixtureAgentSuite
from paper2proof.reporting import report_to_markdown
from paper2proof.schemas import JobRequest
from paper2proof.store import InMemoryJobStore
from paper2proof.workflow import Paper2ProofWorkflow

from tests.unit.helpers import StubExecutor


@pytest.mark.asyncio
async def test_markdown_and_json_derive_from_same_report() -> None:
    workflow = Paper2ProofWorkflow(
        store=InMemoryJobStore(),
        agents=FixtureAgentSuite(),
        executor=StubExecutor(),
        allowed_hosts=frozenset({"github.com"}),
    )
    job, _ = await workflow.create_job(
        JobRequest(fixture_id="reproducible-mean", idempotency_key="report-key")
    )
    job = await workflow.run(job.job_id)
    assert job.report is not None
    markdown = report_to_markdown(job.report)
    assert job.report.job_id in markdown
    assert str(job.report.verdict) in markdown
    assert "agentcore-live" not in markdown
    assert "recorded" in markdown
