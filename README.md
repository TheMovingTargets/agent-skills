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

## Privacy

Cognitive Reload stores private learner progress locally by default, outside the target repository. Public HITL exports exclude GitHub login, raw learner questions, and raw assessment answers.

The skill should not write repository files unless the user approves a publish or export step.

TMT Agent Deploy stores repository-specific configuration, state, and sanitized run summaries under the gitignored `.tmt-agent-deploy/` directory. It prohibits secrets in that directory and stores only credential paths or references.

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
.claude-plugin/
  plugin.json
.codex-plugin/
  plugin.json
.agents/plugins/
  marketplace.json
```

Canonical skill sources live under `skills/<skill-name>`. The existing Claude and Codex plugin manifests remain compatibility layers for Cognitive Reload; use the open Skills CLI to install `tmt-agent-deploy`.

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
