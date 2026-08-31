"""Runtime composition kept explicit for auditability."""

from __future__ import annotations

import os

from paper2proof.agents import AgentSuite, FixtureAgentSuite, StrandsAgentSuite
from paper2proof.archive import EvidenceArchive, S3EvidenceArchive
from paper2proof.config import Settings
from paper2proof.executors import AgentCoreExecutor, DockerSandboxExecutor
from paper2proof.executors.base import ExecutionBackend
from paper2proof.ingestion import PublicPaperIngestor
from paper2proof.store import DynamoDBJobStore, InMemoryJobStore, JobStore
from paper2proof.workflow import Paper2ProofWorkflow


def build_workflow(settings: Settings, store: JobStore | None = None) -> Paper2ProofWorkflow:
    # Some AWS SDK integrations consult AWS_DEFAULT_REGION even when their primary
    # client receives an explicit region. Keep the deployment and CLI behavior aligned.
    os.environ.setdefault("AWS_DEFAULT_REGION", settings.aws_region)
    if store is not None:
        selected_store = store
    elif settings.store_mode == "dynamodb":
        selected_store = DynamoDBJobStore(
            table_name=settings.job_table,
            region=settings.aws_region,
        )
    else:
        selected_store = InMemoryJobStore()

    archive: EvidenceArchive | None = None
    if settings.archive_mode == "s3":
        if not settings.evidence_bucket:
            raise ValueError("evidence_bucket is required when archive_mode is s3")
        archive = S3EvidenceArchive(
            bucket=settings.evidence_bucket,
            region=settings.aws_region,
        )
    if settings.runtime_mode in {"bedrock", "agentcore"}:
        agents: AgentSuite = StrandsAgentSuite(
            model_id=settings.bedrock_model_id,
            region=settings.aws_region,
        )
    else:
        agents = FixtureAgentSuite()

    if settings.runtime_mode == "agentcore":
        executor: ExecutionBackend = AgentCoreExecutor(
            region=settings.aws_region,
            max_output_bytes=settings.max_output_bytes,
        )
    else:
        executor = DockerSandboxExecutor(
            image=settings.docker_image,
            max_output_bytes=settings.max_output_bytes,
        )
    return Paper2ProofWorkflow(
        store=selected_store,
        agents=agents,
        executor=executor,
        allowed_hosts=settings.source_host_allowlist,
        ingestor=PublicPaperIngestor(
            allowed_hosts=settings.source_host_allowlist,
            max_source_bytes=settings.max_source_bytes,
        ),
        archive=archive,
    )
