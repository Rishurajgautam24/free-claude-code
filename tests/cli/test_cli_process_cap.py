import asyncio
import os
import sys

import pytest

from cli.manager import CLISessionManager

FAKE_CLAUDE = f"""#!{sys.executable}
import os, time
log = os.environ["FAKE_CLAUDE_LOG"]
with open(log, "a") as f:
    f.write(f"start {{time.monotonic()}}\\n")
time.sleep(0.4)
with open(log, "a") as f:
    f.write(f"end {{time.monotonic()}}\\n")
print('{{"type": "result", "session_id": "s{{os.getpid()}}", "result": "done"}}', flush=True)
"""


def _max_overlap(log_path):
    events = []
    for line in log_path.read_text().splitlines():
        kind, t = line.split()
        events.append((float(t), 1 if kind == "start" else -1))
    running = peak = 0
    for _, delta in sorted(events):
        running += delta
        peak = max(peak, running)
    return peak


@pytest.mark.asyncio
async def test_concurrent_tasks_wait_for_a_free_process_slot(tmp_path, monkeypatch):
    fake = tmp_path / "claude"
    fake.write_text(FAKE_CLAUDE)
    fake.chmod(0o755)
    log = tmp_path / "runs.log"
    monkeypatch.setenv("PATH", f"{tmp_path}{os.pathsep}{os.environ['PATH']}")
    monkeypatch.setenv("FAKE_CLAUDE_LOG", str(log))

    manager = CLISessionManager(
        str(tmp_path), "http://127.0.0.1:1/v1", max_concurrent=2
    )

    async def run_one():
        session, _, _ = await manager.get_or_create_session()
        return [e async for e in session.start_task("hi")]

    results = await asyncio.wait_for(
        asyncio.gather(*(run_one() for _ in range(4))), timeout=20
    )

    assert all(events[-1]["type"] == "exit" for events in results)
    assert _max_overlap(log) == 2
