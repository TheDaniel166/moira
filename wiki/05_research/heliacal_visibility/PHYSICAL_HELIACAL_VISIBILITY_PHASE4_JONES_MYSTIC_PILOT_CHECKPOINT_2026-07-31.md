# Physical Heliacal Visibility Phase 4 Jones MYSTIC Pilot Checkpoint

Date: 2026-07-31
Status: 550 nm pilot and pre-holdout threshold gate closed; sealed holdouts authorized; spectral and runtime models not admitted
Candidate identifier:
`jones_paranal_scattered_moonlight_2013_v1`
Pilot identifier: `jones_paranal_mystic_550nm_pilot_v1`

## Outcome

The independently assembled libRadtran 2.0.6 MYSTIC pilot completed all 15
declared cases and passed the thresholds frozen after those measurements and
before any of the three reserved holdouts were executed. The result supports
proceeding to the sealed-holdout gate. It does not admit a spectral grid,
runtime model, production data pack, public API, or network dependency.

The generated numerical artifact remains outside the repository. The
repository contains only the generator and validator contracts, exact source
and tool receipts, compact measured checkpoints, and the frozen threshold
declaration. No libRadtran or ESO source bytes are redistributed.

## Pilot Boundary

The pilot is deliberately one-wavelength evidence at 550 nm. Its 15 executed
cases cover:

- target and Moon altitude;
- relative Moon azimuth and target-Moon separation;
- lunar phase across the admitted 1.55-97 degree ROLO domain;
- waxing and waning sides;
- Moon-Earth distance;
- 100,000, 300,000, and 1,000,000 photon counts;
- three independent 300,000-photon seeds; and
- an exact fixed-seed repeat.

Three geometry combinations were reserved before execution and were not used
to select thresholds. The sealed protocol assigns each holdout 1,000,000
photons and seed `135791357`, with an exact repeat of
`holdout_interior_combination`.

The pilot uses the checksum-locked ESO solar, ROLO, and `mie_m15s1.dat`
inputs, while keeping the aerosol phase function classified as source-owned
rather than independently reconstructable. The radiative-transfer assembly
is independent; the aerosol microphysics is not claimed to be independent.

## Explicit Design Limitation

The pilot places the atmosphere and ground at the 2,640 m observer altitude.
Jones uses a 2,000 m lower model boundary beneath the observer. This bounded
pilot therefore does not claim a complete reproduction of the Jones model.
That difference must be resolved or explicitly versioned before any spectral
or production admission.

## Generated Artifact Receipt

The external artifact manifest is locked at:

- bytes: `40507`;
- SHA-256:
  `6357f1618530fb8e504c3c3a41d90b887ab8c4fa32d506a951987dc42625d4e5`;
- executed cases: `15`;
- reserved holdouts: `3`;
- directional radiance range:
  `3.74627e-09` to `8.68312e-08 W m-2 nm-1 sr-1`; and
- runtime or network dependency: none.

The generator is libRadtran 2.0.6 MYSTIC, built from source archive SHA-256
`64930cc40b6e4a37aa220520974d330fc1563796f466a649b2238131f2d69840`.
The exact `uvspec` binary has SHA-256
`d4e94259296a65f7700a0911f0dc7fc14aacde89985befac0266fe0a18531b7a`.
The 1,300-file data tree is bound by SHA-256
`191e39b7d1d6554517227a21dfa0feea11ffc308889ffccbe938408ed0fbf207`.

## Frozen Threshold Results

The threshold declaration was written only after pilot measurement and before
holdout execution. All frozen checks passed:

| Check | Observed | Maximum |
|---|---:|---:|
| Relative standard error, all pilot cases | `0.0110500546` | `0.0125` |
| Relative standard error, base 1M case | `0.0034754440` | `0.004` |
| Standard-error times square-root-photons max/min | `1.010655319` | `1.05` |
| Three-seed 300K sample relative standard deviation | `0.0036260242` | `0.01` |
| Sample spread / mean reported relative error | `0.571126412` | `1.0` |
| Aerosol absolute angle reconstruction error | `0.2069652263` | `0.25` |
| Aerosol relative angle reconstruction error | `0.0075170261` | `0.01` |
| Absolute raw `k0 - 1` | `0.0006827257` | `0.001` |
| Unrepresented AOD fraction above profile top | `5.21443e-07` | `1e-06` |
| Radiance/source-ratio max/min | `1.0000025623` | `1.00001` |
| Absolute MYSTIC-SkyCalc difference | `0.0177259533 mag` | `0.15 mag` |

All directional outputs were finite and positive. The fixed-seed repeat was
byte-identical for `mc.rad.spc`, `mc.rad.std.spc`, `mc0.rad`, `mc0.rad.std`,
and `randomseed`.

The SkyCalc 2.0.9 comparison is source-owned operational evidence, not an
independent oracle. Its 550 nm `flux_sml` value converts to
`1.5224540982e-08 W m-2 nm-1 sr-1`; the matching MYSTIC case produced
`1.4978e-08 W m-2 nm-1 sr-1`.

## Independent Validation

The validator independently reconstructs the atmosphere, O4 companion,
lunar source, aerosol column and 512 Legendre moments, geometry, case set,
repeat files, and convergence diagnostics. It also verifies the exact
libRadtran source archive, `uvspec` binary, data tree, ESO archive members,
pilot specification, builder, and validator receipts.

The threshold evaluator then binds that independently validated artifact to
the frozen threshold specification and the exact SkyCalc comparison capture.
Its checkpoint status is
`pilot_passes_frozen_threshold_gate_holdouts_not_executed`.

## Machine-Checkable Files

- `scripts/visibility_reference_lab/phase4_jones_mystic_pilot_spec.json`
- `scripts/build_visibility_phase4_jones_mystic_pilot.py`
- `scripts/validate_visibility_phase4_jones_mystic_pilot.py`
- `tests/artifacts/visibility_reference_lab/phase4_jones_mystic_pilot_checkpoint_2026-07-31.json`
- `scripts/visibility_reference_lab/phase4_jones_mystic_admission_thresholds.json`
- `scripts/audit_visibility_phase4_jones_mystic_thresholds.py`
- `tests/artifacts/visibility_reference_lab/phase4_jones_mystic_threshold_checkpoint_2026-07-31.json`
- `tests/unit/test_visibility_phase4_jones_mystic_pilot.py`
- `tests/unit/test_visibility_phase4_jones_mystic_thresholds.py`

Rebuild the external pilot from the exact caller-supplied inputs:

```bash
python3 scripts/build_visibility_phase4_jones_mystic_pilot.py \
  --uvspec /home/nilad/.cache/moira/visibility-reference-lab/work/libRadtran-2.0.6/bin/uvspec \
  --lib-radtran-archive /home/nilad/.cache/moira/visibility-reference-lab/source/libRadtran-2.0.6.tar.gz \
  --data-root /home/nilad/.cache/moira/visibility-reference-lab/work/libRadtran-2.0.6/data \
  --eso-archive /mnt/c/Users/nilad/AppData/Local/Temp/moira-jones-20260731/SM-01.tar.gz \
  --output-root /home/nilad/.cache/moira/visibility-reference-lab/work/jones-mystic-pilot-20260731-2
```

Independently validate it:

```bash
python3 scripts/validate_visibility_phase4_jones_mystic_pilot.py \
  --artifact-root /home/nilad/.cache/moira/visibility-reference-lab/work/jones-mystic-pilot-20260731-2 \
  --uvspec /home/nilad/.cache/moira/visibility-reference-lab/work/libRadtran-2.0.6/bin/uvspec \
  --lib-radtran-archive /home/nilad/.cache/moira/visibility-reference-lab/source/libRadtran-2.0.6.tar.gz \
  --data-root /home/nilad/.cache/moira/visibility-reference-lab/work/libRadtran-2.0.6/data \
  --eso-archive /mnt/c/Users/nilad/AppData/Local/Temp/moira-jones-20260731/SM-01.tar.gz
```

Evaluate the frozen thresholds from Windows:

```powershell
.\.venv\Scripts\python.exe scripts\audit_visibility_phase4_jones_mystic_thresholds.py `
  "\\wsl.localhost\Ubuntu\home\nilad\.cache\moira\visibility-reference-lab\work\jones-mystic-pilot-20260731-2" `
  --skycalc-capture "$env:TEMP\moira-jones-20260731\skycalc-jones-g50-waxing.fits"
```

## Gate State

Closed by this checkpoint:

- frozen, checksum-bound 550 nm pilot matrix and generator;
- exact generator, source, and external artifact receipts;
- independent artifact validation;
- repeatability and Monte Carlo convergence measurement;
- aerosol representation and lunar-source linearity measurement;
- pre-holdout numerical threshold freeze; and
- permission to execute the three sealed holdouts.

Still open:

- sealed holdout execution against the frozen thresholds;
- resolution or explicit versioning of the 2,000 m versus 2,640 m lower-boundary limitation;
- independently generated immutable spectral grid and response products;
- interpolation thresholds and untouched spectral holdouts;
- release/distribution disposition for any derived data artifact;
- engine implementation and typed component receipt;
- public-surface parity; and
- Phase 4 closure.
