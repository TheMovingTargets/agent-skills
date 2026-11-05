#!/usr/bin/env python3
"""The installed Vocabularies for the proficiency-profile skill.

Finds the Vocabularies through the sibling-skill search and reads each one in
the language-pack table shape: ids are the first column of a table, in
backticks, and renames are `old.id → new.id` alias lines. Standard library only.

Where each Vocabulary lives:
  Languages           trinity-helicopter-program/references/languages/<pack>.md
                      (one Language per pack, named by the file)
  Language Concepts   the ids in that pack, scoped to its Language
  Architecture        cognitive-reload/references/architecture-concepts.md
                      (Concepts in the scope `arch`)
  Areas, Harnesses    proficiency-profile/references/{areas,harnesses}.md
"""
from __future__ import annotations

import argparse
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path

SKILL_DIR = Path(__file__).resolve().parents[1]
ARCH = "arch"

ROW = re.compile(r"^\s*\|\s*`([^`\s]+)`\s*\|")
# A whole line that is one rename, optionally in one pair of backticks.
# Lines that join several backticked ids with arrows, such as a pack's
# load order, are not aliases.
ALIAS = re.compile(r"^\s*(?:[-*]\s+)?`?([^`\s]+)\s*(?:→|->)\s*([^`\s]+?)`?\s*$")


@dataclass
class Vocabulary:
    ids: list[str] = field(default_factory=list)
    aliases: dict[str, str] = field(default_factory=dict)

    def resolve(self, id_: str) -> str | None:
        seen = set()
        while id_ not in self.ids:
            if id_ in seen or id_ not in self.aliases:
                return None
            seen.add(id_)
            id_ = self.aliases[id_]
        return id_


def parse(text: str) -> Vocabulary:
    """Read the table ids and alias lines of one Vocabulary file."""
    vocab = Vocabulary()
    for line in text.splitlines():
        row = ROW.match(line)
        if row:
            if row.group(1) not in vocab.ids:
                vocab.ids.append(row.group(1))
            continue
        alias = ALIAS.match(line)
        if alias:
            vocab.aliases[alias.group(1)] = alias.group(2)
    return vocab


def read(path: Path) -> Vocabulary:
    if not path.is_file():
        return Vocabulary()
    return parse(path.read_text(encoding="utf-8"))


def _version_key(path: Path) -> list:
    return [int(part) if part.isdigit() else part for part in re.split(r"(\d+)", path.name)]


def skill_search_dirs(skill_dir: Path, cwd: Path, home: Path) -> list[Path]:
    """Folders that may hold sibling skills, in the order they are searched.

    The same order Cognitive Reload with Trinity uses: this skill's own
    parent, the project's skill folders, the home skill folders, then the
    installed plugin caches, newest version first.
    """
    dirs = [
        skill_dir.parent,
        cwd / ".agents" / "skills",
        cwd / ".claude" / "skills",
        home / ".agents" / "skills",
        home / ".claude" / "skills",
        home / ".codex" / "skills",
    ]
    for harness in (".claude", ".codex"):
        cache = home / harness / "plugins" / "cache"
        versions = [path.parent for path in cache.glob("*/*/*/skills")]
        versions.sort(key=_version_key, reverse=True)
        dirs.extend(version / "skills" for version in versions)
    return dirs


def find_skill(name: str, search_dirs: list[Path]) -> Path | None:
    """The first installed skill called `name`: a folder with a SKILL.md."""
    for folder in search_dirs:
        candidate = folder / name
        if (candidate / "SKILL.md").is_file():
            return candidate
    return None


class Vocabularies:
    """Every installed Vocabulary, keyed by kind and, for Concepts, scope."""

    def __init__(
        self,
        concepts: dict[str, Vocabulary],
        areas: Vocabulary,
        harnesses: Vocabulary,
    ):
        self._concepts = concepts
        self._areas = areas
        self._harnesses = harnesses

    def languages(self) -> list[str]:
        return sorted(scope for scope in self._concepts if scope != ARCH)

    def concepts(self, scope: str) -> list[str]:
        """Concept ids in a scope: a Language's pack name, or `arch`."""
        return sorted(self._concepts.get(scope, Vocabulary()).ids)

    def areas(self) -> list[str]:
        return sorted(self._areas.ids)

    def harnesses(self) -> list[str]:
        return sorted(self._harnesses.ids)

    def aliases(self, scope: str) -> dict[str, str]:
        """The alias lines of a Concept scope, as old id → new id."""
        return dict(self._concepts.get(scope, Vocabulary()).aliases)

    def entries(self) -> list[str]:
        """Every installed id, one `kind [scope] id` line each."""
        lines = [f"language {lang}" for lang in self.languages()]
        for scope in [*self.languages(), ARCH]:
            lines += [f"concept {scope} {id_}" for id_ in self.concepts(scope)]
        lines += [f"area {id_}" for id_ in self.areas()]
        lines += [f"harness {id_}" for id_ in self.harnesses()]
        return lines

    def resolve(self, kind: str, id_: str, scope: str | None = None) -> str | None:
        """The installed id that `id_` names, following aliases, or None.

        `kind` is `language`, `concept`, `area` or `harness`. A Concept is
        resolved only within `scope`: its Language's pack name, or `arch`.
        """
        if kind == "language":
            return id_ if id_ in self.languages() else None
        if kind == "concept":
            vocab = self._concepts.get(scope or "")
        elif kind == "area":
            vocab = self._areas
        elif kind == "harness":
            vocab = self._harnesses
        else:
            raise ValueError(f"unknown Vocabulary kind: {kind}")
        return vocab.resolve(id_) if vocab else None


def load(
    skill_dir: Path = SKILL_DIR,
    cwd: Path | None = None,
    home: Path | None = None,
) -> Vocabularies:
    """Read every installed Vocabulary. A skill that isn't found gives none."""
    search = skill_search_dirs(skill_dir, cwd or Path.cwd(), home or Path.home())
    concepts: dict[str, Vocabulary] = {}
    trinity = find_skill("trinity-helicopter-program", search)
    if trinity:
        for pack in sorted((trinity / "references" / "languages").glob("*.md")):
            if pack.name == "README.md" or pack.stem == ARCH:
                continue
            concepts[pack.stem] = read(pack)
    reload = find_skill("cognitive-reload", search)
    concepts[ARCH] = (
        read(reload / "references" / "architecture-concepts.md")
        if reload
        else Vocabulary()
    )
    references = skill_dir / "references"
    return Vocabularies(
        concepts,
        read(references / "areas.md"),
        read(references / "harnesses.md"),
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="The installed Vocabularies.")
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("list", help="print every installed id")
    resolve = commands.add_parser(
        "resolve", help="print the installed id an id names, following aliases"
    )
    resolve.add_argument("kind", choices=["language", "concept", "area", "harness"])
    resolve.add_argument("id")
    resolve.add_argument("--scope", help="a Concept's Language pack name, or arch")
    args = parser.parse_args(argv)

    vocab = load()
    if args.command == "list":
        for line in vocab.entries():
            print(line)
        return 0
    resolved = vocab.resolve(args.kind, args.id, args.scope)
    if resolved is None:
        return 1
    print(resolved)
    return 0


if __name__ == "__main__":
    sys.exit(main())
