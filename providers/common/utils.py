"""Shared utility helpers for provider request builders."""

import re
from typing import Any


def max_tokens_limit(error: str, requested: int | None) -> int | None:
    """The output-token limit a provider states when it rejects max_tokens, if any.

    e.g. "`max_tokens` must be less than or equal to `32768`" (Groq),
    "max_tokens is too large: 128000 ... supports at most 32768" (OpenAI-style),
    "the valid range of max_tokens is [1, 8192]" (DeepSeek).
    """
    if not requested or not re.search(r"max_(completion_)?tokens", error):
        return None
    # shortcut: picks the largest number below the request, which can undershoot when a
    # message also quotes input sizes (vLLM context errors); good enough as a safe cap.
    smaller = [int(n) for n in re.findall(r"\d{3,}", error) if int(n) < requested]
    return max(smaller) if smaller else None


def thinking_enabled(request_data: Any) -> bool:
    """Whether the request asks for thinking (no `thinking` field means no thinking)."""
    thinking = getattr(request_data, "thinking", None)
    return bool(thinking and thinking.enabled)


def set_if_not_none(body: dict[str, Any], key: str, value: Any) -> None:
    """Set body[key] = value only when value is not None."""
    if value is not None:
        body[key] = value
