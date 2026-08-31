from __future__ import annotations

import pytest
from paper2proof.fixtures import list_fixtures, load_fixture
from paper2proof.schemas import Verdict
from paper2proof.security import validate_python_code


def test_fixture_catalog_contains_three_demo_stories() -> None:
    assert list_fixtures() == ["ambiguous-spread", "parameter-drift", "reproducible-mean"]


@pytest.mark.parametrize("fixture_id", list_fixtures())
def test_fixture_contracts_and_code_validate(fixture_id: str) -> None:
    fixture = load_fixture(fixture_id)
    assert fixture.claim_extraction.selected_claim.source.license == "MIT"
    assert fixture.plan.network_access is False
    assert fixture.plan.external_writes is False
    validate_python_code(fixture.plan.code)


def test_expected_fixture_outcomes_are_honest() -> None:
    assert load_fixture("reproducible-mean").metadata.expected_verdict == Verdict.PASS
    assert load_fixture("parameter-drift").metadata.expected_verdict == Verdict.MISMATCH
    assert load_fixture("ambiguous-spread").metadata.expected_verdict == Verdict.INCONCLUSIVE


def test_fixture_identifier_cannot_escape_catalog() -> None:
    with pytest.raises(KeyError):
        load_fixture("../secrets")
