import tempfile
import unittest
from pathlib import Path

from epivra.citations import render, validate
from epivra.storage import Store


class CitationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.store = Store(Path(self.temp.name) / "store.db")
        self.store.create("s", "Question", {})
        self.a = self.store.put(
            "s", "source", {"text": "First passage", "origin": "https://example.org/a"}
        )
        self.b = self.store.put(
            "s", "source", {"text": "Second passage", "origin": "notes.txt"}
        )
        self.resolve = lambda ref: self.store.get("s", ref)

    def tearDown(self):
        self.store.close()
        self.temp.cleanup()

    def report(self, text, evidence=None):
        evidence = evidence if evidence is not None else [self.a.ref, self.b.ref]
        result = {**render(text, evidence, self.resolve), "evidence": evidence}
        validate(result, self.resolve)
        return result

    def test_first_appearance_not_evidence_order_and_repeat(self):
        report = self.report(
            f"B [[cite:{self.b.ref}]]. A [[cite:{self.a.ref}]]. B [[cite:{self.b.ref}]]."
        )
        self.assertTrue(report["text"].startswith("B [1]. A [2]. B [1]."))
        self.assertIn("1. notes.txt", report["text"])
        self.assertNotIn("#source-", report["text"])
        self.assertEqual([self.b.ref, self.a.ref, self.b.ref], report["citations"])

    def test_saved_title_is_used_without_changing_source_binding(self):
        source = self.store.put(
            "s",
            "source",
            {
                "text": "Evidence",
                "title": "Research [2026]",
                "origin": "https://example.org/paper",
            },
        )
        report = self.report(f"Finding [[cite:{source.ref}]].", [source.ref])
        self.assertIn(
            r"[Research \[2026\]](<https://example.org/paper>)", report["text"]
        )
        self.assertEqual([source.ref], report["citations"])

    def test_source_and_two_passages_share_source_number(self):
        note = self.store.put(
            "s",
            "note",
            {"source": self.a.ref, "quote": "First", "offset": 0},
            (self.a.ref,),
        )
        note2 = self.store.put(
            "s",
            "note",
            {"source": self.a.ref, "quote": "passage", "offset": 6},
            (self.a.ref,),
        )
        report = self.report(
            f"One [[cite:{note.ref}]] two [[cite:{note2.ref}]] all [[cite:{self.a.ref}]]"
        )
        self.assertTrue(report["text"].startswith("One [1] two [1] all [1]"))

    def test_zero_citations_and_markdown_code_are_preserved(self):
        for text in [
            "Pure reasoning.",
            "    arr = [1]\n",
            "~~~python\narr = [1]\n~~~~\n",
            "```python\narr = [1]",
            "`[1]` and ``a `[2]` b``",
            "\\[1]",
            "Code:\n\n> ```\n> [1]\n> ```",
        ]:
            with self.subTest(text=text):
                self.assertEqual(text, self.report(text, [])["text"])

    def test_unknown_and_malformed_and_manual_references_are_rejected(self):
        for text in [
            "[[cite:" + "a" * 64 + "]]",
            "[[cite:no]]",
            "Claim [1]",
            "Claim [1](https://example.org)",
            "Claim [1,2]",
            "Claim [1-3]",
            "Lone ` opener.\n\n[[cite:" + "a" * 64 + "]].\n\nLone ` closer.",
        ]:
            with self.subTest(text=text), self.assertRaises(ValueError):
                self.report(text)

    def test_wrong_evidence_and_bad_passage(self):
        with self.assertRaises(ValueError):
            self.report(f"[[cite:{self.a.ref}]]", [self.b.ref])
        note = self.store.put(
            "s",
            "note",
            {"source": self.a.ref, "quote": "First", "offset": 1},
            (self.a.ref,),
        )
        with self.assertRaises(ValueError):
            self.report(f"[[cite:{note.ref}]]")
        other = self.store.create("other", "Other", {})
        source = self.store.put(
            "other", "source", {"text": "Foreign"}, (other.direction,)
        )
        with self.assertRaises(ValueError):
            self.report(f"[[cite:{source.ref}]]")

    def test_bibliography_cannot_be_swallowed_by_unclosed_code(self):
        with self.assertRaisesRegex(ValueError, "Close the fenced"):
            self.report(f"Claim [[cite:{self.a.ref}]]\n\n```python\n[1]")
        report = self.report(f"Claim [[cite:{self.a.ref}]]\n\n~~~python\n[1]\n~~~~")
        self.assertTrue(report["text"].startswith("Claim [1]"))

    def test_link_backtick_does_not_mask_visible_invalid_citation(self):
        text = "[Docs](https://example.org/`) Claim [[cite:bad]] `sample`"
        with self.assertRaises(ValueError):
            self.report(text, [])
        with self.assertRaises(ValueError):
            validate({"text": text, "evidence": []}, self.resolve)

    def test_container_can_implicitly_end_fence_before_bibliography(self):
        for prefix in ("> ```\n> sample code\n\n", "- ```\n  sample code\n\n"):
            with self.subTest(prefix=prefix):
                report = self.report(prefix + f"Claim [[cite:{self.a.ref}]]")
                self.assertTrue(report["text"].startswith(prefix + "Claim [1]"))

    def test_preserves_locations_with_containers_code_links_and_repeated_markers(self):
        marker = f"[[cite:{self.a.ref}]]"
        for text in (
            f"> `{marker}` then {marker}",
            f"- [Docs](https://example.org/`) {marker} `sample`",
            f"## Heading {marker}\r\n\r\n> Quote {marker}",
            f"[Label {marker}](https://example.org)",
        ):
            with self.subTest(text=text):
                report = self.report(text)
                self.assertIn("[1]", report["text"])

    def test_commonmark_newline_mapping_preserves_original_characters(self):
        for separator in ("\r", "\r\n", "\n", "\u2028", "\v", "\u0085"):
            with self.subTest(separator=repr(separator)):
                report = self.report(f"Text{separator}Claim [[cite:{self.a.ref}]]")
                self.assertTrue(report["text"].startswith(f"Text{separator}Claim [1]"))

    def test_html_is_literal_like_the_web_report_renderer(self):
        with self.assertRaises(ValueError):
            self.report("<div>Claim [[cite:bad]]</div>", [])

    def test_table_cells_use_parser_scopes_and_original_positions(self):
        marker = f"[[cite:{self.a.ref}]]"
        text = f"| Code | Finding |\n|---|---|\n| `{marker}` | {marker} |"
        report = self.report(text)
        self.assertTrue(
            report["text"].startswith(text.replace(f"| {marker} |", "| [1] |"))
        )
        with self.assertRaises(ValueError):
            self.report("| A | B |\n|---|---|\n| `literal | [[cite:bad]] ` |", [])

    def test_numeric_reference_definitions_cannot_redirect_generated_citations(self):
        with self.assertRaisesRegex(ValueError, "Numeric reference definitions"):
            self.report(f"Claim [[cite:{self.a.ref}]]\n\n[1]: https://wrong.example")

    def test_publication_revalidation_rejects_tampered_rendering(self):
        report = self.report(f"Claim [[cite:{self.a.ref}]]")
        for change in [
            {"text": report["text"].replace("[1]", "[2]", 1)},
            {"citations": [self.b.ref]},
            {"text": report["text"] + "\nTampered bibliography"},
            {"citations": []},
            {"evidence": []},
        ]:
            with self.subTest(change=change), self.assertRaises(ValueError):
                validate({**report, **change}, self.resolve)
