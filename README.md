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

This kernel starts headless. To attach the browser client without merging branches:

```sh
# Run beside the kernel checkout, not inside it.
git clone --branch web-interface --single-branch https://github.com/parsabe/Clifford.git clifford-web
```

Set `WEB_ROOT` in the kernel's private `.env` to the absolute path of `clifford-web/web`, then restart.
The kernel serves those external static files at `/console/`; REST/SSE/WebSocket APIs remain independent.
The local development script uses loopback port 8000. The pending Debian service uses a private Unix
socket; packaging lives only on `linux-source` and is paused pending server OS/architecture details.

## Validation and status

Run `.venv/bin/pytest -q`, `.venv/bin/ruff check .`, `.venv/bin/ruff format --check .`, and
`.venv/bin/alembic check`. The browser voice tests live on `web-interface`.
Gemma inference and physical microphone/echo performance still require verification on the target
hardware. No email, native phone/watch app or unattended scheduler is configured.

[Documentation](https://github.com/parsabe/Clifford/tree/documentation) ·
[Web interface](https://github.com/parsabe/Clifford/tree/web-interface) ·
[Linux packaging](https://github.com/parsabe/Clifford/tree/linux-source) ·
[Branch index](https://github.com/parsabe/Clifford/tree/master)
