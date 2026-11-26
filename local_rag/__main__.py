"""Usage: python -m local_rag {index,ask,mcq,chat,search,doctor}."""
from __future__ import annotations

import argparse
from contextlib import closing
import ctypes
import json
import os
from pathlib import Path
import sqlite3
import sys

from .bootstrap import ASSETS, runtime_home, sha256
from .engine import Engine
from .index import CORPUS, DATABASE, Index, build_index
from .mcq import parse_many, parse_question, solve as solve_mcq
from .runtime import RagError, config


def memory_info():
    if os.name != "nt":
        return {}
    class MemoryStatus(ctypes.Structure):
        _fields_ = [("length", ctypes.c_ulong), ("load", ctypes.c_ulong)] + [
            (key, ctypes.c_ulonglong) for key in
            ("total", "available", "total_page", "available_page", "total_virtual", "available_virtual", "extended")]
    status = MemoryStatus()
    status.length = ctypes.sizeof(status)
    if not ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(status)):
        return {}
    return {"total_gib": round(status.total / 1024**3, 2),
            "available_gib": round(status.available / 1024**3, 2)}


def doctor(settings, verify=False):
    root = runtime_home()
    result = {"python": sys.version.split()[0], "runtime_home": str(root), "memory": memory_info(),
              "cpu_threads": settings["threads"], "gpu_layers": 0,
              "context_tokens": settings["context_tokens"], "sqlite_fts5": False, "models": {}}
    with closing(sqlite3.connect(":memory:")) as db:
        db.execute("CREATE VIRTUAL TABLE check_fts USING fts5(text)")
        result["sqlite_fts5"] = True
    result["runtime_installed"] = (root / "runtime" / "b12628" / "llama-server.exe").is_file()
    for kind in ("embedding", "llm"):
        asset = ASSETS[kind]
        path = root / "models" / asset["filename"]
        ok = path.is_file() and path.stat().st_size == asset["size"]
        result["models"][kind] = {"present": ok, "path": str(path)}
        if verify and ok:
            result["models"][kind]["sha256_verified"] = sha256(path) == asset["sha256"]
    try:
        index = Index(settings)
        result["index"] = dict(index.stats, size_mb=round(DATABASE.stat().st_size / 1e6, 2))
        index.close()
    except (RagError, OSError, sqlite3.Error) as error:
        result["index"] = {"error": str(error)}
    return result


def print_answer(result, as_json=False):
    if as_json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return
    print("\n" + result["answer"])
    cited = set(result["citations"])
    for source in result["sources"]:
        if source["citation"] in cited:
            print(f"\n[{source['citation']}] {source['title']} | {source['section']}")
            print(f"  {source['article_path']} | {source['slides'] or 'shared feature'} | {source['status']}")
            print(f"  Evidence: {source['evidence_category']} | tiers: {source['confidence_tiers']}")
    print(f"\n({result['seconds']:.1f}s; local CPU inference)")


VERDICT_MARK = {"supported": "+", "contradicted": "x", "unsupported": "?"}


def print_mcq(question, result, as_json=False):
    if as_json:
        print(json.dumps(dict(result, question=question.stem,
                              options=[{"option": a, "text": b} for a, b in question.options]),
                         ensure_ascii=False, indent=2))
        return
    print()
    if result["answer"]:
        print(f"Answer: {result['answer']}. {question.text_of(result['answer'])}")
    else:
        print("Answer: no option is supported by this corpus.")
    if result.get("note"):
        print(f"  {result['note']}")
    if result.get("reason"):
        print(f"  {result['reason']}")
    if result.get("contested"):
        print("  Note: more than one option was judged supported. Read the excerpts before trusting this.")
    for verdict in result.get("verdicts", []):
        mark = VERDICT_MARK.get(verdict["verdict"], "?")
        cites = " " + " ".join(f"[{c}]" for c in verdict["sources"]) if verdict["sources"] else ""
        print(f"  {mark} {verdict['option']}: {verdict['note']}{cites}")
    cited = set(result.get("citations", []))
    for source in result.get("sources", []):
        if source["citation"] in cited:
            print(f"\n[{source['citation']}] {source['title']} | {source['section']}")
            print(f"  {source['article_path']} | {source['slides'] or 'shared feature'} | {source['status']}")
    if "correct" in result:
        print(f"\n  key {result['key']}: {'correct' if result['correct'] else 'WRONG'}")
    print(f"\n({result['seconds']:.1f}s; local CPU inference; mode: {result.get('mode')})")


def run_mcq(engine, questions, args, filters):
    scored = [q for q in questions if q.key]
    right = 0
    for number, question in enumerate(questions, 1):
        if len(questions) > 1:
            print(f"\n{'=' * 62}\nQ{number}: {question.stem}", file=sys.stderr)
        print("Retrieving per-option evidence and reasoning locally on CPU...", file=sys.stderr)
        try:
            result = solve_mcq(engine, question, allow_unknown=args.allow_unknown_terms, **filters)
        except RagError as error:
            print(f"Error: {error}", file=sys.stderr)
            continue
        print_mcq(question, result, args.json)
        right += bool(result.get("correct"))
    if scored:
        print(f"\nScored {right}/{len(scored)} against the supplied answer key.")
    return 0


def main(argv=None):
    parser = argparse.ArgumentParser(description="Offline ART403 RAG: Qwen2.5 3B + BGE-small + SQLite")
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("index", help="Build/resume the local index; no Internet required")
    health = commands.add_parser("doctor", help="Check local files, RAM and index readiness")
    health.add_argument("--verify", action="store_true", help="Recheck model SHA-256 hashes")
    for name in ("ask", "search", "chat", "mcq"):
        command = commands.add_parser(name)
        if name == "mcq":
            command.add_argument("question", nargs="?",
                                 help="Stem then one option per line; omit to read stdin")
            command.add_argument("--json", action="store_true", help="Print structured output")
            command.add_argument("--file", help="A file of blank-line-separated questions")
            command.add_argument("--allow-unknown-terms", action="store_true",
                                 help="Answer even when the stem names something absent from the corpus")
            command.add_argument("--exclude-distractors", action="store_true",
                                 help="Drop known-false exam claims and their corrections from evidence")
        elif name != "chat":
            command.add_argument("question")
            command.add_argument("--json", action="store_true", help="Print structured output")
        command.add_argument("--lexical", action="store_true", help="Use keyword retrieval only; search needs no models")
        command.add_argument("--sourced-only", action="store_true")
        command.add_argument("--module", type=int, choices=range(1, 9))
        command.add_argument("--article", help="Restrict to an exact corpus article_id")
        command.add_argument("--include-distractors", action="store_true", help="Include explicitly false exam claims AND their corrections")
        command.add_argument("--top-k", type=int, choices=range(1, 13), default=None)
    args = parser.parse_args(argv)
    settings = config()
    if args.command == "index":
        print(json.dumps(build_index(settings), indent=2))
        return 0
    if args.command == "doctor":
        result = doctor(settings, args.verify)
        print(json.dumps(result, indent=2))
        ready = result["runtime_installed"] and "error" not in result["index"] and all(
            m["present"] and m.get("sha256_verified", True) for m in result["models"].values())
        return 0 if ready else 1
    if args.top_k:
        settings["top_k"] = args.top_k
    filters = {key: getattr(args, key) for key in ("lexical", "sourced_only", "module", "article")}
    if args.command == "mcq":
        # MCQ distractors are often the corpus's own known-false exam claims; the
        # correction travels with them, so they are included unless asked otherwise.
        filters["include_distractors"] = not args.exclude_distractors
    else:
        filters["include_distractors"] = args.include_distractors
    if args.command in {"ask", "chat", "mcq"}:
        memory = memory_info()
        if memory.get("available_gib", 16) < 4:
            print(f"Available RAM: {memory.get('available_gib')} GiB. Closing large apps can reduce paging and improve speed.", file=sys.stderr)
    questions = []
    if args.command == "mcq":
        if args.file:
            questions = parse_many(Path(args.file).read_text(encoding="utf-8"))
        elif args.question:
            questions = [parse_question(args.question)]
        else:
            print("Reading the question from stdin; finish with Ctrl+Z then Enter.", file=sys.stderr)
            questions = parse_many(sys.stdin.read())
    with Engine(settings) as engine:
        if args.command == "mcq":
            return run_mcq(engine, questions, args, filters)
        if args.command == "search":
            sources = engine.search(args.question, **filters)
            if args.json:
                print(json.dumps(sources, ensure_ascii=False, indent=2))
            else:
                for number, row in enumerate(sources, 1):
                    score = f"; cosine {row['similarity']:.3f}" if row.get("similarity") is not None else ""
                    print(f"\n[S{number}] {row['title']} | {row['section']} ({row['status']}{score})")
                    print(f"{row['article_path']} | {row['slides']}\n{row['text']}")
                if not sources:
                    print("No matching evidence.")
        elif args.command == "ask":
            print("Retrieving evidence and generating locally on CPU...", file=sys.stderr)
            print_answer(engine.ask(args.question, **filters), args.json)
        else:
            print("ART403 offline chat. Each question is independent. Type /exit to quit.\nModels stay loaded until you exit.")
            while True:
                try:
                    question = input("\nYou: ").strip()
                except EOFError:
                    break
                if question.lower() in {"/exit", "/quit"}:
                    break
                if not question:
                    continue
                try:
                    print("Retrieving evidence and generating locally on CPU...", file=sys.stderr)
                    print_answer(engine.ask(question, **filters))
                except RagError as error:
                    print(f"Error: {error}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8")
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\nStopped. Local model processes have been closed.", file=sys.stderr)
        sys.exit(130)
    except (RagError, OSError, sqlite3.Error) as error:
        print(f"Error: {error}", file=sys.stderr)
        sys.exit(1)
