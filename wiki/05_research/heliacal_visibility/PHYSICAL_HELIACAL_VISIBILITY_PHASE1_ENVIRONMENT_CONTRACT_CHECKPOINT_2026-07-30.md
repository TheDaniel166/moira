# Physical Heliacal Visibility Phase 1 Environmental Contract Checkpoint

Date: 2026-07-30

Status:
Environmental-parameter semantics gate passed. Phase 1 remains in progress.
This is not a runtime-table, data-pack, engine, API, or release receipt.

Governing plan:
[PHYSICAL_HELIACAL_VISIBILITY_IMPLEMENTATION_PLAN.md](../../06_roadmap/heliacal_visibility/PHYSICAL_HELIACAL_VISIBILITY_IMPLEMENTATION_PLAN.md)

Predecessor:
[PHYSICAL_HELIACAL_VISIBILITY_PHASE1_NAMED_SPECTRAL_DIRECT_CHECKPOINT_2026-07-30.md](PHYSICAL_HELIACAL_VISIBILITY_PHASE1_NAMED_SPECTRAL_DIRECT_CHECKPOINT_2026-07-30.md)

Compact source-owned receipt:
`tests/artifacts/visibility_reference_lab/phase1_environment_contract_checkpoint_2026-07-30.json`

## Purpose

Checkpoint 4 admitted the clear molecular REPTRAN-fine direct-transmission
reference but deliberately left environmental parameters open. This
checkpoint resolves the control semantics required before an adaptive
radiance design can be trusted:

- observer altitude and pressure ownership;
- ozone-column meaning;
- AOD550 and Angstrom binding;
- the complete named Shettle haze/season inventory;
- aerosol visibility, humidity, and temperature ownership;
- ground-albedo placement; and
- the distinction between physical line-of-sight extinction and delta-M
  solver bookkeeping.

The checkpoint freezes parameter roles, candidate nodes, reserved holdouts,
and fail-closed boundaries. It does not claim that interpolation over those
nodes is already accurate.

## Source-Locked Laboratory

The probe binds:

- libRadtran 2.0.6 archive:
  `64930cc40b6e4a37aa220520974d330fc1563796f466a649b2238131f2d69840`;
- built `uvspec`:
  `d4e94259296a65f7700a0911f0dc7fc14aacde89985befac0266fe0a18531b7a`;
- ten governing manual/source files covering aerosol, pressure, ozone,
  relative humidity, Beer-Lambert/Chapman geometry, and delta-M output
  semantics;
- all eight `data/aerosol/shettle/tau550.<vulcan>.<season>` files; and
- the exact Checkpoint 4 specification, builder, validator, and compact
  checkpoint.

The source declarations are in
`scripts/visibility_reference_lab/phase1_environment_contract_probe_spec.json`.
Every declared byte count and SHA-256 is rechecked before generation.

## Frozen Environmental Contract

### Molecular atmosphere, temperature, and humidity

The first pack requires one of the six source-bound AFGL molecular profiles.
Near-surface temperature, water vapor, and relative humidity are derived from
that named profile.

Independent temperature or relative-humidity overrides are not admitted in
the first pack. libRadtran derives the aerosol-grid relative humidity from
the atmosphere's water-vapor density and temperature. Treating a single
surface humidity value as a complete vertical humidity profile would invent
missing atmosphere state.

An explicit humidity/temperature construction may be added later only under a
new source-identified profile law with its own validation.

### Observer altitude

The admitted construction remains the Checkpoint 2 source-equivalent
truncated atmosphere. The candidate nodes remain:

```text
0, 500, 1500, 3000, 5000 m
```

The following values are reserved as untouched interpolation holdouts:

```text
250, 1000, 2250, 4000 m
```

Interpolation across altitude remains unadmitted until those holdouts are
executed against direct-transmission and radiance quantities.

### Surface pressure

Default surface pressure is derived from the named atmosphere at the observer
altitude.

An explicit measured pressure override is admitted as an input policy, but
the table coordinate is:

```text
requested surface pressure
---------------------------------------------
named-profile pressure at observer altitude
```

Both the absolute pressure and the ratio must pass:

```text
absolute pressure: 500 to 1100 hPa
profile-pressure ratio: 0.85 to 1.08
```

This prevents an absolute pressure that is numerically inside a global box
but physically incoherent with the selected altitude/profile combination.
The ratio candidates are `0.85`, `0.925`, `1.0`, `1.04`, and `1.08`; separate
midpoint holdouts are reserved.

libRadtran's `pressure` control scales the pressure profile and well-mixed
gases. Ozone is then independently normalized to the requested above-observer
column.

### Ozone

Ozone is the total column above the observer altitude in Dobson units and maps
to:

```text
mol_modify O3 <value> DU
```

Candidate values are `200`, `250`, `300`, `350`, `400`, and `500 DU`, with
intermediate values reserved as holdouts.

### Aerosol optical depth and Angstrom exponent

AOD is authoritative at 550 nm. libRadtran's command accepts Angstrom
`alpha` and `beta`, so the exact binding is:

```text
beta = AOD550 * 0.55 ** alpha
```

The separate libRadtran visibility control is not exposed. Internally,
libRadtran maps the requested optical depth back to a Shettle visibility to
construct the vertical aerosol profile. Exposing both visibility and AOD
would create conflicting authorities for the same component.

The frozen candidate values are:

```text
AOD550: 0, 0.02, 0.05, 0.1, 0.2, 0.4, 0.7, 1.0
alpha:  0, 0.5, 1.0, 1.3, 1.8, 2.5
```

Intermediate holdouts are reserved and are not used to tune the future
table.

### Named aerosol profiles

The first-pack stratospheric background is fixed to libRadtran vulcan code
`1`. All eight supported lower-atmosphere haze/season combinations are named:

| Profile | Haze code | Season code |
|---|---:|---:|
| rural summer | 1 | 1 |
| rural winter | 1 | 2 |
| maritime summer | 4 | 1 |
| maritime winter | 4 | 2 |
| urban summer | 5 | 1 |
| urban winter | 5 | 2 |
| tropospheric summer | 6 | 1 |
| tropospheric winter | 6 | 2 |

Haze affects aerosol single-scattering albedo and phase behavior and therefore
belongs to directional radiance. With AOD550 and alpha fixed, the direct
extinction dimensions are season, AOD550, and alpha. The radiance dimensions
also include haze.

### Ground albedo

The first-pack surface law is explicitly a gray Lambertian approximation.
Candidate albedos are `0`, `0.02`, `0.1`, `0.2`, `0.5`, `0.8`, and `1.0`,
with separate holdouts.

Ground albedo is excluded from the direct-transmission table and included in
the radiance table. Spectral surface classes or BRDFs would require a separate
source and complexity decision.

## Delta-M Direct-Beam Finding

libRadtran's default delta-M treatment is appropriate for diffuse
radiative-transfer efficiency, but a raw direct-beam output can inherit a
small dependence on aerosol phase-function/haze type. That is not physical
point-source extinction: the Beer-Lambert direct term depends on total
extinction, not on how extinction is divided into forward scattering and
absorption.

The admitted direct-extinction oracle therefore preserves aerosol optical
depth while setting:

```text
aerosol_modify ssa set 0
```

for the direct-only generator run. This converts the same aerosol extinction
to absorption for solver bookkeeping, removing the aerosol delta-M term
without changing total line-of-sight extinction. Directional-radiance runs do
not use this override.

The 73-run artifact proves both sides:

- the raw delta-M diagnostic produces three distinct outputs across four haze
  codes; and
- the admitted direct-extinction oracle produces one byte-identical output
  within each season across all four haze codes.

This is an additive Checkpoint 5 solver identity. It does not rewrite the
clear-molecular Checkpoint 4 result, where no aerosol delta-M term existed.

## Numerical Evidence

The immutable artifact contains 73 deterministic cases:

- 7 ground-albedo direct-invariance cases;
- 8 named aerosol profile cases;
- 4 raw delta-M haze diagnostics;
- 24 AOD cases across `0.25`, `5`, and `20` degrees;
- 18 Angstrom cases at `400`, `550`, and `780 nm`;
- 6 ozone cases at `600 nm`;
- 5 pressure-ratio cases at `550 nm`; and
- 1 exact repeat.

Results:

- every albedo case has the same direct-output SHA-256;
- every admitted same-season haze case has the same direct-output SHA-256;
- summer and winter direct outputs differ;
- transmission decreases strictly with AOD at every tested altitude;
- near-horizon aerosol slant optical depth is materially nonlinear in AOD:
  the maximum/minimum `tau/AOD` ratio is `2.36273098116443` at `0.25`
  degrees, versus `1.08487839009281` at `5` degrees and
  `1.00578580135771` at `20` degrees;
- all alpha values are byte-identical at `550 nm`, proving the AOD550
  normalization;
- increasing alpha decreases `400 nm` transmission and increases `780 nm`
  transmission;
- increasing ozone decreases `600 nm` transmission;
- increasing pressure ratio decreases `550 nm` transmission; and
- the fixed repeat is byte-identical for input, output, seed, stderr, and
  syntax-check files.

The strong near-horizon AOD nonlinearity rejects an apparent shortcut:
direct aerosol extinction cannot be represented as one unit-AOD surface and
scaled linearly over the full `0-1` domain under the selected Shettle
construction.

## Artifact Identity

Admitted artifact:

```text
external directory:
  phase1-environment-contract-2026-07-30-v2
manifest SHA-256:
  e79a250b01f00783f272bae409fa323a94b5c7811375760bf536eaa7de6b0580
generation fingerprint:
  882f23ac18053ca616b01f175c31cc26a4c68411021506d80d8d308659060cb4
run count:
  73
```

The artifact passed its independent validator under both WSL Python and the
repository's Windows Python environment.

The discarded `v1` experiment exposed a one-ULP platform difference in a
derived logarithm. It is not admitted. The `v2` builder serializes derived
quantities to a fixed 15-significant-digit boundary and passes byte-level
cross-platform reconstruction.

## Explicitly Unchanged

- no `moira` runtime code changed;
- no native code changed;
- no public Python export, facade, serializer, REST model, route, or OpenAPI
  contract changed;
- no package dependency changed;
- no physical table entered the wheel;
- no network or automatic download entered normal calculation;
- no production data pack was authorized; and
- Phase 2 did not begin.

## Remaining Phase 1 Work

Checkpoint 5 closes environmental parameter roles and source semantics. It
does not close:

- altitude and pressure-ratio interpolation against reserved holdouts;
- solar/target/azimuth adaptive radiance nodes;
- a deep-twilight sampling and convergence law;
- versioned CIE response and target-spectrum inputs;
- response-integrated spectral products;
- storage precision and interpolation format;
- end-to-end error propagation;
- the separate checksummed visibility data pack; or
- the Phase 1 exit gate.

The next bounded gate is the altitude/pressure holdout and interpolation
study, followed by adaptive directional-radiance design. Phase 2 remains
inactive.
