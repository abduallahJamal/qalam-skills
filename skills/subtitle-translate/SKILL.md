---
name: subtitle-translate
description: Translate and time SRT and WebVTT subtitles into Arabic or any language — reading-speed limits, two-line wrapping, cue splitting, timing preservation, RTL display rules, and quality checks. Use when asked to subtitle a video, translate a .srt/.vtt, or fix cues that are too long, too fast, or unreadable in Arabic.
license: MIT
compatibility: Python 3.9+ for `qalam` checks; ffmpeg optional for burning in or extracting.
metadata:
  qalam.version: "1.0"
  qalam.kind: procedure
  qalam.category: subtitles
---

# Subtitle translation

Subtitles are read in glances. A translation that is correct but too long to read
in the time available is a bad subtitle, no matter how good the Arabic is.

**Governing rule:** every cue must be readable at its display time. When meaning
and readability conflict, shorten the meaning — never let a cue overflow.

## When to use this

- Translate `.srt`, `.vtt`, or `.ass` subtitles.
- Fix existing subtitles whose Arabic cues are cut off, too fast, or mis-timed.
- The user asks to "subtitle this video" and has a transcript or existing
  subtitles.

Not for: transcribing audio (that is a different task; ask for a transcript
first), or dubbing scripts (no time constraints, use `arabic-style`).

## Inputs

| Input | Default | Notes |
| --- | --- | --- |
| `file` | — | `.srt`, `.vtt`, or `.ass`. Required. |
| `target_language` | `ar` | |
| `register` | neutral | `formal` for documentary, `neutral` for tutorial, `colloquial` only if asked |
| `source_language` | auto | Detect from the file, confirm if unsure |
| `chars_per_line` | 42 | 45–50 for Latin, 38–42 for Arabic is safer |
| `max_lines` | 2 | Never 3 |
| `reading_speed` | 17 cps | 15 for children's content, 20 for dense technical |
| `min_duration` | 1.0 s | Shorter cues flash |
| `max_duration` | 7.0 s | Longer needs a split |

Confirm only the register and target language if unclear; use the defaults above
without asking.

## Procedure

### 1. Parse and measure before translating

```bash
python "$SKILL_DIR/scripts/subs.py" stats input.srt
```

That reports cue count, duration, cue-length distribution, and every cue that is
already too fast or too long **in the source**. Fixing source-level problems
before translating prevents translating a problem twice.

### 2. Translate cue by cue, with context

Subtitles are fragments of a conversation. Never translate a cue in isolation
when the previous and next cue are available:

- Send cues in blocks of 8–15 with the previous block's last cue as context.
- Keep the speaker's tone consistent across a block.
- Never merge two speakers into one cue; subtitle readers rely on the split.

**Sentence spans:** a sentence may run over three cues. Translate the *sentence*,
then distribute it back across the cues at natural boundaries — never word by
word per cue, which produces dangling connectors ("…ولكن" alone in a cue).

### 3. Fit the cue

For each cue, apply in order:

1. **Reading speed** — characters ÷ duration ≤ 17 cps (Arabic). If it fails,
   shorten. This is the first tool, not the last.
2. **Line length** — max 42 characters per line, max 2 lines.
3. **Line balance** — two lines of similar length read better than 40 + 8.
4. **Break at syntax** — never split between a noun and its adjective, a verb and
   its object, or a preposition and its noun.
5. **Keep numbers and names intact** — never break "1,250" or "GitHub" across
   lines.

If a cue still does not fit:

- Shorten by removing redundancy ("كما تعلمون" → gone).
- Move a trailing clause into the next cue if the next cue has room.
- Split the cue in two and shorten the display gap, never below 1.0 s.
- Last resort: raise reading speed to 20 cps and flag it in the report.

### 4. Handle Arabic display rules

- **Line order**: line 1 is the top line, read first. Do not put the continuation
  on top because it feels RTL.
- **Punctuation**: Arabic comma and question mark; no terminal period on a cue
  that continues into the next one.
- **No bidi control characters** in the file. The player handles direction.
- **Latin within Arabic** — isolate short Latin runs; a player that mis-renders
  them is a player bug, not a reason to mangle the text.
- **Numbers**: Western digits are the norm in subtitles for technical content;
  Arabic-Indic for literary/historical. Pick one per file.
- **Honorifics and titles** — keep the register's natural forms, not transliterated
  English titles.
- **No tashkeel**, same as prose.
- **Dialogue dashes**: a cue with two speakers uses an en dash at the start of
  each line: `— النص`.

### 5. Verify timing integrity

The translation must not change the timing grid. Check:

```bash
python "$SKILL_DIR/scripts/subs.py" check input.srt output.ar.srt
```

The check verifies: identical cue count and order, identical start/end times,
no overlap, no negative durations, no empty cues, reading speed, and line count.

If you split a cue, cue counts differ on purpose — the check reports the split
mapping, and you confirm it in the report.

### 6. Deliver

- The translated `.srt`/`.vtt` in UTF-8 with the same line endings as the source.
- A report: cues, split cues, cues above the reading-speed limit, cues where you
  shortened and what you dropped, and anything you could not fit.
- Never claim it is "perfectly timed" — say it was checked mechanically.

## Format rules

**SRT**

```text
1
00:00:12,480 --> 00:00:15,120
الإصدار الجديد متاح الآن،
ويمكنك تحديثه من الإعدادات.
```

- Blank line between cues, no trailing spaces.
- Comma for the millisecond separator, not a period.
- Sequential numbering, starting at 1.

**WebVTT**

```text
WEBVTT

00:00:12.480 --> 00:00:15.120
الإصدار الجديد متاح الآن،
ويمكنك تحديثه من الإعدادات.
```

- `WEBVTT` header on line 1.
- Period for milliseconds.
- Preserve cue identifiers if present; never translate them.
- Preserve `NOTE` and `STYLE` blocks untouched.

## Quality bar for Arabic subtitles

| Check | Standard |
| --- | --- |
| Reading speed | ≤ 17 cps, never above 20 |
| Line length | ≤ 42 chars |
| Lines per cue | ≤ 2 |
| Minimum duration | ≥ 1.0 s |
| Gap between cues | ≥ 0.08 s |
| Synchrony | Sentence boundaries respected across cues |
| Register | Consistent within a scene |
| Terminology | Matches the glossary, if one exists |

## Failure modes

| Symptom | Cause | Fix |
| --- | --- | --- |
| Cue flashes before it can be read | Duration below 1.0 s | Extend into the gap, or merge with a neighbour |
| Viewer complains about overlapping cues | Split cue kept the original end time | Re-cut both halves against the gap |
| Arabic cue wraps into three lines | Line width too generous | Lower `chars_per_line` to 38–42 and re-break |
| Translation reads fast even at 17 cps | Source was already over-speed | Shorten the translation; never shift the timing |
| Numbers appear reversed in the player | Bidi handling in the player, not the file | Test in the delivery player; isolate the run, do not reorder the text |
| Words disappear after rewrapping | A rewrite that truncates instead of rewrapping | Run the checker: word sequences must be identical |
| Sentence begins mid-clause | Cue boundary cut through a clause | Move the boundary to a clause edge and retime both cues |
| Latin names look wrong at the line edge | Break inside a Latin term | Never break inside a name, number, or code span |

## References

- `references/timing-rules.md` — CSPL, reading speed maths, split strategies.
- `references/arabic-subtitles.md` — RTL display, punctuation, and common errors.
- `scripts/subs.py` — parse, stats, check, and re-time helpers.
