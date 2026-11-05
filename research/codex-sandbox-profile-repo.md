# Research: Codex's sandbox and the Profile Repo

Ticket: [#29](https://github.com/TheMovingTargets/agent-skills/issues/29), part of map [#14](https://github.com/TheMovingTargets/agent-skills/issues/14). Terms (Profile Repo, Evidence, Harness) are from `GLOSSARY.md`.

Researched 2026-11-05 against OpenAI's Codex docs (developers.openai.com/codex, which now redirects to learn.chatgpt.com/docs) and the openai/codex source at `main` commit [`49f0c60`](https://github.com/openai/codex/tree/49f0c6022596c361fe676a5c4738fb2be34e3a93) (2026-11-05). The key code paths were also checked at the latest release tag, `rust-v0.166.0` (2026-10-29). The Codex CLI is not installed on this machine, so `codex --help` was not run and nothing was tried at runtime. No Codex config was read or changed.

Code links are permalinks to that commit.

## Answer

**By default, Codex can't write the Profile Repo, and it can't sync it.** In `workspace-write`, which is the default for version-controlled folders, the writable folders are the workspace, `/tmp` and `$TMPDIR`. `~/.local/share/...` is not writable, and network is off. `read-only` writes nothing. `danger-full-access` allows everything.

**Even an extra writable root doesn't make commits work.** Codex keeps `<writable_root>/.git` read-only. Since the clone *is* the root, `git commit` would fail.

**One-time fix:** add both the clone and its `.git` to `writable_roots`. In the source, an explicit rule overrides the default `.git` protection. Set `network_access = true` too if you want sync. The other option is to say yes to Codex's per-command escalation prompt (`require_escalated`): with `on-request`, it runs a command outside the sandbox after you approve it.

**Codex cloud:** doesn't apply. The agent runs in an OpenAI container with no access to `~/.local/share`, so it's local-only at best.

**IDE extension:** same sandbox and the same `~/.codex/config.toml` as the CLI.

**On failure:** detect `CODEX_SANDBOX` / `CODEX_SANDBOX_NETWORK_DISABLED` and catch EPERM/EACCES/EROFS. Ask for an escalated rerun once. If that's declined, spool the Evidence to `$TMPDIR` and merge it at the next writable session start. Print the config snippet and never fail the learning session.

## 1. Can a command write `~/.local/share/...`?

| Mode | Writes outside workspace? | Exactly what is writable | Source |
|---|---|---|---|
| `read-only` | No | Nothing. The whole disk is readable, so session start can still read the profile. | [`SandboxPolicy::ReadOnly`, `has_full_disk_read_access`](https://github.com/openai/codex/blob/49f0c6022596c361fe676a5c4738fb2be34e3a93/codex-rs/protocol/src/protocol.rs#L1250) |
| `workspace-write` | **No**, unless the path is listed in `writable_roots` | cwd, plus `/tmp` on Unix (unless `exclude_slash_tmp`), plus `$TMPDIR` (unless `exclude_tmpdir_env_var`), plus `sandbox_workspace_write.writable_roots`. Network is `false` by default. | [`get_writable_roots_with_cwd`](https://github.com/openai/codex/blob/49f0c6022596c361fe676a5c4738fb2be34e3a93/codex-rs/protocol/src/protocol.rs#L1425); [config reference](https://developers.openai.com/codex/config-reference) |
| `danger-full-access` | Yes | Everything, with network. "No sandbox; no approvals (not recommended)." | [`has_full_disk_write_access`](https://github.com/openai/codex/blob/49f0c6022596c361fe676a5c4738fb2be34e3a93/codex-rs/protocol/src/protocol.rs#L1391); [approvals & security](https://developers.openai.com/codex/agent-approvals-security) |
| Default mode | `workspace-write` with on-request approvals ("Auto") in version-controlled folders, `read-only` in other folders, and possibly `read-only` until the folder is trusted | | [approvals & security](https://developers.openai.com/codex/agent-approvals-security); [sandboxing](https://developers.openai.com/codex/sandboxing) |
| Approval policy `on-request` (default) | Only after you approve | "Codex asks for approval to edit files outside the workspace or to run commands that require network access." | [`AskForApproval` (default `OnRequest`)](https://github.com/openai/codex/blob/49f0c6022596c361fe676a5c4738fb2be34e3a93/codex-rs/protocol/src/protocol.rs#L1163); [approvals & security](https://developers.openai.com/codex/agent-approvals-security) |
| Approval policy `never` | No | Failures go back to the model and are never escalated to you. | [`AskForApproval::Never`](https://github.com/openai/codex/blob/49f0c6022596c361fe676a5c4738fb2be34e3a93/codex-rs/protocol/src/protocol.rs#L1163) |
| `granular` | Only if `sandbox_approval = true` | Prompt categories you set to `false` are auto-rejected. | [`GranularApprovalConfig`](https://github.com/openai/codex/blob/49f0c6022596c361fe676a5c4738fb2be34e3a93/codex-rs/protocol/src/protocol.rs#L1189) |
| `untrusted` | n/a | Retired as an approval policy. Setting it can stop Codex from starting. | [approvals & security](https://developers.openai.com/codex/agent-approvals-security); [config reference](https://developers.openai.com/codex/config-reference) |

**Paths in `writable_roots`:** a leading `~/` is expanded to `$HOME` ([`maybe_expand_home_directory`](https://github.com/openai/codex/blob/49f0c6022596c361fe676a5c4738fb2be34e3a93/codex-rs/utils/absolute-path/src/lib.rs#L28)). `${XDG_DATA_HOME}` is not expanded, so the skill must print the resolved absolute path.

**Newer config:** a permissions profile (`default_permissions` plus `[permissions.<name>.filesystem]` with `"/abs/path" = "write"`) does the same job. Don't combine it with `sandbox_mode` or `[sandbox_workspace_write]` ([config reference](https://developers.openai.com/codex/config-reference); [permissions](https://developers.openai.com/codex/permissions)).

**OS specifics:**

| OS | Enforcement | Source |
|---|---|---|
| macOS | Seatbelt (`sandbox-exec` with a generated profile). No setup needed. Child processes see `CODEX_SANDBOX=seatbelt`. | [sandboxing](https://developers.openai.com/codex/sandboxing); [`sandboxing/mod.rs`](https://github.com/openai/codex/blob/49f0c6022596c361fe676a5c4738fb2be34e3a93/codex-rs/core/src/sandboxing/mod.rs#L180); [`spawn.rs`](https://github.com/openai/codex/blob/49f0c6022596c361fe676a5c4738fb2be34e3a93/codex-rs/core/src/spawn.rs#L23) |
| Linux / WSL2 | bubblewrap (`bwrap` on PATH, or a bundled helper that needs unprivileged user namespaces) plus seccomp. Landlock is legacy: "The legacy Landlock option is rejected" for filesystem-restricted policies. WSL1 is unsupported. | [sandboxing](https://developers.openai.com/codex/sandboxing); [`linux-sandbox/README.md`](https://github.com/openai/codex/blob/49f0c6022596c361fe676a5c4738fb2be34e3a93/codex-rs/linux-sandbox/README.md) |
| Windows | Separate sandbox (MXC, with elevated/unelevated fallbacks). Out of scope here. | [approvals & security](https://developers.openai.com/codex/agent-approvals-security) |

## 2. Network and escalation

| Fact | Detail | Source |
|---|---|---|
| Off by default in `workspace-write` | `network_access: false` by default. Child processes get `CODEX_SANDBOX_NETWORK_DISABLED=1`. | [`SandboxPolicy::WorkspaceWrite`](https://github.com/openai/codex/blob/49f0c6022596c361fe676a5c4738fb2be34e3a93/codex-rs/protocol/src/protocol.rs#L1250); [`spawn.rs` L86-88](https://github.com/openai/codex/blob/49f0c6022596c361fe676a5c4738fb2be34e3a93/codex-rs/core/src/spawn.rs#L86) |
| Enable for every command | `[sandbox_workspace_write]` `network_access = true`. Or, in a permissions profile, `permissions.<name>.network.enabled = true`. Optional `features.network_proxy` adds domain rules. | [approvals & security](https://developers.openai.com/codex/agent-approvals-security); [permissions](https://developers.openai.com/codex/permissions) |
| Per-command escalation | The shell tool takes `sandbox_permissions: "require_escalated"` ("unsandboxed execution") plus a `justification` shown to you as the approval question. There is also `with_additional_permissions`, which stays sandboxed and widens permissions for that one command. | [`shell_spec.rs` L232-250](https://github.com/openai/codex/blob/49f0c6022596c361fe676a5c4738fb2be34e3a93/codex-rs/core/src/tools/handlers/shell_spec.rs#L232); [`SandboxPermissions`](https://github.com/openai/codex/blob/49f0c6022596c361fe676a5c4738fb2be34e3a93/codex-rs/protocol/src/models.rs#L66) |
| Approval choices | Approve once, approve for the session (`ApprovedForSession`), or approve with an execpolicy amendment so future matching commands are allowed (`ApprovedExecpolicyAmendment`). | [`ReviewDecision`](https://github.com/openai/codex/blob/49f0c6022596c361fe676a5c4738fb2be34e3a93/codex-rs/protocol/src/protocol.rs#L4468) |
| So can `git push` run? | Yes, under `on-request` or `granular` with `sandbox_approval = true`: one prompt per escalated command, or once per session. Not under `never`, and not in `read-only` without approval. | as above |

## 3. Is `.git` protected?

| Fact | Detail | Source |
|---|---|---|
| Yes, in every writable root | "`<writable_root>/.git` is protected as read-only whether it appears as a directory or file". If `.git` is a pointer file, the gitdir it points to is protected too. `.agents`, `.codex` and `.aws` are also read-only, and protection is recursive. The reason given is that these are paths "that could be modified to escalate the privileges of the agent (e.g. … notably `.git/hooks`)". | [approvals & security](https://developers.openai.com/codex/agent-approvals-security); [`default_read_only_subpaths_for_writable_root`](https://github.com/openai/codex/blob/49f0c6022596c361fe676a5c4738fb2be34e3a93/codex-rs/protocol/src/permissions.rs#L2355); [`WritableRoot` doc comment](https://github.com/openai/codex/blob/49f0c6022596c361fe676a5c4738fb2be34e3a93/codex-rs/protocol/src/protocol.rs#L1300) |
| Consequence | Listing only `~/.local/share/proficiency-profile` in `writable_roots` lets the skill append JSONL. **`git add`/`commit`/`pull` still fail**, because they write `.git/index`, `.git/objects` and `.git/refs`. | as above |
| Override | Protection is added only "if no explicit rule" covers that path (`append_default_read_only_path_if_no_explicit_rule`). An explicit write entry for `<root>/.git` therefore wins. This is tested for `.codex`/`.aws` ("explicit … rule should win over the default protected carveout"). The same code path covers `.git`, but no `.git`-specific test was found and it wasn't tried at runtime. The permissions docs agree: these paths stay read-only "unless you explicitly override those rules". | [`permissions.rs` L836-843, L2490](https://github.com/openai/codex/blob/49f0c6022596c361fe676a5c4738fb2be34e3a93/codex-rs/protocol/src/permissions.rs#L836); [`permissions_tests.rs` L768](https://github.com/openai/codex/blob/49f0c6022596c361fe676a5c4738fb2be34e3a93/codex-rs/protocol/src/permissions_tests.rs#L768); [permissions](https://developers.openai.com/codex/permissions) |
| Only the top level | Only `<root>/.git` is protected, not nested `<root>/sub/.git`. So a writable root at the *parent* of the clone would not protect the clone's `.git`. Don't rely on this: it is a side effect, not a documented guarantee. | [`default_read_only_subpaths_for_writable_root`](https://github.com/openai/codex/blob/49f0c6022596c361fe676a5c4738fb2be34e3a93/codex-rs/protocol/src/permissions.rs#L2355) |

## 4. Guidance for a Codex user

Least friction, in order. The skill prints this once, when it detects Codex and a blocked write.

**A. One-time config (recommended).** Add this to `~/.codex/config.toml`, using the real resolved path:

```toml
[sandbox_workspace_write]
writable_roots = [
  "~/.local/share/proficiency-profile",
  "~/.local/share/proficiency-profile/.git",   # needed for git commit
  "~/.local/share/trinity-helicopter-program", # Trinity's ledger
]
network_access = true   # optional: only if you want pull/push from inside Codex
```

- `network_access = true` opens network to *every* command in every session. A user who doesn't want that can leave it off. Commits still work, and only sync waits (see B).
- Users on `default_permissions` profiles add the same paths as `"write"` entries in their profile instead. Don't mix the two styles.
- Security note: making `.git` writable lets the agent write `.git/hooks` and `.git/config` in the clone. The skill should run git with `-c core.hooksPath=/dev/null` and must not trust that repo's config for credential helpers. Instead, pass `-c credential.helper=` and the `gh`/`glab` helper explicitly.

**B. No config: approve prompts.** Under `on-request`, the agent reruns the failing `profile.py` command with `require_escalated`. You approve once, or for the session. This works out of the box, but costs a prompt each session. It doesn't work under `never` or in a non-interactive `codex exec` with approvals off.

**C. `danger-full-access`:** works, but don't recommend it.

| Surface | Applies? | Source |
|---|---|---|
| Codex CLI | Yes, as above | |
| IDE extension | Yes. It uses the same local sandbox and shares the config layers with the CLI (`~/.codex/config.toml`). Permissions control sits under the composer. | [config basics](https://developers.openai.com/codex/config-basic); [sandboxing](https://developers.openai.com/codex/sandboxing) |
| Codex desktop app | Same sandbox kind. The docs don't say whether it reads the same `config.toml`. | [sandboxing](https://developers.openai.com/codex/sandboxing) |
| Codex cloud | No. Tasks run in OpenAI-managed containers, and agent-phase internet is off by default (per-environment allowlist). There is no `~/.local/share` of the developer's, and nothing persists to their machine. Treat it as "no Profile Repo". | [approvals & security](https://developers.openai.com/codex/agent-approvals-security); [cloud internet access](https://developers.openai.com/codex/cloud/internet-access) |

## 5. What the writer should do when the write fails

1. **Detect.**
   - Under Codex, `CODEX_SANDBOX` is set (macOS: `seatbelt`), and `CODEX_SANDBOX_NETWORK_DISABLED=1` means no network ([`spawn.rs`](https://github.com/openai/codex/blob/49f0c6022596c361fe676a5c4738fb2be34e3a93/codex-rs/core/src/spawn.rs#L21)).
   - Don't rely on those variables alone. Catch `OSError` with `errno` in {EPERM, EACCES, EROFS} on the first append or `mkdir`, and a non-zero `git commit` whose stderr mentions `.git/index.lock` or "Operation not permitted".
   - Skip network calls up front when `CODEX_SANDBOX_NETWORK_DISABLED=1`. That avoids a slow timeout and matches "skip quietly when offline".
2. **Keep the Evidence.**
   - Append to a spool file at `${TMPDIR:-/tmp}/proficiency-profile-spool/<session-id>.jsonl`. `$TMPDIR` and `/tmp` are writable by default, and macOS `$TMPDIR` is per-user.
   - At every session start where the clone is writable, fold any spool files into the clone, commit, then delete them.
   - Never spool into the workspace: it could get committed to the user's project.
   - Caveats: `$TMPDIR` is cleaned by the OS eventually, and a user can exclude both temp dirs. In that case, keep the Evidence in the session and print it as one compact JSONL block, which the agent can offer to save.
3. **Say what happened**, once per session, without failing the learning session. Exit 0 with a machine-readable status line, for example `PROFILE_WRITE_BLOCKED sandbox=codex spool=<path>`. The skill's instructions tell the agent to:
   - offer one escalated rerun (`require_escalated`, justification "write your proficiency profile outside the workspace"), then
   - show the `config.toml` snippet from section 4 so it doesn't happen again.
4. **Sync** stays opportunistic. If the commit succeeded but the network is off, record "unsynced" and push on a later run. The fallback from [profile-repo-hosting](https://github.com/TheMovingTargets/agent-skills/blob/research/profile-repo-hosting/research/profile-repo-hosting.md) already covers this.
5. **Trinity's ledger** (`skills/trinity-helicopter-program/scripts/ledger.py`) writes under the same base folder and has the same problem, minus `.git`. Its writes are plain appends, so one `writable_roots` entry is enough, and the same spool-and-merge pattern applies.

## Not confirmed from a primary source

- **Explicit `.git` write rule in practice.** That an explicit `writable_roots` entry for `<root>/.git` makes `git commit` work end to end is read from source logic and the `.codex`/`.aws` test. No `.git`-specific test exists, and nothing was run, because the CLI isn't installed locally.
- **`gh` credential helper under Seatbelt.** Whether `gh auth git-credential` can read the macOS keychain from inside Seatbelt with network enabled is not documented. If it can't, the push needs an escalated rerun.
- **Codex desktop app config.** Whether it shares `~/.codex/config.toml` with the CLI is not stated.
- **Default approval policy in the docs.** It isn't stated in the docs pages. `on-request` is the default in source (`#[default] OnRequest`).
