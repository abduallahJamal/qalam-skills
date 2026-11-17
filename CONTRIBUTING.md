# Contributing

Thanks for considering a contribution. This document says what gets merged and
what gets asked for changes.

## What is welcome

- **New skills** for a procedure that is genuinely reusable and not covered.
- **New checks** in the quality gate, with tests and a false-positive analysis.
- **Locale support** beyond Arabic where the same machinery applies (Hebrew, Farsi,
  Urdu all share the RTL and bidi problems).
- **Framework snippets** for RTL that are verified against the framework's own
  current documentation.
- **Bug reports** with the file that reproduces them, even a snippet.

## What is not merged

- A skill that duplicates an existing one with different words.
- Prompt-only "skills" that restate what a model already does.
- Dependencies. The package stays stdlib-only, and the tests stay offline.
- Behaviour that silently drops content to make a check pass.
- Claims of accuracy without a verification step behind them.

## Workflow

1. Open an issue describing the problem the change solves.
2. Fork, branch from `main`, keep one concern per commit.
3. Add tests. For a skill change, add or update the contract test in
   `tests/test_skills_pack.py` if the new behaviour is structural.
4. Run the three commands in `AGENTS.md` before you push.
5. Open a pull request that says what changed, why, and what you did not verify.

## Reporting a defect

Include: the command you ran, the input (redacted if needed), the output, and what
you expected. If it involves Arabic text, paste the raw text — a screenshot
cannot be diffed.

## Code of conduct

Be precise, be kind. Critique the artefact, not the person.
