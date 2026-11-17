---
name: translate-docs
description: Translate long documents, books, and docs between any two languages with consistent terminology, checksummed structure, and a QA gate; Arabic-first defaults with RTL typography, Arabic punctuation, and numbered-script rules. Use when the user asks to translate a Markdown file, book, manual, or whole docs folder, especially Arabic ↔ English.
license: MIT
compatibility: Needs Python 3.9+ for the bundled `qalam` CLI. Optional: pandoc, calibre (ebook-convert) or markitdown to convert PDF/DOCX/EPUB into Markdown first.
metadata:
  qalam.version: "1.0"
  qalam.kind: procedure
  qalam.category: translation
---

# Translate documents

You translate whole documents, not snippets. A book or a manual is long enough
that a single pass degrades: terminology drifts, sections get skipped, and code
turns into prose. This skill turns translation into a pipeline with a state file,
a term base, and a gate that runs on real files.

**The rule that governs everything below:** a translation must be complete,
terminologically consistent, and structurally identical to the source. Style is
a judgement call; those three are not.

## When to use this

The user wants a document translated, or says any of: "translate this book",
"عرّب هذا الملف", "translate the docs folder", "make an Arabic version",
"translate to Arabic/French/Japanese", "turn this PDF into Arabic Markdown".

- PDF/DOCX/EPUB input → load `extract-docs` first, then come back here.
- Subtitle files (.srt/.vtt) → load `subtitle-translate`.
- Application strings (.json/.resx/.po/.arb) → load `localize-app`.
- A paragraph or a single page → just translate it; the pipeline is overhead.

## Inputs to confirm before starting

Ask only for what is missing. Do not interrogate the user for the rest.

| Input | Default | Notes |
| --- | --- | --- |
| `source` | — | File or folder of Markdown. Required. |
| `source_language` | auto | Run `python -m qalam lang <file>` and confirm if unclear. |
| `target_language` | `ar` | A BCP-47 code: `ar`, `ar-EG`, `en`, `fr`, `ja`. |
| `register` | from source | `formal` (فصحى معاصرة) for books and docs, `neutral` for blogs, `technical` for manuals. |
| `numerals` | `preserve` | Western, Arabic-Indic (٠١٢), or preserve the source. |
| `glossary` | new | Existing `glossary.json` if the project has one. |
| `audience` | general | Used for register and example choices only. |

State the values you inferred in one line and continue. This is a long task; a
confirmation loop on defaults wastes the user's time.

## Setup

```bash
python -m qalam info                 # version, skills, en→ar ratio band
python -m qalam install --tools claude codex cursor opencode --dry-run
```

If `python -m qalam` fails, the bundle is not on `PYTHONPATH`. Use the path the
skill was loaded from: `python3 <skill-dir>/../../qalam/cli.py` or add the repo
root to `PYTHONPATH`. Do not reimplement these steps inline — the whole point of
the CLI is that the numbers are computed, not guessed.

## Procedure

### 1. Prepare the working directory

```bash
mkdir -p work/ar && cp -n source.md work/source.md
python -m qalam lang work/source.md
python -m qalam chunk work/source.md --out-dir work/ar --target-chars 6000 --max-chars 12000
```

`work/ar/` now holds `chunk0001.md …`, `chunkNNNN.md`, and `manifest.json`.
Read `manifest.json` once: it lists every chunk with its heading path, size, and
whether it contains code or a table. That is your work plan.

Never translate `manifest.json`, and never rename a chunk file.

### 2. Build or load the term base

```bash
python -m qalam glossary build work/source.md --out work/ar/glossary.json --code
python -m qalam glossary show work/ar/glossary.json
```

The build step proposes candidates only — every `target` is empty. Fill in the
targets yourself for names, products, and domain terms; leave `keep_as_is`
entries alone (code identifiers). Then audit:

```bash
python -m qalam glossary audit work/ar/glossary.json
```

An unattended glossary is worse than none: it locks in mistakes for the whole
document. Spend the time here, on the 20–40 terms that actually repeat.

Rules for a good entry:

- One source form per concept. Polysemous words get separate entries with an
  alias on each, never one entry with two meanings.
- `gender` matters in Arabic: `masculine`, `feminine`, `plural`, or `unknown`.
  Fill it for people and for nouns whose gender is not obvious.
- If a name should stay in Latin script (a brand, a CLI flag), set
  `keep_as_is: true` and put the same string in `target`.
- Arabic targets for feminine proper nouns must match the verb agreement used in
  the target language. `امرأة` is feminine; `شخص` can be either.

If a glossary already exists, do not rebuild it. Load it and merge:

```bash
python -m qalam glossary build work/source.md --from-glossary work/ar/glossary.json --out work/ar/glossary.json
```

### 3. Plan the run

```bash
python -m qalam plan work/ar --glossary work/ar/glossary.json --target-language ar --json
```

`translation_chunk_ids` is your queue. `record_only_chunk_ids` already have a
usable output; record them and move on. `unchanged_chunk_ids` are done.

```bash
python -m qalam record work/ar chunk0003 chunk0007 --glossary work/ar/glossary.json --target-language ar
```

The plan is the only source of truth about what is left. Do not decide by
glancing at filenames, and do not retranslate the whole set because one chunk
changed — that is what the state file prevents.

### 4. Translate chunk by chunk

For each chunk in the queue, in order:

1. Read `chunkNNNN.md` in full. Do not start writing before you have read it.
2. Get the terms that apply to this chunk:

   ```bash
   python -m qalam glossary terms work/ar/glossary.json work/ar/chunk0007.md
   ```

3. Translate into `output_chunkNNNN.md` following the rules in
   `references/translation-rules.md` and, for Arabic,
   `references/arabic-typography.md`.
4. Self-check *before* writing the file. Run the gate on the pair:

   ```bash
   python -m qalam gate --source work/ar/chunk0007.md --target work/ar/output_chunk0007.md \
     --source-language <src> --target-language <tgt> --glossary work/ar/glossary.json
   ```

   Fix every `error`. Read every `warn` and either fix it or explain why it is
   intentional. `info` lines are review notes, not blockers.
5. Only when the gate has no errors, record the chunk:

   ```bash
   python -m qalam record work/ar chunk0007 --glossary work/ar/glossary.json --target-language ar
   ```

Writing the file before the check is the most common cause of a half-translated
document that looks finished. Write, check, then record.

**Parallelism.** If the host supports sub-agents, one chunk per sub-agent, four
to eight at a time. Each sub-agent gets: its chunk path, its output path, the
target language, the term table from step 2, and the two reference files. A
sub-agent that cannot run the gate reports its chunk as `review` rather than
pretending it passed:

```bash
python -m qalam record work/ar chunk0011 --status review --note "gate: 2 warnings unread"
```

### 5. Merge and verify the whole document

```bash
python -m qalam merge --source-dir work/ar --translated-dir work/ar --out work/final.md --strict
python -m qalam gate --source work/source.md --target work/final.md \
  --source-language <src> --target-language <tgt> --glossary work/ar/glossary.json
```

`--strict` fails on missing or blank chunks. Treat a failure as unfinished work,
not as a warning to mention in passing.

Then check the things the gate cannot see, by reading:

- Chapter openings and closings — the places translations usually break.
- Every heading, and the table of contents if the source has one.
- The first and last paragraph of every chunk boundary, where a dropped sentence
  hides most easily.
- Anything the glossary marked `keep_as_is`.

### 6. Deliver a readable preview

```bash
python -m qalam preview work/final.md --out work/preview.html \
  --target-language ar --source-language <src> --title "<book title>"
```

The preview is a single self-contained file: RTL direction, Arabic font stack,
Arabic-friendly line height, code blocks forced LTR, and mirrored punctuation.
Open it, or tell the user to open it — do not paste a whole book into chat.

### 7. Report honestly

Deliver:

- Path to the translated file and to the preview.
- A short table: chunks total / translated / reused from memory / flagged.
- Every gate finding you accepted without fixing, with one line of reasoning.
- What you did not verify (figures, footnotes, anything visual).
- The commands to re-run after edits, so the user can maintain the translation.

Do not claim the translation is "complete and accurate". State what was checked
and what was not.

## Translation rules that are not negotiable

Full detail is in `references/translation-rules.md`; the short version:

1. **Never translate code.** Fenced blocks, inline code, CLI flags, file paths,
   URLs, and HTML tags are copied byte for byte.
2. **Never invent content.** If the source is ambiguous, translate the ambiguity,
   not a guess. If something is genuinely untranslatable, keep it and note it.
3. **Never drop content.** Every sentence in the source has a counterpart.
4. **Keep the structure.** Same number of headings, list items, links, and
   images, in the same order.
5. **Use the glossary.** A term with a target is not a suggestion.
6. **Match the register of the source**, not the house style of the model.
7. **Translate meaning, not words.** Idioms become idioms; units, dates, and
   names follow the target locale's conventions.
8. **Leave the author's voice intact.** Do not add introductory sentences,
   summaries, or "in this section we will" filler.

## Arabic specifics

Load `references/arabic-typography.md` before translating into Arabic. The
parts that break most often:

- **Punctuation is Arabic**: `،` `؛` `؟`, and the Arabic comma after a clause.
  Western `, ; ?` inside Arabic prose is a gate warning.
- **Numerals**: follow the `numerals` input. Keep Western digits inside code,
  URLs, and version numbers even when prose uses ٠١٢.
- **No tashkeel by default.** Add harakat only where the source disambiguates
  meaning or the user asks; a fully vocalised body text reads like a schoolbook.
- **Bidirectional text**: when a Latin name or number sits in an Arabic
  sentence, the renderer handles order — do not insert directional marks by
  hand unless the gate or a visual check proves it necessary.
- **Terminology consistency beats elegance.** The same English term becomes the
  same Arabic term everywhere, even where a synonym would read better.
- **No machine-translation tells.** "من المهم أن نلاحظ", "لا شك أن", "في عالم
  اليوم" are flagged by the gate; rewrite them.

## Failure modes and what to do

| Symptom | Cause | Fix |
| --- | --- | --- |
| Gate reports low length ratio | A chunk was truncated or a chunk is missing | Re-translate that chunk; never pad with words |
| Gate reports `code_changed` | Code was "improved" while translating | Copy the block verbatim from the source |
| `plan` keeps listing the same chunks | Output was written but never recorded | Run `qalam record` after the gate passes |
| Terminology warnings after a glossary edit | Aliases changed | Expected: the planner invalidates only affected chunks. Re-translate those. |
| Arabic text renders backwards in a viewer | Viewer lacks RTL support | Deliver the HTML preview; do not "fix" it with directional marks |
| Numbers changed | Locale conversion | Numbers are content; keep the value, change only digit style |

## References

- `references/translation-rules.md` — the full rule set, with examples.
- `references/arabic-typography.md` — RTL, punctuation, numerals, harakat.
- `references/pipeline.md` — file layout, state file, resuming, troubleshooting.
- `references/prompts.md` — ready prompts for sub-agents and review passes.
