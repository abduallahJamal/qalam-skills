# Arabic editing checklist

Before/after pairs are the fast way to learn the standard this skill enforces.
Every "before" below is real translated-Arabic output, not a strawman.

## 1. Machine-translation tells

| Before | After | Why |
| --- | --- | --- |
| من المهم أن نلاحظ أن النظام يدعم العربية | يدعم النظام العربية | حشو تمهيدي |
| لا شك أن هذه الميزة مفيدة | هذه الميزة مفيدة | تعزيز لا يضيف معلومة |
| في عالم اليوم الرقمي، تحتاج الشركات إلى… | تحتاج الشركات اليوم إلى… | كليشيه ترجمة لـ in today's digital world |
| تجدر الإشارة إلى أن الإصدار الجديد يصلح الخطأ | يصلح الإصدار الجديد الخطأ | حشو |
| يُعتبر هذا النهج من أفضل الممارسات | هذا النهج من أفضل الممارسات | calque لـ is considered |
| بشكل كبير / بشكل عام / بشكل أساسي | كثيرًا / عمومًا / أساسًا | ظرف واحد أفضل من `بشكل + صفة` |

A text with three or more of these per page was translated line by line.

## 2. Bureaucratic constructions

| Before | After |
| --- | --- |
| تم تنفيذ التحديث بواسطة الفريق | نفّذ الفريق التحديث |
| يقوم النظام بمعالجة الطلبات | يعالج النظام الطلبات |
| يجب أن يتم إجراء الاختبار | يجب إجراء الاختبار |
| من أجل أن نتمكن من المتابعة | لمتابعة |
| في حال عدم وجود ملف | إن لم يوجد ملف |
| وفقًا لما ذكره التقرير | وفق التقرير |

`تم + مصدر` is not wrong, but three in a paragraph read like a government form.

## 3. Sentence shape

**Long chain → split**

> قبل: وتعمل الأداة على قراءة الملفات من المجلد المحدد ثم تحللها وتستخرج المصطلحات
> وتقترح ترجمات لها ثم تحفظها في ملف قابل للتعديل يمكن للمستخدم مراجعته لاحقًا.

> بعد: تقرأ الأداة الملفات من المجلد المحدد وتحللها. تستخرج المصطلحات وتقترح
> ترجمات لها، ثم تحفظها في ملف قابل للتعديل يراجعه المستخدم لاحقًا.

**Weak opening → subject first**

> قبل: وهذا ما يجعل النظام مناسبًا للمشاريع الكبيرة.
> بعد: لذلك يناسب النظام المشاريع الكبيرة.

**Nominal stacking → verbal**

> قبل: إن عملية إتمام مراجعة الترجمة تتم عبر عدة مراحل.
> بعد: تتم مراجعة الترجمة على عدة مراحل.

## 4. Terminology consistency

Pick one and keep it:

| English | Options | Advice |
| --- | --- | --- |
| repository | مستودع / مخزن / ريبو | مستودع in docs, ريبو in developer chat |
| commit | إيداع / تثبيت / كوميت | التزم بالمصطلح الشائع في المجال: كوميت في الأدوات |
| deployment | نشر / توزيع | نشر |
| build | بناء / تجميع | بناء |
| token | رمز / توكن | رمز في التوثيق، توكن في سياق API |
| prompt | أمر / موجه / برومبت | موجه في التوثيق، برومبت شائع عمليًا |

The worst outcome is not a debatable choice; it is the same concept with three
renderings in one document. Add the decision to `glossary.json`.

## 5. Pronouns and reference

Arabic drops subjects, so ambiguity creeps in:

> قبل: يقرأ الملف ثم يحلله ويحفظه في المجلد، وهو ما يسمح بمراجعته لاحقًا.
> بعد: يقرأ الأداة الملف ويحلله ويحفظه في المجلد، ما يسمح بمراجعة النتيجة لاحقًا.

Rules:
- Repeat the noun when two or more candidates exist for the pronoun.
- `هو/هي` as a copula is usually a translation artifact: "هو أفضل" → "أفضل".
- `الذي/التي` chains of three or more: split the sentence.

## 6. Punctuation

| Rule | Example |
| --- | --- |
| Arabic comma | `الملف كبير، لكنه سريع` — not `,` |
| No space before | `النص، ثم` — not `النص ، ثم` |
| Semicolon for related clauses | `الأداة تقرأ؛ المحرك يحلل` |
| Question mark | `هل يعمل؟` — not `?` |
| Quotation | `«نص»` for prose |
| Colon | `:` after a lead-in, no space before |
| Ellipsis | `…` |
| Dash | `—` without surrounding spaces in Arabic, or `–` consistently |

Do not use English closing punctuation after Arabic text, and do not leave a
Latin comma inside an Arabic enumeration.

## 7. Repetition and rhythm

- Three consecutive paragraphs starting with the same word: vary two of them.
- `كما` repeated as "also" in every sentence: drop most of them; Arabic does not
  need an explicit "also" as often as English.
- `مما` chains: "مما يؤدي إلى مما يسبب" — one cause is enough.
- Parallel lists should be grammatically parallel (all verbs, or all nouns).

## 8. Numbers and dates

- Consistent digit script throughout (see `translate-docs/references/arabic-typography.md`).
- Thousands separator: `٬` with Arabic-Indic digits, `,` with Western.
- Dates: `٥ نوفمبر ٢٠٢٦` or `5 نوفمبر 2026`, and month names in Arabic.
- Ranges: `10–20` with an en dash, not a hyphen.
- Percent: `٪` with Arabic-Indic digits (`٪٢٥`)، `%` with Western (`25%`).

## 9. Headings

- No terminal punctuation.
- Parallel form across siblings: all nominal or all verbal.
- No "الفصل الأول: مقدمة" when the source is "Chapter 1: Introduction" and the
  book has only three chapters — keep the source's numbering scheme.
- Title case does not exist in Arabic; capitalise the first word only.

## 10. Final read

Read the text aloud. Stop at every place you stumble. That stumble is either a
punctuation problem, a missing pronoun, or a sentence that needs splitting.
Fix, reread, then stop.
