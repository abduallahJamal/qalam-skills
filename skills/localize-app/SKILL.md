---
name: localize-app
description: Localise application strings into Arabic and other languages — JSON, .resx, .po/.pot, XLIFF, .arb, .strings, and YAML — with placeholder safety, plural rules (including Arabic's six categories), RTL metadata, text expansion budgets, and a review pass. Use when asked to translate UI strings, add an Arabic locale, or fix broken placeholders after localisation.
license: MIT
compatibility: Python 3.9+ optional, for placeholder and plural checks. File-format snippets are tool-independent.
metadata:
  qalam.version: "1.0"
  qalam.kind: procedure
  qalam.category: i18n
---

# Localise an app

String localisation is not document translation at a smaller size. Strings are
fragments without context, they carry placeholders that must survive exactly,
they appear inside fixed-size pixels, and Arabic has six plural categories where
English has two.

**Governing rule:** a translation that breaks a placeholder or a plural form is a
crash or a wrong sentence, not a style issue. Those two checks are mandatory for
every key, before any prose is polished.

## When to use this

The user asks to: add Arabic to an app, translate `en.json`, localise a Flutter
`.arb`, a .NET `.resx`, a gettext `.po`, an iOS `.strings`, or "make the interface
Arabic". Also load when a locale file exists and placeholders are broken.

Not for: long-form prose (`translate-docs`) or layout (`rtl-layout` — load that
too when the UI has never supported RTL).

## Procedure

### 1. Inventory the locale files and the pipeline

```bash
find . -name "*.json" -path "*locales*" -o -name "*.resx" -o -name "*.po" \
  -o -name "*.arb" -o -name "*.strings" -o -name "*.xliff" | grep -v node_modules | head -40
```

Record: the source locale, the file format, the key naming convention, where the
files are loaded from, and whether the framework needs registration in a config
file (`i18n.ts`, `l10n.yaml`, `.csproj`, `Info.plist`, Xcode targets).

If an Arabic file exists already, do not overwrite it wholesale. Translate the
missing keys, and report the keys that differ in shape.

### 2. Extract context for every key

A translator without context writes fluent nonsense. Before translating, collect:

- the key name (`checkout.empty_cart.title` — the path is context),
- the source string,
- max length constraints, if the UI enforces any,
- neighbouring keys (they share a screen),
- any comment/description field the format supports (`.resx` `<comment>`,
  gettext `#.`, ARB `@description`, XLIFF `<note>`).

```json
{
  "login.error.invalid_credentials": {
    "value": "Wrong email or password",
    "description": "Shown under the password field after a failed sign-in"
  }
}
```

If the source file has no descriptions, say so in the report: it limits quality,
and it is worth adding descriptors before the next locale.

### 3. Protect placeholders and markup

This is the check that prevents crashes. Compare placeholder sets key by key.

| Format | Placeholder |
| --- | --- |
| ICU MessageFormat | `{count, plural, ...}`, `{name}` |
| printf | `%s`, `%d`, `%1$s` |
| .NET | `{0}`, `{1:yyyy}` |
| Python/str | `%(name)s`, `{}` |
| Flutter/ARB | `{count}`, `{name}` |
| Android | `%1$s`, `<xliff:g>` |
| iOS | `%@`, `%1$@` |
| React | `{count}` inside JSX strings, `<Trans>` components |

Rules:

- Placeholders must appear in the target, with identical names, types, and count.
- Positional placeholders may be reordered — that is their purpose. Named ones
  must keep their names.
- Never translate the identifier inside a placeholder (`{{userName}}` stays).
- Never translate markup: `**bold**`, `<b>`, `<link>`, `\n`, `&amp;`.
- Do not split a placeholder across words.
- If a string is only a placeholder plus punctuation, it may need no translation
  at all — copy it.

### 4. Handle plurals with Arabic rules

Arabic has **six** CLDR plural categories: `zero`, `one`, `two`, `few`, `many`,
`other`. English has two. A two-branch plural translated into Arabic with two
branches is wrong for most counts.

```json
{
  "items": "{count, plural, zero {لا عناصر} one {عنصر واحد} two {عنصران} few {# عناصر} many {# عنصرًا} other {# عنصر}}"
}
```

Notes:

- `few` covers 3–10 and `many` covers 11–99; `other` covers 100+ and
  non-integers.
- `#` inserts the formatted number, honouring the locale's digit script.
- Arabic agreement changes with the category: element count 3–10 takes a plural
  noun; 11–99 takes a singular accusative noun. Do not "fix" that — it is correct.
- If the format has no plural machinery (plain JSON key/value), do not invent
  branches. Either switch the file to ICU, or write a neutral phrasing
  ("العناصر: {count}") and flag it.

### 5. Respect space budgets

Arabic is usually 10–25% shorter in characters but taller in line height, and
some terms expand: short labels, buttons, and verbs expand most.

| Element | Typical change | Mitigation |
| --- | --- | --- |
| Button label | −10% to +30% | Allow wrapping or use a shorter synonym |
| Menu item | ±20% | Truncate with tooltip, never mid-word |
| Tab label | −20% | Arabic is often shorter here |
| Input placeholder | varies | Keep under the source's visual width |
| Heading | ±15% | Check at the smallest breakpoint |
| Error message | −5% | Keep the actionable part first |

If the UI uses fixed widths, flag the keys that will overflow instead of silently
shortening them into vagueness — report them as "needs design change".

### 6. Write the Arabic

- **Register**: simplified فصحى, imperative for actions ("حفظ", "إلغاء"), noun
  phrases for labels ("اسم المستخدم"). No dialect unless the whole product is
  dialectal.
- **Sentence case**, not title case: Arabic has no title case; capitalise the
  first word only.
- **Punctuation**: Arabic `،` `؟` inside sentences; no terminal period on short
  labels, periods on full sentences — match the source's convention per key type.
- **No tashkeel.**
- **Avoid gendered phrasing where the user's gender is unknown.** Prefer neutral
  forms: "تم الحفظ" over "حفظت", "يمكنك المتابعة" over "أنت جاهز".
- **Keep Latin for**: brand names, product names the brand keeps in Latin,
  keyboard shortcuts, code-like values.
- **Consistency**: build or reuse a glossary (`glossary-builder`) for domain nouns;
  the same English noun must not become three Arabic nouns in one app.

### 7. Verify mechanically

For each locale file pair, check:

1. Same key set (no missing, no extra).
2. Placeholder sets identical per key.
3. Plural categories present for Arabic where a count is used.
4. No empty values.
5. No source-language leftovers in values that should be translated.
6. Encoding is UTF-8 without BOM, newlines consistent with the repo.
7. JSON/YAML/PO still parses (`python -m json.tool`, `msgfmt -c`, framework lint).

```bash
python -m json.tool ar.json > /dev/null && echo "json ok"
msgfmt --check -o /dev/null ar.po 2>&1 | head
```

For a quick placeholder diff without extra tooling:

```bash
python - <<'PY'
import json, re, sys
placeholder = re.compile(r"\{[^{}]+\}|%\d*\$?[sd@]|%\([^)]+\)s")
src = json.load(open("en.json")); tgt = json.load(open("ar.json"))
for key in src:
    a = sorted(placeholder.findall(str(src[key])))
    b = sorted(placeholder.findall(str(tgt.get(key, ""))))
    if a != b:
        print("MISMATCH", key, a, b)
missing = set(src) - set(tgt)
print("missing keys:", sorted(missing))
PY
```

### 8. Report

- Keys translated / total, and keys deliberately left in the source language.
- Placeholder mismatches found and fixed.
- Keys that need plural handling but the format cannot express it.
- Keys that will overflow their container (with the estimated change).
- Keys with no context, where quality is best-effort.
- Whether `rtl-layout` work is needed before this locale can ship.

## Failure modes

| Symptom | Cause | Fix |
| --- | --- | --- |
| App crashes after switching to Arabic | Format placeholder changed or dropped | Diff placeholder sets per key; never rename `{}` contents |
| "1 items" shows in Arabic | Two-branch plural in a six-category language | Use the full ICU plural set |
| File loads but keys are missing | Nested JSON flattened during translation | Keep the nesting identical; translate leaves only |
| Build fails on an apostrophe | Unescaped `\'` in `strings.xml` | Escape apostrophes |
| `.strings` file loses its last key | Missing trailing semicolon | Validate the file, not just the diff |
| Translations are correct but text is cut off | Fixed-width container | Report the key as needing a design change instead of shortening it |
| Arabic file silently never loads | Wrong `@@locale` or wrong folder name | Check the locale code and the `values-xx` directory |
| Mixed English inside an Arabic label | Brand or code term translated | Keep brand names and identifiers in Latin script |

## References

- `references/formats.md` — per-format examples and pitfalls.
- `references/plural-rules.md` — Arabic plural categories with worked examples.
