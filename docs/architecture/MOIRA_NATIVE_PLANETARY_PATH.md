# Moira Native Planetary Path

**Status**: Current-state path map
**Date**: 2026-05-08
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
5. call `planet_at(...)` for each requested body
6. inside `planet_at(...)`, fetch raw kernel vectors through the active reader
7. apply apparent-position corrections as requested
8. transform to ecliptic or equatorial / horizontal coordinates
9. package `PlanetData` or `SkyPosition`

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
| Barycentric route chaining | [moira/planets.py](../../moira/planets.py#L407) | Chains NAIF routes into body barycentric positions and states | Python owned | Calls into reader repeatedly; currently not a native wrapper surface. |
| Earth / geocentric construction | [moira/planets.py](../../moira/planets.py#L457) and [moira/planets.py](../../moira/planets.py#L474) | Builds Earth barycentric state and subtracts to geocentric frame | Python owned | This is a high-value future closure target because it sits above native segment evaluation. |
| Apparent correction stack | [moira/corrections.py](../../moira/corrections.py#L152) onward | Light-time, aberration, deflection, frame bias, parallax, diurnal aberration, refraction | Python owned | Entire correction stack remains Python-owned in the canonical planetary path. |
| Rotation composition | [moira/planets.py](../../moira/planets.py#L563) | Precession/nutation rotation composition, optionally NumPy-accelerated | Python owned | Uses Python plus optional NumPy, not C++. |
| Coordinate transforms | [moira/coordinates.py](../../moira/coordinates.py#L173), [moira/coordinates.py](../../moira/coordinates.py#L234), [moira/coordinates.py](../../moira/coordinates.py#L267), [moira/coordinates.py](../../moira/coordinates.py#L286) | Converts corrected vectors into ecliptic, equatorial, and horizontal products | Python owned | Some equivalent primitives exist in the extension, but the canonical planetary path is still Python here. |
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

These functions are still Python-owned orchestration.

They benefit indirectly from the native reader path because their calls to:

- `reader.position(...)`
- `reader.position_and_velocity(...)`

may enter native segment evaluation under the hood.

This means the current native planetary path is:

- **native below the reader API**
- **Python above the reader API**

That distinction is the key truth of the present system.

## 6.3 Apparent Pipeline

After raw vectors are obtained, the apparent pipeline is handled in Python:

- `apply_light_time(...)` at [moira/corrections.py](../../moira/corrections.py#L152)
- `apply_aberration(...)` at [moira/corrections.py](../../moira/corrections.py#L202)
- `apply_deflection(...)` at [moira/corrections.py](../../moira/corrections.py#L272)
- `apply_frame_bias(...)` at [moira/corrections.py](../../moira/corrections.py#L352)
- `topocentric_correction(...)` at [moira/corrections.py](../../moira/corrections.py#L619)
- `apply_diurnal_aberration(...)` at [moira/corrections.py](../../moira/corrections.py#L735)
- `apply_refraction(...)` at [moira/corrections.py](../../moira/corrections.py#L1014)

No canonical native route is active here today.

This is why the current planetary native path should not be described as a native apparent-position pipeline.

It is currently:

- native reader substrate
- Python correction stack

## 6.4 Coordinate and Product Assembly

Once corrected vectors are available, Python-owned transforms complete the path:

- `icrf_to_ecliptic(...)` at [moira/coordinates.py](../../moira/coordinates.py#L173)
- `icrf_to_true_ecliptic(...)` at [moira/coordinates.py](../../moira/coordinates.py#L234)
- `icrf_to_equatorial(...)` at [moira/coordinates.py](../../moira/coordinates.py#L267)
- `equatorial_to_horizontal(...)` at [moira/coordinates.py](../../moira/coordinates.py#L286)
- `cotrans_sp(...)` at [moira/coordinates.py](../../moira/coordinates.py#L524)

Again, equivalent native primitives exist in the extension, but they are not yet the normal planetary-engine route.

---

## 7. Path Variants

## 7.1 `planet_at(...)`

This is the canonical geocentric ecliptic product.

Native participation today:

- yes at the reader/segment layer
- no for the correction pipeline
- no for final coordinate assembly

## 7.2 `sky_position_at(...)`

This is the canonical apparent topocentric sky product.

Native participation today:

- yes at the reader/segment layer
- no for apparent corrections
- no for horizontal coordinate conversion

This makes `sky_position_at(...)` a later closure target than raw vector access.

## 7.3 `all_planets_at(...)`

This is a Python orchestrator over repeated `planet_at(...)` calls, with some shared precomputed quantities.

Native participation today:

- indirect only, through the reader path and the dispatch-routed sidereal helpers

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

These are real and integrated.

They are not hypothetical.

They are exercised by:

- `tests/unit/test_spk_reader.py`
- `tests/integration/test_small_body_native_reader_killer.py`
- checked benchmark artifacts under `tests/artifacts/benchmarks/`

---

## 9. Where the Native Path Stops

The native path currently stops, in practical engine terms, at the reader boundary.

Above that boundary, the following remain Python-owned in the canonical planetary path:

- route chaining across body relationships
- geocentric subtraction orchestration
- light-time iteration
- aberration
- gravitational deflection
- frame bias
- topocentric parallax
- diurnal aberration
- refraction
- ecliptic/equatorial/horizontal assembly
- result vessels

This is the central architectural truth to preserve.

The planetary pipeline is not yet a native planetary engine.

It is a Python planetary engine with a partially native reader substrate.

---

## 10. Evidence Ledger

Current checked evidence relevant to the planetary path includes:

- `tests/test_native_parity.py`
- `tests/test_native_sidereal_phase1.py`
- `tests/unit/test_native_import_resolution.py`
- `tests/unit/test_spk_reader.py`
- `tests/integration/test_small_body_native_reader_killer.py`
- `tests/artifacts/benchmarks/native_phase1_sidereal.json`
- `tests/artifacts/benchmarks/native_phase2_catalog.json`
- `tests/artifacts/benchmarks/native_phase2_ephemeris.json`
- `tests/artifacts/benchmarks/native_phase2_segments.json`
- `tests/artifacts/benchmarks/native_phase2_segments_series_eval_experiment.json`
- `tests/artifacts/benchmarks/native_phase2_small_bodies.json`

The most important current benchmark reading for the planetary path is:

- catalog open/index shows a modest win
- supported repeated planetary native-segment evaluation is still slower than the prior path in the checked artifacts
- small-body reader ownership is measured, but not yet benchmark-closed against a clear pre-migration baseline

---

## 11. Closure Meaning For The Planetary Path

The planetary path can be considered fully native-closed only when all of the following are true:

1. reader-level native execution remains parity-clean
2. engine-level public planetary surfaces are benchmarked honestly
3. at least one canonical public planetary product is production-routed through a clearly admitted native path
4. the current boundary-cost regression is either removed or explicitly accepted with documented justification

In practice, the next closure moves should focus on:

- `all_planets_at(...)`
- `planet_at(...)`
- repeated `reader.position(...)` and `reader.position_and_velocity(...)` workloads

Those are the surfaces that define whether the planetary path is merely native-capable or actually native-advancing.

---

## 12. Present Conclusion

The planetary pipeline is the main closure spine because nearly everything else depends on it.

Right now its shape is:

- public entry: Python
- reader substrate: partially native and materially integrated
- vector orchestration: Python
- apparent corrections: Python
- coordinate assembly: Python
- result packaging: Python

So the honest summary is:

- the native path is real
- it is strongest at kernel ownership and segment evaluation
- it has not yet climbed all the way up into the full canonical planetary calculation pipeline

That is why planetary closure comes first.
