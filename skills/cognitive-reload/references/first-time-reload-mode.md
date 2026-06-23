# First-time guided reload mode

Use `first_time_guided` when no prior cognition artifact exists, or when the developer says they have not reviewed the repo or selected area.

## Purpose

Build an initial human mental model of the codebase before measuring it.

A first-time reload is onboarding plus verification, not a weekly diff review.

## First-time rule

Do not score the repository as a whole from Git evidence alone.

Use statuses:

- `unverified` for areas not yet taught and quizzed
- `partial` for attempted but below-threshold teach-back
- `verified` for areas completed through briefing, walkthrough, Q&A, quiz, and grading

## Required flow

1. Detect first-time mode.
2. Identify target ref/branch and dirty working tree status.
3. Build a candidate area map from repo structure, docs, tests, and safe Git evidence.
4. Recommend one high-value first area.
5. Wait for area selection.
6. Build an evidence ledger for that area.
7. Provide a tutor-led walkthrough of selected files/tests/docs.
8. Answer human questions until the human explicitly says they are ready for quiz.
9. Run a small teach-back quiz.
10. Score only the selected verified area.
11. Produce a report-only JSON baseline with other areas marked `unverified`.

## What not to do

Do not do this:

```text
Here are four files. Tell me when ready for the first quiz.
```

Do this instead:

```text
Let's walk the area together. Start with this route because it is the entry point. Notice that the server derives device scope from the authenticated agent rather than trusting the payload. That matters because...
```

## Latest commit trap

If the latest commit only updates docs, agent instructions, or unrelated files, do not treat it as the onboarding scope. For first-time reloads, sample the system's critical areas instead.

## Initial score behavior

For the first session, prefer:

```json
{
  "overall": {
    "status": "baseline_incomplete",
    "provisional_score": null,
    "agent_handoff_ready": false,
    "reason": "Only selected areas with completed teach-back are scored."
  }
}
```

## Recommended first-session size

A first session should usually verify one area only.

A good first area is:

- privacy-sensitive
- tenant-scoped
- central to product behavior
- likely to be modified by future agents
- supported by tests that can teach invariants
