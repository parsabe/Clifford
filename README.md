# Clifford Linux source and packaging

Linux deployment and pending Debian packaging live on this branch. The backend source lives on
`kernel` and the browser files on `web-interface`; branches are not merged.

**Package work is paused until the server's Ubuntu version and CPU architecture are supplied.**
The current draft targets Ubuntu 24.04 amd64/Python 3.12. No `.deb` has been built or installation-tested.
The draft service uses a private Unix socket, and Caddy targets `clifford.parsabe.com`. DNS and actual
certificate issuance have not been configured. Existing Caddy sites are preserved by the intended
explicit site-enable command. Do not treat the pending installer as ready to deploy.

The builder takes separate source checkouts when development resumes:

```sh
python3 scripts/build_deb.py --source ../clifford-kernel --web-source ../clifford-web
```

It will verify locked dependency artifacts, bundle an offline wheelhouse, and package the selected
kernel and web files. Gemma and speech models remain separate downloads. See `docs/debian.md`.

Docker is an existing unverified deployment recipe: from the kernel checkout use
`docker build -f ../clifford-linux/Dockerfile .`. The Compose example assumes adjacent
`clifford-kernel`, `clifford-web`, and `clifford-linux` checkout directories. It is not an installed
Debian service and keeps its development HTTP port bound only to loopback.

[Kernel](https://github.com/parsabe/Clifford/tree/kernel) ·
[Web interface](https://github.com/parsabe/Clifford/tree/web-interface) ·
[Documentation](https://github.com/parsabe/Clifford/tree/documentation) ·
[Branch index](https://github.com/parsabe/Clifford/tree/master)

## Laravel architecture update

The `web-interface` branch is now a Laravel 13 application deployed separately through aaPanel
with its document root at public/. The paused Debian draft predates this conversion and still
assumes a static web bundle. Its builder is not ready for the new architecture and must be revised
before any package is built. Package work remains paused until the server details are supplied.
Use the web branch's aaPanel guide for the website; do not run the Caddy example alongside aaPanel
on the same public ports. A future backend package can remain private behind aaPanel's Nginx proxy.


## Private-socket update

Shared credential generation and the old token command are removed from these drafts. The legacy
Caddy direct-kernel proxy is disabled to prevent publishing no-token APIs. The draft builder is
explicitly paused until the target platform is supplied and packaging is adapted to the current
Laravel/aaPanel architecture. Docker examples also predate Unix-only access and must not be used as
current installation instructions. Use the kernel branch source-service helper and web branch aaPanel
guide now. No .deb has been built, activated or published by this revision.
