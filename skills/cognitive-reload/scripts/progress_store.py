#!/usr/bin/env python3
"""Resolve GitHub learner identity and atomically read/write local progress."""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path


def run(args: list[str], cwd: Path) -> str:
    result = subprocess.run(args, cwd=cwd, text=True, capture_output=True, check=False)
    if result.returncode:
        raise RuntimeError(result.stderr.strip() or f"command failed: {' '.join(args)}")
    return result.stdout.strip()


def github_login(repo: Path) -> str:
    return run(["gh", "api", "user", "--jq", ".login"], repo)


def repository(repo: Path) -> dict[str, str]:
    remote = run(["git", "remote", "get-url", "origin"], repo)
    match = re.search(r"(?:https?://|ssh://git@|git@)([^/:]+)[:/]([^/]+)/([^/]+?)(?:\.git)?$", remote)
    if not match:
        raise RuntimeError(f"cannot normalize origin remote: {remote}")
    host, owner, name = match.groups()
    if name.endswith(".git"):
        name = name[:-4]
    return {"host": host.lower(), "owner": owner, "name": name}


def progress_path(repo: Path) -> tuple[Path, str, dict[str, str]]:
    login = github_login(repo)
    identity = repository(repo)
    root = Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local" / "share"))
    path = root / "cognitive-reload" / "github" / identity["host"] / identity["owner"] / identity["name"] / login / "progress.json"
    return path, login, identity


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=["identity", "path", "get", "put"])
    parser.add_argument("--repo", default=".")
    args = parser.parse_args()
    repo = Path(args.repo).resolve()
    try:
        path, login, identity = progress_path(repo)
        if args.command == "identity":
            print(json.dumps({"github_login": login, "repository": identity}))
        elif args.command == "path":
            print(path)
        elif args.command == "get":
            print(path.read_text() if path.exists() else "null")
        else:
            payload = json.load(sys.stdin)
            payload["github_login"] = login
            payload["repository"] = {**payload.get("repository", {}), **identity}
            payload["updated_at"] = datetime.now(timezone.utc).isoformat()
            path.parent.mkdir(parents=True, exist_ok=True)
            temporary = path.with_suffix(".tmp")
            temporary.write_text(json.dumps(payload, indent=2) + "\n")
            os.replace(temporary, path)
            print(path)
        return 0
    except (RuntimeError, OSError, json.JSONDecodeError) as exc:
        print(f"progress unavailable: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
