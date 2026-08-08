#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any


ANCHORS = {"top-left", "top-right", "bottom-left", "bottom-right", "center"}
ROTATIONS = {0, 90, 180, 270}


class ConfigError(Exception):
    pass


def load_fitz():
    try:
        import fitz  # type: ignore
    except ImportError as exc:
        raise SystemExit(
            "PyMuPDF is required. Install it with: python3 -m pip install pymupdf"
        ) from exc
    return fitz


def read_json(path: Path) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ConfigError(f"{path}: invalid JSON: {exc}") from exc
    if not isinstance(data, dict):
        raise ConfigError(f"{path}: config root must be an object")
    return data


def resolve_path(config_path: Path, value: str) -> Path:
    path = Path(value).expanduser()
    if path.is_absolute():
        return path
    return (config_path.parent / path).resolve()


def require_string(obj: dict[str, Any], key: str, context: str) -> str:
    value = obj.get(key)
    if not isinstance(value, str) or not value:
        raise ConfigError(f"{context}: {key} must be a non-empty string")
    return value


def require_number(obj: dict[str, Any], key: str, context: str) -> float:
    value = obj.get(key)
    if not isinstance(value, (int, float)):
        raise ConfigError(f"{context}: {key} must be a number")
    return float(value)


@dataclass(frozen=True)
class DocumentSpec:
    id: str
    path: Path
    output: Path


@dataclass(frozen=True)
class SignatureSpec:
    id: str
    path: Path


@dataclass(frozen=True)
class PlacementSpec:
    document: str
    signature: str
    page: int
    anchor: str
    x: float
    y: float
    width: float
    height: float | None
    rotation: int
    label: str | None


@dataclass(frozen=True)
class SignatureConfig:
    documents: dict[str, DocumentSpec]
    signatures: dict[str, SignatureSpec]
    placements: list[PlacementSpec]


def parse_config(config_path: Path, check_files: bool = True) -> SignatureConfig:
    data = read_json(config_path)
    if data.get("version") != 1:
        raise ConfigError("version must be 1")

    documents_raw = data.get("documents")
    signatures_raw = data.get("signatures")
    placements_raw = data.get("placements")
    if not isinstance(documents_raw, list) or not documents_raw:
        raise ConfigError("documents must be a non-empty array")
    if not isinstance(signatures_raw, list) or not signatures_raw:
        raise ConfigError("signatures must be a non-empty array")
    if not isinstance(placements_raw, list) or not placements_raw:
        raise ConfigError("placements must be a non-empty array")

    documents: dict[str, DocumentSpec] = {}
    for index, item in enumerate(documents_raw):
        context = f"documents[{index}]"
        if not isinstance(item, dict):
            raise ConfigError(f"{context}: must be an object")
        doc_id = require_string(item, "id", context)
        if doc_id in documents:
            raise ConfigError(f"{context}: duplicate document id {doc_id!r}")
        path = resolve_path(config_path, require_string(item, "path", context))
        output = resolve_path(config_path, require_string(item, "output", context))
        if check_files and not path.exists():
            raise ConfigError(f"{context}: PDF not found: {path}")
        documents[doc_id] = DocumentSpec(doc_id, path, output)

    signatures: dict[str, SignatureSpec] = {}
    for index, item in enumerate(signatures_raw):
        context = f"signatures[{index}]"
        if not isinstance(item, dict):
            raise ConfigError(f"{context}: must be an object")
        sig_id = require_string(item, "id", context)
        if sig_id in signatures:
            raise ConfigError(f"{context}: duplicate signature id {sig_id!r}")
        path = resolve_path(config_path, require_string(item, "path", context))
        if check_files and not path.exists():
            raise ConfigError(f"{context}: signature image not found: {path}")
        signatures[sig_id] = SignatureSpec(sig_id, path)

    placements: list[PlacementSpec] = []
    for index, item in enumerate(placements_raw):
        context = f"placements[{index}]"
        if not isinstance(item, dict):
            raise ConfigError(f"{context}: must be an object")
        document = require_string(item, "document", context)
        signature = require_string(item, "signature", context)
        if document not in documents:
            raise ConfigError(f"{context}: unknown document id {document!r}")
        if signature not in signatures:
            raise ConfigError(f"{context}: unknown signature id {signature!r}")
        page = item.get("page")
        if not isinstance(page, int) or page < 1:
            raise ConfigError(f"{context}: page must be a 1-based integer")
        anchor = item.get("anchor", "bottom-left")
        if anchor not in ANCHORS:
            raise ConfigError(f"{context}: anchor must be one of {sorted(ANCHORS)}")
        x = require_number(item, "x", context)
        y = require_number(item, "y", context)
        width = require_number(item, "width", context)
        if width <= 0:
            raise ConfigError(f"{context}: width must be positive")
        height_value = item.get("height")
        height = None
        if height_value is not None:
            if not isinstance(height_value, (int, float)) or height_value <= 0:
                raise ConfigError(f"{context}: height must be a positive number")
            height = float(height_value)
        rotation = item.get("rotation", 0)
        if rotation not in ROTATIONS:
            raise ConfigError(f"{context}: rotation must be one of {sorted(ROTATIONS)}")
        label = item.get("label")
        if label is not None and not isinstance(label, str):
            raise ConfigError(f"{context}: label must be a string")
        placements.append(
            PlacementSpec(
                document=document,
                signature=signature,
                page=page,
                anchor=anchor,
                x=x,
                y=y,
                width=width,
                height=height,
                rotation=int(rotation),
                label=label,
            )
        )

    return SignatureConfig(documents, signatures, placements)


def image_size(fitz: Any, image_path: Path) -> tuple[float, float]:
    pixmap = fitz.Pixmap(str(image_path))
    try:
        return float(pixmap.width), float(pixmap.height)
    finally:
        pixmap = None


def placement_rect(
    fitz: Any,
    page_height: float,
    image_width: float,
    image_height: float,
    placement: PlacementSpec,
) -> Any:
    width = placement.width
    height = placement.height or (width * image_height / image_width)

    x = placement.x
    y = placement.y
    if placement.anchor == "bottom-left":
        left, bottom = x, y
    elif placement.anchor == "bottom-right":
        left, bottom = x - width, y
    elif placement.anchor == "top-left":
        left, bottom = x, y - height
    elif placement.anchor == "top-right":
        left, bottom = x - width, y - height
    else:
        left, bottom = x - width / 2, y - height / 2

    top = page_height - bottom - height
    return fitz.Rect(left, top, left + width, top + height)


def validate_with_pdf_metadata(config_path: Path) -> SignatureConfig:
    fitz = load_fitz()
    config = parse_config(config_path)
    opened: dict[str, Any] = {}
    try:
        for doc_id, document in config.documents.items():
            opened[doc_id] = fitz.open(str(document.path))
        for index, placement in enumerate(config.placements):
            doc = opened[placement.document]
            if placement.page > doc.page_count:
                raise ConfigError(
                    f"placements[{index}]: page {placement.page} exceeds "
                    f"{placement.document!r} page count {doc.page_count}"
                )
            image_w, image_h = image_size(
                fitz, config.signatures[placement.signature].path
            )
            page = doc[placement.page - 1]
            rect = placement_rect(fitz, page.rect.height, image_w, image_h, placement)
            if rect.width <= 0 or rect.height <= 0:
                raise ConfigError(f"placements[{index}]: computed rectangle is empty")
            if not page.rect.intersects(rect):
                raise ConfigError(
                    f"placements[{index}]: computed rectangle is outside the page"
                )
    finally:
        for doc in opened.values():
            doc.close()
    return config


def command_init_config(args: argparse.Namespace) -> int:
    pdfs = [Path(value) for value in args.pdf]
    signatures = [Path(value) for value in args.signature]
    output_path = Path(args.output)
    base = output_path.parent.resolve()

    def portable(path: Path) -> str:
        resolved = path.expanduser().resolve()
        try:
            return str(resolved.relative_to(base))
        except ValueError:
            return str(resolved)

    documents = []
    for index, pdf in enumerate(pdfs, start=1):
        stem = pdf.stem or f"document-{index}"
        documents.append(
            {
                "id": stem if len(pdfs) == 1 else f"{stem}-{index}",
                "path": portable(pdf),
                "output": f"signed/{pdf.stem or f'document-{index}'}-signed.pdf",
            }
        )
    sig_items = []
    for index, signature in enumerate(signatures, start=1):
        stem = signature.stem or f"signature-{index}"
        sig_items.append(
            {
                "id": stem if len(signatures) == 1 else f"{stem}-{index}",
                "path": portable(signature),
            }
        )

    config = {
        "version": 1,
        "documents": documents,
        "signatures": sig_items,
        "placements": [
            {
                "document": documents[0]["id"],
                "signature": sig_items[0]["id"],
                "page": 1,
                "anchor": "bottom-left",
                "x": 72,
                "y": 72,
                "width": 144,
                "label": "replace with interviewed placement",
            }
        ],
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(config, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {output_path}")
    return 0


def command_validate(args: argparse.Namespace) -> int:
    config = validate_with_pdf_metadata(Path(args.config))
    print(
        f"Config valid: {len(config.documents)} document(s), "
        f"{len(config.signatures)} signature image(s), "
        f"{len(config.placements)} placement(s)"
    )
    return 0


def command_apply(args: argparse.Namespace) -> int:
    fitz = load_fitz()
    config_path = Path(args.config).expanduser().resolve()
    config = validate_with_pdf_metadata(config_path)
    placements_by_doc: dict[str, list[PlacementSpec]] = {}
    for placement in config.placements:
        placements_by_doc.setdefault(placement.document, []).append(placement)

    for doc_id, placements in placements_by_doc.items():
        document = config.documents[doc_id]
        output = document.output
        output.parent.mkdir(parents=True, exist_ok=True)
        pdf = fitz.open(str(document.path))
        try:
            for placement in placements:
                page = pdf[placement.page - 1]
                signature = config.signatures[placement.signature]
                image_w, image_h = image_size(fitz, signature.path)
                rect = placement_rect(
                    fitz, page.rect.height, image_w, image_h, placement
                )
                page.insert_image(
                    rect,
                    filename=str(signature.path),
                    overlay=True,
                    rotate=placement.rotation,
                )
            pdf.save(str(output), garbage=4, deflate=True)
            print(f"Wrote {output}")
        finally:
            pdf.close()
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Create, validate, and apply visible PDF signature placements."
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    init_config = subparsers.add_parser("init-config")
    init_config.add_argument("--pdf", action="append", required=True)
    init_config.add_argument("--signature", action="append", required=True)
    init_config.add_argument("--output", required=True)
    init_config.set_defaults(func=command_init_config)

    validate = subparsers.add_parser("validate")
    validate.add_argument("--config", required=True)
    validate.set_defaults(func=command_validate)

    apply = subparsers.add_parser("apply")
    apply.add_argument("--config", required=True)
    apply.set_defaults(func=command_apply)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return args.func(args)
    except ConfigError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
