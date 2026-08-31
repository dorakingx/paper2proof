"""Local development fallback that never executes submitted code on the host."""

from __future__ import annotations

import asyncio
import hashlib
import json
import shutil
import subprocess
import uuid
from datetime import UTC, datetime

from paper2proof.executors.base import parse_observed_value
from paper2proof.schemas import (
    ExecutionRecord,
    ExecutionStatus,
    ExperimentPlan,
    RuntimeProvenance,
    TraceEventType,
)
from paper2proof.security import SecurityViolation, validate_python_code
from paper2proof.tracing import TraceRecorder


class DockerSandboxExecutor:
    """Run allowlisted Python in a networkless, read-only, resource-bounded container."""

    def __init__(
        self,
        image: str = (
            "python@sha256:7ce4b6dfe35e55397b7cda544f8a13f191b7ae28dc5aad71fe664dbc9bc2623f"
        ),
        max_output_bytes: int = 1_000_000,
    ) -> None:
        self.image = image
        self.max_output_bytes = max_output_bytes
        self.docker_binary = shutil.which("docker") or "/usr/local/bin/docker"

    async def execute(self, plan: ExperimentPlan, trace: TraceRecorder) -> ExecutionRecord:
        return await asyncio.to_thread(self._execute_sync, plan, trace)

    def _execute_sync(self, plan: ExperimentPlan, trace: TraceRecorder) -> ExecutionRecord:
        started = datetime.now(UTC)
        execution_id = f"exec_{uuid.uuid4().hex}"
        code_sha = hashlib.sha256(plan.code.encode()).hexdigest()
        container_name = f"paper2proof-{uuid.uuid4().hex[:16]}"
        trace.add(
            TraceEventType.GUARDRAIL,
            "Execution Agent",
            "python-ast-policy",
            input_value={"code_sha256": code_sha},
        )
        try:
            safety = validate_python_code(plan.code)
        except SecurityViolation as exc:
            completed = datetime.now(UTC)
            raw = str(exc)
            return ExecutionRecord(
                execution_id=execution_id,
                status=ExecutionStatus.BLOCKED,
                provenance=RuntimeProvenance.DOCKER_LOCAL,
                service="Docker local fallback",
                sandbox_identifier=self.image,
                started_at=started,
                completed_at=completed,
                duration_ms=int((completed - started).total_seconds() * 1_000),
                command_display=plan.command_display,
                code_sha256=code_sha,
                stderr=raw,
                raw_response_sha256=hashlib.sha256(raw.encode()).hexdigest(),
                failure_reason=raw,
            )

        trace.add(
            TraceEventType.TOOL_START,
            "Execution Agent",
            "docker-sandbox",
            input_value={
                "image": self.image,
                "network": "none",
                "read_only": True,
                "code_sha256": code_sha,
                "ast_nodes": safety.node_count,
                "imports": safety.imports,
            },
        )
        command = [
            self.docker_binary,
            "run",
            "--rm",
            "--interactive",
            "--name",
            container_name,
            "--network",
            "none",
            "--read-only",
            "--cap-drop",
            "ALL",
            "--security-opt",
            "no-new-privileges",
            "--pids-limit",
            "64",
            "--memory",
            "256m",
            "--cpus",
            "0.5",
            "--tmpfs",
            "/tmp:rw,noexec,nosuid,size=32m",  # noqa: S108 - container-internal tmpfs
            self.image,
            "python",
            "-I",
            "-",
        ]
        try:
            process = subprocess.run(  # noqa: S603 - fixed executable and reviewed argv
                command,
                input=plan.code,
                capture_output=True,
                text=True,
                timeout=plan.timeout_seconds,
                check=False,
            )
            stdout = process.stdout[: self.max_output_bytes]
            stderr = process.stderr[: self.max_output_bytes]
            observed = parse_observed_value(stdout) if process.returncode == 0 else None
            status = ExecutionStatus.SUCCESS if process.returncode == 0 else ExecutionStatus.ERROR
            failure_reason = None if status == ExecutionStatus.SUCCESS else "sandbox process failed"
            raw = json.dumps(
                {"exit_code": process.returncode, "stdout": stdout, "stderr": stderr},
                sort_keys=True,
            )
        except subprocess.TimeoutExpired as exc:
            subprocess.run(  # noqa: S603 - exact dedicated container name
                [self.docker_binary, "rm", "-f", container_name],
                capture_output=True,
                check=False,
                timeout=10,
            )
            timeout_stdout = exc.stdout or ""
            timeout_stderr = exc.stderr or ""
            stdout = (
                timeout_stdout.decode(errors="replace")
                if isinstance(timeout_stdout, bytes)
                else timeout_stdout
            )[: self.max_output_bytes]
            stderr = (
                timeout_stderr.decode(errors="replace")
                if isinstance(timeout_stderr, bytes)
                else timeout_stderr
            )[: self.max_output_bytes]
            observed = None
            status = ExecutionStatus.ERROR
            failure_reason = f"sandbox exceeded {plan.timeout_seconds}s timeout"
            raw = json.dumps({"timeout": True, "stdout": stdout, "stderr": stderr}, sort_keys=True)
            process = None
        except (FileNotFoundError, ValueError) as exc:
            stdout = ""
            stderr = str(exc)
            observed = None
            status = ExecutionStatus.ERROR
            failure_reason = str(exc)
            raw = str(exc)
            process = None

        completed = datetime.now(UTC)
        trace.add(
            TraceEventType.TOOL_OUTPUT,
            "Execution Agent",
            "docker-sandbox",
            output_value={
                "status": status,
                "exit_code": process.returncode if process else None,
                "raw_response_sha256": hashlib.sha256(raw.encode()).hexdigest(),
            },
        )
        return ExecutionRecord(
            execution_id=execution_id,
            status=status,
            provenance=RuntimeProvenance.DOCKER_LOCAL,
            service="Docker local fallback",
            sandbox_identifier=self.image,
            started_at=started,
            completed_at=completed,
            duration_ms=int((completed - started).total_seconds() * 1_000),
            command_display=plan.command_display,
            code_sha256=code_sha,
            exit_code=process.returncode if process else None,
            stdout=stdout,
            stderr=stderr,
            observed_value=observed,
            raw_response_sha256=hashlib.sha256(raw.encode()).hexdigest(),
            failure_reason=failure_reason,
        )
