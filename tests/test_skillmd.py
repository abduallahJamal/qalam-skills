"""Tests for SKILL.md parsing and validation.

The failures these cover are the ones that make a skill silently invisible in a
host: a BOM, a missing fence, a bad name, a description that is too long.
"""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from qalam.skillmd import (
    SkillDoc,
    SkillError,
    emit,
    iter_skill_files,
    load,
    parse_markdown,
)

VALID = """---
name: demo-skill
description: Do a specific thing with specific objects. Use when the user asks for that thing.
license: MIT
compatibility: Python 3.9+
metadata:
  qalam.version: "1.0"
  owner: tests
---

# Demo

Body text that is long enough to pass the strict length check. It explains what
"done" means, gives a procedure, and describes the report. More text here so the
strict body-length warning does not fire during tests that use --strict.
"""


class ParseTests(unittest.TestCase):
    def test_minimal_parses(self):
        doc = parse_markdown("---\nname: a\ndescription: b\n---\n\nbody\n")
        self.assertEqual(doc.name, "a")
        self.assertEqual(doc.description, "b")
        self.assertIn("body", doc.body)

    def test_bom_is_rejected_with_a_useful_message(self):
        with self.assertRaises(SkillError) as caught:
            parse_markdown("\ufeff---\nname: a\n")
        self.assertIn("first line", str(caught.exception))

    def test_blank_line_before_frontmatter_is_rejected(self):
        with self.assertRaises(SkillError):
            parse_markdown("\n---\nname: a\n---\n")

    def test_unclosed_frontmatter_is_rejected(self):
        with self.assertRaises(SkillError):
            parse_markdown("---\nname: a\nbody with no closing fence\n")

    def test_inline_list_and_quotes(self):
        doc = parse_markdown(
            '---\nname: a\ndescription: "quoted: with colon"\nallowed-tools: Read, Write\n---\n'
        )
        self.assertEqual(doc.description, "quoted: with colon")
        # A comma string stays a string; a bracketed list becomes a list.
        self.assertEqual(doc.frontmatter["allowed-tools"], "Read, Write")

    def test_bracketed_list_is_parsed(self):
        doc = parse_markdown("---\nname: a\ndescription: d\naliases: [x, y]\n---\n")
        self.assertEqual(doc.frontmatter["aliases"], ["x", "y"])

    def test_block_scalar(self):
        doc = parse_markdown("---\nname: a\ndescription: |\n  line one\n  line two\n---\n")
        self.assertIn("line one", doc.description)
        self.assertIn("line two", doc.description)

    def test_tabs_are_rejected(self):
        with self.assertRaises(SkillError):
            parse_markdown("---\nname: a\n\tbad: indent\n---\n")


class ValidationTests(unittest.TestCase):
    def test_valid_file_has_no_errors(self):
        doc = parse_markdown(VALID)
        self.assertEqual(doc.errors(strict=True), [])

    def test_missing_name_is_an_error(self):
        doc = parse_markdown("---\ndescription: something long enough to pass length checks here\n---\n")
        self.assertTrue(any("name" in error for error in doc.errors()))

    def test_missing_description_is_an_error(self):
        doc = parse_markdown("---\nname: x\n---\n")
        self.assertTrue(any("description" in error for error in doc.errors()))

    def test_bad_name_shape_is_an_error(self):
        for bad in ("My-Skill", "my_skill", "my--skill", "-my", "my skill"):
            doc = parse_markdown(f"---\nname: {bad}\ndescription: {'x' * 60}\n---\n")
            self.assertTrue(doc.errors(), f"{bad!r} should be rejected")

    def test_long_description_is_an_error(self):
        doc = parse_markdown(f"---\nname: ok\ndescription: {'x' * 1100}\n---\n")
        self.assertTrue(any("1024" in error for error in doc.errors()))

    def test_short_description_is_only_a_warning(self):
        doc = parse_markdown("---\nname: ok\ndescription: too short\n---\n")
        self.assertEqual(doc.errors(), [])
        self.assertTrue(doc.warning_messages())

    def test_nested_metadata_is_an_error(self):
        doc = parse_markdown(
            "---\nname: ok\ndescription: "
            + "x" * 60
            + "\nmetadata:\n  a:\n    b: c\n---\n"
        )
        self.assertTrue(doc.errors())

    def test_unknown_field_warns(self):
        doc = parse_markdown(
            f"---\nname: ok\ndescription: {'x' * 60}\nmade_up_field: 1\n---\n"
        )
        self.assertTrue(any("made_up_field" in w for w in doc.warning_messages()))

    def test_host_field_warns_only_in_strict_mode(self):
        text = f"---\nname: ok\ndescription: {'x' * 60}\nmodel: opus\n---\n" + ("body " * 60)
        doc = parse_markdown(text)
        self.assertFalse(any("model" in w for w in doc.warning_messages(strict=False)))
        self.assertTrue(any("model" in w for w in doc.warning_messages(strict=True)))

    def test_raise_if_invalid_names_the_path(self):
        doc = parse_markdown("---\nname: Bad Name\ndescription: " + "x" * 60 + "\n---\n", path="x/SKILL.md")
        with self.assertRaises(SkillError) as caught:
            doc.raise_if_invalid()
        self.assertIn("x/SKILL.md", str(caught.exception))


class EmitTests(unittest.TestCase):
    def test_round_trip_preserves_semantics(self):
        doc = parse_markdown(VALID)
        again = parse_markdown(doc.to_markdown())
        self.assertEqual(again.name, doc.name)
        self.assertEqual(again.description, doc.description)
        self.assertEqual(again.frontmatter["metadata"], doc.frontmatter["metadata"])
        self.assertIn("Body text", again.body)

    def test_emit_rejects_invalid(self):
        doc = SkillDoc(frontmatter={"description": "x"}, body="b")
        with self.assertRaises(SkillError):
            emit(doc)

    def test_emit_normalises_multiline_description(self):
        doc = parse_markdown("---\nname: ok\ndescription: |\n  one\n  two\n---\n")
        emitted = doc.to_markdown()
        self.assertIn("description: one two", emitted)


class DiscoveryTests(unittest.TestCase):
    def test_iter_finds_nested_skill_files(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "a").mkdir()
            (root / "a" / "SKILL.md").write_text(VALID, encoding="utf-8")
            (root / "b" / "inner").mkdir(parents=True)
            (root / "b" / "inner" / "SKILL.md").write_text(VALID, encoding="utf-8")
            found = sorted(iter_skill_files(directory))
            self.assertEqual(len(found), 2)

    def test_load_reads_with_bom_tolerance(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "SKILL.md"
            path.write_text(VALID, encoding="utf-8-sig")
            doc = load(str(path))
            self.assertEqual(doc.name, "demo-skill")


if __name__ == "__main__":
    unittest.main()
