from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from api.app import app
from api.routes import collect_message
from providers.common import SSEBuilder
from providers.exceptions import APIError, RateLimitError
from providers.nvidia_nim import NvidiaNimProvider

PAYLOAD = {
    "model": "claude-3-sonnet",
    "max_tokens": 100,
    "stream": False,
    "messages": [{"role": "user", "content": "hi"}],
}


async def _events(*events):
    for e in events:
        yield e


def _turn_events():
    sse = SSEBuilder("msg_1", "m", input_tokens=5)
    out = [sse.message_start()]
    out += list(sse.ensure_thinking_block())
    out.append(sse.emit_thinking_delta("let me think"))
    out += list(sse.ensure_text_block())
    out += [sse.emit_text_delta("Hel"), sse.emit_text_delta("lo")]
    out += list(sse.close_content_blocks())
    out.append(sse.start_tool_block(0, "toolu_1", "Read"))
    out += [sse.emit_tool_delta(0, '{"file_'), sse.emit_tool_delta(0, 'path": "a"}')]
    out += list(sse.close_all_blocks())
    out += [sse.message_delta("tool_use", 7), sse.message_stop()]
    return out


@pytest.mark.asyncio
async def test_collect_message_assembles_all_block_types():
    message = await collect_message(_events(*_turn_events()))
    assert message["id"] == "msg_1"
    assert message["stop_reason"] == "tool_use"
    assert message["usage"]["output_tokens"] == 7
    assert [b["type"] for b in message["content"]] == ["thinking", "text", "tool_use"]
    assert message["content"][0]["thinking"] == "let me think"
    assert message["content"][1]["text"] == "Hello"
    assert message["content"][2]["input"] == {"file_path": "a"}


@pytest.mark.asyncio
async def test_collect_message_raises_on_error_event():
    sse = SSEBuilder("msg_1", "m")
    with pytest.raises(APIError, match="boom"):
        await collect_message(
            _events(sse.message_start(), sse.error_event("api_error", "boom"))
        )


def _post(stream_response):
    provider = MagicMock(spec=NvidiaNimProvider)
    provider.stream_response = stream_response
    with patch("api.routes.get_provider_for_type", return_value=provider):
        return TestClient(app).post("/v1/messages", json=PAYLOAD)


def test_stream_false_returns_one_message():
    async def stream(request, **kwargs):
        for e in _turn_events():
            yield e

    response = _post(stream)
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("application/json")
    assert response.json()["content"][1]["text"] == "Hello"


def test_stream_false_error_before_output_is_a_real_http_error():
    seen = {}

    async def stream(request, **kwargs):
        seen.update(kwargs)
        raise RateLimitError("slow down")
        yield  # pragma: no cover

    response = _post(stream)
    assert seen["raise_before_output"] is True
    assert response.status_code == 429
    assert response.json() == {
        "type": "error",
        "error": {"type": "rate_limit_error", "message": "slow down"},
    }
