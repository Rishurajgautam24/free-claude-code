"""Message and tool format converters."""

import json
from typing import Any


def get_block_attr(block: Any, attr: str, default: Any = None) -> Any:
    """Get attribute from object or dict."""
    if hasattr(block, attr):
        return getattr(block, attr)
    if isinstance(block, dict):
        return block.get(attr, default)
    return default


def get_block_type(block: Any) -> str | None:
    """Get block type from object or dict."""
    return get_block_attr(block, "type")


class AnthropicToOpenAIConverter:
    """Converts Anthropic message format to OpenAI format."""

    @staticmethod
    def convert_messages(
        messages: list[Any],
        *,
        include_reasoning_for_openrouter: bool = False,
    ) -> list[dict[str, Any]]:
        """Convert a list of Anthropic messages to OpenAI format.

        When include_reasoning_for_openrouter is True, assistant messages with
        thinking blocks get reasoning_content added for OpenRouter multi-turn
        reasoning continuation.
        """
        result = []

        for msg in messages:
            role = msg.role
            content = msg.content

            if isinstance(content, str):
                result.append({"role": role, "content": content})
            elif isinstance(content, list):
                if role == "assistant":
                    result.extend(
                        AnthropicToOpenAIConverter._convert_assistant_message(
                            content,
                            include_reasoning_for_openrouter=include_reasoning_for_openrouter,
                        )
                    )
                elif role == "user":
                    result.extend(
                        AnthropicToOpenAIConverter._convert_user_message(content)
                    )
            else:
                result.append({"role": role, "content": str(content)})

        return result

    @staticmethod
    def _convert_assistant_message(
        content: list[Any],
        *,
        include_reasoning_for_openrouter: bool = False,
    ) -> list[dict[str, Any]]:
        """Convert assistant message blocks, preserving interleaved thinking+text order."""
        content_parts: list[str] = []
        thinking_parts: list[str] = []
        tool_calls: list[dict[str, Any]] = []

        for block in content:
            block_type = get_block_type(block)

            if block_type == "text":
                content_parts.append(get_block_attr(block, "text", ""))
            elif block_type == "thinking":
                thinking = get_block_attr(block, "thinking", "")
                content_parts.append(f"<think>\n{thinking}\n</think>")
                if include_reasoning_for_openrouter:
                    thinking_parts.append(thinking)
            elif block_type == "tool_use":
                tool_input = get_block_attr(block, "input", {})
                tool_calls.append(
                    {
                        "id": get_block_attr(block, "id"),
                        "type": "function",
                        "function": {
                            "name": get_block_attr(block, "name"),
                            "arguments": json.dumps(tool_input)
                            if isinstance(tool_input, dict)
                            else str(tool_input),
                        },
                    }
                )

        content_str = "\n\n".join(content_parts)

        # Ensure content is never an empty string for assistant messages
        # NIM (especially Mistral models) requires non-empty content if there are no tool calls
        if not content_str and not tool_calls:
            content_str = " "

        msg: dict[str, Any] = {
            "role": "assistant",
            "content": content_str,
        }
        if tool_calls:
            msg["tool_calls"] = tool_calls
        if include_reasoning_for_openrouter and thinking_parts:
            msg["reasoning_content"] = "\n".join(thinking_parts)

        return [msg]

    @staticmethod
    def _convert_user_message(content: list[Any]) -> list[dict[str, Any]]:
        """Convert user message blocks (including tool results), preserving order."""
        result: list[dict[str, Any]] = []
        parts: list[dict[str, Any]] = []

        def flush_parts() -> None:
            if parts:
                if all(p["type"] == "text" for p in parts):
                    content: Any = "\n".join(p["text"] for p in parts)
                else:
                    content = list(parts)
                result.append({"role": "user", "content": content})
                parts.clear()

        for block in content:
            block_type = get_block_type(block)

            if block_type == "text":
                parts.append(
                    {"type": "text", "text": get_block_attr(block, "text", "")}
                )
            elif block_type == "image":
                url = image_url(get_block_attr(block, "source", {}))
                if url:
                    parts.append({"type": "image_url", "image_url": {"url": url}})
            elif block_type == "tool_result":
                flush_parts()
                tool_content = get_block_attr(block, "content", "")
                if isinstance(tool_content, list):
                    # OpenAI tool messages are text-only: never inline base64 images.
                    tool_content = "\n".join(
                        IMAGE_PLACEHOLDER
                        if isinstance(item, dict) and item.get("type") == "image"
                        else item.get("text", str(item))
                        if isinstance(item, dict)
                        else str(item)
                        for item in tool_content
                    )
                result.append(
                    {
                        "role": "tool",
                        "tool_call_id": get_block_attr(block, "tool_use_id"),
                        "content": str(tool_content) if tool_content else "",
                    }
                )

        flush_parts()
        return result

    @staticmethod
    def convert_tools(tools: list[Any]) -> list[dict[str, Any]]:
        """Convert Anthropic tools to OpenAI format."""
        return [
            {
                "type": "function",
                "function": {
                    "name": tool.name,
                    "description": tool.description or "",
                    "parameters": tool.input_schema,
                },
            }
            for tool in tools
        ]

    @staticmethod
    def convert_system_prompt(system: Any) -> dict[str, str] | None:
        """Convert Anthropic system prompt to OpenAI format."""
        if isinstance(system, str):
            return {"role": "system", "content": system}
        elif isinstance(system, list):
            text_parts = [
                get_block_attr(block, "text", "")
                for block in system
                if get_block_type(block) == "text"
            ]
            if text_parts:
                return {"role": "system", "content": "\n\n".join(text_parts).strip()}
        return None


IMAGE_PLACEHOLDER = "[image omitted]"


def image_url(source: dict[str, Any]) -> str | None:
    """Anthropic image source (base64 or url) -> OpenAI image_url URL."""
    if source.get("type") == "base64" and source.get("data"):
        return f"data:{source.get('media_type', 'image/png')};base64,{source['data']}"
    if source.get("type") == "url":
        return source.get("url")
    return None


def has_images(body: dict[str, Any]) -> bool:
    """Whether an OpenAI request body contains image_url parts."""
    return any(
        isinstance(m.get("content"), list)
        and any(p.get("type") == "image_url" for p in m["content"])
        for m in body.get("messages", [])
    )


def strip_images(body: dict[str, Any]) -> dict[str, Any]:
    """Copy of an OpenAI request body with image parts replaced by a text placeholder."""
    messages = []
    for m in body.get("messages", []):
        if isinstance(m.get("content"), list):
            text = "\n".join(
                IMAGE_PLACEHOLDER if p.get("type") == "image_url" else p.get("text", "")
                for p in m["content"]
            )
            m = {**m, "content": text}
        messages.append(m)
    return {**body, "messages": messages}


def convert_tool_choice(choice: dict[str, Any]) -> str | dict[str, Any] | None:
    """Map Anthropic tool_choice ({"type": auto|any|tool|none}) to OpenAI's format."""
    kind = choice.get("type")
    if kind == "tool":
        return {"type": "function", "function": {"name": choice.get("name")}}
    return {"auto": "auto", "any": "required", "none": "none"}.get(kind)


def build_base_request_body(
    request_data: Any,
    *,
    default_max_tokens: int | None = None,
    include_reasoning_for_openrouter: bool = False,
) -> dict[str, Any]:
    """Build the common parts of an OpenAI-format request body.

    Handles message conversion, system prompt, max_tokens, temperature,
    top_p, stop sequences, tools, and tool_choice. Provider-specific
    parameters (extra_body, penalties, NIM settings) are added by callers.
    """
    from providers.common.utils import set_if_not_none

    messages = AnthropicToOpenAIConverter.convert_messages(
        request_data.messages,
        include_reasoning_for_openrouter=include_reasoning_for_openrouter,
    )

    system = getattr(request_data, "system", None)
    if system:
        system_msg = AnthropicToOpenAIConverter.convert_system_prompt(system)
        if system_msg:
            messages.insert(0, system_msg)

    body: dict[str, Any] = {"model": request_data.model, "messages": messages}

    max_tokens = getattr(request_data, "max_tokens", None)
    set_if_not_none(body, "max_tokens", max_tokens or default_max_tokens)
    set_if_not_none(body, "temperature", getattr(request_data, "temperature", None))
    set_if_not_none(body, "top_p", getattr(request_data, "top_p", None))

    stop_sequences = getattr(request_data, "stop_sequences", None)
    if stop_sequences:
        body["stop"] = stop_sequences

    tools = getattr(request_data, "tools", None)
    if tools:
        body["tools"] = AnthropicToOpenAIConverter.convert_tools(tools)
        # OpenAI rejects tool_choice without tools, so only map it alongside them.
        tool_choice = getattr(request_data, "tool_choice", None)
        if tool_choice:
            set_if_not_none(body, "tool_choice", convert_tool_choice(tool_choice))

    return body
