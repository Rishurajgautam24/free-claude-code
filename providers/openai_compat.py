"""Shared base class for OpenAI-compatible providers (NIM, OpenRouter, LM Studio)."""

import json
import uuid
from abc import abstractmethod
from collections.abc import AsyncIterator, Iterator
from typing import Any

import httpx
from loguru import logger
from openai import AsyncOpenAI, BadRequestError

from providers.base import BaseProvider, ProviderConfig
from providers.common import (
    ContentType,
    HeuristicToolParser,
    SSEBuilder,
    ThinkTagParser,
    append_request_id,
    get_user_facing_error_message,
    map_error,
    map_stop_reason,
)
from providers.common.message_converter import has_images, strip_images
from providers.common.utils import max_tokens_limit
from providers.exceptions import RateLimitError
from providers.rate_limit import ProviderRateLimiter


class OpenAICompatibleProvider(BaseProvider):
    """Base class for providers using OpenAI-compatible chat completions API."""

    def __init__(
        self,
        config: ProviderConfig,
        *,
        provider_name: str,
        base_url: str,
        api_key: str,
        nim_settings: Any = None,
    ):
        super().__init__(config)
        self._provider_name = provider_name
        self._api_key = api_key
        self._base_url = base_url.rstrip("/")
        self._nim_settings = nim_settings
        # Learned from 400s: models without image input, and their max output tokens.
        self._text_only_models: set[str] = set()
        self._max_tokens_caps: dict[str, int] = {}
        self._rate_limiter = ProviderRateLimiter(
            rate_limit=config.rate_limit,
            rate_window=config.rate_window,
            max_concurrency=config.max_concurrency,
        )
        self._client = AsyncOpenAI(
            api_key=self._api_key,
            base_url=self._base_url,
            max_retries=0,
            timeout=httpx.Timeout(
                config.http_read_timeout,
                connect=config.http_connect_timeout,
                read=config.http_read_timeout,
                write=config.http_write_timeout,
            ),
        )

    async def list_models(self) -> list[str]:
        """Model IDs from the provider's OpenAI-compatible /models endpoint."""
        return sorted([model.id async for model in self._client.models.list()])

    async def cleanup(self) -> None:
        """Release HTTP client resources."""
        client = getattr(self, "_client", None)
        if client is not None:
            await client.aclose()

    @abstractmethod
    def _build_request_body(self, request: Any) -> dict:
        """Build request body. Must be implemented by subclasses."""

    def _handle_extra_reasoning(self, delta: Any, sse: SSEBuilder) -> Iterator[str]:
        """Hook for provider-specific reasoning (e.g. OpenRouter reasoning_details)."""
        return iter(())

    def _process_tool_call(self, tc: dict, sse: SSEBuilder) -> Iterator[str]:
        """Process a single tool call delta and yield SSE events."""
        tc_index = tc.get("index", 0)
        if tc_index < 0:
            tc_index = len(sse.blocks.tool_states)

        fn_delta = tc.get("function") or {}
        incoming_name = fn_delta.get("name")
        if incoming_name is not None or tc_index not in sse.blocks.tool_states:
            sse.blocks.register_tool_name(tc_index, incoming_name or "")
        state = sse.blocks.tool_states[tc_index]
        if tc.get("id") and not state.started:
            state.tool_id = tc["id"]

        # Start the block on the first arguments: by then the name, which some
        # providers send after the id or in fragments, is complete.
        args = fn_delta.get("arguments")
        if args:
            if not state.started:
                yield sse.start_tool_block(
                    tc_index,
                    state.tool_id or f"tool_{uuid.uuid4()}",
                    state.name or "tool_call",
                )

            current_name = state.name
            if current_name == "Task":
                parsed = sse.blocks.buffer_task_args(tc_index, args)
                if parsed is not None:
                    yield sse.emit_tool_delta(tc_index, json.dumps(parsed))
                return

            yield sse.emit_tool_delta(tc_index, args)

    async def _open_stream(self, body: dict, tag: str) -> Any:
        """Start the stream, retrying 400s we can fix: output limit, then images."""
        while True:
            try:
                return await self._rate_limiter.execute_with_retry(
                    self._client.chat.completions.create, **body, stream=True
                )
            except BadRequestError as e:
                fixed = self._fix_bad_request(body, str(e), tag)
                if fixed is None:
                    raise
                body = fixed  # each fix strictly shrinks the request, so this ends

    def _fix_bad_request(self, body: dict, error: str, tag: str) -> dict | None:
        """A smaller request the provider should accept, remembered per model, or None."""
        model = body.get("model", "")
        limit = max_tokens_limit(error, body.get("max_tokens"))
        if limit:
            logger.warning("{}: {} allows max_tokens={}, retrying", tag, model, limit)
            self._max_tokens_caps[model] = limit
            return {**body, "max_tokens": limit}
        if has_images(body):
            logger.warning("{}: {} rejected images, retrying without", tag, model)
            self._text_only_models.add(model)
            return strip_images(body)
        return None

    def _flush_task_arg_buffers(self, sse: SSEBuilder) -> Iterator[str]:
        """Emit buffered Task args as a single JSON delta (best-effort)."""
        for tool_index, out in sse.blocks.flush_task_arg_buffers():
            yield sse.emit_tool_delta(tool_index, out)

    async def stream_response(
        self,
        request: Any,
        input_tokens: int = 0,
        *,
        request_id: str | None = None,
        raise_before_output: bool = False,
    ) -> AsyncIterator[str]:
        """Stream response in Anthropic SSE format."""
        with logger.contextualize(request_id=request_id):
            async for event in self._stream_response_impl(
                request, input_tokens, request_id, raise_before_output
            ):
                yield event

    async def _stream_response_impl(
        self,
        request: Any,
        input_tokens: int,
        request_id: str | None,
        raise_before_output: bool = False,
    ) -> AsyncIterator[str]:
        """Shared streaming implementation."""
        tag = self._provider_name
        message_id = f"msg_{uuid.uuid4()}"
        sse = SSEBuilder(message_id, request.model, input_tokens)

        body = self._build_request_body(request)
        model = body.get("model", "")
        if model in self._text_only_models:
            body = strip_images(body)
        cap = self._max_tokens_caps.get(model)
        if cap and body.get("max_tokens", 0) > cap:
            body["max_tokens"] = cap
        req_tag = f" request_id={request_id}" if request_id else ""
        logger.info(
            "{}_STREAM:{} model={} msgs={} tools={}",
            tag,
            req_tag,
            body.get("model"),
            len(body.get("messages", [])),
            len(body.get("tools", [])),
        )

        yield sse.message_start()

        think_parser = ThinkTagParser()
        heuristic_parser = HeuristicToolParser()

        finish_reason = None
        text_tool_calls = 0
        usage_info = None

        async with self._rate_limiter.concurrency_slot():
            try:
                stream = await self._open_stream(body, tag)
                async for chunk in stream:
                    if getattr(chunk, "usage", None):
                        usage_info = chunk.usage

                    if not chunk.choices:
                        continue

                    choice = chunk.choices[0]
                    # Read before the delta check: some providers end with delta=None.
                    if choice.finish_reason:
                        finish_reason = choice.finish_reason
                        logger.debug("{} finish_reason: {}", tag, finish_reason)

                    delta = choice.delta
                    if delta is None:
                        continue

                    # Handle reasoning_content (OpenAI extended format)
                    reasoning = getattr(delta, "reasoning_content", None)
                    if reasoning:
                        for event in sse.ensure_thinking_block():
                            yield event
                        yield sse.emit_thinking_delta(reasoning)

                    # Provider-specific extra reasoning (e.g. OpenRouter reasoning_details)
                    for event in self._handle_extra_reasoning(delta, sse):
                        yield event

                    # Handle text content
                    if delta.content:
                        for part in think_parser.feed(delta.content):
                            if part.type == ContentType.THINKING:
                                for event in sse.ensure_thinking_block():
                                    yield event
                                yield sse.emit_thinking_delta(part.content)
                            else:
                                filtered_text, detected_tools = heuristic_parser.feed(
                                    part.content
                                )

                                if filtered_text:
                                    for event in sse.ensure_text_block():
                                        yield event
                                    yield sse.emit_text_delta(filtered_text)

                                for tool_use in detected_tools:
                                    text_tool_calls += 1
                                    for event in sse.close_content_blocks():
                                        yield event

                                    block_idx = sse.blocks.allocate_index()
                                    if tool_use.get("name") == "Task" and isinstance(
                                        tool_use.get("input"), dict
                                    ):
                                        tool_use["input"]["run_in_background"] = False
                                    yield sse.content_block_start(
                                        block_idx,
                                        "tool_use",
                                        id=tool_use["id"],
                                        name=tool_use["name"],
                                    )
                                    yield sse.content_block_delta(
                                        block_idx,
                                        "input_json_delta",
                                        json.dumps(tool_use["input"]),
                                    )
                                    yield sse.content_block_stop(block_idx)

                    # Handle native tool calls
                    if delta.tool_calls:
                        for event in sse.close_content_blocks():
                            yield event
                        for tc in delta.tool_calls:
                            fn = tc.function  # None on id-only deltas
                            tc_info = {
                                "index": tc.index,
                                "id": tc.id,
                                "function": {
                                    "name": fn.name if fn else None,
                                    "arguments": fn.arguments if fn else None,
                                },
                            }
                            for event in self._process_tool_call(tc_info, sse):
                                yield event

            except Exception as e:
                logger.error("{}_ERROR:{} {}: {}", tag, req_tag, type(e).__name__, e)
                mapped_e = map_error(e)
                if isinstance(mapped_e, RateLimitError):
                    self._rate_limiter.set_blocked(60)  # cool down this provider only
                if raise_before_output and sse.blocks.next_index == 0:
                    raise mapped_e from e
                error_message = append_request_id(
                    get_user_facing_error_message(
                        mapped_e, read_timeout_s=self._config.http_read_timeout
                    ),
                    request_id,
                )
                logger.info(
                    "{}_STREAM: Emitting SSE error event for {}{}",
                    tag,
                    type(e).__name__,
                    req_tag,
                )
                # Open blocks stay open: Claude Code keeps only completed blocks, so a
                # half-streamed tool call is never run with cut-off arguments.
                yield sse.error_event(
                    getattr(mapped_e, "error_type", "api_error"), error_message
                )
                return

        # Flush remaining content
        remaining = think_parser.flush()
        if remaining:
            if remaining.type == ContentType.THINKING:
                for event in sse.ensure_thinking_block():
                    yield event
                yield sse.emit_thinking_delta(remaining.content)
            else:
                for event in sse.ensure_text_block():
                    yield event
                yield sse.emit_text_delta(remaining.content)

        for tool_use in heuristic_parser.flush():
            text_tool_calls += 1
            for event in sse.close_content_blocks():
                yield event

            block_idx = sse.blocks.allocate_index()
            yield sse.content_block_start(
                block_idx,
                "tool_use",
                id=tool_use["id"],
                name=tool_use["name"],
            )
            if tool_use.get("name") == "Task" and isinstance(
                tool_use.get("input"), dict
            ):
                tool_use["input"]["run_in_background"] = False
            yield sse.content_block_delta(
                block_idx,
                "input_json_delta",
                json.dumps(tool_use["input"]),
            )
            yield sse.content_block_stop(block_idx)

        if sse.blocks.text_index == -1 and not sse.blocks.tool_states:
            for event in sse.ensure_text_block():
                yield event
            yield sse.emit_text_delta(" ")

        # Tools that never received arguments still need their block.
        for index, state in list(sse.blocks.tool_states.items()):
            if not state.started and state.name:
                yield sse.start_tool_block(
                    index, state.tool_id or f"tool_{uuid.uuid4()}", state.name
                )

        for event in self._flush_task_arg_buffers(sse):
            yield event

        for event in sse.close_all_blocks():
            yield event

        output_tokens = (
            usage_info.completion_tokens
            if usage_info and hasattr(usage_info, "completion_tokens")
            else sse.estimate_output_tokens()
        )
        if usage_info and hasattr(usage_info, "prompt_tokens"):
            provider_input = usage_info.prompt_tokens
            if isinstance(provider_input, int):
                logger.debug(
                    "TOKEN_ESTIMATE: our={} provider={} diff={:+d}",
                    input_tokens,
                    provider_input,
                    provider_input - input_tokens,
                )
        stop_reason = map_stop_reason(finish_reason)
        # Text-parsed tool calls, and some providers' native ones, end with "stop".
        if stop_reason == "end_turn" and (text_tool_calls or sse.blocks.tool_states):
            stop_reason = "tool_use"
        yield sse.message_delta(stop_reason, output_tokens)
        yield sse.message_stop()
