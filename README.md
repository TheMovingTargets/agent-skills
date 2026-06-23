# Agent Skills

Reusable cross-agent skills maintained by TheMovingTargets. This repository packages skills in the open `SKILL.md` format and keeps them installable across agents such as Claude Code and Codex.

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

## Privacy

Cognitive Reload stores private learner progress locally by default, outside the target repository. Public HITL exports exclude GitHub login, raw learner questions, and raw assessment answers.

The skill should not write repository files unless the user approves a publish or export step.

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
.claude-plugin/
  plugin.json
.codex-plugin/
  plugin.json
.agents/plugins/
  marketplace.json
```

The canonical skill source is `skills/cognitive-reload`. Claude and Codex plugin manifests are compatibility layers around the same skill.

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
