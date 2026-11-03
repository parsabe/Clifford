# Clifford kernel

This branch contains the interface-independent backend: Gemma 3 12B/Ollama integration, offline Vosk
speech recognition, sessions, memory, tools, approvals, plans, MCP connectors, migrations and Python tests.
Clifford is the assistant's name and wake phrase, not the owner's name. No paid-provider key is needed.

## Source checkout

```sh
git clone --branch kernel --single-branch https://github.com/parsabe/Clifford.git clifford-kernel
cd clifford-kernel
uv sync --frozen --extra dev
.venv/bin/python scripts/init_local.py
.venv/bin/alembic upgrade head
```

Install Ollama separately, pull `gemma3:12b`, and install the offline speech model with
`.venv/bin/python scripts/download_voice_model.py`. Run `.venv/bin/python scripts/check_local.py`
to verify an actual model response, then start the backend with `./scripts/start.sh`.

This kernel starts headless. The `web-interface` branch is now a **Laravel 13** application for
PHP 8.3+ and aaPanel. Deploy it as a separate checkout with its document root set to `public/`.
Keep this kernel running privately; configure the Laravel app's server-side kernel URL and token.
Leave kernel `WEB_ROOT` empty when using Laravel. Do not point WEB_ROOT at the Laravel project.

Laravel proxies chat using its authenticated owner session and the server-held kernel token.
For voice, authenticated POST `/v1/voice/tickets` issues a 30-second single-use ticket. Only
`/v1/voice/listen` accepts that ticket (first WebSocket JSON frame, key `ticket`); it cannot call
other APIs. The aaPanel Nginx voice-only proxy forwards the browser socket to that endpoint.
Direct native clients can still use the existing token-authenticated voice protocol. Keep one
kernel worker because ticket storage is process-local; restart invalidates pending tickets.

The local development script uses loopback port 8000. The pending Debian service uses a private
Unix socket; packaging lives on `linux-source` and is still paused pending server OS/architecture.

## Validation and status

Run `.venv/bin/pytest -q`, `.venv/bin/ruff check .`, `.venv/bin/ruff format --check .`, and
`.venv/bin/alembic check`. The Laravel feature tests and browser voice tests live on `web-interface`. The kernel suite passes 46 tests including ticket scope, replay and expiry checks.
Gemma inference and physical microphone/echo performance still require verification on the target
hardware. No email, native phone/watch app or unattended scheduler is configured.

[Documentation](https://github.com/parsabe/Clifford/tree/documentation) ·
[Web interface](https://github.com/parsabe/Clifford/tree/web-interface) ·
[Linux packaging](https://github.com/parsabe/Clifford/tree/linux-source) ·
[Branch index](https://github.com/parsabe/Clifford/tree/master)
