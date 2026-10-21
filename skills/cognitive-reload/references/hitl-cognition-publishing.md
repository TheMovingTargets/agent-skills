# HITL Cognition Publishing

Use this reference when the learner asks to publish, export, display, badge, or
summarize Cognitive Reload progress in the repository.

## Purpose

The local progress store is private learner memory. Published HITL cognition
artifacts are a sanitized projection intended to show the repository's current
human-in-the-loop cognition level.

Do not write artifacts without confirmation. At the end of a reload session,
offer publishing as the default closing action. Once the learner approves, invoke
the bundled exporter directly instead of asking the learner to run commands.

## Default Output

Generate a top-level folder:

```text
hitl-cognition/
  README.md
  current.json
  current.md
  badges/
    hitl-cognition.svg
    hitl-topics.svg
    hitl-assessed.svg
    hitl-freshness.svg
    hitl-*.png          (Azure DevOps repositories, when PyMuPDF is available)
    shields/
      cognition.json
      topics.json
      assessed.json
      freshness.json
  topics/
    <topic-id>.md
  history/
    <yyyy-mm-dd>.json
```

The repository README may also receive a small optional badge block. Only modify
the root README after explicit approval.

## Export Command

Use the bundled exporter, invoked from this skill's own directory. Resolve
`scripts/export_hitl_cognition.py` relative to where this skill is installed — for example
`.agents/skills/cognitive-reload/` (Codex, opencode, Pi) or `.claude/skills/cognitive-reload/`
(Claude Code):

```bash
python3 scripts/export_hitl_cognition.py --repo .
```

Useful options:

- `--dry-run`: print the generated `current.json` summary without writing files.
- `--out hitl-cognition`: choose the output directory.
- `--privacy public`: default sanitized export.
- `--privacy private`: include learner identity and raw learner questions.
- `--readme README.md`: insert/update the root README badge block.
- `--refresh`: re-age a published export from its `current.json` for today's date (freshness colour, index, level), without local progress; it leaves `current.json` and history alone, and files change only when an age threshold (7, 30, 90 days) is crossed, so it suits a scheduled job.
- `--badge-format auto|svg|png`: badge images used in Markdown. `auto` (default) uses PNG for Azure DevOps repositories, which do not display SVG images in Markdown, and SVG elsewhere. PNG badges need PyMuPDF (`pip install pymupdf`); without it `auto` warns and writes SVG, so in an Azure DevOps repository run the exporter with a Python that has PyMuPDF.
- `--progress PATH`: export from a specific local progress file.

After approval, the default command (run from the active skill directory) is:

```bash
python3 scripts/export_hitl_cognition.py --repo . --readme README.md
```

Run the command yourself. Do not respond with only instructions unless file
writes are blocked by the environment.

## Privacy Rules

Public mode:

- include topic names, states, verified scores, code anchors, timestamps, and aggregate counts
- exclude the learner login (GitHub or Azure DevOps)
- exclude raw teach-back answers
- exclude raw learner questions
- include unresolved question count, not raw unresolved question text

Private mode may include the learner login and raw learner questions. Use it only for
local/team repositories where that disclosure is intended.

## README Badge Block

If approved, insert this block near the top of the root README:

```markdown
<!-- hitl-cognition:start -->
![HITL cognition](hitl-cognition/badges/hitl-cognition.svg)
![HITL topics](hitl-cognition/badges/hitl-topics.svg)
![HITL assessed](hitl-cognition/badges/hitl-assessed.svg)
![HITL freshness](hitl-cognition/badges/hitl-freshness.svg)

See [`hitl-cognition/`](hitl-cognition/) for the current human-in-the-loop cognition map.
<!-- hitl-cognition:end -->
```

## Interpretation

Published HITL cognition is evidence of verified human understanding. It is not
a code-quality score, production-readiness score, or agent-generated architecture
claim.

Use these state meanings:

- `unseen`: not covered
- `introduced`: explained conceptually
- `explored`: guided code/test walkthrough completed
- `assessed`: teach-back completed

Only assessed topics contribute verified understanding. Material shown during a
tutorial does not imply understanding.
