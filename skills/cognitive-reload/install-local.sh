#!/usr/bin/env sh
set -eu

usage() {
  printf '%s\n' "Usage: $0 <repository-path> [claude|codex|opencode|pi|all] [--native] [--with-kroki] [--kroki-port PORT]"
  printf '%s\n' ""
  printf '%s\n' "Harnesses map onto two install paths:"
  printf '%s\n' "  claude                    -> .claude/skills/cognitive-reload"
  printf '%s\n' "  codex | opencode | pi     -> .agents/skills/cognitive-reload (the shared, agent-agnostic path all three scan)"
  printf '%s\n' "  all (default)             -> both of the above"
  printf '%s\n' ""
  printf '%s\n' "  --native      also write the harness-specific dirs (.codex/skills, .opencode/skills, .pi/skills)"
  printf '%s\n' "                for users who disabled the shared .agents path"
  printf '%s\n' "  --with-kroki  start the optional local (private) PNG renderer; NOT required for diagrams,"
  printf '%s\n' "                which default to a native Mermaid fence"
}

if [ "$#" -lt 1 ]; then
  usage >&2
  exit 2
fi

repo=$1
shift
target=all
native=false
kroki=false
kroki_port=${COGNITIVE_RELOAD_KROKI_PORT:-8990}
source_dir=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)

if [ "$#" -gt 0 ]; then
  case "$1" in
    claude|codex|opencode|pi|all)
      target=$1
      shift
      ;;
  esac
fi

while [ "$#" -gt 0 ]; do
  case "$1" in
    --native)
      native=true
      shift
      ;;
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

# .claude/skills      -> Claude Code
# .agents/skills       -> shared path scanned by Codex, opencode, and Pi
case "$target" in
  claude)
    install_to ".claude/skills"
    ;;
  codex|opencode|pi)
    install_to ".agents/skills"
    ;;
  all)
    install_to ".claude/skills"
    install_to ".agents/skills"
    ;;
  *)
    usage >&2
    exit 2
    ;;
esac

if [ "$native" = true ]; then
  # Harness-specific locations for users who disabled the shared .agents path.
  case "$target" in
    codex|all)
      install_to ".codex/skills"
      ;;
  esac
  case "$target" in
    opencode|all)
      install_to ".opencode/skills"
      ;;
  esac
  case "$target" in
    pi|all)
      install_to ".pi/skills"
      ;;
  esac
fi

if [ "$kroki" = true ]; then
  "$source_dir/scripts/kroki-local.sh" start "$kroki_port"
fi
