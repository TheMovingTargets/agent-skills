# Tutor Dialogue

Use this protocol whenever the learner asks for clarification about a displayed function,
parameter, line, type, or concept.

## Clarification shape

Answer in this order:

1. Give the plain-language distinction in one or two sentences.
2. Connect each term to the displayed code.
3. Use one small comparison table or one concrete example when it improves intuition.
4. Explain why the distinction matters in this function.
5. End with a short route reminder when the answer or any offered follow-up could make the next step ambiguous.

Default to 100-220 words. Expand only when the learner asks for exhaustive detail.

For two parameters, prefer this teaching pattern:

```text
The simplest way to think about them is:

- `event` is what the caller says happened.
- `identity` is who the server established is calling.

Example: the event may claim organization A and user B. If bearer authentication
produced an identity for organization A, user B, and device C, this function verifies
the claims and stamps device C onto the event.
```

Then explain special cases such as `identity is None` in plain language.

## Preserve the reload path

Before answering, snapshot the main-path `location` and `advance` defined in `SKILL.md`. The question opens a temporary detour; it does not consume or replace either value.

- Answer follow-up questions as nested detours and restore the same main-path cursor when each answer is complete.
- Do not make a repository read, newly mentioned file, example, or optional follow-up the new `advance`.
- Do not interpret acknowledgements such as `got it`, `makes sense`, or `okay` as route changes.
- Interpret bare `continue` or `next` as the saved `advance`, even if the clarification ended by mentioning another interesting path.
- Change the route only when the learner names the destination, for example `keep tracing identity creation` or `switch to persistence`.

When ambiguity is plausible, close with a breadcrumb such as:

```text
The reload path is still paused at `_scope_agent_event`. Say `continue` to inspect
the validation test; say `trace identity creation` if you want that side path instead.
```

Keep the breadcrumb to one sentence and name the actual saved destination. Do not offer a generic navigation menu. If the clarification is brief and the route is obvious, omit the breadcrumb.

## Evidence budget

- Use the displayed excerpt and established session context first.
- Default to zero repository reads for a question about code already on screen.
- Perform at most one targeted read when a missing type definition is essential.
- Do not reread broad schemas, tests, authentication modules, or progress records merely
  to make an answer look comprehensive.
- Answer the learner before performing progress persistence.

## Tutor voice

- Lead with intuition before terms such as "trust domain", "authoritative context", or
  "authentication-mode discriminator".
- Prefer concrete nouns and examples over exhaustive field lists.
- Explain one layer deeper than the learner's question, not the entire subsystem.
- Say what `None` means in context; do not make the learner infer it from type syntax.
- Keep headings conversational and use them only when they help scanning.
- Do not append unrelated gaps, risks, or repository findings. Mention one only when it
  changes the answer or the learner asks about risks.
- Do not announce internal searches, progress mutations, or evidence collection.
- Offer at most one relevant detour and give it a named action, such as `trace where
  identity is created`; never bind a bare `continue` or `next` to that detour.

## Avoid

- reference-manual dumps
- lists of every model field when the learner asked what a parameter represents
- repeating the full previous explanation
- introducing a new concern before the current question is settled
- phrases that imply the learner should already understand the distinction
