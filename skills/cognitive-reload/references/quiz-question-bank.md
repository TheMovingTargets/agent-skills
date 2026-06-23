# Quiz question bank

Use these as small, staged prompts. Do not ask an entire section at once.

## Orientation

- Which file would you inspect first to understand this area?
- Which test file best describes this behavior?
- Where does data enter this subsystem?
- Where does control leave this subsystem?

## Behavior

- Explain the happy path in one paragraph.
- What state is read, written, or transformed?
- What external dependency or boundary does this area rely on?

## Causality

- Why is this boundary placed here rather than one layer above or below?
- What design tradeoff does this module appear to make?
- What assumption would break this design?

## Change awareness

- What changed in the selected reload window?
- Which changed file matters most for behavior?
- Which change is documentation-only, and which changes runtime behavior?

## Invariants and risk

- What must never be persisted, leaked, skipped, or silently changed?
- What would be the riskiest change for an agent to make here?
- What failure mode would you test before approving a change?

## Test awareness

- Which test would you run before modifying this area?
- What behavior does that test protect?
- What missing test would you ask an agent to add?

## Agent guidance

- Give a future coding agent three constraints before modifying this area.
- What should the agent read first?
- What should the agent avoid changing without explicit approval?
- What evidence would you require from the agent before accepting its change?
