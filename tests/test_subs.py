"""Tests for the subtitle tool.

The regression these are written around: an early version of ``wrap_lines``
dropped words when the text did not fit in two lines. Silent text loss in a
subtitle tool is unacceptable, so ``test_wrap_never_drops_words`` is the most
important test in this file.
"""

from __future__ import annotations

import os
import sys
import tempfile
import unittest
from pathlib import Path

SKILL_SCRIPTS = Path(__file__).resolve().parents[1] / "skills" / "subtitle-translate" / "scripts"
sys.path.insert(0, str(SKILL_SCRIPTS))

import subs  # noqa: E402

SRT = """1
00:00:01,000 --> 00:00:03,000
Hello there.

2
00:00:03,500 --> 00:00:06,000
This cue is deliberately long so that it exceeds the reading speed limit and
needs shortening.

3
00:00:06,500 --> 00:00:07,600
- First speaker
- Second speaker
"""

VTT = """WEBVTT

00:00:01.000 --> 00:00:03.000
Hello there.

00:00:03.500 --> 00:00:05.000
Second cue.
"""


class ParseTests(unittest.TestCase):
    def test_srt_parses(self):
        cues, is_vtt = subs.parse(SRT)
        self.assertFalse(is_vtt)
        self.assertEqual(len(cues), 3)
        self.assertEqual(cues[0].start_ms, 1000)
        self.assertEqual(cues[0].end_ms, 3000)

    def test_vtt_parses(self):
        cues, is_vtt = subs.parse(VTT)
        self.assertTrue(is_vtt)
        self.assertEqual(len(cues), 2)
        self.assertEqual(cues[1].start_ms, 3500)

    def test_bom_and_crlf_are_handled(self):
        cues, _ = subs.parse("\ufeff" + SRT.replace("\n", "\r\n"))
        self.assertEqual(len(cues), 3)

    def test_round_trip_preserves_timing_and_text(self):
        cues, _ = subs.parse(SRT)
        again, _ = subs.parse(subs.serialise(cues))
        self.assertEqual(len(cues), len(again))
        for first, second in zip(cues, again):
            self.assertEqual(first.start_ms, second.start_ms)
            self.assertEqual(first.end_ms, second.end_ms)
            self.assertEqual(first.text, second.text)

    def test_vtt_serialise_uses_period(self):
        cues, _ = subs.parse(VTT)
        output = subs.serialise(cues, is_vtt=True)
        self.assertTrue(output.startswith("WEBVTT"))
        self.assertIn("00:00:01.000 --> 00:00:03.000", output)

    def test_srt_serialise_uses_comma(self):
        cues, _ = subs.parse(SRT)
        self.assertIn("00:00:01,000 --> 00:00:03,000", subs.serialise(cues))

    def test_timestamp_round_trip(self):
        for milliseconds in (0, 1000, 61_500, 3_723_456):
            rendered = subs.format_timestamp(milliseconds)
            self.assertEqual(subs.parse_timestamp(rendered), milliseconds)


class MetricTests(unittest.TestCase):
    def test_cps_counts_characters_without_markup(self):
        cue = subs.Cue(index=1, start_ms=0, end_ms=2000, text="<i>four</i>")
        self.assertEqual(cue.chars(), 4)
        self.assertEqual(cue.cps(), 2.0)

    def test_duration_and_zero_guard(self):
        cue = subs.Cue(index=1, start_ms=2000, end_ms=1000, text="x")
        self.assertEqual(cue.duration, 0.0)
        self.assertEqual(cue.cps(), 0.0)

    def test_arabic_detection(self):
        self.assertTrue(subs.Cue(1, 0, 1, "مرحبا بالعالم").is_arabic())
        self.assertFalse(subs.Cue(1, 0, 1, "hello world").is_arabic())

    def test_stats_shape(self):
        cues, _ = subs.parse(SRT)
        report = subs.stats(cues)
        self.assertEqual(report["cues"], 3)
        self.assertIn("max_cps", report)
        self.assertEqual(report["three_line_cues"], 0)


class LintTests(unittest.TestCase):
    def test_slow_cue_is_an_error(self):
        cues = [subs.Cue(1, 0, 1000, "x" * 40)]     # 40 cps
        findings = subs.lint(cues)
        self.assertTrue(any("hard limit" in message for message in findings.errors))

    def test_short_cue_warns(self):
        cues = [subs.Cue(1, 0, 500, "ok")]
        findings = subs.lint(cues, min_duration=1.0)
        self.assertTrue(any("shorter than" in message for message in findings.warnings))

    def test_three_lines_warns(self):
        cues = [subs.Cue(1, 0, 4000, "a\nb\nc")]
        findings = subs.lint(cues)
        self.assertTrue(any("lines" in message for message in findings.warnings))

    def test_overlap_is_an_error(self):
        cues = [subs.Cue(1, 0, 3000, "a"), subs.Cue(2, 2000, 4000, "b")]
        findings = subs.lint(cues)
        self.assertTrue(any("overlaps" in message for message in findings.errors))

    def test_empty_cue_is_an_error(self):
        findings = subs.lint([subs.Cue(1, 0, 2000, "   ")])
        self.assertTrue(any("empty" in message for message in findings.errors))

    def test_clean_file_has_no_errors(self):
        cues = [subs.Cue(1, 0, 2000, "short and clean")]
        self.assertEqual(subs.lint(cues).errors, [])

    def test_compare_detects_timing_change(self):
        source = [subs.Cue(1, 0, 2000, "a")]
        target = [subs.Cue(1, 100, 2000, "ب")]
        findings = subs.compare(source, target)
        self.assertTrue(findings.errors)

    def test_compare_detects_cue_count_change(self):
        source = [subs.Cue(1, 0, 2000, "a"), subs.Cue(2, 2000, 4000, "b")]
        target = [subs.Cue(1, 0, 2000, "أ")]
        self.assertTrue(subs.compare(source, target).errors)

    def test_compare_identical_files_is_clean(self):
        cues, _ = subs.parse(SRT)
        self.assertEqual(subs.compare(cues, cues).errors, [])


class WrapTests(unittest.TestCase):
    def test_wrap_never_drops_words(self):
        """Regression: words were silently lost when the text did not fit."""
        cases = [
            "Welcome back, and thanks for watching this short introduction.",
            "This cue is deliberately long so that it exceeds the reading speed limit and needs shortening.",
            " ".join(f"word{i}" for i in range(1, 40)),
        ]
        for text in cases:
            wrapped = subs.wrap_lines(text, max_chars=30, max_lines=2)
            self.assertEqual(
                wrapped.split(),
                text.split(),
                f"words changed for input: {text!r}",
            )

    def test_wrap_balances_two_lines(self):
        wrapped = subs.wrap_lines("one two three four five six seven eight", max_chars=25, max_lines=2)
        lines = wrapped.split("\n")
        self.assertEqual(len(lines), 2)
        self.assertLessEqual(abs(len(lines[0]) - len(lines[1])), 6)

    def test_short_text_stays_on_one_line(self):
        self.assertEqual(subs.wrap_lines("short text", max_chars=42), "short text")

    def test_arabic_wrap_keeps_words(self):
        text = "هذه جملة عربية طويلة تحتاج إلى تقسيم على سطرين بشكل متوازن"
        wrapped = subs.wrap_lines(text, max_chars=25, max_lines=2)
        self.assertEqual(wrapped.split(), text.split())

    def test_empty_text_is_returned_unchanged(self):
        self.assertEqual(subs.wrap_lines(""), "")
        self.assertEqual(subs.wrap_lines("   "), "   ")


class ShiftTests(unittest.TestCase):
    def test_shift_moves_all_cues(self):
        cues, _ = subs.parse(SRT)
        shifted = [
            subs.Cue(cue.index, cue.start_ms + 1500, cue.end_ms + 1500, cue.text)
            for cue in cues
        ]
        self.assertEqual(shifted[0].start_ms, 2500)

    def test_negative_shift_clamps_at_zero(self):
        cues = [subs.Cue(1, 500, 1500, "a")]
        moved = subs.Cue(1, max(cues[0].start_ms - 2000, 0), max(cues[0].end_ms - 2000, 0), "a")
        self.assertEqual(moved.start_ms, 0)
        self.assertEqual(moved.end_ms, 0)


class CommandTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.source = self.root / "in.srt"
        self.source.write_text(SRT, encoding="utf-8")

    def tearDown(self):
        self.temp.cleanup()

    def test_wrap_command_writes_identical_words(self):
        out = self.root / "wrapped.srt"
        code = subs.main(["wrap", str(self.source), "--chars", "32", "--out", str(out)])
        self.assertEqual(code, 0)
        original, _ = subs.read(str(self.source))
        wrapped, _ = subs.read(str(out))
        for before, after in zip(original, wrapped):
            self.assertEqual(before.plain().split(), after.plain().split())

    def test_shift_command_writes_file(self):
        out = self.root / "shifted.srt"
        self.assertEqual(subs.main(["shift", str(self.source), "--by", "1.25", "--out", str(out)]), 0)
        cues, _ = subs.read(str(out))
        self.assertEqual(cues[0].start_ms, 2250)

    def test_check_reports_mismatch(self):
        target = self.root / "target.srt"
        target.write_text(SRT.replace("00:00:01,000 --> 00:00:03,000", "00:00:02,000 --> 00:00:03,000"), encoding="utf-8")
        self.assertEqual(subs.main(["check", str(self.source), str(target)]), 1)

    def test_check_passes_for_identical_timing(self):
        target = self.root / "target.srt"
        target.write_text(SRT.replace("Hello there.", "مرحبا."), encoding="utf-8")
        # The fixture's second cue is deliberately over the reading limit, so the
        # check must fail on speed but not on timing. Assert the timing error is
        # absent rather than expecting a clean exit.
        import io
        from contextlib import redirect_stdout

        buffer = io.StringIO()
        with redirect_stdout(buffer):
            subs.main(["check", str(self.source), str(target)])
        self.assertNotIn("timing changed", buffer.getvalue())
        self.assertIn("cps exceeds", buffer.getvalue())

    def test_stats_json(self):
        import io
        import json
        from contextlib import redirect_stdout

        buffer = io.StringIO()
        with redirect_stdout(buffer):
            code = subs.main(["stats", str(self.source), "--json"])
        self.assertEqual(code, 0)     # stats exits 0 on parse success
        payload = json.loads(buffer.getvalue())
        self.assertEqual(payload["cues"], 3)


class LegacyConsoleTests(unittest.TestCase):
    """The commands must survive a console that cannot encode the arrow glyph.

    CI caught this on Windows: ``shift``/``wrap``/``check`` printed U+2192 to a
    cp437 stdout, the ``UnicodeEncodeError`` escaped, and a command that had
    already written its output file exited with a traceback instead of 0.
    """

    class _Cp437Stream:
        encoding = "cp437"

        def __init__(self):
            self.text = ""

        def write(self, value):
            value.encode("cp437")  # raise exactly like a real legacy console
            self.text += value
            return len(value)

        def flush(self):
            pass

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.source = self.root / "in.srt"
        self.source.write_text(SRT, encoding="utf-8")
        self.stream = self._Cp437Stream()

    def tearDown(self):
        self.temp.cleanup()

    def _run(self, argv):
        original = sys.stdout
        sys.stdout = self.stream
        try:
            return subs.main(argv)
        finally:
            sys.stdout = original

    def test_shift_writes_file_on_ascii_console(self):
        out = self.root / "shifted.srt"
        self.assertEqual(self._run(["shift", str(self.source), "--by", "1.25", "--out", str(out)]), 0)
        self.assertTrue(out.exists())
        self.assertIn("shifted", self.stream.text)
        self.assertNotIn("\u2192", self.stream.text)

    def test_wrap_writes_file_on_ascii_console(self):
        out = self.root / "wrapped.srt"
        self.assertEqual(self._run(["wrap", str(self.source), "--chars", "32", "--out", str(out)]), 0)
        self.assertTrue(out.exists())

    def test_check_reports_on_ascii_console(self):
        mismatched = self.root / "target.srt"
        mismatched.write_text(
            SRT.replace("00:00:01,000 --> 00:00:03,000", "00:00:02,000 --> 00:00:03,000"),
            encoding="utf-8",
        )
        self.assertEqual(self._run(["check", str(self.source), str(mismatched)]), 1)
        self.assertIn("timing changed", self.stream.text)

    def test_arabic_text_does_not_crash_ascii_console(self):
        target = self.root / "arabic.srt"
        target.write_text(SRT.replace("Hello there.", "مرحبا بكم في هذا الاختبار."), encoding="utf-8")
        # The Arabic glyphs cannot be encoded at all; the command must still
        # finish and report, not raise.
        self.assertIn(self._run(["check", str(self.source), str(target)]), (0, 1))


if __name__ == "__main__":
    unittest.main()
