"""Tests for the generated Profile Repo README (spec §11)."""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

import derive  # noqa: E402
import readme  # noqa: E402
from test_derive import Log, day  # noqa: E402

IDENTITIES = [
    {"homePage": "https://github.com", "name": "octo-learner"},
    {"homePage": "https://app.vssps.visualstudio.com",
     "name": "9b1f0000-0000-4000-8000-000000000000", "display": "Octo Learner"},
    {"homePage": "https://gitlab-self-managed.invalid", "name": "octo"},
]

EXPECTED = """# Proficiency Profile

GitHub · octo-learner · Azure DevOps · Octo Learner · GitLab self-managed · octo

## Summary

### csharp-dotnet

1 Proven · 1 Practiced · 1 Explored · 1 Introduced · 🟢 Current · last exercised 2026-01-14

- **Solid:** async.valuetask
- **Due for a refresh:** cqrs (architecture)
- **In progress:** 2 Concepts met but not yet recalled

## Languages

| Language | Proven | Practiced | Explored | Introduced | Currency |
|---|--:|--:|--:|--:|---|
| csharp-dotnet | 1 | 1 | 1 | 1 | 🟢 Current · 2026-01-14 |

## Areas

| Area | Proven | Practiced | Explored | Introduced | Last Exercised |
|---|--:|--:|--:|--:|---|
| backend | 1 | 0 | 0 | 1 | 2026-01-14 |

## Harnesses

| Harness | Days active | First used | Currency |
|---|--:|---|---|
| claude-code | 2 | 2026-01-05 | 🟢 Current · 2026-01-14 |
| codex | 1 | 2026-01-06 | 🔴 Lapsed · 2026-01-06 |

## Concepts

<details><summary><b>csharp-dotnet</b> (4 Concepts)</summary>

| Concept | Level | Currency |
|---|---|---|
| async.valuetask | Proven | 🟢 Current · 2026-01-14 |
| cqrs (architecture) | Practiced | 🔴 Lapsed · 2026-01-05 |
| lang.var | Explored | — |
| types.record | Introduced | — |

</details>

---

Levels: Introduced → Explored → Practiced → Proven. Currency: 🟢 Current · 🟡 Fading · 🔴 Lapsed · — no successful recall yet.

<sub>Generated 2026-02-04 from 10 Evidence lines. Proficiency and Currency are derived only from Evidence, never from self-claims. Currency model: FSRS-6, default parameters, stability capped at 365 days.</sub>
"""


def sample() -> Log:
    log = Log()
    log.use(0)
    log.use(1, "codex")
    log.teachback(0, "cqrs", 2.5)
    log.card(0, "types.record", areas=("backend",))
    log.weeds(0, "lang.var")
    log.drill(2, "async.valuetask", areas=("backend",))
    log.drill(2, "async.valuetask", "again", areas=("backend",))
    log.drill(9, "async.valuetask", areas=("backend",))
    log.drill(9, "async.valuetask", areas=("backend",))
    log.use(9)
    return log


class TheReadme(unittest.TestCase):
    def test_follows_the_spec_layout(self):
        derived = derive.derive(sample().lines, day(30))
        self.maxDiff = None
        self.assertEqual(readme.render(derived, IDENTITIES), EXPECTED)

    def test_an_empty_profile(self):
        derived = derive.derive([], day(0))
        text = readme.render(derived, IDENTITIES[:1])
        self.assertIn("No Evidence yet.", text)
        self.assertIn("Generated 2026-01-05 from 0 Evidence lines.", text)

    def test_summary_is_the_header_and_the_summary_section(self):
        derived = derive.derive(sample().lines, day(30))
        self.assertEqual(readme.summary(derived, IDENTITIES),
                         EXPECTED.split("\n## Languages")[0].rstrip() + "\n")


if __name__ == "__main__":
    unittest.main()
