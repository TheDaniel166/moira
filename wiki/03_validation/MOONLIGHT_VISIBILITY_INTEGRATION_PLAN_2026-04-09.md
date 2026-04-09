# Moonlight Visibility Integration Plan (2026-04-09)

Purpose:
- define the documentation-level plan for end-to-end validation of the admitted Krisciunas & Schaefer 1991 moonlight layer
- separate formula validation from observational-event validation
- identify the smallest meaningful live-ephemeris case families

Primary repo inputs:
- `moira/heliacal.py`
- `tests/unit/test_heliacal_visibility_policy.py`
- `wiki/03_validation/HELIACAL_VALIDATION_MATRIX_2026-04-09.md`
- `wiki/03_validation/HELIACAL_CLOSURE_AUDIT_2026-04-09.md`
- `wiki/03_validation/SWISS_EPHEMERIS_EXTENSIBILITY_ROADMAP.md`

## 1. Current Baseline

What is already validated:

- the Krisciunas & Schaefer 1991 formula layer
- direct unit behavior such as:
  - full moon brighter than quarter moon
  - near-moon sky brighter than far-from-moon sky
  - no moonlight contribution when Moon or target is below the horizon
  - visibility assessments populate the moonlight diagnostic field when policy admits it

What is not yet broadly validated:

- whether the moonlight-aware path changes real event outcomes credibly under live ephemeris conditions

That distinction must remain explicit.

## 2. Validation Goal

The goal is not to prove:
- "moonlight always gives the correct answer"

The goal is to prove smaller, defensible claims:

1. under bright-moon geometry, the moonlight-aware path moves observability in the expected direction
2. under dark-moon or below-horizon geometry, the moonlight-aware path collapses back toward the non-moonlight case
3. the effect size behaves sensibly across separation, lunar altitude, and phase
4. the generalized visibility event surface remains stable and intelligible when moonlight policy is toggled

## 3. Minimal Live-Ephemeris Case Families

### Family A: bright full-moon suppression cases

Desired geometry:
- target near visibility threshold
- Moon above horizon
- Moon near full
- moderate or small angular separation from target

Expected behavior:
- `MoonlightPolicy.KRISCIUNAS_SCHAEFER_1991` should make visibility harder than `IGNORE`
- in some rows it should delay or suppress an event found in the no-moonlight path

Why this family matters:
- this is the clearest positive test of whether the moonlight model has real event-level consequences

### Family B: quarter-moon comparison cases

Desired geometry:
- same target family and observer setup as Family A where possible
- quarter-moon or less severe lunar phase

Expected behavior:
- moonlight penalty should be weaker than in the full-moon family

Why this family matters:
- proves the effect scales plausibly with phase rather than behaving as a binary toggle

### Family C: below-horizon Moon null-effect cases

Desired geometry:
- target above horizon
- Moon below horizon

Expected behavior:
- moonlight-aware and ignore paths should agree, or nearly agree

Why this family matters:
- validates the admitted null-condition behavior at event level, not just formula level

### Family D: large-separation null-or-small-effect cases

Desired geometry:
- Moon above horizon
- target far from Moon
- same general twilight regime

Expected behavior:
- moonlight penalty should be materially smaller than near-moon cases

Why this family matters:
- tests the spatial falloff behavior under live sky geometry

## 4. Best Initial Target Classes

### A. Threshold planetary cases

Reason:
- planets already have a working generalized visibility path
- some planetary apparitions approach threshold conditions naturally
- easier to reason about than adding many new stellar unknowns at once

### B. Stellar cases after planetary cases

Reason:
- stars are attractive for moonlight validation because many are near threshold
- but stellar heliacal validation itself is still the thinner corpus area
- therefore stellar moonlight cases should follow, not precede, a cleaner planetary integration slice

### C. Moon itself should not be the first moonlight-integration target

Reason:
- the Moon as target belongs to a different criterion family in the strongest current validation path
- it is not the cleanest first demonstration of sky-brightness penalty on another target

## 5. Minimum Row Schema

Each moonlight integration case should record:

- target body or star
- target family
- observer latitude
- observer longitude
- start JD or date
- event kind
- Moon phase regime
- Moon altitude regime
- target-Moon separation regime
- result with `MoonlightPolicy.IGNORE`
- result with `MoonlightPolicy.KRISCIUNAS_SCHAEFER_1991`
- expected relation between the two
- notes on whether the row is a suppression, delay, null-effect, or small-effect case

## 6. Recommended Assertion Families

### Assertion type 1: monotonic penalty

For the same instant and target:
- moonlight-aware limiting magnitude should be stricter than the ignore path under bright-moon conditions

### Assertion type 2: event delay or suppression

For the same start condition:
- moonlight-aware event should occur later than the ignore event, or not be found when the ignore event is found

### Assertion type 3: null-effect correctness

When Moon is below horizon:
- results should match the ignore path within a small event tolerance

### Assertion type 4: spatial scaling

For otherwise similar rows:
- near-moon cases should incur more penalty than far-from-moon cases

## 7. What Should Not Be Claimed Yet

Even after the first integration slice, Moira still should not claim:

- comprehensive observational validation of moonlight-aware heliacal phenomena across all target classes

The first integration phase should only justify:

- event-level plausibility under a small but explicit live-ephemeris case family

## 8. Recommended Execution Order

1. build a small planetary case ledger with full-moon, quarter-moon, and null-effect rows
2. confirm event-delay or suppression behavior under live ephemeris conditions
3. only then add stellar moonlight rows
4. defer terrain or horizon-profile interaction until the moonlight slice itself is stable

## 9. Recommended Wording Discipline

Safe wording after the first integration slice:
- "Moira validates the Krisciunas & Schaefer 1991 formula layer and an initial live-ephemeris integration slice showing sensible event-level moonlight effects."

Unsafe wording even then:
- "Moira fully validates moonlight-aware heliacal visibility observationally."

## 10. Final Judgment

The moonlight layer is already mathematically admitted.

What remains is not formula invention.

What remains is a disciplined integration proof:
- choose a small live-ephemeris case family
- prove the expected direction and scale of effect
- keep claims narrow until the corpus broadens
