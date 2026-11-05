# Architecture Concepts

The Vocabulary of generic architecture patterns that a scored teach-back can record as Evidence in the Proficiency Profile. Each id becomes the Concept IRI `https://w3id.org/xapi/devprof/concepts/arch/<id>`.

Architecture Concepts have no Dimension of their own: they count under the Language they were taught back in.

## Matching a topic to a Concept

- Map a repository topic only onto an id in this table. If nothing fits, record nothing.
- Never invent an id during a session, and never name one after the repository's own frameworks, services or packages.
- A pattern that is missing here is added by a pull request to this file, in generic wording.

## Concepts

| id | concept | typical signs in code |
|---|---|---|
| `layered-architecture` | Layers (presentation, application, domain, data), each calling only the one below | Folders or projects per layer; controllers → services → repositories |
| `hexagonal-ports` | Ports and adapters: the core defines interfaces, adapters plug in the outside world | Interfaces owned by the core; adapters for HTTP, storage, queues |
| `dependency-injection` | Collaborators are passed in rather than constructed | A container or composition root; constructor parameters for services |
| `repository-pattern` | A collection-like interface over persistence | `*Repository` types hiding queries behind domain methods |
| `cqrs` | Separate models or paths for commands (writes) and queries (reads) | Command and query handlers; distinct read models |
| `event-sourcing` | State is derived by replaying an append-only log of events | Event stores, `apply(event)` methods, projections and snapshots |
| `pub-sub` | Publishers emit events to topics; any number of subscribers react | Event buses, topics, subscription handlers |
| `message-queue` | Work is handed off through a durable queue to consumers | Producers and consumers, acknowledgements, dead-letter queues |
| `request-response-api` | A synchronous API where each request gets one response, such as REST or GraphQL | Routes, handlers, status codes, schemas |
| `rpc` | Calling a remote procedure as if it were local | gRPC or JSON-RPC stubs, generated clients |
| `middleware-pipeline` | A request passes through an ordered chain of handlers | `use(...)` registrations, `next()` calls, filters |
| `background-jobs` | Work runs outside the request path, on a schedule or a worker | Hosted services, cron jobs, worker processes |
| `state-machine` | Behavior is governed by explicit states and allowed transitions | State enums, transition tables, guards |
| `plugin-architecture` | The host discovers and loads extensions through a defined contract | Plugin interfaces, registries, manifests |
| `caching` | Keeping computed or fetched results to serve later requests faster | Cache-aside lookups, TTLs, invalidation |
| `retry-backoff` | Retrying failed operations with growing delays | Retry policies, exponential backoff, jitter |
| `idempotency` | Repeating an operation has the same effect as doing it once | Idempotency keys, upserts, deduplication |
| `circuit-breaker` | Stop calling a failing dependency for a while, then probe it | Open, half-open and closed states; fallbacks |

## Ids are forever

Once an id is here and in a Profile Repo, don't rename or remove it. Add the new id as a row and keep the old one as an alias line (`old-id → new-id`) at the end of this file.
