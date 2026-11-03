---
name: cognitive-reload-with-trinity
description: Codebase cognitive reload plus target-language fluency in one session. Runs the cognitive-reload tutoring path (orientation, system diagram, topic map, faithful code excerpts, cursor, progress, assessment gate) and, at every code and test excerpt, layers the trinity-helicopter-program language lessons so the learner understands both what the code does and how the language expresses it. Use when someone wants to onboard to, reload, or review a repository written in a language they are not yet fluent in — for example a C#/.NET port of services they knew in TypeScript or Python — or asks for "cognitive reload with trinity", "reload this repo and teach me the C#", or "walk me through the port and the language".
---

# Cognitive Reload with Trinity

Two skills, one session. **cognitive-reload** answers *what does this system do and why is it built this way*. **trinity-helicopter-program** answers *how does this language say it*. The learner is a strong engineer who may know the domain cold but not the target language — so a plain reload stalls on syntax and idiom, and a plain language tutorial floats free of the system. Interleave them on the same excerpts.

## Load both skills

Load each skill's full instructions before starting, then follow them as modified below.

- If your harness has a skill tool (e.g. Claude Code's `Skill`), invoke `cognitive-reload` (it may be namespaced, e.g. `tmt-agent-skills:cognitive-reload`) and `trinity-helicopter-program`.
- Otherwise (e.g. Codex), read their `SKILL.md` files directly. Look, in order, for a sibling directory of this skill (`../cognitive-reload/`, `../trinity-helicopter-program/`), then `.agents/skills/`, `.claude/skills/`, `~/.agents/skills/`, `~/.claude/skills/`, `~/.codex/skills/`, and installed plugin caches (`~/.claude/plugins/cache/*/*/*/skills/`, `~/.codex/plugins/cache/*/*/*/skills/`). Resolve each skill's bundled `scripts/` and `references/` relative to the directory its `SKILL.md` is in.
- If cognitive-reload can't be found, say so and offer to run trinity-helicopter-program in `repo_reading` mode alone. If trinity can't be found, run cognitive-reload alone and say the language layer is unavailable.

## Who owns what

| Concern | Owner |
|---|---|
| Session mode, startup, orientation, system diagram, topic map | cognitive-reload |
| The zoom ladder and the main-path cursor (`location`, `advance`) | cognitive-reload |
| Which excerpt comes next; faithful-excerpt rules | cognitive-reload (trinity's rule is the same) |
| Concept spotting, bridges, cards, chips, weeds ladder | trinity |
| Repo-cognition progress | cognitive-reload's progress store |
| Language fluency progress | trinity's concept ledger (per learner + language, shared across repos) |
| Assessment (codebase teach-back) | cognitive-reload, behind its assessment gate |
| Fluency drills (`fly`) | trinity, only on request |

Where the two skills' rules overlap they agree; where in doubt, cognitive-reload's interaction contract wins, because it owns the route.

## Startup additions

After cognitive-reload's startup protocol:

1. Identify the target language of the repo (and the source language, if this repo is a port and the original is available — then trinity's side-by-side view applies to excerpts that have a clear counterpart).
2. Load the trinity ledger and profile for that language; if no profile, ask the one calibration question trinity specifies, folded into the same message as cognitive-reload's orientation invitation — not a separate turn.
3. In the orientation, add one line: which language the language layer will teach and how to steer it (`skip`, `weeds`, `surface`).

Orientation, system diagram, and topic map stay language-light: concepts there are architectural. Language teaching starts at the first code-excerpt rung.

## At each code or test excerpt

Follow cognitive-reload's topic teaching loop, and at steps 4–6 (show excerpt, explain, pause) do this:

1. Show the faithful excerpt per cognitive-reload.
2. **Language layer first, briefly.** Apply trinity's triage to the concepts in the excerpt: silence for known, bridge lines for near-analogs, at most two cards for new concepts or false friends (one fewer than trinity alone, to leave room for the architecture), chips for the rest. If the learner can't parse the syntax, the architectural explanation won't land — so this comes first.
3. **Then the architecture**, per cognitive-reload: caller, inputs, outputs, trust assumptions, invariants, downstream effects. Where an idiom carries architectural meaning (DI lifetime, cancellation propagation, disposal order, async boundaries), say so — that's the seam where the two skills reinforce each other.
4. **One pause, one footer.** Combine both skills' invitations into a single line: "Questions on any line? `skip`/`weeds <concept>` for the language, `continue` for <saved advance>."

Keep the combined turn readable at chat width; if both layers won't fit, shrink the excerpt rather than either layer.

## Detours share one cursor

`weeds`, `load`, `compare`, and `surface` are detours in cognitive-reload's sense: push the main-path cursor before them and restore it after. `surface` returns to the exact excerpt and `advance` that the first `weeds` left from, however deep the learner went. Bare `continue`/`next` always executes cognitive-reload's saved `advance` — never a language side path.

## Gates stay separate

- `fly` (language drill) is not a cognitive-reload assessment and doesn't cross its assessment gate; results go only to the trinity ledger.
- A cognitive-reload teach-back is not a language drill; don't mark concepts `fluent` from it unless the learner wrote target-language code that showed it.
- Neither starts without the learner asking.

## Checkpoints and pause

At cognitive-reload's checkpoint moments, also batch-update the trinity ledger (concepts loaded/explored/skipped this segment, with anchors and repo name). At pause, give one recap with two short parts — *system model* (cognitive-reload's recap and resume point) and *language* (concepts loaded, skipped, open language questions) — then cognitive-reload's publishing offer. Trinity's ledger is personal and never published with HITL cognition artifacts.
