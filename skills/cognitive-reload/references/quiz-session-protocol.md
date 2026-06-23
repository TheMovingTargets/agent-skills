# Quiz session protocol

The quiz measures human cognition. It should feel like a guided teach-back, not a hostile exam, homework dump, or substitute for tutoring.

## Quiz is gated

Do not begin quiz mode until the developer explicitly says they are ready for assessment.

Accepted readiness phrases include:

- `ready for quiz`
- `quiz me`
- `I am out of questions; test me`
- `let's do the teach-back`

Do not treat `ready`, `next`, or `I inspected the files` as quiz consent.

## Stages

### Stage A: orientation

Can the human locate the area?

Example:

```text
Which file would you inspect first to understand this flow, and why?
```

### Stage B: behavior

Can the human explain what happens?

```text
In one paragraph, describe the flow from request/input to persisted/output state.
```

### Stage C: invariant

Can the human identify what must remain true?

```text
What invariant must hold before this operation completes?
```

### Stage D: test awareness

Can the human map behavior to tests?

```text
Which test would you run before trusting a change here?
```

### Stage E: agent guidance

Can the human guide a future agent?

```text
Give a coding agent three constraints before modifying this area.
```

## Question sizing

Good:

- one concept
- evidence-bound
- answerable in 1-2 paragraphs
- gradable against files/tests/docs

Bad:

- combines five flows
- requires the entire architecture
- cannot be graded against concrete evidence
- asks for broad speculation

## Grading response template

```text
Assessment: partial, 3.2 / 5 for this attempt.

What you got right:
- You found the entry point.
- You identified the org scope check.

Missing:
- You did not explain device scope.
- You did not name the deletion regression test.

Retake:
Answer this narrower question: why must deletion include device_id as well as org_id?
```

## Do not score too early

If the developer has only acknowledged the briefing, asked questions, or said `next`, do not score. Continue the tutorial or ask whether they want to continue or say `ready for quiz`.
