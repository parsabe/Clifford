import asyncio
import json
from collections.abc import AsyncIterator
from dataclasses import dataclass
from typing import Protocol

import httpx

from clifford.config import Settings


class ProviderError(Exception):
    def __init__(self, code="provider_unavailable"):
        self.code = code
        super().__init__(code)


@dataclass
class Chunk:
    text: str = ""
    usage: dict | None = None


class Provider(Protocol):
    async def stream(self, messages: list[dict], system: str) -> AsyncIterator[Chunk]: ...


class OllamaProvider:
    """Native local Ollama NDJSON API. No credential or cloud fallback."""

    def __init__(self, settings: Settings):
        self.settings = settings

    async def stream(self, messages, system):
        emitted = False
        for attempt in range(self.settings.provider_retries + 1):
            try:
                async with httpx.AsyncClient(timeout=self.settings.provider_timeout) as client:
                    async with client.stream(
                        "POST",
                        self.settings.ollama_base_url.rstrip("/") + "/api/chat",
                        json={
                            "model": self.settings.default_llm_model,
                            "messages": [{"role": "system", "content": system}, *messages],
                            "stream": True,
                            "options": {
                                "num_predict": self.settings.max_output_tokens,
                                "num_ctx": self.settings.ollama_num_ctx,
                                "num_batch": 128,
                            },
                        },
                    ) as response:
                        if response.status_code == 404:
                            raise ProviderError("model_not_installed")
                        response.raise_for_status()
                        completed = False
                        async for line in response.aiter_lines():
                            if not line.strip():
                                continue
                            try:
                                data = json.loads(line)
                                if data.get("error"):
                                    raise ProviderError("model_error")
                                content = data.get("message", {}).get("content", "")
                                if not isinstance(content, str):
                                    raise ValueError()
                            except (ValueError, AttributeError, TypeError):
                                raise ProviderError("invalid_provider_response") from None
                            if content:
                                emitted = True
                                yield Chunk(text=content)
                            if data.get("done") is True:
                                completed = True
                                yield Chunk(
                                    usage={
                                        "input_tokens": data.get("prompt_eval_count"),
                                        "output_tokens": data.get("eval_count"),
                                        "model": self.settings.default_llm_model,
                                    }
                                )
                                break
                        if not completed:
                            raise ProviderError("incomplete_provider_response")
                        return
            except (httpx.TransportError, httpx.HTTPStatusError) as exc:
                transient = not isinstance(
                    exc, httpx.HTTPStatusError
                ) or exc.response.status_code in {429, 500, 502, 503, 504}
                if emitted or not transient or attempt == self.settings.provider_retries:
                    raise ProviderError("ollama_unavailable") from None
                await asyncio.sleep(0.25 * 2**attempt)

    async def check(self):
        try:
            async with httpx.AsyncClient(timeout=5) as client:
                response = await client.get(self.settings.ollama_base_url.rstrip("/") + "/api/tags")
                response.raise_for_status()
                models = {m["name"] for m in response.json().get("models", [])}
                return {
                    "reachable": True,
                    "model_installed": self.settings.default_llm_model in models,
                }
        except (httpx.HTTPError, ValueError, KeyError, TypeError):
            return {"reachable": False, "model_installed": False}


class Router:
    def __init__(self, settings):
        self.settings = settings

    async def stream(self, messages, system):
        if self.settings.default_llm_provider != "ollama":
            raise ProviderError("unsupported_provider_use_ollama")
        async for chunk in OllamaProvider(self.settings).stream(messages, system):
            yield chunk
