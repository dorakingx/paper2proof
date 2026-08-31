from __future__ import annotations

import pytest
from paper2proof.executors.agentcore import AgentCoreExecutor
from paper2proof.executors.base import parse_observed_value
from paper2proof.executors.docker import DockerSandboxExecutor
from paper2proof.fixtures import load_fixture
from paper2proof.schemas import ExecutionStatus
from paper2proof.tracing import TraceRecorder


def test_result_parser_accepts_one_finite_observation() -> None:
    assert parse_observed_value('x\nPAPER2PROOF_RESULT={"observed": 5.0}\n') == 5.0


@pytest.mark.parametrize(
    "output",
    [
        "nothing",
        'PAPER2PROOF_RESULT={"observed": 1}\nPAPER2PROOF_RESULT={"observed": 2}',
        'PAPER2PROOF_RESULT={"observed": "nan"}',
        'PAPER2PROOF_RESULT={"observed": 1, "secret": 2}',
    ],
)
def test_result_parser_rejects_ambiguous_or_non_finite_output(output: str) -> None:
    with pytest.raises(ValueError):
        parse_observed_value(output)


@pytest.mark.asyncio
@pytest.mark.parametrize("backend", [DockerSandboxExecutor(), AgentCoreExecutor()])
async def test_both_execution_backends_block_forbidden_code_before_runtime(backend) -> None:
    plan = load_fixture("reproducible-mean").plan.model_copy(
        update={"code": "import os\nprint(os.environ)"}
    )
    result = await backend.execute(plan, TraceRecorder("trace_0123456789abcdef"))
    assert result.status == ExecutionStatus.BLOCKED
    assert result.failure_reason is not None and "forbidden imports" in result.failure_reason
