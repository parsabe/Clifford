# Execution boundaries

The server access token protects your private assistant; it is distinct from a model-vendor API key.
No model/speech API key fields or cloud-model adapters remain. Do not disable backend authentication
when accessing the server from a phone or another network.

Built-ins provide bounded arithmetic, UTC time, and UTF-8 file read/create within FILES_ROOT. Paths
use directory descriptors and O_NOFOLLOW; traversal and symlinks cannot escape the root. File creation
uses O_EXCL and read-back verification; existing files cannot be overwritten. No unrestricted shell
or desktop tool is registered. Email is not configured.

Register a `Tool` with a Pydantic input schema, validated Result output, risk, permission name, handler
and timeout. Optional remote JSON schemas are checked before validation. Async handlers have timeouts;
synchronous built-ins are size-bounded but OS filesystem calls cannot be preempted. Do not add blocking
network calls as synchronous handlers. Cancellation cannot undo an external side effect.

All Level 2+ actions require approval of exact stored arguments. A caller cannot submit its own
`authorized=true`. Atomic claims prevent approval replay; foreign/pending ownership checks are
server-side. Pending approvals do not currently expire automatically, so deny stale requests.
Disconnecting a platform revokes its pending approvals. Unknown outcomes after a crash require
inspection; exactly-once delivery is not promised.

Untrusted memory, documents, model output and MCP results cannot alter server authorization. Prompt
instructions help linguistic behavior, but the architectural boundary is that chat has no execution
or approval authority. Generated plans are validated and do not automatically run. Browser messages
use textContent, not model-generated HTML. Tokens live only in browser memory.

Raw microphone audio/partials are not persisted. Speech recognition runs on your backend server;
recognized commands submitted to chat become persisted user messages. The browser releases its mic
when voice is disabled or the page closes. It does not implement a hidden/background listener.
Use TLS to protect audio and authentication in transit. Echo cancellation is device-dependent;
headphones are recommended for reliable interruption.

The cloud coding sandbox and network proxy are platform infrastructure, separate from these
application permissions. Approved test commands can use local sockets outside the command sandbox.
You do not need to disable a sandbox on your own Ubuntu deployment. Cloud model download hostnames
need environment network settings; a proxy denial is not an Ollama or application bug.
