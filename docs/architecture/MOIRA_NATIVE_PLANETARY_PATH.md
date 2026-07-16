# Moira Native Planetary Path

**Status**: Current-state path map
**Date**: 2026-07-16
**Companion documents**:
- [MOIRA_NATIVE_BACKEND_ARCHITECTURE.md](./MOIRA_NATIVE_BACKEND_ARCHITECTURE.md)
- [MOIRA_NATIVE_CLOSURE_PROGRAM.md](./MOIRA_NATIVE_CLOSURE_PROGRAM.md)
- [MOIRA_NATIVE_MIGRATION_TRACKER.md](./MOIRA_NATIVE_MIGRATION_TRACKER.md)

---

## 1. Purpose

This document charts the full planetary calculation pipeline and marks where the native path is active, where it is partial, and where execution remains Python-owned.

This is the main closure spine for the native program.

If the planetary path is not understood stage by stage, later native claims for:

- search
- eclipses
- cartography
- event assemblies

cannot be judged clearly.

---

## 2. Governing Reading

For this document:

- `native active` means normal execution can enter native code at that stage
- `native partial` means some supporting native machinery exists but the stage is not broadly closed
- `python owned` means the stage remains implemented in Python in the canonical engine path

The planetary path is not one function.

It is a stack:

1. facade entry and reader context
2. time-scale preparation
3. kernel reader dispatch
4. barycentric / geocentric state-vector construction
5. apparent-position corrections
6. frame transforms
7. longitude / latitude / sky-coordinate assembly
8. result-vessel packaging

---

## 3. Public Entry Points

The main public planetary surfaces are:

- `Moira.chart(...)` in [moira/_facade_core.py](../../moira/_facade_core.py#L70)
- `Moira.sky_position(...)` in [moira/_facade_core.py](../../moira/_facade_core.py#L146)
- `planet_at(...)` in [moira/planets.py](../../moira/planets.py#L610)
- `sky_position_at(...)` in [moira/planets.py](../../moira/planets.py#L848)
- `all_planets_at(...)` in [moira/planets.py](../../moira/planets.py#L1000)
- `heliocentric_planet_at(...)` in [moira/planets.py](../../moira/planets.py#L1102)
- `planet_relative_to(...)` in [moira/planets.py](../../moira/planets.py#L1261)

The facade-level reader context is established by [moira/_facade_kernel.py](../../moira/_facade_kernel.py#L71), which builds a `KernelPool` and wraps public calls in `use_reader_override(...)`.

---

## 4. Pipeline Overview

## 4.1 User-Facing Flow

The normal chart path is:

1. `Moira.chart(dt, ...)`
2. convert datetime to `jd_ut`
3. derive `jd_tt` / `jd_ut1` and local sidereal context
4. call `all_planets_at(...)`
5. admit `NativePlanetaryEvaluator` for the exact default all-planets surface,
   or use the Python-governed fallback for all other modes
6. fetch raw kernel vectors through the active reader
7. apply apparent-position corrections as requested
8. transform to ecliptic or equatorial / horizontal coordinates
9. derive `PlanetData.speed` from the same geocentric longitude product at
   neighbouring TT epochs
10. package `PlanetData` or `SkyPosition`

The normal sky-position path is:

1. `Moira.sky_position(dt, body, lat, lon, elev)`
2. `sky_position_at(...)`
3. planetary vector acquisition
4. correction stack
5. equatorial and horizontal conversion
6. package `SkyPosition`

---

## 5. Stage Map

| Stage | Main module / surface | What happens | Native status now | Notes |
| --- | --- | --- | --- | --- |
| Facade reader setup | [moira/_facade_kernel.py](../../moira/_facade_kernel.py#L71) | Builds `KernelPool` with planetary and supplemental kernels; installs reader override | Python owned | Orchestration only; no native execution here. |
| Chart assembly | [moira/_facade_core.py](../../moira/_facade_core.py#L70) | Calls `all_planets_at(...)`, node functions, obliquity, delta-T, returns `Chart` | Python owned | Public entry layer remains Python by design. |
| Time conversion | `moira.julian` | `ut_to_tt`, `decimal_year`, sidereal helpers | Partial native | Julian and sidereal helper slice is native-routable; wider time policy remains Python-owned. |
| Reader selection | [moira/spk_reader.py](../../moira/spk_reader.py#L166) | Chooses native DAF path or fallback path | Native active | This is the first material native choke point in the main planetary path. |
| Planetary kernel open/catalog | [moira/spk_reader.py](../../moira/spk_reader.py#L149) | Native summary scan and native segment-object construction for supported segment types | Native active | Integrated and parity-tested; benchmark gain is modest for catalog open/index. |
| Segment evaluation | [moira/spk_reader.py](../../moira/spk_reader.py#L122) and [moira/spk_reader.py](../../moira/spk_reader.py#L180) | Native Chebyshev record and series evaluation for supported type-2/type-3 segments | Native active, performance-partial | Functionally live in `SpkReader`, but current checked benchmark artifacts show regression on repeated segment workloads. |
| Small-body supplemental path | [moira/_spk_body_kernel.py](../../moira/_spk_body_kernel.py#L132) | Native-owned type-13 and supported type-2/type-3 segment reading for supplemental kernels | Native active | Important adjacent branch because `KernelPool` is the real reader surface used by the facade. |
| Barycentric route chaining | `moira.planets._native_all_planets_admitted`, `NativePlanetaryEvaluator` | Chains admitted NAIF routes into body barycentric positions and states | Native active for the exact default bulk surface; Python fallback otherwise | Native evaluators are resolved once per calculation to avoid repeated kernel-cache mutex/LRU traffic. |
| Earth / geocentric construction | `NativePlanetaryEvaluator`; Python helpers in `moira/planets.py` | Builds Earth barycentric state and subtracts to geocentric frame | Native active for the exact default bulk surface; Python fallback otherwise | Public semantics and admission remain Python-owned. |
| Apparent correction stack | `NativePlanetaryEvaluator`; [moira/corrections.py](../../moira/corrections.py) | Light-time, aberration, deflection, frame bias, parallax, diurnal aberration, refraction | Native active through ecliptic projection for default bulk geocentric output; Python for non-default and topocentric modes | Native admission is deliberately narrow, not a universal correction port. |
| Rotation composition | `moira/planets.py` and `NativePlanetaryEvaluator` | Python composes explicit precession/nutation policy; admitted native code applies the supplied matrix | Python governed, native strengthened | The matrix and correction policy remain visible at the Python boundary. |
| Coordinate transforms | `NativePlanetaryEvaluator`; [moira/coordinates.py](../../moira/coordinates.py) | Converts corrected vectors into ecliptic, equatorial, and horizontal products | Native ecliptic projection for default bulk output; Python for wider products | Topocentric and sky-coordinate semantics remain Python-owned. |
| Result packaging | `PlanetData`, `SkyPosition`, `HeliocentricData`, `Chart` | Final typed vessel construction | Python owned | Deliberately Python-facing. |

---

## 6. Detailed Path Breakdown

## 6.1 Reader and Kernel Context

The first decisive native boundary is not in `planet_at(...)` itself. It is in the reader layer.

`KernelFacadeMixin` creates a `KernelPool` containing:

- a primary `SpkReader` for the planetary kernel
- optional `SmallBodyKernel` instances for supplemental kernels

This happens in [moira/_facade_kernel.py](../../moira/_facade_kernel.py#L82).

The planetary reader path then enters native code in [moira/spk_reader.py](../../moira/spk_reader.py#L166):

- native DAF catalog reading can replace `jplephem` summary walking
- native segment payload loading can replace `jplephem` segment data interpretation
- native record evaluation can replace Python-side record evaluation for supported segment types

This is the strongest current native insertion point in the planetary stack.

## 6.2 Raw Vector Acquisition

Once the reader is active, [moira/planets.py](../../moira/planets.py#L407) constructs vectors by chaining SPK relationships:

- `_barycentric(...)`
- `_barycentric_state(...)`
- `_earth_barycentric(...)`
- `_earth_barycentric_state(...)`
- `_geocentric(...)`
- `_geocentric_state(...)`

These functions remain the Python-owned fallback orchestration.

They benefit indirectly from the native reader path because their calls to:

- `reader.position(...)`
- `reader.position_and_velocity(...)`

may enter native segment evaluation under the hood.

For the exact default `all_planets_at(...)` mode, Python instead admits
`NativePlanetaryEvaluator`, which owns the dense route chaining, Earth-state
construction, light-time iteration, default corrections, and ecliptic
projection. Segment evaluator lifetimes remain bounded by the kernel handle;
the planetary evaluator holds resolved segments only for one calculation.

## 6.3 Apparent Pipeline

Outside the admitted default bulk mode, the apparent pipeline is handled in Python:

- `apply_light_time(...)` at [moira/corrections.py](../../moira/corrections.py#L152)
- `apply_aberration(...)` at [moira/corrections.py](../../moira/corrections.py#L202)
- `apply_deflection(...)` at [moira/corrections.py](../../moira/corrections.py#L272)
- `apply_frame_bias(...)` at [moira/corrections.py](../../moira/corrections.py#L352)
- `topocentric_correction(...)` at [moira/corrections.py](../../moira/corrections.py#L619)
- `apply_diurnal_aberration(...)` at [moira/corrections.py](../../moira/corrections.py#L735)
- `apply_refraction(...)` at [moira/corrections.py](../../moira/corrections.py#L1014)

The admitted default bulk mode has a real native apparent-position route. It
does not replace these Python surfaces universally: single-body, barycentric,
topocentric, cartesian, and switch-altered products remain on the
Python-governed path.

`PlanetData.speed` is not taken from the uncorrected SPK velocity projection.
It is the TT-day derivative of the same canonical geocentric ecliptic longitude
product, using a declared symmetric 0.002-day step and a second-order one-sided
fallback at kernel coverage boundaries. The native bulk route obtains that
derivative from neighbouring native longitude evaluations.

## 6.4 Coordinate and Product Assembly

Once corrected vectors are available, Python-owned transforms complete the
wider path:

- `icrf_to_ecliptic(...)` at [moira/coordinates.py](../../moira/coordinates.py#L173)
- `icrf_to_true_ecliptic(...)` at [moira/coordinates.py](../../moira/coordinates.py#L234)
- `icrf_to_equatorial(...)` at [moira/coordinates.py](../../moira/coordinates.py#L267)
- `equatorial_to_horizontal(...)` at [moira/coordinates.py](../../moira/coordinates.py#L286)
- `cotrans_sp(...)` at [moira/coordinates.py](../../moira/coordinates.py#L524)

The exact default bulk route performs its ecliptic projection natively from a
Python-supplied rotation matrix and obliquity. Wider coordinate products still
use the named Python transforms.

---

## 7. Path Variants

## 7.1 `planet_at(...)`

This is the canonical geocentric ecliptic product.

Native participation today:

- yes at the reader/segment layer
- the public single-body surface remains Python-governed above that layer
- speed follows the corrected geocentric longitude derivative

## 7.2 `sky_position_at(...)`

This is the canonical apparent topocentric sky product.

Native participation today:

- yes at the reader/segment layer
- no for apparent corrections
- no for horizontal coordinate conversion

This makes `sky_position_at(...)` a later closure target than raw vector access.

## 7.3 `all_planets_at(...)`

This is a Python-governed bulk surface with a narrowly admitted native default route.

Native participation today:

- direct for the exact default apparent geocentric ecliptic planet set
- fallback to shared Python contexts when any admitted-mode condition is not met
- native segment evaluators are resolved once per calculation
- rate semantics are derived from neighbouring corrected native longitudes

This is one of the most important engine-level benchmark surfaces because it reflects real chart-building work.

## 7.4 `heliocentric_planet_at(...)`

This path is still heavily Python-owned above the reader:

- body and Sun barycentric states are fetched from the reader
- heliocentric subtraction, precession/nutation rotation, and ecliptic conversion remain Python

It benefits from native segment evaluation below the reader API but is not itself a native-routed heliocentric pipeline.

## 7.5 `planet_relative_to(...)`

This is also Python-owned above the reader.

Its vector acquisition depends on the same barycentric substrate and therefore inherits any reader-level native acceleration indirectly.

---

## 8. Where the Native Path Is Strongest

The strongest native portion of the planetary path today is:

1. native DAF/SPK catalog reading
2. native payload extraction for supported segment types
3. native record and series evaluation inside the reader layer
4. native small-body reader ownership for supplemental kernels
5. native default bulk apparent geocentric ecliptic evaluation
6. runtime-dispatched AVX2 Type-2 Chebyshev evaluation with a portable scalar fallback

These are real and integrated.

They are not hypothetical.

They are exercised by:

- `tests/unit/test_spk_reader.py`
- `tests/integration/test_small_body_native_reader_killer.py`
- checked benchmark artifacts under `tests/artifacts/benchmarks/`

---

## 9. Where the Native Path Stops

The admitted native route stops at the default bulk apparent geocentric
ecliptic product. The following remain Python-owned:

- admission policy and public meaning
- all non-default correction-switch combinations
- barycentric, cartesian, and topocentric planetary products
- topocentric parallax, diurnal aberration, and refraction
- equatorial and horizontal assembly
- result vessels and facade orchestration

This is a Python-governed planetary engine with a selectively admitted native
bulk substrate, not a universal C++ mirror.

---

## 10. Evidence Ledger

Current checked evidence relevant to the planetary path includes:

- `tests/test_native_parity.py`
- `tests/test_native_sidereal_phase1.py`
- `tests/unit/test_native_import_resolution.py`
- `tests/unit/test_spk_reader.py`
- `tests/unit/test_planet_position_switches.py`
- `tests/unit/test_adversarial_native_runtime_verification.py`
- `tests/unit/test_native_runtime_verification.py`
- `tests/unit/test_native_nutation_2000a.py`
- `tests/integration/test_small_body_native_reader_killer.py`
- `tests/artifacts/benchmarks/native_phase1_sidereal.json`
- `tests/artifacts/benchmarks/native_phase2_catalog.json`
- `tests/artifacts/benchmarks/native_phase2_ephemeris.json`
- `tests/artifacts/benchmarks/native_phase2_segments.json`
- `tests/artifacts/benchmarks/native_phase2_segments_series_eval_experiment.json`
- `tests/artifacts/benchmarks/native_phase2_small_bodies.json`

The checked JSON artifacts remain historical performance evidence, not
scientific validation and not automatic truth about the current source. New
performance claims require a fresh named benchmark run. Scientific behavior is
guarded separately by Python/native comparisons, external-oracle slices where
available, and the invariant that speed differentiates the published
longitude product.

---

## 11. Closure Meaning For The Planetary Path

The planetary path can be considered fully native-closed only when all of the following are true:

1. reader-level native execution remains parity-clean
2. engine-level public planetary surfaces are benchmarked honestly
3. the canonical default bulk planetary product remains production-routed through its clearly admitted native path
4. the current boundary-cost regression is either removed or explicitly accepted with documented justification

In practice, the next closure moves should focus on:

- reducing the cost of corrected neighbouring-epoch rate samples without
  weakening the declared speed product
- preserving Python/native agreement across segment boundaries
- repeated `reader.position(...)` and `reader.position_and_velocity(...)` workloads

Those are the surfaces that define whether the planetary path is merely native-capable or actually native-advancing.

---

## 12. Present Conclusion

The planetary pipeline is the main closure spine because nearly everything else depends on it.

Right now its shape is:

- public entry: Python
- reader substrate: native and materially integrated for admitted segments
- default bulk vector orchestration and apparent ecliptic projection: native
- wider vector orchestration, correction modes, and coordinate products: Python
- result packaging: Python

So the honest summary is:

- the native path is real
- it now reaches one canonical default bulk planetary product
- Python still governs admission, policy, public semantics, and all wider modes

That is why planetary closure comes first.
