# Physical Heliacal Visibility Phase 1 Checkpoint

Date: 2026-07-29
Status: Phase 1 in progress; reproducible reference-lab checkpoint, not a
runtime data pack and not a model-admission receipt
Commit: Uncommitted working tree; no commit or push was requested for this
checkpoint
Governing plan:
[PHYSICAL_HELIACAL_VISIBILITY_IMPLEMENTATION_PLAN.md](../../06_roadmap/heliacal_visibility/PHYSICAL_HELIACAL_VISIBILITY_IMPLEMENTATION_PLAN.md)

Subsequent evidence:
[PHYSICAL_HELIACAL_VISIBILITY_PHASE1_ELEVATED_SITE_CHECKPOINT_2026-07-29.md](PHYSICAL_HELIACAL_VISIBILITY_PHASE1_ELEVATED_SITE_CHECKPOINT_2026-07-29.md)
closes the bounded named-profile elevated-site construction gate. Statements
below that identify nonzero observer altitude as open describe this
checkpoint's historical boundary.

## Outcome

The external libRadtran 2.0.6 reference laboratory now has a
checksum-locked, offline generator and an independent artifact validator.
The first convergence, geometry, and direct-transmission evidence sets were
reproduced and bound to the exact source archive, executable, build
configuration, scientific input trees, repository specification, builder,
validator, and per-case outputs.

This checkpoint does not close Phase 1. It deliberately stops before a
production grid, interpolation law, runtime table, or data pack.

## Implemented Repository Surface

- `scripts/visibility_reference_lab/phase1_lab_spec.json`
  - fixes the research-only model and runtime boundary;
  - locks libRadtran 2.0.6 by bytes and SHA-256;
  - fixes fully spherical one-dimensional MYSTIC controls;
  - declares candidate domain envelopes without authorizing their Cartesian
    expansion;
  - defines a repeated convergence profile, a geometry smoke profile, and
    a repeated direct-transmission smoke profile, plus untouched holdouts; and
  - excludes exact-horizon and nonzero-observer-altitude generation until
    their constructions are admitted.
- `scripts/build_visibility_radiance_lut.py`
  - performs no download;
  - verifies source, build, executable, configuration, and input-data
    receipts;
  - renders deterministic path-neutral libRadtran inputs;
  - builds only three authorized serial profiles;
  - preserves failed cases for diagnosis;
  - resumes only complete, checksum-valid cases;
  - rejects unowned files and symlinks;
  - verifies a fixed-seed byte-identical repeat; and
  - rechecks immutable inputs before emitting a manifest.
- `scripts/validate_visibility_radiance_lut.py`
  - validates the exact current specification and tools;
  - validates the complete authorized case inventory;
  - verifies every bound file and checksum;
  - verifies build, source-data, environment, and runtime-boundary receipts;
    and
  - rejects stale, partial, extended, or tampered artifacts.
- `tests/artifacts/visibility_reference_lab/phase1_reference_lab_checkpoint_2026-07-29.json`
  - preserves the compact source-owned numerical and provenance receipt
    without adding libRadtran, CIE data, or a runtime table to the package.

No engine module, public Python contract, native calculation, facade,
serializer, REST model, OpenAPI surface, dependency declaration, or default
changed.

## External Build Receipt

| Field | Receipt |
|---|---|
| Source | libRadtran 2.0.6 |
| Archive bytes | `154147176` |
| Archive SHA-256 | `64930cc40b6e4a37aa220520974d330fc1563796f466a649b2238131f2d69840` |
| `uvspec` identity | `uvspec, version 2.0.6-MYSTIC` |
| `uvspec` SHA-256 | `d4e94259296a65f7700a0911f0dc7fc14aacde89985befac0266fe0a18531b7a` |
| Platform | Ubuntu 26.04, WSL2, Linux 6.6.114.1 |
| Compilers | GCC, G++, and GFortran 15.2.0 |
| Supporting tools | GNU Make 4.4.1, Flex 2.6.4, netCDF 4.9.3, GSL 2.8 |
| Flags | `CFLAGS=-O2 CXXFLAGS=-O2 FFLAGS=-O2` |
| Solver capabilities | MYSTIC, GSL, and netCDF4 enabled; MYSTIC 3D disabled; VROOM exercised |
| Upstream `make check` | 0 failed `uvspec` calls; 0 failed difference checks |
| Upstream unit tests | 458067 assertions in 17 test cases, all passed |

The official archive contains stale generated `src/.depend` and
`libsrc_c/.depend` files with machine-specific include paths. The documented
clean-build procedure removes only those two generated files. No libRadtran
source patch was applied.

## Immutable Artifact Receipts

| Profile | Cases | Files | Bytes | Root manifest SHA-256 |
|---|---:|---:|---:|---|
| Convergence | 21 | 274 | 96837 | `f5246c0b54b7f1e1cb126a275df5a6c425cf71759d7afcf704dff14d991c2487` |
| Geometry smoke | 6 | 79 | 30883 | `736cb97e0f5e4218bb386f0290454cc15140438126ca1ded70b3b54f49a9d10a` |
| Direct-transmission smoke | 13 | 92 | 43528 | `5eaac5edd15081836ef1a57c62e360421a5bd73f71276095cb0cd6ea78b80aa1` |

All three artifacts:

- validate against the current repository specification and tool hashes;
- bind every output file;
- claim no network or runtime dependency; and
- carry
  `phase1_reference_lab_evidence_not_runtime_data_pack` status.

The convergence profile reproduces the first case byte for byte when its seed
and inputs are repeated. The deterministic direct-transmission profile also
reproduces every raw output byte for its repeated case.

## Convergence Evidence

The convergence case is a sea-level, 550 nm, U.S. Standard atmosphere
reference with:

- solar center altitude: -6 degrees;
- target true altitude: 5 degrees;
- relative solar azimuth: 180 degrees;
- AOD550: 0.1;
- Angstrom exponent: 1.3;
- ozone: 300 DU;
- surface pressure: 1013.25 hPa; and
- ground albedo: 0.2.

Five independent seeds were run at every photon count:

| Photons | Mean radiance (mW m^-2 nm^-1 sr^-1) | Between-seed sample RSD | Mean MYSTIC-reported RSD |
|---:|---:|---:|---:|
| 20000 | 0.014740458 | 22.90% | 33.10% |
| 100000 | 0.013240120 | 7.86% | 15.13% |
| 500000 | 0.013153260 | 4.84% | 7.43% |
| 2000000 | 0.013222160 | 2.32% | 3.72% |

The uncertainty contracts with the expected Monte Carlo scale, but two
million photons still do not establish production precision.

## Geometry Evidence

Every case below used 500000 photons, seed `32452843`, and 550 nm:

| Case | Sun altitude | Target altitude | Relative azimuth | Radiance (mW m^-2 nm^-1 sr^-1) | Reported RSD |
|---|---:|---:|---:|---:|---:|
| Civil, near Sun | -6 deg | 5 deg | 0 deg | 0.463911 | 2.88% |
| Civil, quadrature | -6 deg | 5 deg | 90 deg | 0.0231493 | 5.95% |
| Civil, antisolar | -6 deg | 5 deg | 180 deg | 0.0140619 | 6.97% |
| Nautical, near horizon | -12 deg | 1 deg | 90 deg | 0.000040657 | 67.54% |
| Astronomical, near horizon | -18 deg | 0.25 deg | 90 deg | 0 sampled | not estimable |
| Sunset, high target | 0 deg | 20 deg | 90 deg | 4.62224 | 0.44% |

This is a decisive negative result for a fixed photon budget. The same budget
ranges from sub-percent uncertainty to an unusable sparse-contribution
estimate. The zero sampled at the deepest case is not physical-zero evidence
and is not admitted as a table value.

## Direct-Transmission Evidence

Direct transmission is a separate deterministic component. It uses
libRadtran's recommended double-precision DISORT solver with pseudo-spherical
geometry, 16 streams, true geometric target altitude, and:

```text
direct_spectral_transmission = (edir / E0) / sin(target_altitude)
extinction_magnitude = -2.5 log10(direct_spectral_transmission)
```

The sine division removes the horizontal irradiance projection from
libRadtran's documented `output_quantity transmittance` value. It is not an
empirical air-mass fit.

At 550 nm:

| Target altitude | Direct transmission | Extinction |
|---:|---:|---:|
| 0.25 deg | 0.0003724155 | 8.57243 mag |
| 0.5 deg | 0.0008554776 | 7.66948 mag |
| 1 deg | 0.0029792195 | 6.31474 mag |
| 2 deg | 0.0141836458 | 4.62053 mag |
| 5 deg | 0.1032076570 | 2.46572 mag |
| 10 deg | 0.2895282903 | 1.34577 mag |
| 20 deg | 0.5237992659 | 0.70209 mag |
| 45 deg | 0.7295975852 | 0.34229 mag |

At 5 degrees true altitude:

| Wavelength | Direct transmission | Extinction |
|---:|---:|---:|
| 380 nm | 0.0017691995 | 6.88056 mag |
| 450 nm | 0.0254750167 | 3.98471 mag |
| 550 nm | 0.1032076570 | 2.46572 mag |
| 650 nm | 0.2184704002 | 1.65152 mag |
| 780 nm | 0.3921759935 | 1.01630 mag |

These results are smoke evidence, not a runtime table. The final spectral
grid and a near-horizon solver/model error bound remain open.

## Packaging Boundary Audit

A fresh local Moira 6.1.0 CPython 3.14 Windows wheel was built from the
checkout. Its 632 entries contained:

- no libRadtran file or binary;
- no CIE spectral-response table;
- no visibility radiance LUT; and
- no Phase 1 lab artifact.

This was an unreleased local wheel audit, not a release-artifact identity.
Project dependency metadata was unchanged.

## Decisions Established by This Checkpoint

1. The final table cannot use one fixed photon count over the complete domain.
2. A full Cartesian expansion of the candidate envelopes is computationally
   and scientifically rejected. Before its 81-point spectral dimension it
   contains 653,184,000 combinations; with that dimension it contains
   52,907,904,000 cases.
3. The runtime design must use a source-justified adaptive sparse design and a
   solver-uncertainty stopping or rejection law.
4. Deep-twilight solar radiance cannot be treated independently of the
   Phase 4 natural-background boundary. A Monte Carlo non-detection must not
   be serialized as zero truth.
5. Direct transmission now has an explicit deterministic solver and
   normalization law, but only as a smoke profile. It is not yet a spectral
   production grid.
6. Nonzero observer altitude remains unadmitted. libRadtran rejects the
   generic `altitude` option with the Monte Carlo solver; using `zout` alone
   would leave atmosphere below the observer and would not represent an
   elevated ground site.
7. Exact geometric horizon remains outside the pilot because libRadtran
   forbids `umu=0`.

## Open Phase 1 Gates

- identify and validate an elevated-site construction, likely a
  source-derived atmosphere truncated at the site surface or an independently
  validated MYSTIC elevation construction;
- expand direct transmission to the admitted spectral design and quantify its
  near-horizon solver/model error;
- freeze the adaptive sparse sampling and Monte Carlo convergence law;
- determine whether the deep-twilight solar-only tail is generated,
  upper-bounded, or declared incomplete pending a measured/natural
  background;
- generate admitted spectral products;
- run the reserved off-grid cases only after the table design is frozen;
- compare storage representations and interpolation laws;
- propagate source-solver, storage, and interpolation error into limiting
  magnitude and event time;
- build, checksum, license, and validate the separate visibility data pack;
  and
- add the actual runtime loader only after that pack is admitted.

Phase 2 remains unauthorized until these gates and the Phase 1 exit criteria
close.
