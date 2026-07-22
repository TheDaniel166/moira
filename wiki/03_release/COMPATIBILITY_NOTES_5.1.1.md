# Compatibility Notes — Moira 5.1.1

Date: 2026-07-22

This patch release is backward compatible with 5.1.0 and changes only the
reader-bound historical Delta-T admission for content-identified DE440/LE440
kernels.

## Corrected behavior

Before the 1972 atomic-clock boundary, a DE440-backed chart no longer fails
because the kernel identity lacks an admitted lunar tidal acceleration. The
engine now binds DE440/LE440 to `-25.936 arcsec/cy²` and performs the same
explicit historical source-basis translation already used for admitted
reader-backed products.

No caller flag or migration is required. Existing chart, position, house, and
REST request shapes are unchanged.

## Preserved boundaries

- Kernel identity still comes from SPK summary content, not the filename.
- Unknown or unadmitted DE/LE identities still fail closed for
  basis-sensitive historical Delta-T products.
- Modern direct-EOP epochs do not receive a tidal-basis correction.
- DE430/LE430 remains admitted at `-25.85 arcsec/cy²`.
- DE441/LE441 remains admitted at `-25.936 arcsec/cy²`.

## Upgrade action

Replace any installation-local DE440 hot patch with the published
`moira-astro==5.1.1` wheel. Services that import Moira must be restarted after
the package upgrade so all processes load the canonical mapping from the
released package.
