# Optional Teach-Back Assessment

Load this only after explicit learner consent.

## Contract

- Ask one question at a time.
- Test only material explored in the tutorial.
- Prefer explanation and prediction over filename recall.
- Keep each question to one concept, with at most one follow-up.
- Let the learner ask clarifying questions or return to tutoring at any time.
- Grade immediately and cite the evidence expected.

## Question progression

1. **Mental model:** Explain the component's responsibility in the larger flow.
2. **Causal reasoning:** Predict what happens for a concrete input or failure.
3. **Invariant:** Explain why a security/privacy/data rule exists.
4. **Code navigation:** Identify the implementation anchor and test.
5. **Agent guidance:** State constraints for a future change.

Do not ask all stages automatically. Stop when evidence is sufficient or the learner wants to stop.

## Scoring

Use 0-5 only for an assessed topic:

| Score | Evidence |
|---:|---|
| 0 | No usable model demonstrated |
| 1 | Recognizes terms but cannot explain flow |
| 2 | Partial flow with major errors or missing boundaries |
| 3 | Correct working model; needs support on risks or navigation |
| 4 | Can explain, navigate, predict, and constrain agent work |
| 5 | Can critique tradeoffs, gaps, and tests with strong evidence |

Agent-handoff readiness begins at 4, but always record the dimensions and attempt evidence, not just the number.

## Recording the teach-back as Evidence

After scoring an area, record it in the Proficiency Profile:

```text
python3 <this-skill-dir>/scripts/profile_hook.py run record teachback --lang <pack> --concepts <ids> --score <area score> [--area <id>]
```

- `--concepts` takes only the generic Architecture Concepts the teach-back exercised, mapped from the topic onto [architecture-concepts.md](architecture-concepts.md). If nothing fits, record nothing. Never invent an id, and never name one after the repo's own code.
- `--lang` is the code's Language: the Trinity language pack id, for example `csharp-dotnet`.
- Add `--area` only when the code's place in the stack is obvious.
- The writer turns the score into `passed` (3.0 or above) or `failed`, with `score.scaled` = score / 5. It never changes the score you give.

## Retakes

Preserve each attempt. Offer a narrow retake for the missed concept. After giving the answer directly, allow a later retake but mark it `assisted`; do not pretend it was independent recall.
