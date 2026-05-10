# Moira SpiceyPy Removal Plan

Status date: 2026-05-10

Purpose:
Define the smallest truthful native scope required to remove the production
`spiceypy` dependency from `moira/lunar_limb.py` without weakening kernel
authority, time-scale honesty, or lunar body-frame semantics.

## Governing Conclusion

Yes, Moira can remove `spiceypy` from production.

No, this is not a trivial wrapper swap.

The present `spiceypy` usage is doing five distinct jobs:

1. kernel admission and lifecycle
2. UT Julian Day to ET/TDB conversion
3. Earth ellipsoid observer geometry
4. topocentric apparent Moon state evaluation
5. Moon body-frame rotation and coordinate conversion

Moira already owns large parts of the surrounding substrate:

- SPK reading and state evaluation
- light-time and aberration helpers
- precession, nutation, and rotation primitives
- lunar-limb topography kernels

What Moira does not yet own is the narrow NAIF semantics layer required to
replace the admitted `spiceypy` calls in `moira/lunar_limb.py`.

## Current Production Surface

The active `spiceypy` dependency in `moira/lunar_limb.py` covers:

- `sp.furnsh(...)`
- `sp.str2et(...)`
- `sp.bodvrd(...)`
- `sp.georec(...)`
- `sp.spkcpo(...)`
- `sp.pxform(...)`
- `sp.mxv(...)`
- `sp.reclat(...)`
- `sp.dpr()`

The last three are easy to own immediately.

The first six are the real admission boundary.

## Truth-First Replacement Strategy

Do not re-implement generic SPICE.

Admit only the narrow sovereign slice Moira actually needs for the lunar-limb
production path:

- target body: `MOON`
- observer body: topocentric Earth observer
- inertial frame: `J2000`
- body-fixed frame: `MOON_ME`
- Earth fixed frame only as needed for observer construction
- kernel set:
  - `naif0012.tls`
  - `pck00011.tpc`
  - `moon_pa_de440_200625.bpc`
  - `moon_assoc_me.tf`
  - `moon_de440_250416.tf`
  - `de440.bsp`

This keeps provenance explicit and avoids a false claim of general SPICE
compatibility.

## Recommended Native Phases

### Phase 1: Mechanical Helpers

Own the easy non-NAIF-heavy pieces in native code:

- `dpr()` equivalent
- `reclat()` equivalent
- `mxv()` equivalent
- WGS-84 geodetic-to-Cartesian observer conversion

This phase is low risk and mostly removes convenience dependence.

### Phase 2: Native Time Admission

Replace `str2et("JD ...")` for the admitted path only.

Required truth:

- explicit UT input policy
- leap-second handling from the admitted LSK
- TT/TDB relation stated explicitly

Recommended scope:

- implement a minimal native LSK reader for leap seconds
- convert `jd_ut` to `jd_tt` using Moira policy
- convert `jd_tt` to `et_tdb_seconds_past_j2000`

This should not claim full SPICE time-string parsing.

### Phase 3: Native Kernel Registry

Replace `furnsh(...)` with a native admitted-kernel registry:

- explicit file registration
- explicit kernel kinds
- explicit cache ownership

Do not mimic SPICE's global ambient kernel pool.

### Phase 4: Native Moon Apparent State

Replace the `spkcpo(...)` usage with Moira-native evaluation:

- build the observer vector in Earth-fixed coordinates
- rotate or otherwise place that observer in the admitted inertial frame
- evaluate Earth and Moon states from `de440.bsp`
- solve light-time to the Moon
- apply the same admitted aberration policy now used by Moira

This should produce the topocentric apparent `observer_to_moon_j2000` vector
currently sourced from SPICE.

### Phase 5: Native Moon Body Frame

Replace `pxform("J2000", "MOON_ME", et)` and its inverse.

This is the highest-risk slice.

Truthful options, in order:

1. parse the admitted binary PCK and frame kernel natively
2. admit a narrow native lunar-orientation evaluator derived directly from the
   NAIF kernel lineage for `MOON_ME`

Option 1 is more sovereign and more extensible.
Option 2 is acceptable only if its authority and scope are explicit and the
validation remains strict.

### Phase 6: Python Integration Swap

Only after native parity is demonstrated:

- replace `spiceypy` calls in `moira/lunar_limb.py`
- remove `import spiceypy`
- preserve public semantics

## What Should Not Be Done

Do not:

- hard-code Earth radii from memory without provenance
- replace `MOON_ME` with an approximate mean lunar frame and call it equivalent
- introduce a fake generic frame system that is only partially true
- claim repository-wide SPICE replacement after only removing the lunar-limb use

## Validation Requirements

The replacement must be validated by strata, not only by final output:

1. ET conversion parity for a curated epoch sweep
2. observer geocentric vector parity
3. topocentric apparent Moon vector parity in `J2000`
4. `J2000 <-> MOON_ME` rotation parity
5. final oracle parity against `tests/oracle_lunar_limb_baseline.json`

Suggested tolerances:

- time conversion: explicit second-level tolerance declared by phase
- rotation matrices: elementwise residuals recorded
- final profile correction: preserve the existing `< 1e-6 degree` oracle target

## Minimal Honest Build Order

If the objective is "no production `spiceypy` dependency" with the least
architectural risk, the most honest order is:

1. native helper math and geodetic observer conversion
2. native ET conversion for admitted JD input
3. native kernel registry
4. native topocentric Moon state
5. native `MOON_ME` frame evaluation
6. swap `moira/lunar_limb.py`

This is the smallest path that removes `spiceypy` without downgrading the
astronomical substrate.
