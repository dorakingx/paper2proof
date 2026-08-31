"""Amazon Bedrock AgentCore Runtime entrypoint for Paper2Proof."""

from __future__ import annotations

from typing import Any

from bedrock_agentcore.runtime import BedrockAgentCoreApp

app = BedrockAgentCoreApp(debug=False)
_service: Any | None = None


@app.entrypoint
async def invoke(payload: dict[str, Any]) -> dict[str, Any]:
    """Validate and execute one typed Paper2Proof command."""

    global _service
    if _service is None:
        # Keep the managed server responsive within AgentCore's 30-second
        # initialization window; the Strands/tool graph is loaded on demand.
        from paper2proof.runtime import build_runtime_service

        _service = build_runtime_service()
    return await _service.invoke(payload)


if __name__ == "__main__":
    app.run()
