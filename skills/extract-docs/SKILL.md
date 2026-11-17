---
name: extract-docs
description: Convert PDF, DOCX, EPUB, HTML, and scanned pages into clean Markdown that survives translation — heading structure, tables, code, figures, footnotes, and Arabic extraction pitfalls. Use before translating a book or manual, or when asked to "get the text out of this PDF".
license: MIT
compatibility: Any of pandoc, markitdown, pdftotext (poppler), calibre's ebook-convert, or MinerU/Marker for layout-heavy PDFs. Python 3.9+ optional for verification.
metadata:
  qalam.version: "1.0"
  qalam.kind: procedure
  qalam.category: conversion
---

# Extract documents

Translation quality is capped by extraction quality. A PDF flattened into one
paragraph per page produces a translation that is faithful and unreadable; code
turned into prose produces a translation that is wrong.

**Governing rule:** extraction is a *verification* task, not a conversion task.
Anyone can run `pandoc`; the value is in checking what came out.

## When to use this

- `translate-docs` receives a PDF, DOCX, EPUB, or HTML source.
- The user asks to extract text, convert a book/document to Markdown, or "clean
  up" an OCR dump.
- Arabic PDFs: bidi extraction produces reversed or disconnected text and needs
  the specific checks below.

## Choose the tool by source

| Source | Tool | Why |
| --- | --- | --- |
| DOCX, ODT, EPUB, HTML | `pandoc -t gfm` | Preserves structure; fast; no models |
| DOCX with complex tables | `pandoc` then manual repair | Table merges rarely survive |
| Text-layer PDF | `pdftotext -layout` or `markitdown` | Layout mode keeps columns apart |
| Text-layer PDF with figures/math | MinerU or Marker | Layout-aware; heavy install, ask first |
| Scanned PDF | OCR (tesseract `ara+eng`, or a layout model) | Needs Arabic language data installed |
| Legacy `.doc`/`.ppt` | LibreOffice convert → then pandoc | `soffice --headless --convert-to docx` |
| Web page | `markitdown`, or paste into a Markdown converter | Keep the canonical URL in frontmatter |

Ask before installing anything that downloads models (`pandoc`-incompatible
pip installs, Marker, MinerU). Give the user the command and the download size.

## Procedure

### 1. Establish the reference

Extraction bugs are invisible unless you know what the source contains. Before
converting, record from the original:

- total pages or chapter count,
- the table of contents with page numbers,
- number of figures, tables, and code listings,
- anything unusual: footnotes, marginalia, multi-column layout, RTL body text,
  mixed-script paragraphs.

You will check against these numbers at the end. Without them you cannot tell a
clean extraction from a lossy one.

### 2. Convert

```bash
# DOCX / EPUB / HTML
pandoc input.docx -t gfm --wrap=none --extract-media=./media -o extracted.md

# Text-layer PDF, layout preserved
pdftotext -layout -enc UTF-8 input.pdf - > extracted.txt
# then wrap the text into Markdown, or:
markitdown input.pdf -o extracted.md

# Layout-aware PDF (only if installed and the user agreed)
marker_single input.pdf --output_dir out
```

For Arabic text-layer PDFs, test both `pdftotext` and `markitdown` on one page and
compare: one of them will render logical order correctly and the other will not.

### 3. Repair structure

Extraction output needs three kinds of repair. Do them in this order.

**Headings.** Decide the level scheme and apply it. A PDF gives you bold lines,
not headings; a DOCX usually gives real heading styles that pandoc converts
correctly.

```text
# Book title
## Part
### Chapter
#### Section
```

**Paragraphs.** OCR and `pdftotext` break lines mid-sentence. Join lines that end
without terminal punctuation and continue in the same paragraph; keep hard breaks
only where the source has them (poetry, code, addresses).

**Tables.** A table that lost its header row is worse than no table: the
translator cannot tell which cell is the label. Rebuild from the source
screenshot or page image when the extracted text is ambiguous.

### 4. Arabic-specific extraction problems

These are the ones that silently produce garbage:

| Symptom | Cause | Fix |
| --- | --- | --- |
| Letters disconnected: "م ر ح ب ا" | Presentation forms or missing shaping | Check for U+FB50–U+FEFF; convert with NFKC; if the PDF has no text layer, OCR with `ara` data |
| Text in visual order (reversed) | PDF stores glyph positions, not logical order | Re-extract with a tool that reorders bidi (`pdftotext -layout` usually does; some OCR does not) |
| Numbers reversed (`123` → `321`) | Bidi run split | Isolate numeric runs; verify against the page image |
| Latin words inside Arabic reversed | Same | Same |
| Broken words at line ends | Hyphenation or kashida | Rejoin; never hyphens in Arabic |
| Diacritics detached | Presentation-form extraction | NFKC normalisation, then spot-check |
| Footnote markers moved | Text-layer ordering | Move markers back to their anchors |

Always verify against the page image for at least: the first page, one page with
numbers, one page with Latin text, one page with a table.

### 5. Verify the extraction

```bash
python -m qalam lang extracted.md          # script distribution, direction
python -m qalam chunk extracted.md --out-dir /tmp/check --target-chars 6000
```

Compare with the reference you recorded:

- [ ] Chapter count matches the table of contents
- [ ] Heading count and levels are plausible
- [ ] Figure count matches; every image has an alt text placeholder
- [ ] Table count matches
- [ ] No page numbers left inline as stray digits
- [ ] No running headers/footers repeated per page
- [ ] No hyphenation artifacts (`-` at line end followed by lowercase)
- [ ] First and last paragraph of each chapter are complete sentences
- [ ] Arabic: letters joined, logical order, numbers correct
- [ ] Code blocks still look like code

### 6. Clean up

- Strip running headers, footers, and page numbers (they become noise in a
  translation and inflate the word count).
- Normalise whitespace: one space after punctuation, no trailing spaces, single
  blank line between paragraphs.
- Convert smart quotes consistently (`“ ” ‘ ’` → `"` `'`, or keep typographic
  quotes throughout — pick one).
- Replace ligatures and presentation forms (NFKC).
- Keep images: extract them to `media/`, keep relative paths, and add alt text
  placeholders so a translator can translate them.
- Keep the original filename and record the source in a small frontmatter block:

```yaml
---
source_file: book.pdf
source_pages: 412
extracted_by: pdftotext -layout
extracted_on: 2026-11-05
known_issues: "figures 12 and 19 lost their captions in the source"
---
```

### 7. Report

Give: tool used, page/chapter counts before and after, structures repaired,
anything lost, and the exact list of pages a human should eyeball. Then hand off
to `translate-docs`.

## What "clean" means for translation

A translation-ready Markdown file has:

- headings that reflect the real hierarchy,
- paragraphs that are single logical paragraphs,
- tables with headers,
- code in fences, untouched,
- no page furniture,
- no OCR noise,
- figures with alt text,
- a stable chunk size that does not cut a table or a code block.

## Failure modes

| Symptom | Cause | Fix |
| --- | --- | --- |
| Translation is fluent but repeats itself | Extracted text contains duplicated columns | Re-extract without `-layout`, or with column detection |
| Whole sections missing | PDF pages are images | OCR those pages |
| Arabic reads backwards in the editor | Editor lacks RTL/bidi support | Verify in a bidi-aware viewer before "fixing" the text |
| Code translated into prose | Extraction dropped fences | Re-fence every code block before translating |
| Table cells merged across rows | DOCX merged cells | Rebuild that table manually |
| Chapter headings became bold paragraphs | No heading styles in source | Apply the heading scheme manually; do not translate first |

## References

- `references/extraction-tools.md` — commands, flags, and trade-offs.
- `references/pdf-arabic.md` — bidi and shaping repair in detail.
