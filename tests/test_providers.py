import json

import httpx
import pytest

from clifford.config import Settings
from clifford.providers import llm, speech


def fixture_client(monkeypatch, handler):
    constructor = httpx.AsyncClient
    monkeypatch.setattr(
        llm.httpx,
        "AsyncClient",
        lambda **kw: constructor(**kw, transport=httpx.MockTransport(handler)),
    )


@pytest.mark.asyncio
async def test_ollama_stream_no_keys_small_context(monkeypatch):
    def server(request):
        body = json.loads(request.content)
        assert "authorization" not in request.headers
        assert body["model"] == "gemma3:12b"
        assert body["options"]["num_ctx"] == 2048
        assert body["messages"][0] == {"role": "system", "content": "System"}
        chunks = [
            {"message": {"content": "Hello "}, "done": False},
            {"message": {"content": "Clifford."}, "done": False},
            {"done": True, "eval_count": 3, "prompt_eval_count": 10},
        ]
        return httpx.Response(200, content="\n".join(json.dumps(c) for c in chunks))

    fixture_client(monkeypatch, server)
    chunks = [
        c
        async for c in llm.Router(Settings(_env_file=None)).stream(
            [{"role": "user", "content": "Hi"}], "System"
        )
    ]
    assert "".join(c.text for c in chunks) == "Hello Clifford."
    assert chunks[-1].usage["output_tokens"] == 3


@pytest.mark.asyncio
async def test_transient_retry(monkeypatch):
    calls = []

    def server(request):
        calls.append(request)
        if len(calls) == 1:
            return httpx.Response(503)
        return httpx.Response(200, content='{"message":{"content":"Hi"},"done":true}\n')

    fixture_client(monkeypatch, server)
    assert [c.text async for c in llm.Router(Settings(_env_file=None)).stream([], "")] == ["Hi", ""]
    assert len(calls) == 2


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "status,content,code",
    [
        (404, "{}", "model_not_installed"),
        (200, "{invalid}", "invalid_provider_response"),
        (200, '{"message":{"content":"partial"}}', "incomplete_provider_response"),
        (200, '{"error":"private diagnostic"}', "model_error"),
    ],
)
async def test_ollama_errors(monkeypatch, status, content, code):
    fixture_client(monkeypatch, lambda r: httpx.Response(status, content=content))
    with pytest.raises(llm.ProviderError, match=code):
        _ = [c async for c in llm.Router(Settings(_env_file=None)).stream([], "")]


@pytest.mark.asyncio
async def test_no_retry_after_partial_output(monkeypatch):
    class BrokenStream(httpx.AsyncByteStream):
        async def __aiter__(self):
            yield b'{"message":{"content":"partial"},"done":false}\n'
            raise httpx.ReadError("private info")

    calls = []

    def server(request):
        calls.append(request)
        return httpx.Response(200, stream=BrokenStream())

    fixture_client(monkeypatch, server)
    output = []
    with pytest.raises(llm.ProviderError, match="ollama_unavailable"):
        async for chunk in llm.Router(Settings(_env_file=None)).stream([], ""):
            output.append(chunk.text)
    assert output == ["partial"] and len(calls) == 1


@pytest.mark.asyncio
async def test_model_connection_check(monkeypatch):
    fixture_client(
        monkeypatch, lambda r: httpx.Response(200, json={"models": [{"name": "gemma3:12b"}]})
    )
    assert await llm.OllamaProvider(Settings(_env_file=None)).check() == {
        "reachable": True,
        "model_installed": True,
    }


def test_speech_missing_and_invalid_model(tmp_path):
    provider = speech.LocalSpeech(Settings(_env_file=None, vosk_model_path=str(tmp_path)))
    assert not provider.available()
    with pytest.raises(llm.ProviderError, match="speech_model_not_installed"):
        provider.recognizer()


def test_transcription_adapter():
    class Recognizer:
        def AcceptWaveform(self, audio):
            return audio == b"final"

        def Result(self):
            return '{"text":"clifford tell me the time"}'

        def PartialResult(self):
            return '{"partial":"clifford tell"}'

    assert speech.LocalSpeech.accept(Recognizer(), b"final") == {
        "text": "clifford tell me the time",
        "final": True,
    }
    assert speech.LocalSpeech.accept(Recognizer(), b"partial")["final"] is False
