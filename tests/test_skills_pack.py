"""Contract tests for the shipped skills.

These run against the real ``skills/`` directory, not fixtures. They are the
tests that keep the pack shippable: every skill parses, every skill's
description would plausibly trigger, every referenced file exists, and every
bash command in a skill points at something real.
"""

from __future__ import annotations

import re
import unittest
from pathlib import Path

from qalam.skillmd import iter_skill_files, load

ROOT = Path(__file__).resolve().parents[1]
SKILLS = ROOT / "skills"

EXPECTED = {
    "translate-docs",
    "arabic-style",
    "rtl-layout",
    "glossary-builder",
    "translation-qa",
    "localize-app",
    "extract-docs",
    "subtitle-translate",
    "skill-forge",
}

#: Words that should appear in a description so the host can match a real request.
TRIGGER_WORDS = {
    "translate-docs": ["translate", "Arabic"],
    "arabic-style": ["Arabic", "prose"],
    "rtl-layout": ["RTL", "Arabic"],
    "glossary-builder": ["term base", "Arabic"],
    "translation-qa": ["review", "translation"],
    "localize-app": ["strings", "Arabic"],
    "extract-docs": ["PDF", "Markdown"],
    "subtitle-translate": ["SRT", "Arabic"],
    "skill-forge": ["SKILL.md", "Claude Code"],
}


def skill_docs():
    return {doc.name: doc for doc in (load(path) for path in sorted(iter_skill_files(str(SKILLS))))}


class PackShapeTests(unittest.TestCase):
    def test_expected_skills_are_present(self):
        names = set(skill_docs())
        self.assertEqual(names, EXPECTED)

    def test_every_skill_validates_strictly(self):
        for name, doc in skill_docs().items():
            with self.subTest(skill=name):
                self.assertEqual(doc.errors(strict=True), [], name)

    def test_names_match_their_folders(self):
        for name, doc in skill_docs().items():
            directory = Path(doc.path).parent.name
            self.assertEqual(name, directory)

    def test_descriptions_carry_trigger_words(self):
        docs = skill_docs()
        for name, words in TRIGGER_WORDS.items():
            description = docs[name].description.lower()
            for word in words:
                self.assertIn(word.lower(), description, f"{name} missing {word!r}")

    def test_descriptions_are_single_line_and_bounded(self):
        for name, doc in skill_docs().items():
            self.assertLess(len(doc.description), 1024, name)
            self.assertGreater(len(doc.description), 120, name)
            self.assertNotIn("\n", doc.description.strip(), name)

    def test_frontmatter_uses_portable_fields_only(self):
        portable = {"name", "description", "license", "compatibility", "metadata"}
        for name, doc in skill_docs().items():
            extra = set(doc.frontmatter) - portable
            self.assertEqual(extra, set(), f"{name} uses host-specific fields: {extra}")

    def test_every_skill_has_a_license_and_metadata(self):
        for name, doc in skill_docs().items():
            self.assertEqual(doc.frontmatter.get("license"), "MIT", name)
            self.assertIn("qalam.version", doc.frontmatter.get("metadata", {}), name)

    def test_body_length_is_usable(self):
        for name, doc in skill_docs().items():
            self.assertGreater(len(doc.body), 2000, name)
            self.assertLess(len(doc.body), 20000, f"{name} body is too long to load cheaply")

    def test_every_skill_states_a_governing_rule(self):
        for name, doc in skill_docs().items():
            body = doc.body.lower()
            self.assertTrue(
                "governing rule" in body or "## when to use" in body,
                f"{name} lacks a contract section",
            )

    def test_every_skill_has_a_failure_or_troubleshooting_section(self):
        for name, doc in skill_docs().items():
            body = doc.body.lower()
            self.assertTrue(
                "failure" in body or "troubleshoot" in body or "anti-pattern" in body,
                f"{name} has no failure guidance",
            )


class ReferenceIntegrityTests(unittest.TestCase):
    BLOCK = re.compile(r"`((?:references|scripts|assets)/[^`\s]+)`")

    def test_referenced_files_exist(self):
        for name, doc in skill_docs().items():
            directory = Path(doc.path).parent
            body = self._prose_only(doc.body)
            for match in self.BLOCK.finditer(body):
                relative = match.group(1)
                # Skip directories and globs: prose legitimately mentions the
                # shape of a skills folder ("references/*.md"), and only
                # concrete file references must resolve.
                if relative.endswith("/") or "*" in relative:
                    continue
                path = directory / relative
                self.assertTrue(path.exists(), f"{name} references missing {relative}")

    @staticmethod
    def _prose_only(body: str) -> str:
        """Drop fenced code and quoted examples.

        Examples about how to write skills legitimately contain paths that live
        in *other* skills (``references/timing-rules.md`` as an illustration).
        Only prose references are contracts.
        """
        without_fences = re.sub(r"```[\s\S]*?```", "", body)
        without_quotes = re.sub(r"^>.*$", "", without_fences, flags=re.MULTILINE)
        return without_quotes

    def test_every_reference_file_is_linked_from_its_skill(self):
        for name, doc in skill_docs().items():
            directory = Path(doc.path).parent
            references = directory / "references"
            if not references.is_dir():
                continue
            for path in references.rglob("*.md"):
                relative = path.relative_to(directory).as_posix()
                self.assertIn(relative, doc.body, f"{name} does not link {relative}")

    def test_example_scripts_run(self):
        import subprocess
        import sys as _sys

        result = subprocess.run(
            [
                _sys.executable,
                str(ROOT / "examples" / "check_locales.py"),
                str(ROOT / "examples" / "arabic-app" / "en.json"),
                str(ROOT / "examples" / "arabic-app" / "ar.json"),
            ],
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("no problems found", result.stdout)

    def test_reference_files_are_not_empty(self):
        for name, doc in skill_docs().items():
            directory = Path(doc.path).parent
            for path in directory.rglob("references/*.md"):
                self.assertGreater(path.stat().st_size, 500, f"{name}: {path.name} is a stub")


class CommandIntegrityTests(unittest.TestCase):
    def test_qalam_commands_reference_existing_subcommands(self):
        from qalam.cli import build_parser

        parser = build_parser()
        known = set()
        for action in parser._actions:      # noqa: SLF001 - argparse exposes subparsers here
            if hasattr(action, "choices") and action.choices:
                known |= set(action.choices)
        pattern = re.compile(r"python(?:3)? -m qalam ([a-z]+)")
        for name, doc in skill_docs().items():
            for command in pattern.findall(doc.body):
                self.assertIn(command, known, f"{name} calls unknown subcommand {command!r}")

    def test_subtitle_script_path_is_correct(self):
        doc = skill_docs()["subtitle-translate"]
        script = Path(doc.path).parent / "scripts" / "subs.py"
        self.assertTrue(script.exists())
        self.assertIn("scripts/subs.py", doc.body)

    def test_no_absolute_local_paths_leak_into_skills(self):
        forbidden = ("/home/", "/Users/", "C:\\\\Users")
        for name, doc in skill_docs().items():
            text = doc.body + doc.description
            for needle in forbidden:
                self.assertNotIn(needle, text, f"{name} contains a local path {needle!r}")

    def test_no_hardcoded_claude_home(self):
        # A portable skill must not assume one host's directory.
        for name, doc in skill_docs().items():
            self.assertNotIn("~/.claude/skills/", doc.body, name)


class ArabicContentTests(unittest.TestCase):
    def test_arabic_facing_skills_contain_arabic_examples(self):
        docs = skill_docs()
        for name in ("translate-docs", "arabic-style", "localize-app", "translation-qa"):
            with self.subTest(skill=name):
                self.assertRegex(
                    docs[name].body,
                    r"[\u0620-\u064A]{3,}",
                    f"{name} should show real Arabic examples",
                )

    def test_arabic_skill_references_typography(self):
        body = skill_docs()["translate-docs"].body
        self.assertIn("arabic-typography.md", body)

    def test_rtl_skill_covers_the_four_hosts(self):
        body = skill_docs()["rtl-layout"].body
        for needle in ("Tailwind", "Flutter", "WPF", "Android"):
            self.assertIn(needle, body)


if __name__ == "__main__":
    unittest.main()
