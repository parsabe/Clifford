# Kernel and browser API contracts

The kernel is private Unix-socket HTTP, not a public TCP API. The server identity is the configured
owner and transport access is restricted by socket-directory permissions. There is no persistent
backend bearer token. The supplied startup/service commands disable proxy header rewriting.
Requests arriving over TCP fail with 403 even with forged forwarding or Authorization headers.

## Public website

Laravel serves the browser behind aaPanel/Nginx Password Access. It trusts only configured FastCGI
server parameters for the authenticated site user, never client-supplied headers. Production requests
without the protection marker/user are rejected. There is no custom Laravel login/password route.
Local development at a loopback address with APP_ENV=local is supported explicitly.

- GET /api/providers: selected non-secret assistant/model metadata.
- POST /api/chat/stream: validated text/session/mode input; streamed SSE from the private kernel.
- POST /api/voice/ticket: automatic one-use voice ticket, expires in 30 seconds.

POSTs require Laravel's session/CSRF protection. The browser keeps no persistent backend credential.
PHP cURL uses CLIFFORD_SOCKET_PATH for both JSON and streamed responses, with no TCP fallback.
The only public kernel proxy is the voice-only WebSocket location and it requires a minted ticket.

## Private kernel routes

| Route | Contract |
| --- | --- |
| GET /v1/health | Process/database health |
| GET /v1/providers, /v1/providers/check | Metadata and actual Ollama/model presence |
| POST /v1/chat, /v1/chat/stream | Conversation response or SSE |
| GET /v1/sessions, /v1/sessions/{id} | Completed turns |
| GET/POST /v1/memory, PUT/DELETE /v1/memory/{id} | Explicit owner memory CRUD |
| GET /v1/tools, POST /v1/tools/execute | Validated, permission-aware tools |
| GET /v1/approvals, POST /v1/approvals/{id}/decision | Inspect/decide exact stored actions |
| GET/POST /v1/tasks, GET /v1/tasks/{id} | Typed persisted plans/progress |
| POST /v1/tasks/{id}/run, /cancel | Explicit execution/cancellation |
| POST /v1/plans/propose | Validated model-generated plan; no automatic execution |
| GET /v1/platforms, POST /v1/platforms/{name}/connect, /disconnect | Operator-selected MCP grants |
| POST /v1/voice/tickets | One-use, voice-only ticket |
| WS /v1/realtime | Private-socket text chat/cancellation; no credential frame |
| WS /v1/voice/listen | Ticket-authenticated PCM transcription |

Chat events carry type, id, timestamp, session_id, correlation_id and payload. Emitted types include
session.started, message.received, assistant.delta, assistant.completed and error. An HTTP 200 stream
is not a completion receipt: require assistant.completed and handle error. Abort requests to cancel;
a disconnect racing with commit may still leave a completed pair, so inspect session history before
retrying. Last-Event-ID replay is not implemented.

## Voice

The browser POSTs to Laravel for a ticket, then opens /clifford-voice on the HTTPS site's WSS origin.
Its first JSON frame is {"ticket":"..."}; never put credentials in the URL. Nginx proxies that path
to /v1/voice/listen over the private socket. The ticket is one-use, expires in 30 seconds and does
not grant general API access. Ticket state is process-local, so use one kernel worker.

Wait for audio.ready, then send mono signed 16-bit little-endian PCM at 16kHz, even-sized binary frames
up to 16,000 bytes. Do not send compressed MediaRecorder WebM/WAV headers. audio.transcript events
contain text and final. Raw audio and unused partials are not persisted. Wake gating preserves a
complete Clifford-prefixed sentence; wake-only arms the next sentence for 15 seconds. Client speech
output uses installed device voices, and mic energy can interrupt playback/generation. Initial mic
permission and real acoustic testing are necessary. Headphones improve echo isolation.

Native phone/watch clients are not implemented. Future clients must use an appropriate protected
web gateway; the former direct TCP/bearer kernel protocol is intentionally no longer exposed.
