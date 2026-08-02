# Physical Heliacal Visibility Phase 4 Jones MYSTIC Holdout Checkpoint

Date: 2026-07-31

Status: corrected-v2 sealed 550 nm geometry holdout gate closed; lower-boundary
decision subsequently closed on 2026-08-02; runtime model not admitted

Candidate identifier: `jones_paranal_scattered_moonlight_2013_v1`

Pilot identifier: `jones_paranal_mystic_550nm_pilot_v2`

## Outcome

All three fresh geometry combinations reserved before the corrected-v2 pilot
threshold freeze passed the frozen 550 nm holdout contract. A fourth execution
repeated the interior cross-axis holdout with the same seed and was
byte-identical across all five scientific repeat files. An independent
validator reconstructed the complete input contract and reproduced every
reported metric.

This closes the corrected bounded geometry holdout gate. It does not admit a
spectral grid, interpolation surface, runtime model, production data pack,
public API, or network dependency.

## Correction Boundary

The original v1 pilot, threshold, and holdout evidence was invalidated after
the lower-boundary investigation exposed incorrect libRadtran explicit-aerosol
layer ownership. V1 listed physical files at upper rather than lower layer
boundaries. The exact v1 receipts remain preserved in
`phase4_jones_mystic_v1_invalidation_checkpoint_2026-07-31.json`, but none of
their numerical results is admissible.

The replacement protocol used a corrected v2 pilot, newly frozen v2 threshold
checkpoint, three previously unexecuted v2 holdout geometries, and a new seed.
Both the artifact and compact checkpoint bind the layout
`top_marker_then_null_gap_then_layer_files_at_lower_boundaries`.

## Freeze Ordering

The ordering is machine-bound:

1. Fifteen corrected-v2 pilot cases were executed and independently validated.
2. V2 numerical thresholds were frozen and committed to a canonical receipt.
3. The threshold checkpoint stated that no v2 holdout had been executed or
   used to select a threshold.
4. Only then did the runner derive four executions from the three reserved v2
   geometries and exact-repeat protocol.

No absolute holdout radiance was prefrozen. The gate tested finite positive
output, the prefrozen relative Monte Carlo uncertainty ceiling, and exact
fixed-seed repeatability.

## Frozen Protocol

Each unique holdout used:

- wavelength: `550 nm`;
- photon count: `1,000,000`;
- random seed: `271828183`;
- maximum relative standard error: `0.005`; and
- the same checksum-bound libRadtran 2.0.6 MYSTIC, ESO source members, and
  corrected explicit atmosphere/aerosol construction as the v2 pilot.

`holdout_v2_interior_cross_axis` was executed a second time with identical
inputs and seed.

## Results

| Holdout | Radiance (`W m-2 nm-1 sr-1`) | Standard error | Relative error |
|---|---:|---:|---:|
| `holdout_v2_low_altitude_oblique` | `3.09175e-08` | `3.71113e-11` | `0.0012003331` |
| `holdout_v2_interior_cross_axis` | `7.88475e-09` | `1.97965e-11` | `0.0025107327` |
| `holdout_v2_phase_boundary_waxing` | `9.54726e-09` | `2.84338e-11` | `0.0029782157` |

The worst relative error was `0.0029782157`, below the frozen `0.005` ceiling.
All radiances and standard errors were finite and positive. The repeat was
byte-identical for `mc.rad.spc`, `mc.rad.std.spc`, `mc0.rad`, `mc0.rad.std`,
and `randomseed`.

## Artifact and Tool Receipts

The corrected-v2 external artifact manifest is locked at:

- bytes: `30349`; and
- SHA-256:
  `d01f9d4a984c011d04b2d3cd2d3bde6bfeb426db4ae8bf030537b7f55777b321`.

The committed canonical checkpoint is 6,058 bytes with SHA-256
`5038773b2a2ea05cf07887f0acd45abe5d2e3b8503f81523ff6f35de3421ba4b`.
It binds:

- holdout builder SHA-256:
  `03debaad43172953eb1cd2586739e18d27ba7cdbcc20ca12256b444c223cd9cc`;
- holdout validator SHA-256:
  `304a94c2729e3dfcd058a0f009b482dc9f7512b9bb6adf44fc301afc51d5aa15`;
- corrected pilot builder and validator receipts;
- the exact v2 threshold specification and pre-holdout checkpoint;
- the v1 invalidation lineage;
- the libRadtran source archive, binary, build files, and data tree; and
- external ESO identities without redistributing their bytes.

## Independent Validation

The holdout validator independently derives the reserved-case execution
matrix, verifies every file receipt and run-directory inventory, reconstructs
the corrected explicit aerosol profile through the separately bound pilot
validator, parses MYSTIC outputs, recomputes all frozen checks, and validates
the compact checkpoint. Its final status is
`valid_corrected_v2_holdout_evidence`.

## Explicit Remaining Limitation at This Checkpoint

The atmosphere and ground still begin at the 2,640 m observer altitude,
whereas the Jones construction uses a 2,000 m lower model boundary beneath the
observer. The successful corrected-v2 pilot and holdouts do not erase this
difference. The next gate must reconstruct and validate that lower layer or
explicitly retain a separately versioned observer-bottom model before spectral
admission is designed.

That follow-on gate is now closed by the
[Jones MYSTIC lower-boundary checkpoint](PHYSICAL_HELIACAL_VISIBILITY_PHASE4_JONES_MYSTIC_LOWER_BOUNDARY_CHECKPOINT_2026-08-02.md),
which selects and independently validates the source-faithful 2,000 m lower
boundary with the observer retained at 2,640 m. This historical holdout receipt
remains the exact observer-bottom regression control.

## Machine-Checkable Files

- `scripts/build_visibility_phase4_jones_mystic_holdouts.py`
- `scripts/validate_visibility_phase4_jones_mystic_holdouts.py`
- `tests/artifacts/visibility_reference_lab/phase4_jones_mystic_holdout_checkpoint_2026-07-31.json`
- `tests/artifacts/visibility_reference_lab/phase4_jones_mystic_v1_invalidation_checkpoint_2026-07-31.json`
- `tests/unit/test_visibility_phase4_jones_mystic_holdouts.py`

## Reproduction

```bash
python3 scripts/build_visibility_phase4_jones_mystic_holdouts.py \
  --uvspec /home/nilad/.cache/moira/visibility-reference-lab/work/libRadtran-2.0.6/bin/uvspec \
  --lib-radtran-archive /home/nilad/.cache/moira/visibility-reference-lab/source/libRadtran-2.0.6.tar.gz \
  --data-root /home/nilad/.cache/moira/visibility-reference-lab/work/libRadtran-2.0.6/data \
  --eso-archive /mnt/c/Users/nilad/AppData/Local/Temp/moira-jones-20260731/SM-01.tar.gz \
  --output-root /home/nilad/.cache/moira/visibility-reference-lab/work/jones-mystic-holdouts-v2-20260731-1

python3 scripts/validate_visibility_phase4_jones_mystic_holdouts.py \
  --artifact-root /home/nilad/.cache/moira/visibility-reference-lab/work/jones-mystic-holdouts-v2-20260731-1 \
  --uvspec /home/nilad/.cache/moira/visibility-reference-lab/work/libRadtran-2.0.6/bin/uvspec \
  --lib-radtran-archive /home/nilad/.cache/moira/visibility-reference-lab/source/libRadtran-2.0.6.tar.gz \
  --data-root /home/nilad/.cache/moira/visibility-reference-lab/work/libRadtran-2.0.6/data \
  --eso-archive /mnt/c/Users/nilad/AppData/Local/Temp/moira-jones-20260731/SM-01.tar.gz
```

## Gate State

Closed:

- v1 invalidation with exact historical receipts;
- corrected lower-boundary ownership in the 550 nm pilot profile;
- v2 threshold freeze before any replacement holdout execution;
- all three fresh v2 geometry combinations;
- finite-positive output and frozen uncertainty checks;
- exact fixed-seed repeatability; and
- independent artifact and metric validation.

Still open:

- spectral wavelength/grid selection and interpolation thresholds;
- untouched spectral holdouts and response-integrated products;
- release/distribution disposition for any derived data artifact;
- engine implementation and typed component receipt;
- public-surface parity; and
- Phase 4 closure.
