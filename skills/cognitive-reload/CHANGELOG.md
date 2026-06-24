# Changelog

## 0.6.3 - 2026-06-24

- Emit short cached local PNG URLs by default instead of long direct Kroki Base64 paths.
- Start and verify a loopback static asset server for cached diagram images.
- Keep `--direct-kroki-url` available only for debugging direct Kroki path issues.

## 0.6.2 - 2026-06-24

- Assert that generated Kroki image path segments contain only unpadded URL-safe Base64 characters.
- Report Kroki decode failures as malformed or manually edited image URLs.
- Promote the `scripts/kroki_url.py --check` requirement into the main tutoring flow to prevent handwritten local Kroki URLs.

## 0.6.1 - 2026-06-23

- Make HITL cognition publishing the default closing offer after reload sessions.
- Require agents to run the exporter directly after learner approval instead of returning manual commands.
- Default approved publishing to `hitl-cognition/` plus root README badge block updates.

## 0.6.0 - 2026-06-23

- Add HITL cognition publishing for converting local learner progress into repository-visible artifacts.
- Generate `hitl-cognition/` with `current.json`, Markdown dashboards, topic summaries, history snapshots, SVG badges, and Shields-compatible JSON.
- Add a 0-100 HITL cognition index with orientation, exploration, verified assessment, and freshness components.
- Keep public exports sanitized by default, excluding GitHub login, raw learner questions, and raw assessment answers.
- Support optional root README badge block insertion with explicit approval.
- Add reusable badge and dashboard rendering scripts.

## 0.5.5 - 2026-06-23

- Emit unpadded URL-safe Base64 for Kroki image paths to avoid chat/proxy path mangling.
- Document Kroki `400 Unable to decode the source` as a malformed image URL issue.
- Require regenerating images through `scripts/kroki_url.py --check` instead of retrying stale URLs.

## 0.5.4 - 2026-06-22

- Add an intuition-first dialogue protocol for code and parameter clarifications.
- Default to zero repository reads for questions about an excerpt already on screen.
- Prohibit unrelated implementation gaps and exhaustive field lists in focused answers.
- Batch learner questions into natural progress checkpoints instead of persisting each one.

## 0.5.3 - 2026-06-22

- Add deterministic density guards for chat-rendered Mermaid diagrams.
- Automatically transpose horizontal flowcharts above four nodes to a vertical layout.
- Reject flowcharts above eight nodes and sequence diagrams above four participants.
- Limit tutorial turns to one diagram and discourage prose that merely repeats every node.

## 0.5.2 - 2026-06-22

- Apply a neutral Mermaid theme automatically when generating Kroki URLs.
- Give flowchart connectors and arrowhead markers explicit, higher-contrast colors.
- Preserve caller-supplied Mermaid initialization directives for custom themes.

## 0.5.1 - 2026-06-22

- Change the default local Kroki port from `8000` to `8990`.
- Persist both `kroki_port` and `kroki_url` for use by future skill sessions.
- Allow configuration with `--kroki-port` or `COGNITIVE_RELOAD_KROKI_PORT`.
- Detect occupied ports before invoking Docker and report a precise recovery command.
- Reuse an existing healthy Kroki instance on the configured port.

## 0.5.0 - 2026-06-22

- Add an optional self-hosted Kroki gateway and Mermaid companion to the installer.
- Bind Kroki to loopback and store its endpoint outside the production repository.
- Render Mermaid as ordinary Markdown PNG images for clients without native Mermaid support.
- Add deterministic URL generation, server checks, service management, and a T3 smoke test.
- Retain a concise text fallback and prohibit public rendering of private architecture.

## 0.4.1 - 2026-06-22

- Restore `install-local.sh` for Codex, Claude Code, or dual repository installation.

## 0.4.0 - 2026-06-22

- Start first-time sessions with a concise repository summary and system diagram.
- Add a learner-controlled zoom ladder from architecture to code and tests.
- Require diagrams before implementation excerpts for relational concepts.
- Keep assessment invisible until the learner explicitly opts in.
- Persist resumable progress by authenticated GitHub user and repository outside the working tree.
- Record questions, unresolved issues, code anchors, and exact resume points.
- Remove file-inspection homework and expose small guided excerpts directly.
