import asyncio

import pytest
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient

from clifford.api import create_app
from clifford.contracts import Chat
from clifford.providers.llm import Chunk


def test_migrations_round_trip(configured):
    cfg = Config("alembic.ini")
    command.downgrade(cfg, "base")
    command.upgrade(cfg, "head")
    command.upgrade(cfg, "head")
    with TestClient(create_app(*configured)) as client:
        assert client.get("/v1/health").status_code == 200


@pytest.mark.asyncio
async def test_chat_cancellation_releases_session(configured):
    settings, _ = configured
    started = asyncio.Event()

    class Slow:
        async def stream(self, messages, system):
            started.set()
            await asyncio.sleep(30)
            yield Chunk(text="Too late")

    app = create_app(settings, Slow())
    async with app.router.lifespan_context(app):
        engine = app.state.engine
        sid = engine.session("owner", None)

        async def consume():
            return [event async for event in engine.chat("owner", Chat(text="Hi"), sid)]

        task = asyncio.create_task(consume())
        await started.wait()
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task
        assert sid not in engine.active_sessions


def test_plan_survives_restart_waiting_approval(client, configured):
    task = client.post(
        "/v1/tasks",
        json={
            "title": "Persist",
            "steps": [
                {
                    "id": "a",
                    "tool": "file.create",
                    "arguments": {"path": "persist.txt", "content": "saved"},
                }
            ],
        },
    ).json()
    tid = task["id"]
    waiting = client.post(f"/v1/tasks/{tid}/run").json()
    assert client.post(f"/v1/tasks/{tid}/run").json()["status"] == "waiting_for_authorization"
    aid = waiting["steps"][0]["result"]["approval_id"]
    with TestClient(create_app(*configured)) as restarted:
        restarted.headers["Authorization"] = "Bearer " + "x" * 40
        assert (
            restarted.post(f"/v1/approvals/{aid}/decision", json={"approve": True}).status_code
            == 200
        )
        assert restarted.post(f"/v1/tasks/{tid}/run").json()["status"] == "completed"
