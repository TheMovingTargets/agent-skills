# Git-only context collection

Use read-only Git and filesystem inspection. Do not install dependencies or run mutations as part of this skill.

## Basic commands

```bash
git status --short
git branch --show-current
git remote show origin
git log --oneline --decorate --max-count=30
git log --format='%h%x09%an%x09%ad%x09%s' --date=short --max-count=50
```

## Diff commands

```bash
git diff --stat
git diff --name-only
git diff --stat <base>...HEAD
git diff --name-only <base>...HEAD
git log --oneline <base>..HEAD
```

## First-time structure commands

```bash
find . -maxdepth 3 -type f \
  -not -path './.git/*' \
  -not -path './node_modules/*' \
  -not -path './target/*' \
  -not -path './dist/*' \
  -not -path './build/*' | sort | head -300
```

Use language-specific clues only as evidence, not certainty:

- `Cargo.toml`, `src/`, `tests/` for Rust
- `package.json`, `src/`, `app/`, `pages/` for JS/TS
- `pyproject.toml`, `src/`, `tests/` for Python
- `go.mod`, `cmd/`, `pkg/`, `internal/` for Go

## Prior artifact search

```bash
find docs .agents .claude -path '*cognitive-reload*' -type f 2>/dev/null
find . -path '*/cognitive-reload/*' -type f 2>/dev/null
```

## Dirty state handling

If the working tree has uncommitted changes:

- report them
- do not reset or stash
- clarify whether they are in or out of scope
- if the user asked for main branch only, avoid including dirty feature work unless it affects evidence inspection

## Evidence standards

For every claim about an area, prefer at least one of:

- file path
- test path/name
- commit hash
- module/function/class name
- documented invariant
