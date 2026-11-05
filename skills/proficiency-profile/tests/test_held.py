"""Held Evidence: hold, check, propose and release (spec §4).

Each test runs an installed copy of the skills, so a test can add a row or an
alias line to a Vocabulary the way a merged Vocabulary PR would.
"""
from __future__ import annotations

import json
import shutil
import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from test_remote import RemoteTest  # noqa: E402
from test_writer import NS  # noqa: E402

SKILLS = HERE.parents[1]
REF = "concept:csharp-dotnet/types.made-up"


def install_skills(target: Path) -> Path:
    ignore = shutil.ignore_patterns("tests", "__pycache__")
    for name in ("proficiency-profile", "trinity-helicopter-program", "cognitive-reload"):
        shutil.copytree(SKILLS / name, target / name, ignore=ignore)
    return target


class HeldTest(RemoteTest):
    def setUp(self):
        super().setUp()
        self.skills = install_skills(self.tmp / "skills")
        self.machine.profile = self.skills / "proficiency-profile" / "scripts" / "profile.py"
        self.machine.signed_in = False  # keep debriefs free of the remote offer
        self.machine.create()

    def pack(self) -> Path:
        return self.skills / "trinity-helicopter-program" / "references" / "languages" / "csharp-dotnet.md"

    def install_row(self, text: str) -> None:
        with open(self.pack(), "a", encoding="utf-8") as handle:
            handle.write(text)

    def held(self) -> list[dict]:
        return json.loads(self.machine.run("held", "list").stdout)

    def record_made_up(self):
        self.machine.run("record", "experienced", "--lang", "csharp-dotnet", "--concept", "types.made-up")


class Hold(HeldTest):
    def test_an_unknown_concept_is_held_off_the_profile_and_listed_at_the_debrief(self):
        m = self.machine
        m.start()
        self.assertEqual(m.run("record", "experienced", "--lang", "csharp-dotnet",
                               "--concept", "types.made-up").returncode, 0)
        m.run("record", "experienced", "--lang", "csharp-dotnet", "--concept", "types.record")
        end = m.run("session-end").stdout.strip()
        self.assertEqual(end, "Profile: 2 lines recorded, kept on this machine only. "
                              "Held back, not in the profile yet: Concept `types.made-up` in csharp-dotnet "
                              "(1 line). Check each names a public technology or pattern, "
                              "not something from this repo's own code.")
        self.assertEqual([line["object"]["id"].rsplit("/", 1)[1] for line in m.lines()],
                         ["claude-code", "types.record"])
        self.assertEqual(self.held(), [{"ref": REF, "lines": 1, "status": "unchecked"}])
        self.assertNotIn("types.made-up", m.git(m.clone, "log", "-p"))

    def test_teachback_areas_and_languages_are_held_too(self):
        m = self.machine
        m.start()
        m.run("record", "teachback", "--lang", "csharp-dotnet", "--concepts", "cqrs,saga-pattern",
              "--score", "4", "--area", "gamedev")
        m.run("record", "experienced", "--lang", "cobol", "--concept", "data.picture")
        self.assertEqual([h["ref"] for h in self.held()], [
            "area:gamedev", "concept:arch/saga-pattern", "concept:cobol/data.picture", "language:cobol",
        ])
        self.assertEqual(len(m.lines()), 1)

    def test_an_unknown_harness_holds_the_use_line_and_the_session_still_starts(self):
        m = self.machine
        self.assertEqual(m.start(harness="new-harness").stdout.strip(), "profile: local-only")
        self.assertEqual(m.lines(), [])
        self.assertEqual([h["ref"] for h in self.held()], ["harness:new-harness"])

    def test_off_the_record_drops_the_sessions_held_lines(self):
        m = self.machine
        m.start()
        self.record_made_up()
        m.run("off-the-record")
        self.assertEqual(self.held(), [])


class Check(HeldTest):
    def test_a_failed_check_discards_the_held_lines(self):
        m = self.machine
        m.start()
        self.record_made_up()
        self.record_made_up()
        m.run("session-end")
        self.assertEqual(m.run("held", "discard", REF).stdout.strip(),
                         "Profile: dropped 2 held lines for Concept `types.made-up` in csharp-dotnet.")
        self.install_row("| `types.made-up` | Made up | — | — |\n")
        m.today = "2026-11-06"
        m.start()
        self.assertEqual(self.held(), [])
        self.assertFalse(any("types.made-up" in line["object"]["id"] for line in m.lines()))

    def test_checked_ids_are_not_listed_again(self):
        m = self.machine
        m.start()
        self.record_made_up()
        m.run("held", "confirm", REF)
        self.assertEqual(m.run("session-end").stdout.strip(),
                         "Profile: 1 lines recorded, kept on this machine only.")


class Propose(HeldTest):
    def test_confirming_drafts_a_pack_row(self):
        m = self.machine
        m.start()
        self.record_made_up()
        draft = json.loads(m.run("held", "confirm", REF).stdout)
        self.assertEqual(draft["file"], "skills/trinity-helicopter-program/references/languages/csharp-dotnet.md")
        self.assertEqual(draft["row"], "| `types.made-up` | <concept> | <nearest analog> | <trap> |")
        self.assertEqual(draft["title"], "Vocabulary: add Concept `types.made-up` to csharp-dotnet")
        self.assertEqual(self.held()[0]["status"], "proposed")

    def test_drafts_for_architecture_areas_harnesses_and_languages(self):
        m = self.machine
        m.start(harness="new-harness")
        m.run("record", "teachback", "--lang", "cobol", "--concepts", "saga-pattern", "--score", "4",
              "--area", "gamedev")
        drafts = {ref: json.loads(m.run("held", "confirm", ref).stdout)
                  for ref in ("concept:arch/saga-pattern", "area:gamedev", "harness:new-harness",
                              "language:cobol")}
        self.assertEqual(drafts["concept:arch/saga-pattern"]["file"],
                         "skills/cognitive-reload/references/architecture-concepts.md")
        self.assertEqual(drafts["concept:arch/saga-pattern"]["row"],
                         "| `saga-pattern` | <concept> | <typical signs in code> |")
        self.assertEqual(drafts["area:gamedev"]["row"], "| `gamedev` | <area> | <covers> |")
        self.assertEqual(drafts["harness:new-harness"]["file"],
                         "skills/proficiency-profile/references/harnesses.md")
        self.assertEqual(drafts["language:cobol"]["file"],
                         "skills/trinity-helicopter-program/references/languages/cobol.md")

    def test_an_unknown_ref_is_refused(self):
        result = self.machine.run("held", "confirm", "concept:csharp-dotnet/nope", check=False)
        self.assertNotEqual(result.returncode, 0)


class Release(HeldTest):
    def test_lines_are_released_once_their_id_is_installed(self):
        m = self.machine
        m.start()
        self.record_made_up()
        m.run("held", "confirm", REF)
        m.run("session-end")
        self.install_row("| `types.made-up` | Made up | — | — |\n")
        m.start()
        self.assertEqual(self.held(), [])
        released = [line for line in m.lines() if line["object"]["id"].endswith("types.made-up")]
        self.assertEqual(len(released), 1)
        self.assertEqual(released[0]["object"]["id"], NS + "concepts/csharp-dotnet/types.made-up")
        self.assertEqual(m.run("session-end").stdout.strip(),
                         "Profile: 1 lines recorded, kept on this machine only.")

    def test_aliased_ids_are_rewritten_to_their_target(self):
        m = self.machine
        m.start()
        self.record_made_up()
        m.run("session-end")
        self.install_row("\n`types.made-up → types.record`\n")
        m.start()
        released = m.lines()[-1]
        self.assertEqual(released["object"]["id"], NS + "concepts/csharp-dotnet/types.record")

    def test_a_backdated_line_goes_in_the_file_for_its_own_month(self):
        m = self.machine
        m.today = "2026-10-30"
        m.start()
        self.record_made_up()
        m.run("session-end")
        self.install_row("| `types.made-up` | Made up | — | — |\n")
        m.today = "2026-11-05"
        m.start()
        october = list((m.clone / "evidence" / "2026" / "10").glob("*.jsonl"))
        self.assertEqual(len(october), 1)
        lines = [json.loads(l) for l in october[0].read_text().splitlines()]
        released = [l for l in lines if l["object"]["id"].endswith("types.made-up")]
        self.assertEqual([l["timestamp"] for l in released], ["2026-10-30T00:00:00Z"])

    def test_a_rejected_proposal_drops_its_lines(self):
        m = self.machine
        m.signed_in = True
        m.start()
        self.record_made_up()
        m.run("held", "confirm", REF)
        m.run("held", "pr", REF, "https://github.com/TheMovingTargets/agent-skills/pull/999")
        m.run("session-end")
        for state, still_held in (("OPEN", 1), ("MERGED", 1), ("CLOSED", 0)):
            m.env_overrides = {"FAKE_PR_STATE": state}
            m.start()
            m.run("session-end")
            self.assertEqual(len(self.held()), still_held, state)

    def test_lines_stay_held_while_the_id_is_unknown(self):
        m = self.machine
        m.start()
        self.record_made_up()
        m.run("session-end")
        m.start()
        self.assertEqual(len(self.held()), 1)


if __name__ == "__main__":
    unittest.main()
