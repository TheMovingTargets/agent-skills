---
name: tmt-smart-merge
description: Resolve Git merge, rebase, cherry-pick, and revert conflicts by reconstructing each side's intent from history, code, tests, and documentation; interviewing the user one decision at a time; applying approved semantic resolutions; and verifying the combined behavior. Use when Git reports unmerged paths or conflict markers, an integration operation is blocked, or a user asks to reconcile divergent branches without silently discarding either side's behavior.
---

# TMT Smart Merge

Treat a conflict as a design decision, not a marker-removal exercise. Preserve the intent of both histories where those intents can coexist, and make every real tradeoff visible to the user.

## Invariants

- Inspect the repository, operation state, history, code, tests, and documentation before asking anything discoverable.
- Ask one concise question at a time. State the evidence, recommend an answer, explain its consequence, and wait. Never bury several decisions in one prompt.
- Keep questioning after the initial interview. Open a new decision gate whenever new evidence or a proposed resolution can change behavior, compatibility, data, security, performance, file lifecycle, or Git operation state.
- Identify sides by branch, commit, and intent. Do not rely on “ours” and “theirs”; their meaning is easy to invert during a rebase.
- Preserve unrelated tracked and untracked work. Never stash, clean, reset, abort, switch branches, or restore user changes to make the conflict easier.
- Never fetch, pull, install dependencies, invoke a custom merge driver, or start an integration operation without approval. Show the exact action and scope first.
- Never resolve a semantic conflict by taking an entire side, deleting markers, or trusting a clean parse. Prove the integrated behavior.
- Separate editing, staging, continuation, commit, and push. Approval for one is not approval for the next. Never push unless separately requested.
- Treat the user's answers as the merge contract. If later evidence contradicts an answer, surface the contradiction and ask again rather than silently reinterpreting it.

## Use decision gates

Use this format for every question:

1. **Evidence:** Give the smallest relevant fact from code, history, or tests.
2. **Decision:** Ask exactly one question.
3. **Recommendation:** Lead with the recommended answer and why.
4. **Consequence:** State what changes depending on the answer.

Ask at least at these gates:

- when source, destination, operation, desired outcome, or safe scope cannot be proven locally;
- after presenting the conflict map, before editing the first semantic cluster;
- before choosing between incompatible behaviors, public contracts, migrations, dependency versions, deletions, renames, generated output, binaries, or submodule identities;
- when a test, build result, or new history evidence changes the apparent intent;
- after each semantic cluster or approved mechanical batch is resolved, before staging its explicit paths;
- before continuing the Git operation or creating a commit.

Do not repeat a settled question unless evidence changed. Batch only independent mechanical conflicts whose resolution is already entailed by the approved merge contract.

## 1. Establish the operation boundary

Start read-only. Inspect at least:

```text
git status --porcelain=v2 --branch
git diff --name-only --diff-filter=U
git ls-files -u
```

Resolve the repository root, current `HEAD`, current branch or detached state, unmerged paths, unrelated modifications, and active merge, rebase, cherry-pick, or revert metadata. Use `git rev-parse --git-path <state-file>` rather than assuming the Git directory layout.

If no integration operation is active, distinguish committed conflict markers from an integration request. Do not start a merge, rebase, cherry-pick, or revert until the user approves the exact source, destination, command, dirty-worktree implications, and whether network access is needed.

If unrelated changes overlap a conflicted path, stop and ask how to preserve them. If they do not overlap, fence all edits and Git commands to explicit conflict paths.

Complete this step only when the operation type, exact commits, worktree boundary, and allowed next action are known.

## 2. Run the initial merge interview

Explore first, then resolve the remaining merge contract one question at a time. Establish:

- the observable outcome the integrated history must produce;
- behavior, APIs, data contracts, migrations, fixes, and compatibility guarantees that must survive from each side;
- explicit non-goals and changes that should not cross the boundary;
- the acceptable validation depth and any environment constraints;
- whether the user wants resolution prepared only or also wants staging and operation continuation.

Recommend the narrowest contract supported by repository evidence. Do not ask the user to recite branch intent that commit history, issues, tests, or documentation already establish.

The initial interview is complete only when the operation and first semantic decision can proceed without guessing. It does not close later decision gates.

## 3. Reconstruct both intents

For every unmerged path, inspect the merge base and available index stages, the commits that changed it on each side, nearby call sites, tests, schemas, and relevant documentation. Use path history and blame to distinguish deliberate behavior from incidental text movement.

Read [references/conflict-playbook.md](references/conflict-playbook.md) completely before resolving any nontrivial conflict. Apply its stage-role rules, conflict classifications, and category-specific evidence requirements.

Group files into semantic clusters such as one API change plus its callers and tests. Do not equate one file with one decision. Build a conflict map containing:

| Cluster | Paths | Current-history intent | Incoming-history intent | Proposed integrated outcome | Confidence | Verification | Decision needed |
|---|---|---|---|---|---|---|---|

Mark unsupported interpretations as `Unknown`. Present the map, recommend an order, then ask one question approving or correcting the first cluster's proposed outcome.

Complete this step only when every unmerged path belongs to a cluster, both intents have evidence, and the first cluster has an approved outcome.

## 4. Resolve one semantic cluster at a time

For each cluster:

1. Restate the approved outcome and identify the exact paths in scope.
2. Show the material interaction between the two intents. Ask one question if the merge contract does not already determine it.
3. Apply the smallest coherent edit. Preserve related validation and observability from both sides; remove markers only as a consequence of the integrated edit.
4. Inspect the resulting diff and run the narrowest useful parser, formatter check, type check, or focused test. Compare the result against both side-specific behaviors, not just the target branch.
5. Report what survived, what changed, validation evidence, and any changed assumption. Ask whether to stage the explicit paths; one staging question may cover a previously approved batch of independent mechanical clusters.
6. After approval, stage only named paths with `git add -- <paths>` and confirm that their unmerged index entries are gone.
7. Update the conflict map, then open the next decision gate.

Do not use `git add -A`, broad checkout/restore commands, or wholesale side selection. Leave a cluster unstaged when its behavior remains uncertain.

Complete this step only when every path is either resolved and explicitly staged or listed as blocked with one precise unanswered question.

## 5. Verify the integrated result

Check for remaining unmerged index entries and conflict markers in every touched text file. Run `git diff --check`, inspect the complete staged diff, and execute focused tests for each cluster followed by the broadest relevant suite affordable in the environment.

Verify cross-cluster seams: callers against APIs, migrations against schemas, fixtures against serializers, dependency manifests against lockfiles, generated artifacts against sources, and tests against the intended combined behavior. Investigate failures far enough to classify them as merge regressions, pre-existing failures, or environment blockers. Ask one decision question whenever that classification changes the approved outcome or validation standard.

Complete verification only when there are no unexplained markers or unmerged entries, every merge-contract behavior has evidence, material tests pass or have an explicit user-accepted exception, and unrelated work remains intact.

## 6. Obtain the final continuation decision

Present:

- the final merge contract and cluster decisions;
- resolved, staged, blocked, and unrelated paths;
- validation commands and outcomes;
- the resulting branch and operation state;
- the exact proposed continuation or commit command and its effects.

Ask one final question before `git merge --continue`, `git rebase --continue`, `git cherry-pick --continue`, `git revert --continue`, or a standalone commit. After approval, run only the applicable action, inspect final status and history, and report the resulting commit identity. Do not push.

If the user declines continuation, report the resolution as prepared with continuation pending. Declare the merge complete only when the approved Git operation reaches its expected terminal state and the final report accounts for every conflict, decision, validation result, and preserved unrelated change.
