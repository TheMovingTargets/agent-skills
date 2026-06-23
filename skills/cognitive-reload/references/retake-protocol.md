# Retake protocol

Retakes are normal and should be encouraged. The goal is replenishment, not punishment.

## When to offer a retake

Offer a retake when:

- the answer is partially correct
- the answer misses a critical invariant
- the developer confuses two areas
- the developer asks for a guided explanation first
- the score is below the agent-handoff threshold of 4

## Retake types

### targeted_retake

A narrow follow-up on a missing concept. Preferred.

### full_area_retake

Re-run the area quiz. Use when the initial answer showed broad misunderstanding.

### coached_retake

The agent gives a guided explanation first, then asks a new question. Record that coaching occurred. A project may choose to cap coached retake scores, but the default scaffold does not hard-cap them.

## Recording attempts

Every attempt must be preserved in `quiz_attempts`:

- attempt number
- questions asked
- answer summary
- scores by dimension
- missing concepts
- retake offered
- whether coaching occurred
- whether this attempt updated the verified score

## Current score policy

The current area score reflects the latest successful verified attempt.

Do not delete or overwrite failed attempts.
