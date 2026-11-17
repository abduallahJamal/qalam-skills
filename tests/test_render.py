"""Tests for the RTL preview renderer.

The regression these guard: bidi isolation was applied to finished HTML, which
injected isolate characters inside ``<a>`` tags and produced broken markup. Tags
must be untouched; only text nodes get isolated.
"""

from __future__ import annotations

import re
import tempfile
import unittest
from pathlib import Path

from qalam.render import build_html, markdown_to_html_body, write_preview

ISOLATES = "\u2066\u2067\u2068\u2069"


class BodyTests(unittest.TestCase):
    def test_headings_and_paragraphs(self):
        body = markdown_to_html_body("# عنوان\n\nنص عادي.\n")
        self.assertIn("<h1>", body)
        self.assertIn("<p>", body)
        self.assertIn("نص عادي.", body)

    def test_code_block_is_ltr_and_escaped(self):
        body = markdown_to_html_body("```python\nif a < b:\n    pass\n```\n")
        self.assertIn('<pre dir="ltr">', body)
        self.assertIn("a &lt; b", body)
        self.assertNotIn("a < b", body)

    def test_inline_code_is_protected_from_emphasis(self):
        body = markdown_to_html_body("استخدم `a*b*c` هنا")
        self.assertIn("<code>a*b*c</code>", body)
        self.assertNotIn("<em>", body)

    def test_links_render_with_intact_tags(self):
        body = markdown_to_html_body("راجع [ملاحظات المحلل](https://example.com/parser) الآن")
        self.assertIn('<a href="https://example.com/parser">ملاحظات المحلل</a>', body)

    def test_no_isolate_character_inside_a_tag(self):
        """Regression: isolation must never touch markup."""
        body = markdown_to_html_body(
            "راجع [ملاحظات](https://example.com/a) و ![صورة](media/x.png) ثم `code` هنا"
        )
        for tag in re.findall(r"<[^>]+>", body):
            for isolate in ISOLATES:
                self.assertNotIn(isolate, tag, f"isolate leaked into tag: {tag!r}")

    def test_ordered_and_unordered_lists(self):
        body = markdown_to_html_body("1. أول\n2. ثاني\n\n- عنصر\n- آخر\n")
        self.assertIn("<ol>", body)
        self.assertIn("<ul>", body)
        self.assertEqual(body.count("<li>"), 4)

    def test_table_rendering(self):
        body = markdown_to_html_body("| أ | ب |\n| --- | --- |\n| ١ | ٢ |\n")
        self.assertIn("<table>", body)
        self.assertEqual(body.count("<th>"), 2)
        self.assertEqual(body.count("<td>"), 2)

    def test_blockquote(self):
        body = markdown_to_html_body("> اقتباس\n> ثانٍ\n")
        self.assertIn("<blockquote>", body)

    def test_html_is_escaped_in_text(self):
        body = markdown_to_html_body("استخدم <script>alert(1)</script> هنا")
        # No live tag survives...
        self.assertNotIn("<script>", body)
        # ...and the literal text is escaped. The Latin run inside it is isolated
        # for bidi safety, so compare with isolate characters removed.
        plain = body
        for isolate in ISOLATES:
            plain = plain.replace(isolate, "")
        self.assertIn("&lt;script&gt;", plain)

    def test_ltr_direction_skips_isolation(self):
        body = markdown_to_html_body("Use `code` and 42 here", direction="ltr")
        for isolate in ISOLATES:
            self.assertNotIn(isolate, body)

    def test_numbers_are_isolated_in_rtl(self):
        body = markdown_to_html_body("الإصدار 2.0.1 متاح", direction="rtl")
        self.assertIn("\u2066", body)
        self.assertIn("2.0.1", body.replace("\u2066", "").replace("\u2069", ""))


class DocumentTests(unittest.TestCase):
    def test_rtl_document_structure(self):
        html = build_html("# عنوان\n\nنص.", title="كتاب", target_language="ar")
        self.assertIn('<html lang="ar" dir="rtl">', html)
        self.assertIn("Noto Naskh Arabic", html)
        self.assertNotIn("__FONT__", html)

    def test_no_unreplaced_placeholders(self):
        html = build_html("نص", title="ع", target_language="ar")
        self.assertEqual(re.findall(r"__[A-Z]+__", html), [])

    def test_no_external_requests(self):
        html = build_html("نص", title="ع", target_language="ar")
        external = re.findall(r'(?:src|href)="(https?://[^"]+)"', html)
        self.assertEqual([url for url in external if "example" not in url], [])

    def test_ltr_target_gets_ltr_direction(self):
        html = build_html("text", title="T", target_language="en")
        self.assertIn('dir="ltr"', html)

    def test_title_is_escaped(self):
        html = build_html("نص", title="<script>", target_language="ar")
        self.assertNotIn("<title><script>", html)

    def test_font_size_and_leading_are_applied(self):
        html = build_html("نص", title="ع", body_font_px=21, line_height=2.1)
        self.assertIn("font-size: 21px", html)
        self.assertIn("line-height: 2.1", html)

    def test_meta_chips_render(self):
        html = build_html("نص", title="ع", meta={"المصدر": "en", "الطول": "12 صفحة"})
        self.assertIn("المصدر: en", html)

    def test_print_styles_present(self):
        html = build_html("نص", title="ع")
        self.assertIn("@media print", html)


class FileTests(unittest.TestCase):
    def test_write_preview(self):
        with tempfile.TemporaryDirectory() as directory:
            markdown = Path(directory) / "in.md"
            markdown.write_text("# عنوان\n\nنص عربي.\n", encoding="utf-8")
            out = Path(directory) / "out.html"
            write_preview(str(markdown), str(out), title="ع", target_language="ar")
            content = out.read_text(encoding="utf-8")
            self.assertIn("<!doctype html>", content)
            self.assertIn("نص عربي.", content)


if __name__ == "__main__":
    unittest.main()
