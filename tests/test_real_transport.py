import os
import socket
import subprocess
import sys
import time

import httpx


def test_actual_unix_socket_and_tcp_boundary(configured, tmp_path):
    settings, _ = configured
    path = str(tmp_path / "kernel.sock")
    environment = dict(
        os.environ,
        DATABASE_URL=settings.database_url,
        CLIFFORD_SOCKET_PATH=path,
        FILES_ROOT=str(tmp_path / "files"),
    )
    from clifford.persistence import Store, User

    store = Store(settings.database_url)
    with store.db() as db:
        db.add(User(id="owner"))
    store.engine.dispose()
    processes = []
    with socket.socket() as probe:
        probe.bind(("127.0.0.1", 0))
        port = probe.getsockname()[1]
    try:
        for address in [["--uds", path], ["--host", "127.0.0.1", "--port", str(port)]]:
            process = subprocess.Popen(
                [
                    sys.executable,
                    "-m",
                    "uvicorn",
                    "clifford.api:app",
                    *address,
                    "--no-proxy-headers",
                    "--no-access-log",
                ],
                env=environment,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            processes.append(process)
        with httpx.Client(
            transport=httpx.HTTPTransport(uds=path), base_url="http://localhost", timeout=2
        ) as private:
            for _ in range(100):
                try:
                    response = private.get("/v1/health")
                    break
                except httpx.TransportError:
                    time.sleep(0.05)
            else:
                raise AssertionError("Unix socket failed to start")
            assert response.status_code == 200
            assert private.get("/v1/tools").status_code == 200
            assert private.post("/v1/voice/tickets").json()["expires_in"] == 30
        for _ in range(100):
            try:
                response = httpx.get(
                    f"http://127.0.0.1:{port}/v1/tools",
                    timeout=2,
                    headers={"X-Forwarded-For": "127.0.0.1", "Authorization": "Bearer arbitrary"},
                )
                break
            except httpx.TransportError:
                time.sleep(0.05)
        else:
            raise AssertionError("TCP transport test server failed to start")
        assert response.status_code == 403
        assert response.json()["error"]["code"] == "private_socket_required"
    finally:
        for process in processes:
            process.terminate()
            process.wait(timeout=10)
