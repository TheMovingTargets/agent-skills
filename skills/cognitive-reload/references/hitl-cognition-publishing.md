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

Use the bundled exporter:

```bash
python3 .agents/skills/cognitive-reload/scripts/export_hitl_cognition.py --repo .
```

or the Claude-installed copy:

```bash
python3 .claude/skills/cognitive-reload/scripts/export_hitl_cognition.py --repo .
```

Useful options:

- `--dry-run`: print the generated `current.json` summary without writing files.
- `--out hitl-cognition`: choose the output directory.
- `--privacy public`: default sanitized export.
- `--privacy private`: include learner identity and raw learner questions.
- `--readme README.md`: insert/update the root README badge block.
- `--progress PATH`: export from a specific local progress file.

After approval, the default command is:

```bash
python3 .agents/skills/cognitive-reload/scripts/export_hitl_cognition.py --repo . --readme README.md
```

If the active session is using the Claude-installed copy, use:

```bash
python3 .claude/skills/cognitive-reload/scripts/export_hitl_cognition.py --repo . --readme README.md
```

Run the command yourself. Do not respond with only instructions unless file
writes are blocked by the environment.

## Privacy Rules

Public mode:

- include topic names, states, verified scores, code anchors, timestamps, and aggregate counts
- exclude GitHub login
- exclude raw teach-back answers
- exclude raw learner questions
- include unresolved question count, not raw unresolved question text

Private mode may include GitHub login and raw learner questions. Use it only for
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
