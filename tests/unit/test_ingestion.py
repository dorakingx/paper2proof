from __future__ import annotations

import hashlib

import httpx
import paper2proof.ingestion as ingestion_module
import pytest
from paper2proof.ingestion import PublicPaperIngestor, _extract_pdf_text
from paper2proof.schemas import JobRequest
from paper2proof.security import SecurityViolation


@pytest.mark.asyncio
async def test_arxiv_pdf_ingestion_records_bounded_provenance(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    pdf = b"%PDF controlled test bytes"

    async def handler(request: httpx.Request) -> httpx.Response:
        assert str(request.url) == "https://arxiv.org/pdf/2401.12345.pdf"
        return httpx.Response(200, headers={"content-type": "application/pdf"}, content=pdf)

    monkeypatch.setattr(
        ingestion_module,
        "_extract_pdf_text",
        lambda _content: ("A bounded numerical result of 5.0. " * 10, "Test Paper", 3),
    )
    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        ingestor = PublicPaperIngestor(
            allowed_hosts=frozenset({"arxiv.org", "github.com"}),
            max_source_bytes=1_000,
            resolve_dns=False,
            client=client,
        )
        source = await ingestor.ingest(
            JobRequest(
                paper_url="https://arxiv.org/abs/2401.12345#page=2",
                repo_url="https://github.com/example/research",
                claim_hint="Check the reported 5.0 result.",
                idempotency_key="public-ingest-test",
            )
        )

    assert source.source.title == "Test Paper"
    assert source.source.content_sha256 == hashlib.sha256(pdf).hexdigest()
    assert str(source.repo_url) == "https://github.com/example/research"
    assert source.license_verified is False
    assert len(source.document_text) > 100


@pytest.mark.asyncio
async def test_redirect_target_is_revalidated_against_ssrf_policy() -> None:
    async def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(302, headers={"location": "https://127.0.0.1/private.pdf"})

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        ingestor = PublicPaperIngestor(
            allowed_hosts=frozenset({"arxiv.org", "127.0.0.1"}),
            max_source_bytes=1_000,
            resolve_dns=False,
            client=client,
        )
        with pytest.raises(SecurityViolation, match="non-public"):
            await ingestor.ingest(
                JobRequest(
                    paper_url="https://arxiv.org/abs/2401.12345",
                    idempotency_key="redirect-ssrf-test",
                )
            )


@pytest.mark.asyncio
async def test_declared_oversized_pdf_is_rejected() -> None:
    async def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            headers={"content-type": "application/pdf", "content-length": "2001"},
            content=b"%PDF",
        )

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        ingestor = PublicPaperIngestor(
            allowed_hosts=frozenset({"arxiv.org"}),
            max_source_bytes=1_000,
            resolve_dns=False,
            client=client,
        )
        with pytest.raises(ValueError, match="source-size"):
            await ingestor.ingest(
                JobRequest(
                    paper_url="https://arxiv.org/pdf/2401.12345.pdf",
                    idempotency_key="oversized-pdf-test",
                )
            )


@pytest.mark.asyncio
async def test_non_arxiv_source_is_rejected_before_fetch() -> None:
    ingestor = PublicPaperIngestor(
        allowed_hosts=frozenset({"github.com"}),
        max_source_bytes=1_000,
        resolve_dns=False,
    )
    with pytest.raises(SecurityViolation, match="only public arXiv"):
        await ingestor.ingest(
            JobRequest(
                paper_url="https://github.com/example/paper.pdf",
                idempotency_key="non-arxiv-test",
            )
        )


def test_invalid_pdf_has_structured_error() -> None:
    with pytest.raises(ValueError, match="readable PDF"):
        _extract_pdf_text(b"not a PDF")
