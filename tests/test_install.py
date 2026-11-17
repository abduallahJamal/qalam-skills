"""Tests for skill installation.

Installation is the one part of the pack that writes outside the repo, so these
tests run entirely inside temporary directories and never touch a real
``~/.claude`` or ``~/.codex``.
"""

from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from qalam.install import (
    TOOL_PATHS,
    InstallError,
    discover_skills,
    doctor,
    install_many,
    install_skill,
    installed_skills,
    resolve_target,
    summary,
    uninstall_skill,
    write_cursor_rule,
)

SKILL = """---
name: {name}
description: A test skill long enough to pass the description check in validation.
---

# {name}

Body text for the test skill, enough characters to be plausible in a real pack.
"""


class Fixture(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.skills = self.root / "skills"
        for name in ("alpha", "beta"):
            directory = self.skills / name
            directory.mkdir(parents=True)
            (directory / "SKILL.md").write_text(SKILL.format(name=name), encoding="utf-8")
            (directory / "references").mkdir()
            (directory / "references" / "notes.md").write_text("notes", encoding="utf-8")

        self.home = self.root / "home"
        self.home.mkdir()
        self.project = self.root / "project"
        self.project.mkdir()
        self._cwd = os.getcwd()
        os.chdir(self.project)
        # start() is what actually applies the patch; forgetting it silently
        # writes to the developer's real home directory.
        # Windows resolves Path.home() from USERPROFILE, POSIX from HOME, so both
        # are redirected; patching only HOME leaves Windows pointed at the real
        # user directory.
        self._env = mock.patch.dict(
            os.environ,
            {"HOME": str(self.home), "USERPROFILE": str(self.home)},
        )
        self._env.start()

    def tearDown(self):
        os.chdir(self._cwd)
        self._env.stop()
        self.temp.cleanup()


class DiscoveryTests(Fixture):
    def test_discover_finds_both_skills(self):
        found = sorted(path.name for path in discover_skills(self.skills))
        self.assertEqual(found, ["alpha", "beta"])

    def test_discover_fails_on_empty_root(self):
        empty = self.root / "empty"
        empty.mkdir()
        with self.assertRaises(InstallError):
            discover_skills(empty)

    def test_every_tool_has_both_scopes(self):
        for tool, scopes in TOOL_PATHS.items():
            self.assertIn("user", scopes, tool)
            self.assertIn("project", scopes, tool)

    def test_unknown_tool_is_rejected(self):
        with self.assertRaises(InstallError):
            resolve_target("vim", "user")

    def test_bad_scope_is_rejected(self):
        with self.assertRaises(InstallError):
            resolve_target("claude", "global")


class InstallTests(Fixture):
    def test_project_copy_install(self):
        action = install_skill(self.skills / "alpha", "claude", "project", mode="copy")
        self.assertEqual(action.mode, "copy")
        target = Path(".claude/skills/alpha")
        self.assertTrue((target / "SKILL.md").exists())
        self.assertTrue((target / "references" / "notes.md").exists())

    def test_second_install_without_force_is_a_conflict(self):
        install_skill(self.skills / "alpha", "claude", "project", mode="copy")
        action = install_skill(self.skills / "alpha", "claude", "project", mode="copy")
        self.assertEqual(action.mode, "conflict")

    def test_force_replaces_and_keeps_a_backup(self):
        install_skill(self.skills / "alpha", "claude", "project", mode="copy")
        marker = Path(".claude/skills/alpha/LOCAL_EDIT")
        marker.write_text("hand edited", encoding="utf-8")
        action = install_skill(
            self.skills / "alpha", "claude", "project", mode="copy", force=True
        )
        self.assertEqual(action.mode, "copy")
        self.assertFalse(marker.exists())
        backups = list(Path(".claude/skills/.qalam-backups").rglob("LOCAL_EDIT"))
        self.assertEqual(len(backups), 1)

    def test_dry_run_writes_nothing(self):
        action = install_skill(self.skills / "alpha", "codex", "project", dry_run=True)
        self.assertEqual(action.mode, "link")
        self.assertFalse(Path(".codex/skills").exists())

    def test_link_mode_installs_all_selected_tools(self):
        actions = install_many(
            self.skills, ["claude", "codex", "cursor", "opencode"], scope="project", mode="copy"
        )
        counts = summary(actions)
        self.assertEqual(counts.get("copy"), 8)   # 2 skills x 4 tools
        for tool in ("claude", "codex", "cursor", "opencode"):
            self.assertTrue(Path(TOOL_PATHS[tool]["project"], "alpha", "SKILL.md").exists())

    def test_installed_skills_reports_copies(self):
        install_skill(self.skills / "alpha", "claude", "project", mode="copy")
        found = installed_skills("claude", "project")
        self.assertEqual(len(found), 1)
        self.assertEqual(found[0][0], "alpha")

    def test_uninstall_removes_only_the_named_skill(self):
        install_many(self.skills, ["claude"], scope="project", mode="copy")
        actions = uninstall_skill(["alpha"], "claude", "project")
        self.assertEqual(actions[0].mode, "remove")
        self.assertFalse(Path(".claude/skills/alpha").exists())
        self.assertTrue(Path(".claude/skills/beta/SKILL.md").exists())

    def test_uninstall_missing_skill_is_a_noop(self):
        actions = uninstall_skill(["nope"], "claude", "project")
        self.assertEqual(actions[0].mode, "skip")

    def test_cursor_rule_is_written(self):
        path = write_cursor_rule(Path.cwd())
        self.assertTrue(path.exists())
        text = path.read_text(encoding="utf-8")
        self.assertTrue(text.startswith("---"))
        self.assertIn("alwaysApply", text)

    def test_doctor_reports_missing_before_install(self):
        rows = doctor(self.skills)
        statuses = {status for _tool, _scope, status in rows}
        self.assertIn("not installed", statuses)

    def test_doctor_reports_all_installed_after_install(self):
        for tool in TOOL_PATHS:
            install_many(self.skills, [tool], scope="project", mode="copy")
        rows = doctor(self.skills)
        for tool, scope, status in rows:
            if scope == "project":
                self.assertIn("installed", status, f"{tool}/{scope}: {status}")


class SafetyTests(Fixture):
    def test_home_is_isolated_per_test(self):
        """Guard: if the HOME patch ever stops applying, fail loudly here."""
        # resolve() on both sides: Windows may hand back an 8.3 short path
        # (ABDUAL~1) for temp dirs, which is the same directory, not a leak.
        self.assertEqual(Path.home().resolve(), self.home.resolve())

    def test_install_never_writes_outside_the_target(self):
        install_skill(self.skills / "alpha", "opencode", "user", mode="copy")
        target = self.home / ".config" / "opencode" / "skills" / "alpha"
        self.assertTrue(target.exists())
        self.assertFalse((self.home / ".claude").exists())

    def test_unknown_tool_raises_before_writing(self):
        with self.assertRaises(InstallError):
            install_skill(self.skills / "alpha", "emacs", "user")


if __name__ == "__main__":
    unittest.main()
