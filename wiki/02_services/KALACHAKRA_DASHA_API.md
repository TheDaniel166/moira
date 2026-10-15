# Kalachakra Dasha API

The selected profile is `bphs_santhanam_longitude_row_cycle_v1`, governed by the
[backend standard](../02_standards/KALACHAKRA_DASHA_STANDARD.md),
[source ledger](../06_roadmap/VEDIC_KALACHAKRA_SOURCE_RESEARCH_2026-10-12.md)
and [implementation plan](../06_roadmap/VEDIC_KALACHAKRA_IMPLEMENTATION_PLAN_2026-10-12.md).
It admits nine MD occurrences and optional nine full AD records per MD, preserving
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
assert sum(p.selectable for p in kalachakra_profiles().profiles) == 1
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

## Result semantics

Signs, row positions, cycle indices and path ordinals are zero-based. Nakshatra
and pada numbers are one-based. `path=[m]` identifies an MD occurrence and
`path=[m,a]` its full-axis AD. A repeated sign retains a different path. Child
row wrapping does not advance the parent's MD row cycle.

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
balance and nine-MD coverage. Deha/Jeeva always have `reference=natal_row`.

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

Catalogue/sequence results carry source and rule IDs and all fourteen conflict
decisions. Transitions report ordered occurrence edges, seams, visibility and
bounded classification. Both Cancer/Leo directions retain unresolved KC-10;
unclassified seams/reverse pairs are not asserted to be universally without
gati. Eligibility remains `not_evaluated`. Row totals are not lifespan estimates.

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
converted into caller errors or empty successful schedules. The actual OpenAPI
schema and `/v1/meta/routes` expose all five operations and their bounds.
