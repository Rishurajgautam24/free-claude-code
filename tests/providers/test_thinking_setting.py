"""The request's `thinking` setting (as Claude Code sends it) decides reasoning."""

import pytest

from api.models.anthropic import MessagesRequest
from config.nim import NimSettings
from providers.nvidia_nim.request import build_request_body as nim_body
from providers.open_router.request import build_request_body as openrouter_body


def _request(thinking):
    payload = {
        "model": "claude-opus-5-5",
        "max_tokens": 100,
        "messages": [{"role": "user", "content": "hi"}],
    }
    if thinking is not None:
        payload["thinking"] = thinking
    return MessagesRequest.model_validate(payload)


CASES = [
    ({"type": "adaptive", "display": "omitted"}, True),  # Claude Code main turns
    ({"type": "enabled", "budget_tokens": 1024}, True),
    ({"type": "disabled"}, False),
    (None, False),  # side requests usually omit it
]


@pytest.mark.parametrize(("thinking", "on"), CASES)
def test_nim_follows_thinking_setting(thinking, on):
    extra = nim_body(_request(thinking), NimSettings())["extra_body"]
    assert extra["thinking"] == {"type": "enabled" if on else "disabled"}
    assert extra["chat_template_kwargs"]["enable_thinking"] is on
    assert extra["chat_template_kwargs"]["thinking"] is on


@pytest.mark.parametrize(("thinking", "on"), CASES)
def test_openrouter_follows_thinking_setting(thinking, on):
    body = openrouter_body(_request(thinking))
    assert ("reasoning" in body.get("extra_body", {})) is on
