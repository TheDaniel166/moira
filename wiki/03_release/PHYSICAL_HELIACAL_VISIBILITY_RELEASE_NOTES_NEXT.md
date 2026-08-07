# Physical Heliacal Visibility - Next-Release Notes

Status: Phase 7 engine release candidate; no version, tag, package publication,
or deployment is assigned by this document.

## Outcome

Moira now has an additive, opt-in physical point-source visibility family that
keeps atmospheric, visual-threshold, target, event, and error evidence visible.
It does not replace the legacy limiting-magnitude/arcus-visionis default.

The named composite model is immutable:

```text
clear_sky_naked_eye_point_source_v1
```

Its two public operations are:

- a single-epoch physical visibility assessment; and
- a four-phase first/last physical event search using explicit morning/evening
  and rising/setting semantics.

Both operations are available through their owning Python module, curated root
exports, facade functions, matching `Moira` methods, strict REST models, and
dedicated OpenAPI operations:

```text
POST /v1/visibility/physical-assessment
POST /v1/visibility/physical-event
```

## Scientific and data boundary

The admitted runtime resource is the separately distributed pack:

```text
pack: moira-physical-heliacal-visibility
version: 1.2.0
manifest SHA-256:
  cf93433a9f66a5ea92832271ce3c4b023fcc8693164803539a9f1be85b17468c
license: CC BY-SA 4.0
```

The MIT `moira-astro` distribution contains the compatibility contracts,
release identity, and resource notice. It does not contain the external
numerical payload, libRadtran, REPTRAN source/data, CIE source tables, or a
downloader. A caller supplies `VisibilityDataPackConfig`; a server operator
uses:

- `MOIRA_SERVER_PHYSICAL_VISIBILITY_DATA_PACK_DIRECTORY`; and
- optionally `MOIRA_SERVER_PHYSICAL_VISIBILITY_DATA_PACK_MANIFEST_SHA256`.

Normal execution remains offline. Missing, corrupt, incompatible, unexpected,
or out-of-domain evidence returns a typed failure rather than an extrapolated
or fabricated answer.

## Admitted targets and phases

- Mercury, Venus, Mars, Jupiter, and Saturn are admitted for single-epoch
  assessment inside their source-owned photometric/spectral domains.
- Mars, Jupiter, Saturn, and Sirius are admitted for all four physical event
  phases.
- Mercury and Venus event search fails closed as `body_phase_not_admitted`
  because required guard days can leave their admitted phase-angle domains.
- Other fixed stars and target families remain unadmitted until their
  photometry and spectral treatment have independent receipts.

## Validation

The Phase 7 capability matrix names the evidence class for every admitted
claim. The release boundary includes:

- primary-source equation checks;
- independent libRadtran holdouts excluded from LUT fitting;
- the Tousey-Koomen Table I bounded observational comparison;
- property and event-ownership invariants;
- legacy compatibility fixtures;
- public-object identity, serializer, REST, and OpenAPI parity;
- exact DE441/pack-bound event goldens;
- separate source-solver, storage, interpolation, root, magnitude-envelope,
  and event-time sensitivity receipts;
- exact Python/native differentials for the two private Phase 6 kernels; and
- deterministic external-pack archiving, wheel/sdist inspection, sdist
  reconstruction, two clean installs, native imports, exact pack loads, and an
  active socket-deny guard.

Historical apparition windows and the Sirius/Sothic case remain bounded legacy
corroboration. They are not presented as exact physical-model event truth.

## Native boundary

Phase 6 moved only two dense numerical operations to the required native
extension:

- spectral response-weight resolution; and
- direct-extinction interpolation.

Python still owns doctrine, model and resource admission, policy, invalid-domain
handling, typed status/reasons, event ownership, solver orchestration, receipts,
and public result construction. The Python numerical paths remain executable
differential oracles.

## Explicit exclusions

This release candidate does not claim support for clouds, live weather,
telescopic or extended-object visibility, direct solar visibility, lunar
crescent visibility through this point-source model, a global airglow model,
observer-population probability, or synthetic confidence.

The Jones/Paranal moonlight experiment is quarantined research. It is absent
from the runtime, public API, packaged compatibility resources, release gate,
and active roadmap; it is not a prerequisite for this release.

## Performance boundary

The private kernels pass their differential and microbenchmark admissions.
The representative first and warm assessment budgets pass. The recorded
Jupiter and Sirius event-search timing targets remain red and are documented as
performance limitations, not scientific or contract failures. No approximate
geometry, profile binning, or policy migration was admitted to conceal them.

## Downstream publication

Website documentation is intentionally not part of this engine Phase 7 change.
It may be updated only after an exact engine release artifact and the matching
external data-pack artifact are published and verified.
