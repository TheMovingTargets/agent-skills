# Evidence ledger protocol

Before quizzing any area, create an evidence ledger. The ledger lets the developer see what the agent inspected and why the quiz is grounded.

## Required fields

- `area_id`
- `area_name`
- `classification`: `changed_area`, `sampled_critical_area`, `sampled_stale_area`, `sampled_unverified_area`, or `handoff_area`
- `why_selected`
- `git_evidence`
- `files_inspected`
- `tests_inspected`
- `docs_inspected`
- `observed_invariants`
- `risk_drivers`
- `unknowns`
- `agent_confidence`

Use `templates/evidence-ledger.area.json`.

## Evidence quality

Prefer concrete evidence:

- file paths
- test names
- function/module/class names
- commit hashes
- documentation sections
- observed invariants

Avoid unsupported claims like "this appears robust" unless backed by evidence.

## Confidence labels

Use:

- `low`: evidence is sparse, inferred mostly from names/structure
- `medium`: multiple files/tests/docs inspected, but some unknowns remain
- `high`: implementation, tests, and docs align

## How to present the ledger to the developer

Keep the chat version compact:

```text
Area: Privacy / ingestion
Why selected: high-risk sampled area; unverified; future agents could easily break data boundaries.
Evidence inspected:
- src/api/ingestion.rs
- src/privacy/fingerprint.rs
- tests/device_scoped_deletion.rs
Observed invariants:
- raw content must not be persisted
- exact local paths must not be persisted
- deletion must be scoped by org/user/device
Unknowns:
- desktop adapter lifecycle appears underdocumented
```

Then ask the developer to inspect the relevant files before the quiz.
