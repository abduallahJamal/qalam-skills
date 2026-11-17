# Working on Qalam

Rules for any agent editing this repository. They exist because this pack is
consumed by four different hosts and by people who did not write it.

## The invariants

1. **A skill is portable or it is broken.** Frontmatter uses only the six Agent
   Skills fields: `name`, `description`, `license`, `compatibility`, `metadata`,
   `allowed-tools`. No `model`, `context`, `hooks`, or `paths` in a shipped skill.
2. **Determinism belongs in `qalam/`, not in a prompt.** If a step can be
   computed, add a function and a CLI subcommand. Do not ask a model to count.
3. **No third-party dependencies, no network calls.** The package must run on a
   bare Python 3.9 interpreter.
4. **Silent loss is the worst failure.** A blank chunk, a missing translation, a
   dropped word, or a skipped cue must produce a warning or an error — never a
   clean exit. See `merge_outputs`, `RunState.record`, and `wrap_lines`.
5. **Reports refuse to overclaim.** Every skill states what it did not verify.
6. **Arabic is first-class, not a locale.** Direction, punctuation, numerals,
   harakat, and gender agreement are design constraints, not decorations.

## Before you commit

```bash
python3 -m unittest discover -s tests -t .     # must be green
python3 -m qalam skill check skills --strict   # must be clean
python3 demo/run_demo.py                       # must end with artefacts
```

For a skill change, also:

- bump `metadata.qalam.version` in the affected `SKILL.md`,
- run `qalam install --dry-run` to confirm the installer still resolves it,
- re-read the failure table: did you add a failure mode that is not listed?

## Adding a skill

```bash
python3 -m qalam skill new my-skill "What it does and when. Use when…" --root skills
```

Then, in order: write the description for triggering (not for impressiveness),
add the governing rule, number the procedure, add a failure table, link only the
references that the procedure actually needs, and add a row to the skills table
in both READMEs.

A skill needs a **reason to exist** beyond "a prompt I like". If the work is
always-on guidance, it belongs in `AGENTS.md`. If it is a deterministic
transformation, it belongs in `qalam/`. A skill is for a procedure a model must
follow in order, with judgement between steps.

## Style

- Prose over bullet lists in skill bodies; tables for enumerable facts.
- Name the command, with placeholders in angle brackets.
- One idea per paragraph. No hype, no "powerful", no "seamless".
- British spelling in docs is fine; be consistent within a file.
- Arabic examples must be real Arabic, not transliterated English.

## Testing expectations

- Every bug you fix gets a test that fails before the fix.
- Tests are offline, use `tempfile`, and never touch a real home directory.
- The shell-safety test in `tests/test_install.py::test_home_is_isolated_per_test`
  exists because an earlier version of that suite wrote into the developer's real
  `~/.config/opencode`. Do not weaken it.

## Licensing

MIT. Contributions are under the same licence.
