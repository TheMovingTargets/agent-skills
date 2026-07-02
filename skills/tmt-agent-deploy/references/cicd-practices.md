# CI/CD Deployment Practices

Apply these provider-neutral controls when established automation exists or when proposing it. Do not block an alpha or beta deployment solely because CI/CD is absent; reviewed local automation remains valid.

## Execution boundary

- Prefer triggering and monitoring reviewed deployment workflows over reproducing their commands locally.
- Identify the workflow by a stable file/id and reviewed ref.
- Validate all workflow inputs and record the external run identifier and log URL.
- Treat the workflow as one harness-visible step unless native approval gates exist.
- Resume monitoring an active workflow after interruption; never trigger a duplicate.

## Protection and concurrency

- Bind production jobs to named protected environments.
- Require reviewers where the platform and repository plan support them.
- Restrict deployable branches/tags and prevent self-approval where policy requires independent review.
- Use one concurrency group or provider-native lease per target.
- Keep the skill's mandatory preflight gate even when the workflow also has approvals.

GitHub reference: https://docs.github.com/en/actions/how-tos/deploy/configure-and-manage-deployments/control-deployments

## Identity and secrets

- Prefer OIDC/workload identity with short-lived credentials.
- Grant the workflow and token only the permissions required by the deployment.
- Keep environment secrets behind deployment protections.
- Never copy secret values into config, summaries, command lines, or logs.
- Treat self-hosted runners as non-isolated infrastructure.

GitHub OIDC reference: https://docs.github.com/en/actions/how-tos/secure-your-work/security-harden-deployments/oidc-with-reusable-workflows

## Reuse and provenance

- Reuse reviewed workflows rather than duplicate deployment logic.
- Pin third-party actions and reusable workflows to immutable revisions where feasible.
- Build once and promote the same digest.
- Record commit, artifact digest, workflow ref, and run identifier.
- Use artifact attestations when supported and proportionate to the release risk.

GitHub reusable workflow reference: https://docs.github.com/en/actions/reference/workflows-and-actions/reusing-workflow-configurations

GitHub artifact attestation reference: https://docs.github.com/en/actions/how-tos/secure-your-work/use-artifact-attestations/use-artifact-attestations

## Monitoring and recovery

- Monitor jobs through the provider API or CLI and reference external logs rather than copying them.
- Define workflow timeout and cancellation behavior.
- Make rollback ownership explicit: either the workflow performs and verifies rollback, or a separately reviewed rollback workflow/entry point does.
- After a failed smoke test, complete configured diagnostics before rollback.
- If rollback verification fails, stop workflow retries and enter emergency recovery.

GitHub run monitoring reference: https://docs.github.com/en/actions/how-tos/monitor-workflows/view-workflow-run-history
