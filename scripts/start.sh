#!/bin/sh
set -eu
cd "$(dirname "$0")/.."
socket_path="$(.venv/bin/python -c 'from clifford.config import Settings; print(Settings().socket_path)')"
socket_directory="$(dirname "$socket_path")"
umask 0077
mkdir -p "$socket_directory"
.venv/bin/python - "$socket_directory" <<'PY'
import os,stat,sys
info=os.stat(sys.argv[1])
if stat.S_IMODE(info.st_mode) & 0o007:
    raise SystemExit('Socket directory must exclude other users; use a private directory with mode 0700 or 0750.')
PY
exec .venv/bin/uvicorn clifford.api:app --uds "$socket_path" --workers 1 --ws-max-size 128000 --no-proxy-headers --no-access-log
