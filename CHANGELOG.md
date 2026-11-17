# Changelog

All notable changes to Qalam are recorded here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/); versions follow
[Semantic Versioning](https://semver.org/).

The skills themselves are versioned separately in each `SKILL.md` under
`metadata.qalam.version`, so a host knows which copy it loaded.

## [1.0.0] — 2026-11-17

### Added

- Nine skills, portable across Claude Code, Codex CLI, Cursor, and OpenCode:
  `translate-docs`, `arabic-style`, `rtl-layout`, `glossary-builder`,
  `translation-qa`, `localize-app`, `extract-docs`, `subtitle-translate`, and
  `skill-forge`.
- `qalam` Python package (stdlib only): chunking, glossary, run state,
  translation memory, quality gate, RTL HTML preview, skill validation, and
  installer.
- `qalam install` with link/copy modes, junction support on Windows, backups
  before replacing an existing skill, and `qalam doctor` to report staleness.
- Fifteen-check quality gate including Arabic punctuation, numeral-script
  checks, untranslated line detection, and terminology enforcement.
- Arabic text primitives: direction detection, script distribution, bracket
  balancing, protected-span masking, and bidi isolation.
- Subtitle tool for SRT/VTT: parse, measure, lint, rewrap without dropping
  words, shift, and verify timing after translation.
- 212 offline tests, contract tests over the shipped skills, and a runnable
  end-to-end demo.
- Documentation in Arabic and English.

### Notes

- The skills do not translate by themselves; the host model translates and the
  toolkit verifies.
- Frozen behaviour worth knowing: an empty or blank chunk output is never
  recorded as done, and a merge reports missing chunks instead of skipping them.

### Fixed

- `qalam/install.py` and `qalam/scaffold.py` called
  `Path.write_text(..., newline="\n")`, which only exists from Python 3.10, so
  `qalam install` and `qalam skill new` raised `TypeError` on the 3.9 floor the
  package declares. Both now go through `qalam.textutil.write_text_lf`.
- `skills/subtitle-translate/scripts/subs.py` printed U+2192 and Arabic text
  straight to stdout, so `check`, `shift`, and `wrap` crashed with
  `UnicodeEncodeError` on a legacy Windows code page after the output file was
  already written. Output now degrades to ASCII (`->`) instead of raising.
- CI: Python 3.9 is no longer published for `ubuntu-latest` (26.04), which made
  those jobs fail before running a single test. The floor is now pinned to
  `ubuntu-22.04` so it keeps being tested.

[1.0.0]: https://github.com/abduallahJamal/qalam-skills/releases/tag/v1.0.0
