---
name: skill-forge
description: Write and review agent skills (SKILL.md) that work unchanged in Claude Code, Codex CLI, Cursor, and OpenCode — portable frontmatter, descriptions that trigger reliably, progressive disclosure, bundled scripts, and tests. Use when asked to create a skill, fix one that never loads, or convert a prompt or runbook into a reusable skill.
license: MIT
compatibility: Claude Code, Codex CLI, Cursor 2.4+, OpenCode 1.x. Python 3.9+ optional for `qalam skill check`.
metadata:
  qalam.version: "1.0"
  qalam.kind: procedure
  qalam.category: authoring
---

# Skill forge

A skill is a folder with a `SKILL.md`: frontmatter the host reads every session,
and a body the host reads only when the skill is chosen. Everything that matters
follows from that asymmetry — the description earns the load, the body pays it off.

**Governing rule:** if the work can be done deterministically, put it in a script
and have the skill call the script. A skill that asks a model to recount lines or
compute a ratio will be wrong on long inputs and cost tokens doing it.

## When to use this

- "Make a skill for X", "turn this into a skill", "why doesn't my skill load?"
- Converting a runbook, a checklist, or a long prompt into something reusable.
- Reviewing a skill pack before sharing it with a team.
- Writing a skill that must work in more than one host.

## What makes a skill load

Hosts see only `name` and `description` before deciding. Three failure modes:

1. **Description too vague** — "Helps with documents" never matches a real
   request. It must name the objects and the intents a user actually types.
2. **Frontmatter malformed** — a BOM, a blank line before `---`, tabs, or a
   missing closing fence. Most hosts fail silently.
3. **Duplicated names** across scopes — one shadows the other and behaviour
   becomes unpredictable.

## Procedure

### 1. Decide the shape

| The work is… | Build |
| --- | --- |
| A procedure with steps and checks | a skill with a numbered procedure |
| Reference knowledge the model lacks | a skill that links to `references/*.md` |
| Deterministic computation or file surgery | a skill that calls a bundled script |
| A house rule that always applies | not a skill — put it in `AGENTS.md` |

A skill that is really a rule ("always use four spaces") costs context on every
match and belongs in the project's always-on instructions.

### 2. Write the description first

The description is the product. Structure it as:

```text
<What it does, with the concrete objects and verbs> — <the specific sub-tasks>. Use when <trigger phrases the user would actually type>.
```

Rules:

- Under 1024 characters (hard limit in the spec); aim for 180–350.
- One sentence or two, no line breaks — many hosts list only the first line.
- Include nouns a user would say: "PDF", "subtitle", "Arabic", "RTL", "glossary".
- Include the intent, not the implementation: "review a translation", not "runs
  qalam gate".
- Add a second language if your users type in it: the Arabic phrases "عرّب",
  "ترجمة", "مراجعة" belong in the description of an Arabic-facing skill.

Compare:

```text
# weak — matches almost nothing
description: A helper for translation work.

# usable — names objects, intents, and triggers
description: Translate long documents and books between any two languages with a
consistent glossary and a structural QA gate; Arabic-first defaults with RTL and
punctuation rules. Use when asked to translate a book, manual, or docs folder, or
to produce an Arabic version of a file.
```

### 3. Write the body as a procedure

A body is read by a model under time pressure, mid-task. It must be skimmable.

- **Start with the contract.** One paragraph, or one bolded sentence, that says
  what "done" means. Put the governing rule before any procedure.
- **Number the steps.** The model will follow them in order and will report which
  one failed.
- **Give the exact commands**, with placeholders marked: `qalam gate --source
  <chunk> --target <output>`. A command the model must reconstruct from prose is
  a command it will get wrong.
- **State the defaults** so the model does not stop to ask: "target_language
  defaults to ar; confirm only if the request is ambiguous."
- **List failure modes in a table**, symptom → cause → fix. This is the highest
  value section in any skill, because it is what the model reads when something
  goes wrong.
- **Define the report.** Say what the final message must contain — paths, counts,
  what was not verified.

Length: 150–400 lines for a procedure skill. Beyond that, move detail into
`references/` and link it from the body. A 2000-line SKILL.md is read once and
then ignored.

### 4. Use progressive disclosure

```text
skills/my-skill/
├── SKILL.md                  # the procedure, always loaded on match
├── references/
│   ├── rules.md              # read only when the procedure says to
│   └── checklist.md
├── scripts/
│   └── tool.py               # run, not read
└── assets/
    └── template.html         # copied into output
```

- Name references in the body with a reason, and say what triggers the read
  (for example: "read the timing-rules reference before splitting a cue").
- Never say "read everything in references/". That defeats the mechanism.
- Scripts are for determinism, not for hiding logic. A user will open them; make
  them readable and standard-library-only where possible.

### 5. Make it portable

Write frontmatter with the six spec fields only:

```yaml
---
name: my-skill
description: …
license: MIT
compatibility: Python 3.9+; any of pandoc, calibre
metadata:
  owner: team-name
  version: "1.0"
---
```

`allowed-tools`, `model`, `context`, `hooks`, and `paths` are host-specific:
Claude Code honours them, Cursor and Codex ignore them. A skill that depends on
`allowed-tools` for its behaviour will behave differently per host. If you need a
host-specific field, put it in a variant folder and document the difference — do
not let the portable copy silently depend on it.

Paths: refer to skills files relative to the skill directory, never with absolute
paths, and never assume `~/.claude`.

### 6. Test the skill, not just the prose

Three tests that catch almost everything:

1. **Frontmatter test** — parses, has both required fields, name matches folder.
2. **Trigger test** — take five real user requests that should load this skill and
   five that should not. Does the description distinguish them? If a negative
   request would match, tighten the description.
3. **Script test** — run the bundled script on a fixture; assert exit codes and
   output shape. A skill whose script fails on the first real input burns the
   whole task.

```bash
python -m qalam skill check skills --strict
python -m qalam skill new my-skill "What it does. Use when…" --root skills
```

### 7. Review someone else's skill

Read in this order, and report what you find:

1. Frontmatter — valid, portable, description specific?
2. First paragraph — is the contract clear?
3. Procedure — executable, in order, with real commands?
4. Failure table — present and specific?
5. References — linked with reasons, not dumped?
6. Length — is any section restating what a model already knows?
7. Scripts — deterministic, no network, no destructive defaults?
8. Report contract — does it force honesty about what was not verified?

Common defects worth naming: descriptions that could match anything, procedures
that say "analyze the code" with no criteria, scripts that print but never exit
non-zero, references that duplicate the body, and skills that claim capabilities
the bundled tools do not have.

## Anti-patterns

| Anti-pattern | Why it fails | Instead |
| --- | --- | --- |
| "Be thorough, be accurate" | Unfalsifiable; changes no behaviour | Give a checklist with binary items |
| Repeating the whole rule set in every step | Context bloat, contradictory emphasis | State a rule once, reference it |
| A skill per file type | Fragmented, overlapping triggers | One skill, a table of formats |
| Scripts that need a venv | Users skip them | Standard library, or a documented install |
| Silent success | The model reports done when nothing ran | Every script exits non-zero on failure |
| Instructions to "ask the user" at every step | Turns a task into an interrogation | Defaults + one confirmation |

## Reporting

When you deliver a skill, state: the path, what triggers it, what it does not
cover, and how to verify it loads in each host. Do not claim it "works in all
agents" without naming the versions you checked.

## References

- `references/frontmatter.md` — every field, per host.
- `references/examples.md` — annotated good and bad skill skeletons.
