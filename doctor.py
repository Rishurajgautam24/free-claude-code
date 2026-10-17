"""Check a free-claude-code setup and say exactly what to fix.

Run with: uv run python doctor.py
"""

import asyncio
import os
import shutil
import subprocess
import sys

import httpx

# Importing the app configures logging, which truncates the log file:
# never touch a running server's server.log.
os.environ["LOG_FILE"] = os.devnull

OK, WARN, FAIL = "✓", "!", "✗"


def check_settings() -> tuple[list[tuple[str, str]], object | None]:
    from config.settings import get_settings

    try:
        settings = get_settings()
    except Exception as e:
        return [(FAIL, f".env is invalid: {e}")], None
    env = ".env found" if os.path.exists(".env") else "no .env (using defaults)"
    return [(OK if os.path.exists(".env") else WARN, env)], settings


async def check_providers(settings) -> list[tuple[str, str]]:
    from api.dependencies import _create_provider_for_type

    results = []
    by_provider: dict[str, list[str]] = {}
    for model in settings.configured_models():
        provider, name = model.split("/", 1)
        by_provider.setdefault(provider, []).append(name)

    for provider_type, names in by_provider.items():
        try:
            provider = _create_provider_for_type(provider_type, settings)
        except Exception as e:
            results.append((FAIL, f"{provider_type}: {e}"))
            continue
        try:
            offered = set(await asyncio.wait_for(provider.list_models(), 15))
        except Exception as e:
            results.append((FAIL, f"{provider_type}: can't reach the provider ({e})"))
            continue
        finally:
            await provider.cleanup()
        for name in names:
            if name in offered:
                results.append((OK, f"{provider_type}/{name} is available"))
            else:
                results.append(
                    (FAIL, f"{provider_type}/{name}: the provider has no such model")
                )
    return results


def check_claude_code() -> list[tuple[str, str]]:
    if not shutil.which("claude"):
        return [(FAIL, "Claude Code not found: https://docs.claude.com/claude-code")]
    version = subprocess.run(
        ["claude", "--version"], capture_output=True, text=True, timeout=30
    ).stdout.strip()
    return [(OK, f"Claude Code {version}")]


def check_proxy(settings) -> list[tuple[str, str]]:
    url = f"http://127.0.0.1:{settings.port}/health"
    try:
        httpx.get(url, timeout=2).raise_for_status()
        return [(OK, f"proxy is running on port {settings.port}")]
    except Exception:
        return [
            (
                WARN,
                f"proxy is not running: uv run uvicorn server:app --port {settings.port}",
            )
        ]


def check_security(settings) -> list[tuple[str, str]]:
    results = []
    if (
        settings.host not in ("127.0.0.1", "localhost")
        and not settings.proxy_auth_token
    ):
        results.append(
            (
                FAIL,
                f"HOST={settings.host} without PROXY_AUTH_TOKEN: anyone can use your keys",
            )
        )
    if (
        settings.messaging_platform == "telegram"
        and settings.telegram_bot_token
        and not settings.allowed_telegram_user_id
    ):
        results.append(
            (WARN, "Telegram bot has no ALLOWED_TELEGRAM_USER_ID: it ignores everyone")
        )
    return results or [(OK, "no security issues found")]


def main() -> int:
    results, settings = check_settings()
    if settings is not None:
        results += asyncio.run(check_providers(settings))
        results += (
            check_claude_code() + check_proxy(settings) + check_security(settings)
        )
    for status, message in results:
        print(f" {status} {message}")
    failed = sum(status == FAIL for status, _ in results)
    print(f"\n{failed} problem(s) found." if failed else "\nAll good.")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
