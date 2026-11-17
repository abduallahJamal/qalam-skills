# Security Policy

## Supported versions

| Version | Supported |
| :--- | :--- |
| 1.0.x | ✅ |

## Reporting a vulnerability

Open a private advisory at
<https://github.com/abduallahJamal/qalam-skills/security/advisories/new>
instead of a public issue.

Please include the command you ran, the input file (redacted if it contains
anything private), the output, and what you expected. A reproduction beats a
description.

## Scope, honestly stated

Qalam is a local library and a set of Markdown skills. It opens no sockets, reads
no environment secrets, and installs nothing from the network — CI fails the build
if the package ever imports `socket`, `http.client`, `requests`, `httpx`,
`urllib3`, or `aiohttp`.

The realistic risks are therefore not remote exploits:

1. **The installer writes outside the repository.** `qalam install` creates
   directories under your home folder (`~/.claude/skills/`, `~/.codex/skills/`,
   `~/.cursor/skills/`, `~/.config/opencode/skills/`, `~/.agents/skills/`). It
   refuses unknown tool names before writing anything, backs up an existing skill
   before replacing it, and `--dry-run` lists every path first. Run it with
   `--dry-run` before the first real install.
2. **Skill content steers a model.** The skills are instructions an agent will
   follow with your credentials in scope. Read a `SKILL.md` before installing it
   from a fork. That applies to every skill pack, this one included.
3. **Text you feed the gate.** Files are read and reported on, never executed.
   Markdown is escaped in the HTML preview, and isolates (U+2066/U+2069) are kept
   out of tags — there is a test for that.

If you find a way to make the installer write outside its documented targets, or
to make the preview emit executable markup, that is a security issue and I want
the report.
