#!/usr/bin/env python3
"""Create a local Kroki image URL or Markdown image from diagram source."""

from __future__ import annotations

import argparse
import base64
import json
import os
import re
import sys
import urllib.error
import urllib.request
import zlib
from pathlib import Path


MERMAID_INIT = (
    '%%{init: {"theme":"base","themeVariables":{'
    '"background":"#ffffff","primaryColor":"#f8fafc",'
    '"primaryTextColor":"#111827","primaryBorderColor":"#6366f1",'
    '"lineColor":"#64748b","secondaryColor":"#f1f5f9",'
    '"tertiaryColor":"#ffffff","edgeLabelBackground":"#ffffff"},'
    '"themeCSS":".flowchart-link{stroke:#64748b!important;stroke-width:2px!important}'
    '.marker{fill:#64748b!important;stroke:#64748b!important}"}}%%'
)

FLOWCHART_HEADER = re.compile(r"(?m)^(\s*flowchart\s+)(LR|RL|TD|TB|BT)(\b)", re.I)
FLOWCHART_NODE = re.compile(
    r"(?<![\w-])([A-Za-z_][\w-]*)\s*(?=(?:\[\[|\[\(|\[|\(\(|\(|\{\{|\{))"
)
SEQUENCE_PARTICIPANT = re.compile(
    r"(?im)^\s*(?:participant|actor)\s+([A-Za-z_][\w-]*)\b"
)


def config_path() -> Path:
    root = Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config"))
    return root / "cognitive-reload" / "config.json"


def configured_endpoint() -> str:
    if value := os.environ.get("COGNITIVE_RELOAD_KROKI_URL"):
        return value.rstrip("/")
    path = config_path()
    if path.exists():
        data = json.loads(path.read_text())
        if value := data.get("kroki_url"):
            return str(value).rstrip("/")
        if value := data.get("kroki_port"):
            return f"http://127.0.0.1:{int(value)}"
    port = int(os.environ.get("COGNITIVE_RELOAD_KROKI_PORT", "8990"))
    return f"http://127.0.0.1:{port}"


def encode(source: str) -> str:
    compressed = zlib.compress(source.encode("utf-8"), 9)
    # Kroki accepts URL-safe Base64 in the path segment. Padding is not needed
    # and can be mangled by chat clients, proxies, or markdown image renderers.
    return base64.urlsafe_b64encode(compressed).decode("ascii").rstrip("=")


def guard_mermaid_layout(source: str) -> str:
    """Reject oversized teaching diagrams and transpose crowded horizontal flows."""
    header = FLOWCHART_HEADER.search(source)
    if header:
        node_count = len(set(FLOWCHART_NODE.findall(source)))
        if node_count > 8:
            raise RuntimeError(
                f"Mermaid flowchart has {node_count} nodes; split it into diagrams of at most 8 nodes"
            )
        if header.group(2).upper() in {"LR", "RL"} and node_count > 4:
            source = FLOWCHART_HEADER.sub(r"\1TD\3", source, count=1)

    participant_count = len(set(SEQUENCE_PARTICIPANT.findall(source)))
    if participant_count > 4:
        raise RuntimeError(
            "Mermaid sequence diagram has more than 4 participants; split it by interaction"
        )
    return source


def prepare_source(diagram_type: str, source: str) -> str:
    """Apply layout guards and chat-safe colors to Mermaid source."""
    if diagram_type == "mermaid":
        source = guard_mermaid_layout(source)
    if diagram_type == "mermaid" and not source.lstrip().startswith("%%{init:"):
        return f"{MERMAID_INIT}\n{source}"
    return source


def diagram_url(endpoint: str, diagram_type: str, output_format: str, source: str) -> str:
    return f"{endpoint}/{diagram_type}/{output_format}/{encode(source)}"


def check(url: str) -> None:
    request = urllib.request.Request(url, headers={"User-Agent": "cognitive-reload/0.5"})
    with urllib.request.urlopen(request, timeout=15) as response:
        content_type = response.headers.get("Content-Type", "")
        if response.status != 200 or not content_type.startswith("image/"):
            raise RuntimeError(f"unexpected Kroki response: {response.status} {content_type}")
        response.read(32)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("source", nargs="?", help="diagram file; omit or use - for stdin")
    parser.add_argument("--type", default="mermaid")
    parser.add_argument("--format", choices=["png", "svg"], default="png")
    parser.add_argument("--endpoint")
    parser.add_argument("--alt", help="emit Markdown image syntax using this alt text")
    parser.add_argument("--check", action="store_true", help="verify the rendered URL")
    args = parser.parse_args()

    try:
        if args.source and args.source != "-":
            source = Path(args.source).read_text()
        else:
            source = sys.stdin.read()
        if not source.strip():
            raise RuntimeError("diagram source is empty")
        source = prepare_source(args.type, source)
        endpoint = (args.endpoint or configured_endpoint()).rstrip("/")
        url = diagram_url(endpoint, args.type, args.format, source)
        if args.check:
            check(url)
        print(f"![{args.alt}]({url})" if args.alt else url)
        return 0
    except (OSError, RuntimeError, ValueError, json.JSONDecodeError, urllib.error.URLError) as exc:
        print(f"Kroki rendering unavailable: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
