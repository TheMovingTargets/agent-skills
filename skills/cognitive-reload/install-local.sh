#!/usr/bin/env sh
set -eu

usage() {
  printf '%s\n' "Usage: $0 <repository-path> [claude|codex|opencode|pi|all] [--native] [--with-kroki] [--kroki-port PORT] [--uninstall]"
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
  printf '%s\n' "  --uninstall   remove the skill from the same target/--native paths instead of installing;"
  printf '%s\n' "                repos then fall back to any user-level install (~/.claude, ~/.agents)."
  printf '%s\n' "                Leaves ~/.config/cognitive-reload and any running renderer untouched"
  printf '%s\n' "                (stop that separately with scripts/kroki-local.sh stop)"
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
uninstall=false
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
    --uninstall)
      uninstall=true
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

if [ "$uninstall" = true ] && [ "$kroki" = true ]; then
  printf '%s\n' "--uninstall cannot be combined with --with-kroki." >&2
  printf '%s\n' "Stop the renderer separately with scripts/kroki-local.sh stop." >&2
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

uninstall_from() {
  parent=$1
  destination="$repo/$parent/cognitive-reload"
  # Safety: never delete the source checkout this installer is being run from.
  # Compare physically resolved paths so a symlinked destination cannot alias the source.
  destination_real=$(CDPATH= cd -- "$destination" 2>/dev/null && pwd -P || true)
  source_real=$(CDPATH= cd -- "$source_dir" && pwd -P)
  if [ -n "$destination_real" ] && [ "$destination_real" = "$source_real" ]; then
    printf 'Refusing to remove the running source directory: %s\n' "$destination"
    return
  fi
  if [ ! -d "$destination" ]; then
    printf 'Not installed in %s\n' "$destination"
    return
  fi
  rm -rf "$destination"
  printf 'Removed cognitive-reload from %s\n' "$destination"
  # Best-effort tidy: drop the skills dir and its harness dotdir only while they are empty.
  rmdir "$repo/$parent" 2>/dev/null || true
  case "$parent" in
    */skills)
      rmdir "$repo/${parent%/skills}" 2>/dev/null || true
      ;;
  esac
}

# One entry point for both directions so install and uninstall always touch the same paths.
apply_to() {
  if [ "$uninstall" = true ]; then
    uninstall_from "$1"
  else
    install_to "$1"
  fi
}

# .claude/skills      -> Claude Code
# .agents/skills       -> shared path scanned by Codex, opencode, and Pi
case "$target" in
  claude)
    apply_to ".claude/skills"
    ;;
  codex|opencode|pi)
    apply_to ".agents/skills"
    ;;
  all)
    apply_to ".claude/skills"
    apply_to ".agents/skills"
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
      apply_to ".codex/skills"
      ;;
  esac
  case "$target" in
    opencode|all)
      apply_to ".opencode/skills"
      ;;
  esac
  case "$target" in
    pi|all)
      apply_to ".pi/skills"
      ;;
  esac
fi

if [ "$kroki" = true ]; then
  "$source_dir/scripts/kroki-local.sh" start "$kroki_port"
fi
