"""Self-contained HTML preview with correct RTL typography.

The preview exists so a reviewer can read a translation the way a reader will:
right-to-left, with Arabic letterforms shaped by a real font stack, mirrored
punctuation, and Arabic-friendly line height. It ships as a single file with no
external requests, so it opens offline and can be attached to a review.

This is intentionally not a Markdown engine. It converts the subset Qalam
produces and leaves anything it does not understand as literal text rather than
guessing.
"""

from __future__ import annotations

import html
import re
from typing import Dict, List, Optional, Tuple

from .arabic import language_is_rtl

HEADING = re.compile(r"^(#{1,6})\s+(.*)$")
FENCE = re.compile(r"^(```|~~~)\s*([\w+-]*)")
LIST_ITEM = re.compile(r"^\s*([-*+]|\d+[.)])\s+(.*)$")
RULE = re.compile(r"^\s*([-*_])\s*(?:\1\s*){2,}$")
TABLE_ROW = re.compile(r"^\s*\|(.+)\|\s*$")
TABLE_RULE = re.compile(r"^\s*\|?[\s:-]*-[\s|:-]*$")
QUOTE = re.compile(r"^\s*>\s?(.*)$")
IMAGE = re.compile(r"!\[([^\]]*)\]\(([^)\s]+)(?:\s+\"([^\"]*)\")?\)")
LINK = re.compile(r"\[([^\]]+)\]\(([^)\s]+)(?:\s+\"([^\"]*)\")?\)")
STRONG = re.compile(r"(\*\*|__)(.+?)\1")
EMPH = re.compile(r"(?<![\w*])(\*|_)(?!\s)(.+?)(?<!\s)\1(?![\w*])")
INLINE_CODE = re.compile(r"`([^`\n]+)`")
BARE_URL = re.compile(r"(?<![\"(])\bhttps?://[^\s<>\"]+")

FONT_STACKS = {
    "ar": (
        "'Noto Naskh Arabic', 'Amiri', 'Scheherazade New', 'Traditional Arabic', "
        "'Geeza Pro', 'Segoe UI', 'Dubai', 'Tahoma', serif"
    ),
    "he": "'Noto Sans Hebrew', 'David CLM', 'Segoe UI', 'Arial Hebrew', serif",
    "latin": "'Charter', 'Iowan Old Style', 'Georgia', 'Noto Serif', serif",
}

ARABIC_INDIC_RANGE = "\u0660-\u0669\u06F0-\u06F9"


def _escape(text: str) -> str:
    return html.escape(text, quote=False)


TAG_OR_ENTITY = re.compile(r"<[^>]+>|&[#a-zA-Z0-9]+;")
LATIN_RUN = re.compile(r"[A-Za-z][A-Za-z0-9@._/:#+%-]*")
DIGIT_RUN = re.compile(r"[0-9]+(?:[.,:/][0-9]+)*")


ENTITY = re.compile(r"&[#a-zA-Z0-9]+;")


def _isolate_text_node(text: str) -> str:
    """Wrap Latin and numeric runs in isolates, inside a plain text node only.

    This must never see markup: running it over a finished HTML fragment (as an
    earlier version did) isolates the ``a`` and ``href`` tokens inside tags and
    destroys the document. Text nodes are isolated one at a time.
    """
    def wrap_latin(match: re.Match) -> str:
        value = match.group(0)
        # A single letter is usually an article or a variable; isolating it adds
        # noise without fixing order.
        if len(value) < 2:
            return value
        return f"\u2066{value}\u2069"

    def wrap_digits(match: re.Match) -> str:
        return f"\u2066{match.group(0)}\u2069"

    # Entities stand in for punctuation; isolating inside one would corrupt it
    # into something the browser no longer decodes.
    pieces = ENTITY.split(text)
    entities = ENTITY.findall(text)
    rebuilt = []
    for index, piece in enumerate(pieces):
        piece = LATIN_RUN.sub(wrap_latin, piece)
        piece = DIGIT_RUN.sub(wrap_digits, piece)
        rebuilt.append(piece)
        if index < len(entities):
            rebuilt.append(entities[index])
    return "".join(rebuilt)


def _isolate_rtl_runs(html_fragment: str) -> str:
    """Isolate runs in every text node of an HTML fragment, leaving tags alone."""
    parts = TAG_OR_ENTITY.split(html_fragment)
    tags = TAG_OR_ENTITY.findall(html_fragment)
    output = []
    for index, part in enumerate(parts):
        output.append(_isolate_text_node(part) if part else part)
        if index < len(tags):
            output.append(tags[index])
    return "".join(output)


def _inline(text: str, direction: str) -> str:
    """Convert inline Markdown, protecting code spans from further parsing."""
    stash: List[str] = []

    def stash_code(match: re.Match) -> str:
        stash.append(f"<code>{html.escape(match.group(1))}</code>")
        # The placeholder must contain no digits or Latin letters, or the bidi
        # isolation pass would wrap them and the restore regex would never match
        # — which silently deleted every inline code span from the preview.
        return f"\uE000{chr(0xE100 + len(stash) - 1)}\uE000"

    text = INLINE_CODE.sub(stash_code, text)
    text = _escape(text)
    text = IMAGE.sub(
        lambda m: f'<img src="{html.escape(m.group(2))}" alt="{html.escape(m.group(1))}" loading="lazy">',
        text,
    )
    text = LINK.sub(
        lambda m: f'<a href="{html.escape(m.group(2))}">{m.group(1)}</a>',
        text,
    )
    text = BARE_URL.sub(lambda m: f'<a href="{m.group(0)}">{m.group(0)}</a>', text)
    text = STRONG.sub(r"<strong>\2</strong>", text)
    text = EMPH.sub(r"<em>\2</em>", text)
    if direction == "rtl":
        text = _isolate_rtl_runs(text)

    def restore(match: re.Match) -> str:
        return stash[ord(match.group(1)) - 0xE100]

    return re.sub("\uE000([\uE100-\uE1FF])\uE000", restore, text)


def _table(lines: List[str], direction: str) -> str:
    rows = []
    for line in lines:
        match = TABLE_ROW.match(line)
        if match:
            cells = [cell.strip() for cell in match.group(1).split("|")]
            rows.append(cells)
    if not rows:
        return ""
    header = rows[0]
    body = [row for row in rows[1:] if not TABLE_RULE.match("|" + "|".join(row) + "|")]
    out = ["<table>", "<thead><tr>"]
    for cell in header:
        out.append(f"<th>{_inline(cell, direction)}</th>")
    out.append("</tr></thead><tbody>")
    for row in body:
        out.append("<tr>")
        for cell in row:
            out.append(f"<td>{_inline(cell, direction)}</td>")
        out.append("</tr>")
    out.append("</tbody></table>")
    return "\n".join(out)


def markdown_to_html_body(markdown: str, direction: str = "rtl") -> str:
    lines = markdown.splitlines()
    blocks: List[str] = []
    index = 0
    while index < len(lines):
        line = lines[index]
        if not line.strip():
            index += 1
            continue
        fence = FENCE.match(line)
        if fence:
            marker = fence.group(1)
            language = fence.group(2) or ""
            index += 1
            code_lines = []
            while index < len(lines) and not lines[index].startswith(marker):
                code_lines.append(lines[index])
                index += 1
            index += 1
            language_class = f' class="language-{html.escape(language)}"' if language else ""
            blocks.append(
                f'<pre dir="ltr"><code{language_class}>{html.escape(chr(10).join(code_lines))}</code></pre>'
            )
            continue
        heading = HEADING.match(line)
        if heading:
            level = len(heading.group(1))
            blocks.append(
                f"<h{level}>{_inline(heading.group(2).strip(), direction)}</h{level}>"
            )
            index += 1
            continue
        if RULE.match(line):
            blocks.append("<hr>")
            index += 1
            continue
        if TABLE_ROW.match(line):
            table_lines = []
            while index < len(lines) and TABLE_ROW.match(lines[index]):
                table_lines.append(lines[index])
                index += 1
            blocks.append(_table(table_lines, direction))
            continue
        if QUOTE.match(line):
            quoted = []
            while index < len(lines) and QUOTE.match(lines[index]):
                quoted.append(QUOTE.match(lines[index]).group(1))
                index += 1
            blocks.append(
                f"<blockquote>{_inline(' '.join(quoted), direction)}</blockquote>"
            )
            continue
        list_item = LIST_ITEM.match(line)
        if list_item:
            ordered = list_item.group(1)[0].isdigit()
            tag = "ol" if ordered else "ul"
            items = []
            while index < len(lines):
                match = LIST_ITEM.match(lines[index])
                if not match:
                    break
                items.append(match.group(2))
                index += 1
            body = "\n".join(f"<li>{_inline(item, direction)}</li>" for item in items)
            blocks.append(f"<{tag}>\n{body}\n</{tag}>")
            continue
        paragraph = [line]
        index += 1
        while index < len(lines) and lines[index].strip():
            if (
                HEADING.match(lines[index])
                or FENCE.match(lines[index])
                or LIST_ITEM.match(lines[index])
                or TABLE_ROW.match(lines[index])
                or QUOTE.match(lines[index])
            ):
                break
            paragraph.append(lines[index])
            index += 1
        blocks.append(
            f"<p>{_inline(' '.join(part.strip() for part in paragraph), direction)}</p>"
        )
    return "\n".join(blocks)


CSS_TEMPLATE = """
:root {
  --ink: #16202b;
  --muted: #5b6b7b;
  --bg: #fbfaf7;
  --paper: #ffffff;
  --rule: #e3ded4;
  --accent: #0f6f5c;
  --accent-soft: #e7f2ef;
  --code-bg: #f2f0ea;
}
@media (prefers-color-scheme: dark) {
  :root {
    --ink: #e8e6e1;
    --muted: #9fb0bf;
    --bg: #14181d;
    --paper: #1b2027;
    --rule: #2c343d;
    --accent: #6fd3b8;
    --accent-soft: #1f2c2a;
    --code-bg: #232a32;
  }
}
* { box-sizing: border-box; }
html { -webkit-text-size-adjust: 100%; }
body {
  margin: 0;
  background: var(--bg);
  color: var(--ink);
  font-family: __FONT__;
  font-size: __SIZE__px;
  line-height: __LEADING__;
  text-rendering: optimizeLegibility;
}
main {
  max-width: 38rem;
  margin: 0 auto;
  padding: 3rem 1.25rem 5rem;
}
header.doc {
  margin-bottom: 2.5rem;
  padding-bottom: 1.5rem;
  border-bottom: 1px solid var(--rule);
}
header.doc .eyebrow {
  font-size: 0.78rem;
  letter-spacing: 0.06em;
  text-transform: uppercase;
  color: var(--muted);
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem 1rem;
  align-items: baseline;
}
.tag {
  background: var(--accent-soft);
  color: var(--accent);
  border-radius: 999px;
  padding: 0.1rem 0.55rem;
  font-size: 0.72rem;
  letter-spacing: 0.02em;
}
h1, h2, h3, h4, h5, h6 {
  line-height: 1.3;
  margin: 2.2em 0 0.6em;
  font-weight: 650;
  letter-spacing: 0;
}
h1 { font-size: 1.9em; margin-top: 0; }
h2 { font-size: 1.45em; padding-bottom: 0.25em; border-bottom: 1px solid var(--rule); }
h3 { font-size: 1.18em; }
p, li { margin: 0 0 1.05em; }
p { text-align: __ALIGN__; }
ul, ol { padding-inline-start: 1.6em; }
li { margin-bottom: 0.45em; }
blockquote {
  margin: 1.6em 0;
  padding: 0.6em 1.1em;
  border-inline-start: 3px solid var(--accent);
  background: var(--accent-soft);
  border-radius: 0 6px 6px 0;
  color: var(--muted);
}
code {
  font-family: "JetBrains Mono", "SFMono-Regular", "Cascadia Mono", "Consolas", monospace;
  font-size: 0.9em;
  background: var(--code-bg);
  padding: 0.12em 0.35em;
  border-radius: 4px;
  unicode-bidi: isolate;
}
pre {
  background: var(--code-bg);
  padding: 1em 1.1em;
  border-radius: 8px;
  overflow-x: auto;
  direction: ltr;
  text-align: left;
  border: 1px solid var(--rule);
}
pre code { background: none; padding: 0; font-size: 0.86em; line-height: 1.55; }
a { color: var(--accent); text-underline-offset: 0.18em; }
img { max-width: 100%; height: auto; border-radius: 6px; }
hr { border: 0; border-top: 1px solid var(--rule); margin: 2.5em 0; }
table {
  width: 100%;
  border-collapse: collapse;
  margin: 1.6em 0;
  font-size: 0.95em;
}
th, td {
  border: 1px solid var(--rule);
  padding: 0.55em 0.7em;
  text-align: __ALIGN__;
}
th { background: var(--accent-soft); font-weight: 650; }
:focus-visible { outline: 3px solid var(--accent); outline-offset: 2px; }
.meta-note {
  margin-top: 4rem;
  padding-top: 1rem;
  border-top: 1px solid var(--rule);
  color: var(--muted);
  font-size: 0.82rem;
}
@media print {
  body { background: #fff; color: #000; }
  main { max-width: none; padding: 0; }
  a::after { content: " (" attr(href) ")"; font-size: 0.8em; color: #444; }
}
"""


def build_html(
    markdown: str,
    title: str,
    target_language: str = "ar",
    source_language: str = "en",
    body_font_px: int = 19,
    line_height: float = 1.95,
    meta: Optional[Dict[str, str]] = None,
    align: Optional[str] = None,
) -> str:
    """Render a full, self-contained HTML document."""
    rtl = language_is_rtl(target_language)
    direction = "rtl" if rtl else "ltr"
    font = FONT_STACKS["ar"] if target_language.startswith("ar") else (
        FONT_STACKS["he"] if rtl else FONT_STACKS["latin"]
    )
    text_align = align or ("justify" if rtl else "left")
    css = (
        CSS_TEMPLATE.replace("__FONT__", font)
        .replace("__SIZE__", str(body_font_px))
        .replace("__LEADING__", str(line_height))
        .replace("__ALIGN__", text_align)
    )
    body = markdown_to_html_body(markdown, direction)
    chips: List[str] = []
    if meta:
        for key, value in meta.items():
            if value:
                chips.append(f'<span class="tag">{html.escape(key)}: {html.escape(value)}</span>')
    chips_html = "\n".join(chips)
    return f"""<!doctype html>
<html lang="{html.escape(target_language)}" dir="{direction}">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{html.escape(title)}</title>
<style>{css}</style>
</head>
<body>
<main>
<header class="doc">
<div class="eyebrow">
<span>{html.escape(title)}</span>
{chips_html}
</div>
</header>
<article lang="{html.escape(target_language)}" dir="{direction}">
{body}
</article>
<p class="meta-note">
  Preview generated by Qalam. Text direction, line height, and font stack are
  tuned for {html.escape(target_language)}; code blocks stay left-to-right.
</p>
</main>
</body>
</html>
"""


def write_preview(markdown_path: str, html_path: str, **kwargs) -> str:
    with open(markdown_path, "r", encoding="utf-8") as handle:
        markdown = handle.read()
    html_text = build_html(markdown, **kwargs)
    with open(html_path, "w", encoding="utf-8", newline="\n") as handle:
        handle.write(html_text)
    return html_path
