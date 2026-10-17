from unittest.mock import AsyncMock, patch

import httpx
import openai
import pytest

from api.models.anthropic import Message
from providers.common.message_converter import (
    IMAGE_PLACEHOLDER,
    AnthropicToOpenAIConverter,
    has_images,
    strip_images,
)
from tests.providers.test_streaming_errors import (
    AsyncStreamMock,
    _make_chunk,
    _make_provider,
    _make_request,
)

PNG = {"type": "base64", "media_type": "image/png", "data": "iVBORw0KGgo="}


def _user(*blocks):
    msg = Message.model_validate({"role": "user", "content": list(blocks)})
    return AnthropicToOpenAIConverter.convert_messages([msg])


def test_user_image_becomes_image_url_part():
    (msg,) = _user(
        {"type": "text", "text": "what is this?"}, {"type": "image", "source": PNG}
    )
    assert msg["content"] == [
        {"type": "text", "text": "what is this?"},
        {
            "type": "image_url",
            "image_url": {"url": "data:image/png;base64,iVBORw0KGgo="},
        },
    ]


def test_url_image_source():
    (msg,) = _user(
        {"type": "image", "source": {"type": "url", "url": "https://x/y.png"}}
    )
    assert msg["content"][0]["image_url"]["url"] == "https://x/y.png"


def test_text_only_user_message_stays_a_string():
    (msg,) = _user({"type": "text", "text": "a"}, {"type": "text", "text": "b"})
    assert msg["content"] == "a\nb"


def test_tool_result_image_is_not_inlined_as_base64():
    (msg,) = _user(
        {
            "type": "tool_result",
            "tool_use_id": "t1",
            "content": [
                {"type": "text", "text": "screenshot.png"},
                {"type": "image", "source": PNG},
            ],
        }
    )
    assert msg == {
        "role": "tool",
        "tool_call_id": "t1",
        "content": f"screenshot.png\n{IMAGE_PLACEHOLDER}",
    }


def test_strip_images():
    body = {
        "messages": _user(
            {"type": "text", "text": "hi"}, {"type": "image", "source": PNG}
        )
    }
    assert has_images(body)
    stripped = strip_images(body)
    assert not has_images(stripped)
    assert stripped["messages"][0]["content"] == f"hi\n{IMAGE_PLACEHOLDER}"
    assert has_images(body)  # original untouched


def _bad_request():
    response = httpx.Response(400, request=httpx.Request("POST", "http://x"))
    return openai.BadRequestError(
        "model does not support images", response=response, body=None
    )


def _image_request():
    request = _make_request()
    request.messages = [
        Message.model_validate(
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": "hi"},
                    {"type": "image", "source": PNG},
                ],
            }
        )
    ]
    return request


async def _run(provider, create):
    with (
        patch.object(provider._client.chat.completions, "create", create),
        patch.object(provider._rate_limiter, "wait_if_blocked", new_callable=AsyncMock),
    ):
        return "".join([e async for e in provider.stream_response(_image_request())])


@pytest.mark.asyncio
async def test_text_only_model_retries_without_images_and_is_remembered():
    provider = _make_provider()
    ok = AsyncStreamMock(
        [_make_chunk(content="a cat"), _make_chunk(finish_reason="stop")]
    )
    create = AsyncMock(side_effect=[_bad_request(), ok])

    text = await _run(provider, create)

    assert "a cat" in text
    first, second = (c.kwargs["messages"] for c in create.call_args_list)
    assert has_images({"messages": first})
    assert not has_images({"messages": second})

    # Next request skips the failing attempt entirely.
    create = AsyncMock(return_value=AsyncStreamMock([_make_chunk(content="ok")]))
    await _run(provider, create)
    assert create.call_count == 1
    assert not has_images({"messages": create.call_args.kwargs["messages"]})


@pytest.mark.asyncio
async def test_bad_request_without_images_is_not_retried():
    provider = _make_provider()
    create = AsyncMock(side_effect=_bad_request())
    with (
        patch.object(provider._client.chat.completions, "create", create),
        patch.object(provider._rate_limiter, "wait_if_blocked", new_callable=AsyncMock),
    ):
        text = "".join([e async for e in provider.stream_response(_make_request())])
    assert create.call_count == 1
    assert "model does not support images" in text
