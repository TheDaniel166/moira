# Planetary Heliacal Validation Corpus (2026-04-09)

Purpose:
- define the next-step corpus shape for planetary heliacal validation beyond the current published-window slice
- preserve explicit event semantics and observer assumptions
- keep planetary validation stronger than vague "known apparition date" checks

Primary repo inputs:
- `tests/unit/test_planet_heliacal.py`
- `tests/integration/test_visibility_validation.py`
- `wiki/03_validation/HELIACAL_VALIDATION_MATRIX_2026-04-09.md`
- `moira/heliacal.py`

## 1. Current Baseline

The current planetary validation basis is real:

- `tests/unit/test_planet_heliacal.py` validates narrow planetary helpers against known apparition dates with broad tolerances
- `tests/integration/test_visibility_validation.py` validates generalized planetary event search against admitted published apparition windows

This is enough to justify a slice claim.

It is not yet enough to justify:
- broad closure across planets, event families, and observing conditions

## 2. Current Strengths

The present planetary corpus already does three useful things:

- proves the narrow planetary helpers are not detached from reality
- proves the generalized event surface reaches the same family of outcomes
- preserves morning/evening apparition semantics for selected concrete cases

Those are real gains. They should remain in the corpus even after expansion.

## 3. Current Weaknesses

### 3.1 Small case count

The current generalized corpus in `test_visibility_validation.py` is intentionally small.

Consequence:
- it validates representative slices, not broad planetary coverage

### 3.2 Window-style validation

The present integration checks mainly ask whether an event lands inside an admitted window.

Consequence:
- useful for sanity and event-family anchoring
- weaker than a corpus with explicit observed or published event dates and tolerances

### 3.3 Limited environmental diversity

The present corpus does not yet read like a designed matrix across:
- latitude
- planetary brightness regimes
- morning vs evening families
- difficult versus easy visibility cases

## 4. Desired Corpus Shape

The next admitted planetary corpus should be a matrix, not a list of anecdotes.

Each row should vary along these axes:

- body:
  at minimum `Mercury`, `Venus`, `Jupiter`, and one dimmer outer-planet case only if the source basis is credible
- event kind:
  heliacal rising, heliacal setting, acronychal rising, acronychal setting
- observer latitude:
  at least low, mid, and higher latitude where the source supports it
- season and solar geometry:
  avoid clustering all cases into one twilight regime
- difficulty:
  include both easy bright apparitions and near-threshold cases

## 5. Preferred Oracle Families

### A. Published apparition windows with explicit observing context

Use when they include:
- body
- date range
- observer region or latitude relevance
- event family semantics

Role:
- good first expansion path

Limitation:
- still a window oracle, not an exact-date oracle

### B. Published event dates or almanac-style visibility notices

Use when they include:
- a stated first or last visibility date
- observer site or region
- explicit event family

Role:
- stronger than broad windows

### C. Well-documented modern observational reports

Use when they include:
- observer location
- date
- identified event type
- enough context to compare with Moira's policy assumptions

Role:
- good for threshold or difficult cases

## 6. Inadmissible or Weak Corpus Material

Do not build the planetary corpus around:

- unsourced "best viewed" calendar pages
- generic astrology blog dates
- Swiss output alone
- undocumented social-media observation reports without location and conditions

These may suggest candidate dates, but they are not the oracle.

## 7. Minimum Row Schema

Each future planetary validation row should contain:

- body
- event kind
- source citation
- source kind
- observer latitude
- observer longitude or region
- start date or start JD
- expected event date or expected date window
- tolerance or window width
- visibility criterion notes if source supplies them
- remarks on ambiguity or observational uncertainty

## 8. Recommended Validation Tiers

### Tier 1: exact-date or near-date rows

Use when the source is precise enough.

Expected assertion style:
- event JD within declared tolerance of published event JD

### Tier 2: bounded-window rows

Use when the source gives a date range or apparition window.

Expected assertion style:
- event JD inside admitted interval

### Tier 3: doctrine-comparison rows

Use when exact observational truth is weak, but comparative behavior matters.

Expected assertion style:
- generalized event surface and narrow planetary helper remain consistent under the same policy

## 9. Recommended Initial Expansion Matrix

The first corpus expansion should remain modest and deliberate.

Suggested structure:

1. Mercury:
   include at least one morning and one evening event because Mercury stresses threshold geometry
2. Venus:
   include both morning and evening apparitions because Venus is bright and observationally prominent
3. Jupiter:
   include one morning and one evening case as a slower-moving bright outer-planet anchor
4. Optional harder case:
   only if a stronger source exists for Mars or Saturn first/last visibility

## 10. Claim Discipline

Safe wording now:
- "planetary heliacal validation is externally anchored through known apparition cases and published visibility windows"

Unsafe wording now:
- "planetary heliacal visibility is comprehensively validated across all major planets and event families"

Safer wording after the next corpus phase:
- "planetary heliacal validation covers a small multi-planet, multi-event corpus with explicit event windows or published dates"

## 11. Immediate Next Artifact

The next useful document after this one is:
- a concrete row ledger of proposed planetary validation cases before any test expansion

That keeps the validation program inspectable before implementation begins.

## 12. Final Judgment

Planetary heliacal validation is already real.

Its weakness is not legitimacy.
Its weakness is breadth and corpus design.

The next improvement is therefore:
- build a compact multi-planet, multi-event corpus with explicit row semantics

not:
- add more helper functions
