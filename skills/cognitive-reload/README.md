# Cognitive Reload

An interactive, diagram-first codebase tutor with optional teach-back assessment and local progress memory. Runs across agent harnesses (Claude Code, Codex, opencode, Pi) and renders diagrams with no setup by default. Progress optionally persists per GitHub user when `gh` is available.

## Install

Cognitive Reload uses the open `SKILL.md` format, so it runs across agent harnesses. It installs
into just two repository-scoped paths that together cover all supported harnesses:

```text
.claude/skills/cognitive-reload    # Claude Code
.agents/skills/cognitive-reload    # Codex, opencode, and Pi (all natively scan .agents/skills)
```

Run the included installer (defaults to `all`, writing both paths):

```bash
./install-local.sh /path/to/repository
```

Pass a harness name to install a single target: `claude`, `codex`, `opencode`, `pi`, or `all`. Add
`--native` to additionally write the harness-specific dirs (`.codex/skills`, `.opencode/skills`,
`.pi/skills`) if you have disabled the shared `.agents` path in your harness.

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

## Diagrams

Diagrams render with **no setup** by default. The bundled `scripts/kroki_url.py` helper emits a
native ```mermaid fence, which renders in GitHub, IDEs, and most agent UIs. Two optional image tiers
exist for clients that cannot render Mermaid:

- **Local (private):** a self-hosted Kroki renders PNGs served from a loopback cache. Best for
  private repositories. See below.
- **Public (opt-in):** render through `https://kroki.io` with `--render-mode public`. This sends the
  diagram source to a third party, so it is **never** used automatically — enable it only for
  non-sensitive repositories.

`auto` (the default) stays network-free: it uses a fence unless a local renderer is configured.

### Optional local renderer (private)

To install and start a private local Kroki renderer:

```bash
./install-local.sh /path/to/repository --with-kroki
```

This requires Docker Desktop with Docker Compose. It starts pinned Kroki `0.30.1` gateway and Mermaid companion images on `127.0.0.1:8990`, then records the port, endpoint, and `render_mode: local` in `${XDG_CONFIG_HOME:-~/.config}/cognitive-reload/config.json`. Expect roughly 1.5 GB of compressed image downloads on the first installation. To use another port:

```bash
./install-local.sh /path/to/repository --with-kroki --kroki-port 8123
```

The selected port may also be supplied through `COGNITIVE_RELOAD_KROKI_PORT`. A command-line `--kroki-port` value takes precedence. The installer checks for port conflicts before starting Docker.

Verify rendering and inline image display in your agent UI:

```bash
<skill-dir>/scripts/kroki-local.sh smoke
```

where `<skill-dir>` is the installed skill directory (e.g. `.agents/skills/cognitive-reload`). Paste the emitted Markdown image into your agent UI; if it appears, Cognitive Reload can render diagrams inline for clients without native Mermaid support. The loopback image URL only works when the renderer and the display UI share a host — remote or cloud harnesses cannot reach it and should use the fence (or public) tier.

The image helper applies chat-safe connector and arrowhead colors automatically so that
transparent PNGs remain readable in both dark and light themes.

Manage the service with `kroki-local.sh status` or `kroki-local.sh stop`.

## Publish HITL Cognition

After a reload and optional teach-back, export local progress into repository-visible
artifacts. Run the exporter from the installed skill directory (`<skill-dir>` is e.g.
`.agents/skills/cognitive-reload` or `.claude/skills/cognitive-reload`):

```bash
python3 <skill-dir>/scripts/export_hitl_cognition.py --repo . --dry-run
python3 <skill-dir>/scripts/export_hitl_cognition.py --repo .
```

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
python3 <skill-dir>/scripts/export_hitl_cognition.py --repo . --readme README.md
```

During normal skill use, Cognitive Reload offers this export at the end of a
reload session. After approval, the agent should invoke the exporter directly
rather than asking you to run the command manually.

Public exports omit GitHub login, raw learner questions, and raw assessment answers.
Use `--privacy private` only for intended private/team artifacts.

The progress helper requires Python 3 and Git. An authenticated GitHub CLI (`gh`) is optional and only enables persistent learner identity across sessions; without it, tutoring still works with session-only progress. Diagrams need nothing extra (native Mermaid fence); the optional **local** image tier additionally requires Docker Desktop and Docker Compose.

## Version

See `VERSION` and `CHANGELOG.md`. Version is kept outside `SKILL.md` frontmatter so the entrypoint remains compatible with validators that permit only `name` and `description`.
