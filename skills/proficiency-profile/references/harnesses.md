# Harnesses

The Vocabulary of Harnesses: the coding-agent environments a developer works through. Each id becomes the Activity IRI `https://w3id.org/xapi/devprof/harnesses/<id>`, the object of the day's `use` Statement.

| id | harness | how the skill knows it |
|---|---|---|
| `claude-code` | Claude Code, in any of its surfaces (terminal, IDE, desktop, web) | The skill is running under Claude Code |
| `codex` | OpenAI Codex, CLI or IDE | The skill is running under Codex |

## Ids are forever

Harnesses grow only by a pull request to this file. Once an id is here and in a Profile Repo, don't rename or remove it. Add the new id as a row and keep the old one as an alias line (`old-id → new-id`) at the end of this file.
