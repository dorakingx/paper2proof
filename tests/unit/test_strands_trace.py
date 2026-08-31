from __future__ import annotations

from typing import Any, cast

from paper2proof.null_model import DirectToolOnlyModel
from paper2proof.schemas import TraceEventType
from paper2proof.tracing import TraceRecorder
from strands import Agent, tool


@tool
def bounded_echo(value: str) -> str:
    """Return a controlled value for direct-tool trace verification."""
    return f"observed:{value}"


def test_direct_strands_tool_call_is_observable_without_model_inference() -> None:
    recorder = TraceRecorder("trace_0123456789abcdef")
    agent = Agent(
        model=DirectToolOnlyModel(),
        tools=[bounded_echo],
        callback_handler=None,
        hooks=cast(Any, recorder.strands_hooks("Execution Agent")),
    )
    result = agent.tool.bounded_echo(value="5.0")
    assert result["status"] == "success"
    assert [event.event_type for event in recorder.events] == [
        TraceEventType.TOOL_START,
        TraceEventType.TOOL_OUTPUT,
    ]
    assert recorder.events[0].name == "bounded_echo"
    assert "5.0" not in (recorder.events[0].input_summary or "")
