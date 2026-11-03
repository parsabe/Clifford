"""Fetch the official Vosk English model over verified HTTPS. Never replace existing models."""

import argparse
import hashlib
import os
import stat
import tempfile
import zipfile
from pathlib import Path, PurePosixPath

import httpx

URL = "https://alphacephei.com/vosk/models/vosk-model-small-en-us-0.15.zip"
NAME = "vosk-model-small-en-us-0.15"


def download(destination: Path, expected_sha256: str | None = None):
    destination.mkdir(parents=True, exist_ok=True)
    target = destination / NAME
    if target.exists():
        if (target / "am/final.mdl").is_file() and (target / "conf/model.conf").is_file():
            print("Speech model already installed; preserved existing files.")
            return
        raise RuntimeError("Incomplete model directory exists; inspect it before retrying.")
    with tempfile.TemporaryDirectory(dir=destination) as directory:
        staging = Path(directory)
        archive = staging / "model.zip"
        digest, downloaded = hashlib.sha256(), 0
        with httpx.stream("GET", URL, follow_redirects=True, timeout=120) as response:
            response.raise_for_status()
            with archive.open("wb") as output:
                for block in response.iter_bytes():
                    downloaded += len(block)
                    if downloaded > 100_000_000:
                        raise RuntimeError("Model download exceeds size limit")
                    digest.update(block)
                    output.write(block)
        if expected_sha256 and digest.hexdigest() != expected_sha256.lower():
            raise RuntimeError("Model SHA256 does not match the supplied trusted checksum")
        with zipfile.ZipFile(archive) as zipped:
            if sum(info.file_size for info in zipped.infolist()) > 250_000_000:
                raise RuntimeError("Unpacked model exceeds size limit")
            for info in zipped.infolist():
                parts = PurePosixPath(info.filename)
                if (
                    parts.is_absolute()
                    or ".." in parts.parts
                    or "\\" in info.filename
                    or not parts.parts
                    or parts.parts[0] != NAME
                    or stat.S_ISLNK(info.external_attr >> 16)
                ):
                    raise RuntimeError("Unsafe model archive path")
            zipped.extractall(staging)
        model = staging / NAME
        if not (model / "am/final.mdl").is_file() or not (model / "conf/model.conf").is_file():
            raise RuntimeError("Downloaded archive is not the expected speech model")
        os.rename(model, target)
        print("Speech model installed from the official HTTPS source.")
        print(
            "Downloaded archive SHA256 (fingerprint, not an independent trust source):",
            digest.hexdigest(),
        )


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--destination", default="data/models")
    parser.add_argument(
        "--sha256", help="Optional checksum obtained independently from a trusted source"
    )
    args = parser.parse_args()
    download(Path(args.destination), args.sha256)
