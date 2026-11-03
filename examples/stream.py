"""Minimal SSE integration client. Server credentials are read from the process environment."""

import asyncio
import json
import os

import httpx


async def main():
    token = os.environ["CLIFFORD_AUTH_SECRET"]
    async with httpx.AsyncClient(timeout=180) as client:
        async with client.stream(
            "POST",
            "http://127.0.0.1:8000/v1/chat/stream",
            headers={"Authorization": f"Bearer {token}"},
            json={"text": "Hello Clifford"},
        ) as response:
            response.raise_for_status()
            async for line in response.aiter_lines():
                if line.startswith("data: "):
                    event = json.loads(line[6:])
                    if event["type"] == "assistant.delta":
                        print(event["payload"]["text"], end="", flush=True)
                    elif event["type"] == "error":
                        raise RuntimeError(event["payload"]["code"])
    print()


if __name__ == "__main__":
    asyncio.run(main())
