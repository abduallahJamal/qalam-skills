---
name: Bug report
about: Something produces the wrong result, crashes, or silently drops content
title: "bug: "
labels: ["bug"]
---

## What happened

<!-- The actual output. Paste it, do not describe it. -->

## What you expected

## Reproduce

```bash
# exact commands, in order
```

Input file, if it is small enough to paste. If it contains private text, reduce it
to the smallest fragment that still reproduces the problem.

## Environment

| | |
| :--- | :--- |
| Qalam version (`python3 -m qalam --version`) | |
| Python version | |
| OS | |
| Host agent (Claude Code / Codex / Cursor / OpenCode / terminal) | |

## Did you check the obvious

- [ ] `python3 -m unittest discover -s tests -t .` is green on a clean checkout
- [ ] This is not the gate reporting a real defect in my own file
- [ ] I looked for an existing issue with the same output
