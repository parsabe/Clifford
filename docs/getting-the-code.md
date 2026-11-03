# Download component branches

The master branch intentionally contains the README branch index, not a merged application tree.
Select a component using GitHub's branch selector, then choose **Code → Download ZIP**.

| Component | Branch | Source ZIP |
| --- | --- | --- |
| Backend | kernel | [Download](https://github.com/parsabe/Clifford/archive/refs/heads/kernel.zip) |
| Browser interface | web-interface | [Download](https://github.com/parsabe/Clifford/archive/refs/heads/web-interface.zip) |
| Android client reservation | android-app | [Download](https://github.com/parsabe/Clifford/archive/refs/heads/android-app.zip) |
| Linux deployment/package draft | linux-source | [Download](https://github.com/parsabe/Clifford/archive/refs/heads/linux-source.zip) |
| Windows client reservation | windows-source | [Download](https://github.com/parsabe/Clifford/archive/refs/heads/windows-source.zip) |
| Documentation | documentation | [Download](https://github.com/parsabe/Clifford/archive/refs/heads/documentation.zip) |

For development, clone with `git clone --branch <branch> --single-branch <repository> <directory>`.
The kernel's `WEB_ROOT` points at the web branch's `web/` directory; no merge is needed.
The original all-in-one source remains recoverable at commit `f230eaf` in Git history.
No private `.env`, token, uploaded prompt, database, model or virtual environment belongs in Git.
