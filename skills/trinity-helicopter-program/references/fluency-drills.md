# Fluency drills (`fly`)

Drills happen only when the learner asks (`fly`, "quiz me", "let me try"). They test whether the learner can *operate* the language, not recite it. Never slip a drill into a lesson uninvited.

## Drill types

Pick one or two per `fly`, anchored on concepts from the session, preferring ones loaded or explored but not yet fluent.

- **Predict** — show a small faithful excerpt (or a labelled illustrative snippet) and ask what it prints, returns, throws, or allocates. Best for false friends (`struct` copies, lazy LINQ, hot `Task`s).
- **Next line** — show the start of a method from this repo with the remainder hidden and ask the learner to write the next few lines idiomatically. Then show the real code and compare.
- **Translate** — give a 5–15 line snippet in a language the learner is fluent in and ask for the idiomatic target-language version. Grade on idiom, not just correctness.
- **Spot the smell** — show an illustrative snippet that compiles but is non-idiomatic or subtly wrong (`async void`, `.Result` on a task, `throw ex;`, multiple enumeration, `new HttpClient()` per call, logging to stdout in a stdio MCP server) and ask what a reviewer would flag.
- **Choose** — present a real decision from the port's decision log and ask which option and why, before revealing what was chosen.

## Grading

- Correct and idiomatic → mark the concept `fluent` in the ledger.
- Correct but not idiomatic → show the idiomatic version, explain the difference in two or three sentences, leave the status as is.
- Wrong → explain using the bridge language, then offer one narrower retry. No score shaming; the learner chose to fly.

Record every attempt with its grade (`record drill --grade good|hard|again` in SKILL.md's Recording Evidence): correct and idiomatic is `good`, correct but not idiomatic is `hard`, and wrong is `again`.

Keep it short: at most three questions before pausing. Afterwards restore the cursor and continue the main path.
