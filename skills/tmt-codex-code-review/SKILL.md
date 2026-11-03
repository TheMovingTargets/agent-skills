---
name: tmt-codex-code-review
description: Dispatch a code change — a branch, PR, or diff since a fixed point — to the Codex CLI for adversarial cross-model review that hunts defects, then triage each finding into fix, reject, or defer. Use when the user wants code reviewed by Codex or a second model, says "have codex review this branch", or wants an adversarial pass alongside a standards/spec code review.
---

# TMT Codex Code Review

A cross-model defect hunt: Codex is valuable precisely because it shares none of the reviewing agent's context, priors, or blind spots — including the blind spots of whoever wrote the change. The skill's job is to give Codex a self-contained **packet** naming the change and its intent, run it read-only, and triage what comes back.

This is the code sibling of `tmt-codex-plan-review`, which reviews a plan before implementation. A conformance review (does the diff follow the repo's standards, does it match its spec) is a different axis: when both run, report this one as its own section, never merged into or reranked against the others.

## Invariants

- **Recursion guard.** If the incoming prompt already contains a review packet (it opens with `# Adversarial code review` or `# Adversarial plan review`), you are the reviewer, not the dispatcher: perform the review directly against the repository and skip every step below. This skill is installed in cross-harness skill directories, so the Codex-side executor will discover it too — it must never re-dispatch to Codex from inside Codex.
- Codex runs read-only. The review must never modify the repository, its refs, or external systems.
- The packet is self-contained: Codex sees only what the packet holds plus the repository it is pointed at. Anything left out of the packet is invisible to the review.
- Relay Codex's findings faithfully before judging them. Never blend, soften, or reorder them into your own assessment first.
- No silent fallback: a failed Codex run is a blocker to report with remediation, never a cue to perform the review yourself. A same-model review is not an adversarial review.

## 1. Preflight

From the repository root, confirm the Codex CLI is present and runnable: `codex --version`, then a trivial probe such as `codex exec --sandbox read-only -C <repository-root> "Reply with the single word: ready"`.

On failure, stop and report the exact error with remediation — a stale CLI rejecting its configured model (HTTP 400 `invalid_request_error` naming the model) means upgrade the CLI (`npm install -g @openai/codex@latest`) or repoint the model in `~/.codex/config.toml`; an auth error means `codex login`.

Preflight is complete only when the probe returns output from Codex itself.

## 2. Pin the change

The fixed point is whatever the user named — a commit, branch, tag, `main`, `HEAD~5`, or a PR number. If they named none, ask.

- For a PR, resolve its base branch and head commit (`gh pr view <n> --json baseRefName,headRefOid`), fetch both, and use them as fixed point and head.
- Otherwise the head is `HEAD`. When the user wants uncommitted work included, the diff is `git diff <fixed-point>` against the working tree; say so in the packet.

Record the exact diff command (`git diff <fixed-point>...<head>`, three-dot so it compares against the merge-base), the head SHA, and `git log --oneline <fixed-point>..<head>`.

Codex reads files beyond the diff from the working tree, so the **review root** must be checked out at the head. When the current checkout is already there, the review root is the repository root. Otherwise create a detached worktree outside the repository (`git worktree add --detach <temp-path> <head>`), use it as the review root for steps 4–5, and remove it (`git worktree remove <temp-path>`) after the run.

The change is pinned when `git rev-parse` resolves both ends, the diff is non-empty, and the review root's `HEAD` is the head SHA (or the uncommitted work under review). A bad ref or empty diff stops here.

## 3. Gather intent

Codex can judge a defect only against what the change was meant to do.

- **Spec.** Look for the originating issue in commit messages (`#123`, `Closes #45`) and fetch it with the repo's issue-tracker workflow (e.g. `docs/agents/issue-tracker.md`, `gh issue view`); else a spec path the user passes; else a spec under `docs/`, `specs/`, or `.scratch/` matching the branch. If none exists, ask; when the user confirms there is none, the packet states that and Codex reviews against the commit messages.
- **Standards and domain docs.** List the repo files that govern this code — `AGENTS.md`/`CLAUDE.md`, `CONTEXT.md`, relevant ADRs, `CONTRIBUTING.md`. Pass paths; Codex reads them itself.
- **Attack surface.** Read the diff yourself and pick the 3–6 places it is most likely wrong: changed contracts and their callers, error and empty paths, concurrency and ordering, persistence and migrations, auth and input trust boundaries, behaviour the tests do not exercise.

Intent is gathered when the spec is in hand verbatim (or its absence confirmed) and every attack vector names repository paths.

## 4. Assemble the packet

Write one markdown file to a location outside version control (e.g. the system temp directory), following [references/packet-template.md](references/packet-template.md). The packet carries six sections:

1. **Role and rules** — Codex is an adversarial reviewer; review only, no fixes.
2. **The change** — fixed point, head SHA, diff command, commit list. Codex runs the diff itself; the packet carries the command, not the diff.
3. **Intent** — the spec, verbatim; a summary launders exactly the ambiguities the review should catch.
4. **Governing docs and key files** — repository paths, one line each on why they matter.
5. **Attack vectors** — the questions from step 3.
6. **Output contract** — numbered findings, each with severity (blocker / major / minor / nit), `path:line` evidence, a failure scenario, and a concrete fix; a list of what was checked and found sound; a closing verdict: **mergeable** or **needs changes first**.

The packet is complete when all six sections are present and the spec text is verbatim.

## 5. Run the review

From the repository root, feed the packet on stdin — a packet passed as one shell argument can exceed the OS argument limit:

```bash
codex exec --sandbox read-only -C <repository-root> -o <output-path> - < <packet-path>
```

Use plain `codex exec`, not `codex exec review`: the built-in reviewer takes no `--sandbox` flag, its `--base` accepts only a branch, and it has no place for the spec or attack vectors. If the harness provides a dedicated Codex delegate agent, it may carry this step instead — the packet and output contract are unchanged.

The run is complete when Codex has returned findings and a verdict, not merely exited.

## 6. Triage

Present the work in two strictly separated parts:

1. **Codex's findings, verbatim** — severity, evidence, failure scenarios, fixes, checked-and-sound list, verdict, unedited.
2. **Disposition of each finding** — exactly one of:
   - **Fix** — state the concrete code change at `path:line`.
   - **Reject** — cite the code, test, or spec line that disproves it.
   - **Defer** — say why it is out of scope and where it is recorded (an issue in the repo's tracker).

Triage is complete when every finding carries a disposition and Codex's verdict is shown beside your own. If any finding is a **blocker** you did not reject, say plainly that the change should not merge as written. Dispositions describe changes; applying them is a separate request from the user.
