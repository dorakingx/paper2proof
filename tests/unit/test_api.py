from __future__ import annotations

import asyncio
import time

from fastapi.testclient import TestClient
from paper2proof.agentcore_client import AgentCoreRuntimeClient
from paper2proof.api import create_app
from paper2proof.config import Settings
from paper2proof.rate_limit import RateLimitExceeded, RateLimitResult
from paper2proof.schemas import JobRequest

from tests.unit.helpers import StubExecutor


class AllowingRateLimiter:
    async def check(self, _subject: str) -> RateLimitResult:
        return RateLimitResult(limit=30, remaining=29, retry_after_seconds=3_600)


class DenyingRateLimiter:
    async def check(self, _subject: str) -> RateLimitResult:
        raise RateLimitExceeded(retry_after_seconds=42)


class RecordingDispatcher:
    def __init__(self) -> None:
        self.job_ids: list[str] = []

    async def dispatch(self, job_id: str) -> None:
        self.job_ids.append(job_id)


def test_health_and_fixture_catalog() -> None:
    app = create_app(Settings(runtime_mode="fixture"))
    with TestClient(app) as client:
        health = client.get("/health")
        assert health.status_code == 200
        assert health.json()["strands_agents"] is True
        assert health.json()["agentcore_code_interpreter"] is False
        assert health.headers["cache-control"] == "no-store"
        assert health.headers["x-content-type-options"] == "nosniff"
        assert "frame-ancestors 'none'" in health.headers["content-security-policy"]
        fixtures = client.get("/v1/fixtures")
        assert fixtures.status_code == 200
        assert len(fixtures.json()) == 3
        web = client.get("/")
        assets = client.get("/assets/app.js")
        assert web.status_code == 200
        assert "Paper2Proof — Claims into evidence" in web.text
        assert assets.status_code == 200
        assert "createJob" in assets.text


def test_public_request_size_and_rate_limit_boundaries() -> None:
    settings = Settings(runtime_mode="fixture", max_api_body_bytes=1_024)
    allowed_app = create_app(settings, rate_limiter=AllowingRateLimiter())
    with TestClient(allowed_app) as client:
        accepted = client.post(
            "/v1/jobs",
            json={
                "fixture_id": "reproducible-mean",
                "idempotency_key": "rate-limit-allowed",
            },
        )
        assert accepted.status_code == 202
        assert accepted.headers["x-ratelimit-limit"] == "30"
        assert accepted.headers["x-ratelimit-remaining"] == "29"

        oversized = client.post(
            "/v1/jobs",
            content="x" * 1_025,
            headers={"content-type": "application/json"},
        )
        assert oversized.status_code == 413
        assert oversized.json()["detail"] == "Request body exceeds the public API limit."

    denied_app = create_app(settings, rate_limiter=DenyingRateLimiter())
    with TestClient(denied_app) as client:
        denied = client.post(
            "/v1/jobs",
            json={
                "fixture_id": "reproducible-mean",
                "idempotency_key": "rate-limit-denied",
            },
        )
        assert denied.status_code == 429
        assert denied.headers["retry-after"] == "42"
        assert denied.headers["x-content-type-options"] == "nosniff"


def test_background_job_and_evidence_downloads() -> None:
    app = create_app(Settings(runtime_mode="fixture"))
    app.state.workflow.executor = StubExecutor()
    with TestClient(app) as client:
        created = client.post(
            "/v1/jobs",
            json={
                "fixture_id": "reproducible-mean",
                "execution_budget_seconds": 30,
                "idempotency_key": "api-test-key",
            },
        )
        assert created.status_code == 202
        job_id = created.json()["job_id"]
        payload = created.json()
        for _ in range(100):
            payload = client.get(f"/v1/jobs/{job_id}").json()
            if payload["status"] == "COMPLETED":
                break
            time.sleep(0.005)
        assert payload["status"] == "COMPLETED"
        json_download = client.get(f"/v1/jobs/{job_id}/evidence.json")
        markdown_download = client.get(f"/v1/jobs/{job_id}/evidence.md")
        assert json_download.status_code == 200
        assert markdown_download.status_code == 200
        assert json_download.json()["verdict"] == "PASS"
        assert "Paper2Proof Evidence Report" in markdown_download.text

        duplicate = client.post(
            "/v1/jobs",
            json={
                "fixture_id": "reproducible-mean",
                "execution_budget_seconds": 30,
                "idempotency_key": "api-test-key",
            },
        )
        assert duplicate.status_code == 200
        assert client.get(f"/v1/jobs/{job_id}").json()["job_id"] == job_id
        assert client.get("/v1/jobs").status_code == 405


def test_api_returns_structured_not_ready_not_found_and_conflict_errors() -> None:
    app = create_app(Settings(runtime_mode="fixture"))
    queued, _created = asyncio.run(
        app.state.workflow.create_job(
            JobRequest(fixture_id="reproducible-mean", idempotency_key="queued-api-test")
        )
    )
    with TestClient(app) as client:
        assert client.get("/v1/jobs/missing").status_code == 404
        assert (
            client.post("/v1/jobs/missing/decision", json={"option_id": "reject"}).status_code
            == 404
        )
        assert client.get(f"/v1/jobs/{queued.job_id}/evidence.json").status_code == 409
        assert client.get(f"/v1/jobs/{queued.job_id}/evidence.md").status_code == 409
        assert (
            client.post(
                f"/v1/jobs/{queued.job_id}/decision", json={"option_id": "approve"}
            ).status_code
            == 409
        )


def test_inline_api_completes_before_returning() -> None:
    app = create_app(Settings(runtime_mode="fixture", inline_jobs=True))
    app.state.workflow.executor = StubExecutor()
    with TestClient(app) as client:
        result = client.post(
            "/v1/jobs",
            json={
                "fixture_id": "reproducible-mean",
                "execution_budget_seconds": 30,
                "idempotency_key": "inline-api-test",
            },
        )
        assert result.status_code == 200
        assert result.json()["status"] == "COMPLETED"


def test_remote_api_relays_agentcore_job_without_building_local_workflow(monkeypatch) -> None:
    async def run(_self, request):  # type: ignore[no-untyped-def]
        local_app = create_app(Settings(runtime_mode="fixture"))
        local_app.state.workflow.executor = StubExecutor()
        job, _created = await local_app.state.workflow.create_job(request)
        job = await local_app.state.workflow.run(job.job_id)
        return job, True

    monkeypatch.setattr(AgentCoreRuntimeClient, "run", run)
    app = create_app(
        Settings(
            runtime_mode="agentcore",
            agent_runtime_arn=("arn:aws:bedrock-agentcore:us-west-2:123456789012:runtime/example"),
        )
    )
    assert app.state.workflow is None
    with TestClient(app) as client:
        response = client.post(
            "/v1/jobs",
            json={
                "fixture_id": "reproducible-mean",
                "execution_budget_seconds": 30,
                "idempotency_key": "remote-api-test",
            },
        )
    assert response.status_code == 200
    assert response.json()["status"] == "COMPLETED"


def test_remote_api_persists_then_dispatches_background_job(monkeypatch) -> None:
    async def create(_self, request):  # type: ignore[no-untyped-def]
        local_app = create_app(Settings(runtime_mode="fixture"))
        job, created = await local_app.state.workflow.create_job(request)
        return job, created

    monkeypatch.setattr(AgentCoreRuntimeClient, "create", create)
    dispatcher = RecordingDispatcher()
    app = create_app(
        Settings(
            runtime_mode="agentcore",
            agent_runtime_arn=("arn:aws:bedrock-agentcore:us-west-2:123456789012:runtime/example"),
        ),
        job_dispatcher=dispatcher,
    )

    with TestClient(app) as client:
        response = client.post(
            "/v1/jobs",
            json={
                "fixture_id": "reproducible-mean",
                "execution_budget_seconds": 30,
                "idempotency_key": "remote-background-test",
            },
        )

    assert response.status_code == 202
    assert response.json()["status"] == "QUEUED"
    assert dispatcher.job_ids == [response.json()["job_id"]]
