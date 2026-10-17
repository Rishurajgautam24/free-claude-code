import asyncio
import os
import sys

import pytest

from cli.session import CLISession

FAKE_CLAUDE = f"""#!{sys.executable}
import sys
sys.stderr.write("w" * 5_000_000)  # far more than a pipe/stream buffer holds
sys.stderr.flush()
print('{{"type": "result", "session_id": "s1", "result": "done"}}', flush=True)
"""


@pytest.mark.asyncio
async def test_large_stderr_does_not_deadlock(tmp_path, monkeypatch):
    fake = tmp_path / "claude"
    fake.write_text(FAKE_CLAUDE)
    fake.chmod(0o755)
    monkeypatch.setenv("PATH", f"{tmp_path}{os.pathsep}{os.environ['PATH']}")

    session = CLISession(str(tmp_path), "http://127.0.0.1:1/v1")
    try:
        events = await asyncio.wait_for(_collect(session.start_task("hi")), timeout=20)
    finally:
        await session.stop()

    assert events[-1]["type"] == "exit"
    assert events[-1]["code"] == 0
    assert len(events[-1]["stderr"]) == 5_000_000


async def _collect(stream):
    return [event async for event in stream]
