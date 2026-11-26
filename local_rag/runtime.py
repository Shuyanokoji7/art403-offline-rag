"""Own and clean up CPU-only llama.cpp processes; use loopback HTTP only."""
from __future__ import annotations

import json
import math
import os
from pathlib import Path
import secrets
import socket
import subprocess
import time
import urllib.error
import urllib.request

from .bootstrap import ASSETS, HERE, runtime_home


class RagError(RuntimeError):
    """An actionable setup, corpus, or inference error."""


def config() -> dict:
    value = json.loads((HERE / "config.json").read_text(encoding="utf-8"))
    bounds = {
        "threads": (1, 16), "embedding_threads": (1, 16),
        "context_tokens": (2048, 8192), "max_answer_tokens": (64, 1024),
        "mcq_answer_tokens": (128, 1536),
        "chunk_tokens": (128, 480), "overlap_words": (0, 48),
        "top_k": (1, 12), "timeout_seconds": (30, 900),
    }
    for key, (low, high) in bounds.items():
        if type(value.get(key)) is not int or not low <= value[key] <= high:
            raise RagError(f"config.json: {key} must be an integer in [{low}, {high}]")
    if not 0 <= value.get("min_similarity", -1) <= 1:
        raise RagError("config.json: min_similarity must be between 0 and 1")
    return value


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise RagError("Local inference refused an HTTP redirect")


def normalize(vector: list[float]) -> list[float]:
    if not vector or any(not math.isfinite(x) for x in vector):
        raise RagError("Embedding model returned an empty or non-finite vector")
    norm = math.sqrt(sum(x * x for x in vector))
    if norm == 0:
        raise RagError("Embedding model returned a zero vector")
    return [x / norm for x in vector]


class Server:
    def __init__(self, kind: str, settings: dict):
        self.kind, self.settings = kind, settings
        self.process = None
        self.log = None
        self.base_url = ""
        self.api_key = secrets.token_urlsafe(32)
        # Ignore system proxies, including enterprise HTTP proxy environment variables.
        self.opener = urllib.request.build_opener(urllib.request.ProxyHandler({}), NoRedirect())

    def start(self):
        if self.process is not None:
            return self
        root = runtime_home()
        executable = root / "runtime" / "b12628" / "llama-server.exe"
        model = root / "models" / ASSETS[self.kind]["filename"]
        if not executable.is_file() or not model.is_file():
            raise RagError("Runtime/model missing. Run: python -m local_rag.bootstrap (one-time Internet setup)")
        if model.stat().st_size != ASSETS[self.kind]["size"]:
            raise RagError(f"Model is incomplete: {model}. Rerun setup.")
        with socket.socket() as sock:
            sock.bind(("127.0.0.1", 0))
            port = sock.getsockname()[1]
        self.base_url = f"http://127.0.0.1:{port}"
        threads = self.settings["embedding_threads" if self.kind == "embedding" else "threads"]
        arguments = [str(executable), "--model", str(model), "--host", "127.0.0.1",
                     "--port", str(port), "--n-gpu-layers", "0", "--threads", str(threads),
                     "--threads-batch", str(threads), "--parallel", "1", "--threads-http", "2",
                     "--no-webui", "--no-warmup", "--offline", "--api-key", self.api_key]
        if self.kind == "embedding":
            arguments += ["--embedding", "--pooling", "cls", "--ctx-size", "512",
                          "--batch-size", "512", "--ubatch-size", "512"]
        else:
            arguments += ["--ctx-size", str(self.settings["context_tokens"]),
                          "--batch-size", "256", "--ubatch-size", "64",
                          "--cache-ram", "0", "--no-context-shift"]
        logs = root / "logs"
        logs.mkdir(parents=True, exist_ok=True)
        self.log_path = logs / f"{self.kind}-{os.getpid()}-{port}.log"
        self.log = self.log_path.open("wb")
        environment = {k: v for k, v in os.environ.items()
                       if not k.startswith("LLAMA_ARG_") and k != "LLAMA_API_KEY"}
        environment["HF_HUB_OFFLINE"] = "1"
        try:
            self.process = subprocess.Popen(
                arguments, stdin=subprocess.DEVNULL, stdout=self.log, stderr=self.log,
                env=environment,
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
            )
            deadline = time.monotonic() + self.settings["timeout_seconds"]
            while time.monotonic() < deadline:
                if self.process.poll() is not None:
                    raise RagError(f"{self.kind} server exited. See {self.log_path}")
                try:
                    if self.request("/health", timeout=1).get("status") == "ok":
                        return self
                except RagError:
                    pass
                time.sleep(0.2)
            raise RagError(f"Timed out loading {self.kind}. Free RAM and inspect {self.log_path}")
        except BaseException:
            self.close()
            raise

    def request(self, path: str, body=None, timeout=None):
        if not path.startswith("/") or path.startswith("//"):
            raise RagError("Only local inference endpoints are permitted")
        payload = None if body is None else json.dumps(body, ensure_ascii=False).encode("utf-8")
        request = urllib.request.Request(self.base_url + path, data=payload,
                                         headers={"Content-Type": "application/json",
                                                  "Authorization": "Bearer " + self.api_key})
        try:
            with self.opener.open(request, timeout=timeout or self.settings["timeout_seconds"]) as response:
                return json.load(response)
        except urllib.error.HTTPError as error:
            detail = error.read().decode("utf-8", errors="replace")[:800]
            raise RagError(f"Local {self.kind} API returned {error.code}: {detail}") from error
        except (OSError, ValueError, urllib.error.URLError) as error:
            raise RagError(f"Local {self.kind} API unavailable: {error}") from error

    def tokens(self, text: str) -> int:
        self.start()
        return len(self.request("/tokenize", {"content": text, "add_special": True,
                                               "parse_special": False})["tokens"])

    def embed(self, texts: list[str]) -> list[list[float]]:
        self.start()
        data = self.request("/v1/embeddings", {"input": texts, "encoding_format": "float"})
        rows = sorted(data["data"], key=lambda row: row["index"])
        if len(rows) != len(texts) or [r["index"] for r in rows] != list(range(len(texts))):
            raise RagError("Embedding response does not match the requested inputs")
        vectors = [normalize(row["embedding"]) for row in rows]
        if any(len(v) != 384 for v in vectors):
            raise RagError("Expected 384-dimensional BGE-small embeddings")
        return vectors

    def close(self):
        if self.process is not None:
            if self.process.poll() is None:
                self.process.terminate()
                try:
                    self.process.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    self.process.kill()
                    self.process.wait(timeout=5)
            self.process = None
        if self.log:
            self.log.close()
            self.log = None

    def __enter__(self):
        return self.start()

    def __exit__(self, *args):
        self.close()
