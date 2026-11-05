#!/usr/bin/env python3
"""Held Evidence: Statements naming an id that no installed Vocabulary has yet.

They wait in a queue on this machine, never in the Profile Repo. At the
debrief the developer checks each id names a public technology or pattern,
not something from the repo's own code. A confirmed id gets a drafted
Vocabulary PR. Once the id is installed, the lines are released into the
Profile Repo with their original timestamps. Standard library only.

A ref names one unknown id: `concept:<pack or arch>/<id>`, `language:<id>`,
`area:<id>` or `harness:<id>`.
"""
from __future__ import annotations

import json
from pathlib import Path

import vocabularies

NS = "https://w3id.org/xapi/devprof/"
REPO = "TheMovingTargets/agent-skills"
PACKS = "skills/trinity-helicopter-program/references/languages"


# --- Ids inside a Statement -------------------------------------------------


def _resolve(vocab, kind: str, id_: str, scope: str | None = None) -> str | None:
    return vocab.resolve(kind, id_, scope)


def resolve_statement(statement: dict, vocab) -> tuple[dict, list[str]]:
    """Rewrite aliased ids to their targets, and list the refs still unknown."""
    unknown: list[str] = []
    st = json.loads(json.dumps(statement))
    obj = st["object"]["id"]
    if obj.startswith(NS + "concepts/"):
        scope, _, concept = obj[len(NS + "concepts/"):].partition("/")
        resolved = _resolve(vocab, "concept", concept, scope)
        if resolved is None:
            unknown.append(f"concept:{scope}/{concept}")
        else:
            st["object"]["id"] = f"{NS}concepts/{scope}/{resolved}"
    elif obj.startswith(NS + "harnesses/"):
        harness = obj[len(NS + "harnesses/"):]
        resolved = _resolve(vocab, "harness", harness)
        if resolved is None:
            unknown.append(f"harness:{harness}")
        else:
            st["object"]["id"] = NS + "harnesses/" + resolved
    for category in st.get("context", {}).get("contextActivities", {}).get("category", []):
        for kind, prefix in (("language", NS + "languages/"), ("area", NS + "areas/")):
            if category["id"].startswith(prefix):
                id_ = category["id"][len(prefix):]
                resolved = _resolve(vocab, kind, id_)
                if resolved is None:
                    unknown.append(f"{kind}:{id_}")
                else:
                    category["id"] = prefix + resolved
    return st, sorted(set(unknown))


# --- Describing and proposing a ref ---------------------------------------------


def describe(ref: str) -> str:
    kind, _, rest = ref.partition(":")
    if kind == "concept":
        scope, _, concept = rest.partition("/")
        if scope == vocabularies.ARCH:
            return f"Architecture Concept `{concept}`"
        return f"Concept `{concept}` in {scope}"
    return f"{kind.capitalize()} `{rest}`"


def draft(ref: str) -> dict:
    """The Vocabulary PR for a confirmed ref: the file, the row and a generic title."""
    kind, _, rest = ref.partition(":")
    if kind == "concept":
        scope, _, concept = rest.partition("/")
        if scope == vocabularies.ARCH:
            file = "skills/cognitive-reload/references/architecture-concepts.md"
            row = f"| `{concept}` | <concept> | <typical signs in code> |"
        else:
            file = f"{PACKS}/{scope}.md"
            row = f"| `{concept}` | <concept> | <nearest analog> | <trap> |"
    elif kind == "area":
        file = "skills/proficiency-profile/references/areas.md"
        row = f"| `{rest}` | <area> | <covers> |"
    elif kind == "harness":
        file = "skills/proficiency-profile/references/harnesses.md"
        row = f"| `{rest}` | <harness> | <how the skill knows it> |"
    else:
        file = f"{PACKS}/{rest}.md"
        row = None
    title = f"Vocabulary: add {describe(ref).replace(' in ', ' to ')}"
    body = (
        f"Adds {describe(ref)} to `{file}`"
        + (", as a new language pack in the shape of `csharp-dotnet.md` (see `README.md` beside it)"
           if row is None else "")
        + ". A developer confirmed it names a public technology or pattern, not anything from a "
        "repository's own code. Generic wording only."
    )
    return {"ref": ref, "repo": REPO, "file": file, "row": row, "title": title, "body": body}


# --- The queue -------------------------------------------------------------------


class Queue:
    """held.json: the held Statements, and each ref's status and proposal PR."""

    def __init__(self, path: Path):
        self.path = path
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            data = {}
        self.lines: list[dict] = data.get("lines", [])
        self.refs: dict[str, dict] = data.get("refs", {})

    def save(self) -> None:
        live = {ref for line in self.lines for ref in line["refs"]}
        self.refs = {ref: info for ref, info in self.refs.items() if ref in live}
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self.path.with_suffix(".tmp")
        temporary.write_text(json.dumps({"lines": self.lines, "refs": self.refs}, indent=2) + "\n",
                             encoding="utf-8")
        temporary.replace(self.path)

    def hold(self, statement: dict, refs: list[str]) -> None:
        self.lines.append({"statement": statement, "refs": refs})
        for ref in refs:
            self.refs.setdefault(ref, {"status": "unchecked"})

    def listing(self) -> list[dict]:
        return [
            {"ref": ref, "lines": sum(ref in line["refs"] for line in self.lines),
             "status": info["status"], **({"pr": info["pr"]} if info.get("pr") else {})}
            for ref, info in sorted(self.refs.items())
        ]

    def unchecked(self) -> list[dict]:
        return [entry for entry in self.listing() if entry["status"] == "unchecked"]

    def drop_ref(self, ref: str) -> int:
        before = len(self.lines)
        self.lines = [line for line in self.lines if ref not in line["refs"]]
        self.refs.pop(ref, None)
        return before - len(self.lines)

    def drop_ids(self, ids: set[str]) -> None:
        self.lines = [line for line in self.lines if line["statement"]["id"] not in ids]

    def release(self, vocab) -> list[dict]:
        """Take out the lines whose ids are all installed now, rewritten through aliases."""
        released, kept = [], []
        for line in self.lines:
            statement, unknown = resolve_statement(line["statement"], vocab)
            if unknown:
                kept.append({**line, "refs": unknown})
            else:
                released.append(statement)
        self.lines = kept
        return released
