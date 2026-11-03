# Access, tools and security

The current kernel is reachable only through a filesystem-protected Unix socket. Its supported
startup/service commands disable proxy-header rewriting. TCP requests are rejected; forwarded
headers or old bearer values cannot grant access. Socket directory ownership/group permissions
must restrict local access to the intended services.

The public Laravel site uses aaPanel/Nginx Password Access, not a custom app password/hash. Its
FastCGI protection/user fields are trusted server parameters, never HTTP headers from clients.
Only configure the marker after site-wide protection is active, including the voice location.
Laravel fails closed when that boundary is missing. CSRF remains required. Voice tickets are
short-lived, one-use and voice-only; no persistent backend credential reaches the browser.

Built-ins include bounded arithmetic, UTC time and UTF-8 file read/create within FILES_ROOT. Directory
descriptors and O_NOFOLLOW prevent traversal/symlink escape. Creation is exclusive and read-back
verified; existing targets cannot be overwritten. No unrestricted terminal or desktop tool is enabled.

Tools have typed inputs/outputs, risk, permission, handler and timeout metadata. Async operations
are bounded; synchronous filesystem calls cannot be preempted while in the OS. Network integrations
must not be added as unbounded blocking handlers. Cancellation cannot undo external committed effects.

Level 2+ actions require exact stored-argument approval. Callers cannot submit authorized=true.
Atomic claims reject replay; owner checks isolate records. Approvals have no automatic expiry yet,
so deny stale actions explicitly. Platform disconnect revokes pending platform approvals. Unknown
outcomes after a crash require inspection; exactly-once delivery is not promised.

Memory, documents, model output and MCP results are untrusted data, not permission sources. The
architectural boundary is that chat does not execute or approve actions. Generated plans must pass
registry validation and explicit execution/approval. Browser model text is rendered as textContent.

Raw microphone audio/unused partial transcripts are not persisted. Accepted commands become normal
conversation messages. Disable voice or close the page to stop capture. Headphones improve acoustic
interruption isolation; continuous background listening and native phone/watch apps are not provided.

The cloud command sandbox/proxy are separate from application permissions. Use approved local test
execution where required; do not disable TLS verification or bypass restricted download destinations.
The target aaPanel site's service permissions, TLS and actual model/voice performance need verification.
