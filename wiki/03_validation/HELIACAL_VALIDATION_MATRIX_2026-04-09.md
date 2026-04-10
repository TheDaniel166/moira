# Heliacal Validation Matrix (2026-04-09)

Purpose:
- state exactly what the current heliacal and generalized visibility subsystem validates
- separate strong evidence from slice evidence and provisional claims
- preserve honesty about target-family and criterion-family coverage

Primary sources:
- `moira/heliacal.py`
- `tests/unit/test_heliacal_visibility_policy.py`
- `tests/integration/test_visibility_validation.py`
- `wiki/03_validation/VALIDATION_ASTRONOMY.md`
- `tests/fixtures/yallop_table4_reference.json`

This document is a validation matrix, not a feature roadmap.

## Claim Levels

- `strong`
  externally anchored corpus or well-defined published law is present and enforced
- `slice`
  a real validation anchor exists, but only for a narrow corpus or delegated slice
- `provisional`
  unit or formula validation exists, but the end-to-end observational claim is not yet broadly demonstrated
- `not_yet_claimed`
  the subsystem shape exists, but a corresponding validation claim should not yet be made

## Target Families

- `Moon`
- `Planets`
- `Stars`
- `Cross-family generalized search`
- `Moonlight-aware visibility`

## Criterion Families

Current admitted criterion or policy families visible in the codebase:

- `LIMITING_MAGNITUDE_THRESHOLD`
- `YALLOP_LUNAR_CRESCENT`
- moonlight modification via `MoonlightPolicy.KRISCIUNAS_SCHAEFER_1991`

## Matrix

| Target family | Criterion / policy family | Current evidence basis | Main enforcement path | Claim level | Notes |
| --- | --- | --- | --- | --- | --- |
| Moon | `YALLOP_LUNAR_CRESCENT` | Published Yallop 1997 Table 4 corpus | `tests/integration/test_visibility_validation.py`, `tests/fixtures/yallop_table4_reference.json` | `strong` | This is the strongest heliacal-family validation in the subsystem. |
| Moon | generalized lunar event surface through Yallop evening path | Direct generalized-event integration on lunar branch | `tests/unit/test_heliacal_visibility_policy.py` | `slice` | Confirms surface wiring and doctrinal routing, not a broad corpus by itself. |
| Planets | `LIMITING_MAGNITUDE_THRESHOLD` | Published modern planetary apparition windows | `tests/integration/test_visibility_validation.py` | `slice` | Real external anchor exists, but the corpus is still small and window-based rather than broad event-family coverage. |
| Stars | generalized stellar heliacal event surface | Sirius / Sothic 139 AD anchor plus delegated stellar branch comparison | `tests/integration/test_visibility_validation.py`, `wiki/03_validation/VALIDATION_ASTRONOMY.md` | `slice` | Real validation exists, but broad stellar heliacal coverage is still thin. |
| Cross-family generalized search | typed event and target-family routing | unit-level branch and vessel tests across Moon / star / planet paths | `tests/unit/test_heliacal_visibility_policy.py` | `slice` | Strong for API/doctrine correctness, not sufficient alone for observational breadth claims. |
| Moonlight-aware visibility | `KRISCIUNAS_SCHAEFER_1991` formula layer | paper-equation unit tests | `tests/unit/test_heliacal_visibility_policy.py` | `provisional` | Formula law is tested, but live-ephemeris event consequences are not yet broadly validated. |
| Environment realism | terrain / horizon profile effects | none | none | `not_yet_claimed` | Explicitly deferred in `moira/heliacal.py`. |

## Current Strong Claims That Are Safe

These are the heliacal-family claims the current evidence supports cleanly:

- Moira has a real generalized heliacal and visibility subsystem, not just narrow helper functions.
- Moira has a typed event taxonomy spanning heliacal, acronychal, and cosmic event families.
- Moira has a typed target-family taxonomy spanning Moon, planets, and stars.
- Moira's lunar crescent class law is strongly validated against a published Yallop corpus.

## Current Slice Claims That Are Safe

These claims are legitimate, but should be described as limited-scope:

- planetary generalized visibility events are externally anchored against admitted published apparition windows
- stellar generalized heliacal events have a real historical anchor through the Sirius / Sothic slice
- generalized search routing across target families is tested and functioning

These are real validations, but they do not yet justify a broad statement such as:
- "all generalized heliacal phenomena are comprehensively validated"

## Current Provisional Claims Only

These should remain carefully worded:

- moonlight-aware visibility materially improves real event prediction across live observational cases

What is validated today:
- the Krisciunas & Schaefer 1991 formula layer

What is not yet broadly validated:
- end-to-end event timing or observability consequences under live ephemeris conditions

## Corpus Summary

### Moon

Validation basis:
- Yallop 1997 Table 4 fixture corpus

Evidence already stated in the code/docs:
- `295/295` within `±0.05` q-value in `moira/heliacal.py`

Assessment:
- this is the strongest externally grounded heliacal-family corpus in the repo

### Planets

Validation basis:
- published modern apparition windows

Current shape:
- integration tests verify generalized event search lands inside admitted visibility windows for selected cases

Assessment:
- real validation
- still a slice, not a broad apparition corpus

### Stars

Validation basis:
- Sirius / Sothic historical anchor
- delegated comparison to the stellar heliacal branch

Assessment:
- real validation
- narrow anchor only
- this is the largest remaining breadth weakness

### Moonlight-aware visibility

Validation basis:
- direct formula-unit tests for the K&S 1991 model

Assessment:
- physically meaningful and testable
- still provisional at the observational-event level

## Main Gaps Revealed by the Matrix

### 1. Stellar breadth gap

Most important missing validation expansion:
- a broader stellar heliacal corpus beyond the Sirius anchor

Reason:
- this is the thinnest target-family validation basis relative to the subsystem's stated breadth

### 2. Planetary breadth gap

Current state:
- planetary validation is real, but sparse

Reason:
- published-window checks are useful, but they are a narrower validation family than a richer apparition corpus

### 3. Moonlight end-to-end gap

Current state:
- formula law validated
- observational consequence not yet broadly validated

Reason:
- this is the clearest place where a mathematically admitted layer still lacks a correspondingly strong event-level claim

### 4. Claim-discipline gap

Current state:
- the subsystem is easy to overstate

Reason:
- without a matrix like this, "implemented" can be mistaken for "fully closed and broadly validated"

## Recommended Wording Discipline

Safe wording now:

- "Moira implements a generalized heliacal and visibility subsystem with strong lunar-crescent validation and narrower validated slices for planetary and stellar event families."

Unsafe wording now:

- "Moira fully validates heliacal visibility for Moon, planets, and stars across all event families."

Safe wording for moonlight now:

- "Moira admits the Krisciunas & Schaefer 1991 moonlight model and validates its formula layer; broader live-ephemeris event validation remains open."

## Next Validation Documents Suggested by This Matrix

1. `stellar_heliacal_validation_sources_*.md`
  Goal: identify admissible external or historical stellar corpora beyond Sirius.

2. `stellar_heliacal_validation_corpus_*.md`
  Goal: define the admitted stellar corpus shape anchored by the current Sirius slice.

3. `stellar_heliacal_case_ledger_*.md`
  Goal: capture the current admitted Sirius row and explicit future expansion rows.

4. `planetary_heliacal_validation_corpus_*.md`
   Goal: define a broader planetary apparition/event corpus than the present window-based slice.

5. `moonlight_visibility_integration_plan_*.md`
   Goal: define real observer/date/body cases for end-to-end moonlight validation.

## Final Judgment

The current heliacal subsystem is:
- structurally mature
- strongly validated for one important lunar criterion family
- genuinely validated in narrower planetary and stellar slices
- still provisional in moonlight-aware end-to-end event claims

That is a strong position, but not a finished one.
