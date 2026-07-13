---
name: tmt-codex-plan-review
description: Dispatch a plan, design, or PRD to the Codex CLI for adversarial cross-model review, then triage the findings into plan amendments. Use when the user wants a plan reviewed by Codex or a second model, says "have codex review this", or wants an adversarial second opinion before implementing.
---

# TMT Codex Plan Review

A cross-model check: Codex is valuable precisely because it shares none of the reviewing agent's context, priors, or blind spots. The skill's job is to give Codex a self-contained **packet**, run it read-only, and triage what comes back.

## Invariants

- **Recursion guard.** If the incoming prompt already contains a review packet (it opens with `# Adversarial plan review`), you are the reviewer, not the dispatcher: perform the review directly against the repository and skip every step below. This skill is installed in cross-harness skill directories, so the Codex-side executor will discover it too — it must never re-dispatch to Codex from inside Codex.
- Codex runs read-only. The review must never modify the repository or external systems.
- The packet is self-contained: Codex sees only what the packet holds plus the repository it is pointed at. Anything left out of the packet is invisible to the review.
- Relay Codex's findings faithfully before judging them. Never blend, soften, or reorder them into your own assessment first.
- No silent fallback: a failed Codex run is a blocker to report with remediation, never a cue to perform the review yourself. A same-model review is not an adversarial review.

## 1. Preflight

Confirm the Codex CLI is present and runnable: `codex --version`, then a trivial probe such as `codex exec --sandbox read-only "Reply with the single word: ready"`.

On failure, stop and report the exact error with remediation — a stale CLI rejecting its configured model (HTTP 400 `invalid_request_error` naming the model) means upgrade the CLI (`npm install -g @openai/codex@latest`) or repoint the model in `~/.codex/config.toml`; an auth error means `codex login`.

Preflight is complete only when the probe returns output from Codex itself.

## 2. Assemble the packet

Write one markdown file to a location outside version control (e.g. the system temp directory), following [references/packet-template.md](references/packet-template.md). The packet carries five sections:

1. **Role and rules** — Codex is an adversarial reviewer; review only, no implementation.
2. **Context** — the problem the plan solves and the evidence or diagnosis behind it.
3. **The plan, verbatim** — never summarized; a summary launders exactly the ambiguities the review should catch.
4. **Attack vectors** — 3–6 specific questions where the plan is most likely wrong (ordering and concurrency, idempotency, migration and backfill safety, breakage of existing behavior, a simpler design that achieves the same goal). Name the key files Codex should read, as repository paths.
5. **Output contract** — numbered findings, each with severity (blocker / major / minor / nit), code evidence, and a concrete amendment; a closing verdict: **sound as written** or **needs revision first**.

The packet is complete when all five sections are present and the plan text is verbatim.

## 3. Run the review

From the repository root:

```bash
codex exec --sandbox read-only -C <repository-root> "$(cat <packet-path>)"
```

Capture the full output (`--output-last-message <file>` on CLIs that support it). If the harness provides a dedicated Codex delegate agent, it may carry this step instead — the packet and output contract are unchanged.

The run is complete when Codex has returned findings and a verdict, not merely exited.

## 4. Triage

Present the work in two strictly separated parts:

1. **Codex's findings, verbatim** — severity, evidence, amendments, verdict, unedited.
2. **Disposition of each finding** — exactly one of:
   - **Accept** — state the concrete plan amendment.
   - **Reject** — cite the code or evidence that disproves it.
   - **Defer** — say why it is out of scope and where it is recorded.

Triage is complete when every finding carries a disposition and the amended plan is shown alongside Codex's verdict. If any finding is a **blocker**, say plainly that the plan should not be implemented as written.
