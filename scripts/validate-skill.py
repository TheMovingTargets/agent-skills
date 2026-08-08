#!/usr/bin/env python3
from __future__ import annotations

import json
import re
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SKILLS = {
    "cognitive-reload": ROOT / "skills" / "cognitive-reload",
    "pdf-signature-emded": ROOT / "skills" / "pdf-signature-emded",
    "tmt-agent-deploy": ROOT / "skills" / "tmt-agent-deploy",
    "tmt-codex-plan-review": ROOT / "skills" / "tmt-codex-plan-review",
    "tmt-field-debug": ROOT / "skills" / "tmt-field-debug",
    "tmt-smart-merge": ROOT / "skills" / "tmt-smart-merge",
}


def frontmatter(path: Path) -> dict[str, str]:
    text = path.read_text(encoding="utf-8")
    if not text.startswith("---\n"):
        raise ValueError(f"{path}: missing YAML frontmatter")
    try:
        _, block, _ = text.split("---\n", 2)
    except ValueError as exc:
        raise ValueError(f"{path}: malformed YAML frontmatter") from exc
    fields: dict[str, str] = {}
    for line in block.splitlines():
        if ":" in line:
            key, value = line.split(":", 1)
            fields[key.strip()] = value.strip()
    return fields


def validate_skill(name: str, directory: Path) -> list[str]:
    errors: list[str] = []
    skill = directory / "SKILL.md"
    if not skill.exists():
        return [f"missing required file: {skill}"]
    try:
        fields = frontmatter(skill)
    except ValueError as exc:
        return [str(exc)]
    if fields.get("name") != name:
        errors.append(f"{skill}: expected name {name!r}, got {fields.get('name')!r}")
    if not fields.get("description"):
        errors.append(f"{skill}: missing description")
    if not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", name):
        errors.append(f"{skill}: invalid skill name {name!r}")
    if directory.name != name:
        errors.append(f"{directory}: directory must match skill name")
    return errors


def main() -> int:
    errors: list[str] = []
    for name, directory in SKILLS.items():
        errors.extend(validate_skill(name, directory))

    required = [
        ROOT / ".claude-plugin" / "plugin.json",
        ROOT / ".codex-plugin" / "plugin.json",
        ROOT / ".agents" / "plugins" / "marketplace.json",
        ROOT / "skills" / "cognitive-reload" / "scripts" / "progress_store.py",
        ROOT / "skills" / "cognitive-reload" / "scripts" / "export_hitl_cognition.py",
        ROOT / "skills" / "pdf-signature-emded" / "VERSION",
        ROOT / "skills" / "pdf-signature-emded" / "requirements.txt",
        ROOT / "skills" / "pdf-signature-emded" / "references" / "config-format.md",
        ROOT / "skills" / "pdf-signature-emded" / "scripts" / "pdf_signature_embed.py",
        ROOT / "skills" / "tmt-agent-deploy" / "VERSION",
        ROOT / "skills" / "tmt-agent-deploy" / "requirements.txt",
        ROOT / "skills" / "tmt-agent-deploy" / "schemas" / "config.schema.json",
        ROOT / "skills" / "tmt-agent-deploy" / "scripts" / "bootstrap.py",
        ROOT / "skills" / "tmt-agent-deploy" / "scripts" / "deploy_state.py",
        ROOT / "skills" / "tmt-field-debug" / "VERSION",
        ROOT / "skills" / "tmt-field-debug" / "references" / "report-contract.md",
        ROOT / "skills" / "tmt-smart-merge" / "VERSION",
        ROOT / "skills" / "tmt-smart-merge" / "references" / "conflict-playbook.md",
        ROOT / "scripts" / "test-tmt-agent-deploy.py",
    ]
    errors.extend(
        f"missing required file: {path}" for path in required if not path.exists()
    )

    try:
        package = json.loads((ROOT / "package.json").read_text(encoding="utf-8"))
        if package.get("name") != "tmt-agent-skills":
            errors.append("package.json: expected package name tmt-agent-skills")
    except (OSError, json.JSONDecodeError) as exc:
        errors.append(f"package.json: {exc}")

    try:
        marketplace = json.loads(
            (ROOT / ".agents" / "plugins" / "marketplace.json").read_text(
                encoding="utf-8"
            )
        )
        if marketplace.get("name") != "tmt-agent-skills":
            errors.append("marketplace.json: expected name tmt-agent-skills")
        plugin_names = [item.get("name") for item in marketplace.get("plugins", [])]
        if plugin_names != ["cognitive-reload"]:
            errors.append("marketplace.json: cognitive-reload plugin identity changed")
    except (OSError, json.JSONDecodeError) as exc:
        errors.append(f"marketplace.json: {exc}")

    try:
        codex = json.loads(
            (ROOT / ".codex-plugin" / "plugin.json").read_text(encoding="utf-8")
        )
        if codex.get("name") != "cognitive-reload":
            errors.append("Codex plugin identity changed")
        if codex.get("skills") != "./skills/cognitive-reload":
            errors.append("Codex plugin must expose only cognitive-reload")
    except (OSError, json.JSONDecodeError) as exc:
        errors.append(f"Codex plugin manifest: {exc}")

    if errors:
        for error in errors:
            print(error, file=sys.stderr)
        return 1
    print("tmt-agent-skills collection is structurally valid")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
