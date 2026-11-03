"""Explicit live local-model check: exits nonzero unless a real response completes."""

import asyncio

from clifford.config import Settings
from clifford.providers.llm import OllamaProvider
from clifford.providers.speech import LocalSpeech


async def main():
    settings = Settings()
    provider = OllamaProvider(settings)
    status = await provider.check()
    print("Ollama reachable:", status["reachable"])
    print("Gemma model installed:", status["model_installed"])
    print("Speech model installed:", LocalSpeech(settings).available())
    if not status["model_installed"]:
        raise SystemExit("Run ollama serve and ollama pull gemma3:12b on the backend server.")
    text = ""
    async for chunk in provider.stream(
        [{"role": "user", "content": "Reply with a short greeting."}],
        "You are Clifford, the assistant, not the user.",
    ):
        text += chunk.text
    if not text.strip():
        raise SystemExit("Local inference returned an empty response")
    print("Live Gemma response:", text)


if __name__ == "__main__":
    asyncio.run(main())
