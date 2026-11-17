# Register guide

Arabic has a wide gap between written and spoken registers, and mixing them by
accident is the most common stylistic failure. Decide the register at the start
and hold it.

## The registers

### فصحى معاصرة — contemporary standard

The default for books, documentation, journalism, reports, and subtitles for
broadcast media.

- Pronouns: نحن، أنت، هو — full forms, not enclitics in formal prose.
- Verbs: full inflection, المضارع المنصوب والمجزوم used correctly.
- Vocabulary: modern coinages accepted (حاسوب، شبكة، برنامج).
- No dialect words, ever.

```text
تقرأ الأداة الملف وتستخرج المصطلحات المتكررة، ثم تحفظها في ملف يراجعه المحرر.
```

### فصحى معاصرة مبسطة — simplified standard

Same grammar, shorter sentences, more direct address. For tutorials, onboarding
copy, and developer documentation.

```text
افتح الملف، ثم شغّل الأمر التالي. ستحصل على قائمة المصطلحات في مجلد العمل.
```

### فصحى تقنية — technical standard

Standard Arabic syntax with established English technical terms left in Latin
script. Normal in Arabic developer documentation; when done carelessly it
becomes unreadable.

```text
بعد تشغيل `build`، ينتقل المشروع إلى مرحلة `test` قبل النشر.
```

Rules for this register:
- Keep identifiers, commands, and API names in Latin script inside code spans.
- Use the Arabic term for a concept the first time, with the English in
  parentheses: «المستودع (repository)».
- Never inflect an English word with Arabic affixes: no "يعمل deploy" mixing
  without a code span.

### عامية — dialect

Dialogue, marketing on social platforms, and user-facing chat. Egyptian,
Levantine, and Gulf differ enough that one does not substitute for another.

- Write in the dialect the user writes in, not a generic "Arabizi".
- Do not mix dialects inside one text.
- Do not use dialect in documentation.

### فصحى تراثية — classical

Religious texts, classical literature, and historical material. Preserves
orthography, uses classical vocabulary, may carry full tashkeel.

Do not produce classical pastiche for modern content; it reads as parody.

## Choosing

| Text | Register |
| --- | --- |
| Book, report, essay | فصحى معاصرة |
| README, tutorial, docs | فصحى معاصرة مبسطة |
| Developer docs with code | فصحى تقنية |
| Subtitles (broadcast/documentary) | فصحى معاصرة مبسطة |
| Subtitles (drama dialogue) | فصحى معاصرة, or dialect if the source is heavily colloquial and the user agrees |
| Social post, ad | عامية or simplified standard, not mixed |
| UI strings | simplified standard, short imperatives |
| Religious/classical | فصحى تراثية |

## Holding the register

Switches happen at predictable places. Watch for them:

1. **Explanations turn colloquial** when the writer tries to be friendly. Fix:
   keep the register, add clarity instead of warmth.
2. **Warnings turn bureaucratic** ("يتعين على المستخدم أن يقوم بـ"). Fix:
   imperative.
3. **Examples turn dialectal** because that is how people talk. Fix: keep
   examples in the same register as the body.
4. **Quotes import a different register.** Fine — quotes keep their own voice,
   and mark them clearly.

## Common register errors by pairing

| Wrong | Right | Problem |
| --- | --- | --- |
| ما تنساش تحفظ الملف في التوثيق | لا تنس حفظ الملف | عامية في نص فصيح |
| يجب على المستخدم اللي عايز يبدأ… | على المستخدم الذي يريد البدء… | خلط |
| إحنا هنشرح في الفصل ده | نشرح في هذا الفصل | خلط |
| كده تبقى جاهز | بذلك تكون جاهزًا | خلط |

Mix is acceptable only in quoted speech, and only if the source does it.
