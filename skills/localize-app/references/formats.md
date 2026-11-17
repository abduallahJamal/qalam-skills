# Locale formats

Each section shows the same three keys in the format, then the traps specific to it.

Source strings:

```text
greeting = "Welcome back, {name}"
items    = "{count, plural, one {# item} other {# items}}"
signin   = "Sign in"
```

## JSON (i18next, react-intl, vue-i18n, custom)

```json
{
  "greeting": "مرحبًا بعودتك، {{name}}",
  "items": "{count, plural, zero {لا عناصر} one {عنصر واحد} two {عنصران} few {# عناصر} many {# عنصرًا} other {# عنصر}}",
  "signin": "تسجيل الدخول"
}
```

Traps:

- i18next uses `{{name}}`; react-intl uses `{name}`. Do not convert between them
  when translating — the file format is fixed.
- Nested objects are common; keep the nesting identical, only translate leaves.
- Key sorting: preserve the existing order so diffs stay reviewable.
- A value that is an array (lists of steps) must keep its length.

## .NET RESX

```xml
<data name="Greeting" xml:space="preserve">
  <value>مرحبًا بعودتك، {0}</value>
  <comment>Shown on the dashboard after sign-in</comment>
</data>
```

Traps:

- `<comment>` is the context field — read it, translate the `<value>` only.
- `xml:space="preserve"` must be kept, or leading/trailing spaces are lost.
- `{0}` placeholders are positional; reordering is allowed, renaming is not.
- Do not translate `name` attributes; they are keys.
- Some projects use `ResXFileCodeGenerator` with a generated designer file — never
  edit the generated file.

## gettext PO

```po
#. Shown under the password field after a failed sign-in
#: src/pages/login.tsx:42
msgid "Wrong email or password"
msgstr "البريد الإلكتروني أو كلمة المرور غير صحيحة"

msgid "{count} items"
msgid_plural "{count} items"
msgstr_plural[0] "لا عناصر"
```

Traps:

- `msgid` is the key and the source; never change it.
- `#.` is the developer comment — read it before translating.
- Arabic requires `msgstr[0..5]` for zero/one/two/few/many/other. A PO file with
  only `[0]` and `[1]` is structurally wrong for Arabic.
- Run `msgfmt --check` to validate placeholders and plural counts.
- `#, c-format` and `#, python-format` flags mean printf placeholders; they must
  survive exactly.

## Flutter ARB

```json
{
  "@@locale": "ar",
  "greeting": "مرحبًا بعودتك، {name}",
  "@greeting": {
    "description": "Dashboard greeting",
    "placeholders": {"name": {"type": "String"}}
  },
  "items": "{count, plural, zero{لا عناصر} one{عنصر واحد} two{عنصران} few{{count} عناصر} many{{count} عنصرًا} other{{count} عنصر}}",
  "@items": {
    "description": "Item count",
    "placeholders": {"count": {"type": "int"}}
  }
}
```

Traps:

- `@`-prefixed metadata must stay, with `description` translated only if your team
  treats it as human-facing (usually keep it in the source language).
- Placeholder **types** are declared in metadata; do not change `type`.
- Keep `@@locale` correct — a wrong value means the file is never loaded.
- ICU syntax is strict: no spaces inside `{}` in some versions; validate with
  `flutter gen-l10n`.

## iOS / macOS .strings

```text
"login.error" = "البريد الإلكتروني أو كلمة المرور غير صحيحة";
"greeting" = "مرحبًا بعودتك، %@";
```

Traps:

- The file is semicolon-terminated; a missing `;` silently drops the last key.
- `%@` is an object placeholder; `%1$@` is positional. Keep the type.
- `.stringsdict` handles plurals and needs the six Arabic categories:
  `zero`, `one`, `two`, `few`, `many`, `other`.
- Keep the file UTF-8; older projects used UTF-16 — match the existing encoding.

## Android strings.xml

```xml
<string name="greeting">مرحبًا بعودتك، %1$s</string>
<plurals name="items">
  <item quantity="zero">لا عناصر</item>
  <item quantity="one">عنصر واحد</item>
  <item quantity="two">عنصران</item>
  <item quantity="few">%1$d عناصر</item>
  <item quantity="many">%1$d عنصرًا</item>
  <item quantity="other">%1$d عنصر</item>
</plurals>
```

Traps:

- Use `%1$s` positional form so translators can reorder.
- Escape apostrophes: `\'` — an unescaped one is a build error.
- `<![CDATA[ … ]]>` is used for HTML in strings; do not unpack it.
- Do not translate `translatable="false"` strings or `name` attributes.
- Put the file in `res/values-ar/` (or `values-ar-rEG` for regional).

## XLIFF

```xml
<trans-unit id="greeting">
  <source>Welcome back, {name}</source>
  <target state="translated">مرحبًا بعودتك، {name}</target>
  <note>Dashboard greeting</note>
</trans-unit>
```

Traps:

- `state` tells the toolchain whether the string is reviewed. Do not mark
  `final` unless a human approved it.
- `<note>` is context; `<source>` is read-only.
- XLIFF 1.2 and 2.0 have different structures; match the file you were given.

## YAML (Rails, Jekyll, custom)

```yaml
ar:
  greeting: "مرحبًا بعودتك، %{name}"
  signin: "تسجيل الدخول"
```

Traps:

- Indentation is structure; never reformat.
- `%{name}` is Ruby-style interpolation.
- Quote strings that start with a special character (`*`, `&`, `%`, `@`, `-`) —
  in Arabic prose this is rare, but a string starting with `#` will be a comment.
- Arabic text in YAML is safe unquoted, but quoting avoids colon ambiguity.

## Cross-format checklist

- [ ] Key set identical to source
- [ ] Placeholder sets identical per key
- [ ] Plural categories complete for Arabic
- [ ] `@`/`#.`/`<comment>`/`<note>` context preserved
- [ ] Encoding and newline style preserved
- [ ] File still parses with the framework's own validator
- [ ] Key order preserved for reviewable diffs
