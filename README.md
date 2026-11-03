# TMT Agent Skills

Reusable cross-agent skills maintained by TheMovingTargets. This repository packages skills in the open `SKILL.md` format and keeps them installable across agent harnesses such as Claude Code, Codex, opencode, and Pi.

Install into the current project or folder:

```bash
npx skills@latest add TheMovingTargets/agent-skills
```

### Install as a plugin

The repository is also a plugin marketplace, `tmt`, with one plugin, `tmt-agent-skills`, that bundles every skill below.

Claude Code:

```bash
claude plugin marketplace add TheMovingTargets/agent-skills
claude plugin install tmt-agent-skills@tmt
```

Codex:

```bash
codex plugin marketplace add TheMovingTargets/agent-skills
codex plugin add tmt-agent-skills@tmt
```

Claude Code only auto-updates a third-party marketplace after you turn on auto-update for it (`autoUpdate: true` on the marketplace, or **Enable auto-update** in `/plugin` → Marketplaces). Plugins reinstall only when the `version` in `.claude-plugin/plugin.json` and `.codex-plugin/plugin.json` changes, so bump both with `package.json` on every release.

## Included Skills

### Cognitive Reload

Guided, resumable codebase tutoring for agentic development. Cognitive Reload helps an agent rebuild a developer's mental model of a repository, teach architecture diagram-first, resume per GitHub or Azure DevOps user and repository, and publish sanitized HITL cognition artifacts.

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

### DOC/PDF Signature Embed

Visible PDF and Word signature image placement with reusable JSON placement configs. DOC/PDF Signature Embed:

- Interviews users to translate signature placement intent into deterministic PDF coordinates or DOCX text anchors.
- Saves portable JSON configs for repeatable batch signing.
- Applies one or more signature images to one or more PDFs or Word documents while preserving original inputs.
- Uses structural validation before writing signed document copies.

Install only DOC/PDF Signature Embed:

```bash
npx skills@latest add TheMovingTargets/agent-skills \
  --skill doc-pdf-signature-embed
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

### TMT Codex Code Review

Adversarial cross-model defect hunt on a code change — a branch, PR, or diff since a fixed point — via the Codex CLI. The code sibling of TMT Codex Plan Review, and a separate axis from standards/spec conformance review. TMT Codex Code Review:

- Pins the change (fixed point, head SHA, diff command, commits) and gathers its intent: the originating spec verbatim, governing docs, and attack vectors.
- Runs Codex read-only against the repository; Codex runs the diff itself and reads beyond it.
- Relays findings verbatim (severity, `path:line` evidence, failure scenario, fix, verdict), then dispositions each one: fix, reject, or defer.
- Fails loudly with remediation when Codex is unavailable — it never substitutes a same-model review.

Install only TMT Codex Code Review:

```bash
npx skills@latest add TheMovingTargets/agent-skills \
  --skill tmt-codex-code-review
```

### Trinity Helicopter Program

Side-by-side language fluency for experienced engineers. When an agent ports code into a language you don't know yet (for example TypeScript or Python MCP servers into C#/.NET), or you're reading a finished repository in that language, Trinity Helicopter Program teaches the target language through the real code, the moment it needs it. It:

- Shows faithful source and target excerpts side by side, with a construct mapping table.
- Triages each concept against what you already know: silence for known concepts, a one-line bridge from Rust/Java/C++/TypeScript/Python where a near analog exists, and a short card for genuinely new concepts and false friends.
- Lets you `skip` a concept (never explained again) or go into the `weeds` one rung at a time (semantics, runtime machinery, edge cases, idiom), and `surface` back to exactly where you were.
- Records port decisions ("record over class because…") and behaviour differences between source and port as teaching material.
- Keeps a local concept ledger per learner and target language, shared across repositories, outside any working tree.
- Offers optional fluency drills (`fly`) only on request.

Ships with a C#/.NET language pack, including the C# MCP SDK; other target languages can be added as packs.

Install only Trinity Helicopter Program:

```bash
npx skills@latest add TheMovingTargets/agent-skills \
  --skill trinity-helicopter-program
```

### Cognitive Reload with Trinity

Runs Cognitive Reload and Trinity Helicopter Program together on the same excerpts, for onboarding to or reloading a repository written in a language you're not yet fluent in. Cognitive Reload owns the route (orientation, system diagram, topic map, cursor, progress, assessment gate); Trinity adds the language layer at each code and test excerpt. Install all three:

```bash
npx skills@latest add TheMovingTargets/agent-skills \
  --skill cognitive-reload --skill trinity-helicopter-program --skill cognitive-reload-with-trinity
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

To learn a language alongside a port:

```text
Use trinity-helicopter-program. You're porting src/tools/*.ts to C#; teach me the C# side by side as you go. I know Rust, Java and TypeScript.
```

To reload a repository and learn its language at the same time:

```text
Cognitive reload with trinity on this repo. I know the Python original but have never written C#.
```

## Privacy

Cognitive Reload stores private learner progress locally by default, outside the target repository. Public HITL exports exclude GitHub login, raw learner questions, and raw assessment answers.

The skill should not write repository files unless the user approves a publish or export step.

TMT Agent Deploy stores repository-specific configuration, state, and sanitized run summaries under the gitignored `.tmt-agent-deploy/` directory. It prohibits secrets in that directory and stores only credential paths or references.

Trinity Helicopter Program stores its concept ledger and port flight logs locally under `${XDG_DATA_HOME:-~/.local/share}/trinity-helicopter-program/`, outside any repository, and never publishes them.

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
  doc-pdf-signature-embed/
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
  trinity-helicopter-program/
    SKILL.md
    agents/
    references/languages/
    scripts/
  cognitive-reload-with-trinity/
    SKILL.md
    agents/
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
