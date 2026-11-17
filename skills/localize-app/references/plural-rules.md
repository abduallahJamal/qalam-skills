# Arabic plural rules

Arabic marks six CLDR categories. A translation with two branches is not
"simpler" — it is wrong for most numbers.

## The categories

| Category | Integer counts | Arabic noun form | Example (عنصر) |
| --- | --- | --- | --- |
| `zero` | 0 | often a negation phrase | لا عناصر |
| `one` | 1 | singular | عنصر واحد |
| `two` | 2 | dual | عنصران |
| `few` | 3–10 | plural genitive | ٣ عناصر |
| `many` | 11–99 | singular accusative | ١١ عنصرًا |
| `other` | 100+, decimals | singular after the count | ١٠٠ عنصر |

Note the inversion that trips people up: 3–10 takes the **plural** noun, 11–99
takes the **singular**. This is correct Arabic grammar, not a bug.

## Worked example

```json
"{count, plural, zero {لا توجد ملفات} one {ملف واحد} two {ملفان} few {# ملفات} many {# ملفًا} other {# ملف}}"
```

| count | output |
| --- | --- |
| 0 | لا توجد ملفات |
| 1 | ملف واحد |
| 2 | ملفان |
| 3 | ٣ ملفات |
| 11 | ١١ ملفًا |
| 100 | ١٠٠ ملف |

## Common template cases

**Items in a list**

```text
zero {لا عناصر} one {عنصر واحد} two {عنصران} few {# عناصر} many {# عنصرًا} other {# عنصر}
```

**Days remaining**

```text
zero {ينتهي اليوم} one {يوم واحد متبقٍ} two {يومان متبقيان} few {# أيام متبقية} many {# يومًا متبقيًا} other {# يوم متبقٍ}
```

**People**

```text
zero {لا مشاركين} one {مشارك واحد} two {مشاركان} few {# مشاركين} many {# مشاركًا} other {# مشارك}
```

**Files uploaded** — prefer the count-first form when the sentence is long:

```text
تم رفع {count} من الملفات
```

This sidesteps agreement entirely and is legitimate for progress messages.

## Rules of thumb

1. If the number is at the **start** of the phrase or after a preposition, the
   singular-after-count form (`other`) is often acceptable for all counts.
2. If the number modifies a noun the user reads as a quantity ("3 items in cart"),
   use the full six branches.
3. `zero` should be a real phrase, not "٠ عناصر". "لا عناصر" and "لا توجد عناصر"
   read correctly; "٠ عناصر" does not.
4. Do not use `dual` for things that never come in exactly two (rare) — but do not
   skip it for things that do (days, hands, twins, eyes).
5. Ordinals are a separate rule set; do not reuse the plural branches.

## Formats that cannot express it

| Format | Solution |
| --- | --- |
| Plain key/value JSON | Use ICU MessageFormat, or restructure the string to avoid agreement |
| Simple `%s` printf | Same as above; a bare printf cannot carry six forms |
| `.strings` without `.stringsdict` | Add a `.stringsdict` |
| Android `strings.xml` | Use `<plurals>` with all six `<item quantity>` |
| gettext PO | Six `msgstr[N]` entries, in the order `nplurals` declares |

If the format genuinely cannot express the categories and changing it is out of
scope, translate with a count-independent phrasing and report it as a limitation.
Never fake plurality by writing "عناصر" and letting 1 read as "1 عناصر".

## Testing

Try these counts on every count-bearing string before shipping: **0, 1, 2, 3, 10,
11, 99, 100, 101, 1.5**.

If a number can be negative, add **−1** (falls in `other` in CLDR Arabic).
