from __future__ import annotations

import io
import json
from typing import Any

import pytest
from botocore.exceptions import ClientError
from paper2proof import agentcore_client
from paper2proof.agentcore_client import AgentCoreRuntimeClient, AgentRuntimeError
from paper2proof.schemas import DecisionSubmission, JobRequest


class FakeAgentCoreClient:
    def __init__(self, responses: list[dict[str, Any]]) -> None:
        self.responses = responses
        self.calls: list[dict[str, Any]] = []

    def invoke_agent_runtime(self, **kwargs: Any) -> dict[str, Any]:
        self.calls.append(kwargs)
        payload = self.responses.pop(0)
        return {
            "statusCode": payload.pop("statusCode", 200),
            "contentType": "application/json",
            "response": io.BytesIO(json.dumps(payload).encode()),
        }


class RawAgentCoreClient:
    def __init__(self, response: dict[str, Any] | Exception) -> None:
        self.response = response

    def invoke_agent_runtime(self, **_kwargs: Any) -> dict[str, Any]:
        if isinstance(self.response, Exception):
            raise self.response
        return self.response


def job_payload() -> dict[str, Any]:
    return {
        "job_id": "job_0123456789abcdef",
        "trace_id": "trace_0123456789abcdef",
        "request": {
            "fixture_id": "reproducible-mean",
            "execution_budget_seconds": 30,
            "idempotency_key": "remote-client-test",
        },
        "status": "QUEUED",
        "created_at": "2026-08-31T00:00:00Z",
        "updated_at": "2026-08-31T00:00:00Z",
        "transitions": [],
        "trace": [],
        "evidence_archives": [],
    }


@pytest.mark.asyncio
async def test_runtime_client_sends_bounded_command_and_validates_job() -> None:
    fake = FakeAgentCoreClient([{"ok": True, "created": True, "job": job_payload()}])
    client = AgentCoreRuntimeClient(
        runtime_arn="arn:aws:bedrock-agentcore:us-west-2:123456789012:runtime/example",
        region="us-west-2",
        client=fake,
    )
    request = JobRequest(
        fixture_id="reproducible-mean",
        execution_budget_seconds=30,
        idempotency_key="remote-client-test",
    )

    job, created = await client.run(request)

    assert created is True
    assert job.job_id == "job_0123456789abcdef"
    invocation = fake.calls[0]
    assert invocation["qualifier"] == "DEFAULT"
    assert len(invocation["runtimeSessionId"]) >= 33
    assert json.loads(invocation["payload"])["action"] == "run"


@pytest.mark.asyncio
async def test_runtime_client_supports_durable_create_and_run_job_commands() -> None:
    fake = FakeAgentCoreClient(
        [
            {"ok": True, "created": True, "job": job_payload()},
            {"ok": True, "job": job_payload()},
        ]
    )
    client = AgentCoreRuntimeClient(runtime_arn="arn:example", region="us-west-2", client=fake)
    request = JobRequest(fixture_id="reproducible-mean", idempotency_key="durable-client")

    created_job, created = await client.create(request)
    run_job = await client.run_job(created_job.job_id)

    assert created is True
    assert run_job.job_id == created_job.job_id
    assert [json.loads(call["payload"])["action"] for call in fake.calls] == [
        "create",
        "run_job",
    ]


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("runtime_error", "expected_status"),
    [
        ({"code": "not_found", "message": "private detail"}, 404),
        ({"code": "conflict", "message": "private detail"}, 409),
        ({"code": "unexpected", "message": "private detail"}, 502),
    ],
)
async def test_runtime_client_maps_only_safe_errors(
    runtime_error: dict[str, str], expected_status: int
) -> None:
    fake = FakeAgentCoreClient([{"ok": False, "error": runtime_error}])
    client = AgentCoreRuntimeClient(runtime_arn="arn:example", region="us-west-2", client=fake)

    with pytest.raises(AgentRuntimeError) as raised:
        await client.get("job_0123456789abcdef")

    assert raised.value.status_code == expected_status
    assert "private detail" not in raised.value.public_message


@pytest.mark.asyncio
async def test_runtime_client_rejects_malformed_success_response() -> None:
    fake = FakeAgentCoreClient([{"ok": True, "created": True, "job": {"unexpected": True}}])
    client = AgentCoreRuntimeClient(runtime_arn="arn:example", region="us-west-2", client=fake)
    request = JobRequest(fixture_id="reproducible-mean", idempotency_key="invalid-response")

    with pytest.raises(AgentRuntimeError, match="invalid response"):
        await client.run(request)


@pytest.mark.asyncio
async def test_runtime_client_health_get_and_decide() -> None:
    fake = FakeAgentCoreClient(
        [
            {"ok": True, "service": "paper2proof-agentcore-runtime"},
            {"ok": True, "job": job_payload()},
            {"ok": True, "job": job_payload()},
        ]
    )
    client = AgentCoreRuntimeClient(runtime_arn="arn:example", region="us-west-2", client=fake)

    assert (await client.health())["service"] == "paper2proof-agentcore-runtime"
    assert (await client.get("job_0123456789abcdef")).job_id == "job_0123456789abcdef"
    decided = await client.decide("job_0123456789abcdef", DecisionSubmission(option_id="reject"))
    assert decided.job_id == "job_0123456789abcdef"


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "payload",
    [
        {"ok": True, "created": "yes", "job": job_payload()},
        {"ok": True, "job": {"invalid": True}},
    ],
)
async def test_runtime_client_rejects_invalid_typed_fields(payload: dict[str, Any]) -> None:
    fake = FakeAgentCoreClient([payload])
    client = AgentCoreRuntimeClient(runtime_arn="arn:example", region="us-west-2", client=fake)

    with pytest.raises(AgentRuntimeError, match="invalid response"):
        if "created" in payload:
            await client.run(
                JobRequest(fixture_id="reproducible-mean", idempotency_key="invalid-field")
            )
        else:
            await client.get("job_0123456789abcdef")


def test_runtime_client_requires_arn() -> None:
    with pytest.raises(ValueError, match="runtime_arn"):
        AgentCoreRuntimeClient(runtime_arn="", region="us-west-2", client=object())


@pytest.mark.asyncio
async def test_runtime_client_maps_sdk_and_http_failures() -> None:
    sdk_error = ClientError(
        {"Error": {"Code": "AccessDeniedException", "Message": "private AWS detail"}},
        "InvokeAgentRuntime",
    )
    sdk_client = AgentCoreRuntimeClient(
        runtime_arn="arn:example",
        region="us-west-2",
        client=RawAgentCoreClient(sdk_error),
    )
    with pytest.raises(AgentRuntimeError, match="temporarily unavailable") as sdk_failure:
        await sdk_client.health()
    assert "private AWS detail" not in sdk_failure.value.public_message

    http_client = AgentCoreRuntimeClient(
        runtime_arn="arn:example",
        region="us-west-2",
        client=RawAgentCoreClient({"statusCode": 500, "response": b"failure"}),
    )
    with pytest.raises(AgentRuntimeError, match="could not complete"):
        await http_client.health()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "body",
    [
        bytearray(b"not-json"),
        b"[]",
        object(),
    ],
)
async def test_runtime_client_rejects_invalid_response_bodies(body: Any) -> None:
    client = AgentCoreRuntimeClient(
        runtime_arn="arn:example",
        region="us-west-2",
        client=RawAgentCoreClient({"statusCode": 200, "response": body}),
    )
    with pytest.raises(AgentRuntimeError, match="invalid response"):
        await client.health()


@pytest.mark.asyncio
async def test_runtime_client_limits_response_size(monkeypatch) -> None:
    monkeypatch.setattr(agentcore_client, "MAX_RUNTIME_RESPONSE_BYTES", 10)
    client = AgentCoreRuntimeClient(
        runtime_arn="arn:example",
        region="us-west-2",
        client=RawAgentCoreClient({"statusCode": 200, "response": b"{" + b"x" * 11}),
    )
    with pytest.raises(AgentRuntimeError, match="more evidence"):
        await client.health()
