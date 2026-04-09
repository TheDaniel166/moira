# Planetary Heliacal Case Ledger (2026-04-09)

Purpose:
- provide the concrete case ledger for expanding planetary heliacal validation
- turn the corpus-design document into explicit future case rows
- keep validation-row design separate from test implementation

Upstream documents:
- `wiki/03_validation/PLANETARY_HELIACAL_VALIDATION_CORPUS_2026-04-09.md`
- `wiki/03_validation/HELIACAL_VALIDATION_MATRIX_2026-04-09.md`

Current status:
- partially populated ledger
- current admitted rows now explicitly capture the cases already embodied in `tests/unit/test_planet_heliacal.py` and `tests/integration/test_visibility_validation.py`

## Current Admitted Slice

Existing planetary validation already covers a narrow slice with:
- known apparition-date style checks for narrow helper functions
- generalized-event checks against published windows for selected Venus and Jupiter cases

This ledger is for what comes next, not for rewriting the current slice.

## Candidate Case Table

| Case ID | Body | Event kind | Latitude band | Source kind | Expected form | Difficulty | Admission status | Notes |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| PHC-001 | Mercury | heliacal rising | low or mid latitude | candidate needed | exact date or bounded window | hard | candidate_needed | Mercury should stress threshold geometry. |
| PHC-002 | Mercury | heliacal setting | low or mid latitude | candidate needed | exact date or bounded window | hard | candidate_needed | Pair with PHC-001 if source basis is coherent. |
| PHC-003 | Venus | heliacal rising | mid latitude | repo-admitted apparition-date/window slice | expected date near 2020-06-20 or bounded window | easy-medium | admitted_current_slice | Based on `tests/unit/test_planet_heliacal.py` and generalized window integration. |
| PHC-004 | Venus | heliacal setting | mid latitude | repo-admitted apparition-date/window slice | bounded window | easy-medium | admitted_current_slice | Current generalized-event window covers 2021 pre-superior-conjunction last morning visibility. |
| PHC-005 | Venus | acronychal rising | mid latitude | repo-admitted apparition-date/window slice | bounded window | medium | admitted_current_slice | Current generalized-event window covers 2021 first evening visibility after superior conjunction. |
| PHC-006 | Jupiter | heliacal rising | mid latitude | repo-admitted apparition-date/window slice | bounded window | medium | admitted_current_slice | Current generalized-event window covers 2023 post-conjunction morning visibility. |
| PHC-007 | Jupiter | acronychal or heliacal setting | mid latitude | candidate needed | bounded window | medium | candidate_needed | Completes Jupiter family symmetry. |
| PHC-008 | Mars or Saturn | any one clearly sourced event | any usable latitude | candidate needed | exact date or bounded window | medium-hard | optional_later | Only if a stronger source exists. |

## Current Admitted Rows From Existing Tests

These rows already exist implicitly in the test suite and are now made explicit here:

| Admitted row | Body | Event kind | Start JD | Observer | Expected form | Current enforcement path |
| --- | --- | --- | --- | --- | --- | --- |
| APR-001 | Venus | heliacal rising | `2458994.5` | `35°N, 35°E` | expected around `2020-06-20` / JD `2459011` with broad tolerance | `tests/unit/test_planet_heliacal.py` |
| APR-002 | Jupiter | heliacal rising | `2460045.5` | `35°N, 35°E` | expected late April 2023 / JD window `2460060–2460090` | `tests/unit/test_planet_heliacal.py` |
| APR-003 | Venus | acronychal rising | `2459299.5` | `35°N, 35°E` | expected late April 2021 / JD window `2459315–2459360` | `tests/unit/test_planet_heliacal.py` |
| APR-004 | Venus | heliacal setting | `2459050.5` | `35°N, 35°E` | expected late Jan / early Feb 2021 / JD window `2459230–2459270` | `tests/unit/test_planet_heliacal.py` |
| APR-005 | Saturn | acronychal setting | `2459822.5` start search | `35°N, 35°E` | physically plausible event-family enforcement, not yet named as an external-reference row | `tests/unit/test_planet_heliacal.py` |
| APR-006 | Venus | heliacal rising | `2458994.5` | `35°N, 35°E` | generalized event must land in JD window `2459004.0–2459044.0` | `tests/integration/test_visibility_validation.py` |
| APR-007 | Jupiter | heliacal rising | `2460045.5` | `35°N, 35°E` | generalized event must land in JD window `2460050.0–2460110.0` | `tests/integration/test_visibility_validation.py` |
| APR-008 | Venus | acronychal rising | `2459299.5` | `35°N, 35°E` | generalized event must land in JD window `2459310.0–2459360.0` | `tests/integration/test_visibility_validation.py` |
| APR-009 | Venus | heliacal setting | `2459050.5` | `35°N, 35°E` | generalized event must land in JD window `2459220.0–2459290.0` | `tests/integration/test_visibility_validation.py` |

## Admission Status Meanings

- `existing_slice_plus_expansion`
  family already has some validation basis and should be broadened
- `candidate_needed`
  no concrete row captured yet
- `optional_later`
  valid only after stronger core rows are assembled
- `captured_pending_review`
  row identified but not yet admitted
- `admitted_future_row`
  ready for future validation implementation

## Row Requirements

Each future admitted row should specify:
- body
- event kind
- source citation
- source type
- observer latitude
- observer longitude or region
- start date or JD
- expected exact date or allowed event window
- tolerance
- notes on visibility criterion or observational ambiguity

## Priority Order

1. Mercury morning/evening threshold rows
2. Venus expansion rows beyond the present window checks
3. Jupiter complementary event-family rows
4. only then harder Mars or Saturn cases

## Current Honest State

Planetary heliacal validation is real but still sparse.

This ledger exists so the next expansion becomes a designed corpus rather than a drift of miscellaneous apparition examples.
