# Physical Heliacal Visibility Phase 4 Jones MYSTIC V1 Invalidation Checkpoint

Date: 2026-07-31

Status: v1 pilot, threshold, and holdout evidence invalidated before runtime
admission; corrected v2 replacement evidence validated

## Finding

The libRadtran 2.0.6 source and `AERO_FILES` example establish that an
`aerosol_file explicit` property file owns the layer beginning at its listed
altitude and extending to the next higher boundary. The uppermost row is a top
marker; its property file is ignored.

The v1 writer instead listed each physical file at the layer's upper boundary.
That shifted every physical layer upward and placed the final one above the
intended 20 km profile top. Because the v1 builder and validator implemented
the same mistaken serialization, checksums, exact repeats, Monte Carlo
convergence, and sealed holdouts could all pass without testing the governing
source rule.

## Disposition

- The v1 external artifacts remain reproducible historical records.
- Their numerical results are not valid for scientific or runtime admission.
- No engine code, public API, runtime model, or production data pack consumed
  the v1 artifacts.
- The compact JSON invalidation checkpoint preserves every affected v1
  specification, tool, checkpoint, manifest, and commit receipt.
- V2 uses a top marker, a null 20-120 km gap, and physical files listed at
  their inclusive lower boundaries.
- V2 uses fresh holdout geometries and seed `271828183`; no v1 holdout value is
  reused as an admission expectation.

## Bound Evidence

The machine-readable receipt is:

`tests/artifacts/visibility_reference_lab/phase4_jones_mystic_v1_invalidation_checkpoint_2026-07-31.json`

It is 4,085 bytes with SHA-256
`083a267b527ceaf129416784ea2a088bbbde4840006469d7f1c4710b30588b2b`.
It binds libRadtran source archive SHA-256
`64930cc40b6e4a37aa220520974d330fc1563796f466a649b2238131f2d69840`,
`uvspec_lex.l` SHA-256
`174755190e50ecc3099c80a29cb71627c0a33a5e2009d1869c23140095658d89`,
and the `AERO_FILES` example SHA-256
`5b97de8f32828f44c0a568a4565bd94b9272dbe7524764b205a1e896309bb0ad`.

## Replacement Gate

The replacement pilot model is `jones_paranal_mystic_550nm_pilot_v2`. Its
corrected pilot, frozen threshold evaluation, fresh sealed holdouts, and
independent holdout validation all pass. At this checkpoint the next unresolved
gate was the Jones 2,000 m lower model boundary versus the 2,640 m observer
altitude. That gate was subsequently closed by the
[Jones MYSTIC lower-boundary checkpoint](PHYSICAL_HELIACAL_VISIBILITY_PHASE4_JONES_MYSTIC_LOWER_BOUNDARY_CHECKPOINT_2026-08-02.md).
No spectral or runtime model is admitted by either correction receipt.
