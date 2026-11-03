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
        clifford_auth_secret="x" * 40,
        files_root=str(tmp_path / "files"),
        requests_per_minute=1000,
    )
    provider = FixtureProvider()
    return settings, provider


@pytest.fixture
def client(configured):
    settings, provider = configured
    with TestClient(create_app(settings, provider)) as client:
        client.headers["Authorization"] = "Bearer " + "x" * 40
        yield client
