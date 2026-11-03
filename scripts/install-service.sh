#!/bin/sh
# Install the source kernel service; does not build the paused .deb or alter model downloads.
set -eu
[ "$(id -u)" -eq 0 ] || { echo 'Run with sudo.' >&2; exit 1; }
web_user="${1:-www}"
id "$web_user" >/dev/null
kernel_root="$(CDPATH= cd -- "$(dirname "$0")/.." && pwd)"
case "$kernel_root" in *[!A-Za-z0-9_./-]*) echo 'Use a kernel path without spaces or shell metacharacters.' >&2; exit 1;; esac
case "$kernel_root" in /root/*|/home/*) echo 'Install the kernel under /opt; the service protects home directories.' >&2; exit 1;; esac
[ -x "$kernel_root/.venv/bin/python" ] || { echo 'Install kernel Python dependencies first.' >&2; exit 1; }
python_location="$(readlink -f "$kernel_root/.venv/bin/python")"
case "$python_location" in /root/*|/home/*) echo 'Recreate the venv with a system or /opt managed Python runtime.' >&2; exit 1;; esac
getent group clifford-web >/dev/null || groupadd --system clifford-web
getent group clifford >/dev/null || groupadd --system clifford
id clifford >/dev/null 2>&1 || useradd --system --gid clifford --no-create-home --home-dir /var/lib/clifford --shell /usr/sbin/nologin clifford
usermod -a -G clifford-web "$web_user"
cd "$kernel_root"
.venv/bin/python scripts/init_local.py
chown root:clifford .env
chmod 0640 .env
install -d -o clifford -g clifford -m 0700 data
# Preserve existing project data while allowing its dedicated service owner to use it.
chown -R clifford:clifford data
if ! runuser -u clifford -- .venv/bin/python -c 'import clifford' >/dev/null 2>&1; then
    echo 'Service account cannot run this Python environment. Install the kernel outside private home directories, with a service-readable Python runtime.' >&2
    exit 1
fi
cat > /etc/systemd/system/clifford.service <<UNIT
[Unit]
Description=Clifford private Unix-socket kernel
After=network.target ollama.service
[Service]
Type=simple
User=clifford
Group=clifford-web
SupplementaryGroups=clifford
WorkingDirectory=$kernel_root
Environment=CLIFFORD_SOCKET_PATH=/run/clifford/api.sock
Environment=PYTHONDONTWRITEBYTECODE=1
RuntimeDirectory=clifford
RuntimeDirectoryMode=0750
UMask=0077
ExecStartPre=$kernel_root/.venv/bin/python -m alembic upgrade head
ExecStart=$kernel_root/.venv/bin/python -m uvicorn clifford.api:app --uds /run/clifford/api.sock --workers 1 --ws-max-size 128000 --no-proxy-headers --no-access-log
Restart=on-failure
RestartSec=5
NoNewPrivileges=true
PrivateTmp=true
ProtectHome=true
ProtectSystem=strict
ReadWritePaths=$kernel_root/data /run/clifford
[Install]
WantedBy=multi-user.target
UNIT
systemctl daemon-reload
systemctl enable --now clifford.service
systemctl restart clifford.service
echo 'Kernel service installed. Restart the site PHP-FPM and Nginx in aaPanel to apply the socket group.'
echo 'Configure aaPanel site password access using the supplied web-branch guide.'
