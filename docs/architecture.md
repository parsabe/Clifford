# Architecture and persistence

`kernel` contains the headless Python AI service. `web-interface` contains the separate Laravel 13
application and browser voice client. Branches are not merged. Gemma/Vosk stay on the server;
aaPanel hosts Laravel's public/ directory and handles HTTPS/site access.

## Access boundary

The kernel accepts only its configured private Unix socket, with proxy-header rewriting disabled.
Filesystem ownership and the clifford-web service group restrict access. TCP requests fail closed.
No persistent kernel secret, backend token, custom web-password hash or user timeout field is used.

Laravel uses cURL over that socket, with bounded internal request/stream timeouts and no TCP fallback.
aaPanel/Nginx site Password Access authenticates the public site. Trusted FastCGI marker/user fields
assert that perimeter; client headers cannot supply them. They must only be configured after site-wide
access protection is active. Laravel session/CSRF protection remains, using its automatically generated
standard app encryption key. There is no separate custom Laravel login page or password prompt.

Voice uses automatically minted, short-lived, single-use tickets for the Nginx voice-only socket proxy.
Tickets are not settings users fill in and cannot grant general API access. Keep one kernel worker.

## Components

The kernel API handles private HTTP/SSE/WebSocket transport and one configured owner. Engine code
manages recent completed turns, explicit memory, typed specialist plan proposals and dependency
execution. Ollama adapters use gemma3:12b with bounded context/retries and no cloud-model fallback.
The offline Vosk adapter caches a model and creates independent recognizers for voice sessions.
The web client implements wake gating, PCM16 resampling, local device speech and interruption.

The tool registry enforces schema validation, configured roots/permissions and action-specific
approval. MCP tools are registered only from operator-selected bridges and tool allowlists. Server
annotations never grant privileges. Disconnect removes tools and revokes outstanding approvals.
No email bridge or unrestricted shell/desktop tool is connected.

## Memory and recovery

SQLAlchemy/Alembic persist owner identities, sessions, completed turn pairs, explicit memories,
plans, approvals, execution receipts and audit identifiers. Data can contain personal information;
protect disk/backups and apply a retention policy. Credentials are not ordinary database fields.

Memory records support working/episodic/semantic/procedural categories, scope, provenance,
confidence, timestamps and expiry. Writes are explicit, not automatic transcript promotion.
Retrieval currently ranks lexical overlap among at most 500 recent owner records; no embedding
index or automatic summarizer is claimed. Recent chat is bounded by count and a character budget.

Plans contain at most 12 topologically ordered steps, stop on failure/approval, and resume explicitly.
Completed steps and approvals persist across restarts. Approval claiming prevents replay; a crash
can still leave an unknown outcome requiring inspection. Cancellation revokes pending approvals
but cannot undo a committed action. There is no unattended scheduler or distributed worker system.
Model output and retrieved content cannot approve or execute tools by themselves.
