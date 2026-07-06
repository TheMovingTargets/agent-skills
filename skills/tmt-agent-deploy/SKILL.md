---
name: tmt-agent-deploy
description: Configure, execute, monitor, recover, diagnose, and audit repository deployments. Use when a user asks to deploy or redeploy an application or component, prepare a repository for repeatable deployments, configure deployment targets, run smoke tests, roll back a failed release, recover an interrupted deployment, diagnose one or more failed or rolled-back deployment attempts, propose deployment fixes, or change deployment confirmation policy.
---

# TMT Agent Deploy

Drive deployments through reviewed repository automation or established CI/CD workflows. Never invent a production command during a run.

## Invariants

- Treat deployment as destabilizing. Always show the active confirmation policy, exact target and scope, source identity, ordered plan, rollback plan, and known risks; then wait for explicit preflight approval.
- Keep executable deployment logic in tracked repository files or reviewed external workflows. `.tmt-agent-deploy/` contains configuration and state, never executable deployment scripts.
- Never store secrets in `.tmt-agent-deploy/`. Store only environment-variable names, credential paths, identity-provider references, secret-manager identifiers, or authentication command references.
- Execute local commands as argument arrays with an explicit working directory. Do not construct shell snippets or interpolate unvalidated parameters.
- During an active run, execute every repository entry point through `deploy_state.py run-entrypoint`. Never execute a repository command and checkpoint it as separate shell commands.
- Run configured sub-deployments sequentially in dependency order. Roll back every changed component in reverse order.
- Require reviewed rollback and rollback verification for every target. Block irreversible migrations unless application rollback remains compatible or the user gives exact destructive authorization for a documented recovery plan.
- Require exact authorization for deletion, replacement, downgrade, secret rotation, irreversible migration, or any other destructive external change regardless of confirmation policy.
- Prefer existing CI/CD deployment workflows. Treat a reviewed workflow as one step unless it exposes native approval gates. Do not make missing CI/CD a blocker when reviewed local automation exists.
- Persist only sanitized run summaries. Never copy command output or external logs into local state.
- Stop after rollback. Never retry a failed deployment automatically.
- Keep post-run diagnosis read-only. Diagnosis is not approval to edit automation, change external systems, or start another deployment.
- Separate observed evidence, supported inferences, and unverified hypotheses. Never present a plausible fix as a proven root cause.

## Select a branch

1. If `.tmt-agent-deploy/config.yaml` is absent or setup is incomplete, run **Setup**.
2. If `state/current-run.yaml` records an unfinished run, run **Recover** before diagnosis, reconfiguration, or a new deployment.
3. If the user asks why a completed deployment failed, mentions repeated failed attempts, or asks for deployment fixes, run **Diagnose failed deployment**.
4. If the user asks to change deployment configuration, run **Reconfigure**.
5. Otherwise run **Deploy**.

When an initial request asks for deployment, continue from Setup into Deploy without requiring a new request.

## Initialize local tooling

Before the first local write, obtain approval to create resumable private state. Then:

1. Ensure the repository root `.gitignore` is proposed with `.tmt-agent-deploy/`.
2. Verify Python 3.9 or newer, then run `python3 scripts/bootstrap.py --repo <repository-root>` from this skill directory.
3. Use the interpreter path printed by the bootstrap script for `scripts/deploy_state.py`.
4. Apply `0700` to the local directory and `0600` to its files where supported.

Initialization is complete when the ignored local directory exists, its isolated Python environment is usable, and no secret value has been written.

## Setup

Read [references/setup-interview.md](references/setup-interview.md) completely and follow it one section at a time. Read [references/configuration.md](references/configuration.md) before drafting configuration. If CI/CD exists or is proposed, also read [references/cicd-practices.md](references/cicd-practices.md).

Explore first without modifying the repository or external systems. Treat existing runbooks, tracked scripts, workflow definitions, infrastructure code, tests, and target configuration as evidence, not as automatically consistent truth.

Persist approved interview progress in `state/setup-draft.yaml` so setup can resume. Present:

- every proposed tracked repository change;
- every proposed external-system change;
- the complete local configuration;
- validation and dry-run commands;
- unresolved risks and blockers.

Wait for explicit approval before writing tracked files or changing external systems. Exact destructive authorization is separate. Validate configuration with:

```text
<local-python> scripts/deploy_state.py validate --repo <repository-root>
<local-python> scripts/deploy_state.py snapshot --repo <repository-root>
```

Run non-production validation and every configured dry-run entry point. If a safe dry run does not exist, propose tracked automation and ask for approval; do not simulate it with ad hoc commands.

Setup is complete only when configuration validates, behavioral artifacts are snapshotted, every target has rollback and rollback verification, required dry runs pass, blockers are resolved or explicitly overridden, and `state/MEMORY.md` reflects the approved architecture.

## Reconfigure

Accept either manual `config.yaml` edits or an explicit reconfiguration interview. Validate manual edits before use. Re-run only the relevant sections of the setup interview, show behavioral differences, and require approval for material behavior changes.

Explain that `confirmation_policy` supports:

- `each-step`: approve each harness-visible deployment step.
- `preflight-only`: after mandatory preflight approval, run the reviewed sequence without additional harness-side prompts.

Reconfiguration is complete when configuration validates, affected behavioral artifacts are snapshotted, and durable architecture changes are reflected in `state/MEMORY.md`.

## Deploy

### 1. Recover and validate

Run:

```text
<local-python> scripts/deploy_state.py status --repo <repository-root>
<local-python> scripts/deploy_state.py validate --repo <repository-root>
<local-python> scripts/deploy_state.py drift --repo <repository-root>
```

Do not begin a new run while an unfinished run exists. Re-read every drifted artifact. Explain differences. Require approval only when behavior changed materially, then regenerate configuration or snapshot as needed.

### 2. Resolve scope

Resolve the named environment, target, component set, runtime parameters, and immutable source identity. Block ambiguous phrases such as “this user.” Validate every runtime parameter against its configured type and constraints before substitution.

Prefer the configured CI/CD workflow when available. Otherwise use configured tracked repository entry points. Never switch execution paths silently.

### 3. Enforce preconditions

Verify every configured precondition, including:

- source and artifact identity;
- source-state policy;
- credential references and tooling;
- exact target-side prerequisites used by later entry points (executable path, required module/subcommand, and version), not merely a related tool version;
- current target health;
- concurrency guard;
- backup or restore point for persistent data;
- migration compatibility;
- reviewed rollback and verification;
- smoke tests, diagnostics, timeouts, and retry policy.

An unhealthy baseline, missing concurrency guard, or missing verified backup blocks deployment unless the user gives an explicit override with a recorded reason. Mutating steps have zero retries unless verified idempotent.

### 4. Mandatory preflight gate

Show the checklist in [references/configuration.md](references/configuration.md), the active confirmation policy, and how to change it. Always wait for explicit approval—even under `preflight-only`.

### 5. Start and execute

Create the checkpoint before the first executable step:

```text
<local-python> scripts/deploy_state.py start-run --repo <repository-root> --environment <name> --target <name> --source <identity> --policy <policy>
```

For each configured entry point:

1. Confirm it still resolves to a reviewed tracked artifact or workflow.
2. Under `each-step`, show it and wait for approval.
3. For a repository entry point, run:

   ```text
   <local-python> scripts/deploy_state.py run-entrypoint --repo <repository-root> --environment <name> --target <name> --path <target-relative-config-path>
   ```

   Use paths such as `build.0`, `components.0.deploy.0`, or
   `components.0.smoke_tests.0.entrypoint`. The runner loads the reviewed argv,
   cwd, timeout, mutation metadata, and component from the validated
   configuration; checkpoints `running`; executes without a shell; checkpoints
   exactly one terminal result; and returns the entry point's nonzero status.
   For a non-mutating idempotent smoke/diagnostic attempt that has another
   configured retry remaining, add `--attempt <n> --retryable`. This records
   `retryable-failure` without clearing or disguising it. Omit `--retryable` on
   the final allowed attempt so a final failure becomes terminal.
4. For an external workflow, checkpoint immediately around the provider call;
   never chain the call and terminal checkpoint in one shell invocation.
5. Never retry a mutating step unless it is marked idempotent.
6. Save only a structured result summary and an external log reference.

If a pre-change step fails, stop without rollback. If a failed step may have changed the target, run rollback automatically. If the user cancels after mutation starts, run rollback automatically.

### 6. Smoke, diagnose, and rollback

Run required smoke tests. On failure:

1. Run the configured diagnostic entry point.
2. Apply configured retry count, delay, and maximum diagnostic time.
3. Use configured evidence rules to distinguish deployment failure from transient or external failure.
4. If deployment failure remains, roll back all changed components in reverse order.
5. Verify rollback.
6. Stop and report; do not redeploy.

If rollback or verification fails, enter emergency stop: run only configured diagnostics, report configured recovery references, and never improvise production commands.

### 7. Finish

Write the sanitized Markdown summary directly inside
`.tmt-agent-deploy/runs/`, clear the active checkpoint only after final state
is known, and retain the newest 50 summaries:

```text
<local-python> scripts/deploy_state.py finish-run --repo <repository-root> --outcome <succeeded|rolled-back|failed|cancelled> --summary <summary-file>
<local-python> scripts/deploy_state.py prune-runs --repo <repository-root>
```

Report the exact source deployed, target and scope, step outcomes, smoke-test evidence, rollback outcome if any, external log references, and local summary path.

Deployment is complete only when the target is verified healthy or rollback reaches a verified state, the checkpoint is finalized, and the user receives the report.

## Recover

Read `state/current-run.yaml`, external run status, and configured recovery entry points. Do not start another deployment.

- If no target-changing step began, finalize the interrupted run as cancelled.
- If target state is uncertain or changed, run configured diagnostics and rollback automatically.
- If an external workflow is still active, resume monitoring rather than triggering another run.
- If rollback cannot be verified, enter emergency stop.

Recovery is complete only when target state is verified, the interrupted run is finalized, and its summary is written.

## Diagnose failed deployment

Read [references/diagnose-failed-deployment.md](references/diagnose-failed-deployment.md) completely and follow it. This mode applies only after the run has reached a final state and `state/current-run.yaml` is absent.

Treat diagnosis as a separate read-only phase:

1. Establish the final target state before analyzing causes.
2. Read the failed or rolled-back run summary, its recorded configuration identity, the current configuration and deployment memory, behavioral artifacts, and referenced external logs. Flag any hash mismatch instead of treating current configuration as historical evidence.
3. Compare at least the latest two relevant unsuccessful runs when failures are repeated.
4. Reconstruct the failure boundary and determine which steps did and did not execute.
5. Classify the primary cause, contributing factors, rollback weaknesses, and evidence gaps.
6. Propose ranked fixes with exact artifacts, validation commands, dry runs, and deployment-readiness gates.

Do not edit repository automation or local deployment configuration unless the user separately asks to implement a proposed fix. Never start or resume a deployment from diagnosis mode. A later deployment request starts a new run and still requires validation plus mandatory preflight approval.
