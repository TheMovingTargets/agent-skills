#!/usr/bin/env python3
"""PROTOTYPE, throwaway. Answers "Prototype: the Profile Repo README" (agent-skills#22).

Three structurally different generated READMEs for one Profile Repo, all derived from the
same sample Evidence log by the rules settled in #18 (what Evidence the skills emit) and
#20 (Proficiency levels and Currency display).

    python3 prototypes/profile-readme/render.py            # writes sample-evidence.jsonl + README-A/B/C.md
    python3 prototypes/profile-readme/render.py --variant B   # print one variant to stdout

Stdlib only. Not production code: no tests, no validation, sample data is invented.
"""
import json, math, random, sys, uuid
from collections import defaultdict
from datetime import date, timedelta
from pathlib import Path

HERE = Path(__file__).parent
TODAY = date(2026, 11, 4)
NS = "https://example.org/xapi/devprof"
V = {
    "experienced": "http://adlnet.gov/expapi/verbs/experienced",
    "interacted": "http://adlnet.gov/expapi/verbs/interacted",
    "practiced": f"{NS}/verbs/practiced",
    "passed": "http://adlnet.gov/expapi/verbs/passed",
    "failed": "http://adlnet.gov/expapi/verbs/failed",
    "use": "http://activitystrea.ms/use",
}
LANG_NAMES = {"csharp": "C# / .NET", "typescript": "TypeScript", "python": "Python"}
HARNESS_NAMES = {"claude-code": "Claude Code", "codex": "Codex"}

# ---------------------------------------------------------------- FSRS-6 (from research/currency-model.md)
W = (0.212, 1.2931, 2.3065, 8.2956, 6.4133, 0.8334, 3.0194, 0.001, 1.8722, 0.1666,
     0.796, 1.4835, 0.0614, 0.2629, 1.6483, 0.6014, 1.8729, 0.5425, 0.0912, 0.0658, 0.1542)
DECAY = -W[20]
FACTOR = 0.9 ** (1 / DECAY) - 1
AGAIN, HARD, GOOD, EASY = 1, 2, 3, 4
S_CAP = 365.0  # decided in #20


def clamp_d(d): return min(max(d, 1.0), 10.0)
def clamp_s(s): return min(max(s, 0.001), S_CAP)
def d0(g): return W[4] - math.e ** (W[5] * (g - 1)) + 1
def retrievability(s, t): return (1 + FACTOR * t / s) ** DECAY


def replay(events):
    s = d = last = None
    for day, g in events:
        if s is None:
            s, d = clamp_s(W[g - 1]), clamp_d(d0(g))
        else:
            r = retrievability(s, day - last)
            if g == AGAIN:
                long = W[11] * d ** -W[12] * ((s + 1) ** W[13] - 1) * math.e ** ((1 - r) * W[14])
                s = min(long, s / math.e ** (W[17] * W[18]))
            else:
                hard = W[15] if g == HARD else 1
                easy = W[16] if g == EASY else 1
                s *= 1 + math.e ** W[8] * (11 - d) * s ** -W[9] * (math.e ** ((1 - r) * W[10]) - 1) * hard * easy
            s = clamp_s(s)
            d = clamp_d(W[7] * d0(EASY) + (1 - W[7]) * (d + (10 - d) * -(W[6] * (g - 3)) / 9))
        last = day
    return s, d, last


def band(events):
    """events: [(date, grade)] -> (band, last_exercised) or (None, None)."""
    if not events:
        return None, None
    per_day = {}
    for dt, g in sorted(events):
        per_day.setdefault(dt, g)  # first retrieval of the day (#16)
    days = sorted(per_day)
    s, _, last = replay([(dt.toordinal(), per_day[dt]) for dt in days])
    r = retrievability(s, TODAY.toordinal() - last)
    return ("Current" if r >= 0.9 else "Fading" if r >= 0.7 else "Lapsed"), days[-1]


# ---------------------------------------------------------------- sample Evidence (invented)
def stmt(day, verb, obj, lang=None, harness="claude-code", areas=(), dim="language", result=None):
    cats = []
    if lang: cats.append({"id": f"{NS}/languages/{lang}"})
    if harness: cats.append({"id": f"{NS}/harnesses/{harness}"})
    cats += [{"id": f"{NS}/areas/{a}"} for a in areas]
    s = {
        "id": str(uuid.UUID(int=random.getrandbits(128))),
        "actor": {"objectType": "Agent", "account": {"homePage": "https://github.com", "name": "sample-dev"}},
        "verb": {"id": V[verb], "display": {"en": verb}},
        "object": {"objectType": "Activity", "id": obj},
        "context": {"contextActivities": {"category": cats}, "extensions": {f"{NS}/extensions/dimension": dim}},
        "timestamp": f"{day.isoformat()}T00:00:00.000Z",
    }
    if result: s["result"] = result
    return s


def sample():
    random.seed(7)
    out = []
    C = lambda slug: f"{NS}/concepts/{slug}"
    d = lambda y, m, dd: date(y, m, dd)

    # TypeScript: strong earlier in the year via Cognitive Reload teach-backs, idle since spring.
    ts = ["async-await", "discriminated-unions", "conditional-types", "event-loop", "esm-modules",
          "zod-schemas", "generics", "error-handling"]
    for i, c in enumerate(ts):
        out.append(stmt(d(2026, 2, 2 + i), "experienced", C(c), "typescript", areas=("backend",)))
    for day in (d(2026, 2, 20), d(2026, 3, 9), d(2026, 4, 14)):
        for c in ts[:5]:
            out.append(stmt(day, "passed", C(c), "typescript", areas=("backend",),
                            result={"success": True, "score": {"scaled": 0.72}}))
    out.append(stmt(d(2026, 3, 9), "passed", C("hexagonal-ports"), "typescript", areas=("backend",),
                    result={"success": True, "score": {"scaled": 0.84}}))
    out.append(stmt(d(2026, 4, 14), "passed", C("hexagonal-ports"), "typescript", areas=("backend",),
                    result={"success": True, "score": {"scaled": 0.76}}))
    out.append(stmt(d(2026, 3, 20), "experienced", C("react-server-components"), "typescript", areas=("frontend",)))

    # C#: the current port. Lots of cards, weeds, and drills over Oct-Nov.
    cs = ["async-await", "valuetask", "nullable-reference-types", "records", "pattern-matching",
          "linq-deferred-execution", "di-lifetimes", "iasyncenumerable", "span-of-t", "using-declarations",
          "struct-copy-semantics", "configureawait", "cancellation-tokens", "ihostedservice", "minimal-apis",
          "throw-vs-throw-ex", "source-generators", "generic-variance"]
    start = d(2026, 9, 28)
    for i, c in enumerate(cs):
        day = start + timedelta(days=i * 2)
        area = ("infrastructure",) if c in ("ihostedservice", "di-lifetimes") else ("backend",) if i % 3 else ()
        out.append(stmt(day, "experienced", C(c), "csharp", areas=area))
        if i % 3 == 0:
            out.append(stmt(day, "interacted", C(c), "csharp", areas=area))
    drills = [  # (concept, [(date, scaled)]) : 1.0 idiomatic=Good, 0.6 correct-not-idiomatic=Hard, 0 wrong=Again
        ("async-await", [(d(2026, 10, 2), 1.0), (d(2026, 10, 12), 1.0), (d(2026, 11, 2), 1.0)]),
        ("nullable-reference-types", [(d(2026, 10, 3), 0.6), (d(2026, 10, 14), 1.0), (d(2026, 10, 28), 1.0)]),
        ("records", [(d(2026, 10, 6), 1.0)]),
        ("linq-deferred-execution", [(d(2026, 10, 8), 0.0), (d(2026, 10, 8), 1.0), (d(2026, 10, 20), 1.0)]),
        ("struct-copy-semantics", [(d(2026, 10, 18), 0.0)]),
        ("di-lifetimes", [(d(2026, 10, 16), 0.6)]),
        ("cancellation-tokens", [(d(2026, 10, 22), 1.0), (d(2026, 10, 30), 1.0)]),
    ]
    for c, attempts in drills:
        for day, sc in attempts:
            out.append(stmt(day, "practiced", C(c), "csharp", areas=("backend",),
                            result={"success": sc > 0, "score": {"scaled": sc}}))
    # A Cognitive Reload teach-back on the ported service, area_score 3.4/5 -> Good
    for c in ("event-sourcing", "async-await", "di-lifetimes"):
        out.append(stmt(d(2026, 10, 24), "passed", C(c), "csharp", areas=("backend",),
                        result={"success": True, "score": {"scaled": 0.68}}))

    # Python: a little exposure, one drill months ago.
    for c in ("asyncio", "type-hints", "dataclasses", "context-managers"):
        out.append(stmt(d(2026, 5, 11), "experienced", C(c), "python", harness="codex", areas=("infrastructure",)))
    out.append(stmt(d(2026, 5, 12), "practiced", C("context-managers"), "python", harness="codex",
                    areas=("infrastructure",), result={"success": True, "score": {"scaled": 1.0}}))

    # Harness `use`: one line per Harness per day a learning skill ran (#18).
    days = set()
    for s in out:
        h = next(c["id"].rsplit("/", 1)[1] for c in s["context"]["contextActivities"]["category"] if "/harnesses/" in c["id"])
        days.add((s["timestamp"][:10], h))
    for ts_, h in sorted(days):
        out.append(stmt(date.fromisoformat(ts_), "use", f"{NS}/harnesses/{h}", None, harness=None, dim="harness"))
    out.sort(key=lambda s: s["timestamp"])
    return out


# ---------------------------------------------------------------- derivation (#20)
LEVELS = ["Introduced", "Explored", "Practiced", "Proven"]
RETRIEVAL = {V["practiced"], V["passed"], V["failed"]}


def grade(s):
    sc = s.get("result", {}).get("score", {}).get("scaled")
    if s["verb"]["id"] == V["practiced"]:  # GAP: #18 didn't say how Hard vs Good is encoded; guessed score.scaled
        return AGAIN if not s["result"]["success"] else GOOD if sc >= 0.9 else HARD
    if s["verb"]["id"] in (V["passed"], V["failed"]):  # area_score/5 thresholds from #18
        return AGAIN if sc < 0.4 else HARD if sc < 0.6 else GOOD if sc < 0.8 else EASY
    return GOOD  # use


def cats(s, kind):
    return [c["id"].rsplit("/", 1)[1] for c in s["context"]["contextActivities"]["category"] if f"/{kind}/" in c["id"]]


def derive(ev):
    concept = defaultdict(lambda: {"verbs": set(), "ret": [], "areas": set()})
    lang_ret, area_ret, harness_use = defaultdict(list), defaultdict(list), defaultdict(list)
    for s in ev:
        dt = date.fromisoformat(s["timestamp"][:10])
        if s["verb"]["id"] == V["use"]:
            harness_use[s["object"]["id"].rsplit("/", 1)[1]].append((dt, GOOD))
            continue
        lang = cats(s, "languages")[0]
        key = (lang, s["object"]["id"].rsplit("/", 1)[1])
        c = concept[key]
        c["verbs"].add(s["verb"]["id"])
        c["areas"].update(cats(s, "areas"))
        if s["verb"]["id"] in RETRIEVAL:
            g = grade(s)
            c["ret"].append((dt, g))
            lang_ret[lang].append((dt, g))
            for a in cats(s, "areas"):
                area_ret[a].append((dt, g))

    concepts = {}
    for (lang, slug), c in concept.items():
        lvl = 0  # Introduced: any experienced or any retrieval
        if V["interacted"] in c["verbs"]: lvl = 1
        if any(g >= HARD for _, g in c["ret"]): lvl = 2
        good_days = sorted({dt for dt, g in c["ret"] if g >= GOOD})
        if good_days and (good_days[-1] - good_days[0]).days >= 7: lvl = 3
        b, last = band(c["ret"])
        concepts[(lang, slug)] = {"level": LEVELS[lvl], "band": b, "last": last, "areas": sorted(c["areas"])}

    def strongest_per_day(events):
        best = {}
        for dt, g in events: best[dt] = max(best.get(dt, 0), g)
        return list(best.items())

    langs = {}
    for lang in sorted({l for l, _ in concepts}):
        counts = {L: sum(1 for (l, _), c in concepts.items() if l == lang and c["level"] == L) for L in LEVELS}
        b, last = band(strongest_per_day(lang_ret[lang]))
        langs[lang] = {"counts": counts, "band": b, "last": last}
    areas = {}
    for a in sorted({a for c in concepts.values() for a in c["areas"]}):
        counts = {L: sum(1 for c in concepts.values() if a in c["areas"] and c["level"] == L) for L in LEVELS}
        last = max((dt for dt, _ in area_ret[a]), default=None)
        areas[a] = {"counts": counts, "last": last}
    harnesses = {}
    for h, uses in sorted(harness_use.items()):
        b, last = band(uses)
        days = sorted({dt for dt, _ in uses})
        harnesses[h] = {"band": b, "days": len(days), "first": days[0], "last": last, "all": days}
    return concepts, langs, areas, harnesses


# ---------------------------------------------------------------- variants
BANNER = "> **PROTOTYPE** (agent-skills#22). Sample Evidence, invented developer. Variant {v}.\n"
FOOTER = ("\n\n---\n\n<sub>Generated from {n} Evidence lines in `evidence/`. Proficiency and Currency are derived only "
          "from Evidence, never from self-claims. Currency model: FSRS-6, default parameters, stability capped at "
          "365 days. Generated {today}.</sub>\n")
ICON = {"Current": "🟢", "Fading": "🟡", "Lapsed": "🔴", None: "⚪"}
GLYPH = {"Introduced": "○", "Explored": "◔", "Practiced": "◑", "Proven": "●"}


def cur(b, last):
    return "—" if b is None else f"{ICON[b]} {b} · {last.isoformat()}"


def counts_line(cnt):
    return " · ".join(f"{cnt[L]} {L}" for L in reversed(LEVELS) if cnt[L])


def nice(slug):
    return slug.replace("-", " ")


def variant_a(n, concepts, langs, areas, harnesses):
    """Reference tables: everything visible, scannable, dense."""
    o = [BANNER.format(v="A (tables)"), "# Proficiency Profile: sample-dev\n",
         "Linked Identities: GitHub `sample-dev` · Azure DevOps `sample-dev@example.com`\n",
         "## Languages\n", "| Language | Proven | Practiced | Explored | Introduced | Currency |", "|---|--:|--:|--:|--:|---|"]
    for l, x in langs.items():
        c = x["counts"]
        o.append(f"| {LANG_NAMES[l]} | {c['Proven']} | {c['Practiced']} | {c['Explored']} | {c['Introduced']} | {cur(x['band'], x['last'])} |")
    o += ["\n## Areas\n", "| Area | Proven | Practiced | Explored | Introduced | Last Exercised |", "|---|--:|--:|--:|--:|---|"]
    for a, x in areas.items():
        c = x["counts"]
        o.append(f"| {a} | {c['Proven']} | {c['Practiced']} | {c['Explored']} | {c['Introduced']} | {x['last'] or '—'} |")
    o += ["\n## Harnesses\n", "| Harness | Days active | First used | Currency |", "|---|--:|---|---|"]
    for h, x in harnesses.items():
        o.append(f"| {HARNESS_NAMES[h]} | {x['days']} | {x['first']} | {cur(x['band'], x['last'])} |")
    o.append("\n## Concepts\n")
    for l in langs:
        rows = sorted(((s, c) for (ll, s), c in concepts.items() if ll == l),
                      key=lambda r: (-LEVELS.index(r[1]["level"]), r[0]))
        o += [f"<details><summary><b>{LANG_NAMES[l]}</b> ({len(rows)} Concepts)</summary>\n",
              "| Concept | Level | Currency |", "|---|---|---|"]
        o += [f"| {nice(s)} | {c['level']} | {cur(c['band'], c['last'])} |" for s, c in rows]
        o.append("\n</details>\n")
    o.append("Levels: Introduced → Explored → Practiced → Proven. Currency: 🟢 Current · 🟡 Fading · 🔴 Lapsed · — no recall yet.")
    return "\n".join(o) + FOOTER.format(n=n, today=TODAY)


def variant_b(n, concepts, langs, areas, harnesses):
    """Narrative + action: what's solid, what's slipping, what's in progress."""
    o = [BANNER.format(v="B (narrative)"), "# sample-dev\n"]
    active = [l for l, x in langs.items() if x["band"] == "Current"]
    o.append(f"Currently working in **{', '.join(LANG_NAMES[l] for l in active) or 'no Language'}**, "
             f"through {', '.join(HARNESS_NAMES[h] for h, x in harnesses.items() if x['band'] == 'Current')}.\n")
    for l, x in langs.items():
        rows = [(s, c) for (ll, s), c in concepts.items() if ll == l]
        solid = [s for s, c in rows if c["level"] == "Proven" and c["band"] == "Current"]
        slipping = [s for s, c in rows if c["level"] in ("Proven", "Practiced") and c["band"] in ("Fading", "Lapsed")]
        progress = [s for s, c in rows if c["level"] in ("Introduced", "Explored")]
        o.append(f"## {LANG_NAMES[l]}  {ICON[x['band']]}\n")
        o.append(f"_{counts_line(x['counts'])}. Last exercised {x['last'] or 'never'}._\n")
        if solid: o.append("**Solid:** " + ", ".join(nice(s) for s in solid) + "\n")
        if slipping: o.append("**Due for a refresh:** " + ", ".join(nice(s) for s in slipping) + "\n")
        if progress: o.append(f"**In progress:** {len(progress)} Concepts met but not yet recalled.\n")
    o.append("## Across the stack\n")
    o.append(" · ".join(f"**{a}** {counts_line(x['counts'])}" for a, x in areas.items()) + "\n")
    o.append("## Harnesses\n")
    for h, x in harnesses.items():
        o.append(f"- {ICON[x['band']]} **{HARNESS_NAMES[h]}**: {x['days']} days since {x['first']}, last {x['last']}")
    return "\n".join(o) + "\n" + FOOTER.format(n=n, today=TODAY)


def variant_c(n, concepts, langs, areas, harnesses):
    """Matrix + timeline: Concepts across Languages, Harness activity by month."""
    o = [BANNER.format(v="C (matrix)"), "# sample-dev · Proficiency Profile\n",
         "`●` Proven `◑` Practiced `◔` Explored `○` Introduced · 🟢 Current 🟡 Fading 🔴 Lapsed\n",
         "## Concept × Language\n"]
    ls = list(langs)
    o.append("| Concept | " + " | ".join(LANG_NAMES[l] for l in ls) + " |")
    o.append("|---|" + "|".join(":-:" for _ in ls) + "|")
    o.append("| **Language** | " + " | ".join(f"**{ICON[langs[l]['band']]}**" for l in ls) + " |")
    slugs = sorted({s for _, s in concepts}, key=lambda s: (-max(LEVELS.index(concepts[(l, s)]["level"]) for l in ls if (l, s) in concepts), s))
    for s in slugs:
        cells = []
        for l in ls:
            c = concepts.get((l, s))
            cells.append("" if not c else GLYPH[c["level"]] + (ICON[c["band"]] if c["band"] else ""))
        o.append(f"| {nice(s)} | " + " | ".join(cells) + " |")
    o.append("\n## Area × level\n")
    o.append("| Area | " + " | ".join(reversed(LEVELS)) + " | Last Exercised |")
    o.append("|---|" + "|".join("--:" for _ in LEVELS) + "|---|")
    for a, x in areas.items():
        o.append(f"| {a} | " + " | ".join(str(x["counts"][L] or "") for L in reversed(LEVELS)) + f" | {x['last'] or '—'} |")
    o.append("\n## Harness activity (days per month, 2026)\n")
    months = list(range(1, TODAY.month + 1))
    bars = " ▁▂▃▄▅▆▇█"
    o.append("```text")
    o.append("              " + "".join("JFMAMJJASOND"[m - 1] for m in months))
    for h, x in harnesses.items():
        per = [sum(1 for dt in x["all"] if dt.month == m and dt.year == 2026) for m in months]
        o.append(f"{HARNESS_NAMES[h]:<13} " + "".join(bars[min(8, math.ceil(p / 2))] for p in per) + f"  {ICON[x['band']]} {x['band']}")
    o.append("```")
    return "\n".join(o) + "\n" + FOOTER.format(n=n, today=TODAY)


VARIANTS = {"A": variant_a, "B": variant_b, "C": variant_c}

if __name__ == "__main__":
    ev = sample()
    derived = derive(ev)
    if "--variant" in sys.argv:
        print(VARIANTS[sys.argv[sys.argv.index("--variant") + 1].upper()](len(ev), *derived))
        sys.exit()
    (HERE / "sample-evidence.jsonl").write_text("".join(json.dumps(s, separators=(",", ":")) + "\n" for s in ev))
    for k, fn in VARIANTS.items():
        (HERE / f"README-{k}.md").write_text(fn(len(ev), *derived))
    print(f"{len(ev)} Evidence lines -> README-A.md, README-B.md, README-C.md in {HERE}")
