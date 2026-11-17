# Timing and reading rules

## Reading speed

Characters per second (CPS) is the standard readability measure.

| Audience | CPS |
| --- | --- |
| Children | 13–15 |
| General audience | 15–17 |
| Adult documentary | 16–18 |
| Dense technical | 18–20 |
| Above 20 | Only for on-screen text the viewer can pause |

Arabic has a higher information density per character than English, so the same
CPS number carries more meaning — but Arabic glyphs are also wider and the script
is cursive, so a 42-character Arabic line occupies more width than 42 Latin
characters. Use 38–42 characters per line for Arabic.

Formula:

```text
CPS = characters_including_spaces / display_seconds
```

Count characters after removing markup (`<i>`, `{\an8}`) and dialogue dashes, but
keep the numbers and punctuation the viewer actually reads.

## Durations

| Rule | Value | Why |
| --- | --- | --- |
| Minimum duration | 1.0 s | Shorter reads as a flash |
| Comfortable duration | 1.5–5.0 s | Reading rhythm |
| Maximum duration | 7.0 s | Beyond this the viewer re-reads |
| Minimum gap between cues | 0.08 s (2 frames at 25 fps) | Prevents merging on some players |
| Preferred gap | 0.12–0.25 s | Feels like speech, not slides |

Two-line cue of 84 characters needs about 5 seconds at 17 CPS. If the original
slot is 3 seconds, either shorten the text or split the cue.

## Splitting strategy

Split at the strongest boundary available, in this order:

1. End of a sentence.
2. Before a conjunction that starts a new clause (لكن، ثم، لذلك).
3. At a comma.
4. Between a complete noun phrase and a prepositional phrase.

Never split:

- between a noun and its adjective,
- between a verb and its object,
- between a preposition and its noun,
- inside a number, a name, or a Latin term,
- in the middle of a quoted sentence when the quote continues.

When splitting, keep the timing continuous: the first half keeps the start, the
second half takes the remainder, and neither goes below the minimum duration.

## 25 fps frame rounding

Broadcast subtitles are frame-accurate. At 25 fps, one frame is 40 ms; at 23.976,
41.7 ms. Round cue boundaries to the nearest frame after any shift, or an editor
will drift gradually. `subs.py shift` keeps exact milliseconds — round afterwards
in the editor if the deliverable is broadcast.

## Re-timing a translation

A translation that is shorter than its slot can be:
- left as-is (preferred), or
- extended into the following gap, up to the next cue's start minus the minimum gap.

A translation that is longer must not push the following cues; it must be
shortened. Subtitles are locked to the picture. Moving the picture is a different
job.

## Measuring an existing file

```bash
python subs.py stats file.srt
```

Reports average and maximum CPS, cues over 17 CPS, maximum characters, and
three-line cues. Run it on the source *before* translating: a source with 40%
over-speed cues will produce an over-speed translation no matter how careful you
are.

## Quality targets

| Metric | Target |
| --- | --- |
| Cues over 17 CPS | < 5% |
| Cues over 20 CPS | 0 |
| Cues over 2 lines | 0 |
| Cues under 1.0 s | < 2% |
| Overlapping cues | 0 |
| Cue count change after translation | 0 (unless reported) |
