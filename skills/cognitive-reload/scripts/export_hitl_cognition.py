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
        raise RuntimeError("no local Cognitive Reload progress found for this learner and repository")
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
        summary["learner_login"] = progress.get("learner_login") or progress.get("github_login")
        summary["identity_provider"] = progress.get("identity_provider", "github")
        summary["learner_questions"] = progress.get("learner_questions") or []
        summary["unresolved_questions"] = progress.get("unresolved_questions") or []

    return summary


def badge_widths(label: str, message: str) -> tuple[int, int]:
    return max(58, 7 * len(label) + 10), max(48, 7 * len(message) + 10)


def png_renderer():
    """PyMuPDF if installed (PNG badges need it); None otherwise. The exporter itself stays dependency-free."""
    try:
        import pymupdf
        return pymupdf
    except ImportError:
        try:
            import fitz
            return fitz
        except ImportError:
            return None


def _rgb(color: str) -> tuple[float, float, float]:
    value = color.lstrip("#")
    if len(value) == 3:
        value = "".join(char * 2 for char in value)
    return tuple(int(value[index:index + 2], 16) / 255 for index in (0, 2, 4))


def badge_png(label: str, message: str, color_name: str, renderer, scale: int = 2) -> bytes:
    """The same badge as `badge_svg`, drawn directly at `scale`x for hosts that do not show SVG in Markdown
    (Azure DevOps). Drawn rather than rasterised: MuPDF's SVG support drops the clip path, gradient and centring."""
    label_width, message_width = badge_widths(label, message)
    width = label_width + message_width
    document = renderer.open()
    page = document.new_page(width=width, height=20)
    radius = 3 / 20  # PyMuPDF takes a fraction of the shorter side: 3 px, like the SVG's rx="3"
    page.draw_rect(renderer.Rect(0, 0, width, 20), color=None,
                   fill=_rgb(BADGE_COLORS.get(color_name, color_name)), radius=radius)
    page.draw_rect(renderer.Rect(0, 0, label_width, 20), color=None, fill=_rgb("#555"), radius=radius)
    page.draw_rect(renderer.Rect(label_width - 3, 0, label_width, 20), color=None, fill=_rgb("#555"))  # square join
    for start, end, text in ((0, label_width, label), (label_width, width, message)):
        x = start + (end - start - renderer.get_text_length(text, fontname="helv", fontsize=11)) / 2
        page.insert_text((x, 15), text, fontname="helv", fontsize=11, color=(0, 0, 0), fill_opacity=0.3)
        page.insert_text((x, 14), text, fontname="helv", fontsize=11, color=(1, 1, 1))
    return page.get_pixmap(matrix=renderer.Matrix(scale, scale), alpha=True).tobytes("png")


def refresh_summary(current: dict) -> dict:
    """Recompute a published summary for today: freshness, and the index and level it feeds, change; everything
    else comes from the published current.json, so no learner progress or identity is needed (CI can run it)."""
    if current.get("privacy") != "public":
        raise RuntimeError("--refresh only rebuilds public exports; rerun the export from local progress instead")
    cognition = current["hitl_cognition"]
    counts = current.get("counts") or {}
    progress = {
        "orientation": cognition.get("orientation", "not_started"),
        "updated_at": cognition.get("last_reload_at"),
        "repository": current.get("repository") or {},
        "topics": {topic["id"]: {"state": topic["state"], "verified_score": topic["verified_score"],
                                 "concepts_seen": topic.get("concepts_seen") or [],
                                 "code_anchors": topic.get("code_anchors") or [],
                                 "assessment_attempts": [None] * topic.get("assessment_attempt_count", 0)}
                   for topic in current.get("topics") or []},
        "learner_questions": [None] * counts.get("learner_questions", 0),
        "unresolved_questions": [None] * counts.get("unresolved_questions", 0),
        "resume": current.get("resume") or {},
    }
    return build_summary(progress, "public")


def badge_svg(label: str, message: str, color_name: str) -> str:
    color = BADGE_COLORS.get(color_name, color_name)
    label_width, message_width = badge_widths(label, message)
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


def freshness_band(days: int | None) -> str:
    """The age band behind the badge colour; changes only when a threshold is crossed."""
    if days is None:
        return "unknown"
    if days <= 7:
        return "at most 7 days"
    if days <= 30:
        return "8-30 days"
    if days <= 90:
        return "31-90 days"
    return "over 90 days"


def freshness_message(last_reload_at: str | None) -> str:
    """The reload date. A badge is a static image, so a relative age ("today", "3 days") would go stale; the colour
    ages instead, whenever the exporter runs (see --refresh)."""
    parsed = parse_datetime(last_reload_at)
    return parsed.astimezone(timezone.utc).date().isoformat() if parsed else "unknown"


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


def badge_definitions(cognition: dict) -> dict[str, tuple[str, str, str]]:
    """Badge name → (label, message, color)."""
    return {
        "cognition": ("HITL cognition", f'{cognition["level"]} {cognition["index"]}', cognition["color"]),
        "topics": ("HITL topics", f'{cognition["explored_topics"]}/{cognition["topic_count"]} explored', "blue"),
        "assessed": ("HITL assessed", f'{cognition["assessed_topics"]}/{cognition["topic_count"]} assessed',
                     "green" if cognition["assessed_topics"] else "lightgrey"),
        "freshness": ("HITL freshness", freshness_message(cognition["last_reload_at"]),
                      badge_color_for_freshness(cognition["freshness_days"])),
    }


def badge_markdown(cognition: dict, prefix: str, badge_format: str) -> str:
    """Image lines for the four badges. PNG badges are drawn at 2x and sized back with Azure DevOps' `=WxH` syntax."""
    lines = []
    for name, (label, message, _) in badge_definitions(cognition).items():
        path = f"{prefix}hitl-{name}.{badge_format}"
        if badge_format == "png":
            label_width, message_width = badge_widths(label, message)
            path += f" ={label_width + message_width}x20"
        lines.append(f"![{label}]({path})")
    return " ".join(lines)  # one line: Azure DevOps turns each line break into a break, stacking the badges


def current_markdown(summary: dict, badge_format: str = "svg") -> str:
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

Freshness: reloaded `{freshness_message(cognition["last_reload_at"])}`, `{freshness_band(cognition["freshness_days"])}` old when these files were last written

## Badges

{badge_markdown(cognition, "badges/", badge_format)}

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


def readme_block(cognition: dict, badge_format: str = "svg") -> str:
    return f"""<!-- hitl-cognition:start -->
{badge_markdown(cognition, "hitl-cognition/badges/", badge_format)}

See [`hitl-cognition/`](hitl-cognition/) for the current human-in-the-loop cognition map.
<!-- hitl-cognition:end -->"""


def update_readme(path: Path, cognition: dict, badge_format: str = "svg") -> None:
    existing = path.read_text() if path.exists() else ""
    block = readme_block(cognition, badge_format)
    if README_BLOCK_RE.search(existing):
        updated = README_BLOCK_RE.sub(block, existing)
    else:
        updated = f"{block}\n\n{existing}" if existing else f"{block}\n"
    write_text(path, updated)


def resolve_badge_format(requested: str, summary: dict, renderer) -> str:
    """`auto` gives PNG for Azure DevOps repositories (which do not show SVG in Markdown) when PyMuPDF is present,
    and SVG everywhere else."""
    if requested == "png" and renderer is None:
        raise RuntimeError("PNG badges need PyMuPDF: pip install pymupdf (or use --badge-format svg)")
    if requested != "auto":
        return requested
    if (summary.get("repository") or {}).get("provider") != "azure-devops":
        return "svg"
    if renderer is None:
        print("warning: Azure DevOps does not show SVG badges in Markdown; install PyMuPDF (pip install pymupdf) "
              "for PNG badges. Writing SVG.", file=sys.stderr)
        return "svg"
    return "png"


def export(summary: dict, out: Path, readme: Path | None, badge_format: str = "svg", renderer=None,
           snapshot: bool = True) -> list[Path]:
    """Write the dashboard, badges and topic pages; with `snapshot`, also current.json and today's history entry
    (a refresh leaves those as the record of the reload)."""
    written: list[Path] = []
    cognition = summary["hitl_cognition"]
    badges = out / "badges"
    shields_dir = badges / "shields"
    topics_dir = out / "topics"
    history_dir = out / "history"
    date_name = datetime.now(timezone.utc).date().isoformat()

    files = {
        out / "README.md": current_markdown(summary, badge_format),
        out / "current.md": current_markdown(summary, badge_format),
    }
    for name, (label, message, color) in badge_definitions(cognition).items():
        files[badges / f"hitl-{name}.svg"] = badge_svg(label, message, color)

    for path, text in files.items():
        write_text(path, text)
        written.append(path)

    if badge_format == "png":
        for name, (label, message, color) in badge_definitions(cognition).items():
            path = badges / f"hitl-{name}.png"
            temporary = path.with_suffix(".png.tmp")
            temporary.write_bytes(badge_png(label, message, color, renderer))
            os.replace(temporary, path)
            written.append(path)

    if snapshot:
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
            freshness_message(cognition["last_reload_at"]),
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
        update_readme(readme, cognition, badge_format)
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
    parser.add_argument("--badge-format", choices=["auto", "svg", "png"], default="auto",
                        help="badge images in Markdown; auto uses PNG for Azure DevOps (needs PyMuPDF), else SVG")
    parser.add_argument("--refresh", action="store_true",
                        help="re-age a published export from its current.json (freshness colour, index, level); "
                             "needs no local progress, so it can run on a schedule")
    args = parser.parse_args()

    try:
        repo = Path(args.repo).resolve()
        out = Path(args.out)
        if not out.is_absolute():
            out = repo / out
        if args.refresh:
            summary = refresh_summary(json.loads((out / "current.json").read_text()))
        else:
            progress_path = Path(args.progress).resolve() if args.progress else None
            progress = read_progress(repo, progress_path)
            summary = build_summary(progress, args.privacy)
        if args.dry_run:
            print(json.dumps(summary, indent=2))
            return 0
        readme = Path(args.readme) if args.readme else None
        if readme and not readme.is_absolute():
            readme = repo / readme
        renderer = png_renderer()
        badge_format = resolve_badge_format(args.badge_format, summary, renderer)
        written = export(summary, out, readme, badge_format, renderer, snapshot=not args.refresh)
        for path in written:
            print(path)
        return 0
    except (OSError, RuntimeError, json.JSONDecodeError) as exc:
        print(f"HITL cognition export failed: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
