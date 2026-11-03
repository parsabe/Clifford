# Connecting platform types

Clifford supports multiple MCP Streamable HTTP servers through the official MCP Python SDK. An MCP
server is the platform-specific bridge (notes, files, project management, calendar, etc.). Configure
only bridges you trust and have deliberately authorized. No email bridge is configured.

Set `PLATFORM_SERVERS` in the server's `.env` to a JSON array, for example:

```dotenv
PLATFORM_SERVERS=[{"name":"notes","url":"http://127.0.0.1:9001/mcp","allowed_tools":["search_notes","create_note"],"read_only_tools":["search_notes"]},{"name":"projects","url":"https://your-trusted-bridge.example/mcp","allowed_tools":["list_projects"],"read_only_tools":["list_projects"]}]
```

These are illustrative bridges/tool names, not services included with this repository. Install and
authorize your real MCP servers, then replace these values with their actual schemas/URLs.
Restart Clifford, call authenticated `GET /v1/platforms`, and explicitly POST
`/v1/platforms/notes/connect`. Inspect GET `/v1/tools` for the discovered schema. Only `allowed_tools`
are registered, with names such as `platform.notes.search_notes`. Only operator-listed
`read_only_tools` run without a separate approval. Other registered tools require an action-specific
approval through the existing approval API. Disconnect removes tools and denies pending approvals.

Remote bridges require HTTPS. Loopback HTTP bridges are supported. URLs containing embedded
credentials, fragments or query secrets are rejected. Tool schemas containing external references
are rejected. Tool output is untrusted content, not a source of authorization.

This connector path works with authenticated bridges that already manage their platform sessions;
it does not provide a universal OAuth setup wizard or automatically log into every website. A remote
bridge requiring a token/OAuth flow cannot be used until a suitable supported auth bridge is set up.
The user must grant each real account scope. In this cloud environment, the bridge hostname must also
be permitted in network settings. OAuth credentials for a chosen platform are separate from model
API keys; Gemma/Vosk/device speech require no paid-provider keys.
