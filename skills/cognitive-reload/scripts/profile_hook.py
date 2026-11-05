#!/usr/bin/env python3
"""Cognitive Reload's link to the proficiency-profile skill. Standard library only.

Finds proficiency-profile's profile.py with the sibling-skill search and passes
Cognitive Reload's events to it. When it isn't installed, Cognitive Reload works
as before: `session-start` says so once and every other call is a silent no-op.

  profile_hook.py run <profile.py args…>          pass a command through
  profile_hook.py pitch --lang L --concepts …     name | refresher | primer, per Architecture Concept

The profile only pitches explanations. It never skips repo-specific teaching
and never affects scoring.
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
NOT_FOUND = "proficiency-profile not found: nothing is recorded this session."


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


def cmd_run(args: list[str]) -> int:
    profile = find_profile()
    if profile is None:
        if args[:1] == ["session-start"]:
            print(NOT_FOUND)
        return 0
    return subprocess.run([sys.executable, str(profile), *args]).returncode


def cmd_pitch(lang: str, concepts: list[str]) -> int:
    """Proven and Current: name the pattern, skip the primer. Lapsed: a brief refresher."""
    states: dict = {}
    profile = find_profile()
    if profile is not None:
        keys = ",".join(f"arch/{c}" for c in concepts)
        result = subprocess.run([sys.executable, str(profile), "read", "--lang", lang, "--concepts", keys],
                                capture_output=True, text=True)
        if result.returncode == 0 and result.stdout.strip():
            states = json.loads(result.stdout).get("concepts", {})
    out = {}
    for concept in concepts:
        state = states.get(f"arch/{concept}", {})
        if state.get("level") == "Proven" and state.get("band") == "Current":
            out[concept] = "name"
        elif state.get("band") == "Lapsed":
            out[concept] = "refresher"
        else:
            out[concept] = "primer"
    print(json.dumps(out, indent=2))
    return 0


def main(argv: list[str]) -> int:
    if argv[:1] == ["run"]:
        return cmd_run(argv[1:])
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    sub = parser.add_subparsers(dest="command", required=True)
    pitch = sub.add_parser("pitch")
    pitch.add_argument("--lang", required=True)
    pitch.add_argument("--concepts", required=True)
    args = parser.parse_args(argv)
    return cmd_pitch(args.lang, [c.strip() for c in args.concepts.split(",") if c.strip()])


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
