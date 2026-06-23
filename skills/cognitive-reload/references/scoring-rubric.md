# Scoring rubric

Scores are per developer, per area, and only valid after a teach-back attempt.

## Area dimensions

Score each dimension from 0 to 5.

### orientation

Can the human find the relevant files, tests, docs, and boundaries?

- 0: cannot identify where to look
- 1: recognizes names but cannot navigate
- 2: can find obvious files with help
- 3: can locate main files/tests independently
- 4: can locate entry points, boundaries, and tests quickly
- 5: can teach another developer how to navigate the area

### causal_understanding

Can the human explain why the system works this way?

- 0: no causal explanation
- 1: repeats names without flow
- 2: basic flow but important gaps
- 3: explains behavior and most boundaries
- 4: explains design tradeoffs and invariants
- 5: can critique alternatives and teach the design

### change_awareness

Can the human explain recent or relevant changes?

- 0: unaware of changes
- 1: recognizes that something changed
- 2: can name changed files but not intent
- 3: explains intent and behavior change
- 4: connects changes to tests/docs/risks
- 5: can guide future changes based on recent history

For first-time reloads with unchanged sampled areas, score this as awareness of why the area was sampled and how it relates to current repo state.

### risk_awareness

Can the human identify likely failure modes and unsafe agent actions?

- 0: cannot identify risks
- 1: generic risks only
- 2: finds obvious risks
- 3: identifies area-specific risks
- 4: connects risks to invariants and tests
- 5: can design review strategy and guardrails

### test_awareness

Can the human map intended behavior to tests?

- 0: no test awareness
- 1: knows tests exist
- 2: can name broad test area
- 3: can identify relevant tests
- 4: can explain what tests protect
- 5: can specify missing tests and regression strategy

### agent_guidance_readiness

Can the human safely guide a future coding agent?

- 0: cannot guide
- 1: can give generic instructions only
- 2: can give simple task instructions with risk
- 3: can guide local changes with supervision
- 4: can guide an agent safely in this area
- 5: can guide, review, and recover from agent mistakes

## Area score

The default area score is the average of all dimension scores.

```text
area_score = average(orientation, causal_understanding, change_awareness, risk_awareness, test_awareness, agent_guidance_readiness)
```

## Thresholds

- `>= 4.0`: agent-handoff ready for this area
- `3.0-3.9`: partial; human can participate but should not blindly guide an agent
- `2.0-2.9`: weak; guided reload needed
- `< 2.0`: not ready
- `null`: unverified

## Overall score

Do not compute a repo-wide overall score unless a meaningful set of critical areas has verified scores.

For first-time guided reload, use `baseline_incomplete` until enough areas are verified.

## Weighting

When computing overall scores, weight areas by:

- architectural importance
- risk level
- recent change volume
- staleness

State the weighting assumptions in JSON.
