# Field Debug Report Contract

Produce a self-contained, sanitized Markdown artifact. An implementation agent must not need chat history or raw log access to understand the supported fix, though it may need repository access to perform the work.

Use this exact top-level order.

## 1. Incident summary

Include:

- title and report timestamp with timezone;
- implementation readiness: `READY` or `BLOCKED`;
- severity and current status;
- user-visible symptom and expected behavior;
- exact environment, target, components, scope, and deployed source identity;
- first known bad and last known good timestamps;
- concise supported cause and confidence: `high`, `medium`, or `low`.

## 2. Safety and target state

State current target health, blast radius, data-integrity status, whether a deployment is active, and whether rollback or emergency action is required. List investigation constraints and confirm that field probes were read-only. Mark unknowns explicitly.

## 3. Evidence index

Use a table:

| ID | UTC timestamp/window | Source | Sanitized query or reference | Observation | Reliability |
|---|---|---|---|---|---|

Assign stable IDs such as `E1`. Link local files where portable; identify external run, dashboard, log stream, trace, or request references without embedding credentials or sensitive payloads. Include material negative evidence.

## 4. Timeline

Order deployment and infrastructure changes, symptom onset, representative failures, probes, recovery events, and current state. Cite evidence IDs on every row or bullet.

## 5. Reproduction or observable signature

Document the exact deployed-path signature, safe invocation or query, expected failing result, observed result, frequency, comparison baseline, and limitations. If reproduction was unsafe or impossible, explain why and name the missing artifact or access.

## 6. Hypothesis ledger

Use a table:

| Rank | Hypothesis and prediction | Probe | Evidence | Result | Status |
|---|---|---|---|---|---|

Keep falsified hypotheses and contradictory evidence. Do not rewrite the history after finding a likely cause.

## 7. Causal analysis

Separate:

- **Observed facts:** direct evidence only.
- **Supported inference:** the narrowest explanation consistent with observations.
- **Unverified remainder:** assumptions or links not proven.

Show the causal chain from trigger through the failing boundary to the user-visible symptom. Explain why existing preflight, smoke tests, monitoring, or rollback did not prevent or reveal it. Assess contributing factors and residual state.

## 8. Suggested fixes

Rank each fix and label it `required`, `validation`, `hardening`, or `cleanup`. Include:

- exact repository files, symbols, configuration, or reviewed workflow steps when known;
- intended behavioral change and evidence addressed;
- alternatives considered and why they rank lower;
- compatibility, security, operational, migration, and data risks;
- rollback implications and any separate authorization required.

Avoid code patches. This report is the implementation specification.

## 9. Implementation brief

Write this section as direct input to `implement`:

### Objective

State the observable outcome, not the preferred code shape.

### Required changes

List implementation tasks in dependency order. Anchor each task to files or discovery boundaries and evidence IDs. Distinguish confirmed edits from implementation-time discovery.

### Acceptance criteria

Make every criterion independently verifiable. Include the original symptom, unaffected behavior, error handling, observability, and compatibility where relevant.

### Test plan

Specify the regression seam, pre-fix failing assertion, focused tests, integration or contract tests, and full-suite expectations. Include the non-production deployment rehearsal and post-deploy smoke or observation query, but do not authorize deployment.

### Non-goals

Fence out speculative refactors, unrelated cleanup, and operational actions not required by the supported cause.

### Risks and constraints

Capture data, security, performance, migration, backward-compatibility, rollout, and rollback constraints.

### Implementation inputs

List relevant source identity, artifacts, runbooks, evidence IDs, and commands that the implementation agent may safely reuse. Do not require raw sensitive logs.

## 10. Open questions and blockers

List each unresolved ambiguity, why it matters, its owner when known, and the smallest action needed to resolve it. Write `None` only when the report is `READY`.

## 11. Readiness and next authorization

Give one verdict:

- `READY`: the report may be passed directly to `implement`.
- `BLOCKED`: implementation would require guessing; list the blocking sections.

Request exactly one next authorization. Implementation authorization is distinct from deployment, mutation, cleanup, or production instrumentation authorization.
