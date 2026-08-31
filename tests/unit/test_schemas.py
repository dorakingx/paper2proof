from __future__ import annotations

from itertools import pairwise

import pytest
from paper2proof.schemas import JobRequest, JobStatus, Tolerance, assert_transition
from pydantic import ValidationError


def test_declared_happy_path_transitions_are_valid() -> None:
    path = [
        JobStatus.QUEUED,
        JobStatus.INTAKE,
        JobStatus.CLAIMS_EXTRACTED,
        JobStatus.PLAN_READY,
        JobStatus.EXECUTING,
        JobStatus.VERIFYING,
        JobStatus.COMPLETED,
    ]
    for current, target in pairwise(path):
        assert_transition(current, target)


def test_terminal_state_cannot_transition() -> None:
    with pytest.raises(ValueError, match="invalid job transition"):
        assert_transition(JobStatus.COMPLETED, JobStatus.EXECUTING)


def test_job_request_requires_exactly_one_source() -> None:
    with pytest.raises(ValidationError):
        JobRequest(idempotency_key="abcdefgh")
    with pytest.raises(ValidationError):
        JobRequest(
            fixture_id="x",
            paper_url="https://arxiv.org/abs/1234.5678",
            idempotency_key="abcdefgh",
        )


def test_tolerance_requires_absolute_or_relative_value() -> None:
    with pytest.raises(ValidationError):
        Tolerance()
    assert Tolerance(absolute=0.1).absolute == 0.1
