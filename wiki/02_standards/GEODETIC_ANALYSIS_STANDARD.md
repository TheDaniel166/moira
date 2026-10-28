# Geodetic Analysis Standard

Version: 1.3
Date: 2026-10-28
Status: Python engine implementation with `Moira` facade methods (section 7).

REST admission is recorded in `GEODETIC_BACKEND_STANDARD.md` section 7:
- kernel-free houses, geometry, sensitivity and uncertainty;
- per P10-03b, overlay, comparison, loci and chart-backed houses, in direct
  and chart-backed forms.

Timing has no REST admission. `Moira.geodetic_compare` takes a separate
`place_error_policy`; when it is omitted, `error_policy` governs both bodies
and places.

This document governs the six Geodetic expansions and their common body
inputs. Existing scalar/dictionary APIs retain their shapes. Undefined geometry
refusals and corrected fixed-target orb windows are deliberate corrections.

## 1. Geometry and nonlinear diagnostics

`moira.geodetic.geodetic_geometry` reports the tropical MC, ARMC, plane
intersection norm, meridional altitude sine, rising rate, and geometry status.
Coincident planes and zero-rising-rate branch ties have no published ASC.
Finite angles are normalized to `[0, 360)`, including floating wrap edges.
Latitude conventions and the existing Earth obliquity/pole guards remain.

The independent spherical altitude relation is
`sin(h)=sin(phi) sin(delta)+cos(phi) cos(delta) cos(H)`.
For the tropical MC degree `L`, `delta_MC=asin(sin(epsilon) sin(L))`.
Thus a meridional tie occurs where `cos(phi-delta_MC)=0`. Whole-box sine and
product intervals test this manifold before sensitivity or nonlinear sampling.

`GeodeticDiagnosticPolicy` requires a positive angular residual tolerance and
records maximum evaluations and adaptive depth. The diagnostic samples centers,
faces, edges, corners and interior critical meridians, then refines cells with
large residuals. It reports domain intersections, base conditioning, sampled
ASC deviations/circular arcs, nonlinearity, or budget exhaustion. MC retains
its direct longitude mapping and local MC estimate. A complete sampling schedule
is **not** a confidence interval, global enclosure, or guaranteed error bound.

## 2. Shared bodies and provenance

`moira.geodetic_inputs` provides:

- `geodetic_snapshot_at(jd_ut1, bodies, reader=...)` for explicit selected
  bodies through canonical `planet_at` apparent geocentric reductions.
- `geodetic_snapshot_from_chart` for a `moira.chart.ChartContext`, without
  recalculation. The facade's lighter `Chart` is a different epoch contract.
- `geodetic_snapshot_from_positions(..., source_frame=...)` for supplied
  **tropical** longitudes and caller-declared corrections/frame/known epochs.

Snapshots retain ordered immutable positions, requested aliases, stable IDs,
shared `SmallBodyIdentity`/NAIF IDs where resolved, tropical and selected-zodiac
longitudes, available latitude/speed, source kind, frame, corrections, and known
UT1/TT epochs. Sidereal snapshots require an explicit reference offset. A named
ayanamsa system is metadata for that supplied offset; it is not recalculated.
The snapshot epoch is the offset reference epoch when known.

Examples of admitted body names are `Sun`, `asteroid:Ceres`,
`asteroid:Chiron`, `asteroid:Eris`, and `comet:1P/Halley` or `comet:Halley`.
Centaurs/TNOs reuse the asteroid catalog namespace. Ambiguous `Halley` is
refused. Duplicate aliases of one canonical identity are refused. Manual labels
remain static and do not acquire an ephemeris. Numeric NAIF mover IDs are not
admitted: existing numeric transit targets mean longitude degrees.

Default body failure policy raises. Explicit `error_policy="collect"` retains
typed body failures and marks the snapshot incomplete. There is no silent
omission, substitution, implicit full catalog, extrapolation, or download.
ChartContext and PlanetData do not expose every reduction/resource receipt;
`resource_receipt_status="not_exposed_by_source"` records that limit. Missing
provenance is never fabricated. Timing admits actual resources separately.

## 3. Twelve houses and static overlays

`moira.geodetic_analysis.geodetic_house_chart` requires a typed location,
obliquity and explicit house system. It derives ARMC from the **tropical** MC
and calls `houses_from_armc` with `HousePolicy.strict()` by default. Explicit
fallback policies preserve the house engine's requested/effective system and
reason. The house engine applies the zodiac offset, including Whole Sign
anchoring; equatorial geometry is never shifted by ayanamsa.

The result retains `GeodeticChart`, `HouseCusps`, twelve cusps, four separate
angle targets, location and declared frame/reference epochs. Systems where
MC is not cusp 10 and ASC is not cusp 1 retain that distinction. A branch
disagreement with the house engine raises instead of relabelling geometry.
Solar-dependent systems require a tropical Sun explicitly. Comparisons may
reuse an explicitly included Sun snapshot; no additional Sun is calculated.

`geodetic_natal_overlay` requires an explicit `AspectPolicy`. It reuses
`assign_house` and `aspects_to_point`, retains cusp-boundary placement witnesses,
and records exact separation/orb/allowed orb. Four angles are default targets;
cusp contacts require `include_cusps=True`. Coincident target names are listed
explicitly. Contacts are static: `applying` remains `None` even if natal speed
is available. Frame, known/unknown epochs, zodiac, offset and system metadata
must match exactly; conversions are never guessed. Partial snapshots remain
visibly incomplete through their overlay and comparison results.

## 4. Inverse geographic angle loci

`moira.geodetic_curves.geodetic_angular_loci` accepts one snapshot, obliquity,
selected angles and a `GeodeticCurvePolicy`. MC/IC are meridians. For ASC/DSC,
the fixed ecliptic degree is projected at **ecliptic latitude zero**:

`cos(H)=-tan(phi) tan(delta)`, `ARMC=RA+H`.

H is negative for rising and positive for setting. The inverse ARMC mapping
returns tropical geographic longitude. Every retained sample passes the
forward angle/branch test and retains a residual/rising-rate witness. Equinox
targets require no division by sin(delta). Poles, circumpolar regions,
coincident planes, branch mismatch and tangent endpoints are explicit
exclusions. Critical latitude samples prevent bridging invalid branches.
Antimeridian crossings are refined on the analytic locus and split into
segments with equivalent +/-180-degree boundary vertices. MC/IC remain valid
without an ASC. Sampling density, work limit and incomplete refinement are
inspectable; straight interpolation between vertices is not analytic truth.

These are loci of a **zodiacal longitude**, not physical rising/setting tracks
of a high-latitude comet. Refraction, terrain, ellipsoidal/physical-horizon
geometry and 3D mundane placement remain outside this implementation.

## 5. Comparisons of supplied places

`compare_geodetic_locations` reuses one snapshot at every named location.
`GeodeticNamedLocation` requires a unique stable ID; display names may repeat.
Default output order is caller order. Optional `minimum_contact_orb` ordering
is explicitly geometric, with stable input-order ties. It is not a suitability
or astrological outcome score. The baseline is the first valid input location,
independent of sorting. Results include circular angle differences, house
changes, added/removed contact keys and explicit collected calculation errors.
Default failures raise; collecting is caller-selected. Duplicate IDs and
other checked structural errors always raise.

## 6. Fixed-reference transit timing

`moira.geodetic_timing.GeodeticFixedReference` freezes location, obliquity,
reference UT1/known TT, selected angles, zodiac and reference ayanamsa. Only
`frozen_tropical_anchor` is admitted. Sidereal display degrees map back with
that same reference offset; no event-time ayanamsa changes the target.

`find_geodetic_transits` requires explicit `(aspect_angle_deg, orb_deg)` pairs
and `GeodeticTimingPolicy(step_days=...)`. Undirected angles 0..180 expand to
both directed branches except conjunction/opposition, which are each searched
once. Events and windows sort chronologically. Event epochs are **JD UT1**,
not civil UTC. Canonical ephemeris UT1/TT/TDB/Delta-T identity is retained.

The private fixed-target batch core is shared with `transits_aspects`. Legacy
bulk admission and the server's imported `_require_natal_aspect_mover` guard
are unchanged. The new wrapper resolves qualified asteroid/comet identities
before scanning. Comets use canonical resolver sampling, never the asteroid
native evaluator. Existing native/resolver series and step guards remain in
the legacy path; canonical evaluations confirm refined contacts.

One longitude memo and stationary-point scan serve every target. Bounded
adaptive subdivision checks circular steps and curvature. Ordinary roots use
bracketed refinement. Touching roots require a refined zero of finite-
difference angular velocity plus an accepted angular residual. Nonisolated
near-continuous contacts and unresolved extrema are visibly incomplete rather
than fabricated finite event lists. Connected orb windows may contain several
direct/retrograde passes. Orb windows are searched across the bounded covered
study interval rather than assuming two days is sufficient.

Coverage uses actual disjoint TDB descriptors, route availability, the
planetary clock, Earth, Sun and the provider's Jupiter/Saturn deflection routes
where required. Comet coverage follows the first SmallBodyKernel selected by
the canonical provider. Descriptor seams are scan splits; true gaps are never
bracketed. Padding reserves half-day speed samples, the caller-declared maximum
light-time (default one day), and a small clock margin. Evaluated distances
must satisfy that light-time policy. A larger reserve is caller-selectable for
distant objects. This padding policy is not a global trajectory enclosure.
Coverage resources retain content hashes, catalog metadata when actually
available, disjoint intervals and descriptor boundaries. These are candidate
coverage receipts, not invented per-evaluation reduction receipts.

Default coverage policy requires the full requested span. Explicit
`allow_partial` returns available segments, gaps and an incomplete result.
Requested endpoints must bind to a supported planetary ephemeris clock even
for partial body coverage; an unavailable clock raises. Budgets bound
evaluations, subdivisions and depth. Orb entry/exit statuses distinguish
`found`, `outside_study_span`, `outside_coverage`, `coverage_gap`,
`search_budget_exhausted` and unresolved boundaries. Missing times never
prove the absence of an event. Completion is only under the declared finite
scan policy, not a mathematical guarantee against arbitrarily oscillatory
motion between samples. Reader/clock identity changes abort the result.

## 7. Facade access

Six `Moira` methods compose the owning modules with the engine's own reader.
They add no doctrine; each equals the hand-built composition exactly
(`tests/unit/test_geodetic_facade.py`). No `moira.facade` module-level export
or REST route is added.

| Method | Composition |
| --- | --- |
| `geodetic_houses(location, dt, system, ...)` | `geodetic_house_chart` at `dt`'s JD UT1 and engine-clock TT |
| `geodetic_overlay(natal_dt, location, system, *, aspect_policy, ...)` | `geodetic_snapshot_at`, then the place's figure on the snapshot's epochs and offset, then `geodetic_natal_overlay` |
| `geodetic_compare(natal_dt, locations, system, *, aspect_policy, ...)` | snapshot, then `compare_geodetic_locations` |
| `geodetic_loci(natal_dt, ...)` | snapshot, then `geodetic_angular_loci` |
| `geodetic_transits(location, reference_dt, mover, start_dt, end_dt, ...)` | `GeodeticFixedReference` from `geodetic_chart_at_location`, then `find_geodetic_transits` |
| `geodetic_uncertainty(chart, uncertainty, *, policy)` | `diagnose_geodetic_uncertainty` |

Epochs: a civil datetime becomes JD UT1 through `utc_to_ut1`; TT is the
engine-clock TT used by snapshots, and obliquity is true obliquity at that TT.
The snapshot is built first and a place's figure reuses its UT1/TT, frame and
offset, which overlays and comparisons require.

Zodiac lanes: tropical refuses an `ayanamsa_system`; sidereal requires one, and
its offset is `moira.sidereal.ayanamsa` at JD UT1 (that function is contracted
for UT). Bodies default to the ten planets. `aspect_policy` and the house
`system` are required, as in the owning functions. Solar-dependent house
systems need an explicit tropical `sun_longitude`; none is calculated
implicitly. Timing locations pass through `geodetic_chart_at_location`, so a
geocentric latitude is refused.

## 8. Example

```python
from moira.geodetic import GeodeticLocation
from moira.geodetic_inputs import geodetic_snapshot_at
from moira.geodetic_analysis import geodetic_house_chart, geodetic_natal_overlay
from moira.geodetic_timing import (
    GeodeticFixedReference, GeodeticTimingPolicy, find_geodetic_transits,
)
from moira.obliquity import true_obliquity
from moira.aspects import AspectPolicy
from moira.constants import HouseSystem

# reader is an explicitly configured pool containing the requested kernels.
snapshot = geodetic_snapshot_at(
    2451545.0, ["Sun", "asteroid:Eris", "comet:1P/Halley"], reader=reader,
)
figure = geodetic_house_chart(
    GeodeticLocation(40.0, -74.0), obliquity=true_obliquity(snapshot.jd_tt),
    system=HouseSystem.EQUAL, jd_ut1=snapshot.jd_ut1, jd_tt=snapshot.jd_tt,
)
overlay = geodetic_natal_overlay(figure, snapshot, aspect_policy=AspectPolicy(tier=0))
reference = GeodeticFixedReference(figure.angles, snapshot.jd_ut1, snapshot.jd_tt)
timing = find_geodetic_transits(
    reference, "comet:Halley", 2451545.0, 2451575.0,
    aspects=((0.0, 1.0), (90.0, 1.0)),
    policy=GeodeticTimingPolicy(step_days=0.5), reader=reader,
)
```

## 9. Verification scope

The focused `test_geodetic_*` unit files cover geometry, whole-box diagnostic
semantics, identity/frame/epoch contracts, composition with house/aspect owners,
inverse altitude/forward witnesses, comparison ordering/failures, analytic
synthetic timing, gaps, seams and budgets. Transit regressions preserve legacy
admission and provider/solver behavior. Integration tests use installed
resources for a major planet, asteroid, centaur, TNO and comet. The comet test
can take an explicitly supplied released Halley shard, verifies its size/hash
against the repository manifest, and certifies that shard only. No test
downloads or mutates installed resources. Provider parity is integration
evidence, not new universal ephemeris-accuracy certification.

Primary derivation references: [USNO altitude equation](https://aa.usno.navy.mil/faq/alt_az),
[NAIF SPK coverage and time contracts](https://naif.jpl.nasa.gov/pub/naif/toolkit_docs/C/req/spk.html),
and [JPL Horizons comet-solution limits](https://ssd.jpl.nasa.gov/horizons/manual.html).
