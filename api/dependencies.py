"""Dependency injection for FastAPI."""

import hmac

from fastapi import Depends, HTTPException, Request
from loguru import logger

from config.settings import OPENAI_COMPATIBLE_PRESETS, VALID_PROVIDERS, Settings
from config.settings import get_settings as _get_settings
from providers.base import BaseProvider, ProviderConfig
from providers.common import get_user_facing_error_message
from providers.exceptions import AuthenticationError
from providers.lmstudio import LMStudioProvider
from providers.nvidia_nim import NVIDIA_NIM_BASE_URL, NvidiaNimProvider
from providers.open_router import OPENROUTER_BASE_URL, OpenRouterProvider

# Provider registry: keyed by provider type string, lazily populated
_providers: dict[str, BaseProvider] = {}


def get_settings() -> Settings:
    """Get application settings via dependency injection."""
    return _get_settings()


def require_auth(
    request: Request, settings: Settings = Depends(get_settings)
) -> str | None:
    """Check the client token `<token>[:<model>]`; return the model override, if any.

    A model without a known provider prefix uses the default MODEL's provider.
    """
    auth = request.headers.get("authorization", "").removeprefix("Bearer ").strip()
    token, _, model = (auth or request.headers.get("x-api-key", "")).partition(":")
    expected = settings.proxy_auth_token
    if expected and not hmac.compare_digest(token.encode(), expected.encode()):
        raise AuthenticationError("Invalid proxy auth token")
    if not model:
        return None
    provider, sep, _ = model.partition("/")
    if not sep or provider not in VALID_PROVIDERS:
        return f"{settings.provider_type}/{model}"
    return model


def _provider_config(settings: Settings, api_key: str, base_url: str) -> ProviderConfig:
    return ProviderConfig(
        api_key=api_key,
        base_url=base_url,
        rate_limit=settings.provider_rate_limit,
        rate_window=settings.provider_rate_window,
        max_concurrency=settings.provider_max_concurrency,
        http_read_timeout=settings.http_read_timeout,
        http_write_timeout=settings.http_write_timeout,
        http_connect_timeout=settings.http_connect_timeout,
    )


def _require_key(key: str, env_var: str, key_page: str) -> str:
    if not key.strip():
        raise AuthenticationError(
            f"{env_var} is not set. Add it to your .env file. Get a key at {key_page}"
        )
    return key


def _create_provider_for_type(provider_type: str, settings: Settings) -> BaseProvider:
    """Construct and return a new provider instance for the given provider type."""
    if provider_type == "nvidia_nim":
        key = _require_key(
            settings.nvidia_nim_api_key,
            "NVIDIA_NIM_API_KEY",
            "https://build.nvidia.com/settings/api-keys",
        )
        return NvidiaNimProvider(
            _provider_config(settings, key, NVIDIA_NIM_BASE_URL),
            nim_settings=settings.nim,
        )
    if provider_type == "open_router":
        key = _require_key(
            settings.open_router_api_key,
            "OPENROUTER_API_KEY",
            "https://openrouter.ai/keys",
        )
        return OpenRouterProvider(_provider_config(settings, key, OPENROUTER_BASE_URL))
    if provider_type == "lmstudio":
        return LMStudioProvider(
            _provider_config(settings, "lm-studio", settings.lm_studio_base_url)
        )
    if provider_type == "ollama":
        return LMStudioProvider(
            _provider_config(settings, "ollama", settings.ollama_base_url), "OLLAMA"
        )
    if provider_type == "custom":
        if not settings.custom_base_url.strip():
            raise AuthenticationError(
                "CUSTOM_BASE_URL is not set. Add your OpenAI-compatible endpoint to .env"
            )
        config = _provider_config(
            settings, settings.custom_api_key or "none", settings.custom_base_url
        )
        return LMStudioProvider(config, "CUSTOM")
    if provider_type in OPENAI_COMPATIBLE_PRESETS:
        base_url, key_page = OPENAI_COMPATIBLE_PRESETS[provider_type]
        env_var = f"{provider_type.upper()}_API_KEY"
        key = _require_key(getattr(settings, env_var.lower()), env_var, key_page)
        return LMStudioProvider(
            _provider_config(settings, key, base_url), provider_type.upper()
        )
    logger.error(
        "Unknown provider_type: '{}'. Supported: {}", provider_type, VALID_PROVIDERS
    )
    raise ValueError(
        f"Unknown provider_type: '{provider_type}'. "
        f"Supported: {', '.join(VALID_PROVIDERS)}"
    )


def get_provider_for_type(provider_type: str) -> BaseProvider:
    """Get or create a provider for the given provider type.

    Providers are cached in the registry and reused across requests.
    """
    if provider_type not in _providers:
        try:
            _providers[provider_type] = _create_provider_for_type(
                provider_type, get_settings()
            )
        except AuthenticationError as e:
            raise HTTPException(
                status_code=503, detail=get_user_facing_error_message(e)
            ) from e
        logger.info("Provider initialized: {}", provider_type)
    return _providers[provider_type]


def get_provider() -> BaseProvider:
    """Get or create the default provider (based on MODEL env var).

    Backward-compatible convenience for health/root endpoints and tests.
    """
    return get_provider_for_type(get_settings().provider_type)


async def cleanup_provider():
    """Cleanup all provider resources."""
    global _providers
    for provider in _providers.values():
        await provider.cleanup()
    _providers = {}
    logger.debug("Provider cleanup completed")
