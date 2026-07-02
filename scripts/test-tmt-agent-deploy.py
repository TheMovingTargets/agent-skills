#!/usr/bin/env python3
"""Run TMT Agent Deploy tests in its bootstrapped isolated environment."""

from __future__ import annotations

import subprocess
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SKILL = ROOT / "skills" / "tmt-agent-deploy"


def main() -> int:
    with tempfile.TemporaryDirectory() as temporary:
        result = subprocess.run(
            [
                sys.executable,
                str(SKILL / "scripts" / "bootstrap.py"),
                "--repo",
                temporary,
            ],
            text=True,
            capture_output=True,
            check=False,
        )
        if result.returncode:
            sys.stderr.write(result.stdout)
            sys.stderr.write(result.stderr)
            return result.returncode
        python = result.stdout.strip().splitlines()[-1]
        completed = subprocess.run(
            [
                python,
                "-m",
                "unittest",
                "discover",
                "-s",
                str(SKILL / "tests"),
                "-p",
                "test_*.py",
                "-v",
            ],
            cwd=ROOT,
            check=False,
        )
        return completed.returncode


if __name__ == "__main__":
    raise SystemExit(main())
