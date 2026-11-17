# Arabic typography and bidirectional text

Arabic is not "English with a different font". Direction, punctuation, numerals,
letterform shaping, and line height all change what a reader sees. This file is
the checklist for getting those right in anything you produce.

## Direction

- Paragraph direction is right-to-left (`dir="rtl"` in HTML, `FlowDirection="RightToLeft"`
  in WPF, `Directionality(textDirection: TextDirection.rtl)` in Flutter,
  `I18nManager.forceRTL(true)` in React Native).
- Code, URLs, file paths, and terminal output stay left-to-right **inside** the
  RTL flow. In Markdown they are code spans (` ` ` / fences); in HTML wrap them
  with `<bdi>` or `unicode-bidi: isolate`.
- Never mix `dir="rtl"` with `text-align: left` on prose; alignment follows the
  reading direction unless the design deliberately justifies both edges.

## Punctuation

Arabic uses its own marks. Substituting ASCII punctuation is the single most
visible sign of a machine translation.

| Meaning | Arabic | Not |
| --- | --- | --- |
| comma | `،` | `,` |
| semicolon | `؛` | `;` |
| question mark | `؟` | `?` |
| decimal separator | `٫` | `.` (keep `.` in code) |
| thousands separator | `٬` | `,` (keep in code) |

Rules:

- Punctuation attaches to the preceding word with no space: `النص، ثم`.
- Opening marks mirror: `«نص»`, `(نص)`, `[نص]`.
- Quotation: `«…»` is standard for prose; `"…"` appears in technical text and is
  acceptable when the source uses it consistently.
- Ellipsis is `…`, not three dots.
- A parenthetical spanning a sentence keeps its closing mark inside.

## Numerals

Three options; pick one per project and state it.

1. **Western (0–9)** — default for technical, scientific, and web content, and
   what most Arabic software uses.
2. **Arabic-Indic (٠١٢٣٤٥٦٧٨٩)** — common in print, literature, and some
   newspapers.
3. **Preserve** — mirror whatever the source does.

In all three cases:

- Keep Western digits inside code, URLs, versions, IPs, and hex values.
- Do not convert the *value*: `1,250` becomes `١٬٢٥٠` or `1,250`, never `1.250`.
- Dates: `٢٠٢٦` or `2026`, both fine; the month name follows the locale.

The gate checks the chosen script (`--numerals western|arabic-indic|preserve`).

## Harakat (tashkeel)

- Body prose: **no harakat**. Fully vocalised text reads like a children's book.
- Add harakat only to disambiguate a genuine ambiguity (e.g. passive vs active
  voice where the meaning changes).
- Technical terms and loanwords need no harakat.
- Never add harakat to headings.

## Letterforms and layout

- **Fonts**: a Naskh or modern Arabic UI face. Good defaults:
  `Noto Naskh Arabic`, `Amiri`, `Scheherazade New`, `Cairo`, `IBM Plex Sans Arabic`,
  `Dubai`, `Segoe UI`. Avoid a Latin-first font that falls back per-glyph, which
  produces mismatched weights inside one line.
- **Line height**: Arabic ascenders and descenders are taller. Use 1.8–2.0 for
  body text where Latin needs 1.5.
- **Letter spacing**: never add tracking to Arabic — it breaks the cursive joins.
- **Italics**: Arabic has no italic tradition; use a weight change or a coloured
  emphasis instead of a slanted face.
- **Underline**: fine, but increase the offset (Arabic descenders collide with a
  close underline).
- **Kashida/tatweel (ـ)**: do not use it to justify text. Use word spacing.
- **Justification**: acceptable for Arabic prose, but without kashida it needs a
  hyphenation-free, slightly ragged approach; `text-align: justify` with
  `text-justify: inter-word` is the safe default.

## Bidirectional text (bidi)

The Unicode bidi algorithm handles order; your job is to avoid feeding it
ambiguous input.

- **Isolate embedded runs** instead of inserting marks: in HTML use `<bdi>`,
  `<span dir="ltr">`, or `unicode-bidi: isolate`; in plain text use U+2067
  RLI … U+2069 PDI around an RTL run inside an LTR sentence, and U+2066 LRI …
  U+2069 around an LTR run inside RTL.
- Prefer isolates over the older marks LRM/RLM (U+200E/U+200F), which do not
  bound a run.
- A trailing punctuation mark after a Latin word in an Arabic sentence is the
  classic broken case:
  `الإصدار v2.0.` — the dot may jump to the wrong end. Isolating the run fixes it.
- Never "fix" bidi by reordering characters in the string. The stored text stays
  in logical order; only the renderer decides visual order.

## Tables and mixed content

- Reverse column order for RTL tables (first column on the right), or set the
  table's `direction: rtl` and let the renderer mirror it.
- Numbers in cells stay LTR and right-aligned to the column, not to the page.
- Code cells are LTR with `dir="ltr"` on the cell.

## What "correct RTL" means in review

1. Reading starts on the right; the first heading is at the top right.
2. No line begins with a closing bracket or `،` `؟`.
3. Numbers and Latin names keep their internal order and sit on the correct side.
4. Code blocks are left-aligned with monospace alignment intact.
5. Line height gives room for Arabic descenders; nothing clips.
6. Lists: bullets on the right, indentation from the right.
7. Icons that imply direction (arrows, chevrons) are mirrored; media controls and
   logos are not.

For framework-specific implementation, load `rtl-layout`.
