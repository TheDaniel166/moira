# P-GAP-F1 Facade Parity Review

Version: 0.5
Date: 2026-06-15
Status: P-GAP-F1A through P-GAP-F1D implemented; remaining facade bundles require explicit approval
Scope: decision review for whether REST-admitted families should receive
high-level `Moira` convenience methods

## 1. Review Boundary

This began as a planning and admission review. P-GAP-F1A, P-GAP-F1B,
P-GAP-F1C, and P-GAP-F1D have since been implemented after explicit approval; the remaining
bundles are still admission decisions, not automatic implementation authority.

The public `Moira` facade is a protected API surface. The relevant facade
mixins carry machine contracts that mark API changes as requiring human
confirmation. Therefore this review records the approved method additions and
deferrals. P-GAP-F1A, P-GAP-F1B, P-GAP-F1C, and P-GAP-F1D have mutated the
facade.

Inspected code truth:

- `moira.facade.Moira`
- `moira._facade_astronomy`
- `moira._facade_classical`
- `moira._facade_predictive`
- `moira._facade_spatial`
- `moira._facade_special`
- live REST families recorded in
  `docs/architecture/MOIRA_SERVER_REST_FACADE_INIT_GAP_LEDGER.md`

## 2. Decision Rule

Do not add a `Moira` method merely because a REST route exists.

Add a facade convenience method when all are true:

- the computation is already stable as an engine/root import surface
- the method can delegate without reimplementing doctrine
- the method improves Python ergonomics over raw module calls
- the method has a coherent owner mixin
- the method name is not narrower than the engine result it returns
- the method will not collapse distinct REST transport products into one vague
  facade concept

Keep REST-only when any are true:

- the route is website/UI transport support
- the route is a server inspection or reduction packet
- the route exists mainly for OpenAPI/client serialization
- the route depends on request/response envelopes rather than engine vessels
- adding the method would imply doctrine maturity beyond the engine truth

## 3. Recommended Facade Additions

P-GAP-F1A and P-GAP-F1B are implemented. The remaining families should receive
`Moira` convenience methods only after explicit approval.

| Family | Recommendation | Proposed owner | Reason |
|---|---|---|---|
| Panchanga | implemented | `VedicFacadeMixin` | Stable root functions exist; chart-backed REST routes expose useful Python ergonomics that the facade previously lacked. |
| Shadbala | implemented | `VedicFacadeMixin` | Stable root functions and profiles exist; wrapper delegates without changing doctrine. |
| Jaimini | implemented | `VedicFacadeMixin` | Stable karaka/profile/pair functions exist; facade convenience reduces raw module plumbing. |
| Ashtakavarga | implemented | `VedicFacadeMixin` | Stable result/profile/sign/transit functions exist; route admission already proved bounded transport semantics. |
| Varga | implemented | `VedicFacadeMixin` | Stable direct divisional functions exist; facade exposes named/generic chart projections without returning REST envelopes. |
| Huber | implemented | `ClassicalFacadeMixin` | Stable direct-cusp and age-point functions exist; methods accept caller-supplied `HouseCusps` and delegate. |
| Nine Parts | implemented | `ClassicalFacadeMixin` | One stable aggregate root function exists; facade method returns the engine aggregate directly. |
| Lord of the Orb | implemented | `AnnualLordFacadeMixin` | Doctrine is explicitly declared in `moira.lord_of_the_orb` and P12-10; facade wrappers preserve caller-supplied birth planetary-hour ruler truth. |
| Planetary Hours | already present | `PredictiveFacadeMixin` | `Moira.planetary_hours(...)` already delegates to the owning module. No parity work needed. |
| Ayanamsa / sidereal conversion utilities | implemented | `VedicFacadeMixin` | Mechanical sidereal primitives are stable root functions and useful at the facade without creating route envelopes or doctrine claims. |

Implemented Vedic facade bundle:

- `panchanga(...)`
- `panchanga_profile(...)`
- `shadbala(...)`
- `shadbala_profile(...)`
- `jaimini_karakas(...)`
- `jaimini_profile(...)`
- `ashtakavarga(...)`
- `ashtakavarga_profile(...)`
- `varga(...)`
- `shodashvarga(...)`

Implemented chart-backed companions keep direct longitude inputs and chart
inputs distinct:

- `shadbala_for_chart(...)`
- `jaimini_karakas_for_chart(...)`
- `ashtakavarga_for_chart(...)`
- `varga_named(...)`
- `varga_for_chart(...)`
- `shodashvarga_for_chart(...)`
- local profile helpers for Shadbala, Jaimini, and Ashtakavarga

Implemented classical/modern facade bundle:

- `huber_house_zones(...)`
- `huber_age_point(...)`
- `huber_age_point_contacts(...)`
- `huber_dynamic_intensity(...)`
- `huber_intensity_at(...)`
- `huber_chart_intensity_profile(...)`
- `nine_parts(...)`

Implemented annual-lord specialist facade bundle:

- `lord_of_orb(...)`
- `current_lord_of_orb(...)`

Implemented utility parity cleanup:

- `ayanamsa(...)`
- `tropical_to_sidereal(...)`
- `sidereal_to_tropical(...)`
- `list_ayanamsa_systems(...)`

## 4. Specialist Deferrals

These should not be added in the first facade parity bundle.

| Family | Recommendation | Reason |
|---|---|---|
| Lord of the Turn | defer | Caller-supplied Solar Return profile route exists, but facade admission should wait for annual-lord API design across Varshaphal/Tajika surfaces. |
| Electional scored windows | defer | REST admits server-defined predicate/scorer profiles; `Moira.electional_windows` currently accepts a Python predicate. Do not collapse those two models. |
| Sothic | defer | Previously deferred for specialist review; do not reintroduce by facade parity. |
| Longevity | defer | High-stakes doctrine and public-language safeguards remain unresolved. |

## 5. REST-Only Surfaces

These should remain REST-only or lower-level module/import surfaces.

| Family | Recommendation | Reason |
|---|---|---|
| Website chart-wheel packets | keep REST-only | UI transport support, not an engine-level astrological technique. |
| Locations | keep REST-only | Server/UI lookup support; do not introduce location-data authority into the core facade casually. |
| Pipeline inspection aliases | keep REST-only | Reduction visibility route family; useful for HTTP clients, not a `Moira` convenience method. |
| Batch envelopes | mostly keep existing facade shape | Batch engine helpers already exist; REST response envelope symmetry is not a facade obligation. |
| Frame-specific positions | already present | `heliocentric`, `planetocentric`, `ssb_chart`, and `received_light` already exist in `AstronomyFacadeMixin`. |
| Generic phenomena | already present | `phenomena`, `proximity_events`, `solar_condition_at`, and `solar_condition_events` already exist in `SpecialTopicsFacadeMixin`. |
| Sidereal/Nakshatra utilities | facade admitted | Low-level ayanamsa and longitude-conversion functions are now facade utilities; `Moira.nakshatras(chart)` already existed. |
| Harmograms | keep module-level for now | Research/spectral surface is root-exported; first-class facade methods should wait until chart-backed sampling policy is admitted. |

## 6. Proposed Implementation Workflow

Do not implement all parity methods at once.

1. `P-GAP-F1A` Vedic facade convenience bundle
   - status: implemented in `moira._facade_vedic.VedicFacadeMixin`
   - added Panchanga, Shadbala, Jaimini, Ashtakavarga, and Varga wrappers
   - wrappers delegate to owning modules/root functions
   - `Moira` now inherits `VedicFacadeMixin`
   - focused facade tests live in `tests/unit/test_vedic_facade.py`

2. `P-GAP-F1B` Classical/modern facade convenience bundle
   - status: implemented in `moira._facade_classical.ClassicalFacadeMixin`
   - added direct-cusp Huber wrappers and one Nine Parts aggregate wrapper
   - Huber methods are explicitly prefixed with `huber_` to preserve technique
     identity
   - focused facade tests live in `tests/unit/test_classical_facade.py`

3. `P-GAP-F1C` Annual-lord specialist facade bundle
   - status: implemented in
     `moira._facade_annual_lords.AnnualLordFacadeMixin`
   - added Lord of the Orb wrappers after explicit API-change approval
   - preserve the declared caller-seeded boundary from
     `moira.lord_of_the_orb` and P12-10
   - review Lord of the Turn separately because its Solar Return profile
     semantics are tied more closely to Varshaphal/Tajika annual-chart policy
   - do not derive birth planetary hour inside Lord of the Orb facade methods

4. `P-GAP-F1D` Utility parity cleanup
   - status: implemented in `moira._facade_vedic.VedicFacadeMixin`
   - direct ayanamsa/sidereal conversion was admitted as `Moira` utility
     methods
   - keep website, locations, pipeline, and rendering support out of `Moira`

## 7. Verification Requirements For Future Implementation

For each approved facade method:

- test that the method delegates to the same engine function as the root import
- test chart-backed wrappers with existing chart fixtures where possible
- test direct wrappers with finite caller-supplied longitude maps
- test missing required bodies or houses reject clearly
- test no route envelope classes are returned from facade methods
- run `py_compile` on changed facade files
- run focused facade tests

## 8. Review Result

P-GAP-F1 decision is complete, and P-GAP-F1A through P-GAP-F1D are implemented.

Implemented:

- `P-GAP-F1A` Vedic facade convenience bundle
- `P-GAP-F1B` Classical/modern facade convenience bundle
- `P-GAP-F1C` Annual-lord specialist facade bundle
- `P-GAP-F1D` Utility parity cleanup

No additional facade bundle is currently recommended from this review without
a new explicit admission decision.

Do not implement remaining facade changes automatically from this review
because the facade mixins explicitly require human confirmation for API
changes.
