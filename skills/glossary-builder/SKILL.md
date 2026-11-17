---
name: glossary-builder
description: Build, audit, and maintain a bilingual term base from documents, a codebase, or an existing translation — with Arabic-aware matching (alef/hamza folding, diacritics, aliases), gender agreement, and per-chunk term injection. Use when terminology must stay consistent across a long translation, a docs site, or an app.
license: MIT
compatibility: Python 3.9+ for the bundled `qalam` CLI; the schema and rules are tool-independent.
metadata:
  qalam.version: "1.0"
  qalam.kind: procedure
  qalam.category: terminology
---

# Glossary builder

A glossary is the cheapest quality lever in any translation project. Without one,
the same English word becomes four Arabic words across four chapters, and no
amount of per-chunk quality fixes that.

**Governing rule:** a glossary entry is a decision, not a suggestion. If a term is
in the glossary with a target, every chunk follows it, even where a synonym would
read more elegantly.

## When to use this

- Before translating anything longer than a few pages (usually called from
  `translate-docs`, step 2).
- The user has an existing translation and wants new text to match it.
- A docs site has drifted: the same concept is named three ways.
- A codebase needs its identifiers pinned so prose never translates them.

Not for: a one-paragraph translation (build it in your head), or a UI string
table (use `localize-app`, which seeds terms from the strings themselves).

## Procedure

### 1. Decide the scope

| Scope | Input | Typical size |
| --- | --- | --- |
| Single document | the source Markdown | 15–40 terms |
| Book series | all volumes' source | 80–250 terms |
| Docs site | the `docs/` tree | 50–150 terms |
| App + docs | strings + docs + code identifiers | 100–400 terms |

Bigger is not better. A 600-term glossary nobody maintains is worse than 60 terms
that are actually enforced. Start with the terms that repeat.

### 2. Extract candidates

```bash
python -m qalam glossary build <paths...> --out glossary.json --min-frequency 2 --limit 200
```

Useful flags:

- `--code` — also propose identifiers found in the source tree, pre-marked
  `keep_as_is` so prose never translates them.
- `--from-glossary existing.json` — keep every existing decision and add only new
  candidates (this is how you extend a glossary safely).
- `--min-frequency 3` — for a first pass on a very large corpus.

The extractor proposes; it does not decide. Every `target` is empty on purpose.

### 3. Fill in targets — the actual work

Work through the candidates in frequency order and stop when the tail is noise.
For each term decide four things:

1. **Target** — the rendering a professional would use in this domain.
2. **Category** — `person`, `place`, `org`, `product`, `technical`, `title`,
   `other`. Categories drive review priorities.
3. **Gender** — `masculine`, `feminine`, `plural`, `unknown`. This is not
   cosmetic: Arabic verbs and adjectives agree with it.
4. **Aliases** — other surface forms that mean the same thing (abbreviations,
   transliteration variants, the English form if the Arabic keeps it).

And one flag:

5. **`keep_as_is`** — true for identifiers, brand names that stay in Latin script,
   and anything the author quotes verbatim. A `keep_as_is` term may have
   `target == source`.

Quality rules:

- One meaning per entry. If a word has two senses, that is two entries, each with
  the other's surface form as an alias — resolved with the audit step.
- Prefer a rendering that survives inflection ("المستودع" works as subject and
  object; a rendering that only works in one case will fight you).
- Do not invent a novel Arabic coinage when an established term exists. If no
  established term exists, pick the clearest descriptive phrase and note it.
- For people, decide transliteration once (فاراداي not فارادي), and add the Latin
  form as an alias so matching finds both.

### 4. Audit before use

```bash
python -m qalam glossary audit glossary.json
```

The audit fails on:

- the same surface form used by two entries (polysemy),
- an alias that collides with another entry's source,
- entries with no target and no `keep_as_is`,
- `keep_as_is` entries whose target differs from the source.

Fix every finding. A conflicting glossary produces conflicting instructions to the
translating agent, and the agent will pick arbitrarily.

### 5. Inject per chunk

Never paste the whole glossary into a translation prompt. Send only what applies:

```bash
python -m qalam glossary terms glossary.json chunk0007.md
```

It returns the terms that appear in that chunk (by source or alias) plus the
highest-frequency terms book-wide, as a Markdown table. If it prints nothing,
the prompt gets no term section at all — a dangling "terms:" heading with an
empty table is worse than omitting it.

### 6. Keep it alive

- When a translator makes a new decision mid-run, add it immediately. Because the
  run state hashes the terms that applied to each chunk, only chunks containing
  that term are re-translated next run.
- When a decision changes, edit the target, re-run `audit`, then re-plan.
- Commit the glossary next to the translation. It is project state, not scratch
  output.

### 7. Report

Give the user: number of terms, how many have targets, the ten highest-frequency
terms, and any term you left undecided with the reason. Do not claim the glossary
is "complete" — say which sections were covered.

## Schema

```json
{
  "version": 1,
  "terms": [
    {
      "source": "repository",
      "target": "مستودع",
      "category": "technical",
      "aliases": ["repo"],
      "gender": "masculine",
      "confidence": "high",
      "frequency": 42,
      "keep_as_is": false,
      "notes": "ريبو only in developer chat, never in docs"
    }
  ]
}
```

Matching is Arabic-aware: alef/hamza forms fold together, alef maqsura matches
yeh, tatweel is ignored, and diacritics are stripped for matching while preserved
in display.

## Codebase seeding

For a repo that ships Arabic docs or an Arabic UI:

```bash
python -m qalam glossary build README.md docs --code --out glossary.json
```

Identifiers that appear three or more times are proposed with
`keep_as_is: true` and `target == source`, so a translator is told explicitly to
copy them. That single step removes the most common class of code-translation
damage: a function name that got "translated" in a paragraph.

## Failure modes

| Symptom | Cause | Fix |
| --- | --- | --- |
| Same term translated differently per chapter | Glossary not injected per chunk | Use `glossary terms <chunk>` in every worker prompt |
| Audit reports duplicates | Two entries share a surface form | Merge, or split into two entries with the other's form as an alias and disambiguate in `notes` |
| Every chunk re-translates after one edit | You edited a high-frequency term | Expected. Confirm that is what you want before re-running the plan |
| Glossary bloats past 400 terms | Candidates added faster than reviewed | Delete the long tail; keep what repeats |
| Arabic gender disagreements | `gender` left `unknown` | Fill it for every person and every inanimate noun whose agreement is not obvious |

## References

- `references/term-choices.md` — established Arabic renderings for common
  technical and academic terms, with the reasoning.
- `references/schema.md` — the full schema and the matching rules.
