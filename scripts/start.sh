#!/bin/sh
set -eu
cd "$(dirname "$0")/.."
exec .venv/bin/uvicorn clifford.api:app --host 127.0.0.1 --port 8000 --workers 1 --ws-max-size 128000 --no-access-log
