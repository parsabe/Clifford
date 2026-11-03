from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient

from clifford.api import create_app
from clifford.config import Settings
from clifford.providers.llm import Chunk


class FixtureProvider:
    """Deterministic test double; never installed as a runtime provider."""

    def __init__(self):
        self.calls = []

    async def stream(self, messages, system):
        self.calls.append((messages, system))
        yield Chunk(text="Hello ")
        yield Chunk(text="from CLIFFORD.")
        yield Chunk(usage={"output_tokens": 4})


@pytest.fixture
def configured(tmp_path, monkeypatch):
    url = f"sqlite:///{tmp_path}/test.db"
    monkeypatch.setenv("DATABASE_URL", url)
    cfg = Config(str(Path(__file__).parents[1] / "alembic.ini"))
    cfg.set_main_option("script_location", str(Path(__file__).parents[1] / "migrations"))
    command.upgrade(cfg, "head")
    settings = Settings(
        _env_file=None,
        database_url=url,
        files_root=str(tmp_path / "files"),
        requests_per_minute=1000,
    )
    provider = FixtureProvider()
    return settings, provider


@pytest.fixture
def client(configured):
    settings, provider = configured
    with TestClient(socket_app(create_app(settings, provider))) as client:
        yield client


class SocketTransport:
    """ASGI test fixture only; real Unix/TCP transport is verified separately."""

    def __init__(self, app, path):
        self.app, self.path = app, path

    async def __call__(self, scope, receive, send):
        if scope["type"] in {"http", "websocket"}:
            scope = dict(scope, client=None, server=(self.path, None))
        await self.app(scope, receive, send)


def socket_app(app):
    app.add_middleware(SocketTransport, path="/run/clifford/api.sock")
    return app
