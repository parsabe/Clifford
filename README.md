# Clifford web interface

This branch contains the image-inspired cyan waveform browser client, hands-free wake gating,
PCM capture/resampling, automatic local device speech and interruption handling. Native apps are
separate projects. No backend or paid-provider credentials are included here.

Clone `kernel` and `web-interface` into separate directories. Install/start the kernel according to
its README. Set the kernel's private `WEB_ROOT` setting to the absolute path of this branch's `web/`
directory, then restart the kernel. It serves this client at `/console/` on the same authenticated
API origin; no merge or frontend build is needed. Do not use a file:// URL.

One initial Enable voice action and microphone permission are required. Use HTTPS for remote
microphone access. Say “Clifford, ...”; replies speak automatically. Spoken interruption cancels
playback and generation. Local OS speech voices must be installed; physical microphone/echo
performance still needs device testing. Use headphones for initial tests.

Run `node tests/voice.test.mjs` for the five deterministic voice-state tests.

[Kernel](https://github.com/parsabe/Clifford/tree/kernel) ·
[Client API contracts](https://github.com/parsabe/Clifford/blob/documentation/docs/api.md) ·
[Branch index](https://github.com/parsabe/Clifford/tree/master)
