"""Tests for the Vocabulary parser, run on fixture packs."""
from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
SKILL = HERE.parent
sys.path.insert(0, str(SKILL / "scripts"))

import vocabularies  # noqa: E402

FIXTURES = HERE / "fixtures" / "siblings"
SKILL_NAMES = ["proficiency-profile", "trinity-helicopter-program", "cognitive-reload"]


def install(name: str, skills_dir: Path) -> Path:
    """Copy a fixture skill into skills_dir, with the SKILL.md the search needs.

    The fixtures carry no SKILL.md of their own, so a recursive skill scan of
    this repo never mistakes them for real skills.
    """
    target = skills_dir / name
    shutil.copytree(FIXTURES / name, target)
    (target / "SKILL.md").write_text(
        f"---\nname: {name}\ndescription: Fixture.\n---\n", encoding="utf-8"
    )
    return target


def setUpModule():
    global TMP
    TMP = Path(tempfile.mkdtemp())


def tearDownModule():
    shutil.rmtree(TMP)


def load_fixtures():
    """Load from the three fixture skills installed side by side."""
    skills = TMP / "siblings"
    if not skills.exists():
        for name in SKILL_NAMES:
            install(name, skills)
    return vocabularies.load(
        skill_dir=skills / "proficiency-profile", cwd=TMP / "cwd", home=TMP / "home"
    )


class ListsInstalledIds(unittest.TestCase):
    def test_one_language_per_pack_and_its_concepts(self):
        vocab = load_fixtures()
        self.assertEqual(vocab.languages(), ["tiny", "toy-lang"])
        self.assertEqual(
            vocab.concepts("toy-lang"),
            ["async.task", "async.value-task", "basics.hello", "basics.loop-for"],
        )
        self.assertEqual(vocab.concepts("tiny"), ["core.one"])

    def test_architecture_concepts_areas_and_harnesses(self):
        vocab = load_fixtures()
        self.assertEqual(vocab.concepts("arch"), ["layered-architecture", "pub-sub"])
        self.assertEqual(vocab.areas(), ["backend", "frontend"])
        self.assertEqual(vocab.harnesses(), ["claude-code", "codex"])


class ResolvesAliases(unittest.TestCase):
    def setUp(self):
        self.vocab = load_fixtures()

    def test_installed_id_resolves_to_itself(self):
        self.assertEqual(
            self.vocab.resolve("concept", "async.task", "toy-lang"), "async.task"
        )
        self.assertEqual(self.vocab.resolve("area", "backend"), "backend")
        self.assertEqual(self.vocab.resolve("harness", "codex"), "codex")
        self.assertEqual(self.vocab.resolve("language", "tiny"), "tiny")

    def test_alias_resolves_to_its_target(self):
        self.assertEqual(
            self.vocab.resolve("concept", "async.valuetask", "toy-lang"),
            "async.value-task",
        )
        self.assertEqual(
            self.vocab.resolve("concept", "publish-subscribe", "arch"), "pub-sub"
        )

    def test_alias_chain_resolves_to_the_last_target(self):
        self.assertEqual(
            self.vocab.resolve("concept", "async.old-task", "toy-lang"),
            "async.value-task",
        )

    def test_unknown_id_resolves_to_none(self):
        self.assertIsNone(self.vocab.resolve("concept", "async.nope", "toy-lang"))
        self.assertIsNone(self.vocab.resolve("area", "gamedev"))
        self.assertIsNone(self.vocab.resolve("language", "cobol"))

    def test_concept_is_scoped_to_its_language(self):
        self.assertIsNone(self.vocab.resolve("concept", "core.one", "toy-lang"))
        self.assertIsNone(self.vocab.resolve("concept", "pub-sub", "toy-lang"))

    def test_only_whole_alias_lines_are_aliases(self):
        # The load-order lines join ids with arrows too, and must not count.
        self.assertEqual(
            self.vocab.aliases("toy-lang"),
            {"async.valuetask": "async.value-task", "async.old-task": "async.valuetask"},
        )

    def test_alias_cycle_resolves_to_none(self):
        self.assertIsNone(self.vocab.resolve("concept", "core.a", "tiny"))


class FindsVocabulariesThroughTheSiblingSkillSearch(unittest.TestCase):
    """Trinity and Cognitive Reload may be installed somewhere other than
    next to this skill, as Cognitive Reload with Trinity already allows."""

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tmp)
        self.project = self.tmp / "project"
        self.home = self.tmp / "home"
        self.skill = install("proficiency-profile", self.tmp / "alone")

    def install(self, name: str, skills_dir: Path) -> None:
        install(name, skills_dir)

    def load(self):
        return vocabularies.load(
            skill_dir=self.skill, cwd=self.project, home=self.home
        )

    def test_finds_skills_in_project_and_home_folders(self):
        self.install("cognitive-reload", self.project / ".agents" / "skills")
        self.install("trinity-helicopter-program", self.home / ".codex" / "skills")
        vocab = self.load()
        self.assertEqual(vocab.languages(), ["tiny", "toy-lang"])
        self.assertEqual(vocab.concepts("arch"), ["layered-architecture", "pub-sub"])

    def test_sibling_folder_comes_before_home_folders(self):
        self.install("trinity-helicopter-program", self.skill.parent)
        other = self.home / ".claude" / "skills"
        self.install("trinity-helicopter-program", other)
        (other / "trinity-helicopter-program" / "references" / "languages" / "tiny.md").unlink()
        self.assertEqual(self.load().languages(), ["tiny", "toy-lang"])

    def test_finds_skills_in_the_newest_plugin_cache(self):
        cache = self.home / ".claude" / "plugins" / "cache" / "market" / "plugin"
        self.install("trinity-helicopter-program", cache / "0.9.0" / "skills")
        self.install("trinity-helicopter-program", cache / "0.10.0" / "skills")
        (cache / "0.9.0" / "skills" / "trinity-helicopter-program" / "references"
         / "languages" / "tiny.md").unlink()
        self.assertEqual(self.load().languages(), ["tiny", "toy-lang"])

    def test_a_folder_without_skill_md_is_not_a_skill(self):
        (self.skill.parent / "trinity-helicopter-program").mkdir()
        self.install("trinity-helicopter-program", self.home / ".agents" / "skills")
        self.assertEqual(self.load().languages(), ["tiny", "toy-lang"])

    def test_missing_skills_give_empty_vocabularies(self):
        vocab = self.load()
        self.assertEqual(vocab.languages(), [])
        self.assertEqual(vocab.concepts("arch"), [])
        self.assertEqual(vocab.areas(), ["backend", "frontend"])


class TheSeededVocabularies(unittest.TestCase):
    """The Vocabularies this repo ships, with the seeds the spec names."""

    def setUp(self):
        self.vocab = vocabularies.load(cwd=TMP / "cwd", home=TMP / "home")

    def test_architecture_concepts(self):
        self.assertEqual(
            self.vocab.concepts("arch"),
            sorted([
                "layered-architecture", "hexagonal-ports", "dependency-injection",
                "repository-pattern", "cqrs", "event-sourcing", "pub-sub",
                "message-queue", "request-response-api", "rpc",
                "middleware-pipeline", "background-jobs", "state-machine",
                "plugin-architecture", "caching", "retry-backoff", "idempotency",
                "circuit-breaker",
            ]),
        )

    def test_architecture_concepts_have_no_aliases_yet(self):
        self.assertEqual(self.vocab.aliases("arch"), {})

    def test_areas(self):
        self.assertEqual(
            self.vocab.areas(),
            sorted([
                "frontend", "backend", "data", "infrastructure", "mobile",
                "systems", "testing", "security", "tooling", "ai",
            ]),
        )

    def test_harnesses(self):
        self.assertEqual(self.vocab.harnesses(), ["claude-code", "codex"])

    def test_the_csharp_pack(self):
        self.assertIn("csharp-dotnet", self.vocab.languages())
        concepts = self.vocab.concepts("csharp-dotnet")
        self.assertEqual(len(concepts), 87)
        self.assertIn("async.valuetask", concepts)
        self.assertEqual(self.vocab.aliases("csharp-dotnet"), {})


class CommandLine(unittest.TestCase):
    """`vocabularies.py list` and `resolve`, on the Vocabularies this repo ships."""

    def run_cli(self, *args):
        env = {**os.environ, "HOME": str(TMP / "home")}
        return subprocess.run(
            [sys.executable, str(SKILL / "scripts" / "vocabularies.py"), *args],
            capture_output=True, text=True, cwd=TMP, env=env, check=False,
        )

    def test_list_prints_every_installed_id(self):
        result = self.run_cli("list")
        self.assertEqual(result.returncode, 0, result.stderr)
        lines = result.stdout.splitlines()
        for line in [
            "language csharp-dotnet",
            "concept csharp-dotnet proj.csproj",
            "concept csharp-dotnet async.valuetask",
            "concept arch circuit-breaker",
            "area ai",
            "harness claude-code",
        ]:
            self.assertIn(line, lines)
        self.assertEqual(len(lines), 1 + 87 + 18 + 10 + 2)

    def test_resolve_prints_the_installed_id(self):
        result = self.run_cli("resolve", "concept", "cqrs", "--scope", "arch")
        self.assertEqual((result.returncode, result.stdout), (0, "cqrs\n"))

    def test_resolve_fails_on_an_unknown_id(self):
        result = self.run_cli("resolve", "area", "gamedev")
        self.assertEqual((result.returncode, result.stdout), (1, ""))


if __name__ == "__main__":
    unittest.main()
