from __future__ import annotations

import importlib.util
import json
from pathlib import Path
from types import ModuleType, SimpleNamespace

from paper2proof.schemas import JobRecord, JobRequest, JobStatus


def load_worker() -> ModuleType:
    path = Path(__file__).resolve().parents[2] / "services" / "api" / "worker.py"
    spec = importlib.util.spec_from_file_location("paper2proof_test_worker", path)
    if spec is None or spec.loader is None:
        raise RuntimeError("worker module could not be loaded")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def job(status: JobStatus) -> JobRecord:
    return JobRecord(
        job_id="job_0123456789abcdef",
        trace_id="trace_0123456789abcdef",
        request=JobRequest(
            fixture_id="reproducible-mean",
            idempotency_key="worker-contract-test",
        ),
        status=status,
    )


def test_worker_reports_only_failed_sqs_items(monkeypatch) -> None:
    worker = load_worker()

    class RuntimeClient:
        def __init__(self, **_kwargs) -> None:
            pass

        async def run_job(self, _job_id: str) -> JobRecord:
            return job(JobStatus.COMPLETED)

    monkeypatch.setattr(worker, "AgentCoreRuntimeClient", RuntimeClient)
    monkeypatch.setattr(
        worker,
        "get_settings",
        lambda: SimpleNamespace(agent_runtime_arn="arn:example", aws_region="us-west-2"),
    )
    event = {
        "Records": [
            {
                "messageId": "valid",
                "body": json.dumps({"job_id": "job_0123456789abcdef"}),
            },
            {"messageId": "invalid", "body": "not-json"},
        ]
    }

    result = worker.handler(event, None)

    assert result == {"batchItemFailures": [{"itemIdentifier": "invalid"}]}


def test_worker_retries_non_stable_runtime_result(monkeypatch) -> None:
    worker = load_worker()

    class RuntimeClient:
        def __init__(self, **_kwargs) -> None:
            pass

        async def run_job(self, _job_id: str) -> JobRecord:
            return job(JobStatus.INTAKE)

    monkeypatch.setattr(worker, "AgentCoreRuntimeClient", RuntimeClient)
    monkeypatch.setattr(
        worker,
        "get_settings",
        lambda: SimpleNamespace(agent_runtime_arn="arn:example", aws_region="us-west-2"),
    )

    result = worker.handler(
        {
            "Records": [
                {
                    "messageId": "retry-me",
                    "body": json.dumps({"job_id": "job_0123456789abcdef"}),
                }
            ]
        },
        None,
    )

    assert result == {"batchItemFailures": [{"itemIdentifier": "retry-me"}]}
