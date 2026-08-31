from __future__ import annotations

from typing import Any

import pytest
from paper2proof.agents import FixtureAgentSuite
from paper2proof.archive import S3EvidenceArchive
from paper2proof.schemas import JobRequest
from paper2proof.store import InMemoryJobStore
from paper2proof.workflow import Paper2ProofWorkflow

from tests.unit.helpers import StubExecutor


class FakeS3Client:
    def __init__(self) -> None:
        self.objects: list[dict[str, Any]] = []

    def put_object(self, **arguments: Any) -> dict[str, str]:
        self.objects.append(arguments)
        return {"ETag": f'"etag-{len(self.objects)}"'}


@pytest.mark.asyncio
async def test_s3_archive_writes_immutable_encrypted_json_and_markdown() -> None:
    selected = Paper2ProofWorkflow(
        store=InMemoryJobStore(),
        agents=FixtureAgentSuite(),
        executor=StubExecutor(),
        allowed_hosts=frozenset({"github.com"}),
    )
    job, _created = await selected.create_job(
        JobRequest(fixture_id="reproducible-mean", idempotency_key="archive-test-key")
    )
    completed = await selected.run(job.job_id)
    assert completed.report is not None

    client = FakeS3Client()
    archive = S3EvidenceArchive(
        bucket="paper2proof-evidence-test",
        region="us-west-2",
        client=client,
    )
    record = await archive.archive(completed.report)

    assert record.evidence_sha256 == completed.report.evidence_sha256
    assert record.json_key.endswith(".json")
    assert record.markdown_key.endswith(".md")
    assert len(client.objects) == 2
    assert all(item["ServerSideEncryption"] == "AES256" for item in client.objects)
    assert all(item["IfNoneMatch"] == "*" for item in client.objects)
    assert all(item["ChecksumSHA256"] for item in client.objects)


@pytest.mark.asyncio
async def test_s3_archive_rejects_unsealed_evidence() -> None:
    selected = Paper2ProofWorkflow(
        store=InMemoryJobStore(),
        agents=FixtureAgentSuite(),
        executor=StubExecutor(),
        allowed_hosts=frozenset({"github.com"}),
    )
    job, _created = await selected.create_job(
        JobRequest(fixture_id="reproducible-mean", idempotency_key="unsealed-test-key")
    )
    completed = await selected.run(job.job_id)
    assert completed.report is not None
    unsealed = completed.report.model_copy(update={"evidence_sha256": None})
    archive = S3EvidenceArchive(
        bucket="paper2proof-evidence-test",
        region="us-west-2",
        client=FakeS3Client(),
    )
    with pytest.raises(ValueError, match="sealed"):
        await archive.archive(unsealed)
