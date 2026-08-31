"""Amazon Bedrock AgentCore Code Interpreter backend via a Strands direct tool call."""

from __future__ import annotations

import asyncio
import hashlib
import json
import re
import uuid
from datetime import UTC, datetime
from typing import Any, cast

from strands import Agent
from strands_tools.code_interpreter import AgentCoreCodeInterpreter

from paper2proof.executors.base import parse_observed_value
from paper2proof.null_model import DirectToolOnlyModel
from paper2proof.schemas import (
    ExecutionRecord,
    ExecutionStatus,
    ExperimentPlan,
    RuntimeProvenance,
    TraceEventType,
)
from paper2proof.security import SecurityViolation, validate_python_code
from paper2proof.tracing import TraceRecorder

SESSION_ID_PATTERN = re.compile(r"['\"]sessionId['\"]\s*:\s*['\"]([^'\"]+)['\"]")


def _content_text(result: dict[str, Any]) -> str:
    chunks: list[str] = []
    for item in result.get("content", []):
        if "text" in item:
            chunks.append(str(item["text"]))
        elif "json" in item:
            chunks.append(json.dumps(item["json"], sort_keys=True))
    return "\n".join(chunks)


class AgentCoreExecutor:
    """Execute approved Python through the official Strands AgentCore tool."""

    def __init__(
        self,
        *,
        region: str = "us-west-2",
        identifier: str = "aws.codeinterpreter.v1",
        max_output_bytes: int = 1_000_000,
    ) -> None:
        self.region = region
        self.identifier = identifier
        self.max_output_bytes = max_output_bytes

    async def execute(self, plan: ExperimentPlan, trace: TraceRecorder) -> ExecutionRecord:
        return await asyncio.to_thread(self._execute_sync, plan, trace)

    def _execute_sync(self, plan: ExperimentPlan, trace: TraceRecorder) -> ExecutionRecord:
        started = datetime.now(UTC)
        execution_id = f"exec_{uuid.uuid4().hex}"
        session_name = f"paper2proof-{uuid.uuid4().hex[:20]}"
        code_sha = hashlib.sha256(plan.code.encode()).hexdigest()
        try:
            safety = validate_python_code(plan.code)
        except SecurityViolation as exc:
            completed = datetime.now(UTC)
            raw = str(exc)
            trace.add(
                TraceEventType.GUARDRAIL,
                "Execution Agent",
                "python-ast-policy",
                input_value={"code_sha256": code_sha},
                output_value={"blocked": True, "reason": raw},
            )
            return ExecutionRecord(
                execution_id=execution_id,
                status=ExecutionStatus.BLOCKED,
                provenance=RuntimeProvenance.AGENTCORE_LIVE,
                service="Amazon Bedrock AgentCore Code Interpreter",
                region=self.region,
                sandbox_identifier=self.identifier,
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
            TraceEventType.GUARDRAIL,
            "Execution Agent",
            "python-ast-policy",
            input_value={"code_sha256": code_sha},
            output_value={"ast_nodes": safety.node_count, "imports": safety.imports},
        )
        tool = AgentCoreCodeInterpreter(
            region=self.region,
            identifier=self.identifier,
            auto_create=False,
            persist_sessions=False,
            session_timeout_seconds=min(plan.timeout_seconds + 30, 300),
        )
        agent = Agent(
            model=DirectToolOnlyModel(),
            tools=[tool.code_interpreter],
            callback_handler=None,
            hooks=cast(Any, trace.strands_hooks("Execution Agent")),
            agent_id="paper2proof-execution-agent",
            name="Execution Agent",
            description="Runs one approved experiment in AgentCore Code Interpreter.",
        )

        init_result = agent.tool.code_interpreter(
            code_interpreter_input={
                "action": {
                    "type": "initSession",
                    "description": "Paper2Proof bounded reproduction experiment",
                    "session_name": session_name,
                }
            }
        )
        init_text = _content_text(init_result)
        session_match = SESSION_ID_PATTERN.search(init_text)
        session_id = session_match.group(1) if session_match else None
        if init_result.get("status") != "success":
            return self._error_record(
                execution_id,
                plan,
                started,
                code_sha,
                init_text or "AgentCore session initialization failed",
                session_id,
            )

        execute_result = agent.tool.code_interpreter(
            code_interpreter_input={
                "action": {
                    "type": "executeCode",
                    "session_name": session_name,
                    "code": plan.code,
                    "language": "python",
                    "clear_context": True,
                }
            }
        )
        raw = json.dumps(execute_result, sort_keys=True, default=str)
        stdout = _content_text(execute_result)[: self.max_output_bytes]
        stderr = ""
        status = (
            ExecutionStatus.SUCCESS
            if execute_result.get("status") == "success"
            else ExecutionStatus.ERROR
        )
        observed: float | None = None
        failure_reason: str | None = None
        if status == ExecutionStatus.SUCCESS:
            try:
                observed = parse_observed_value(stdout)
            except ValueError as exc:
                status = ExecutionStatus.ERROR
                failure_reason = str(exc)
                stderr = str(exc)
        else:
            failure_reason = stdout or "AgentCore execution failed"
            stderr = failure_reason

        completed = datetime.now(UTC)
        return ExecutionRecord(
            execution_id=execution_id,
            status=status,
            provenance=RuntimeProvenance.AGENTCORE_LIVE,
            service="Amazon Bedrock AgentCore Code Interpreter",
            region=self.region,
            sandbox_identifier=self.identifier,
            session_id=session_id,
            started_at=started,
            completed_at=completed,
            duration_ms=int((completed - started).total_seconds() * 1_000),
            command_display=plan.command_display,
            code_sha256=code_sha,
            exit_code=0 if status == ExecutionStatus.SUCCESS else 1,
            stdout=stdout,
            stderr=stderr,
            observed_value=observed,
            raw_response_sha256=hashlib.sha256(raw.encode()).hexdigest(),
            failure_reason=failure_reason,
        )

    def _error_record(
        self,
        execution_id: str,
        plan: ExperimentPlan,
        started: datetime,
        code_sha: str,
        reason: str,
        session_id: str | None,
    ) -> ExecutionRecord:
        completed = datetime.now(UTC)
        return ExecutionRecord(
            execution_id=execution_id,
            status=ExecutionStatus.ERROR,
            provenance=RuntimeProvenance.AGENTCORE_LIVE,
            service="Amazon Bedrock AgentCore Code Interpreter",
            region=self.region,
            sandbox_identifier=self.identifier,
            session_id=session_id,
            started_at=started,
            completed_at=completed,
            duration_ms=int((completed - started).total_seconds() * 1_000),
            command_display=plan.command_display,
            code_sha256=code_sha,
            exit_code=1,
            stderr=reason[: self.max_output_bytes],
            raw_response_sha256=hashlib.sha256(reason.encode()).hexdigest(),
            failure_reason=reason,
        )
