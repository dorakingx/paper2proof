from __future__ import annotations

from typing import Any

import pytest
from botocore.exceptions import ClientError
from paper2proof.schemas import JobRecord, JobRequest, JobStatus
from paper2proof.store import DynamoDBJobStore, JobNotFoundError


class FakeDynamoDBClient:
    def __init__(self) -> None:
        self.items: dict[str, dict[str, dict[str, str]]] = {}

    def transact_write_items(self, *, TransactItems: list[dict[str, Any]]) -> None:
        keys = [item["Put"]["Item"]["pk"]["S"] for item in TransactItems]
        if any(key in self.items for key in keys):
            raise ClientError(
                {"Error": {"Code": "TransactionCanceledException", "Message": "conflict"}},
                "TransactWriteItems",
            )
        for item in TransactItems:
            payload = item["Put"]["Item"]
            self.items[payload["pk"]["S"]] = payload

    def get_item(self, *, Key: dict[str, Any], **_kwargs: Any) -> dict[str, Any]:
        item = self.items.get(Key["pk"]["S"])
        return {"Item": item} if item else {}

    def put_item(self, *, Item: dict[str, Any], **_kwargs: Any) -> None:
        key = Item["pk"]["S"]
        if key not in self.items:
            raise ClientError(
                {
                    "Error": {
                        "Code": "ConditionalCheckFailedException",
                        "Message": "missing",
                    }
                },
                "PutItem",
            )
        self.items[key] = Item

    def scan(self, **_kwargs: Any) -> dict[str, Any]:
        return {
            "Items": [
                item for item in self.items.values() if item.get("entity", {}).get("S") == "job"
            ]
        }


def job(key: str = "dynamo-idempotency") -> JobRecord:
    return JobRecord(
        job_id="job_0123456789abcdef",
        trace_id="trace_0123456789abcdef",
        request=JobRequest(fixture_id="reproducible-mean", idempotency_key=key),
    )


@pytest.mark.asyncio
async def test_dynamodb_store_atomically_deduplicates_and_persists_jobs() -> None:
    client = FakeDynamoDBClient()
    store = DynamoDBJobStore(table_name="jobs", region="us-west-2", client=client)
    original = job()
    created, first_created = await store.create(original)
    duplicate = original.model_copy(update={"job_id": "job_fedcba9876543210"})
    existing, second_created = await store.create(duplicate)

    assert first_created is True
    assert second_created is False
    assert existing.job_id == created.job_id

    created.status = JobStatus.INTAKE
    await store.save(created)
    loaded = await store.get(created.job_id)
    listed = await store.list()
    assert loaded.status == JobStatus.INTAKE
    assert [item.job_id for item in listed] == [created.job_id]


@pytest.mark.asyncio
async def test_dynamodb_store_returns_typed_not_found_errors() -> None:
    store = DynamoDBJobStore(table_name="jobs", region="us-west-2", client=FakeDynamoDBClient())
    with pytest.raises(JobNotFoundError):
        await store.get("job_0123456789abcdef")
    with pytest.raises(JobNotFoundError):
        await store.save(job())
