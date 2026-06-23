# Human question loop

The human is allowed to interrupt the walkthrough at any time with questions. Answering those questions is part of the cognitive reload, not a distraction from it.

## Trigger

Enter the question loop when the developer asks about:

- a displayed code block
- a function, class, route, command, or test name
- a data model, schema, field, identifier, or invariant
- why a design exists
- what would break if code changed
- which test protects behavior
- how a future agent should modify the area

## Response shape

When answering a question:

1. Answer directly.
2. Point back to the relevant file/line/excerpt when available.
3. Distinguish observed repo facts from inference.
4. Explain the concept at the human's current level.
5. Offer to go one level deeper or continue the walkthrough.

Example:

```text
That check matters because it prevents the client from choosing its own organization scope. The observed fact is that the route uses the authenticated agent context to set org/user/device. My inference is that this is intended to prevent cross-tenant attribution bugs.

Want to go deeper on this check, or continue to the test that proves it?
```

## Do not quiz during Q&A

Do not turn a human question into a quiz unless the developer explicitly asks to be quizzed.

Bad:

```text
Good question. What do you think the answer is?
```

Good:

```text
Good question. Here's what the code shows...
```

## Track unresolved questions

If the code does not answer the human's question, record it as an unresolved question in the final JSON draft:

```json
{
  "question": "Where is device deletion authorization enforced?",
  "status": "unresolved_from_git_evidence",
  "next_action": "Inspect persistence layer or integration tests in a later reload"
}
```
