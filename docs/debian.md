# Pending Debian package

Status: draft source only. Build and installation testing are paused awaiting the server's Ubuntu
version and architecture. No installable artifact is claimed. Target assumptions currently are
Ubuntu 24.04, amd64 and CPython 3.12; these will be adjusted after the user supplies details.

Intended layout:

- Root-owned runtime: `/opt/clifford/venv`; package files and migrations under `/usr/lib/clifford`.
- Root-private configuration: `/etc/clifford/clifford.env`; generated once and preserved on upgrades.
- Persistent conversations/files/models: `/var/lib/clifford`; never purged automatically.
- Private backend socket: `/run/clifford/api.sock`; no backend TCP port in the Debian service.
- Caddy site: `clifford.parsabe.com`; browser assets bundled from `web-interface`.

The installer draft includes hash-checked Python wheels, service/user creation and Caddy configuration.
Ollama/Gemma installation and offline speech-model download remain separate. Caddy site activation
will be explicit after DNS points to the server and ports 80/443 are reachable. The domain has not
been provisioned and SSL is not live. Existing Caddy sites must remain intact.

The planned administrator commands are `sudo clifford status`, `sudo clifford token`,
`sudo clifford download-voice`, and `sudo clifford enable-site`. They are draft source, not a tested
installed CLI. Do not run package maintainer scripts directly on a server.
