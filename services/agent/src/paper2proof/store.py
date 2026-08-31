"""Job persistence interfaces; in-memory store is limited to local development."""

from __future__ import annotations

import asyncio
import builtins
from copy import deepcopy
from typing import Any, Protocol, cast

import boto3  # type: ignore[import-untyped]
from botocore.exceptions import ClientError  # type: ignore[import-untyped]

from paper2proof.schemas import JobRecord


class JobNotFoundError(KeyError):
    pass


class JobStore(Protocol):
    async def create(self, job: JobRecord) -> tuple[JobRecord, bool]: ...

    async def save(self, job: JobRecord) -> None: ...

    async def get(self, job_id: str) -> JobRecord: ...

    async def list(self) -> builtins.list[JobRecord]: ...


class InMemoryJobStore:
    def __init__(self) -> None:
        self._jobs: dict[str, JobRecord] = {}
        self._idempotency: dict[str, str] = {}
        self._lock = asyncio.Lock()

    async def create(self, job: JobRecord) -> tuple[JobRecord, bool]:
        async with self._lock:
            key = job.request.idempotency_key
            if existing_id := self._idempotency.get(key):
                return deepcopy(self._jobs[existing_id]), False
            self._jobs[job.job_id] = deepcopy(job)
            self._idempotency[key] = job.job_id
            return deepcopy(job), True

    async def save(self, job: JobRecord) -> None:
        async with self._lock:
            if job.job_id not in self._jobs:
                raise JobNotFoundError(job.job_id)
            self._jobs[job.job_id] = deepcopy(job)

    async def get(self, job_id: str) -> JobRecord:
        async with self._lock:
            if job_id not in self._jobs:
                raise JobNotFoundError(job_id)
            return deepcopy(self._jobs[job_id])

    async def list(self) -> builtins.list[JobRecord]:
        async with self._lock:
            return [deepcopy(job) for job in self._jobs.values()]


class DynamoDBJobStore:
    """DynamoDB-backed store with atomic idempotency reservation."""

    def __init__(
        self,
        *,
        table_name: str,
        region: str,
        client: Any | None = None,
    ) -> None:
        self.table_name = table_name
        self.client = client or boto3.client("dynamodb", region_name=region)

    @staticmethod
    def _job_key(job_id: str) -> str:
        return f"JOB#{job_id}"

    @staticmethod
    def _idempotency_key(key: str) -> str:
        return f"IDEMPOTENCY#{key}"

    @staticmethod
    def _job_item(job: JobRecord) -> dict[str, dict[str, str]]:
        return {
            "pk": {"S": DynamoDBJobStore._job_key(job.job_id)},
            "entity": {"S": "job"},
            "job_id": {"S": job.job_id},
            "updated_at": {"S": job.updated_at.isoformat()},
            "payload": {"S": job.model_dump_json()},
        }

    async def create(self, job: JobRecord) -> tuple[JobRecord, bool]:
        return await asyncio.to_thread(self._create_sync, job)

    def _create_sync(self, job: JobRecord) -> tuple[JobRecord, bool]:
        key = job.request.idempotency_key
        try:
            self.client.transact_write_items(
                TransactItems=[
                    {
                        "Put": {
                            "TableName": self.table_name,
                            "Item": self._job_item(job),
                            "ConditionExpression": "attribute_not_exists(pk)",
                        }
                    },
                    {
                        "Put": {
                            "TableName": self.table_name,
                            "Item": {
                                "pk": {"S": self._idempotency_key(key)},
                                "entity": {"S": "idempotency"},
                                "job_id": {"S": job.job_id},
                            },
                            "ConditionExpression": "attribute_not_exists(pk)",
                        }
                    },
                ]
            )
        except ClientError as exc:
            code = cast(str, exc.response.get("Error", {}).get("Code", ""))
            if code not in {"TransactionCanceledException", "ConditionalCheckFailedException"}:
                raise
            mapping = self.client.get_item(
                TableName=self.table_name,
                Key={"pk": {"S": self._idempotency_key(key)}},
                ConsistentRead=True,
            ).get("Item")
            if not mapping or "job_id" not in mapping:
                raise RuntimeError("idempotency reservation conflicted without a mapping") from exc
            return self._get_sync(mapping["job_id"]["S"]), False
        return job.model_copy(deep=True), True

    async def save(self, job: JobRecord) -> None:
        await asyncio.to_thread(self._save_sync, job)

    def _save_sync(self, job: JobRecord) -> None:
        try:
            self.client.put_item(
                TableName=self.table_name,
                Item=self._job_item(job),
                ConditionExpression="attribute_exists(pk)",
            )
        except ClientError as exc:
            code = exc.response.get("Error", {}).get("Code")
            if code == "ConditionalCheckFailedException":
                raise JobNotFoundError(job.job_id) from exc
            raise

    async def get(self, job_id: str) -> JobRecord:
        return await asyncio.to_thread(self._get_sync, job_id)

    def _get_sync(self, job_id: str) -> JobRecord:
        item = self.client.get_item(
            TableName=self.table_name,
            Key={"pk": {"S": self._job_key(job_id)}},
            ConsistentRead=True,
        ).get("Item")
        if not item or "payload" not in item:
            raise JobNotFoundError(job_id)
        return JobRecord.model_validate_json(item["payload"]["S"])

    async def list(self) -> builtins.list[JobRecord]:
        return await asyncio.to_thread(self._list_sync)

    def _list_sync(self) -> builtins.list[JobRecord]:
        jobs: builtins.list[JobRecord] = []
        start_key: dict[str, dict[str, str]] | None = None
        while True:
            arguments: dict[str, Any] = {
                "TableName": self.table_name,
                "FilterExpression": "entity = :job",
                "ExpressionAttributeValues": {":job": {"S": "job"}},
                "ProjectionExpression": "payload",
            }
            if start_key:
                arguments["ExclusiveStartKey"] = start_key
            response = self.client.scan(**arguments)
            for item in response.get("Items", []):
                if "payload" in item:
                    jobs.append(JobRecord.model_validate_json(item["payload"]["S"]))
            start_key = response.get("LastEvaluatedKey")
            if not start_key:
                break
        return sorted(jobs, key=lambda item: item.created_at, reverse=True)
