# Language packs

A pack is a concept catalog for one target language, named `<language>[-<platform>].md` (e.g. `csharp-dotnet.md`, `rust.md`, `go.md`, `kotlin-jvm.md`). The skill reads only the pack for the current target.

## When no pack exists

Build the catalog for the current session on the fly, then offer to save it here at the end. Keep the same shape as `csharp-dotnet.md`:

1. A version note: which compiler/runtime/package versions matter and where to check them in a project.
2. Concept families with stable, dotted ids (`family.concept`), lowercase, hyphenated.
3. One table row per concept: id, concept, nearest analog in commonly known languages, and the single most likely trap for someone coming from that analog.
4. An explicit list of **false friends** — syntax that looks familiar but behaves differently.
5. A suggested load order for the most common port into this language.

Keep rows terse. The pack is a map for the tutor, not lesson text; lessons are written fresh against the code on screen.

## Ids are forever

Once a concept id is in a pack and in learners' ledgers, don't rename it — add a new id and keep the old one as an alias line (`old.id → new.id`) at the end of the pack.
