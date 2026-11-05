"""Tests for deriving Proficiency and Currency from invented Evidence.

The worked numbers come from the README prototype (agent-skills#22) and the
FSRS-6 simulation in the Currency research (agent-skills#16).
"""
from __future__ import annotations

import datetime as dt
import sys
import unittest
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

import derive  # noqa: E402

NS = "https://w3id.org/xapi/devprof/"
ADL = "http://adlnet.gov/expapi/verbs/"
DAY0 = dt.date(2026, 1, 5)


def day(n: int) -> dt.date:
    return DAY0 + dt.timedelta(days=n)


class Log:
    """Invented Evidence, built the way the writer builds it."""

    def __init__(self):
        self.lines: list[dict] = []

    def _add(self, n, verb, obj, lang=None, areas=(), result=None, dimension="language"):
        st = {
            "id": str(uuid.uuid4()),
            "actor": {"objectType": "Agent",
                      "account": {"homePage": "https://github.com", "name": "octo-learner"}},
            "verb": {"id": verb},
            "object": {"objectType": "Activity", "id": obj},
        }
        if result is not None:
            st["result"] = result
        categories = ([NS + "languages/" + lang] if lang else []) + [NS + "areas/" + a for a in areas]
        st["context"] = {"extensions": {NS + "extensions/dimension": dimension}}
        if categories:
            st["context"]["contextActivities"] = {"category": [{"id": c} for c in categories]}
        st["timestamp"] = f"{day(n).isoformat()}T00:00:00Z"
        self.lines.append(st)
        return st

    def card(self, n, concept, lang="csharp-dotnet", areas=()):
        return self._add(n, ADL + "experienced", f"{NS}concepts/{lang}/{concept}", lang, areas)

    def weeds(self, n, concept, lang="csharp-dotnet", areas=()):
        return self._add(n, ADL + "interacted", f"{NS}concepts/{lang}/{concept}", lang, areas)

    def drill(self, n, concept, grade="good", lang="csharp-dotnet", areas=()):
        result = {"good": {"success": True, "score": {"scaled": 1.0}},
                  "hard": {"success": True, "score": {"scaled": 0.5}},
                  "again": {"success": False, "score": {"scaled": 0.0}}}[grade]
        return self._add(n, NS + "verbs/practiced", f"{NS}concepts/{lang}/{concept}", lang, areas, result)

    def teachback(self, n, concept, score, lang="csharp-dotnet", areas=()):
        verb = "passed" if score >= 3.0 else "failed"
        return self._add(n, ADL + verb, f"{NS}concepts/arch/{concept}", lang, areas,
                         {"success": verb == "passed", "score": {"scaled": score / 5}})

    def use(self, n, harness="claude-code"):
        return self._add(n, "http://activitystrea.ms/schema/1.0/use", f"{NS}harnesses/{harness}",
                         result={"success": True, "score": {"scaled": 1.0}}, dimension="harness")

    def void(self, n, target):
        self.lines.append({
            "id": str(uuid.uuid4()),
            "actor": target["actor"],
            "verb": {"id": ADL + "voided"},
            "object": {"objectType": "StatementRef", "id": target["id"]},
            "timestamp": f"{day(n).isoformat()}T00:00:00Z",
        })

    def concept(self, on: int, concept="async.valuetask", lang="csharp-dotnet"):
        return derive.derive(self.lines, day(on)).concepts[(lang, concept)]

    def band(self, on: int, concept="async.valuetask"):
        return self.concept(on, concept).band


class Currency(unittest.TestCase):
    def test_one_good_drill_is_current_about_3_days_and_lapsed_after_about_22(self):
        log = Log()
        log.drill(0, "async.valuetask")
        self.assertEqual([log.band(n) for n in (0, 2, 3, 21, 22)],
                         ["Current", "Current", "Fading", "Fading", "Lapsed"])

    def test_a_second_drill_7_days_later_holds_off_lapsed_for_about_6_5_months(self):
        log = Log()
        log.drill(0, "async.valuetask")
        log.drill(7, "async.valuetask")
        self.assertEqual(log.band(7 + 21), "Current")
        self.assertEqual(log.band(7 + 22), "Fading")
        self.assertEqual(log.band(7 + 190), "Fading")   # about 6.2 months
        self.assertEqual(log.band(7 + 205), "Lapsed")   # about 6.7 months

    def test_drills_on_days_0_7_and_21_hold_off_lapsed_for_about_1_7_years(self):
        log = Log()
        for n in (0, 7, 21):
            log.drill(n, "async.valuetask")
        self.assertEqual(log.band(21 + int(1.6 * 365)), "Fading")
        self.assertEqual(log.band(21 + int(1.8 * 365)), "Lapsed")

    def test_stability_follows_the_research_simulation(self):
        # "Good on day 0, 3 and 10": S = 39 days, so R >= 0.9 until day 10 + 39.
        log = Log()
        for n in (0, 3, 10):
            log.drill(n, "async.valuetask")
        self.assertEqual(log.band(10 + 39), "Current")
        self.assertEqual(log.band(10 + 40), "Fading")

    def test_stability_is_capped_at_365_days(self):
        # Daily Good for a year reaches S of about 1020 days without the cap.
        log = Log()
        for n in range(365):
            log.drill(n, "async.valuetask")
        self.assertEqual(log.band(364 + 365), "Current")
        self.assertEqual(log.band(364 + 366), "Fading")

    def test_only_the_first_retrieval_of_a_day_is_a_review(self):
        good_first, again_first = Log(), Log()
        good_first.drill(0, "async.valuetask", "good")
        good_first.drill(0, "async.valuetask", "again")
        again_first.drill(0, "async.valuetask", "again")
        again_first.drill(0, "async.valuetask", "good")
        self.assertEqual(good_first.band(1), "Current")
        self.assertEqual(again_first.band(1), "Fading")

    def test_last_exercised_is_the_last_retrieval_day(self):
        log = Log()
        log.drill(0, "async.valuetask")
        log.card(5, "async.valuetask")
        log.drill(3, "async.valuetask", "hard")
        self.assertEqual(log.concept(10).last, day(3))


class Levels(unittest.TestCase):
    def level(self, log, concept="async.valuetask"):
        return log.concept(30, concept).level

    def test_a_card_is_introduced_with_no_currency(self):
        log = Log()
        log.card(0, "async.valuetask")
        self.assertEqual((self.level(log), log.band(30)), ("Introduced", None))

    def test_weeds_are_explored(self):
        log = Log()
        log.card(0, "async.valuetask")
        log.weeds(0, "async.valuetask")
        self.assertEqual(self.level(log), "Explored")

    def test_a_failed_retrieval_is_introduced_with_no_currency_but_counts_for_the_language(self):
        log = Log()
        log.drill(0, "async.valuetask", "again")
        derived = derive.derive(log.lines, day(1))
        concept = derived.concepts[("csharp-dotnet", "async.valuetask")]
        self.assertEqual((concept.level, concept.band), ("Introduced", None))
        self.assertIsNotNone(derived.languages["csharp-dotnet"].band)
        self.assertEqual(derived.languages["csharp-dotnet"].last, day(0))

    def test_a_hard_retrieval_is_practiced(self):
        log = Log()
        log.drill(0, "async.valuetask", "hard")
        self.assertEqual(self.level(log), "Practiced")

    def test_good_on_two_days_7_apart_is_proven(self):
        log = Log()
        log.drill(0, "async.valuetask")
        log.drill(7, "async.valuetask")
        self.assertEqual(self.level(log), "Proven")

    def test_good_on_two_days_6_apart_is_only_practiced(self):
        log = Log()
        log.drill(0, "async.valuetask")
        log.drill(6, "async.valuetask")
        log.drill(10, "async.valuetask", "hard")
        self.assertEqual(self.level(log), "Practiced")

    def test_the_highest_level_ever_reached_is_kept(self):
        log = Log()
        log.drill(0, "async.valuetask")
        log.drill(7, "async.valuetask")
        log.drill(8, "async.valuetask", "again")
        self.assertEqual(self.level(log), "Proven")
        # Without the failed drill, day 28 would still be Current (S of about 21 days).
        self.assertEqual(log.band(28), "Lapsed")

    def test_teachback_scores_map_to_grades(self):
        log = Log()
        log.teachback(0, "cqrs", 1.9)          # Again
        log.teachback(0, "rpc", 2.5)           # Hard
        log.teachback(0, "caching", 3.4)       # Good
        log.teachback(7, "caching", 4.0)       # Easy
        derived = derive.derive(log.lines, day(8))
        levels = {key[1]: c.level for key, c in derived.concepts.items()}
        self.assertEqual(levels, {"arch/cqrs": "Introduced", "arch/rpc": "Practiced",
                                  "arch/caching": "Proven"})

    def test_voided_lines_are_ignored(self):
        log = Log()
        wrong = log.drill(0, "async.valuetask")
        log.card(0, "types.record")
        log.void(1, wrong)
        derived = derive.derive(log.lines, day(2))
        self.assertEqual(list(derived.concepts), [("csharp-dotnet", "types.record")])
        self.assertIsNone(derived.languages["csharp-dotnet"].band)

    def test_a_concept_is_scoped_to_its_language(self):
        log = Log()
        log.drill(0, "async.task", lang="csharp-dotnet")
        log.card(0, "async.task", lang="rust")
        derived = derive.derive(log.lines, day(1))
        self.assertEqual(derived.concepts[("csharp-dotnet", "async.task")].level, "Practiced")
        self.assertEqual(derived.concepts[("rust", "async.task")].level, "Introduced")


class RollUps(unittest.TestCase):
    def test_language_counts_band_and_last_exercised(self):
        log = Log()
        log.card(0, "types.record")
        log.weeds(0, "lang.var")
        log.drill(0, "async.task", "hard")
        log.drill(2, "async.valuetask")
        log.drill(9, "async.valuetask")
        derived = derive.derive(log.lines, day(10))
        language = derived.languages["csharp-dotnet"]
        self.assertEqual(language.counts,
                         {"Proven": 1, "Practiced": 1, "Explored": 1, "Introduced": 1})
        self.assertEqual((language.band, language.last), ("Current", day(9)))

    def test_language_reviews_take_the_days_first_retrieval(self):
        log = Log()
        log.drill(0, "async.task", "again")
        log.drill(0, "async.valuetask", "good")
        derived = derive.derive(log.lines, day(1))
        self.assertEqual(derived.languages["csharp-dotnet"].band, "Fading")

    def test_area_counts_and_last_exercised(self):
        log = Log()
        log.card(0, "types.record", areas=("backend",))
        log.drill(4, "async.task", areas=("backend", "testing"))
        log.card(6, "lang.var", areas=("frontend",))
        derived = derive.derive(log.lines, day(10))
        self.assertEqual(derived.areas["backend"].counts,
                         {"Proven": 0, "Practiced": 1, "Explored": 0, "Introduced": 1})
        self.assertEqual(derived.areas["backend"].last, day(4))
        self.assertIsNone(derived.areas["frontend"].last)
        self.assertEqual(sorted(derived.areas), ["backend", "frontend", "testing"])

    def test_harness_days_first_last_and_band(self):
        log = Log()
        for n in (0, 1, 5):
            log.use(n)
        log.use(3, "codex")
        derived = derive.derive(log.lines, day(6))
        claude = derived.harnesses["claude-code"]
        self.assertEqual((claude.days, claude.first, claude.last), (3, day(0), day(5)))
        self.assertEqual(claude.band, "Current")
        self.assertEqual(derived.harnesses["codex"].band, "Fading")


if __name__ == "__main__":
    unittest.main()
