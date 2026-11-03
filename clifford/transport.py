"""Kernel access is restricted to the configured, filesystem-protected Unix socket."""

from fastapi import HTTPException


def require_socket(scope, path):
    server = scope.get("server")
    if (
        scope.get("client") is not None
        or not isinstance(server, (list, tuple))
        or len(server) != 2
        or server[0] != path
        or server[1] is not None
    ):
        raise HTTPException(403, detail={"code": "private_socket_required"})
