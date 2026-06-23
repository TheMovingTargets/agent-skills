#!/usr/bin/env python3
"""Render HITL cognition Markdown dashboard from an exported current.json file."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import export_hitl_cognition as hitl


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("current_json")
    parser.add_argument("--out", default="README.md")
    args = parser.parse_args()
    try:
        summary = json.loads(Path(args.current_json).read_text())
        path = Path(args.out)
        hitl.write_text(path, hitl.current_markdown(summary))
        print(path)
        return 0
    except (OSError, KeyError, json.JSONDecodeError) as exc:
        print(f"dashboard render failed: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
