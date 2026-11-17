# Arabic PDF extraction

PDF is a page description format, not a text format. Each glyph is placed at
coordinates, in whatever order the producer emitted them. For Arabic that means
extraction can return disconnected letters, visual (reversed) order, or both.

## The three failure modes

### 1. Disconnected letters

Arabic letters change shape by position (initial, medial, final, isolated). Some
PDFs store the *shaped* glyphs, which Unicode sees as presentation forms
(U+FB50–U+FEFF) rather than the base letters (U+0600–U+06FF).

Symptom: text looks fine on screen, but search fails, and copying yields
"ﻣﺮﺣﺒﺎ" (presentation forms) instead of "مرحبا".

Fix:

```python
import unicodedata
text = unicodedata.normalize("NFKC", text)   # folds presentation forms to base letters
```

Verify: after NFKC, no character should be in U+FB50–U+FEFF.

```python
bad = [c for c in text if "\uFB50" <= c <= "\uFDFF" or "\uFE70" <= c <= "\uFEFF"]
print(len(bad), "presentation-form characters remain")
```

### 2. Visual order (reversed text)

The PDF places the glyph for the last word at the smallest x. Extractors that
read in coordinate order produce "ابلحرم" instead of "مرحبا".

Symptom: the text reads backwards character-by-character or word-by-word.

Fix: use an extractor that applies the Latin/Arabic bidi algorithm and converts
visual order back to logical order. In practice:

- `pdftotext` with `-layout` usually produces logical order for Arabic PDFs.
- Some OCR pipelines produce visual order; check before trusting.
- No tool is reliable for every PDF; always verify against the page image.

There is no safe automatic reversal. Do not "fix" bidi by reversing strings —
ligatures, numbers, and Latin runs inside Arabic make reversal lossy.

### 3. Numbers and Latin runs out of place

`الإصدار 2.0.1 متاح` can extract as `الإصدار 1.0.2 متاح` or with the number moved.

Fix: isolate numeric and Latin runs during verification, compare against the page
image, and correct by hand where the tool got it wrong. Numbers are content.

## Verification workflow

1. Render the page to an image (`pdftoppm -f 12 -l 12 -r 150 book.pdf page`).
2. Extract the same page to text.
3. Compare structure: paragraph count, numbers, Latin words, bracketed content.
4. Read the extracted page in a bidi-aware viewer. Browsers and most modern
   editors are correct; a terminal or a log file is not a reliable check.
5. Record the pages you verified. State in the report which pages were not.

## Diacritics

Fully vocalised religious or poetic text often loses marks or places them on the
wrong consonant. Check a sample against the image. If diacritics matter for the
work, extract with a layout-aware model, not with plain text extraction.

## Kashida and justification

PDFs justify Arabic with kashida (tatweel, U+0640) inserted between letters.
Extraction leaves them in, and they break search and matching.

```python
text = text.replace("\u0640", "")
```

The Qalam normaliser does this automatically for matching; do it on the extracted
text too, before translation.

## Tables

Arabic tables are usually right-to-left: the first logical column is the
rightmost on the page. Extractors commonly emit columns left-to-right, which
reverses the table's meaning.

Check: if the header row reads as if the label column is on the left when the
page shows it on the right, reverse the column order in the Markdown table and
note it.

## Mixed-script paragraphs

Arabic technical books quote code, URLs, and English terms inline. Extraction
often:

- reverses a Latin run inside an Arabic line,
- drops the spaces around it,
- merges a code span into the Arabic sentence.

Fix: re-check every line that contains both scripts; wrap the Latin run in code
spans if the source renders it as code.

## Quick audit script

```python
import re, sys, unicodedata

text = open(sys.argv[1], encoding="utf-8").read()
normalised = unicodedata.normalize("NFKC", text)

checks = {
    "presentation forms": len(re.findall(r"[\uFB50-\uFEFF]", text)),
    "tatweel": text.count("\u0640"),
    "arabic chars": len(re.findall(r"[\u0620-\u064A]", text)),
    "latin words": len(re.findall(r"\b[A-Za-z]{3,}\b", text)),
    "ascii commas after arabic": len(re.findall(r"[\u0620-\u064A]\s*,", text)),
    "lone page numbers": len(re.findall(r"^\s*\d{1,4}\s*$", text, re.M)),
}
for name, value in checks.items():
    print(f"{name:28} {value}")

if checks["presentation forms"]:
    print("\n→ run NFKC before translating")
if checks["ascii commas after arabic"]:
    print("→ likely a visual-order extraction; verify against page images")
```

A file with many lone page numbers needs page-furniture removal before chunking;
otherwise the translation includes "٢٣" as a paragraph, and the chunker spends
context on it.
