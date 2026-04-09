# Stellar Heliacal Candidate Source Ledger (2026-04-09)

Purpose:
- provide the concrete intake ledger for stellar heliacal validation sources
- keep source discovery separate from source admission
- ensure every candidate source is captured with enough metadata to judge whether it can become an oracle

Upstream documents:
- `wiki/03_validation/STELLAR_HELIACAL_VALIDATION_SOURCES_2026-04-09.md`
- `wiki/03_validation/HELIACAL_VALIDATION_MATRIX_2026-04-09.md`

Current status:
- partially populated intake ledger
- no new non-Sirius external source admitted yet

## Intake Rules

Do not admit a source into validation simply because it mentions a heliacal rising.

A candidate source must be captured first, then judged against:
- provenance
- explicit event semantics
- observer/location specificity
- calendrical clarity
- visibility-criterion transparency

## Candidate Table

| Candidate ID | Star | Source title / citation | Source kind | Event kind | Site / latitude | Date or range | Criterion stated? | Oracle tier | Admission status | Notes |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| SHS-001 | Sirius | Censorinus / Sothic anchor lineage | historical anchor | heliacal rising | Alexandria band / Egyptian context | 139 AD anchor slice | partial | Tier A | admitted_anchor | Current governing stellar anchor in Moira. |
| SHS-002 | Sirius | Bradley E. Schaefer, “The Heliacal Rise of Sirius and Ancient Egyptian Chronology” (2000) | scholarly historical reconstruction | heliacal rising | Alexandria / Egyptian chronology context | 139 AD-centered historical discussion | yes | Tier A | captured_pending_review | Strong direct candidate for expanding the current Sirius anchor documentation into a more explicit scholarly oracle row. |
| SHS-003 | multi-star / general | Bradley E. Schaefer, “Heliacal Rise Phenomena” (1987) | scholarly methodology paper | heliacal rising / setting family | general methodological scope | general | yes | Tier A | captured_pending_review | Valuable for criterion-law and event-semantics review; not by itself a star/date oracle row. |
| SHS-004 | TBD non-Sirius bright star | candidate source not yet captured | TBD | TBD | TBD | TBD | TBD | Tier A or B | candidate_needed | First non-Sirius bright-star candidate with explicit event semantics still needed. |
| SHS-005 | TBD non-Sirius bright star | candidate source not yet captured | TBD | TBD | TBD | TBD | TBD | Tier A or B | candidate_needed | Second bright-star candidate with different declination geometry still needed. |
| SHS-006 | TBD | candidate historical reconstruction source not yet captured | scholarly reconstruction | TBD | TBD | TBD | TBD | Tier A | candidate_needed | Reserve slot for a non-Sirius historical reconstruction source. |
| SHS-007 | TBD | candidate modern observational-study source not yet captured | observational study | TBD | TBD | TBD | TBD | Tier A or B | candidate_needed | Reserve slot for a modern stellar visibility study with usable row data. |

## Admission Status Meanings

- `admitted_anchor`
  already admitted as a governing validation anchor
- `candidate_needed`
  slot intentionally reserved; no source captured yet
- `captured_pending_review`
  source is identified but not yet judged admissible
- `admitted_secondary`
  admissible as a secondary oracle or corpus member
- `rejected`
  source reviewed and explicitly excluded

## Required Review Questions

For each future captured source:

1. Does it identify a specific star unambiguously?
2. Does it specify first visibility, last visibility, or another event family explicitly?
3. Does it provide a site, latitude, or region precise enough to model?
4. Does it provide a date, year, or constrained date range?
5. Does it state or imply an observational criterion clearly enough to compare against Moira policy?
6. Is it primary, scholarly secondary, or merely convenience commentary?
7. If historical, how much calendrical reconstruction uncertainty is present?

If those questions cannot be answered, the source should not become part of the admitted validation corpus.

## Immediate Next Fill Targets

The first useful additions to this ledger should be:

1. review SHS-002 for direct admission fields and uncertainty notes
2. review SHS-003 strictly as methodology support, not as a standalone event oracle
3. capture one non-Sirius historically prominent bright-star source
4. capture one source family from modern observational visibility literature

## Current Captured Scholarly Candidates

Already captured in this ledger:

- Bradley E. Schaefer, `Heliacal Rise Phenomena` (1987)
- Bradley E. Schaefer, `The Heliacal Rise of Sirius and Ancient Egyptian Chronology` (2000)

These are not yet promoted beyond `captured_pending_review` except where Moira already treats the Sirius anchor as admitted doctrine.

## Current Honest State

Right now, Sirius remains the only clearly admitted stellar heliacal validation anchor.

This ledger exists so future expansion happens under provenance discipline rather than ad hoc reference gathering.
