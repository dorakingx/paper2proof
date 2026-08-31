"""Paper2Proof command-line interface for reproducible fixture evidence."""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
import uuid
from pathlib import Path

from paper2proof.config import Settings
from paper2proof.factory import build_workflow
from paper2proof.fixtures import list_fixtures
from paper2proof.reporting import report_to_markdown
from paper2proof.schemas import JobRequest, JobStatus


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="paper2proof")
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("list-fixtures", help="List controlled demo fixtures")
    run = subparsers.add_parser("run-fixture", help="Run one controlled claim-to-evidence job")
    run.add_argument("fixture_id", choices=list_fixtures())
    run.add_argument(
        "--runtime", choices=["fixture", "docker", "bedrock", "agentcore"], default="docker"
    )
    run.add_argument("--json-out", type=Path)
    run.add_argument("--markdown-out", type=Path)
    return parser


async def _run_fixture(args: argparse.Namespace) -> int:
    settings = Settings(runtime_mode=args.runtime)
    workflow = build_workflow(settings)
    request = JobRequest(
        fixture_id=args.fixture_id,
        execution_budget_seconds=settings.execution_timeout_seconds,
        idempotency_key=f"cli-{uuid.uuid4().hex}",
    )
    job, _created = await workflow.create_job(request)
    job = await workflow.run(job.job_id)
    payload = job.model_dump(mode="json")
    print(json.dumps(payload, indent=2, sort_keys=True))
    if args.json_out:
        args.json_out.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    if args.markdown_out and job.report:
        args.markdown_out.write_text(report_to_markdown(job.report))
    return 0 if job.status in {JobStatus.COMPLETED, JobStatus.AWAITING_APPROVAL} else 1


def main() -> None:
    args = _parser().parse_args()
    if args.command == "list-fixtures":
        print("\n".join(list_fixtures()))
        return
    sys.exit(asyncio.run(_run_fixture(args)))


if __name__ == "__main__":
    main()
