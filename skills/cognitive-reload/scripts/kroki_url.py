#!/usr/bin/env python3
"""Emit a diagram for chat: a native Mermaid fence, or a rendered image URL.

Render modes (``--render-mode``):

- ``fence``  : print a plain ```mermaid fenced block. Zero dependencies, no network.
- ``local``  : render a PNG through a self-hosted Kroki and serve it from a loopback cache.
- ``public`` : render through a public service (kroki.io). Requires an explicit opt-in because
               it sends the diagram source to a third party.
- ``auto``   : (default) network-free. Use a fence unless a local renderer is explicitly
               configured, in which case use ``local``. Never silently reaches the network.
"""

from __future__ import annotations

import argparse
import base64
import hashlib
import json
import os
import re
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request
import zlib
from pathlib import Path


ENCODED_PATH = re.compile(r"^[A-Za-z0-9_-]+$")
ASSET_PORT = int(os.environ.get("COGNITIVE_RELOAD_ASSET_PORT", "8991"))
# Explicit render-mode opt-in via the environment. Kept separate from any endpoint value so a
# custom --endpoint can never, by itself, imply consent to send source to a public service.
ENV_MODE = os.environ.get("COGNITIVE_RELOAD_RENDER_MODE", "").strip().lower()
PUBLIC_KROKI_URL = "https://kroki.io"

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


class LayoutError(RuntimeError):
    """Diagram violates the chat-layout policy and must be simplified, not retried or fenced over."""


def config_path() -> Path:
    root = Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config"))
    return root / "cognitive-reload" / "config.json"


def cache_dir() -> Path:
    root = Path(os.environ.get("XDG_CACHE_HOME", Path.home() / ".cache"))
    return root / "cognitive-reload" / "diagrams"


def config_data() -> dict:
    path = config_path()
    if path.exists():
        try:
            return json.loads(path.read_text())
        except (OSError, json.JSONDecodeError):
            return {}
    return {}


def local_configured(data: dict) -> bool:
    """Has a local renderer been explicitly set up? Used only to let `auto` pick `local`."""
    if data.get("render_mode") == "local" or data.get("local_render"):
        return True
    # Migration: pre-0.7 installs recorded a self-hosted renderer as diagram_mode=kroki_image.
    return data.get("diagram_mode") == "kroki_image"


def resolve_mode(cli_mode: str | None) -> str:
    if cli_mode and cli_mode != "auto":
        return cli_mode
    if ENV_MODE in {"fence", "public", "local"}:
        return ENV_MODE
    # auto: stay network-free. Reach `local` only when a renderer is explicitly configured.
    if local_configured(config_data()):
        return "local"
    return "fence"


def configured_endpoint() -> str:
    if value := os.environ.get("COGNITIVE_RELOAD_KROKI_URL"):
        return value.rstrip("/")
    data = config_data()
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
    encoded = base64.urlsafe_b64encode(compressed).decode("ascii").rstrip("=")
    if not ENCODED_PATH.fullmatch(encoded):
        raise RuntimeError("generated Kroki path contains non URL-safe Base64 characters")
    return encoded


def guard_mermaid_layout(source: str) -> str:
    """Reject oversized teaching diagrams and transpose crowded horizontal flows."""
    header = FLOWCHART_HEADER.search(source)
    if header:
        node_count = len(set(FLOWCHART_NODE.findall(source)))
        if node_count > 8:
            raise LayoutError(
                f"Mermaid flowchart has {node_count} nodes; split it into diagrams of at most 8 nodes"
            )
        if header.group(2).upper() in {"LR", "RL"} and node_count > 4:
            source = FLOWCHART_HEADER.sub(r"\1TD\3", source, count=1)

    participant_count = len(set(SEQUENCE_PARTICIPANT.findall(source)))
    if participant_count > 4:
        raise LayoutError(
            "Mermaid sequence diagram has more than 4 participants; split it by interaction"
        )
    return source


def guard(diagram_type: str, source: str) -> str:
    """Apply layout policy. Raises LayoutError on a violation that must be simplified."""
    if diagram_type == "mermaid":
        return guard_mermaid_layout(source)
    return source


def apply_theme(diagram_type: str, source: str) -> str:
    """Inject chat-safe connector/arrowhead colors for rendered images only."""
    if diagram_type == "mermaid" and not source.lstrip().startswith("%%{init:"):
        return f"{MERMAID_INIT}\n{source}"
    return source


def fence_block(diagram_type: str, source: str) -> str:
    """A plain ```mermaid block. No theme directive, so it does not fight the host UI theme."""
    if diagram_type != "mermaid":
        raise RuntimeError(
            f"fence render mode only supports Mermaid diagrams, not {diagram_type!r}; "
            "use --render-mode local or public for other diagram types"
        )
    return f"```mermaid\n{source.strip()}\n```"


def diagram_url(endpoint: str, diagram_type: str, output_format: str, source: str) -> str:
    return f"{endpoint}/{diagram_type}/{output_format}/{encode(source)}"


def fetch_image(url: str) -> tuple[bytes, str]:
    request = urllib.request.Request(url, headers={"User-Agent": "cognitive-reload/0.7"})
    try:
        with urllib.request.urlopen(request, timeout=15) as response:
            content_type = response.headers.get("Content-Type", "")
            if response.status != 200 or not content_type.startswith("image/"):
                raise RuntimeError(f"unexpected Kroki response: {response.status} {content_type}")
            return response.read(), content_type
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace").strip()
        if "Unable to decode the source" in body:
            raise RuntimeError(
                "Kroki rejected the encoded source. Regenerate with this helper and do not hand-build "
                "or edit the /mermaid/png/... URL."
            ) from exc
        raise RuntimeError(f"unexpected Kroki response: {exc.code} {body}") from exc


def check(url: str) -> None:
    data, _content_type = fetch_image(url)
    if not data:
        raise RuntimeError("Kroki returned an empty image")


def port_in_use(port: int) -> bool:
    with socket.socket() as sock:
        sock.settimeout(0.2)
        return sock.connect_ex(("127.0.0.1", port)) == 0


def server_serves_cache(port: int, marker: str) -> bool:
    url = f"http://127.0.0.1:{port}/.cognitive-reload-health"
    try:
        with urllib.request.urlopen(url, timeout=1) as response:
            return response.read().decode("utf-8", errors="replace").strip() == marker
    except (OSError, urllib.error.URLError):
        return False


def start_asset_server(directory: Path) -> str:
    directory.mkdir(parents=True, exist_ok=True)
    marker = "cognitive-reload-diagram-cache"
    (directory / ".cognitive-reload-health").write_text(marker + "\n")

    for port in range(ASSET_PORT, ASSET_PORT + 20):
        if server_serves_cache(port, marker):
            return f"http://127.0.0.1:{port}"
        if port_in_use(port):
            continue

        log_path = directory / "asset-server.log"
        with log_path.open("ab") as log:
            subprocess.Popen(
                [
                    sys.executable,
                    "-m",
                    "http.server",
                    str(port),
                    "--bind",
                    "127.0.0.1",
                    "--directory",
                    str(directory),
                ],
                stdout=log,
                stderr=log,
                start_new_session=True,
            )

        deadline = time.time() + 3
        while time.time() < deadline:
            if server_serves_cache(port, marker):
                return f"http://127.0.0.1:{port}"
            time.sleep(0.1)

    raise RuntimeError("could not start local diagram asset server")


def cached_image_url(source: str, output_format: str, kroki_url: str) -> str:
    if output_format != "png":
        raise RuntimeError("local diagram cache only supports PNG output")

    image, _content_type = fetch_image(kroki_url)
    digest = hashlib.sha256(source.encode("utf-8")).hexdigest()[:16]
    filename = f"{digest}.png"
    directory = cache_dir()
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / filename
    path.write_bytes(image)
    asset_endpoint = start_asset_server(directory)
    asset_url = f"{asset_endpoint}/{filename}"
    check(asset_url)
    return asset_url


def render_image(mode: str, args, guarded: str) -> str:
    """Build the Markdown image (or raw URL) for an image render mode. May raise on render failure."""
    themed = apply_theme(args.type, guarded)
    if mode == "public":
        endpoint = (args.endpoint or PUBLIC_KROKI_URL).rstrip("/")
    else:
        endpoint = (args.endpoint or configured_endpoint()).rstrip("/")
    kroki_url = diagram_url(endpoint, args.type, args.format, themed)
    if args.check:
        check(kroki_url)
    # Public mode emits the service URL directly; the loopback cache is for local renders only.
    if mode == "public" or args.direct_kroki_url or args.format != "png":
        url = kroki_url
    else:
        url = cached_image_url(themed, args.format, kroki_url)
    return f"![{args.alt}]({url})" if args.alt else url


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", nargs="?", help="diagram file; omit or use - for stdin")
    parser.add_argument("--type", default="mermaid")
    parser.add_argument("--format", choices=["png", "svg"], default="png")
    parser.add_argument(
        "--render-mode",
        choices=["fence", "public", "local", "auto"],
        default=None,
        help="fence (default, zero-dep), local (self-hosted Kroki), public (kroki.io, opt-in), auto",
    )
    parser.add_argument("--endpoint", help="override the renderer endpoint (does not imply public egress)")
    parser.add_argument("--alt", help="emit Markdown image syntax using this alt text (image modes)")
    parser.add_argument("--check", action="store_true", help="verify the rendered URL (image modes)")
    parser.add_argument(
        "--direct-kroki-url",
        action="store_true",
        help="emit the long encoded Kroki URL instead of a short cached local image URL",
    )
    args = parser.parse_args()

    # An explicitly selected image mode must fail loudly instead of silently degrading to a fence.
    forced = bool(args.render_mode and args.render_mode != "auto") or ENV_MODE in {
        "fence",
        "public",
        "local",
    }

    try:
        if args.source and args.source != "-":
            source = Path(args.source).read_text()
        else:
            source = sys.stdin.read()
        if not source.strip():
            raise RuntimeError("diagram source is empty")

        mode = resolve_mode(args.render_mode)
        # Layout policy is enforced in every mode and is never papered over by a fallback.
        guarded = guard(args.type, source)

        if mode == "fence":
            print(fence_block(args.type, guarded))
            return 0

        try:
            print(render_image(mode, args, guarded))
            return 0
        except LayoutError:
            raise
        except (OSError, RuntimeError, ValueError, urllib.error.URLError) as render_exc:
            if forced:
                raise
            # auto picked an image mode (a configured local renderer) but it is unreachable:
            # degrade to a usable Mermaid fence rather than failing the turn.
            print(fence_block(args.type, guarded))
            print(
                f"Diagram rendering unavailable ({render_exc}); emitted a Mermaid fence instead.",
                file=sys.stderr,
            )
            return 0
    except LayoutError as exc:
        print(f"Diagram layout rejected: {exc}", file=sys.stderr)
        return 2
    except (OSError, RuntimeError, ValueError, json.JSONDecodeError, urllib.error.URLError) as exc:
        print(f"Diagram rendering unavailable: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
