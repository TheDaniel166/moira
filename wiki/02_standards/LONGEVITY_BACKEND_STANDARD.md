# Longevity Backend Standard

Version: 0.1
Date: 2026-06-13
Status: conservative backend standard for Phase 12 doctrine evaluation

## Scope

This standard governs the traditional longevity candidate surface:

- `moira.longevity`

It covers:

- hyleg selection
- alcocoden identification
- dignity scoring at the hyleg degree
- Ptolemaic planetary year tables
- house-based selection of minor, mean, or major years
- the `HylegResult` vessel

It does not admit public REST routes. Longevity remains deferred for doctrine
and validation.

## High-Stakes Boundary

Longevity calculations are interpretively high-stakes. Moira must not present
this subsystem as medical, actuarial, predictive, or counseling truth.

Any future public surface must state plainly that this is a traditional
astrological doctrine product, not a life-expectancy model and not advice.

No website or REST route should expose longevity until doctrine, provenance,
validation, language, and safeguards are stronger than the current backend
candidate.

## Authority And Provenance

The engine documents its traditional sources as:

- Bonatti, *Book of Astronomy*, Treatise 5
- al-Qabisi, *Introduction to Astrology*
- Abu Ma'shar, *Great Introduction*

The implementation also uses:

- Ptolemaic planetary year tables
- Egyptian bounds from `moira.egyptian_bounds`
- domicile and exaltation tables from `moira.dignities`
- triplicity scoring from `moira.triplicity`
- Chaldean face rulers
- angular, succedent, and cadent house categories from `moira.dignities`

This standard does not claim that all historical variants of
hyleg/alcocoden doctrine are represented.

## Governing Objects

The admitted backend objects and constants are:

- `HylegResult`
- `PTOLEMAIC_YEARS`
- `EGYPTIAN_BOUNDS`
- `FACE_RULERS`

The admitted computations are:

- `dignity_score_at(planet, longitude, is_day_chart)`
- `find_hyleg(planet_positions, house_cusps, is_day_chart)`
- `calculate_longevity(planet_positions, house_cusps, is_day_chart)`

The current result vessel includes:

- `hyleg`
- `hyleg_lon`
- `alcocoden`
- `alcocoden_score`
- `years_minor`
- `years_mean`
- `years_major`
- `house`
- `granted_years`

## Current Computation Truth

The current backend:

- consumes direct planet longitude and house cusp inputs
- expects at minimum the classical seven planets for complete dignity scoring
- accepts `Ascendant` and optionally `Lot of Fortune` in the point map
- receives `is_day_chart` from the caller
- selects the hyleg through a documented Bonatti priority order
- uses dignity score at the hyleg degree to identify the alcocoden
- selects granted years by the alcocoden's house type

The current backend does not independently compute:

- chart positions
- house cusps
- sect
- Lot of Fortune
- bounds beyond the delegated Egyptian bounds table
- broader testimony, affliction, aspect, or bonification logic

## Doctrine Gaps Before REST

Public route admission is blocked until the following are decided and tested:

- exact hyleg candidate eligibility doctrine
- day/night and sect derivation policy
- accepted house system or house-frame policy
- direct cusp input versus chart-backed derivation policy
- Lot of Fortune formula and sect reversal policy
- treatment of the Ascendant as a hyleg candidate
- tie-break policy among alcocoden candidates
- dignity weighting and participating triplicity policy
- aspect testimony, benefic/malefic modification, and ray doctrine if admitted
- whether minor/mean/major year selection by house type is sufficient
- language restrictions for public and website exposure
- validation examples from named traditional sources

Until those decisions exist, REST transport must not be designed.

## Required Transport Invariants If Ever Admitted

Any future transport must preserve:

- requested chart or direct-input source
- all input planet longitudes
- all house cusps
- requested and effective house system if chart-backed
- sect source and derived day/night state
- Lot of Fortune source and formula policy
- hyleg candidate list
- hyleg eligibility decisions
- rejected candidates and rejection reasons
- dignity component scores for each alcocoden candidate
- alcocoden tie-break truth
- Ptolemaic year table values used
- alcocoden house placement
- granted-years selection rule
- warnings and limitations

Any future transport must reject:

- non-finite longitudes
- malformed house cusp lists
- missing required luminaries
- missing classical planet positions when complete scoring is requested
- unknown planet names
- ambiguous sect state
- hidden or implicit Lot of Fortune derivation
- attempts to request interpretive life-expectancy claims

## Validation Requirements

There is no dedicated longevity test suite named in the Phase 12 ledger.
Before route design, the backend must gain focused tests for:

- dignity scoring components
- Egyptian bound scoring
- face scoring
- triplicity scoring with day/night policy
- hyleg priority order
- hyleg fallback behavior
- alcocoden candidate ranking
- tie-break behavior
- house type to minor/mean/major year selection
- malformed input rejection
- deterministic result fields

Any future REST work must add adversarial transport tests for non-finite
values, incomplete charts, ambiguous sect, malformed houses, and unsafe public
language.

## REST Admission Guidance

Current status:

- `defer_for_doctrine`

No REST route should be implemented from this standard alone. The next valid
step is a doctrine packet with examples and validation fixtures, not transport
design.

If admitted later, the first public route should be diagnostic and
truth-preserving, not interpretive. It should expose candidate reasoning and
warnings rather than presenting a single unexplained number.

## Non-Goals

This standard does not admit:

- public REST routes
- website exposure
- life expectancy prediction
- medical, health, or counseling claims
- interpretive text generation
- death prediction
- unqualified chart-backed automation
- hidden sect or Lot of Fortune derivation
- historical-variant blending
- `/v1/special/*` exposure
