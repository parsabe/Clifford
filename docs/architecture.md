# Architecture and persistence

`clifford/api.py` on `kernel` handles authenticated transport. `engine.py` handles recent conversation,
explicit memory retrieval, bounded specialist plan proposals and sequential dependency execution.
`providers/llm.py` calls the native Ollama `/api/chat` NDJSON protocol with `gemma3:12b`, a small
configured context window, bounded retries before emitted text, and no cloud fallback.
`providers/speech.py` uses a cached offline Vosk model and separate recognizers per listening socket.
`web/voice.js` on `web-interface` separates wake gating, PCM conversion, local speech output and capture lifecycle.
`platforms.py` uses the official MCP SDK; `tools.py` remains the central schema/approval boundary.

SQLAlchemy models and frozen Alembic migrations store owner identities, sessions, completed turn
pairs, explicit memories, plans, approvals, execution receipts and audit metadata. Token and account
credentials are never database fields. The backend supports one configured owner and one worker.
The owner's name is not inferred from the assistant name. Devices share authenticated state through
the same APIs. Databases/tool results can contain personal content; use disk encryption and backups.

Memory records support category (working/episodic/semantic/procedural), owner, scope, provenance,
confidence, timestamps and expiry. The API supports create/read/update/delete. Chat does not
indiscriminately promote personal information to durable memory. Retrieval is lexical word overlap
among at most 500 recent owner records, not embeddings/vector search. Recent completed message pairs
are bounded by count and a character budget. This budget is approximate, not exact Gemma tokenization.
No summarizer, full paginated export or automatic memory consolidation is claimed.

Plans have at most 12 steps with dependencies referring to earlier steps. They stop on failure or
an approval boundary. Completed steps and pending approvals survive restart. Approval claiming is
atomic and at-most-once; a crash after claiming can leave an unknown outcome that needs inspection,
not an automatic retry. Cancellation revokes pending approvals. A final committed effect cannot be
undone by cancelling afterward. Plans execute explicitly; unattended scheduling is absent.

Model output cannot execute tools or approve actions. MCP tools are registered only after an
operator has configured a server and explicitly connected its allowlisted tools. Disconnect revokes
pending platform approvals. Server-supplied annotations cannot grant read access or bypass approval.
Platform URLs/account bridges require separate configuration; no platform is silently connected.
