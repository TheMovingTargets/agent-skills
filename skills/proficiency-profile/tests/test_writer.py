"""Tests for the profile.py writer, driven through its command line.

Each test gets its own XDG folders, HOME and global git config, and pins
"today" with PROFICIENCY_PROFILE_TODAY, so nothing touches the real machine.
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
PROFILE = HERE.parent / "scripts" / "profile.py"
NS = "https://w3id.org/xapi/devprof/"
ADL = "http://adlnet.gov/expapi/verbs/"
ACTOR = {
    "objectType": "Agent",
    "account": {"homePage": "https://github.com", "name": "octo-learner"},
}
DIMENSION = NS + "extensions/dimension"


def language_context(*categories: str) -> dict:
    return {
        "contextActivities": {"category": [{"id": NS + c} for c in categories]},
        "extensions": {DIMENSION: "language"},
    }


USE_CLAUDE_CODE = {
    "actor": ACTOR,
    "verb": {"id": "http://activitystrea.ms/schema/1.0/use"},
    "object": {"objectType": "Activity", "id": NS + "harnesses/claude-code"},
    "result": {"success": True, "score": {"scaled": 1.0}},
    "context": {"extensions": {DIMENSION: "harness"}},
    "timestamp": "2026-11-05T00:00:00Z",
}


class Machine:
    """One developer machine: its own XDG folders, HOME, git config and repo."""

    def __init__(self, root: Path, today: str = "2026-11-05"):
        self.root = root
        self.today = today
        self.home = root / "home"
        self.home.mkdir(parents=True, exist_ok=True)
        self.gitconfig = root / "gitconfig"
        self.gitconfig.write_text("", encoding="utf-8")
        self.clone = root / "data" / "proficiency-profile"
        self.state = root / "state" / "proficiency-profile"
        self.config = root / "config" / "proficiency-profile"
        self.repo = self.work_repo("work", "https://github.com/example-team/app.git")

    def env(self) -> dict[str, str]:
        env = {
            key: value
            for key, value in os.environ.items()
            if not key.startswith(("GIT_", "XDG_", "CODEX_"))
        }
        env.update(
            HOME=str(self.home),
            XDG_DATA_HOME=str(self.root / "data"),
            XDG_STATE_HOME=str(self.root / "state"),
            XDG_CONFIG_HOME=str(self.root / "config"),
            GIT_CONFIG_GLOBAL=str(self.gitconfig),
            GIT_CONFIG_NOSYSTEM="1",
            PROFICIENCY_PROFILE_TODAY=self.today,
        )
        return env

    def work_repo(self, name: str, remote: str | None) -> Path:
        repo = self.root / name
        repo.mkdir()
        self.git(repo, "init", "-q")
        if remote:
            self.git(repo, "remote", "add", "origin", remote)
        return repo

    def git(self, repo: Path, *args: str) -> str:
        return subprocess.run(
            ["git", "-C", str(repo), *args],
            capture_output=True, text=True, check=True, env=self.env(),
        ).stdout

    def run(self, *args: str, check: bool = True) -> subprocess.CompletedProcess:
        result = subprocess.run(
            [sys.executable, str(PROFILE), *args],
            capture_output=True, text=True, env=self.env(), cwd=self.root,
        )
        if check and result.returncode != 0:
            raise AssertionError(
                f"profile.py {' '.join(args)} exited {result.returncode}:\n"
                f"{result.stdout}{result.stderr}"
            )
        return result

    def create(self) -> None:
        self.run("create", "--host", "github.com", "--login", "octo-learner")

    def start(self, harness: str = "claude-code", repo: Path | None = None):
        return self.run("session-start", "--harness", harness, "--repo", str(repo or self.repo))

    def lines(self) -> list[dict]:
        """Every Evidence line in the clone, in file order."""
        out = []
        for path in sorted((self.clone / "evidence").rglob("*.jsonl")):
            out += [json.loads(line) for line in path.read_text().splitlines()]
        return out

    def commits(self) -> list[str]:
        return self.git(self.clone, "log", "--format=%s").splitlines()


def without_id(statement: dict) -> dict:
    return {key: value for key, value in statement.items() if key != "id"}


class MachineTest(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tmp)
        self.machine = Machine(self.tmp / "machine")


class AScriptedSession(MachineTest):
    def test_records_valid_statements_and_makes_one_commit(self):
        m = self.machine
        m.create()
        m.start()
        m.run("record", "experienced", "--lang", "csharp-dotnet", "--concept", "types.record")
        m.run("record", "drill", "--lang", "csharp-dotnet", "--concept", "async.valuetask",
              "--grade", "good", "--area", "backend")
        m.run("record", "teachback", "--lang", "csharp-dotnet",
              "--concepts", "cqrs,lang.patterns", "--score", "3.5")
        end = m.run("session-end")

        self.assertEqual(
            [without_id(line) for line in m.lines()],
            [
                USE_CLAUDE_CODE,
                {
                    "actor": ACTOR,
                    "verb": {"id": ADL + "experienced"},
                    "object": {"objectType": "Activity",
                               "id": NS + "concepts/csharp-dotnet/types.record"},
                    "context": language_context("languages/csharp-dotnet"),
                    "timestamp": "2026-11-05T00:00:00Z",
                },
                {
                    "actor": ACTOR,
                    "verb": {"id": NS + "verbs/practiced"},
                    "object": {"objectType": "Activity",
                               "id": NS + "concepts/csharp-dotnet/async.valuetask"},
                    "result": {"success": True, "score": {"scaled": 1.0}},
                    "context": language_context("languages/csharp-dotnet", "areas/backend"),
                    "timestamp": "2026-11-05T00:00:00Z",
                },
                {
                    "actor": ACTOR,
                    "verb": {"id": ADL + "passed"},
                    "object": {"objectType": "Activity", "id": NS + "concepts/arch/cqrs"},
                    "result": {"success": True, "score": {"scaled": 0.7}},
                    "context": language_context("languages/csharp-dotnet"),
                    "timestamp": "2026-11-05T00:00:00Z",
                },
                {
                    "actor": ACTOR,
                    "verb": {"id": ADL + "passed"},
                    "object": {"objectType": "Activity",
                               "id": NS + "concepts/csharp-dotnet/lang.patterns"},
                    "result": {"success": True, "score": {"scaled": 0.7}},
                    "context": language_context("languages/csharp-dotnet"),
                    "timestamp": "2026-11-05T00:00:00Z",
                },
            ],
        )
        self.assertEqual(m.commits(), ["Evidence: 5 lines (2026-11-05)", "Profile: created"])
        self.assertEqual(end.stdout.strip(), "Profile: 5 lines recorded, kept on this machine only.")


class OnceADay(MachineTest):
    def test_use_line_is_written_once_per_harness_per_day(self):
        m = self.machine
        m.create()
        m.start()
        m.run("session-end")
        m.start()
        m.start(harness="codex")
        m.run("session-end")
        harnesses = [line["object"]["id"] for line in m.lines()]
        self.assertEqual(harnesses, [NS + "harnesses/claude-code", NS + "harnesses/codex"])

    def test_use_line_is_written_again_the_next_day(self):
        m = self.machine
        m.create()
        m.start()
        m.run("session-end")
        m.today = "2026-11-06"
        m.start()
        self.assertEqual(
            [line["timestamp"] for line in m.lines()],
            ["2026-11-05T00:00:00Z", "2026-11-06T00:00:00Z"],
        )

    def test_interacted_is_written_once_per_concept_per_day(self):
        m = self.machine
        m.create()
        m.start()
        for concept in ("types.record", "types.record", "lang.patterns", "types.record"):
            m.run("record", "interacted", "--lang", "csharp-dotnet", "--concept", concept)
        interacted = [line["object"]["id"].rsplit("/", 1)[1]
                      for line in m.lines() if line["verb"]["id"] == ADL + "interacted"]
        self.assertEqual(interacted, ["types.record", "lang.patterns"])

    def test_every_drill_attempt_is_written(self):
        m = self.machine
        m.create()
        m.start()
        for grade in ("again", "hard", "good"):
            m.run("record", "drill", "--lang", "csharp-dotnet", "--concept", "types.record",
                  "--grade", grade)
        drills = [line["result"] for line in m.lines() if line["verb"]["id"] == NS + "verbs/practiced"]
        self.assertEqual(drills, [
            {"success": False, "score": {"scaled": 0.0}},
            {"success": True, "score": {"scaled": 0.5}},
            {"success": True, "score": {"scaled": 1.0}},
        ])


class Rounding(MachineTest):
    def test_commit_dates_are_midnight_utc(self):
        m = self.machine
        m.create()
        m.start()
        m.run("session-end")
        dates = m.git(m.clone, "log", "--format=%aI %cI").splitlines()
        self.assertEqual(dates, ["2026-11-05T00:00:00Z 2026-11-05T00:00:00Z"] * 2)

    def test_commits_run_with_hooks_off(self):
        hooks = self.tmp / "hooks"
        hooks.mkdir()
        for name in ("pre-commit", "commit-msg", "post-commit"):
            hook = hooks / name
            hook.write_text("#!/bin/sh\necho hook ran >> " + str(self.tmp / "hook-log") + "\nexit 1\n")
            hook.chmod(0o755)
        m = self.machine
        m.gitconfig.write_text(f"[core]\n\thooksPath = {hooks}\n")
        m.create()
        m.start()
        m.run("session-end")
        self.assertEqual(m.commits(), ["Evidence: 1 lines (2026-11-05)", "Profile: created"])
        self.assertFalse((self.tmp / "hook-log").exists())

    def test_teachback_score_bands(self):
        m = self.machine
        m.create()
        m.start()
        m.run("record", "teachback", "--lang", "csharp-dotnet", "--concepts", "cqrs", "--score", "2.9")
        m.run("record", "teachback", "--lang", "csharp-dotnet", "--concepts", "rpc", "--score", "3")
        results = [(line["verb"]["id"].rsplit("/", 1)[1], line["result"]) for line in m.lines()[1:]]
        self.assertEqual(results, [
            ("failed", {"success": False, "score": {"scaled": 0.58}}),
            ("passed", {"success": True, "score": {"scaled": 0.6}}),
        ])


class Locking(MachineTest):
    def test_concurrent_records_append_complete_lines(self):
        m = self.machine
        m.create()
        m.start()
        cmd = [sys.executable, str(PROFILE), "record", "experienced",
               "--lang", "csharp-dotnet", "--concept", "types.record"]
        procs = [subprocess.Popen(cmd, env=m.env(), cwd=m.root) for _ in range(12)]
        self.assertEqual([p.wait() for p in procs], [0] * 12)
        lines = m.lines()  # every line parses as JSON
        self.assertEqual(len(lines), 13)
        self.assertEqual(len({line["id"] for line in lines}), 13)
        self.assertEqual(m.run("session-end").stdout.strip(),
                         "Profile: 13 lines recorded, kept on this machine only.")


class OffTheRecord(MachineTest):
    def test_discards_the_sessions_lines_and_stops_recording(self):
        m = self.machine
        m.create()
        m.start()
        m.run("session-end")
        m.start(harness="codex")
        m.run("record", "experienced", "--lang", "csharp-dotnet", "--concept", "types.record")
        m.run("off-the-record")
        m.run("record", "experienced", "--lang", "csharp-dotnet", "--concept", "lang.var")
        end = m.run("session-end")
        self.assertEqual([line["object"]["id"] for line in m.lines()],
                         [NS + "harnesses/claude-code"])
        self.assertEqual(end.stdout.strip(),
                         "Profile: off the record, nothing recorded this session.")
        self.assertEqual(m.commits(), ["Evidence: 1 lines (2026-11-05)", "Profile: created"])
        self.assertEqual(m.git(m.clone, "status", "--porcelain"), "")

    def test_next_session_records_again(self):
        m = self.machine
        m.create()
        m.start()
        m.run("off-the-record")
        m.run("session-end")
        m.start()
        m.run("session-end")
        self.assertEqual(len(m.lines()), 1)


class ExcludedRepos(MachineTest):
    def test_excluding_a_repo_discards_the_session_and_stores_only_a_hash(self):
        m = self.machine
        m.create()
        m.start()
        m.run("record", "experienced", "--lang", "csharp-dotnet", "--concept", "types.record")
        m.run("exclude-repo", "--repo", str(m.repo))
        m.run("record", "experienced", "--lang", "csharp-dotnet", "--concept", "lang.var")
        self.assertEqual(m.run("session-end").stdout.strip(),
                         "Profile: not recorded, this repo is excluded.")
        self.assertEqual(m.lines(), [])
        stored = (m.config / "excluded-repos").read_text()
        self.assertRegex(stored, r"^[0-9a-f]{64}\n$")
        self.assertNotIn("example", stored)

    def test_session_start_stops_at_once_in_an_excluded_repo(self):
        m = self.machine
        m.create()
        m.run("exclude-repo", "--repo", str(m.repo))
        self.assertEqual(m.start().stdout.strip(), "profile: excluded")
        m.run("record", "experienced", "--lang", "csharp-dotnet", "--concept", "types.record")
        m.run("session-end")
        self.assertEqual(m.lines(), [])

    def test_the_same_remote_in_another_clone_is_excluded_too(self):
        m = self.machine
        m.create()
        m.run("exclude-repo", "--repo", str(m.repo))
        for name, remote in (("ssh", "git@github.com:example-team/app.git"),
                             ("https", "https://user@GitHub.com/example-team/app/")):
            other = m.work_repo(name, remote)
            self.assertEqual(m.start(repo=other).stdout.strip(), "profile: excluded")

    def test_other_repos_still_record(self):
        m = self.machine
        m.create()
        m.run("exclude-repo", "--repo", str(m.repo))
        other = m.work_repo("other", "https://github.com/example-team/other.git")
        self.assertEqual(m.start(repo=other).stdout.strip(), "profile: local-only")
        self.assertEqual(len(m.lines()), 1)


class Recovery(MachineTest):
    def test_lines_left_by_an_unfinished_session_are_committed_as_recovered(self):
        m = self.machine
        m.create()
        m.start()
        m.run("record", "experienced", "--lang", "csharp-dotnet", "--concept", "types.record")
        # No session-end: the harness was closed.
        m.today = "2026-11-07"
        m.start()
        self.assertEqual(m.commits(), ["Evidence: 2 lines (recovered)", "Profile: created"])
        recovered_date = m.git(m.clone, "log", "-1", "--format=%aI").strip()
        self.assertEqual(recovered_date, "2026-11-05T00:00:00Z")
        self.assertEqual(m.run("session-end").stdout.strip(),
                         "Profile: 1 lines recorded, kept on this machine only.")
        self.assertEqual(m.commits()[0], "Evidence: 1 lines (2026-11-07)")


class VocabularyCheck(MachineTest):
    def test_unknown_ids_are_rejected(self):
        m = self.machine
        m.create()
        m.start()
        for args in (
            ["experienced", "--lang", "csharp-dotnet", "--concept", "types.made-up"],
            ["experienced", "--lang", "cobol", "--concept", "types.record"],
            ["drill", "--lang", "csharp-dotnet", "--concept", "types.record",
             "--grade", "good", "--area", "gamedev"],
            ["experienced", "--lang", "csharp-dotnet", "--concept", "cqrs"],
        ):
            result = m.run("record", *args, check=False)
            self.assertEqual(result.returncode, 3, args)
            self.assertIn("not recorded", result.stderr)
        self.assertEqual(len(m.lines()), 1)

    def test_teachback_records_known_concepts_and_rejects_unknown_ones(self):
        m = self.machine
        m.create()
        m.start()
        result = m.run("record", "teachback", "--lang", "csharp-dotnet",
                       "--concepts", "cqrs,our-internal-bus", "--score", "4", check=False)
        self.assertEqual(result.returncode, 3)
        self.assertEqual([line["object"]["id"] for line in m.lines()[1:]],
                         [NS + "concepts/arch/cqrs"])

    def test_unknown_harness_is_rejected(self):
        m = self.machine
        m.create()
        result = m.run("session-start", "--harness", "notepad", "--repo", str(m.repo), check=False)
        self.assertEqual(result.returncode, 3)
        self.assertEqual(m.lines(), [])


class Voids(MachineTest):
    def test_a_void_refers_to_the_line_and_goes_in_the_current_file(self):
        m = self.machine
        m.create()
        m.start()
        m.run("record", "experienced", "--lang", "csharp-dotnet", "--concept", "types.record")
        m.run("session-end")
        wrong = m.lines()[1]["id"]
        m.today = "2026-12-02"
        m.start()
        m.run("void", wrong)
        m.run("session-end")
        void = m.lines()[-1]
        self.assertEqual(without_id(void), {
            "actor": ACTOR,
            "verb": {"id": ADL + "voided"},
            "object": {"objectType": "StatementRef", "id": wrong},
            "timestamp": "2026-12-02T00:00:00Z",
        })
        self.assertEqual(len(list((m.clone / "evidence" / "2026" / "12").glob("*.jsonl"))), 1)

    def test_lines_lists_the_sessions_lines_to_pick_a_void_from(self):
        m = self.machine
        m.create()
        m.start()
        m.run("record", "experienced", "--lang", "csharp-dotnet", "--concept", "types.record")
        ids = [line["id"] for line in m.lines()]
        self.assertEqual(m.run("lines").stdout.splitlines(), [
            f"{ids[0]} use harnesses/claude-code",
            f"{ids[1]} experienced concepts/csharp-dotnet/types.record",
        ])

    def test_voiding_an_unknown_id_is_refused(self):
        m = self.machine
        m.create()
        m.start()
        result = m.run("void", "8d0c0000-0000-4000-8000-000000000000", check=False)
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(len(m.lines()), 1)


class WithoutAProfile(MachineTest):
    def test_nothing_is_recorded_before_the_profile_is_created(self):
        m = self.machine
        self.assertEqual(m.start().stdout.strip(), "profile: none")
        m.run("record", "experienced", "--lang", "csharp-dotnet", "--concept", "types.record")
        self.assertEqual(m.run("session-end").stdout, "")
        self.assertFalse(m.clone.exists())

    def test_creating_mid_session_writes_the_days_use_line(self):
        m = self.machine
        m.start()
        m.create()
        m.run("record", "experienced", "--lang", "csharp-dotnet", "--concept", "types.record")
        m.run("session-end")
        self.assertEqual(len(m.lines()), 2)
        self.assertEqual(sorted(p.name for p in m.clone.iterdir() if p.name != ".git"),
                         ["README.md", "evidence", "profile.json"])

    def test_a_decline_is_remembered(self):
        m = self.machine
        m.start()
        m.run("decline")
        m.run("session-end")
        self.assertEqual(m.start().stdout.strip(), "profile: declined")
        m.create()
        self.assertEqual(m.start().stdout.strip(), "profile: local-only")

    def test_the_profile_names_no_repository_or_host(self):
        m = self.machine
        m.create()
        m.start()
        m.run("record", "teachback", "--lang", "csharp-dotnet", "--concepts", "cqrs", "--score", "4")
        m.run("session-end")
        files = [p for p in m.clone.rglob("*") if p.is_file() and ".git" not in p.parts]
        text = "".join(p.read_text() for p in files)
        for leak in ("example-team", "app.git", "work", str(m.root)):
            self.assertNotIn(leak, text)


if __name__ == "__main__":
    unittest.main()
