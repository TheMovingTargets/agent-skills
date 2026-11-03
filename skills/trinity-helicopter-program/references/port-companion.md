# Port companion mode

The agent is doing a real port; the learner is learning the target language alongside it. Two jobs share one session, and the port is the one with a deadline. Keep them from tangling.

## Port units

Break the port into units small enough to teach in one sitting: one tool, one handler, one module, one config/bootstrap file, one test file. Typical order for an MCP server port: project scaffold and host bootstrap → one simple tool end to end → its tests → remaining tools → resources/prompts/UI resources → transport and deployment (Dockerfile). The first two units carry most of the new concepts; later units mostly reuse them, so lessons get shorter.

## Pacing

Ask once at the start (default `lockstep`), and let the learner change it any time:

- `lockstep` — port one unit, then teach it, then wait for `continue` before porting the next. Best for the first few units.
- `shadow` — keep porting; after each unit, append a lesson stub to the flight log and keep going. The learner pulls lessons with `debrief` (all queued) or `debrief <unit>`.
- `debrief` — finish the port (or a milestone), then teach the units in order.

Flight log: `python3 <skill-dir>/scripts/ledger.py flightlog --repo <repo-root> --append "<unit>|<target path:lines>|<source path:lines>|<concept ids>|<decision notes>"`; read it back with `--show`. It's stored outside the repo.

## Before porting each unit: port notes

While doing the port, jot (in the flight log or session memory) for each unit:

- the source anchors and target anchors,
- the target-language concepts it uses (by concept id),
- **decisions**: every place where the target language offered a real choice — record vs class, `Task` vs `ValueTask`, exceptions vs result object, DI lifetime, sync vs async I/O, `System.Text.Json` source-gen vs reflection — with the one-line reason you chose.

Decisions are the richest teaching material in a port: they're where idiom lives. A senior engineer learns more from "why `record` here and `class` there" than from a card on records.

## Teaching a unit

1. One-line summary of the unit and where it sits in the port. When starting a unit, skim the whole source and target files (not only the first excerpt) and add one line previewing any behaviour deltas you can see (see step 6), e.g. "Delta to watch: a missing key gives `None` from Python's `dict.get` but throws `KeyNotFoundException` from the C# indexer — we'll reach it at `Settings.cs:30-34`." The learner then reads every excerpt knowing where the two versions diverge.
2. Source excerpt and target excerpt as **separate faithful blocks**, each labelled `path:start-end`. If they don't line up 1:1, show the target excerpt plus the minimal source excerpt it replaces, and explain the restructure in prose.
3. A mapping table: source construct → target construct → concept id. Include rows where the source had nothing (e.g. `CancellationToken`) or the target has nothing (e.g. zod schemas absorbed into the type system).
4. Bridges, cards (≤3), and chips per [concept-cards.md](concept-cards.md).
5. The decisions for this unit, one line each, phrased as "chose X over Y because Z". Each decision is a natural `weeds` target.
6. **Behaviour deltas.** When the excerpt reaches a delta previewed in step 1, explain it in place. Look for inputs where the source and the port behave differently even though the happy path matches — falsy vs null, exceptions vs default values, rounding, string comparison, malformed input. Name any you find in one line as a port note, separate from the lesson. They teach the target language's semantics sharply, and they're exactly what contract tests miss.
7. Pause with the cursor set to the next excerpt of this unit or the next unit.

Steps 5 and 6 are one line per item; if the unit has many decisions, show the two most instructive and keep the rest for later excerpts.

When the unit has tests, teach the test after the code: tests show the target language's testing idioms (xUnit facts/theories, fixtures, mocking) and pin down what the port promises.

## Learner questions that affect the port

If a question reveals a bug, a missed source behaviour, or a better construct, say so plainly, separate from the lesson: "Port issue: the TS version retried on 429; the C# port doesn't yet. I'll fix that in this unit." Then fix it in the port as normal engineering work — and the fix becomes a teaching moment.

If the learner proposes a construct for the port, evaluate it on merit. Agreeing to be nice teaches the wrong idiom.

## Faithfulness during a live port

Excerpts must come from the files as they are now on disk (or the committed ref). Never show the code you're *about* to write as if it exists. If you're about to change lines you're teaching, finish the change first, then re-excerpt.
