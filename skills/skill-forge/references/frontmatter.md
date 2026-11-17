# SKILL.md frontmatter, per host

## The portable core

These six fields are defined by the Agent Skills specification and are safe
everywhere:

| Field | Required | Limit | Purpose |
| --- | --- | --- | --- |
| `name` | yes (hosts infer it from the folder if absent) | 64 chars, `^[a-z0-9]+(-[a-z0-9]+)*$` | Identifier and, where supported, the slash command |
| `description` | yes | 1024 chars | The only text the host sees before loading |
| `license` | no | — | SPDX identifier or short text |
| `compatibility` | no | 500 chars | Runtimes and tools the skill needs |
| `metadata` | no | flat map of strings | Your own keys; hosts do not act on them |
| `allowed-tools` | no (experimental) | — | Pre-approves tools in Claude Code; ignored elsewhere |

`metadata` values must be strings. A nested map is invalid per the spec, and some
hosts reject the file rather than ignoring the field. Quote numbers: `version:
"1.0"`, not `version: 1.0`.

## Host-specific fields

| Field | Claude Code | Codex | Cursor | OpenCode |
| --- | --- | --- | --- | --- |
| `allowed-tools` | pre-approves for the turn | ignored | ignored | ignored |
| `disallowed-tools` | removes tools | ignored | ignored | ignored |
| `model`, `effort` | honoured | ignored | ignored | ignored |
| `context: fork`, `agent` | honoured | ignored | ignored | ignored |
| `paths` | glob-scoped auto-load | ignored | supported (its own glob scoping) | ignored |
| `when_to_use` | appended to description | ignored | ignored | ignored |
| `argument-hint`, `arguments` | honoured | ignored | ignored | ignored |
| `hooks` | honoured | ignored | ignored | ignored |
| `disable-model-invocation` | honoured | ignored | ignored | ignored |

Consequence: a skill that only works because of `allowed-tools` will prompt for
permissions in three of four hosts. Do not depend on it for correctness; use it
as an optimisation where available.

## Discovery paths

| Host | Personal | Project | Also reads |
| --- | --- | --- | --- |
| Claude Code | `~/.claude/skills/` | `.claude/skills/` | nested `.claude/skills/` in subdirectories, plugin skills |
| Codex CLI | `~/.codex/skills/` | `.codex/skills/` | `~/.agents/skills/` in some versions |
| Cursor | `~/.cursor/skills/` | `.cursor/skills/` | `~/.agents/skills/`, legacy `.claude/` and `.codex/` |
| OpenCode | `~/.config/opencode/skills/` | `.opencode/skills/` | `~/.claude/`, `~/.agents/`, `.claude/`, `.agents/` |

`~/.agents/skills/` is the closest thing to a portable home: Cursor and OpenCode
read it, and it is a reasonable third location for Codex. `qalam install` writes
to all four plus `agents` if you ask it to.

## Frontmatter rules that break loading

| Problem | Symptom | Fix |
| --- | --- | --- |
| BOM at the start of the file | Skill silently absent | Save as UTF-8 **without** BOM |
| Blank line before `---` | Frontmatter not recognised | `---` must be the first line |
| Tabs for indentation | YAML parse error | Spaces only |
| Unquoted `:` in description | Truncated or invalid YAML | Wrap the value in double quotes |
| Description over 1024 chars | Rejected by strict hosts | Shorten; move detail to the body |
| Name with uppercase or underscores | Rejected by OpenCode | Lowercase, hyphens |
| Name ≠ folder name | Ambiguous in some hosts | Make them identical |
| Same skill name in two scopes | One shadows the other | Rename, or remove the duplicate |

## Minimal valid file

```markdown
---
name: my-skill
description: Do a specific thing with specific objects. Use when the user asks to <trigger>.
---

# My skill

What "done" means.
```

Two fields is enough. Everything else is optional; add fields only when a host
you actually use acts on them.
