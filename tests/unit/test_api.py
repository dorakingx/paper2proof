from __future__ import annotations

import asyncio
import time

from fastapi.testclient import TestClient
from paper2proof.api import create_app
from paper2proof.config import Settings
from paper2proof.schemas import JobRequest

from tests.unit.helpers import StubExecutor


def test_health_and_fixture_catalog() -> None:
    app = create_app(Settings(runtime_mode="fixture"))
    with TestClient(app) as client:
        health = client.get("/health")
        assert health.status_code == 200
        assert health.json()["strands_agents"] is True
        assert health.json()["agentcore_code_interpreter"] is False
        fixtures = client.get("/v1/fixtures")
        assert fixtures.status_code == 200
        assert len(fixtures.json()) == 3


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
        assert client.get("/v1/jobs").json()[0]["job_id"] == job_id


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
