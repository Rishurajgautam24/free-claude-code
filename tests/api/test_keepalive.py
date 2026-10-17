import asyncio

import anyio
import pytest

from api.routes import PING_MESSAGE, KeepAliveStreamingResponse


async def _run(body, interval):
    sent = []

    async def send(message):
        sent.append(message)

    async def receive():
        await asyncio.sleep(3600)  # client never disconnects

    response = KeepAliveStreamingResponse(body)
    response.ping_interval = interval
    await response({"type": "http", "asgi": {"spec_version": "2.3"}}, receive, send)
    return sent


@pytest.mark.asyncio
async def test_pings_while_provider_is_quiet():
    async def provider():
        yield "a"
        await asyncio.sleep(0.25)
        yield "b"

    sent = await _run(provider(), interval=0.1)
    bodies = [m.get("body") for m in sent[1:]]
    assert sent[0]["type"] == "http.response.start"
    assert bodies[0] == b"a"
    assert bodies[-2:] == [b"b", b""]
    assert PING_MESSAGE in sent
    assert sent[-1]["more_body"] is False  # nothing sent after the final message


@pytest.mark.asyncio
async def test_no_pings_for_a_fast_stream():
    async def provider():
        for i in range(3):
            yield str(i)

    sent = await _run(provider(), interval=10)
    assert [m.get("body") for m in sent[1:]] == [b"0", b"1", b"2", b""]


@pytest.mark.asyncio
async def test_provider_error_propagates():
    async def provider():
        yield "a"
        raise RuntimeError("boom")

    with pytest.raises(RuntimeError, match="boom"):
        await _run(provider(), interval=10)


@pytest.mark.asyncio
async def test_disconnect_lets_provider_finish_shielded_cleanup():
    # httpx/httpcore close the upstream connection inside an anyio-shielded
    # cleanup; a client disconnect must not interrupt it (connection leak).
    cleaned = asyncio.Event()

    async def provider():
        try:
            yield "a"
            await asyncio.sleep(60)
        finally:
            with anyio.CancelScope(shield=True):
                await anyio.sleep(0.01)
                cleaned.set()

    async def send(message):
        pass

    disconnected = asyncio.Event()

    async def receive():
        await disconnected.wait()
        return {"type": "http.disconnect"}

    response = KeepAliveStreamingResponse(provider())
    task = asyncio.create_task(
        response({"type": "http", "asgi": {"spec_version": "2.3"}}, receive, send)
    )
    await asyncio.sleep(0.05)
    disconnected.set()
    await asyncio.wait_for(task, 1)
    await asyncio.wait_for(cleaned.wait(), 1)
