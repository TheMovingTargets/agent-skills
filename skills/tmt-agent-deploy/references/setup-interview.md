# Setup Interview

Explore, present findings, and ask one decision at a time. Never infer a production target, credential, release source, approval boundary, or recovery behavior.

## 1. Establish local state

Explain `.tmt-agent-deploy/`, its gitignore rule, privacy boundary, secret prohibition, and resumable setup draft. Obtain approval before creating it. Resume an existing draft rather than restarting unless the user requests a reset.

Completion criterion: local-state permission and any prior setup progress are resolved.

## 2. Explore deployment evidence

Inspect, where present:

- repository and worktree identity;
- agent instructions and deployment runbooks;
- build manifests and lockfiles;
- Make, task-runner, and package scripts;
- deployment, migration, backup, restore, smoke, diagnostic, and rollback scripts;
- container, infrastructure-as-code, service, and process-manager files;
- CI/CD workflows, environments, protections, concurrency, artifacts, and external logs;
- health checks, observability references, and tests;
- gitignored local deployment documentation without exposing its values.

Map contradictions and gaps. Do not execute deployment commands during exploration.

Completion criterion: every deployment-relevant artifact found has a stated role or is marked unresolved.

## 3. Identify environments and targets

For each environment, ask for its exact name, criticality, provider-neutral description, target names, services/components, dependency order, and operator-facing references. Define required runtime scopes such as tenant, customer, region, or instance.

For every runtime parameter, record its type and validation constraints. Never accept ambiguous scope at deployment time.

Completion criterion: every requested deployment can resolve to one environment, target, component set, and validated parameter set.

## 4. Define release sources

For every target, identify the source of truth: Git commit, immutable artifact digest, container digest, package version, or another exact identity. Record branch/tag protections, clean-worktree requirements, test/review gates, build provenance, and promotion rules.

Prefer building once, testing that artifact, and promoting the same digest. Do not rebuild during deployment when existing tooling supports immutable promotion.

Completion criterion: deployed bytes can be traced to a unique reviewed source.

## 5. Select automation entry points

Prefer, in order:

1. an established reviewed CI/CD deployment workflow;
2. existing tracked repository automation;
3. newly proposed tracked automation.

Do not generate executable files under `.tmt-agent-deploy/`. If automation is missing, propose tracked scripts, workflow files, service definitions, health checks, or infrastructure changes and wait for approval before writing.

Record commands as argument arrays with explicit working directories. Record workflow identifiers, immutable refs where supported, validated inputs, monitor commands/APIs, and external log locations.

For every target-side command, add a non-mutating preflight that proves the
exact prerequisite used later: executable path, required module or subcommand,
and relevant version. A broad probe such as `python --version` does not prove
that `python -m pip` or `python -m venv` works.

Completion criterion: every executable step resolves to reviewed tracked
automation or an established workflow, and target-side prerequisites are
proven by exact invocations.

## 6. Resolve authentication and external controls

Record credential references only. Prefer short-lived federated identity such as OIDC over long-lived credentials. Identify required roles, least privileges, environment protections, reviewers, branch restrictions, and provider-native controls.

Present every proposed external change. Require exact authorization for destructive changes.

Completion criterion: authentication can be resolved without storing a secret and every external change has an approval boundary.

## 7. Define sequential deployment graph

Order preflight checks, builds, artifact publication, target changes, migrations, component deployments, and post-deploy steps. Mark whether each step mutates the target and whether it is proven idempotent. Mutating steps default to zero retries.

For CI/CD, treat the workflow as one harness-visible step unless it exposes native approval gates.

Completion criterion: the sequence and the point at which target mutation begins are explicit.

## 8. Configure concurrency

Identify the CI concurrency group, provider lease, or tracked lock automation for each production target. Missing concurrency control blocks deployment unless the user explicitly overrides it with a recorded reason.

Completion criterion: overlapping deployment behavior is deterministic.

## 9. Protect persistent state

For targets that can change persistent data, identify backup creation, backup verification, restore entry points, retention, and recovery evidence. Verify migrations remain compatible with application rollback.

Irreversible migration exceptions require exact destructive authorization and a documented recovery plan.

Completion criterion: every stateful change has a verified restore or explicitly authorized exception.

## 10. Define rollback

Require tracked rollback and rollback-verification entry points for every component. Define reverse-order rollback for multi-component runs and cancellation after mutation. Define external workflow rollback ownership when CI/CD controls deployment.

Completion criterion: every target-changing step maps to reviewed rollback behavior and a verification result.

## 11. Define health, smoke, and diagnostics

Record baseline health, required smoke tests, diagnostic entry points, external observability references, transient-failure evidence, and deployment-failure evidence.

When existing tests do not define them, ask for global defaults for:

- step timeout;
- diagnostic retry count;
- retry delay;
- maximum diagnostic duration.

Use global retry defaults for diagnostics and smoke tests. Mutating steps require explicit idempotence before retries.

Completion criterion: a failed smoke test deterministically reaches retry, rollback, or external-failure reporting.

## 12. Set confirmation and reporting

Default to `each-step`. Offer `preflight-only`. Explain that both policies retain the mandatory preflight gate and exact destructive authorization.

Confirm Markdown run summaries, external log references, UTC naming, newest-50 retention, and durable architecture updates in `state/MEMORY.md`.

Completion criterion: the user understands the active policy and how to change it by reconfiguration or manual edit.

## 13. Draft and approve

Show:

- `.gitignore` change;
- `config.yaml`;
- `state/MEMORY.md`;
- tracked repository additions or edits;
- external-system changes;
- dry-run and validation plan;
- blockers, overrides, and destructive authorizations.

Obtain explicit approval before writing tracked files or changing external systems. Preserve the setup draft until validation succeeds.

Completion criterion: every proposed mutation is approved, rejected, or deferred.

## 14. Validate and transition

Bootstrap tooling, validate schema and secret policy, snapshot behavioral artifacts, run non-production validation and configured dry runs, then update memory. If the original request was a deployment, transition directly to the mandatory deployment preflight.

Completion criterion: setup passes every Setup completion condition in `SKILL.md`.
