# Physical Heliacal Visibility Phase 1 Closure

Date: 2026-07-30

Status: Phase 1 complete; Phase 2 is the next authorized phase

Runtime boundary: separately validated data pack exists, but no engine loader,
public API, release, or deployment is part of this phase

Governing plan:
[PHYSICAL_HELIACAL_VISIBILITY_IMPLEMENTATION_PLAN.md](../../06_roadmap/heliacal_visibility/PHYSICAL_HELIACAL_VISIBILITY_IMPLEMENTATION_PLAN.md)

Radiance evidence:
[PHYSICAL_HELIACAL_VISIBILITY_PHASE1_RADIANCE_RESPONSE_CHECKPOINT_2026-07-30.md](PHYSICAL_HELIACAL_VISIBILITY_PHASE1_RADIANCE_RESPONSE_CHECKPOINT_2026-07-30.md)

Compact closure receipt:
`tests/artifacts/visibility_reference_lab/phase1_closure_checkpoint_2026-07-30.json`

Closure-receipt SHA-256:
`6daaa62566214747dd50bc449da577065a2484c707ec39b7c1d88dafb0778776`

## Outcome

Phase 1 now has a reproducible offline atmospheric reference laboratory and a
separate immutable physical-visibility data pack. All admitted reference
artifacts and the final pack passed independent validation on Linux and
Windows. The pack is not installed into Moira and cannot be acquired
automatically.

The phase closes with:

- checksum-bound libRadtran 2.0.6 and REPTRAN 2024 source identities;
- named-atmosphere, environmental-role, aerosol, ozone, pressure, albedo, and
  direct-versus-radiance contracts;
- admitted observer-altitude and pressure-ratio direct-extinction
  interpolation evidence;
- adaptive response-integrated directional-radiance tables;
- untouched response and direct-extinction holdouts;
- separate solver, interpolation, and storage-error bounds;
- a versioned metadata-only compatibility contract;
- an exact-inventory, caller-path-only independent pack validator; and
- durable admitted and rejected-design receipts.

## Final Data Pack Identity

| Field | Value |
|---|---|
| Pack ID | `moira-physical-heliacal-visibility` |
| Version | `1.0.0` |
| Compatibility ID | `moira-physical-heliacal-visibility-data-pack-v1` |
| Format | `regular-grid-ieee754-binary32-le-v1` |
| License | CC BY-SA 4.0 |
| External directory | `moira-physical-heliacal-visibility-1.0.0-v2` |
| Files | 12 |
| Bytes | 110,481 |
| Payload files | 11 |
| Generation fingerprint | `b0d09b91086c2b3064e6c56cfaeae97226e7a6b2779fd70c5b7807aeab748750` |
| Manifest SHA-256 | `49ac2b68ea105a8e055b27e8d4d70f6cbfe9533f971ef5e6000f0bdd95d6771b` |
| Source-artifact manifest SHA-256 | `6bb91212d1d54762af8276ea066b4c6d5f4df837d84a46057f57b35924bae12f` |
| Linux validation | Passed |
| Windows validation | Passed |

The pack contains four 64-cell response products—photopic luminance,
scotopic luminance, and their per-cell relative standard errors—plus 22,800
direct-extinction values, axes, the admitted error envelope, provenance,
checksums, README, and licensing notice.

It contains no CIE source table, libRadtran or REPTRAN source/data file,
profile, executable, or engine code.

## First-Pack Domain

The first pack is deliberately a fixed-environment baseline:

| Input | Admitted value or interval |
|---|---|
| Molecular atmosphere | U.S. Standard |
| Aerosol profile | rural summer |
| Observer altitude | 0 m |
| Surface pressure | 1013.25 hPa |
| AOD550 | 0.1 |
| Angstrom exponent | 1.3 |
| Ozone | 300 DU |
| Gray ground albedo | 0.2 |
| Solar-center altitude | -9 to 0 degrees |
| Target true altitude | 0.25 to 45 degrees |
| Relative solar azimuth | 0 to 180 degrees |

The earlier Phase 1 environmental and altitude/pressure studies establish
source semantics and bounded evidence; they do not silently add those
environmental dimensions to this first pack. Phase 2 must return typed
`not_evaluable` outside the manifest's exact domain. A broader atmosphere,
altitude, pressure, aerosol, ozone, or albedo domain requires a new
versioned data pack and independent evidence.

This distinction prevents a flexible request contract from being mistaken
for data that the first pack does not actually contain.

## Interpolation and Error Contract

Response luminance uses trilinear interpolation in `log10` luminance over
solar altitude, target altitude, and relative solar azimuth. Direct
extinction uses linear interpolation in extinction magnitude over
`log10(target_true_altitude_deg + 0.25)` independently in each one-nanometre
spectral bin. Neither path extrapolates.

| Error owner | Admitted Phase 1 evidence |
|---|---|
| Photopic response interpolation | maximum 0.354270 mag; p95 0.287715 mag |
| Scotopic response interpolation | maximum 0.252966 mag; p95 0.244817 mag |
| Direct-extinction interpolation | maximum 0.0212954 mag; p95 0.00279149 mag |
| Binary32 storage | maximum `9.487461198887104e-7` mag |
| Solver uncertainty | retained per response cell |
| Limiting-magnitude propagation | Phase 2 owner |
| Event-time propagation | Phase 3 owner |

The 531 nm monochromatic reconstruction remains a transparent diagnostic
only. It is not shipped or used as a runtime interpolation surface.

Modeled twilight below -9 degrees solar-center altitude is typed
`not_evaluable` with reason
`solar_twilight_below_data_pack_domain`; a Monte Carlo zero is never treated
as physical zero.

## Validator and Failure Law

The independent validator accepts only an explicit caller-supplied directory.
It enforces:

- supported pack and format versions;
- exact file inventory and regular-file status;
- no symlinks or unexpected directories;
- manifest, payload, and `SHA256SUMS` identities;
- finite positive table values and exact axis/value counts;
- compatibility, interpolation, error-envelope, license, and provenance
  contracts; and
- zero network access.

Missing, corrupt, unsupported, or out-of-domain data fails explicitly. No
code path searches for or downloads a replacement.

The first compiled `1.0.0` candidate was rejected because two required notice
phrases were split by Markdown wrapping. Its numerical tables, checksums, and
provenance passed, but the artifact was not admitted. The rejected directory
remains immutable and is bound by
`phase1_visibility_data_pack_v1_failed_notice_checkpoint_2026-07-30.json`.
The admitted `v2` rebuild changes the notice packaging and tooling receipts,
not the scientific source artifact.

## Phase 1 Exit Gate

- [x] Source, generator, configuration, and external-data identities are
  checksum bound.
- [x] The documented external laboratory reproduced all admitted artifacts.
- [x] Admitted artifacts and the final pack pass Linux and Windows validation.
- [x] Untouched off-grid interpolation error is measured.
- [x] Solver, interpolation, and storage errors are separated.
- [x] Downstream error ownership is explicit without fabricated derivatives.
- [x] The immutable pack has exact file checksums and a versioned manifest.
- [x] Runtime use requires neither libRadtran nor network access.
- [x] The first-pack domain and fail-closed boundaries are explicit.
- [x] A source-controlled closure receipt binds all admitted checkpoints.

## Explicitly Unchanged

- no engine calculation, native code, facade, serializer, REST model, route,
  or OpenAPI contract changed;
- no engine loader exists yet;
- no table or CIE dataset entered the MIT wheel;
- no package dependency, default policy, or legacy output changed;
- no tag, package release, website install, or deployment occurred; and
- Phase 2 implementation has not begun.

## Next Authorized Work

Phase 2 may implement the Python spectral single-epoch truth layer against an
explicit caller-supplied, independently validated pack. It must enforce the
pack's exact domain and compatibility ID, preserve typed `not_evaluable`
results, and leave event-time solving to Phase 3.
