"""Tests for the Arabic text primitives."""

from __future__ import annotations

import unittest

from qalam.arabic import (
    ARABIC_MT_SMELLS,
    LTR,
    NEUTRAL,
    RTL,
    balance_brackets,
    estimate_direction,
    isolate_ltr,
    isolate_rtl,
    language_is_rtl,
    mask_protected,
    normalise_arabic,
    normalise_digits,
    protected_spans,
    script_distribution,
    strip_diacritics,
    strip_tatweel,
    to_digits,
)


class DirectionTests(unittest.TestCase):
    def test_arabic_is_rtl(self):
        self.assertEqual(estimate_direction("مرحبا بالعالم"), RTL)

    def test_english_is_ltr(self):
        self.assertEqual(estimate_direction("hello world"), LTR)

    def test_leading_number_does_not_decide_direction(self):
        # A leading digit is a weak character; the first strong char decides.
        self.assertEqual(estimate_direction("2026 سنة جديدة"), RTL)

    def test_punctuation_only_is_neutral(self):
        self.assertEqual(estimate_direction("1234 .,;"), NEUTRAL)

    def test_hebrew_is_rtl_but_detected_as_rtl(self):
        self.assertEqual(estimate_direction("שלום עולם"), RTL)

    def test_language_is_rtl_handles_regions(self):
        self.assertTrue(language_is_rtl("ar-EG"))
        self.assertTrue(language_is_rtl("fa"))
        self.assertFalse(language_is_rtl("en-US"))
        self.assertFalse(language_is_rtl(""))


class DigitTests(unittest.TestCase):
    def test_to_digits_scripts(self):
        self.assertEqual(to_digits(1234), "1234")
        self.assertEqual(to_digits(1234, "arabic-indic"), "١٢٣٤")
        self.assertEqual(to_digits(1234, "extended-arabic-indic"), "۱۲۳۴")

    def test_to_digits_rejects_unknown_script(self):
        with self.assertRaises(ValueError):
            to_digits(1, "roman")

    def test_normalise_digits_folds_both_scripts(self):
        self.assertEqual(normalise_digits("١٢٣ ۱۲۳ 123"), "123 123 123")


class NormalisationTests(unittest.TestCase):
    def test_alef_forms_fold(self):
        self.assertEqual(
            normalise_arabic("أحمد إبراهيم آدم"),
            normalise_arabic("احمد ابراهيم ادم"),
        )

    def test_tatweel_is_removed(self):
        self.assertEqual(strip_tatweel("مـــرحبا"), "مرحبا")

    def test_diacritics_are_optional(self):
        vocalised = "كِتَابٌ جَدِيد"
        plain = "كتاب جديد"
        self.assertEqual(
            normalise_arabic(vocalised, keep_diacritics=False),
            normalise_arabic(plain, keep_diacritics=False),
        )
        self.assertNotEqual(strip_diacritics("كِتَاب"), "كِتَاب")

    def test_presentation_forms_fold_to_base_letters(self):
        # U+FEA0..U+FEFC are Arabic presentation forms.
        presentation = "\uFEDF\uFE8E"   # LAM + ALEF final forms
        folded = normalise_arabic(presentation)
        self.assertTrue(all(0x0600 <= ord(ch) <= 0x06FF or ch.isspace() for ch in folded))

    def test_whitespace_collapses(self):
        self.assertEqual(normalise_arabic("مرحبا   \u00A0  بالعالم"), "مرحبا بالعالم")


class ScriptDistributionTests(unittest.TestCase):
    def test_pure_arabic(self):
        shares = script_distribution("هذا نص عربي بالكامل")
        self.assertGreater(shares["arabic"], 0.9)

    def test_mixed(self):
        shares = script_distribution("hello عالم")
        self.assertAlmostEqual(shares["latin"], 5 / 9, places=2)
        self.assertAlmostEqual(shares["arabic"], 4 / 9, places=2)

    def test_empty_text_is_all_zero(self):
        self.assertEqual(script_distribution("")["arabic"], 0.0)


class BracketTests(unittest.TestCase):
    def test_balanced(self):
        self.assertEqual(balance_brackets("(نص) [آخر] «ثالث»"), [])

    def test_unclosed(self):
        problems = balance_brackets("(مرحبا")
        self.assertEqual(len(problems), 1)
        self.assertIn("unclosed", problems[0])

    def test_mismatched(self):
        self.assertTrue(balance_brackets("(مرحبا]"))

    def test_unexpected_closer(self):
        self.assertTrue(balance_brackets("نص)"))


class IsolationTests(unittest.TestCase):
    def test_isolate_wraps_in_unicode_isolates(self):
        self.assertEqual(isolate_rtl("نص"), "\u2067نص\u2069")
        self.assertEqual(isolate_ltr("abc"), "\u2066abc\u2069")


class ProtectedSpanTests(unittest.TestCase):
    def test_code_and_links_are_protected(self):
        # Inline code, link target, and the two HTML tags = four protected spans.
        text = "استخدم `npm i` ثم [docs](https://x.dev) و<b>وسم</b>"
        spans = protected_spans(text)
        self.assertEqual(len(spans), 4)
        self.assertEqual(text[spans[0][0]:spans[0][1]], "`npm i`")

    def test_masking_round_trips(self):
        text = "شغّل `make` الآن"
        masked, saved = mask_protected(text)
        self.assertNotIn("make", masked)
        self.assertEqual(saved, ["`make`"])
        restored = masked
        for index, value in enumerate(saved):
            restored = restored.replace(f"\uE000{index}\uE000", value)
        self.assertEqual(restored, text)


class MtSmellTests(unittest.TestCase):
    def test_known_phrases_are_recorded(self):
        self.assertIn("من المهم أن نلاحظ", ARABIC_MT_SMELLS)
        self.assertTrue(all(isinstance(v, str) for v in ARABIC_MT_SMELLS.values()))


if __name__ == "__main__":
    unittest.main()
