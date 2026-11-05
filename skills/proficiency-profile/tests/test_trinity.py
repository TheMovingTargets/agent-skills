"""Trinity Helicopter Program's hooks into the profile (spec §10), through its profile_hook.py."""
from __future__ import annotations

import json
import re
import shutil
import subprocess
import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from test_held import install_skills  # noqa: E402
from test_writer import ADL, NS, MachineTest  # noqa: E402

TRINITY = HERE.parents[1] / "trinity-helicopter-program"


class TrinityTest(MachineTest):
    def setUp(self):
        super().setUp()
        self.skills = install_skills(self.tmp / "skills")
        m = self.machine
        m.profile = self.skills / "proficiency-profile" / "scripts" / "profile.py"
        self.hook_path = self.skills / "trinity-helicopter-program" / "scripts" / "profile_hook.py"
        self.ledger_path = self.skills / "trinity-helicopter-program" / "scripts" / "ledger.py"

    def call(self, script: Path, *args: str, check: bool = True) -> subprocess.CompletedProcess:
        env = {**self.machine.env(), "TRINITY_LEARNER": "octo-learner"}
        result = subprocess.run([sys.executable, str(script), *args], capture_output=True, text=True,
                                env=env, cwd=self.machine.repo)
        if check and result.returncode:
            raise AssertionError(f"{script.name} {args}: {result.stdout}{result.stderr}")
        return result

    def hook(self, *args: str, check: bool = True):
        return self.call(self.hook_path, *args, check=check)

    def ledger(self, *args: str):
        return self.call(self.ledger_path, *args)

    def drill(self, concept: str, grade: str = "good", lang: str = "csharp-dotnet"):
        self.hook("run", "record", "drill", "--lang", lang, "--concept", concept, "--grade", grade)


class AScriptedTrinitySession(TrinityTest):
    def test_records_the_expected_lines(self):
        m = self.machine
        m.create()
        start = self.hook("run", "session-start", "--harness", "claude-code", "--repo", str(m.repo))
        self.assertEqual(start.stdout.strip(), "profile: local-only")
        # A card, weeds to rung 2, a skip and a fly drill, as SKILL.md maps them.
        self.hook("run", "record", "experienced", "--lang", "csharp-dotnet", "--concept", "types.record")
        self.hook("run", "record", "interacted", "--lang", "csharp-dotnet", "--concept", "types.record")
        self.ledger("mark", "--lang", "csharp-dotnet", "lang.var", "known")
        self.drill("types.record", "hard")
        end = self.hook("run", "session-end")
        self.assertEqual(end.stdout.strip(), "Profile: 4 lines recorded, kept on this machine only.")
        self.assertEqual(
            [(line["verb"]["id"], line["object"]["id"].removeprefix(NS)) for line in m.lines()],
            [("http://activitystrea.ms/schema/1.0/use", "harnesses/claude-code"),
             (ADL + "experienced", "concepts/csharp-dotnet/types.record"),
             (ADL + "interacted", "concepts/csharp-dotnet/types.record"),
             (NS + "verbs/practiced", "concepts/csharp-dotnet/types.record")],
        )

    def test_skill_md_names_every_hook(self):
        text = (TRINITY / "SKILL.md").read_text()
        for command in (
            "profile_hook.py run session-start --harness",
            "profile_hook.py run record experienced --lang",
            "profile_hook.py run record interacted --lang",
            "profile_hook.py run record drill --lang",
            "profile_hook.py run session-end",
            "profile_hook.py triage --lang",
            "profile_hook.py bridges --lang",
            "profile_hook.py refresh --lang",
        ):
            self.assertIn(command, text)
        self.assertRegex(text, re.compile(r"`skip`[^\n]*ledger only", re.I))


class Triage(TrinityTest):
    def seed(self):
        """Proven and Current, Practiced and Lapsed, Introduced, and ledger-only Concepts."""
        m = self.machine
        m.create()
        m.today = "2026-09-01"
        self.hook("run", "session-start", "--harness", "claude-code", "--repo", str(m.repo))
        self.drill("types.record", "hard")
        self.drill("lang.var")
        self.hook("run", "session-end")
        m.today = "2026-10-20"
        self.hook("run", "session-start", "--harness", "claude-code", "--repo", str(m.repo))
        self.drill("async.valuetask")
        self.hook("run", "session-end")
        m.today = "2026-10-27"
        self.hook("run", "session-start", "--harness", "claude-code", "--repo", str(m.repo))
        self.drill("async.valuetask")
        self.hook("run", "record", "experienced", "--lang", "csharp-dotnet", "--concept", "lang.patterns")
        self.hook("run", "session-end")
        m.today = "2026-11-05"
        self.ledger("mark", "--lang", "csharp-dotnet", "proj.csproj", "known")
        self.ledger("mark", "--lang", "csharp-dotnet", "lang.var", "fluent")

    def test_uses_the_stronger_of_the_ledger_and_the_profile(self):
        self.seed()
        result = json.loads(self.hook(
            "triage", "--lang", "csharp-dotnet", "--concepts",
            "async.valuetask,types.record,lang.patterns,proj.csproj,lang.var,linq.deferred").stdout)
        self.assertEqual(result, {
            "async.valuetask": "silence",    # Proven and Current in the profile
            "types.record": "refresher",     # Practiced, Lapsed
            "lang.patterns": "triage",       # only Introduced
            "proj.csproj": "silence",        # ledger: known
            "lang.var": "silence",           # ledger: fluent beats Lapsed in the profile
            "linq.deferred": "triage",       # never met
        })

    def test_refresh_offers_the_top_due_concept(self):
        self.seed()
        self.assertEqual(self.hook("refresh", "--lang", "csharp-dotnet").stdout.strip(), "types.record")

    def test_no_refresh_when_nothing_is_due(self):
        self.machine.create()
        self.assertEqual(self.hook("refresh", "--lang", "csharp-dotnet").stdout, "")


class BridgeLanguages(TrinityTest):
    def test_languages_with_practiced_or_proven_concepts_become_bridges(self):
        pack = self.skills / "trinity-helicopter-program" / "references" / "languages" / "rust.md"
        pack.write_text("# Language pack: Rust\n\n| id | concept |\n|---|---|\n"
                        "| `own.borrow` | Borrowing |\n| `own.move` | Moves |\n")
        m = self.machine
        m.create()
        self.hook("run", "session-start", "--harness", "claude-code", "--repo", str(m.repo))
        self.drill("own.borrow", "hard", lang="rust")
        self.hook("run", "record", "experienced", "--lang", "csharp-dotnet", "--concept", "types.record")
        self.hook("run", "session-end")
        self.assertEqual(json.loads(self.hook("bridges", "--lang", "csharp-dotnet").stdout), ["rust"])
        self.assertEqual(json.loads(self.hook("bridges", "--lang", "rust").stdout), [])


class WithoutTheProfileSkill(TrinityTest):
    def setUp(self):
        super().setUp()
        shutil.rmtree(self.skills / "proficiency-profile")

    def test_trinity_works_as_today_and_says_so_once(self):
        m = self.machine
        start = self.hook("run", "session-start", "--harness", "claude-code", "--repo", str(m.repo))
        self.assertEqual((start.returncode, start.stdout.strip()),
                         (0, "proficiency-profile not found: nothing is recorded this session."))
        record = self.hook("run", "record", "experienced", "--lang", "csharp-dotnet",
                           "--concept", "types.record")
        self.assertEqual((record.returncode, record.stdout, record.stderr), (0, "", ""))
        self.assertEqual(self.hook("run", "session-end").stdout, "")
        self.ledger("mark", "--lang", "csharp-dotnet", "types.record", "known")
        self.assertEqual(json.loads(self.hook("triage", "--lang", "csharp-dotnet",
                                              "--concepts", "types.record,lang.var").stdout),
                         {"types.record": "silence", "lang.var": "triage"})
        self.assertEqual(json.loads(self.hook("bridges", "--lang", "csharp-dotnet").stdout), [])


if __name__ == "__main__":
    unittest.main()
