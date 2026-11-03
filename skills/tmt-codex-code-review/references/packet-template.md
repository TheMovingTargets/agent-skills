# Review packet template

Copy this structure into a single markdown file. Replace every `<...>` placeholder; delete nothing. The packet must stand alone: Codex reads it plus the repository, nothing else.

```markdown
# Adversarial code review

You are an adversarial reviewer. This packet IS the review run: perform the
review yourself, directly against the repository. Do not invoke any skill, do
not run codex, and do not delegate — a code-review skill you discover in your
skill directories describes the dispatch that already brought you this packet.

Your job is to find defects in the change below: wrong behaviour, broken
contracts and callers, unhandled error and empty paths, ordering and
concurrency bugs, data-loss or migration hazards, security and trust-boundary
mistakes, and behaviour the tests do not actually exercise. Read beyond the
diff — callers, callees, tests, and schema — wherever a finding depends on it.
Review only — do NOT fix anything, modify any file, or change any git ref.
Cite code evidence (path:line) for every finding.

## The change

- Fixed point: <ref and resolved SHA>
- Head: <ref and resolved SHA> — the working tree you are in is checked out at this head
- Diff: `<git diff <fixed-point>...<head>>` <or "includes uncommitted work: git diff <fixed-point>">
- Commits:

<git log --oneline <fixed-point>..<head>, verbatim>

## Intent

<The originating issue or spec, VERBATIM, with its identifier. Or exactly:
"No spec exists; review against the commit messages above.">

## Governing docs and key files

- <repo-relative path — one line on why it matters>
- <...>

## Specific questions to attack

- <A question naming the change's riskiest assumption, with paths>
- <An error-path / edge-case question>
- <An ordering / concurrency / idempotency question>
- <A persistence, migration, or compatibility question>
- <"Which changed behaviour do the tests not actually exercise?">

## Required output

Return a numbered list of findings. Each finding must have:

1. Severity: blocker / major / minor / nit.
2. The code evidence (path:line).
3. A failure scenario: concrete input or state, and the wrong result.
4. A concrete suggested fix.

Then list briefly what you checked and found sound.

End with an overall verdict, exactly one of:
- **Mergeable** — no finding gates the merge.
- **Needs changes first** — list which findings gate the merge.
```
