# Integration with agent workflows

`cognitive-reload` complements agent-heavy workflows by measuring whether the human remains able to guide the work.

## Typical flow

```text
grill-me → to-prd → to-issues → tdd/implementation → code review → cognitive-reload → handoff/ADR/issues
```

## Planning skills

After planning skills such as `grill-me` or `to-prd`, cognitive reload can verify whether implementation still matches the intended design.

## Issue-generation skills

After `to-issues`, cognitive reload can identify whether implemented issue batches have fragmented the human's mental model.

## TDD skills

When TDD has been used, quiz the human on what the tests prove. Tests are executable cognition artifacts.

## Handoff skills

Before handoff, cognitive reload should produce:

- verified cognition areas
- unverified areas
- bus-factor risks
- agent guidance constraints
- ADR candidates
- issue candidates

## Agent switching

If the developer is switching from Claude to Codex, Cursor, or another agent, prioritize `agent_guidance_readiness` and produce handoff notes that are independent of a specific agent harness.
