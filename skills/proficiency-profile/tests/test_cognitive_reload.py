"""Cognitive Reload's hooks into the profile (spec §10), through its profile_hook.py."""
from __future__ import annotations

import json
import shutil
import subprocess
import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from test_held import install_skills  # noqa: E402
from test_writer import ADL, NS, MachineTest  # noqa: E402

RELOAD = HERE.parents[1] / "cognitive-reload"


class ReloadTest(MachineTest):
    def setUp(self):
        super().setUp()
        self.skills = install_skills(self.tmp / "skills")
        self.machine.profile = self.skills / "proficiency-profile" / "scripts" / "profile.py"
        self.hook_path = self.skills / "cognitive-reload" / "scripts" / "profile_hook.py"

    def hook(self, *args: str) -> subprocess.CompletedProcess:
        result = subprocess.run([sys.executable, str(self.hook_path), *args], capture_output=True,
                                text=True, env=self.machine.env(), cwd=self.machine.repo)
        if result.returncode:
            raise AssertionError(f"profile_hook.py {args}: {result.stdout}{result.stderr}")
        return result

    def start(self):
        return self.hook("run", "session-start", "--harness", "claude-code", "--repo", str(self.machine.repo))

    def teachback(self, score: str, *concepts: str, area: str | None = None):
        args = ["run", "record", "teachback", "--lang", "csharp-dotnet", "--concepts", ",".join(concepts),
                "--score", score]
        self.hook(*args, *(["--area", area] if area else []))


class TeachBack(ReloadTest):
    def test_a_scored_teachback_records_passed_and_failed_lines_with_score_scaled(self):
        m = self.machine
        m.create()
        self.start()
        self.teachback("3.5", "dependency-injection", "repository-pattern", area="backend")
        self.teachback("2", "cqrs")
        end = self.hook("run", "session-end")
        self.assertEqual(end.stdout.strip(), "Profile: 4 lines recorded, kept on this machine only.")
        self.assertEqual(
            [(line["verb"]["id"].removeprefix(ADL), line["object"]["id"].removeprefix(NS), line["result"])
             for line in m.lines()[1:]],
            [("passed", "concepts/arch/dependency-injection", {"success": True, "score": {"scaled": 0.7}}),
             ("passed", "concepts/arch/repository-pattern", {"success": True, "score": {"scaled": 0.7}}),
             ("failed", "concepts/arch/cqrs", {"success": False, "score": {"scaled": 0.4}})],
        )
        self.assertEqual(m.lines()[1]["context"]["contextActivities"]["category"],
                         [{"id": NS + "languages/csharp-dotnet"}, {"id": NS + "areas/backend"}])

    def test_tutoring_records_nothing(self):
        m = self.machine
        m.create()
        self.start()
        self.hook("run", "session-end")
        self.assertEqual([line["verb"]["id"] for line in m.lines()],
                         ["http://activitystrea.ms/schema/1.0/use"])

    def test_skill_md_and_assessment_name_the_hooks(self):
        skill = (RELOAD / "SKILL.md").read_text()
        assessment = (RELOAD / "references" / "assessment.md").read_text()
        self.assertIn("profile_hook.py run session-start --harness", skill)
        self.assertIn("profile_hook.py run session-end", skill)
        self.assertIn("profile_hook.py pitch --lang", skill)
        self.assertIn("profile_hook.py run record teachback --lang", assessment)
        # session-end comes after the private checkpoint and before the publishing offer.
        pause = skill[skill.index("## Finish or pause"):]
        self.assertLess(pause.index("private checkpoint"), pause.index("session-end"))
        self.assertLess(pause.index("session-end"), pause.index("publishing"))


class Pitch(ReloadTest):
    def test_the_profile_pitches_architecture_explanations(self):
        m = self.machine
        m.create()
        m.today = "2026-08-01"
        self.start()
        self.teachback("3.4", "retry-backoff")              # Good once, then nothing: Lapsed by November
        self.hook("run", "session-end")
        m.today = "2026-10-20"
        self.start()
        self.teachback("4", "dependency-injection")
        self.hook("run", "session-end")
        m.today = "2026-10-27"
        self.start()
        self.teachback("3.6", "dependency-injection")       # Good again 7 days later: Proven
        self.hook("run", "session-end")
        m.today = "2026-11-05"
        pitch = json.loads(self.hook("pitch", "--lang", "csharp-dotnet", "--concepts",
                                     "dependency-injection,retry-backoff,caching").stdout)
        self.assertEqual(pitch, {"dependency-injection": "name", "retry-backoff": "refresher",
                                 "caching": "primer"})


class Standalone(ReloadTest):
    def setUp(self):
        super().setUp()
        shutil.rmtree(self.skills / "proficiency-profile")
        shutil.rmtree(self.skills / "trinity-helicopter-program")

    def test_works_as_today_without_the_profile_skill(self):
        start = self.start()
        self.assertEqual(start.stdout.strip(), "proficiency-profile not found: nothing is recorded this session.")
        teachback = self.hook("run", "record", "teachback", "--lang", "csharp-dotnet",
                              "--concepts", "cqrs", "--score", "4")
        self.assertEqual((teachback.stdout, teachback.stderr), ("", ""))
        self.assertEqual(self.hook("run", "session-end").stdout, "")
        self.assertEqual(json.loads(self.hook("pitch", "--lang", "csharp-dotnet", "--concepts", "cqrs").stdout),
                         {"cqrs": "primer"})
        self.assertFalse(self.machine.clone.exists())


if __name__ == "__main__":
    unittest.main()
