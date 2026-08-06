# Conflict Resolution Playbook

Use this playbook to classify a conflict before editing it and to gather the evidence appropriate to that class.

## Contents

1. Name the histories precisely
2. Read the three-way state
3. Classify the conflict
4. Apply category-specific rules
5. Avoid seductive shortcuts
6. Verify preservation of intent

## 1. Name the histories precisely

Resolve and record the actual commit identities before interpreting a conflict:

- the common ancestor or per-commit parent used as the base;
- the commit currently checked out;
- the commit or replayed patch being integrated;
- the destination history the operation is building.

Use branch names only as friendly labels; retain object IDs because branch refs can move. During rebase, stage 2 and stage 3 often feel reversed to a user thinking in terms of the branch they started from. Describe each stage by its resolved commit and purpose, never by an unexplained “ours” or “theirs.”

Useful read-only evidence includes:

```text
git merge-base <left> <right>
git log --left-right --cherry-pick --oneline <left>...<right>
git diff <base>..<left> -- <path>
git diff <base>..<right> -- <path>
git log --follow -- <path>
git blame <commit> -- <path>
git diff --cc -- <path>
```

Choose revision ranges that match the active operation. Do not paste these commands mechanically when a rebase or cherry-pick has a different per-commit base.

## 2. Read the three-way state

For an unmerged path, Git may expose:

- stage 1: merge base;
- stage 2: current index side;
- stage 3: other index side.

Inspect available blobs with `git show :1:<path>`, `git show :2:<path>`, and `git show :3:<path>`. A missing stage can be expected for add/add, add/delete, or modify/delete cases; it is evidence, not an error to paper over.

Compare syntax trees, symbols, call sites, and tests when text lines conceal the real relationship. A clean textual union is not sufficient when both sides changed the same invariant, ordering rule, error contract, or data shape.

## 3. Classify the conflict

Assign every cluster one primary class and any relevant risk tags:

| Class | Typical shape | Required evidence before editing |
|---|---|---|
| Mechanical | Formatting, imports, adjacent independent edits | Both edits remain semantically independent after combination |
| Behavioral | Same function or rule changed differently | Expected inputs, outputs, errors, ordering, and tests for both intents |
| Structural | Rename, move, extraction, split, or consolidation | Symbol and path history plus all affected callers |
| Lifecycle | Modify/delete, rename/delete, or file replacement | Why the file disappeared and whether its responsibility moved |
| Contract | Public API, schema, serialization, config, protocol | Consumers, compatibility window, migrations, and rollback constraints |
| Dependency | Manifest, lockfile, toolchain, generated metadata | Direct dependency intent and the repository's canonical regeneration command |
| Generated | Source and derived output both changed | Authoritative source, generator version, deterministic output, and drift check |
| Validation | Test, fixture, snapshot, golden file | Which behavior each assertion protects; never weaken both to make a suite green |
| Opaque | Binary, encrypted file, vendored blob, submodule | Proven provenance, authoritative producer, exact desired identity, and validation path |

Risk-tag security boundaries, persistent data, migrations, concurrency, performance, compatibility, and externally published artifacts. Any risk tag opens a user decision gate unless the merge contract already answers it exactly.

## 4. Apply category-specific rules

### Mechanical conflicts

Combine only after proving the edits are independent. Re-run formatting or import organization through the repository's established tool after the semantic content is correct. A formatting tool may normalize a resolution; it may not choose one.

### Behavioral and contract conflicts

Write down both observable behaviors before proposing code. Prefer a composition that preserves both. When they are mutually exclusive, present the concrete inputs or consumers affected by each choice and ask the user one question with a recommendation.

For schemas, migrations, protocols, and serialized data, preserve deployed compatibility and historical ordering. Never renumber or rewrite an already-applied migration merely to remove a filename conflict. Ask which environments have observed it when repository evidence cannot prove that fact.

### Structural and lifecycle conflicts

Follow responsibilities, not paths. Determine whether a deletion is intentional, whether the code moved, and whether the other side edited the old location without seeing the move. Port the behavior into the surviving structure only after confirming it still belongs there. Ask before resurrecting a deleted responsibility or discarding a post-rename fix.

### Dependencies and generated files

Resolve authoritative human-edited sources first. Then use the repository's pinned package manager or generator to recreate derived artifacts. Ask before installing tools, accessing the network, changing an unrelated transitive graph, or accepting a generator-version change. Review regenerated diffs for unrelated churn and never hand-edit a lockfile unless the ecosystem explicitly requires it.

### Tests, fixtures, and snapshots

Treat each side's validation as intent evidence. Preserve assertions for both surviving behaviors. Regenerate snapshots or goldens only after the user approves the new observable output and the canonical producer is known. A deleted or loosened assertion requires the same decision gate as deleting the behavior it protected.

### Opaque conflicts

Do not synthesize binary content. Select or regenerate an artifact only from an authoritative source and after the user approves the identity. For submodules, inspect the referenced commits and containment relationship; do not choose the numerically newer object ID. If the content cannot be meaningfully inspected or reproduced, leave it blocked.

## 5. Avoid seductive shortcuts

Do not use these as decision mechanisms:

- blanket `checkout --ours`, `checkout --theirs`, `restore --ours`, or `restore --theirs`;
- automatic union merge for source, configuration, schemas, or tests;
- marker deletion followed only by parsing or compilation;
- `git add -A` or staging unrelated paths;
- lockfile or snapshot regeneration before resolving its source intent;
- deleting a test because both implementations cannot satisfy it;
- assuming the more recent timestamp, larger version, or destination branch is authoritative;
- enabling `rerere` or a custom merge driver during the operation without separate approval and review of the recorded resolution.

A whole-side selection can be an approved implementation after evidence proves that side already incorporates the other intent. It is never the evidence itself.

## 6. Verify preservation of intent

For each cluster, verify all applicable layers:

1. **Textual:** no unexplained markers, malformed output, or whitespace errors.
2. **Structural:** imports, references, generated files, path moves, and build graph remain coherent.
3. **Behavioral:** focused tests demonstrate every surviving behavior from both histories.
4. **Contractual:** public APIs, data formats, migrations, configuration, and compatibility promises remain valid.
5. **Historical:** the staged result implements the approved merge contract rather than merely resembling one side.
6. **Operational:** the index, active operation, unrelated changes, and proposed continuation command are exactly understood.

Preserve negative evidence. If a behavior cannot be tested, state why, identify the best available static or historical evidence, lower confidence, and ask whether that residual risk is acceptable before staging.
