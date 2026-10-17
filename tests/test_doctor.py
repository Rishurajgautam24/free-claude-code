from unittest.mock import AsyncMock, MagicMock, patch

import pytest

import doctor
from config.settings import Settings


def _settings(**overrides) -> Settings:
    return Settings().model_copy(update=overrides)


def _provider(models=None, error=None):
    provider = MagicMock()
    provider.list_models = AsyncMock(return_value=models, side_effect=error)
    provider.cleanup = AsyncMock()
    return provider


@pytest.mark.asyncio
async def test_providers_report_missing_models_and_unreachable_providers():
    providers = {
        "nvidia_nim": _provider(models=["glm"]),
        "open_router": _provider(error=RuntimeError("connection refused")),
    }
    settings = _settings(
        model="nvidia_nim/glm,nvidia_nim/gone", model_opus="open_router/x"
    )
    with patch(
        "api.dependencies._create_provider_for_type",
        side_effect=lambda name, _: providers[name],
    ):
        results = await doctor.check_providers(settings)

    assert (doctor.OK, "nvidia_nim/glm is available") in results
    assert (doctor.FAIL, "nvidia_nim/gone: the provider has no such model") in results
    assert any(s == doctor.FAIL and "can't reach" in m for s, m in results)
    for provider in providers.values():
        provider.cleanup.assert_awaited_once()


@pytest.mark.asyncio
async def test_missing_key_is_reported():
    with patch(
        "api.dependencies._create_provider_for_type",
        side_effect=RuntimeError("GROQ_API_KEY is not set"),
    ):
        results = await doctor.check_providers(_settings(model="groq/llama"))
    assert results == [(doctor.FAIL, "groq: GROQ_API_KEY is not set")]


@pytest.mark.parametrize(
    ("overrides", "expected"),
    [
        ({}, doctor.OK),
        ({"host": "0.0.0.0"}, doctor.FAIL),
        ({"host": "0.0.0.0", "proxy_auth_token": "t"}, doctor.OK),
        (
            {"messaging_platform": "telegram", "telegram_bot_token": "x"},
            doctor.WARN,
        ),
    ],
)
def test_security(overrides, expected):
    assert doctor.check_security(_settings(**overrides))[0][0] == expected
