#!/usr/bin/env python3
"""A stand-in for `gh` and `glab` in tests. Never touches the network.

Driven by environment variables:
  FAKE_CLI_LOG       file that each call is appended to, one JSON array per line
  FAKE_REMOTES       folder holding bare repos, as <owner>/<name>.git
  FAKE_SIGNED_IN     "1" if the CLI is signed in
  FAKE_LOGIN         the signed-in account's login / username
  FAKE_ID            the signed-in account's numeric id
  FAKE_PR_STATE      what `gh pr view` reports: OPEN, MERGED or CLOSED
"""
import json
import os
import subprocess
import sys
from pathlib import Path

tool = Path(sys.argv[1]).name
args = sys.argv[2:]
with open(os.environ["FAKE_CLI_LOG"], "a", encoding="utf-8") as log:
    log.write(json.dumps([tool, *args]) + "\n")

signed_in = os.environ.get("FAKE_SIGNED_IN") == "1"
login = os.environ.get("FAKE_LOGIN", "octo-learner")
remotes = Path(os.environ["FAKE_REMOTES"])


def bare(owner_name: str) -> Path:
    return remotes / f"{owner_name}.git"


if args[:2] == ["pr", "view"]:
    print(json.dumps({"state": os.environ.get("FAKE_PR_STATE", "OPEN")}))
    sys.exit(0)
if args[:2] == ["auth", "status"]:
    if signed_in:
        print(f"Logged in to {'github.com' if tool == 'gh' else 'gitlab.com'} as {login}")
        sys.exit(0)
    print("You are not logged in", file=sys.stderr)
    sys.exit(1)
if not signed_in:
    print("not logged in", file=sys.stderr)
    sys.exit(4)
if args[:2] == ["api", "user"]:
    uid = int(os.environ.get("FAKE_ID", "1234"))
    print(json.dumps({"login": login, "id": uid} if tool == "gh" else {"username": login, "id": uid}))
    sys.exit(0)
if args[:2] == ["repo", "view"]:
    path = bare(args[2])
    if not path.exists():
        print("not found", file=sys.stderr)
        sys.exit(1)
    print(json.dumps({"url": str(path)} if tool == "gh" else {"http_url_to_repo": str(path)}))
    sys.exit(0)
if args[:2] == ["repo", "create"]:
    if "--private" not in args:
        print("refusing: tests require --private", file=sys.stderr)
        sys.exit(2)
    path = bare(f"{login}/{args[2]}")
    path.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(["git", "init", "-q", "--bare", "-b", "main", str(path)], check=True)
    sys.exit(0)
print(f"fake {tool}: unsupported {args}", file=sys.stderr)
sys.exit(64)
