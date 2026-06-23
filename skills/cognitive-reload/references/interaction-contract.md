# Interaction contract

`cognitive-reload` is a human cognition ritual, not an agent summary generator.

## Core rule

The agent must strengthen and measure the human's mental model through an interactive, tutor-led loop.

Do not compress the session into:

```text
briefing → file checklist → quiz prompt → final JSON
```

Use:

```text
discover → orient → walkthrough → answer questions → continue walkthrough → explicit quiz readiness → quiz one area → grade → retake or proceed → JSON update
```

## Required first response shape

The first response after evidence collection should contain:

1. Detected reload mode.
2. Whether prior cognition artifacts exist.
3. Git evidence summary.
4. Candidate codebase areas.
5. Recommended session agenda.
6. A single clear prompt asking the developer to approve the recommended first area or choose another.

## Required second response after area selection

After the developer chooses an area, do **not** jump to `inspect these files and tell me when ready`.

Instead provide:

1. Area purpose in plain language.
2. A mini flow map through the relevant files/functions/tests.
3. The first line-numbered excerpt.
4. Notes explaining what to notice.
5. A question invitation: `What questions do you have about this block before we continue? You can say next to keep walking.`

## Waiting points

The agent should wait for the developer at these checkpoints unless the user explicitly requested a non-interactive report:

- after proposing the area map/session agenda
- after each code/doc/test excerpt or small cluster of excerpts
- after answering a human question
- after the human explicitly says `ready for quiz`, then after asking 1-3 quiz questions
- after grading partial answers and offering retakes

## First-time guided reload UX

For first-time reloads:

- Do not assume the developer knows the repo.
- Do not treat recent diffs as the main source of cognition.
- Explain what the area is before testing understanding.
- Walk through representative code and tests in small slices.
- Keep Q&A open until the human explicitly asks to be quizzed.
- Score only after the developer demonstrates understanding.
- Mark all other areas `unverified`.

## Quiz gate

Quiz mode begins only after the developer explicitly indicates assessment readiness.

Valid readiness examples:

- `ready for quiz`
- `quiz me`
- `I am out of questions; test me`
- `let's do the teach-back`

Invalid readiness examples:

- `ready`
- `next`
- `continue`
- `I inspected the files`
- `looks good`

Those mean continue the tutorial or Q&A, not assessment.

## Quiz interaction limits

- Ask at most 2-3 questions before waiting.
- Prefer one primary concept per question.
- Avoid giant multipart architecture prompts.
- Grade using evidence from the repo and the rubric.
- If the answer is weak, ask a narrower retake question.

## Report-only mode

Report-only mode means no files are written. It does not mean non-interactive mode.

The agent may still show JSON drafts in chat.
