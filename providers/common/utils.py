"""Shared utility helpers for provider request builders."""

from typing import Any


def thinking_enabled(request_data: Any) -> bool:
    """Whether the request asks for thinking (no `thinking` field means no thinking)."""
    thinking = getattr(request_data, "thinking", None)
    return bool(thinking and thinking.enabled)


def set_if_not_none(body: dict[str, Any], key: str, value: Any) -> None:
    """Set body[key] = value only when value is not None."""
    if value is not None:
        body[key] = value
