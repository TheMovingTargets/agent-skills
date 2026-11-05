"""Codex's sandbox: detection, the spool and its merge, the escalation offer and the snippet.

The sandbox is simulated: the CODEX_SANDBOX variables are set, and the clone,
its .git or the state folder is made read-only.
"""
from __future__ import annotations

import os
import stat
import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from test_remote import RemoteTest  # noqa: E402

BLOCKED = "PROFILE_WRITE_BLOCKED sandbox=codex"


def set_writable(root: Path, writable: bool) -> None:
    """chmod a tree read-only (or back), the way a sandbox denies writes."""
    paths = [root, *root.rglob("*")] if root.exists() else []
    for path in sorted(paths, key=lambda p: len(p.parts), reverse=not writable):
        if path.is_symlink():
            continue
        mode = path.stat().st_mode
        if writable:
            path.chmod(mode | stat.S_IWUSR)
        else:
            path.chmod(mode & ~(stat.S_IWUSR | stat.S_IWGRP | stat.S_IWOTH))


class CodexTest(RemoteTest):
    def setUp(self):
        super().setUp()
        m = self.machine
        m.signed_in = False
        self.tmpdir = self.tmp / "codex-tmp"
        self.tmpdir.mkdir()
        m.create()
        self.spool = self.tmpdir / "proficiency-profile-spool"
        self.locked_down: list[Path] = []
        self.addCleanup(self.open_up)

    def sandbox(self, *paths: Path, network: bool = False):
        """Enter the simulated sandbox: env vars set, the given folders read-only."""
        overrides = {"CODEX_SANDBOX": "seatbelt", "TMPDIR": str(self.tmpdir)}
        if not network:
            overrides["CODEX_SANDBOX_NETWORK_DISABLED"] = "1"
        self.machine.env_overrides = overrides
        for path in paths:
            set_writable(path, False)
            self.locked_down.append(path)

    def open_up(self):
        for path in self.locked_down:
            set_writable(path, True)
        self.locked_down = []
        self.machine.env_overrides = {"TMPDIR": str(self.tmpdir)}

    def default_sandbox(self):
        """Codex's workspace-write: neither the clone nor the state folder is writable."""
        m = self.machine
        m.run("session-start", "--harness", "codex", "--repo", str(m.repo))  # machine id, state dirs exist
        m.run("session-end")
        self.sandbox(m.clone, m.state)


class Detection(CodexTest):
    def test_a_read_only_clone_and_state_are_detected_and_offer_escalation_once(self):
        m = self.machine
        self.default_sandbox()
        start = m.start()
        self.assertEqual(start.returncode, 0)
        out = start.stdout.splitlines()
        self.assertEqual(out[0], "profile: local-only")
        self.assertEqual(out[1], f"{BLOCKED} spool={self.spool}")
        self.assertIn("Offer the developer one escalated rerun", out[2])
        record = m.run("record", "experienced", "--lang", "csharp-dotnet", "--concept", "types.record")
        self.assertEqual((record.returncode, record.stdout), (0, ""))

    def test_a_read_only_git_folder_alone_is_detected(self):
        m = self.machine
        self.default_sandbox()
        self.open_up()
        self.sandbox(m.clone / ".git")
        self.assertIn(BLOCKED, m.start().stdout)

    def test_permission_errors_are_detected_without_the_env_vars(self):
        m = self.machine
        self.default_sandbox()
        m.env_overrides = {"TMPDIR": str(self.tmpdir)}
        self.assertIn("PROFILE_WRITE_BLOCKED sandbox=unknown", m.start().stdout)


class Spool(CodexTest):
    def test_evidence_is_spooled_never_in_the_workspace_and_the_session_never_fails(self):
        m = self.machine
        self.default_sandbox()
        before = m.git(m.clone, "log", "--format=%H")
        m.start()
        for concept in ("types.record", "lang.var"):
            self.assertEqual(m.run("record", "experienced", "--lang", "csharp-dotnet",
                                   "--concept", concept).returncode, 0)
        end = m.run("session-end")
        self.assertEqual(end.returncode, 0)
        self.assertEqual(end.stdout.strip(), "Profile: 3 lines kept in a temporary spool, to be added "
                                             "at the next session that can write the profile.")
        self.assertEqual(m.git(m.clone, "log", "--format=%H"), before)
        self.assertEqual(len((self.spool / "evidence.jsonl").read_text().splitlines()), 3)
        self.assertEqual(sorted(p.name for p in m.repo.iterdir()), [".git"])

    def test_the_spool_is_merged_at_the_next_writable_session_start(self):
        m = self.machine
        self.default_sandbox()
        m.start()
        m.run("record", "experienced", "--lang", "csharp-dotnet", "--concept", "types.record")
        m.run("session-end")
        self.open_up()
        m.today = "2026-11-06"
        m.start()
        self.assertFalse(self.spool.exists())
        self.assertEqual(m.commits()[0], "Evidence: 2 lines (recovered)")
        self.assertEqual([line["timestamp"] for line in m.lines()[-3:]],
                         ["2026-11-05T00:00:00Z", "2026-11-05T00:00:00Z", "2026-11-06T00:00:00Z"])

    def test_off_the_record_discards_spooled_lines(self):
        m = self.machine
        self.default_sandbox()
        m.start()
        m.run("record", "experienced", "--lang", "csharp-dotnet", "--concept", "types.record")
        m.run("off-the-record")
        self.assertEqual((self.spool / "evidence.jsonl").read_text(), "")

    def test_nowhere_to_write_still_never_fails(self):
        m = self.machine
        self.default_sandbox()
        self.sandbox(m.clone, m.state, self.tmpdir)
        for args in (["session-start", "--harness", "codex", "--repo", str(m.repo)],
                     ["record", "experienced", "--lang", "csharp-dotnet", "--concept", "types.record"],
                     ["session-end"]):
            self.assertEqual(m.run(*args, check=False).returncode, 0, args)


class Network(CodexTest):
    def test_network_disabled_skips_sync_without_trying(self):
        m = self.machine
        self.open_up()
        m.signed_in = True
        m.run("add-remote", "--host", "github.com")
        trace = self.tmp / "git-trace"
        self.sandbox(network=False)
        m.env_overrides["GIT_TRACE"] = str(trace)
        m.start()
        m.run("record", "experienced", "--lang", "csharp-dotnet", "--concept", "types.record")
        end = m.run("session-end")
        self.assertEqual(end.stdout.strip(),
                         "Profile: 2 lines recorded, kept on this machine until it can sync.")
        self.assertEqual(end.stderr, "")
        commands = [line for line in trace.read_text().splitlines() if "built-in: git" in line]
        self.assertTrue(any(" commit " in line for line in commands))
        self.assertFalse(any(" fetch" in line or " push" in line for line in commands))


class Snippet(CodexTest):
    def test_the_config_snippet_uses_absolute_paths(self):
        m = self.machine
        snippet = m.run("codex-config").stdout
        trinity = self.tmp / "laptop" / "data" / "trinity-helicopter-program"
        self.assertEqual(snippet, f"""\
[sandbox_workspace_write]
writable_roots = [
  "{m.clone}",
  "{m.clone}/.git",
  "{m.state}",
  "{trinity}",
]
# network_access = true   # optional: lets the profile sync from inside Codex
""")
        self.assertTrue(all(Path(p).is_absolute() for p in (m.clone, m.state, trinity)))

    def test_the_snippet_is_printed_when_a_write_is_blocked(self):
        m = self.machine
        self.default_sandbox()
        self.assertIn(f'"{m.clone}/.git",', m.start().stdout)


if __name__ == "__main__":
    unittest.main()
