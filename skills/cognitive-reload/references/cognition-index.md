# Cognition Index

Use this reference when explaining or publishing the repository HITL cognition
index.

## Components

The index is a 0-100 summary derived from local Cognitive Reload progress:

```text
30% orientation coverage
30% topic exploration coverage
30% verified assessment coverage
10% freshness
```

## Orientation

```text
not_started -> 0
introduced  -> 18
explored    -> 30
```

## Topic Exploration

Each topic contributes to the 30-point exploration component:

```text
unseen     -> 0.00
introduced -> 0.33
explored   -> 0.75
assessed   -> 1.00
```

## Verified Assessment

Only assessed topics with `verified_score` contribute to the 30-point verified
component. Unassessed topics contribute zero to this component.

```text
verified component = 30 * sum(score / 5 for each topic) / total topic count
```

This intentionally prevents a repository from looking "agent-ready" when many
topics were explained but not tested.

## Freshness

Freshness is based on `updated_at`:

```text
0-7 days    -> 10
8-30 days   -> 6
31-90 days  -> 3
91+ days    -> 0
unknown     -> 0
```

## Levels

```text
0-24   unmapped
25-49  oriented
50-69  developing
70-84  operational
85-100 agent-guidance ready
```

## Agent-Ready Topics

A topic is agent-guidance ready when:

- state is `assessed`
- latest verified score is `>= 4`

Do not infer readiness from tutorial coverage alone.
