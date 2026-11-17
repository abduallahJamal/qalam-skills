---
name: translation-qa
description: Review a finished translation against its source and report defects in meaning, omissions, code, links, numbers, terminology, and Arabic readability — with a mechanical gate for what can be computed and a structured review pass for what cannot. Use when asked to check, review, or approve a translation before publishing.
license: MIT
compatibility: Python 3.9+ for `qalam gate`. Works on any source/target pair of Markdown files.
metadata:
  qalam.version: "1.0"
  qalam.kind: procedure
  qalam.category: quality
---

# Translation QA

You are reviewing, not rewriting. The deliverable is a defect report a human can
act on, plus a verdict that is honest about what was and was not checked.

**Governing rule:** every finding names a location, quotes both texts, and states
why it is a defect. "This reads awkwardly" without a fix suggestion and a reason
is noise, and a review full of noise gets ignored wholesale — including the real
defects.

## When to use this

- The user asks to review, check, approve, or proofread a translation.
- `translate-docs` reaches its final pass.
- A translator delivered a file and someone needs to sign off.

Not for: translating (that is `translate-docs`), or editing Arabic prose with no
source to compare (`arabic-style`).

## Procedure

### 1. Establish the baseline

Without these three, a "defect" may be a deliberate choice:

1. **Source and target files**, both complete.
2. **Register** the translation was supposed to hold (فصحى معاصرة, technical,
   literary, dialect).
3. **Glossary**, if one exists.

If any is missing, say so in the report header. A review without a glossary cannot
judge terminology, only internal consistency.

### 2. Run the mechanical gate first

```bash
python -m qalam gate --source source.md --target target.md \
  --source-language en --target-language ar \
  --glossary glossary.json --numerals preserve --json > gate.json
```

Read the JSON, not just the human summary. What each finding means:

| Code | Severity | What it proves |
| --- | --- | --- |
| `length_ratio` | error / warn | Content is missing or padded |
| `structure` | error | Headings, fences, links, or images do not match one-for-one |
| `code_blocks`, `code_changed` | error | Code was altered — always a defect |
| `inline_code` | error | A code span was translated or dropped |
| `links`, `images` | error | A target was lost or an image path broke |
| `numbers` | warn | A value differs; verify each one against the source |
| `duplicate_paragraph` | error | The model repeated a block |
| `brackets` | error | Unbalanced or mismatched punctuation |
| `untranslated` | warn | A line is still in the source language |
| `language_mix` | error / warn | Target is not predominantly in the target language |
| `arabic_punctuation`, `arabic_spacing` | warn | Latin punctuation or a space before punctuation |
| `numerals` | warn / info | Digit script does not follow the requested convention |
| `mt_smell` | info | A known machine-translation phrase |
| `terminology` | warn | A glossary source form survived translation |
| `whitespace` | info | Cosmetic; fix in bulk, never per line |

Fix errors before you read for style. A document with broken code and missing
links has bigger problems than its rhythm.

### 3. Read in three passes

Do not read source and target side by side from the first sentence; you will
match words instead of meaning.

**Pass A — target only.** Read the translation as a reader of the target language
would. Note every place you stumble, re-read, or lose track. Do not look at the
source. These notes are where readability defects live.

**Pass B — source and target aligned, paragraph by paragraph.** For each pair
look for the six defects that matter:

1. **Meaning changed** — a claim is stronger, weaker, or different.
2. **Omitted** — a clause, qualifier, negation, or example is missing.
3. **Added** — content, emphasis, or explanation not in the source.
4. **Mistranslated term** — a glossary term rendered differently.
5. **Broken reference** — pronoun, cross-reference, or list item pointing wrong.
6. **Register drift** — a formal source became casual, or the reverse.

**Pass C — structural spot checks.** First and last paragraph of every chunk
boundary, every heading, every table, every list of three or more items, every
negative sentence, and every number with a unit.

### 4. Classify findings

Use four severities, defined by what the reader does next:

| Severity | Definition | Example |
| --- | --- | --- |
| **Blocking** | Wrong meaning, missing content, broken code. Cannot publish. | A requirement lost the word "not". |
| **Major** | Reads as a defect to a native reader, meaning survives. | "يُعتبر من" calque; inconsistent term. |
| **Minor** | Style, rhythm, punctuation. | ASCII comma after an Arabic clause. |
| **Note** | Preference, or a decision only the author can make. | Persona of a quoted character. |

### 5. Write the report

Use this shape. It is short on purpose: a reviewer reads the top and skims the
rest.

```markdown
# Review: <document>, <src> → <tgt>

## Verdict
<Blocking: 0 | Major: 4 | Minor: 11 | Notes: 2>
<One sentence: publishable / publishable after fixes / needs re-translation of N sections>

## What was checked
- Mechanical gate: all checks, glossary enforced, numerals preserve
- Full read of target, aligned read of all N paragraphs, structure spot checks
- NOT checked: figures, footnotes rendering, print layout

## Blocking
1. **§3.2, para 2 — meaning inverted**
   Source: "The parser must not discard trailing whitespace."
   Target: "يجب أن يتجاهل المحلل المسافات البيضاء الزائدة."
   Problem: تجاهل = discard; the negation is missing.
   Suggested: "يجب ألا يتجاهل المحلل المسافات البيضاء الزائدة."

## Major
…

## Minor
| # | Location | Issue | Suggested |
| --- | --- | --- | --- |

## Notes
…
```

Rules for the report:

- Quote the source and the target. A finding without a quote cannot be verified.
- Give the suggested fix inline. The reviewer should not have to solve it.
- Group minor findings into a table; do not give each one a section.
- If a category has no defects, write "none". Do not pad.

### 6. Verify your own findings

Before delivering, re-check each Blocking and Major item against the source. False
positives destroy trust faster than missed minor issues. Delete anything you
cannot reproduce.

Then confirm the counts: `errors` from the gate must all appear in the report or
be explicitly explained.

## What the gate cannot catch

Say this in the report, every time. The gate does not know:

- whether the translation *means* what the source means,
- whether an idiom landed,
- whether the register holds,
- whether a term choice was wise (only that it was consistent),
- whether a name is transliterated the way the reader expects,
- whether a footnote, figure caption, or table header renders correctly.

Do not present a clean gate as an approval.

## Arabic review specifics

- **Negation and modality** are where meaning breaks. Read every `لا`, `لم`, `لن`,
  `يجب`, `ينبغي`, `يجوز` against the source.
- **Agreement** — verb and adjective must agree with the noun's gender and number.
  Dual (المثنى) is the form translators forget.
- **Idafa chains** longer than three nouns: unreadable, rewrite.
- **Punctuation** — Arabic comma, and no space before it.
- **MT tells** — the gate lists known phrases; the review should catch the
  structural ones the list cannot (`تم + مصدر`, `يُعتبر من`, passive chains).

## Failure modes in a review

| Failure | Why it happens | Fix |
| --- | --- | --- |
| Report lists 100 minor issues and misses the inverted negation | Reading for style before meaning | Run the six defect classes first, style last |
| Reviewer rewrites instead of reporting | Producing is easier than judging | Quote, diagnose, suggest — never paste a full rewrite |
| Findings cannot be verified | No source quote | Every finding carries source and target text |
| Verdict says "looks good" after a clean gate | Treating the gate as approval | State explicitly what the gate cannot check |
| False positives on deliberate choices | No register or glossary baseline | Ask for the baseline; mark disagreements as Notes |
| Duplicated findings | Same defect counted per line | Group systemic findings with a count |
| Severity inflation | Everything feels urgent | Apply the reader-action test in the severity guide |
| The gate's own warnings are ignored | Reading only the summary | Parse the JSON and account for every error |

## References

- `references/review-checklist.md` — the pass-by-pass checklist.
- `references/severity-guide.md` — how to classify borderline findings.
