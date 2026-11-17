# Framework snippets

Each section is self-contained and copy-pasteable. All of them assume direction is
already set at the root; that is covered in the skill body.

## Web: CSS logical baseline

```css
:root {
  --font-arabic: "Noto Naskh Arabic", "IBM Plex Sans Arabic", "Segoe UI", serif;
  --leading-arabic: 1.9;
}

[lang="ar"], [lang="fa"], [lang="ur"] {
  font-family: var(--font-arabic);
  line-height: var(--leading-arabic);
  letter-spacing: 0;          /* never track Arabic */
}

/* Cards, nav, forms: logical only */
.card { padding-inline: 1.25rem; border-inline-start: 3px solid var(--accent); }
.nav  { display: flex; gap: .5rem; }

/* Mixed-direction user content */
.prose, .user-content { unicode-bidi: plaintext; text-align: start; }

/* Code always LTR inside RTL pages */
pre, code, kbd, samp { direction: ltr; text-align: left; unicode-bidi: isolate; }
```

If you must support old browsers, provide both physical and logical declarations;
logical wins where supported:

```css
.button { margin-left: 8px; margin-inline-start: 8px; }
```

## React: locale-aware direction

```tsx
const RTL_LOCALES = new Set(["ar", "he", "fa", "ur", "ps", "sd", "yi", "ckb"]);

export function useDirection(locale: string) {
  const rtl = RTL_LOCALES.has(locale.split("-")[0].toLowerCase());
  useEffect(() => {
    const root = document.documentElement;
    root.lang = locale;
    root.dir = rtl ? "rtl" : "ltr";
    document.body.dataset.dir = rtl ? "rtl" : "ltr";
  }, [locale, rtl]);
  return rtl ? "rtl" : "ltr";
}
```

Icon mirroring as a component property, not a CSS hack per call site:

```tsx
export function DirectionalIcon({ src, mirror = true, ...rest }: Props) {
  return <img src={src} data-mirror={mirror} className="directional-icon" {...rest} />;
}
```

```css
.directional-icon[data-mirror="true"]:dir(rtl) { transform: scaleX(-1); }
```

`:dir()` is supported in current browsers and is more robust than `[dir="rtl"]`
ancestor matching, because it follows nested direction changes.

## Tailwind

| Avoid | Use |
| --- | --- |
| `ml-4 mr-2` | `ms-4 me-2` |
| `pl-6 pr-6` | `ps-6 pe-6` |
| `left-0 right-0` | `start-0 end-0` |
| `text-left text-right` | `text-start text-end` |
| `space-x-4` | `gap-4` |
| `border-l-2` | `border-s-2` |
| `rounded-l-lg` | `rounded-s-lg` |
| `translate-x-4` | `translate-x-4 rtl:-translate-x-4` (or a direction-aware wrapper) |

For transforms Tailwind has no logical equivalent; add the `rtl:` variant
explicitly and mirror the sign.

## Flutter

```dart
// Directional insets
padding: const EdgeInsetsDirectional.only(start: 16, end: 8)

// Directional alignment
alignment: AlignmentDirectional.centerStart

// Text
Text("مرحبا", textAlign: TextAlign.start)

// Icons that mirror
Icon(Icons.arrow_forward, textDirection: Directionality.of(context))  // auto-mirrors for directional icons
// Icons that must not mirror
Icon(Icons.play_arrow, matchTextDirection: false)

// Language switching at runtime
Directionality(textDirection: isRtl ? TextDirection.rtl : TextDirection.ltr, child: app)
```

Material's `Icons.arrow_back` and friends respect text direction; brand and media
icons do not, which is the behaviour you want.

Localised formatting:

```dart
import 'package:intl/intl.dart';
final fmt = NumberFormat.decimalPattern('ar');
fmt.format(1234.5);           // ١٬٢٣٤٫٥
DateFormat.yMMMMd('ar').format(DateTime.now());
```

## WPF

```xml
<Window FlowDirection="RightToLeft" Language="ar-SA" FontFamily="Segoe UI, Tahoma">
```

- `FlowDirection` propagates to children; set it back to `LeftToRight` on an
  embedded block that must stay LTR:

```xml
<FlowDirection="LeftToRight" Language="en-US" xml:lang="en-US" TextAlignment="Left"/>
```

- Use `Grid` column order that reads naturally; `FlowDirection` mirrors the visual
  placement of columns, so define columns logically (first = start).
- `TextBlock.TextAlignment="Right"` inside an RTL window is usually unnecessary;
  it also breaks mixed content. Prefer inheriting.
- Avoid fixed `Margin="left"` assumptions; use separate margins for the mirrored
  edges or bind to `FlowDirection`.
- For labels next to inputs, keep the label-INPUT order as in the source; WPF
  mirrors the whole row.
- Set `xml:lang` on mixed-language runs so the right font and hyphenation apply.
- Localise numbers with `CultureInfo.GetCultureInfo("ar-EG")`; keep
  `CultureInfo.InvariantCulture` for technical values.

```xml
<TextBlock>
  <Run xml:lang="ar">الإصدار</Run>
  <Run xml:lang="en">1.4.0</Run>
</TextBlock>
```

## Android

```xml
<!-- AndroidManifest.xml -->
<application android:supportsRtl="true" ... />
```

```xml
<!-- res/layout/screen.xml -->
<TextView
    android:textDirection="firstStrong"
    android:textAlignment="viewStart"
    android:paddingStart="16dp"
    android:paddingEnd="8dp" />
```

- Use `start`/`end` attributes; never `left`/`right`.
- `android:textDirection="locale"` for known-language content,
  `firstStrong` for user-generated content.
- Drawables: mirror with `android:autoMirrored="true"` on the drawable (for
  arrows) and leave it off for logos.
- `LinearLayout` with `layoutDirection` follows the locale automatically when
  `supportsRtl` is on.
- Numbers: `NumberFormat.getInstance(Locale.forLanguageTag("ar-EG"))`.

## iOS / SwiftUI

```swift
// UIKit
view.semanticContentAttribute = .forceRightToLeft
label.textAlignment = .natural
NSLayoutConstraint(item: a, attribute: .leading, relatedBy: .equal, toItem: b, attribute: .trailing, constant: 0, multiplier: 1, size: nil)

// SwiftUI
Text("مرحبا").environment(\.layoutDirection, .rightToLeft)
Text("مرحبا").multilineTextAlignment(.leading)
```

- Use `leading`/`trailing` constraints, never `left`/`right`.
- `UIImage.imageFlippedForRightToLeftLayoutDirection()` for directional glyphs.
- `Locale(identifier: "ar")` for formatters.

## React Native

```js
import { I18nManager } from "react-native";
I18nManager.forceRTL(true);          // requires an app restart
I18nManager.allowRTL(true);
```

Restart after changing it, and test a cold start: the flag does not apply to the
current session. Then use:

```js
{ flexDirection: "row" }                       // auto-reverses with RTL
{ marginStart: 12, marginEnd: 8 }              // logical
{ textAlign: "left" }                          // becomes start-relative in RTL builds
```

`transform: [{ scaleX: -1 }]` on an icon needs a matching flip on the child text,
which is why logical icons are preferred.

## Charts and data visualisation

- Mirror the axis labels' alignment, not the data order.
- Time axes stay left-to-right in almost every Arabic convention; do not flip them
  without asking.
- Legend placement moves to the start side.
- Numeric tooltips use the locale formatter but keep LTR internal order.

## Email HTML

Email clients ignore `:dir()`. Use `[dir="rtl"]` attribute selectors and put
`dir="rtl"` on every `<table>`; also set `align="right"` because Outlook desktop
ignores direction on some table cells.

```html
<table dir="rtl" align="right" style="direction:rtl;text-align:right">
```
