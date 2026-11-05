"""Cognitive Reload with Trinity: one profile lifecycle across both skills (spec §10)."""
from __future__ import annotations

import subprocess
import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from test_held import install_skills  # noqa: E402
from test_writer import ADL, NS, MachineTest  # noqa: E402

COMBINED = HERE.parents[1] / "cognitive-reload-with-trinity" / "SKILL.md"


class CombinedTest(MachineTest):
    def setUp(self):
        super().setUp()
        self.skills = install_skills(self.tmp / "skills")
        self.machine.profile = self.skills / "proficiency-profile" / "scripts" / "profile.py"
        self.machine.create()

    def hook(self, skill: str, *args: str) -> subprocess.CompletedProcess:
        script = self.skills / skill / "scripts" / "profile_hook.py"
        result = subprocess.run([sys.executable, str(script), "run", *args], capture_output=True,
                                text=True, env=self.machine.env(), cwd=self.machine.repo)
        if result.returncode:
            raise AssertionError(f"{skill} hook {args}: {result.stdout}{result.stderr}")
        return result

    def reload(self, *args):
        return self.hook("cognitive-reload", *args)

    def trinity(self, *args):
        return self.hook("trinity-helicopter-program", *args)

    def evidence_commits(self) -> list[str]:
        return [c for c in self.machine.commits() if c.startswith("Evidence:")]


class OneLifecycle(CombinedTest):
    def test_a_combined_session_makes_one_start_one_end_and_one_commit(self):
        m = self.machine
        self.reload("session-start", "--harness", "claude-code", "--repo", str(m.repo))
        self.trinity("record", "experienced", "--lang", "csharp-dotnet", "--concept", "types.record")
        self.trinity("record", "drill", "--lang", "csharp-dotnet", "--concept", "types.record",
                     "--grade", "good")
        self.reload("record", "teachback", "--lang", "csharp-dotnet", "--concepts", "cqrs", "--score", "4")
        end = self.reload("session-end")
        self.assertEqual(end.stdout.strip(), "Profile: 4 lines recorded, kept on this machine only.")
        self.assertEqual(self.evidence_commits(), ["Evidence: 4 lines (2026-11-05)"])
        self.assertEqual(
            [line["verb"]["id"].rsplit("/", 1)[1] for line in m.lines()],
            ["use", "experienced", "practiced", "passed"],
        )
        self.assertEqual(m.lines()[3]["object"]["id"], NS + "concepts/arch/cqrs")
        self.assertEqual(m.lines()[1]["verb"]["id"], ADL + "experienced")

    def test_a_second_session_start_joins_the_running_session(self):
        m = self.machine
        self.reload("session-start", "--harness", "claude-code", "--repo", str(m.repo))
        self.trinity("record", "experienced", "--lang", "csharp-dotnet", "--concept", "types.record")
        again = self.trinity("session-start", "--harness", "claude-code", "--repo", str(m.repo))
        self.assertEqual(again.stdout.strip(), "profile: local-only")
        self.trinity("record", "experienced", "--lang", "csharp-dotnet", "--concept", "lang.var")
        self.reload("session-end")
        self.assertEqual(self.evidence_commits(), ["Evidence: 3 lines (2026-11-05)"])
        late = self.trinity("session-end")
        self.assertEqual(late.stdout.strip(), "Profile: no session in progress.")
        self.assertEqual(len(self.evidence_commits()), 1)

    def test_a_session_left_from_another_day_is_still_recovered(self):
        m = self.machine
        self.reload("session-start", "--harness", "claude-code", "--repo", str(m.repo))
        self.trinity("record", "experienced", "--lang", "csharp-dotnet", "--concept", "types.record")
        m.today = "2026-11-06"
        self.reload("session-start", "--harness", "claude-code", "--repo", str(m.repo))
        self.assertEqual(self.evidence_commits(), ["Evidence: 2 lines (recovered)"])

    def test_a_session_in_another_repo_is_not_joined(self):
        m = self.machine
        self.reload("session-start", "--harness", "claude-code", "--repo", str(m.repo))
        self.trinity("record", "experienced", "--lang", "csharp-dotnet", "--concept", "types.record")
        other = m.work_repo("other", "https://github.com/example-team/other.git")
        self.reload("session-start", "--harness", "claude-code", "--repo", str(other))
        self.assertEqual(self.evidence_commits(), ["Evidence: 2 lines (recovered)"])


class TheCombinedSkill(unittest.TestCase):
    def setUp(self):
        self.text = COMBINED.read_text()

    def test_runs_one_session_start_and_one_session_end(self):
        self.assertEqual(self.text.count("profile_hook.py run session-start"), 1)
        self.assertEqual(self.text.count("profile_hook.py run session-end"), 1)
        self.assertIn("Skip the `session-start` and `session-end` steps in both skills", self.text)

    def test_asks_the_profile_question_once_in_the_combined_orientation(self):
        self.assertIn("profile question", self.text)
        self.assertIn("same message as cognitive-reload's orientation invitation", self.text)

    def test_routes_drills_through_trinity_and_teachbacks_through_cognitive_reload(self):
        self.assertIn("Drills record through trinity's hook", self.text)
        self.assertIn("teach-backs through cognitive-reload's", self.text)
        self.assertNotIn("results go only to the trinity ledger", self.text)


if __name__ == "__main__":
    unittest.main()
