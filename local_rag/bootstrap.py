"""One-time online setup. All query/index commands are separate and offline."""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import platform
import shutil
import sys
import time
import urllib.request
import zipfile

HERE = Path(__file__).resolve().parent
ASSETS = json.loads((HERE / "assets.json").read_text(encoding="utf-8"))


def runtime_home() -> Path:
    override = os.environ.get("ART403_RAG_HOME")
    if override:
        return Path(override).expanduser().resolve()
    return Path(os.environ.get("LOCALAPPDATA", Path.home() / ".local" / "share")) / "ART403-RAG"


def sha256(path: Path) -> str:
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def download(asset: dict, target: Path) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.exists() and sha256(target) == asset["sha256"]:
        print(f"Verified existing {target.name}", flush=True)
        return
    partial = target.with_suffix(target.suffix + ".partial")
    start = partial.stat().st_size if partial.exists() else 0
    if start > asset["size"]:
        raise RuntimeError(f"Oversized partial download: {partial}")
    if start < asset["size"]:
        headers = {"User-Agent": "ART403-local-RAG/1.0"}
        if start:
            headers["Range"] = f"bytes={start}-"
        request = urllib.request.Request(asset["url"], headers=headers)
        with urllib.request.urlopen(request, timeout=60) as response:
            if start and response.status != 206:
                start = 0  # Server does not support resuming this object.
            if start and not response.headers.get("Content-Range", "").startswith(f"bytes {start}-"):
                raise RuntimeError("Download server returned an invalid byte range")
            received, last_report = start, 0.0
            with partial.open("ab" if start else "wb") as output:
                while block := response.read(1024 * 1024):
                    output.write(block)
                    received += len(block)
                    if time.monotonic() - last_report > 10:
                        print(f"{target.name}: {received / 1e6:.0f}/{asset['size'] / 1e6:.0f} MB", flush=True)
                        last_report = time.monotonic()
    if partial.stat().st_size != asset["size"] or sha256(partial) != asset["sha256"]:
        raise RuntimeError(f"Checksum mismatch: {partial}. Remove that partial file and rerun setup.")
    partial.replace(target)
    print(f"Downloaded and SHA-256 verified {target.name}", flush=True)


def main() -> None:
    if sys.version_info < (3, 11):
        raise RuntimeError("Python 3.11 or newer is required")
    if platform.system() != "Windows" or platform.machine().lower() not in {"amd64", "x86_64"}:
        raise RuntimeError("This setup contains the Windows x64 CPU runtime for the target machine.")
    root = runtime_home()
    root.mkdir(parents=True, exist_ok=True)
    if shutil.disk_usage(root).free < 3 * 1024**3:
        raise RuntimeError("Setup needs at least 3 GiB of free disk space")
    print(f"Runtime and models: {root}\nOnly this setup command uses the Internet.", flush=True)
    archive = root / "downloads" / ASSETS["runtime"]["filename"]
    download(ASSETS["runtime"], archive)
    destination = root / "runtime" / "b12628"
    destination.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(archive) as bundle:
        for member in bundle.infolist():
            if not (destination / member.filename).resolve().is_relative_to(destination.resolve()):
                raise RuntimeError("Unsafe runtime archive path")
        bundle.extractall(destination)
    for name in ("embedding", "llm"):
        download(ASSETS[name], root / "models" / ASSETS[name]["filename"])
    print("Setup complete. Next: python -m local_rag index", flush=True)


if __name__ == "__main__":
    try:
        main()
    except (OSError, RuntimeError) as error:
        print(f"Setup failed: {error}", file=sys.stderr)
        sys.exit(1)
