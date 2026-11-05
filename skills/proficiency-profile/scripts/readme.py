#!/usr/bin/env python3
"""Render the Profile Repo README from derived values (spec §11). Standard library only.

The README is generated, never hand-edited. A band is always shown with its
Last Exercised date and never as a percentage.
"""
from __future__ import annotations

from derive import LEVELS, MODEL, Derived

ICON = {"Current": "🟢", "Fading": "🟡", "Lapsed": "🔴"}
HOST_LABELS = {
    "https://github.com": "GitHub",
    "https://gitlab.com": "GitLab",
    "https://app.vssps.visualstudio.com": "Azure DevOps",
    "https://github-enterprise.invalid": "GitHub Enterprise",
    "https://gitlab-self-managed.invalid": "GitLab self-managed",
}
COUNT_COLUMNS = list(reversed(LEVELS))  # Proven first


def identity_label(identity: dict) -> str:
    """`host · name`, as recorded in §5. Azure DevOps shows its display name."""
    home = identity["homePage"]
    host = HOST_LABELS.get(home)
    if host is None:
        host = home.removeprefix("https://").removesuffix(".invalid").replace("-", " ")
    return f"{host} · {identity.get('display') or identity['name']}"


def concept_label(concept: str) -> str:
    if concept.startswith("arch/"):
        return concept[len("arch/"):] + " (architecture)"
    return concept


def currency(band: str | None, last) -> str:
    return "—" if band is None else f"{ICON[band]} {band} · {last.isoformat()}"


def _plural(n: int, word: str) -> str:
    return f"{n} {word}" if n == 1 else f"{n} {word}s"


def _header(identities: list[dict]) -> list[str]:
    return ["# Proficiency Profile", "", " · ".join(identity_label(i) for i in identities), ""]


def _summary(derived: Derived) -> list[str]:
    out = ["## Summary", ""]
    if not derived.languages:
        return out + ["No Evidence yet.", ""]
    for lang, state in derived.languages.items():
        counts = " · ".join(f"{state.counts[level]} {level}" for level in COUNT_COLUMNS)
        status = counts
        if state.band:
            status += f" · {ICON[state.band]} {state.band} · last exercised {state.last.isoformat()}"
        out += [f"### {lang}", "", status, ""]
        concepts = sorted((c, s) for (l, c), s in derived.concepts.items() if l == lang)
        solid = [c for c, s in concepts if s.level == "Proven" and s.band == "Current"]
        refresh = [c for c, s in concepts
                   if s.level in ("Practiced", "Proven") and s.band in ("Fading", "Lapsed")]
        progress = [c for c, s in concepts if s.level in ("Introduced", "Explored")]
        lists = []
        if solid:
            lists.append("- **Solid:** " + ", ".join(concept_label(c) for c in solid))
        if refresh:
            lists.append("- **Due for a refresh:** " + ", ".join(concept_label(c) for c in refresh))
        if progress:
            lists.append(f"- **In progress:** {_plural(len(progress), 'Concept')} met but not yet recalled")
        if lists:
            out += lists + [""]
    return out


def _counts_table(first: str, last: str, rows: list[tuple[str, dict, str]]) -> list[str]:
    out = [f"| {first} | " + " | ".join(COUNT_COLUMNS) + f" | {last} |",
           "|---|" + "--:|" * len(COUNT_COLUMNS) + "---|"]
    for name, counts, tail in rows:
        out.append(f"| {name} | " + " | ".join(str(counts[c]) for c in COUNT_COLUMNS) + f" | {tail} |")
    return out


def render(derived: Derived, identities: list[dict]) -> str:
    out = _header(identities) + _summary(derived)

    out += ["## Languages", ""]
    if derived.languages:
        out += _counts_table("Language", "Currency", [
            (lang, s.counts, currency(s.band, s.last)) for lang, s in derived.languages.items()
        ])
    else:
        out.append("None yet.")
    out += ["", "## Areas", ""]
    if derived.areas:
        out += _counts_table("Area", "Last Exercised", [
            (area, s.counts, s.last.isoformat() if s.last else "—") for area, s in derived.areas.items()
        ])
    else:
        out.append("None yet.")
    out += ["", "## Harnesses", ""]
    if derived.harnesses:
        out += ["| Harness | Days active | First used | Currency |", "|---|--:|---|---|"]
        out += [f"| {h} | {s.days} | {s.first.isoformat()} | {currency(s.band, s.last)} |"
                for h, s in derived.harnesses.items()]
    else:
        out.append("None yet.")
    out += ["", "## Concepts", ""]
    if not derived.languages:
        out += ["None yet.", ""]
    for lang in derived.languages:
        rows = sorted(((c, s) for (l, c), s in derived.concepts.items() if l == lang),
                      key=lambda row: (-LEVELS.index(row[1].level), row[0]))
        out += [f"<details><summary><b>{lang}</b> ({_plural(len(rows), 'Concept')})</summary>", "",
                "| Concept | Level | Currency |", "|---|---|---|"]
        out += [f"| {concept_label(c)} | {s.level} | {currency(s.band, s.last)} |" for c, s in rows]
        out += ["", "</details>", ""]
    out += [
        "---",
        "",
        "Levels: Introduced → Explored → Practiced → Proven. "
        "Currency: 🟢 Current · 🟡 Fading · 🔴 Lapsed · — no successful recall yet.",
        "",
        f"<sub>Generated {derived.today.isoformat()} from {derived.lines} Evidence lines. "
        "Proficiency and Currency are derived only from Evidence, never from self-claims. "
        f"Currency model: {MODEL}.</sub>",
    ]
    return "\n".join(out) + "\n"


def summary(derived: Derived, identities: list[dict]) -> str:
    """What "show my profile" prints: the header and the Summary section."""
    return "\n".join(_header(identities) + _summary(derived)).rstrip() + "\n"
