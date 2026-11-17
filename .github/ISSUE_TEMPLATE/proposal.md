---
name: Skill or gate check proposal
about: A new skill, or a new check in the quality gate
title: "proposal: "
labels: ["enhancement"]
---

## What procedure or defect does this cover

<!-- One paragraph. If it is "a prompt I like", say so and it will be closed with
that reason — see CONTRIBUTING.md for what a skill needs to justify its place. -->

## Could this be computed instead

<!-- If the step is deterministic, it belongs in qalam/ as a function plus a CLI
subcommand, not in a prompt. Say which one you think this is. -->

## For a new gate check

| | |
| :--- | :--- |
| What it catches | |
| Severity (error / warning / info) | |
| False positives you can already name | |
| Where it would live in `qalam/qa.py` | |

## For a new skill

| | |
| :--- | :--- |
| Trigger sentences a user would actually type | |
| Governing rule (what "done" means) | |
| Which existing skill is closest, and why this is not a duplicate | |
| References it needs | |
