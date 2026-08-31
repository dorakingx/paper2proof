"""Job persistence interfaces; in-memory store is limited to local development."""

from __future__ import annotations

import asyncio
from copy import deepcopy

from paper2proof.schemas import JobRecord


class JobNotFoundError(KeyError):
    pass


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

    async def list(self) -> list[JobRecord]:
        async with self._lock:
            return [deepcopy(job) for job in self._jobs.values()]
