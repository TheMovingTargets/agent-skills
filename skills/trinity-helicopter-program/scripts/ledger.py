#!/usr/bin/env python3
"""Concept ledger for the trinity-helicopter-program skill.

Stores, per learner and target language, which concepts the learner knows,
has been shown, has explored in depth, or has demonstrated fluency in, plus a
per-repository flight log of port units awaiting lessons. Standard library only.

Storage (outside any repository):
  ${XDG_DATA_HOME:-~/.local/share}/trinity-helicopter-program/<learner>/<lang>.json
  ${XDG_DATA_HOME:-~/.local/share}/trinity-helicopter-program/<learner>/flightlogs/<repo-slug>.jsonl

Learner id: $TRINITY_LEARNER, else `git config user.email`, else $USER. It is a
local key only; nothing is uploaded.
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
import re
import subprocess
import sys
from pathlib import Path

STATUSES = ["seen", "loaded", "explored", "known", "fluent"]
# Ordering used so a weaker status never overwrites a stronger one by accident.
RANK = {"seen": 0, "loaded": 1, "explored": 2, "known": 3, "fluent": 4}


def now() -> str:
    return dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat()


def learner_id() -> str:
    env = os.environ.get("TRINITY_LEARNER")
    if env:
        return env
    try:
        email = subprocess.run(
            ["git", "config", "--global", "user.email"],
            capture_output=True, text=True, timeout=5,
        ).stdout.strip()
        if email:
            return email
    except (OSError, subprocess.SubprocessError):
        pass
    return os.environ.get("USER") or os.environ.get("USERNAME") or "learner"


def slug(text: str) -> str:
    return re.sub(r"[^a-z0-9._-]+", "-", text.lower()).strip("-") or "x"


def root() -> Path:
    base = os.environ.get("XDG_DATA_HOME") or str(Path.home() / ".local" / "share")
    return Path(base) / "trinity-helicopter-program" / slug(learner_id())


def ledger_path(lang: str) -> Path:
    return root() / f"{slug(lang)}.json"


def load(lang: str) -> dict:
    path = ledger_path(lang)
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    return {
        "schema": 1,
        "learner": learner_id(),
        "language": lang,
        "profile": {"knows": [], "style": "terse cards, weeds on demand"},
        "concepts": {},
        "questions": [],
        "created": now(),
    }


def save(lang: str, data: dict) -> None:
    path = ledger_path(lang)
    path.parent.mkdir(parents=True, exist_ok=True)
    data["updated"] = now()
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    tmp.replace(path)


def cmd_show(a: argparse.Namespace) -> int:
    data = load(a.lang)
    exists = ledger_path(a.lang).exists()
    if a.json:
        print(json.dumps(data, indent=2))
        return 0
    print(f"learner: {data['learner']}  language: {a.lang}  ledger: {'found' if exists else 'new (not saved yet)'}")
    prof = data["profile"]
    print(f"knows: {', '.join(prof.get('knows') or []) or '(unset — ask once)'}  style: {prof.get('style')}")
    by: dict[str, list[str]] = {s: [] for s in STATUSES}
    for cid, c in sorted(data["concepts"].items()):
        by.setdefault(c["status"], []).append(cid + (f"(d{c['depth']})" if c.get("depth") else ""))
    for s in STATUSES:
        if by.get(s):
            print(f"{s} ({len(by[s])}): {', '.join(by[s])}")
    open_q = [q for q in data["questions"] if not q.get("resolved")]
    if open_q:
        print("open questions:")
        for i, q in enumerate(data["questions"]):
            if not q.get("resolved"):
                print(f"  [{i}] {q['text']}")
    return 0


def cmd_status(a: argparse.Namespace) -> int:
    data = load(a.lang)
    for cid in a.concepts:
        c = data["concepts"].get(cid)
        print(f"{cid}: {c['status'] if c else 'unseen'}" + (f" depth={c.get('depth', 0)}" if c else ""))
    return 0


def cmd_profile(a: argparse.Namespace) -> int:
    data = load(a.lang)
    if a.knows is not None:
        data["profile"]["knows"] = [k.strip() for k in a.knows.split(",") if k.strip()]
    if a.style is not None:
        data["profile"]["style"] = a.style
    save(a.lang, data)
    print(f"saved profile: {data['profile']}")
    return 0


def cmd_mark(a: argparse.Namespace) -> int:
    data = load(a.lang)
    for cid in a.concepts:
        c = data["concepts"].setdefault(cid, {"status": "seen", "depth": 0, "anchors": [], "first": now()})
        # `known` is the learner's own declaration: honoured over anything but a demonstrated `fluent`.
        skip_declared = a.status == "known" and c["status"] != "fluent"
        if skip_declared or a.force or RANK[a.status] >= RANK[c["status"]]:
            c["status"] = a.status
        if a.depth is not None:
            c["depth"] = max(c.get("depth", 0), a.depth)
        if a.anchor and a.anchor not in c["anchors"]:
            c["anchors"].append(a.anchor)
            c["anchors"] = c["anchors"][-10:]
        if a.repo:
            repos = c.setdefault("repos", [])
            if a.repo not in repos:
                repos.append(a.repo)
        c["last"] = now()
        print(f"{cid}: {c['status']} depth={c.get('depth', 0)}")
    save(a.lang, data)
    return 0


def cmd_unmark(a: argparse.Namespace) -> int:
    data = load(a.lang)
    for cid in a.concepts:
        data["concepts"].pop(cid, None)
        print(f"{cid}: cleared")
    save(a.lang, data)
    return 0


def cmd_question(a: argparse.Namespace) -> int:
    data = load(a.lang)
    if a.resolve is not None:
        data["questions"][a.resolve]["resolved"] = now()
        print(f"resolved [{a.resolve}]")
    elif a.text:
        data["questions"].append({"text": a.text, "asked": now()})
        print(f"recorded [{len(data['questions']) - 1}]")
    save(a.lang, data)
    return 0


def flightlog_path(repo: str) -> Path:
    repo_path = Path(repo).resolve()
    tag = hashlib.sha1(str(repo_path).encode()).hexdigest()[:8]
    return root() / "flightlogs" / f"{slug(repo_path.name)}-{tag}.jsonl"


def cmd_flightlog(a: argparse.Namespace) -> int:
    path = flightlog_path(a.repo)
    if a.append:
        parts = [p.strip() for p in a.append.split("|")]
        parts += [""] * (5 - len(parts))
        entry = {
            "unit": parts[0], "target": parts[1], "source": parts[2],
            "concepts": [c.strip() for c in parts[3].split(",") if c.strip()],
            "decisions": parts[4], "taught": False, "at": now(),
        }
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(entry) + "\n")
        print(f"queued lesson: {entry['unit']}")
        return 0
    entries = []
    if path.exists():
        entries = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    if a.taught is not None:
        entries[a.taught]["taught"] = now()
        path.write_text("".join(json.dumps(e) + "\n" for e in entries), encoding="utf-8")
        print(f"marked taught [{a.taught}]")
        return 0
    if not entries:
        print(f"flight log empty ({path})")
    for i, e in enumerate(entries):
        if a.pending and e.get("taught"):
            continue
        mark = "x" if e.get("taught") else " "
        print(f"[{i}] [{mark}] {e['unit']}  target={e['target']}  source={e['source']}")
        if e["concepts"]:
            print(f"       concepts: {', '.join(e['concepts'])}")
        if e["decisions"]:
            print(f"       decisions: {e['decisions']}")
    return 0


def main(argv: list[str]) -> int:
    p = argparse.ArgumentParser(prog="ledger.py", description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)

    s = sub.add_parser("show", help="profile, concepts by status, open questions")
    s.add_argument("--lang", required=True)
    s.add_argument("--json", action="store_true")
    s.set_defaults(fn=cmd_show)

    s = sub.add_parser("status", help="status of specific concept ids")
    s.add_argument("--lang", required=True)
    s.add_argument("concepts", nargs="+")
    s.set_defaults(fn=cmd_status)

    s = sub.add_parser("profile", help="set languages the learner knows and preferred style")
    s.add_argument("--lang", required=True)
    s.add_argument("--knows", help="comma-separated, e.g. rust,java,c++,typescript")
    s.add_argument("--style")
    s.set_defaults(fn=cmd_profile)

    s = sub.add_parser("mark", help="record a concept status")
    s.add_argument("--lang", required=True)
    s.add_argument("concepts", nargs="+", help="concept ids followed by the status as the last word")
    s.add_argument("--depth", type=int, help="deepest weeds rung reached (1-5+)")
    s.add_argument("--anchor", help="path:lines where it was taught")
    s.add_argument("--repo", help="repository name, for cross-repo history")
    s.add_argument("--force", action="store_true", help="allow downgrading a status")
    s.set_defaults(fn=cmd_mark)

    s = sub.add_parser("unmark", help="forget concepts (e.g. learner asked to relearn)")
    s.add_argument("--lang", required=True)
    s.add_argument("concepts", nargs="+")
    s.set_defaults(fn=cmd_unmark)

    s = sub.add_parser("question", help="record or resolve an open learner question")
    s.add_argument("--lang", required=True)
    s.add_argument("text", nargs="?")
    s.add_argument("--resolve", type=int, metavar="INDEX")
    s.set_defaults(fn=cmd_question)

    s = sub.add_parser("flightlog", help="per-repo queue of port units awaiting lessons")
    s.add_argument("--repo", default=".")
    g = s.add_mutually_exclusive_group()
    g.add_argument("--append", metavar="'unit|target|source|ids,comma|decisions'")
    g.add_argument("--show", action="store_true", default=True)
    g.add_argument("--taught", type=int, metavar="INDEX")
    s.add_argument("--pending", action="store_true", help="only untaught units")
    s.set_defaults(fn=cmd_flightlog)

    a = p.parse_args(argv)
    if a.cmd == "mark":
        if len(a.concepts) < 2 or a.concepts[-1] not in STATUSES:
            p.error(f"mark: last argument must be a status: {', '.join(STATUSES)}")
        a.status = a.concepts.pop()
    return a.fn(a)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
