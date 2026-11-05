#!/usr/bin/env python3
"""The proficiency-profile writer. Standard library only.

The learning skills never build a Statement themselves. They call this script
at session start, at each recordable event, and at the debrief, and it turns
those events into trimmed xAPI 2.0 Statements in the Profile Repo.

Locations:
  ${XDG_DATA_HOME:-~/.local/share}/proficiency-profile/    the local clone
  ${XDG_STATE_HOME:-~/.local/state}/proficiency-profile/   machine id, lock, session
  ${XDG_CONFIG_HOME:-~/.config}/proficiency-profile/excluded-repos

The Profile Repo holds only README.md, profile.json and
evidence/<yyyy>/<mm>/<machine-id>.jsonl. Nothing written there names a
repository, organization, hostname or work email address.

Set PROFICIENCY_PROFILE_TODAY=YYYY-MM-DD to pin "today" (for tests).
"""
from __future__ import annotations

import argparse
import contextlib
import datetime as dt
import fcntl
import hashlib
import json
import os
import re
import secrets
import subprocess
import sys
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import derive  # noqa: E402
import held  # noqa: E402
import hosting  # noqa: E402
import readme  # noqa: E402
import vocabularies  # noqa: E402

NS = "https://w3id.org/xapi/devprof/"
DIMENSION = NS + "extensions/dimension"
ADL = "http://adlnet.gov/expapi/verbs/"
VERBS = {
    "experienced": ADL + "experienced",
    "interacted": ADL + "interacted",
    "passed": ADL + "passed",
    "failed": ADL + "failed",
    "voided": ADL + "voided",
    "practiced": NS + "verbs/practiced",
    "use": "http://activitystrea.ms/schema/1.0/use",
}
# Fly-drill grades: Good is idiomatic, Hard is correct but not idiomatic.
GRADES = {"good": (True, 1.0), "hard": (True, 0.5), "again": (False, 0.0)}
SCHEMA_VERSION = 1

EXIT_UNKNOWN_ID = 3
EXIT_NO_SESSION = 4


# --- Locations -------------------------------------------------------------


def _xdg(variable: str, default: str) -> Path:
    base = os.environ.get(variable) or str(Path.home() / default)
    return Path(base) / "proficiency-profile"


def clone_dir() -> Path:
    return _xdg("XDG_DATA_HOME", ".local/share")


def state_dir() -> Path:
    return _xdg("XDG_STATE_HOME", ".local/state")


def excluded_file() -> Path:
    return _xdg("XDG_CONFIG_HOME", ".config") / "excluded-repos"


def session_file() -> Path:
    return state_dir() / "session.json"


def today() -> dt.date:
    pinned = os.environ.get("PROFICIENCY_PROFILE_TODAY")
    if pinned:
        return dt.date.fromisoformat(pinned)
    return dt.datetime.now(dt.timezone.utc).date()


def midnight(day: dt.date) -> str:
    """Timestamps and commit dates are rounded down to midnight UTC."""
    return f"{day.isoformat()}T00:00:00Z"


def machine_id() -> str:
    """A random id for this machine, never derived from its hostname."""
    path = state_dir() / "machine-id"
    if not path.exists():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(secrets.token_hex(8) + "\n", encoding="utf-8")
    return path.read_text(encoding="utf-8").strip()


def profile_exists() -> bool:
    return (clone_dir() / "profile.json").is_file()


# --- The lock and session state ----------------------------------------------


@contextlib.contextmanager
def locked():
    """Hold the machine-wide writer lock: one writer appends or commits at once."""
    state_dir().mkdir(parents=True, exist_ok=True)
    with open(state_dir() / "lock", "a", encoding="utf-8") as handle:
        fcntl.flock(handle, fcntl.LOCK_EX)
        try:
            yield
        finally:
            fcntl.flock(handle, fcntl.LOCK_UN)


def load_session() -> dict | None:
    try:
        return json.loads(session_file().read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


def save_session(session: dict) -> None:
    session_file().parent.mkdir(parents=True, exist_ok=True)
    temporary = session_file().with_suffix(".tmp")
    temporary.write_text(json.dumps(session, indent=2) + "\n", encoding="utf-8")
    temporary.replace(session_file())


def recording(session: dict | None) -> bool:
    return bool(
        session
        and profile_exists()
        and not session.get("excluded")
        and not session.get("off_record")
    )


# --- Excluded repos ----------------------------------------------------------


def _repo_git(repo: Path, *args: str) -> str:
    result = subprocess.run(["git", "-C", str(repo), *args], capture_output=True, text=True)
    return result.stdout.strip() if result.returncode == 0 else ""


def repo_remote(repo: Path) -> str:
    """The repo's `origin` (else first) remote, normalized to `host/path`, or ""."""
    remotes = _repo_git(repo, "remote").split()
    if not remotes:
        return ""
    name = "origin" if "origin" in remotes else remotes[0]
    remote = _repo_git(repo, "remote", "get-url", name)
    return normalize_remote(remote) if remote else ""


def repo_key(repo: Path) -> str:
    """A hash naming a repository, from its remote URL, else its path.

    Only the hash is stored, so the excluded-repos file names no repository.
    """
    remote = repo_remote(repo)
    if remote:
        identity = "remote:" + remote
    else:
        top = _repo_git(repo, "rev-parse", "--show-toplevel") or str(repo)
        identity = "path:" + str(Path(top).resolve())
    return hashlib.sha256(identity.encode("utf-8")).hexdigest()


def normalize_remote(remote: str) -> str:
    """`host/path` for a remote, so SSH and HTTPS forms of one repo match."""
    remote = remote.strip()
    remote = re.sub(r"^[a-z][a-z0-9+.-]*://", "", remote, flags=re.I)  # scheme
    remote = re.sub(r"^[^/@]+@", "", remote)  # user or credentials
    remote = re.sub(r"^([^/:]+):(?!\d+/)", r"\1/", remote)  # scp-style host:path
    remote = re.sub(r"^([^/:]+):\d+/", r"\1/", remote)  # port
    remote = re.sub(r"(\.git)?/*$", "", remote)
    host, _, path = remote.partition("/")
    return f"{host.lower()}/{path}"


def excluded_keys() -> set[str]:
    try:
        return set(excluded_file().read_text(encoding="utf-8").split())
    except OSError:
        return set()


# --- Statements ----------------------------------------------------------------


def actor() -> dict:
    """The Linked Identity for the session's repo host, else the creation identity (§5)."""
    session = load_session() or {}
    identity = hosting.choose_actor(identities(), session.get("repo_kinds", []))
    return {
        "objectType": "Agent",
        "account": {"homePage": identity["homePage"], "name": identity["name"]},
    }


def statement(
    verb: str,
    object_iri: str,
    dimension: str,
    categories: list[str] = (),
    result: dict | None = None,
) -> dict:
    built: dict = {
        "id": str(uuid.uuid4()),
        "actor": actor(),
        "verb": {"id": VERBS[verb]},
        "object": {"objectType": "Activity", "id": object_iri},
    }
    if result is not None:
        built["result"] = result
    context: dict = {}
    if categories:
        context["contextActivities"] = {"category": [{"id": c} for c in categories]}
    context["extensions"] = {DIMENSION: dimension}
    built["context"] = context
    built["timestamp"] = midnight(today())
    validate(built)
    return built


def void_statement(target_id: str) -> dict:
    built = {
        "id": str(uuid.uuid4()),
        "actor": actor(),
        "verb": {"id": VERBS["voided"]},
        "object": {"objectType": "StatementRef", "id": target_id},
        "timestamp": midnight(today()),
    }
    validate(built)
    return built


UUID4 = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$")
MIDNIGHT = re.compile(r"^\d{4}-\d{2}-\d{2}T00:00:00Z$")


def validate(st: dict) -> None:
    """Refuse any Statement with a field the spec never writes (§2)."""
    def only(value, allowed: set[str], where: str) -> None:
        if not isinstance(value, dict) or not set(value) <= allowed:
            raise ValueError(f"{where} has fields outside {sorted(allowed)}")

    only(st, {"id", "actor", "verb", "object", "result", "context", "timestamp"}, "Statement")
    if not UUID4.match(st.get("id", "")):
        raise ValueError("id must be a random UUID v4")
    if not MIDNIGHT.match(st.get("timestamp", "")):
        raise ValueError("timestamp must be midnight UTC")
    only(st["actor"], {"objectType", "account"}, "actor")
    only(st["actor"]["account"], {"homePage", "name"}, "actor.account")
    only(st["verb"], {"id"}, "verb")
    if st["verb"]["id"] not in VERBS.values():
        raise ValueError(f"unknown verb {st['verb']['id']}")
    only(st["object"], {"objectType", "id"}, "object")
    if "result" in st:
        only(st["result"], {"success", "completion", "score"}, "result")
        if "score" in st["result"]:
            only(st["result"]["score"], {"scaled"}, "result.score")
    if "context" in st:
        only(st["context"], {"contextActivities", "extensions"}, "context")
        if "contextActivities" in st["context"]:
            only(st["context"]["contextActivities"], {"category"}, "contextActivities")
            for category in st["context"]["contextActivities"]["category"]:
                only(category, {"id"}, "category")
        extensions = st["context"].get("extensions", {})
        if set(extensions) != {DIMENSION} or extensions[DIMENSION] not in ("language", "harness"):
            raise ValueError("context.extensions must hold only the Dimension")


# --- The Evidence log ----------------------------------------------------------


def month_dir(day: dt.date) -> Path:
    return clone_dir() / "evidence" / f"{day.year:04d}" / f"{day.month:02d}"


def read_lines(path: Path) -> list[dict]:
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return []
    return [json.loads(line) for line in text.splitlines() if line.strip()]


def day_lines(day: dt.date) -> list[dict]:
    """Every machine's lines for the day, without voided lines and voids."""
    lines = []
    for path in sorted(month_dir(day).glob("*.jsonl")):
        lines += read_lines(path)
    voided = {
        line["object"]["id"] for line in lines if line["verb"]["id"] == VERBS["voided"]
    }
    return [
        line
        for line in lines
        if line["timestamp"] == midnight(day)
        and line["verb"]["id"] != VERBS["voided"]
        and line["id"] not in voided
    ]


def already_today(verb: str, object_iri: str) -> bool:
    return any(
        line["verb"]["id"] == VERBS[verb] and line["object"]["id"] == object_iri
        for line in day_lines(today())
    )


def append(session: dict | None, statements: list[dict]) -> None:
    """Append complete lines to this machine's file for each line's own month.

    Call under the lock. A session remembers each line's id, so it can count
    them at the debrief and discard them when going off the record. Released
    Held Evidence is appended with no session.
    """
    by_month: dict[Path, list[dict]] = {}
    for st in statements:
        day = dt.date.fromisoformat(st["timestamp"][:10])
        by_month.setdefault(month_dir(day) / f"{machine_id()}.jsonl", []).append(st)
    for path, group in by_month.items():
        path.parent.mkdir(parents=True, exist_ok=True)
        payload = "".join(json.dumps(st, separators=(",", ":")) + "\n" for st in group)
        with open(path, "a", encoding="utf-8") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
    if session is not None and statements:
        session.setdefault("lines", []).extend(st["id"] for st in statements)
        save_session(session)


def held_queue() -> held.Queue:
    return held.Queue(state_dir() / "held.json")


def record_or_hold(session: dict, statements: list[dict], vocab) -> list[dict]:
    """Append Statements whose ids are installed; hold the rest. Call under the lock.

    Aliased ids are rewritten to their targets first. Returns the appended ones.
    """
    queue = held_queue()
    ready, held_ids = [], []
    for st in statements:
        st, unknown = held.resolve_statement(st, vocab)
        if unknown:
            queue.hold(st, unknown)
            held_ids.append(st["id"])
        else:
            ready.append(st)
    if held_ids:
        queue.save()
        session.setdefault("lines", []).extend(held_ids)
        save_session(session)
    append(session, ready)
    return ready


def release_held(vocab) -> None:
    """Drop lines whose proposal PR was closed unmerged, and release installed ones. Call under the lock."""
    queue = held_queue()
    if not queue.lines:
        return
    for entry in queue.listing():
        if entry["status"] == "proposed" and entry.get("pr"):
            if hosting.pr_state(entry["pr"]) == "CLOSED":
                queue.drop_ref(entry["ref"])
    append(None, queue.release(vocab))
    queue.save()


def discard(ids: set[str]) -> None:
    """Remove uncommitted lines by id from this machine's files. Call under the lock."""
    for path in (clone_dir() / "evidence").rglob(f"{machine_id()}.jsonl"):
        kept = [line for line in path.read_text(encoding="utf-8").splitlines()
                if line.strip() and json.loads(line)["id"] not in ids]
        temporary = path.with_suffix(".tmp")
        temporary.write_text("".join(line + "\n" for line in kept), encoding="utf-8")
        temporary.replace(path)
        if not kept and not tracked(path):
            path.unlink()


# --- Git ---------------------------------------------------------------------


def run_git(*args: str, day: dt.date | None = None) -> subprocess.CompletedProcess:
    """Run git in the clone with hooks, signing and editors off, and rounded dates."""
    env = dict(os.environ, GIT_EDITOR="true", GIT_TERMINAL_PROMPT="0")
    if day is not None:
        env["GIT_AUTHOR_DATE"] = env["GIT_COMMITTER_DATE"] = midnight(day)
    return subprocess.run(
        ["git", "-c", "core.hooksPath=/dev/null", "-c", "commit.gpgsign=false",
         "-C", str(clone_dir()), *args],
        capture_output=True, text=True, env=env,
    )


def git(*args: str, day: dt.date | None = None, check: bool = True) -> str:
    result = run_git(*args, day=day)
    if check and result.returncode != 0:
        raise RuntimeError(f"git {' '.join(args)} failed: {result.stderr.strip()}")
    return result.stdout


def tracked(path: Path) -> bool:
    rel = path.relative_to(clone_dir()).as_posix()
    return bool(git("ls-files", "--", rel, check=False).strip())


def uncommitted_lines() -> list[dict]:
    """Evidence lines in the working tree that aren't in HEAD."""
    lines = []
    for path in sorted((clone_dir() / "evidence").rglob("*.jsonl")):
        rel = path.relative_to(clone_dir()).as_posix()
        committed = git("show", f"HEAD:{rel}", check=False)
        known = {json.loads(line)["id"] for line in committed.splitlines() if line.strip()}
        lines += [line for line in read_lines(path) if line["id"] not in known]
    return lines


def all_lines() -> list[dict]:
    """Every Evidence line, in file order (one file per machine per month)."""
    lines = []
    for path in sorted((clone_dir() / "evidence").rglob("*.jsonl")):
        lines += read_lines(path)
    return lines


def identities() -> list[dict]:
    profile = json.loads((clone_dir() / "profile.json").read_text(encoding="utf-8"))
    return profile["identities"]


def derived() -> derive.Derived:
    return derive.derive(all_lines() if profile_exists() else [], today())


def regenerate_readme() -> None:
    (clone_dir() / "README.md").write_text(
        readme.render(derived(), identities()), encoding="utf-8"
    )


def commit_evidence(label: str | None = None) -> int:
    """Commit uncommitted Evidence and the regenerated README as one commit. Call under the lock."""
    lines = uncommitted_lines()
    if not lines:
        return 0
    day = max(dt.date.fromisoformat(line["timestamp"][:10]) for line in lines)
    regenerate_readme()
    git("add", "--all", "--", "evidence", "README.md")
    git("commit", "-q", "-m", f"Evidence: {len(lines)} lines ({label or day.isoformat()})", day=day)
    return len(lines)


# --- Sync ------------------------------------------------------------------------


def has_remote() -> bool:
    return profile_exists() and "origin" in git("remote", check=False).split()


def pull() -> bool:
    """Fetch and rebase onto the remote, then regenerate the README. False when offline.

    Each machine writes only its own Evidence files, so README.md is the only
    file that can conflict: it is regenerated from the merged Evidence.
    """
    if run_git("fetch", "-q", "origin").returncode != 0:
        return False
    if not git("rev-parse", "--verify", "-q", "origin/main", check=False).strip():
        return True
    git("checkout", "--", "README.md", check=False)
    result = run_git("rebase", "--autostash", "--committer-date-is-author-date", "origin/main")
    while result.returncode != 0:
        conflicted = set(git("diff", "--name-only", "--diff-filter=U", check=False).split())
        if not conflicted or conflicted - {"README.md"}:
            run_git("rebase", "--abort")
            raise RuntimeError(f"rebase stopped on {sorted(conflicted) or result.stderr.strip()}")
        regenerate_readme()
        git("add", "README.md")
        result = run_git("rebase", "--continue")
    regenerate_readme()
    return True


def push() -> bool:
    """Push, rebasing and retrying when rejected. Never forces. False when offline."""
    for _ in range(3):
        result = run_git("push", "-q", "-u", "origin", "main")
        if result.returncode == 0:
            return True
        if not re.search(r"rejected|fetch first|non-fast-forward", result.stderr):
            return False
        if not pull():
            return False
    return False


def write_profile_json(profile: dict) -> None:
    (clone_dir() / "profile.json").write_text(json.dumps(profile, indent=2) + "\n", encoding="utf-8")


def read_profile_json() -> dict:
    return json.loads((clone_dir() / "profile.json").read_text(encoding="utf-8"))


def init_local(identity: dict, email: str, home_provider: str | None) -> None:
    """Create the local clone with its first commit. Call under the lock."""
    clone_dir().mkdir(parents=True, exist_ok=True)
    git("init", "-q", "-b", "main")
    git("config", "user.name", identity["name"])
    git("config", "user.email", email)
    write_profile_json({
        "schema_version": SCHEMA_VERSION,
        "home_provider": home_provider,
        "identities": [identity],
    })
    regenerate_readme()
    git("add", "README.md", "profile.json")
    git("commit", "-q", "-m", "Profile: created", day=today())


def connect(provider: hosting.Provider, login: str, user_id: int) -> None:
    """Create the private remote, set the noreply identity and push. Call under the lock."""
    url = provider.create(login)
    git("config", "user.email", provider.noreply(login, user_id))
    git("remote", "add", "origin", url)
    git("push", "-q", "-u", "origin", "main")


def not_signed_in(provider: hosting.Provider) -> str:
    return (f"Not signed in to {provider.cli}, so the profile stays on this machine. "
            f"The developer can run `{provider.cli} auth login`, then say \"add a remote\".")


# --- Commands ----------------------------------------------------------------


def write_use_line(session: dict, vocab=None) -> None:
    """The day's Harness `use` line, once per Harness per day. Call under the lock."""
    iri = NS + "harnesses/" + session["harness"]
    if not already_today("use", iri):
        use = statement("use", iri, "harness", result={"success": True, "score": {"scaled": 1.0}})
        record_or_hold(session, [use], vocab or vocabularies.load())


def cmd_create(args) -> int:
    """Create the Profile Repo after the developer's one approval.

    With --remote, the private remote is created too, or an existing one is
    cloned, if the host's CLI is signed in. Otherwise the profile is local-only.
    """
    if profile_exists():
        print("profile: exists")
        return 0
    kind = hosting.HOME_PROVIDERS[args.host]
    provider = hosting.Provider(kind)
    hint = None
    with locked():
        if args.remote and provider.signed_in():
            login, user_id = provider.user()
            url = provider.repo_url(login)
            if url:
                clone_dir().parent.mkdir(parents=True, exist_ok=True)
                subprocess.run(["git", "clone", "-q", url, str(clone_dir())],
                               capture_output=True, text=True, check=True)
                git("config", "user.name", login)
                git("config", "user.email", provider.noreply(login, user_id))
            else:
                init_local(hosting.identity(kind, login), provider.noreply(login, user_id), kind)
                connect(provider, login, user_id)
        else:
            if args.remote:
                hint = not_signed_in(provider)
            init_local(hosting.identity(kind, args.login), f"{args.login}@localhost", None)
        (state_dir() / "declined").unlink(missing_ok=True)
        session = load_session()
        if recording(session):
            write_use_line(session)
    print("profile: remote" if has_remote() else "profile: local-only")
    if hint:
        print(hint)
    return 0


def cmd_add_remote(args) -> int:
    """Connect a local-only profile to a new private remote."""
    if not profile_exists():
        print("No Proficiency Profile on this machine.", file=sys.stderr)
        return 1
    if has_remote():
        print("profile: remote")
        return 0
    kind = hosting.HOME_PROVIDERS[args.host]
    provider = hosting.Provider(kind)
    if not provider.signed_in():
        print("profile: local-only")
        print(not_signed_in(provider))
        return 0
    with locked():
        login, user_id = provider.user()
        if provider.repo_url(login):
            print(f"A Profile Repo already exists on {provider.label}; this machine's profile "
                  "stays local. Move this clone aside and create again to use that one.",
                  file=sys.stderr)
            return 1
        profile = read_profile_json()
        profile["home_provider"] = kind
        account = hosting.identity(kind, login)
        if account not in profile["identities"]:
            profile["identities"].append(account)
        write_profile_json(profile)
        regenerate_readme()
        git("add", "profile.json", "README.md")
        git("commit", "-q", "-m", f"Profile: Home Provider {kind}", day=today())
        connect(provider, login, user_id)
    print("profile: remote")
    return 0


def cmd_session_start(args) -> int:
    vocab = vocabularies.load()
    harness = vocab.resolve("harness", args.harness) or args.harness
    repo = Path(args.repo or ".").resolve()
    excluded = repo_key(repo) in excluded_keys()
    host = repo_remote(repo).partition("/")[0]
    session = {
        "harness": harness,
        "repo": repo_key(repo),
        "repo_kinds": hosting.repo_kinds(host),
        "excluded": excluded,
        "off_record": False,
        "lines": [],
    }
    with locked():
        if not excluded and profile_exists():
            commit_evidence("recovered")
            if has_remote():
                session["offline"] = not pull()
            release_held(vocab)
        save_session(session)
        if recording(session):
            write_use_line(session, vocab)
    if excluded:
        print("profile: excluded")
    elif has_remote():
        print("profile: remote")
    elif profile_exists():
        print("profile: local-only")
    elif (state_dir() / "declined").exists():
        print("profile: declined")
    else:
        print("profile: none")
    return 0


def cmd_record(args) -> int:
    session = load_session()
    if session is None:
        print("not recorded: no session; run session-start first", file=sys.stderr)
        return EXIT_NO_SESSION
    if not recording(session):
        return 0
    vocab = vocabularies.load()
    lang = vocab.resolve("language", args.lang) or args.lang
    categories = [NS + "languages/" + lang] + ([NS + "areas/" + args.area] if args.area else [])
    statements: list[dict] = []
    if args.event in ("experienced", "interacted", "drill"):
        iri = f"{NS}concepts/{lang}/{args.concept}"
        if args.event == "drill":
            success, scaled = GRADES[args.grade]
            statements.append(statement("practiced", iri, "language", categories,
                                        {"success": success, "score": {"scaled": scaled}}))
        else:
            statements.append(statement(args.event, iri, "language", categories))
    else:
        scaled = round(args.score / 5, 4)
        verb = "passed" if args.score >= 3.0 else "failed"
        for name in [c.strip() for c in args.concepts.split(",") if c.strip()]:
            # A teach-back's Concepts are Architecture Concepts unless the pack has the id.
            in_pack = vocab.resolve("concept", name, lang) is not None
            in_arch = vocab.resolve("concept", name, vocabularies.ARCH) is not None
            scope = lang if in_pack and not in_arch else vocabularies.ARCH
            statements.append(statement(verb, f"{NS}concepts/{scope}/{name}", "language", categories,
                                        {"success": verb == "passed", "score": {"scaled": scaled}}))
    with locked():
        session = load_session() or session
        if not recording(session):
            return 0
        if args.event == "interacted":
            resolved = [held.resolve_statement(st, vocab)[0] for st in statements]
            statements = [st for st in resolved if not already_today("interacted", st["object"]["id"])]
        record_or_hold(session, statements, vocab)
    return 0


def cmd_session_end(args) -> int:
    session = load_session()
    if session is None:
        print("Profile: no session in progress.")
        return 0
    with locked():
        count = commit_evidence() if recording(session) else 0
        pushed = push() if has_remote() else None
        session_file().unlink(missing_ok=True)
    if session.get("excluded"):
        print("Profile: not recorded, this repo is excluded.")
        return 0
    if session.get("off_record"):
        print("Profile: off the record, nothing recorded this session.")
        return 0
    if not profile_exists():
        return 0
    if pushed is None:
        where = "kept on this machine only."
    elif pushed:
        where = "pushed."
    else:
        where = "kept on this machine until it can sync."
    if not count:
        line = "Profile: nothing new recorded." + (
            "" if pushed is not False else " It will sync when this machine is back online.")
    elif pushed:
        line = f"Profile: {count} lines recorded and pushed."
    else:
        line = f"Profile: {count} lines recorded, {where}"
    print(" ".join([line, *debrief_offers(session, offer_remote=pushed is None)]))
    return 0


def debrief_offers(session: dict, offer_remote: bool) -> list[str]:
    """At most one offer to add a remote, and a one-time offer to link this host's account."""
    offers = []
    unchecked = held_queue().unchecked()
    if unchecked:
        items = "; ".join(
            f"{held.describe(e['ref'])} ({e['lines']} line{'s' if e['lines'] != 1 else ''})"
            for e in unchecked
        )
        offers.append(f"Held back, not in the profile yet: {items}. Check each names a public "
                      "technology or pattern, not something from this repo's own code.")
    home = hosting.kind_of(identities()[0])
    if offer_remote and home in ("github", "gitlab"):
        provider = hosting.Provider(home)
        if provider.signed_in():
            offers.append(f"It can be backed up to a private {provider.label} repo: "
                          "say \"add a remote\".")
    kinds = session.get("repo_kinds", [])
    linked = {hosting.kind_of(record) for record in identities()}
    offered_file = state_dir() / "link-offers"
    try:
        offered = set(offered_file.read_text(encoding="utf-8").split())
    except OSError:
        offered = set()
    if kinds and not linked & set(kinds) and kinds[0] not in offered:
        label = hosting.LABELS[kinds[0]]
        offers.append(f"Work here is under an {label} account that isn't linked: "
                      f"say \"link my {label} account\" to count it as yours."
                      if label[0] in "AEIOU" else
                      f"Work here is under a {label} account that isn't linked: "
                      f"say \"link my {label} account\" to count it as yours.")
        with open(offered_file, "a", encoding="utf-8") as handle:
            handle.write(kinds[0] + "\n")
    return offers


def stop_recording(session: dict, flag: str) -> None:
    """Discard the session's uncommitted lines and record nothing more. Call under the lock."""
    if profile_exists():
        ids = set(session.get("lines", []))
        discard(ids)
        queue = held_queue()
        queue.drop_ids(ids)
        queue.save()
    session[flag] = True
    session["lines"] = []
    save_session(session)


def cmd_off_the_record(args) -> int:
    with locked():
        session = load_session()
        if session is None:
            print("Profile: no session in progress.")
            return 0
        stop_recording(session, "off_record")
    print("Profile: off the record for the rest of this session.")
    return 0


def cmd_exclude_repo(args) -> int:
    key = repo_key(Path(args.repo or ".").resolve())
    with locked():
        if key not in excluded_keys():
            excluded_file().parent.mkdir(parents=True, exist_ok=True)
            with open(excluded_file(), "a", encoding="utf-8") as handle:
                handle.write(key + "\n")
        session = load_session()
        if session is not None and session.get("repo") == key:
            stop_recording(session, "excluded")
    print("Profile: this repo won't be recorded.")
    return 0


def cmd_void(args) -> int:
    session = load_session()
    if session is None:
        print("not voided: no session; run session-start first", file=sys.stderr)
        return EXIT_NO_SESSION
    if not recording(session):
        return 0
    with locked():
        session = load_session() or session
        if not recording(session):
            return 0
        known = {
            line["id"]
            for path in (clone_dir() / "evidence").rglob("*.jsonl")
            for line in read_lines(path)
        }
        if args.statement_id not in known:
            print(f"not voided: no line with id {args.statement_id}", file=sys.stderr)
            return EXIT_UNKNOWN_ID
        append(session, [void_statement(args.statement_id)])
    return 0


def cmd_lines(args) -> int:
    """List a day's lines, so a factually wrong one can be found and voided."""
    if not profile_exists():
        return 0
    day = dt.date.fromisoformat(args.day) if args.day else today()
    names = {iri: name for name, iri in VERBS.items()}
    for line in day_lines(day):
        print(f"{line['id']} {names[line['verb']['id']]} {line['object']['id'].removeprefix(NS)}")
    return 0


def cmd_read(args) -> int:
    """Levels and Currency as JSON, for a learning skill's triage."""
    result = derived()
    out: dict = {"model": derive.MODEL}
    if not args.lang:
        out["languages"] = {
            lang: {"counts": s.counts, "band": s.band, "last_exercised": _iso(s.last)}
            for lang, s in result.languages.items()
        }
        print(json.dumps(out, indent=2, ensure_ascii=False))
        return 0
    language = result.languages.get(args.lang)
    out.update(
        language=args.lang,
        counts=language.counts if language else {level: 0 for level in reversed(derive.LEVELS)},
        band=language.band if language else None,
        last_exercised=_iso(language.last) if language else None,
    )
    concepts = {c: s for (l, c), s in result.concepts.items() if l == args.lang}
    wanted = [c.strip() for c in args.concepts.split(",")] if args.concepts else sorted(concepts)
    out["concepts"] = {}
    for concept in wanted:
        state = concepts.get(concept)
        out["concepts"][concept] = {
            "level": state.level if state else None,
            "band": state.band if state else None,
            "last_exercised": _iso(state.last) if state else None,
        }
    out["due_for_refresh"] = [
        c for c, s in sorted(concepts.items())
        if s.level in ("Practiced", "Proven") and s.band in ("Fading", "Lapsed")
    ]
    print(json.dumps(out, indent=2, ensure_ascii=False))
    return 0


def _iso(day: dt.date | None) -> str | None:
    return day.isoformat() if day else None


def cmd_show(args) -> int:
    """"Show my profile": the README's header and Summary."""
    if not profile_exists():
        print("No Proficiency Profile on this machine.")
        return 0
    print(readme.summary(derived(), identities()), end="")
    return 0


def cmd_link(args) -> int:
    """Record a Linked Identity, so work under that account counts toward this profile."""
    if not profile_exists():
        print("No Proficiency Profile on this machine.", file=sys.stderr)
        return 1
    try:
        account = hosting.identity(args.kind, args.name, args.display)
    except ValueError as exc:
        print(f"not linked: {exc}", file=sys.stderr)
        return 2
    with locked():
        profile = read_profile_json()
        if account not in profile["identities"]:
            profile["identities"].append(account)
            write_profile_json(profile)
            regenerate_readme()
            git("add", "profile.json", "README.md")
            git("commit", "-q", "-m", "Profile: Linked Identity added", day=today())
    print(f"Profile: linked {readme.identity_label(account)}.")
    return 0


def cmd_sync(args) -> int:
    if not has_remote():
        print("Profile: kept on this machine only, nothing to sync.")
        return 0
    with locked():
        synced = pull() and push()
    print("Profile: synced." if synced else "Profile: offline, kept on this machine until it can sync.")
    return 0


def cmd_held(args) -> int:
    """List, confirm, discard or note the proposal PR for Held Evidence."""
    with locked():
        queue = held_queue()
        if args.action == "list":
            print(json.dumps(queue.listing(), indent=2))
            return 0
        if args.ref not in queue.refs:
            print(f"nothing held for {args.ref}", file=sys.stderr)
            return EXIT_UNKNOWN_ID
        if args.action == "discard":
            dropped = queue.drop_ref(args.ref)
            queue.save()
            print(f"Profile: dropped {dropped} held line{'s' if dropped != 1 else ''} "
                  f"for {held.describe(args.ref)}.")
        elif args.action == "confirm":
            queue.refs[args.ref]["status"] = "proposed"
            queue.save()
            print(json.dumps(held.draft(args.ref), indent=2, ensure_ascii=False))
        elif args.action == "pr":
            queue.refs[args.ref]["pr"] = args.url
            queue.save()
            print(f"Profile: noted the proposal for {held.describe(args.ref)}.")
    return 0


def cmd_decline(args) -> int:
    state_dir().mkdir(parents=True, exist_ok=True)
    (state_dir() / "declined").write_text(midnight(today()) + "\n", encoding="utf-8")
    print("Profile: not created. Ask again only when the developer brings it up.")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    commands = parser.add_subparsers(dest="command", required=True)

    create = commands.add_parser("create", help="create the local Profile Repo, after the developer's approval")
    create.add_argument("--host", choices=sorted(hosting.HOME_PROVIDERS), required=True)
    create.add_argument("--login", required=True,
                        help="the account login; with --remote, the signed-in CLI's login wins")
    create.add_argument("--remote", action="store_true",
                        help="also create the private remote, or clone an existing one")
    create.set_defaults(func=cmd_create)

    add_remote = commands.add_parser("add-remote", help="connect a local-only profile to a private remote")
    add_remote.add_argument("--host", choices=sorted(hosting.HOME_PROVIDERS), required=True)
    add_remote.set_defaults(func=cmd_add_remote)

    link = commands.add_parser("link", help="record a Linked Identity")
    link.add_argument("--kind", choices=sorted(hosting.KINDS), required=True)
    link.add_argument("--name", required=True,
                      help="login, or the Azure DevOps profile id GUID")
    link.add_argument("--display", help="Azure DevOps display name")
    link.set_defaults(func=cmd_link)

    commands.add_parser("sync", help="pull, then push").set_defaults(func=cmd_sync)

    start = commands.add_parser("session-start", help="begin a recording session")
    start.add_argument("--harness", required=True)
    start.add_argument("--repo")
    start.set_defaults(func=cmd_session_start)

    record = commands.add_parser("record", help="record one session event")
    events = record.add_subparsers(dest="event", required=True)
    for event in ("experienced", "interacted"):
        sub = events.add_parser(event)
        sub.add_argument("--concept", required=True)
    drill = events.add_parser("drill")
    drill.add_argument("--concept", required=True)
    drill.add_argument("--grade", choices=sorted(GRADES), required=True)
    teachback = events.add_parser("teachback")
    teachback.add_argument("--concepts", required=True)
    teachback.add_argument("--score", type=float, required=True)
    for sub in events.choices.values():
        sub.add_argument("--lang", required=True)
        sub.add_argument("--area")
    record.set_defaults(func=cmd_record)

    end = commands.add_parser("session-end", help="commit the session and print the debrief line")
    end.set_defaults(func=cmd_session_end)

    commands.add_parser(
        "off-the-record", help="discard this session's lines and stop recording"
    ).set_defaults(func=cmd_off_the_record)

    exclude = commands.add_parser("exclude-repo", help="never record in this repo")
    exclude.add_argument("--repo")
    exclude.set_defaults(func=cmd_exclude_repo)

    void = commands.add_parser("void", help="void a factually wrong line by its id")
    void.add_argument("statement_id")
    void.set_defaults(func=cmd_void)

    lines = commands.add_parser("lines", help="list a day's lines (default today) with their ids")
    lines.add_argument("--day", help="YYYY-MM-DD")
    lines.set_defaults(func=cmd_lines)

    read = commands.add_parser("read", help="levels and Currency as JSON, for triage")
    read.add_argument("--lang")
    read.add_argument("--concepts", help="comma-separated Concept ids (default: all)")
    read.set_defaults(func=cmd_read)

    commands.add_parser("show", help="print the profile summary").set_defaults(func=cmd_show)

    held_cmd = commands.add_parser("held", help="Held Evidence: list, confirm, discard, pr")
    held_actions = held_cmd.add_subparsers(dest="action", required=True)
    held_actions.add_parser("list")
    for action in ("confirm", "discard"):
        held_actions.add_parser(action).add_argument("ref")
    pr = held_actions.add_parser("pr")
    pr.add_argument("ref")
    pr.add_argument("url")
    held_cmd.set_defaults(func=cmd_held)

    commands.add_parser(
        "decline", help="remember that the developer declined a Profile Repo"
    ).set_defaults(func=cmd_decline)

    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
