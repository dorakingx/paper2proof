"""Typed command surface for the managed AgentCore Runtime."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import model_validator

from paper2proof.config import Settings
from paper2proof.factory import build_workflow
from paper2proof.schemas import DecisionSubmission, JobRequest, JobStatus, StrictModel
from paper2proof.store import JobNotFoundError
from paper2proof.workflow import Paper2ProofWorkflow


class RuntimeInvocation(StrictModel):
    """One bounded command accepted by the private IAM-authorized runtime."""

    action: Literal["health", "create", "run", "run_job", "get", "decide"]
    request: JobRequest | None = None
    job_id: str | None = None
    decision: DecisionSubmission | None = None

    @model_validator(mode="after")
    def validate_action_payload(self) -> RuntimeInvocation:
        if self.action in {"create", "run"} and self.request is None:
            raise ValueError(f"{self.action} requires request")
        if self.action in {"run_job", "get", "decide"} and not self.job_id:
            raise ValueError(f"{self.action} requires job_id")
        if self.action == "decide" and self.decision is None:
            raise ValueError("decide requires decision")
        return self


class AgentRuntimeService:
    """Dispatch validated runtime commands without exposing arbitrary tools or shell."""

    def __init__(self, *, workflow: Paper2ProofWorkflow, settings: Settings) -> None:
        self.workflow = workflow
        self.settings = settings

    async def invoke(self, payload: dict[str, Any]) -> dict[str, Any]:
        invocation = RuntimeInvocation.model_validate(payload)
        if invocation.action == "health":
            return {
                "ok": True,
                "service": "paper2proof-agentcore-runtime",
                "runtime_mode": self.settings.runtime_mode,
                "store_mode": self.settings.store_mode,
                "archive_mode": self.settings.archive_mode,
            }
        if invocation.action == "run":
            if invocation.request is None:
                raise RuntimeError("validated run invocation has no request")
            job, created = await self.workflow.create_job(invocation.request)
            if created or job.status == JobStatus.QUEUED:
                job = await self.workflow.run(job.job_id)
            return {"ok": True, "created": created, "job": job.model_dump(mode="json")}
        if invocation.action == "create":
            if invocation.request is None:
                raise RuntimeError("validated create invocation has no request")
            job, created = await self.workflow.create_job(invocation.request)
            return {"ok": True, "created": created, "job": job.model_dump(mode="json")}
        if invocation.action == "run_job":
            if invocation.job_id is None:
                raise RuntimeError("validated run_job invocation has no job_id")
            try:
                job = await self.workflow.store.get(invocation.job_id)
            except JobNotFoundError:
                return {
                    "ok": False,
                    "error": {"code": "not_found", "message": "job not found"},
                }
            if job.status == JobStatus.QUEUED:
                job = await self.workflow.run(job.job_id)
            return {"ok": True, "job": job.model_dump(mode="json")}
        if invocation.action == "get":
            if invocation.job_id is None:
                raise RuntimeError("validated get invocation has no job_id")
            try:
                job = await self.workflow.store.get(invocation.job_id)
            except JobNotFoundError:
                return {
                    "ok": False,
                    "error": {"code": "not_found", "message": "job not found"},
                }
            return {"ok": True, "job": job.model_dump(mode="json")}
        if invocation.job_id is None or invocation.decision is None:
            raise RuntimeError("validated decision invocation is incomplete")
        try:
            job = await self.workflow.decide(invocation.job_id, invocation.decision)
        except JobNotFoundError:
            return {
                "ok": False,
                "error": {"code": "not_found", "message": "job not found"},
            }
        except ValueError:
            return {
                "ok": False,
                "error": {
                    "code": "conflict",
                    "message": "job is not awaiting a compatible decision",
                },
            }
        return {"ok": True, "job": job.model_dump(mode="json")}


def build_runtime_service(settings: Settings | None = None) -> AgentRuntimeService:
    selected = settings or Settings()
    return AgentRuntimeService(workflow=build_workflow(selected), settings=selected)
