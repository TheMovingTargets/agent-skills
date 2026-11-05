#!/usr/bin/env python3
"""Derive Proficiency and Currency from the Evidence log. Standard library only.

Proficiency is a level per Concept within each Language: the highest ever
reached. Currency is FSRS-6 retrievability R with the 21 published default
parameters, no optimizer, and stability capped at 365 days after every update.
Retrievals are replayed as reviews, at most one per item per UTC day (the
day's first). The items are each Concept within a Language, each Language and
each Harness. Changing any of this means deliberately replaying the log.
"""
from __future__ import annotations

import datetime as dt
import math
from collections import defaultdict
from dataclasses import dataclass, field

NS = "https://w3id.org/devprof/"
ADL = "http://adlnet.gov/expapi/verbs/"
PRACTICED = NS + "verbs/practiced"
PASSED, FAILED = ADL + "passed", ADL + "failed"
EXPERIENCED, INTERACTED, VOIDED = ADL + "experienced", ADL + "interacted", ADL + "voided"
USE = "http://activitystrea.ms/schema/1.0/use"
RETRIEVALS = {PRACTICED, PASSED, FAILED}

MODEL = "FSRS-6, default parameters, stability capped at 365 days"
LEVELS = ["Introduced", "Explored", "Practiced", "Proven"]

# --- FSRS-6, transcribed from py-fsrs v6.3.2 (see research/currency-model.md) ---

W = (0.212, 1.2931, 2.3065, 8.2956, 6.4133, 0.8334, 3.0194, 0.001, 1.8722, 0.1666,
     0.796, 1.4835, 0.0614, 0.2629, 1.6483, 0.6014, 1.8729, 0.5425, 0.0912, 0.0658, 0.1542)
DECAY = -W[20]
FACTOR = 0.9 ** (1 / DECAY) - 1
AGAIN, HARD, GOOD, EASY = 1, 2, 3, 4
STABILITY_CAP = 365.0


def _clamp_d(d: float) -> float:
    return min(max(d, 1.0), 10.0)


def _clamp_s(s: float) -> float:
    return min(max(s, 0.001), STABILITY_CAP)


def _d0(grade: int) -> float:
    return W[4] - math.e ** (W[5] * (grade - 1)) + 1


def retrievability(stability: float, elapsed_days: int) -> float:
    return (1 + FACTOR * elapsed_days / stability) ** DECAY


def replay(reviews: list[tuple[int, int]]) -> tuple[float, int]:
    """(day ordinal, grade) reviews, sorted, one per day -> (stability, last day)."""
    s = d = last = None
    for day, g in reviews:
        if s is None:
            s, d = _clamp_s(W[g - 1]), _clamp_d(_d0(g))
        else:
            r = retrievability(s, day - last)
            if g == AGAIN:
                forget = W[11] * d ** -W[12] * ((s + 1) ** W[13] - 1) * math.e ** ((1 - r) * W[14])
                s = min(forget, s / math.e ** (W[17] * W[18]))
            else:
                hard = W[15] if g == HARD else 1
                easy = W[16] if g == EASY else 1
                s *= 1 + math.e ** W[8] * (11 - d) * s ** -W[9] * (math.e ** ((1 - r) * W[10]) - 1) * hard * easy
            s = _clamp_s(s)
            d = _clamp_d(W[7] * _d0(EASY) + (1 - W[7]) * (d + (10 - d) * -(W[6] * (g - 3)) / 9))
        last = day
    return s, last


def band_of(r: float) -> str:
    return "Current" if r >= 0.9 else "Fading" if r >= 0.7 else "Lapsed"


class Item:
    """One FSRS item: reviews on distinct days, the first retrieval of each day."""

    def __init__(self):
        self.by_day: dict[dt.date, int] = {}

    def review(self, day: dt.date, grade: int) -> None:
        self.by_day.setdefault(day, grade)

    def currency(self, today: dt.date) -> tuple[str | None, dt.date | None]:
        if not self.by_day:
            return None, None
        days = sorted(self.by_day)
        s, last = replay([(d.toordinal(), self.by_day[d]) for d in days])
        return band_of(retrievability(s, today.toordinal() - last)), days[-1]


# --- Evidence to reviews ---


def grade(line: dict) -> int:
    """The FSRS grade of a retrieval or `use` line (§3)."""
    verb = line["verb"]["id"]
    result = line.get("result", {})
    scaled = result.get("score", {}).get("scaled", 0.0)
    if verb == PRACTICED:
        if not result.get("success"):
            return AGAIN
        return GOOD if scaled >= 1.0 else HARD
    if verb in (PASSED, FAILED):
        return AGAIN if scaled < 0.4 else HARD if scaled < 0.6 else GOOD if scaled < 0.8 else EASY
    return GOOD


def _categories(line: dict, kind: str) -> list[str]:
    activities = line.get("context", {}).get("contextActivities", {})
    prefix = f"{NS}{kind}/"
    return [c["id"][len(prefix):] for c in activities.get("category", []) if c["id"].startswith(prefix)]


def _date(line: dict) -> dt.date:
    return dt.date.fromisoformat(line["timestamp"][:10])


@dataclass
class ConceptState:
    level: str
    band: str | None
    last: dt.date | None
    areas: list[str]


@dataclass
class LanguageState:
    counts: dict[str, int]
    band: str | None
    last: dt.date | None


@dataclass
class AreaState:
    counts: dict[str, int]
    last: dt.date | None


@dataclass
class HarnessState:
    band: str | None
    days: int
    first: dt.date
    last: dt.date


@dataclass
class Derived:
    today: dt.date
    lines: int
    concepts: dict[tuple[str, str], ConceptState] = field(default_factory=dict)
    languages: dict[str, LanguageState] = field(default_factory=dict)
    areas: dict[str, AreaState] = field(default_factory=dict)
    harnesses: dict[str, HarnessState] = field(default_factory=dict)


def _counts(states) -> dict[str, int]:
    counts = {level: 0 for level in reversed(LEVELS)}
    for state in states:
        counts[state.level] += 1
    return counts


def derive(lines: list[dict], today: dt.date) -> Derived:
    """Derive the profile from Evidence lines in log order (line order within a day)."""
    voided = {line["object"]["id"] for line in lines if line["verb"]["id"] == VOIDED}
    live = [line for line in lines if line["verb"]["id"] != VOIDED and line["id"] not in voided]
    live.sort(key=_date)  # stable: keeps line order within a day

    verbs: dict[tuple[str, str], set[str]] = defaultdict(set)
    good_days: dict[tuple[str, str], set[dt.date]] = defaultdict(set)
    hard_or_better: set[tuple[str, str]] = set()
    concept_items: dict[tuple[str, str], Item] = defaultdict(Item)
    concept_areas: dict[tuple[str, str], set[str]] = defaultdict(set)
    language_items: dict[str, Item] = defaultdict(Item)
    area_last: dict[str, dt.date] = {}
    harness_items: dict[str, Item] = defaultdict(Item)

    for line in live:
        verb, day = line["verb"]["id"], _date(line)
        if verb == USE:
            harness_items[line["object"]["id"].rsplit("/", 1)[1]].review(day, GOOD)
            continue
        languages = _categories(line, "languages")
        if not languages:
            continue
        lang = languages[0]
        key = (lang, line["object"]["id"][len(NS + "concepts/"):].removeprefix(lang + "/"))
        areas = _categories(line, "areas")
        verbs[key].add(verb)
        concept_areas[key].update(areas)
        if verb in RETRIEVALS:
            g = grade(line)
            concept_items[key].review(day, g)
            language_items[lang].review(day, g)
            for area in areas:
                area_last[area] = max(area_last.get(area, day), day)
            if g >= HARD:
                hard_or_better.add(key)
            if g >= GOOD:
                good_days[key].add(day)

    derived = Derived(today=today, lines=len(lines))
    for key in verbs:
        level = 0
        if INTERACTED in verbs[key]:
            level = 1
        if key in hard_or_better:
            level = 2
        days = sorted(good_days[key])
        if days and (days[-1] - days[0]).days >= 7:
            level = 3
        band, last = concept_items[key].currency(today)
        if level < 2:
            band = None  # no successful recall yet: shown as "—"
        derived.concepts[key] = ConceptState(LEVELS[level], band, last, sorted(concept_areas[key]))

    for lang in sorted({lang for lang, _ in derived.concepts}):
        band, last = language_items[lang].currency(today)
        states = [c for (l, _), c in derived.concepts.items() if l == lang]
        derived.languages[lang] = LanguageState(_counts(states), band, last)

    for area in sorted({a for c in derived.concepts.values() for a in c.areas}):
        states = [c for c in derived.concepts.values() if area in c.areas]
        derived.areas[area] = AreaState(_counts(states), area_last.get(area))

    for harness in sorted(harness_items):
        item = harness_items[harness]
        band, last = item.currency(today)
        days = sorted(item.by_day)
        derived.harnesses[harness] = HarnessState(band, len(days), days[0], last)
    return derived
