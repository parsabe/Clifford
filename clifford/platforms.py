"""Operator-configured MCP connectors, explicit tool grants, no implicit account access."""

import asyncio
from urllib.parse import urlsplit

import jsonschema
from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client
from pydantic import RootModel

from .tools import Tool, ToolError


class Arguments(RootModel[dict]):
    pass


class Platforms:
    def __init__(self, settings, registry):
        self.servers = {server.name: server for server in settings.platform_servers}
        if len(self.servers) != len(settings.platform_servers):
            raise ValueError("duplicate platform names")
        self.registry = registry
        self.connected = set()

    def list(self):
        return [
            {
                "name": s.name,
                "connected": s.name in self.connected,
                "allowed_tools": s.allowed_tools,
                "read_only_tools": s.read_only_tools,
            }
            for s in self.servers.values()
        ]

    def server(self, name):
        if name not in self.servers:
            raise ToolError("platform_not_configured")
        server = self.servers[name]
        parsed = urlsplit(server.url)
        if (
            parsed.scheme not in {"http", "https"}
            or not parsed.hostname
            or parsed.username
            or parsed.password
            or parsed.query
            or parsed.fragment
        ):
            raise ToolError("invalid_platform_url")
        if parsed.scheme != "https" and parsed.hostname not in {"localhost", "127.0.0.1", "::1"}:
            raise ToolError("platform_requires_https")
        return server

    async def request(self, name, method, arguments=None):
        server = self.server(name)
        try:
            async with asyncio.timeout(20):
                async with streamablehttp_client(server.url) as (read, write, _):
                    async with ClientSession(read, write) as session:
                        await session.initialize()
                        if method == "list":
                            return await session.list_tools()
                        return await session.call_tool(method, arguments or {})
        except Exception:
            raise ToolError("platform_unavailable_or_authentication_required") from None

    async def connect(self, name):
        server = self.server(name)
        listed = await self.request(name, "list")
        # Validate everything before altering the registry. Server annotations cannot
        # grant permissions: only operator configuration decides read vs modifying risk.
        pending = []
        for remote in listed.tools:
            if remote.name not in server.allowed_tools:
                continue
            jsonschema.Draft202012Validator.check_schema(remote.inputSchema)

            def check_refs(value):
                if isinstance(value, dict):
                    for key, item in value.items():
                        if key in {"$ref", "$dynamicRef"} and not str(item).startswith("#"):
                            raise ToolError("external_schema_references_not_allowed")
                        check_refs(item)
                elif isinstance(value, list):
                    for item in value:
                        check_refs(item)

            check_refs(remote.inputSchema)

            async def handler(args, tool_name=remote.name):
                result = await self.request(name, tool_name, args.root)
                if result.isError:
                    raise ToolError("platform_tool_failed")
                return {"value": result.model_dump(mode="json")}

            pending.append(
                Tool(
                    name=f"platform.{name}.{remote.name}",
                    description=f"{name}: {remote.description or remote.name}",
                    schema=Arguments,
                    handler=handler,
                    risk=1 if remote.name in server.read_only_tools else 2,
                    permission=f"platform.{name}",
                    timeout=25,
                    json_schema=remote.inputSchema,
                )
            )
        self.disconnect(name)
        for tool in pending:
            self.registry.tools[tool.name] = tool
        self.connected.add(name)
        return {"name": name, "tools_registered": [t.name for t in pending]}

    def disconnect(self, name):
        self.server(name)
        prefix = f"platform.{name}."
        for key in list(self.registry.tools):
            if key.startswith(prefix):
                del self.registry.tools[key]
        from sqlalchemy import select

        from .persistence import Approval

        with self.registry.store.db() as db:
            for approval in db.scalars(select(Approval).where(Approval.status == "pending")):
                if approval.tool.startswith(prefix):
                    approval.status = "denied"
        self.connected.discard(name)
        return {"name": name, "connected": False}
