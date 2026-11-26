"""Offline regression tests for multiple-choice solving. No models or servers required."""
import unittest

from .mcq import (NO_ANSWER, check_years, fuse, parse_many, parse_question, schema,
                  unknown_subjects, validate)
from .runtime import RagError
from .test_rag import record

QUESTION = """Which statement best describes the Lotus Mahal?
A. A timber pavilion built in 1631
B. A garden pavilion with cusped arches
C. A rock-cut cave shrine
D. A colonial chapel"""


def sources(count=3):
    return [dict(record(f"r{i}", f"Evidence {i}"), citation=f"S{i}") for i in range(1, count + 1)]


class ParsingTests(unittest.TestCase):
    def test_parses_stem_and_options(self):
        question = parse_question(QUESTION)
        self.assertEqual(question.letters, ["A", "B", "C", "D"])
        self.assertEqual(question.text_of("B"), "A garden pavilion with cusped arches")
        self.assertIn("Lotus Mahal", question.stem)
        self.assertIsNone(question.key)

    def test_accepts_bracket_and_paren_markers(self):
        question = parse_question("Stem?\n(a) first\nB) second\nc: third")
        self.assertEqual(question.letters, ["A", "B", "C"])
        self.assertEqual(question.text_of("C"), "third")

    def test_reads_and_validates_answer_key(self):
        self.assertEqual(parse_question(QUESTION + "\nAnswer: C").key, "C")
        with self.assertRaises(RagError):
            parse_question(QUESTION + "\nAnswer: F")

    def test_joins_wrapped_option_lines(self):
        question = parse_question("Stem?\nA. first option\n  continued here\nB. second")
        self.assertEqual(question.text_of("A"), "first option continued here")

    def test_rejects_malformed_questions(self):
        for bad in ("A. only one option", "Stem with no options at all",
                    "Stem?\nA. one\nA. duplicate", "Stem?\nB. out\nC. of order"):
            with self.assertRaises(RagError):
                parse_question(bad)

    def test_splits_a_file_into_questions(self):
        questions = parse_many(QUESTION + "\n\n" + QUESTION.replace("Lotus Mahal", "Hampi"))
        self.assertEqual(len(questions), 2)
        self.assertIn("Hampi", questions[1].stem)

    def test_keeps_a_stem_separated_from_its_options(self):
        questions = parse_many("Q1 stem?\n\nA. one\nB. two")
        self.assertEqual(len(questions), 1)
        self.assertEqual(questions[0].stem, "Q1 stem?")


class CoverageTests(unittest.TestCase):
    def test_flags_proper_nouns_absent_from_the_corpus(self):
        self.assertEqual(unknown_subjects("What do Batala prints show?", {"lotus", "mahal"}),
                         ["Batala"])

    def test_ignores_sentence_openers_and_known_words(self):
        self.assertEqual(unknown_subjects("Which Lotus Mahal arch is cusped?",
                                          {"lotus", "mahal", "arch", "cusped"}), [])

    def test_reports_each_unknown_once(self):
        self.assertEqual(unknown_subjects("Batala and Batala again, plus Kalighat", set()),
                         ["Batala", "Kalighat"])

    def test_treats_a_possessive_as_a_mention_of_the_name(self):
        self.assertEqual(unknown_subjects("How did Manet's view differ?", {"manet"}), [])
        self.assertEqual(unknown_subjects("What of Van Gogh’s letters?", {"gogh"}), [])

    def test_accepts_a_hyphenated_name_the_corpus_shortens(self):
        self.assertEqual(unknown_subjects("Toulouse-Lautrec's poster?", {"lautrec"}), [])

    def test_still_flags_a_genuinely_absent_name(self):
        self.assertEqual(unknown_subjects("What of Batala's prints?", {"manet", "gogh"}),
                         ["Batala's"])


class FusionTests(unittest.TestCase):
    def rows(self, *ids):
        return [dict(record(i), id=i, parent_id=i, article_id=i, similarity=0.5) for i in ids]

    def test_rewards_passages_found_by_several_option_queries(self):
        shared, only = self.rows("shared")[0], self.rows("only")[0]
        result = fuse([[only, shared], [shared], [shared]], limit=2)
        self.assertEqual(result[0]["id"], "shared")

    def test_collapses_split_parts_of_one_passage(self):
        first, second = self.rows("a", "b")
        second["parent_id"] = first["parent_id"]
        self.assertEqual(len(fuse([[first, second]], limit=5)), 1)

    def test_caps_passages_from_a_single_article(self):
        rows = self.rows("a", "b", "c", "d")
        for row in rows:
            row["article_id"] = "same"
        self.assertEqual(len(fuse([rows], limit=10)), 3)


class ValidationTests(unittest.TestCase):
    def setUp(self):
        self.question = parse_question(QUESTION)
        self.sources = sources()

    def payload(self, **overrides):
        body = {"options": [{"option": letter, "verdict": "unsupported", "note": "n", "sources": []}
                            for letter in "ABCD"],
                "insufficient_evidence": False, "answer": "B", "reason": "because", "sources": ["S1"]}
        body.update(overrides)
        import json
        return json.dumps(body)

    def test_accepts_a_committed_letter(self):
        result = validate(self.payload(), self.question, self.sources)
        self.assertEqual(result["answer"], "B")
        self.assertEqual(result["citations"], ["S1"])
        self.assertEqual(len(result["verdicts"]), 4)

    def test_treats_no_answer_as_abstention(self):
        result = validate(self.payload(answer=NO_ANSWER, sources=[]), self.question, self.sources)
        self.assertIsNone(result["answer"])
        self.assertTrue(result["insufficient_evidence"])

    def test_rejects_a_letter_outside_the_options(self):
        with self.assertRaises(RagError):
            validate(self.payload(answer="E"), self.question, self.sources)

    def test_rejects_an_invented_citation(self):
        with self.assertRaises(RagError):
            validate(self.payload(sources=["S9"]), self.question, self.sources)

    def test_rejects_a_choice_with_no_citation(self):
        with self.assertRaises(RagError):
            validate(self.payload(sources=[]), self.question, self.sources)

    def test_rejects_invalid_json(self):
        with self.assertRaises(RagError):
            validate("not json", self.question, self.sources)


class YearCheckTests(unittest.TestCase):
    def setUp(self):
        self.question = parse_question(QUESTION)
        self.sources = [dict(record("r1", "Built in 1565 at Hampi."), citation="S1")]

    def test_allows_a_year_present_in_the_evidence(self):
        check_years("Dated 1565.", self.question, ["S1"], self.sources)

    def test_allows_a_year_quoted_from_the_question(self):
        # 1631 appears in option A; naming a distractor's date is not a hallucination.
        check_years("Option A's 1631 is wrong.", self.question, ["S1"], self.sources)

    def test_rejects_a_year_the_model_invented(self):
        with self.assertRaises(RagError):
            check_years("Built in 1742.", self.question, ["S1"], self.sources)


class SchemaTests(unittest.TestCase):
    def test_constrains_the_answer_to_real_letters(self):
        built = schema(["A", "B", "C"], sources(2))
        self.assertEqual(built["properties"]["answer"]["enum"], ["A", "B", "C", NO_ANSWER])
        self.assertEqual(built["properties"]["sources"]["items"]["enum"], ["S1", "S2"])

    def test_requires_a_verdict_for_every_option(self):
        built = schema(["A", "B", "C", "D"], sources(1))
        self.assertEqual(built["properties"]["options"]["minItems"], 4)
        self.assertEqual(built["properties"]["options"]["maxItems"], 4)

    def test_orders_elimination_before_the_committed_answer(self):
        keys = list(schema(["A", "B"], sources(1))["properties"])
        self.assertLess(keys.index("options"), keys.index("answer"))


if __name__ == "__main__":
    unittest.main()
