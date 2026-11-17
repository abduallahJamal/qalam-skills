"""Tests for the LF-safe file writer shared by install and scaffold.

Regression these are written around: both modules used
``Path.write_text(..., newline="\\n")``, which raises ``TypeError`` on Python 3.9
because the ``newline`` argument only arrived in 3.10. The package declares
``requires-python = ">=3.9"``, so the floor was broken and CI caught it.
"""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from qalam.install import write_cursor_rule
from qalam.scaffold import scaffold
from qalam.textutil import write_text_lf


class WriteTextLfTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)

    def tearDown(self):
        self.temp.cleanup()

    def test_writes_utf8_and_lf_only(self):
        path = self.root / "nested" / "copy.md"
        write_text_lf(path, "سطر أول\nسطر ثانٍ\n")
        data = path.read_bytes()
        self.assertIn("سطر أول".encode("utf-8"), data)
        self.assertNotIn(b"\r\n", data)
        self.assertEqual(data.decode("utf-8"), "سطر أول\nسطر ثانٍ\n")

    def test_creates_missing_parent_directories(self):
        path = self.root / "a" / "b" / "c.md"
        write_text_lf(path, "x\n")
        self.assertTrue(path.exists())

    def test_cursor_rule_is_lf(self):
        path = write_cursor_rule(self.root)
        data = path.read_bytes()
        self.assertNotIn(b"\r\n", data)
        self.assertTrue(data.startswith(b"---"))

    def test_scaffold_files_are_lf(self):
        result = scaffold(
            "sample-skill",
            "A sample skill description that is comfortably long for validation.",
            self.root,
        )
        for path in result.files:
            with self.subTest(path=path.name):
                self.assertNotIn(b"\r\n", path.read_bytes())


if __name__ == "__main__":
    unittest.main()
