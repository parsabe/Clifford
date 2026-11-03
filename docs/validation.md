# Validation for the local-model revision

- 42 Python tests passed against deterministic HTTP/transcription fixtures and real temporary SQLite
  databases/files. They cover no-key Ollama NDJSON, retries, incomplete/error responses, no retry after
  partial output, transcription adaptation, missing speech model, MCP allowlists/schemas/approvals,
  authentication, memory, persistence, streaming, cancellation and tool boundaries.
- Five Node tests passed for a complete wake-prefixed sentence, wake-only expiry, replacement after
  interruption, continuous PCM16 resampling, and automatic speech-queue cancellation.
- Ruff lint/formatting, JavaScript module syntax and Alembic schema checks are part of final validation.

Actual Gemma 3 12B inference and actual microphone recognition are not verified here. The official
Ollama manifest and official Vosk model host both returned explicit HTTP 403 proxy denials in this
cloud instance. No verification was disabled or network restriction bypassed. The updated environment
draft adds the requested download hostnames, but saving a draft does not apply it to the running
instance. Browser speech output also depends on installed local OS voices. Test hardware acoustics
and echo cancellation before relying on interruption.

The earlier 35-test report described a different provider configuration. The current source removes
those paid-provider SDKs and replaces their tests with local Ollama/Vosk coverage. Starlette emits
an HTTPX test-client migration warning; the Python tests otherwise pass.

Final current-instance checks:

- A real temporary MCP server passed discovery, allowed-tool registration, approval, action,
  read-back verification and disconnect through the official SDK transport. This verifies the
  protocol, not access to a real account on a third-party platform.
- Chromium passed the full wake-prefixed sentence, automatic speech, energy-triggered interruption,
  replacement sentence without another wake, microphone release, and mobile layout checks using
  explicitly synthetic transcript/device fixtures. No JavaScript errors occurred.
- The real renamed backend returned correct identity/wake metadata and calculator result 8.
- `scripts/check_local.py` correctly failed readiness: Ollama unreachable, Gemma absent, Vosk absent.
  This is an unresolved deployment prerequisite, not a passing live inference test.
- Database upgrade/schema check, Ruff, module syntax checks and the frozen dependency installation
  succeeded. The model download step is not verified successful under the current cloud network policy.

The draft API retained obsolete optional provider-key requirements and re-added their domains
(api.anthropic.com, api.openai.com, api.fish.audio). They have no bound values and are unused by the
application. Delete these three requirements and their obsolete custom domains in environment
settings; the available draft tool supports addition but not deletion of secret requirements.
The new requested download domains are ollama.com, registry.ollama.ai, and alphacephei.com.


## Separate branch validation

After splitting the source, the kernel passed 44 Python tests, including new headless startup and
external web-root checks. The web-interface branch passed its five Node voice tests and JavaScript
syntax checks. Linux packaging drafts passed lint, Python compilation and maintainer-shell syntax
checks only; no .deb was built or installation-tested. Android and Windows are reserved branches.


## Laravel revision

Kernel voice-ticket changes pass 46 Python tests. The PHP 8.3 Laravel application passes 11 feature
tests with 59 assertions, five Node voice-state tests, Composer/platform checks, Pint and optimization.
Actual local HTTP/browser checks cover login, CSRF enforcement, SSE, ticket format, automatic speech,
synthetic interruption, mic release, mobile layout and logout. A representative aaPanel Nginx config
passed syntax validation. Upstream kernel/audio fixtures are explicitly synthetic: real target
inference, microphone acoustics, DNS, certificate issuance and aaPanel deployment are not claimed.
Details: web-interface branch deploy/VALIDATION.md.
