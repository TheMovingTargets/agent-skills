"""Cognitive Reload's install-local.sh installs this skill alongside it."""
from __future__ import annotations

import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

SKILLS = Path(__file__).resolve().parents[2]
INSTALL = SKILLS / "cognitive-reload" / "install-local.sh"


class InstallLocal(unittest.TestCase):
    def setUp(self):
        self.repo = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.repo)

    def run_install(self, *args):
        return subprocess.run(["sh", str(INSTALL), str(self.repo), *args],
                              capture_output=True, text=True, check=True)

    def installed(self, parent: str) -> list[str]:
        folder = self.repo / parent
        return sorted(p.name for p in folder.iterdir()) if folder.exists() else []

    def test_installs_the_profile_skill_alongside_by_default(self):
        self.run_install("claude")
        self.assertEqual(self.installed(".claude/skills"),
                         ["cognitive-reload", "proficiency-profile"])
        self.assertTrue((self.repo / ".claude/skills/proficiency-profile/scripts/profile.py").is_file())

    def test_without_profile_installs_cognitive_reload_alone(self):
        self.run_install("codex", "--without-profile")
        self.assertEqual(self.installed(".agents/skills"), ["cognitive-reload"])

    def test_uninstall_removes_both(self):
        self.run_install()
        self.run_install("--uninstall")
        self.assertEqual(self.installed(".claude/skills") + self.installed(".agents/skills"), [])


if __name__ == "__main__":
    unittest.main()
