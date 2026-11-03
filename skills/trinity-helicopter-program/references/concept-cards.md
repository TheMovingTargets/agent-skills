# Concept cards, bridges, and chips

Three sizes of teaching, picked per concept per learner. The aim is the smallest one that leaves the learner able to read the line without stalling.

| Size | When | Length |
|---|---|---|
| chip | New, but not central to this excerpt; or the learner may already know it | one line: `` `concept-id` — 6–10 words `` |
| bridge | Near-exact analog exists in a language the learner knows | one sentence |
| card | Genuinely new, or a false friend | ~60–120 words |

## Choosing the bridge language

Pick the analog from the learner's profile that is *closest in behaviour*, not the most popular one. Good defaults when targeting C#/.NET:

- Generics, interfaces, exceptions, GC, annotations → Java (and flag where C# differs: reified generics, unchecked exceptions, value types).
- Ownership-adjacent things: `IDisposable`/`using`, `Span<T>`, `ref struct`, `readonly struct` → Rust (and say plainly that C# has no borrow checker; the guarantees are narrower).
- Value types, operator overloading, destructors-vs-finalizers, templates-vs-generics → C++.
- `async`/`await`, lambdas, structural-ish object shapes, JSON handling → TypeScript/JavaScript (and flag that .NET has a thread pool, not a single event loop).
- Comprehensions, duck typing, decorators → Python (LINQ, interfaces, attributes respectively — usually partial analogs).

A bridge that is only 80% right must name the 20%: "≈ Java `Optional`, except `string?` is a compile-time annotation only — at runtime it's the same `string` and can still be null."

## Card format

```markdown
**`await using` — asynchronous disposal** · `resources.await-using` · new
Bridge: Rust `Drop` at end of scope, but async and opt-in; Java try-with-resources without braces.
Here: `McpHost.cs:18` — the transport is disposed (flushing stdout) when `Main` returns.
Trap: only works on `IAsyncDisposable`; plain `using` on an async resource blocks a thread on dispose.
→ `skip` · `weeds` · `continue`
```

Rules:
- Header: name, stable concept id, and status: `new`, `false friend`, or `revisit` (shown before, learner asked again).
- **Here** always points at the line in the excerpt on screen. A card without an anchor in the real code is a lecture; avoid it.
- **Trap** is one specific failure, not a generic warning. Prefer the trap most likely for someone coming from the bridge language.
- The footer line is the only menu. Don't append other offers.

## False friends get cards even for experts

Syntax that matches a known language but behaves differently is where fluent engineers get burned, so always card these, even if the concept looks trivial. C#/.NET examples:

- `struct` — a value type, copied on assignment and when passed (like a C++ struct by value, unlike any Java object). Mutating a struct you got from a property or a `List<T>` indexer mutates a copy; the original is unchanged.
- `string?` — annotation, not an `Option` type.
- `async void` — legal, but exceptions crash the process; not the TS `async () => {}` it resembles.
- `==` on records vs classes — value equality vs reference equality.
- `readonly` field holding a mutable object — the reference is readonly, the object isn't (Java `final`, not C++ `const`).
- `IEnumerable<T>` LINQ chains — lazy like Rust iterators, but re-enumerated on every pass, re-running side effects and queries.
- `Task` — already running when you get it (hot), unlike a Rust `Future` (inert until polled).

## Worked example — port companion, one excerpt

> Source `src/tools/search.ts:12-24` and target `Acme.Mcp/SearchTools.cs:9-27` shown as two faithful blocks.
>
> Mapping:
>
> | TypeScript | C# | concept |
> |---|---|---|
> | `server.tool("search", schema, handler)` | `[McpServerTool, Description(...)]` on a method | `mcp.tool-attributes` |
> | `z.string().describe(...)` | `[Description("...")] string query` | `attrs.basics` |
> | `async (args) => {...}` | `async Task<string> SearchAsync(...)` | `async.task` |
> | (none) | `CancellationToken ct` parameter | `async.cancellation` |
>
> Bridge: `async Task<string>` ≈ TS `async (): Promise<string>`, but a thread-pool continuation, not the event loop.
>
> Card: `mcp.tool-attributes` (new) …
> Card: `async.cancellation` (new — no TS analog in the source; the SDK supplies it) …
>
> Chips: `types.nrt` — `string?` is a nullability annotation · `lang.file-scoped-ns` — `namespace X;` covers the file
>
> Why the port looks like this: the SDK discovers tools by reflection over attributes, so the zod schema becomes method parameters with `[Description]`, and JSON Schema is generated from the C# types.
>
> → `skip <id>` · `weeds <id>` · `load <chip>` · `continue` (next: `SearchTools.cs:29-48`, the result shaping)

## Repeats

If a concept the ledger shows as `loaded` appears again, use a chip ("`async.cancellation` again — flows into `HttpClient.GetAsync`") unless this occurrence teaches something new, in which case add only the new part. Repetition in context is how fluency forms; re-reading the same card is not.
