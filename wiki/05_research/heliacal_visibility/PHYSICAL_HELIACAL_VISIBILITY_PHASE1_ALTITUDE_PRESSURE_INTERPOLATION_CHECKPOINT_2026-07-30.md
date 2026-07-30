# Physical Heliacal Visibility Phase 1 Altitude/Pressure Checkpoint

Date: 2026-07-30

Status: altitude/pressure interpolation gate passed; Phase 1 remains in
progress

Runtime boundary: research evidence only, not a runtime table or data pack

## Outcome

The direct-transmission laboratory now has frozen observer-altitude and
pressure-ratio nodes, an admitted interpolation coordinate, and independently
reserved holdouts. The admitted method is bilinear interpolation in
extinction magnitude. It does not extrapolate and it rejects a query unless
all four corners of its training cell satisfy both the absolute-pressure and
pressure-ratio bounds.

The final v5 artifact contains 5,037 deterministic libRadtran runs and 15,111
spectral values across all six named molecular atmospheres. Independent
validation evaluated 12,636 spectral values that were never used as training
nodes. Another 396 values were explicitly excluded because one or more
training-cell corners failed the already-frozen pressure-domain law.

## Admitted Grid

Observer-altitude training nodes are 0, 500, 1,000, 1,500, 2,250, 3,000,
4,000, and 5,000 metres. Fourteen separate altitude holdouts lie between
those nodes.

Pressure is represented as a ratio to the selected named atmosphere's
surface pressure at the observer altitude. Training ratios are 0.85, 0.925,
1.0, 1.04, and 1.08. Eight separate pressure-ratio holdouts lie between those
nodes. The 500-1,100 hPa absolute bound and the 0.85-1.08 ratio bound both
remain mandatory.

The validation cross-product uses target true altitudes 0.25, 5, and 20
degrees and wavelengths 400, 550, and 780 nm.

## Error Result

| Quantity | Measured | Fixed ceiling |
|---|---:|---:|
| Maximum absolute extinction error | 0.0124664 mag | 0.025 mag |
| 95th-percentile absolute extinction error | 0.00404537 mag | 0.01 mag |
| Maximum relative transmission error | 0.0114163 | 0.025 |

No acceptance threshold was relaxed after observing a holdout.

The worst case is the subarctic-winter profile at 3,250 m, pressure ratio
1.08, target altitude 0.25 degrees, and 400 nm. Its predicted extinction is
18.1641139 mag versus 18.1516475 mag from the withheld libRadtran run.

## Failed Designs Preserved

Four compact failure receipts remain source controlled.

1. The initial altitude holdouts failed the unchanged error ceiling.
2. A denser altitude-node design still failed because the native AFGL
   vertical grid changes surface-relative Shettle aerosol discretization when
   the bottom boundary crosses native levels.
3. The scientifically corrected site-relative grid passed numerically, but
   its validator incorrectly required arbitrary double values in a
   binary32-staged atmosphere profile to round-trip as doubles.
4. The next artifact passed on Linux but was rejected on Windows because the
   validator required byte equality for a recomputed logarithm that differed
   by approximately `1e-15`.

The admitted design keeps the source-bound, site-relative 290-level
near-horizon grid. The validator requires byte and checksum identity for raw
libRadtran outputs and stored canonical receipts, then compares independently
recomputed transcendental values with a fixed cross-platform numerical
tolerance. It does not weaken the scientific acceptance limits.

## Immutable Receipt

| Field | Value |
|---|---|
| Artifact directory | `phase1-altitude-pressure-interpolation-2026-07-30-v5` |
| Generation fingerprint | `ef95bba5a00667ce3bd1d983f9b9de93b989bd315da0e702f3342153d07bf165` |
| Manifest SHA-256 | `2264727cf4d1a74bb747aa51cc44e4ba9e703e09c132ab57eb2c0afef863c727` |
| Summary SHA-256 | `68648160b2d2b0f172fcc37715f1148e614f65f4f0a8e20a1bbfb1b8a4a04ab5` |
| Files | 50,768 |
| Bytes | 69,923,910 |
| Native Linux validation | Passed |
| Windows validation of the same immutable bytes | Passed |

The Windows validation used an immutable tar transport to local NTFS because
walking more than 50,000 individual WSL files through the UNC bridge is
prohibitively slow. The manifest and every per-file checksum were revalidated
after extraction.

## Boundary and Next Gate

No engine module, native code, public API, package dependency, or runtime data
changed. The artifact remains external research evidence.

The next Phase 1 gate freezes the solar-altitude, target-altitude, and
relative-azimuth adaptive radiance design; establishes a fail-closed
deep-twilight law; and runs untouched directional-radiance holdouts.
