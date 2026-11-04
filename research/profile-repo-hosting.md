# Research: creating and pushing a private Profile Repo on GitHub, GitLab and Azure DevOps

Ticket: [#17](https://github.com/TheMovingTargets/agent-skills/issues/17), part of map [#14](https://github.com/TheMovingTargets/agent-skills/issues/14). Terms (Profile Repo, Home Provider, Linked Identity) are from `GLOSSARY.md`.

Researched 2026-11-04 against official docs and the CLIs' own `--help` (gh 2.103, azure-devops extension 1.0.8). glab was not installed locally, so its behaviour comes from docs.gitlab.com only. Nothing was created; all checks were read-only.

## Answer

A skill can do this with the provider CLI the developer already uses, run from the harness's shell. The flow is the same on all three:

1. **Probe**: is the CLI installed, and is it signed in? (read-only status command, never print a token)
2. **Identify**: read the signed-in account from the provider's "current user" API. That account becomes the Home Provider's Linked Identity.
3. **Check**: does a repo with the chosen name already exist under that identity? If it does, reuse it, never overwrite.
4. **Ask once**: show the developer the exact target (host, owner or namespace, name, "private") and wait for approval, as the map requires.
5. **Create** with an explicit private flag (never rely on a default), then `git push` over HTTPS using the CLI as git's credential helper.
6. **Fall back**: if any step is missing (no CLI, not signed in, no network, no approval), keep the Proficiency Profile as a local git repo and record "not connected". Tell the developer the one command that would connect it. Retry on a later run; never block the learning session.

GitHub and GitLab fit this cleanly: each has a personal namespace, a `--private` flag, a current-user endpoint and a git credential helper. **Azure DevOps is the odd one out**: it has no personal namespace, so a repo has to live in an organization and project. Repos have no visibility of their own; they inherit the project's, and anyone who can read the project can read the repo. A skill can create the repo, but it must ask the developer which organization and project to use. It should warn that a shared project is not private to them, and that an employer's organization is out of scope for this map.

## Per provider

### GitHub (`gh`)

| Step | Command | Source |
|---|---|---|
| Signed in? | `gh auth status --hostname github.com --active` exits 1 if the account has auth problems. Add `--json hosts` for machine-readable output; with `--json` it always exits 0, so parse the result. | `gh auth status --help` |
| Identity | `gh api user --jq '{login, id}'`. `login` is the Linked Identity; `id` is stable across renames. | `gh api --help`; [REST: get the authenticated user](https://docs.github.com/en/rest/users/users#get-the-authenticated-user) |
| Exists? | `gh repo view <login>/<name> --json visibility` (non-zero if missing) | `gh repo view --help` |
| Create + push | `gh repo create <name> --private --source <dir> --remote origin --push`. If `OWNER/` is omitted, the owner is the authenticated user. | `gh repo create --help` |
| Push auth | `gh auth setup-git` sets gh as git's credential helper for authenticated hosts. Default git protocol is chosen at login. | `gh auth setup-git --help` |

- **Auth usually present:** the token is stored in the OS keyring by `gh auth login`. `GH_TOKEN` / `GITHUB_TOKEN` take precedence over stored credentials when set (`gh help environment`).
- **Scopes:** the default login scopes are `repo`, `read:org` and `gist`. Creating a private repo needs `repo` for OAuth and classic tokens ([REST docs](https://docs.github.com/en/rest/repos/repos#create-a-repository-for-the-authenticated-user)). So a normal `gh auth login` is enough. A fine-grained `GH_TOKEN` may not be, so treat a 403 as "not connected", not as a failure.
- **Default is public at the API level:** `private` defaults to `false` on `POST /user/repos`. Always pass `--private`.
- `GH_HOST` / `--hostname` cover GitHub Enterprise Server hosts. `GH_ENTERPRISE_TOKEN` is their token variable.

### GitLab (`glab`)

| Step | Command | Source |
|---|---|---|
| Signed in? | `glab auth status --hostname <host>` (or `--all`). `-F json` gives JSON. Exit code is **not documented**, so check the output too. | [glab auth status](https://docs.gitlab.com/cli/auth/status/) |
| Identity | `glab api user` → `id`, `username`, `name` (`GET /user`) | [Users API](https://docs.gitlab.com/api/users/) |
| Exists? | `glab repo view <username>/<name>` | glab docs |
| Create | `glab repo create <name> --private --skipGitInit`. Without `--group`, it goes in the user's own namespace. The host is the first configured host, or `GITLAB_HOST`. | [glab repo create](https://docs.gitlab.com/cli/repo/create/) |
| Push auth | `glab auth login --setup-git-credential-helper` makes glab git's credential helper and refreshes OAuth tokens. | [glab auth login](https://docs.gitlab.com/cli/auth/login/) |

- **Auth usually present:** OAuth (`--web`, or `--device` on 17.9+) or a PAT. The token is stored in the OS keyring, or in plaintext in `~/.config/glab-cli/config.yml` if no keyring is available. `GITLAB_TOKEN`, `GITLAB_ACCESS_TOKEN` and `OAUTH_TOKEN` override stored credentials.
- **Scopes:** `api` gives full API access and also git read/write over HTTP for personal tokens. `write_repository` alone allows push but is not documented as allowing project creation. `read_user` covers `GET /user` ([token scopes](https://docs.gitlab.com/security/tokens/access_token_scopes/)).
- **Default visibility is the instance default** when no flag is given, so always pass `--private`.
- **Gotcha:** with `--readme`, `glab repo create` clones the new project locally. Use `--skipGitInit` when the local Profile Repo already exists, then add the remote and push.
- Self-managed instances work the same way through `--hostname` / `GITLAB_HOST`.

### Azure DevOps (`az repos`, `azure-devops` extension)

| Step | Command | Source |
|---|---|---|
| Signed in? | `az account show` fails if there is no `az login`. `az devops` also accepts a stored PAT (`az devops login`) or `AZURE_DEVOPS_EXT_PAT`. Guest users can only use `az devops login`. | [Sign in with a PAT](https://learn.microsoft.com/azure/devops/cli/log-in-via-pat) |
| Identity | `GET https://app.vssps.visualstudio.com/_apis/profile/profiles/me?api-version=7.1` returns `id`, `displayName`, `emailAddress`. Use a bearer token from `az account get-access-token --resource 499b84ac-1321-427f-aa17-267ca6975798`. | [Profiles - Get](https://learn.microsoft.com/rest/api/azure/devops/profile/profiles/get); [Entra tokens with Azure CLI](https://learn.microsoft.com/azure/devops/cli/entra-tokens) |
| Where? | `az devops configure --list` shows the default organization and project, if any. `az devops project list --org <url>` lists projects. | `az devops configure --help`; [az devops project](https://learn.microsoft.com/cli/azure/devops/project) |
| Exists? | `az repos show --repository <name> --org <url> --project <p>` | `az repos --help` |
| Create | `az repos create --name <name> --org <url> --project <p>`. There is **no visibility flag**. | `az repos create --help` |
| Push auth | Git Credential Manager over HTTPS. Microsoft recommends `git config --global credential.azreposCredentialType oauth` (Entra tokens). SSH also works. | [Credential managers](https://learn.microsoft.com/azure/devops/repos/git/set-up-credential-managers) |

- **No personal namespace.** Every repo lives in `organization/project`, and visibility is a project setting. **Public projects are retired**: new ones cannot be created and existing ones convert to private in 2027 ([make project private](https://learn.microsoft.com/azure/devops/organizations/projects/make-project-public)). `az devops project create --visibility` defaults to `private` ([az devops project](https://learn.microsoft.com/cli/azure/devops/project)). So "private" really means "visible to that project's members".
- **Implication:** a Profile Repo is private to the developer only in a project they alone belong to. In practice that means a personal organization they own, with a dedicated project. Creating a project or organization goes beyond "create a repo", so the skill should ask for an existing organization and project, offer `az devops project create --visibility private` only with explicit approval, and never pick the configured default organization silently. That default is often an employer's, and employer-hosted profiles are out of scope for #14.
- **Auth guidance:** Microsoft recommends Entra tokens over PATs, and organizations increasingly restrict PAT creation ([Entra auth](https://learn.microsoft.com/azure/devops/integrate/get-started/authentication/entra)). Entra tokens from `az account get-access-token` last about one hour, so fetch one per run and never store it.

## When no CLI is signed in

| Situation | Detect | Behaviour |
|---|---|---|
| CLI not installed | `command -v gh` / `glab` / `az` | Local-only profile. Mention the install and sign-in command once. |
| Installed, not signed in | Status command fails, or no account in its JSON | Local-only. Suggest `gh auth login`, `glab auth login` or `az login`. **The skill must not run login itself**: login is interactive and opens a browser or asks for a token, which is the developer's job. |
| Signed in, insufficient scope (403 on create) | Create call fails with 401/403 | Local-only. Suggest `gh auth refresh -s repo`, or a PAT with `api` scope. |
| Signed in to several accounts or hosts | More than one entry in `gh auth status --json hosts` / `glab auth status --all` | Ask which one is the Home Provider. Record the others as Linked Identities (from their current-user API) without creating anything. |
| Network blocked by the harness sandbox | Connection or TLS error | Local-only, retry next run (see below). |

**Safe fallback = local-first.** Always create the Profile Repo as a local git repo in a per-user location outside any working repository, and commit there. "Connecting" it later only adds a remote and pushes. Nothing is lost while it is disconnected, the sync logic is identical in both states, and pushing later uploads the full history. Store connection state (provider, host, owner or namespace, repo name, Linked Identities) in the profile's own config, never a token.

## Harness notes

- **Claude Code:** Bash runs as the user, so keyring-stored CLI credentials work. Its optional sandbox is **off by default**. When it is on, network goes through an allow-list proxy that starts empty, and Go CLIs such as `gh` "may fail TLS verification" on macOS unless excluded via `excludedCommands` ([sandboxing](https://code.claude.com/docs/en/sandboxing)). Treat sandbox failures as "not connected".
- **Codex CLI:** the default `workspace-write` sandbox has **network disabled** unless `sandbox_workspace_write.network_access = true` is set ([agent approvals & security](https://developers.openai.com/codex/agent-approvals-security)). The local-first fallback is therefore the normal path in Codex, and the push happens when the developer allows network or runs one command themselves.

## Open points for the spec

- Exact exit-code behaviour of `glab auth status` is undocumented. Verify it on a real install before relying on it.
- Whether GitHub fine-grained tokens can create user-owned private repos is not stated on the REST page. Handle it as a 403 fallback.
- Azure DevOps: decide whether the spec supports it as a Home Provider at all, or only as a Linked Identity, given there is no personal namespace.
