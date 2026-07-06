# Diagnose Failed Deployments

Use this workflow only for completed `failed`, `rolled-back`, or `cancelled`
runs. If `state/current-run.yaml` exists, recover the active run first.

## 1. Establish safety and scope

- Confirm the run is finalized and identify the environment, target,
  components, requested source, and final source.
- Verify the target's current health through configured read-only diagnostics.
- State whether rollback was verified, failed, or unnecessary.
- Do not execute deploy, rollback, migration, cleanup, or repair entry points.
- Treat a request to diagnose or propose fixes as read-only. Require a separate
  request before editing files or changing external systems.

## 2. Collect evidence

Read:

- the selected summary under `.tmt-agent-deploy/runs/`;
- the newest relevant unsuccessful summaries, using at least two when the user
  reports repeated failures;
- `state/MEMORY.md`, `state/artifacts.yaml`, and `config.yaml`;
- the authoritative deployment, rollback, and recovery artifacts;
- referenced external workflow logs or provider status;
- relevant repository history between the known-good and requested sources.

Compare each summary's recorded configuration and artifact-snapshot hashes with
the current files. If historical configuration content was not retained, state
that limitation; do not reconstruct it from the current configuration.

Use current external diagnostics only to establish current state or test a
specific read-only hypothesis. Do not persist raw logs. Redact secrets and
personal data from notes and reports.

## 3. Reconstruct each attempt

Build a compact attempt table with:

- source and run identifier;
- last successful step;
- first failed step;
- whether target mutation had started;
- failure signature;
- rollback extent and verification;
- residual artifacts;
- final target state.

Mark every expected step as `passed`, `failed`, `not reached`, `skipped by
phase`, or `unknown`. Do not infer that a step ran merely because a later
artifact exists.

For repeated attempts, distinguish:

- the same root cause recurring;
- a previous blocker being fixed and exposing the next blocker;
- independent failures;
- a deploy-harness or runbook defect;
- an application, dependency, credential, infrastructure, capacity, migration,
  or smoke-test failure.

## 4. Form a causal analysis

Report three evidence levels:

1. **Observed:** directly supported by checkpoints, exit status, target state,
   or logs.
2. **Inferred:** the narrowest explanation consistent with the observations.
3. **Hypothesized:** plausible but requiring a named test.

Identify:

- primary failure mechanism;
- triggering condition;
- why preflight or dry-run validation did not catch it;
- contributing configuration or process weaknesses;
- blast radius and whether persistent data changed;
- rollback gaps, including phase-inapplicable or non-idempotent rollback steps;
- residual state that could affect the next attempt.

Prefer a causal chain over a single label. For example:

```text
argument transport changed quoting
  -> remote shell parsed Python source
  -> verification never reached Python
  -> run failed after source mutation
  -> rollback was required
```

## 5. Propose fixes

Rank fixes as:

- **Required before retry:** directly removes the supported failure mechanism or
  repairs unsafe rollback/recovery behavior.
- **Required validation:** proves the fix across the same execution boundary
  that failed.
- **Hardening:** improves observability, phase safety, idempotency, or
  preflight coverage.
- **Cleanup:** removes residual artifacts only after exact destructive
  authorization.

For every proposal include:

- the tracked repository artifact or reviewed external workflow to change;
- the exact behavioral change;
- why it addresses the evidence;
- risks and compatibility constraints;
- focused tests;
- a non-production dry run;
- the pass/fail gate for a future deployment.

Keep executable fixes in tracked repository files or reviewed workflows. Avoid
fragile inline programs passed through SSH; prefer a tracked target-side helper
with simple validated arguments. Exercise remote transport, quoting, privilege,
working-directory, and environment behavior in validation rather than testing
only the inner command locally.

Make rollback phase-aware. Never propose a rollback step that assumes an
activation, migration, or replacement occurred unless checkpoint evidence
proves that phase completed. Prefer independently reversible components or a
tracked idempotent rollback helper that inspects explicit release state.

## 6. Deliver the diagnosis

Use this output:

1. Final target state and safety status.
2. Attempt comparison.
3. Primary cause with evidence level and confidence.
4. Contributing factors and detection gaps.
5. Rollback and residual-state assessment.
6. Ranked proposed fixes.
7. Validation plan and future deployment readiness: `NO-GO`, `CONDITIONAL`, or
   `READY`.

End with the smallest explicit next authorization needed, such as approval to
implement the required tracked fix. Do not imply that diagnosis approval also
authorizes implementation or deployment.
