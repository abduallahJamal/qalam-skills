# Translation rules

The gate enforces the mechanical part of this file. The rest is the difference
between a translation a reader finishes and one they abandon on page three.

## 1. Fidelity

**Complete.** Every sentence has a counterpart. Nothing is summarised, expanded,
or "clarified" unless the user asked for a localised adaptation rather than a
translation.

**Nothing invented.** If a sentence is ambiguous, the translation carries the
same ambiguity. If a term cannot be translated without a guess, keep the source
form and note it in the report.

**No editorialising.** Do not add transitions the author did not write
("كما سنرى لاحقًا"), do not add section summaries, and do not soften claims.

**Numbers, units, dates, and names are content, not style.** `3.5 s` stays
three and a half seconds. `1997` stays 1997. A person's name follows the
glossary, not personal preference.

## 2. Structure

A translation preserves the shape of the source:

| Element | Rule |
| --- | --- |
| Headings | Same count, same levels, same order |
| Lists | Same item count; nesting preserved |
| Tables | Same rows and columns; cells translated, headers translated |
| Links | Same `href` targets; link text translated |
| Images | Same paths; alt text translated |
| Code | Byte-identical, including whitespace and comments |
| Footnotes | Same markers; note text translated in place |
| Emphasis | Carried over, but not exaggerated |

If the source has a heading with no body text, keep it that way.

## 3. Register and voice

Match the source's register, not the model's default.

- **Academic / technical manual** → formal, precise, few metaphors, consistent
  pronouns. Arabic: فصحى معاصرة, third person, no direct address unless the
  source addresses the reader.
- **Tutorial** → direct address, imperative for steps ("افتح الملف").
- **Essay / literary** → keep rhythm and imagery; sentence length may vary from
  the source, but paragraph shape should not.
- **Marketing** → adapt idioms; keep claims identical.

Do not upgrade a casual source to formal prose, and do not relax a formal source
into chatty language.

## 4. Terminology

- A term with a glossary target is mandatory.
- A term without one: pick a translation, then **add it to the glossary** before
  translating another chunk, so the decision propagates.
- Proper nouns: transliterate names that have no established Arabic form
  (فاراداي، تورينج), keep brand names in Latin script when the brand does
  (`GitHub`, `PostgreSQL`), and follow the glossary if it says otherwise.
- Acronyms: expand on first use if the source expands them; keep the Latin
  acronym in parentheses so a reader can search for it.

## 5. Things translators quietly break

- **Negation** — a dropped `لا` inverts a requirement. Re-read every negative
  sentence against the source.
- **Modality** — `must` / `should` / `may` are three different obligations.
  Colours: يجب / ينبغي / يجوز. Keep them distinct.
- **Quantifiers** — `most`, `many`, `some`, `all` must not collapse into "كثير".
- **Conditionals** — `if` vs `unless` vs `only if` change the meaning of a whole
  section.
- **Cross-references** — "see chapter 4" must point at chapter 4 in the
  translation, which has the same numbering.
- **Lists of three** — the third item is the one that disappears.
- **Parentheticals** — easy to drop, and often carry the real qualifier.

## 6. Language-specific notes

### Into Arabic

- Sentence order may change; paragraph boundaries should not.
- Prefer verbal sentences for procedure, nominal for definition.
- Avoid stacked إضافات ("تطبيق إدارة مشاريع الفريق") when a phrase reads better.
- Use `و` sparingly between clauses; Arabic tolerates more full stops than English.
- Definite article: keep it where the source is definite, drop it where the
  target idiom requires (generic plurals).
- No tashkeel by default; add it only for disambiguation.

### Into English

- Do not keep Arabic word order; rewrite clauses into English order.
- Transliterate names with a consistent system, and give the Arabic in
  parentheses at first mention when the reader may need to search for it.
- Arabic sources often lack paragraph breaks; add them at topic shifts, never
  mid-thought.

### Code-switching in the source

When the source mixes languages (very common in Arabic technical writing):

- Translate the prose into the target language.
- Keep quoted foreign terms as the author wrote them, and add a translation in
  parentheses only if the author did not.
- Do not "clean up" the author's mixing — it is often deliberate.

## 7. Quality bar before you report

Run `python -m qalam gate` and then read:

1. The first and last paragraph of every chunk boundary.
2. Every heading.
3. Every negative and every modal sentence.
4. Every list with three or more items.
5. Every number that carries a unit.

If you cannot read the source language well enough to be sure, say so in the
report. A labelled partial translation is useful; a confident wrong one is not.
