# Research: xAPI statements as the Evidence format

Question (issue #15): can xAPI 2.0 statements serve as the **Evidence** format, stored as append-only JSON lines in the **Profile Repo** with no Learning Record Store (LRS)? If so, what is the minimal profile: verbs, IRIs for Concepts and Areas, where Harness and Language go, and which parts of xAPI to drop? Constraint: Evidence names nothing more specific than Dimension, Language, Area, Harness and Concept, and never the repository.

Terms in **bold** are from `GLOSSARY.md`.

## Answer

**Yes.** The xAPI 2.0 Statement data model works on its own as a file format. A JSON Lines file of Statements is valid xAPI *data*, but it is not an xAPI *system*: conformance is defined for LRSs and for clients talking to an LRS, and neither applies to a file in git. The Evidence format can be a narrow subset of xAPI 2.0:

- **actor**: the developer as an `account` (**Home Provider** origin + login). That is a **Linked Identity**, not a repository.
- **verb**: six verbs, reused where an existing IRI fits, plus one coined verb (`practiced`).
- **object**: always an Activity whose id is a **Concept** IRI.
- **context.contextActivities.category**: the **Language**, **Harness** and **Area**(s) as Activities, plus the profile version IRI.
- **context.extensions**: one key holding the **Dimension**.
- **result**: only `success`, `completion` and `score.scaled`.
- **id** and **timestamp** are required. Everything else is dropped.

Two traps to avoid. `context.language` is a natural-language tag (RFC 5646, like `en`), **not** a programming language. And the profile version should **not** go in `category` until the profile defines Patterns, because the profile spec then requires every such Statement to follow one.

## 1. Can Statements live outside an LRS?

- The standard defines an LRS as "a server ... responsible for receiving, storing, and providing access to Learning Records", and a Statement as "a data structure showing evidence for any sort of experience or event" ([9274.1.1 Overview §3.1][ov]). The Statement is defined as data. Nothing says it is only valid while inside an LRS.
- The Statement rules are written for the **Learning Record Provider** (LRP), the component that creates Statements ([9274.1.1 Content §5.2][content]). The skills that write Evidence act as the LRP. They can follow every LRP data rule while writing to a file instead of `POST /statements`.
- What we lose by having no LRS:
  - The LRS-set fields `stored` and `authority` ([Content §5.2.2][content]).
  - The query API and the document resources (State, Agent Profile, Activity Profile) ([Content §5.1.6][content]).
  - Server-side validation and voiding enforcement.

  None of these is needed to derive **Proficiency** and **Currency** from a local file.
- **Path to an LRS later stays open.** `POST /statements` accepts "an array of Statements" ([Content §5.1.6.1][content]). An LRS "shall not make any modifications to its state based on receiving a Statement with a statementId that it already has" ([9274.1.1 LRSs §4.1.6.1][lrs]). So if every line carries its own UUID, replaying the file into any LRS is idempotent.
- **Append-only fits xAPI's model.** "Statements are expected to be unique and to be immutable ... and should not be deleted" ([Content §5.2.4][content]). Corrections use a voiding Statement (verb `http://adlnet.gov/expapi/verbs/voided`, object a `StatementRef`), never an edit ([Content §5.2.5][content]). So a wrong Evidence line is cancelled by appending another line, and the file stays append-only.
- **Git sync:** one Statement per line means concurrent appends from two machines merge cleanly with git's built-in `union` merge driver, which takes "lines from both versions" ([gitattributes][gitattr]). Choosing that is the Profile Repo layout ticket's call. This only notes that JSON Lines allows it.

**Do not claim "xAPI conformant"** for the Profile Repo. Say "Evidence lines are xAPI 2.0 Statements". The spec allows deliberate deviation and asks implementers to weigh interoperability ([Content §5.1.9][content]), but nothing here needs to deviate.

## 2. Rules the format must keep (from the LRP data requirements)

From [Content §5.2.1, §5.2.4.1, §5.2.7][content]:

- **No extra properties.** "An LRP shall not add additional properties to Statements." Anything ours, such as Dimension, goes in `extensions`, whose keys "shall be IRIs".
- No `null` values (except inside extensions), no empty objects, no empty strings, and no property used twice.
- `contextActivities` values should be arrays of Activity objects.
- `timestamp` must be RFC 3339 / ISO 8601, in UTC, and not in the future. Millisecond precision is a *should*, "if used".
- `version` is *not recommended*. If it is set, it must be `2.0.0`.
- `stored` and `authority` are for the LRS. The LRP *should not* set them.
- IRIs we coin should be under a namespace we control and should be lowercase. Reuse an existing identifier "where a suitable identifier already exists". Anchors (`...#verb`) are allowed.

## 3. Minimal profile

### 3.1 Statement shape

| Property | Keep? | Evidence rule | Why |
| --- | --- | --- | --- |
| `id` | **Required** (spec: Recommended) | UUID v4, set by the skill | Dedupe on sync and idempotent LRS replay. Voiding needs a target. |
| `actor` | **Required** | Agent with `account: { homePage: <Home Provider origin>, name: <login> }` | Exactly one identifier is required ([Content §5.2.2.1][content]). An `account` *is* a **Linked Identity**. `mbox` would put an email address in the file. |
| `verb` | **Required** | `id` from §3.2. `display` with `en` only. | `display` is Recommended. It never changes meaning. |
| `object` | **Required** | Activity: `{ "objectType": "Activity", "id": <Concept IRI> }`, with no `definition` | Definitions are hosted in the profile's vocabulary instead ([Content §5.2.3][content]). The profile spec says to either omit the definition or include all of it ([Profiles §7.4][prof]). |
| `result` | Optional | Only `success`, `completion` and `score.scaled`. No `response`, `duration` or `extensions`. | `response` can carry the learner's answer text, which breaks "no learner questions". `duration` reveals working patterns (see §5). |
| `context` | **Required** | Only `contextActivities.category` and `extensions` (§3.3). | |
| `timestamp` | **Required** (spec: Optional) | UTC. The default precision is still open (see §5). | **Currency** is derived from it. |
| `stored`, `authority`, `version` | Drop | | LRS-owned or not recommended for an LRP ([Content §5.2.4.1][content]). |
| `attachments` (and Statement signing) | Drop | | Signed credentials are out of scope for the map. Attachments would carry artifacts. |
| `context.registration` | Drop | | Only needed for profile Patterns (see §3.4). A per-session UUID adds linkability and no signal. |
| `context.instructor`, `team`, `contextAgents`, `contextGroups` | Drop | | No other people belong in Evidence. 2.0 itself deprecates `instructor` and `team` ([Content §5.2.2.5][content]). |
| `context.contextActivities.parent`, `grouping`, `other` | Drop | | In practice these name a course, lesson or repository (the "where"), which is exactly what Evidence must never say. |
| `context.platform` | Drop | | A free string, not an IRI. Harness is carried as an Activity in `category` instead (§3.3). |
| `context.language` | **Drop. Never use it for Language.** | | It is "Code representing the language in which the experience ... occurred", an RFC 5646 tag, and invalid values are forbidden ([Content §5.2.2.5, §5.2.4.1][content]). |
| `context.revision`, `context.statement` | Drop | | |
| `object` as Agent, `StatementRef` (except in voiding) or `SubStatement` | Drop | | |
| Interaction Activities (`interactionType`, `choices`, ...) | Drop | | These carry question and choice text. |

### 3.2 Verb set

Reuse established IRIs where the meaning fits. Coin only the one that does not exist.

| Learning event | Verb IRI | Source and definition | Result |
| --- | --- | --- | --- |
| **shown** (the skill taught or explained the Concept) | `http://adlnet.gov/expapi/verbs/experienced` | ADL Vocabulary: "the actor only encountered the object ... where a specific achievement or completion is not required" ([adl.jsonld][adl]) | none |
| **explored** (the developer dug deeper or asked follow-ups) | `http://adlnet.gov/expapi/verbs/interacted` | ADL Vocabulary: "the actor engaged with a physical or virtual object" ([adl.jsonld][adl]). `asked` is the alternative if "explored" means "asked about". | none |
| **drilled** (did a practice exercise) | **coined:** `{ns}/verbs/practiced` | Nothing in the ADL, cmi5, Activity Streams, AcrossX or Tin Can registries means "practiced" ([ADL profiles repo][profiles-repo]). `attempted` only means "made an effort to access the object" ([adl.jsonld][adl]). | `success`, optional `score.scaled` |
| **assessed: passed** (teach-back or assessment gate met) | `http://adlnet.gov/expapi/verbs/passed` | cmi5 §9.3.4 ([cmi5 spec][cmi5]) | `success: true`, optional `score.scaled` |
| **assessed: failed** | `http://adlnet.gov/expapi/verbs/failed` | cmi5 §9.3.5 ([cmi5 spec][cmi5]) | `success: false`, optional `score.scaled` |
| **used** (applied the Concept in real work, including a Harness feature) | `http://activitystrea.ms/use` | Activity Streams profile: "the actor has used the object in some manner" ([activity-streams.jsonld][as]) | optional `completion` |
| (correction) | `http://adlnet.gov/expapi/verbs/voided` | Reserved by the standard. The object must be a `StatementRef` ([Content §5.2.5][content]). | none |

The coined verb is published in the profile document (§3.4) as a `Verb` concept with `prefLabel` and `definition`, and with `broadMatch: ["http://adlnet.gov/expapi/verbs/attempted"]` ([Profiles §7.1][prof]).

Leave `mastered` out ("the highest level of comprehension", [adl.jsonld][adl]). Mastery is a **Proficiency** judgment derived from Evidence. If a skill recorded it, the summary would be stored as if it were Evidence.

### 3.3 IRIs and where Harness, Language, Area and Dimension go

**Namespace `{ns}`.** Use a path the skills' maintainers control, for example the public skills repo's GitHub Pages site, or a `https://w3id.org/xapi/<profile-name>/` permanent redirect. `w3id.org/xapi/` is where the ADL, cmi5 and AcrossX profiles are rooted ([adl.jsonld][adl], [cmi5.jsonld][cmi5-ld]). The IRIs do not have to resolve ([Content §5.2.7][content]). Hosting a human-readable page plus JSON metadata at each IRI is a *should* ([Content §5.2.3.1][content]).

| Term | IRI pattern | Carried in | Activity type |
| --- | --- | --- | --- |
| **Concept** | `{ns}/concepts/<slug>`, e.g. `.../concepts/async-await` | `object.id` | `{ns}/activitytypes/concept` |
| **Language** | `{ns}/languages/<slug>`, e.g. `.../languages/csharp` | `context.contextActivities.category[]` | `{ns}/activitytypes/language` |
| **Harness** | `{ns}/harnesses/<slug>`, e.g. `.../harnesses/claude-code` | `context.contextActivities.category[]` | `{ns}/activitytypes/harness` |
| **Area** | `{ns}/areas/<slug>`, e.g. `.../areas/backend` (zero or more) | `context.contextActivities.category[]` | `{ns}/activitytypes/area` |
| **Dimension** | value `"language"` or `"harness"` | `context.extensions["{ns}/extensions/dimension"]` | (context extension) |

Why each goes where it does:

- **`category` for Language, Harness and Area.** The spec defines category as "an Activity used to categorize the Statement. 'Tags' would be a synonym" ([xAPI 1.0.3 Data, Context Activities][ctx103]; 2.0 keeps the same four keys, [Content §5.2.2.5][content]). Area and Concept are already "cross-cutting tags" on the map, so this matches. Carrying them as Activities also gives each one an IRI, a type and a hosted definition, which `platform` (a free string) cannot.
- **Concept stays generic and Language is separate.** Keep Concepts like `async-await` language-neutral, and say which Language through `category`. Then the same Concept seen in two Languages shows up as transfer instead of two unrelated ids. This is what the glossary means by "never specific to a repository" and "a shared vocabulary". A Concept that only exists in one ecosystem still gets a neutral slug.
- **Coin Language IRIs instead of reusing Wikidata.** The spec prefers existing identifiers when they are suitable ([Content §5.2.7][content]). But a Wikidata item (for example `http://www.wikidata.org/entity/Q2370`, C#) names the language alone. The glossary's **Language** is the language *plus its ecosystem*, so the meanings differ. Coin our own IRI, and put the Wikidata IRI in the hosted definition.
- **Dimension as an extension.** It is not a tag: there is exactly one per Statement, and it decides which ledger the Evidence counts toward. It could be inferred (a Concept typed as a Harness feature implies Harness), but an explicit value keeps derivation simple. Extensions are the only legal place for it, because LRPs may not add properties ([Content §5.2.1][content]). The extension is declared as a `ContextExtension` with an inline JSON Schema `{"enum": ["language","harness"]}` ([Profiles §7.2][prof]).
- **Repository identity has no slot.** Once `parent`, `grouping`, `other`, `platform`, `revision`, `registration`, `attachments`, `result.response` and Activity `definition` are dropped, nothing in a Statement can hold a repo name, path or code. A validator only has to check that every IRI in `object.id` and `category` is in the profile vocabulary.

### 3.4 The profile document

Publish the vocabulary as an xAPI Profile (JSON-LD, `conformsTo: https://w3id.org/xapi/profiles#1.0`) ([Profiles §6][prof]). It contains:

- `Verb` concept: `practiced`.
- `ActivityType` concepts: `concept`, `language`, `harness`, `area`.
- One `Activity` concept per Concept, Language, Harness and Area. This is the canonical definition with `name` and `description` ([Profiles §7.4][prof]).
- `ContextExtension`: `dimension`.

Statement Templates (§8) are optional and useful as a validator. **Do not define Patterns, and do not put the profile version IRI in `category` yet.** Once a Statement has the profile in its category activities, the LRP "MUST follow a Pattern from a Profile for every Statement" and all such Statements must share a `registration` ([Profiles §9][prof]). Those constraints only make sense for sequenced courses. The spec's guidance that category "SHOULD be used to indicate a profile" ([xAPI 1.0.3][ctx103]) is a *should*, so leaving it out still conforms. Add it later only if Patterns ever exist.

### 3.5 Example line

```json
{"id":"6f1c2a9e-3b7d-4c11-9a0e-2d5f8b7c4e10","actor":{"objectType":"Agent","account":{"homePage":"https://github.com","name":"octocat"}},"verb":{"id":"http://adlnet.gov/expapi/verbs/passed","display":{"en":"passed"}},"object":{"objectType":"Activity","id":"https://example.org/xapi/devprof/concepts/async-await"},"result":{"success":true,"score":{"scaled":0.8}},"context":{"contextActivities":{"category":[{"id":"https://example.org/xapi/devprof/languages/csharp"},{"id":"https://example.org/xapi/devprof/harnesses/claude-code"},{"id":"https://example.org/xapi/devprof/areas/backend"}]},"extensions":{"https://example.org/xapi/devprof/extensions/dimension":"language"}},"timestamp":"2026-11-04T00:00:00.000Z"}
```

(`example.org` stands in for `{ns}`.)

## 4. What is dropped from full xAPI, in one list

The whole REST API and its headers (`X-Experience-API-Version`, concurrency, attachments multipart). The State, Agent Profile, Activity Profile, Agents, Activities and About resources. `stored`, `authority`, `version`. `attachments` and signing. SubStatements, `StatementRef` (except in voiding) and Agent objects. Interaction Activities. `registration`, `instructor`, `team`, `contextAgents`, `contextGroups`, `parent`, `grouping`, `other`, `platform`, `language`, `revision`, `context.statement`. `result.response`, `result.duration`, `result.extensions`. Inline Activity `definition`. Profile Patterns and the profile category tag. Sources: [Content §5.1–5.2][content], [Profiles §9][prof].

## 5. Open points for other tickets

- **Timestamp precision (privacy check on the map).** Millisecond timestamps across many lines reveal working hours. Rounding to the day (`...T00:00:00.000Z`) is still a valid RFC 3339 UTC timestamp ([Content §5.2.7][content]) and is probably enough for decay models that work in days. The day-versus-time choice belongs to the privacy and decay tickets.
- **Concept and Area vocabulary governance.** Who adds slugs, and how the two skills agree on them. The profile document is the natural registry.
- **Public Profile Summary.** It should drop `actor` and aggregate rather than publish lines. That is not settled here.
- **Import of existing local data.** Old concept-ledger entries map to `experienced` or `practiced` with back-dated timestamps. The spec only forbids *future* timestamps ([Content §5.2.4.1][content]).

## Sources

- [content]: IEEE 9274.1.1-2023 (xAPI 2.0) source, "xAPI Base Standard for Content". <https://opensource.ieee.org/xapi/xapi-base-standard-documentation/-/blob/main/9274.1.1%20xAPI%20Base%20Standard%20for%20Content.md>
- [lrs]: IEEE 9274.1.1-2023 source, "xAPI Base Standard for LRSs". <https://opensource.ieee.org/xapi/xapi-base-standard-documentation/-/blob/main/9274.1.1%20xAPI%20Base%20Standard%20for%20LRSs.md>
- [ov]: IEEE 9274.1.1-2023 source, "xAPI Base Standard Overview" (definitions). <https://opensource.ieee.org/xapi/xapi-base-standard-documentation/-/blob/main/9274.1.1%20xAPI%20Base%20Standard%20Overview.md>
- [ctx103]: xAPI 1.0.3, Part Two, Context Activities (the fuller definition of parent, grouping, category and other). <https://github.com/adlnet/xAPI-Spec/blob/master/xAPI-Data.md#2462-contextactivities-property>
- [prof]: xAPI Profiles 1.0, Part Two: Document Structure. <https://github.com/adlnet/xapi-profiles/blob/master/xapi-profiles-structure.md>
- [adl]: ADL Vocabulary profile. <https://github.com/adlnet/xapi-authored-profiles/blob/master/adl/adl.jsonld>
- [cmi5]: cmi5 specification, §9.3 Verbs. <https://github.com/AICC/CMI-5_Spec_Current/blob/quartz/cmi5_spec.md>
- [cmi5-ld]: cmi5 profile (JSON-LD). <https://github.com/adlnet/xapi-authored-profiles/blob/master/cmi5/cmi5.jsonld>
- [as]: Activity Streams xAPI profile. <https://github.com/adlnet/xapi-authored-profiles/blob/master/activity-streams/activity-streams.jsonld>
- [profiles-repo]: ADL authored profiles (AcrossX, Tin Can registry and others), searched for a "practiced" verb. <https://github.com/adlnet/xapi-authored-profiles>
- [gitattr]: git, gitattributes, built-in merge drivers (`union`). <https://git-scm.com/docs/gitattributes#_built_in_merge_drivers>

[content]: https://opensource.ieee.org/xapi/xapi-base-standard-documentation/-/blob/main/9274.1.1%20xAPI%20Base%20Standard%20for%20Content.md
[lrs]: https://opensource.ieee.org/xapi/xapi-base-standard-documentation/-/blob/main/9274.1.1%20xAPI%20Base%20Standard%20for%20LRSs.md
[ov]: https://opensource.ieee.org/xapi/xapi-base-standard-documentation/-/blob/main/9274.1.1%20xAPI%20Base%20Standard%20Overview.md
[ctx103]: https://github.com/adlnet/xAPI-Spec/blob/master/xAPI-Data.md#2462-contextactivities-property
[prof]: https://github.com/adlnet/xapi-profiles/blob/master/xapi-profiles-structure.md
[adl]: https://github.com/adlnet/xapi-authored-profiles/blob/master/adl/adl.jsonld
[cmi5]: https://github.com/AICC/CMI-5_Spec_Current/blob/quartz/cmi5_spec.md
[cmi5-ld]: https://github.com/adlnet/xapi-authored-profiles/blob/master/cmi5/cmi5.jsonld
[as]: https://github.com/adlnet/xapi-authored-profiles/blob/master/activity-streams/activity-streams.jsonld
[profiles-repo]: https://github.com/adlnet/xapi-authored-profiles
[gitattr]: https://git-scm.com/docs/gitattributes#_built_in_merge_drivers
