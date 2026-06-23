# Tutor-led walkthrough protocol

`cognitive-reload` should feel like a senior engineer walking the developer through the repo, not like an exam proctor assigning homework.

## Core principle

Teach before testing.

A developer who has not reviewed the repo should not be asked to prove understanding until the agent has helped them build an initial mental model.

## Required walkthrough shape

For each selected area, provide a walkthrough in small slices:

1. Area purpose: what problem this area solves.
2. Flow map: the 3-6 step path through files/functions/tests.
3. Excerpt 1: entry point or public interface.
4. Excerpt 2: core invariant or transformation.
5. Excerpt 3: test proving expected behavior.
6. Optional excerpt 4: documentation, config, or edge-case handling.
7. Open Q&A loop.
8. Quiz only after explicit readiness.

## Excerpt requirements

Use line-numbered excerpts, not entire files.

Good excerpt:

```text
apps/api/.../routers/events.py lines 42-88
```

Then show the excerpt and explain:

- what this block does
- why it matters for the chosen area
- what invariant or boundary it protects
- what adjacent code/test completes the story
- what a future agent might accidentally break

## Excerpt size limits

Prefer excerpts of 20-60 lines.
Never paste an entire large file unless the file is very small.
If a file is large, use targeted commands such as:

```bash
git show <ref>:path/to/file.py | nl -ba | sed -n '40,110p'
```

For tests:

```bash
git show <ref>:tests/test_file.py | nl -ba | sed -n '150,230p'
```

## Walkthrough voice

Use tutorial language:

- "Start here. This is the entry point."
- "Notice this check; it is the tenant boundary."
- "This variable matters because it is stamped by the server, not trusted from the client."
- "The test below is the safety net for this invariant."
- "A future agent might be tempted to simplify this, but that would weaken the boundary."

Avoid handoff-only language:

- "Inspect these files and tell me when ready."
- "Here are the files."
- "Answer these questions."

## Human pacing

After each excerpt or concept cluster, ask:

```text
What questions do you have about this block before we move to the next piece?
You can also say `next` to continue.
```

Do not move to quiz mode merely because the human says `next`. `next` means continue the tutorial. Quiz requires explicit readiness.

## Explicit quiz gate

Use wording like:

```text
We can stay in walkthrough/Q&A mode as long as you want. When you have no more questions and want to be assessed, say `ready for quiz`.
```
