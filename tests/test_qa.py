"""Tests for the quality gate.

Each test is a failure the gate exists to catch: lost code, dropped links,
changed numbers, duplicated paragraphs, untranslated text, ASCII punctuation in
Arabic, and terminology drift.
"""

from __future__ import annotations

import unittest

from qalam.glossary import Glossary, Term
from qalam.qa import (
    check_arabic_output,
    check_code_blocks,
    check_duplicate_paragraphs,
    check_inline_code,
    check_length_ratio,
    check_links,
    check_numbers,
    check_terminology,
    render_report,
    run_gate,
)

SOURCE = """# Introduction

The parser must not discard trailing whitespace. See [the docs](https://example.com/docs)
for details, and run `make test` before committing.

```python
def parse(text):
    return text.rstrip("\\n")
```

There are 42 records in the sample dataset.
"""

GOOD = """# مقدمة

يجب ألا يتجاهل المحلل المسافات البيضاء في نهاية النص. راجع
[التوثيق](https://example.com/docs) للتفاصيل، وشغّل `make test` قبل الإيداع.

```python
def parse(text):
    return text.rstrip("\\n")
```

توجد 42 سجلًا في مجموعة البيانات النموذجية.
"""


def codes(findings) -> set:
    return {finding.code for finding in findings}


class CodeTests(unittest.TestCase):
    def test_unchanged_code_passes(self):
        self.assertEqual(check_code_blocks(SOURCE, GOOD), [])

    def test_changed_code_fails(self):
        broken = GOOD.replace('return text.rstrip("\\n")', 'return text.rstrip("\\r\\n")')
        self.assertIn("code_changed", codes(check_code_blocks(SOURCE, broken)))

    def test_missing_block_fails(self):
        broken = GOOD.replace("```python\ndef parse(text):\n    return text.rstrip(\"\\n\")\n```", "")
        self.assertIn("code_blocks", codes(check_code_blocks(SOURCE, broken)))

    def test_inline_code_change_fails(self):
        broken = GOOD.replace("`make test`", "`make build`")
        self.assertIn("inline_code", codes(check_inline_code(SOURCE, broken)))

    def test_inline_code_translated_fails(self):
        broken = GOOD.replace("`make test`", "`اختبار`")
        self.assertIn("inline_code", codes(check_inline_code(SOURCE, broken)))


class LinkTests(unittest.TestCase):
    def test_preserved_link_passes(self):
        self.assertEqual(check_links(SOURCE, GOOD), [])

    def test_dropped_target_fails(self):
        broken = GOOD.replace("(https://example.com/docs)", "(https://example.com/guide)")
        self.assertIn("links", codes(check_links(SOURCE, broken)))

    def test_lost_image_fails(self):
        source = "![diagram](media/fig1.png)\n"
        target = "![رسم](media/fig1.png)\n"
        self.assertEqual(check_links(source, target), [])
        self.assertIn("images", codes(check_links(source, "![رسم](media/fig2.png)\n")))


class NumberTests(unittest.TestCase):
    def test_same_numbers_pass(self):
        self.assertEqual(check_numbers(SOURCE, GOOD), [])

    def test_arabic_indic_digits_are_equivalent(self):
        target = GOOD.replace("42", "٤٢")
        self.assertEqual(check_numbers(SOURCE, target), [])

    def test_changed_number_warns(self):
        broken = GOOD.replace("42", "43")
        self.assertIn("numbers", codes(check_numbers(SOURCE, broken)))

    def test_dropped_number_warns(self):
        broken = GOOD.replace(" 42", "")
        self.assertIn("numbers", codes(check_numbers(SOURCE, broken)))


class LengthTests(unittest.TestCase):
    def test_in_band_passes(self):
        self.assertEqual(check_length_ratio(SOURCE, GOOD, "en", "ar"), [])

    def test_empty_target_is_an_error(self):
        findings = check_length_ratio(SOURCE, "", "en", "ar")
        self.assertEqual(findings[0].severity, "error")

    def test_too_short_is_an_error(self):
        findings = check_length_ratio(SOURCE, "نص قصير جدًا.", "en", "ar")
        self.assertTrue(any(f.code == "length_ratio" and f.severity == "error" for f in findings))

    def test_too_long_warns(self):
        padded = GOOD + ("\n\n" + "كلمة " * 400)
        findings = check_length_ratio(SOURCE, padded, "en", "ar")
        self.assertTrue(any(f.severity == "warn" for f in findings))


class DuplicateTests(unittest.TestCase):
    def test_duplicate_paragraphs_flagged(self):
        paragraph = "هذه فقرة طويلة بما يكفي لاختبار التكرار في الملف الناتج بالكامل."
        target = f"{paragraph}\n\n{paragraph}\n"
        self.assertIn("duplicate_paragraph", codes(check_duplicate_paragraphs(target)))

    def test_distinct_paragraphs_pass(self):
        target = "فقرة أولى طويلة بما يكفي للاختبار هنا ونصها مختلف تمامًا.\n\nفقرة ثانية طويلة بما يكفي للاختبار هنا ونصها مختلف أيضًا.\n"
        self.assertEqual(check_duplicate_paragraphs(target), [])


class ArabicOutputTests(unittest.TestCase):
    def test_arabic_comma_required(self):
        findings = check_arabic_output("هذا نص عربي عادي, ثم تكملة.")
        self.assertIn("arabic_punctuation", codes(findings))

    def test_correct_punctuation_passes(self):
        findings = check_arabic_output("هذا نص عربي عادي، ثم تكملة.")
        self.assertNotIn("arabic_punctuation", codes(findings))

    def test_space_before_punctuation(self):
        findings = check_arabic_output("هذا نص عربي ، ثم تكملة")
        self.assertIn("arabic_spacing", codes(findings))

    def test_mt_smell_reported_as_info(self):
        findings = check_arabic_output("من المهم أن نلاحظ أن النظام يعمل.")
        smells = [f for f in findings if f.code == "mt_smell"]
        self.assertTrue(smells)
        self.assertEqual(smells[0].severity, "info")

    def test_western_numerals_when_arabic_indic_requested(self):
        findings = check_arabic_output("عدد العناصر 125 عنصرًا.", numerals="arabic-indic")
        self.assertIn("numerals", codes(findings))

    def test_non_arabic_text_is_not_checked(self):
        self.assertEqual(check_arabic_output("plain english text"), [])


class TerminologyTests(unittest.TestCase):
    def setUp(self):
        self.glossary = Glossary(
            terms=[Term(source="repository", target="مستودع", category="technical", frequency=9)]
        )

    def test_untranslated_term_warns(self):
        findings = check_terminology("افتح الـ repository ثم شغّل الأمر.", self.glossary)
        self.assertIn("terminology", codes(findings))

    def test_translated_term_passes(self):
        findings = check_terminology("افتح المستودع ثم شغّل الأمر.", self.glossary)
        self.assertNotIn("terminology", codes(findings))


class GateIntegrationTests(unittest.TestCase):
    def test_good_translation_passes_gate(self):
        report = run_gate(SOURCE, GOOD, glossary=None, max_warnings=10)
        self.assertEqual(report["errors"], 0, render_report(report))
        self.assertTrue(report["ok"], render_report(report))

    def test_broken_translation_fails_gate(self):
        broken = GOOD.replace('return text.rstrip("\\n")', "return text").replace("42", "43")
        report = run_gate(SOURCE, broken)
        self.assertFalse(report["ok"])
        self.assertGreater(report["errors"], 0)

    def test_report_renders_metrics(self):
        report = run_gate(SOURCE, GOOD)
        text = render_report(report)
        self.assertIn("ratio", text)
        self.assertIn("errors=", text)

    def test_skip_removes_a_check(self):
        text_with_digit_issue = GOOD.replace("42", "٤٢")
        full = run_gate(SOURCE, text_with_digit_issue, numerals="western")
        skipped = run_gate(SOURCE, text_with_digit_issue, numerals="western", checks=("structure",))
        self.assertGreaterEqual(full["warnings"], skipped["warnings"])

    def test_unknown_check_is_reported(self):
        report = run_gate(SOURCE, GOOD, checks=("not_a_check",))
        self.assertTrue(any(f.code == "gate" for f in report["findings"]))


if __name__ == "__main__":
    unittest.main()
