---
name: proficiency-profile
description: Records Evidence from the learning skills (Trinity Helicopter Program, Cognitive Reload) into the developer's private Proficiency Profile. Use when a learning skill starts or ends a session or records a card, drill or teach-back, reads levels and Currency for triage, or when the developer says "show my profile", "link my <host> account", "add a remote", "sync", "off the record" or "don't record in this repo".
---

# Proficiency Profile

The Proficiency Profile is a developer's durable record of what they can do, built only from Evidence the learning skills record. It lives in a private Profile Repo: a git clone on this machine, pushed to a private repo on github.com or gitlab.com when one is connected. Its terms (Evidence, Concept, Area, Harness, Held Evidence) are defined in the repo's `GLOSSARY.md`.

`scripts/profile.py` is the writer: it builds every Statement, checks every id against the Vocabularies, dedupes, locks and commits. Callers pass events, never Statements. Run it as `python3 <this-skill-dir>/scripts/profile.py <command>`. `--help` on any command lists its flags.

Recording is **silent**. During a session, nothing from the writer reaches the developer. The one exception is the single debrief line that `session-end` prints.

## The session lifecycle

A learning skill drives these steps:

1. **Start.** Run `session-start --harness <claude-code|codex> --repo <path>` at the skill's session start. It prints the profile's state:
   - `profile: remote` or `profile: local-only`: recording is on.
   - `profile: none`: ask the creation question (below).
   - `profile: declined` or `profile: excluded`: record nothing and say nothing.
2. **Record.** Run one `record` command per event, as it happens:

   | Session event | Command |
   |---|---|
   | Concept card shown | `record experienced --lang <pack> --concept <id>` |
   | Weeds rung 2 or deeper | `record interacted --lang <pack> --concept <id>` |
   | `fly` drill attempt | `record drill --lang <pack> --concept <id> --grade good\|hard\|again` |
   | Scored teach-back | `record teachback --lang <pack> --concepts <id,…> --score <0-5>` |

   - Add `--area <id>` only when the code's place in the stack is obvious.
   - The ids come from the Vocabularies: a Trinity pack, Cognitive Reload's `references/architecture-concepts.md`, and this skill's `references/areas.md` and `references/harnesses.md`.
   - Pass ids only from the Vocabularies; never invent one. The writer holds any id it doesn't know as Held Evidence, off the Profile Repo, and the debrief lists it.
3. **End.** At the debrief, run `session-end` and put the line it prints into the recap, word for word. If it prints nothing, add nothing. It may end with held ids to check (below), or an offer to add a remote or to link an account. Act on an offer only when the developer says yes.

The step is done when `session-end` has run once for the session. A skill driving another learning skill runs one lifecycle for both. A second `session-start` for the same repo, Harness and day joins the running session, so it never adds a commit.

## Reading the profile

`read --lang <pack> [--concepts <id,…>]` prints JSON for triage: the Language's level counts, band and Last Exercised, then each Concept's `level` (`Introduced`, `Explored`, `Practiced`, `Proven`, or null if never met), `band` (`Current`, `Fading`, `Lapsed`, or null before a successful recall), and the `due_for_refresh` list. `read` with no `--lang` gives every Language's roll-up.

Currency is a band with its Last Exercised date. Present it that way, never as a percentage.

## Creating the Profile Repo

When `session-start` prints `profile: none`, fold one question into the first teaching message: whether to keep a private Proficiency Profile of what this session shows. Teaching goes on whatever the answer.

- **Yes:** run `create --host github.com|gitlab.com --login <login> --remote`. One yes covers both the local clone and the private remote. Pick the host whose CLI (`gh` or `glab`) is signed in; take the login from `gh api user --jq .login` or `glab api user` (its `username`), or ask the developer. If neither CLI is signed in, the profile starts local-only and the command prints the sign-in hint to pass on. Never run a login yourself. Recording starts from that point in the session.
- **No:** run `decline`. Ask again only when the developer brings it up.

## Developer commands

| The developer says | Run |
|---|---|
| "show my profile" | `show`, and print its Markdown as it is. |
| "add a remote" | `add-remote --host github.com\|gitlab.com` |
| "sync" | `sync` |
| "link my <host> account" | `link --kind <kind> --name <name>`, with the kind and name below. |
| "off the record" | `off-the-record`. This discards the session's uncommitted lines and records nothing more this session. |
| "don't record in this repo" | `exclude-repo --repo <path>`. Only a hash of the remote is stored. |
| a recorded line is factually wrong (wrong Concept, wrong person, recorded by mistake) | `lines [--day YYYY-MM-DD]` to find the line's id, then `void <id>`. A changed mind is never a reason to void. |

Confirm each of these to the developer in one line.

## Under Codex

Codex's default sandbox can't write the Profile Repo and has no network. When a write is blocked, `session-start` prints a `PROFILE_WRITE_BLOCKED` line, then the offer and the config snippet, and the writer keeps the session's Evidence in a spool under `$TMPDIR`. Every command still exits 0.

1. Offer the developer one escalated rerun of `session-start` (`require_escalated`, with the justification "write your proficiency profile outside the workspace"). If they approve, run every `profile.py` command this session escalated.
2. If they decline, carry on teaching. The spool is merged at the next session that can write.
3. Show the printed `config.toml` snippet once, so it doesn't happen again. `codex-config` prints it on request. Its `network_access` line is optional, for sync.

In a Codex cloud task there is no Profile Repo: skip this skill.

## Checking Held Evidence

When the debrief lists held ids, ask the developer about each one: does it name a public technology or pattern, and is it free of the repo's own names (an internal framework, service or package)?

- **No to either:** run `held discard <ref>`. Its lines are dropped.
- **Yes to both:** run `held confirm <ref>`. It prints a draft Vocabulary PR as JSON: the target `file` in `TheMovingTargets/agent-skills`, a `row` with placeholders (null for a new language pack), a `title` and a `body`. Fill the placeholders in generic wording, then offer to open the PR. Open it only on the developer's yes. After it's open, run `held pr <ref> <url>`.

`held list` shows each ref, its line count and status. The `ref` forms are `concept:<pack or arch>/<id>`, `language:<id>`, `area:<id>` and `harness:<id>`.

Held lines are released at a later `session-start`, once the id is installed: aliased ids are rewritten to their target, and each line keeps its original date. Lines whose PR was closed unmerged are dropped then.

A language pack that Trinity built on the fly follows the same path: saving the pack is the proposal.

## Linking an account

A Linked Identity lets work under another account count toward this profile. Record only a bare login, or an id: never an organization, a hostname or an email address.

| Host | `--kind` | `--name` |
|---|---|---|
| github.com | `github` | login, from `gh api user --jq .login` |
| gitlab.com | `gitlab` | username, from `glab api user` |
| Azure DevOps | `azure-devops` | the `id` GUID from `profiles/me`, plus `--display <displayName>` (see below) |
| GitHub Enterprise | `github-enterprise` | login, from `gh api user --hostname <host> --jq .login` |
| self-managed GitLab | `gitlab-self-managed` | username, from `glab api user --hostname <host>` |

For Azure DevOps, read `id` and `displayName` from `az rest --resource 499b84ac-1321-427f-aa17-267ca6975798 --url "https://app.vssps.visualstudio.com/_apis/profile/profiles/me?api-version=7.1"`.

Each session's Evidence is recorded under the linked account for the repo's host, and otherwise under the account the profile was created with.
