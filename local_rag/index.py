"""Lossless, token-bounded corpus ingestion and a small persistent hybrid index."""
from __future__ import annotations

import array
from collections import Counter
from contextlib import closing, contextmanager
import hashlib
import json
import os
from pathlib import Path
import re
import sqlite3
import sys
import time

from .bootstrap import ASSETS, HERE, runtime_home, sha256
from .runtime import RagError, Server

ROOT = HERE.parent
CORPUS = ROOT / "retrieval_chunks.jsonl"
DATA = HERE / "data"
DATABASE = DATA / "index.sqlite3"
SCHEMA_VERSION = 2
QUERY_PREFIX = "Represent this sentence for searching relevant passages: "
STOPWORDS = set("a an the and or of in on at to for from by with is are was were be been being it its this that these those what which who when where why how does do did can could would should please tell me about explain describe according corpus course lecture answer question".split())
NAVIGATION = {"Connected Features", "Applied To", "Connection Scope", "Sources"}


def pack(vector):
    values = array.array("f", vector)
    if sys.byteorder != "little":
        values.byteswap()
    return values.tobytes()


def unpack(blob):
    values = array.array("f")
    values.frombytes(blob)
    if sys.byteorder != "little":
        values.byteswap()
    return values


def corpus_rows(path: Path):
    seen = set()
    with path.open(encoding="utf-8-sig") as stream:
        for number, line in enumerate(stream, 1):
            if not line.strip():
                continue
            try:
                row = json.loads(line)
                for key in ("id", "article_id", "title", "section", "text", "article_path",
                            "status", "slides", "source", "evidence_category"):
                    if not isinstance(row[key], str) or (key not in {"slides", "source"} and not row[key].strip()):
                        raise ValueError(f"invalid {key}")
                if row["id"] in seen:
                    raise ValueError(f"duplicate id {row['id']}")
                if row["status"] not in {"draft", "sourced"}:
                    raise ValueError("invalid status")
                if type(row["contains_false_exam_claim"]) is not bool:
                    raise ValueError("contains_false_exam_claim must be boolean")
                if not isinstance(row["confidence_tiers"], list) or any(t not in (1, 2, 3) for t in row["confidence_tiers"]):
                    raise ValueError("invalid confidence_tiers")
                link = Path(row["article_path"])
                if link.is_absolute() or ".." in link.parts or link.suffix != ".md":
                    raise ValueError("article_path must be a relative Markdown path within the corpus")
                seen.add(row["id"])
                yield row
            except (ValueError, KeyError, TypeError) as error:
                raise RagError(f"Invalid corpus record on line {number}: {error}") from error
    if not seen:
        raise RagError("The corpus has no records")


def split_text(text: str, count_tokens, limit: int, overlap_words: int):
    """Keep original Unicode slices; repeat title and whole-word overlap, never truncate."""
    if count_tokens(text) <= limit:
        return [(text, 0, len(text))]
    first, separator, body = text.partition("\n")
    prefix = first + "\n" if separator else ""
    base = len(prefix)
    if not separator:
        body = text
    if prefix and count_tokens(prefix) > limit // 2:
        prefix, body, base = "", text, 0
    spans = [(m.start(), m.end()) for m in re.finditer(r"\S+\s*", body)]
    if spans:
        spans[0] = (0, spans[0][1])
    result, start = [], 0
    while start < len(spans):
        low, high, best = start + 1, len(spans), start
        while low <= high:
            mid = (low + high) // 2
            part = body[spans[start][0]:spans[mid - 1][1]]
            if count_tokens(prefix + part) <= limit:
                best, low = mid, mid + 1
            else:
                high = mid - 1
        if best == start:
            # A single URL/unbroken string can exceed the tokenizer limit. Slice by characters.
            a, end = spans[start]
            while a < end:
                lo, hi, fit = a + 1, end, a
                while lo <= hi:
                    mid = (lo + hi) // 2
                    if count_tokens(prefix + body[a:mid]) <= limit:
                        fit, lo = mid, mid + 1
                    else:
                        hi = mid - 1
                if fit == a:
                    raise RagError("Chunk budget cannot hold the title and one character")
                result.append((prefix + body[a:fit], base + a, base + fit))
                a = fit
            start += 1
        else:
            a, b = spans[start][0], spans[best - 1][1]
            result.append((prefix + body[a:b], base + a, base + b))
            if best == len(spans):
                break
            start = max(start + 1, best - overlap_words)
    return result


def embedding_signature(settings):
    return f"bge-small-en-v1.5:q8_0:{ASSETS['embedding']['sha256']}:cls:384:v1:tokens{settings['chunk_tokens']}:overlap{settings['overlap_words']}"


@contextmanager
def index_lock(database):
    lock_path = Path(database).with_suffix(".lock")
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    stream = lock_path.open("a+b")
    if not stream.tell():
        stream.write(b"0")
        stream.flush()
    stream.seek(0)
    try:
        if os.name == "nt":
            import msvcrt
            msvcrt.locking(stream.fileno(), msvcrt.LK_NBLCK, 1)
        else:
            import fcntl
            fcntl.flock(stream.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
    except OSError as error:
        stream.close()
        raise RagError("Another index build is running. Wait for it to finish.") from error
    try:
        yield
    finally:
        stream.seek(0)
        if os.name == "nt":
            msvcrt.locking(stream.fileno(), msvcrt.LK_UNLCK, 1)
        else:
            fcntl.flock(stream.fileno(), fcntl.LOCK_UN)
        stream.close()


def build_index(settings, corpus=CORPUS, database=DATABASE, progress=print):
    with index_lock(database):
        return _build_index(settings, corpus, database, progress)


def _build_index(settings, corpus, database, progress):
    corpus, database = Path(corpus), Path(database)
    if not corpus.is_file():
        raise RagError(f"Corpus not found: {corpus}")
    rows = list(corpus_rows(corpus))  # Validate before replacing an existing index.
    fingerprint = sha256(corpus)
    signature = embedding_signature(settings)
    database.parent.mkdir(parents=True, exist_ok=True)
    if database.exists():
        with closing(sqlite3.connect(database)) as existing:
            meta = dict(existing.execute("SELECT key, value FROM meta"))
            if (meta.get("corpus_sha256") == fingerprint and meta.get("embedding_signature") == signature
                    and meta.get("schema_version") == str(SCHEMA_VERSION)):
                progress("Index already current; no embeddings recomputed.")
                return json.loads(meta["stats"])
    temp = database.with_suffix(".building.sqlite3")
    if temp.exists():
        temp.unlink()
    cache = sqlite3.connect(database.parent / "embedding-cache.sqlite3")
    cache.execute("CREATE TABLE IF NOT EXISTS cache (key TEXT PRIMARY KEY, vector BLOB NOT NULL)")
    db = sqlite3.connect(temp)
    db.executescript("""
        CREATE TABLE meta (key TEXT PRIMARY KEY, value TEXT NOT NULL);
        CREATE TABLE chunks (id TEXT UNIQUE NOT NULL, parent_id TEXT NOT NULL,
            title TEXT NOT NULL, section TEXT NOT NULL, text TEXT NOT NULL,
            article_id TEXT NOT NULL, status TEXT NOT NULL, false_claim INTEGER NOT NULL,
            metadata TEXT NOT NULL, vector BLOB NOT NULL);
        CREATE INDEX article_lookup ON chunks(article_id, section);
        CREATE VIRTUAL TABLE search USING fts5(title, section, text,
            tokenize='porter unicode61 remove_diacritics 2');
    """)
    started, chunks, cached = time.monotonic(), 0, 0
    try:
        with Server("embedding", settings) as embedder:
            for number, row in enumerate(rows, 1):
                pieces = split_text(row["text"], embedder.tokens, settings["chunk_tokens"], settings["overlap_words"])
                for part, (text, start, end) in enumerate(pieces, 1):
                    key = hashlib.sha256((signature + "\n" + text).encode("utf-8")).hexdigest()
                    found = cache.execute("SELECT vector FROM cache WHERE key=?", (key,)).fetchone()
                    if found:
                        vector = found[0]
                        cached += 1
                    else:
                        vector = pack(embedder.embed([text])[0])
                        cache.execute("INSERT INTO cache VALUES (?,?)", (key, vector))
                    metadata = dict(row, parent_id=row["id"], id=f"{row['id']}~{part}", text=text,
                                    part=part, parts=len(pieces), char_start=start, char_end=end,
                                    parent_content_sha256=row.get("content_sha256"),
                                    content_sha256=hashlib.sha256(text.encode("utf-8")).hexdigest(),
                                    parent_token_count=row.get("token_count"),
                                    embedding_token_count=embedder.tokens(text))
                    metadata.pop("token_count", None)  # Parent counts use a different tokenizer.
                    db.execute("INSERT INTO chunks VALUES (?,?,?,?,?,?,?,?,?,?)", (
                        metadata["id"], row["id"], row["title"], row["section"], text,
                        row["article_id"], row["status"], int(row["contains_false_exam_claim"]),
                        json.dumps(metadata, ensure_ascii=False), vector))
                    db.execute("INSERT INTO search VALUES (?,?,?)", (row["title"], row["section"], text))
                    chunks += 1
                if number % 50 == 0:
                    cache.commit()
                    db.commit()
                    progress(f"Indexed {number}/{len(rows)} source records ({chunks} passages, {cached} cached)")
        stats = {"source_records": len(rows), "passages": chunks,
                 "articles": len({r["article_id"] for r in rows}), "cached_embeddings": cached,
                 "build_seconds": round(time.monotonic() - started, 2),
                 "statuses": dict(Counter(r["status"] for r in rows))}
        for key, value in {"corpus_sha256": fingerprint, "embedding_signature": signature,
                           "schema_version": str(SCHEMA_VERSION), "stats": json.dumps(stats)}.items():
            db.execute("INSERT INTO meta VALUES (?,?)", (key, value))
        db.commit()
        cache.commit()
    except BaseException:
        cache.commit()  # Successful embedding work survives an interrupted build.
        raise
    finally:
        db.close()
        cache.close()
    try:
        temp.replace(database)  # Only a fully completed index replaces the previous good copy.
    except PermissionError as error:
        raise RagError("Close other RAG sessions before replacing the index, then rerun index. Embeddings are cached.") from error
    progress(f"Index ready: {chunks} passages from {len(rows)} records.")
    return stats


def query_terms(query):
    return list(dict.fromkeys(t for t in re.findall(r"[^\W_]+", query.lower()) if t not in STOPWORDS and len(t) > 1))[:40]


class Index:
    def __init__(self, settings, corpus=CORPUS, database=DATABASE):
        self.settings = settings
        if not Path(database).is_file():
            raise RagError("Index missing. Run: python -m local_rag index")
        self.db = sqlite3.connect(Path(database).resolve().as_uri() + "?mode=ro", uri=True)
        try:
            meta = dict(self.db.execute("SELECT key, value FROM meta"))
            if meta.get("schema_version") != str(SCHEMA_VERSION):
                raise RagError("Index format changed. Run: python -m local_rag index")
            if meta.get("corpus_sha256") != sha256(Path(corpus)):
                raise RagError("Corpus has changed. Run: python -m local_rag index")
            if meta.get("embedding_signature") != embedding_signature(settings):
                raise RagError("Embedding/chunk configuration changed. Run: python -m local_rag index")
            self.stats = json.loads(meta["stats"])
            self.rows = {}
            self.vectors = {}
            for rowid, metadata, vector in self.db.execute("SELECT rowid, metadata, vector FROM chunks"):
                self.rows[rowid] = json.loads(metadata)
                self.vectors[rowid] = unpack(vector)
                if len(self.vectors[rowid]) != 384:
                    raise RagError("Invalid vector in index. Rebuild the index.")
        except BaseException:
            self.db.close()
            raise

    def search(self, query, embedder=None, *, limit=6, sourced_only=False,
               module=None, include_distractors=False, article=None):
        query = query.strip()
        if not query or len(query) > 2000:
            raise RagError("Enter a question between 1 and 2,000 characters")
        allowed = {i for i, r in self.rows.items()
                   if r["section"] not in NAVIGATION
                   and (include_distractors or not r["contains_false_exam_claim"])
                   and (not sourced_only or r["status"] == "sourced")
                   and (module is None or re.search(rf"\bM{module}:", r["slides"]))
                   and (article is None or r["article_id"] == article)}
        terms = query_terms(query)
        lexical = []
        if terms:
            expression = " OR ".join('"' + t + '"' for t in terms)
            # Apply filters before ranking/truncation; rare module matches must survive.
            lexical = [i for i, in self.db.execute(
                "SELECT rowid FROM search WHERE search MATCH ? ORDER BY bm25(search,4.0,1.5,1.0)",
                (expression,)) if i in allowed][:60]
        similarities, dense = {}, []
        if embedder:
            text = QUERY_PREFIX + query
            if embedder.tokens(text) > 512:
                raise RagError("Question exceeds the embedding model's 512-token limit; shorten it.")
            vector = embedder.embed([text])[0]
            similarities = {i: sum(a * b for a, b in zip(vector, self.vectors[i])) for i in allowed}
            dense = sorted(allowed, key=lambda i: similarities[i], reverse=True)[:60]
        scores = {}
        for ranking in (lexical, dense):
            for rank, i in enumerate(ranking, 1):
                scores[i] = scores.get(i, 0) + 1 / (60 + rank)
        ranking = sorted(scores, key=lambda i: scores[i], reverse=True)
        # No article can consume every context slot, and near-identical split parts are collapsed.
        results, per_article, parents = [], Counter(), set()
        for i in ranking:
            row = self.rows[i]
            if row["parent_id"] in parents or per_article[row["article_id"]] >= 3:
                continue
            results.append(dict(row, score=scores[i], similarity=similarities.get(i),
                                lexical_match=i in lexical))
            parents.add(row["parent_id"])
            per_article[row["article_id"]] += 1
            if len(results) == limit:
                break
        return results

    def companions(self, hits, *, sourced_only=False, module=None):
        """Attach catalogue corrections and attribution limits for retrieved entities."""
        articles = list(dict.fromkeys(r["article_id"] for r in hits))[:3]
        already = {r["id"] for r in hits}
        companions = []
        for section in ("External Checks", "Attribution Note"):
            for row in self.rows.values():
                if (row["article_id"] in articles and row["section"] == section
                        and row["id"] not in already
                        and (not sourced_only or row["status"] == "sourced")
                        and (module is None or re.search(rf"\bM{module}:", row["slides"]))):
                    companions.append(dict(row, score=0, similarity=None, companion=True))
        return companions

    def close(self):
        self.db.close()
