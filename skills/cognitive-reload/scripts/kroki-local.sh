#!/usr/bin/env sh
set -eu

script_dir=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
skill_dir=$(CDPATH= cd -- "$script_dir/.." && pwd)
compose_file="$skill_dir/assets/kroki-compose.yaml"
project_name=cognitive-reload-kroki

usage() {
  printf '%s\n' "Usage: $0 start [PORT] | stop | status | smoke"
}

compose() {
  if docker compose version >/dev/null 2>&1; then
    docker compose --project-name "$project_name" --file "$compose_file" "$@"
  elif command -v docker-compose >/dev/null 2>&1; then
    docker-compose --project-name "$project_name" --file "$compose_file" "$@"
  else
    printf '%s\n' "Docker Compose is required. Install and start Docker Desktop first." >&2
    exit 2
  fi
}

write_config() {
  port=$1
  config_root=${XDG_CONFIG_HOME:-"$HOME/.config"}
  config_dir="$config_root/cognitive-reload"
  config_file="$config_dir/config.json"
  mkdir -p "$config_dir"
  python3 - "$config_file" "$port" <<'PY'
import json
import os
import sys
from pathlib import Path

path = Path(sys.argv[1])
port = int(sys.argv[2])
data = json.loads(path.read_text()) if path.exists() else {}
# Signal that a local renderer is explicitly configured so `auto` render mode can select it.
data["render_mode"] = "local"
data["local_render"] = True
data.pop("diagram_mode", None)  # superseded by render_mode/local_render
data["kroki_port"] = port
data["kroki_url"] = f"http://127.0.0.1:{port}"
temporary = path.with_suffix(".tmp")
temporary.write_text(json.dumps(data, indent=2) + "\n")
os.replace(temporary, path)
PY
}

smoke_endpoint() {
  port=$1
  printf '%s\n' 'flowchart LR' '  A["Cognitive Reload"] --> B["Local Kroki"]' '  B --> C["Inline chat image"]' |
    python3 "$script_dir/kroki_url.py" --render-mode local --endpoint "http://127.0.0.1:$port" --alt "Kroki rendering test" --check
}

smoke() {
  printf '%s\n' 'flowchart LR' '  A["Cognitive Reload"] --> B["Local Kroki"]' '  B --> C["Inline chat image"]' |
    python3 "$script_dir/kroki_url.py" --render-mode local --alt "Kroki rendering test" --check
}

port_in_use() {
  python3 - "$1" <<'PY'
import socket
import sys

with socket.socket() as sock:
    sock.settimeout(0.5)
    sys.exit(0 if sock.connect_ex(("127.0.0.1", int(sys.argv[1]))) == 0 else 1)
PY
}

command=${1:-}
case "$command" in
  start)
    port=${2:-${COGNITIVE_RELOAD_KROKI_PORT:-8990}}
    case "$port" in
      ''|*[!0-9]*)
        printf 'Port must be numeric: %s\n' "$port" >&2
        exit 2
        ;;
    esac
    if [ "$port" -lt 1 ] || [ "$port" -gt 65535 ]; then
      printf 'Port must be between 1 and 65535: %s\n' "$port" >&2
      exit 2
    fi
    if port_in_use "$port"; then
      if smoke_endpoint "$port" >/dev/null 2>&1; then
        write_config "$port"
        printf 'An existing Kroki renderer is ready at http://127.0.0.1:%s\n' "$port"
        exit 0
      fi
      printf 'Port %s is already used by another service. Re-run install-local.sh with --kroki-port PORT, or run kroki-local.sh start PORT.\n' "$port" >&2
      exit 2
    fi
    KROKI_PORT=$port compose up --detach
    attempts=0
    until smoke_endpoint "$port" >/dev/null 2>&1; do
      attempts=$((attempts + 1))
      if [ "$attempts" -ge 30 ]; then
        printf '%s\n' "Kroki containers started, but the rendering smoke test timed out." >&2
        exit 1
      fi
      sleep 1
    done
    write_config "$port"
    printf 'Local Kroki is ready at http://127.0.0.1:%s\n' "$port"
    printf '%s\n' "Run '$0 smoke' and paste its Markdown into your agent UI to verify inline images."
    ;;
  stop)
    compose down
    ;;
  status)
    compose ps
    ;;
  smoke)
    smoke
    ;;
  *)
    usage >&2
    exit 2
    ;;
esac
