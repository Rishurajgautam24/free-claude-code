from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient

from api.app import app
from api.dependencies import get_settings
from config.settings import Settings
from providers.nvidia_nim import NvidiaNimProvider


def _client(**overrides) -> TestClient:
    settings = Settings().model_copy(update=overrides)
    app.dependency_overrides[get_settings] = lambda: settings
    return TestClient(app)


def teardown_function():
    app.dependency_overrides.clear()


def test_lists_every_configured_model_once():
    body = (
        _client(
            model="nvidia_nim/glm,open_router/step:free",
            model_opus="nvidia_nim/kimi",
            model_haiku="nvidia_nim/glm",
        )
        .get("/v1/models")
        .json()
    )

    assert [m["id"] for m in body["data"]] == [
        "claude-fcc/nvidia_nim/kimi",
        "claude-fcc/nvidia_nim/glm",
        "claude-fcc/open_router/step:free",
    ]
    assert all("claude" in m["id"] for m in body["data"])  # Claude Code's filter
    descriptions = {m["display_name"]: m["description"] for m in body["data"]}
    assert descriptions["nvidia_nim/glm"] == "MODEL_HAIKU, MODEL"
    assert descriptions["open_router/step:free"] == "MODEL fallback 1"
    assert body["has_more"] is False
    assert body["first_id"] == "claude-fcc/nvidia_nim/kimi"


def test_requires_proxy_token_when_set():
    client = _client(proxy_auth_token="s3cret")
    assert client.get("/v1/models").status_code == 401
    assert client.get("/v1/models", headers={"x-api-key": "s3cret"}).status_code == 200


def test_picked_model_routes_to_that_model():
    settings = Settings()
    assert (
        settings.resolve_model("claude-fcc/open_router/anthropic/claude-3-opus")
        == "open_router/anthropic/claude-3-opus"
    )
    # Unknown provider after the prefix: normal tier mapping applies.
    assert settings.resolve_model("claude-fcc/bogus/x") == settings.model


def test_messages_with_picked_model_use_its_provider():
    seen = []

    async def stream(request, **kwargs):
        seen.append(request.model)
        yield "event: message_stop\ndata: {}\n\n"

    provider = MagicMock(spec=NvidiaNimProvider)
    provider.stream_response = stream
    with patch("api.routes.get_provider_for_type", return_value=provider) as get:
        response = TestClient(app).post(
            "/v1/messages",
            json={
                "model": "claude-fcc/open_router/step:free",
                "max_tokens": 10,
                "messages": [{"role": "user", "content": "hi"}],
            },
        )
        b"".join(response.iter_bytes())
    get.assert_called_once_with("open_router")
    assert seen == ["step:free"]


def _catalog(provider_or_error):
    provider = MagicMock(spec=NvidiaNimProvider)
    if isinstance(provider_or_error, Exception):
        provider.list_models.side_effect = provider_or_error
    else:
        provider.list_models.return_value = provider_or_error
    return patch("api.routes.get_provider_for_type", return_value=provider)


def test_catalog_lists_every_model_of_a_provider():
    with _catalog(["llama-3.3-70b", "gpt-oss-120b"]):
        body = _client().get("/v1/models?catalog=groq").json()
    assert [m["id"] for m in body["data"]] == [
        "claude-fcc/groq/llama-3.3-70b",
        "claude-fcc/groq/gpt-oss-120b",
    ]
    assert body["data"][0]["display_name"] == "groq/llama-3.3-70b"


def test_catalog_errors_are_clear():
    client = _client()
    assert client.get("/v1/models?catalog=bogus").status_code == 400
    with _catalog(RuntimeError("connection refused")):
        response = client.get("/v1/models?catalog=lmstudio")
    assert response.status_code == 502
    assert "Could not list lmstudio models" in response.json()["detail"]
