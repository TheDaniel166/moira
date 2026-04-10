# Stellar Heliacal Case Ledger (2026-04-09)

Purpose:
- provide the concrete case ledger for expanding stellar heliacal validation
- turn the stellar corpus-design document into explicit current and future rows
- keep validation-row design separate from broad test implementation

Upstream documents:
- `wiki/03_validation/STELLAR_HELIACAL_VALIDATION_CORPUS_2026-04-09.md`
- `wiki/03_validation/STELLAR_HELIACAL_CANDIDATE_SOURCE_LEDGER_2026-04-09.md`
- `wiki/03_validation/HELIACAL_VALIDATION_MATRIX_2026-04-09.md`

Current status:
- partially populated ledger
- one current admitted row now explicitly captures the stellar slice already embodied in `tests/integration/test_visibility_validation.py`

## Current Admitted Slice

Existing stellar validation already covers a narrow slice with:
- the Sirius / Sothic 139 AD anchor family
- generalized stellar event routing against the direct star-heliacal path

This ledger is for what comes next, not for pretending the current slice is already broad.

## Current Admitted Rows

| Admitted row | Star | Event kind | Start JD / date | Observer | Source kind | Expected form | Current enforcement path | Notes |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| SHR-001 | Sirius | heliacal rising | `139-01-01` start search | `31.2°N, 29.9°E` | repo-admitted historical anchor slice | generalized stellar event equals direct star-heliacal path within 1 minute and falls within 5 days before the Sothic rising entry | `tests/integration/test_visibility_validation.py`, `tests/fixtures/stellar_heliacal_reference.json` | Current governing stellar validation row. |

## Candidate Case Table

| Case ID | Star | Event kind | Latitude band | Source kind | Expected form | Difficulty | Admission status | Notes |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| SHC-001 | Sirius | heliacal rising | Alexandria / Egyptian context | admitted historical anchor | bounded relation to the Sothic anchor and direct star path | medium | admitted_current_slice | Existing governing row. |
| SHC-002 | non-Sirius bright star | heliacal rising | low or mid latitude | candidate needed | exact date or bounded window | medium-hard | candidate_needed | First non-Sirius expansion row should be historically prominent and unambiguous. |
| SHC-003 | non-Sirius bright star | heliacal rising | contrasting declination geometry | candidate needed | exact date or bounded window | medium-hard | candidate_needed | Choose to widen geometry rather than duplicate Sirius-like conditions. |
| SHC-004 | bright star with modern observational study | heliacal rising or setting | documented site | candidate needed | exact date or bounded window | hard | candidate_needed | Use only if the observational criterion is explicit enough to compare. |
| SHC-005 | non-Sirius bright star | heliacal setting | any credible latitude | optional later | exact date or bounded window | hard | optional_later | Add only after the rising-family corpus is established. |

## Admission Status Meanings

- `admitted_current_slice`
  already embodied in the current test suite and validation matrix
- `candidate_needed`
  no concrete validation row captured yet
- `captured_pending_review`
  row identified but not yet admitted
- `admitted_future_row`
  ready for future validation implementation
- `optional_later`
  should not be pursued until the core rising-family rows exist

## Row Requirements

Each future admitted row should specify:
- star
- event kind
- source citation
- source type
- observer latitude
- observer longitude or site/region
- start date or JD
- expected exact date or allowed event window
- tolerance
- notes on visibility criterion or calendrical ambiguity

## Priority Order

1. preserve and keep enforcing the current Sirius anchor row
2. capture the first non-Sirius bright-star rising row with explicit semantics
3. capture a second non-Sirius row with materially different geometry
4. only then pursue stellar setting rows or more difficult modern observational cases

## Current Honest State

Stellar heliacal validation is real but still thin.

This ledger exists so the next expansion becomes a designed corpus rather than a drift of miscellaneous star references.

The next real blocker is not implementation of a new star-event function.
It is admission of at least one non-Sirius external stellar row with explicit event semantics.