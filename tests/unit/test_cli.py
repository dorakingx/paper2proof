from __future__ import annotations

import sys
from types import SimpleNamespace

import paper2proof.cli as cli
import pytest
from paper2proof.agents import FixtureAgentSuite
from paper2proof.store import InMemoryJobStore
from paper2proof.workflow import Paper2ProofWorkflow

from tests.unit.helpers import StubExecutor


def fixture_workflow() -> Paper2ProofWorkflow:
    return Paper2ProofWorkflow(
        store=InMemoryJobStore(),
        agents=FixtureAgentSuite(),
        executor=StubExecutor(),
        allowed_hosts=frozenset({"github.com"}),
    )


def test_main_lists_controlled_fixtures(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setattr(sys, "argv", ["paper2proof", "list-fixtures"])
    cli.main()

    output = capsys.readouterr().out
    assert "reproducible-mean" in output
    assert "ambiguous-spread" in output


@pytest.mark.asyncio
async def test_run_fixture_writes_json_and_markdown(
    monkeypatch: pytest.MonkeyPatch, tmp_path
) -> None:
    json_path = tmp_path / "evidence.json"
    markdown_path = tmp_path / "evidence.md"
    monkeypatch.setattr(cli, "build_workflow", lambda _settings: fixture_workflow())
    args = SimpleNamespace(
        runtime="fixture",
        fixture_id="reproducible-mean",
        json_out=json_path,
        markdown_out=markdown_path,
    )

    exit_code = await cli._run_fixture(args)

    assert exit_code == 0
    assert '"status": "COMPLETED"' in json_path.read_text()
    assert "Paper2Proof Evidence Report" in markdown_path.read_text()


def test_main_propagates_run_exit_code(monkeypatch: pytest.MonkeyPatch) -> None:
    async def fake_run(_args) -> int:
        return 1

    monkeypatch.setattr(cli, "_run_fixture", fake_run)
    monkeypatch.setattr(
        sys,
        "argv",
        ["paper2proof", "run-fixture", "reproducible-mean", "--runtime", "fixture"],
    )
    with pytest.raises(SystemExit) as exc_info:
        cli.main()
    assert exc_info.value.code == 1
