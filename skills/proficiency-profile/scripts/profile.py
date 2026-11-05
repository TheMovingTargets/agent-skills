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
HOSTS = {"github.com": "https://github.com", "gitlab.com": "https://gitlab.com"}
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


def repo_key(repo: Path) -> str:
    """A hash naming a repository, from its remote URL, else its path.

    Only the hash is stored, so the excluded-repos file names no repository.
    """
    def git_out(*args: str) -> str:
        result = subprocess.run(
            ["git", "-C", str(repo), *args], capture_output=True, text=True
        )
        return result.stdout.strip() if result.returncode == 0 else ""

    remotes = git_out("remote").split()
    remote = ""
    if remotes:
        name = "origin" if "origin" in remotes else remotes[0]
        remote = git_out("remote", "get-url", name)
    if remote:
        identity = "remote:" + normalize_remote(remote)
    else:
        top = git_out("rev-parse", "--show-toplevel") or str(repo)
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
    profile = json.loads((clone_dir() / "profile.json").read_text(encoding="utf-8"))
    identity = profile["identities"][0]
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


def append(session: dict, statements: list[dict]) -> None:
    """Append complete lines to this machine's file for the current month.

    Call under the lock. The session remembers each line's id, so it can
    count them at the debrief and discard them when going off the record.
    """
    if not statements:
        return
    path = month_dir(today()) / f"{machine_id()}.jsonl"
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = "".join(json.dumps(st, separators=(",", ":")) + "\n" for st in statements)
    with open(path, "a", encoding="utf-8") as handle:
        handle.write(payload)
        handle.flush()
        os.fsync(handle.fileno())
    session.setdefault("lines", []).extend(st["id"] for st in statements)
    save_session(session)


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


def git(*args: str, day: dt.date | None = None, check: bool = True) -> str:
    """Run git in the clone with hooks and signing off, and rounded dates."""
    env = dict(os.environ)
    if day is not None:
        env["GIT_AUTHOR_DATE"] = env["GIT_COMMITTER_DATE"] = midnight(day)
    result = subprocess.run(
        ["git", "-c", "core.hooksPath=/dev/null", "-c", "commit.gpgsign=false",
         "-C", str(clone_dir()), *args],
        capture_output=True, text=True, env=env,
    )
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


def commit_evidence(label: str | None = None) -> int:
    """Commit uncommitted Evidence as one commit. Call under the lock."""
    lines = uncommitted_lines()
    if not lines:
        return 0
    day = max(dt.date.fromisoformat(line["timestamp"][:10]) for line in lines)
    git("add", "--all", "--", "evidence")
    git("commit", "-q", "-m", f"Evidence: {len(lines)} lines ({label or day.isoformat()})", day=day)
    return len(lines)


# --- Commands ----------------------------------------------------------------


def write_use_line(session: dict) -> None:
    """The day's Harness `use` line, once per Harness per day. Call under the lock."""
    iri = NS + "harnesses/" + session["harness"]
    if not already_today("use", iri):
        append(session, [statement("use", iri, "harness",
                                   result={"success": True, "score": {"scaled": 1.0}})])


def cmd_create(args) -> int:
    if profile_exists():
        print("profile: exists")
        return 0
    clone = clone_dir()
    clone.mkdir(parents=True, exist_ok=True)
    with locked():
        git("init", "-q", "-b", "main")
        git("config", "user.name", args.login)
        git("config", "user.email", f"{args.login}@localhost")
        profile = {
            "schema_version": SCHEMA_VERSION,
            "home_provider": None,
            "identities": [{"homePage": HOSTS[args.host], "name": args.login}],
        }
        (clone / "profile.json").write_text(json.dumps(profile, indent=2) + "\n", encoding="utf-8")
        (clone / "README.md").write_text(
            "# Proficiency Profile\n\nGenerated from Evidence. Never edit this file by hand.\n",
            encoding="utf-8",
        )
        git("add", "README.md", "profile.json")
        git("commit", "-q", "-m", "Profile: created", day=today())
        (state_dir() / "declined").unlink(missing_ok=True)
        session = load_session()
        if recording(session):
            write_use_line(session)
    print("profile: local-only")
    return 0


def cmd_session_start(args) -> int:
    vocab = vocabularies.load()
    harness = vocab.resolve("harness", args.harness)
    if harness is None:
        print(f"unknown Harness {args.harness!r}", file=sys.stderr)
        return EXIT_UNKNOWN_ID
    repo = Path(args.repo or ".").resolve()
    excluded = repo_key(repo) in excluded_keys()
    with locked():
        if profile_exists():
            commit_evidence("recovered")
        session = {
            "harness": harness,
            "repo": repo_key(repo),
            "excluded": excluded,
            "off_record": False,
            "lines": [],
        }
        save_session(session)
        if recording(session):
            write_use_line(session)
    if excluded:
        print("profile: excluded")
    elif profile_exists():
        print("profile: local-only")
    elif (state_dir() / "declined").exists():
        print("profile: declined")
    else:
        print("profile: none")
    return 0


def resolve_or_report(vocab, kind: str, id_: str, scope: str | None = None) -> str | None:
    resolved = vocab.resolve(kind, id_, scope)
    if resolved is None:
        where = f" in {scope}" if scope else ""
        print(f"not recorded: unknown {kind} {id_!r}{where}", file=sys.stderr)
    return resolved


def language_categories(vocab, args) -> list[str] | None:
    lang = resolve_or_report(vocab, "language", args.lang)
    if lang is None:
        return None
    categories = [NS + "languages/" + lang]
    if args.area:
        area = resolve_or_report(vocab, "area", args.area)
        if area is None:
            return None
        categories.append(NS + "areas/" + area)
    return categories


def cmd_record(args) -> int:
    session = load_session()
    if session is None:
        print("not recorded: no session; run session-start first", file=sys.stderr)
        return EXIT_NO_SESSION
    if not recording(session):
        return 0
    vocab = vocabularies.load()
    categories = language_categories(vocab, args)
    if categories is None:
        return EXIT_UNKNOWN_ID
    lang = categories[0].rsplit("/", 1)[1]
    status = 0
    statements: list[dict] = []
    if args.event in ("experienced", "interacted", "drill"):
        concept = resolve_or_report(vocab, "concept", args.concept, lang)
        if concept is None:
            return EXIT_UNKNOWN_ID
        iri = f"{NS}concepts/{lang}/{concept}"
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
            arch = vocab.resolve("concept", name, vocabularies.ARCH)
            if arch is not None:
                iri = f"{NS}concepts/arch/{arch}"
            else:
                concept = resolve_or_report(vocab, "concept", name, lang)
                if concept is None:
                    status = EXIT_UNKNOWN_ID
                    continue
                iri = f"{NS}concepts/{lang}/{concept}"
            statements.append(statement(verb, iri, "language", categories,
                                        {"success": verb == "passed", "score": {"scaled": scaled}}))
    with locked():
        session = load_session() or session
        if not recording(session):
            return 0
        if args.event == "interacted":
            statements = [st for st in statements
                          if not already_today("interacted", st["object"]["id"])]
        append(session, statements)
    return status


def cmd_session_end(args) -> int:
    session = load_session()
    if session is None:
        print("Profile: no session in progress.")
        return 0
    with locked():
        count = commit_evidence() if recording(session) else 0
        session_file().unlink(missing_ok=True)
    if session.get("excluded"):
        print("Profile: not recorded, this repo is excluded.")
    elif session.get("off_record"):
        print("Profile: off the record, nothing recorded this session.")
    elif not profile_exists():
        pass
    elif count:
        print(f"Profile: {count} lines recorded, kept on this machine only.")
    else:
        print("Profile: nothing new recorded.")
    return 0


def stop_recording(session: dict, flag: str) -> None:
    """Discard the session's uncommitted lines and record nothing more. Call under the lock."""
    if profile_exists():
        discard(set(session.get("lines", [])))
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


def cmd_decline(args) -> int:
    state_dir().mkdir(parents=True, exist_ok=True)
    (state_dir() / "declined").write_text(midnight(today()) + "\n", encoding="utf-8")
    print("Profile: not created. Ask again only when the developer brings it up.")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    commands = parser.add_subparsers(dest="command", required=True)

    create = commands.add_parser("create", help="create the local Profile Repo, after the developer's approval")
    create.add_argument("--host", choices=sorted(HOSTS), required=True)
    create.add_argument("--login", required=True)
    create.set_defaults(func=cmd_create)

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

    commands.add_parser(
        "decline", help="remember that the developer declined a Profile Repo"
    ).set_defaults(func=cmd_decline)

    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
