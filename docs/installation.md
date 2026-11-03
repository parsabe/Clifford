# Install from separate component branches

The master branch is a project index. Clone each component separately; do not merge them:

```sh
git clone --branch kernel --single-branch https://github.com/parsabe/Clifford.git clifford-kernel
git clone --branch web-interface --single-branch https://github.com/parsabe/Clifford.git clifford-web
```

Follow the kernel README to install Python dependencies, Ollama/Gemma, the offline Vosk speech model
and database migrations. In the kernel's private `.env`, set `WEB_ROOT` to the absolute path of
`clifford-web/web`; restart the kernel to serve the browser client at `/console/`.
No merge or frontend build is needed. The backend remains independently runnable without web files.

The source development script uses loopback port 8000. Linux package development is on `linux-source`
and is paused until the server's Ubuntu release and CPU architecture are provided. Its proposed
Debian service uses a private Unix socket behind Caddy for `clifford.parsabe.com`; no `.deb` or live
SSL deployment has been verified yet. DNS must point at the server and ports 80/443 must be reachable
before issuing a public certificate.

A 12GB server may be tight for quantized Gemma 3 12B. Defaults use a small 2,048-token context and
512-token output. A GPU is optional; response speed and actual memory fit need hardware verification.
Paid model/speech API keys are not required. Protect access with the generated backend login token.

After enabling microphone access once, say “Clifford, ...”. Replies speak automatically using a
local device voice, and interruption cancels playback/generation. Real echo and recognition quality
still need device testing. Phones need HTTPS for remote mic access. Native Android and Windows
clients are reserved development branches, and no native watch app is included.
