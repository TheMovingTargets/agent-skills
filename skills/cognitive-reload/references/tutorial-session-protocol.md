# Tutorial session protocol

A tutorial session is the learning phase before a teach-back quiz.

## Required states

Use these conceptual states even if no file is written:

- `area_selected`
- `walkthrough_in_progress`
- `human_questions_open`
- `quiz_ready_confirmed`
- `quiz_in_progress`
- `graded`
- `retake_available`

## State transitions

`area_selected` -> `walkthrough_in_progress`

After the developer chooses an area, do not ask for quiz readiness immediately. Start the walkthrough.

`walkthrough_in_progress` -> `human_questions_open`

After each excerpt, invite questions.

`human_questions_open` -> `walkthrough_in_progress`

When the developer says `next`, continue teaching the next excerpt or concept.

`human_questions_open` -> `quiz_ready_confirmed`

Only when the developer explicitly says something like:

- `ready for quiz`
- `quiz me`
- `I am out of questions; test me`
- `let's do the teach-back`

`quiz_ready_confirmed` -> `quiz_in_progress`

Ask 1-3 focused questions.

`quiz_in_progress` -> `graded`

Grade the answer, cite the evidence basis, and decide whether a retake is useful.

## Non-transitions

These should not trigger quiz mode:

- `ready`
- `I inspected the files`
- `continue`
- `next`
- `looks good`
- silence

Those only mean the human is following along, not that they consented to assessment.
