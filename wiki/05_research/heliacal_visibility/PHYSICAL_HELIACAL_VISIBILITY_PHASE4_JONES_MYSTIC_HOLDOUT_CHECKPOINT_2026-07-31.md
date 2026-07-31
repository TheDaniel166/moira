# Physical Heliacal Visibility Phase 4 Jones MYSTIC Holdout Checkpoint

Date: 2026-07-31
Status: sealed 550 nm geometry holdout gate closed; lower-boundary decision required before spectral design; runtime model not admitted
Candidate identifier:
`jones_paranal_scattered_moonlight_2013_v1`
Pilot identifier: `jones_paranal_mystic_550nm_pilot_v1`

## Outcome

All three geometry combinations reserved before the pilot threshold freeze
passed the frozen 550 nm holdout contract. A fourth execution repeated the
interior holdout with the same seed and was byte-identical across all five
scientific repeat files. An independent validator reconstructed the input
contract and reproduced every reported metric.

This closes the bounded geometry holdout gate. It does not admit a spectral
grid, interpolation surface, runtime model, production data pack, public API,
or network dependency.

## Freeze Ordering

The ordering is machine-bound:

1. Fifteen pilot cases were executed and measured.
2. Numerical thresholds were frozen and committed.
3. The threshold checkpoint stated that no holdout had been executed or used
   to select a threshold.
4. Only then did the holdout runner derive the four runnable cases from the
   three reserved geometries and the frozen repeat protocol.

No absolute holdout radiance was prefrozen. The holdout gate tested finite
positive output, the prefrozen relative Monte Carlo uncertainty ceiling, and
exact fixed-seed repeatability.

## Frozen Protocol

Each unique holdout used:

- wavelength: `550 nm`;
- photon count: `1,000,000`;
- random seed: `135791357`;
- maximum relative standard error: `0.005`; and
- the same checksum-bound libRadtran 2.0.6 MYSTIC, ESO source members, and
  explicit atmosphere/aerosol construction as the pilot.

`holdout_interior_combination` was executed a second time with the exact same
inputs and seed.

## Results

| Holdout | Radiance (`W m-2 nm-1 sr-1`) | Standard error | Relative error |
|---|---:|---:|---:|
| Horizon combination | `7.85928e-09` | `2.10308e-11` | `0.0026759194` |
| Interior combination | `7.81629e-09` | `2.05735e-11` | `0.0026321311` |
| ROLO phase-boundary waning | `9.59937e-08` | `2.61302e-10` | `0.0027220745` |

The worst relative error was `0.0027220745`, below the frozen `0.005`
ceiling. All radiances and standard errors were finite and positive.

The fixed-seed repeat was byte-identical for:

- `mc.rad.spc`;
- `mc.rad.std.spc`;
- `mc0.rad`;
- `mc0.rad.std`; and
- `randomseed`.

## Artifact and Tool Receipts

The final external artifact manifest is locked at:

- bytes: `28947`; and
- SHA-256:
  `8e009491741e11f5ea5491e627a93cb7f3db23da5495abb09181ed5290e82e77`.

The compact external checkpoint has SHA-256
`7cbe21b6b53969f68d2c95718f564f58ccf6932d7b83475252828fa17a491da0`.
Its committed canonical copy binds:

- holdout builder SHA-256:
  `302dd4c502fe8153f99cc2a8bdfca6c0cb9782599d96ae52a2119475e5ff2eb2`;
- holdout validator SHA-256:
  `d7bb1739ac016f8f01f449cbc1782c8f9f7f002d73a3a43c4d4a71c35267d984`;
- pilot builder and validator receipts;
- the exact frozen threshold specification and pre-holdout checkpoint;
- the libRadtran source archive, binary, build files, and data tree; and
- the external ESO archive/member identities without redistribution.

## Independent Validation

The holdout validator does not use the holdout builder to derive expected
geometries, lunar inputs, output values, or diagnostics. It imports only the
checksum-bound pilot validator for the already independent atmosphere,
aerosol, source-member, and libRadtran input reconstruction path. It then
independently derives the reserved-case execution matrix, verifies every file
receipt and run-directory inventory, parses the MYSTIC outputs, recomputes the
frozen checks, and validates the compact checkpoint.

The first generated artifact exposed a validator-only receipt rule that
incorrectly rejected a legitimate zero-byte `stderr.txt`. No numerical result
failed. The rule was corrected to permit zero-byte files, and the complete
four-case artifact was rebuilt under a new root so its manifest binds the
corrected validator. The earlier artifact is not the admitted checkpoint.

## Explicit Remaining Limitation

The atmosphere and ground still begin at the 2,640 m observer altitude,
whereas the Jones construction uses a 2,000 m lower model boundary beneath
the observer. The successful 550 nm pilot and holdouts do not erase this
difference. The next gate must resolve it by reconstructing the lower layer or
by declaring and validating a separately versioned observer-bottom model
before a spectral admission matrix is designed.

## Machine-Checkable Files

- `scripts/build_visibility_phase4_jones_mystic_holdouts.py`
- `scripts/validate_visibility_phase4_jones_mystic_holdouts.py`
- `tests/artifacts/visibility_reference_lab/phase4_jones_mystic_holdout_checkpoint_2026-07-31.json`
- `tests/unit/test_visibility_phase4_jones_mystic_holdouts.py`

Rebuild the final external artifact:

```bash
python3 scripts/build_visibility_phase4_jones_mystic_holdouts.py \
  --uvspec /home/nilad/.cache/moira/visibility-reference-lab/work/libRadtran-2.0.6/bin/uvspec \
  --lib-radtran-archive /home/nilad/.cache/moira/visibility-reference-lab/source/libRadtran-2.0.6.tar.gz \
  --data-root /home/nilad/.cache/moira/visibility-reference-lab/work/libRadtran-2.0.6/data \
  --eso-archive /mnt/c/Users/nilad/AppData/Local/Temp/moira-jones-20260731/SM-01.tar.gz \
  --output-root /home/nilad/.cache/moira/visibility-reference-lab/work/jones-mystic-holdouts-20260731-2
```

Independently validate it:

```bash
python3 scripts/validate_visibility_phase4_jones_mystic_holdouts.py \
  --artifact-root /home/nilad/.cache/moira/visibility-reference-lab/work/jones-mystic-holdouts-20260731-2 \
  --uvspec /home/nilad/.cache/moira/visibility-reference-lab/work/libRadtran-2.0.6/bin/uvspec \
  --lib-radtran-archive /home/nilad/.cache/moira/visibility-reference-lab/source/libRadtran-2.0.6.tar.gz \
  --data-root /home/nilad/.cache/moira/visibility-reference-lab/work/libRadtran-2.0.6/data \
  --eso-archive /mnt/c/Users/nilad/AppData/Local/Temp/moira-jones-20260731/SM-01.tar.gz
```

## Gate State

Closed by this checkpoint:

- execution ordering after the committed threshold freeze;
- all three reserved 550 nm geometry combinations;
- finite-positive output and frozen uncertainty checks;
- exact fixed-seed repeatability; and
- independent artifact and metric validation.

Still open:

- the 2,000 m versus 2,640 m lower-atmosphere decision;
- spectral wavelength/grid selection;
- interpolation thresholds and untouched spectral holdouts;
- response-integrated products;
- release/distribution disposition for any derived data artifact;
- engine implementation and typed component receipt;
- public-surface parity; and
- Phase 4 closure.
