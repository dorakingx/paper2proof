"""Bounded SQS dispatch for durable background execution."""

from __future__ import annotations

import asyncio
import json
from typing import Annotated, Any, Protocol

import boto3  # type: ignore[import-untyped]
from pydantic import StringConstraints

from paper2proof.schemas import StrictModel


class JobMessage(StrictModel):
    job_id: Annotated[str, StringConstraints(pattern=r"^job_[a-f0-9]{16,64}$")]


class JobDispatcher(Protocol):
    async def dispatch(self, job_id: str) -> None: ...


class SQSJobDispatcher:
    def __init__(
        self,
        *,
        queue_url: str,
        region: str,
        client: Any | None = None,
    ) -> None:
        if not queue_url:
            raise ValueError("queue_url is required")
        self.queue_url = queue_url
        self.client = client or boto3.client("sqs", region_name=region)

    async def dispatch(self, job_id: str) -> None:
        message = JobMessage(job_id=job_id)
        await asyncio.to_thread(
            self.client.send_message,
            QueueUrl=self.queue_url,
            MessageBody=json.dumps(message.model_dump(mode="json"), separators=(",", ":")),
            MessageGroupId=f"job-{job_id[-16:]}",
            MessageDeduplicationId=job_id,
        )
