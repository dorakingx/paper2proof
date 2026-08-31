from __future__ import annotations

import hashlib
from datetime import UTC, datetime

import pytest
from paper2proof.comparison import compare_claim
from paper2proof.fixtures import load_fixture
from paper2proof.schemas import (
    ExecutionRecord,
    ExecutionStatus,
    RuntimeProvenance,
    Verdict,
)


def execution(
    observed: float | None, status: ExecutionStatus = ExecutionStatus.SUCCESS
) -> ExecutionRecord:
    now = datetime.now(UTC)
    raw = f"observed={observed}"
    return ExecutionRecord(
        execution_id="exec_12345678",
        status=status,
        provenance=RuntimeProvenance.DOCKER_LOCAL,
        service="test sandbox",
        started_at=now,
        completed_at=now,
        duration_ms=0,
        command_display="python -I -",
        code_sha256="0" * 64,
        exit_code=0 if status == ExecutionStatus.SUCCESS else 1,
        observed_value=observed,
        raw_response_sha256=hashlib.sha256(raw.encode()).hexdigest(),
        failure_reason=None if status == ExecutionStatus.SUCCESS else "test failure",
    )


def test_exact_observation_passes() -> None:
    claim = load_fixture("reproducible-mean").claim_extraction.selected_claim
    comparison, verdict = compare_claim(claim, execution(5.0))
    assert comparison.within_tolerance is True
    assert verdict == Verdict.PASS


def test_stale_reported_value_mismatches() -> None:
    claim = load_fixture("parameter-drift").claim_extraction.selected_claim
    comparison, verdict = compare_claim(claim, execution(5.0))
    assert comparison.absolute_error == pytest.approx(0.2)
    assert comparison.within_tolerance is False
    assert verdict == Verdict.MISMATCH


def test_execution_error_is_inconclusive() -> None:
    claim = load_fixture("reproducible-mean").claim_extraction.selected_claim
    comparison, verdict = compare_claim(claim, execution(None, status=ExecutionStatus.ERROR))
    assert comparison.within_tolerance is None
    assert verdict == Verdict.INCONCLUSIVE
