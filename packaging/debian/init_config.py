"""Generate private Debian configuration once; upgrades preserve operator settings."""

import argparse
import os
from pathlib import Path


def initialize(path: Path):
    if path.is_symlink():
        raise RuntimeError("Refusing a symlink for the private configuration")
    if path.exists():
        return False
    content = """# Private kernel transport; no shared backend credential.
CLIFFORD_SOCKET_PATH=/run/clifford/api.sock
CLIFFORD_USER_ID=owner
ASSISTANT_NAME=Clifford
WAKE_PHRASE=Clifford
DATABASE_URL=sqlite:////var/lib/clifford/clifford.db
DEFAULT_LLM_PROVIDER=ollama
DEFAULT_LLM_MODEL=gemma3:12b
OLLAMA_BASE_URL=http://127.0.0.1:11434
PROVIDER_TIMEOUT=180
PROVIDER_RETRIES=1
OLLAMA_NUM_CTX=2048
MAX_OUTPUT_TOKENS=512
CONTEXT_CHAR_BUDGET=4000
VOSK_MODEL_PATH=/var/lib/clifford/models/vosk-model-small-en-us-0.15
FILES_ROOT=/var/lib/clifford/files
REQUESTS_PER_MINUTE=60
PLATFORM_SERVERS=[]
WEB_ROOT=/usr/share/clifford/web
"""
    # O_EXCL preserves an existing configuration even during a concurrent attempt.
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, "w") as output:
        output.write(content)
    return True


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("path", type=Path)
    initialize(parser.parse_args().path)
