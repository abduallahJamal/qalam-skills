# Arabic subtitles

## Display

- Players render bidi themselves. Write logical-order text and let them handle
  direction; never insert LRM/RLM marks into the cue text.
- Line 1 is read first, regardless of direction. In a two-line Arabic cue, line 1
  is the top line, and it is the first part of the sentence.
- Punctuation marks sit at the visual end of the line, which for Arabic is the
  left edge. Keep the mark attached to the last Arabic word in logical order and
  the player will place it correctly.
- Do not right-align manually. Alignment is a player setting.

## Punctuation and style

| Situation | Use |
| --- | --- |
| Comma | `،` |
| Question | `؟` |
| Exclamation | `!` (same glyph works) |
| Quotation | `«»` |
| Two speakers | `— النص` on each line |
| Continuation | No terminal mark on the first cue |
| Emphasis | Avoid italics; Arabic has no italic tradition. If the source uses `<i>`, keep the tag — the player may underline or recolour |

No terminal period on short cues: subtitles read faster without them, and Arabic
already uses the comma as the main breath mark.

## Register

- **Documentaries, news, tutorials**: فصحى معاصرة مبسطة. Clear, direct,
  no dialect.
- **Drama and comedy**: dialect matching the source's register — only if the user
  asked for it. Mixing dialects inside one film is worse than using فصحى.
- **Children's content**: simpler vocabulary, shorter cues (13–15 CPS).
- **Technical**: keep identifiers and Latin terms in code-like isolation.

## Common errors

| Error | Example | Fix |
| --- | --- | --- |
| Calque | "ما هي هذه الفكرة التي تعتقد أنها…" | "برأيك، ما هذه الفكرة…" |
| Over-literal connectors | "و لكن" at the start of a cue | "لكن" |
| Pronoun ambiguity | cue 12 says "قال إنه..." with three men in the scene | name the speaker |
| Sentence split mid-clause | cue ends with "من أجل" | re-cut the boundary |
| Excessive formality | "يتعين عليكم الانتقال إلى الصفحة" | "انتقل إلى الصفحة" |
| Romanised names | "this is called React" → "رياكت" | keep "React" |
| Numerals mixed | ٣ in one cue, 3 in the next | pick one per file |
| Full tashkeel | "مَرْحَبًا بِكَ" | "مرحبا بك" |

## Numbers and names

- Western digits by default in technical content; Arabic-Indic in literary or
  historical material — one choice per file.
- Names of products and brands stay in Latin script when the source renders them
  so (`GitHub`, `Photoshop`), and get a transliteration in parentheses only if
  the content is spoken-heavy.
- Person names: transliterate consistently (فاراداي، تورينج) and never in two
  ways in one film.
- Dates and times: follow the target locale's format, but keep the on-screen
  clock or caption consistent with any graphic showing the same value.

## Line breaking Arabic

Break at a clause boundary and prefer lines of similar length. A single word on
line 2 ("…وهذا ما سنراه\nلاحقًا") is bad. If a break produces a line shorter than
about a third of the other, re-break.

Never break:

- between a noun and its idafa complement ("صفحة\nالنتائج"),
- between a preposition and its noun ("في\nالمجلد"),
- between a verb and its subject when the subject is short.

## Verification

1. Watch the first minute with sound off — the cues must still make sense.
2. Read a scene at 2× speed: if it becomes impossible, reduce CPS.
3. Check the cues that contain numbers, Latin words, or dialogue between two
   speakers.
4. Open the file in the target player (VLC, mpv, browser) — not only in the
   editor. Player bidi support varies.
