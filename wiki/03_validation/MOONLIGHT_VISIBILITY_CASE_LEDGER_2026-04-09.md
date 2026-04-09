# Moonlight Visibility Case Ledger (2026-04-09)

Purpose:
- provide the concrete case ledger for end-to-end moonlight-aware visibility validation
- turn the moonlight integration plan into explicit future case families
- preserve the distinction between formula validation and event-level validation

Upstream documents:
- `wiki/03_validation/MOONLIGHT_VISIBILITY_INTEGRATION_PLAN_2026-04-09.md`
- `wiki/03_validation/HELIACAL_VALIDATION_MATRIX_2026-04-09.md`

Current status:
- partially populated ledger
- no live-ephemeris moonlight integration corpus admitted yet

## Candidate Case Table

| Case ID | Target family | Example target | Moon regime | Separation regime | Expected relation | Admission status | Notes |
| --- | --- | --- | --- | --- | --- | --- | --- |
| MVC-001 | planet | TBD threshold planet | near full, above horizon | near or moderate | K&S path should delay or suppress event vs ignore path | candidate_needed | Bright-moon suppression anchor case. |
| MVC-002 | planet | same or similar target as MVC-001 | quarter moon | near or moderate | K&S penalty should be weaker than MVC-001 | candidate_needed | Phase-scaling comparison case. |
| MVC-003 | planet | same or similar target class | any phase | Moon below horizon | K&S and IGNORE paths should agree closely | candidate_needed | Null-effect anchor case. |
| MVC-004 | planet | similar target class | bright moon | large separation | K&S penalty should be smaller than near-moon case | candidate_needed | Spatial-falloff anchor case. |
| MVC-005 | star | TBD later | bright moon | near or moderate | same directional behavior as planetary cases | deferred_until_planetary_slice | Do not start with stellar cases. |

## Current Admitted Formula-Layer Evidence

These are not yet live-ephemeris event rows, but they are already enforced and should be treated as the mathematical baseline:

| Evidence ID | Evidence kind | Current enforcement path | Status | Notes |
| --- | --- | --- | --- | --- |
| MVE-001 | full Moon brighter than quarter Moon | `tests/unit/test_heliacal_visibility_policy.py` | admitted_formula_baseline | Confirms phase scaling direction in the K&S layer. |
| MVE-002 | near-Moon sky brighter than far-from-Moon sky | `tests/unit/test_heliacal_visibility_policy.py` | admitted_formula_baseline | Confirms separation scaling direction. |
| MVE-003 | zero moonlight when Moon below horizon | `tests/unit/test_heliacal_visibility_policy.py` | admitted_formula_baseline | Governs future null-effect event cases. |
| MVE-004 | zero moonlight when target below horizon | `tests/unit/test_heliacal_visibility_policy.py` | admitted_formula_baseline | Preserves geometric null condition. |
| MVE-005 | assessment populates moonlight diagnostics when K&S policy is active | `tests/unit/test_heliacal_visibility_policy.py` | admitted_formula_baseline | Confirms policy routing and diagnostic exposure. |

## Admission Status Meanings

- `candidate_needed`
  slot reserved; no concrete case captured yet
- `deferred_until_planetary_slice`
  valid case family, but intentionally postponed
- `captured_pending_review`
  case identified but not yet admitted
- `admitted_future_row`
  ready for future validation implementation

## Minimum Recorded Fields

Each future case row should record:
- target
- target family
- observer latitude
- observer longitude
- event kind
- start date or JD
- Moon phase description
- Moon altitude regime
- target-Moon separation regime
- result under `MoonlightPolicy.IGNORE`
- result under `MoonlightPolicy.KRISCIUNAS_SCHAEFER_1991`
- expected relationship between the two

## Assertion Intent by Family

### Suppression or delay family

Expected outcome:
- moonlight-aware event later than ignore event, or missing where ignore finds one

### Null-effect family

Expected outcome:
- nearly identical result when Moon is below horizon

### Spatial falloff family

Expected outcome:
- near-moon case shows stronger penalty than far-moon case

### Phase scaling family

Expected outcome:
- full moon case shows stronger penalty than quarter-moon case

## Priority Order

1. one bright-moon suppression case
2. one null-effect below-horizon case
3. one phase-comparison case
4. one separation-comparison case
5. only then any stellar moonlight cases

## Current Honest State

The moonlight layer is formula-validated but not yet event-level corpus-validated.

This ledger exists so that future integration rows can be admitted deliberately, with explicit expected relations rather than vague “looks plausible” judgments.
