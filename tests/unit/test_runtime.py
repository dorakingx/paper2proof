from __future__ import annotations

import pytest
from paper2proof.config import Settings
from paper2proof.factory import build_workflow
from paper2proof.runtime import AgentRuntimeService, RuntimeInvocation
from pydantic import ValidationError

from tests.unit.helpers import StubExecutor


def service() -> AgentRuntimeService:
    settings = Settings(runtime_mode="fixture")
    workflow = build_workflow(settings)
    workflow.executor = StubExecutor()
    return AgentRuntimeService(workflow=workflow, settings=settings)


@pytest.mark.asyncio
async def test_runtime_health_run_and_get_without_enumeration() -> None:
    runtime = service()
    health = await runtime.invoke({"action": "health"})
    assert health["ok"] is True

    result = await runtime.invoke(
        {
            "action": "run",
            "request": {
                "fixture_id": "reproducible-mean",
                "idempotency_key": "runtime-test-run",
                "execution_budget_seconds": 30,
            },
        }
    )
    assert result["created"] is True
    assert result["job"]["status"] == "COMPLETED"
    job_id = result["job"]["job_id"]
    assert (await runtime.invoke({"action": "get", "job_id": job_id}))["job"]["job_id"] == job_id
    with pytest.raises(ValidationError):
        await runtime.invoke({"action": "list"})


@pytest.mark.asyncio
async def test_runtime_create_then_worker_run_is_durable_contract() -> None:
    runtime = service()
    created = await runtime.invoke(
        {
            "action": "create",
            "request": {
                "fixture_id": "reproducible-mean",
                "idempotency_key": "runtime-background-create",
                "execution_budget_seconds": 30,
            },
        }
    )
    assert created["created"] is True
    assert created["job"]["status"] == "QUEUED"

    completed = await runtime.invoke({"action": "run_job", "job_id": created["job"]["job_id"]})

    assert completed["job"]["status"] == "COMPLETED"
    replay = await runtime.invoke({"action": "run_job", "job_id": created["job"]["job_id"]})
    assert replay["job"]["job_id"] == completed["job"]["job_id"]


@pytest.mark.asyncio
async def test_runtime_decision_requires_explicit_human_command() -> None:
    runtime = service()
    result = await runtime.invoke(
        {
            "action": "run",
            "request": {
                "fixture_id": "ambiguous-spread",
                "idempotency_key": "runtime-test-decision",
                "execution_budget_seconds": 30,
            },
        }
    )
    assert result["job"]["status"] == "AWAITING_APPROVAL"
    decided = await runtime.invoke(
        {
            "action": "decide",
            "job_id": result["job"]["job_id"],
            "decision": {"option_id": "reject", "note": "Not scientifically justified."},
        }
    )
    assert decided["job"]["status"] == "BLOCKED"


@pytest.mark.asyncio
async def test_runtime_returns_bounded_not_found_and_conflict_errors() -> None:
    runtime = service()
    missing = await runtime.invoke({"action": "get", "job_id": "job_0123456789abcdef"})
    assert missing == {
        "ok": False,
        "error": {"code": "not_found", "message": "job not found"},
    }

    result = await runtime.invoke(
        {
            "action": "run",
            "request": {
                "fixture_id": "reproducible-mean",
                "idempotency_key": "runtime-test-conflict",
                "execution_budget_seconds": 30,
            },
        }
    )
    conflict = await runtime.invoke(
        {
            "action": "decide",
            "job_id": result["job"]["job_id"],
            "decision": {"option_id": "reject"},
        }
    )
    assert conflict["ok"] is False
    assert conflict["error"]["code"] == "conflict"


@pytest.mark.parametrize(
    "payload",
    [
        {"action": "run"},
        {"action": "get"},
        {"action": "decide", "job_id": "job_x"},
        {"action": "shell", "request": {}},
        {"action": "health", "unexpected": True},
    ],
)
def test_runtime_rejects_incomplete_or_unknown_commands(payload: dict[str, object]) -> None:
    with pytest.raises(ValidationError):
        RuntimeInvocation.model_validate(payload)
