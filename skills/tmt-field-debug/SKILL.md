---
name: tmt-field-debug
description: Diagnose incidents, regressions, and unexplained behavior on deployed infrastructure through bounded remote logs, live health evidence, and falsifiable production-safe probes. Use after a deployment has finished or when a running environment is faulty, especially when tmt-agent-deploy run records and external log references are available; produce a sanitized implementation-ready Markdown brief without changing the target or implementing fixes.
---

# TMT Field Debug

Investigate the system that is actually failing. Treat deployed infrastructure as an evidence source, not a place to improvise repairs.

## Invariants

- Keep the investigation read-only. Do not deploy, restart, scale, fail over, purge, replay, migrate, rotate, edit configuration or feature flags, attach a debugger, add instrumentation, or change application data.
- Treat a probe as mutating when its effects are unknown. Ask for clarification instead of guessing; separate authorization does not make a mutating action part of this skill.
- Use established access paths, provider tooling, runbooks, and configured diagnostics. Never invent a privileged remote command or bypass the deployment harness.
- Bound every query by the exact environment, target, component, time window, and identifiers needed. Avoid unbounded log downloads, broad production scans, and probes that can materially increase load or cost.
- Never expose secrets, tokens, credential values, private keys, personal data, or raw sensitive payloads. Preserve references, timestamps, hashes, request IDs, and sanitized excerpts instead of copying raw logs into the report.
- Separate observations, inferences, and hypotheses. A plausible explanation is not a root cause until a named probe discriminates it from credible alternatives.
- Ask a concise clarifying question whenever ambiguity changes the target, safety, interpretation, or next probe. Continue only with work whose meaning and safety remain unambiguous.
- Do not edit product code or deployment automation. The only local write this skill makes is the requested sanitized Markdown report.

## 1. Establish the incident contract

Inspect local repository context and `.tmt-agent-deploy/` state before asking for facts already available. Resolve:

- the user-visible symptom and expected behavior;
- environment, account or project, region, target, component, and tenant or request scope;
- first known occurrence, last known good time, timezone, and investigation window;
- current severity, blast radius, and whether the incident is ongoing;
- deployed source or artifact identity and relevant deployment run;
- allowed access paths and known-safe read-only diagnostics;
- report path when the user specified one.

If `.tmt-agent-deploy/state/current-run.yaml` exists or an external deployment workflow is active, stop field probes and invoke `tmt-agent-deploy` recovery or monitoring. Do not compete with a changing target.

Ask about every unresolved ambiguity that could select a different system, expose unrelated data, create load, or change the meaning of success. Group tightly related questions, but do not turn the whole investigation into an upfront questionnaire.

Complete this step only when the exact target, symptom, window, source identity, and safe access boundary are known, or when the report can name the missing item as a blocker.

## 2. Reconstruct the deployed reality

Read relevant deployment summaries, `state/MEMORY.md`, `state/artifacts.yaml`, current deployment configuration, authoritative runbooks, provider status, and source history. Follow external log references from the selected run. Flag configuration or artifact hash drift; do not treat current configuration as historical truth.

Establish current health and a timeline that correlates:

- deploy, rollback, configuration, dependency, and infrastructure events;
- symptom onset and representative request or trace identifiers;
- changes in errors, latency, saturation, traffic, and resource health;
- affected versus unaffected components, instances, tenants, regions, or versions.

Prefer structured provider queries and configured diagnostic entry points. For remote shell access, run only known read-only commands with an explicit host, working directory, timeout, and output bound. Record the command or provider query in sanitized form before interpreting its result.

Complete this step only when every material claim in the timeline has a source reference and the report can distinguish known, unknown, and conflicting target state.

## 3. Reproduce or define an observable signature

Prefer a production-safe observation loop over a local approximation. Define the narrowest signature that detects the reported symptom: a log event, trace condition, metric threshold, health response, or safe idempotent request.

Run synthetic requests only when their endpoint, identity, data effects, rate, and cleanup behavior are proven non-mutating. Ask before using real tenant data or any request whose side effects are ambiguous. Otherwise observe an existing request or compare already-recorded evidence.

Measure the baseline and reproduction rate. For intermittent incidents, use repeated bounded queries over a fixed window; do not generate load merely to increase reproduction.

Complete this step only when the exact symptom is observable against the deployed path, or when the evidence gap and the access or artifact needed to close it are documented.

## 4. Test ranked hypotheses

Maintain 3–5 ranked hypotheses when the evidence supports that many. For each one record:

- proposed mechanism and causal chain;
- supporting and contradicting evidence;
- a prediction that differs from competing hypotheses;
- one bounded read-only probe and its expected discriminating result;
- status: `untested`, `supported`, `weakened`, `falsified`, or `blocked`.

Test one prediction at a time. Prefer comparisons across known-good and affected versions, instances, regions, tenants, or time windows. Use logs targeted at the failing boundary, correlated traces, metrics, dependency status, configuration snapshots, and read-only data queries; never “collect everything and grep.”

Before an ambiguous probe, show the competing interpretations or safety uncertainty and ask the user. When a probe is safe and its meaning is unambiguous, run it without ceremony. Re-rank after every material result and preserve negative evidence.

Complete this step only when one causal explanation is supported across the failing boundary and credible alternatives are falsified or explicitly bounded, or when every remaining hypothesis has a named blocker.

## 5. Determine fixes without applying them

Trace the supported mechanism into the repository and deployment artifacts. Propose the smallest fix that breaks the causal chain, then add hardening only where evidence justifies it.

For each proposed change identify exact files, symbols or workflow steps, behavioral change, compatibility and data risks, regression seam, focused tests, non-production validation, deployed smoke evidence, rollback implications, and pass/fail criteria. Do not claim exact files when repository evidence cannot support them; turn that gap into a discovery task for implementation.

Classify work as:

- `required`: removes the supported failure mechanism;
- `validation`: proves the same boundary that failed;
- `hardening`: improves detection, isolation, or recovery;
- `cleanup`: removes residual state and may require destructive authorization.

Set implementation readiness to `READY` only when the required changes, acceptance criteria, test plan, risks, and non-goals are self-contained. Otherwise set `BLOCKED` and list the smallest questions or evidence needed.

## 6. Deliver the Markdown handoff

Read [references/report-contract.md](references/report-contract.md) completely and follow its schema. Use the user's output path; otherwise write `docs/field-debug/<YYYY-MM-DD>-<incident-slug>.md` when `docs/` exists, or `field-debug-<YYYY-MM-DD>-<incident-slug>.md` at the repository root.

Sanitize the report while retaining precise evidence references and reproducible read-only queries. Include all requested sections even when their value is `None`, `Unknown`, or `Blocked`. End with the smallest next authorization: normally implementation through `implement`, additional access, or a specific user answer. Never imply authorization to deploy.

Complete the skill only when the report exists, every conclusion maps to evidence, every tested hypothesis has a result, unresolved ambiguity is explicit, and the implementation brief is either `READY` for direct input to `implement` or honestly `BLOCKED`.
