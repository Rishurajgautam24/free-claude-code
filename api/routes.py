"""FastAPI route handlers."""

import json
import traceback
import uuid
from collections.abc import AsyncIterator

import anyio
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse
from loguru import logger
from starlette.types import Message, Send

from config.settings import Settings
from providers.common import get_user_facing_error_message
from providers.exceptions import InvalidRequestError, ProviderError
from providers.logging_utils import build_request_summary, log_request_compact

from .dependencies import get_provider_for_type, get_settings, require_auth
from .models.anthropic import MessagesRequest, TokenCountRequest
from .models.responses import TokenCountResponse
from .optimization_handlers import try_optimizations
from .request_utils import get_token_count

router = APIRouter()

PING_MESSAGE: Message = {
    "type": "http.response.body",
    "body": b'event: ping\ndata: {"type": "ping"}\n\n',
    "more_body": True,
}


class KeepAliveStreamingResponse(StreamingResponse):
    """StreamingResponse that also sends an SSE ping every `ping_interval` seconds.

    Claude Code aborts a stream after ~5 minutes without bytes, e.g. while a
    request waits for a provider concurrency slot. The body is still iterated in
    the response task, so client-disconnect cancellation works as before.
    """

    ping_interval = 15.0

    async def stream_response(self, send: Send) -> None:
        finished = False

        async def tracking_send(message: Message) -> None:
            nonlocal finished
            if message["type"] == "http.response.body" and not message.get(
                "more_body", False
            ):
                finished = True  # no pings after the final body message
            await send(message)

        async def ping() -> None:
            while True:
                await anyio.sleep(self.ping_interval)
                if not finished:
                    await send(PING_MESSAGE)

        # shortcut: errors leave as an ExceptionGroup; Starlette unwraps them on ASGI
        # spec 2.3 (uvicorn), but not on 2.4 servers. Unwrap here if we support one.
        async with anyio.create_task_group() as tg:
            tg.start_soon(ping)
            await super().stream_response(tracking_send)
            tg.cancel_scope.cancel()


async def stream_with_fallback(
    request_data: MessagesRequest,
    models: list[str],
    first_events: AsyncIterator[str],
    input_tokens: int,
    request_id: str,
) -> AsyncIterator[str]:
    """Relay `first_events`; if models[0] fails before any content, try the next model.

    The last model streams its error to the client as usual.
    """
    for i, model in enumerate(models):
        is_last = i == len(models) - 1
        try:
            events = first_events
            if i:
                provider = get_provider_for_type(Settings.parse_provider_type(model))
                request_data.model = Settings.parse_model_name(model)
                events = provider.stream_response(
                    request_data,
                    input_tokens=input_tokens,
                    request_id=request_id,
                    raise_before_output=not is_last,
                )
            async for event in events:
                # The client already got message_start from the first attempt.
                if i and event.startswith("event: message_start"):
                    continue
                yield event
            return
        except Exception as e:
            if is_last:
                raise
            logger.warning(
                "MODEL_FALLBACK: {} failed before output ({}), trying {}",
                model,
                get_user_facing_error_message(e),
                models[i + 1],
            )


# =============================================================================
# Routes
# =============================================================================
@router.post("/v1/messages")
async def create_message(
    request_data: MessagesRequest,
    raw_request: Request,
    settings: Settings = Depends(get_settings),
    model_override: str | None = Depends(require_auth),
):
    """Create a message (always streaming)."""

    try:
        if model_override:
            request_data.resolved_provider_model = model_override
            request_data.model = Settings.parse_model_name(model_override)

        if not request_data.messages:
            raise InvalidRequestError("messages cannot be empty")

        optimized = try_optimizations(request_data, settings)
        if optimized is not None:
            return optimized

        # Resolve the provider of the first model now, so misconfiguration is a 503.
        models = (request_data.resolved_provider_model or settings.model).split(",")
        provider = get_provider_for_type(Settings.parse_provider_type(models[0]))

        request_id = f"req_{uuid.uuid4().hex[:12]}"
        log_request_compact(logger, request_id, request_data)

        input_tokens = get_token_count(
            request_data.messages, request_data.system, request_data.tools
        )
        first_events = provider.stream_response(
            request_data,
            input_tokens=input_tokens,
            request_id=request_id,
            raise_before_output=len(models) > 1,
        )
        return KeepAliveStreamingResponse(
            stream_with_fallback(
                request_data, models, first_events, input_tokens, request_id
            ),
            media_type="text/event-stream",
            headers={
                "X-Accel-Buffering": "no",
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
            },
        )

    except ProviderError:
        raise
    except Exception as e:
        logger.error(f"Error: {e!s}\n{traceback.format_exc()}")
        raise HTTPException(
            status_code=getattr(e, "status_code", 500),
            detail=get_user_facing_error_message(e),
        ) from e


@router.post("/v1/messages/count_tokens", dependencies=[Depends(require_auth)])
async def count_tokens(request_data: TokenCountRequest):
    """Count tokens for a request."""
    request_id = f"req_{uuid.uuid4().hex[:12]}"
    with logger.contextualize(request_id=request_id):
        try:
            tokens = get_token_count(
                request_data.messages, request_data.system, request_data.tools
            )
            summary = build_request_summary(request_data)
            summary["request_id"] = request_id
            summary["input_tokens"] = tokens
            logger.info("COUNT_TOKENS: {}", json.dumps(summary))
            return TokenCountResponse(input_tokens=tokens)
        except Exception as e:
            logger.error(
                "COUNT_TOKENS_ERROR: request_id={} error={}\n{}",
                request_id,
                get_user_facing_error_message(e),
                traceback.format_exc(),
            )
            raise HTTPException(
                status_code=500, detail=get_user_facing_error_message(e)
            ) from e


@router.get("/")
async def root(settings: Settings = Depends(get_settings)):
    """Root endpoint."""
    return {
        "status": "ok",
        "provider": settings.provider_type,
        "model": settings.model,
    }


@router.get("/health")
async def health():
    """Health check endpoint."""
    return {"status": "healthy"}


@router.post("/stop", dependencies=[Depends(require_auth)])
async def stop_cli(request: Request):
    """Stop all CLI sessions and pending tasks."""
    handler = getattr(request.app.state, "message_handler", None)
    if not handler:
        # Fallback if messaging not initialized
        cli_manager = getattr(request.app.state, "cli_manager", None)
        if cli_manager:
            await cli_manager.stop_all()
            logger.info("STOP_CLI: source=cli_manager cancelled_count=N/A")
            return {"status": "stopped", "source": "cli_manager"}
        raise HTTPException(status_code=503, detail="Messaging system not initialized")

    count = await handler.stop_all_tasks()
    logger.info("STOP_CLI: source=handler cancelled_count={}", count)
    return {"status": "stopped", "cancelled_count": count}
