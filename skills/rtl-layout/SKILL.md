---
name: rtl-layout
description: Make interfaces render correctly in Arabic, Hebrew, Persian, and Urdu — direction, mirrored layout, logical CSS properties, bidirectional text, numerals, icon mirroring, and RTL testing in HTML/CSS, React, Tailwind, Flutter, WPF, Android, iOS, and React Native. Use when building or fixing an RTL UI, when text looks reversed, or when asked to "add Arabic support".
license: MIT
compatibility: Framework-agnostic guidance; snippets exist for web, Flutter, WPF, Android, iOS, and React Native.
metadata:
  qalam.version: "1.0"
  qalam.kind: reference
  qalam.category: frontend
---

# RTL layout

RTL is not a stylesheet flip. It is a set of decisions: which properties are
physical, which are logical, which icons mirror, which numbers stay LTR, and
where bidirectional text needs isolation. Get those right and Arabic looks native;
get them wrong and every review cycle rediscovers the same six bugs.

## When to use this

The user asks to: support Arabic in an app or site, fix reversed text, add an RTL
variant, "flip the layout", or review a screenshot where things look wrong after
switching to Arabic. Also load before shipping any UI that contains Arabic.

## Procedure

### 1. Find out what already exists

Do not start writing CSS before you know how direction is currently decided.

```bash
# web
grep -rn "dir=\|direction:\|rtl\|:dir(" --include=*.{html,css,tsx,jsx,vue,svelte} . | head -40
# tailwind
grep -rn "rtl:\|ltr:\|space-x\|ml-\|mr-\|pl-\|pr-\|left-\|right-" --include=*.{tsx,jsx,vue,svelte,html} . | head -40
# flutter
grep -rn "Directionality\|EdgeInsetsDirectional\|TextAlign\|AlignmentDirectional" lib | head -30
# wpf
grep -rn "FlowDirection" --include=*.xaml . | head -20
```

Report what you found in one line. Most RTL bugs are a hard-coded physical
property, not a missing feature.

### 2. Set direction once, at the root

Direction is a property of the document or app, not of individual components.

**HTML**

```html
<html lang="ar" dir="rtl">
```

For a language switcher, set both attributes together — `lang` drives font and
spell-check, `dir` drives layout:

```js
document.documentElement.lang = locale;
document.documentElement.dir = isRTL(locale) ? "rtl" : "ltr";
```

**React**

```tsx
export function DirectionProvider({ locale, children }: { locale: string; children: React.ReactNode }) {
  const rtl = RTL_LOCALES.has(locale.split("-")[0]);
  useEffect(() => {
    document.documentElement.lang = locale;
    document.documentElement.dir = rtl ? "rtl" : "ltr";
  }, [locale, rtl]);
  return <div dir={rtl ? "rtl" : "ltr"}>{children}</div>;
}
```

**Flutter** — `MaterialApp` already wraps everything in a `Directionality` derived
from the locale; do not wrap widgets individually.

```dart
MaterialApp(
  locale: const Locale('ar'),
  supportedLocales: const [Locale('ar'), Locale('en')],
  localizationsDelegates: GlobalMaterialLocalizations.delegates,
)
```

**WPF**

```xml
<Window FlowDirection="RightToLeft" Language="ar-SA">
```

**Android** — set `android:supportsRtl="true"` in the manifest once; then use
start/end attributes everywhere.

**iOS** — set `semanticContentAttribute = .forceRightToLeft` on the layout view
when the app is Arabic-only, or rely on the locale automatically.

### 3. Replace physical properties with logical ones

This is the actual fix for 80% of RTL bugs.

| Physical | Logical |
| --- | --- |
| `margin-left` / `margin-right` | `margin-inline-start` / `margin-inline-end` |
| `padding-left` / `padding-right` | `padding-inline-start` / `padding-inline-end` |
| `border-left` | `border-inline-start` |
| `left` / `right` (positioned) | `inset-inline-start` / `inset-inline-end` |
| `text-align: left/right` | `text-align: start/end` |
| `float: left` | `float: inline-start` |
| `width` + fixed side | `inline-size` with logical insets |

Tailwind: use `ms-*`/`me-*`/`ps-*`/`pe-*`/`start-*`/`end-*` and
`text-start`/`text-end`. Avoid `space-x-*`, which is physical — use `gap-*`.

```html
<!-- wrong: breaks in RTL -->
<div class="flex space-x-4 pl-6 text-left">
<!-- right -->
<div class="flex gap-4 ps-6 text-start">
```

### 4. Handle the things that do not flip

Do not mirror everything. This is where RTL implementations look amateur.

**Mirror** — arrows that indicate direction of travel or reading, chevrons in
breadcrumbs, progress indicators, list bullets, "back" icons, text-alignment icons,
next/previous controls, indent/outdent.

**Do not mirror** — clocks, media player controls (play/pause/volume), logos and
brand marks, numbers, mathematical symbols, checkmarks, charts whose axes are
data-driven, keyboard shortcuts, photographs.

**Mirror conditionally** — charts and timelines (mirror the axis *labels*, not the
data), map controls, sliders (mirror direction, keep value order), carousels
(mirror navigation, keep content order).

```css
.icon-arrow { /* flips with direction */ }
[dir="rtl"] .icon-arrow { transform: scaleX(-1); }
.icon-logo, .icon-play { transform: none !important; }
```

For SVG sets, prefer authoring with `currentColor` and a `data-mirror` attribute
so one rule handles them:

```css
[dir="rtl"] [data-mirror="true"] { transform: scaleX(-1); }
```

### 5. Fix bidirectional text inside the layout

A layout can be RTL while some spans are LTR. Isolate them instead of reordering
characters.

```html
<p>الإصدار <bdi>v2.1.0</bdi> متاح الآن</p>
<code dir="ltr">npm install</code>
```

CSS for user-generated content that may contain both directions:

```css
.mixed { unicode-bidi: plaintext; }   /* direction of each paragraph from its first strong char */
```

Never insert U+200E/U+200F marks into the source text to "fix" display; they leak
into copy-paste, search, and diffs. Use isolation.

### 6. Fonts and numerals

- Load a font with real Arabic coverage and adequate vertical metrics:
  `Noto Naskh Arabic`, `IBM Plex Sans Arabic`, `Cairo`, `Tajawal`, `Dubai`,
  `Segoe UI`. A Latin-only font falls back per-glyph and produces mismatched
  weights mid-sentence.
- Line height 1.8–2.0 for Arabic body text (Latin needs ~1.5).
- Never apply `letter-spacing` to Arabic: it severs cursive joins.
- Numerals: decide Western vs Arabic-Indic once, then use the platform formatter
  (`Intl.NumberFormat("ar-EG")` gives ٠١٢…, `"ar-EG-u-nu-latn"` keeps 0–9).

```js
new Intl.NumberFormat("ar-EG").format(1234.5)            // ١٬٢٣٤٫٥
new Intl.NumberFormat("ar-EG-u-nu-latn").format(1234.5)  // 1,234.5
new Intl.DateTimeFormat("ar", { dateStyle: "long" }).format(new Date())
```

Keep Western digits inside code, versions, and technical IDs regardless.

### 7. Test it like a real RTL reader

1. Switch to Arabic and read the first screen right to left — does your eye land
   on the right element first?
2. Tab through the interface. Focus order must follow visual order.
3. Resize to the narrowest supported width. Arabic text is usually shorter in
   words but taller in line height; check clipping.
4. Paste mixed content into inputs and a preview: numbers, URLs, a Latin name at
   the start of an Arabic sentence, an Arabic name inside English.
5. Check every icon at 200% zoom for accidental mirroring.
6. Screen-reader pass: does the reading order match the visual order?

### 8. Report

State, in this order: what was hard-coded, what you changed, what you deliberately
did not mirror, what you could not verify (real device rendering, screen reader
behaviour), and the one-command way to reproduce the check.

## Framework notes

Detailed snippets live in `references/frameworks.md`. The short version:

- **React/Tailwind** — logical utilities, `dir` on `<html>`, avoid `space-x`,
  mirror icons with a data attribute.
- **Flutter** — `EdgeInsetsDirectional`, `AlignmentDirectional`,
  `TextAlign.start`, `Directionality` from locale, and never `EdgeInsets.only(left:)`.
- **WPF** — `FlowDirection` on the window, `TextAlignment` follow parent, and set
  `FlowDirection` per control when mixing an embedded English block.
- **Android** — `supportsRtl`, `start`/`end` attributes, `textDirection`,
  `TextDirectionHeuristics`.
- **iOS** — `leading`/`trailing` constraints, `.natural` text alignment,
  `semanticContentAttribute`.

## Failure modes

| Symptom | Cause | Fix |
| --- | --- | --- |
| Whole layout flips but the scrollbar moves to the left | Platform default for RTL documents | Expected; verify against the platform's own RTL apps before calling it a bug |
| Text appears reversed ("moc.elpmaxe") | A Latin string rendered in an RTL paragraph without isolation | Wrap in `<bdi dir="ltr">` or set `dir` on the element |
| Numbers split (١٢٣ becomes ٣٢١) | Digits split across a direction boundary | Isolate the whole numeric run |
| Icons mirrored twice | `scaleX(-1)` plus a mirrored parent | Apply mirroring at one level only |
| Padding correct in LTR, wrong in RTL | Physical property | Logical property |
| Arabic font looks bold/thin randomly | Per-glyph fallback | One font with full Arabic coverage |

## References

- `references/frameworks.md` — snippets per framework.
- `references/checklist.md` — pre-ship RTL review checklist.
