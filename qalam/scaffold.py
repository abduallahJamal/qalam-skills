"""Scaffold a new, spec-compliant skill folder.

The generated skill is deliberately boring: valid frontmatter, a description
written for auto-invocation, a short body, a references file the body links to
only when needed, and a test that the frontmatter stays valid. Boring is the
point — skills rot when they start as a big Markdown dump.
"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import List, Tuple

TEMPLATE = """---
name: {name}
description: {description}
license: MIT
metadata:
  qalam.version: "1.0"
  qalam.kind: procedure
---

# {title}

## When to use this

{when}

Do not use this skill {not_when}.

## Procedure

1. **Confirm the inputs.** {first_step}
2. **Do the work.** {second_step}
3. **Verify before you report.** {third_step}

## Output contract

State exactly what you produced, where you wrote it, and what you did not verify.
If you could not complete a step, say which step and why — a partial result that
is honestly labelled is worth more than a confident one that hides a gap.

## References

Load only what this task needs:

- `references/checklist.md` — the checks to run before you call the work done.
"""

CHECKLIST = """# Checklist

- [ ] Inputs confirmed with the user, not assumed
- [ ] Result verified against the input, not just produced
- [ ] Nothing silently dropped
- [ ] Limitations stated explicitly
"""

TEST_TEMPLATE = '''"""Keep the generated skill loadable by every host."""

from pathlib import Path

SKILL = Path(__file__).resolve().parents[1] / "SKILL.md"


def test_frontmatter_is_portable():
    text = SKILL.read_text(encoding="utf-8")
    assert text.startswith("---\\n"), "SKILL.md must begin with YAML frontmatter"
    frontmatter = text.split("---", 2)[1]
    assert "name: {name}" in frontmatter
    assert "description:" in frontmatter
    assert len(frontmatter) < 1500, "frontmatter stays small; hosts read it every session"
'''


@dataclass
class ScaffoldResult:
    directory: Path
    files: List[Path]


def _title(name: str) -> str:
    return " ".join(part.capitalize() for part in name.split("-"))


def scaffold(
    name: str,
    description: str,
    root: Path,
    when: str = "",
    not_when: str = "",
    first_step: str = "list what you have and what is missing",
    second_step: str = "work through the steps in order, writing real files",
    third_step: str = "re-read the result against the input and fix what differs",
    with_test: bool = True,
    force: bool = False,
) -> ScaffoldResult:
    if not re.fullmatch(r"[a-z0-9]+(-[a-z0-9]+)*", name):
        raise ValueError(
            "skill name must be lowercase words joined by hyphens, e.g. `review-pr`"
        )
    directory = root / name
    if directory.exists() and any(directory.iterdir()) and not force:
        raise FileExistsError(f"{directory} already exists; pass --force to overwrite")

    title = _title(name)
    body = TEMPLATE.format(
        name=name,
        description=" ".join(description.split()),
        title=title,
        when=when or f"the user asks for {title.lower()} work.",
        not_when=not_when or "for unrelated requests",
        first_step=first_step,
        second_step=second_step,
        third_step=third_step,
    )
    (directory / "references").mkdir(parents=True, exist_ok=True)
    files: List[Path] = []
    skill_path = directory / "SKILL.md"
    skill_path.write_text(body, encoding="utf-8", newline="\n")
    files.append(skill_path)
    checklist = directory / "references" / "checklist.md"
    checklist.write_text(CHECKLIST, encoding="utf-8", newline="\n")
    files.append(checklist)
    if with_test:
        tests = directory / "tests"
        tests.mkdir(exist_ok=True)
        test_path = tests / f"test_{name.replace('-', '_')}_contract.py"
        test_path.write_text(TEST_TEMPLATE.format(name=name), encoding="utf-8", newline="\n")
        files.append(test_path)
    return ScaffoldResult(directory=directory, files=files)


def portable_frontmatter(name: str, description: str, license_text: str = "MIT") -> str:
    """Frontmatter limited to the spec fields, for pasting into any SKILL.md."""
    return (
        "---\n"
        f"name: {name}\n"
        f"description: {' '.join(description.split())}\n"
        f"license: {license_text}\n"
        "---\n"
    )
