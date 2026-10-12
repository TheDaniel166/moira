# Small-body catalog release 2026.10.10.1

Publication and activation were verified on October 12, 2026. This is a data
release, independent of the engine/PyPI version (production engine: 6.9.9).
The [public ephemerides page](https://moira-astro.com/ephemerides) exposes the
current catalogs, adaptive policies, receipts and historical downloads.

## Exact release identities

| Catalog | Bodies | Type-13 shards | Manifest SHA-256 |
| --- | ---: | ---: | --- |
| [moira-asteroids](https://moira-astro.com/kernels/asteroids/2026.10.10.1/manifest.json) | 11,223 | 449 | `3d6ef5dee648dad240ef9db4dfcc460a3ecbf0f1cb4b103d1d99f1056878319d` |
| [moira-comets](https://moira-astro.com/kernels/comets/2026.10.10.1/manifest.json) | 497 | 20 | `2c147176c66ea1b3c007bb779357c6afcc23ace6fbe9cc18ce169980b3198671` |

The packaged metadata-only manifests and canonical identity receipts now bind
these exact releases. Identity registries and aliases have not changed; BSP
data remain external, except for the unchanged 25-body asteroid wheel catalog
`moira-asteroids-wheel@2026.08.14.1`. Known identity is not installed position
capability. This source alignment does not itself publish a new engine wheel.

## Sampling and source freshness

- Asteroids: ten-day/seven-node base, with certified adaptive apsidal
  refinement for the 59 audited bodies in 40 rebuilt shards. The other 409
  shards are byte-identical and were hash-verified on the server before
  hard-link reuse. Policy: `moira-small-body-type13-apsidal-adaptive-v4`.
- Comets: the same base, with certified adaptive apsidal refinement for all
  497 admitted trajectories. Policy: `moira-comet-type13-apsidal-adaptive-v5`.
  The final October 11 source-solution census checked all 497 bodies; 38 were
  refreshed and 459 segments remained byte-identical.
- Local refinement starts at one day and is halved as necessary. Policy floors
  are 1.5 hours for repaired asteroids and 11.25 minutes for comets, not uniform
  spacing throughout the catalogs. Certification compares half-step witnesses
  under unchanged `8.64 s` event-time and `1e-9 AU` radial-distance gates.
  Failure requires finer sampling or rejection, not wider acceptance gates.
- Comet refinement queries are bounded to 32 Julian years with integration
  anchors. Coverage and target solutions remain manifest-declared;
  nongravitational-model and distant-apparition limitations are not removed
  by better interpolation.

## Validation scope and preserved evidence

Final sealed-release integration checked native state/element, coverage,
identity and provenance invariants for all 11,720 bodies; four frozen asteroid
element holdouts; six anchored asteroid apsidal events; and three anchored
comet events with Halley `JPL#75` and Encke `JPL#K273/22`. The largest comet
timing residual was `0.000603497 s`, inside the unchanged `8.64 s` gate.

All-body structural/provenance checks and adaptive internal convergence are
not an independent all-body/all-epoch JPL accuracy guarantee. The selected
external event comparisons do not claim that wider coverage. Scientific
validation/support files are byte-bound in each release manifest and its
`SHA256SUMS`; for example, the comet manifest includes
`validation/current-comet-anchored-oracle/report.json` and `source_review.json`.

The original September 28 element/node admission, holdouts and scientific
tolerances remain immutable. Its exact September asteroid and July comet
manifests are archived in
[tests/fixtures/small_body_release_manifests](../../tests/fixtures/small_body_release_manifests/README.md).
Those historical authority results are not relabelled to admit different
catalog bytes or Encke's newer solution. No new historical geometric-node
oracle sweep is claimed by the October release closure.

## Publication boundary

Server publication at `2026-10-12T16:14:02Z` verified staged/live release
identities, public manifests and checksums, selected BSP byte ranges and
production readiness. An independent live receipt at `16:21:47Z` confirmed
both manifest hashes and served small-body identities. Existing planetary
bindings were preserved: DE440 facade, DE441 server fallback and DE441
Workspace API. The unrelated Jupiter result remained unchanged.

Prior catalogs were retained: asteroid `2026.09.18.1` and the raw comet
rollback directory `rollback-raw-20261012`. No ephemeris files were deleted.
The ephemerides website update was subsequently staged and promoted from the
same verified artifact; historical downloads were preserved. Catalog
publication did not modify the unrelated Vedic work.
