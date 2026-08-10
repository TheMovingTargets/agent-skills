# TMT Agent Skills

Reusable cross-agent skills maintained by TheMovingTargets. This repository packages skills in the open `SKILL.md` format and keeps them installable across agent harnesses such as Claude Code, Codex, opencode, and Pi.

Install into the current project or folder:

```bash
npx skills@latest add TheMovingTargets/agent-skills
```

## Included Skills

### Cognitive Reload

Guided, resumable codebase tutoring for agentic development. Cognitive Reload helps an agent rebuild a developer's mental model of a repository, teach architecture diagram-first, resume per GitHub user and repository, and publish sanitized HITL cognition artifacts.

Use it for:

- First-time repository onboarding.
- Returning-developer reloads.
- Architecture walkthroughs.
- Code teach-backs and optional assessment.
- Public HITL cognition dashboards and badges.

### TMT Agent Deploy

Provider- and harness-neutral deployment setup and execution. TMT Agent Deploy:

- Discovers existing deployment scripts, runbooks, infrastructure, and CI/CD.
- Creates a private, gitignored `.tmt-agent-deploy/` configuration and state area.
- Reuses reviewed repository automation and prefers established CI/CD workflows.
- Requires deployment preflight approval and configurable per-step confirmation.
- Runs smoke tests, diagnoses failures, and automatically invokes reviewed rollback.
- Produces sanitized local run summaries with external log references.

### TMT Field Debug

Read-only field diagnosis for incidents on deployed infrastructure. TMT Field Debug:

- Consumes TMT Agent Deploy run records, source identity, and external log references.
- Correlates bounded remote logs, health evidence, traces, metrics, and deployed versions.
- Tests ranked hypotheses with production-safe, read-only probes.
- Stops for clarification whenever target, safety, or evidence meaning is ambiguous.
- Produces a sanitized Markdown diagnosis with an implementation-ready brief.

Install only TMT Field Debug:

```bash
npx skills@latest add TheMovingTargets/agent-skills \
  --skill tmt-field-debug
```

### PDF Signature Emded

Visible PDF and Word signature image placement with reusable JSON placement configs. PDF Signature Emded:

- Interviews users to translate signature placement intent into deterministic PDF coordinates or DOCX text anchors.
- Saves portable JSON configs for repeatable batch signing.
- Applies one or more signature images to one or more PDFs or Word documents while preserving original inputs.
- Uses structural validation before writing signed document copies.

Install only PDF Signature Emded:

```bash
npx skills@latest add TheMovingTargets/agent-skills \
  --skill pdf-signature-emded
```

### TMT Smart Merge

Deliberate, intent-preserving Git conflict resolution. TMT Smart Merge:

- Reconstructs both histories from commits, index stages, code, tests, and documentation.
- Interviews one decision at a time and recommends an answer with concrete consequences.
- Keeps opening decision gates as later conflicts, tests, and history reveal new tradeoffs.
- Resolves semantic clusters instead of blindly choosing “ours” or “theirs.”
- Verifies combined behavior and requires separate approval before staging and continuing.

Install only TMT Smart Merge:

```bash
npx skills@latest add TheMovingTargets/agent-skills \
  --skill tmt-smart-merge
```

Install only TMT Agent Deploy:

```bash
npx skills@latest add TheMovingTargets/agent-skills \
  --skill tmt-agent-deploy
```

Install only Cognitive Reload:

```bash
npx skills@latest add TheMovingTargets/agent-skills \
  --skill cognitive-reload
```

### TMT Codex Plan Review

Adversarial cross-model review of a plan, design, or PRD via the Codex CLI. TMT Codex Plan Review:

- Assembles a self-contained review packet: context, the plan verbatim, attack vectors, and a strict output contract.
- Runs Codex read-only against the repository (`codex exec --sandbox read-only`).
- Relays findings verbatim (severity, code evidence, amendments, verdict), then dispositions each one: accept, reject, or defer.
- Fails loudly with remediation when Codex is unavailable — it never substitutes a same-model review.

Install only TMT Codex Plan Review:

```bash
npx skills@latest add TheMovingTargets/agent-skills \
  --skill tmt-codex-plan-review
```

## Install Options

Install into the current project or folder:

```bash
npx skills@latest add TheMovingTargets/agent-skills
```

This creates `.agents/skills/cognitive-reload` and `skills-lock.json` in the directory where you run the command.

Install `cognitive-reload` globally for the current user:

```bash
npx skills@latest add TheMovingTargets/agent-skills \
  --skill cognitive-reload \
  --global
```

Install globally for specific agent targets:

```bash
npx skills@latest add TheMovingTargets/agent-skills \
  --skill cognitive-reload \
  --agent claude-code \
  --agent codex \
  --global
```

List available skills without installing:

```bash
npx skills@latest add TheMovingTargets/agent-skills --list
```

## Usage

In a repository, ask your agent:

```text
Use the cognitive-reload skill. Start a first-time reload for this repository.
```

To resume local progress:

```text
Use the cognitive-reload skill. Resume my existing local cognitive-reload progress for this GitHub user and repository.
```

To publish sanitized HITL cognition artifacts:

```text
Use the cognitive-reload skill. Publish the public HITL cognition dashboard and README badges from my progress.
```

To configure and deploy a repository:

```text
Build and deploy the full stack to the Production EC2 instance. Complete smoke tests and report back the results.
```

To deploy one scoped service:

```text
Build a new instance of the client service, redeploy for this user, and report back after confirming that the service came back up.
```

If required scope is ambiguous, TMT Agent Deploy stops and asks for the exact target parameters.

To change confirmation policy or another persisted setting:

```text
Use tmt-agent-deploy in reconfiguration mode and change the confirmation policy.
```

To investigate a problem on an already-deployed service:

```text
Use tmt-field-debug to diagnose the production API errors since the latest rollout. Use the deployment run and remote logs, test safe hypotheses, and write an implementation-ready report.
```

To resolve an interrupted integration without losing either branch's intent:

```text
Use tmt-smart-merge to inspect this conflicted rebase, interview me one decision at a time, resolve approved semantic clusters, and ask before staging or continuing.
```

## Privacy

Cognitive Reload stores private learner progress locally by default, outside the target repository. Public HITL exports exclude GitHub login, raw learner questions, and raw assessment answers.

The skill should not write repository files unless the user approves a publish or export step.

TMT Agent Deploy stores repository-specific configuration, state, and sanitized run summaries under the gitignored `.tmt-agent-deploy/` directory. It prohibits secrets in that directory and stores only credential paths or references.

TMT Field Debug writes sanitized reports with evidence references rather than raw remote logs, credentials, or sensitive payloads.

## Repository Layout

```text
skills/
  cognitive-reload/
    SKILL.md
    references/
    scripts/
    assets/
    schemas/
    templates/
  tmt-agent-deploy/
    SKILL.md
    references/
    schemas/
    scripts/
    tests/
  pdf-signature-emded/
    SKILL.md
    references/
    scripts/
  tmt-field-debug/
    SKILL.md
    agents/
    references/
  tmt-smart-merge/
    SKILL.md
    agents/
    references/
.claude-plugin/
  plugin.json
.codex-plugin/
  plugin.json
.agents/plugins/
  marketplace.json
```

Canonical skill sources live under `skills/<skill-name>`. The existing Claude and Codex plugin manifests remain compatibility layers for Cognitive Reload; use the open Skills CLI to install `tmt-agent-deploy`, `tmt-field-debug`, or `tmt-smart-merge`.

## Update

```bash
npx skills@latest update
```

Or reinstall from the repository:

```bash
npx skills@latest add TheMovingTargets/agent-skills --skill cognitive-reload --global
```

## License

MIT
