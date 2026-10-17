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
