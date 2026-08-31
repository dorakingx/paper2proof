"""Bounded execution backends."""

from paper2proof.executors.agentcore import AgentCoreExecutor
from paper2proof.executors.docker import DockerSandboxExecutor

__all__ = ["AgentCoreExecutor", "DockerSandboxExecutor"]
