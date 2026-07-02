# Configuration and State Contract

## Local layout

```text
.tmt-agent-deploy/
  config.yaml
  runs/
    <UTC timestamp>-<deployment id>.md
  state/
    MEMORY.md
    artifacts.yaml
    setup-draft.yaml
    current-run.yaml
    .venv/
```

The whole directory is gitignored. Apply restrictive permissions where supported. Never store secrets, raw logs, private key contents, tokens, passwords, or credential values.

## Configuration

Validate `config.yaml` against `schemas/config.schema.json`. Its major sections are:

- `schema_version` and `validated_by`;
- `confirmation_policy`;
- global timeout, diagnostic, and retention defaults;
- behavioral artifact inventory;
- named environments and targets;
- required runtime parameter types and constraints;
- immutable source identity and release preconditions;
- concurrency, baseline health, backup, migration, deployment, rollback, verification, smoke, and diagnostic entry points.

Repository entry points use `argv` arrays and explicit `cwd`. Workflow entry points identify the provider, workflow, ref, validated inputs, and external log reference. Values may reference validated runtime parameters; never interpolate unvalidated free text.

An artifact marked `behavioral: true` participates in material drift review. SHA-256 changes trigger a re-read. The agent decides whether behavior changed materially, explains that decision, and asks for approval only when it did.

## Memory

`state/MEMORY.md` is the current human-readable deployment architecture:

- environments, targets, components, and dependencies;
- source and artifact flow;
- automation and CI/CD ownership;
- authentication references and trust boundaries;
- concurrency and approval controls;
- backup, migration, rollback, smoke, diagnostic, and recovery design;
- unresolved risks and explicitly accepted overrides.

Update it only for durable discoveries or architecture changes, not routine run results.

`state/artifacts.yaml` is machine-readable drift state. `state/setup-draft.yaml` makes the interview resumable. `state/current-run.yaml` is an atomic recovery checkpoint and must exist only while a run is unfinished.

## Mandatory preflight display

Before every deployment, display:

1. Active confirmation policy and how to change it.
2. Environment, target, components, and validated runtime scope.
3. Exact source commit, artifact digest, or release identity.
4. Source-state and release-gate results.
5. Credential-reference and tool readiness.
6. Current target health.
7. Concurrency guard or explicit override.
8. Ordered entry points and current SHA-256 values.
9. Target-mutation boundary and retry behavior.
10. Backup or restore point and migration compatibility.
11. Reverse-order rollback and rollback verification.
12. Smoke tests, diagnostics, retry delay/count, and maximum duration.
13. External changes, destructive actions, risks, and accepted overrides.

Then wait for explicit approval. Never merge this approval with setup approval.

## Run summaries

Use UTC filenames:

```text
runs/20260702T184500Z-production-a1b2c3d.md
```

Store only:

- deployment identifier and UTC timestamps;
- environment, target, component scope, and validated parameter names/values that are not sensitive;
- source and immutable artifact identities;
- active confirmation policy and approval events;
- entry-point names and SHA-256 values;
- structured outcomes and durations;
- smoke, diagnostic, rollback, and rollback-verification summaries;
- explicit overrides and destructive authorizations;
- external workflow/run/log references;
- final target state.

Never store raw command output. Retain the newest 50 summaries.

## Drift

Run `snapshot` after approved setup or material reconfiguration. Run `drift` before every deployment.

- Missing or changed behavioral artifact: block, re-read, explain behavior impact, and reconfigure if necessary.
- Non-behavioral artifact change: report and continue when validation still passes.
- Manual `config.yaml` edit: validate and compare behavior before deployment.
- Skill/schema version change: migrate or revalidate before deployment.

## Confirmation

`each-step` asks before every harness-visible executable step. A CI/CD workflow is one step unless it provides native gates.

`preflight-only` runs the reviewed sequence after mandatory preflight approval without further harness-side prompts.

Both policies still require exact authorization for destructive actions and explicit overrides for configured blockers.
