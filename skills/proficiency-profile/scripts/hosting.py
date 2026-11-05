#!/usr/bin/env python3
"""Home Providers, Linked Identities and the provider CLIs. Standard library only.

A Linked Identity is recorded as an xAPI account (spec §5). None of them
records an organization, a hostname or an email address:

  github               https://github.com                    login
  gitlab               https://gitlab.com                    username
  azure-devops         https://app.vssps.visualstudio.com    profile id GUID, plus a display name
  github-enterprise    https://github-enterprise.invalid     login
  gitlab-self-managed  https://gitlab-self-managed.invalid   login

The skill never runs a login. A CLI that isn't signed in means the profile
stays local.
"""
from __future__ import annotations

import json
import re
import shutil
import subprocess

KINDS = {
    "github": "https://github.com",
    "gitlab": "https://gitlab.com",
    "azure-devops": "https://app.vssps.visualstudio.com",
    "github-enterprise": "https://github-enterprise.invalid",
    "gitlab-self-managed": "https://gitlab-self-managed.invalid",
}
LABELS = {
    "github": "GitHub",
    "gitlab": "GitLab",
    "azure-devops": "Azure DevOps",
    "github-enterprise": "GitHub Enterprise",
    "gitlab-self-managed": "GitLab self-managed",
}
HOME_PROVIDERS = {"github.com": "github", "gitlab.com": "gitlab"}
REPO_NAME = "proficiency-profile"

LOGIN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")
GUID = re.compile(r"^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$")


def identity(kind: str, name: str, display: str | None = None) -> dict:
    """A Linked Identity record, refusing anything that could name an org, host or email."""
    if kind not in KINDS:
        raise ValueError(f"unknown account kind {kind!r}")
    if kind == "azure-devops":
        if not GUID.match(name):
            raise ValueError("an Azure DevOps account is its profile id GUID, from profiles/me")
        if not display or "@" in display:
            raise ValueError("an Azure DevOps account needs its display name, not an email address")
        return {"homePage": KINDS[kind], "name": name.lower(), "display": display}
    if not LOGIN.match(name):
        raise ValueError(f"{name!r} isn't a bare login: no email, host or organization")
    return {"homePage": KINDS[kind], "name": name}


def kind_of(record: dict) -> str | None:
    return next((k for k, home in KINDS.items() if home == record["homePage"]), None)


def repo_kinds(host: str) -> list[str]:
    """Account kinds that can own work in a repo on `host`, most likely first."""
    host = host.lower()
    if host in HOME_PROVIDERS:
        return [HOME_PROVIDERS[host]]
    if host in ("dev.azure.com", "ssh.dev.azure.com") or host.endswith(".visualstudio.com"):
        return ["azure-devops"]
    if not host:
        return []
    if "gitlab" in host:
        return ["gitlab-self-managed", "github-enterprise"]
    return ["github-enterprise", "gitlab-self-managed"]


def choose_actor(identities: list[dict], kinds: list[str]) -> dict:
    """The Linked Identity for the repo's host, else the one the profile was created under."""
    for kind in kinds:
        for record in identities:
            if kind_of(record) == kind:
                return record
    return identities[0]


class Provider:
    """A Home Provider reached through its CLI: gh for github.com, glab for gitlab.com."""

    def __init__(self, kind: str):
        self.kind = kind
        self.cli = "gh" if kind == "github" else "glab"
        self.host = "github.com" if kind == "github" else "gitlab.com"
        self.label = LABELS[kind]

    def _run(self, *args: str) -> subprocess.CompletedProcess | None:
        if shutil.which(self.cli) is None:
            return None
        try:
            return subprocess.run([self.cli, *args], capture_output=True, text=True, timeout=60)
        except (OSError, subprocess.TimeoutExpired):
            return None

    def signed_in(self) -> bool:
        result = self._run("auth", "status", "--hostname", self.host)
        # glab's exit code isn't documented, so its output is checked too.
        return bool(result and result.returncode == 0 and "not logged" not in
                    (result.stdout + result.stderr).lower())

    def user(self) -> tuple[str, int]:
        result = self._run("api", "user")
        if not result or result.returncode != 0:
            raise RuntimeError(f"{self.cli} api user failed")
        data = json.loads(result.stdout)
        return (data["login"] if self.kind == "github" else data["username"]), int(data["id"])

    def repo_url(self, login: str) -> str | None:
        """The Profile Repo's clone URL, or None if it doesn't exist."""
        if self.kind == "github":
            result = self._run("repo", "view", f"{login}/{REPO_NAME}", "--json", "url")
            key = "url"
        else:
            result = self._run("repo", "view", f"{login}/{REPO_NAME}", "-F", "json")
            key = "http_url_to_repo"
        if not result or result.returncode != 0:
            return None
        return json.loads(result.stdout)[key]

    def create(self, login: str) -> str:
        """Create the Profile Repo, always with an explicit private flag, and return its URL."""
        args = ["repo", "create", REPO_NAME, "--private"]
        if self.kind == "gitlab":
            args.append("--skipGitInit")
        result = self._run(*args)
        if not result or result.returncode != 0:
            raise RuntimeError(f"{self.cli} repo create failed")
        url = self.repo_url(login)
        if url is None:
            raise RuntimeError(f"{self.cli} created the repo but can't see it")
        return url

    def noreply(self, login: str, user_id: int) -> str:
        if self.kind == "github":
            return f"{user_id}+{login}@users.noreply.github.com"
        return f"{user_id}-{login}@users.noreply.gitlab.com"


def pr_state(url: str) -> str | None:
    """OPEN, MERGED or CLOSED for a proposal PR on GitHub, or None if gh can't tell."""
    if shutil.which("gh") is None:
        return None
    try:
        result = subprocess.run(["gh", "pr", "view", url, "--json", "state"],
                                capture_output=True, text=True, timeout=60)
    except (OSError, subprocess.TimeoutExpired):
        return None
    if result.returncode != 0:
        return None
    return json.loads(result.stdout).get("state")
