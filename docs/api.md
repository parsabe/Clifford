# One backend, multiple clients

All data endpoints require `Authorization: Bearer <your backend token>`. `/v1/health`, contract
metadata and static client files are public, but contain no user data. Model API keys do not exist.
Use HTTPS/WSS outside localhost. Store tokens in an OS keychain for native clients; the reference
browser holds its token only in memory. Never put a token in a URL or vendor key in client code.

| Route | Contract |
| --- | --- |
| POST `/v1/chat` | `{text, session_id?, mode?}` → session ID and event list |
| POST `/v1/chat/stream` | Same input → SSE text/events |
| GET `/v1/providers` | Assistant/wake names, configured model and speech availability |
| GET `/v1/providers/check` | Live Ollama reachability and selected model presence |
| GET `/v1/sessions`, `/v1/sessions/{id}` | Conversation continuity across devices |
| GET/POST `/v1/memory`, PUT/DELETE `/v1/memory/{id}` | Explicit memory management |
| GET `/v1/tools`, POST `/v1/tools/execute` | Schemas and bounded, permission-aware execution |
| GET `/v1/approvals`, POST `/v1/approvals/{id}/decision` | Inspect and decide exact stored actions |
| GET/POST `/v1/tasks`, GET `/v1/tasks/{id}` | Durable typed plans/progress |
| POST `/v1/tasks/{id}/run`, `/cancel` | Explicit execution/cancellation |
| POST `/v1/plans/propose` | Gemma-generated plan, validated before storage; no execution |
| GET `/v1/platforms` | Operator-configured MCP platform status |
| POST `/v1/platforms/{name}/connect`, `/disconnect` | Discover explicitly allowed tools or revoke them |
| WS `/v1/realtime` | Text streaming and cancellation |
| WS `/v1/voice/listen` | Offline streaming transcription from mono PCM16 audio |

Chat events include `type`, `id`, `timestamp`, `session_id`, `correlation_id` and structured `payload`.
Emitted types include `session.started`, `message.received`, `assistant.delta`, `assistant.completed`,
`error`, and WebSocket control `task.cancelled`. An HTTP 200 stream is not a success receipt: require
`assistant.completed`. The session ID is shared across desktop/phone/watch clients as needed.
The server persists completed turns. Abort HTTP or send `{"type":"cancel"}` on the text socket to
cancel generation. A disconnect racing with a final commit can still leave a completed pair; check
session history before retrying. SSE replay/Last-Event-ID resumption is not implemented.

## Voice protocol

1. Open WSS `/v1/voice/listen` and send `{"token":"<backend token>"}` as the first JSON frame
   within 10 seconds. Authentication is not placed in the URL.
2. Wait for `audio.ready`. Its payload specifies 16,000Hz, one channel, signed 16-bit little-endian PCM.
3. Send binary PCM frames (even byte length, at most 16,000 bytes each). Do not send WAV headers,
   compressed audio, browser MediaRecorder WebM, or floating point data to this socket.
4. Receive `audio.transcript` events with `{text, final}`. Partial results are informational; only
   final results should submit a completed turn. `speech_model_not_installed` is a real setup error.
5. Stop capture and close the socket when disabled. Raw audio and unused partials are not persisted.

The client owns wake gating and playback cancellation. The supplied `WakeGate` preserves a sentence
beginning with “Clifford”, and arms the next sentence after a wake-only utterance. Mic energy during
playback cancels speech and text before the final replacement transcript arrives. Automatic speech
uses local device voices; no text is sent to an external TTS vendor. A native phone/watch client can
implement this same lifecycle with platform audio APIs and speech synthesis. No particular watch
browser or background-microphone capability is assumed.

The first reference-client microphone permission and audio initialization require a user gesture.
That is a browser/OS permission rule, not a limitation that changing the model or cloud sandbox removes.
A native app would also need microphone permission and platform-specific background entitlements.
