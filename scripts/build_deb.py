"""Build a self-contained runtime .deb for Ubuntu 24.04 amd64 / CPython 3.12.

Locked source artifacts are checked by pip before any source wheel is built. The installed
package performs no pip network requests and checks hashes for every bundled wheel.
"""

import argparse
import email
import hashlib
import re
import shutil
import subprocess
import sys
import tempfile
import tomllib
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def run(*args, **kwargs):
    subprocess.run([str(arg) for arg in args], check=True, cwd=ROOT, **kwargs)


def wheel_requirements(directory):
    entries = {}
    for wheel in sorted(directory.glob("*.whl")):
        with zipfile.ZipFile(wheel) as archive:
            names = [name for name in archive.namelist() if name.endswith(".dist-info/METADATA")]
            if len(names) != 1:
                raise RuntimeError("Invalid wheel metadata")
            metadata = email.message_from_bytes(archive.read(names[0]))
        name = re.sub(r"[-_.]+", "-", metadata["Name"]).lower()
        if name in entries:
            raise RuntimeError(f"Duplicate wheel package {name}")
        with wheel.open("rb") as artifact:
            digest = hashlib.file_digest(artifact, "sha256").hexdigest()
        entries[name] = f"{name}=={metadata['Version']} --hash=sha256:{digest}"
    if not entries:
        raise RuntimeError("Empty wheelhouse")
    return "\n".join(entries[name] for name in sorted(entries)) + "\n"


def copy(source, destination, executable=False):
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(source, destination)
    destination.chmod(0o755 if executable else 0o644)


def build(output, source, web_source):
    raise RuntimeError(
        "Debian build is paused pending target OS/architecture and the aaPanel Unix-socket redesign"
    )
    global ROOT
    packaging_root = ROOT
    ROOT = source.resolve()
    web_source = web_source.resolve()
    if not (ROOT / "pyproject.toml").is_file() or not (web_source / "web/index.html").is_file():
        raise RuntimeError("Supply separate kernel and web-interface source checkouts")
    if sys.version_info[:2] != (3, 12):
        raise RuntimeError("Build with CPython 3.12 for the Ubuntu 24.04 package")
    arch = subprocess.check_output(["dpkg", "--print-architecture"], text=True).strip()
    if arch != "amd64":
        raise RuntimeError("This build recipe currently targets amd64 only")
    version = tomllib.loads((ROOT / "pyproject.toml").read_text())["project"]["version"] + "-1"
    output.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="clifford-deb-", dir=output) as temp:
        work = Path(temp)
        package, sources, wheels = work / "package", work / "sources", work / "wheels"
        for path in [package, sources, wheels]:
            path.mkdir()
        locked = work / "locked.txt"
        run(
            "uv",
            "export",
            "--frozen",
            "--no-dev",
            "--no-emit-project",
            "--format",
            "requirements-txt",
            "--output-file",
            locked,
        )
        run(
            sys.executable,
            "-m",
            "pip",
            "download",
            "--require-hashes",
            "--dest",
            sources,
            "-r",
            locked,
        )
        # Build only the hash-verified sdist dependencies. Existing wheels are copied unchanged.
        for artifact in sources.iterdir():
            if artifact.suffix == ".whl":
                shutil.copyfile(artifact, wheels / artifact.name)
            else:
                run(
                    sys.executable,
                    "-m",
                    "pip",
                    "wheel",
                    "--no-index",
                    "--no-deps",
                    "--no-build-isolation",
                    "--wheel-dir",
                    wheels,
                    artifact,
                )
        run("uv", "build", "--wheel", "--out-dir", wheels)
        dest = package / "usr/share/clifford/wheels"
        shutil.copytree(wheels, dest)
        (dest.parent / "wheel-requirements.txt").write_text(wheel_requirements(wheels))
        for name in ["env.py", "script.py.mako", "versions/0001_initial_assistant_schema.py"]:
            copy(ROOT / "migrations" / name, package / "usr/lib/clifford/migrations" / name)
        ini = package / "usr/lib/clifford/alembic.ini"
        ini.write_text(
            "[alembic]\nscript_location = /usr/lib/clifford/migrations\npath_separator = os\n"
        )
        copy(
            ROOT / "scripts/download_voice_model.py",
            package / "usr/lib/clifford/scripts/download_voice_model.py",
        )
        copy(
            packaging_root / "packaging/debian/init_config.py",
            package / "usr/lib/clifford/debian/init_config.py",
        )
        copy(
            packaging_root / "packaging/debian/clifford_admin.py",
            package / "usr/bin/clifford",
            True,
        )
        copy(
            packaging_root / "packaging/debian/clifford.service",
            package / "usr/lib/systemd/system/clifford.service",
        )
        copy(
            packaging_root / "packaging/debian/caddy-group.conf",
            package / "etc/systemd/system/caddy.service.d/clifford.conf",
        )
        copy(
            packaging_root / "packaging/debian/clifford.caddy",
            package / "etc/caddy/conf.d/clifford.caddy",
        )
        copy(
            packaging_root / "docs/debian.md",
            package / "usr/share/doc/clifford-assistant/README.Debian",
        )
        shutil.copytree(web_source / "web", package / "usr/share/clifford/web")
        control = package / "DEBIAN"
        control.mkdir()
        installed = (
            sum(path.stat().st_size for path in package.rglob("*") if path.is_file()) // 1024
        )
        (control / "control").write_text(f"""Package: clifford-assistant
Version: {version}
Section: misc
Priority: optional
Architecture: amd64
Maintainer: Clifford maintainers <noreply@parsabe.com>
Depends: python3 (>= 3.12), python3 (<< 3.13), python3-venv, adduser, ca-certificates, libc6 (>= 2.35), libstdc++6, libgcc-s1, libgomp1, libatomic1, init-system-helpers, caddy, curl
Installed-Size: {installed}
Homepage: https://github.com/parsabe/Clifford
Description: Local Gemma assistant with private service and HTTPS configuration
 Includes a hash-checked offline Python runtime wheelhouse for Ubuntu 24.04 amd64.
 Uses system Python 3.12. Ollama and AI/speech models are installed separately.
 Caddy provides TLS at clifford.parsabe.com through a private Unix socket.
""")
        (control / "conffiles").write_text(
            "/etc/caddy/conf.d/clifford.caddy\n/etc/systemd/system/caddy.service.d/clifford.conf\n"
        )
        for name in ["postinst", "prerm", "postrm"]:
            copy(packaging_root / "packaging/debian" / name, control / name, True)
        sums = []
        for path in sorted(package.rglob("*")):
            if path.is_file() and control not in path.parents:
                with path.open("rb") as file:
                    sums.append(
                        hashlib.file_digest(file, "md5").hexdigest()
                        + "  "
                        + str(path.relative_to(package))
                    )
        (control / "md5sums").write_text("\n".join(sums) + "\n")
        target = output / f"clifford-assistant_{version}_amd64.deb"
        run("dpkg-deb", "--root-owner-group", "-Zxz", "--build", package, target)
        with target.open("rb") as file:
            checksum = hashlib.file_digest(file, "sha256").hexdigest()
        target.with_suffix(".deb.sha256").write_text(checksum + "  " + target.name + "\n")
        print(f"Built {target} ({target.stat().st_size / 1024 / 1024:.1f} MiB)")
        return target


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=ROOT / "dist")
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--web-source", type=Path, required=True)
    args = parser.parse_args()
    build(args.output.resolve(), args.source, args.web_source)
