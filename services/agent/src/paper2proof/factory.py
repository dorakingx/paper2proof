"""Runtime composition kept explicit for auditability."""

from __future__ import annotations

from paper2proof.agents import AgentSuite, FixtureAgentSuite, StrandsAgentSuite
from paper2proof.config import Settings
from paper2proof.executors import AgentCoreExecutor, DockerSandboxExecutor
from paper2proof.executors.base import ExecutionBackend
from paper2proof.store import InMemoryJobStore
from paper2proof.workflow import Paper2ProofWorkflow


def build_workflow(
    settings: Settings, store: InMemoryJobStore | None = None
) -> Paper2ProofWorkflow:
    selected_store = store or InMemoryJobStore()
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
    )
