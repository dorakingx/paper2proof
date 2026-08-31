"""Strict client for the private Paper2Proof AgentCore Runtime."""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Any
from uuid import uuid4

import boto3  # type: ignore[import-untyped]
from botocore.config import Config  # type: ignore[import-untyped]
from botocore.exceptions import BotoCoreError, ClientError  # type: ignore[import-untyped]
from pydantic import ValidationError

from paper2proof.schemas import DecisionSubmission, JobRecord, JobRequest

MAX_RUNTIME_RESPONSE_BYTES = 8_000_000
LOGGER = logging.getLogger(__name__)


class AgentRuntimeError(RuntimeError):
    """A safe, public-facing representation of an AgentCore invocation failure."""

    def __init__(self, *, code: str, message: str, status_code: int = 502) -> None:
        super().__init__(message)
        self.code = code
        self.public_message = message
        self.status_code = status_code


class AgentCoreRuntimeClient:
    """Invoke the bounded Runtime command surface and revalidate every response."""

    def __init__(
        self,
        *,
        runtime_arn: str,
        region: str,
        read_timeout_seconds: int = 165,
        client: Any | None = None,
    ) -> None:
        if not runtime_arn:
            raise ValueError("runtime_arn is required")
        self.runtime_arn = runtime_arn
        self.client = client or boto3.client(
            "bedrock-agentcore",
            region_name=region,
            config=Config(
                connect_timeout=5,
                read_timeout=read_timeout_seconds,
                retries={"max_attempts": 2, "mode": "standard"},
            ),
        )

    async def health(self) -> dict[str, Any]:
        return await self._invoke({"action": "health"})

    async def run(self, request: JobRequest) -> tuple[JobRecord, bool]:
        result = await self._invoke({"action": "run", "request": request.model_dump(mode="json")})
        created = result.get("created")
        if not isinstance(created, bool):
            raise self._invalid_response()
        return self._validated_job(result.get("job")), created

    async def create(self, request: JobRequest) -> tuple[JobRecord, bool]:
        result = await self._invoke(
            {"action": "create", "request": request.model_dump(mode="json")}
        )
        created = result.get("created")
        if not isinstance(created, bool):
            raise self._invalid_response()
        return self._validated_job(result.get("job")), created

    async def run_job(self, job_id: str) -> JobRecord:
        result = await self._invoke({"action": "run_job", "job_id": job_id})
        return self._validated_job(result.get("job"))

    async def get(self, job_id: str) -> JobRecord:
        result = await self._invoke({"action": "get", "job_id": job_id})
        return self._validated_job(result.get("job"))

    async def decide(self, job_id: str, decision: DecisionSubmission) -> JobRecord:
        result = await self._invoke(
            {
                "action": "decide",
                "job_id": job_id,
                "decision": decision.model_dump(mode="json"),
            }
        )
        return self._validated_job(result.get("job"))

    async def _invoke(self, payload: dict[str, Any]) -> dict[str, Any]:
        return await asyncio.to_thread(self._invoke_sync, payload)

    def _invoke_sync(self, payload: dict[str, Any]) -> dict[str, Any]:
        try:
            response = self.client.invoke_agent_runtime(
                agentRuntimeArn=self.runtime_arn,
                qualifier="DEFAULT",
                runtimeSessionId=f"paper2proof-{uuid4().hex}",
                contentType="application/json",
                accept="application/json",
                payload=json.dumps(payload, separators=(",", ":")).encode("utf-8"),
            )
        except (BotoCoreError, ClientError) as exc:
            error_code = "unknown"
            if isinstance(exc, ClientError):
                error_code = str(exc.response.get("Error", {}).get("Code", "unknown"))
            LOGGER.warning(
                "AgentCore invocation failed (%s: %s)",
                type(exc).__name__,
                error_code,
            )
            raise AgentRuntimeError(
                code="upstream_unavailable",
                message="AgentCore Runtime is temporarily unavailable.",
            ) from exc

        status_code = response.get("statusCode", 200)
        if not isinstance(status_code, int) or not 200 <= status_code < 300:
            raise AgentRuntimeError(
                code="upstream_failure",
                message="AgentCore Runtime could not complete the request.",
            )

        body = response.get("response")
        raw = self._read_body(body)
        if len(raw) > MAX_RUNTIME_RESPONSE_BYTES:
            raise AgentRuntimeError(
                code="upstream_response_too_large",
                message="AgentCore Runtime returned more evidence than the public API can relay.",
            )
        try:
            decoded = json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise self._invalid_response() from exc
        if not isinstance(decoded, dict):
            raise self._invalid_response()
        if decoded.get("ok") is not True:
            self._raise_runtime_error(decoded.get("error"))
        return decoded

    @staticmethod
    def _read_body(body: Any) -> bytes:
        if isinstance(body, bytes):
            return body
        if isinstance(body, bytearray):
            return bytes(body)
        read = getattr(body, "read", None)
        if not callable(read):
            raise AgentCoreRuntimeClient._invalid_response()
        try:
            value = read(MAX_RUNTIME_RESPONSE_BYTES + 1)
        finally:
            close = getattr(body, "close", None)
            if callable(close):
                close()
        if not isinstance(value, bytes):
            raise AgentCoreRuntimeClient._invalid_response()
        return value

    @staticmethod
    def _raise_runtime_error(error: Any) -> None:
        code = error.get("code") if isinstance(error, dict) else None
        if code == "not_found":
            raise AgentRuntimeError(code=code, message="Job not found.", status_code=404)
        if code == "conflict":
            raise AgentRuntimeError(
                code=code,
                message="The job state conflicts with this action.",
                status_code=409,
            )
        raise AgentRuntimeError(
            code="upstream_failure",
            message="AgentCore Runtime could not complete the request.",
        )

    @staticmethod
    def _validated_job(value: Any) -> JobRecord:
        try:
            return JobRecord.model_validate(value)
        except ValidationError as exc:
            raise AgentCoreRuntimeClient._invalid_response() from exc

    @staticmethod
    def _invalid_response() -> AgentRuntimeError:
        return AgentRuntimeError(
            code="invalid_upstream_response",
            message="AgentCore Runtime returned an invalid response.",
        )
