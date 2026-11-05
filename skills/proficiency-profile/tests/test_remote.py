"""The remote Profile Repo, sync and Linked Identities.

Remotes are local bare git repos, and `gh`/`glab` are stubbed by
fakes/fake_cli.py, so no real repo is created and nothing leaves the machine.
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
sys.path.insert(0, str(HERE))
from test_writer import ACTOR, NS, Machine  # noqa: E402

FAKE = HERE / "fakes" / "fake_cli.py"
ADO_GUID = "9b1f2c3d-0000-4000-8000-00000000abcd"


class RemoteMachine(Machine):
    """A Machine whose gh and glab are the fake CLI, sharing one remotes folder."""

    def __init__(self, root: Path, remotes: Path, today: str = "2026-11-05"):
        self.remotes = remotes
        self.bin = root / "bin"
        self.bin.mkdir(parents=True)
        self.log = root / "cli-log"
        self.log.write_text("")
        self.signed_in = True
        super().__init__(root, today)
        for tool in ("gh", "glab"):
            wrapper = self.bin / tool
            wrapper.write_text(f'#!/bin/sh\nexec "{sys.executable}" "{FAKE}" {tool} "$@"\n')
            wrapper.chmod(0o755)

    def env(self) -> dict[str, str]:
        env = super().env()
        env.update(
            PATH=f"{self.bin}{os.pathsep}{env.get('PATH', '')}",
            FAKE_CLI_LOG=str(self.log),
            FAKE_REMOTES=str(self.remotes),
            FAKE_SIGNED_IN="1" if self.signed_in else "0",
            FAKE_LOGIN="octo-learner",
            FAKE_ID="1234",
        )
        return env

    def calls(self) -> list[list[str]]:
        return [json.loads(line) for line in self.log.read_text().splitlines()]

    def create_remote(self, host: str = "github.com"):
        return self.run("create", "--host", host, "--login", "octo-learner", "--remote")

    def bare(self) -> Path:
        return self.remotes / "octo-learner" / "proficiency-profile.git"

    def remote_log(self) -> list[str]:
        return self.git(self.bare(), "log", "--format=%s", "main").splitlines()

    def session(self, *records: str, harness: str = "claude-code", repo: Path | None = None):
        self.start(harness=harness, repo=repo)
        for concept in records:
            self.run("record", "experienced", "--lang", "csharp-dotnet", "--concept", concept)
        return self.run("session-end")


class RemoteTest(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tmp)
        self.remotes = self.tmp / "remotes"
        self.remotes.mkdir()
        self.machine = RemoteMachine(self.tmp / "laptop", self.remotes)

    def second_machine(self) -> RemoteMachine:
        return RemoteMachine(self.tmp / "desktop", self.remotes)


class Creation(RemoteTest):
    def test_creates_a_private_github_repo_and_pushes(self):
        m = self.machine
        self.assertEqual(m.create_remote().stdout.strip(), "profile: remote")
        self.assertIn(["gh", "repo", "create", "proficiency-profile", "--private"], m.calls())
        self.assertEqual(m.remote_log(), ["Profile: created"])
        self.assertEqual(m.git(m.clone, "config", "user.email").strip(),
                         "1234+octo-learner@users.noreply.github.com")
        profile = json.loads((m.clone / "profile.json").read_text())
        self.assertEqual(profile["home_provider"], "github")
        self.assertEqual(profile["identities"], [{"homePage": "https://github.com", "name": "octo-learner"}])

    def test_creates_a_private_gitlab_repo(self):
        m = self.machine
        m.create_remote("gitlab.com")
        self.assertIn(["glab", "repo", "create", "proficiency-profile", "--private", "--skipGitInit"],
                      m.calls())
        self.assertEqual(m.git(m.clone, "config", "user.email").strip(),
                         "1234-octo-learner@users.noreply.gitlab.com")
        self.assertEqual(m.remote_log(), ["Profile: created"])

    def test_not_signed_in_stays_local_and_never_runs_a_login(self):
        m = self.machine
        m.signed_in = False
        out = m.create_remote().stdout
        self.assertIn("profile: local-only", out)
        self.assertIn("gh auth login", out)
        self.assertFalse(any(call[1:2] == ["repo"] or call[1:3] == ["auth", "login"]
                             for call in m.calls()))
        self.assertTrue((m.clone / "profile.json").exists())

    def test_nothing_is_created_or_called_on_decline(self):
        m = self.machine
        m.start()
        m.run("decline")
        m.run("session-end")
        self.assertEqual(m.calls(), [])
        self.assertFalse(m.clone.exists())
        self.assertFalse(m.bare().exists())

    def test_a_second_machine_clones_the_existing_repo(self):
        self.machine.create_remote()
        self.machine.session("types.record")
        desktop = self.second_machine()
        self.assertEqual(desktop.create_remote().stdout.strip(), "profile: remote")
        self.assertNotIn(["gh", "repo", "create", "proficiency-profile", "--private"], desktop.calls())
        self.assertEqual(len(desktop.lines()), 2)
        self.assertEqual(desktop.git(desktop.clone, "config", "user.email").strip(),
                         "1234+octo-learner@users.noreply.github.com")


class Sync(RemoteTest):
    def test_session_commit_is_pushed_with_rounded_dates(self):
        m = self.machine
        m.create_remote()
        end = m.session("types.record")
        self.assertEqual(end.stdout.strip(), "Profile: 2 lines recorded and pushed.")
        self.assertEqual(m.remote_log(), ["Evidence: 2 lines (2026-11-05)", "Profile: created"])
        self.assertEqual(m.git(m.bare(), "log", "-1", "--format=%aI %cI", "main").strip(),
                         "2026-11-05T00:00:00Z 2026-11-05T00:00:00Z")

    def test_session_start_pulls_and_regenerates_the_readme(self):
        laptop = self.machine
        laptop.create_remote()
        desktop = self.second_machine()
        desktop.create_remote()
        laptop.session("types.record")
        desktop.start()
        # The laptop's use line already covers Claude Code today, so the desktop adds none.
        self.assertEqual(len(desktop.lines()), 2)
        # Regenerated right after the pull, before the desktop's own use line was written.
        self.assertIn("from 2 Evidence lines", (desktop.clone / "README.md").read_text())

    def test_rejected_push_rebases_and_retries_and_two_machines_merge_cleanly(self):
        laptop = self.machine
        laptop.create_remote()
        desktop = self.second_machine()
        desktop.create_remote()
        laptop.start()
        desktop.start()
        laptop.run("record", "experienced", "--lang", "csharp-dotnet", "--concept", "types.record")
        desktop.run("record", "experienced", "--lang", "csharp-dotnet", "--concept", "lang.var")
        laptop.run("session-end")
        end = desktop.run("session-end")  # rejected first: laptop pushed in between
        self.assertEqual(end.stdout.strip(), "Profile: 2 lines recorded and pushed.")
        self.assertEqual(laptop.remote_log(), [
            "Evidence: 2 lines (2026-11-05)",
            "Evidence: 2 lines (2026-11-05)",
            "Profile: created",
        ])
        files = laptop.git(laptop.bare(), "ls-tree", "-r", "--name-only", "main").split()
        self.assertEqual(len([f for f in files if f.startswith("evidence/2026/11/")]), 2)
        # The README was regenerated through the conflict, from both machines' lines.
        readme = laptop.git(laptop.bare(), "show", "main:README.md")
        self.assertIn("from 4 Evidence lines", readme)
        self.assertNotIn("<<<<<<<", readme)
        # Rebased commits keep their midnight dates, and nothing was force-pushed.
        dates = set(laptop.git(laptop.bare(), "log", "--format=%aI %cI", "main").splitlines())
        self.assertEqual(dates, {"2026-11-05T00:00:00Z 2026-11-05T00:00:00Z"})
        self.assertFalse(any("--force" in call or "-f" in call for call in desktop.calls()))

    def test_offline_skips_sync_quietly_and_says_so_once(self):
        m = self.machine
        m.create_remote()
        m.git(m.clone, "remote", "set-url", "origin", str(self.tmp / "unreachable.git"))
        start = m.start()
        self.assertEqual((start.returncode, start.stdout.strip(), start.stderr), (0, "profile: remote", ""))
        m.run("record", "experienced", "--lang", "csharp-dotnet", "--concept", "types.record")
        self.assertEqual(m.run("session-end").stdout.strip(),
                         "Profile: 2 lines recorded, kept on this machine until it can sync.")
        self.assertEqual(m.commits()[0], "Evidence: 2 lines (2026-11-05)")

    def test_sync_pushes_what_was_kept_offline(self):
        m = self.machine
        m.create_remote()
        url = m.git(m.clone, "remote", "get-url", "origin").strip()
        m.git(m.clone, "remote", "set-url", "origin", str(self.tmp / "unreachable.git"))
        m.session("types.record")
        m.git(m.clone, "remote", "set-url", "origin", url)
        self.assertEqual(m.run("sync").stdout.strip(), "Profile: synced.")
        self.assertEqual(m.remote_log()[0], "Evidence: 2 lines (2026-11-05)")


class LocalOnlyOffer(RemoteTest):
    def test_debrief_offers_a_remote_when_a_cli_is_signed_in(self):
        m = self.machine
        m.create()
        end = m.session("types.record").stdout.strip()
        self.assertEqual(end, "Profile: 2 lines recorded, kept on this machine only. "
                              "It can be backed up to a private GitHub repo: say \"add a remote\".")

    def test_no_offer_without_a_signed_in_cli(self):
        m = self.machine
        m.signed_in = False
        m.create()
        self.assertEqual(m.session("types.record").stdout.strip(),
                         "Profile: 2 lines recorded, kept on this machine only.")

    def test_add_remote_connects_a_local_only_profile(self):
        m = self.machine
        m.create()
        m.session("types.record")
        self.assertEqual(m.run("add-remote", "--host", "github.com").stdout.strip(), "profile: remote")
        self.assertEqual(m.remote_log(), ["Profile: Home Provider github",
                                          "Evidence: 2 lines (2026-11-05)", "Profile: created"])
        self.assertEqual(json.loads((m.clone / "profile.json").read_text())["home_provider"], "github")


class LinkedIdentities(RemoteTest):
    def profile(self) -> dict:
        return json.loads((self.machine.clone / "profile.json").read_text())

    def test_recording_rules(self):
        m = self.machine
        m.create()
        m.run("link", "--kind", "gitlab", "--name", "octo")
        m.run("link", "--kind", "azure-devops", "--name", ADO_GUID, "--display", "Octo Learner")
        m.run("link", "--kind", "github-enterprise", "--name", "olearner")
        m.run("link", "--kind", "gitlab-self-managed", "--name", "olearner")
        self.assertEqual(self.profile()["identities"], [
            {"homePage": "https://github.com", "name": "octo-learner"},
            {"homePage": "https://gitlab.com", "name": "octo"},
            {"homePage": "https://app.vssps.visualstudio.com", "name": ADO_GUID, "display": "Octo Learner"},
            {"homePage": "https://github-enterprise.invalid", "name": "olearner"},
            {"homePage": "https://gitlab-self-managed.invalid", "name": "olearner"},
        ])
        readme = (m.clone / "README.md").read_text()
        self.assertIn("Azure DevOps · Octo Learner", readme)
        self.assertNotIn(ADO_GUID, readme)

    def test_names_that_look_like_emails_hosts_or_orgs_are_refused(self):
        m = self.machine
        m.create()
        for kind, name in (("github", "octo@corp.example"), ("github-enterprise", "git.corp.example/octo"),
                           ("azure-devops", "octo@corp.example"), ("gitlab", "corp:octo")):
            result = m.run("link", "--kind", kind, "--name", name, check=False)
            self.assertNotEqual(result.returncode, 0, (kind, name))
        self.assertEqual(len(self.profile()["identities"]), 1)

    def test_linking_twice_keeps_one_entry(self):
        m = self.machine
        m.create()
        m.run("link", "--kind", "gitlab", "--name", "octo")
        m.run("link", "--kind", "gitlab", "--name", "octo")
        self.assertEqual(len(self.profile()["identities"]), 2)

    def test_actor_is_the_identity_matching_the_repo_host(self):
        m = self.machine
        m.create()
        m.run("link", "--kind", "azure-devops", "--name", ADO_GUID, "--display", "Octo Learner")
        ado_repo = m.work_repo("ado", "https://contoso@dev.azure.com/contoso/Proj/_git/svc")
        m.session("types.record", repo=ado_repo)
        accounts = {json.dumps(line["actor"]["account"]) for line in m.lines()}
        self.assertEqual(accounts, {json.dumps({"homePage": "https://app.vssps.visualstudio.com",
                                                "name": ADO_GUID})})

    def test_self_hosted_repos_use_the_self_hosted_identity(self):
        m = self.machine
        m.create()
        m.run("link", "--kind", "gitlab-self-managed", "--name", "olearner")
        repo = m.work_repo("self", "git@gitlab.corp.example:team/app.git")
        m.session(repo=repo)
        self.assertEqual(m.lines()[0]["actor"]["account"],
                         {"homePage": "https://gitlab-self-managed.invalid", "name": "olearner"})

    def test_unlinked_host_uses_the_creation_identity_and_offers_a_link_once(self):
        m = self.machine
        m.signed_in = False
        m.create()
        ado_repo = m.work_repo("ado", "https://dev.azure.com/contoso/Proj/_git/svc")
        first = m.session("types.record", repo=ado_repo).stdout.strip()
        self.assertEqual(m.lines()[0]["actor"], ACTOR)
        self.assertEqual(first, "Profile: 2 lines recorded, kept on this machine only. "
                                "Work here is under an Azure DevOps account that isn't linked: "
                                "say \"link my Azure DevOps account\" to count it as yours.")
        m.today = "2026-11-06"
        second = m.session(repo=ado_repo).stdout.strip()
        self.assertEqual(second, "Profile: 1 lines recorded, kept on this machine only.")

    def test_the_profile_records_no_organization_host_or_email(self):
        m = self.machine
        m.create_remote()
        m.run("link", "--kind", "azure-devops", "--name", ADO_GUID, "--display", "Octo Learner")
        m.run("link", "--kind", "github-enterprise", "--name", "olearner")
        ado_repo = m.work_repo("ado", "https://contoso@dev.azure.com/contoso/Proj/_git/svc")
        m.session("types.record", repo=ado_repo)
        files = m.git(m.bare(), "ls-tree", "-r", "--name-only", "main").split()
        text = "".join(m.git(m.bare(), "show", f"main:{f}") for f in files)
        for leak in ("contoso", "Proj", "corp", "dev.azure.com", "@", str(self.tmp)):
            self.assertNotIn(leak, text)


if __name__ == "__main__":
    unittest.main()
