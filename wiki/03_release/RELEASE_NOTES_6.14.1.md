# Release Notes - Moira 6.14.1

**Release date:** 15 November 2026.

This is the first published release of the 6.14 line. Version 6.14.0 was
tagged, but its publication workflow failed while building wheels and nothing
was uploaded, so upgrades from 6.13.1 receive every 6.14.0 change here.

The features are described in the [6.14.0 release notes](RELEASE_NOTES_6.14.0.md):
the out-of-bounds declination solver, comet topocentric apparent places, and
Sothic drift fitting. Read the
[compatibility notes](COMPATIBILITY_NOTES_6.14.1.md) before upgrading.

## Why 6.14.0 did not ship

The macOS arm64 wheel built successfully and then failed its own import test:

```
ImportError: dlopen(..._moira_native.cpython-310-darwin.so, 0x0002):
symbol not found in flat namespace
'__ZN5moira6native30spk_chebyshev_record_avx2_implEPKdmdPdmm'
```

CMake compiles the AVX2 interpolation kernel only on x86 and defines
`MOIRA_NATIVE_AVX2_COMPILED` there. The four dispatch sites in
`interpolation.hpp` were guarded by `runtime_avx2_available()` alone, so a
non-x86 build still emitted calls to four `*_avx2_*_impl` symbols it had never
compiled. macOS links Python extensions with `-undefined dynamic_lookup`, so
this does not fail at link time; it fails at `dlopen`.

It had been latent since July. The references were previously deleted by dead
code elimination, because `runtime_avx2_available()` compiled to a literal
`return false` without the macro and the optimiser folded the branch away. A
sound change in the SPK batch work replaced it with a cached function-local
static — CPUID is serializing and can trap on virtualized hosts — which made
the result opaque across translation units, so the branch and its symbol
references survived. The guard had been load-bearing by accident.

The call sites now carry the same flag that compiles the definitions, so no
build can reference a kernel it did not build, whatever the optimiser does.
Verified by compiling a unit that calls all four wrappers and dumping its
undefined symbols: four before the fix with the macro undefined, zero after,
and four still resolved by linking on x86.

Only `macos-26` is arm64 in the wheel matrix, and every release gate runs on
`ubuntu-latest`, so arm64 was first exercised at wheel-build time during
publication. That ordering is why this surfaced only at release.

## Sothic corrections

`sothic_drift_rate` documented a drift of "~0.242 days/year". That is the
tropical-year excess, but Sirius's heliacal rising recurs near the **Julian**
year, so the rate is about 0.25 — which this module's own cycle identity
already assumed, since `533265 / 1460 = 365.25` exactly. Measured against
DE441 near Memphis the fitted rate runs 0.2491 to 0.2509 d/yr.

Nothing could have caught it. The only numeric test built a synthetic series
stepping by 0.242 and asserted the fit returned 0.242, taking its expected
value from the docstring it was meant to check. That test keeps its real job,
exercising the least-squares fit and the half-year unwrapping, with a slope
that cannot be mistaken for a physical rate; the rate itself is now anchored
against real risings at two epochs three thousand years apart.

Two documentation defects are also fixed. `sothic_epochs` described its result
as "one per epoch found in the range"; it is one per *year* within tolerance,
and consecutive years are a single realignment window whose width is
`2 * tolerance / 0.25` by construction — four years at ±0.5 day, eight at ±1,
sixteen at ±2. And `predict_sothic_epoch` now states how far its fixed
1460-year projection sits from the realignment the engine computes: two years
at one cycle back from AD 139, five at two, widening about three years per
cycle because the computed interval is nearer 1455.

`SothicHeliacalPolicy` now carries the Egyptological source for its 10 degree
arcus visionis — Gautschy (2011), mean about 10 degrees for Sirius in ancient
Egypt, plausibly 9 to 11 by transparency — with the day-per-degree sensitivity
that band implies. The value is unchanged and is corroborated against the
published IMCCE Sirius model at the civil-day level; only its provenance moved
to where a caller meets it.

## Validation

Everything in 6.14.0's validation still holds. Added here: the symbol-level
verification of the AVX2 guard described above, a real-rising anchor for the
Sothic drift rate, and tests pinning the epoch window width and the schematic
projection gap.
