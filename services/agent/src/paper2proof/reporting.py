"""Human-readable evidence rendering derived from the same JSON contract."""

from __future__ import annotations

from paper2proof.schemas import EvidenceReport


def report_to_markdown(report: EvidenceReport) -> str:
    claim = report.claim
    lines = [
        "# Paper2Proof Evidence Report",
        "",
        f"- Job: `{report.job_id}`",
        f"- Generated: {report.generated_at.isoformat()}",
        f"- Terminal state: **{report.terminal_status}**",
        f"- Verdict: **{report.verdict}**",
        f"- Trace: `{report.trace_id}`",
        f"- Evidence SHA-256: `{report.evidence_sha256 or 'pending'}`",
        "",
        "## Source claim",
        "",
        f"> {claim.statement}",
        "",
        f"Source: [{claim.source.title}]({claim.source.url}) — {claim.source.locator}",
        "",
        f"Reported value: **{claim.reported_value} {claim.unit}**",
        "",
    ]
    if report.plan:
        lines.extend(
            [
                "## Experiment plan",
                "",
                f"- Display command: `{report.plan.command_display}`",
                f"- Timeout: {report.plan.timeout_seconds}s",
                f"- Network access: {report.plan.network_access}",
                f"- External writes: {report.plan.external_writes}",
                f"- Estimated run cost: ${report.plan.estimated_cost_usd:.4f}",
                "",
                "```python",
                report.plan.code.rstrip(),
                "```",
                "",
            ]
        )
    if report.execution:
        execution = report.execution
        lines.extend(
            [
                "## Observed execution",
                "",
                f"- Provenance: **{execution.provenance}**",
                f"- Service: {execution.service}",
                f"- Region: {execution.region or 'local'}",
                f"- Status: {execution.status}",
                f"- Exit code: {execution.exit_code}",
                f"- Duration: {execution.duration_ms} ms",
                f"- Code SHA-256: `{execution.code_sha256}`",
                f"- Observed value: {execution.observed_value}",
                "",
                "```text",
                execution.stdout.rstrip(),
                "```",
                "",
            ]
        )
    if report.comparison:
        comparison = report.comparison
        lines.extend(
            [
                "## Comparison",
                "",
                "| Reported | Observed | Absolute error | Relative error | Within tolerance |",
                "|---:|---:|---:|---:|:---:|",
                f"| {comparison.reported_value} | {comparison.observed_value} | "
                f"{comparison.absolute_error} | {comparison.relative_error} | "
                f"{comparison.within_tolerance} |",
                "",
                comparison.rationale,
                "",
            ]
        )
    lines.extend(["## Limitations", ""])
    lines.extend(f"- {item}" for item in report.limitations)
    if report.next_decision:
        lines.extend(["", "## Next decision", "", report.next_decision])
    lines.extend(
        [
            "",
            "---",
            "",
            "A PASS means the bounded observed value matched this declared claim and tolerance. "
            "It is not a declaration that the paper is scientifically true.",
            "",
        ]
    )
    return "\n".join(lines)
