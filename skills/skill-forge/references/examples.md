# Annotated examples

## Good: a procedure skill

```markdown
---
name: changelog-entry
description: Write a changelog entry from a git range, grouping commits by user
  impact and stripping internal noise. Use when asked to update CHANGELOG.md, cut
  a release, or summarise what changed since a tag.
license: MIT
---

# Changelog entry

You write the entry a user reads, not the entry a developer would want.

## Procedure

1. `git log --oneline <last-tag>..HEAD` and read every commit.
2. Drop: merge commits, version bumps, CI tweaks, and anything that changes no
   user-visible behaviour.
3. Group the rest under Added / Changed / Fixed / Removed.
4. Write each line as a user-visible effect, not an implementation detail.
5. Insert above the previous version section. Do not renumber old versions.

## Failure modes

| Symptom | Fix |
| --- | --- |
| Entry reads like a commit message | Rewrite as impact |
| More than 12 lines | Group similar items |

## Report

State the range used, the number of commits dropped, and the file path.
```

Why it works: the description names objects (CHANGELOG.md, git range, release)
and triggers. The body has a contract in one line, five executable steps, a
failure table, and a report contract.

## Bad: a skill that cannot load

```markdown
## My helper

Use this when you need help with code.
```

Three defects: no frontmatter at all, a description that matches everything, and
no procedure.

## Bad: a skill that loads and then wastes the model's time

```markdown
---
name: review-code
description: Reviews code thoroughly and carefully, ensuring high quality.
---

Please carefully review the code. Check for bugs, security issues, performance
problems, and style. Be thorough and comprehensive. Make sure the code is good.
```

No criteria, no output shape, no failure handling. The model will produce a
generic list. Contrast with a review skill that states: the file scope, the four
categories, a severity taxonomy, a finding format, and a "do not report" list.

## Good: frontmatter that stays portable

```yaml
---
name: pdf-invoice
description: Extract line items, totals, and tax from PDF invoices into CSV,
  flagging any invoice whose totals do not reconcile. Use when asked to process
  invoices, extract figures from a PDF bill, or reconcile a batch of invoices.
license: MIT
compatibility: Python 3.9+; pdftotext (poppler) or pymupdf
metadata:
  owner: finance-tools
  version: "1.2"
---
```

No host-specific fields, so the same folder loads everywhere. The runtime needs
are stated in `compatibility`, which is where a reader looks.

## Good: a script-backed skill

```markdown
## Verify

```bash
python "$SKILL_DIR/scripts/reconcile.py" out.csv --strict
```

`--strict` exits 1 when any invoice's line items do not sum to its total. If it
exits non-zero, report the failing invoice numbers — do not "fix" them by
adjusting the total.
```

The last sentence is the important one: it tells the model that a failing check
is information, not an obstacle to route around.

## Description length sweep

| Length | Effect |
| --- | --- |
| < 40 chars | Hosts list it, models rarely match it |
| 150–350 chars | Sweet spot: specific and scannable |
| > 700 chars | Truncated in listings; the tail never influences matching |
| > 1024 chars | Rejected by strict hosts |

Put the highest-signal nouns in the first 160 characters: that is what most
listing UIs actually show.
