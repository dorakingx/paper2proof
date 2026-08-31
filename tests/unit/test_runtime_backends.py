from __future__ import annotations

import subprocess
from collections.abc import Iterator
from types import SimpleNamespace
from typing import Any

import paper2proof.executors.agentcore as agentcore_module
import paper2proof.executors.docker as docker_module
import pytest
from paper2proof.executors.agentcore import AgentCoreExecutor
from paper2proof.executors.docker import DockerSandboxExecutor
from paper2proof.fixtures import load_fixture
from paper2proof.schemas import ExecutionStatus, RuntimeProvenance
from paper2proof.tracing import TraceRecorder


def trace() -> TraceRecorder:
    return TraceRecorder("trace_0123456789abcdef")


@pytest.mark.asyncio
async def test_docker_backend_records_success_and_hardening_flags(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: list[str] = []

    def fake_run(command: list[str], **_kwargs: Any) -> subprocess.CompletedProcess[str]:
        captured.extend(command)
        return subprocess.CompletedProcess(
            command,
            0,
            stdout='PAPER2PROOF_RESULT={"observed": 5.0}\n',
            stderr="",
        )

    monkeypatch.setattr(docker_module.subprocess, "run", fake_run)
    result = await DockerSandboxExecutor(image="python:test").execute(
        load_fixture("reproducible-mean").plan, trace()
    )

    assert result.status == ExecutionStatus.SUCCESS
    assert result.observed_value == 5.0
    assert result.provenance == RuntimeProvenance.DOCKER_LOCAL
    assert "--interactive" in captured
    assert "--network" in captured and "none" in captured
    assert "--read-only" in captured and "--cap-drop" in captured


@pytest.mark.asyncio
async def test_docker_backend_records_nonzero_exit(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_run(command: list[str], **_kwargs: Any) -> subprocess.CompletedProcess[str]:
        return subprocess.CompletedProcess(command, 2, stdout="partial", stderr="experiment failed")

    monkeypatch.setattr(docker_module.subprocess, "run", fake_run)
    result = await DockerSandboxExecutor().execute(load_fixture("reproducible-mean").plan, trace())

    assert result.status == ExecutionStatus.ERROR
    assert result.exit_code == 2
    assert result.failure_reason == "sandbox process failed"


@pytest.mark.asyncio
async def test_docker_backend_cleans_up_exact_container_after_timeout(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[list[str]] = []

    def fake_run(command: list[str], **_kwargs: Any) -> subprocess.CompletedProcess[str]:
        calls.append(command)
        if len(calls) == 1:
            raise subprocess.TimeoutExpired(command, 1, output=b"partial", stderr=b"late")
        return subprocess.CompletedProcess(command, 0, stdout="", stderr="")

    monkeypatch.setattr(docker_module.subprocess, "run", fake_run)
    result = await DockerSandboxExecutor().execute(load_fixture("reproducible-mean").plan, trace())

    assert result.status == ExecutionStatus.ERROR
    assert "timeout" in (result.failure_reason or "")
    assert result.stdout == "partial"
    assert calls[1][1:3] == ["rm", "-f"]
    assert calls[1][3] == calls[0][calls[0].index("--name") + 1]


@pytest.mark.asyncio
async def test_docker_backend_handles_missing_runtime(monkeypatch: pytest.MonkeyPatch) -> None:
    def missing_runtime(*_args: Any, **_kwargs: Any) -> None:
        raise FileNotFoundError("docker unavailable")

    monkeypatch.setattr(docker_module.subprocess, "run", missing_runtime)
    result = await DockerSandboxExecutor().execute(load_fixture("reproducible-mean").plan, trace())

    assert result.status == ExecutionStatus.ERROR
    assert result.failure_reason == "docker unavailable"


def install_agentcore_fake(monkeypatch: pytest.MonkeyPatch, results: list[dict[str, Any]]) -> None:
    class FakeInterpreter:
        def __init__(self, **_kwargs: Any) -> None:
            self.results: Iterator[dict[str, Any]] = iter(results)

        def code_interpreter(self, **_kwargs: Any) -> dict[str, Any]:
            return next(self.results)

    class FakeAgent:
        def __init__(self, *, tools: list[Any], **_kwargs: Any) -> None:
            self.tool = SimpleNamespace(code_interpreter=tools[0])

    monkeypatch.setattr(agentcore_module, "AgentCoreCodeInterpreter", FakeInterpreter)
    monkeypatch.setattr(agentcore_module, "Agent", FakeAgent)


@pytest.mark.asyncio
async def test_agentcore_backend_records_live_success(monkeypatch: pytest.MonkeyPatch) -> None:
    install_agentcore_fake(
        monkeypatch,
        [
            {"status": "success", "content": [{"text": "{'sessionId': 'session-123'}"}]},
            {
                "status": "success",
                "content": [{"text": 'PAPER2PROOF_RESULT={"observed": 5.0}'}],
            },
        ],
    )
    result = await AgentCoreExecutor().execute(load_fixture("reproducible-mean").plan, trace())

    assert result.status == ExecutionStatus.SUCCESS
    assert result.provenance == RuntimeProvenance.AGENTCORE_LIVE
    assert result.session_id == "session-123"
    assert result.observed_value == 5.0


@pytest.mark.asyncio
async def test_agentcore_backend_records_initialization_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    install_agentcore_fake(
        monkeypatch,
        [{"status": "error", "content": [{"json": {"message": "access denied"}}]}],
    )
    result = await AgentCoreExecutor().execute(load_fixture("reproducible-mean").plan, trace())

    assert result.status == ExecutionStatus.ERROR
    assert "access denied" in (result.failure_reason or "")


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "execute_result, expected_reason",
    [
        ({"status": "error", "content": [{"text": "remote failure"}]}, "remote failure"),
        ({"status": "success", "content": [{"text": "missing result envelope"}]}, "exactly one"),
    ],
)
async def test_agentcore_backend_records_execution_failures(
    monkeypatch: pytest.MonkeyPatch,
    execute_result: dict[str, Any],
    expected_reason: str,
) -> None:
    install_agentcore_fake(
        monkeypatch,
        [
            {"status": "success", "content": [{"text": "session ready"}]},
            execute_result,
        ],
    )
    result = await AgentCoreExecutor().execute(load_fixture("reproducible-mean").plan, trace())

    assert result.status == ExecutionStatus.ERROR
    assert expected_reason in (result.failure_reason or "")
