# Physical Visibility Reference Lab

Status: Phase 1 complete research and data-pack tooling; not an engine runtime
dependency. The admitted pack remains a separate external artifact.

## Boundary

This directory owns the repository specification for Moira's external
libRadtran reference laboratory. The generator:

- accepts an already downloaded, checksum-pinned libRadtran archive;
- accepts an already built libRadtran source tree;
- performs no network access;
- runs only the explicitly authorized `convergence`, `geometry_smoke`, and
  `direct_transmission_smoke` profiles, plus the separately versioned
  elevated-site, direct-geometry, named-spectral direct, environmental, and
  altitude/pressure interpolation probes;
- writes each case atomically and binds every output file by SHA-256;
- rejects partial, unowned, stale, or tampered artifacts; and
- never enters the `moira` package or its installed dependency graph.

Checkpoint 1 is deliberately a sea-level pilot. The elevated-site checkpoint
adds a bounded 0-5,000 m construction for the named U.S. Standard atmosphere
with profile-derived pressure. Checkpoint 3 bounds low-altitude spherical
direct-beam geometry for a controlled exponential atmosphere. Checkpoint 4
admits a 380-780 nm REPTRAN-fine reference surface for all six AFGL named
atmospheres and validates the 290-level candidate against 579- and 1,157-level
controls. Checkpoint 5 source-binds the environmental-parameter contract,
including all eight Shettle haze/season profiles, AOD550 and Angstrom
semantics, ozone, pressure ownership, gray albedo, and the direct-beam
delta-M boundary. Checkpoint 6 admits site-relative altitude/pressure
interpolation against withheld values across all six molecular profiles.
The final radiance checkpoint admits 380-780 nm response-integrated photopic
and scotopic products, untouched off-grid holdouts, a 57-node direct
extinction surface, binary32 storage, and a fail-closed deep-twilight law. The
final compiler produces a separately licensed, checksummed data pack from
that admitted artifact. None of these specifications installs a table or
loader into the engine.

## Verified Build Environment

The first checkpoint was reproduced under Ubuntu 26.04 on WSL2 with:

```text
GCC/G++/GFortran 15.2.0
GNU Make 4.4.1
Flex 2.6.4
netCDF 4.9.3
GSL 2.8
Python 3.14.4
```

Ubuntu packages:

```bash
sudo apt-get install \
  build-essential \
  gfortran \
  flex \
  libnetcdf-dev \
  libgsl-dev \
  ca-certificates
```

These packages belong to the external research environment. They are not
Moira package dependencies.

## Source Lock

Use only the archive identity declared in `phase1_lab_spec.json`:

```text
libRadtran 2.0.6
bytes: 154147176
SHA-256:
64930cc40b6e4a37aa220520974d330fc1563796f466a649b2238131f2d69840
```

Source acquisition is an explicit operator action outside the builder. Verify
the archive before extraction:

```bash
sha256sum libRadtran-2.0.6.tar.gz
```

The named-spectral probe additionally requires the official external REPTRAN
module declared in `phase1_named_spectral_direct_probe_spec.json`:

```text
reptran_2024_all.tar.gz
bytes: 698709957
SHA-256:
55893c80bcc999651bac3bf014ee64aaf602653ba640eb5bebe787a5d8eacce7
```

The module is a separately downloaded research input. Its archive contains no
embedded notice or license file, so Moira does not redistribute it. The
builder accepts a separately constructed merged data root, verifies all 1,478
files through a canonical receipt, and performs no download.

The upstream archive contains two stale generated dependency files,
`libsrc_c/.depend` and `src/.depend`, with machine-specific include paths.
Remove only those two generated files from a fresh extraction before
building. No source patch is required.

## Configure, Build, and Test

From an empty work directory:

```bash
tar -xzf /path/to/libRadtran-2.0.6.tar.gz
cd libRadtran-2.0.6
rm -- libsrc_c/.depend src/.depend

CC=gcc \
CXX=g++ \
F77=gfortran \
FC=gfortran \
CFLAGS=-O2 \
CXXFLAGS=-O2 \
FFLAGS=-O2 \
./configure --prefix=/absolute/external/install/libRadtran-2.0.6

make -j"$(nproc)"
make check
make run_unittests
```

The first checkpoint recorded:

- `make check`: zero failed `uvspec` calls and zero failed difference checks;
- `make run_unittests`: 458067 assertions in 17 test cases;
- MYSTIC enabled;
- MYSTIC 3D disabled;
- GSL and netCDF4 enabled; and
- `mc_vroom on` exercised successfully by every generated case.

The upstream `make clean` target may exit nonzero when `libRadtran.so` does not
exist. The two exact stale `.depend` files above are the relevant archive
normalization; do not treat an unrelated recursive cleanup failure as
permission to remove broader paths.

## Inspect the Repository Specification

From the Moira repository:

```bash
python scripts/build_visibility_radiance_lut.py inspect
```

The reported 52,907,904,000-case Cartesian product is intentionally
prohibited. Candidate axes are an envelope for sparse-design research, not an
instruction to enumerate every combination.

## Generate Authorized Evidence

Choose a new, external output directory for each immutable run:

```bash
python scripts/build_visibility_radiance_lut.py build \
  --source-archive /absolute/source/libRadtran-2.0.6.tar.gz \
  --libradtran-root /absolute/work/libRadtran-2.0.6 \
  --output /absolute/artifacts/phase1_convergence \
  --profile convergence

python scripts/build_visibility_radiance_lut.py build \
  --source-archive /absolute/source/libRadtran-2.0.6.tar.gz \
  --libradtran-root /absolute/work/libRadtran-2.0.6 \
  --output /absolute/artifacts/phase1_geometry_smoke \
  --profile geometry_smoke

python scripts/build_visibility_radiance_lut.py build \
  --source-archive /absolute/source/libRadtran-2.0.6.tar.gz \
  --libradtran-root /absolute/work/libRadtran-2.0.6 \
  --output /absolute/artifacts/phase1_direct_transmission_smoke \
  --profile direct_transmission_smoke
```

Generation is serial by specification. The source archive, executable,
selected source files, source-data trees, specification, builder, and
validator are rechecked after the run and before the manifest is emitted.

Directional sky radiance uses fully spherical one-dimensional MYSTIC.
Direct transmission uses libRadtran's recommended double-precision DISORT
solver with pseudo-spherical geometry. For a target at true altitude `h`,
libRadtran's direct downward irradiance is normalized as:

```text
direct_spectral_transmission = (edir / E0) / sin(h)
extinction_magnitude = -2.5 log10(direct_spectral_transmission)
```

The distinction is intentional. `output_quantity transmittance` defines
irradiance output as `E/E0`, so the geometric projection must be removed to
recover line-of-sight transmission. The direct profile fixes a nonoperative
random seed only because `uvspec` writes a random-seed file even for this
deterministic solver.

## Generate the Elevated-Site Probe

Inspect and build the separately versioned probe:

```bash
python scripts/build_visibility_elevated_site_probe.py inspect

python scripts/build_visibility_elevated_site_probe.py build \
  --source-archive /absolute/source/libRadtran-2.0.6.tar.gz \
  --libradtran-root /absolute/work/libRadtran-2.0.6 \
  --output /absolute/artifacts/phase1_elevated_site_probe
```

libRadtran rejects its generic `altitude` option for Monte Carlo and rejects
`mc_elevation_file` with spherical MYSTIC geometry. The admitted research
construction therefore:

1. truncates the source atmosphere at the observing altitude;
2. uses libRadtran's default logarithmic, linear, and linear-mixing-ratio
   interpolation laws;
3. treats the new bottom level as the physical surface;
4. derives pressure from the named atmosphere rather than accepting an
   explicit pressure override; and
5. carries a bound O4 companion profile that reproduces libRadtran's
   preinterpolation O4 semantics.

The O4 companion is required because interpolating source-derived O4 is not
equivalent to recomputing O4 from interpolated O2. The 45 deterministic
DISORT pairs compare libRadtran's supported `altitude` construction with the
truncated profile at 0, 500, 1,500, 3,000, and 5,000 m. Seven spherical MYSTIC
runs add a byte-identical sea-level source/truncated control and a
byte-identical fixed-seed repeat at 1,500 m.

## Generate the Named-Spectral Direct Probe

Inspect the source-owned contract:

```bash
python scripts/build_visibility_named_spectral_direct_probe.py --inspect-spec
```

Build into a new external directory. `--max-new-runs` is optional and permits
durable bounded batches; the manifest is emitted only after all 54 runs pass.

```bash
python scripts/build_visibility_named_spectral_direct_probe.py \
  --source-archive /absolute/source/libRadtran-2.0.6.tar.gz \
  --reptran-archive /absolute/source/reptran_2024_all.tar.gz \
  --libradtran-root /absolute/work/libRadtran-2.0.6 \
  --data-root /absolute/work/libRadtran-2.0.6-reptran-2024/data \
  --output-root /absolute/artifacts/phase1_named_spectral_direct \
  --max-new-runs 10
```

The 50 bulk runs use `twostr` only for the direct-beam channel. Four stress
anchors rerun the same inputs with the governing pseudo-spherical 16-stream
DISORT configuration and require byte-identical 8,001-row stdout. REPTRAN fine
(1 cm-1 bands) is the admitted full-spectral reference. REPTRAN medium remains
a vertical-grid characterization surface because water and oxygen bands can
differ materially near the horizon.

## Generate the Environmental-Contract Probe

Inspect and build the separately versioned Checkpoint 5 probe:

```bash
python scripts/build_visibility_environment_contract_probe.py --inspect-spec

python scripts/build_visibility_environment_contract_probe.py \
  --source-archive /absolute/source/libRadtran-2.0.6.tar.gz \
  --libradtran-root /absolute/work/libRadtran-2.0.6 \
  --output /absolute/artifacts/phase1_environment_contract
```

The probe runs 73 deterministic cases covering direct-transmission invariance
to gray ground albedo, all eight named aerosol profiles, raw delta-M haze
diagnostics, AOD550, Angstrom exponent, ozone, pressure ratio, and an exact
repeat.

The direct-extinction oracle uses `aerosol_modify ssa set 0`. This preserves
total aerosol optical depth while excluding delta-M phase-function
bookkeeping from the physical line-of-sight extinction quantity. Directional
radiance keeps the physical aerosol single-scattering albedo and does not use
this override.

The environment contract admits measured surface-pressure overrides only
when both 500-1,100 hPa and a 0.85-1.08 ratio to the selected named profile at
observer altitude pass. Temperature and relative humidity remain
named-profile-derived because surface scalars do not define their vertical
profiles.

## Generate the Altitude/Pressure Interpolation Probe

Inspect and build the separately versioned Checkpoint 6 probe:

```bash
python scripts/build_visibility_altitude_pressure_interpolation_probe.py \
  --inspect-spec

python scripts/build_visibility_altitude_pressure_interpolation_probe.py \
  --source-archive /absolute/source/libRadtran-2.0.6.tar.gz \
  --libradtran-root /absolute/work/libRadtran-2.0.6 \
  --output /absolute/artifacts/phase1_altitude_pressure
```

The v5 design uses eight observer-altitude nodes from 0 through 5,000 m,
five pressure-ratio nodes from 0.85 through 1.08, fourteen altitude
holdouts, eight pressure holdouts, three target altitudes, three
wavelengths, and all six named molecular profiles. Its site-relative
290-level construction avoids the native-grid aerosol discretization defect
exposed by the rejected designs.

Interpolation is bilinear in extinction magnitude. It does not extrapolate
and rejects a query unless all four corners pass the 500-1,100 hPa absolute
bound and the 0.85-1.08 profile-relative pressure bound.

## Generate the Adaptive Radiance/Response Artifact

Inspect and build the final Phase 1 radiance artifact:

```bash
python scripts/build_visibility_radiance_response_probe.py --inspect-spec

python scripts/build_visibility_radiance_response_probe.py \
  --source-archive /absolute/source/libRadtran-2.0.6.tar.gz \
  --reptran-archive /absolute/source/reptran_2024_all.tar.gz \
  --libradtran-root /absolute/work/libRadtran-2.0.6 \
  --data-root /absolute/work/libRadtran-2.0.6-reptran-2024/data \
  --cie-root /absolute/source/cie \
  --named-direct-artifact /absolute/artifacts/phase1_named_spectral_direct \
  --output /absolute/artifacts/phase1_radiance_response
```

The 4-by-4-by-4 training grid spans solar-center altitude −9° through 0°,
target true altitude 0.25° through 45°, and relative solar azimuth 0° through
180°. Twenty-seven monochromatic midpoint combinations and nine separately
selected response-integrated combinations remain holdouts.

The 531 nm anchors use adaptive independent seeds. Full spectra use
REPTRAN-fine ALIS over 380-780 nm with an explicit
`mc_spectral_is 531` reference matching the shape normalizer. A separate
training-only six-wavelength diagnostic selected 531 nm by minimizing the
larger of the photopic and scotopic relative standard errors without
executing a holdout. The spectral photon schedule is fixed by solar node, and
the photopic/scotopic response
integrals use the exact CIE source identities bound by the specification.
Every seed, photon count, input byte, output file, convergence stop, and
source receipt is independently reconstructed by the validator.

The modeled solar-twilight table stops at −9°. A request below that bound is
not evaluable with reason `solar_twilight_below_data_pack_domain`; a Monte
Carlo zero is never converted into physical zero. Measured total or
directional background routes remain separate and unaffected.

## Build and Validate the Separate Data Pack

The final data pack is a separate CC BY-SA 4.0 artifact, not part of the MIT
engine wheel:

```bash
python scripts/build_visibility_data_pack.py --inspect-spec

python scripts/build_visibility_data_pack.py \
  --radiance-spec scripts/visibility_reference_lab/phase1_radiance_response_probe_spec.json \
  --source-artifact /absolute/artifacts/phase1_radiance_response \
  --cie-root /absolute/source/cie \
  --output /absolute/data-packs/moira-physical-heliacal-visibility-1.0.0

python scripts/validate_visibility_data_pack.py \
  /absolute/data-packs/moira-physical-heliacal-visibility-1.0.0
```

The compiler copies only response-integrated binary32 tables, direct
extinction, per-cell uncertainty, error envelopes, provenance, and notice
material. It includes no CIE source table, libRadtran/REPTRAN file, source,
or executable. The validator accepts only an explicit caller-supplied
directory and never searches for or downloads a replacement.

## Validate an Artifact

Pin the root-manifest hash in the consuming checkpoint:

```bash
python scripts/validate_visibility_radiance_lut.py \
  /absolute/artifacts/phase1_convergence \
  --expected-manifest-sha256 EXPECTED_SHA256

python scripts/validate_visibility_elevated_site_probe.py \
  /absolute/artifacts/phase1_elevated_site_probe \
  --expected-manifest-sha256 EXPECTED_SHA256

python scripts/validate_visibility_named_spectral_direct_probe.py \
  /absolute/artifacts/phase1_named_spectral_direct \
  --expected-manifest-sha256 EXPECTED_SHA256

python scripts/validate_visibility_environment_contract_probe.py \
  /absolute/artifacts/phase1_environment_contract

python scripts/validate_visibility_altitude_pressure_interpolation_probe.py \
  /absolute/artifacts/phase1_altitude_pressure

python scripts/validate_visibility_radiance_response_probe.py \
  /absolute/artifacts/phase1_radiance_response \
  --cie-root /absolute/source/cie
```

Validation checks:

- the complete authorized case inventory;
- the exact current specification and tool hashes;
- every case receipt and every file checksum;
- the byte-identical repeats for convergence and deterministic direct
  transmission evidence;
- source, build, toolchain, and runtime-boundary receipts;
- absence of unbound files and symlinks; and
- absence of a runtime or network dependency claim.

The elevated-site validator additionally verifies the exact governing
libRadtran source receipts, every case's generation identity, the central
atmosphere and O4 profile identities, deterministic oracle tolerances, and
both byte-identical MYSTIC controls.

The named-spectral validator independently reconstructs the 290-, 579-, and
1,157-level grids, reparses every spectrum, recomputes every 1/5/20 nm
comparison, verifies the external REPTRAN data-root receipt, and checks all
DISORT parity anchors. The checkpoint artifact was validated under both WSL
Python and the repository's Windows Python 3.14.3 environment.

The environmental-contract validator reconstructs the exact 73-case
inventory and environmental semantics, reparses every emitted value, checks
all source/tool/file receipts, and enforces the direct-albedo and admitted
same-season haze invariants, AOD/Angstrom/ozone/pressure trends, and the exact
repeat. Its admitted artifact also passed under WSL and Windows Python.

The altitude/pressure validator reconstructs the full 5,037-run inventory,
reparses all 15,111 spectral values, independently repeats bilinear
interpolation at 12,636 withheld values, enforces 396 explicit
complete-cell exclusions, and checks the unchanged maximum, p95, and
relative-transmission ceilings. Its admitted immutable bytes passed under
Linux and Windows.

## Current Scientific Limits

- The first `1.0.0` pack is a fixed-environment U.S. Standard, rural-summer,
  sea-level baseline at 1013.25 hPa, AOD550 0.1, Angstrom exponent 1.3,
  ozone 300 DU, and gray albedo 0.2. The environmental roles and the separate
  altitude/pressure evidence are admitted, but those dimensions are not
  silently present in this pack.
- Exact geometric horizon viewing is excluded because libRadtran forbids
  `umu=0`; the pack begins at 0.25 degrees true altitude.
- Modeled twilight is admitted only from -9 through 0 degrees solar-center
  altitude. Below -9 degrees it is typed `not_evaluable`; measured background
  routes remain separate.
- The response-integrated products cover 380-780 nm. The 531 nm
  monochromatic reconstruction is retained only as an intermediate diagnostic
  and is neither shipped nor interpolated at runtime.
- Clouds, moonlight, site-specific airglow, spectral target models, and
  environment domains beyond the fixed baseline require later separately
  sourced and validated work.
- Monte Carlo uncertainty varies across the twilight domain and is retained
  per cell. A zero-contribution result is never evidence of zero physical
  radiance.
- Phase 1 does not implement an engine loader or single-epoch limiting
  magnitude. Those belong to Phase 2; event-time error propagation belongs to
  Phase 3.
