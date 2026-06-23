# GitHub User Progress Memory

Progress is keyed by the authenticated GitHub user and repository, not by commit author or OS username.

## Identity

Use `gh api user --jq .login` through `scripts/progress_store.py`. Normalize the repository from the `origin` remote. If `gh` is absent or unauthenticated, use session-only state and tell the learner once.

Do not ask the learner to authenticate unless they ask for persistent progress.

## Storage

Default local path:

```text
${XDG_DATA_HOME:-~/.local/share}/cognitive-reload/github/<host>/<owner>/<repo>/<login>/progress.json
```

This is outside the working tree, so report-only mode does not dirty the repository. It is local to the current machine. Do not claim it syncs through GitHub.

An organization may later provide a connector-backed store. Do not upload progress, create a gist, or commit it without explicit permission.

## Required progress shape

Use `assets/progress.schema.json` as the contract. Preserve:

- repository and GitHub login
- last target ref and commit
- orientation status
- per-topic state: `unseen`, `introduced`, `explored`, or `assessed`
- concepts and code anchors shown
- learner questions and unresolved questions
- assessment attempts and latest verified score
- exact resume point

## Semantics

- `introduced`: explained at concept/diagram level
- `explored`: at least one guided code/test walkthrough plus learner interaction
- `assessed`: optional teach-back completed
- Material shown does not imply understanding.
- Never lower or raise cognition scores without assessment evidence.
- Record self-reported confidence separately from verified assessment.

## Checkpoint cadence

Do not read and rewrite the progress artifact for every learner question. Record questions
in session memory and persist them after a meaningful topic segment, on a topic switch,
when pausing, or after assessment. Answer clarification questions before any checkpoint
tool call. This keeps tutoring responsive and avoids exposing bookkeeping during a simple
code discussion.

## Resume behavior

Begin a resumed session with a concise personalized recap:

```text
Welcome back. Last time you mapped the event journey and explored tenant scoping through `_scope_agent_event`. You asked whether nested metadata receives the same validation; that remains unresolved. We can resume there, revisit the system map, or choose another topic.
```

Do not repeat the first-time survey unless the target ref changed substantially or the learner requests it.

## Report-only mode

Report-only means:

- do not write cognition reports into the repository
- do not modify product files
- local progress checkpoints are allowed and disclosed
- if the learner says `do not save progress`, keep state in the session only
