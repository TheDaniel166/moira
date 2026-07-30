# Physical Heliacal Visibility Phase 1 Direct-Geometry Checkpoint

Date: 2026-07-29

Status: controlled near-horizon direct-transmission geometry gate passed;
Phase 1 remains in progress

## Scope

This checkpoint establishes a source-traced and independently recomputed
error bound for libRadtran 2.0.6 deterministic pseudo-spherical direct
transmission near the horizon.

It answers three bounded questions:

1. Which spherical direct-beam law does the selected libRadtran output
   actually apply at the surface?
2. Can Moira reconstruct that law independently from the bound layer optical
   depths and vertical grid?
3. Does a proposed lower-atmosphere refinement keep the resulting
   layer-discretization error below the declared 0.1% controlled-geometry
   tolerance over the admitted altitude domain?

This is research and validation evidence. It does not add engine calculations,
runtime tables, package dependencies, public contracts, or an admitted
physical heliacal model.

## Source Trace

The external generator remains libRadtran 2.0.6, pinned by:

```text
source archive bytes:
154147176

source archive SHA-256:
64930cc40b6e4a37aa220520974d330fc1563796f466a649b2238131f2d69840

uvspec SHA-256:
d4e94259296a65f7700a0911f0dc7fc14aacde89985befac0266fe0a18531b7a
```

The [libRadtran manual](https://www.libradtran.org/doc/libRadtran.pdf)
defines the pseudo-spherical direct beam by replacing the plane-parallel
optical path with the spherical Chapman integral. The source trace then fixes
how that law reaches the selected surface flux output:

- `doc/radiative_transfer_theory.tex`, equations `eq2.24` and `pseudoBeer`,
  defines the continuous spherical Chapman path;
- `libsrc_c/cdisort.c` computes a Chapman optical depth at the midpoint of
  each layer and stores
  `CH(layer) = vertical_optical_depth_to_midpoint /
  Chapman_optical_depth_to_midpoint`; and
- `c_fluxes()` evaluates the surface direct output as the full surface
  vertical optical depth divided by that bottom-layer midpoint `CH`.

The governing `cdisort.c` source receipt is:

```text
bytes:
400115

SHA-256:
952c11494efa72ebc53adf2a5e2ab34a9af5a0f241983e38a101f54a5dc03b93
```

This distinction is material. For a coarse surface layer, the selected
libRadtran surface output is not the exact sum of all constant-extinction
shell segments from an observer exactly at the surface. It is the full
surface vertical optical depth scaled by the Chapman factor reconstructed at
the bottom-layer midpoint.

## Controlled Design

The versioned probe uses a pure-absorption exponential atmosphere at 550 nm:

- vertical optical depth: `0.1`;
- scale heights: `0.25`, `0.5`, `1.0`, `1.5`, `8.0`, and `20.0` km;
- diagnostic true altitudes: `0`, `0.05`, and `0.1` degrees;
- admitted true altitudes: `0.25`, `0.5`, `1`, `2`, `5`, `10`, `20`, and
  `45` degrees;
- vertical control: `90` degrees;
- refraction: disabled;
- solver: double-precision DISORT;
- geometry: pseudo-spherical; and
- streams: `16`.

Two vertical grids are compared:

| Grid | Levels | Role |
|---|---:|---|
| `afglus_source_levels_v1` | 50 | Coarse source-grid control |
| `near_horizon_piecewise_refined_v1` | 290 | Candidate for later named-atmosphere validation |

The refined candidate uses 25 m layers from 0-2 km, 50 m from 2-5 km,
100 m from 5-10 km, 250 m from 10-25 km, 1 km from 25-50 km, and 5 km
from 50-120 km.

The build contains 144 nonrepeat cases and one fixed-input repeat, for 145
`uvspec` runs.

## Independent Oracles

The builder and validator do not share a numerical quadrature implementation:

- builder: adaptive Simpson integration over a squared-altitude transform;
- validator: adaptive Gauss-Kronrod 15 integration over the same physical
  continuous atmosphere;
- builder layer reconstruction: direct summation with `math.fsum`; and
- validator layer reconstruction: separately written compensated summation.

Every case records:

- the selected libRadtran direct transmission and slant optical depth;
- the source-traced bottom-layer-midpoint Chapman reconstruction;
- an exact same-layer shell sum from a surface observer;
- the independently integrated continuous exponential atmosphere; and
- the plane-parallel comparison where defined.

The positive-altitude production extraction remains
`edir / sin(target_true_altitude)`. The pure-absorption
`4 * pi * uavgdir` channel is a cross-check only. It remains forbidden as a
general production transmission channel because aerosol delta-M scaling
changes its semantics.

## Acceptance Results

| Gate | Frozen tolerance | Maximum observed | Result |
|---|---:|---:|---|
| Admitted libRadtran vs source-traced midpoint-Chapman slant optical depth | `2e-5` absolute | `5.353239300731616e-7` | Pass |
| Admitted positive-altitude extraction-channel difference | `5e-5` relative | `5.973554226944694e-7` | Pass |
| Refined midpoint-Chapman vs continuous atmosphere | `0.001` relative | `0.0003497406476989963` | Pass |
| Vertical optical-depth control | `2e-5` absolute | `1.99328181738068e-8` | Pass |
| Fixed-input repeat | Byte-identical | Byte-identical | Pass |

Additional diagnostics:

- refined exact-shell versus continuous maximum:
  `0.0007030175882411937`;
- coarse source-grid midpoint-Chapman versus continuous admitted maximum:
  `0.10138558685013145`;
- plane-parallel versus continuous admitted maximum:
  `9.857026256012775`; and
- exact horizon remains diagnostic-only and is not admitted.

The coarse-grid result demonstrates why lower-atmosphere refinement is
required. The refined-grid result admits this 290-level construction only as
a candidate for the next named-atmosphere and full-spectral probe.

The `0`, `0.05`, and `0.1` degree cases deliberately have no admission
tolerance. At extremely small transmissions, libRadtran's fixed-width text
output can amplify rounding when converted back to optical depth. Those cases
remain useful diagnostics but cannot weaken or fail the explicitly admitted
domain beginning at `0.25` degrees.

## Immutable Receipts

Repository specification:

```text
scripts/visibility_reference_lab/phase1_direct_geometry_probe_spec.json
bytes: 7753
SHA-256:
5f2052236632764a67325951a55b8262f21dc51e630149194ff87baf5ff2a316
```

Builder:

```text
scripts/build_visibility_direct_geometry_probe.py
bytes: 63892
SHA-256:
957f196ed69ab3fa071119f7110f6d4cbbaf4555a45cd394b94ff829e9d3f74e
```

Independent validator:

```text
scripts/validate_visibility_direct_geometry_probe.py
bytes: 54163
SHA-256:
af0221277c9ac63156c85ec39b7ffad1adc621c3ed477ea30f79cfe75f079878
```

External artifact manifest:

```text
bytes: 521126
SHA-256:
b69b377bd465b4740ef0dacd802c03d9fb6ee9eaf809a41356d60126dd23cd92

generation fingerprint:
138ee8e4f516aaacd0538f95f188b89aabb68c1ee1e591a0dc13b8d7bdd185b5

bound files: 1305
bound file bytes: 2564019
```

The compact source-owned receipt is
`tests/artifacts/visibility_reference_lab/phase1_direct_geometry_checkpoint_2026-07-29.json`.

Both earlier Phase 1 checkpoint identities remain byte-for-byte unchanged.

## Closed and Open

Closed by this checkpoint:

- the selected libRadtran surface direct-beam implementation trace;
- independent reconstruction of its bottom-layer midpoint Chapman use;
- controlled near-horizon solver/output agreement over the admitted domain;
- controlled continuous-atmosphere error for the 290-level refined candidate;
- deterministic positive-altitude extraction; and
- a fixed-input repeat.

Still open:

- validate the refined grid against the named atmosphere and the complete
  spectral direct-transmission design;
- freeze the final spectral and atmospheric design axes;
- freeze the adaptive sparse directional-radiance design;
- resolve the deep-twilight solar-only tail;
- generate the admitted spectral products;
- run untouched off-grid holdouts;
- measure storage and interpolation error;
- propagate source, solver, storage, and interpolation error into limiting
  magnitude and event time; and
- construct and validate the separately versioned visibility data pack.

Phase 2 remains inactive.
