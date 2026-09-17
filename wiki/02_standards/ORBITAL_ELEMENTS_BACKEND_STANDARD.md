# Orbital Elements Backend Standard

Version: 1.1<br>
Date: 2026-09-15<br>
Status: Orbital Core Stages 1 and 2 implemented; release evidence incomplete
Scope: source-receipted osculating elements and apsidal passages from inertial SPK states

This standard governs the strict orbital-core surfaces:

- `moira.orbits.osculating_elements`
- `moira.orbits.OsculatingElements`
- `moira.orbits.apsidal_passages`
- `moira.orbits.ApsidalPassages`
- its body, source, gravity, frame, time, singularity, and undefined-field
  receipts
- the planet-only `/v1/orbits/elements` and `/v1/orbits/distance-extremes`
  adapters

The historical `orbital_elements_at` and `KeplerianElements` names remain as a
planet-only compatibility adapter. `distance_extremes_at` is the corresponding
planet-only passage adapter.

This standard does not govern visual-binary Campbell elements, Uranian mean
elements, catalog-supplied elements, apparent chart positions, orbital nodes,
or an orbit-classification product.

---

## 1. Public Entry Point

```python
osculating_elements(
    body: str | int,
    jd_ut: float,
    *,
    center: OrbitalCenter,
    frame: OrbitalFrame,
    reader: KernelReader | None = None,
) -> OsculatingElements
```

`jd_ut` means UT1 Julian Day. `center` and `frame` are required policy choices;
there is no implicit center or frame on the strict API. The function resolves
one body, binds one immutable reader-pool snapshot, constructs one exact state
and source receipt, rotates position and velocity through the same
instantaneous matrix, and extracts one conic.

The strict function does not apply light-time, aberration, deflection,
nutation outside the selected frame construction, topocentric displacement,
or zodiac doctrine.

---

## 2. Body And Center Admission

The strict core admits:

| Target kind | NAIF endpoint | Required center |
|---|---:|---|
| Mercury, Venus, Earth | `199`, `299`, `399` | `SUN` |
| Mars through Pluto | DE-series system barycenters `4` through `9` | `SUN` |
| Earth-Moon barycenter | `3` | `SUN` |
| Moon | `301` | `EARTH` |
| Sovereign catalog asteroid | catalog NAIF ID | `SUN` |
| Sovereign catalog comet | catalog NAIF ID | `SUN` |

The Sun is a center, not a Sun-centered target. The Moon is not silently
reinterpreted as heliocentric. Calculated points, fixed stars, deep-sky
objects, lots, nodes, and unknown or ambiguous names fail with a structured
orbital error.

Small-body identity and availability are distinct. A body can resolve in the
catalog yet fail with `OrbitalBodyNotLoadedError` when its governed release is
not installed.

---

## 3. Time Contract

The declared chain is:

```text
caller UT1 JD -> source-owned Delta T -> TT JD -> NAIF naif0012 -> TDB JD
```

- UT1 is retained as `jd_ut`.
- TT governs precession, nutation, obliquity, and the output `epoch_tt`.
- TDB is the only epoch passed to built-in SPK segment evaluation and is
  retained as `epoch_tdb`.
- `tdb_minus_tt_seconds`, `delta_t_seconds`, the Delta-T source product and
  retarget mode, identity-convergence count, and TT/TDB iteration count are
  returned.

TT/TDB uses the constants and implicit equation in official NAIF
`naif0012.tls`, SHA-256
`678e32bdb5a744117a467cd9601cd6b373f0e9bc9bbde1371d5eee39600a039b`.
The bounded fixed-point solution uses the same policy in both directions.

Public `SpkReader` and `KernelPool` position/evaluator methods preserve their
TT-facing signatures and convert exactly once. Private capabilities with
`_tdb` in their names consume raw TDB. Third-party legacy readers retain their
old TT protocol but do not acquire strict source-receipt claims.

---

## 4. State And Coverage Contract

The strict route requires atomic state-with-receipt evaluation. A state source
records every routed leg:

- center and target NAIF IDs and traversal sign;
- SPK segment type and exact closed TDB coverage;
- kernel content label, SHA-256, byte count, and pool priority;
- planetary ephemeris identity where applicable; and
- catalog ID, version, manifest SHA-256, release timestamp, and observed-arc
  restriction where applicable.

`KernelPool` fixes one reader-order snapshot for the operation. Direct,
reverse, and center-chain routes add both position and velocity with the same
signs. Coverage is a list of exact closed intervals, not a min/max envelope;
a gap is not filled by interpolation.

Public and REST receipts never expose a local filesystem path.

---

## 5. Gravity Policy

The two-body gravitational parameter is selected from the official JPL
Horizons `gm_Horizons.pck` artifact retrieved 2026-09-15, SHA-256
`169cfed3b0927e73929d0a1b5c931f9afb5167a83b921064127ffc54a673df0c`,
15,428 bytes. The last textual PCK assignment wins.

| Target | Components summed | Rule |
|---|---|---|
| Planet center | Sun + planet body | `SUN_PLUS_PLANET_BODY` |
| Planet system barycenter | Sun + planet system | `SUN_PLUS_PLANET_SYSTEM` |
| Earth-Moon barycenter | Sun + Earth-Moon system | `SUN_PLUS_EARTH_MOON_SYSTEM` |
| Moon about Earth | Earth + Moon | `EARTH_PLUS_MOON` |
| Asteroid or comet | Sun only | `SUN_MASSLESS_TARGET` |

The receipt exposes component IDs and values in km3/s2, their sum, the policy
version, source identity, and admitted DE440/DE441 identity. An unidentified or
unadmitted planetary ephemeris fails; gravity is never guessed from a body
name.

---

## 6. Frame Contract

Stage 1 admits three inertial element frames:

| Frame | Construction |
|---|---|
| `J2000_ECLIPTIC` | ICRF axes passively rotated by the Horizons-documented IAU 1976/1980 J2000 obliquity, 84381.448 arcseconds; no frame bias |
| `MEAN_ECLIPTIC_OF_DATE` | SOFA `Ecm06` on the closed TT interval JD 2415020.0 through 2488070.0; SOFA `Ltecm` outside it within the SOFA long-term domain |
| `TRUE_ECLIPTIC_OF_DATE` | `Rx(epsa + deps) * Pnm06a`, with SOFA `Obl06` and `Nut06a`, only on that same closed modern interval |

The authority fixture is compiled from official IAU SOFA C Issue 2023-10-11,
SHA-256
`375729d8c0a254fd27c55484de5c8b83cccef351e1ef19d9cf7f26f5485e5538`.
PyERFA is a secondary parity check, not the frozen oracle.

The frame receipt names the exact routine/model and router branch. Position and
velocity receive the same instantaneous rotation; Stage 1 does not add a
moving-frame derivative. True-of-date requests outside the admitted interval
fail with `OrbitalFrameUnavailableError`.

Chart-stack precession is bias-inclusive on both its modern and long-term
branches. A raw ICRF vector may not receive an explicit frame-bias operation
immediately before that bias-owning matrix.

---

## 7. Conic And Undefined-Field Semantics

`OrbitShape` is `ELLIPTIC`, `PARABOLIC`, or `HYPERBOLIC`. The strict vessel
uses `None`, never a sentinel magnitude, for an element that does not exist.
Each absent field has one `UndefinedElement` receipt containing every
simultaneous reason:

- `CIRCULAR`
- `EQUATORIAL`
- `PARABOLIC`
- `HYPERBOLIC`

The extraction also supplies nonsingular alternatives when defined:
longitude of pericenter, argument of latitude, true longitude, and mean
longitude. Parabolic motion uses Barker's equation. Hyperbolic semi-major axis
is negative and its anomaly is signed. Apocenter distance and orbital period
are absent for open conics.

The dimensionless circular, equatorial, parabolic, and rectilinear thresholds
and their policy ID are included in provenance. Zero-position, zero-velocity,
and rectilinear states fail explicitly rather than producing unstable angles.

---

## 8. Apsidal-Passage Contract

```python
apsidal_passages(
    body,
    jd_ut,
    *,
    center,
    direction,
    max_days=None,
    reader=None,
) -> ApsidalPassages
```

`center` (`SUN` or `EARTH`) and `direction` (`NEXT` or `PREVIOUS`) are
required. The start is inclusive. A passage is not an osculating-conic date:
it is an isolated, two-sided local extremum of live center-relative distance.
The implementation samples
`dot(position, velocity_per_day) / norm(position)` in TDB, refines one
chronological sign crossing, and independently confirms the distance on both
sides. Negative-to-positive is pericenter; positive-to-negative is apocenter.

One reader-pool snapshot, clock identity, gravitational model, and ordered
route schedule are frozen before sampling. A bracket never crosses a route
entry. Touching source seams are traversed only when independently evaluated
position and velocity residuals pass the published gates; gaps and rejected
seams are visible coverage boundaries. The receipt includes the route-plan
identity, exact schedule, source-segment evaluation counts, seam measurements,
search interval, algorithm version, constants, and total evaluation count.

The search is bounded by a positive finite `max_days` when supplied. Otherwise
an elliptic starting state searches up to 1.5 starting osculating periods;
parabolic and hyperbolic starts search to the route edge. These conics provide
sampling/window scale only and never replace trajectory evaluation. The fixed
`MOIRA_APSIDAL_PASSAGES_V1` policy uses a `1e-8 day` root tolerance, 96 root
iterations, 20,000 state-evaluation budget, `1/256` period fraction, `1/20`
local-motion fraction, and steps clamped to `0.05–32 days`.

Each pericenter and apocenter outcome is exactly one of:

- `FOUND`, with TDB, TT, verified inverse UT1, distance, and no coverage edge;
- `BEYOND_COVERAGE`, with the exact directional route edge and no event
  coordinates; or
- `NOT_IN_WINDOW`, with no event coordinates and detail naming the explicit or
  automatic bound. A numerically flat synthetic interval uses
  `NO_ISOLATED_EXTREMUM`.

An event on a coverage edge is not found without witnesses on both sides.
Convergence or budget exhaustion raises `OrbitalSearchError`; a complete-pair
compatibility adapter raises `OrbitalPassageUnavailableError` rather than
converting computational or coverage absence into a physical claim.

---

## 9. Compatibility Surface

```python
orbital_elements_at(body, jd_ut, reader) -> KeplerianElements
```

This positional signature is preserved for the nine historical planet names.
Its `epoch_jd` now truthfully contains TT. Built-in DE440/DE441 readers delegate
to the strict Sun/J2000 route. Historical third-party protocol readers retain
the old extraction path without a strict provenance claim. Small bodies, Moon,
and EMB must use `osculating_elements`.

```python
distance_extremes_at(body, jd_ut, reader) -> DistanceExtremes
```

This remains positional and planet-only. It delegates once to
`apsidal_passages(center=SUN, direction=NEXT)` and requires both outcomes to be
`FOUND`. Both `DistanceExtremes.*_jd` fields are TT. Small bodies, the Moon,
EMB, alternate centers, and previous-direction searches use the strict API.

`phenomena.perihelion` and `phenomena.aphelion` also delegate to the strict
core, but admit every loaded orbital body and preserve verified UT1 in
`PhenomenonEvent.jd_ut`. They select Earth for the Moon and Sun for every other
admitted body; they do not introduce an implicit general center policy.

---

## 10. REST Boundary

`POST /v1/orbits/elements` fixes the strict call to `center=SUN`, `frame=J2000_ECLIPTIC`.
Its time envelope truthfully exposes UT1 input, TT output, TDB state evaluation, both numerical
epochs, offsets, and the conversion receipt. Provenance includes allowlisted gravity, frame,
state-leg, exact-coverage, and singularity data with no local paths.
Small bodies (asteroids and comets) are admitted. For parabolic and hyperbolic trajectories ($e \ge 1.0$),
open-conic fields (`semi_major_axis_au`, `aphelion_distance_au`, `orbital_period_days`,
`mean_anomaly_deg`, and `mean_motion_deg_per_day`) are nullable and serialize as `null`, while
the exact 12 fields are preserved for elliptic bodies.

`POST /v1/orbits/distance-extremes` admits both major planets and small bodies. Its request is UT1;
state/root evaluation is TDB; its legacy event JD fields are TT. The response
carries the same source-owned Delta-T and pinned NAIF TT/TDB receipt plus
both scale-explicit outcomes and allowlisted search, route, usage, seam,
gravity, and algorithm provenance. When a requested passage is unavailable (e.g. open conic
lacking an apocenter, or event outside search interval), it raises `OrbitalPassageUnavailableError`,
which is mapped to HTTP 422 (`orbital_event_availability`). It does not serialize local paths.

`POST /v1/orbits/class` and `POST /v1/orbits/class/batch` expose osculating asteroid orbit
classification according to official JPL Small-Body Database (SBDB) criteria (`IEO`, `ATE`,
`APO`, `AMO`, `MCA`, `IMB`, `MBA`, `OMB`, `TJN`, and fallback `AST`). The payload provides:
- The assigned orbit class code, title, and narrative definition.
- Detailed diagnostic predicate boundary margins recording distance to qualifying thresholds
  for perihelion distance ($q$), aphelion distance ($Q$), semi-major axis ($a$), and Jupiter Tisserand parameter ($T_J$).
- Provenance including underlying osculating elements, time conversion, gravity, and SPK state-source legs.
The batch variant `POST /v1/orbits/class/batch` accepts up to 128 targets at the same epoch,
provides isolated per-item error reporting with full path redaction, and echoes batch request metadata.

Structured orbital errors are translated before generic `ValueError` handling.
Client responses contain stable error codes and safe finite details; internal
computation failures are logged with a request ID and do not expose paths or
exception text.

---

## 11. Validation And Release Boundary

Offline authority fixtures contain disjoint calibration, planet holdout, and
catalog holdout sets queried with exact `TLIST` JDTDB and `TIME_TYPE=TDB` for
both Horizons VECTORS and ELEMENTS. Kernel tests compare raw ICRF states and
J2000-ecliptic elements at the identical TDB instant.

The Stage 2 passage fixture independently scans official geometric Horizons
VECTORS in exact TDB, refines radial-velocity crossings, and records exact
event/witness response hashes. Ten DE441 planet/system cases pass `1e-4 day`
and `1e-9 AU` gates. The installed asteroid and comet manifests lack a
reviewed Stage 2 passage-accuracy admission and exact target-solution binding;
their six authority comparisons are therefore `NOT RUN` pending governed
catalog validation admission, not accepted with wider tolerances.

The packaged 25-body wheel catalog remains a fallback implementation test, not
proof of the full release inventory. The configured release-host validation
passes the inventory gate for all 10,025 bodies in
`moira-asteroids@2026.08.12.1` and all 497 bodies in
`moira-comets@2026.07.28.1`. Release readiness remains blocked until the live
Horizons drift audit passes, the catalog accuracy admissions are reviewed, and
the three Stage 1 receipts are reviewed.

The implementation worktree's compatibility captures use the same DE441,
comet-release, and packaged-wheel hashes as baseline commit
`29dd164c80c2a6788aa598a832eff3d4fd8e727a`. All 19 required probes complete on
both builds. The reader-clock receipt proves exact legacy numeric-TDB replay,
exactly one conversion in every sampled public TT adapter, an observable second
conversion, and native/Python planetary agreement within `1e-9`. Its 84 changed
fields out of 137 are the intended clock correction. The frame receipt has 121
changed fields out of 188; its matrix probe isolates frame construction at
fixed TT, while its protected high-level consumers include both the separately
receipted clock shift and the frame correction. Raw maxima in these receipts
span mixed units and are not accuracy claims.

Focused Stage 1/2 tests, the isolated 52-case live-primary element audit, and
the Stage 2 Earth/Neptune live passage sentinels pass.
The full 10,522-body asteroid/comet inventory gate passes. The repository-wide
non-network command remains independently blocked by pre-existing harness-import,
hybrid-eclipse-topology, and asteroid fixture/resource failures that each
reproduce at the untouched baseline. The plan's exact changed-file Ruff command
likewise reports 66 inherited findings on both candidate and baseline, while
the new Stage 1 files pass separately.
The validation receipt therefore says implementation-review-ready and
release-blocked; it does not authorize a version, tag, publication, or
deployment.

Stage 1/2 implementation does not authorize a version change, tag, package
publication, website pin update, staging deployment, or production promotion.
