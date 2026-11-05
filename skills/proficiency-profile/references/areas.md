# Areas

The Vocabulary of Areas: broad parts of the software stack that Evidence can be tagged with, across every Language and repository. Each id becomes the Activity IRI `https://w3id.org/devprof/areas/<id>`.

Tag an Area only when the code's place in the stack is obvious. A missing Area is better than a wrong one.

| id | area | covers |
|---|---|---|
| `frontend` | Frontend | Browser and desktop user interfaces, rendering, client state |
| `backend` | Backend | Servers, APIs, business logic, service integration |
| `data` | Data | Databases, queries, pipelines, analytics, storage formats |
| `infrastructure` | Infrastructure | Cloud resources, containers, deployment, networking, CI/CD |
| `mobile` | Mobile | Native and cross-platform phone and tablet apps |
| `systems` | Systems | Operating systems, embedded, runtimes, low-level performance |
| `testing` | Testing | Automated tests, test frameworks, test design |
| `security` | Security | Authentication, authorization, cryptography, secure coding |
| `tooling` | Tooling | Build systems, developer tools, CLIs, editors, linters |
| `ai` | AI | Model integration, agents, prompts, machine learning |

## Ids are forever

Areas grow only by a pull request to this file. Once an id is here and in a Profile Repo, don't rename or remove it. Add the new id as a row and keep the old one as an alias line (`old-id → new-id`) at the end of this file.
