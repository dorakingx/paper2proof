"""SQS Lambda worker that runs durable Paper2Proof jobs in AgentCore Runtime."""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Any

from paper2proof.agentcore_client import AgentCoreRuntimeClient
from paper2proof.config import get_settings
from paper2proof.queue import JobMessage
from paper2proof.schemas import TERMINAL_STATUSES, JobStatus

LOGGER = logging.getLogger(__name__)


def handler(event: dict[str, Any], _context: Any) -> dict[str, list[dict[str, str]]]:
    settings = get_settings()
    client = AgentCoreRuntimeClient(
        runtime_arn=settings.agent_runtime_arn,
        region=settings.aws_region,
        read_timeout_seconds=570,
    )
    failures: list[dict[str, str]] = []
    for record in event.get("Records", []):
        message_id = str(record.get("messageId", "unknown"))
        try:
            message = JobMessage.model_validate(json.loads(record["body"]))
            job = asyncio.run(client.run_job(message.job_id))
            if job.status not in TERMINAL_STATUSES | {JobStatus.AWAITING_APPROVAL}:
                raise RuntimeError("worker returned before the job reached a stable state")
        except Exception as exc:
            LOGGER.warning("Background job failed safely (%s)", type(exc).__name__)
            failures.append({"itemIdentifier": message_id})
    return {"batchItemFailures": failures}
