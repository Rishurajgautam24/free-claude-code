"""Claude Code (2.1.29x) sends mid-conversation role "system" messages."""

from api.models.anthropic import MessagesRequest
from providers.common.message_converter import AnthropicToOpenAIConverter

# Shape captured from a real Claude Code request.
REQUEST = {
    "model": "claude-opus-5-5",
    "max_tokens": 32000,
    "messages": [
        {"role": "user", "content": [{"type": "text", "text": "say hi"}]},
        {
            "role": "system",
            "content": [
                {
                    "type": "text",
                    "text": "# Environment\nPlatform: darwin",
                    "cache_control": {"type": "ephemeral"},
                }
            ],
        },
    ],
}


def test_request_with_system_role_is_accepted():
    request = MessagesRequest.model_validate(REQUEST)
    assert request.messages[1].role == "system"


def test_system_message_becomes_a_user_turn():
    request = MessagesRequest.model_validate(REQUEST)
    converted = AnthropicToOpenAIConverter.convert_messages(request.messages)
    assert converted == [
        {"role": "user", "content": "say hi"},
        {"role": "user", "content": "# Environment\nPlatform: darwin"},
    ]


def test_string_system_message():
    request = MessagesRequest.model_validate(
        {**REQUEST, "messages": [{"role": "system", "content": "be brief"}]}
    )
    converted = AnthropicToOpenAIConverter.convert_messages(request.messages)
    assert converted == [{"role": "user", "content": "be brief"}]
