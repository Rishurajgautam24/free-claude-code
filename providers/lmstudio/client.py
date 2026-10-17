"""LM Studio provider implementation."""

from typing import Any

from providers.base import ProviderConfig
from providers.openai_compat import OpenAICompatibleProvider

from .request import build_request_body

LMSTUDIO_DEFAULT_BASE_URL = "http://localhost:1234/v1"


class LMStudioProvider(OpenAICompatibleProvider):
    """Plain OpenAI-compatible provider: LM Studio, and the other OpenAI-compatible APIs."""

    def __init__(self, config: ProviderConfig, provider_name: str = "LMSTUDIO"):
        super().__init__(
            config,
            provider_name=provider_name,
            base_url=config.base_url or LMSTUDIO_DEFAULT_BASE_URL,
            api_key=config.api_key or "lm-studio",
        )

    def _build_request_body(self, request: Any) -> dict:
        """Internal helper for tests and shared building."""
        return build_request_body(request)
