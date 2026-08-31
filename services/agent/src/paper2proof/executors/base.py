"""Execution backend protocol and response parsing."""

from __future__ import annotations

import json
import math
import re
from typing import Protocol

from paper2proof.schemas import ExecutionRecord, ExperimentPlan
from paper2proof.tracing import TraceRecorder

RESULT_PATTERN = re.compile(r"PAPER2PROOF_RESULT=(\{[^\r\n]*?\})")


class ExecutionBackend(Protocol):
    async def execute(self, plan: ExperimentPlan, trace: TraceRecorder) -> ExecutionRecord: ...


def parse_observed_value(output: str) -> float:
    matches = RESULT_PATTERN.findall(output)
    if len(matches) != 1:
        raise ValueError("sandbox output must contain exactly one PAPER2PROOF_RESULT object")
    payload = json.loads(matches[0])
    if set(payload) != {"observed"}:
        raise ValueError("result object must contain only the observed key")
    observed = float(payload["observed"])
    if not math.isfinite(observed):
        raise ValueError("observed result must be finite")
    return observed
