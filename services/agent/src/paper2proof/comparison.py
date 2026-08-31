"""Deterministic numerical comparison; the model cannot change the verdict math."""

from __future__ import annotations

from paper2proof.schemas import Claim, Comparison, ExecutionRecord, ExecutionStatus, Verdict


def compare_claim(claim: Claim, execution: ExecutionRecord) -> tuple[Comparison, Verdict]:
    if execution.status != ExecutionStatus.SUCCESS or execution.observed_value is None:
        return (
            Comparison(
                reported_value=claim.reported_value,
                tolerance=claim.tolerance,
                rationale=(
                    "The sandbox did not return a finite observed value, so no numerical claim "
                    "was decided."
                ),
            ),
            Verdict.INCONCLUSIVE,
        )

    observed = execution.observed_value
    absolute_error = abs(observed - claim.reported_value)
    denominator = abs(claim.reported_value)
    relative_error = (
        absolute_error / denominator if denominator else (0.0 if absolute_error == 0 else None)
    )

    absolute_pass = (
        claim.tolerance.absolute is not None and absolute_error <= claim.tolerance.absolute
    )
    relative_pass = (
        claim.tolerance.relative is not None
        and relative_error is not None
        and relative_error <= claim.tolerance.relative
    )
    within_tolerance = absolute_pass or relative_pass
    comparison = Comparison(
        reported_value=claim.reported_value,
        observed_value=observed,
        absolute_error=absolute_error,
        relative_error=relative_error,
        tolerance=claim.tolerance,
        within_tolerance=within_tolerance,
        rationale=(
            "Observed and reported values agree under the declared tolerance."
            if within_tolerance
            else "Observed and reported values differ beyond the declared tolerance."
        ),
    )
    return comparison, Verdict.PASS if within_tolerance else Verdict.MISMATCH
