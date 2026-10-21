# Learner Progress Memory

Progress is keyed by the authenticated learner (a GitHub or Azure DevOps user) and repository, not by commit author or OS username.

## Identity

Run `scripts/progress_store.py identity`. It normalizes the repository from the `origin` remote and picks the identity provider from it:

- **GitHub** remotes: the login from `gh api user --jq .login`.
- **Azure DevOps** remotes (`dev.azure.com`, `ssh.dev.azure.com`, `*.visualstudio.com`, or any host serving the `<org>/<project>/_git/<repo>` layout, such as a git proxy): the signed-in user's account from the organization's `_apis/connectionData`, through the Azure CLI's `az login` first and then a personal access token in `AZURE_DEVOPS_EXT_PAT`. For a proxied remote the organization is assumed to be `https://dev.azure.com/<org>`; set `COGNITIVE_RELOAD_ADO_ORG_URL` to override it.

If the provider's sign-in is absent or fails, use session-only state and tell the learner once.

Do not ask the learner to authenticate unless they ask for persistent progress.

## Storage

Default local path:

```text
${XDG_DATA_HOME:-~/.local/share}/cognitive-reload/github/<host>/<owner>/<repo>/<login>/progress.json
${XDG_DATA_HOME:-~/.local/share}/cognitive-reload/azure-devops/dev.azure.com/<org>/<project>/<repo>/<account>/progress.json
```

This is outside the working tree, so report-only mode does not dirty the repository. It is local to the current machine. Do not claim it syncs through GitHub or Azure DevOps.

An organization may later provide a connector-backed store. Do not upload progress, create a gist, or commit it without explicit permission.

## Required progress shape

Use `assets/progress.schema.json` as the contract. Preserve:

- repository, identity provider and learner login (`learner_login`; GitHub records also keep `github_login`)
- last target ref and commit
- orientation status
- per-topic state: `unseen`, `introduced`, `explored`, or `assessed`
- concepts and code anchors shown
- learner questions and unresolved questions
- assessment attempts and latest verified score
- exact main-path resume route: topic, rung, current anchor, and executable next step

Persist the main reload path, not the most recent clarification detour. In `resume`,
use `next_step` for the concrete action that a bare `continue` or `next` should perform.
Keep `next_anchor` for the destination anchor when one exists. Older records without
the added route fields remain valid; reconstruct the safest route from `summary` and
`next_anchor`, and preserve it through any opening questions.

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
code discussion. A clarification may add a learner question, but it must not overwrite
the persisted main-path resume route.

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
