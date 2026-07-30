# Physical Heliacal Visibility Phase 1 Named-Spectral Direct Checkpoint

Date: 2026-07-30

Status: named-atmosphere full-spectral direct-transmission gate passed for the
clear molecular surface domain; Phase 1 remains in progress

## Scope

This checkpoint takes the 290-level candidate admitted by the controlled
direct-geometry checkpoint and tests it with the six named AFGL atmospheres
and the full 380-780 nm direct-transmission spectrum.

It answers four bounded questions:

1. Does the 290-level grid remain converged for real pressure, temperature,
   water-vapor, ozone, and molecular profiles near the horizon?
2. Is the 579-level comparison grid itself converged against a 1,157-level
   calculation?
3. Which REPTRAN resolution is suitable as the full-spectral research
   reference?
4. Can a faster direct-beam bulk solver be used without changing the
   governing 16-stream DISORT output?

This remains external research and validation evidence. It does not add
engine calculations, public contracts, runtime tables, package dependencies,
automatic downloads, or a physical heliacal model.

## Source and Data Lock

The executable and source remain libRadtran 2.0.6:

```text
source archive bytes:
154147176

source archive SHA-256:
64930cc40b6e4a37aa220520974d330fc1563796f466a649b2238131f2d69840

uvspec SHA-256:
d4e94259296a65f7700a0911f0dc7fc14aacde89985befac0266fe0a18531b7a
```

The full-spectral calculation additionally binds the official
[REPTRAN download module](https://www.libradtran.org/doku.php?id=download):

```text
reptran_2024_all.tar.gz
bytes: 698709957
SHA-256:
55893c80bcc999651bac3bf014ee64aaf602653ba640eb5bebe787a5d8eacce7

regular archive files: 292
```

The 260 files overlapping the libRadtran 2.0.6 source tree are byte-identical.
The module supplies 32 official files absent from that tree, including the
general medium- and fine-resolution lookup data required by `uvspec`.

The archive contains no embedded notice or license file. It is therefore
kept as an external operator-supplied research input and is not redistributed
by Moira. The separately constructed merged data root contains 1,478 files
and is bound by this canonical receipt:

```text
regular file bytes: 873635625
canonical receipt bytes: 204827
canonical receipt SHA-256:
68f1817782e424ef617dab03ad985a3fbcb91fa2ed0239a8c2de1e8cb6855b59
```

## Controlled Design

Named atmospheres:

- tropical;
- midlatitude summer;
- midlatitude winter;
- subarctic summer;
- subarctic winter; and
- U.S. Standard.

Vertical grids:

| Grid | Levels | Role |
|---|---:|---|
| Native AFGL | 50 | Coarse diagnostic control |
| `near_horizon_piecewise_refined_v1` | 290 | Candidate |
| `near_horizon_piecewise_reference_v1` | 579 | Grid-error reference |
| `near_horizon_piecewise_convergence_v1` | 1,157 | Reference-convergence diagnostic |

The 290-level construction retains 25 m layers from 0-2 km, 50 m from
2-5 km, 100 m from 5-10 km, 250 m from 10-25 km, 1 km from 25-50 km, and
5 km from 50-120 km. The 579- and 1,157-level controls divide every step by
two and four.

The vertical matrix covers all six profiles at `0.25` degrees true altitude
and the U.S. Standard profile at `0.5`, `1`, `2`, `5`, `10`, `20`, and `45`
degrees. The observer remains at the profile surface. Refraction is disabled.

The full spectrum is:

```text
380-780 nm
output step: 0.05 nm
rows per run: 8001
```

REPTRAN medium uses 5 cm-1 bands and REPTRAN fine uses 1 cm-1 bands. The
equal-step output is compared in half-open 1, 5, and 20 nm diagnostic bins.
These bins are unweighted numerical diagnostics; they are not CIE response
integration and do not represent a target spectrum.

The checkpoint deliberately excludes aerosol, cloud, ground-albedo effects,
CIE response data, target spectra, pressure overrides, elevated observers,
runtime interpolation, limiting magnitude, and event time.

## Solver Parity

The governing direct solver remains pseudo-spherical 16-stream DISORT.
Fifty bulk direct-beam runs use `twostr`, followed by four DISORT stress
anchors:

- U.S. Standard, `0.25` degrees, 290 levels, REPTRAN fine;
- U.S. Standard, `0.25` degrees, 579 levels, REPTRAN medium;
- tropical, `0.25` degrees, 290 levels, REPTRAN medium; and
- U.S. Standard, `45` degrees, 290 levels, REPTRAN medium.

All four DISORT stdout files are byte-identical to their 8,001-row `twostr`
counterparts. This admits `twostr` only as a direct-beam generation
accelerator under these parity gates; DISORT remains the governing solver.

## Acceptance Results

Values below are maximum extinction-magnitude differences after equal-step
bin averaging.

| Comparison | 1 nm | 5 nm | 20 nm |
|---|---:|---:|---:|
| 290-level candidate vs 579-level reference | `0.0021747648486831893` | `0.0014793362143320915` | `0.0009251996429829469` |
| 579-level reference vs 1,157-level convergence control | `0.0005383102314783803` | `0.000428510572537017` | `0.0003788155571649315` |
| Conservative combined candidate grid bound | `0.0027130750801615698` | `0.0019078467868691084` | `0.0013040152001478783` |
| REPTRAN-fine 290-level candidate vs 579-level reference | `0.0009911761883017317` | `0.0008148543346673419` | `0.0007187127901082604` |
| Native 50-level grid vs 579-level reference | `0.18968620808949826` | `0.09127626084604672` | `0.08058758441655986` |

Frozen conservative combined limits are `0.003`, `0.0025`, and `0.002` mag
for 1, 5, and 20 nm bins. All pass. The native 50-level atmosphere remains
only a diagnostic and is not suitable for the low-altitude direct reference.

## Spectral Resolution Finding

The largest REPTRAN-medium versus REPTRAN-fine differences are:

| Bin | Maximum difference | Stress location |
|---|---:|---|
| 1 nm | `2.5079702399353927` mag | Tropical, `0.25` degrees, 760 nm |
| 5 nm | `0.43181699588608113` mag | Tropical, `0.25` degrees, 725 nm |
| 20 nm | `0.2718747355689283` mag | Tropical, `0.25` degrees, 720 nm |

The near-horizon tropical water-vapor structure and the oxygen A band make
medium resolution unsuitable as the full-spectral truth surface. REPTRAN fine
is therefore the admitted research reference. This does not require a runtime
table to carry 8,001 spectral samples: the implementation plan still requires
response-integrated runtime products after versioned CIE and target-spectrum
inputs are bound.

## Immutable Receipts

Repository specification:

```text
scripts/visibility_reference_lab/phase1_named_spectral_direct_probe_spec.json
bytes: 11509
SHA-256:
30822b4a90fe24c63872a904de8078770b2450c15798a6c24450fd6ecc0548ee
```

Builder:

```text
scripts/build_visibility_named_spectral_direct_probe.py
bytes: 68914
SHA-256:
0fc0809d2c95ba572e8aab9754783936d64933c7c381b324d4ee522f965cd7d2
```

Independent validator:

```text
scripts/validate_visibility_named_spectral_direct_probe.py
bytes: 46191
SHA-256:
0fe3b0abc46277ddf4230b3da15328a966e251e4bab1277ac61c056bb4258d99
```

External artifact:

```text
manifest bytes: 198494
manifest SHA-256:
b2bac79b30a3458fe17f8446b3da40f61deba1d7320b679724ebd60a65a539e8

generation fingerprint:
f9b370bdbd97e9a48976b07771fb048e84c452aff2c5aa8e4f3cd68fe9d2e608

bound files: 379
bound file bytes: 11203625
uvspec runs: 54
```

The validator independently reconstructs every grid, reparses every spectrum,
recomputes every comparison, checks all checksums, and rejects unbound files
or symlinks. The exact artifact passes under both WSL Python and Windows
Python 3.14.3.

The compact source-owned receipt is
`tests/artifacts/visibility_reference_lab/phase1_named_spectral_direct_checkpoint_2026-07-30.json`.
The direct-geometry predecessor remains byte-for-byte unchanged.

## Closed and Open

Closed by this checkpoint:

- the official REPTRAN module and merged external data-root identity;
- the six-profile clear molecular full-spectral direct surface;
- the named-atmosphere low-altitude error bound for the 290-level candidate;
- convergence of the 579-level reference against 1,157 levels;
- admission of REPTRAN fine as the full-spectral research reference;
- rejection of REPTRAN medium as a full-spectral truth substitute;
- byte-identical direct-beam parity for four DISORT anchors; and
- cross-platform independent artifact validation.

Still open:

- production observer-altitude and pressure policy;
- aerosol, AOD550, Angstrom, ozone-column, and albedo dimensions;
- adaptive sparse directional-radiance design;
- the deep-twilight solar-only tail;
- versioned CIE response and target-spectrum inputs;
- response-integrated spectral products;
- untouched off-grid holdouts;
- storage and interpolation selection;
- propagated limiting-magnitude and event-time error; and
- the separately versioned visibility data pack.

Phase 2 remains inactive.
