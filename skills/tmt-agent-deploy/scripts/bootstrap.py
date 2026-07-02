#!/usr/bin/env python3
"""Bootstrap isolated TMT Agent Deploy helper dependencies."""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path


SKILL_ROOT = Path(__file__).resolve().parents[1]
REQUIREMENTS = SKILL_ROOT / "requirements.txt"


def run(command: list[str]) -> None:
    subprocess.run(command, check=True)


def interpreter(venv: Path) -> Path:
    if os.name == "nt":
        return venv / "Scripts" / "python.exe"
    return venv / "bin" / "python"


def apply_private_permissions(root: Path) -> None:
    if os.name == "nt":
        return
    for directory in [root, root / "runs", root / "state"]:
        directory.chmod(0o700)
    for path in root.rglob("*"):
        if path.is_file() and ".venv" not in path.parts:
            path.chmod(0o600)


def bootstrap(repo: Path) -> Path:
    if sys.version_info < (3, 9):
        raise RuntimeError("Python 3.9 or newer is required")
    local_root = repo.resolve() / ".tmt-agent-deploy"
    state = local_root / "state"
    runs = local_root / "runs"
    venv = state / ".venv"
    state.mkdir(parents=True, exist_ok=True)
    runs.mkdir(parents=True, exist_ok=True)

    python = interpreter(venv)
    created = not python.exists()
    try:
        if created:
            uv = shutil.which("uv")
            if uv:
                run([uv, "venv", str(venv), "--python", sys.executable])
            else:
                run([sys.executable, "-m", "venv", str(venv)])

        uv = shutil.which("uv")
        if uv:
            run(
                [
                    uv,
                    "pip",
                    "install",
                    "--python",
                    str(python),
                    "-r",
                    str(REQUIREMENTS),
                ]
            )
        else:
            run([str(python), "-m", "pip", "install", "-r", str(REQUIREMENTS)])
    except (OSError, subprocess.CalledProcessError):
        if created:
            shutil.rmtree(venv, ignore_errors=True)
        raise

    apply_private_permissions(local_root)
    return python


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", default=".")
    args = parser.parse_args()
    try:
        print(bootstrap(Path(args.repo)))
        return 0
    except (OSError, RuntimeError, subprocess.CalledProcessError) as exc:
        print(f"bootstrap failed: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
