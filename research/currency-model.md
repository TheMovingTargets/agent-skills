# Research: a Currency model for skills

Question (issue #16): which decay model should turn dated Evidence into Currency: FSRS retrievability, half-life regression (HLR), or something simpler? How does each behave for skills rather than flashcards? How should Evidence of different strength map to a "review" and its grade? What defaults work with no per-user training data? Is a dependency-free Python implementation practical?

Terms (Evidence, Currency, Proficiency, Concept, Dimension) are as defined in `GLOSSARY.md`.

## Answer

**Use FSRS-6 retrievability with the published default parameters.** Replay each Concept's dated Evidence as FSRS reviews, at most one per Concept per day, and do the same for each Language and Harness. Report Currency as R at the current date, in bands keyed to stability S, and always show the last-exercised date next to it.

- Only retrieval-type Evidence becomes a review. A drill, teach-back or unaided use is a review. Exposure alone (a card shown, a concept explained) is not, apart from first contact.
- The model needs nothing beyond the Python standard library. The arithmetic is about 35 lines using only `math` (sketch below), and no optimizer is needed.
- HLR is ruled out. It has no usable default weights, ignores spacing, caps half-life at 9 months and scores worse on the public benchmark.
- A fixed-half-life "last seen" decay is too simple. It cannot tell one demonstration apart from a year of daily use, and fixing that turns it back into HLR or FSRS.
- One choice is left to the spec: whether to **cap S**, for example at 365 days. With the defaults, a year of daily use stays "Current" for about 2.8 years after it stops.

## The candidates, from primary sources

### FSRS (Free Spaced Repetition Scheduler)

The model gives each item two state variables, stability S and difficulty D. Retrievability decays as a power law in elapsed days:

- FSRS-6: `R(t, S) = (1 + factor · t/S)^(-w20)`, with `factor = 0.9^(-1/w20) - 1`, chosen so that `R(S, S) = 0.9`. **S is the number of days until R falls to 90%.** D is bounded to [1, 10], and grades are 1 Again, 2 Hard, 3 Good, 4 Easy. [FSRS algorithm wiki](https://github.com/open-spaced-repetition/awesome-fsrs/wiki/The-Algorithm)
- FSRS-4.5 and FSRS-5 fixed the decay at 0.5 (factor 19/81). FSRS-6 makes the decay a trainable parameter, `w20`, whose default is 0.1542. That default gives a much flatter long tail. [py-fsrs `scheduler.py`](https://github.com/open-spaced-repetition/py-fsrs/blob/main/fsrs/scheduler.py), `FSRS_DEFAULT_DECAY`
- **Update rules** (py-fsrs v6.3.2, `scheduler.py`):
  - First rating: `S0 = w[G-1]` and `D0 = w4 - e^(w5·(G-1)) + 1`.
  - A success multiplies S by `1 + e^w8 · (11-D) · S^-w9 · (e^(w10·(1-R)) - 1) · hard_penalty · easy_bonus`.
  - A lapse (Again) resets S to `w11 · D^-w12 · ((S+1)^w13 - 1) · e^(w14·(1-R))`.
  - D moves by `-w6·(G-3)` with linear damping and mean reversion toward `D0(Easy)`.
  - Because of the `(1-R)` term, a review at high R adds little stability. This is the spacing effect built into the model.
- **Defaults:** 21 FSRS-6 parameters, published in py-fsrs and the wiki: `0.212, 1.2931, 2.3065, 8.2956, 6.4133, 0.8334, 3.0194, 0.001, 1.8722, 0.1666, 0.796, 1.4835, 0.0614, 0.2629, 1.6483, 0.6014, 1.8729, 0.5425, 0.0912, 0.0658, 0.1542`. The project does not say exactly how they were derived. They come from the open Anki review-log datasets used by the benchmark, about 10k users and 727M reviews. [srs-benchmark](https://github.com/open-spaced-repetition/srs-benchmark)
- **Reference implementation:** [py-fsrs](https://github.com/open-spaced-repetition/py-fsrs), described as the official Python implementation. It is MIT-licensed; v6.3.2 was released August 2026.
  - Its only runtime dependency is `typing-extensions`. The optimizer is a lazy-loaded extra that needs torch, numpy and pandas. Source: `pyproject.toml` and `fsrs/__init__.py`.
  - Defaults: `desired_retention=0.9`, `maximum_interval=36500`. `maximum_interval` caps the scheduled interval, not S.
- **Background paper:** Ye, Su & Cao, "A Stochastic Shortest Path Algorithm for Optimizing Spaced Repetition Scheduling", KDD 2022, [doi:10.1145/3534678.3539081](https://doi.org/10.1145/3534678.3539081). This paper is the origin of the DSR (difficulty, stability, retrievability) model that FSRS builds on.
- **Newer version:** the benchmark already lists FSRS-7 (34 parameters). py-fsrs still implements FSRS-6.

### Half-life regression (HLR)

- Settles & Meeder, "A Trainable Spaced Repetition Model for Language Learning", ACL 2016, [doi:10.18653/v1/P16-1174](https://doi.org/10.18653/v1/P16-1174), from Duolingo. The model is `p = 2^(-Δ/h)` with `h = 2^(Θ·x)`, where x is a feature vector.
- Reference implementation: [duolingo/halflife-regression `experiment.py`](https://github.com/duolingo/halflife-regression/blob/master/experiment.py), MIT-licensed.
  - Features: `sqrt(1+right)`, `sqrt(1+wrong)`, a bias term and per-lexeme indicators.
  - h is clipped to between 15 minutes and `MAX_HALF_LIFE = 274` days (9 months).
  - Θ is learned by SGD from Duolingo's data, and no general-purpose default weights are published.
- **Features are counts only.** HLR knows how many successes and failures there were and the time since the last one. It does not know when the earlier ones happened, so ten reviews crammed into one week look the same as ten reviews spread over a year.

### ACT-R base-level activation (the "simple, principled" alternative)

- Activation is `m = ln Σ_j t_j^(-d)` over past exposures j, with d around 0.5. Recall probability then needs a further logistic with a threshold τ and a noise s.
  - Anderson & Schooler, "Reflections of the environment in memory", *Psychological Science* 1991, [doi:10.1111/j.1467-9280.1991.tb00174.x](https://doi.org/10.1111/j.1467-9280.1991.tb00174.x).
  - Pavlik & Anderson, *Cognitive Science* 29(4), 2005, [doi:10.1207/s15516709cog0000_14](https://doi.org/10.1207/s15516709cog0000_14). This paper adds spacing-dependent decay.
- The sum takes weighted traces naturally, so a strong piece of Evidence can count as a heavier trace. However, τ, s and the per-trace decay need fitting. Activation is also not a probability readers can interpret.

### Head-to-head on the public benchmark

The figures are from [srs-benchmark](https://github.com/open-spaced-repetition/srs-benchmark), "without same-day reviews": about 10k Anki users, mean ± 99% CI. Lower log loss and RMSE are better; higher AUC is better.

| Model | Params | Log loss | RMSE (bins) | AUC |
|---|---|---|---|---|
| FSRS-6 (per-user optimized) | 21 | 0.3460 | 0.0653 | 0.7034 |
| FSRS-7, default params (no training) | 0 trained | 0.3620 | 0.0910 | 0.7029 |
| ACT-R | 5 | 0.4033 | 0.1074 | 0.5225 |
| HLR | 3 | 0.4694 | 0.1275 | 0.6369 |

- Even with no per-user training, FSRS defaults beat trained HLR and ACT-R on calibration (log loss, RMSE) and on discrimination (AUC).
- The benchmark reports no FSRS-6 default-parameter row, so FSRS-6 defaults have not been measured there. It is reasonable to assume they behave close to the FSRS-7 default row, but that is an inference.

## How these behave for skills, not flashcards

Flashcards are atomic facts reviewed on a schedule. Skill Evidence differs in four ways.

1. **It is opportunistic.** Reviews happen when the developer happens to touch a Concept, not when a scheduler asks.
   - This does not matter to FSRS. R(t, S) is defined for any elapsed t, and scheduling is a separate layer (`_next_interval`) that a profile never calls.
   - It also does not matter to HLR.
2. **It is often dense at the Dimension level** (a Language used every working day) **and sparse at the Concept level.**
   - In FSRS, daily use brings in little new stability per review, because R is close to 1 at each review. Stability still compounds into years (table below).
3. **Skill decay is real but slower for well-practised skills.**
   - Arthur et al. reviewed 53 articles (189 data points). Skill loss grew from d ≈ -0.01 right after training to d ≈ -1.4 after more than 365 days of non-use. Cognitive, accuracy-based tasks decayed more than physical or speed-based ones. "Factors that influence skill decay and retention", *Human Performance* 11(1), 1998, [doi:10.1207/s15327043hup1101_3](https://doi.org/10.1207/s15327043hup1101_3)
   - Bahrick found that well-learned school Spanish stabilised in a "permastore" lasting decades. *JEP: General* 113(1), 1984, [doi:10.1037/0096-3445.113.1.1](https://doi.org/10.1037/0096-3445.113.1.1)
   - A power-law tail, as in FSRS and ACT-R, fits both findings better than a pure exponential with a fixed half-life.
4. **Exposure is not retrieval.** Being re-shown material helps retention much less than retrieving it. Roediger & Karpicke, "Test-enhanced learning", *Psychological Science* 2006, [doi:10.1111/j.1467-9280.2006.01693.x](https://doi.org/10.1111/j.1467-9280.2006.01693.x). This is why only retrieval-type Evidence should count as a graded review.

### Simulation: FSRS-6 defaults on skill-shaped histories

I ran the stdlib sketch below: one review per day, elapsed time in whole days, S in days. "R ≥ 0.9 until" is simply S.

| History | S (days) | R ≥ 0.9 until | R ≥ 0.7 until | R after 1 yr idle | R after 1 yr, decay 0.5 (FSRS-5 curve) |
|---|---|---|---|---|---|
| One exposure, Hard | 1.3 | 1 d | 12 d | 0.42 | 0.12 |
| One drill passed, Good | 2.3 | 2 d | 21 d | 0.46 | 0.16 |
| Good on day 0, 3 and 10 | 39 | 39 d | ~1 yr | 0.70 | 0.56 |
| Good weekly for 12 weeks | 238 | 238 d | ~6 yr | 0.87 | 0.86 |
| Good daily for 365 days | 1020 | ~2.8 yr | ~26 yr | 0.95 | 0.96 |
| Good weekly 12 weeks, then Again at +6 months | 5.2 | 5 d | — | 0.52 | — |

Reading the table:

- **Ordering is sensible.** More practice, and better-spaced practice, means longer Currency, and a failed retrieval collapses S.
- **The tail is very flat with FSRS-6's default decay of 0.1542.** One passed drill still reads R ≈ 0.46 a year later.
  - That is why Currency should be shown in bands keyed to S, not as a raw percentage.
  - Keying to S means R ≥ 0.9 only until t = S, so low-S Concepts drop out of "Current" within days.
- **Heavily practised Dimensions stay "Current" for years after use stops.**
  - That matches the permastore evidence about retention.
  - It does not match a profile reader's question, "has this been exercised lately?". Hence two safeguards:
    - always show last-exercised next to R;
    - optionally cap S, for example at 365 days, so that "Current" never outlasts a year of non-use.
- These numbers extrapolate beyond flashcard data. Few Anki intervals run to years, so treat S above about 1 year as ordinal, not as calibrated.

## Mapping Evidence to reviews and grades

FSRS needs a recall outcome (Again, Hard, Good or Easy) at a date. Proposed mapping:

| Evidence (what the skill observed) | FSRS review? | Grade |
|---|---|---|
| Concept taught or card shown, no check (first contact) | yes, creates the item | Hard (S0 = 1.3 d) |
| Concept re-shown or re-explained, no check | **no** (exposure, not retrieval) | — |
| Check answered correctly with hints, or a partial teach-back | yes | Hard |
| Drill passed, teach-back passed, correct unaided | yes | Good |
| Used unprompted in real work, or explained fluently with no hesitation | yes | Easy |
| Drill or teach-back failed, needed re-teaching | yes | Again |
| Learner skipped it as "already known" (self-report) | **no**: the glossary excludes self-assessment from Evidence | — |

Rules:

- **One review per Concept per UTC day.** Use the *first* retrieval-type Evidence of the day. That is the honest recall after the gap; later attempts that day come after relearning.
  - This matches the benchmark's "without same-day reviews" setting.
  - It avoids FSRS's separate short-term-stability path (`w17` to `w19`).
- **Dimension-level Currency:** replay a separate FSRS item per Language and per Harness. Its reviews are each day with any retrieval-type Evidence in that Dimension, graded by the strongest grade that day.
  - This is simpler than combining many Concept R values, and it answers "is this Language still current?" directly.
- Leave FSRS difficulty D out of Proficiency. It is a property of the item's history, not a judgement of mastery. Proficiency is a separate model (see the map).

## Defaults without training data

- Use the 21 published FSRS-6 defaults unchanged. Do not run the optimizer: it needs a large review log, and torch.
- **Bands on R:**
  - **Current**: R ≥ 0.90, meaning t ≤ S.
  - **Fading**: 0.70 ≤ R < 0.90.
  - **Lapsed**: R < 0.70.
  - 0.9 is FSRS's own anchor and default `desired_retention`. The 0.70 cut-off is a judgement call; change it freely.
- **Optional cap on S**, for example 365 days, applied after each update. This is the one knob worth deciding in the spec.
- Time unit: whole days between UTC dates, the same as py-fsrs, which rounds intervals to whole days.

## Is dependency-free Python practical? Yes

Two options:

1. **Vendor about 35 lines.** The block below is transcribed from py-fsrs v6.3.2's `_initial_stability`, `_initial_difficulty`, `_next_difficulty`, `_next_forget_stability`, `_next_recall_stability` and `get_card_retrievability`, and needs only `math`.
2. **Depend on py-fsrs.** It is MIT-licensed and pure Python, but it brings in `typing-extensions`, a scheduler, fuzzing and learning steps that a profile does not need.

The skills' contract is "files, a shell and `python3`", so option 1 fits better. It is also deterministic, which matters for regenerating a README from the Evidence log.

```python
import math
W = (0.212, 1.2931, 2.3065, 8.2956, 6.4133, 0.8334, 3.0194, 0.001, 1.8722, 0.1666,
     0.796, 1.4835, 0.0614, 0.2629, 1.6483, 0.6014, 1.8729, 0.5425, 0.0912, 0.0658, 0.1542)
DECAY = -W[20]
FACTOR = 0.9 ** (1 / DECAY) - 1
AGAIN, HARD, GOOD, EASY = 1, 2, 3, 4

def clamp_d(d): return min(max(d, 1.0), 10.0)
def clamp_s(s): return max(s, 0.001)
def d0(g): return W[4] - math.e ** (W[5] * (g - 1)) + 1
def retrievability(s, t): return (1 + FACTOR * t / s) ** DECAY

def replay(events):
    """events: sorted (day:int, grade), at most one per day. Returns (S, D, last_day)."""
    s = d = last = None
    for day, g in events:
        if s is None:
            s, d = clamp_s(W[g - 1]), clamp_d(d0(g))
        else:
            r = retrievability(s, day - last)
            if g == AGAIN:
                long = W[11] * d ** -W[12] * ((s + 1) ** W[13] - 1) * math.e ** ((1 - r) * W[14])
                s = min(long, s / math.e ** (W[17] * W[18]))
            else:
                hard = W[15] if g == HARD else 1
                easy = W[16] if g == EASY else 1
                s *= 1 + math.e ** W[8] * (11 - d) * s ** -W[9] * (math.e ** ((1 - r) * W[10]) - 1) * hard * easy
            s = clamp_s(s)
            d = clamp_d(W[7] * d0(EASY) + (1 - W[7]) * (d + (10 - d) * -(W[6] * (g - 3)) / 9))
        last = day
    return s, d, last
```

Caveat: I checked this sketch against the py-fsrs source by reading it, and asserted `R(S, S) = 0.9`. I did not run it side by side with the py-fsrs package. A build ticket should add a golden test against py-fsrs output, for example with `learning_steps=()` and `enable_fuzzing=False`.

## Why not the others

- **HLR:**
  - It needs trained Θ, and the published weights are specific to Duolingo vocabulary.
  - Its count-only features ignore spacing and order.
  - Its 274-day ceiling clips long-term skills.
  - On the benchmark it trails even untrained FSRS.
- **ACT-R base-level:**
  - Weighted traces are attractive for Evidence of different strength.
  - But turning activation into a readable R needs fitted τ and s.
  - Its benchmark AUC (0.52) is close to chance.
- **Fixed half-life from last-exercised** (`2^(-t/h)`):
  - It is trivial to compute and explain.
  - It treats one demonstration the same as a year of daily use.
  - Making h grow with practice reinvents HLR or FSRS, with hand-picked constants and no benchmark behind them.
  - The last-exercised date is still worth showing on its own.

## Open questions for the spec

- Cap S at 365 days, or show R uncapped with last-exercised next to it?
- Is first-contact exposure graded Hard, or does an item exist only after its first retrieval?
- Re-run the defaults when py-fsrs moves to FSRS-7? Its defaults differ, and the Evidence log can simply be replayed, so changing models does not lose data.
