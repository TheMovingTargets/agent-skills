#!/usr/bin/env python3
from __future__ import annotations

import re
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SKILL = ROOT / "skills" / "cognitive-reload" / "SKILL.md"


def main() -> int:
    text = SKILL.read_text(encoding="utf-8")
    if not text.startswith("---\n"):
        print(f"{SKILL}: missing YAML frontmatter", file=sys.stderr)
        return 1

    try:
        _, frontmatter, _ = text.split("---\n", 2)
    except ValueError:
        print(f"{SKILL}: malformed YAML frontmatter", file=sys.stderr)
        return 1

    fields = {}
    for line in frontmatter.splitlines():
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        fields[key.strip()] = value.strip()

    name = fields.get("name")
    description = fields.get("description")
    if name != "cognitive-reload":
        print(f"{SKILL}: expected name cognitive-reload, got {name!r}", file=sys.stderr)
        return 1
    if not description:
        print(f"{SKILL}: missing description", file=sys.stderr)
        return 1
    if not re.fullmatch(r"[a-z0-9-]+", name):
        print(f"{SKILL}: invalid skill name {name!r}", file=sys.stderr)
        return 1

    required = [
        ROOT / ".claude-plugin" / "plugin.json",
        ROOT / ".codex-plugin" / "plugin.json",
        ROOT / ".agents" / "plugins" / "marketplace.json",
        SKILL.parent / "scripts" / "progress_store.py",
        SKILL.parent / "scripts" / "export_hitl_cognition.py",
    ]
    missing = [path for path in required if not path.exists()]
    if missing:
        for path in missing:
            print(f"missing required file: {path}", file=sys.stderr)
        return 1

    print("cognitive-reload skill package is structurally valid")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
