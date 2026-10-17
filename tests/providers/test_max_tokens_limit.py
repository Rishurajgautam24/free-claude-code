from unittest.mock import AsyncMock, patch

import httpx
import openai
import pytest

from providers.common.message_converter import has_images
from providers.common.utils import max_tokens_limit
from tests.providers.test_image_input import _image_request
from tests.providers.test_streaming_errors import (
    AsyncStreamMock,
    _make_chunk,
    _make_provider,
)

GROQ = (
    "`max_tokens` must be less than or equal to `32768`, the maximum value for "
    "`max_tokens` is less than the `context_window` for this model"
)
OPENAI = (
    "max_tokens is too large: 128000. This model supports at most 32768 "
    "completion tokens, whereas you provided 128000."
)
DEEPSEEK = "Invalid max_tokens value, the valid range of max_tokens is [1, 8192]"


@pytest.mark.parametrize(
    ("error", "limit"), [(GROQ, 32768), (OPENAI, 32768), (DEEPSEEK, 8192)]
)
def test_reads_limit_from_provider_errors(error, limit):
    assert max_tokens_limit(error, 128000) == limit


@pytest.mark.parametrize(
    ("error", "requested"),
    [
        ("model does not support images", 128000),  # unrelated 400
        (GROQ, None),  # request had no max_tokens
        ("max_tokens must be at least 200000", 128000),  # no smaller limit stated
    ],
)
def test_no_limit(error, requested):
    assert max_tokens_limit(error, requested) is None


def _bad_request(message):
    response = httpx.Response(400, request=httpx.Request("POST", "http://x"))
    return openai.BadRequestError(message, response=response, body=None)


def _ok():
    return AsyncStreamMock(
        [_make_chunk(content="ok"), _make_chunk(finish_reason="stop")]
    )


async def _run(provider, create, request):
    request.max_tokens = 128000
    with (
        patch.object(provider._client.chat.completions, "create", create),
        patch.object(provider._rate_limiter, "wait_if_blocked", new_callable=AsyncMock),
    ):
        return "".join([e async for e in provider.stream_response(request)])


@pytest.mark.asyncio
async def test_retries_with_stated_limit_and_remembers_it():
    provider = _make_provider()
    create = AsyncMock(side_effect=[_bad_request(GROQ), _ok()])

    assert "ok" in await _run(provider, create, _image_request())
    first, second = (c.kwargs["max_tokens"] for c in create.call_args_list)
    assert first > 32768  # NIM caps 128000 to its own default first
    assert second == 32768

    create = AsyncMock(return_value=_ok())
    await _run(provider, create, _image_request())
    assert create.call_count == 1
    assert create.call_args.kwargs["max_tokens"] == 32768


@pytest.mark.asyncio
async def test_output_limit_and_images_fixed_in_turn():
    provider = _make_provider()
    create = AsyncMock(
        side_effect=[_bad_request(DEEPSEEK), _bad_request("no image input"), _ok()]
    )

    assert "ok" in await _run(provider, create, _image_request())
    last = create.call_args_list[-1].kwargs
    assert create.call_count == 3
    assert last["max_tokens"] == 8192
    assert not has_images({"messages": last["messages"]})
