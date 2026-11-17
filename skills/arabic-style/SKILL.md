---
name: arabic-style
description: Edit and improve Arabic prose — فصحى register, sentence rhythm, removing machine-translation artifacts, punctuation, and terminology consistency — without changing meaning. Use when the user asks to review, refine, or "make natural" Arabic writing, or before delivering any Arabic text.
license: MIT
compatibility: Optional Python 3.9+ for the bundled checks; the editorial rules need no runtime.
metadata:
  qalam.version: "1.0"
  qalam.kind: procedure
  qalam.category: writing
---

# Arabic style

You are an Arabic editor, not a rewriter. The author's claims, structure, and
voice survive your edit. What changes is the language: register, rhythm,
punctuation, and the traces of translation that make a text feel machine-made.

**Governing rule:** every change must be defensible as an improvement in
clarity, correctness, or consistency. "I would have phrased it differently" is
not a reason to touch a sentence.

## When to use this

The user asks to: review Arabic writing, "حسّن الصياغة", "خلّيها عربية طبيعية",
proofread, tighten, or check a translated text before publishing. Also load this
*before delivering* any Arabic output that a human will read as prose.

Not for: translating (use `translate-docs`), UI strings (use `localize-app`),
or RTL layout bugs (use `rtl-layout`).

## Procedure

### 1. Establish the brief

Three facts decide everything else. Infer them from the text if you can; ask
only when the answer changes the edit:

- **Register**: فصحى معاصرة (books, docs, journalism) · فصحى تراثية (religious,
  classical) · عامية (dialogue, social) · تقنية (mixed Arabic/English for
  developers).
- **Audience**: general reader, specialist, or developer.
- **Purpose**: inform, instruct, persuade, or document.

Then say in one line what you are editing toward, e.g. "فصحى معاصرة، قارئ عام،
نص توثيقي — سأحافظ على المصطلحات التقنية كما هي."

### 2. Read once without editing

Read the whole piece before touching a sentence. Editing paragraph by paragraph
produces locally clean text with a broken spine: repeated openings, drifting
terminology, and a conclusion that contradicts the introduction.

While reading, mark (mentally or in a scratch file):

- the author's recurring terms, and every variant spelling of them,
- sentences you had to read twice,
- paragraphs whose first sentence does not match what follows,
- anything that sounds translated.

### 3. Diagnose, then fix

Work through `references/arabic-editing.md`. The high-yield checks, in order:

1. **Machine-translation tells** — "من المهم أن نلاحظ", "لا شك أن", "في عالم
   اليوم", "تجدر الإشارة إلى أن", "بشكل كبير". Cut or rewrite.
2. **Structural calques** — "يُعتبر X من Y" (is considered), passive chains,
   `تم + مصدر` where a verb is cleaner ("تم إنجاز" → "أُنجز").
3. **Sentence length** — Arabic tolerates long sentences, but a 60-word sentence
   with five و's is a translation artifact. Split it.
4. **Punctuation** — Arabic comma `،`, `؛`, `؟`; no space before punctuation; no
   English commas inside Arabic prose.
5. **Terminology drift** — one concept, one term.
6. **Pronoun ambiguity** — Arabic allows dropping the subject; make sure the
   reader still knows who acts.
7. **Repetition** — the same sentence opening three paragraphs in a row.

### 4. Preserve what is good

Some "problems" are style. Do not flatten:

- A short sentence after a long one is rhythm, not an error.
- Deliberate repetition in persuasive text is rhetoric.
- Regional or classical vocabulary that fits the register is not a mistake.
- Quoted speech keeps the speaker's voice, including its irregularities.

### 5. Verify

```bash
python -m qalam gate --source <original.md> --target <edited.md> \
  --source-language ar --target-language ar
```

A same-language run is valid: it checks structure, punctuation, duplication, and
untouched numbers. Then read the diff yourself, out loud if possible.

### 6. Deliver

Give the edited text, then a short change log:

| # | Before | After | Reason |
| --- | --- | --- | --- |
| 1 | تم إنجاز المهمة بواسطة الفريق | أنجز الفريق المهمة | بناء مبني للمجهول وترجمة حرفية |
| 2 | لا شك أن الأداة مفيدة | الأداة مفيدة | حشو |

If a change is a judgement call rather than a correction, say so and keep the
author's version available. Never present a rewrite as a "fix" when it is a
preference.

## Arabic prose rules

### Sentence and paragraph

- Start paragraphs with the subject or a short adverbial, not with "وهذا" or
  "مما يعني".
- Vary sentence openings; Arabic writing that starts every paragraph with
  "يُعدّ" or "تُعدّ" reads as generated.
- One idea per paragraph. Arabic tolerates long paragraphs, but not paragraphs
  that change subject mid-way.
- Prefer the verbal sentence (فعل + فاعل) for procedure and narrative; the
  nominal sentence (مبتدأ + خبر) for definition and description.

### Verb forms

- Active over passive unless the actor is unknown or irrelevant.
- `تم + مصدر` is bureaucratic: "تم تحديث الملف" → "حُدِّث الملف" or "حدّثنا الملف".
- Continuous action: use المضارع, not "يقوم بـ + مصدر" ("يقوم بتحليل" → "يحلّل").
- Future: `سـ` for near, `سوف` for emphasis; do not mix both in one text.

### Connectors

- `و` is the default coordinator; do not replace every `and` with `كما أن`.
- Use `لكن` / `غير أن` / `بيد أن` deliberately, not interchangeably.
- `أما … فـ` for contrast, sparingly.
- Avoid `علاوة على ذلك`, `بالإضافة إلى ذلك` in every other paragraph.

### Idiom and metaphor

Translate the image, not the words. "The elephant in the room" is not
"الفيل في الغرفة". Either find an Arabic image that does the same work or state
the meaning plainly.

## What you must not do

- Do not add sentences that were not in the original, even helpful ones.
- Do not "simplify" technical precision into vagueness.
- Do not convert فصحى to عامية or the reverse unless asked.
- Do not tashkeel the whole text.
- Do not correct quoted material.
- Do not change the meaning of a claim, a number, or a qualification.

## Reporting

Say what you changed and why, in Arabic if the user writes in Arabic. If the
document is long, group changes by category and give counts, then list only the
ten most instructive examples.

Be explicit about what you did **not** verify: facts, figures, quotations,
sources, and anything requiring domain expertise. Style editing does not make a
text true, and you should not imply that it does.

## Failure modes

| Symptom | Cause | Fix |
| --- | --- | --- |
| The edit reads like a different author | Rewriting instead of editing | Revert sentences where only the phrasing changed |
| Register drifts mid-document | Editing paragraphs in isolation | Read the whole piece first; fix openings and closings last |
| Every sentence became short and choppy | Splitting as a reflex | Split only sentences with two or more independent ideas |
| Terminology improved but inconsistent | Synonyms chosen for variety | Pick one rendering, add it to the glossary, apply everywhere |
| Arabic looks translated but "correct" | Calques preserved | Work through the structural-calque table in the reference |
| The user's voice disappeared | House style overwrote it | Keep sentence openings and imagery the author chose |
| Quotes were corrected | Editing quoted material | Quotes keep their own wording, including errors |

## References

- `references/arabic-editing.md` — the full checklist with before/after pairs.
- `references/register-guide.md` — choosing and holding a register.
