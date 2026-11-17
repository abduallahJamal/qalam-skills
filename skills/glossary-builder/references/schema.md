# Glossary schema and matching

## File

```json
{
  "version": 1,
  "terms": [ /* Term objects */ ]
}
```

`version` is 1. Future versions must keep old files loadable; a reader that does
not understand a version should refuse rather than guess.

## Term

| Field | Type | Required | Meaning |
| --- | --- | --- | --- |
| `source` | string | yes | The source-language form. Unique after normalisation. |
| `target` | string | no | The approved rendering. Empty means "not decided yet". |
| `category` | enum | no | `person`, `place`, `org`, `product`, `technical`, `title`, `other`. Default `other`. |
| `aliases` | string[] | no | Other surface forms that resolve to this term. |
| `gender` | enum | no | `masculine`, `feminine`, `plural`, `unknown`. Default `unknown`. |
| `confidence` | enum | no | `high`, `medium`, `low`. Default `medium`. |
| `frequency` | integer | no | Occurrences in the source. Filled by `count_frequencies`. |
| `keep_as_is` | boolean | no | Copy the source verbatim; never translate. |
| `notes` | string | no | A human note; may be shown to the translator. |

## Normalisation used for matching

Matching is deliberately forgiving, because Arabic surface forms vary:

1. Unicode NFKC (folds presentation forms).
2. Tatweel (U+0640) removed.
3. Diacritics removed for matching (kept for display).
4. Alef forms fold to bare alef: أ إ آ ٱ → ا.
5. Alef maqsura ى folds to yeh ي.
6. Teh marbuta ة folds to heh ه **only in the non-display normalisation**.
7. Arabic-Indic and Persian digits fold to ASCII.
8. Whitespace collapsed, trimmed, case-folded.

Consequence: `المستودع`, `المستَودَع`, and `المستودعـ` all match. `مكتبة` and
`مكتبه` match. This is intentional for matching and wrong for display — never
write normalised text back to a document.

## Matching rules

- A term matches a chunk if its `source` **or any alias** occurs as a
  whole-token match.
- Longer forms win: "طلب دمج" beats "طلب".
- Minimum length 2 characters for term injection (shorter forms produce noise).
- A high-frequency tail is injected book-wide: the top N terms by `frequency`,
  default 20, so a translator sees the project's core vocabulary even in a chunk
  that does not mention it.

## Change semantics

| Edit | Effect on a run |
| --- | --- |
| Add a term | No chunk re-translates; new chunks see it |
| Change a `target` | Chunks containing that term re-translate |
| Add an `alias` | Chunks containing the alias re-translate |
| Change `category` or `gender` | Chunks containing the term re-translate |
| Toggle `keep_as_is` | Chunks containing the term re-translate |
| Change `notes` | No re-translation (notes are advisory) |
| Change `confidence` | No re-translation |

This is enforced by hashing a signature over `source`, `target`, `category`,
`gender`, `keep_as_is`, and the sorted alias set — not over `notes`,
`confidence`, or `frequency`.

## Authoring rules

- One meaning per entry. Two senses → two entries, with cross-referenced notes.
- `keep_as_is` and a different `target` is a contradiction; the audit rejects it.
- An alias must not equal another entry's source.
- Empty `target` with `keep_as_is: false` means "undecided"; the audit reports it.
