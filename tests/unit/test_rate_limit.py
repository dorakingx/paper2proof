from __future__ import annotations

from datetime import UTC, datetime

import pytest
from botocore.exceptions import ClientError
from paper2proof.rate_limit import DynamoDBHourlyRateLimiter, RateLimitExceeded


class RecordingDynamoDB:
    def __init__(self, count: int = 1) -> None:
        self.count = count
        self.arguments = None

    def update_item(self, **kwargs):
        self.arguments = kwargs
        return {"Attributes": {"request_count": {"N": str(self.count)}}}


class RejectingDynamoDB:
    def update_item(self, **_kwargs):
        raise ClientError(
            {
                "Error": {
                    "Code": "ConditionalCheckFailedException",
                    "Message": "limit reached",
                }
            },
            "UpdateItem",
        )


def test_rate_limit_uses_hashed_hourly_key_and_ttl() -> None:
    client = RecordingDynamoDB(count=4)
    limiter = DynamoDBHourlyRateLimiter(
        table_name="paper2proof-jobs",
        limit=30,
        region="us-west-2",
        client=client,
    )

    result = limiter._check_sync("203.0.113.10", datetime(2026, 8, 31, 11, 15, tzinfo=UTC))

    assert result.limit == 30
    assert result.remaining == 26
    assert result.retry_after_seconds == 45 * 60
    assert client.arguments is not None
    key = client.arguments["Key"]["pk"]["S"]
    assert key.startswith("RATE#2026083111#")
    assert "203.0.113.10" not in key
    assert client.arguments["ExpressionAttributeValues"][":expires"]["N"] == "1788350400"


def test_rate_limit_maps_conditional_failure_to_bounded_error() -> None:
    limiter = DynamoDBHourlyRateLimiter(
        table_name="paper2proof-jobs",
        limit=1,
        region="us-west-2",
        client=RejectingDynamoDB(),
    )

    with pytest.raises(RateLimitExceeded) as exc_info:
        limiter._check_sync("judge", datetime(2026, 8, 31, 11, 59, 30, tzinfo=UTC))

    assert exc_info.value.retry_after_seconds == 30
