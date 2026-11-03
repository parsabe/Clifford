# Clifford

Clifford is a local Gemma 3 12B assistant. The assistant's name and wake phrase are **Clifford**.
This branch is the project index. Each component is maintained on its own branch; **do not merge
component branches into master or into one another**.

| Branch | Contents | Status |
| --- | --- | --- |
| [kernel](https://github.com/parsabe/Clifford/tree/kernel) | Backend, local Gemma/Ollama, Vosk speech recognition, APIs, memory, tools, approvals and platform connectors | Implemented; live model/device verification pending |
| [web-interface](https://github.com/parsabe/Clifford/tree/web-interface) | Laravel 13 web app, Blade UI, private kernel proxy, automatic speech and interruption | PHP 8.3+/aaPanel; feature/browser checks pass; real device verification pending |
| [android-app](https://github.com/parsabe/Clifford/tree/android-app) | Native Android app development | Reserved; native app not yet implemented |
| [linux-source](https://github.com/parsabe/Clifford/tree/linux-source) | Linux deployment, systemd/Caddy and Debian package source | Package build paused pending Ubuntu version and CPU architecture |
| [windows-source](https://github.com/parsabe/Clifford/tree/windows-source) | Windows source and compilation work | Reserved; native build target not yet implemented |
| [documentation](https://github.com/parsabe/Clifford/tree/documentation) | Installation, architecture, API, security, capabilities and validation | Maintained separately |

## Download and run

Select the relevant branch above and use **Code → Download ZIP**, or clone that branch explicitly:

```sh
git clone --branch kernel --single-branch https://github.com/parsabe/Clifford.git clifford-kernel
git clone --branch web-interface --single-branch https://github.com/parsabe/Clifford.git clifford-web
```

Follow the kernel README for the private AI service. Deploy the separate Laravel web app using
Composer, its interactive installer and aaPanel document root **public/**. Configure the supplied
rewrite/WebSocket rules and HTTPS; keep kernel WEB_ROOT empty. Component branches remain separate.

[Laravel / aaPanel guide](https://github.com/parsabe/Clifford/blob/web-interface/deploy/README.md)

[Installation guide](https://github.com/parsabe/Clifford/blob/documentation/docs/installation.md) ·
[API/client contracts](https://github.com/parsabe/Clifford/blob/documentation/docs/api.md) ·
[Capability status](https://github.com/parsabe/Clifford/blob/documentation/docs/capabilities.md)

The intended HTTPS domain is **clifford.parsabe.com**. DNS/certificate activation has not happened.
aaPanel now owns web hosting and HTTPS. The separate Debian draft needs adaptation to this Laravel
architecture; package work will resume after the server's Ubuntu version and architecture are supplied. No `.deb` is published yet.

No paid model API keys are required. Private backend authentication, models and databases are excluded
from the repository. The original all-in-one source remains recoverable at commit `f230eaf`.


The current kernel is **Unix-socket only**, with no shared backend token. Laravel uses aaPanel site
access protection and has no custom web password/hash setting. The setup command removes retired
fields automatically. Update both kernel and web-interface and apply the linked aaPanel socket guide;
removing environment lines alone does not upgrade an older installation.
