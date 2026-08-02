# Physical Heliacal Visibility Phase 4 Jones MYSTIC Pilot Checkpoint

Date: 2026-07-31

Status: corrected v2 550 nm pilot and pre-holdout threshold gate closed;
replacement sealed holdouts passed separately; spectral and runtime models not
admitted

Candidate identifier: `jones_paranal_scattered_moonlight_2013_v1`

Pilot identifier: `jones_paranal_mystic_550nm_pilot_v2`

## Outcome

The corrected, independently assembled libRadtran 2.0.6 MYSTIC pilot completed
all 15 declared cases. Every threshold frozen after those measurements and
before execution of the three new reserved holdouts passed. The result does
not admit a spectral grid, runtime model, production data pack, public API, or
network dependency.

The generated numerical artifact remains outside the repository. The
repository contains the generator and validator contracts, exact source and
tool receipts, compact measured checkpoints, and the frozen threshold
declaration. No libRadtran or ESO source bytes are redistributed.

## V1 Invalidation and V2 Correction

The original v1 pilot, threshold, and holdout evidence is invalid for
scientific admission. libRadtran applies each `aerosol_file explicit` property
file from its listed altitude upward to the next boundary; the uppermost line
is only a top marker. V1 listed each physical file at its layer's upper
boundary. That shifted every layer upward and placed the last physical layer
above the intended 20 km profile top.

The v1 builder and validator shared the same incorrect serialization, so
receipt, repeatability, convergence, and holdout checks could not detect the
source-semantics error. No engine, public API, runtime model, or production
data pack used the invalidated evidence. The exact old receipts and source
rule are preserved in
`phase4_jones_mystic_v1_invalidation_checkpoint_2026-07-31.json`.

V2 writes a null top marker, an explicit null gap down to the 20 km profile
top, and each physical file at its inclusive lower boundary. The pilot builder
and independent validator reconstruct and check that ownership separately.

## Pilot Boundary

The pilot remains one-wavelength evidence at 550 nm. Its 15 executed cases
cover target and Moon altitude, relative azimuth and separation, lunar phase
over the admitted 1.55-97 degree ROLO domain, waxing and waning sides,
Moon-Earth distance, three photon counts, three independent 300,000-photon
seeds, and an exact fixed-seed repeat.

Three fresh geometry combinations were reserved before corrected-v2 execution
and were not used to select thresholds. The sealed protocol assigns each
holdout 1,000,000 photons and seed `271828183`, with an exact repeat of
`holdout_v2_interior_cross_axis`.

The pilot uses checksum-locked ESO solar, ROLO, and `mie_m15s1.dat` inputs.
The aerosol phase function remains source-owned rather than independently
reconstructable. The radiative-transfer assembly is independent; the aerosol
microphysics is not claimed to be independent.

## Explicit Design Limitation

The pilot places the atmosphere and ground at the 2,640 m observer altitude.
Jones uses a 2,000 m lower model boundary beneath the observer. This difference
must be resolved or explicitly versioned before spectral or production
admission.

## Generated Artifact Receipt

The corrected-v2 external artifact manifest is locked at:

- bytes: `41237`;
- SHA-256:
  `f3a139617abe43ffc1098a6b2df5e90dc10a48a32b1219316a772e6d60245aa7`;
- executed cases: `15`;
- reserved holdouts: `3`;
- directional radiance range:
  `3.74437e-09` to `8.66392e-08 W m-2 nm-1 sr-1`; and
- runtime or network dependency: none.

The source archive, `uvspec` binary, and 1,300-file data tree remain bound by
SHA-256 values `64930cc40b6e4a37aa220520974d330fc1563796f466a649b2238131f2d69840`,
`d4e94259296a65f7700a0911f0dc7fc14aacde89985befac0266fe0a18531b7a`,
and `191e39b7d1d6554517227a21dfa0feea11ffc308889ffccbe938408ed0fbf207`.

## Frozen Threshold Results

| Check | Observed | Maximum |
|---|---:|---:|
| Relative standard error, all pilot cases | `0.0110471732` | `0.0125` |
| Relative standard error, base 1M case | `0.0034758176` | `0.004` |
| Standard-error times square-root-photons max/min | `1.009499576` | `1.05` |
| Three-seed 300K sample relative standard deviation | `0.0039599941` | `0.01` |
| Sample spread / mean reported relative error | `0.623234396` | `1.0` |
| Aerosol absolute angle reconstruction error | `0.2069652263` | `0.25` |
| Aerosol relative angle reconstruction error | `0.0075170261` | `0.01` |
| Absolute raw `k0 - 1` | `0.0006827257` | `0.001` |
| Unrepresented AOD fraction above profile top | `5.21443e-07` | `1e-06` |
| Radiance/source-ratio max/min | `1.0000041606` | `1.00001` |
| Absolute MYSTIC-SkyCalc difference | `0.0174360371 mag` | `0.15 mag` |

All directional outputs were finite and positive. The fixed-seed repeat was
byte-identical for `mc.rad.spc`, `mc.rad.std.spc`, `mc0.rad`, `mc0.rad.std`,
and `randomseed`.

The SkyCalc 2.0.9 comparison is source-owned operational evidence, not an
independent oracle. Its 550 nm `flux_sml` value converts to
`1.5224540982e-08 W m-2 nm-1 sr-1`; the matching corrected MYSTIC case produced
`1.4982e-08 W m-2 nm-1 sr-1`.

## Independent Validation

The validator independently reconstructs the atmosphere, O4 companion, lunar
source, corrected aerosol column and 512 Legendre moments, explicit layer
ownership, geometry, case set, repeat files, and convergence diagnostics. It
also verifies the exact generator and external-source receipts.

The threshold evaluator binds that artifact to the frozen v2 threshold
specification and exact SkyCalc capture. Its checkpoint status is
`corrected_v2_pilot_passes_threshold_gate_holdouts_not_executed`.

## Machine-Checkable Files

- `scripts/visibility_reference_lab/phase4_jones_mystic_pilot_spec.json`
- `scripts/build_visibility_phase4_jones_mystic_pilot.py`
- `scripts/validate_visibility_phase4_jones_mystic_pilot.py`
- `tests/artifacts/visibility_reference_lab/phase4_jones_mystic_pilot_checkpoint_2026-07-31.json`
- `scripts/visibility_reference_lab/phase4_jones_mystic_admission_thresholds.json`
- `scripts/audit_visibility_phase4_jones_mystic_thresholds.py`
- `tests/artifacts/visibility_reference_lab/phase4_jones_mystic_threshold_checkpoint_2026-07-31.json`
- `tests/artifacts/visibility_reference_lab/phase4_jones_mystic_v1_invalidation_checkpoint_2026-07-31.json`
- `tests/unit/test_visibility_phase4_jones_mystic_pilot.py`
- `tests/unit/test_visibility_phase4_jones_mystic_thresholds.py`

## Reproduction

```bash
python3 scripts/build_visibility_phase4_jones_mystic_pilot.py \
  --uvspec /home/nilad/.cache/moira/visibility-reference-lab/work/libRadtran-2.0.6/bin/uvspec \
  --lib-radtran-archive /home/nilad/.cache/moira/visibility-reference-lab/source/libRadtran-2.0.6.tar.gz \
  --data-root /home/nilad/.cache/moira/visibility-reference-lab/work/libRadtran-2.0.6/data \
  --eso-archive /mnt/c/Users/nilad/AppData/Local/Temp/moira-jones-20260731/SM-01.tar.gz \
  --output-root /home/nilad/.cache/moira/visibility-reference-lab/work/jones-mystic-pilot-v2-20260731-2

python3 scripts/validate_visibility_phase4_jones_mystic_pilot.py \
  --artifact-root /home/nilad/.cache/moira/visibility-reference-lab/work/jones-mystic-pilot-v2-20260731-2 \
  --uvspec /home/nilad/.cache/moira/visibility-reference-lab/work/libRadtran-2.0.6/bin/uvspec \
  --lib-radtran-archive /home/nilad/.cache/moira/visibility-reference-lab/source/libRadtran-2.0.6.tar.gz \
  --data-root /home/nilad/.cache/moira/visibility-reference-lab/work/libRadtran-2.0.6/data \
  --eso-archive /mnt/c/Users/nilad/AppData/Local/Temp/moira-jones-20260731/SM-01.tar.gz
```

## Gate State

Closed:

- corrected, checksum-bound 550 nm pilot matrix and generator;
- independent artifact validation and explicit aerosol-layer ownership;
- repeatability, convergence, aerosol representation, and lunar-source checks;
- corrected-v2 pre-holdout numerical threshold freeze; and
- fresh sealed holdouts in the companion holdout checkpoint.

Still open:

- an independently generated spectral grid and interpolation thresholds;
- untouched spectral holdouts and response-integrated products;
- release/distribution disposition for any derived data artifact;
- engine implementation and typed component receipt;
- public-surface parity; and
- Phase 4 closure.

The lower-boundary disposition listed by the original checkpoint was closed
on 2026-08-02 by the
[Jones MYSTIC lower-boundary checkpoint](PHYSICAL_HELIACAL_VISIBILITY_PHASE4_JONES_MYSTIC_LOWER_BOUNDARY_CHECKPOINT_2026-08-02.md).
This pilot remains the exact corrected-v2 observer-bottom control.
