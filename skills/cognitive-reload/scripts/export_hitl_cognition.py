#!/usr/bin/env python3
"""Export local Cognitive Reload progress into repo-visible HITL artifacts."""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from xml.sax.saxutils import escape as xml_escape


STATE_WEIGHT = {
    "unseen": 0.0,
    "introduced": 0.33,
    "explored": 0.75,
    "assessed": 1.0,
}

LEVELS = [
    (85, "agent-guidance ready", "brightgreen"),
    (70, "operational", "green"),
    (50, "developing", "yellow"),
    (25, "oriented", "blue"),
    (0, "unmapped", "lightgrey"),
]

BADGE_COLORS = {
    "brightgreen": "#4c1",
    "green": "#97ca00",
    "yellow": "#dfb317",
    "orange": "#fe7d37",
    "red": "#e05d44",
    "blue": "#007ec6",
    "lightgrey": "#9f9f9f",
}

README_BLOCK_RE = re.compile(
    r"<!-- hitl-cognition:start -->.*?<!-- hitl-cognition:end -->",
    re.S,
)


def run(args: list[str], cwd: Path) -> str:
    result = subprocess.run(args, cwd=cwd, text=True, capture_output=True, check=False)
    if result.returncode:
        raise RuntimeError(result.stderr.strip() or f"command failed: {' '.join(args)}")
    return result.stdout.strip()


def read_progress(repo: Path, progress_path: Path | None) -> dict:
    if progress_path:
        return json.loads(progress_path.read_text())
    script = Path(__file__).with_name("progress_store.py")
    output = run([sys.executable, str(script), "get", "--repo", str(repo)], repo)
    if output == "null":
        raise RuntimeError("no local Cognitive Reload progress found for this GitHub user and repository")
    return json.loads(output)


def parse_datetime(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def freshness_days(updated_at: str | None) -> int | None:
    parsed = parse_datetime(updated_at)
    if not parsed:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    delta = datetime.now(timezone.utc) - parsed.astimezone(timezone.utc)
    return max(0, delta.days)


def freshness_points(days: int | None) -> int:
    if days is None:
        return 0
    if days <= 7:
        return 10
    if days <= 30:
        return 6
    if days <= 90:
        return 3
    return 0


def orientation_points(orientation: str | None) -> int:
    if orientation == "explored":
        return 30
    if orientation == "introduced":
        return 18
    return 0


def level_for(index: int) -> tuple[str, str]:
    for threshold, label, color in LEVELS:
        if index >= threshold:
            return label, color
    return "unmapped", "lightgrey"


def slugify(value: str) -> str:
    slug = re.sub(r"[^a-zA-Z0-9]+", "-", value.strip().lower()).strip("-")
    return slug or "topic"


def topic_name(topic_id: str) -> str:
    return topic_id.replace("_", " ").replace("-", " ").title()


def safe_score(value: object) -> float | None:
    return value if isinstance(value, (int, float)) else None


def build_summary(progress: dict, privacy: str) -> dict:
    topics = progress.get("topics") or {}
    topic_count = len(topics)
    topic_rows = []
    explored_equivalent = 0.0
    verified_sum = 0.0
    verified_count = 0
    assessed_count = 0
    introduced_count = 0
    explored_count = 0
    agent_ready_count = 0

    for topic_id, topic in sorted(topics.items()):
        state = topic.get("state", "unseen")
        score = safe_score(topic.get("verified_score"))
        explored_equivalent += STATE_WEIGHT.get(state, 0.0)
        if state in {"introduced", "explored", "assessed"}:
            introduced_count += 1
        if state in {"explored", "assessed"}:
            explored_count += 1
        if state == "assessed":
            assessed_count += 1
        if score is not None:
            verified_sum += score
            verified_count += 1
        agent_ready = state == "assessed" and score is not None and score >= 4
        if agent_ready:
            agent_ready_count += 1

        row = {
            "id": topic_id,
            "name": topic_name(topic_id),
            "state": state,
            "verified_score": score,
            "agent_ready": agent_ready,
            "concepts_seen": list(topic.get("concepts_seen") or []),
            "code_anchors": list(topic.get("code_anchors") or []),
            "assessment_attempt_count": len(topic.get("assessment_attempts") or []),
        }
        if privacy == "private":
            row["assessment_attempts"] = topic.get("assessment_attempts") or []
        topic_rows.append(row)

    denominator = max(topic_count, 1)
    orientation = progress.get("orientation", "not_started")
    exploration_component = 30 * explored_equivalent / denominator
    verified_component = 30 * sum(
        ((safe_score(topic.get("verified_score")) or 0) / 5)
        for topic in topics.values()
    ) / denominator
    days = freshness_days(progress.get("updated_at"))
    index = round(
        orientation_points(orientation)
        + exploration_component
        + verified_component
        + freshness_points(days)
    )
    index = max(0, min(100, index))
    level, color = level_for(index)

    summary = {
        "schema_version": "0.6.0",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "privacy": privacy,
        "repository": progress.get("repository") or {},
        "hitl_cognition": {
            "index": index,
            "level": level,
            "color": color,
            "orientation": orientation,
            "topic_count": topic_count,
            "introduced_topics": introduced_count,
            "explored_topics": explored_count,
            "assessed_topics": assessed_count,
            "agent_ready_topics": agent_ready_count,
            "verified_average": round(verified_sum / verified_count, 2) if verified_count else None,
            "freshness_days": days,
            "last_reload_at": progress.get("updated_at"),
        },
        "topics": topic_rows,
        "counts": {
            "learner_questions": len(progress.get("learner_questions") or []),
            "unresolved_questions": len(progress.get("unresolved_questions") or []),
        },
        "resume": progress.get("resume") or {},
    }

    if privacy == "private":
        summary["github_login"] = progress.get("github_login")
        summary["learner_questions"] = progress.get("learner_questions") or []
        summary["unresolved_questions"] = progress.get("unresolved_questions") or []

    return summary


def badge_svg(label: str, message: str, color_name: str) -> str:
    color = BADGE_COLORS.get(color_name, color_name)
    label_width = max(58, 7 * len(label) + 10)
    message_width = max(48, 7 * len(message) + 10)
    width = label_width + message_width
    label_text_x = label_width / 2
    message_text_x = label_width + message_width / 2
    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="20" role="img" aria-label="{xml_escape(label)}: {xml_escape(message)}">
  <title>{xml_escape(label)}: {xml_escape(message)}</title>
  <linearGradient id="s" x2="0" y2="100%">
    <stop offset="0" stop-color="#bbb" stop-opacity=".1"/>
    <stop offset="1" stop-opacity=".1"/>
  </linearGradient>
  <clipPath id="r"><rect width="{width}" height="20" rx="3" fill="#fff"/></clipPath>
  <g clip-path="url(#r)">
    <rect width="{label_width}" height="20" fill="#555"/>
    <rect x="{label_width}" width="{message_width}" height="20" fill="{color}"/>
    <rect width="{width}" height="20" fill="url(#s)"/>
  </g>
  <g fill="#fff" text-anchor="middle" font-family="Verdana,Geneva,DejaVu Sans,sans-serif" text-rendering="geometricPrecision" font-size="11">
    <text x="{label_text_x:.1f}" y="15" fill="#010101" fill-opacity=".3">{xml_escape(label)}</text>
    <text x="{label_text_x:.1f}" y="14">{xml_escape(label)}</text>
    <text x="{message_text_x:.1f}" y="15" fill="#010101" fill-opacity=".3">{xml_escape(message)}</text>
    <text x="{message_text_x:.1f}" y="14">{xml_escape(message)}</text>
  </g>
</svg>
"""


def badge_color_for_freshness(days: int | None) -> str:
    if days is None:
        return "lightgrey"
    if days <= 7:
        return "brightgreen"
    if days <= 30:
        return "green"
    if days <= 90:
        return "orange"
    return "red"


def freshness_message(days: int | None) -> str:
    if days is None:
        return "unknown"
    if days == 0:
        return "today"
    if days == 1:
        return "1 day"
    return f"{days} days"


def shields(label: str, message: str, color: str) -> dict:
    return {
        "schemaVersion": 1,
        "label": label,
        "message": message,
        "color": color,
    }


def markdown_list(values: list[str]) -> str:
    if not values:
        return "- None recorded"
    return "\n".join(f"- `{value}`" if "/" in value or ":" in value else f"- {value}" for value in values)


def current_markdown(summary: dict) -> str:
    cognition = summary["hitl_cognition"]
    repo = summary.get("repository") or {}
    rows = []
    for topic in summary["topics"]:
        score = topic["verified_score"]
        rows.append(
            "| {name} | `{state}` | {score} | {ready} |".format(
                name=topic["name"],
                state=topic["state"],
                score="n/a" if score is None else f"{score:.1f} / 5",
                ready="yes" if topic["agent_ready"] else "no",
            )
        )
    if not rows:
        rows.append("| No topics recorded | `unseen` | n/a | no |")
    target = repo.get("target_ref") or "unknown"
    commit = repo.get("target_commit") or "unknown"
    return f"""# HITL Cognition

Current level: `{cognition["level"]}` (`{cognition["index"]}/100`)

This dashboard is generated from Cognitive Reload progress. It summarizes verified
human understanding of this repository; it is not a code-quality score.

Repository target: `{target}` at `{commit}`

Last reload: `{cognition["last_reload_at"] or "unknown"}`

Freshness: `{freshness_message(cognition["freshness_days"])}`

## Badges

![HITL cognition](badges/hitl-cognition.svg)
![HITL topics](badges/hitl-topics.svg)
![HITL assessed](badges/hitl-assessed.svg)
![HITL freshness](badges/hitl-freshness.svg)

## Topic Map

| Topic | State | Verified | Agent-ready |
|---|---:|---:|---:|
{chr(10).join(rows)}

## Counts

- Learner questions recorded: `{summary["counts"]["learner_questions"]}`
- Unresolved questions recorded: `{summary["counts"]["unresolved_questions"]}`
- Agent-ready topics: `{cognition["agent_ready_topics"]}`
"""


def topic_markdown(topic: dict) -> str:
    score = topic["verified_score"]
    return f"""# {topic["name"]}

State: `{topic["state"]}`

Verified score: `{"n/a" if score is None else f"{score:.1f} / 5"}`

Agent-ready: `{"yes" if topic["agent_ready"] else "no"}`

Assessment attempts: `{topic["assessment_attempt_count"]}`

## Concepts Seen

{markdown_list(topic["concepts_seen"])}

## Code Anchors

{markdown_list(topic["code_anchors"])}
"""


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(text)
    os.replace(temporary, path)


def write_json(path: Path, data: dict) -> None:
    write_text(path, json.dumps(data, indent=2) + "\n")


def readme_block() -> str:
    return """<!-- hitl-cognition:start -->
![HITL cognition](hitl-cognition/badges/hitl-cognition.svg)
![HITL topics](hitl-cognition/badges/hitl-topics.svg)
![HITL assessed](hitl-cognition/badges/hitl-assessed.svg)
![HITL freshness](hitl-cognition/badges/hitl-freshness.svg)

See [`hitl-cognition/`](hitl-cognition/) for the current human-in-the-loop cognition map.
<!-- hitl-cognition:end -->"""


def update_readme(path: Path) -> None:
    existing = path.read_text() if path.exists() else ""
    block = readme_block()
    if README_BLOCK_RE.search(existing):
        updated = README_BLOCK_RE.sub(block, existing)
    else:
        updated = f"{block}\n\n{existing}" if existing else f"{block}\n"
    write_text(path, updated)


def export(summary: dict, out: Path, readme: Path | None) -> list[Path]:
    written: list[Path] = []
    cognition = summary["hitl_cognition"]
    badges = out / "badges"
    shields_dir = badges / "shields"
    topics_dir = out / "topics"
    history_dir = out / "history"
    date_name = datetime.now(timezone.utc).date().isoformat()

    files = {
        out / "README.md": current_markdown(summary),
        out / "current.md": current_markdown(summary),
        badges / "hitl-cognition.svg": badge_svg(
            "HITL cognition",
            f'{cognition["level"]} {cognition["index"]}',
            cognition["color"],
        ),
        badges / "hitl-topics.svg": badge_svg(
            "HITL topics",
            f'{cognition["explored_topics"]}/{cognition["topic_count"]} explored',
            "blue",
        ),
        badges / "hitl-assessed.svg": badge_svg(
            "HITL assessed",
            f'{cognition["assessed_topics"]}/{cognition["topic_count"]} assessed',
            "green" if cognition["assessed_topics"] else "lightgrey",
        ),
        badges / "hitl-freshness.svg": badge_svg(
            "HITL freshness",
            freshness_message(cognition["freshness_days"]),
            badge_color_for_freshness(cognition["freshness_days"]),
        ),
    }

    for path, text in files.items():
        write_text(path, text)
        written.append(path)

    write_json(out / "current.json", summary)
    written.append(out / "current.json")
    write_json(history_dir / f"{date_name}.json", summary)
    written.append(history_dir / f"{date_name}.json")

    shields_payloads = {
        shields_dir / "cognition.json": shields(
            "HITL cognition", f'{cognition["level"]} {cognition["index"]}', cognition["color"]
        ),
        shields_dir / "topics.json": shields(
            "HITL topics", f'{cognition["explored_topics"]}/{cognition["topic_count"]} explored', "blue"
        ),
        shields_dir / "assessed.json": shields(
            "HITL assessed", f'{cognition["assessed_topics"]}/{cognition["topic_count"]} assessed', "green"
        ),
        shields_dir / "freshness.json": shields(
            "HITL freshness",
            freshness_message(cognition["freshness_days"]),
            badge_color_for_freshness(cognition["freshness_days"]),
        ),
    }
    for path, payload in shields_payloads.items():
        write_json(path, payload)
        written.append(path)

    for topic in summary["topics"]:
        path = topics_dir / f"{slugify(topic['id'])}.md"
        write_text(path, topic_markdown(topic))
        written.append(path)

    if readme:
        update_readme(readme)
        written.append(readme)

    return written


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", default=".")
    parser.add_argument("--progress", help="explicit progress.json path")
    parser.add_argument("--out", default="hitl-cognition")
    parser.add_argument("--privacy", choices=["public", "private"], default="public")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--readme", help="root README path to update with badge block")
    args = parser.parse_args()

    try:
        repo = Path(args.repo).resolve()
        progress_path = Path(args.progress).resolve() if args.progress else None
        progress = read_progress(repo, progress_path)
        summary = build_summary(progress, args.privacy)
        if args.dry_run:
            print(json.dumps(summary, indent=2))
            return 0
        out = Path(args.out)
        if not out.is_absolute():
            out = repo / out
        readme = Path(args.readme) if args.readme else None
        if readme and not readme.is_absolute():
            readme = repo / readme
        written = export(summary, out, readme)
        for path in written:
            print(path)
        return 0
    except (OSError, RuntimeError, json.JSONDecodeError) as exc:
        print(f"HITL cognition export failed: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
