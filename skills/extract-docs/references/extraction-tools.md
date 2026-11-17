# Extraction tools

## pandoc

Best for: DOCX, EPUB, ODT, HTML, LaTeX, and anything with a real structure.

```bash
# DOCX → GitHub-flavoured Markdown, media extracted
pandoc book.docx -t gfm --wrap=none --extract-media=media -o book.md

# EPUB → Markdown, one file
pandoc book.epub -t gfm --wrap=none --extract-media=media -o book.md

# HTML → Markdown, keep tables
pandoc page.html -f html -t gfm --wrap=none -o page.md

# PDF — only for text-layer PDFs with simple layout; check output carefully
pandoc book.pdf -t gfm --wrap=none -o book.md

# Split by chapter when the source has real headings
pandoc book.epub -t gfm --wrap=none --split-level=1 -o chapter.md
```

Flags that matter:

| Flag | Effect |
| --- | --- |
| `--wrap=none` | No hard line breaks at 72 columns (essential for diffing and chunking) |
| `--extract-media=DIR` | Images written out with rewritten relative paths |
| `--split-level=N` | One output file per heading of level N or higher |
| `-t gfm` | GitHub-flavoured Markdown: tables, strikethrough, task lists |
| `--markdown-headings=atx` | `#` headings instead of `===` underlines |
| `--strip-comments` | Drop HTML comments |
| `--id-prefix` | Avoid duplicate anchor ids when merging files |

Known limits: complex merged table cells simplify, footnotes flatten, and
`--wrap=none` can produce very long lines (fine for machines, hard to review).

## pdftotext (poppler)

Best for: text-layer PDFs where you want raw text and control.

```bash
pdftotext -layout -enc UTF-8 book.pdf book.txt   # layout: keeps columns apart
pdftotext -enc UTF-8 book.pdf -                  # stream to stdout
pdftotext -f 12 -l 20 book.pdf chapter.txt       # page range
```

`-layout` preserves the visual arrangement; without it, pdftotext reflows and
interleaves columns. For RTL PDFs, test both: one of them usually produces
logical order and the other does not.

There is no Markdown output. You get text, and you add structure yourself.

## markitdown

Best for: PDF, DOCX, PPTX, XLSX, HTML, and mixed input with one command.

```bash
markitdown book.pdf -o book.md
python -m markitdown book.pdf > book.md
```

Produces Markdown directly. Quality on complex layout is lower than a dedicated
layout model, but it is fast and needs no model download.

## Calibre (ebook-convert)

Best for: converting between ebook formats, and as a fallback for EPUB→DOCX.

```bash
ebook-convert book.epub book.docx
ebook-convert book.pdf book.epub    # poor for layout-heavy PDFs
```

Useful when a PDF has to become an EPUB for a reader, not when you need clean
Markdown.

## Marker / MinerU (layout-aware, model-based)

Best for: academic PDFs with formulas, multi-column layout, and figures.

```bash
# Marker
marker_single book.pdf --output_dir out
# MinerU (v2+)
mineru-kit parse book.pdf -o out
```

Trade-offs: they download models (hundreds of MB), run slowly on CPU, and produce
noisy artefacts on decorative layouts. Ask before installing, and use them only
when the extracted structure actually matters.

## tesseract (OCR)

Best for: scanned pages with no text layer.

```bash
# Arabic + English, per page
tesseract page-012.png page-012 -l ara+eng --psm 3
```

- `--psm 3` (default) for a full page, `--psm 6` for a single block.
- Arabic OCR needs `tesseract-ocr-ara` installed; without it you get Latin
  garbage from Arabic glyphs.
- OCR output always needs the Arabic checks in `pdf-arabic.md`: shaping, bidi,
  and numbers.

## LibreOffice (legacy formats)

```bash
soffice --headless --convert-to docx --outdir converted old.doc
soffice --headless --convert-to html --outdir converted old.rtf
```

Convert to DOCX or HTML first, then use pandoc. LibreOffice's own Markdown export
is weaker than pandoc's.

## Choosing quickly

```text
Is there a text layer?
├─ no  → OCR (tesseract for simple, a layout model for hard)
└─ yes
   ├─ DOCX/EPUB/HTML → pandoc
   ├─ simple PDF → pdftotext -layout | markitdown
   └─ complex PDF (math, columns, figures) → Marker/MinerU (ask first)

Is the text Arabic?
└─ always run the bidi/shaping checks in pdf-arabic.md afterwards
```
