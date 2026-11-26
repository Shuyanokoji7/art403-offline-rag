"""Offline regression tests. No model downloads or running servers required."""
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from .engine import REFUSAL, check_named_support, evidence_fallback, messages_for, validate_answer
from .index import Index, build_index, corpus_rows, index_lock, split_text
from .runtime import RagError, config


def record(identifier="lotus", text="Lotus Mahal has cusped arches.", **overrides):
    row = {"id": identifier, "article_id": identifier, "title": "Lotus Mahal", "section": "Structure",
           "text": text, "article_path": "articles/lotus.md", "status": "sourced", "slides": "M1:23",
           "source": "ART403 Module 1", "evidence_category": "curated_analysis", "confidence_tiers": [1],
           "contains_false_exam_claim": False, "content_sha256": hashlib.sha256(text.encode()).hexdigest()}
    return dict(row, **overrides)


class FakeEmbedder:
    calls = 0
    def __init__(self, *args):
        pass
    def __enter__(self):
        return self
    def __exit__(self, *args):
        pass
    def tokens(self, text):
        return len(text) // 3 + 2
    def embed(self, texts):
        FakeEmbedder.calls += len(texts)
        return [[1.0] + [0.0] * 383 for _ in texts]


class RagTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.corpus = self.root / "input.jsonl"
        self.database = self.root / "index.sqlite3"
        self.settings = config()
        FakeEmbedder.calls = 0

    def tearDown(self):
        self.temp.cleanup()

    def write(self, rows):
        self.corpus.write_text("\n".join(json.dumps(r, ensure_ascii=False) for r in rows), encoding="utf-8")

    def build(self):
        with patch("local_rag.index.Server", FakeEmbedder):
            return build_index(self.settings, self.corpus, self.database, progress=lambda _: None)

    def test_unicode_split_preserves_every_character_and_budget(self):
        text = "Ceramic — Motifs\n  " + ("café 日本語 flowers, arches.\n" * 50)
        count = lambda x: len(x) + 2
        pieces = split_text(text, count, 100, 3)
        covered = set(range(text.index("\n") + 1))
        for chunk, start, end in pieces:
            self.assertLessEqual(count(chunk), 100)
            self.assertTrue(chunk.endswith(text[start:end]))
            covered.update(range(start, end))
        self.assertEqual(covered, set(range(len(text))))

    def test_unbroken_long_url_is_split_without_loss(self):
        text = "Source\nhttps://example.test/" + "abcdefgh" * 200
        pieces = split_text(text, len, 100, 3)
        covered = set(range(len("Source\n")))
        for chunk, start, end in pieces:
            self.assertLessEqual(len(chunk), 100)
            self.assertTrue(chunk.endswith(text[start:end]))
            covered.update(range(start, end))
        self.assertEqual(covered, set(range(len(text))))

    def test_duplicate_ids_and_path_escape_rejected(self):
        self.write([record(), record()])
        with self.assertRaisesRegex(RagError, "duplicate"):
            list(corpus_rows(self.corpus))
        self.write([record(article_path="../outside.md")])
        with self.assertRaisesRegex(RagError, "article_path"):
            list(corpus_rows(self.corpus))

    def test_index_reuses_embeddings_and_rejects_stale_corpus(self):
        self.write([record()])
        self.build()
        count = FakeEmbedder.calls
        self.build()
        self.assertEqual(FakeEmbedder.calls, count)
        self.write([record(), record("other", text="A different passage about Hampi")])
        with self.assertRaisesRegex(RagError, "Corpus has changed"):
            Index(self.settings, self.corpus, self.database)
        self.assertEqual(self.build()["cached_embeddings"], 1)

    def test_failed_build_preserves_previous_index(self):
        self.write([record()])
        self.build()
        before = self.database.read_bytes()
        self.write([record(), record()])
        with self.assertRaises(RagError):
            self.build()
        self.assertEqual(before, self.database.read_bytes())

    def test_filtering_excludes_distractors_drafts_navigation(self):
        self.write([record(), record("draft", status="draft"),
                    record("false", contains_false_exam_claim=True, section="Distinctions"),
                    record("nav", section="Connected Features"), record("module2", slides="M2:8")])
        self.build()
        index = Index(self.settings, self.corpus, self.database)
        try:
            hits = index.search("Lotus", sourced_only=True, module=1)
            self.assertEqual([r["article_id"] for r in hits], ["lotus"])
            hits = index.search("Lotus", sourced_only=True, module=1, include_distractors=True)
            self.assertEqual({r["article_id"] for r in hits}, {"lotus", "false"})
        finally:
            index.close()

    def test_fts_operator_input_is_data(self):
        self.write([record()])
        self.build()
        index = Index(self.settings, self.corpus, self.database)
        try:
            self.assertTrue(index.search('"Lotus" OR (* NOT title:foo)'))
        finally:
            index.close()

    def test_catalogue_correction_is_attached(self):
        self.write([record(), record("correction", article_id="lotus", section="External Checks",
                                    text="Catalogue corrects the lecture date.", evidence_category="external_verification")])
        self.build()
        index = Index(self.settings, self.corpus, self.database)
        try:
            companions = index.companions([dict(record(), id="lotus~1")])
            self.assertEqual(companions[0]["section"], "External Checks")
        finally:
            index.close()

    def test_model_or_chunk_config_mismatch_rejected(self):
        self.write([record()])
        self.build()
        changed = dict(self.settings, chunk_tokens=self.settings["chunk_tokens"] + 1)
        with self.assertRaisesRegex(RagError, "configuration changed"):
            Index(changed, self.corpus, self.database)

    def test_invented_or_absent_citations_are_rejected(self):
        for labels in ([], ["S99"]):
            with self.assertRaises(RagError):
                validate_answer(json.dumps({"paragraphs": [{"text": "It was made in 1876.", "sources": labels}], "insufficient_evidence": False}), [record()])
        answer, citations = validate_answer(json.dumps({"paragraphs": [{"text": "Cusped arches.", "sources": ["S1"]}], "insufficient_evidence": False}), [record()])
        self.assertEqual(citations, ["S1"])
        self.assertEqual(answer, "Cusped arches. [S1]")

    def test_refusal_does_not_emit_uncited_model_claims(self):
        answer, citations = validate_answer(json.dumps({"paragraphs": [{"text": "Invented fact"}], "insufficient_evidence": True}), [])
        self.assertEqual(answer, REFUSAL)
        self.assertFalse(citations)

    def test_prompt_preserves_evidence_categories(self):
        evidence = record(status="draft", evidence_category="unresolved_external_attribution", confidence_tiers=[3])
        prompt = messages_for("Who made it?", [evidence])
        body = json.loads(prompt[1]["content"])
        self.assertEqual(body["evidence"][0]["status"], "draft")
        self.assertEqual(body["evidence"][0]["confidence_tiers"], [3])

    def test_simultaneous_index_build_is_rejected(self):
        with index_lock(self.database):
            with self.assertRaisesRegex(RagError, "Another index build"):
                with index_lock(self.database):
                    pass

    def test_unsupported_object_or_year_uses_exact_source_fallback(self):
        sources = [dict(record(), citation="S1")]
        for answer in ("Lotus Mahal is unlike Charminar. [S1]", "Lotus Mahal was built in 1876. [S1]"):
            with self.assertRaises(RagError):
                check_named_support(answer, ["S1"], sources, {"Lotus Mahal", "Charminar"})
        check_named_support("Lotus Mahal has cusped arches. [S1]", ["S1"], sources, {"Lotus Mahal"})
        answer, citations = evidence_fallback(sources, ["S1"])
        self.assertIn("> " + sources[0]["text"], answer)
        self.assertNotIn("Charminar", answer)
        self.assertEqual(citations, ["S1"])


if __name__ == "__main__":
    unittest.main()
