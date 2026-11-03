"""Create a private local configuration only when it does not already exist."""

import os
import secrets
from pathlib import Path

path = Path(".env")
if not path.exists():
    contents = (
        Path(".env.example")
        .read_text()
        .replace(
            "CLIFFORD_AUTH_SECRET=\n", "CLIFFORD_AUTH_SECRET=" + secrets.token_urlsafe(32) + "\n"
        )
    )
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, "w") as file:
        file.write(contents)
    print(
        "Created private .env with generated backend authentication. No provider keys configured."
    )
else:
    print("Preserved existing .env.")
