from types import SimpleNamespace

import pytest

from clifford.config import PlatformServer
from clifford.platforms import Platforms
from clifford.tools import Registry, ToolError


@pytest.mark.asyncio
async def test_platform_grants_schema_and_approval(configured, monkeypatch):
    settings, _ = configured
    settings.platform_servers = [
        PlatformServer(
            name="notes",
            url="http://localhost:9999/mcp",
            allowed_tools=["read", "write"],
            read_only_tools=["read"],
        )
    ]
    from clifford.persistence import Store, User

    store = Store(settings.database_url)
    with store.db() as db:
        db.add(User(id="owner"))
    registry = Registry(settings, store)
    platforms = Platforms(settings, registry)
    calls = []

    async def request(name, method, arguments=None):
        calls.append(method)
        if method == "list":
            return SimpleNamespace(
                tools=[
                    SimpleNamespace(
                        name=n,
                        description=n,
                        inputSchema={
                            "type": "object",
                            "properties": {"text": {"type": "string"}},
                            "required": ["text"],
                            "additionalProperties": False,
                        },
                    )
                    for n in ["read", "write", "ungranted"]
                ]
            )
        return SimpleNamespace(
            isError=False, model_dump=lambda **kw: {"content": [{"type": "text", "text": "done"}]}
        )

    monkeypatch.setattr(platforms, "request", request)
    result = await platforms.connect("notes")
    assert len(result["tools_registered"]) == 2
    assert "platform.notes.ungranted" not in registry.tools
    with pytest.raises(ToolError, match="invalid_arguments"):
        registry.validate("platform.notes.read", {"text": 1})
    assert (await registry.execute("owner", "platform.notes.read", {"text": "a"}))[
        "status"
    ] == "completed"
    approval = await registry.execute("owner", "platform.notes.write", {"text": "b"})
    assert "write" not in calls
    assert approval["status"] == "waiting_for_authorization"
    assert (await registry.decision("owner", approval["approval_id"], True))[
        "status"
    ] == "completed"
    platforms.disconnect("notes")
    assert "platform.notes.read" not in registry.tools


def test_remote_platform_requires_tls(configured):
    settings, _ = configured
    settings.platform_servers = [PlatformServer(name="unsafe", url="http://example.com/mcp")]
    with pytest.raises(ToolError, match="platform_requires_https"):
        Platforms(settings, None).server("unsafe")
