# Kalachakra Dasha API

The admitted profiles are `bphs_santhanam_longitude_row_cycle_v1` and
`rao_2000_longitude_continuous_v1`, governed by the
[backend standard](../02_standards/KALACHAKRA_DASHA_STANDARD.md),
[source ledger](../06_roadmap/VEDIC_KALACHAKRA_SOURCE_RESEARCH_2026-10-12.md)
and [implementation plan](../06_roadmap/VEDIC_KALACHAKRA_IMPLEMENTATION_PLAN_2026-10-12.md).
Each admits nine MD occurrences and optional nine full AD records per MD, preserving
repeated signs and birth clipping. Other traditions remain named research candidates.
Discovery and OpenAPI enumerate the same supported named ayanamsas.

## Python

All public types and operations are exported from `moira`, `moira.facade`,
`moira.vedic` and `moira.kalachakra`. The five operations also have `Moira`
instance wrappers. Source-only supplied sidereal computation requires no kernel:

```python
from moira import (
    KalachakraSeed, KalachakraEpoch, KalachakraProjection,
    kalachakra_profiles, kalachakra_sequence,
    project_kalachakra_sequence, current_kalachakra_periods,
)

profile_id = "bphs_santhanam_longitude_row_cycle_v1"
source = kalachakra_sequence(
    KalachakraSeed("sidereal", 34 + 50 / 60), profile_id=profile_id,
)
schedule = project_kalachakra_sequence(
    source, birth_epoch=KalachakraEpoch("jd_utc", 2451545.0),
    year_basis="savana_360",
)
active = current_kalachakra_periods(
    schedule, KalachakraEpoch("jd_utc", 2451545.0),
)
assert len(source.periods) == 9
assert schedule.generated_node_count == 90
assert active.status == "active" and len(active.active_line) == 2
assert sum(p.selectable for p in kalachakra_profiles().profiles) == 2
```

For date-derived input use the facade's reader; module-level astronomy calls
require an explicit `reader=` or an active reader context. No global kernel is
silently opened by a pure calculation:

```python
from datetime import datetime, timezone
from moira import Moira

engine = Moira()
derived = engine.kalachakra_for_datetime(
    datetime(2000, 1, 1, 12, tzinfo=timezone.utc), profile_id=profile_id,
    ayanamsa_system="Lahiri", projection=KalachakraProjection("julian_365.25"),
)
supplied_tropical = engine.kalachakra_sequence(
    KalachakraSeed("tropical", derived.provenance.moon_tropical_lon, "Lahiri"),
    profile_id=profile_id,
    birth_epoch=KalachakraEpoch("datetime", datetime(2000, 1, 1, 12, tzinfo=timezone.utc)),
    projection=KalachakraProjection("julian_365.25"),
)
assert derived.periods == supplied_tropical.periods
assert supplied_tropical.provenance.input_origin == "supplied_tropical"
```

`levels=1` returns nine MDs with `children_status=not_requested`; default level
two returns 90 full period nodes. `profile_id` is required. A projection requires
an explicit `savana_360` or `julian_365.25` clock; source-only results omit it.
No extra cycles, higher depths, arbitrary trees, time-fraction methods, custom
ayanamsa offsets, co-lord overrides or eligibility bypasses are admitted.

## REST

| Method and path | Operation |
| --- | --- |
| `GET /v1/dasha/kalachakra/profiles` | Profile, source/rule/conflict and candidate discovery; no kernel work |
| `POST /v1/dasha/kalachakra/sequence` | Supplied sidereal/tropical seed, optional explicit projection |
| `POST /v1/dasha/kalachakra/chart/sequence` | Aware natal timestamp, derive one Moon and one true ayanamsa |
| `POST /v1/dasha/kalachakra/current` | Direct seed and explicit query, projected bounded active line |
| `POST /v1/dasha/kalachakra/chart/current` | Chart-derived seed and explicit query, one astronomical computation |

Source-only request:

```json
{
  "profile_id": "bphs_santhanam_longitude_row_cycle_v1",
  "seed": {"basis": "sidereal", "moon_sidereal_lon": 45.8},
  "levels": 2
}
```

For projection add `birth_epoch` and `projection`; for `/current` additionally
provide `query_epoch`:

```json
{
  "profile_id": "bphs_santhanam_longitude_row_cycle_v1",
  "seed": {"basis": "sidereal", "moon_sidereal_lon": 45.8},
  "birth_epoch": {"kind": "jd_utc", "value": 2451545.0},
  "projection": {"year_basis": "savana_360"},
  "query_epoch": {"kind": "datetime", "value": "2000-01-01T12:00:00Z"}
}
```

For supplied tropical input, the seed instead contains `basis=tropical`,
`moon_tropical_lon`, and `ayanamsa_system`. It always requires `birth_epoch`,
including source-only requests, because the reduction needs an astronomical
epoch. Supplied tropical longitude is never relabelled as a derived Moon.

Chart request:

```json
{
  "profile_id": "bphs_santhanam_longitude_row_cycle_v1",
  "birth_datetime": "2000-01-01T12:00:00Z",
  "ayanamsa_system": "Lahiri",
  "projection": {"year_basis": "julian_365.25"},
  "levels": 2
}
```

Add `query_epoch` for `/chart/current`. All civil timestamps must be aware;
numeric/Unix timestamps and naive timestamps are rejected. Integers are accepted
for numeric angles and JDs, but booleans, numeric strings, nonfinite values and
extra fields are not. Longitudes must already be in `[0,360)`. `levels` is a strict
integer. Unknown or research-candidate profiles and unsupported clocks are 422s.
Astronomical JDs are preflighted within `[-10000000,10000000]`, then actual reader
coverage is enforced. Pure calendar projection instead requires finite,
representable endpoints.

## Rao 2000 profile and compatibility

Select `profile_id="rao_2000_longitude_continuous_v1"` on any of the same four
calculation routes or Python/facade operations. Discovery version `ved014.2`
lists both admitted profiles and their versions, source/rule/conflict IDs,
row namespace, continuation and Deha/Jeeva reference. The old candidate ID
`candidate_rao_2000_continuous` is not an executable alias. Other candidates
remain unselectable, and profile selection remains mandatory.

Rao version `ved014.rao2000.1` implements chapter 24 of the 2000 textbook:
whole-row longitude balance, continuous progression through four padas then the
other subgroup in the same Savya/Apasavya family, and nine forward AD occurrences
starting at each MD. Their weight sum is recomputed for each parent. For example,
Taurus/Taurus in the initial Savya sequence is `256/97` source years; the selected
Santhanam profile's value remains `256/100`.

Rao's Deha/Jeeva reference is `birth_nine_md_window`: the first/ninth emitted MD
signs, reversed for Apasavya. Its `coverage_years` uses the actual nine forward
MDs minus the elapsed part of the birth MD; it need not equal the natal-row total.
Rao's row IDs are `R2000/S1/1` through `R2000/A2/4`; each period identifies the
source row it occupies. `md_cycle_index` starts at zero and increments when the
eighth family row wraps to the first (a 72-occurrence family table); children
inherit the MD's cycle index.
Santhanam keeps its original row IDs and natal-row cycle semantics.

Rao's directed gati readings use `R2000_GATI` and include `markati`. Continuous
row seams can be classified under that source. Santhanam retains `KC_GATI`, its
unclassified row seams and unresolved KC-10 Cancer/Leo readings. Classification
metadata does not generate event predictions. Eligibility remains `not_evaluated`.

Markati requires occurrence context: `Vi Cn Le Ge` in Savya and `Ge Le Cn Vi`
in Apasavya. The central transition is a temporary reversal in those sequences.
The same pairs in ordinary `Ge Cn Le Vi` / `Vi Le Cn Ge` progression return
`classification=null` and `classification_status=not_classified_by_profile`.
The classifier reads neighbors from the selected source sequence, including
across row seams and outside the returned or birth-clipped window; it does not
emit extra periods. This corrects the unreleased Rao extension's pair-only
Markati classification in both MD and AD transitions.

The source decisions `R2000-01` through `R2000-09` are discoverable. In particular,
the profile explicitly carries the reconciled KC-03 star membership rather than
silently copying Table 45's defective heading. Footnote 64 governs the nine-MD
bound despite Exercise 34's ten printed entries. Footnote 65 prefers the 360-day
clock; choosing `julian_365.25` is an explicit Moira projection, not a claim of
textbook calendar parity. Both clocks remain available without a default.

```python
rao = kalachakra_sequence(
    KalachakraSeed("sidereal", 45 + 50 / 60),
    profile_id="rao_2000_longitude_continuous_v1",
)
assert [p.sign_index for p in rao.periods] == [7, 6, 5, 4, 3, 2, 1, 0, 8]
assert rao.birth.deha_jeeva_reference == "birth_nine_md_window"
assert rao.periods[1].children[0].denominator == 97
```

Santhanam's calculation version and sequence/current payloads are preserved.
Independent source tests and 648 frozen pre-refactor transport cases guard the
extension. Clients must accept the newly admitted profile and source-specific
metadata to consume Rao; the bounds remain levels 1-2 and 9/90 period nodes.

## Result semantics

Signs, row positions, cycle indices and path ordinals are zero-based. Nakshatra
and pada numbers are one-based. `path=[m]` identifies an MD occurrence and
`path=[m,a]` its full-axis AD. A repeated sign retains a different path. Child
row wrapping does not advance the parent's MD cycle.

Source-year values use exact, reduced ratios. For example `49/100` is serialized
as `{"numerator":"49","denominator":"100"}`. Strings preserve integers beyond
JavaScript's exact range. Components are bounded to 400 digits. These are output
evidence, not accepted arbitrary-rational request inputs. An admitted floating
longitude means its exact binary64 value; theoretical rational pada edges are
not snapped to that value.

Each period has `full_years`, nullable `visible_years`, and corresponding
`full_dates` / `visible_dates` when projected. Wholly pre-birth ADs retain full
records with `visibility=clipped_before_birth` and null visible intervals.
`birth` distinguishes row total, elapsed row, original-row remainder, birth-MD
balance and nine-MD coverage. `deha_jeeva_reference` is `natal_row` for
Santhanam and `birth_nine_md_window` for Rao.

Projected endpoints are UTC-derived Julian dates. The astronomical receipt
separately identifies UT1, TT, TDB, bound Delta-T, ephemeris identity, true
ayanamsa and the apparent geocentric true-ecliptic frame. Live-star ayanamsas
require the actual anchor; no polynomial fallback is silently substituted.
Calendar clocks are fixed-day engineering projections, not physical elapsed-time
or universal classical calendar claims.

Active intervals are `[start,end)`: a shared endpoint belongs to the successor.
The first instant is birth; the exact final endpoint is `after_coverage`.
Outside queries return 200 with `before_birth` or `after_coverage` and an empty
active line. They do not generate more cycles. A valid source sequence may have
a residual too short to project at the chosen JD origin; the projection fails
explicitly while the source-only calculation remains available.

The catalogue carries fourteen KC and nine R2000 decisions; each calculation
carries its selected profile's source, rule and conflict IDs. Transitions report
ordered occurrence edges, seams, visibility and bounded classification.
Santhanam retains unresolved KC-10 for both Cancer/Leo directions; Rao carries
its separately sourced directed classifications. An unclassified edge is not
asserted to be universally without gati. Eligibility remains `not_evaluated`.
Row totals are not lifespan estimates.

## Errors

Errors retain the common envelope and `X-Request-ID` correlation:

| HTTP | Code | Meaning |
| --- | --- | --- |
| 422 | `validation_error` | Invalid caller input or incompatible request |
| 422 | `kalachakra_projection_unrepresentable` | A positive source interval collapses/overflows under projection; bounded path/reason details |
| 422 | `kalachakra_epoch_out_of_coverage` | Birth epoch outside serving ephemeris coverage |
| 503 | `kalachakra_resource_unavailable` | Missing ephemeris, lunar clock identity or required anchor |
| 503 | `kernel_not_ready` | Existing outer facade/startup kernel-readiness boundary |
| 500 | `kalachakra_internal_invariant` | Generated result or serializer invariant failure; sanitized, logged with request ID |

Bad requests are rejected before astronomical work. Internal defects are not
converted into caller errors or empty successful schedules. A missing anchor
catalogue key returns `503`; internal `KeyError` or `IndexError` failures during
time binding, ayanamsa reduction or lunar computation return the sanitized
`kalachakra_internal_invariant` `500`, not a resource outage. The actual OpenAPI
schema and `/v1/meta/routes` expose all five operations and their bounds.
