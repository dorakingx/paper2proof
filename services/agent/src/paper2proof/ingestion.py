"""Bounded public-paper ingestion with redirect and SSRF validation."""

from __future__ import annotations

import hashlib
import re
from io import BytesIO
from typing import Annotated

import httpx
from pydantic import AnyHttpUrl, Field, StringConstraints, TypeAdapter
from pypdf import PdfReader

from paper2proof.schemas import JobRequest, SourceReference, StrictModel
from paper2proof.security import SecurityViolation, normalize_public_url

ARXIV_ID = re.compile(
    r"^(?:[0-9]{4}\.[0-9]{4,5}|[a-z-]+(?:\.[A-Z]{2})?/\d{7})(?:v\d+)?$",
    re.IGNORECASE,
)


class SourceDocument(StrictModel):
    """Normalized, bounded text and provenance supplied to the agent roles."""

    source: SourceReference
    document_text: Annotated[str, StringConstraints(min_length=100, max_length=60_000)]
    repo_url: AnyHttpUrl | None = None
    claim_hint: str | None = None
    license_verified: bool = False
    timeout_seconds: int = Field(ge=1, le=300)


def _arxiv_pdf_url(normalized_url: str) -> str:
    parsed = httpx.URL(normalized_url)
    path = parsed.path
    if path.startswith("/abs/"):
        identifier = path.removeprefix("/abs/")
    elif path.startswith("/pdf/"):
        identifier = path.removeprefix("/pdf/").removesuffix(".pdf")
    else:
        raise SecurityViolation("only arXiv abstract or PDF URLs are supported in this build")
    if not ARXIV_ID.fullmatch(identifier):
        raise SecurityViolation("invalid arXiv identifier")
    return f"https://arxiv.org/pdf/{identifier}.pdf"


def _extract_pdf_text(content: bytes, *, max_pages: int = 24) -> tuple[str, str, int]:
    try:
        reader = PdfReader(BytesIO(content), strict=False)
    except Exception as exc:
        raise ValueError("source is not a readable PDF") from exc
    if reader.is_encrypted and reader.decrypt("") == 0:
        raise ValueError("encrypted PDFs are not supported")
    selected_pages = list(reader.pages[:max_pages])
    chunks = [(page.extract_text() or "").replace("\x00", " ") for page in selected_pages]
    text = "\n\n".join(chunk.strip() for chunk in chunks if chunk.strip())[:60_000]
    if len(text) < 100:
        raise ValueError("PDF contains too little extractable text")
    metadata_title = str(reader.metadata.title or "").strip() if reader.metadata else ""
    return text, metadata_title, len(selected_pages)


class PublicPaperIngestor:
    """Fetch one allowlisted public arXiv PDF without trusting redirects."""

    def __init__(
        self,
        *,
        allowed_hosts: frozenset[str],
        max_source_bytes: int,
        resolve_dns: bool = True,
        client: httpx.AsyncClient | None = None,
    ) -> None:
        self.allowed_hosts = allowed_hosts
        self.max_source_bytes = max_source_bytes
        self.resolve_dns = resolve_dns
        self.client = client

    async def ingest(self, request: JobRequest) -> SourceDocument:
        if request.paper_url is None:
            raise ValueError("paper_url is required for public-paper ingestion")
        normalized = normalize_public_url(
            str(request.paper_url),
            allowed_hosts=self.allowed_hosts,
            resolve_dns=self.resolve_dns,
        )
        host = httpx.URL(normalized).host
        if host not in {"arxiv.org", "export.arxiv.org"}:
            raise SecurityViolation("only public arXiv papers are supported in this build")
        pdf_url = _arxiv_pdf_url(normalized)
        content = await self._fetch_pdf(pdf_url)
        document_text, metadata_title, page_count = _extract_pdf_text(content)

        normalized_repo: str | None = None
        if request.repo_url is not None:
            normalized_repo = normalize_public_url(
                str(request.repo_url),
                allowed_hosts=frozenset({"github.com"}),
                resolve_dns=self.resolve_dns,
            )

        identifier = httpx.URL(pdf_url).path.removeprefix("/pdf/").removesuffix(".pdf")
        title = metadata_title or f"arXiv {identifier}"
        source = SourceReference(
            url=TypeAdapter(AnyHttpUrl).validate_python(normalized),
            title=title[:500],
            license="Publicly accessible; article license not verified",
            locator=f"PDF pages 1-{page_count}",
            excerpt=document_text[:1_000],
            content_sha256=hashlib.sha256(content).hexdigest(),
        )
        return SourceDocument(
            source=source,
            document_text=document_text,
            repo_url=(
                TypeAdapter(AnyHttpUrl).validate_python(normalized_repo)
                if normalized_repo
                else None
            ),
            claim_hint=request.claim_hint,
            license_verified=False,
            timeout_seconds=request.execution_budget_seconds,
        )

    async def _fetch_pdf(self, url: str) -> bytes:
        if self.client is not None:
            return await self._fetch_with_client(self.client, url)
        timeout = httpx.Timeout(20.0, connect=5.0)
        async with httpx.AsyncClient(timeout=timeout) as client:
            return await self._fetch_with_client(client, url)

    async def _fetch_with_client(self, client: httpx.AsyncClient, url: str) -> bytes:
        current = url
        for _redirect in range(4):
            normalized = normalize_public_url(
                current,
                allowed_hosts=self.allowed_hosts,
                resolve_dns=self.resolve_dns,
            )
            async with client.stream(
                "GET",
                normalized,
                follow_redirects=False,
                headers={
                    "User-Agent": "Paper2Proof/0.1 (+https://github.com/dorakingx/paper2proof)"
                },
            ) as response:
                if response.is_redirect:
                    location = response.headers.get("location")
                    if not location:
                        raise ValueError("paper redirect omitted a location")
                    current = str(response.url.join(location))
                    continue
                response.raise_for_status()
                declared_size = int(response.headers.get("content-length", "0") or "0")
                if declared_size > self.max_source_bytes:
                    raise ValueError("paper exceeds the configured source-size limit")
                chunks: list[bytes] = []
                received = 0
                async for chunk in response.aiter_bytes():
                    received += len(chunk)
                    if received > self.max_source_bytes:
                        raise ValueError("paper exceeds the configured source-size limit")
                    chunks.append(chunk)
                content = b"".join(chunks)
                content_type = response.headers.get("content-type", "").casefold()
                if "application/pdf" not in content_type and not content.startswith(b"%PDF"):
                    raise ValueError("paper endpoint did not return a PDF")
                return content
        raise ValueError("paper exceeded the redirect limit")
