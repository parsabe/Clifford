#!/usr/bin/python3
"""Local administrator commands for the Debian installation. No network credentials shipped."""

import argparse
import json
import os
import stat
import subprocess
import tempfile
from pathlib import Path

CONFIG = Path("/etc/clifford/clifford.env")
CADDYFILE = Path("/etc/caddy/Caddyfile")
IMPORT = "import /etc/caddy/conf.d/*.caddy"


def enable_site(path=CADDYFILE, run=subprocess.run):
    if path.is_symlink():
        raise RuntimeError("Caddyfile is a symlink; configure the import manually")
    original = path.read_text() if path.exists() else ""
    # The exact import is idempotent. Other overlapping imports are left alone;
    # Caddy validates the candidate and rejects duplicates before we install it.
    updated = (
        original
        if IMPORT in [line.strip() for line in original.splitlines()]
        else (original.rstrip() + "\n\n# Clifford managed site include\n" + IMPORT + "\n")
    )
    mode = stat.S_IMODE(path.stat().st_mode) if path.exists() else 0o644
    with tempfile.NamedTemporaryFile(
        mode="w", dir=path.parent, prefix=".clifford-", delete=False
    ) as f:
        candidate = Path(f.name)
        f.write(updated)
    try:
        os.chmod(candidate, mode)
        # Keep the original directory for any relative imports in existing sites.
        run(["caddy", "validate", "--config", str(candidate), "--adapter", "caddyfile"], check=True)
        if updated != original:
            if path.exists():
                backup = path.with_name("Caddyfile.before-clifford")
                if not backup.exists():
                    # Atomic exclusive backup; never overwrite a previous operator backup.
                    fd = os.open(backup, os.O_WRONLY | os.O_CREAT | os.O_EXCL, mode)
                    with os.fdopen(fd, "w") as output:
                        output.write(original)
            os.replace(candidate, path)
        run(["systemctl", "daemon-reload"], check=True)
        # Restart is necessary to apply the private socket supplementary group.
        run(["systemctl", "restart", "caddy.service"], check=True)
    finally:
        candidate.unlink(missing_ok=True)


def main():
    parser = argparse.ArgumentParser(description="Manage the installed Clifford service")
    parser.add_argument("command", choices=["status", "download-voice"])
    args = parser.parse_args()
    if os.geteuid() != 0:
        parser.exit(1, "Run this administrator command with sudo.\n")
    if args.command == "download-voice":
        subprocess.run(
            [
                "runuser",
                "-u",
                "clifford",
                "--",
                "/opt/clifford/venv/bin/python",
                "/usr/lib/clifford/scripts/download_voice_model.py",
                "--destination",
                "/var/lib/clifford/models",
            ],
            check=True,
        )
        subprocess.run(["systemctl", "restart", "clifford.service"], check=True)
    else:
        subprocess.run(["systemctl", "--no-pager", "status", "clifford.service"], check=False)
        health = subprocess.run(
            [
                "curl",
                "--fail",
                "--silent",
                "--show-error",
                "--unix-socket",
                "/run/clifford/api.sock",
                "http://localhost/v1/health",
            ],
            text=True,
            capture_output=True,
        )
        if health.returncode:
            parser.exit(1, "Clifford health request failed; inspect journalctl -u clifford.\n")
        print(json.dumps(json.loads(health.stdout)))
        print("Backend uses a private Unix socket; no port 8000 listener is installed.")


if __name__ == "__main__":
    try:
        main()
    except (RuntimeError, OSError, subprocess.CalledProcessError) as exc:
        raise SystemExit(str(exc)) from None
