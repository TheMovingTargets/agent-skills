#!/usr/bin/env sh
set -eu

usage() {
  printf '%s\n' "Usage: $0 <repository-path> [codex|claude|both] [--with-kroki] [--kroki-port PORT]"
}

if [ "$#" -lt 1 ]; then
  usage >&2
  exit 2
fi

repo=$1
shift
target=both
kroki=false
kroki_port=${COGNITIVE_RELOAD_KROKI_PORT:-8990}
source_dir=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)

if [ "$#" -gt 0 ]; then
  case "$1" in
    codex|claude|both)
      target=$1
      shift
      ;;
  esac
fi

while [ "$#" -gt 0 ]; do
  case "$1" in
    --with-kroki)
      kroki=true
      shift
      ;;
    --kroki-port)
      if [ "$#" -lt 2 ]; then
        usage >&2
        exit 2
      fi
      kroki_port=$2
      shift 2
      ;;
    *)
      usage >&2
      exit 2
      ;;
  esac
done

case "$kroki_port" in
  ''|*[!0-9]*)
    printf 'Kroki port must be numeric: %s\n' "$kroki_port" >&2
    exit 2
    ;;
esac
if [ "$kroki_port" -lt 1 ] || [ "$kroki_port" -gt 65535 ]; then
  printf 'Kroki port must be between 1 and 65535: %s\n' "$kroki_port" >&2
  exit 2
fi

if [ ! -d "$repo" ]; then
  printf 'Repository directory does not exist: %s\n' "$repo" >&2
  exit 2
fi

install_to() {
  parent=$1
  destination="$repo/$parent/cognitive-reload"
  destination_parent=$(CDPATH= cd -- "$(dirname -- "$destination")" 2>/dev/null && pwd || true)
  if [ -n "$destination_parent" ] && [ "$destination_parent/$(basename -- "$destination")" = "$source_dir" ]; then
    printf 'Already installed in %s\n' "$destination"
    return
  fi
  mkdir -p "$destination"
  cp -R "$source_dir/." "$destination/"
  printf 'Installed cognitive-reload in %s\n' "$destination"
}

case "$target" in
  codex)
    install_to ".agents/skills"
    ;;
  claude)
    install_to ".claude/skills"
    ;;
  both)
    install_to ".agents/skills"
    install_to ".claude/skills"
    ;;
  *)
    usage >&2
    exit 2
    ;;
esac

if [ "$kroki" = true ]; then
  "$source_dir/scripts/kroki-local.sh" start "$kroki_port"
fi
