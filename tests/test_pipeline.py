"""Tests for chunking, run state, glossary, and translation memory.

These cover the properties a long translation run depends on: chunks never split
code, state records exactly what was translated, and an alias edit invalidates
only the chunks that contain it.
"""

from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path

from qalam.chunk import (
    ChunkingError,
    check_chunks,
    merge_outputs,
    split_text,
    write_chunks,
)
from qalam.glossary import Glossary, Term, apply_replacements, extract_terms
from qalam.runstate import RunState, certify, chunk_terms_signature, plan, read_pairs
from qalam.tm import MemoryEntry, TranslationMemory, normalise_key, split_sentences

BODY = "\n\n".join(
    ["# Chapter %d\n\n%s" % (index, ("This is paragraph text. " * 40)) for index in range(1, 6)]
)


class ChunkTests(unittest.TestCase):
    def test_split_produces_contiguous_chunks(self):
        chunks = split_text(BODY, target_chars=800, max_chars=2000)
        self.assertGreater(len(chunks), 1)
        self.assertEqual(check_chunks(chunks, 2000), [])
        for previous, current in zip(chunks, chunks[1:]):
            self.assertEqual(current.start_line, previous.end_line + 1)

    def test_chunks_keep_heading_paths(self):
        chunks = split_text(BODY, target_chars=800, max_chars=2000)
        self.assertTrue(any(chunk.heading_path for chunk in chunks))
        self.assertEqual(chunks[0].heading_path[0], "Chapter 1")

    def test_code_block_is_never_split(self):
        code = "```python\n" + "\n".join(f"line_{i} = {i}" for i in range(400)) + "\n```\n"
        text = "# Title\n\nintro paragraph\n\n" + code + "\n\noutro paragraph\n"
        chunks = split_text(text, target_chars=500, max_chars=1000)
        holders = [chunk for chunk in chunks if chunk.has_code]
        self.assertEqual(len(holders), 1)
        self.assertIn("line_399", holders[0].text)

    def test_table_is_kept_together(self):
        table = "| a | b |\n| --- | --- |\n" + "\n".join(f"| {i} | {i * 2} |" for i in range(60))
        text = "# T\n\n" + table + "\n\nend\n"
        chunks = split_text(text, target_chars=400, max_chars=1000)
        self.assertTrue(any(chunk.has_table for chunk in chunks))

    def test_rejects_bad_arguments(self):
        with self.assertRaises(ChunkingError):
            split_text(BODY, target_chars=100)
        with self.assertRaises(ChunkingError):
            split_text(BODY, target_chars=1000, max_chars=500)

    def test_write_chunks_and_manifest(self):
        with tempfile.TemporaryDirectory() as directory:
            chunks = write_chunks(BODY, directory, target_chars=800, max_chars=2000)
            self.assertTrue(os.path.exists(os.path.join(directory, "manifest.json")))
            self.assertTrue(os.path.exists(os.path.join(directory, f"{chunks[0].id}.md")))
            text = Path(directory, "manifest.json").read_text(encoding="utf-8")
            self.assertIn("source_sha256", text)

    def test_chunk_text_is_not_modified(self):
        chunks = split_text(BODY, target_chars=800, max_chars=2000)
        joined = "\n".join(chunk.text for chunk in chunks)
        for line in BODY.splitlines():
            if line.strip():
                self.assertIn(line.strip(), joined)


class MergeTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        (self.root / "chunk0001.md").write_text("one\n", encoding="utf-8")
        (self.root / "chunk0002.md").write_text("two\n", encoding="utf-8")
        (self.root / "output_chunk0001.md").write_text("واحد\n", encoding="utf-8")
        (self.root / "output_chunk0002.md").write_text("اثنان\n", encoding="utf-8")

    def tearDown(self):
        self.temp.cleanup()

    def test_merge_in_numeric_order(self):
        out = self.root / "final.md"
        count, warnings = merge_outputs(str(self.root), str(self.root), str(out))
        self.assertEqual(count, 2)
        self.assertEqual(warnings, [])
        self.assertEqual(out.read_text(encoding="utf-8"), "واحد\n\nاثنان\n")

    def test_missing_chunk_is_reported_not_skipped_silently(self):
        (self.root / "output_chunk0002.md").unlink()
        out = self.root / "final.md"
        _count, warnings = merge_outputs(str(self.root), str(self.root), str(out))
        self.assertTrue(any("chunk0002" in warning for warning in warnings))

    def test_blank_chunk_is_reported(self):
        (self.root / "output_chunk0002.md").write_text("   \n", encoding="utf-8")
        out = self.root / "final.md"
        _count, warnings = merge_outputs(str(self.root), str(self.root), str(out))
        self.assertTrue(any("blank" in warning for warning in warnings))


class GlossaryTests(unittest.TestCase):
    def test_round_trip(self):
        glossary = Glossary(
            [Term(source="repo", target="مستودع", aliases=["repository"], gender="masculine")]
        )
        with tempfile.TemporaryDirectory() as directory:
            path = os.path.join(directory, "g.json")
            glossary.save(path)
            loaded = Glossary.load(path)
        self.assertEqual(len(loaded.terms), 1)
        self.assertEqual(loaded.terms[0].target, "مستودع")
        self.assertEqual(loaded.terms[0].aliases, ["repository"])

    def test_find_matches_alias_and_folds_forms(self):
        glossary = Glossary([Term(source="مستودع", target="repository", aliases=["repo"])])
        self.assertIsNotNone(glossary.find("مستَودَع"))
        self.assertIsNotNone(glossary.find("REPO"))

    def test_matching_prefers_longer_terms(self):
        glossary = Glossary(
            [Term(source="طلب", target="request"), Term(source="طلب دمج", target="pull request")]
        )
        matches = glossary.matching("افتح طلب دمج جديد")
        self.assertEqual(matches[0].source, "طلب دمج")

    def test_frequency_count(self):
        glossary = Glossary([Term(source="parser", target="محلل")])
        glossary.count_frequencies(["the parser and the parser", "another parser"])
        self.assertEqual(glossary.terms[0].frequency, 3)

    def test_merge_never_overwrites(self):
        base = Glossary([Term(source="a", target="أ")])
        extra = Glossary([Term(source="a", target="X"), Term(source="b", target="ب")])
        base.merge(extra)
        self.assertEqual(base.find("a").target, "أ")
        self.assertEqual(len(base.terms), 2)

    def test_apply_replacements_reports_survivors(self):
        glossary = Glossary([Term(source="repository", target="مستودع")])
        _out, problems = apply_replacements("افتح الـ repository", glossary)
        self.assertTrue(problems)

    def test_extract_terms_finds_repeats(self):
        text = "GitHub GitHub GitHub and PostgreSQL PostgreSQL appear often."
        terms = extract_terms([text], min_frequency=2)
        sources = {term.source for term in terms}
        self.assertIn("GitHub", sources)


class RunStateTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        (self.root / "chunk0001.md").write_text("Repository text here.\n", encoding="utf-8")
        (self.root / "chunk0002.md").write_text("Other text here.\n", encoding="utf-8")
        (self.root / "output_chunk0001.md").write_text("نص المستودع هنا.\n", encoding="utf-8")
        (self.root / "output_chunk0002.md").write_text("نص آخر هنا.\n", encoding="utf-8")

    def tearDown(self):
        self.temp.cleanup()

    def test_untracked_outputs_are_recorded_not_retranslated(self):
        result = plan(str(self.root), target_language="ar")
        self.assertEqual(result.record_only, ["chunk0001", "chunk0002"])
        self.assertEqual(result.translate, [])

    def test_retranslate_untracked_flag(self):
        result = plan(str(self.root), target_language="ar", retranslate_untracked=True)
        self.assertEqual(sorted(result.translate), ["chunk0001", "chunk0002"])

    def test_recorded_chunks_are_unchanged(self):
        glossary = Glossary([Term(source="Repository", target="مستودع")])
        self.assertEqual(certify(str(self.root), glossary, "ar"), [])
        result = plan(str(self.root), glossary=glossary, target_language="ar")
        self.assertEqual(sorted(result.unchanged), ["chunk0001", "chunk0002"])

    def test_source_change_triggers_one_chunk(self):
        certify(str(self.root), None, "ar")
        (self.root / "chunk0002.md").write_text("Other text here, edited.\n", encoding="utf-8")
        result = plan(str(self.root), target_language="ar")
        self.assertEqual(result.translate, ["chunk0002"])
        self.assertEqual(result.reasons["chunk0002"], "source_changed")
        self.assertEqual(result.unchanged, ["chunk0001"])

    def test_alias_edit_invalidates_only_matching_chunks(self):
        glossary = Glossary([Term(source="Repository", target="مستودع")])
        certify(str(self.root), glossary, "ar")
        self.assertEqual(plan(str(self.root), glossary=glossary).translate, [])

        glossary.terms[0].aliases.append("repo")
        result = plan(str(self.root), glossary=glossary)
        # chunk0002 does not mention the term, so it must stay untouched.
        self.assertEqual(result.translate, ["chunk0001"])
        self.assertEqual(result.reasons["chunk0001"], "glossary_changed")
        self.assertEqual(result.unchanged, ["chunk0002"])

    def test_blank_output_queues_translation(self):
        (self.root / "output_chunk0001.md").write_text("  \n", encoding="utf-8")
        result = plan(str(self.root))
        self.assertIn("chunk0001", result.translate)
        self.assertEqual(result.reasons["chunk0001"], "blank_output")

    def test_recording_blank_output_is_refused(self):
        state = RunState()
        with self.assertRaises(ValueError):
            state.record("chunk0001", "src", "   \n", None, "ar")

    def test_term_signature_is_stable(self):
        glossary = Glossary([Term(source="Repository", target="مستودع")])
        first = chunk_terms_signature("Repository text", glossary)
        second = chunk_terms_signature("Repository text", glossary)
        self.assertEqual(first, second)

    def test_state_file_round_trip(self):
        certify(str(self.root), None, "ar")
        state = RunState.load(str(self.root))
        self.assertEqual(len(state.chunks), 2)
        self.assertEqual(len(read_pairs(str(self.root))), 2)


class TranslationMemoryTests(unittest.TestCase):
    def test_normalise_key_ignores_punctuation_and_case(self):
        self.assertEqual(normalise_key("Hello, World!"), normalise_key("hello world"))

    def test_sentence_splitting(self):
        sentences = split_sentences("First sentence. Second one! Third?")
        self.assertEqual(len(sentences), 3)

    def test_reuse_hits_known_sentence(self):
        memory = TranslationMemory()
        source = "This is a sufficiently long sentence to be stored in memory."
        memory.add(
            MemoryEntry(
                source=source,
                target="هذه جملة طويلة بما يكفي لتُخزَّن في الذاكرة.",
                source_language="en",
                target_language="ar",
            )
        )
        prefilled, leftovers, hits = memory.reuse(source, "ar")
        self.assertEqual(hits, 1)
        self.assertEqual(leftovers, [])
        self.assertIn("الذاكرة", prefilled)

    def test_short_sentences_are_not_stored(self):
        memory = TranslationMemory()
        memory.add(MemoryEntry(source="Yes.", target="نعم.", source_language="en", target_language="ar"))
        self.assertEqual(memory.stats()["entries"], 0)

    def test_identical_target_is_not_stored(self):
        memory = TranslationMemory()
        text = "This sentence is identical in both languages so it is not stored."
        memory.add(MemoryEntry(source=text, target=text, source_language="en", target_language="en"))
        self.assertEqual(memory.stats()["entries"], 0)

    def test_save_and_load(self):
        with tempfile.TemporaryDirectory() as directory:
            path = os.path.join(directory, "tm.json")
            memory = TranslationMemory()
            memory.add(
                MemoryEntry(
                    source="A sentence long enough to be remembered by the memory store.",
                    target="جملة طويلة بما يكفي ليحفظها مخزن الذاكرة.",
                    source_language="en",
                    target_language="ar",
                )
            )
            memory.save(path)
            loaded = TranslationMemory.load(path)
            self.assertEqual(loaded.stats()["entries"], 1)

    def test_learning_requires_aligned_paragraphs(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory, "s.md")
            target = Path(directory, "t.md")
            source.write_text("one\n\ntwo\n", encoding="utf-8")
            target.write_text("واحد\n", encoding="utf-8")
            with self.assertRaises(ValueError):
                TranslationMemory().learn_from_pair(str(source), str(target), "en", "ar")


if __name__ == "__main__":
    unittest.main()
