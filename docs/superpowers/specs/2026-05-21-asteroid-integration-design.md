# Asteroid Integration Refactor — Design Spec
**Date:** 2026-05-21
**Status:** Approved

## Problem

The asteroid integration has three structural defects:

1. **`_kernel_for` reaches into pool internals.** It inspects `reader._readers` directly to extract a `SmallBodyKernel`, bypassing `KernelPool`'s public interface. Any change to pool internals silently breaks asteroid lookups.

2. **Duplicated apparent-place pipeline.** `_asteroid_apparent` in `asteroids.py` mirrors the planetary correction chain (light-time → deflection → aberration → frame bias → precession → nutation) step for step. Every correction improvement to planets must be manually mirrored to asteroids.

3. **`SmallBodyKernel` is not a `KernelReader`.** Its `position(naif_id, jd)` signature differs from the protocol's `position(center, target, jd)`, forcing `KernelPool` to use `isinstance` checks and separate dispatch paths throughout.

Secondary issues: legacy shim pile in `asteroids.py`, `_SB441_PREFERRED` defined but never wired, two `_native_catalog_is_fully_supported` functions with different behavior and identical names, module-level kernel state vars that are always `None`.

## Goals

- `SmallBodyKernel` becomes a proper `KernelReader`.
- `KernelPool` becomes the single center-resolution authority, with no `isinstance` checks.
- `asteroid_at` routes through the same apparent-place pipeline as `planet_at`.
- Public surface of `asteroids.py` is unchanged: `asteroid_at`, `all_asteroids_at`, `list_asteroids`, `available_in_kernel`, `AsteroidData`, `ASTEROID_NAIF`.

## Architecture

### 1. Pool-level center chaining

`KernelPool.position(center, target, jd)` gains two-phase dispatch:

**Phase 1 — direct match:** iterate readers, return from the first that has `(center, target)` at `jd`.

**Phase 2 — center chain:** if no reader serves `(center, target)` directly but one serves `(X, target)`, compose (first match wins, consistent with phase-1):
```
raw    = reader.position(X, target, jd)
bridge = self.position(center, X, jd)   # recursive; planetary reader covers Sun, etc.
return vec_add(raw, bridge)
```

The planetary `SpkReader` already in the pool covers `(0, 10)` — the Sun's SSB position. Heliocentric asteroid kernels (e.g., `asteroids.bsp`, center=10) are composed transparently: `chiron_helio + sun_ssb = chiron_ssb`.

All `isinstance(reader, self._SmallBodyKernel)` checks are removed from `KernelPool`. The `SmallBodyKernel` import is removed from `KernelPool.__init__`.

### 2. SmallBodyKernel as KernelReader

**`position(naif_id, jd)` renamed to `position(center, target, jd)`** — raises `KeyError` if `not self.has_body(target)`, then raises `ValueError` if `center != self.segment_center(target)`. Returns the raw kernel-frame vector. The `has_body` check must precede the center check because `segment_center` returns 0 silently for unknown targets, which would otherwise pass a `center=0` validation incorrectly.

**`position_and_velocity(center, target, jd)` added** — raises `NotImplementedError`. Satisfies the protocol without claiming a capability that does not exist.

All other required protocol methods (`has_segment`, `has_segment_at`, `coverage`, `covered_bodies`, `close`) are already present with correct signatures.

### 3. Naming disambiguation

The two functions named `_native_catalog_is_fully_supported` serve different purposes and get distinct names:

| Old name | New name | Location | Handles |
|---|---|---|---|
| `_native_catalog_is_fully_supported` | `_planetary_kernel_native_supported` | `spk_reader.py` | Types 2, 3 only (planetary kernels never contain type 13) |
| `_native_catalog_is_fully_supported` | `_small_body_kernel_native_supported` | `_spk_body_kernel.py` | Types 2, 3, 13 |

### 4. Shared apparent-place pipeline

A new internal function extracted from `planets.py`:

```python
def _apparent_geocentric_ecliptic(
    body_id,             # Body enum or NAIF int — opaque to the pipeline
    jd_tt: float,
    reader: KernelReader,
    *,
    barycentric_fn,      # callable(body_id, jd_tt, reader) -> Vec3 (SSB)
    deflectors,          # list of (geocentric_vec, schwarzschild_radius)
    earth_ssb: Vec3,
    earth_vel: Vec3,
    obliquity: float,
    rot_mat,             # pre-composed precession + nutation matrix
) -> tuple[float, float, float]:   # lon, lat, dist
```

Pipeline: `apply_light_time → apply_deflection → apply_aberration → apply_frame_bias → rot_mat → icrf_to_ecliptic`.

Body-agnostic and frame-agnostic. Does not know whether `body_id` is a planet or an asteroid.

**Planetary callers** pass:
```python
barycentric_fn = lambda b, t, r: _barycentric(b, t, r, cache)
```

**`asteroid_at`** passes:
```python
barycentric_fn = lambda b, t, r: r.position(0, b, t)
```

Deflectors for asteroids are always Sun + Jupiter + Saturn (matching current `_asteroid_apparent` behaviour). They are passed explicitly by `asteroid_at` rather than computed body-specifically as planets do.

### 5. asteroids.py cleanup

**New helper (replaces inline deflector logic from `_asteroid_apparent`):**
- `_asteroid_deflectors(jd_tt, reader, earth_ssb) -> list` — returns `[(sun_geocentric, SR_Sun), (jupiter_geocentric, SR_Jupiter), (saturn_geocentric, SR_Saturn)]`. Extracted from the existing inline computation in `_asteroid_apparent`; no new astronomical logic.

**Deleted functions:**
- `_asteroid_barycentric` — pool handles SSB resolution
- `_asteroid_apparent` — replaced by `_apparent_geocentric_ecliptic`
- `_asteroid_geocentric` — superseded by the apparent path
- `_kernel_for` — pool dispatch replaces the internal reach-in
- `load_secondary_kernel`, `load_tertiary_kernel`, `load_quaternary_kernel` — all delegated to `add_to_global_pool`; callers use `load_asteroid_kernel` directly
- `_ensure_primary_kernel`, `_ensure_secondary_kernel`, `_ensure_tertiary_kernel`, `_ensure_quaternary_kernel`

**Deleted state:**
- `_primary_kernel`, `_secondary_kernel`, `_tertiary_kernel`, `_quaternary_kernel` — always `None`, never written
- `_SB441_PREFERRED` — defined, never wired
- Duplicate `_PRIMARY_KERNEL_PATH`, `_SECONDARY_KERNEL_PATH`, `_TERTIARY_KERNEL_PATH`, `_QUATERNARY_KERNEL_PATH` at mid-file (already defined at top)

**`asteroid_at` shape after refactor:**
```python
def asteroid_at(name_or_naif, jd_ut, reader=None):
    jd_tt   = ut_to_tt(jd_ut)
    naif_id = _resolve_naif(name_or_naif)
    obliquity               = true_obliquity(jd_tt)
    earth_ssb, earth_vel    = _earth_barycentric_state(jd_tt, reader)
    rot_mat                 = _compose_rotation_matrix(jd_tt)
    deflectors              = _asteroid_deflectors(jd_tt, reader, earth_ssb)  # new helper — see below
    lon, lat, dist = _apparent_geocentric_ecliptic(
        naif_id, jd_tt, reader,
        barycentric_fn=lambda b, t, r: r.position(0, b, t),
        deflectors=deflectors,
        earth_ssb=earth_ssb, earth_vel=earth_vel,
        obliquity=obliquity, rot_mat=rot_mat,
    )
    # speed via central finite difference (unchanged)
    return AsteroidData(...)
```

## Files Changed

| File | Change |
|---|---|
| `moira/_spk_body_kernel.py` | `SmallBodyKernel.position` renamed; `position_and_velocity` added; `_native_catalog_is_fully_supported` renamed |
| `moira/spk_reader.py` | `_native_catalog_is_fully_supported` renamed; `KernelPool` isinstance checks removed; pool center-chaining added |
| `moira/planets.py` | `_apparent_geocentric_ecliptic` extracted as shared internal |
| `moira/asteroids.py` | `_asteroid_barycentric`, `_asteroid_apparent`, `_asteroid_geocentric`, `_kernel_for`, legacy shims deleted; `asteroid_at` rewritten to use shared pipeline |

## Protected Zones Implicated

- Ephemeris and kernel access (`spk_reader.py`, `_spk_body_kernel.py`) — high sensitivity
- Astronomical core computation (apparent-place pipeline in `planets.py`) — high sensitivity
- Public API surfaces (`asteroid_at`, `all_asteroids_at`) — must remain stable

## Verification

- Existing adversarial DAF reader tests (7) must pass unchanged.
- Existing killer suite (42 tests) must pass unchanged.
- Existing asteroid integration tests must pass with identical outputs.
- New integration test: query Chiron (heliocentric kernel) and verify the SSB result matches the pre-refactor path to within `1e-6°`.
- New integration test: query Ceres from `sb441-n373s.bsp` (SSB kernel, direct path) — verify pool phase-1 dispatch is taken, not phase-2.
