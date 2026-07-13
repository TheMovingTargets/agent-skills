# Review packet template

Copy this structure into a single markdown file. Replace every `<...>` placeholder; delete nothing. The packet must stand alone: Codex reads it plus the repository, nothing else.

```markdown
# Adversarial plan review

You are an adversarial reviewer. This packet IS the review run: perform the
review yourself, directly against the repository. Do not invoke any skill, do
not run codex, and do not delegate — a plan-review skill you discover in your
skill directories describes the dispatch that already brought you this packet.

Your job is to find weaknesses in the plan below: incorrect assumptions,
ordering and concurrency problems, missing edge cases, migration or backfill
hazards, breakage of existing behavior, and simpler alternatives. Review only —
do NOT implement anything or modify any file. Cite code evidence (file paths,
line numbers) for every finding.

## Context

<What problem the plan solves. The diagnosis or evidence behind it, including
measured data where it exists. Repository purpose in one or two sentences.>

Key files to read before reviewing:

- <repo-relative path — one line on why it matters>
- <...>

## The plan under review

<The plan, VERBATIM. Do not summarize, compress, or reorder it.>

## Specific questions to attack

- <A question naming the plan's riskiest assumption>
- <An ordering / concurrency / idempotency question>
- <A migration, backfill, or rollback safety question>
- <"Is there a simpler design that achieves the same goal?">

## Required output

Return a numbered list of findings. Each finding must have:

1. Severity: blocker / major / minor / nit.
2. The code evidence (path and lines).
3. A concrete suggested amendment to the plan.

End with an overall verdict, exactly one of:
- **Sound as written** — implementable without revision.
- **Needs revision first** — list which findings gate implementation.
```
