#!/usr/bin/env python3
"""Render HITL cognition badges from an exported current.json file."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import export_hitl_cognition as hitl


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("current_json")
    parser.add_argument("--out", default="badges")
    args = parser.parse_args()
    try:
        summary = json.loads(Path(args.current_json).read_text())
        out = Path(args.out)
        cognition = summary["hitl_cognition"]
        badges = {
            out / "hitl-cognition.svg": hitl.badge_svg(
                "HITL cognition",
                f'{cognition["level"]} {cognition["index"]}',
                cognition["color"],
            ),
            out / "hitl-topics.svg": hitl.badge_svg(
                "HITL topics",
                f'{cognition["explored_topics"]}/{cognition["topic_count"]} explored',
                "blue",
            ),
            out / "hitl-assessed.svg": hitl.badge_svg(
                "HITL assessed",
                f'{cognition["assessed_topics"]}/{cognition["topic_count"]} assessed',
                "green" if cognition["assessed_topics"] else "lightgrey",
            ),
            out / "hitl-freshness.svg": hitl.badge_svg(
                "HITL freshness",
                hitl.freshness_message(cognition["freshness_days"]),
                hitl.badge_color_for_freshness(cognition["freshness_days"]),
            ),
        }
        for path, svg in badges.items():
            hitl.write_text(path, svg)
            print(path)
        return 0
    except (OSError, KeyError, json.JSONDecodeError) as exc:
        print(f"badge render failed: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
