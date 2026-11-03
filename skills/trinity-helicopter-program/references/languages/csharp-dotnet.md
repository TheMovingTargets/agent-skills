# Language pack: C# / .NET

Concept catalog for teaching C# on modern .NET (8+) to engineers fluent in other languages. Ids are stable: use them in the ledger. Each row gives the nearest analog and the trap most likely for someone arriving from it. This is a map, not the curriculum — teach only what the code in front of you uses.

Always check the project's `<TargetFramework>`, `<LangVersion>`, `<Nullable>`, and package versions before claiming a feature exists; several rows below are version-dependent (noted).

## Contents

1. Project & toolchain (`proj.*`)
2. Types & language core (`types.*`, `lang.*`)
3. Async & concurrency (`async.*`)
4. Resources & memory (`resources.*`, `mem.*`)
5. Errors (`errors.*`)
6. Collections & LINQ (`linq.*`)
7. Hosting: DI, config, logging, ASP.NET Core (`host.*`, `web.*`)
8. Serialization (`json.*`)
9. Attributes, reflection, generators, AOT (`attrs.*`)
10. Testing (`test.*`)
11. MCP C# SDK (`mcp.*`)
12. Containers & deployment (`deploy.*`)
13. Suggested load order for a TS/Python → C# MCP port

## 1. Project & toolchain

| id | concept | nearest analog | trap |
|---|---|---|---|
| `proj.csproj` | SDK-style `.csproj`: MSBuild XML, globs all `*.cs` by default | `Cargo.toml` / `package.json` + build tool | No file list to maintain; but properties/targets are MSBuild, evaluated in order, and can be overridden from `Directory.Build.props` up the tree |
| `proj.dotnet-cli` | `dotnet new/build/run/test/publish/add package` | `cargo` | `dotnet run` builds Debug; `publish` is the deployable output |
| `proj.nuget` | `<PackageReference>`; central versions via `Directory.Packages.props` | crates.io / npm | Transitive versions resolve to lowest applicable, not latest |
| `proj.tfm` | Target framework moniker `net8.0`, `net9.0` | Rust edition + MSRV, roughly | Language version follows the TFM by default; features "missing" are usually a TFM issue |
| `proj.solution` | `.sln` / `.slnx` groups projects; project references form the DAG | Cargo workspace | One assembly per project; `internal` = assembly-private |
| `proj.implicit-usings` | `<ImplicitUsings>` + `global using` | prelude | Names in scope you never imported |
| `proj.top-level` | Top-level statements in `Program.cs` | script-style `main` | Only one file may do it; `args` is implicit |
| `proj.warnings` | `<Nullable>enable`, `<TreatWarningsAsErrors>`, Roslyn analyzers, `.editorconfig` | clippy `-D warnings` | Nullability is only as good as the warnings you don't suppress |

## 2. Types & language core

| id | concept | nearest analog | trap |
|---|---|---|---|
| `types.value-vs-ref` | `struct` (value) vs `class` (reference) | C++ value vs heap object; Java has only the latter | Struct copies; boxing when cast to `object`/interface |
| `types.record` | `record` / `record struct`: value equality, `with` expressions, positional ctor | Kotlin data class, Rust `#[derive(PartialEq, Clone)]` | `record` is still a reference type; `with` is a shallow copy |
| `types.nrt` | Nullable reference types: `string?`, `!` suppression | TS `strictNullChecks`; *not* Rust `Option` | Annotations only — no runtime check; deserializers can still hand you null |
| `types.properties` | `{ get; set; }`, `init`, `required`, computed `=>` | Java getters/setters, TS accessors | Properties are methods; struct property returns a copy |
| `types.primary-ctor` | Primary constructors on classes (C# 12) | TS parameter properties | Parameters are captured, not fields — mutable and no `readonly` |
| `types.generics` | Reified generics, constraints `where T : class, new()` | Java generics without erasure; Rust trait bounds | `List<int>` is a distinct type at runtime; no specialization tricks like C++ |
| `types.interfaces` | Interfaces with default and static abstract members | Java interfaces, Rust traits (partly) | No implementing interfaces for types you don't own (no orphan-impl equivalent) — extension methods instead |
| `types.enums` | `enum`, `[Flags]` | C/C++ enums | Not sum types; any int casts in. Use records + pattern matching for ADTs |
| `lang.patterns` | `is`, `switch` expressions, property/list/relational patterns | Rust `match`, TS narrowing | Exhaustiveness is a warning, not an error, and not checked for class hierarchies |
| `lang.delegates` | `Func<>`, `Action<>`, lambdas, closures, `event` | Java functional interfaces, TS function types | Closures capture variables, not values |
| `lang.extension-methods` | `static` methods with `this` param, appear as instance methods | Rust extension traits, Kotlin extensions | Resolved statically by imported namespace — invisible until you see the `using` |
| `lang.strings` | Interpolation `$"..."`, raw `"""..."""`, `StringBuilder`, `Span`-based APIs | template literals, Rust `format!` | Interpolated strings in logging calls defeat structured logging (see `host.logging`) |
| `lang.var` | `var` local type inference | Rust `let`, TS `const` | Inference is local only; no inference across method signatures |
| `lang.collection-expr` | `[1, 2, ..rest]` (C# 12) | JS array spread | Target-typed: same syntax makes array, list, or span |
| `lang.file-scoped-ns` | `namespace X;` | Rust `mod` per file, roughly | Namespaces ≠ assemblies ≠ folders (only by convention) |
| `lang.static-readonly` | `const` vs `static readonly` | C++ `constexpr` vs `static const` | `const` is baked into callers at compile time |

## 3. Async & concurrency

| id | concept | nearest analog | trap |
|---|---|---|---|
| `async.task` | `Task`/`Task<T>`, `async`/`await` | JS `Promise`, Rust `Future` | Tasks are hot (already running); continuations resume on the thread pool, not an event loop |
| `async.state-machine` | Compiler lowers `async` methods to a state machine | Rust's generated `Future` | Each `await` may resume on a different thread; thread-local state doesn't follow |
| `async.valuetask` | `ValueTask<T>` to avoid allocation on sync completion | — | Await it exactly once; don't store or await twice |
| `async.cancellation` | `CancellationToken` passed explicitly | `AbortSignal` | Cooperative only; ignored tokens mean un-cancellable work. Pass it on, always |
| `async.async-void` | `async void` | TS `async` arrow with unhandled rejection | Exceptions crash the process; only for event handlers |
| `async.sync-over-async` | `.Result`, `.Wait()`, `GetAwaiter().GetResult()` | `block_on` | Thread-pool starvation, deadlocks under sync contexts. Async all the way |
| `async.configureawait` | `ConfigureAwait(false)` | — | Matters in libraries and UI apps; mostly noise in ASP.NET Core |
| `async.async-enumerable` | `IAsyncEnumerable<T>`, `await foreach`, `yield return` | async generators, Rust `Stream` | Pass `[EnumeratorCancellation]` token or it can't be cancelled |
| `async.parallel` | `Task.WhenAll`, `Parallel.ForEachAsync`, `Channel<T>`, `SemaphoreSlim` | `Promise.all`, tokio mpsc/Semaphore | Real parallelism: shared mutable state needs `lock`/`Interlocked`/concurrent collections |
| `async.lock` | `lock`, `Monitor`, `SemaphoreSlim` for async | `Mutex` | Can't `await` inside `lock`; use `SemaphoreSlim.WaitAsync` |

## 4. Resources & memory

| id | concept | nearest analog | trap |
|---|---|---|---|
| `resources.idisposable` | `IDisposable`, `Dispose()` | Rust `Drop`, Java `AutoCloseable` | Not automatic — forgetting `using` leaks until finalization (maybe never) |
| `resources.using` | `using (...) {}` and `using var x = ...;` | try-with-resources; Rust scope drop | `using var` disposes at end of the enclosing scope, not the statement |
| `resources.await-using` | `IAsyncDisposable`, `await using` | async drop (which Rust lacks) | Plain `using` on an async-disposable blocks |
| `mem.gc` | Generational GC, LOH, finalizers | JVM GC | Finalizers are a safety net, not destructors; don't rely on timing |
| `mem.span` | `Span<T>`, `Memory<T>`, `ref struct`, `stackalloc` | Rust slices (without borrow checker), C++ `std::span` | `Span` can't cross `await` or live on the heap; that's the compiler enforcing what a borrow checker would |
| `mem.pooling` | `ArrayPool<T>`, `ObjectPool` | arena/pool allocators | Return what you rent; don't use after return |

## 5. Errors

| id | concept | nearest analog | trap |
|---|---|---|---|
| `errors.exceptions` | Unchecked exceptions, `try/catch/finally` | Java (but no checked exceptions), Python | Nothing in the signature tells you what throws |
| `errors.rethrow` | `throw;` vs `throw ex;` | — | `throw ex;` resets the stack trace |
| `errors.filters` | `catch (X e) when (cond)` | Rust match guards | Filter runs before unwinding — good for logging without catching |
| `errors.guards` | `ArgumentNullException.ThrowIfNull`, `ArgumentException.ThrowIfNullOrEmpty` | `assert!`/precondition helpers | — |
| `errors.result-style` | Result/OneOf-style returns for expected failures | Rust `Result` | Not built in; teams differ. Check what this codebase does and follow it |

## 6. Collections & LINQ

| id | concept | nearest analog | trap |
|---|---|---|---|
| `linq.ienumerable` | `IEnumerable<T>` lazy sequences, `yield return` | Rust `Iterator`, Python generators | Re-enumerated on every pass — side effects and queries run again |
| `linq.methods` | `Where/Select/SelectMany/GroupBy/ToList/ToDictionary` | Rust iterator adapters, JS array methods | Lazy until materialized (`ToList()`, `foreach`, `Count()`) |
| `linq.query-syntax` | `from x in xs where ... select ...` | SQL, Python comprehensions | Same thing as method syntax; teams usually pick one |
| `linq.iqueryable` | `IQueryable<T>` translated to SQL (EF Core) | query builders | Mixing in a non-translatable method throws or pulls the whole table client-side |
| `linq.collections` | `List<T>`, `Dictionary<K,V>`, `HashSet<T>`, `IReadOnlyList<T>`, immutable/frozen collections | `Vec`, `HashMap` | Expose read-only interfaces; `IReadOnlyList` isn't immutable, just a view |

## 7. Hosting: DI, config, logging, ASP.NET Core

| id | concept | nearest analog | trap |
|---|---|---|---|
| `host.generic-host` | `Host.CreateApplicationBuilder(args)` → services, config, logging, lifetime | NestJS app bootstrap, Spring Boot | Everything is wired through the builder before `Build()`; after that the container is fixed |
| `host.di` | `IServiceCollection`, constructor injection | Spring DI, NestJS providers | DI is the default way to get dependencies — `new`-ing services bypasses config and lifetimes |
| `host.di-lifetimes` | Singleton / Scoped / Transient | Spring scopes | Injecting a scoped service into a singleton ("captive dependency") — caught only with scope validation on |
| `host.config` | `IConfiguration`: `appsettings.json` + `appsettings.{Env}.json` + env vars (`A__B`) + user-secrets | dotenv + config libs | Env var `__` maps to `:` sections; later providers override earlier |
| `host.options` | `IOptions<T>`, `IOptionsMonitor<T>`, validation | typed config structs | Bind once, validate on start (`ValidateOnStart`) or fail late |
| `host.logging` | `ILogger<T>`, message templates, `[LoggerMessage]` source-gen | `tracing`, pino/winston | Use templates (`"Got {Count}", n`), not interpolation. **stdio MCP servers must log to stderr**, never stdout |
| `host.background` | `IHostedService`, `BackgroundService` | worker threads / tokio tasks | Unhandled exception stops the host (default .NET 6+) |
| `web.minimal-api` | `WebApplication`, `app.MapGet/MapPost`, route handlers with injected params | Express/Fastify, axum | Parameters bind from route/query/body/DI by convention — know which |
| `web.middleware` | `app.Use...` pipeline order | Express middleware, tower layers | Order matters (auth before endpoints, etc.) |
| `web.httpclient` | `IHttpClientFactory`, typed clients, `AddHttpClient<T>` | axios instance, reqwest Client | `new HttpClient()` per call exhausts sockets; long-lived singletons miss DNS changes — use the factory |
| `web.auth` | Authentication/authorization handlers, Entra ID via `Microsoft.Identity.Web` | passport / middleware | Authentication ≠ authorization; both must be registered and ordered |

## 8. Serialization

| id | concept | nearest analog | trap |
|---|---|---|---|
| `json.stj` | `System.Text.Json`: `JsonSerializer`, `JsonSerializerOptions`, `JsonNode`/`JsonElement` | serde, `JSON.parse` + zod | Default is case-sensitive PascalCase unless options set camelCase (ASP.NET Core sets web defaults) |
| `json.attributes` | `[JsonPropertyName]`, `[JsonIgnore]`, `[JsonRequired]` | serde attributes | Missing properties deserialize to default, not error, unless required |
| `json.source-gen` | `JsonSerializerContext` source generation | serde derive | Needed for trimming/Native AOT; every type must be registered |
| `json.polymorphism` | `[JsonPolymorphic]`, `[JsonDerivedType]` | serde tagged enums | Opt-in; base-typed values otherwise lose derived fields |

## 9. Attributes, reflection, generators, AOT

| id | concept | nearest analog | trap |
|---|---|---|---|
| `attrs.basics` | Attributes `[Foo]` as metadata on types/members/params | Java annotations, Python decorators (metadata only), Rust attributes | Attributes do nothing by themselves; something reads them (reflection or a generator) |
| `attrs.reflection` | `Type`, `GetMethods`, assembly scanning | Java reflection | Breaks under trimming/AOT unless annotated |
| `attrs.source-generators` | Roslyn source generators emit code at compile time | Rust proc macros | Generated code lives in `obj/`; find it via the IDE or `EmitCompilerGeneratedFiles` |
| `attrs.aot` | Trimming and Native AOT publish | static Rust binary | Reflection-heavy libraries need source-gen modes or warnings become runtime failures |

## 10. Testing

| id | concept | nearest analog | trap |
|---|---|---|---|
| `test.xunit` | xUnit `[Fact]`, `[Theory]` + `[InlineData]` | Jest `test`/`test.each`, pytest parametrize | New class instance per test; shared setup via constructor or fixtures |
| `test.fixtures` | `IClassFixture<T>`, `ICollectionFixture<T>`, `IAsyncLifetime` | pytest fixtures | Collections also control parallelism |
| `test.mocking` | NSubstitute / Moq on interfaces | jest.mock, mockall | You can only mock virtual/interface members — another reason for interfaces in DI |
| `test.webappfactory` | `WebApplicationFactory<Program>` in-memory server | supertest | Needs `public partial class Program` or InternalsVisibleTo with top-level statements |

## 11. MCP C# SDK

Verify every API name against the `ModelContextProtocol*` package version actually referenced; the SDK has moved quickly. Read the package's README/XML docs or decompile if in doubt.

| id | concept | source-side analog (TS SDK) | trap |
|---|---|---|---|
| `mcp.host-setup` | `builder.Services.AddMcpServer()` + transport + tool registration | `new McpServer(...)` + `server.connect(transport)` | It's DI-registered; tools get dependencies through DI, not closures |
| `mcp.stdio` | `.WithStdioServerTransport()` | `StdioServerTransport` | Anything written to stdout corrupts the protocol — route logs to stderr |
| `mcp.http` | `ModelContextProtocol.AspNetCore`: `.WithHttpTransport()` + `app.MapMcp()` | Streamable HTTP transport + Express | Now an ASP.NET Core app: middleware, auth, and hosting rules apply |
| `mcp.tool-attributes` | `[McpServerToolType]` class, `[McpServerTool]` method, `[Description]` | `server.tool(name, zodSchema, handler)` | JSON Schema is generated from parameter types and descriptions — the C# types *are* the schema |
| `mcp.tool-di-params` | Tool params injected from DI / request context (`CancellationToken`, server, services) vs bound from arguments | handler `extra` arg | Know which params the model sees in the schema and which come from DI |
| `mcp.discovery` | `.WithToolsFromAssembly()` vs `.WithTools<T>()` | explicit registration | Reflection scan — consider explicit registration for trimming/AOT |
| `mcp.results` | Return types → content blocks (string, structured content, `CallToolResult`) | returning `{ content: [...] }` | Return shapes affect what the client renders; match the source's content types |
| `mcp.resources-prompts` | Resource/prompt attributes and handlers | `server.resource` / `server.prompt` | URI templates and MIME types must match the source exactly for clients to keep working |
| `mcp.ui-resources` | MCP Apps UI: tools linking to `ui://` HTML resources | TS MCP Apps helpers | Port the metadata linkage (tool → UI resource) precisely; HTML/JS assets usually move unchanged — check how they're embedded (`EmbeddedResource`, files) |

## 12. Containers & deployment

| id | concept | nearest analog | trap |
|---|---|---|---|
| `deploy.publish` | `dotnet publish -c Release`, framework-dependent vs self-contained | `cargo build --release` | Self-contained needs a RID (`-r linux-x64`) |
| `deploy.dockerfile` | Multi-stage: `mcr.microsoft.com/dotnet/sdk` build → `aspnet` or `runtime` (or `runtime-deps` for self-contained/AOT) | node multi-stage builds | Copy `.csproj` and restore first for layer caching; match image to the app type |
| `deploy.sdk-containers` | `dotnet publish /t:PublishContainer` without a Dockerfile | Jib, ko | Different knobs from Dockerfiles; check which the repo uses |
| `deploy.aot` | Native AOT: fast start, small image, no JIT | static Go/Rust binary | Reflection/JSON/DI patterns must be AOT-safe; heed trim warnings |
| `deploy.config` | `ASPNETCORE_URLS`/`ASPNETCORE_HTTP_PORTS`, `DOTNET_ENVIRONMENT` | `PORT`, `NODE_ENV` | Default port is 8080 in .NET 8+ container images |

## 13. Suggested load order for a TS/Python → C# MCP port

Teach in the order the port meets them, not this list's order. For a typical port the first unit (scaffold + host + one tool) meets roughly:

`proj.csproj` → `proj.dotnet-cli` → `proj.top-level` → `host.generic-host` → `host.di` → `mcp.host-setup` → `mcp.stdio` → `host.logging` → `mcp.tool-attributes` → `attrs.basics` → `async.task` → `async.cancellation` → `types.nrt`

then tests (`test.xunit`, `test.mocking`), then whatever the remaining tools need (`json.*`, `web.httpclient`, `linq.*`, `types.record`), then deployment (`deploy.*`). Expect most cards in the first two units and mostly chips afterwards.
