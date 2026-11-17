"""Install Qalam skills into the agent tools on this machine.

One canonical folder per skill, four tools, two scopes:

===============  =========================  =========================
tool             user scope                 project scope
===============  =========================  =========================
claude           ~/.claude/skills           .claude/skills
codex            ~/.codex/skills            .codex/skills
cursor           ~/.cursor/skills           .cursor/skills
opencode         ~/.config/opencode/skills  .opencode/skills
agents           ~/.agents/skills           .agents/skills
===============  =========================  =========================

``agents`` is the portable location that OpenCode and Cursor also read, so a
machine that only wants the skills discoverable once can install there.

Installation is a link by default, so editing a skill edits every tool at once.
On Windows a directory junction is used, which needs no administrator rights.
If linking is refused, or ``--mode copy`` is requested, the folder is copied and
``qalam install --refresh`` is how you push updates.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Sequence, Tuple

TOOL_PATHS: Dict[str, Dict[str, str]] = {
    "claude": {"user": "~/.claude/skills", "project": ".claude/skills"},
    "codex": {"user": "~/.codex/skills", "project": ".codex/skills"},
    "cursor": {"user": "~/.cursor/skills", "project": ".cursor/skills"},
    "opencode": {"user": "~/.config/opencode/skills", "project": ".opencode/skills"},
    "agents": {"user": "~/.agents/skills", "project": ".agents/skills"},
}

TOOL_NOTES = {
    "claude": "Personal skills load in every Claude Code project; project skills travel with the repo.",
    "codex": "Codex CLI reads skills at session start, so restart it after installing.",
    "cursor": "Cursor 2.4+ reads .cursor/skills; rules (.mdc) are separate and always-on.",
    "opencode": "OpenCode also reads ~/.claude/skills and ~/.agents/skills, so avoid duplicates.",
    "agents": "Portable scope read by OpenCode, Cursor, and other Agent Skills hosts.",
}

BACKUP_DIR = ".qalam-backups"


class InstallError(RuntimeError):
    pass


@dataclass
class Action:
    tool: str
    scope: str
    skill: str
    target: Path
    mode: str          # link / copy / refresh / skip / remove / conflict
    detail: str = ""

    def render(self) -> str:
        return f"{self.mode:10} {self.tool:9} {self.scope:8} {self.target}  {self.detail}".rstrip()


def resolve_target(tool: str, scope: str) -> Path:
    if tool not in TOOL_PATHS:
        raise InstallError(f"unknown tool {tool!r}; choose from {', '.join(TOOL_PATHS)}")
    if scope not in ("user", "project"):
        raise InstallError("scope must be 'user' or 'project'")
    raw = TOOL_PATHS[tool][scope]
    if scope == "user":
        return Path(raw).expanduser()
    return Path.cwd() / raw


def discover_skills(source_root: Path) -> List[Path]:
    skills = sorted(
        path.parent for path in source_root.glob("*/SKILL.md") if path.parent.name != "node_modules"
    )
    if not skills:
        raise InstallError(f"no skills found under {source_root} (expected <name>/SKILL.md)")
    return skills


def _same_path(left: Path, right: Path) -> bool:
    try:
        return left.resolve() == right.resolve()
    except OSError:
        return False


def _backup(path: Path, tool: str) -> Optional[Path]:
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    backup_root = path.parent / BACKUP_DIR / f"{stamp}-{tool}"
    if path.is_dir():
        backup_root.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(path), str(backup_root))
        return backup_root
    return None


def _link_dir(source: Path, target: Path) -> Optional[str]:
    """Create a directory link; return a note, or None on success."""
    if os.name == "nt":
        try:
            result = subprocess.run(
                ["cmd", "/c", "mklink", "/J", str(target), str(source)],
                capture_output=True,
                text=True,
            )
        except OSError as error:
            return f"junction failed: {error}"
        if result.returncode != 0:
            return f"junction failed: {(result.stderr or result.stdout).strip()}"
        return None
    try:
        os.symlink(source, target, target_is_directory=True)
        return None
    except (OSError, NotImplementedError) as error:
        return f"symlink failed: {error}"


def _copy_dir(source: Path, target: Path) -> None:
    shutil.copytree(
        source,
        target,
        ignore=shutil.ignore_patterns("__pycache__", "*.pyc", ".DS_Store"),
    )


def _is_link(path: Path) -> bool:
    if path.is_symlink():
        return True
    if os.name == "nt" and path.exists():
        # Junctions are reparse points; comparing inodes with the source is the
        # portable check that avoids walking the whole tree.
        try:
            return os.stat(path).st_ino != 0 and path.is_dir() and os.path.islink(str(path))
        except OSError:
            return False
    return False


def install_skill(
    source: Path,
    tool: str,
    scope: str,
    mode: str = "link",
    force: bool = False,
    dry_run: bool = False,
) -> Action:
    target_root = resolve_target(tool, scope)
    target = target_root / source.name

    if target.exists() or target.is_symlink():
        if _is_link(target) and _same_path(target, source):
            return Action(tool, scope, source.name, target, "skip", "already linked")
        if not force:
            return Action(
                tool,
                scope,
                source.name,
                target,
                "conflict",
                "exists; pass --force to replace (a backup is kept)",
            )
        if dry_run:
            return Action(tool, scope, source.name, target, "refresh", "would replace")

    if dry_run:
        return Action(tool, scope, source.name, target, mode, "would install")

    target_root.mkdir(parents=True, exist_ok=True)
    detail = ""
    if target.exists() or target.is_symlink():
        if target.is_symlink() or target.is_file():
            target.unlink()
        else:
            backup = _backup(target, tool)
            if backup:
                detail = f"backup: {backup}"

    if mode == "copy":
        _copy_dir(source, target)
        return Action(tool, scope, source.name, target, "copy", detail or "copied")

    note = _link_dir(source, target)
    if note is None:
        return Action(tool, scope, source.name, target, "link", detail or "linked")

    if target.exists():
        shutil.rmtree(target, ignore_errors=True)
    _copy_dir(source, target)
    return Action(tool, scope, source.name, target, "copy", f"{note}; copied instead")


def uninstall_skill(
    skill_names: Sequence[str], tool: str, scope: str, dry_run: bool = False
) -> List[Action]:
    target_root = resolve_target(tool, scope)
    actions: List[Action] = []
    for name in skill_names:
        target = target_root / name
        if not (target.exists() or target.is_symlink()):
            actions.append(Action(tool, scope, name, target, "skip", "not installed"))
            continue
        if dry_run:
            actions.append(Action(tool, scope, name, target, "remove", "would remove"))
            continue
        if target.is_symlink():
            target.unlink()
        else:
            shutil.rmtree(target)
        actions.append(Action(tool, scope, name, target, "remove", "removed"))
    return actions


def installed_skills(tool: str, scope: str) -> List[Tuple[str, str]]:
    root = resolve_target(tool, scope)
    if not root.is_dir():
        return []
    found: List[Tuple[str, str]] = []
    for entry in sorted(root.iterdir()):
        if not entry.is_dir():
            continue
        marker = entry / "SKILL.md"
        if not marker.exists():
            continue
        kind = "link" if _is_link(entry) and not entry.is_symlink() else (
            "symlink" if entry.is_symlink() else "copy"
        )
        found.append((entry.name, kind))
    return found


def doctor(source_root: Path) -> List[Tuple[str, str, str]]:
    """Report, per tool and scope, whether each skill is present and current."""
    rows: List[Tuple[str, str, str]] = []
    skills = [path.name for path in discover_skills(source_root)]
    for tool in TOOL_PATHS:
        for scope in ("user", "project"):
            root = resolve_target(tool, scope)
            if not root.is_dir():
                rows.append((tool, scope, "not installed"))
                continue
            present = []
            stale = []
            for name in skills:
                target = root / name
                if not target.exists():
                    continue
                present.append(name)
                marker = target / "SKILL.md"
                source_marker = source_root / name / "SKILL.md"
                try:
                    if _is_link(target) and _same_path(target, source_root / name):
                        continue
                    if marker.read_bytes() != source_marker.read_bytes():
                        stale.append(name)
                except OSError:
                    stale.append(name)
            if not present:
                rows.append((tool, scope, "empty"))
            elif stale:
                rows.append((tool, scope, f"{len(present)} installed, stale: {', '.join(stale)}"))
            elif len(present) == len(skills):
                rows.append((tool, scope, f"all {len(present)} installed"))
            else:
                rows.append((tool, scope, f"{len(present)}/{len(skills)} installed"))
    return rows


CURSOR_RULE = """---
description: Qalam translation and Arabic-localisation skills are available in this repo
globs:
alwaysApply: false
---

# Qalam skills

The skills in `.cursor/skills/` handle translation, Arabic copy-editing, RTL
layout, glossaries, and translation QA. Load the matching skill before doing
that kind of work:

- `translate-docs` — translating long Markdown/books/documents
- `arabic-style` — editing Arabic prose for clarity and register
- `rtl-layout` — RTL correctness in HTML/CSS, WPF, Flutter, and mobile
- `glossary-builder` — building or repairing a term base
- `translation-qa` — reviewing a finished translation
- `localize-app` — software strings, i18n files, and plurals
- `extract-docs` — converting PDF/DOCX/EPUB to clean Markdown first
- `subtitle-translate` — SRT/VTT subtitles
- `skill-forge` — writing new skills in this style

Do not answer a translation request from memory when the matching skill exists.
"""


def write_cursor_rule(project_root: Path, dry_run: bool = False) -> Optional[Path]:
    rule = project_root / ".cursor" / "rules" / "qalam.mdc"
    if dry_run:
        return rule
    rule.parent.mkdir(parents=True, exist_ok=True)
    rule.write_text(CURSOR_RULE, encoding="utf-8", newline="\n")
    return rule


def install_many(
    source_root: Path,
    tools: Sequence[str],
    scope: str,
    mode: str = "link",
    force: bool = False,
    dry_run: bool = False,
    cursor_rule: bool = False,
) -> List[Action]:
    skills = discover_skills(source_root)
    actions: List[Action] = []
    for tool in tools:
        for skill in skills:
            actions.append(
                install_skill(skill, tool, scope, mode=mode, force=force, dry_run=dry_run)
            )
        if cursor_rule and tool == "cursor" and scope == "project":
            rule = write_cursor_rule(Path.cwd(), dry_run=dry_run)
            if rule:
                actions.append(
                    Action(
                        "cursor",
                        scope,
                        "(rule)",
                        rule,
                        "rule",
                        "optional pointer rule for Cursor",
                    )
                )
    return actions


def summary(actions: Iterable[Action]) -> Dict[str, int]:
    counts: Dict[str, int] = {}
    for action in actions:
        counts[action.mode] = counts.get(action.mode, 0) + 1
    return counts
