"""A non-inference model used only for deterministic direct Strands tool calls."""

from __future__ import annotations

from typing import Any

from strands.models import Model


class DirectToolOnlyModel(Model):
    """Prevents accidental model inference in the bounded execution agent."""

    def __init__(self) -> None:
        self._config: dict[str, Any] = {
            "model_id": "paper2proof-direct-tool-only",
            "context_window_limit": 1,
        }

    def update_config(self, **model_config: Any) -> None:
        self._config.update(model_config)

    def get_config(self) -> dict[str, Any]:
        return dict(self._config)

    async def stream(self, *_args: Any, **_kwargs: Any):  # type: ignore[no-untyped-def]
        raise RuntimeError("DirectToolOnlyModel cannot perform inference")
        yield  # pragma: no cover

    async def structured_output(self, *_args: Any, **_kwargs: Any):  # type: ignore[no-untyped-def]
        raise RuntimeError("DirectToolOnlyModel cannot perform inference")
        yield  # pragma: no cover
