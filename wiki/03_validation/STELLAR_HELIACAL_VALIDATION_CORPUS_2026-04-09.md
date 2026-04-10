# Stellar Heliacal Validation Corpus (2026-04-09)

Purpose:
- define the admitted stellar heliacal validation corpus shape beyond source discovery
- preserve explicit event semantics and observer assumptions for stellar rows
- keep stellar validation stronger than vague "star-related historical mention" checks

Primary repo inputs:
- `wiki/03_validation/STELLAR_HELIACAL_VALIDATION_SOURCES_2026-04-09.md`
- `wiki/03_validation/STELLAR_HELIACAL_CANDIDATE_SOURCE_LEDGER_2026-04-09.md`
- `wiki/03_validation/HELIACAL_VALIDATION_MATRIX_2026-04-09.md`
- `tests/integration/test_visibility_validation.py`
- `moira/heliacal.py`
- `moira/stars.py`
- `moira/sothic.py`

## 1. Current Baseline

The current stellar heliacal validation basis is real but narrow.

It currently includes one admitted corpus family:

- Sirius / Sothic 139 AD anchor slice
- generalized stellar event delegation check against the direct star-heliacal path
- explicit enforcement in `tests/integration/test_visibility_validation.py`

It also has two admitted secondary support sources:

- Schaefer (2000) as secondary scholarly support for the Sirius anchor context
- Schaefer (1987) as secondary methodology support for event semantics and criterion law

This is enough to justify a stellar validation slice claim.

It is not yet enough to justify:
- broad stellar heliacal closure across named stars
- broad validation across declination regimes, magnitudes, and observational contexts

## 2. Current Strengths

The present stellar corpus already does three useful things:

- proves the generalized stellar branch is not detached from a real historical anchor
- proves the generalized visibility surface and the direct star-heliacal search stay aligned for Sirius
- preserves the doctrinal separation between the Sothic subsystem and the broader stellar heliacal surface

Those are real gains. They should remain in the corpus even after expansion.

## 3. Current Weaknesses

### 3.1 Single admitted star

The current admitted stellar corpus has one star only: Sirius.

Consequence:
- it validates a real stellar slice, not broad named-star coverage

### 3.2 Historical-anchor concentration

The present admitted row is anchored to the Sothic historical family.

Consequence:
- strong for Sirius doctrine and historical anchor integrity
- weaker for claiming modern observational breadth across other stars

### 3.3 Limited geometry diversity

The current corpus does not yet behave like a designed matrix across:

- different declinations
- different brightness regimes
- different latitude bands
- different event difficulty levels

## 4. Desired Corpus Shape

The next admitted stellar corpus should be a matrix, not a loose collection of references.

Each future row should vary along these axes:

- star:
  at minimum one additional bright historically prominent star beyond Sirius
- event kind:
  heliacal rising first; heliacal setting only when the source basis is equally clear
- observer latitude:
  preserve at least one low/mid-latitude historical family and one distinct geometry family
- source family:
  historical anchor, scholarly reconstruction, or explicit observational study
- difficulty:
  include both easy bright-star cases and more threshold-sensitive rows only after strong sources exist

## 5. Preferred Oracle Families

### A. Historically explicit first-visibility records tied to a named star and site

Use when they include:
- a named star
- a named site or latitude band
- a historical year or date range
- explicit first-visibility semantics

Role:
- strongest historical stellar oracle family

### B. Scholarly modern reconstructions with explicit assumptions

Use when they include:
- star identity
- observer location or latitude
- stated visibility criterion or solar-depression rule
- reconstructed date or day range

Role:
- strongest expansion family beyond the raw Sirius anchor

### C. Modern observational stellar visibility studies

Use when they include:
- explicit event family
- site conditions
- named stars or star classes
- dates or predicted windows

Role:
- supports broader doctrine stress after the historical anchor family is widened

## 6. Inadmissible or Weak Stellar Corpus Material

Do not build the stellar corpus around:

- unsourced astrology pages listing heliacal rising dates
- generic historical summaries without event semantics
- Swiss output alone
- star-position references with no visibility event content

These may suggest candidate dates, but they are not the oracle.

## 7. Minimum Row Schema

Each future admitted stellar row should contain:

- star name
- event kind
- source citation
- source type
- observer latitude
- observer longitude or site/region
- start date or start JD
- expected exact date or admitted date window
- tolerance or window width
- source criterion notes if supplied
- notes on calendrical or observational uncertainty

## 8. Recommended Validation Tiers

### Tier 1: historical-anchor or exact-date rows

Use when the source is specific enough.

Expected assertion style:
- event JD within declared tolerance of the admitted event JD or date band

### Tier 2: bounded-window rows

Use when the source provides a day range rather than a single exact date.

Expected assertion style:
- event JD inside the admitted interval

### Tier 3: doctrine-comparison rows

Use when external truth is narrower, but subsystem routing still needs enforcement.

Expected assertion style:
- generalized stellar event surface and direct star-heliacal helper remain aligned under the same policy

## 9. Current Admitted Corpus

The currently admitted stellar corpus contains one row family only:

- Sirius heliacal rising in the 139 AD Sothic anchor context

That row is supported, but not widened, by:

- SHS-002 as secondary scholarly support
- SHS-003 as secondary methodology support

This row is enough to support the present safe wording:

- "stellar heliacal validation is presently anchored by the Sirius / Sothic slice"

It is not enough to support:

- "stellar heliacal visibility is broadly validated across the named-star surface"

## 10. Immediate Next Artifact

The next useful document after this one is:

- a concrete stellar case ledger containing the current admitted row plus explicit candidate rows for expansion

That keeps the corpus inspectable before broader implementation expands.

## 11. Final Judgment

Stellar heliacal validation is already real.

Its weakness is not legitimacy.
Its weakness is breadth and corpus design.

The next improvement is therefore:
- expand from the admitted Sirius anchor into a small, explicit bright-star corpus with inspectable provenance

not:
- add new heliacal algorithms to a subsystem that already exists

## 12. Remaining External Gaps

The remaining gaps are now narrower and more explicit:

- no admitted non-Sirius stellar heliacal validation row yet exists
- no contrasting-declination bright-star row yet exists
- no admitted modern observational stellar study has yet been converted into a corpus row

Those are the real external-oracle gaps left in the stellar branch.