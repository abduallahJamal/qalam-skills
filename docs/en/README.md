# Qalam — Arabic-first skills for coding agents

Qalam is a skill pack for Claude Code, Codex CLI, Cursor, and OpenCode, plus the
toolkit the skills call. Each skill is one `SKILL.md` folder written to the Agent
Skills specification, so the same directory loads in all four hosts without a
per-host variant.

The design rule: **the model decides what to do, the tool computes the answer.**
Every deterministic step — chunking, the quality gate, term matching, subtitle
timing — runs in a bundled standard-library Python package. A skill that asks a
model to recount lines will be wrong on the input that matters.

```text
qalam-skills/
├── skills/           nine self-contained skills
├── qalam/            Python package (stdlib only, no network)
├── bin/qalam         run straight from a checkout
├── demo/             one end-to-end run you can execute
└── tests/            212 tests, all offline
```

---

## The skills

| Skill | Load it when | It does |
| --- | --- | --- |
| `translate-docs` | Translating a book, manual, or docs folder | Chunking, glossary, resumable state, quality gate, RTL preview |
| `arabic-style` | Editing Arabic prose, proofreading, "make it natural" | Register, rhythm, punctuation, machine-translation artefacts — without changing meaning |
| `rtl-layout` | An Arabic UI is reversed, clipped, or unreadable | Logical properties, bidi isolation, icon mirroring, per-framework snippets |
| `glossary-builder` | Terminology drifts across a long project | Build, audit, and inject a bilingual term base |
| `translation-qa` | Reviewing a translation before publishing | Mechanical gate + structured reading + severity-ranked report |
| `localize-app` | Adding Arabic to an application | JSON/resx/po/arb/strings, placeholder safety, six plural categories |
| `extract-docs` | Getting text out of PDF/DOCX/EPUB | Clean Markdown, plus the specific ways Arabic PDF extraction fails |
| `subtitle-translate` | Subtitling a video | Reading speed, line breaking, timing checks, RTL display |
| `skill-forge` | Writing or reviewing a skill | Portable frontmatter, triggering descriptions, failure tables |

Every skill opens with a **governing rule** that defines "done", then a numbered
procedure, a failure table, and a report contract. None of them say "be
thorough"; they say what is checked and how.

---

## Install

```bash
python3 -m qalam install --tools claude codex cursor opencode --dry-run
python3 -m qalam install --tools claude codex cursor opencode
```

The default mode is a **link**, so editing a skill edits it in every host at once.
On Windows a directory junction is used, which needs no administrator rights. If
linking fails on the target filesystem, the installer copies instead and says so.

| Tool | User scope | Project scope |
| --- | --- | --- |
| Claude Code | `~/.claude/skills/` | `.claude/skills/` |
| Codex CLI | `~/.codex/skills/` | `.codex/skills/` |
| Cursor | `~/.cursor/skills/` | `.cursor/skills/` |
| OpenCode | `~/.config/opencode/skills/` | `.opencode/skills/` |
| Portable | `~/.agents/skills/` | `.agents/skills/` |

```bash
python3 -m qalam install --tools claude cursor --scope project
python3 -m qalam install --tools cursor --scope project --cursor-rule
python3 -m qalam doctor --details
python3 -m qalam uninstall --tools codex --skill translate-docs
```

Manual install is a plain copy of the skill folder. Then restart the agent: most
hosts read skill metadata once, at session start.

---

## Use

Ask in natural language; the description is what triggers the skill. Name the
object and the intent:

- "Translate this book into Arabic and keep the terminology consistent"
- "Review this translation before we publish"
- "The interface flips the wrong way in Arabic"
- "Localise `en.json` into Arabic"

Or invoke explicitly: `/translate-docs` in Claude Code, `$translate-docs` in Codex.

Every skill is also usable from a terminal:

```bash
./bin/qalam chunk docs/manual.md --out-dir work/ar --target-chars 6000
./bin/qalam glossary build docs --out work/ar/glossary.json --code
./bin/qalam plan work/ar --glossary work/ar/glossary.json --target-language ar
./bin/qalam gate --source docs/manual.md --target work/final.ar.md --glossary work/ar/glossary.json
./bin/qalam preview work/final.ar.md --out work/preview.html --target-language ar
```

---

## How the pipeline holds together

```text
source document
   ├─ qalam chunk ─────────► chunk0001.md … + manifest.json
   ├─ qalam glossary build ► glossary.json   (you fill in the targets)
   ├─ qalam plan ──────────► only the chunks that need work
   ├─ per chunk: translate + qalam gate + qalam record
   ├─ qalam merge ─────────► one document
   └─ qalam preview ───────► readable RTL HTML
```

`run_state.json` records, per chunk, a hash of the source and a signature of every
glossary entry that applied to it. On re-run:

- unchanged chunk → skipped,
- changed source → re-translated,
- edited term or new alias → only the chunks containing it are invalidated.

That is the difference between a tool you run once and a tool you maintain with.

### The gate

Fifteen checks: length ratio, structure, fenced code, inline code, links, link
text, numbers, duplicated paragraphs, brackets, untranslated lines, language mix,
Arabic punctuation, headings, whitespace, terminology.

```text
$ qalam gate --source demo/source.en.md --target demo/bad.ar.md --glossary demo/glossary.json
words 177 → 171 (ratio 0.966)
WARN  arabic_punctuation  ASCII ',' after Arabic letters; use '،'
WARN  link_text           link text left in the source language: [the parser notes](…)
errors=0 warnings=2 infos=0 ok=true
```

Real defects in a real file. The corrected file returns `no findings`.

---

## Arabic support, concretely

- **Direction** — root `dir`, logical CSS properties, `<bdi>` and U+2066/U+2069
  isolates for mixed runs, never hand-inserted marks in the stored text.
- **Punctuation** — `،` `؛` `؟`, attached to the preceding word, mirrored brackets.
- **Numerals** — Western, Arabic-Indic, or preserve, with Western digits kept
  inside code, URLs, and versions.
- **Harakat** — none by default; added only to resolve genuine ambiguity.
- **Plurals** — all six CLDR categories in localisation files, not two.
- **Matching** — alef/hamza folding, alef maqsura, tatweel and diacritics handled
  for lookup while display keeps the original forms.
- **Gender** — a first-class field in the glossary, because Arabic agreement
  depends on it.

---

## Engineering notes

- No third-party dependencies, no network calls, no install step beyond Python.
- 212 tests. Most of them guard defects that actually occurred during development:
  words dropped when rewrapping subtitles, isolate characters leaking into HTML
  tags, inline code vanishing from the preview, code fences reported as
  "untranslated", punctuation polluting translation-memory keys.
- Contract tests over the shipped skills: trigger words in descriptions, every
  referenced file exists, every CLI subcommand exists, every skill has failure
  guidance and stays under a length budget.
- `python3 demo/run_demo.py` runs the whole pipeline and writes real artefacts.

## Known limits

- Qalam does not translate. Your model does; the pack organises and verifies it.
- Image-only PDFs need OCR first (`extract-docs` covers it).
- The gate is mechanical: it cannot judge whether a sentence means the same thing.
  Human review stays necessary, and the skills say so instead of pretending.
- Preview output is HTML, not PDF; print to PDF from a browser.

## License

MIT.
