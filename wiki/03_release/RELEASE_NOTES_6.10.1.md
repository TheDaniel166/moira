# Release Notes - Moira 6.10.1

**Release date:** 17 October 2026.

Moira 6.10.1 consolidates the Light Box Conformance Program (`GAP-007`),
100% `P0` runtime calculation-truth exposure (`171 / 171` production-user
surfaces), the three Natal Discovery REST packet endpoints, single-pass
`KernelPool` startup indexing, and the streamlined single-commit release gate
into a published baseline release.

## Runtime Light Box calculation exposure and conformance

- **Additive `ComputationTruth` and `*_with_truth` receipts across `P0` surfaces:**
  Core astronomical, sidereal, station, void-of-course, coordinate, node,
  obliquity, phenomena, planetary-hour, transit, chart-shape, chart-wheel, and
  relationship calculations expose typed stage, time-scale, frame, policy, and
  authority receipts alongside their results.
- **Complete public calculation inventory (`1,251` canonical surfaces):**
  Every public Python facade export and FastAPI OpenAPI operation is inventoried
  across `150` reviewed families (`171` `P0`, `354` `P1`, `726` `P2`).
- **100% `P0` admission and replay coverage:**
  All `171` `P0` production-user calculations (and `209` canonical calculations
  overall) are structurally admitted and bound to `63` passing replay contracts
  in `tests/evidence/lightbox/contracts.json`.
- **Single-commit release gate:**
  `scripts/check_lightbox_release_gate.py --exact-release` validates clean
  committed worktrees directly without requiring a separate two-commit
  parent-SHA ceremony.

## Natal Discovery and server performance

- **Bounded Natal Discovery REST routes:**
  `POST /v1/natal-discovery/dispositor-chains`,
  `POST /v1/natal-discovery/jones-shape`, and
  `POST /v1/natal-discovery/lunar-context` expose traditional dispositor graphs,
  Marc Edmund Jones 10-planet temperament shape evidence, and source-verified
  natal lunar context with explicit computation-truth receipts.
- **Single-pass `KernelPool` startup indexing:**
  `KernelPool._from_initial_readers` reuses already-parsed SPK segment indexes
  across initial pool slots during server initialization and prewarm.

## Validation and compatibility

See [compatibility notes](COMPATIBILITY_NOTES_6.10.1.md) before upgrading, and
[`LIGHT_BOX_CURRENT_STATUS.generated.md`](../03_validation/LIGHT_BOX_CURRENT_STATUS.generated.md)
for the machine-generated conformance summary.

