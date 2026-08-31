"""Immutable evidence archive interfaces and S3 implementation."""

from __future__ import annotations

import asyncio
import base64
import hashlib
from typing import Any, Protocol, cast

import boto3  # type: ignore[import-untyped]

from paper2proof.reporting import report_to_markdown
from paper2proof.schemas import EvidenceArchiveRecord, EvidenceReport


class EvidenceArchive(Protocol):
    async def archive(self, report: EvidenceReport) -> EvidenceArchiveRecord: ...


class S3EvidenceArchive:
    def __init__(
        self,
        *,
        bucket: str,
        region: str,
        client: Any | None = None,
    ) -> None:
        self.bucket = bucket
        self.client = client or boto3.client("s3", region_name=region)

    async def archive(self, report: EvidenceReport) -> EvidenceArchiveRecord:
        return await asyncio.to_thread(self._archive_sync, report)

    def _archive_sync(self, report: EvidenceReport) -> EvidenceArchiveRecord:
        if report.evidence_sha256 is None:
            raise ValueError("evidence must be sealed before archival")
        prefix = f"evidence/{report.job_id}/{report.evidence_sha256}"
        json_key = f"{prefix}.json"
        markdown_key = f"{prefix}.md"
        json_body = (report.model_dump_json(indent=2) + "\n").encode()
        markdown_body = report_to_markdown(report).encode()
        json_result = self._put(json_key, json_body, "application/json")
        markdown_result = self._put(markdown_key, markdown_body, "text/markdown; charset=utf-8")
        return EvidenceArchiveRecord(
            bucket=self.bucket,
            json_key=json_key,
            markdown_key=markdown_key,
            json_etag=str(json_result.get("ETag", "")).strip('"') or None,
            markdown_etag=str(markdown_result.get("ETag", "")).strip('"') or None,
            evidence_sha256=report.evidence_sha256,
        )

    def _put(self, key: str, body: bytes, content_type: str) -> dict[str, Any]:
        checksum = base64.b64encode(hashlib.sha256(body).digest()).decode()
        result = self.client.put_object(
            Bucket=self.bucket,
            Key=key,
            Body=body,
            ContentType=content_type,
            ServerSideEncryption="AES256",
            ChecksumSHA256=checksum,
            IfNoneMatch="*",
            Metadata={"paper2proof-evidence-sha256": key.rsplit("/", 1)[-1].split(".", 1)[0]},
        )
        return cast(dict[str, Any], result)
