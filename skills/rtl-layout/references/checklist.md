# Pre-ship RTL checklist

Run this before a release that touches layout. Each item is binary: pass, fail,
or not applicable.

## Direction

- [ ] The document or app root sets both `lang` and `dir` (or the platform
      equivalent), from one place
- [ ] Switching language updates direction without a reload, or the reload is
      explicit and documented
- [ ] Nested LTR blocks (code, embedded English) reset direction locally

## Layout

- [ ] No `left`/`right`/`margin-left`/`padding-right`/`text-align: left` in
      direction-sensitive rules
- [ ] No `space-x-*`; spacing uses `gap`
- [ ] Icon-only buttons keep their hit area in the same visual position
- [ ] Scrollbars, drawers, and modals open from the start side
- [ ] Fixed-position elements (toasts, FABs) use logical insets

## Content

- [ ] Code, URLs, versions, and file paths render LTR
- [ ] Mixed Arabic/Latin text keeps internal order (bidi isolates present)
- [ ] Numerals follow one documented convention
- [ ] Arabic punctuation is used in Arabic text
- [ ] Nothing is truncated with an ellipsis at the visual start of a line

## Typography

- [ ] An Arabic-capable font is loaded, not a per-glyph fallback
- [ ] Line height ≥ 1.8 for Arabic body text
- [ ] No letter-spacing on Arabic
- [ ] No italic used for emphasis in Arabic
- [ ] Descenders are not clipped by tight line boxes or fixed heights

## Interaction

- [ ] Tab order follows visual order
- [ ] Swipe/gesture directions mirror where the platform expects them
- [ ] Keyboard shortcuts are unchanged by direction
- [ ] Focus rings are visible on a dark and light background

## Verification

- [ ] Read the first screen right-to-left with no instruction from the author
- [ ] 200% zoom pass on icons and text
- [ ] Screen-reader pass: reading order matches visual order
- [ ] Narrowest supported viewport: no clipping, no overlap
- [ ] One real device or one real platform renderer, not just DevTools
