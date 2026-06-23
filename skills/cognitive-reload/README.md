# Cognitive Reload

An interactive, diagram-first codebase tutor with optional teach-back assessment and local progress memory keyed to the authenticated GitHub user.

## Install

Copy this directory into either repository-scoped skill location:

```text
.agents/skills/cognitive-reload   # Codex
.claude/skills/cognitive-reload   # Claude Code
```

Or run the included installer:

```bash
./install-local.sh /path/to/repository both
```

Use `codex` or `claude` instead of `both` to install only one copy.

## Usage

Ask your agent to use the skill from the repository you want to learn:

```text
Use the cognitive-reload skill. Start a first-time reload for this repository.
```

For a returning session:

```text
Use the cognitive-reload skill. Resume my cognitive-reload progress for this repository.
```

For a focused walkthrough:

```text
Use the cognitive-reload skill. Walk me through the authentication subsystem.
```

For help:

```text
Use the cognitive-reload skill. What can this skill do?
```

The skill starts with a repository overview and diagram, pauses for questions at
each layer, and only begins assessment when you explicitly ask for a quiz or
teach-back.

To install and start a private local Kroki renderer for chat diagrams:

```bash
./install-local.sh /path/to/repository both --with-kroki
```

This requires Docker Desktop with Docker Compose. It starts pinned Kroki `0.30.1` gateway and Mermaid companion images on `127.0.0.1:8990`, then records both the port and endpoint in `${XDG_CONFIG_HOME:-~/.config}/cognitive-reload/config.json`. Expect roughly 1.5 GB of compressed image downloads on the first installation. To use another port:

```bash
./install-local.sh /path/to/repository both --with-kroki --kroki-port 8123
```

The selected port may also be supplied through `COGNITIVE_RELOAD_KROKI_PORT`. A command-line `--kroki-port` value takes precedence. The installer checks for port conflicts before starting Docker.

Verify both rendering and T3 image display:

```bash
.agents/skills/cognitive-reload/scripts/kroki-local.sh smoke
```

Paste the emitted Markdown image into T3. If the image appears, Cognitive Reload can render diagrams inline without native Mermaid support.

The image helper applies chat-safe connector and arrowhead colors automatically so that
transparent PNGs remain readable in both dark and light themes.

Manage the service with `kroki-local.sh status` or `kroki-local.sh stop`.

## Publish HITL Cognition

After a reload and optional teach-back, export local progress into repository-visible
artifacts:

```bash
python3 .agents/skills/cognitive-reload/scripts/export_hitl_cognition.py --repo . --dry-run
python3 .agents/skills/cognitive-reload/scripts/export_hitl_cognition.py --repo .
```

Claude installations can use the `.claude/skills/...` path instead.

The default export writes:

```text
hitl-cognition/
  README.md
  current.json
  current.md
  badges/
    hitl-cognition.svg
    hitl-topics.svg
    hitl-assessed.svg
    hitl-freshness.svg
    shields/
      cognition.json
      topics.json
      assessed.json
      freshness.json
  topics/
  history/
```

To add or update a root README badge block:

```bash
python3 .agents/skills/cognitive-reload/scripts/export_hitl_cognition.py --repo . --readme README.md
```

During normal skill use, Cognitive Reload offers this export at the end of a
reload session. After approval, the agent should invoke the exporter directly
rather than asking you to run the command manually.

Public exports omit GitHub login, raw learner questions, and raw assessment answers.
Use `--privacy private` only for intended private/team artifacts.

The progress helper requires Python 3, Git, and an authenticated GitHub CLI (`gh`) for persistent learner identity. Without `gh`, tutoring still works with session-only progress. Local diagram rendering additionally requires Docker Desktop and Docker Compose.

## Version

See `VERSION` and `CHANGELOG.md`. Version is kept outside `SKILL.md` frontmatter so the entrypoint remains compatible with validators that permit only `name` and `description`.
