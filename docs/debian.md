# Debian package work remains paused

No .deb is ready or published. The target Ubuntu version/architecture have not been supplied,
and the package must be redesigned for the current Laravel/aaPanel/private-socket layout.
The builder explicitly refuses to create a stale installer until that work resumes.

Shared kernel-secret generation and the old token CLI are removed. Legacy direct-kernel Caddy
publication is disabled. Do not use the old Docker/Caddy examples as current deployment instructions.

For the working source path now, use the kernel branch scripts/install-service.sh and web-interface
branch deploy/README.md. The kernel uses /run/clifford/api.sock, and aaPanel handles the website,
site password access and HTTPS. There is no custom Laravel web-password hash or backend token field.
The source helper is not a .deb and has not been installed on the user's machine by this session.
