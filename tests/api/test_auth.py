from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from api.app import app
from api.dependencies import get_settings
from config.settings import Settings
from providers.nvidia_nim import NvidiaNimProvider

PAYLOAD = {
    "model": "claude-3-sonnet",
    "messages": [{"role": "user", "content": "Hi"}],
    "max_tokens": 100,
}


@pytest.fixture
def calls():
    seen = []

    async def _stream(request, **kwargs):
        seen.append(request)
        yield "event: message_stop\ndata: {}\n\n"

    provider = MagicMock(spec=NvidiaNimProvider)
    provider.stream_response = _stream
    with patch("api.routes.get_provider_for_type", return_value=provider) as get:
        yield get, seen


def _client(token: str = "") -> TestClient:
    settings = Settings().model_copy(update={"proxy_auth_token": token})
    app.dependency_overrides[get_settings] = lambda: settings
    return TestClient(app)


@pytest.fixture(autouse=True)
def _clear_overrides():
    yield
    app.dependency_overrides.clear()


def test_no_token_configured_accepts_any_client():
    assert _client().post("/v1/messages/count_tokens", json=PAYLOAD).status_code == 200


@pytest.mark.parametrize(
    "headers",
    [{"Authorization": "Bearer s3cret"}, {"x-api-key": "s3cret"}],
)
def test_valid_token_accepted(headers):
    response = _client("s3cret").post(
        "/v1/messages/count_tokens", json=PAYLOAD, headers=headers
    )
    assert response.status_code == 200


@pytest.mark.parametrize(
    ("method", "path"),
    [
        ("post", "/v1/messages"),
        ("post", "/v1/messages/count_tokens"),
        ("post", "/stop"),
    ],
)
@pytest.mark.parametrize(
    "headers", [{}, {"Authorization": "Bearer wrong"}, {"x-api-key": "wrong"}]
)
def test_bad_token_rejected(method, path, headers):
    response = getattr(_client("s3cret"), method)(path, json=PAYLOAD, headers=headers)
    assert response.status_code == 401
    assert response.json()["error"]["type"] == "authentication_error"


def test_health_stays_public():
    assert _client("s3cret").get("/health").status_code == 200


@pytest.mark.parametrize(
    ("token", "resolved"),
    [
        ("s3cret:open_router/arcee-ai/x:free", "open_router/arcee-ai/x:free"),
        # No known provider prefix: use the default MODEL's provider.
        ("s3cret:moonshotai/kimi-k2.5", "nvidia_nim/moonshotai/kimi-k2.5"),
        ("s3cret:kimi", "nvidia_nim/kimi"),
    ],
)
def test_token_suffix_overrides_model(calls, token, resolved):
    response = _client("s3cret").post(
        "/v1/messages", json=PAYLOAD, headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 200
    b"".join(response.iter_bytes())
    get, seen = calls
    (request,) = seen
    get.assert_called_once_with(resolved.split("/", 1)[0])
    assert request.resolved_provider_model == resolved
    assert request.model == resolved.split("/", 1)[1]
    assert request.original_model == "claude-3-sonnet"


@pytest.mark.asyncio
async def test_cli_session_sends_proxy_token():
    from cli.session import CLISession

    process = AsyncMock()
    process.stdout.read.side_effect = [b""]
    process.stderr.read.return_value = b""
    process.wait.return_value = 0
    process.returncode = 0
    with patch("asyncio.create_subprocess_exec", new_callable=AsyncMock) as run:
        run.return_value = process
        session = CLISession("/tmp", "http://localhost:8082/v1", auth_token="s3cret")
        [e async for e in session.start_task("Hi")]
    env = run.call_args.kwargs["env"]
    assert env["ANTHROPIC_API_KEY"] == env["ANTHROPIC_AUTH_TOKEN"] == "s3cret"
