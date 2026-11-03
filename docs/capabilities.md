# Current status

| Capability | Status |
| --- | --- |
| Clifford identity and wake phrase; owner kept distinct | Implemented |
| Local Gemma 3 12B/Ollama adapter, no vendor keys | Implemented; protocol tests pass; real inference pending model installation |
| Authenticated REST/SSE/WebSocket, persisted sessions/memory | Implemented and tested |
| Small-context settings for a 12GB server | Configured; actual memory fit/speed needs hardware verification |
| Offline Vosk PCM transcription transport | Implemented; adapter/protocol tested; real model/microphone pending |
| Wake phrase plus full sentence, wake-only next sentence | Implemented; deterministic state tests pass |
| Automatic local device speech and spoken interruption | Implemented; cancellation/queue tests pass; real acoustic performance pending |
| Server-backed laptop/phone/future watch client contracts | Implemented; no native phone/watch application included |
| Multiple configured MCP platform bridges | Implemented; schema/grant/approval tests pass; real chosen platforms need setup |
| Email | Not connected; no email feature configured |
| Calculator, time, scoped files, approval-bound plans | Implemented and tested |
| Universal OAuth, desktop automation, persistent scheduling | Not implemented |
| Vector memory, automatic summarization, distributed workers | Not implemented |
| Docker/Compose, Caddy deployment examples | Provided; not executed here |

Clifford is not fully verified for hands-free daily use until actual Gemma inference, microphone
recognition, speaker echo behavior and interruption have passed on the intended server/client devices.
