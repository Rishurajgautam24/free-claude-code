import pytest
from fastapi import HTTPException

from api.dependencies import _create_provider_for_type, get_provider_for_type
from config.settings import OPENAI_COMPATIBLE_PRESETS, Settings
from providers.lmstudio import LMStudioProvider


def _settings(**env) -> Settings:
    return Settings().model_copy(update=env)


@pytest.fixture(autouse=True)
def reset_provider():
    import api.dependencies

    saved = api.dependencies._providers
    api.dependencies._providers = {}
    yield
    api.dependencies._providers = saved


@pytest.mark.parametrize("name", sorted(OPENAI_COMPATIBLE_PRESETS))
def test_preset_uses_its_base_url_and_key(name):
    provider = _create_provider_for_type(name, _settings(**{f"{name}_api_key": "k"}))
    assert isinstance(provider, LMStudioProvider)
    assert provider._base_url == OPENAI_COMPATIBLE_PRESETS[name][0]
    assert provider._api_key == "k"
    assert provider._provider_name == name.upper()


def test_preset_without_key_is_a_clear_503(monkeypatch):
    monkeypatch.setattr("api.dependencies.get_settings", lambda: _settings())
    with pytest.raises(HTTPException) as exc:
        get_provider_for_type("groq")
    assert exc.value.status_code == 503
    assert "GROQ_API_KEY is not set" in exc.value.detail


def test_ollama_needs_no_key():
    provider = _create_provider_for_type("ollama", _settings())
    assert isinstance(provider, LMStudioProvider)
    assert provider._base_url == "http://localhost:11434/v1"


def test_custom_endpoint():
    provider = _create_provider_for_type(
        "custom", _settings(custom_base_url="https://llm.example.com/v1/")
    )
    assert isinstance(provider, LMStudioProvider)
    assert provider._base_url == "https://llm.example.com/v1"
    with pytest.raises(Exception, match="CUSTOM_BASE_URL is not set"):
        _create_provider_for_type("custom", _settings())


@pytest.mark.parametrize(
    "model",
    [
        "groq/llama-3.3-70b-versatile",
        "gemini/gemini-2.5-flash",
        "custom/x",
        "ollama/qwen3",
    ],
)
def test_new_providers_are_valid_model_prefixes(model):
    assert (
        Settings.validate_model_format(f"nvidia_nim/a,{model}")
        == f"nvidia_nim/a,{model}"
    )
