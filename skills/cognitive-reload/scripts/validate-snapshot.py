#!/usr/bin/env python3
"""Validate a cognitive-reload JSON snapshot.

This intentionally uses only the Python standard library for portability. It performs
structural checks that catch common skill-output mistakes even when jsonschema is not
installed.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

VALID_MODES = {"first_time_guided", "weekly_reload", "deep_reload", "handoff_reload"}
VALID_STATUSES = {"unverified", "verified", "partial", "retake_available", "stale"}
REQUIRED_TOP = {"schema_version", "skill", "session", "overall", "areas", "evidence_ledgers", "quiz_attempts"}
DIMENSIONS = {"orientation", "causal_understanding", "change_awareness", "risk_awareness", "test_awareness", "agent_guidance_readiness"}


def fail(msg: str) -> None:
    print(f"ERROR: {msg}", file=sys.stderr)
    sys.exit(1)


def check_score(value, path: str) -> None:
    if value is None:
        return
    if not isinstance(value, (int, float)) or not (0 <= value <= 5):
        fail(f"{path} must be null or a number between 0 and 5")


def main() -> None:
    if len(sys.argv) != 2:
        fail("usage: validate-snapshot.py <snapshot.json>")
    path = Path(sys.argv[1])
    try:
        data = json.loads(path.read_text())
    except Exception as exc:
        fail(f"could not parse JSON: {exc}")

    missing = REQUIRED_TOP - set(data)
    if missing:
        fail(f"missing required top-level fields: {sorted(missing)}")

    if data.get("skill", {}).get("name") != "cognitive-reload":
        fail("skill.name must be cognitive-reload")

    mode = data.get("session", {}).get("mode")
    if mode not in VALID_MODES:
        fail(f"session.mode must be one of {sorted(VALID_MODES)}")

    overall = data.get("overall", {})
    check_score(overall.get("provisional_score"), "overall.provisional_score")

    areas = data.get("areas")
    if not isinstance(areas, list):
        fail("areas must be a list")

    for idx, area in enumerate(areas):
        prefix = f"areas[{idx}]"
        for key in ("area_id", "area_name", "status", "agent_handoff_ready"):
            if key not in area:
                fail(f"{prefix}.{key} is required")
        if area["status"] not in VALID_STATUSES:
            fail(f"{prefix}.status must be one of {sorted(VALID_STATUSES)}")
        check_score(area.get("score"), f"{prefix}.score")
        dims = area.get("dimensions", {})
        if dims:
            unknown_dims = set(dims) - DIMENSIONS
            if unknown_dims:
                fail(f"{prefix}.dimensions has unknown dimensions: {sorted(unknown_dims)}")
            for name, value in dims.items():
                check_score(value, f"{prefix}.dimensions.{name}")
        if area["status"] == "unverified" and area.get("score") is not None:
            fail(f"{prefix} is unverified but has a score")

    for idx, attempt in enumerate(data.get("quiz_attempts", [])):
        if "attempt_id" not in attempt or "area_id" not in attempt:
            fail(f"quiz_attempts[{idx}] must include attempt_id and area_id")
        check_score(attempt.get("area_score"), f"quiz_attempts[{idx}].area_score")

    print(f"OK: {path}")


if __name__ == "__main__":
    main()
