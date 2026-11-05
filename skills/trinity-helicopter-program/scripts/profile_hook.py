#!/usr/bin/env python3
"""Trinity's link to the proficiency-profile skill. Standard library only.

Finds proficiency-profile's profile.py with the sibling-skill search that
cognitive-reload-with-trinity uses, and passes Trinity's events to it. When
it isn't installed, Trinity works as before: `session-start` says so once and
every other call is a silent no-op.

  profile_hook.py run <profile.py args…>        pass a command through
  profile_hook.py triage --lang L --concepts …  silence | refresher | triage, per Concept
  profile_hook.py bridges --lang L              other Languages with Practiced or Proven Concepts
  profile_hook.py refresh --lang L              the top "Due for a refresh" Concept, if any
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import ledger  # noqa: E402

NOT_FOUND = "proficiency-profile not found: nothing is recorded this session."
QUIET = {"known", "fluent"}  # ledger statuses that already mean silence


def _version_key(path: Path) -> list:
    return [int(part) if part.isdigit() else part for part in re.split(r"(\d+)", path.name)]


def find_profile() -> Path | None:
    """profile.py from the first installed proficiency-profile skill, searched in order."""
    home = Path.home()
    dirs = [
        HERE.parents[1],
        Path.cwd() / ".agents" / "skills",
        Path.cwd() / ".claude" / "skills",
        home / ".agents" / "skills",
        home / ".claude" / "skills",
        home / ".codex" / "skills",
    ]
    for harness in (".claude", ".codex"):
        versions = [p.parent for p in (home / harness / "plugins" / "cache").glob("*/*/*/skills")]
        dirs += [v / "skills" for v in sorted(versions, key=_version_key, reverse=True)]
    for folder in dirs:
        skill = folder / "proficiency-profile"
        if (skill / "SKILL.md").is_file() and (skill / "scripts" / "profile.py").is_file():
            return skill / "scripts" / "profile.py"
    return None


def profile_read(lang: str | None = None, concepts: list[str] | None = None) -> dict:
    profile = find_profile()
    if profile is None:
        return {}
    args = [sys.executable, str(profile), "read"]
    if lang:
        args += ["--lang", lang]
    if concepts:
        args += ["--concepts", ",".join(concepts)]
    result = subprocess.run(args, capture_output=True, text=True)
    return json.loads(result.stdout) if result.returncode == 0 and result.stdout.strip() else {}


def ledger_statuses(lang: str) -> dict[str, str]:
    return {cid: c.get("status") for cid, c in ledger.load(lang).get("concepts", {}).items()}


def cmd_run(args: list[str]) -> int:
    profile = find_profile()
    if profile is None:
        if args[:1] == ["session-start"]:
            print(NOT_FOUND)
        return 0
    return subprocess.run([sys.executable, str(profile), *args]).returncode


def cmd_triage(lang: str, concepts: list[str]) -> int:
    """The stronger of the ledger and the profile decides how much to say."""
    statuses = ledger_statuses(lang)
    profile = profile_read(lang, concepts).get("concepts", {})
    out = {}
    for concept in concepts:
        state = profile.get(concept, {})
        if statuses.get(concept) in QUIET:
            out[concept] = "silence"
        elif state.get("level") == "Proven" and state.get("band") == "Current":
            out[concept] = "silence"
        elif state.get("level") in ("Practiced", "Proven") and state.get("band") in ("Fading", "Lapsed"):
            out[concept] = "refresher"
        else:
            out[concept] = "triage"
    print(json.dumps(out, indent=2))
    return 0


def cmd_bridges(lang: str) -> int:
    languages = profile_read().get("languages", {})
    bridges = [other for other, state in sorted(languages.items())
               if other != lang and state["counts"]["Practiced"] + state["counts"]["Proven"] > 0]
    print(json.dumps(bridges))
    return 0


def cmd_refresh(lang: str) -> int:
    """Lapsed before Fading, then the longest unexercised, skipping what the ledger calls known."""
    read = profile_read(lang)
    statuses = ledger_statuses(lang)
    due = [c for c in read.get("due_for_refresh", []) if statuses.get(c) not in QUIET]
    concepts = read.get("concepts", {})
    due.sort(key=lambda c: (concepts[c]["band"] != "Lapsed", concepts[c]["last_exercised"] or "", c))
    if due:
        print(due[0])
    return 0


def main(argv: list[str]) -> int:
    if argv[:1] == ["run"]:
        return cmd_run(argv[1:])
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    sub = parser.add_subparsers(dest="command", required=True)
    triage = sub.add_parser("triage")
    triage.add_argument("--lang", required=True)
    triage.add_argument("--concepts", required=True)
    for name in ("bridges", "refresh"):
        sub.add_parser(name).add_argument("--lang", required=True)
    args = parser.parse_args(argv)
    if args.command == "triage":
        return cmd_triage(args.lang, [c.strip() for c in args.concepts.split(",") if c.strip()])
    if args.command == "bridges":
        return cmd_bridges(args.lang)
    return cmd_refresh(args.lang)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
