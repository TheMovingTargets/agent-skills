#!/usr/bin/env python3
"""Resolve learner identity (GitHub or Azure DevOps) and atomically read/write local progress."""

from __future__ import annotations

import argparse
import base64
import json
import os
import re
import subprocess
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

# Azure DevOps' Entra resource ID, used to get a token for its REST API from `az login`.
AZURE_DEVOPS_RESOURCE = "499b84ac-1321-427f-aa17-267ca6975798"
CONNECTION_DATA = "{org_url}/_apis/connectionData?api-version=7.1-preview"

GITHUB_REMOTE = re.compile(r"(?:https?://|ssh://git@|git@)([^/:]+)[:/]([^/]+)/([^/]+?)(?:\.git)?$")
ADO_REMOTES = [
    # https://dev.azure.com/org/project/_git/repo, https://org@dev.azure.com/org/project/_git/repo
    re.compile(r"^https?://(?:[^@/]+@)?dev\.azure\.com/(?P<org>[^/]+)/(?P<project>[^/]+)/_git/(?P<repo>[^/?#]+)"),
    # git@ssh.dev.azure.com:v3/org/project/repo
    re.compile(r"^(?:ssh://)?git@ssh\.dev\.azure\.com[:/]v3/(?P<org>[^/]+)/(?P<project>[^/]+)/(?P<repo>[^/?#]+)"),
    # https://org.visualstudio.com/[DefaultCollection/]project/_git/repo
    re.compile(r"^https?://(?:[^@/]+@)?(?P<org>[^./]+)\.visualstudio\.com/(?:DefaultCollection/)?(?P<project>[^/]+)"
               r"/_git/(?P<repo>[^/?#]+)"),
    # any other host that serves the Azure DevOps path layout, such as a git proxy: host/org/project/_git/repo
    re.compile(r"^https?://(?:[^@/]+@)?[^/]+/(?P<org>[^/]+)/(?P<project>[^/]+)/_git/(?P<repo>[^/?#]+)"),
]


def run(args: list[str], cwd: Path) -> str:
    result = subprocess.run(args, cwd=cwd, text=True, capture_output=True, check=False)
    if result.returncode:
        raise RuntimeError(result.stderr.strip() or f"command failed: {' '.join(args)}")
    return result.stdout.strip()


def repository(repo: Path) -> dict[str, str]:
    remote = run(["git", "remote", "get-url", "origin"], repo)
    for pattern in ADO_REMOTES:
        match = pattern.search(remote)
        if match:
            org, project, name = match["org"], match["project"], match["repo"].removesuffix(".git")
            return {"provider": "azure-devops", "host": "dev.azure.com", "owner": f"{org}/{project}", "name": name,
                    "organization_url": os.environ.get("COGNITIVE_RELOAD_ADO_ORG_URL",
                                                       f"https://dev.azure.com/{org}").rstrip("/")}
    match = GITHUB_REMOTE.search(remote)
    if not match:
        raise RuntimeError(f"cannot normalize origin remote: {remote}")
    host, owner, name = match.groups()
    return {"provider": "github", "host": host.lower(), "owner": owner, "name": name.removesuffix(".git")}


def github_login(repo: Path) -> str:
    return run(["gh", "api", "user", "--jq", ".login"], repo)


def azure_devops_login(repo: Path, org_url: str) -> str:
    """The signed-in Azure DevOps user's account (their sign-in name, usually an e-mail address).

    Tries the Azure CLI's Entra sign-in (`az login`) first, then a personal access token in AZURE_DEVOPS_EXT_PAT
    (the variable `az devops` itself reads). Neither the token nor the response is printed.
    """
    url = CONNECTION_DATA.format(org_url=org_url)
    errors = []
    try:
        data = json.loads(run(["az", "rest", "--resource", AZURE_DEVOPS_RESOURCE, "--url", url], repo))
        return _account(data)
    except (RuntimeError, OSError, ValueError, KeyError) as exc:
        errors.append(f"az login: {str(exc).splitlines()[0] if str(exc) else type(exc).__name__}")
    token = os.environ.get("AZURE_DEVOPS_EXT_PAT")
    if token:
        credentials = base64.b64encode(f":{token}".encode()).decode()
        request = urllib.request.Request(url, headers={"Authorization": f"Basic {credentials}"})
        try:
            with urllib.request.urlopen(request, timeout=30) as response:
                return _account(json.loads(response.read()))
        except ValueError:  # an invalid token gets an HTML sign-in page instead of JSON
            errors.append("AZURE_DEVOPS_EXT_PAT: rejected by Azure DevOps")
        except (urllib.error.URLError, OSError, KeyError) as exc:
            errors.append(f"AZURE_DEVOPS_EXT_PAT: {type(exc).__name__}")
    else:
        errors.append("AZURE_DEVOPS_EXT_PAT: not set")
    raise RuntimeError("cannot resolve the Azure DevOps user (" + "; ".join(errors) + ")")


def _account(data: dict) -> str:
    user = data["authenticatedUser"]
    account = (user.get("properties", {}).get("Account", {}) or {}).get("$value") or user.get("id")
    if not account or user.get("descriptor", "").startswith("Microsoft.TeamFoundation.UnauthenticatedIdentity"):
        raise KeyError("no authenticated user")
    return account


def learner(repo: Path, identity: dict[str, str]) -> str:
    if identity["provider"] == "azure-devops":
        return azure_devops_login(repo, identity["organization_url"])
    return github_login(repo)


def progress_path(repo: Path) -> tuple[Path, str, dict[str, str]]:
    identity = repository(repo)
    login = learner(repo, identity)
    root = Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local" / "share"))
    provider_dir = "github" if identity["provider"] == "github" else identity["provider"]
    path = (root / "cognitive-reload" / provider_dir / identity["host"] / Path(identity["owner"]) / identity["name"]
            / re.sub(r"[^\w.@+-]", "_", login) / "progress.json")
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
            output = {"identity_provider": identity["provider"], "learner_login": login, "repository": identity}
            if identity["provider"] == "github":
                output["github_login"] = login
            print(json.dumps(output))
        elif args.command == "path":
            print(path)
        elif args.command == "get":
            print(path.read_text() if path.exists() else "null")
        else:
            payload = json.load(sys.stdin)
            payload["identity_provider"] = identity["provider"]
            payload["learner_login"] = login
            if identity["provider"] == "github":
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
