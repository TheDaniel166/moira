# Physical Heliacal Visibility Phase 1 Elevated-Site Checkpoint

Date: 2026-07-29
Status: Phase 1 in progress; elevated-site reference construction validated
for named-profile-derived pressure; not a runtime table, data pack, or model
admission
Commit: Uncommitted working tree; no commit or push was requested for this
checkpoint
Governing plan:
[PHYSICAL_HELIACAL_VISIBILITY_IMPLEMENTATION_PLAN.md](../../06_roadmap/heliacal_visibility/PHYSICAL_HELIACAL_VISIBILITY_IMPLEMENTATION_PLAN.md)

## Outcome

The nonzero-observer-altitude research gate is closed for one bounded
construction:

- U.S. Standard atmosphere;
- site altitudes 0, 500, 1,500, 3,000, and 5,000 m;
- pressure derived from that named profile;
- a source-derived atmosphere whose bottom level is the physical site
  surface; and
- a separately bound oxygen-dimer companion profile preserving libRadtran's
  preinterpolation O4 semantics.

All 45 deterministic DISORT comparisons matched libRadtran's supported
`altitude` construction at the precision emitted by `uvspec`. The
sea-level source atmosphere and generated sea-level atmosphere produced
byte-identical spherical MYSTIC scientific files. A fixed-seed 1,500 m repeat
was also byte-identical.

This checkpoint does not admit an explicit pressure override, a production
altitude dimension, a radiance table, a data pack, or Phase 2.

## Why a Truncated Atmosphere Is Required

The libRadtran 2.0.6 manual defines atmosphere-file heights above mean sea
level and defines `zout` relative to the physical surface. Its source then
establishes three relevant constraints:

1. `altitude` inserts a physical surface and is supported by the deterministic
   one-dimensional oracle;
2. `altitude` is rejected with the Monte Carlo solver; and
3. `mc_elevation_file` is rejected with spherical MYSTIC geometry.

Therefore a spherical one-dimensional MYSTIC site cannot be represented by
adding `altitude` or by using `zout` alone. The validated construction cuts
the named atmosphere at the site altitude and lets its new bottom level
become the physical surface.

The governing upstream identities are bound in the specification:

| File | SHA-256 |
|---|---|
| `src/atmosphere.c` | `b900ade7e603260a47fec3efa305577ab6806bbf539021ec028a0c1360099cf8` |
| `src/uvspec_lex.l` | `174755190e50ecc3099c80a29cb71627c0a33a5e2009d1869c23140095658d89` |
| `src/ancillary.c` | `97dc576d1cb8f54c40d733cea3d5a56b49a0e7f8f39aa812e55ba7fbe1a7665f` |
| `libsrc_c/mystic.c` | `d1d981e0dd2e961f7f8991368b92e2179c382bab81c8ae72ed17cd31dbcab87b` |

Primary upstream documentation:

- [libRadtran 2.0.6 manual](https://www.libradtran.org/doc/libRadtran.pdf)
- [libRadtran basic usage](https://libradtran.org/doku.php?id=basic_usage)
- [Emde and Mayer 2007 spherical MYSTIC paper](https://acp.copernicus.org/articles/7/2259/2007/acp-7-2259-2007.pdf)

## Interpolation and O4 Closure

The generated atmosphere mirrors libRadtran's default vertical interpolation:

| Quantity | Construction |
|---|---|
| Pressure | logarithmic |
| Temperature | linear |
| Air number density | logarithmic |
| O3, O2, H2O, CO2, NO2 | linear mixing ratio against interpolated air |
| Numeric staging | binary32 at libRadtran assignment boundaries |
| Serialization | nine significant decimal digits, binary32 round-trip |

The first attempted cut exposed a subtle derived-species mismatch at 500 m,
0.5 degrees target altitude, and 380 nm. Its extinction differed from the
native deterministic construction by `1.243376991766354e-05` magnitude,
exceeding the declared `5e-06` tolerance.

The cause was not the atmosphere interpolation above. libRadtran derives O4
from O2 at the original source levels and then interpolates that O4 profile
when it inserts an altitude. A cut atmosphere would otherwise derive O4 from
the already-interpolated O2 value. Those operations are not equivalent.

The final construction generates a two-column O4 companion with the same
source-level derivation and linear-mixing-ratio interpolation, then supplies
it through `mol_file O4`. The corrected case and all other deterministic
comparisons matched exactly at emitted precision. No tolerance was relaxed.

## Repository Surface

- `scripts/visibility_reference_lab/phase1_elevated_site_probe_spec.json`
  fixes the source semantics, interpolation laws, five site altitudes,
  deterministic oracle, MYSTIC smoke, O4 closure, and research-only runtime
  boundary.
- `scripts/build_visibility_elevated_site_probe.py` generates bound atmosphere
  and O4 profiles, runs 97 authorized `uvspec` invocations, preserves failures,
  resumes only exact generation identities, and emits a complete immutable
  manifest.
- `scripts/validate_visibility_elevated_site_probe.py` independently validates
  current tool/spec identities, generator/source receipts, central profiles,
  every case profile and generation identity, all file checksums, direct
  tolerances, and both byte-identical controls.
- `tests/artifacts/visibility_reference_lab/phase1_elevated_site_checkpoint_2026-07-29.json`
  preserves the compact source-owned result and provenance receipt.
- `tests/unit/test_visibility_elevated_site_probe.py` covers interpolation,
  malformed inputs, O4 noncommutativity, forbidden MYSTIC options, stale
  resumability, tamper rejection, runtime boundaries, and checkpoint identity.

Checkpoint 1's specification, builder, validator, and three artifact manifests
remain byte-for-byte unchanged.

No engine module, public Python contract, facade, native calculation,
serializer, REST model, OpenAPI document, package dependency, runtime data
path, or default policy changed.

## External Artifact Receipt

| Field | Receipt |
|---|---|
| Root manifest SHA-256 | `823ac54a3a6a52a5ab709bffb80693ffc945f800c6957f9024053c52289557ff` |
| Root manifest bytes | `196890` |
| Bound files | `789` |
| Bound file bytes | `986265` |
| Site profiles | `5` |
| Direct comparisons | `45` cases, `90` `uvspec` runs |
| Spherical MYSTIC | `7` cases |
| Total `uvspec` runs | `97` |
| Network dependency | none |
| Engine/runtime dependency | none |

The independent validator confirmed:

- every file is bound;
- every case carries the exact build/spec/generator identity;
- every case uses its central atmosphere and O4 profile;
- all direct comparisons satisfy their original tolerances;
- the sea-level source/truncated control is byte-identical; and
- the 1,500 m fixed-seed repeat is byte-identical.

## Named-Profile Surface Values

| Site altitude | Derived pressure | Profile level source |
|---:|---:|---|
| 0 m | 1013.000000 hPa | existing source level |
| 500 m | 954.193054 hPa | interpolated |
| 1,500 m | 845.308228 hPa | interpolated |
| 3,000 m | 701.200012 hPa | existing source level |
| 5,000 m | 540.500000 hPa | existing source level |

These values are receipts for this named profile. They are not a general
altitude-to-pressure formula and do not authorize caller-supplied pressure
overrides.

## MYSTIC Smoke Evidence

Every site used a solar-center altitude of -6 degrees, target true altitude
of 5 degrees, relative solar azimuth of 180 degrees, 550 nm, 100,000 photons,
and seed `32452843`.

| Site altitude | Radiance (mW m^-2 nm^-1 sr^-1) | Reported RSD |
|---:|---:|---:|
| 0 m | 0.0150261 | 14.16% |
| 500 m | 0.0138112 | 19.94% |
| 1,500 m | 0.0124351 | 18.16% |
| 3,000 m | 0.0141600 | 16.46% |
| 5,000 m | 0.0117670 | 19.55% |

This is a construction smoke, not an altitude-response law. The fixed photon
count is still too noisy for production, and the samples must not be used as
an interpolation table.

## Remaining Phase 1 Gates

- expand direct transmission to the admitted spectral design and quantify
  near-horizon solver/model error;
- freeze the adaptive sparse radiance design and solver-uncertainty stopping
  law;
- resolve the deep-twilight solar-only tail against the natural-background
  boundary;
- generate admitted spectral products;
- run untouched off-grid validation cases only after the design is frozen;
- select and validate storage and interpolation representations;
- propagate source-solver, storage, and interpolation error into limiting
  magnitude and event time; and
- build, checksum, license, and validate the separate immutable visibility
  data pack.

Phase 2 remains inactive until those gates and the Phase 1 exit criteria close.
