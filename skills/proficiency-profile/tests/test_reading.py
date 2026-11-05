"""`read`, `show` and the README the writer regenerates, through the command line."""
from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from test_writer import MachineTest  # noqa: E402


def drill(m, concept, grade="good"):
    m.run("record", "drill", "--lang", "csharp-dotnet", "--concept", concept, "--grade", grade)


class Reading(MachineTest):
    def two_weeks(self):
        m = self.machine
        m.create()
        m.today = "2026-11-02"
        m.start()
        drill(m, "async.valuetask")
        drill(m, "types.record", "hard")
        m.run("record", "experienced", "--lang", "csharp-dotnet", "--concept", "lang.var")
        m.run("session-end")
        m.today = "2026-11-09"
        m.start()
        drill(m, "async.valuetask")
        m.run("session-end")
        m.today = "2026-11-10"
        return m

    def test_session_end_commits_the_regenerated_readme_with_the_evidence(self):
        m = self.two_weeks()
        changed = m.git(m.clone, "show", "--name-only", "--format=", "HEAD").split()
        self.assertIn("README.md", changed)
        readme = (m.clone / "README.md").read_text()
        self.assertIn("| csharp-dotnet | 1 | 1 | 0 | 1 | 🟢 Current · 2026-11-09 |", readme)
        self.assertIn("Generated 2026-11-09 from 6 Evidence lines.", readme)
        self.assertIn("GitHub · octo-learner", readme)

    def test_show_prints_the_summary(self):
        m = self.two_weeks()
        shown = m.run("show").stdout
        self.assertTrue(shown.startswith("# Proficiency Profile\n\nGitHub · octo-learner\n\n## Summary"))
        self.assertIn("- **Solid:** async.valuetask", shown)
        self.assertNotIn("## Languages", shown)

    def test_read_gives_levels_and_currency_for_triage(self):
        m = self.two_weeks()
        result = json.loads(m.run("read", "--lang", "csharp-dotnet",
                                  "--concepts", "async.valuetask,types.record,lang.var,linq.deferred").stdout)
        self.assertEqual(result, {
            "model": "FSRS-6, default parameters, stability capped at 365 days",
            "language": "csharp-dotnet",
            "counts": {"Proven": 1, "Practiced": 1, "Explored": 0, "Introduced": 1},
            "band": "Current",
            "last_exercised": "2026-11-09",
            "concepts": {
                "async.valuetask": {"level": "Proven", "band": "Current", "last_exercised": "2026-11-09"},
                "types.record": {"level": "Practiced", "band": "Fading", "last_exercised": "2026-11-02"},
                "lang.var": {"level": "Introduced", "band": None, "last_exercised": None},
                "linq.deferred": {"level": None, "band": None, "last_exercised": None},
            },
            "due_for_refresh": ["types.record"],
        })

    def test_read_without_a_language_lists_every_language(self):
        m = self.two_weeks()
        result = json.loads(m.run("read").stdout)
        self.assertEqual(list(result["languages"]), ["csharp-dotnet"])
        self.assertEqual(result["languages"]["csharp-dotnet"]["counts"]["Proven"], 1)

    def test_without_a_profile_read_and_show_are_empty(self):
        m = self.machine
        self.assertEqual(json.loads(m.run("read", "--lang", "csharp-dotnet").stdout)["concepts"], {})
        self.assertEqual(m.run("show").stdout.strip(), "No Proficiency Profile on this machine.")


if __name__ == "__main__":
    unittest.main()
