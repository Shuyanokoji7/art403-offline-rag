"""Small corpus-specific smoke evaluation, with Python network access limited to loopback."""
from __future__ import annotations

import argparse
from contextlib import contextmanager
import ctypes
import ipaddress
import json
import os
import socket
import threading
import time
from unittest.mock import patch

from .engine import Engine
from .index import DATA
from .runtime import config

RETRIEVAL_CASES = [
    ("What structural features distinguish the Lotus Mahal?", "lotus-mahal"),
    ("What is kalamkari and how is it made?", "feature-kalamkari"),
    ("When was La Japonaise painted?", "camille-monet-in-japanese-costume-la-japonaise"),
    ("What is the corrected date of Under Mannen Bridge at Fukagawa?", "under-mannen-bridge-at-fukagawa"),
    ("What is the Gandaberunda motif?", "feature-gandaberunda"),
    ("Describe the flowers on the uncaptioned ceramic dish on the course cover.", "uncaptioned-floral-dish-on-the-course-cover"),
    ("How do the early granite friezes differ from the later green-chlorite friezes?", "later-green-chlorite-friezes-mahanabami-dibba"),
    ("What is the role of the mirror in A Goldsmith in his Shop?", "a-goldsmith-in-his-shop"),
]
GENERATION_CASES = [
    {"question": "When was La Japonaise painted, and how does the museum date differ from the lecture?", "required": ["1876", "1875"]},
    {"question": "What is the corrected date of Under Mannen Bridge at Fukagawa?", "required": ["1830"]},
    {"question": "What structural features distinguish the Lotus Mahal?", "required": ["arch"]},
    {"question": "Who is the confirmed maker of the uncaptioned floral ceramic dish on the course cover?", "uncertain": True},
    {"question": "What battery voltage should I use for a Tesla Model 3?", "refuse": True},
]


@contextmanager
def loopback_only():
    original = socket.socket.connect
    def connect(sock, address):
        if not isinstance(address, tuple) or not ipaddress.ip_address(address[0]).is_loopback:
            raise RuntimeError(f"Offline evaluation blocked a non-loopback connection: {address}")
        return original(sock, address)
    with patch.object(socket.socket, "connect", connect):
        yield


def working_set(pid):
    if os.name != "nt":
        return 0
    class Counters(ctypes.Structure):
        _fields_ = [("cb", ctypes.c_ulong), ("faults", ctypes.c_ulong)] + [
            (name, ctypes.c_size_t) for name in ("peak", "working", "peak_pool", "pool", "peak_nonpaged", "nonpaged", "pagefile", "peak_pagefile")]
    kernel = ctypes.windll.kernel32
    kernel.OpenProcess.restype = ctypes.c_void_p
    handle = kernel.OpenProcess(0x0400 | 0x0010, False, pid)
    if not handle:
        return 0
    result = Counters()
    result.cb = ctypes.sizeof(result)
    try:
        success = ctypes.windll.psapi.GetProcessMemoryInfo(ctypes.c_void_p(handle), ctypes.byref(result), result.cb)
        return result.working if success else 0
    finally:
        kernel.CloseHandle(ctypes.c_void_p(handle))


def run(generate=False):
    settings = config()
    report = {"settings": settings, "python_network_policy": "loopback only", "llama_cpp_offline_flag": True,
              "retrieval_cases": [], "generation_cases": []}
    with loopback_only(), Engine(settings) as engine:
        report["index"] = engine.index.stats
        stop = threading.Event()
        peak = [0]
        def sample_memory():
            while not stop.wait(0.5):
                pids = [os.getpid()] + [s.process.pid for s in (engine.embedder, engine.llm) if s.process]
                peak[0] = max(peak[0], sum(working_set(pid) for pid in pids))
        sampler = threading.Thread(target=sample_memory, daemon=True)
        sampler.start()
        try:
            for question, expected in RETRIEVAL_CASES:
                start = time.monotonic()
                hits = engine.search(question)
                passed = any(h["article_id"] == expected for h in hits)
                row = {"question": question, "expected_article": expected, "passed": passed,
                       "seconds": round(time.monotonic() - start, 2),
                       "hits": [{"article_id": h["article_id"], "section": h["section"],
                                 "similarity": h["similarity"]} for h in hits]}
                report["retrieval_cases"].append(row)
                print(f"Retrieval {'PASS' if passed else 'FAIL'}: {question}", flush=True)
            if generate:
                for case in GENERATION_CASES:
                    try:
                        result = engine.ask(case["question"])
                        answer = result["answer"].lower()
                        if case.get("refuse"):
                            passed = result["insufficient_evidence"]
                        elif case.get("uncertain"):
                            passed = result["insufficient_evidence"] or any(w in answer for w in ("not established", "unknown", "unresolved", "not confirmed", "not identified", "uncertain", "no confirmed", "does not identify"))
                        else:
                            passed = not result["insufficient_evidence"] and all(w in answer for w in case["required"])
                        row = {"question": case["question"], "passed": passed, "result": result}
                    except Exception as error:
                        row = {"question": case["question"], "passed": False, "error": str(error)}
                        if hasattr(error, "model_output"):
                            row["model_output"] = error.model_output
                    report["generation_cases"].append(row)
                    print(f"Generation {'PASS' if row['passed'] else 'FAIL'}: {case['question']}", flush=True)
                    print(row.get("result", {}).get("answer", row.get("error", "")), flush=True)
        finally:
            stop.set()
            sampler.join(timeout=2)
        report["sampled_peak_combined_working_set_gib"] = round(peak[0] / 1024**3, 3)
    report["passed"] = all(c["passed"] for c in report["retrieval_cases"] + report["generation_cases"])
    DATA.mkdir(parents=True, exist_ok=True)
    path = DATA / ("evaluation-full.json" if generate else "evaluation-retrieval.json")
    path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Report: {path}", flush=True)
    print(f"Sampled peak process working sets: {report['sampled_peak_combined_working_set_gib']} GiB", flush=True)
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--generate", action="store_true", help="Also test five real LLM answers (slower)")
    args = parser.parse_args()
    raise SystemExit(0 if run(args.generate)["passed"] else 1)
