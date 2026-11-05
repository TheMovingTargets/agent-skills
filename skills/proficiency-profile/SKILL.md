---
name: proficiency-profile
description: Records Evidence from the learning skills (Trinity Helicopter Program, Cognitive Reload) into the developer's private Proficiency Profile. Use when a learning skill starts or ends a session or records a card, drill or teach-back, reads levels and Currency for triage, or when the developer says "show my profile", "off the record" or "don't record in this repo".
---

# Proficiency Profile

The Proficiency Profile is a developer's durable record of what they can do, built only from Evidence the learning skills record. It lives in a private Profile Repo, a git clone on this machine. Its terms (Evidence, Concept, Area, Harness, Held Evidence) are defined in the repo's `GLOSSARY.md`.

`scripts/profile.py` is the writer: it builds every Statement, checks every id against the Vocabularies, dedupes, locks and commits. Callers pass events, never Statements. Run it as `python3 <this-skill-dir>/scripts/profile.py <command>`. `--help` on any command lists its flags.

Recording is **silent**. During a session, nothing from the writer reaches the developer. The one exception is the single debrief line that `session-end` prints.

## The session lifecycle

A learning skill drives these steps:

1. **Start.** Run `session-start --harness <claude-code|codex> --repo <path>` at the skill's session start. It prints the profile's state:
   - `profile: local-only`: recording is on.
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
   - Exit code 3 means an unknown id. That event wasn't recorded, so carry on teaching.
3. **End.** At the debrief, run `session-end` and put the line it prints into the recap. If it prints nothing, add nothing.

The step is done when `session-end` has run once for the session. A skill driving another learning skill runs one lifecycle for both.

## Reading the profile

`read --lang <pack> [--concepts <id,…>]` prints JSON for triage: the Language's level counts, band and Last Exercised, then each Concept's `level` (`Introduced`, `Explored`, `Practiced`, `Proven`, or null if never met), `band` (`Current`, `Fading`, `Lapsed`, or null before a successful recall), and the `due_for_refresh` list. `read` with no `--lang` gives every Language's roll-up.

Currency is a band with its Last Exercised date. Present it that way, never as a percentage.

## Creating the Profile Repo

When `session-start` prints `profile: none`, fold one question into the first teaching message: whether to keep a private Proficiency Profile of what this session shows. Teaching goes on whatever the answer.

- **Yes:** run `create --host github.com|gitlab.com --login <login>`. Take the login from `gh api user --jq .login` or `glab api user` (its `username`), or ask the developer. Lines from the session so far start recording from that point.
- **No:** run `decline`. Ask again only when the developer brings it up.

## Developer commands

| The developer says | Run |
|---|---|
| "show my profile" | `show`, and print its Markdown as it is. |
| "off the record" | `off-the-record`. This discards the session's uncommitted lines and records nothing more this session. |
| "don't record in this repo" | `exclude-repo --repo <path>`. Only a hash of the remote is stored. |
| a recorded line is factually wrong (wrong Concept, wrong person, recorded by mistake) | `lines [--day YYYY-MM-DD]` to find the line's id, then `void <id>`. A changed mind is never a reason to void. |

Confirm each of these to the developer in one line.
