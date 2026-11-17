# Review checklist

Ordered by how often the item is actually broken, not by category.

## Meaning

- [ ] Negations present and in the right clause
- [ ] Modality preserved: must / should / may / can / might are distinct
- [ ] Quantifiers preserved: all / most / many / some / few
- [ ] Conditionals preserved: if / unless / only if / provided that
- [ ] Causation not upgraded to correlation, or the reverse
- [ ] Comparisons complete: "X is larger than Y" did not lose Y
- [ ] Numbers, units, and ranges identical in value
- [ ] Dates keep calendar and precision ("early 2024" is not "2024")
- [ ] Lists and examples complete, including the last item

## Omissions and additions

- [ ] Parentheticals kept
- [ ] Qualifiers kept ("in most cases", "except when")
- [ ] Footnotes and cross-references kept and pointing correctly
- [ ] No explanatory sentences added by the translator
- [ ] No section summarised into one line

## Code and markup

- [ ] Fenced blocks byte-identical
- [ ] Inline code spans identical in content and count
- [ ] CLI flags, env vars, paths untouched
- [ ] Link targets identical; link text translated
- [ ] Image paths identical; alt text translated
- [ ] HTML tags and attributes untouched
- [ ] Table rows and columns match; headers translated

## Terminology

- [ ] Every glossary term uses its target
- [ ] No source form survives in prose
- [ ] Proper nouns follow the glossary consistently
- [ ] Acronyms expanded on first use as in the source
- [ ] No term has two renderings in the same document

## Arabic language

- [ ] Register holds throughout, including in examples
- [ ] Arabic punctuation: ، ؛ ؟ and no space before them
- [ ] Digit script follows the project decision, code excepted
- [ ] Verb–subject agreement, including dual
- [ ] No MT tells: من المهم أن نلاحظ، لا شك أن، في عالم اليوم، يُعتبر من، تم + مصدر
- [ ] No calqued idioms
- [ ] Sentence length varied; no 60-word chains
- [ ] Paragraph openings not all identical
- [ ] No tashkeel except for disambiguation
- [ ] No tatweel used for justification

## Structure

- [ ] Heading count and levels match
- [ ] Heading text reads naturally in the target language
- [ ] Chapters begin and end at the same places
- [ ] Chunk boundaries: no sentence dropped or duplicated
- [ ] TOC (if present) matches the headings

## Delivery

- [ ] Output file opens and renders RTL correctly
- [ ] Preview generated and spot-checked
- [ ] Report states what was not verified
- [ ] Counts in the report match the gate output
