"""Initialize kernel settings and remove the retired shared-token field."""

import os
from pathlib import Path

path = Path(".env")
if path.is_symlink():
    raise SystemExit("Refusing to replace a symlinked environment file")
if not path.exists():
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, "w") as output:
        output.write(Path(".env.example").read_text())
    print("Created kernel configuration for private Unix-socket access.")
else:
    original = path.read_text()
    updated = (
        "\n".join(
            line for line in original.splitlines() if not line.startswith("CLIFFORD_AUTH_SECRET=")
        )
        + "\n"
    )
    if "CLIFFORD_SOCKET_PATH=" not in updated:
        updated += "CLIFFORD_SOCKET_PATH=/run/clifford/api.sock\n"
    if updated != original:
        path.write_text(updated)
        path.chmod(0o600)
    print("Preserved kernel settings; retired shared-token field removed.")
