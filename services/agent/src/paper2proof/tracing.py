"""Observable Strands events without exposing private chain-of-thought."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Callable
from typing import Any

from strands.hooks import (
    AfterInvocationEvent,
    AfterToolCallEvent,
    BeforeInvocationEvent,
    BeforeToolCallEvent,
)

from paper2proof.schemas import TraceEvent, TraceEventType


def _stable_summary(value: Any, limit: int = 240) -> str:
    try:
        serialized = json.dumps(value, sort_keys=True, default=str, separators=(",", ":"))
    except (TypeError, ValueError):
        serialized = repr(value)
    if len(serialized) <= limit:
        return serialized
    digest = hashlib.sha256(serialized.encode()).hexdigest()[:12]
    return f"{serialized[:limit]}… [sha256:{digest}]"


class TraceRecorder:
    def __init__(self, trace_id: str) -> None:
        self.trace_id = trace_id
        self.events: list[TraceEvent] = []

    def add(
        self,
        event_type: TraceEventType,
        role: str,
        name: str,
        *,
        input_value: Any | None = None,
        output_value: Any | None = None,
    ) -> TraceEvent:
        event = TraceEvent(
            ordinal=len(self.events) + 1,
            trace_id=self.trace_id,
            event_type=event_type,
            role=role,
            name=name,
            input_summary=_stable_summary(input_value) if input_value is not None else None,
            output_summary=_stable_summary(output_value) if output_value is not None else None,
        )
        self.events.append(event)
        return event

    def strands_hooks(self, role: str) -> list[Callable[..., None]]:
        def before_invocation(event: BeforeInvocationEvent) -> None:
            self.add(
                TraceEventType.AGENT_START,
                role,
                "strands-invocation",
                input_value={"message_count": len(event.messages or [])},
            )

        def after_invocation(event: AfterInvocationEvent) -> None:
            result = event.result
            self.add(
                TraceEventType.AGENT_OUTPUT,
                role,
                "strands-invocation",
                output_value={"completed": result is not None},
            )

        def before_tool(event: BeforeToolCallEvent) -> None:
            tool_use = event.tool_use
            tool_input = tool_use.get("input", {})
            redacted_input = {
                "keys": sorted(tool_input),
                "payload_sha256": hashlib.sha256(
                    json.dumps(tool_input, sort_keys=True, default=str).encode()
                ).hexdigest(),
            }
            self.add(
                TraceEventType.TOOL_START,
                role,
                str(tool_use.get("name", "unknown-tool")),
                input_value=redacted_input,
            )

        def after_tool(event: AfterToolCallEvent) -> None:
            self.add(
                TraceEventType.TOOL_OUTPUT,
                role,
                str(event.tool_use.get("name", "unknown-tool")),
                output_value={
                    "status": event.result.get("status"),
                    "tool_use_id": event.result.get("toolUseId"),
                },
            )

        return [before_invocation, after_invocation, before_tool, after_tool]
