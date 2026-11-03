# Clifford

Clifford is the assistant's name, **not the user's name**. Its wake phrase is **“Clifford”**.
This is a working backend and browser reference client. It uses **Gemma 3 12B through local Ollama**,
**offline Vosk** for speech recognition, and **local device voices** for speech output.
There are no paid model/speech API keys, provider SDKs, or cloud-model fallbacks.

## What works, and what is not yet verified

Authenticated text streaming, SQLite sessions/memory, approved tools/plans, local-model protocol,
voice transport/state logic, and configured MCP platform tools have automated coverage.
Actual Gemma inference and real microphone/acoustic interruption have **not** been verified here:
this cloud instance has no model installed, its proxy denies the official model download hosts,
and it has no physical microphone. Do not mistake protocol fixtures for live inference.
See [capabilities](docs/capabilities.md) and [validation](docs/validation.md).

## Install on your Ubuntu server

A 12GB RAM server is tight for Gemma 3 12B. Use Ollama's quantized `gemma3:12b`, close other heavy
services, and start with the included 2,048-token context and 512-token response limit. The download
is roughly 8GB plus runtime/context memory. GPU acceleration is optional, but CPU responses may be
slow. Neither fitting nor real-time speed is guaranteed on an unidentified 12GB server. Check
`free -h`, `lscpu`, and `nvidia-smi` (if installed). Swap may prevent an out-of-memory kill but does not
make inference fast. Do not silently switch to a smaller model.

Install system prerequisites and Ollama using its official installer:

```sh
sudo apt update
sudo apt install -y python3-venv curl ffmpeg
curl -fsSL https://ollama.com/install.sh | sh
ollama pull gemma3:12b
```

The installer normally registers the Ollama service. If it isn't running, start it with
`sudo systemctl start ollama` or run `ollama serve` in another terminal. Keep Ollama's port private.

From the **source directory** (see [getting the code](docs/getting-the-code.md)):

```sh
python3 -m venv .bootstrap
.bootstrap/bin/pip install uv==0.12.23
.bootstrap/bin/uv sync --frozen --extra dev
.venv/bin/python scripts/init_local.py
.venv/bin/python scripts/download_voice_model.py
.venv/bin/alembic upgrade head
.venv/bin/python scripts/check_local.py
./scripts/start.sh
```

The live check must print a real Gemma greeting before local inference is considered ready.
The download script fetches the official English Vosk model over verified HTTPS. It preserves an
existing model and accepts `--sha256` if you have an independently trusted checksum. Download once;
recognition then works offline. It does not send recordings to an outside speech service.

`init_local.py` creates a private `.env` and a random **backend access token**. This protects access
to your own server; it is not a paid-provider API key. Existing `.env` files are preserved. No key
from the pasted request is included. Old optional model-key fields in cloud environment settings
can be removed; they are unused by this code.

## Use voice

Open the reference client at `/console/` on the backend, connect using your backend token, and
choose **Enable voice** once. The browser must receive microphone permission. After that:

- “Clifford, tell me the time” submits the complete sentence after the wake phrase.
- Saying “Clifford” alone arms the next sentence for 15 seconds.
- Replies speak automatically using a **local installed device voice**; no read-aloud tap is needed.
- Speaking over a reply stops queued/current speech and cancels the active text stream. Your next
  recognized sentence replaces the request without another wake phrase.
- Disable voice to release the microphone. Closing the page also stops capture.

This browser client must remain open and enabled. It is not a system-wide always-on background
service or a custom trained wake-word detector. Wake detection follows local transcription, so
accuracy depends on the Vosk model, accent, device, and noise. Barge-in uses sustained mic energy
and browser echo cancellation. Use headphones for reliable isolation; speaker echo/noise can cause
false interruptions. Real acoustic performance must be tested on your hardware.

The browser needs HTTPS on a phone/remote computer (localhost is allowed for desktop development).
One-time permission/interaction cannot be bypassed by a web application. If no local speech voice
is available, install an OS voice and restart the browser. On Ubuntu, the packages
`speech-dispatcher` and `espeak-ng` may be needed; browser support varies. This replaces the prior
Fish voice; its voice identity is no longer used.

## Your server, phone, and future watch client

Run one central backend on your server. Ollama and Vosk stay there. Devices use the versioned REST,
SSE and WebSocket API; they do not need a copy of Gemma. A laptop can instead run the same stack
locally. The service binds to loopback by default; put a TLS reverse proxy in front of it for remote
clients. A sample [Caddy configuration](deploy/Caddyfile) supports streaming and WebSockets.
Replace its example domain with a real domain pointing to your server, install Caddy and permit
HTTPS traffic. Do not publish port 11434 or unauthenticated backend endpoints to the Internet.

The responsive browser console can be used on supported phones. **No native phone or watch app is
included.** A future watchOS client uses the same text/event/audio contracts and its own native
microphone and speech APIs. Browser availability on watchOS is not assumed. See [client contracts](docs/api.md).

## Platform access, without email

No email platform is connected or enabled. The backend has a real MCP connector path for multiple
operator-configured platforms. You select their server URLs and exact allowed tools; read grants
are explicit and modifying tools require action-specific approval. It never acquires account access
merely because you mention a platform. See [platform configuration](docs/platforms.md). Platforms
requiring OAuth need a separately authenticated MCP bridge; this project does not implement universal
OAuth/account login for every service.

## Development

```sh
.venv/bin/pytest -q
node tests/voice.test.mjs
.venv/bin/ruff check .
.venv/bin/ruff format --check .
.venv/bin/alembic check
```

Use one backend worker. The deployment has one configured owner; multiple devices share that
owner's sessions. A public multi-user identity service, unattended scheduling, and native apps are
not implemented. SQLite is the tested persistence target; PostgreSQL is configurable but unverified.
Docker/Compose recipes are provided but untested here. Compose runs Ollama on a private internal
network; after startup pull the model with `docker compose exec ollama ollama pull gemma3:12b` and
install speech with `docker compose exec clifford .venv/bin/python scripts/download_voice_model.py`.

The source is in `clifford/`, tests in `tests/`, migrations in `migrations/`, and scripts in `scripts/`.
OpenAPI is available at `/docs` and `/openapi.json`, with a checked-in export at `docs/openapi.json`.
Download this repository with **Code → Download ZIP** on GitHub, or clone it.
See [getting the code](docs/getting-the-code.md) for download instructions.
