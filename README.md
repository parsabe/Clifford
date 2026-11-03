# Clifford private kernel

Gemma 3 12B/Ollama, Vosk speech recognition, memory, tools, approvals and MCP connectors live here.
The assistant and wake phrase are Clifford. The web-interface branch is a separate Laravel app.

**No shared access secret is used.** The kernel accepts requests only over its configured private
Unix socket; TCP requests are rejected even if a caller forges forwarding/Authorization headers.
Run it with the supplied commands, which disable proxy-header rewriting and protect the socket directory.

## Source installation

```sh
git clone --branch kernel --single-branch https://github.com/parsabe/Clifford.git /opt/clifford/kernel
cd /opt/clifford/kernel
uv sync --frozen --extra dev
.venv/bin/python scripts/init_local.py
.venv/bin/alembic upgrade head
```

Use Python 3.12+ available to the service outside private home directories. If uv downloads Python,
set UV_PYTHON_INSTALL_DIR=/opt/clifford/python before provisioning. Install local Ollama and pull
gemma3:12b separately, then download Vosk with scripts/download_voice_model.py and run
scripts/check_local.py to verify actual inference. Model files are not bundled or faked.

For aaPanel, install the source service as root:

```sh
sudo ./scripts/install-service.sh www
```

Replace www if the site's actual PHP-FPM/Nginx account differs. The helper grants the socket group,
preserves project data, installs systemd service and starts the kernel. Restart PHP-FPM and Nginx
after group changes. It is not the paused .deb build. Custom data paths require matching service
ReadWritePaths and owner permissions. The service's default socket is /run/clifford/api.sock, inside
a 0750 runtime directory owned by Clifford and the clifford-web group.

For manual local development, choose a private directory:

```sh
CLIFFORD_SOCKET_PATH="$PWD/data/run/api.sock" ./scripts/start.sh
```

The start script refuses a socket directory accessible to other users. It never starts a TCP listener.
Laravel uses PHP cURL over this socket. aaPanel site Password Access protects the public web app;
its custom backend-token and web-password-hash fields have been removed. See the web branch guide.
The kernel is headless; WEB_ROOT is optional for other static clients and is left empty for Laravel.

Voice uses automatically minted, 30-second single-use tickets for the Nginx-proxied socket endpoint.
They are not user configuration or general API credentials. Keep one kernel worker; pending tickets
are invalidated by restart. The text WebSocket is private-socket only and has no credential frame.

Validation: 47 Python tests pass, including actual Unix and rejected TCP transports. Run
.venv/bin/pytest -q and .venv/bin/ruff check . . Physical microphone/echo and real target-server Gemma
performance remain unverified here. No email or unattended scheduling is configured.

[Laravel web / aaPanel](https://github.com/parsabe/Clifford/tree/web-interface) ·
[Documentation](https://github.com/parsabe/Clifford/tree/documentation) ·
[Branch index](https://github.com/parsabe/Clifford/tree/master)
