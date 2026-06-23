# Team coverage model

Team mode extends solo cognition scoring without forcing every developer to know everything.

## Per-developer scoring

Each developer has per-area scores. Do not collapse these into one flat average too early.

## Area coverage

For each area:

```text
coverage_score = max(verified developer score for the area)
```

## Redundancy

```text
redundancy_count = number of developers with score >= 4.0
```

## Bus-factor risk

Flag bus-factor risk when:

- area importance is high or critical
- coverage score is >= 4.0
- redundancy_count is 1

Flag coverage gap when:

- area importance is high or critical
- no developer has verified score >= 3.0

## Specialization

A healthy team map may have overlapping specializations, not identical knowledge. Preserve who knows what.

## Team artifact fields

Recommended fields:

- `developers`
- `areas`
- `coverage_by_area`
- `redundancy_by_area`
- `bus_factor_risks`
- `coverage_gaps`
- `recommended_cross_training`
