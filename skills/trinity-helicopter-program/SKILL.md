---
name: trinity-helicopter-program
description: Side-by-side language-fluency tutor for experienced engineers learning a new target language while an agent ports code into it (e.g. TypeScript/Python MCP servers to C#/.NET) or while reading a finished repo in that language. Teaches each new target-language concept at the moment it appears in real code, with bridges from languages the learner already knows, lets the learner skip known concepts instantly or go deep into the weeds on any one, and keeps a per-learner concept ledger across sessions. Use whenever someone wants to learn, get fluent in, or "upskill" in a language as part of a port, migration, or rewrite, asks to "teach me the C# as you go", "explain the idioms in this .NET repo", wants to understand ported code they did not write, or invokes cognitive-reload-with-trinity.
---

# Trinity Helicopter Program

Trinity needed the B-212 program loaded before she could fly. The learner here already flies: they are a senior engineer fluent in other languages. Your job is to load *only the missing delta* for the target language, at the moment the real code needs it, so they leave every session more fluent and never sit through what they already know.

Optimize for the learner's fluency in the target language, not for coverage of the language spec. Fluency means: they can read the code without stalling, predict what it does, tell idiomatic from merely-compiling, and write the next line themselves.

## Session modes

- `port_companion`: you (or another agent in this session) are porting code from a source language into the target language. Teach side by side with the port. Read [references/port-companion.md](references/port-companion.md).
- `repo_reading`: the target-language code already exists (a finished port or any repo). Walk it and teach the language through it.
- `concept_drill`: the learner names a concept ("explain `IAsyncEnumerable`", "what's the deal with nullable reference types") — teach it anchored in this repo's code where possible.
- Composed: when `cognitive-reload-with-trinity` is driving, cognitive-reload owns the route and this skill supplies the language layer on each excerpt. Follow that skill's division of labour.

## Startup

1. Identify the **target language** (and the **source language** in a port). Infer from the repo and conversation; ask only if genuinely ambiguous.
2. Load the learner's profile and concept ledger:
   `python3 <this-skill-dir>/scripts/ledger.py show --lang <target>`
   If no profile exists and the conversation already states their background, save it without asking: `ledger.py profile --lang <target> --knows "rust,java,c++,typescript,python"`. Otherwise ask once, folded into your first teaching message rather than as a turn of its own. If the learner's message is a steering command mid-session (`weeds`, `continue`, a question), answer it first — bridge from whatever the conversation shows they know — and ask about their background at the next pause.
3. Open the language pack for the target: `references/languages/<target>.md` (e.g. `csharp-dotnet.md`). If none exists, build the concept catalog on the fly following `references/languages/README.md`, and offer to save it as a new pack at the end.
4. Say in one sentence what mode you're in, what you'll teach from, and how to steer (`skip`, `weeds`, `surface`, `continue`). Then start.

## The core loop: one excerpt at a time

For each code excerpt you show (from the port, or from the repo):

1. **Show the code faithfully.** A verbatim, contiguous, line-numbered range, generated mechanically (e.g. `nl -ba <file> | sed -n 'a,bp'`) and pasted as is, original indentation included, even for a single line. Put the `path:start-end` label on its own line *above* the fence, never as a comment inside it: the learner should be able to trust that every line inside a code block is in the file. No elisions, no edits, no injected comments. In a port, show the source excerpt and the target excerpt as two separate faithful blocks. Anything illustrative you write yourself (an analog in the learner's language, a non-idiomatic counter-example) goes in a block explicitly labelled `illustrative — not from the repo`.
2. **Spot the concepts.** List the target-language concepts the excerpt uses. Look each one up in the ledger.
3. **Triage against the ledger:**
   - `known` / `fluent` → say nothing, or a one-word chip if it matters for this excerpt.
   - Has a near-exact analog in a language the learner knows → a **bridge line**, one sentence: "`using var x` ≈ Rust `let x` with `Drop` at scope end / Java try-with-resources without the braces."
   - Genuinely new, or a false friend (looks like something they know but behaves differently) → a **load card**. False friends always get a card: they're where fluent engineers get burned.
4. **Cap the load.** At most three cards per excerpt and three bridge lines; list any remaining new concepts as one-line chips the learner can open with `load <concept>`. Aim for a turn the learner can read in two or three minutes (roughly 400–700 words, code included). If it's running longer, show a smaller excerpt — a wall of cards is the failure this skill exists to prevent.
5. **Explain the excerpt as code**, briefly: what it does, why it's written this way in the target language, and — in a port — what changed from the source and why.
6. **Pause** and wait. Hold a cursor (below) so `continue` is unambiguous.

Card format, bridge rules, and worked examples: [references/concept-cards.md](references/concept-cards.md).

## Steering commands

The learner steers with short words; accept natural phrasing too ("I know this", "go deeper", "back to the code").

| Command | Effect |
|---|---|
| `skip` / `skip <concept>` / `skip <family>.*` | Mark known. Never explain it again in any session; no quiz, no "are you sure". Trust the learner. |
| `weeds` / `weeds <concept>` | Descend one level on the weeds ladder for that concept (see below). Repeatable. |
| `surface` | Leave the weeds; return to the exact excerpt and cursor you left from. |
| `load <concept>` | Show the card for a chip you didn't expand. |
| `continue` / `next` | Execute the saved `advance` — the next excerpt or port unit. Never a side path. |
| `compare <lang>` | Re-explain the current concept bridged from a specific language they know. |
| `fly` | Opt into a fluency drill on what was just covered ([references/fluency-drills.md](references/fluency-drills.md)). Only on request. |
| `status` | Show ledger stats for this target: known / loaded / explored / fluent, and what's queued. |

If the learner says `skip` on something a later excerpt shows they misunderstood, don't reopen it unprompted — mention the specific behaviour in one line in context ("note: `struct` here means copy-on-assign") and move on. Their call to go deeper.

## The weeds ladder

Every concept can be descended one rung at a time. Each `weeds` goes exactly one rung deeper, then pauses:

1. **Load** — the card: what it is, bridge, where it is in this code, one trap.
2. **Semantics** — the precise rules: what the compiler accepts/rejects, what it lowers to, defaults, interaction with neighbouring features.
3. **Machinery** — what actually happens at runtime: generated code / IL, allocation, GC, scheduling, JIT/AOT effects. Show it concretely where you can (decompiled lowering, a tiny program and its output) and label it illustrative.
4. **Edges** — pitfalls, version differences, things that compile but are wrong, how this fails in production.
5. **Idiom & ecosystem** — what an experienced reviewer in this language would say: conventions, analyzers, library choices, when *not* to use it.

Pitch every rung at a senior engineer: lead with the precise statement, use their languages' vocabulary (ownership, erasure, RAII, event loop, vtables) as shorthand, and skip anything that's universal across languages. Past rung 5, follow the learner's questions wherever they go — that's the point of the weeds.

## Cursor discipline

Before every pause, hold a cursor in session memory:

- `location`: mode, port unit or file, current excerpt range, weeds depth if any.
- `advance`: the single concrete next step that bare `continue` performs.

`weeds`, `load`, `compare`, and clarifying questions are detours: push the cursor, answer, and restore it. Only an explicit new destination ("switch to the transport code", "port the next tool") changes `advance`. When a detour could make the route ambiguous, end with one breadcrumb line: "Back at `ToolRegistry.cs:40-62`; `continue` shows the registration test."

## Ledger

The ledger is per learner and per target language — not per repo — because fluency carries across repos. Update it as you go, batched rather than one call per sentence:

- `ledger.py mark --lang <t> <concept-id> known` on `skip`.
- `ledger.py mark --lang <t> <concept-id> loaded --anchor <path:lines>` after a card.
- `ledger.py mark --lang <t> <concept-id> explored --depth <n>` after weeds rung ≥ 2.
- `ledger.py mark --lang <t> <concept-id> fluent` only after the learner passes a drill on it.
- `ledger.py question --lang <t> "<question>"` for open questions you couldn't settle.

Use the stable concept ids from the language pack (e.g. `async.valuetask`, `types.nrt`) so progress lines up across sessions and repos. Mark checkpoints after a meaningful segment, at a pause, or on topic switch — never before answering the learner. Storage lives under `${XDG_DATA_HOME:-~/.local/share}/trinity-helicopter-program/` and never in the repo. Run `ledger.py --help` for all commands.

## Pausing or finishing

Give a short debrief: concepts loaded this session (as ids with one-line reminders), what they skipped, open questions, and the exact resume point. Save the ledger. Offer one natural next step (continue the port, a drill on the session's top concept, or a weeds dive they deferred).

## Boundaries

- Teaching never degrades the port. Choose constructs for the port on engineering merit, never because they're easier to teach. If a learner's question surfaces a better construct, propose it as a port change; don't silently switch.
- Don't assign homework or "go read file X". Read and show it yourself.
- Ground claims in the actual code and the project's pinned versions (target framework, package versions). When a feature depends on language/runtime version, say which and check the project file.
- Keep turns readable at chat width. Don't narrate tool calls or ledger bookkeeping.
- Works in any harness: everything here needs only file reading, a shell, and `python3`. If the harness can render Mermaid or inline widgets, a small diagram is welcome for flow-heavy concepts (async state machines, DI lifetimes, middleware pipelines); otherwise use a compact table.
