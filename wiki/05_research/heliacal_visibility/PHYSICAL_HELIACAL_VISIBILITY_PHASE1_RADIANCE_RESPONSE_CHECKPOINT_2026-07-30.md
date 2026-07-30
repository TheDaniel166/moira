# Physical Heliacal Visibility Phase 1 Radiance/Response Checkpoint

Date: 2026-07-30

Status: adaptive radiance, response integration, interpolation, and storage
gate passed

Runtime boundary: external research evidence only; not an engine table,
loader, API, or release

Governing plan:
[PHYSICAL_HELIACAL_VISIBILITY_IMPLEMENTATION_PLAN.md](../../06_roadmap/heliacal_visibility/PHYSICAL_HELIACAL_VISIBILITY_IMPLEMENTATION_PLAN.md)

Predecessor:
[PHYSICAL_HELIACAL_VISIBILITY_PHASE1_ALTITUDE_PRESSURE_INTERPOLATION_CHECKPOINT_2026-07-30.md](PHYSICAL_HELIACAL_VISIBILITY_PHASE1_ALTITUDE_PRESSURE_INTERPOLATION_CHECKPOINT_2026-07-30.md)

Compact source-owned receipt:
`tests/artifacts/visibility_reference_lab/phase1_radiance_response_checkpoint_2026-07-30.json`

## Outcome

The final v9 artifact closes the remaining scientific-table questions for the
first physical-visibility data pack:

- an adaptive, independently seeded MYSTIC radiance design;
- source-locked CIE photopic and scotopic response integration;
- untouched off-grid response holdouts;
- a dense direct-extinction interpolation surface with untouched midpoint
  holdouts;
- separate solver, interpolation, and storage-error receipts;
- a fail-closed deep-twilight law; and
- an explicit boundary between shipped response products and a retained
  monochromatic diagnostic.

The same immutable artifact passed independent reconstruction under WSL
Python and the repository's Windows Python environment.

## Spectral Reference Selection

An initial 550 nm reference produced an imbalanced scotopic error. The failed
artifact was rejected before admission. A separate training-only diagnostic
then evaluated 507, 519, 531, 543, 550, and 555 nm over eight fixed seeds at
the exposed training point.

The 531 nm candidate minimized the larger of the photopic and scotopic
relative standard errors:

| Response | Relative standard error at 531 nm |
|---|---:|
| Photopic | 0.0185032 |
| Scotopic | 0.0710570 |

The diagnostic did not execute any holdout and did not alter the fixed
response-error ceilings. The final artifact uses 531 nm consistently for
spectral importance sampling, shape normalization, and the independent
absolute anchor.

## Admitted Response Surface

The response training grid is:

| Coordinate | Nodes |
|---|---|
| Solar-center altitude | -9, -6, -3, 0 degrees |
| Target true altitude | 0.25, 5, 20, 45 degrees |
| Relative solar azimuth | 0, 60, 120, 180 degrees |

Nine complementary Latin-square midpoint combinations were never used to
build or tune the 64-node table. Trilinear interpolation is performed in
`log10` response luminance.

| Quantity | Maximum error | 95th percentile | Fixed ceilings |
|---|---:|---:|---:|
| Photopic response | 0.354270 mag | 0.287715 mag | 0.5 / 0.3 mag |
| Scotopic response | 0.252966 mag | 0.244817 mag | 0.5 / 0.3 mag |

No response threshold was relaxed after holdout execution.

The full response calculations use REPTRAN-fine ALIS from 380 through 780 nm
and the exact source identities for the CIE photopic and scotopic tables.
Solver uncertainty is preserved per table cell. Across the completed
artifact, the maximum response relative standard errors are 0.209430
photopic and 0.232138 scotopic.

## Direct Extinction and Storage

The direct-extinction surface contains 57 target-altitude training nodes from
0.25 through 45 degrees and 400 one-nanometre spectral bins. Fifty-six
untouched midpoint altitudes produce 22,400 independently evaluated holdout
bins.

| Quantity | Measured | Fixed ceiling |
|---|---:|---:|
| Maximum extinction error | 0.0212954 mag | 0.05 mag |
| 95th-percentile extinction error | 0.00279149 mag | 0.02 mag |
| Mean extinction error | 0.000881366 mag | reported, not gated |

Interpolation is linear in extinction magnitude over
`log10(target_true_altitude_deg + 0.25)`. Extrapolation is prohibited.

Little-endian IEEE-754 binary32 was selected for the data pack. Its maximum
measured storage error is `9.487461198887104e-7` mag against a fixed
`1e-5`-mag ceiling. A separately evaluated quantized candidate also passed
its own ceiling but was not selected; the standard-library-readable binary32
format is simpler and retains materially more margin.

## Monochromatic Diagnostic Boundary

The reconstructed 531 nm surface remains in the error envelope as an
intermediate diagnostic. It is not:

- shipped as a runtime table;
- used by runtime interpolation; or
- an admission gate for the response-integrated products.

Its maximum comparison error is 0.544179 mag and its 95th-percentile error is
0.423551 mag. Reporting those values is intentional. Hiding them or treating
the monochromatic surface as an admitted proxy for the integrated responses
would be a false claim.

## Deep-Twilight Law

The modeled solar-twilight table ends at a solar-center altitude of -9
degrees. A request below that boundary is typed `not_evaluable` with reason:

```text
solar_twilight_below_data_pack_domain
```

A Monte Carlo non-detection is never converted into physical zero. Measured
directional or total-background routes are independent and remain available.
A future lower-Sun expansion requires new versioned data-pack evidence, not
an undocumented extrapolation.

## Immutable Receipt

| Field | Value |
|---|---|
| Artifact directory | `phase1-radiance-response-2026-07-30-v9` |
| Runs | 662 |
| Files | 5,621 |
| Bytes | 317,168,353 |
| Generation fingerprint | `aef8bdc07948ff5367dba1834baea708dfea0bc0dffb6898899dabc6f231c8c0` |
| Manifest SHA-256 | `6bb91212d1d54762af8276ea066b4c6d5f4df837d84a46057f57b35924bae12f` |
| Summary SHA-256 | `829774108d1c1337399784c20254c1d6cc5fc071d532450f4afb74431d870104` |
| Linux independent validation | Passed |
| Windows independent validation | Passed |

Eight rejected radiance designs remain represented by compact source-owned
failure receipts. They preserve convergence, zero-normalization, spectral
balance, exposed-holdout, interpolation, and cross-platform validation
failures without allowing any rejected artifact to become an admitted
baseline.

## Explicitly Unchanged

- no `moira` runtime or native code changed;
- no public Python, facade, serializer, REST, or OpenAPI contract changed;
- no installed dependency changed;
- no CIE, libRadtran, or REPTRAN source file entered the engine wheel;
- no automatic download or calculation-time network path was introduced; and
- limiting-magnitude and event-time error propagation remain owned by Phases
  2 and 3 respectively.

The next and final Phase 1 gate is compilation and dual-platform validation
of the separate immutable data pack.
