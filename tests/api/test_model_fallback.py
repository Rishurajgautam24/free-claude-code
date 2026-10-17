from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from api.app import app
from config.settings import Settings, get_settings
from providers.nvidia_nim import NvidiaNimProvider

PAYLOAD = {
    "model": "claude-3-sonnet",
    "messages": [{"role": "user", "content": "Hi"}],
    "max_tokens": 100,
}


@pytest.fixture
def chain(monkeypatch):
    monkeypatch.setenv("MODEL", "nvidia_nim/primary, open_router/backup")
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


def _provider(fail_before_output: bool, calls: list):
    async def stream(request, **kwargs):
        calls.append((request.model, kwargs["raise_before_output"]))
        yield "event: message_start\ndata: {}\n\n"
        if fail_before_output and kwargs["raise_before_output"]:
            raise RuntimeError("primary down")
        yield f"event: content_block_delta\ndata: {request.model}\n\n"
        yield "event: message_stop\ndata: {}\n\n"

    provider = MagicMock(spec=NvidiaNimProvider)
    provider.stream_response = stream
    return provider


def _post(providers):
    with patch("api.routes.get_provider_for_type", side_effect=providers.__getitem__):
        response = TestClient(app).post("/v1/messages", json=PAYLOAD)
        return response.status_code, response.text


def test_falls_back_when_first_model_fails_before_output(chain):
    calls = []
    status, body = _post(
        {
            "nvidia_nim": _provider(fail_before_output=True, calls=calls),
            "open_router": _provider(fail_before_output=False, calls=calls),
        }
    )
    assert status == 200
    assert calls == [("primary", True), ("backup", False)]
    assert body.count("message_start") == 1
    assert "data: backup" in body
    assert "data: primary" not in body


def test_healthy_first_model_is_used_alone(chain):
    calls = []
    status, body = _post(
        {
            "nvidia_nim": _provider(fail_before_output=False, calls=calls),
            "open_router": _provider(fail_before_output=False, calls=calls),
        }
    )
    assert status == 200
    assert calls == [("primary", True)]
    assert "data: primary" in body


def test_chain_is_validated_and_normalized():
    assert (
        Settings.validate_model_format("nvidia_nim/a , open_router/b:free")
        == "nvidia_nim/a,open_router/b:free"
    )
    with pytest.raises(ValueError, match="Invalid provider"):
        Settings.validate_model_format("nvidia_nim/a,bogus/b")
