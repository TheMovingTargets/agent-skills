#!/usr/bin/env python3
"""Validate deployment configuration and maintain non-secret local state."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml
from jsonschema import Draft202012Validator


SKILL_ROOT = Path(__file__).resolve().parents[1]
SCHEMA_PATH = SKILL_ROOT / "schemas" / "config.schema.json"
VERSION = (SKILL_ROOT / "VERSION").read_text(encoding="utf-8").strip()
LOCAL_DIR = ".tmt-agent-deploy"
SECRET_KEY = re.compile(
    r"(?:^|_)(?:secret|password|passwd|token|private_key|api_key|credential)(?:$|_)",
    re.IGNORECASE,
)
ALLOWED_REFERENCE_KEYS = {
    "credential_refs",
    "external_log_reference",
    "recovery_references",
    "reference",
}
SECRET_CONTENT = re.compile(
    r"-----BEGIN [A-Z ]*PRIVATE KEY-----|(?:^|\s)(?:gh[pousr]_|AKIA)[A-Za-z0-9_-]{12,}",
    re.MULTILINE,
)
SSH_UNSAFE_REMOTE_ARG = re.compile(r"[\s;|&()<>$`*?{}\[\]!\\]")


class StateError(RuntimeError):
    pass


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def local_paths(repo: Path) -> tuple[Path, Path, Path]:
    root = repo.resolve() / LOCAL_DIR
    return root, root / "state", root / "runs"


def load_yaml(path: Path) -> Any:
    try:
        with path.open(encoding="utf-8") as handle:
            return yaml.safe_load(handle)
    except (OSError, yaml.YAMLError) as exc:
        raise StateError(f"cannot read {path}: {exc}") from exc


def atomic_yaml(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    temporary = Path(temporary_name)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            yaml.safe_dump(payload, handle, sort_keys=False)
            handle.flush()
            os.fsync(handle.fileno())
        if os.name != "nt":
            temporary.chmod(0o600)
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def secret_violations(value: Any, location: str = "$") -> list[str]:
    violations: list[str] = []
    if isinstance(value, dict):
        for key, child in value.items():
            child_location = f"{location}.{key}"
            if (
                isinstance(key, str)
                and key not in ALLOWED_REFERENCE_KEYS
                and SECRET_KEY.search(key)
            ):
                violations.append(f"{child_location}: secret-like field name is prohibited")
            violations.extend(secret_violations(child, child_location))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            violations.extend(secret_violations(child, f"{location}[{index}]"))
    elif isinstance(value, str) and SECRET_CONTENT.search(value):
        violations.append(f"{location}: secret-like content is prohibited")
    return violations


def ssh_remote_argument_violations(value: Any, location: str = "$") -> list[str]:
    violations: list[str] = []
    if isinstance(value, dict):
        argv = value.get("argv")
        if (
            value.get("type") == "repository"
            and isinstance(argv, list)
            and argv
            and Path(argv[0]).name == "ssh"
        ):
            host_index = next(
                (
                    index
                    for index, argument in enumerate(argv[1:], start=1)
                    if isinstance(argument, str) and "@" in argument
                ),
                None,
            )
            if host_index is not None:
                for index, argument in enumerate(
                    argv[host_index + 1 :], start=host_index + 1
                ):
                    if isinstance(argument, str) and SSH_UNSAFE_REMOTE_ARG.search(
                        argument
                    ):
                        violations.append(
                            f"{location}.argv[{index}]: SSH remote arguments must "
                            "be shell-safe tokens; use a tracked remote helper instead"
                        )
        for key, child in value.items():
            violations.extend(
                ssh_remote_argument_violations(child, f"{location}.{key}")
            )
    elif isinstance(value, list):
        for index, child in enumerate(value):
            violations.extend(
                ssh_remote_argument_violations(child, f"{location}[{index}]")
            )
    return violations


def leaf_validation_errors(error: Any) -> list[Any]:
    if not error.context:
        return [error]
    leaves: list[Any] = []
    for child in error.context:
        leaves.extend(leaf_validation_errors(child))
    return leaves


def validate_config(repo: Path) -> dict[str, Any]:
    root, _, _ = local_paths(repo)
    config_path = root / "config.yaml"
    config = load_yaml(config_path)
    if not isinstance(config, dict):
        raise StateError("config.yaml must contain a mapping")

    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    validator = Draft202012Validator(schema)
    errors = []
    for error in validator.iter_errors(config):
        errors.extend(leaf_validation_errors(error))
    errors.sort(key=lambda error: (list(error.absolute_path), error.message))
    messages = list(
        dict.fromkeys(
            f"{'.'.join(str(part) for part in error.absolute_path) or '$'}: {error.message}"
            for error in errors
        )
    )
    messages.extend(secret_violations(config))
    messages.extend(ssh_remote_argument_violations(config))
    if config.get("validated_by", {}).get("version") != VERSION:
        messages.append(
            f"validated_by.version must equal installed skill version {VERSION!r}"
        )
    if messages:
        raise StateError("configuration invalid:\n- " + "\n- ".join(messages))
    return config


def validate_local_state(repo: Path) -> dict[str, Any]:
    config = validate_config(repo)
    root, state, runs = local_paths(repo)
    memory = state / "MEMORY.md"
    if not memory.is_file():
        raise StateError(f"deployment memory missing: {memory}")

    violations: list[str] = []
    candidates = [memory]
    candidates.extend(
        path
        for directory in [state, runs]
        if directory.exists()
        for path in directory.iterdir()
        if path.is_file() and path.suffix.lower() in {".yaml", ".yml", ".json", ".md"}
    )
    for path in dict.fromkeys(candidates):
        text = path.read_text(encoding="utf-8")
        if SECRET_CONTENT.search(text):
            violations.append(f"{path}: secret-like content is prohibited")
        if path.suffix.lower() in {".yaml", ".yml", ".json"}:
            payload = load_yaml(path)
            violations.extend(
                f"{path}:{message}" for message in secret_violations(payload)
            )
    if violations:
        raise StateError("local state invalid:\n- " + "\n- ".join(violations))
    return config


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def artifact_snapshot(repo: Path, config: dict[str, Any]) -> dict[str, Any]:
    repository_root = repo.resolve()
    artifacts = []
    for item in config["artifacts"]:
        relative = Path(item["path"])
        if relative.is_absolute() or ".." in relative.parts:
            raise StateError(f"artifact path must stay within repository: {relative}")
        path = repository_root / relative
        if not path.is_file():
            raise StateError(f"artifact does not exist: {relative}")
        try:
            path.resolve().relative_to(repository_root)
        except ValueError as exc:
            raise StateError(f"artifact resolves outside repository: {relative}") from exc
        artifacts.append(
            {
                "path": relative.as_posix(),
                "role": item["role"],
                "behavioral": item["behavioral"],
                "sha256": sha256(path),
            }
        )
    return {"generated_at": utc_now(), "artifacts": artifacts}


def snapshot(repo: Path) -> dict[str, Any]:
    config = validate_local_state(repo)
    payload = artifact_snapshot(repo, config)
    _, state, _ = local_paths(repo)
    atomic_yaml(state / "artifacts.yaml", payload)
    return payload


def drift(repo: Path) -> dict[str, Any]:
    config = validate_local_state(repo)
    _, state, _ = local_paths(repo)
    stored_path = state / "artifacts.yaml"
    if not stored_path.exists():
        raise StateError("artifact snapshot missing; run snapshot after approved setup")
    stored = load_yaml(stored_path) or {}
    old = {item["path"]: item for item in stored.get("artifacts", [])}
    current = artifact_snapshot(repo, config)
    new = {item["path"]: item for item in current["artifacts"]}
    changes = []
    for path in sorted(set(old) | set(new)):
        before = old.get(path)
        after = new.get(path)
        if before != after:
            changes.append(
                {
                    "path": path,
                    "status": "added" if before is None else "removed" if after is None else "changed",
                    "behavioral": bool((after or before).get("behavioral")),
                    "before_sha256": before.get("sha256") if before else None,
                    "after_sha256": after.get("sha256") if after else None,
                }
            )
    return {
        "drift": changes,
        "material_review_required": any(change["behavioral"] for change in changes),
    }


def current_run_path(repo: Path) -> Path:
    _, state, _ = local_paths(repo)
    return state / "current-run.yaml"


def start_run(
    repo: Path, environment: str, target: str, source: str, policy: str
) -> dict[str, Any]:
    config = validate_local_state(repo)
    if environment not in config["environments"]:
        raise StateError(f"unknown environment: {environment}")
    if target not in config["environments"][environment]["targets"]:
        raise StateError(f"unknown target {target!r} in environment {environment!r}")
    if policy != config["confirmation_policy"]:
        raise StateError("run policy does not match configuration")
    path = current_run_path(repo)
    if path.exists():
        raise StateError("unfinished deployment exists; recover it before starting another")
    snapshot_path = repo.resolve() / LOCAL_DIR / "state" / "artifacts.yaml"
    if not snapshot_path.is_file():
        raise StateError("artifact snapshot missing; run snapshot after approved setup")
    now = datetime.now(timezone.utc)
    run_id = f"{now.strftime('%Y%m%dT%H%M%SZ')}-{environment}-{hashlib.sha256(source.encode()).hexdigest()[:7]}"
    payload = {
        "deployment_id": run_id,
        "started_at": now.isoformat().replace("+00:00", "Z"),
        "updated_at": now.isoformat().replace("+00:00", "Z"),
        "environment": environment,
        "target": target,
        "source": source,
        "confirmation_policy": policy,
        "configuration_sha256": sha256(repo.resolve() / LOCAL_DIR / "config.yaml"),
        "artifact_snapshot_sha256": sha256(snapshot_path),
        "status": "started",
        "target_mutation_started": False,
        "changed_components": [],
        "steps": [],
    }
    atomic_yaml(path, payload)
    return payload


def checkpoint(
    repo: Path,
    step: str,
    status: str,
    mutates_target: bool,
    component: str | None,
    external_log_reference: str | None,
) -> dict[str, Any]:
    allowed_statuses = {
        "running",
        "succeeded",
        "retryable-failure",
        "failed",
        "cancelled",
    }
    if status not in allowed_statuses:
        raise StateError(
            f"invalid checkpoint status {status!r}; expected one of "
            + ", ".join(sorted(allowed_statuses))
        )
    path = current_run_path(repo)
    if not path.exists():
        raise StateError("no active deployment")
    payload = load_yaml(path)
    previous = next(
        (
            event
            for event in reversed(payload.get("steps", []))
            if event.get("step") == step
        ),
        None,
    )
    if previous is None and status != "running":
        raise StateError(f"step {step!r} must checkpoint running before {status}")
    if previous is not None:
        previous_status = previous.get("status")
        if previous_status in {
            "succeeded",
            "retryable-failure",
            "failed",
            "cancelled",
        }:
            raise StateError(
                f"step {step!r} is already terminal with status {previous_status!r}"
            )
        if previous_status == "running" and status == "running":
            raise StateError(f"step {step!r} is already running")
    event = {
        "at": utc_now(),
        "step": step,
        "status": status,
        "mutates_target": mutates_target,
    }
    if component:
        event["component"] = component
    if external_log_reference:
        event["external_log_reference"] = external_log_reference
    payload["steps"].append(event)
    payload["updated_at"] = utc_now()
    if status == "failed":
        payload["failure_recorded"] = True
    if status == "cancelled":
        payload["cancellation_recorded"] = True
    if payload.get("failure_recorded"):
        payload["status"] = "failed"
    elif payload.get("cancellation_recorded"):
        payload["status"] = "cancelled"
    elif status == "retryable-failure":
        payload["status"] = "retrying"
    else:
        payload["status"] = status
    if mutates_target and status in {
        "running",
        "succeeded",
        "retryable-failure",
        "failed",
        "cancelled",
    }:
        payload["target_mutation_started"] = True
    if component and mutates_target and status == "succeeded":
        if component not in payload["changed_components"]:
            payload["changed_components"].append(component)
    atomic_yaml(path, payload)
    return payload


def resolve_repository_entrypoint(
    config: dict[str, Any],
    environment: str,
    target: str,
    entrypoint_path: str,
) -> tuple[dict[str, Any], str | None]:
    try:
        target_config: Any = config["environments"][environment]["targets"][target]
    except KeyError as exc:
        raise StateError(
            f"unknown target {target!r} in environment {environment!r}"
        ) from exc

    value = target_config
    parts = entrypoint_path.split(".")
    if not parts or any(not part for part in parts):
        raise StateError("entrypoint path must be a non-empty dotted path")
    try:
        for part in parts:
            value = value[int(part)] if isinstance(value, list) else value[part]
    except (KeyError, IndexError, TypeError, ValueError) as exc:
        raise StateError(f"entrypoint path does not resolve: {entrypoint_path}") from exc

    if not isinstance(value, dict) or value.get("type") != "repository":
        raise StateError(
            f"entrypoint path must resolve to a repository entrypoint: {entrypoint_path}"
        )

    component = None
    if len(parts) >= 2 and parts[0] == "components":
        try:
            component = target_config["components"][int(parts[1])]["name"]
        except (KeyError, IndexError, TypeError, ValueError) as exc:
            raise StateError(
                f"cannot resolve component for entrypoint: {entrypoint_path}"
            ) from exc
    return value, component


def run_repository_entrypoint(
    repo: Path,
    environment: str,
    target: str,
    entrypoint_path: str,
    attempt: int = 1,
    retryable: bool = False,
) -> int:
    if attempt < 1:
        raise StateError("entrypoint attempt must be at least 1")
    config = validate_local_state(repo)
    run_path = current_run_path(repo)
    if not run_path.exists():
        raise StateError("no active deployment")
    run = load_yaml(run_path)
    if run.get("environment") != environment or run.get("target") != target:
        raise StateError("active deployment scope does not match requested entrypoint")
    config_path = repo.resolve() / LOCAL_DIR / "config.yaml"
    if run.get("configuration_sha256") != sha256(config_path):
        raise StateError("configuration changed after the deployment started")

    recovery_path = any(
        segment in {"diagnostics", "rollback", "rollback_verify"}
        for segment in entrypoint_path.split(".")
    )
    if run.get("failure_recorded") and not recovery_path:
        raise StateError("deployment has failed; only diagnostics or rollback may run")

    entrypoint, component = resolve_repository_entrypoint(
        config, environment, target, entrypoint_path
    )
    if retryable and (entrypoint["mutates_target"] or not entrypoint["idempotent"]):
        raise StateError(
            "only non-mutating idempotent entrypoints may use retryable failure"
        )
    step = entrypoint["name"]
    if attempt > 1:
        step = f"{step} [attempt {attempt}]"
    mutates_target = entrypoint["mutates_target"]
    checkpoint(repo, step, "running", mutates_target, component, None)

    cwd = Path(entrypoint["cwd"])
    if not cwd.is_absolute():
        cwd = repo.resolve() / cwd
    try:
        completed = subprocess.run(
            entrypoint["argv"],
            cwd=cwd,
            timeout=entrypoint["timeout_seconds"],
            check=False,
        )
        returncode = completed.returncode
    except subprocess.TimeoutExpired:
        print(
            f"entrypoint timed out after {entrypoint['timeout_seconds']} seconds: {step}",
            file=sys.stderr,
        )
        returncode = 124
    except OSError as exc:
        print(f"entrypoint could not execute: {step}: {exc}", file=sys.stderr)
        returncode = 126

    terminal_status = (
        "succeeded"
        if returncode == 0
        else "retryable-failure"
        if retryable
        else "failed"
    )
    checkpoint(
        repo,
        step,
        terminal_status,
        mutates_target,
        component,
        entrypoint.get("external_log_reference"),
    )
    return returncode


def finish_run(repo: Path, outcome: str, summary: Path) -> Path:
    path = current_run_path(repo)
    if not path.exists():
        raise StateError("no active deployment")
    payload = load_yaml(path)
    root, _, runs = local_paths(repo)
    summary = summary if summary.is_absolute() else repo.resolve() / summary
    if not summary.is_file():
        raise StateError(f"summary does not exist: {summary}")
    try:
        relative_summary = summary.resolve().relative_to(runs.resolve())
    except ValueError as exc:
        raise StateError(f"summary must be inside {runs}") from exc
    if summary.suffix.lower() != ".md":
        raise StateError("summary must be Markdown")
    payload["outcome"] = outcome
    payload["finished_at"] = utc_now()
    payload["summary"] = relative_summary.as_posix()
    path.unlink()
    if os.name != "nt":
        summary.chmod(0o600)
    return root / "runs" / relative_summary


def prune_runs(repo: Path, keep: int = 50) -> list[Path]:
    _, _, runs = local_paths(repo)
    if not runs.exists():
        return []
    summaries = sorted(
        (path for path in runs.glob("*.md") if path.is_file()),
        key=lambda path: path.name,
        reverse=True,
    )
    removed = summaries[keep:]
    for path in removed:
        path.unlink()
    return removed


def status(repo: Path) -> dict[str, Any]:
    path = current_run_path(repo)
    return {"active": path.exists(), "run": load_yaml(path) if path.exists() else None}


def print_json(value: Any) -> None:
    print(json.dumps(value, indent=2, sort_keys=True))


def main() -> int:
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="command", required=True)
    for command in ["validate", "snapshot", "drift", "status", "prune-runs"]:
        child = subparsers.add_parser(command)
        child.add_argument("--repo", default=".")

    start = subparsers.add_parser("start-run")
    start.add_argument("--repo", default=".")
    start.add_argument("--environment", required=True)
    start.add_argument("--target", required=True)
    start.add_argument("--source", required=True)
    start.add_argument("--policy", required=True)

    mark = subparsers.add_parser("checkpoint")
    mark.add_argument("--repo", default=".")
    mark.add_argument("--step", required=True)
    mark.add_argument("--status", required=True)
    mark.add_argument("--mutates-target", action="store_true")
    mark.add_argument("--component")
    mark.add_argument("--external-log-reference")

    execute = subparsers.add_parser("run-entrypoint")
    execute.add_argument("--repo", default=".")
    execute.add_argument("--environment", required=True)
    execute.add_argument("--target", required=True)
    execute.add_argument("--path", required=True)
    execute.add_argument("--attempt", type=int, default=1)
    execute.add_argument("--retryable", action="store_true")

    finish = subparsers.add_parser("finish-run")
    finish.add_argument("--repo", default=".")
    finish.add_argument(
        "--outcome",
        required=True,
        choices=["succeeded", "rolled-back", "failed", "cancelled"],
    )
    finish.add_argument("--summary", required=True, type=Path)

    args = parser.parse_args()
    repo = Path(args.repo)
    try:
        if args.command == "validate":
            validate_local_state(repo)
            print_json({"valid": True, "version": VERSION})
        elif args.command == "snapshot":
            print_json(snapshot(repo))
        elif args.command == "drift":
            print_json(drift(repo))
        elif args.command == "status":
            print_json(status(repo))
        elif args.command == "prune-runs":
            print_json({"removed": [str(path) for path in prune_runs(repo)]})
        elif args.command == "start-run":
            print_json(
                start_run(repo, args.environment, args.target, args.source, args.policy)
            )
        elif args.command == "checkpoint":
            print_json(
                checkpoint(
                    repo,
                    args.step,
                    args.status,
                    args.mutates_target,
                    args.component,
                    args.external_log_reference,
                )
            )
        elif args.command == "run-entrypoint":
            return run_repository_entrypoint(
                repo,
                args.environment,
                args.target,
                args.path,
                args.attempt,
                args.retryable,
            )
        else:
            print(finish_run(repo, args.outcome, args.summary))
        return 0
    except (StateError, OSError, json.JSONDecodeError) as exc:
        print(str(exc), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
