from __future__ import annotations

import hashlib
import json
import uuid
from datetime import UTC, datetime

from paper2proof.schemas import (
    ExecutionRecord,
    ExecutionStatus,
    ExperimentPlan,
    RuntimeProvenance,
    TraceEventType,
)
from paper2proof.tracing import TraceRecorder


class StubExecutor:
    def __init__(self, observed: float = 5.0, *, fail: bool = False) -> None:
        self.observed = observed
        self.fail = fail
        self.calls = 0

    async def execute(self, plan: ExperimentPlan, trace: TraceRecorder) -> ExecutionRecord:
        self.calls += 1
        now = datetime.now(UTC)
        raw = json.dumps({"observed": self.observed, "fail": self.fail})
        trace.add(
            TraceEventType.TOOL_START,
            "Execution Agent",
            "stub-sandbox",
            input_value={"code_sha256": hashlib.sha256(plan.code.encode()).hexdigest()},
        )
        trace.add(
            TraceEventType.TOOL_OUTPUT,
            "Execution Agent",
            "stub-sandbox",
            output_value={"status": "error" if self.fail else "success"},
        )
        return ExecutionRecord(
            execution_id=f"exec_{uuid.uuid4().hex}",
            status=ExecutionStatus.ERROR if self.fail else ExecutionStatus.SUCCESS,
            provenance=RuntimeProvenance.RECORDED,
            service="unit-test stub (never presented as live)",
            started_at=now,
            completed_at=now,
            duration_ms=0,
            command_display=plan.command_display,
            code_sha256=hashlib.sha256(plan.code.encode()).hexdigest(),
            exit_code=1 if self.fail else 0,
            stdout=("" if self.fail else f'PAPER2PROOF_RESULT={{"observed":{self.observed}}}'),
            stderr="stub failed" if self.fail else "",
            observed_value=None if self.fail else self.observed,
            raw_response_sha256=hashlib.sha256(raw.encode()).hexdigest(),
            failure_reason="stub failed" if self.fail else None,
        )
