#!/usr/bin/env python3
from __future__ import annotations

import json
import re
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SKILLS = {
    "cognitive-reload": ROOT / "skills" / "cognitive-reload",
    "cognitive-reload-with-trinity": ROOT / "skills" / "cognitive-reload-with-trinity",
    "doc-pdf-signature-embed": ROOT / "skills" / "doc-pdf-signature-embed",
    "proficiency-profile": ROOT / "skills" / "proficiency-profile",
    "tmt-agent-deploy": ROOT / "skills" / "tmt-agent-deploy",
    "tmt-codex-code-review": ROOT / "skills" / "tmt-codex-code-review",
    "tmt-codex-plan-review": ROOT / "skills" / "tmt-codex-plan-review",
    "tmt-field-debug": ROOT / "skills" / "tmt-field-debug",
    "tmt-smart-merge": ROOT / "skills" / "tmt-smart-merge",
    "trinity-helicopter-program": ROOT / "skills" / "trinity-helicopter-program",
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
        ROOT / ".claude-plugin" / "marketplace.json",
        ROOT / ".codex-plugin" / "plugin.json",
        ROOT / ".agents" / "plugins" / "marketplace.json",
        ROOT / "skills" / "cognitive-reload" / "scripts" / "progress_store.py",
        ROOT / "skills" / "cognitive-reload" / "scripts" / "export_hitl_cognition.py",
        ROOT / "skills" / "doc-pdf-signature-embed" / "VERSION",
        ROOT / "skills" / "doc-pdf-signature-embed" / "requirements.txt",
        ROOT / "skills" / "doc-pdf-signature-embed" / "references" / "config-format.md",
        ROOT / "skills" / "doc-pdf-signature-embed" / "scripts" / "pdf_signature_embed.py",
        ROOT / "skills" / "tmt-agent-deploy" / "VERSION",
        ROOT / "skills" / "tmt-agent-deploy" / "requirements.txt",
        ROOT / "skills" / "tmt-agent-deploy" / "schemas" / "config.schema.json",
        ROOT / "skills" / "tmt-agent-deploy" / "scripts" / "bootstrap.py",
        ROOT / "skills" / "tmt-agent-deploy" / "scripts" / "deploy_state.py",
        ROOT / "skills" / "tmt-codex-code-review" / "VERSION",
        ROOT / "skills" / "tmt-codex-code-review" / "references" / "packet-template.md",
        ROOT / "skills" / "tmt-codex-plan-review" / "VERSION",
        ROOT / "skills" / "tmt-codex-plan-review" / "references" / "packet-template.md",
        ROOT / "skills" / "tmt-field-debug" / "VERSION",
        ROOT / "skills" / "tmt-field-debug" / "references" / "report-contract.md",
        ROOT / "skills" / "tmt-smart-merge" / "VERSION",
        ROOT / "skills" / "tmt-smart-merge" / "references" / "conflict-playbook.md",
        ROOT / "skills" / "cognitive-reload-with-trinity" / "VERSION",
        ROOT / "skills" / "trinity-helicopter-program" / "VERSION",
        ROOT / "skills" / "trinity-helicopter-program" / "scripts" / "ledger.py",
        ROOT / "skills" / "trinity-helicopter-program" / "references" / "languages" / "csharp-dotnet.md",
        ROOT / "scripts" / "test-tmt-agent-deploy.py",
        ROOT / "skills" / "cognitive-reload" / "references" / "architecture-concepts.md",
        ROOT / "skills" / "proficiency-profile" / "references" / "areas.md",
        ROOT / "skills" / "proficiency-profile" / "references" / "harnesses.md",
        ROOT / "skills" / "proficiency-profile" / "scripts" / "vocabularies.py",
        ROOT / "skills" / "proficiency-profile" / "scripts" / "profile.py",
        ROOT / "skills" / "proficiency-profile" / "VERSION",
    ]
    errors.extend(
        f"missing required file: {path}" for path in required if not path.exists()
    )

    version = None
    try:
        package = json.loads((ROOT / "package.json").read_text(encoding="utf-8"))
        if package.get("name") != "tmt-agent-skills":
            errors.append("package.json: expected package name tmt-agent-skills")
        version = package.get("version")
    except (OSError, json.JSONDecodeError) as exc:
        errors.append(f"package.json: {exc}")

    for marketplace_path in (
        ROOT / ".agents" / "plugins" / "marketplace.json",
        ROOT / ".claude-plugin" / "marketplace.json",
    ):
        label = marketplace_path.relative_to(ROOT)
        try:
            marketplace = json.loads(marketplace_path.read_text(encoding="utf-8"))
            if marketplace.get("name") != "tmt":
                errors.append(f"{label}: expected marketplace name tmt")
            plugin_names = [
                item.get("name") for item in marketplace.get("plugins", [])
            ]
            if plugin_names != ["tmt-agent-skills"]:
                errors.append(f"{label}: expected one plugin, tmt-agent-skills")
        except (OSError, json.JSONDecodeError) as exc:
            errors.append(f"{label}: {exc}")

    # Installed plugins only update when the plugin version changes, so both
    # manifests must carry the package.json version on every release.
    try:
        claude = json.loads(
            (ROOT / ".claude-plugin" / "plugin.json").read_text(encoding="utf-8")
        )
        if claude.get("name") != "tmt-agent-skills":
            errors.append("Claude plugin identity changed")
        if claude.get("version") != version:
            errors.append(
                f"Claude plugin version {claude.get('version')} does not match "
                f"package.json version {version}"
            )
        expected_skills = sorted(f"./skills/{name}" for name in SKILLS)
        if sorted(claude.get("skills", [])) != expected_skills:
            errors.append("Claude plugin must list every skill in skills/")
    except (OSError, json.JSONDecodeError) as exc:
        errors.append(f"Claude plugin manifest: {exc}")

    try:
        codex = json.loads(
            (ROOT / ".codex-plugin" / "plugin.json").read_text(encoding="utf-8")
        )
        if codex.get("name") != "tmt-agent-skills":
            errors.append("Codex plugin identity changed")
        if codex.get("version") != version:
            errors.append(
                f"Codex plugin version {codex.get('version')} does not match "
                f"package.json version {version}"
            )
        if codex.get("skills") != "./skills":
            errors.append("Codex plugin must expose every skill in ./skills")
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
