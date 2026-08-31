from __future__ import annotations

import pytest
from paper2proof.agents import StrandsAgentSuite
from paper2proof.fixtures import list_fixtures, load_fixture
from paper2proof.schemas import JobStatus, Verdict
from paper2proof.security import SecurityViolation, validate_python_code
from paper2proof.tracing import TraceRecorder


def test_fixture_catalog_contains_twelve_evaluation_stories_and_three_public_demos() -> None:
    assert len(list_fixtures()) == 12
    assert list_fixtures(public_only=True) == [
        "ambiguous-spread",
        "parameter-drift",
        "reproducible-mean",
    ]


@pytest.mark.parametrize("fixture_id", list_fixtures())
def test_fixture_contracts_and_code_validate(fixture_id: str) -> None:
    fixture = load_fixture(fixture_id)
    assert fixture.claim_extraction.selected_claim.source.license == "MIT"
    if fixture.metadata.expected_status == JobStatus.BLOCKED:
        assert fixture.plan.dependencies or fixture.metadata.risk_level == "PROHIBITED"
        with pytest.raises(SecurityViolation):
            validate_python_code(fixture.plan.code)
    else:
        assert fixture.plan.network_access is False
        assert fixture.plan.external_writes is False
        validate_python_code(fixture.plan.code)


def test_expected_fixture_outcomes_are_honest() -> None:
    assert load_fixture("reproducible-mean").metadata.expected_verdict == Verdict.PASS
    assert load_fixture("parameter-drift").metadata.expected_verdict == Verdict.MISMATCH
    assert load_fixture("ambiguous-spread").metadata.expected_verdict == Verdict.INCONCLUSIVE
    assert load_fixture("dangerous-host-access").metadata.expected_verdict == Verdict.BLOCKED


def test_fixture_identifier_cannot_escape_catalog() -> None:
    with pytest.raises(KeyError):
        load_fixture("../secrets")


@pytest.mark.asyncio
async def test_production_suite_preserves_controlled_fixture_claim_and_plan() -> None:
    suite = object.__new__(StrandsAgentSuite)
    fixture = load_fixture("dangerous-host-access")
    trace = TraceRecorder("trace_0123456789abcdef")

    extraction = await suite.extract_claims(fixture, trace)
    plan = await suite.plan(fixture, extraction.selected_claim, trace)

    assert extraction == fixture.claim_extraction
    assert plan == fixture.plan
    assert "import os" in plan.code
    assert [event.name for event in trace.events] == [
        "controlled-fixture-claim-contract",
        "controlled-fixture-claim-contract",
        "controlled-fixture-plan-contract",
        "controlled-fixture-plan-contract",
    ]
