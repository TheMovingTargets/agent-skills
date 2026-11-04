# Developer Proficiency

How the learning skills (Trinity Helicopter Program, Cognitive Reload) record and summarize what a developer can do, across every repository and coding harness they work in.

## Language

### The profile

**Proficiency Profile**:
The single, durable record of one developer's proficiency, built only from Evidence the skills recorded.
_Avoid_: skill profile, CV, resume, portfolio

**Profile Repo**:
The private git repository that holds a developer's Proficiency Profile and is owned by the skills.
_Avoid_: profile repository (that is the host's public `<login>/<login>` repo), ledger repo

**Public Profile Summary**:
An opt-in, sanitized excerpt of the Proficiency Profile published outside the Profile Repo, such as a section of the host's public profile README.
_Avoid_: badge page, public profile

**Home Provider**:
The code host (GitHub, GitLab, Azure DevOps) where a developer's Profile Repo lives.

**Linked Identity**:
One of a developer's accounts on a code host, recorded in the Proficiency Profile so that work done under it counts toward the same profile.
_Avoid_: alias, login (when meaning the person)

### What is measured

**Dimension**:
A kind of proficiency the profile tracks: Language or Harness.

**Language**:
A programming language together with its ecosystem (runtime, standard library, major frameworks), as a Dimension.

**Harness**:
A coding-agent environment the developer works through, such as Claude Code or Codex, as a Dimension.
_Avoid_: tool, IDE, agent

**Concept**:
One generic, named idea from a shared vocabulary, such as a language feature, a harness feature or an architecture pattern, that Evidence is about. Never specific to a repository.
_Avoid_: topic (a Cognitive Reload topic is repository-specific), skill

**Area**:
A broad part of the software stack, such as frontend, backend or infrastructure, that Evidence can be attributed to across all Languages and repositories.
_Avoid_: domain, layer, tier, a Cognitive Reload area (a part of one repository)

**Proficiency**:
How well a developer commands something within a Dimension, judged only from Evidence.
_Avoid_: skill level, rating, score (unless it's a specific assessment score)

**Currency**:
How recently a Proficiency has been exercised, and so how much of it can still be relied on.
_Avoid_: freshness, recency score

**Evidence**:
A dated record of something the developer did or showed during a session, stated only in Dimensions, Areas and Concepts, from which Proficiency and Currency are derived. It never identifies the repository it came from.
_Avoid_: activity, log entry, self-assessment, evidence ledger (Cognitive Reload's record of what the agent inspected)

**HITL Cognition Artifact**:
A sanitized, publishable record from Cognitive Reload showing that a human understands code in a repository. It lives in that repository, never in a Proficiency Profile.
