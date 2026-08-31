"""Privacy-preserving, cross-instance rate limiting for the anonymous public API."""

from __future__ import annotations

import asyncio
import hashlib
from datetime import UTC, datetime, timedelta
from typing import Any, NamedTuple, Protocol

import boto3  # type: ignore[import-untyped]
from botocore.exceptions import ClientError  # type: ignore[import-untyped]


class RateLimitExceeded(RuntimeError):
    """The caller consumed the bounded public-demo allowance."""

    def __init__(self, *, retry_after_seconds: int) -> None:
        super().__init__("public demo rate limit exceeded")
        self.retry_after_seconds = retry_after_seconds


class RateLimitResult(NamedTuple):
    limit: int
    remaining: int
    retry_after_seconds: int


class RateLimiter(Protocol):
    async def check(self, subject: str) -> RateLimitResult: ...


class DynamoDBHourlyRateLimiter:
    """One atomic counter per hashed caller and UTC hour."""

    def __init__(
        self,
        *,
        table_name: str,
        limit: int,
        region: str,
        client: Any | None = None,
    ) -> None:
        if limit < 1:
            raise ValueError("rate limit must be positive")
        self.table_name = table_name
        self.limit = limit
        self.client = client or boto3.client("dynamodb", region_name=region)

    async def check(self, subject: str) -> RateLimitResult:
        return await asyncio.to_thread(self._check_sync, subject, datetime.now(UTC))

    def _check_sync(self, subject: str, now: datetime) -> RateLimitResult:
        hour = now.replace(minute=0, second=0, microsecond=0)
        next_hour = hour + timedelta(hours=1)
        retry_after = max(1, int((next_hour - now).total_seconds()))
        subject_hash = hashlib.sha256(subject.encode()).hexdigest()[:32]
        key = f"RATE#{hour:%Y%m%d%H}#{subject_hash}"
        try:
            response = self.client.update_item(
                TableName=self.table_name,
                Key={"pk": {"S": key}},
                UpdateExpression=(
                    "SET expires_at = :expires, entity = if_not_exists(entity, :entity) "
                    "ADD request_count :one"
                ),
                ConditionExpression=(
                    "attribute_not_exists(request_count) OR request_count < :limit"
                ),
                ExpressionAttributeValues={
                    ":expires": {"N": str(int((next_hour + timedelta(days=2)).timestamp()))},
                    ":entity": {"S": "rate-limit"},
                    ":one": {"N": "1"},
                    ":limit": {"N": str(self.limit)},
                },
                ReturnValues="UPDATED_NEW",
            )
        except ClientError as exc:
            if exc.response.get("Error", {}).get("Code") == "ConditionalCheckFailedException":
                raise RateLimitExceeded(retry_after_seconds=retry_after) from exc
            raise
        count = int(response["Attributes"]["request_count"]["N"])
        return RateLimitResult(
            limit=self.limit,
            remaining=max(0, self.limit - count),
            retry_after_seconds=retry_after,
        )
