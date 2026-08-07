# Physical Heliacal Visibility Phase 4 Jones MYSTIC Lower-Boundary Checkpoint

> **Historical research only.** The proposed next gate in this checkpoint was
> canceled by the 2026-08-07
> [Jones/Paranal quarantine decision](PHYSICAL_HELIACAL_VISIBILITY_JONES_PARANAL_QUARANTINE_2026-08-07.md).
> Nothing in this document is an active product or release dependency.

Date: 2026-08-02
Status: Jones 2,000 m lower-model-boundary gate closed; source-faithful profile
selected for spectral research; spectral grid and runtime model not admitted

## Outcome

The Jones/ESO geometry is now resolved without retaining the corrected-v2
observer-bottom approximation as the candidate model.

The source-faithful research profile is:

`jones_2000m_ground_observer_2640m_v1`

It has:

- a 2.000 km lower atmosphere and ground boundary;
- an explicit 2.640 km observer level in both the atmosphere and O4 files;
- libRadtran `zout 0.64`, because numeric `zout` is height above the surface;
- 806.2488072631218 hPa at the 2.000 km surface, which preserves 744 hPa at
  the 2.640 km observer after the bound AFGL pressure scaling;
- 259.19991781804873 DU above the 2.000 km surface, which preserves the same
  `4.914335e11 cm-3` observer-level ozone number density as the 258 DU
  observer-bottom control; and
- the Jones exponential aerosol column down to 2.000 km while preserving every
  corrected-v2 layer boundary and optical property above 2.640 km.

The selection is controlled by the source semantics (`sm_h = 2.64` and
`sm_hmin = 2.0`), not by numerical closeness to the observer-bottom control.

## Frozen Comparison

The experiment compared two profiles at 550 nm:

| Profile | Surface | Observer | `zout` | Observer pressure | Role |
|---|---:|---:|---:|---:|---|
| `observer_bottom_control_v2` | 2.640 km | 2.640 km | 0.00 km | 744 hPa | Exact corrected-v2 holdout regression control |
| `jones_2000m_ground_observer_2640m_v1` | 2.000 km | 2.640 km | 0.64 km | 744 hPa | Source-faithful lower-boundary candidate |

The candidate aerosol receipt is:

- observer-to-infinite-top AOD550 normalization: `0.0294`;
- observer-to-20 km AOD550: `0.02939998466958803`;
- 2 km-to-20 km AOD550: `0.05011536771007698`; and
- restored below-observer AOD550: `0.020715383040488946`.

The candidate adds boundaries at 2.000, 2.250, 2.500, and 2.640 km, then uses
every corrected-v2 boundary above 2.640 km unchanged. Physical aerosol files
remain bound to inclusive lower boundaries. The 20-120 km region remains an
explicit null gap.

## Execution

The final matrix used the three corrected-v2 reserved holdout geometries for
both profiles, plus one exact candidate repeat:

- seven serial MYSTIC runs;
- 1,000,000 photons per run;
- fixed seed `271828183`;
- fully spherical one-dimensional MYSTIC; and
- a frozen maximum relative Monte Carlo standard error of `0.005`.

The control reproduced the committed corrected-v2 holdout radiance and
standard-error values exactly. The candidate repeat was byte-identical for
`mc.rad.spc`, `mc.rad.std.spc`, `mc3.rad`, `mc3.rad.std`, and `randomseed`.

MYSTIC uses its internal altitude-level index in the altitude-plane output
filename. The source-bound surface control therefore emits `mc0.*`, while the
2.640 km candidate observer emits `mc3.*`. This is an output identity detail,
not a change in the evaluated altitude.

## Measurements

| Case | Control radiance | Candidate radiance | Candidate/control | Relative change | Candidate minus control |
|---|---:|---:|---:|---:|---:|
| Low-altitude oblique | `3.09175e-08` | `3.26044e-08` | `1.0545613326` | `+5.4561%` | `-0.05768 mag` |
| Interior cross-axis | `7.88475e-09` | `8.07704e-09` | `1.0243875836` | `+2.4388%` | `-0.02616 mag` |
| Phase-boundary waxing | `9.54726e-09` | `9.60728e-09` | `1.0062866205` | `+0.6287%` | `-0.00680 mag` |

The maximum relative Monte Carlo standard error was
`0.002984007960629856`, below the frozen `0.005` ceiling.

These differences are measurements only. No candidate/control difference
threshold was prefrozen, and the numerical difference was not used to choose
the profile.

## Independent Validation and Reproducibility

The independent validator does not import the new lower-boundary builder. It:

- verifies every corrected-v2 lineage receipt;
- reopens the exact ESO and libRadtran archives and verifies the governing
  configuration and source members;
- independently reconstructs the 2.000 and 2.640 km atmosphere and O4 rows;
- independently reconstructs every candidate aerosol layer and Legendre
  representation;
- reparses every MYSTIC input and output;
- verifies the exact corrected-v2 control regression;
- recomputes all paired diagnostics and checks; and
- enforces the closed runtime, network, redistribution, and admission
  boundaries.

Two final artifacts were built serially from the same frozen contract. Their
entire directory trees were byte-for-byte identical:

- manifest: 71,981 bytes, SHA-256
  `4223b52c001f5f6e427130bdc4523c1031f617e904987c823a3cd18883911736`;
- compact checkpoint: 14,529 bytes, SHA-256
  `6c3ef3b750ff235719a3b9014e05bb5a5a7f6c022decc2f83a0f4f85f4906b31`.

The atmosphere-only probe initially left a time-varying, scientifically unused
`randomseed` file. The final builder removes that incidental file before
receipting the probe. The two final full-tree matches demonstrate that it no
longer contaminates reproducibility.

## Pre-Authority Attempts

Five pre-authority attempts are retained in the frozen specification history:

1. a profile probe rejected before radiance execution because its source
   declaration was incomplete;
2. a candidate inventory gate that discovered `mc3.*` instead of `mc0.*` at
   nonzero `zout`;
3. an inventory diagnostic that confirmed that profile-specific behavior;
4. a scientifically successful artifact superseded by zero-byte-receipt and
   probe-inventory validator hardening; and
5. an independently validated artifact superseded because the incidental
   probe `randomseed` receipt was time varying.

None is authoritative. The first three were atomically discarded; the two
retained external artifacts are explicitly superseded by the identical final
artifacts.

## Boundary

This checkpoint does not:

- admit a spectral wavelength grid or interpolation surface;
- admit a runtime Jones model or production data pack;
- change Moira engine calculations or public APIs;
- add a runtime, network, or automatic-download dependency;
- redistribute ESO or libRadtran source bytes; or
- modify the legacy `krisciunas_schaefer_1991` path.

## Repository Receipts

- `scripts/visibility_reference_lab/phase4_jones_mystic_lower_boundary_spec.json`
- `scripts/build_visibility_phase4_jones_mystic_lower_boundary.py`
- `scripts/validate_visibility_phase4_jones_mystic_lower_boundary.py`
- `tests/artifacts/visibility_reference_lab/phase4_jones_mystic_lower_boundary_checkpoint_2026-08-02.json`
- `tests/unit/test_visibility_phase4_jones_mystic_lower_boundary.py`

The full generated artifacts remain external because they contain derived
evidence built from caller-supplied GPL/source inputs. The repository stores
only the compact checksummed receipt.

## Next Gate

The next authorized work is:

`design_jones_2000m_ground_spectral_admission_matrix`

That design must freeze its wavelength grid, interpolation policy, numerical
thresholds, and untouched spectral holdouts before executing admission
holdouts. Phase 4 remains open, and no runtime implementation is authorized by
this checkpoint.
