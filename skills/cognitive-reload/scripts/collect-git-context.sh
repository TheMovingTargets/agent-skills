#!/usr/bin/env bash
set -euo pipefail

# Read-only Git context collector for cognitive-reload.
# It writes JSON to stdout and does not modify the repository.

base="${1:-}"

json_escape() {
  python3 -c 'import json,sys; print(json.dumps(sys.stdin.read()))'
}

run_lines_json() {
  local cmd="$1"
  bash -lc "$cmd" 2>/dev/null | python3 -c 'import json,sys; print(json.dumps([line.rstrip("\n") for line in sys.stdin]))'
}

branch=$(git branch --show-current 2>/dev/null || true)
head=$(git rev-parse --short HEAD 2>/dev/null || true)
dirty=$(git status --short 2>/dev/null | wc -l | tr -d ' ')

printf '{\n'
printf '  "branch": %s,\n' "$(printf '%s' "$branch" | json_escape)"
printf '  "head": %s,\n' "$(printf '%s' "$head" | json_escape)"
printf '  "dirty_file_count": %s,\n' "${dirty:-0}"
printf '  "status_short": %s,\n' "$(run_lines_json 'git status --short')"
printf '  "recent_commits": %s,\n' "$(run_lines_json "git log --oneline --decorate --max-count=30")"
printf '  "commit_table": %s,\n' "$(run_lines_json "git log --format='%h%x09%an%x09%ad%x09%s' --date=short --max-count=50")"
if [[ -n "$base" ]]; then
  printf '  "base": %s,\n' "$(printf '%s' "$base" | json_escape)"
  printf '  "diff_stat": %s,\n' "$(run_lines_json "git diff --stat $base...HEAD")"
  printf '  "diff_files": %s\n' "$(run_lines_json "git diff --name-only $base...HEAD")"
else
  printf '  "base": null,\n'
  printf '  "diff_stat": %s,\n' "$(run_lines_json 'git diff --stat')"
  printf '  "diff_files": %s\n' "$(run_lines_json 'git diff --name-only')"
fi
printf '}\n'
