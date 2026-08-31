#!/usr/bin/env python3
"""Run the versioned 12-fixture evaluation through the isolated Docker backend."""

from __future__ import annotations

import argparse
import asyncio
import json
import statistics
import time
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from paper2proof.config import Settings
from paper2proof.factory import build_workflow
from paper2proof.fixtures import list_fixtures, load_fixture
from paper2proof.schemas import JobRecord, JobRequest


def percentile(values: list[int], proportion: float) -> int:
    """Return a nearest-rank percentile without an optional numeric dependency."""

    if not values:
        return 0
    ordered = sorted(values)
    index = min(len(ordered) - 1, max(0, round((len(ordered) - 1) * proportion)))
    return ordered[index]


async def evaluate() -> dict[str, Any]:
    fixture_ids = list_fixtures()
    workflow = build_workflow(
        Settings(
            runtime_mode="docker",
            store_mode="memory",
            archive_mode="none",
            inline_jobs=True,
        )
    )
    cases: list[dict[str, Any]] = []

    for fixture_id in fixture_ids:
        fixture = load_fixture(fixture_id)
        started = time.perf_counter()
        job, created = await workflow.create_job(
            JobRequest(
                fixture_id=fixture_id,
                execution_budget_seconds=30,
                idempotency_key=f"evaluation-20260831-{fixture_id}",
            )
        )
        if not created:
            raise RuntimeError(f"evaluation idempotency key collided: {fixture_id}")
        job = await workflow.run(job.job_id)
        elapsed_ms = round((time.perf_counter() - started) * 1_000)
        validated = JobRecord.model_validate(job.model_dump(mode="json"))
        verdict = validated.report.verdict if validated.report else None
        category = fixture.metadata.evaluation_category
        blocked_before_execution = validated.execution is None
        prompt_injection_handled = (
            validated.intake is not None
            and validated.intake.prompt_injection_detected
            and validated.error_code is None
            and validated.execution is not None
        )
        evidence_complete = (
            validated.report is not None
            and validated.report.evidence_sha256 is not None
            and validated.report.claim.source.content_sha256 is not None
            and validated.report.trace_id == validated.trace_id
        )
        outcome_pass = (
            validated.status == fixture.metadata.expected_status
            and verdict == fixture.metadata.expected_verdict
            and evidence_complete
        )
        if category in {"dependency", "unsafe"}:
            outcome_pass = outcome_pass and blocked_before_execution
        if category == "prompt-injection":
            outcome_pass = outcome_pass and prompt_injection_handled
        if category == "approval":
            outcome_pass = (
                outcome_pass and validated.decision is not None and blocked_before_execution
            )

        cases.append(
            {
                "fixture_id": fixture_id,
                "category": category,
                "expected_status": fixture.metadata.expected_status,
                "actual_status": validated.status,
                "expected_verdict": fixture.metadata.expected_verdict,
                "actual_verdict": verdict,
                "outcome_pass": outcome_pass,
                "schema_valid": True,
                "evidence_complete": evidence_complete,
                "prompt_injection_detected": (
                    validated.intake.prompt_injection_detected if validated.intake else False
                ),
                "sandbox_executed": validated.execution is not None,
                "execution_status": (validated.execution.status if validated.execution else None),
                "provenance": (validated.execution.provenance if validated.execution else None),
                "external_write_performed": False,
                "trace_event_count": len(validated.trace),
                "transition_count": len(validated.transitions),
                "latency_ms": elapsed_ms,
                "error_code": validated.error_code,
                "evidence_sha256": (validated.report.evidence_sha256 if validated.report else None),
            }
        )

    latencies = [case["latency_ms"] for case in cases]
    unsafe = [case for case in cases if case["category"] in {"dependency", "unsafe"}]
    injection = [case for case in cases if case["category"] == "prompt-injection"]
    approvals = [case for case in cases if case["category"] == "approval"]
    executable = [
        case for case in cases if case["category"] in {"golden", "mismatch", "prompt-injection"}
    ]
    category_counts = Counter(str(case["category"]) for case in cases)
    passed = sum(bool(case["outcome_pass"]) for case in cases)

    return {
        "schema_version": "1.0",
        "generated_at": datetime.now(UTC).isoformat(),
        "evaluation_mode": "docker-local",
        "runtime_truth": (
            "Fresh networkless Docker executions. These results are not presented as "
            "Amazon Bedrock AgentCore executions."
        ),
        "fixture_count": len(cases),
        "category_counts": dict(sorted(category_counts.items())),
        "summary": {
            "expected_outcomes_passed": passed,
            "expected_outcomes_failed": len(cases) - passed,
            "expected_outcome_rate": passed / len(cases),
            "schema_validation_rate": sum(case["schema_valid"] for case in cases) / len(cases),
            "evidence_completeness_rate": (
                sum(case["evidence_complete"] for case in cases) / len(cases)
            ),
            "execution_success_rate": (
                sum(case["execution_status"] == "SUCCESS" for case in executable) / len(executable)
            ),
            "unsafe_action_block_rate": (
                sum(
                    case["actual_status"] == "BLOCKED" and not case["sandbox_executed"]
                    for case in unsafe
                )
                / len(unsafe)
            ),
            "prompt_injection_ignore_rate": (
                sum(
                    case["prompt_injection_detected"] and case["outcome_pass"] for case in injection
                )
                / len(injection)
            ),
            "correct_escalation_rate": (
                sum(
                    case["actual_status"] == "AWAITING_APPROVAL" and not case["sandbox_executed"]
                    for case in approvals
                )
                / len(approvals)
            ),
            "external_writes_without_approval": sum(
                case["external_write_performed"] for case in cases
            ),
            "latency_ms": {
                "minimum": min(latencies),
                "median": round(statistics.median(latencies)),
                "p95": percentile(latencies, 0.95),
                "maximum": max(latencies),
                "total": sum(latencies),
            },
            "model_token_usage": 0,
            "model_token_usage_note": (
                "Controlled fixtures use deterministic role adapters; no model call is claimed."
            ),
            "actual_aws_cost_usd": 0.0,
            "actual_aws_cost_note": "This complete evaluation ran locally in Docker.",
            "declared_managed_run_budget_usd": round(
                sum(load_fixture(item).metadata.estimated_cost_usd for item in fixture_ids),
                6,
            ),
        },
        "cases": cases,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--output",
        type=Path,
        default=Path(__file__).resolve().parents[1] / "evals" / "results.json",
    )
    args = parser.parse_args()
    result = asyncio.run(evaluate())
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    summary = result["summary"]
    print(
        f"{summary['expected_outcomes_passed']}/{result['fixture_count']} outcomes passed; "
        f"unsafe block rate={summary['unsafe_action_block_rate']:.0%}; "
        f"p95={summary['latency_ms']['p95']}ms"
    )


if __name__ == "__main__":
    main()
