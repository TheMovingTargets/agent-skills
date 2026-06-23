# Cognitive Reload Skill

Guided, resumable codebase tutoring for agentic development. Cognitive Reload helps an agent rebuild a developer's mental model of a repository, teach architecture diagram-first, resume per GitHub user and repository, and publish sanitized HITL cognition artifacts.

## Install

Install interactively with the cross-agent skills installer:

```bash
npx skills@latest add your-org/cognitive-reload-skill
```

Then choose `cognitive-reload` and the agent targets you want, such as Claude Code, Codex, or both.

For a non-interactive install, use:

```bash
npx skills@latest add your-org/cognitive-reload-skill \
  --skill cognitive-reload \
  --agent claude-code \
  --agent codex \
  --global
```

Replace `your-org/cognitive-reload-skill` with the final GitHub repository once published.

## Use

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

## What It Does

- Starts with a broad repository map before code details.
- Teaches diagram-first, then code and tests.
- Pauses for human questions between layers.
- Saves local progress keyed by authenticated GitHub user and repository.
- Supports optional teach-back assessment.
- Exports public HITL cognition dashboards and badges without raw learner answers or raw questions.

## Privacy

The skill stores private learner progress locally by default, outside the target repository. Public HITL exports exclude GitHub login, raw learner questions, and raw assessment answers.

The skill should not write repository files unless the user approves a publish/export step.

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

The canonical skill source is `skills/cognitive-reload`. The Claude and Codex plugin manifests are compatibility layers around the same skill.

## Update

```bash
npx skills@latest update
```

Or reinstall from the repository:

```bash
npx skills@latest add your-org/cognitive-reload-skill --skill cognitive-reload --global
```

## License

MIT
