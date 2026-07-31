# Physical Heliacal Visibility Implementation Plan

Date: 2026-07-31
Status: Phases 0 through 3 complete; Phase 4 is in progress
Scope: Moira engine truth, offline reference-data production, public Python
contracts, REST transport, validation, native strengthening, release
documentation, and later website adoption

## Purpose

This document is the governing implementation checklist for Moira's next
physical heliacal-visibility model.

The project is an additive modernization. It is not a repair to the admitted
legacy heliacal public surface, and it does not silently reinterpret any
existing visibility-policy value.

The intended result is a versioned, opt-in, naked-eye point-source visibility
stack with:

- source-locked atmospheric and human-vision components;
- deterministic offline runtime behavior;
- physical event timing based on a visibility-margin crossing;
- explicit model validity, dependency completeness, and provenance receipts;
- identical effective policy across Python, facade, serializer, REST, and
  OpenAPI surfaces; and
- optional native acceleration only after Python doctrine is frozen.

The current model remains authoritative for its existing contract until every
required admission gate in this document passes.

## Reading Rule

A checked task means the named work and its evidence receipt are complete.
Writing code, producing a table, or passing a narrow unit test is not by itself
a completed phase.

Quarantined scope is not unfinished work. It may be reopened only as a new
source-and-admission project with an explicit contract proposal.

## Current Engine Baseline

The existing Python implementation in `moira/heliacal.py` provides:

- legacy arcus-visionis event search;
- Kasten-Young 1989 relative air mass;
- Schaefer component extinction and directional twilight calculations;
- Krisciunas-Schaefer moonlight handling;
- Crumey 2014 naked-eye point-source threshold assessment;
- measured-SQM and Bortle background inputs;
- explicit physical-model validity checks; and
- typed single-epoch visibility assessments.

The admitted physical path is intentionally bounded:

- it is opt-in;
- single-epoch assessment admits Mercury through Saturn and Sirius;
- event search admits Mars, Jupiter, Saturn, and Sirius;
- it is naked-eye and point-source only;
- Mercury, Venus, and other unsupported event targets fail closed rather than
  fabricating event times; and
- legacy behavior remains the default.

The current native implementation in `src/native/include/visibility.hpp`
contains the admitted legacy arcus computation and fixed-star search support.
It does not contain the newer physical assessment stack.

The current public-contract gaps relevant to this project are:

- `Moira` exposes `visibility_tonight()` and `is_visible_tonight()` but does
  not expose the general `visibility_event()` facade method;
- the general REST visibility-event request does not accept the full
  visibility policy;
- the general REST event response does not expose a complete typed physical
  receipt; and
- existing heliacal validation and closure documents predate the current
  physical single-epoch implementation.

These are modernization inputs, not evidence that the existing legacy event
contract is broken.

## Completion Boundary

The first public physical-event release requires Phases 0 through 5 and Phase
7 to close.

Phase 6 is a measured performance decision. Scientific completion does not
require moving policy or doctrine into C++.

The website is downstream. Website presentation begins only after the engine,
transport, and release-documentation gates close.

## Non-Negotiable Compatibility Rules

- [x] Existing visibility-policy enum strings retain their current meanings.
- [x] Existing request defaults remain unchanged.
- [x] Existing legacy outputs remain regression protected.
- [x] The new model is selected explicitly through a versioned policy.
- [x] The normal installed runtime performs no network access.
- [x] Missing optional data never triggers an ambient download.
- [x] Unsupported or incomplete physical cases fail closed with a typed reason.
- [x] Scientific uncertainty remains separate from solver precision.
- [x] No synthetic confidence score is admitted without a defensible
  population model.
- [x] Python owns public semantics, doctrine, policy resolution, and result
  construction.
- [x] C++ may own only admitted, differential-tested numerical kernels.
- [x] A default-model change is a future major-version decision, not part of
  this roadmap.

Frozen composite model identifier:
`clear_sky_naked_eye_point_source_v1`.

The identifier is a first-class immutable model family, not a mutable alias for
the newest implementation.

Phase 0 decisions are governed by:

- [PHYSICAL_HELIACAL_VISIBILITY_ADMISSION_DOCTRINE.md](../../01_doctrines/heliacal_visibility/PHYSICAL_HELIACAL_VISIBILITY_ADMISSION_DOCTRINE.md);
  and
- [PHYSICAL_HELIACAL_VISIBILITY_SOURCE_LEDGER_2026-07-29.md](../../05_research/heliacal_visibility/PHYSICAL_HELIACAL_VISIBILITY_SOURCE_LEDGER_2026-07-29.md).

## Source Hierarchy

The implementation must distinguish current admitted components from candidate
modernization sources.

| Source or model | Planned role | Admission boundary |
|---|---|---|
| Schaefer 1990/1993 | Preserve the existing named component model and use it as a regression/reference family | Do not silently replace its formulas |
| Kasten and Young 1989 | Preserve the existing broadband relative-air-mass option | Do not extend beyond its admitted domain |
| Krisciunas and Schaefer 1991 | Preserve the current moonlight option | A modern moonlight model receives a new identifier |
| [Crumey 2014](https://arxiv.org/abs/1405.4209) | Preserve the current scotopic component and source the separately named full-range point-source candidate | Twilight use requires independent observational validation |
| [libRadtran 2.0.6](https://www.libradtran.org/doku.php?id=start) | Offline reference generator for direct transmission and directional twilight radiance | No installed-runtime dependency or invocation |
| [CIE MES2](https://files.cie.co.at/841_CIE_TN_004-2016.pdf) | Declared photopic/scotopic spectral weighting across adaptation states | A weighting system, not a point-source detection threshold |
| [CIE photopic response](https://cie.co.at/datatable/cie-spectral-luminous-efficiency-photopic-vision) | Versioned `V(lambda)` response data | Kept in the separately licensed data pack |
| [CIE scotopic response](https://www.cie.co.at/datatable/cie-spectral-luminous-efficiency-scotopic-vision) | Versioned `V'(lambda)` response data | Kept in the separately licensed data pack |
| [Tousey and Koomen 1953](https://opg.optica.org/josa/abstract.cfm?uri=josa-43-3-177) | Source-owned twilight comparison observations | Validation evidence, not a universal coefficient table |
| [Jones et al. 2013](https://doi.org/10.1051/0004-6361/201322433) | Candidate modern physical moonlight model | New named Paranal-only option; validate independently inside its frozen domain before considering any later site transfer |
| [ESO SkyCalc](https://www.eso.org/observing/etc/doc/skycalc/helpskycalccli.html) | Component comparison and validation reference | Never claim global authority from a site model |
| [PALACE](https://gmd.copernicus.org/articles/18/4353/2025/) | Airglow research and component-validation reference | Site-bound unless independent evidence supports expansion |

No formula may be implemented from recollection or a secondary summary when
the primary paper, official dataset, or official software documentation is
available.

## Architecture

### Governing Python layer

`moira/heliacal.py` continues to own:

- public enums and dataclasses;
- policy resolution;
- event-kind doctrine;
- supported-domain decisions;
- typed failure reasons;
- public orchestration; and
- compatibility projections.

The new numerical implementation should not make that protected module a
monolith. Candidate internal modules are:

- `moira/_visibility_lut.py`
  - manifest validation;
  - checksum verification;
  - data-domain checks;
  - table loading; and
  - interpolation.
- `moira/_visibility_spectral.py`
  - target transmission;
  - directional sky-radiance composition;
  - CIE response integration;
  - apparent target conditioning; and
  - limiting-magnitude evaluation.
- `moira/_visibility_event_solver.py`
  - observation-window construction;
  - adaptive sampling;
  - complete root bracketing;
  - threshold refinement; and
  - first-day or last-day event classification.

`moira/sky/visibility.py` remains a public re-export boundary rather than a
second doctrine owner.

### Offline reference-data layer

Candidate build surfaces are:

- `scripts/build_visibility_radiance_lut.py`;
- `scripts/validate_visibility_radiance_lut.py`;
- an engine-side metadata-only compatibility manifest;
- a separately distributed immutable visibility data pack;
- source-data receipts; and
- licensing and notice material.

Full spectral outputs remain research or validation artifacts. The runtime
table should carry only the response-integrated products required by the
admitted public model. The engine runtime receives an explicit caller-supplied
data-pack path and never downloads the pack.

### Native layer

Native work is deferred until after Python admission and benchmarking.
Candidate native responsibility is limited to:

- LUT lookup and interpolation;
- repeated visibility-margin evaluation; and
- root-bracket refinement.

Native code must not decide model defaults, event meanings, fallback policy,
failure reasons, or provenance.

## Phase Status

| Phase | Gate | Status | Completion receipt |
|---|---|---|---|
| 0 | Doctrine, source, licensing, and contract lock | Complete | Closure receipt below |
| 1 | Reproducible atmospheric reference laboratory | Complete | [Checkpoints 1-6](../../05_research/heliacal_visibility/PHYSICAL_HELIACAL_VISIBILITY_PHASE1_ALTITUDE_PRESSURE_INTERPOLATION_CHECKPOINT_2026-07-30.md), [radiance/response checkpoint](../../05_research/heliacal_visibility/PHYSICAL_HELIACAL_VISIBILITY_PHASE1_RADIANCE_RESPONSE_CHECKPOINT_2026-07-30.md), and [closure receipt](../../05_research/heliacal_visibility/PHYSICAL_HELIACAL_VISIBILITY_PHASE1_CLOSURE_2026-07-30.md) |
| 2 | Python spectral single-epoch truth | Complete | [Closure receipt](../../05_research/heliacal_visibility/PHYSICAL_HELIACAL_VISIBILITY_PHASE2_CLOSURE_2026-07-30.md) |
| 3 | Physical visibility-event solver | Complete | [Closure receipt](../../05_research/heliacal_visibility/PHYSICAL_HELIACAL_VISIBILITY_PHASE3_CLOSURE_2026-07-30.md) and [restart checkpoint](../../05_research/heliacal_visibility/PHYSICAL_HELIACAL_VISIBILITY_PHASE3_RESTART_CHECKPOINT_2026-07-30.md) |
| 4 | Moonlight, airglow, horizon, and local realism | In progress | [Directional-horizon checkpoint](../../05_research/heliacal_visibility/PHYSICAL_HELIACAL_VISIBILITY_PHASE4_DIRECTIONAL_HORIZON_CHECKPOINT_2026-07-31.md); [background-composition checkpoint](../../05_research/heliacal_visibility/PHYSICAL_HELIACAL_VISIBILITY_PHASE4_BACKGROUND_COMPOSITION_CHECKPOINT_2026-07-31.md); [observer-factor checkpoint](../../05_research/heliacal_visibility/PHYSICAL_HELIACAL_VISIBILITY_PHASE4_OBSERVER_FACTOR_CHECKPOINT_2026-07-31.md) |
| 5 | Public contract parity | Not started | Pending |
| 6 | Optional native strengthening | Not started | Pending benchmark decision |
| 7 | Validation, admission, release, and documentation | Not started | Pending |

## Phase 0 - Doctrine, Source, and Contract Lock

### Event doctrine

- [x] Inventory every public `HeliacalEventKind`.
- [x] Record whether each kind is geometrical, visibility based, or
  underdetermined in the current contract.
- [x] Define the observation interval for every admitted physical event kind.
- [x] Define which threshold crossing owns the reported event time.
- [x] Define first-qualifying-day and last-qualifying-day semantics.
- [x] Decide whether acronychal events enter the first physical admission or a
  later named admission.
- [x] Keep cosmic events geometrical unless a separately sourced doctrine
  explicitly changes them.
- [x] Define polar, circumpolar, no-rise, no-set, and no-crossing behavior.

### Supported physical domain

- [x] Freeze naked-eye, unresolved point-source scope.
- [x] Freeze the known-location directed-observation protocol.
- [x] Freeze admitted planet and fixed-star body sets.
- [x] Keep the Sun outside the point-source model.
- [x] Keep lunar crescent visibility on its lunar-specific policy.
- [x] Define clear-sky requirements.
- [x] Define solar-depression, target-altitude, wavelength, atmosphere, and
  observer-altitude validity domains.
- [x] Define the treatment of refraction at the observation-window boundary.
- [x] Define local-horizon semantics and interpolation.

### Input and fallback doctrine

- [x] Define measured directional background as the highest-priority input.
- [x] Define how measured SQM values are transformed and receipted.
- [x] Define named atmosphere profiles and every value they supply.
- [x] Define whether pressure may be derived from altitude and under which
  named atmosphere.
- [x] Define AOD550, Angstrom exponent, ozone, albedo, temperature, and
  humidity units and valid ranges.
- [x] Define the Bortle path as a coarse compatibility input.
- [x] Prohibit invisible substitution when a required physical input is
  unavailable.

### Source and licensing ledger

- [x] Record exact editions, versions, URLs or DOIs, access dates, and relevant
  sections for every admitted source.
- [x] Record libRadtran source archive checksum and the required build-receipt
  fields; the actual compiler and build configuration are Phase 1 evidence.
- [x] Record the project's artifact boundary for generated libRadtran outputs.
- [x] Review CIE dataset redistribution and attribution requirements.
- [x] Review Jones, ESO, and PALACE code/data terms before copying any data or
  coefficients.
- [x] Record all accepted licenses and notices in the source ledger and
  proposed form.

### Public contract sketch

- [x] Freeze the composite model identifier.
- [x] Decide whether the composite is a policy preset, a first-class model
  family, or both.
- [x] Sketch additive request fields.
- [x] Sketch typed assessment and event receipts.
- [x] Define stable `not_evaluable` reason identifiers.
- [x] Define how legacy responses omit physical-only fields.
- [x] Define the data-pack identity fields exposed to callers.

### Phase 0 exit gate

- [x] No event-kind semantic question remains implicit.
- [x] No formula depends on memory or an unidentified source.
- [x] Every candidate dataset has an explicit licensing disposition.
- [x] The supported domain and every closed exclusion are written down.
- [x] The proposed public changes are additive and compatibility reviewed.
- [x] A Phase 0 closure receipt is added to this document.

### Phase 0 Closure Receipt

Date:
2026-07-29

Commit:
Uncommitted working tree; no commit or push was requested for Phase 0.

Runtime:
Python 3.14.3 for documentation tooling only.

Implemented:
Source ledger, four-phase physical event doctrine, validity and input
boundaries, data-pack and licensing disposition, additive public-contract
sketch, stable typed failure reasons, and frozen composite model identity.

Explicitly unchanged:
Engine calculations, native code, packaged data, public Python exports,
facades, serializers, REST routes/models, OpenAPI, validation claims, existing
enum strings, existing defaults, and existing legacy output shapes.

Source/data identities:
Schironi 2024 DOI `10.1515/9783111314532-002`; Crumey 2014 DOI
`10.1093/mnras/stu992`; Tousey-Koomen 1953 DOI
`10.1364/JOSA.43.000177`; libRadtran 2.0.6 archive SHA-256
`64930cc40b6e4a37aa220520974d330fc1563796f466a649b2238131f2d69840`;
CIE photopic DOI `10.25039/CIE.DS.dktna2s3`, SHA-256
`ee5d5d17922ae645d4af52cacf6a50bdb9385749f9d2181ca312eb2b08febac2`;
CIE scotopic DOI `10.25039/CIE.DS.gr6w4b5g`, SHA-256
`6a75d3fdbcbf5e9e9a07478511933eefeda953f3e2cc14b74459e5a099ec3759`.

Tests:
`scripts/check_doc_consistency.py` passed; focused
`tests/unit/test_git_wiki_sync.py` passed (`1 passed`); the five changed
canonical/generated pages passed exact targeted synchronization; and
`git diff --check` passed.

Independent validation:
Primary-source and official-software/data cross-check only. No numerical model
has been admitted or validated by this documentation phase.

Known limitations at Phase 0 closure:
No generator environment, atmospheric table, Python physical model, event
solver, transport, native work, or released artifact existed at that gate.
The Phase 1 checkpoint below supersedes the generator portion of this
historical statement. The repository-wide wiki check still reports the
pre-existing
`API_REFERENCE.md` and `REST_API_REFERENCE.md` mirror drift; those unrelated
generated updates were kept outside this Phase 0 edit boundary.

Next authorized phase:
Phase 1, Reproducible Atmospheric Reference Laboratory.

## Phase 1 - Reproducible Atmospheric Reference Laboratory

### Generator environment

- [x] Pin libRadtran 2.0.6 by source checksum.
- [x] Record compiler, build flags, solver configuration, and source datasets.
- [x] Use fully spherical MYSTIC for low-Sun and near-horizon directional
  radiance reference cases.
- [x] Use fixed random seeds.
- [x] Run repeated convergence cases and record Monte Carlo uncertainty.
- [x] Keep the generator outside Moira's runtime dependency graph.

Checkpoint 1 established the candidate grid envelopes below but did not
freeze their final sparse nodes. The fixed-budget geometry smoke showed
reported relative uncertainty ranging from 0.44% to 67.54%, plus one
zero-contribution case with no estimable relative uncertainty. Therefore the
reference-grid boxes remain open until the adaptive design, deep-twilight
law, and solver-error budget are admitted. Checkpoint 2 below closes the
bounded elevated-site construction gate without freezing production grid
nodes. Checkpoint 3 source-traces the deterministic surface direct-beam law
and admits a 290-level refinement for controlled exponential-atmosphere
geometry only. Checkpoint 4 validates that refinement across all six AFGL
named atmospheres, binds the official external REPTRAN module, and admits
REPTRAN fine as the full-spectral research reference. Checkpoint 5
source-binds the environmental parameter roles, candidate nodes, reserved
holdouts, all eight named Shettle profiles, measured-pressure policy, and
delta-M-safe direct-extinction oracle. Checkpoint 6 admits the site-relative
observer-altitude and pressure-ratio interpolation law against 12,636
withheld spectral values across all six molecular profiles. The final
radiance/response checkpoint admits the 4-by-4-by-4 response grid, nine
untouched response holdouts, 57-node direct surface, binary32 storage,
per-cell uncertainty, and fail-closed deep-twilight law. The separately
validated `1.0.0` data pack closes Phase 1 with an explicit fixed-environment
baseline.

### Direct-transmission pilot

- [x] Freeze a separately identified direct-transmission solver.
- [x] Use double-precision DISORT with pseudo-spherical geometry.
- [x] Record the `edir/E0` horizontal-irradiance output law.
- [x] Remove the geometric projection explicitly with
  `sin(target_true_altitude)`.
- [x] Record both spectral transmission and extinction magnitude.
- [x] Verify a byte-identical deterministic repeat.
- [x] Source-trace the bottom-layer midpoint Chapman reconstruction used by
  the selected libRadtran surface direct output.
- [x] Quantify controlled near-horizon solver/output and
  layer-discretization error independently from 0.25-45 degrees.
- [x] Expand the smoke cases to the final admitted spectral reference design.
- [x] Validate the refined vertical grid and near-horizon error budget with
  the named atmosphere and full spectral design.
- [x] Separate physical aerosol direct extinction from delta-M
  phase-function bookkeeping while preserving total optical depth.

### Elevated-site construction

- [x] Bind the governing libRadtran altitude, interpolation, and spherical
  MYSTIC source semantics.
- [x] Reject `altitude` in Monte Carlo inputs and reject
  `mc_elevation_file` with spherical MYSTIC.
- [x] Generate source-derived atmospheres whose bottom level is the physical
  observing surface.
- [x] Preserve libRadtran's preinterpolation O4 semantics with a bound
  companion profile.
- [x] Compare the construction to the supported deterministic altitude oracle
  at 0, 500, 1,500, 3,000, and 5,000 m over three target altitudes and three
  wavelengths.
- [x] Verify byte-identical sea-level source/truncated and fixed-seed elevated
  MYSTIC controls.
- [x] Admit an explicit measured-pressure override only when both the
  500-1,100 hPa absolute bound and 0.85-1.08 named-profile pressure-ratio
  bound pass; the default remains profile-derived.

### Reference grid

- [x] Define the solar-zenith grid.
- [x] Define target elevation and relative solar-azimuth grids.
- [x] Validate the observer-altitude construction and named-profile pressure
  derivation over the five checkpoint nodes.
- [x] Define the pressure-ratio dimension and reserve its holdouts.
- [x] Freeze the production observer-altitude nodes and admit altitude and
  pressure-ratio interpolation.
- [x] Define AOD550 and Angstrom-exponent dimensions and reserve their
  holdouts.
- [x] Define ozone-column values and reserve their holdouts.
- [x] Define and source-bind the six named molecular atmosphere profiles.
- [x] Define and source-bind all eight named Shettle haze/season profiles.
- [x] Define gray Lambertian ground-albedo values and reserve their holdouts.
- [x] Define the build-time full-spectral reference grid and
  response-integrated product nodes.
- [x] Reserve independent altitude, pressure-ratio, AOD550, Angstrom, ozone,
  and albedo cases that are never used to tune interpolation.
- [x] Reserve independent solar, target, azimuth, and response-integrated
  off-grid cases that are never used to build or tune the runtime table.

### Runtime table

- [x] Determine whether a regular, adaptive, or sparse grid best controls table
  size without hiding interpolation behavior.
- [x] Compare float32, float64, and any quantized representation against the
  scientific error budget.
- [x] Record storage precision separately from source-solver uncertainty.
- [x] Use a standard-library-readable deterministic format.
- [x] Include format version, dimensions, units, bounds, interpolation method,
  and missing-value law in the manifest.
- [x] Include SHA-256 checksums for every packaged file.
- [x] Publish an independent validator that rejects a mismatched or unsupported
  manifest. Engine loading remains Phase 2.

### Data-pack implementation

- [x] Confirm the engine wheel contains no physical table or CIE dataset.
- [x] Build the separately versioned, checksummed visibility data pack defined
  by Phase 0.
- [x] Publish the standalone explicit caller-supplied-path validator and the
  versioned metadata compatibility contract. The engine loader and public
  request binding remain Phase 2 work.
- [x] Verify that missing data fails explicitly and never starts a download.
- [x] Verify base-engine dependency metadata remains unchanged unless a
  separately approved packaging decision says otherwise.

### Phase 1 exit gate

- [x] A clean documented environment reproduces the reference artifacts.
- [x] Generated root manifests and checksums are bound by source-controlled
  compact receipts.
- [x] Grid-node reproduction is bounded by storage precision.
- [x] Independent off-grid interpolation error is measured.
- [x] Solver uncertainty, interpolation error, and storage error are bounded
  separately and published as downstream error inputs.
- [x] Limiting-magnitude propagation is assigned to Phase 2 and event-time
  propagation to Phase 3; Phase 1 does not fabricate unavailable derivatives.
- [x] Runtime use requires neither libRadtran nor network access.
- [x] A Phase 1 closure receipt is added to this document.

### Phase 1 Checkpoint 1 Receipt

Date:
2026-07-29

Status:
In progress; not a closure or model-admission receipt.

Implemented:
Offline source-locked generator, complete artifact validator, deterministic
MYSTIC input rendering, fixed-seed convergence profile, six-case geometry
smoke profile, deterministic direct-transmission smoke profile, immutable
external receipts, compact source-owned checkpoint, and current-wheel
boundary audit.

Evidence:
[PHYSICAL_HELIACAL_VISIBILITY_PHASE1_CHECKPOINT_2026-07-29.md](../../05_research/heliacal_visibility/PHYSICAL_HELIACAL_VISIBILITY_PHASE1_CHECKPOINT_2026-07-29.md).
The exact convergence, geometry, and direct-transmission root-manifest
SHA-256 values are
`f5246c0b54b7f1e1cb126a275df5a6c425cf71759d7afcf704dff14d991c2487`,
`736cb97e0f5e4218bb386f0290454cc15140438126ca1ded70b3b54f49a9d10a`,
and
`5eaac5edd15081836ef1a57c62e360421a5bd73f71276095cb0cd6ea78b80aa1`.

Explicitly unchanged:
Engine calculations, public contracts, native code, facades, serializers,
REST/OpenAPI, installed dependencies, default policies, and release identity.

Open:
Elevated-site construction, full direct-transmission spectral design and
near-horizon error bound, adaptive sparse radiance design, spectral
production, untouched holdout execution, storage/interpolation selection,
error propagation, separate data-pack construction, and the Phase 1 exit
gate.

Next authorized work:
Continue Phase 1 only. Phase 2 remains inactive.

### Phase 1 Checkpoint 2 Receipt

Date:
2026-07-29

Status:
Elevated-site construction gate passed for named-profile-derived pressure;
Phase 1 remains in progress.

Implemented:
Separate immutable elevated-site specification, source-equivalent atmosphere
and O4 profile construction, 45 deterministic altitude-oracle comparisons,
seven spherical MYSTIC smoke/control cases, generation-identity-safe resume,
complete central-profile binding, independent validator, and compact
source-owned checkpoint.

Evidence:
[PHYSICAL_HELIACAL_VISIBILITY_PHASE1_ELEVATED_SITE_CHECKPOINT_2026-07-29.md](../../05_research/heliacal_visibility/PHYSICAL_HELIACAL_VISIBILITY_PHASE1_ELEVATED_SITE_CHECKPOINT_2026-07-29.md).
The root-manifest SHA-256 is
`823ac54a3a6a52a5ab709bffb80693ffc945f800c6957f9024053c52289557ff`.

Closed:
The source-justified nonzero-observer-altitude construction for the U.S.
Standard atmosphere at 0-5,000 m with profile-derived pressure. The initial
O4 noncommutativity discrepancy was repaired without relaxing a tolerance.

Explicitly unchanged:
Engine calculations, public contracts, native code, facades, serializers,
REST/OpenAPI, installed dependencies, default policies, release identity, and
checkpoint 1 identities.

Open:
Production altitude/pressure dimension policy, full direct-transmission
spectral design and near-horizon error bound, adaptive sparse radiance design,
deep-twilight law, spectral production, untouched holdout execution,
storage/interpolation selection, error propagation, separate data-pack
construction, and the Phase 1 exit gate.

Next authorized work:
Continue Phase 1 only. Phase 2 remains inactive.

### Phase 1 Checkpoint 3 Receipt

Date:
2026-07-29

Status:
Controlled direct-transmission geometry gate passed; Phase 1 remains in
progress.

Implemented:
Source-traced libRadtran surface direct-beam semantics, a separately versioned
pure-absorption exponential-atmosphere probe, independent midpoint-Chapman and
continuous spherical-path oracles, a 50-level source-grid control, a 290-level
refined candidate, 144 nonrepeat cases, one byte-identical repeat, complete
artifact binding, an independent validator, and a compact source-owned
checkpoint.

Evidence:
[PHYSICAL_HELIACAL_VISIBILITY_PHASE1_DIRECT_GEOMETRY_CHECKPOINT_2026-07-29.md](../../05_research/heliacal_visibility/PHYSICAL_HELIACAL_VISIBILITY_PHASE1_DIRECT_GEOMETRY_CHECKPOINT_2026-07-29.md).
The external root-manifest SHA-256 is
`b69b377bd465b4740ef0dacd802c03d9fb6ee9eaf809a41356d60126dd23cd92`.

Closed:
The deterministic surface direct-beam implementation trace, admitted-domain
solver-versus-reconstruction agreement, positive-altitude extraction check,
and controlled continuous-atmosphere error bound for the 290-level candidate.
Its maximum midpoint-Chapman versus continuous error is
`0.0003497406476989963`, below the frozen `0.001` relative tolerance. The
coarse source-grid control reaches `0.10138558685013145`.

Explicitly unchanged:
Engine calculations, public contracts, native code, facades, serializers,
REST/OpenAPI, installed dependencies, default policies, release identity,
and checkpoint 1 and 2 identities.

Open:
Named-atmosphere and full-spectral direct-transmission validation, production
altitude/pressure dimension policy, adaptive sparse radiance design,
deep-twilight law, spectral production, untouched holdout execution,
storage/interpolation selection, error propagation, separate data-pack
construction, and the Phase 1 exit gate.

Next authorized work:
Continue Phase 1 only. Phase 2 remains inactive.

### Phase 1 Checkpoint 4 Receipt

Date:
2026-07-30

Status:
Named-atmosphere full-spectral direct-transmission gate passed for the clear
molecular surface domain; Phase 1 remains in progress.

Implemented:
An official external REPTRAN-module receipt, a canonical 1,478-file merged
data-root receipt, all six AFGL atmosphere profiles, 290/579/1,157-level
vertical controls, a 380-780 nm spectrum at 0.05 nm output spacing, REPTRAN
medium/fine characterization, 50 resumable bulk runs, four governing DISORT
anchors, a fixed-input repeat, an independent cross-platform validator, and a
compact source-owned checkpoint.

Evidence:
[PHYSICAL_HELIACAL_VISIBILITY_PHASE1_NAMED_SPECTRAL_DIRECT_CHECKPOINT_2026-07-30.md](../../05_research/heliacal_visibility/PHYSICAL_HELIACAL_VISIBILITY_PHASE1_NAMED_SPECTRAL_DIRECT_CHECKPOINT_2026-07-30.md).
The external root-manifest SHA-256 is
`b2bac79b30a3458fe17f8446b3da40f61deba1d7320b679724ebd60a65a539e8`.

Closed:
The clear molecular named-atmosphere full-spectral reference gate. The
conservative combined 290-level candidate error is
`0.0027130750801615698`, `0.0019078467868691084`, and
`0.0013040152001478783` mag in 1, 5, and 20 nm bins. All four DISORT anchors
are byte-identical to their bulk direct-beam counterparts. REPTRAN fine is
admitted as the research reference; REPTRAN medium is not a full-spectral
truth substitute.

Explicitly unchanged:
Engine calculations, public contracts, native code, facades, serializers,
REST/OpenAPI, installed dependencies, default policies, release identity,
runtime tables, and checkpoint 1-3 identities. The REPTRAN archive is not
redistributed.

Open:
Production altitude/pressure policy, aerosol/AOD/Angstrom/ozone/albedo
dimensions, adaptive sparse radiance design, deep-twilight law, versioned CIE
and target-spectrum inputs, response-integrated spectral production, untouched
holdouts, storage/interpolation selection, error propagation, separate
data-pack construction, and the Phase 1 exit gate.

Next authorized work:
Continue Phase 1 only. Phase 2 remains inactive.

### Phase 1 Checkpoint 5 Receipt

Date:
2026-07-30

Status:
Environmental-parameter semantics gate passed; Phase 1 remains in progress.

Implemented:
A separately versioned 73-run environmental-contract probe, complete
source/tool/file receipt, all eight Shettle haze/season profiles, AOD550 and
Angstrom binding, ozone-column values, gray-albedo role, profile-relative
measured-pressure policy, temperature/humidity ownership, raw delta-M
diagnostics, a delta-M-safe direct-extinction oracle, exact repeat, independent
cross-platform validator, and compact source-owned checkpoint.

Evidence:
[PHYSICAL_HELIACAL_VISIBILITY_PHASE1_ENVIRONMENT_CONTRACT_CHECKPOINT_2026-07-30.md](../../05_research/heliacal_visibility/PHYSICAL_HELIACAL_VISIBILITY_PHASE1_ENVIRONMENT_CONTRACT_CHECKPOINT_2026-07-30.md).
The external root-manifest SHA-256 is
`e79a250b01f00783f272bae409fa323a94b5c7811375760bf536eaa7de6b0580`;
the generation fingerprint is
`882f23ac18053ca616b01f175c31cc26a4c68411021506d80d8d308659060cb4`.

Closed:
Environmental parameter roles, units, candidate nodes, reserved holdouts,
pressure ownership, the full named aerosol inventory, direct-versus-radiance
dimension ownership, and direct-beam delta-M contamination. The 73-case
artifact passed independent validation under WSL and Windows. Its
near-horizon AOD evidence rejects linear unit-AOD scaling across the full
admitted AOD range.

Explicitly unchanged:
Engine calculations, public contracts, native code, facades, serializers,
REST/OpenAPI, installed dependencies, default policies, release identity,
runtime tables, data-pack authorization, and checkpoint 1-4 identities.

Open:
Altitude and pressure-ratio holdout execution, environmental interpolation,
solar/target/azimuth adaptive radiance nodes, deep-twilight sampling and
convergence, versioned CIE and target-spectrum inputs, response-integrated
spectral products, storage/interpolation selection, error propagation,
separate data-pack construction, and the Phase 1 exit gate.

Next authorized work:
Continue Phase 1 with the altitude/pressure holdout study. Phase 2 remains
inactive.

### Phase 1 Checkpoint 6 Receipt

Date:
2026-07-30

Status:
Altitude/pressure interpolation gate passed; Phase 1 remains in progress.

Implemented:
A separately versioned 5,037-run artifact across all six named molecular
profiles; eight observer-altitude nodes from 0 through 5,000 m; five
profile-relative pressure nodes; 14 altitude and eight pressure holdouts;
site-relative 290-level atmospheres; bilinear interpolation in extinction
magnitude; a complete source/tool/file receipt; an independent
cross-platform validator; and four preserved failed-design receipts.

Evidence:
[PHYSICAL_HELIACAL_VISIBILITY_PHASE1_ALTITUDE_PRESSURE_INTERPOLATION_CHECKPOINT_2026-07-30.md](../../05_research/heliacal_visibility/PHYSICAL_HELIACAL_VISIBILITY_PHASE1_ALTITUDE_PRESSURE_INTERPOLATION_CHECKPOINT_2026-07-30.md).
The external root-manifest SHA-256 is
`2264727cf4d1a74bb747aa51cc44e4ba9e703e09c132ab57eb2c0afef863c727`;
the generation fingerprint is
`ef95bba5a00667ce3bd1d983f9b9de93b989bd315da0e702f3342153d07bf165`.

Closed:
Observer-altitude and pressure-ratio production nodes, site-relative
atmosphere construction, complete-cell and no-extrapolation laws, and the
withheld interpolation gate. Across 12,636 evaluated values, maximum
extinction error is `0.0124663582904496` mag, 95th-percentile error is
`0.00404537460338972` mag, and maximum relative transmission error is
`0.0114162743931566`. All fixed ceilings pass without relaxation.

Explicitly unchanged:
Engine calculations, public contracts, native code, facades, serializers,
REST/OpenAPI, installed dependencies, default policies, release identity,
runtime tables, data-pack authorization, and checkpoint 1-5 identities.

Open:
The adaptive solar/target/azimuth radiance grid, deep-twilight law, CIE
response integration, untouched directional holdouts, storage precision,
separate data-pack construction, and the Phase 1 exit gate.

Next authorized work:
Continue Phase 1 with adaptive radiance and response integration. Phase 2
remains inactive.

### Phase 1 Radiance/Response Checkpoint Receipt

Date:
2026-07-30

Status:
Adaptive radiance, response integration, direct interpolation, storage, and
deep-twilight gates passed.

Implemented:
A 662-run, 5,621-file v9 reference artifact; a 4-by-4-by-4
solar/target/azimuth grid; nine untouched response holdouts; source-locked CIE
photopic/scotopic integration; training-only selection of a balanced 531 nm
importance reference; 57 direct-extinction training nodes and 22,400
untouched holdout bins; per-cell solver uncertainty; binary32 storage; and
eight preserved rejected-design receipts.

Evidence:
[PHYSICAL_HELIACAL_VISIBILITY_PHASE1_RADIANCE_RESPONSE_CHECKPOINT_2026-07-30.md](../../05_research/heliacal_visibility/PHYSICAL_HELIACAL_VISIBILITY_PHASE1_RADIANCE_RESPONSE_CHECKPOINT_2026-07-30.md).
The external root-manifest SHA-256 is
`6bb91212d1d54762af8276ea066b4c6d5f4df837d84a46057f57b35924bae12f`;
the generation fingerprint is
`aef8bdc07948ff5367dba1834baea708dfea0bc0dffb6898899dabc6f231c8c0`.

Closed:
Photopic/scotopic response interpolation passes the unchanged maximum/p95
ceilings; direct interpolation passes `0.05`/`0.02`-mag ceilings; binary32
storage error is below `1e-5` mag; a Monte Carlo zero is not physical zero;
modeled twilight below -9 degrees is typed `not_evaluable`; and the
monochromatic reconstruction is explicitly diagnostic rather than a shipped
or gating surface.

Explicitly unchanged:
Engine calculations, public contracts, native code, facades, serializers,
REST/OpenAPI, installed dependencies, default policies, release identity, and
runtime loader state.

Next authorized work:
Compile and validate the separate data pack. Phase 2 remains inactive until
the Phase 1 exit gate passes.

### Phase 1 Closure Receipt

Date:
2026-07-30

Status:
Complete. Phase 2 is now the next authorized phase.

Implemented:
The separately licensed `moira-physical-heliacal-visibility` data pack
version `1.0.0`; an exact-inventory independent validator; a metadata-only
compatibility contract; pack notice, provenance, and checksums; dual-platform
validation; and a compact closure receipt binding every admitted Phase 1
checkpoint.

Evidence:
[PHYSICAL_HELIACAL_VISIBILITY_PHASE1_CLOSURE_2026-07-30.md](../../05_research/heliacal_visibility/PHYSICAL_HELIACAL_VISIBILITY_PHASE1_CLOSURE_2026-07-30.md).
The admitted pack root-manifest SHA-256 is
`49ac2b68ea105a8e055b27e8d4d70f6cbfe9533f971ef5e6000f0bdd95d6771b`;
the generation fingerprint is
`b0d09b91086c2b3064e6c56cfaeae97226e7a6b2779fd70c5b7807aeab748750`.
The source-controlled closure receipt SHA-256 is
`6daaa62566214747dd50bc449da577065a2484c707ec39b7c1d88dafb0778776`.

First-pack domain:
U.S. Standard, rural-summer, sea-level fixed baseline at 1013.25 hPa,
AOD550 0.1, Angstrom exponent 1.3, ozone 300 DU, and gray albedo 0.2.
Solar-center altitude is -9 through 0 degrees, target true altitude is 0.25
through 45 degrees, and relative solar azimuth is 0 through 180 degrees.
All other environments are typed outside this pack's domain; earlier
environmental evidence is not mistaken for absent pack axes.

Explicitly unchanged:
No engine or native code, public contract, API transport, installed
dependency, default, legacy output, tag, release, website, or deployment was
changed. No CIE table or libRadtran/REPTRAN source file entered the MIT wheel.
No engine loader exists yet.

Acceptance:
The immutable source artifact and final pack passed independent Linux and
Windows validation with matching identities. Focused Phase 1 unit tests,
Ruff, documentation consistency, wiki synchronization, and diff checks are
the closing repository gate for the scoped Phase 1 commit.

Next authorized work:
Phase 2, Python Spectral Single-Epoch Truth. It must validate an explicit
caller-supplied pack, enforce the exact manifest domain, preserve typed
failures, and leave event-time solving to Phase 3.

## Phase 2 - Python Spectral Single-Epoch Truth

### Policy and vessels

- [x] Add only additive, versioned policy values.
- [x] Preserve the meanings of all existing policy values.
- [x] Add a composite model receipt listing every resolved component.
- [x] Add atmosphere-input completeness truth.
- [x] Add table identity and checksum receipt.
- [x] Add explicit validity-domain receipt.
- [x] Add the fixed observer-protocol and adaptation-state receipts.
- [x] Keep evaluated-clear, not-applicable, missing-dependency, and
  out-of-domain states distinct.

### Physical calculation

- [x] Load and validate the declared runtime table.
- [x] Interpolate target transmission.
- [x] Interpolate directional twilight radiance.
- [x] Compose admitted background components without double counting measured
  background.
- [x] Apply the versioned CIE MES2 spectral-response component.
- [x] Apply the separately named
  `blackwell_crumey_full_range_point_source_v1` threshold.
- [x] Condition target magnitude through the admitted atmospheric path.
- [x] Return visibility margin and evaluated visible/not-visible truth.
- [x] Propagate the Phase 1 solver, maximum interpolation, and storage-error
  inputs into limiting-magnitude and visibility-margin bounds without
  presenting them as scientific confidence.
- [x] Return component receipts with units and provenance.

### Background precedence

- [x] Implement measured directional or spectral background first.
- [x] Implement measured SQM anchoring with disclosed transformation.
- [x] Implement named source-identified reference atmospheres.
- [x] Retain Bortle as a visibly coarse compatibility fallback.
- [x] Reject incompatible or double-counted background combinations.

### Verification

- [x] Add primary-source equation fixtures.
- [x] Add manifest and checksum failure tests.
- [x] Add grid-node and independent off-grid cases.
- [x] Add boundary and invalid-domain tests.
- [x] Add monotonicity tests only where the physical relationship is
  legitimately monotonic.
- [x] Add component-composition and no-double-counting tests.
- [x] Add JSON-safe serialization round trips without activating Phase 5
  facade or REST transport.
- [x] Prove all existing default assessments are unchanged.

### Phase 2 closure receipt - 2026-07-30

The engine now has a no-search/no-download loader for explicit local pack
versions 1.0 and 1.1, exact identity and checksum validation, bounded
interpolation, CIE MES2 adaptation, the Crumey full-range point-source
threshold, non-overlapping background composition, response-weighted target
extinction, typed single-epoch truth, a declared data-pack numerical-error
envelope, and additive owning-module vessels.

Pack version 1.1 adds pack-owned, source-locked physical spectral profiles for
Mercury, Venus, Mars, Jupiter, and Saturn. The public assessment no longer
accepts caller-supplied planetary response weights. Moira resolves apparent
V-band magnitude, phase angle, and Saturn ring geometry from one engine-owned
photometry context; source-domain violations return typed non-evaluable
results rather than extrapolation.

The admitted 1.1 root manifest SHA-256 is
`f594fd12058cc7f5c7bc9de7f2b06652bef3c0604ef7b0a05a069e54e4026c87`;
the target-profile payload SHA-256 is
`40f4362aca22e329ad25916efa8476fee7a86eb1a6b0dfc1cf1b6c88f64531a0`.
An independent read-only validator rederived the profiles from the locked
Payne, Mallama, CIE, and solar-spectrum sources without importing either the
builder or engine. A second immutable build reproduced all 13 files exactly.

The three stale legacy fixture boundaries were completed at their mocked
resource edges, including the Yallop event, fixed-star not-found, and KS1991
assessment cases. The full focused legacy selection now passes 496 tests with
one pre-existing empty optional enumeration skipped; no failure is deselected.
The focused Phase 2 selection passes all 88 tests. The combined gate collects
585 tests, passes 584, skips that same optional enumeration, and deselects
nothing.
JSON-safe and immutable pickle round trips pass without claiming Phase 5
facade, REST, or OpenAPI parity.

The Phase 2 error-budget receipt propagates plus or minus one
maximum-contributing per-cell solver relative standard error, maximum
background interpolation error, direct-extinction maximum
interpolation error, and binary32 storage error. It reports lower and upper
limiting-magnitude and visibility-margin envelope limits plus a
`visible`/`not_visible`/`indeterminate` classification limited to those pack
numerical terms. The solver term is not relabeled as a hard maximum. P95
interpolation values remain diagnostics rather than bounds. Measurement,
planetary-source/model, observer-population, and actual
atmospheric uncertainty are named separately and are not fabricated into an
aggregate confidence interval.

Detailed evidence is recorded in
[PHYSICAL_HELIACAL_VISIBILITY_PHASE2_CLOSURE_2026-07-30.md](../../05_research/heliacal_visibility/PHYSICAL_HELIACAL_VISIBILITY_PHASE2_CLOSURE_2026-07-30.md).
The earlier implementation state remains in
[PHYSICAL_HELIACAL_VISIBILITY_PHASE2_CHECKPOINT_2026-07-30.md](../../05_research/heliacal_visibility/PHYSICAL_HELIACAL_VISIBILITY_PHASE2_CHECKPOINT_2026-07-30.md).

### Phase 2 exit gate

- [x] Every result names its effective component models and data identity.
- [x] Every unsupported or incomplete case fails closed.
- [x] Independent reference cases pass the Phase 1 error budget, and its
  downstream numerical inputs are propagated through the single-epoch margin.
- [x] Existing Schaefer, Kasten-Young, Krisciunas-Schaefer, Crumey, Yallop,
  and legacy defaults retain their frozen behavior.
- [x] A Phase 2 closure receipt is added to this document.

## Phase 3 - Physical Visibility-Event Solver

The governing threshold is:

```text
visibility_margin(t)
    = limiting_magnitude(t) - conditioned_target_magnitude(t)
```

### Solver implementation

- [x] Construct the valid observation window from target-horizon and
  solar-geometry constraints.
- [x] Evaluate all required ephemeris and atmospheric state at each sample.
- [x] Adaptively sample the complete valid interval.
- [x] Detect all visibility-margin sign changes.
- [x] Refine each witnessed bracket with a deterministic root solver.
- [x] Detect tangencies or near-zero intervals that do not produce a simple
  sign change.
- [x] Select the crossing required by the Phase 0 event doctrine.
- [x] Classify each observing day.
- [x] Search for the first qualifying day for rising events.
- [x] Search for the last qualifying day for setting events.
- [x] Preserve an explicit no-event result.

### Event receipt

- [x] Return primary `jd_ut`.
- [x] Return typed event-time semantics.
- [x] Return observation-window start and end.
- [x] Return threshold-crossing direction.
- [x] Return the boundary source and an applicable-or-not-applicable final
  visibility-margin residual.
- [x] Return the derived arcus, defined from solar altitude at the threshold.
- [x] Return scan, bracket, and root tolerances.
- [x] Return atmosphere, table, observer, horizon, model, and ephemeris
  receipts.
- [x] Return an optional deterministic data-pack numerical sensitivity
  interval.
- [x] Do not label a sensitivity interval as probabilistic confidence.

### Body and dispatch behavior

- [x] Admit only the currently source-complete body/event combinations frozen
  in Phase 0.
- [x] Keep lunar crescent search on the lunar-specific model.
- [x] Ensure the new fixed-star path does not enter the legacy native arcus
  accelerator.
- [x] Preserve all legacy native dispatch behavior for legacy policies.

### Verification

- [x] Test multiple-crossing intervals.
- [x] Test tangency and near-threshold cases.
- [x] Test scan-step convergence.
- [x] Test root-residual compliance.
- [x] Test first-day and last-day ownership.
- [x] Test circumpolar, polar-day, polar-night, no-rise, and no-set cases.
- [x] Test deterministic repeated execution.
- [x] Test sensitivity to the admitted atmospheric dimensions.
- [x] Prove legacy event dates remain unchanged when the new policy is absent.

### Phase 3 closure receipt - 2026-07-30

The additive Python event solver is closed for Mars, Jupiter, Saturn, and
Sirius across all four physical phases. Mercury and Venus remain valid
Phase 2 single-epoch targets but fail closed for event search because
first/last guard days can leave their source-owned phase-angle domains.

Exact data-pack version 1.2 preserves every admitted version 1.1 payload byte
and adds the BSC5/CALSPEC/CIE Sirius profile. An independently implemented
validator rederived that profile from checksum-locked local sources, and a
second offline build reproduced all 14 files byte-for-byte.

Crossing completeness is governed by source-controlled certificate
`physical-heliacal-event-lipschitz-v1`. An independent validator recomputed
the runtime log-altitude direct-extinction derivative, all table-coordinate
slopes, astronomical coordinate bounds, and the 8,799.9842 magnitude/day
derived margin ceiling below the admitted 16,384 ceiling. Same-sign intervals
that cannot be excluded are recursively enclosed; an unwitnessed possible
zero returns `crossing_completeness_not_certified`.

Source-owned event goldens use JPL Horizons for Jupiter and the Sun, and
Hipparcos plus the offline Astropy/ERFA/IERS transform for Sirius. The current
engine event differs from those independent one-minute-grid interpolants by
1.21 seconds for Jupiter and 2.56 seconds for Sirius, within the declared
60-second oracle tolerance. Both independent guard-day evaluations remain
non-qualifying.

The detailed scope, receipts, commands, limitations, and next boundary are in
[PHYSICAL_HELIACAL_VISIBILITY_PHASE3_CLOSURE_2026-07-30.md](../../05_research/heliacal_visibility/PHYSICAL_HELIACAL_VISIBILITY_PHASE3_CLOSURE_2026-07-30.md).

### Phase 3 exit gate

- [x] No valid interval crossing can be skipped by the admitted search
  strategy; possible-zero intervals that cannot be proved or witnessed fail
  closed.
- [x] Event-time semantics are inspectable from the result.
- [x] Solver precision and atmospheric sensitivity are reported separately.
- [x] Planetary and stellar physical events pass independent validation.
- [x] A Phase 3 closure receipt is added to this document.

## Phase 4 - Moonlight, Airglow, Horizon, and Local Realism

### Moonlight

- [x] Preserve Krisciunas-Schaefer under its existing identifier.
- [x] Freeze the Jones paper, official ESO source-package receipts, first
  candidate domain, operational comparator, and independent artifact contract.
- [x] Classify and checksum-lock the solar, ROLO, and aerosol inputs; preserve
  the aerosol table as source-owned without claiming an unavailable public
  reconstruction recipe.
- [ ] Implement Jones 2013 only under a new versioned identifier.
- [ ] Expose lunar phase, separation, lunar altitude, atmospheric, and
  scattering inputs in the component receipt.
- [ ] Validate the implementation against source-owned examples and
  independent conditions.
- [ ] Reject unsupported lunar geometry instead of extrapolating silently.

### Airglow and natural background

- [x] Preserve measured local background as the preferred authority.
- [ ] Use ESO and PALACE results as site-bound comparison/reference material.
- [x] Do not make a Paranal profile a global default.
- [x] Separate airglow, zodiacal light, integrated starlight, and artificial
  light whenever modeled components are supplied.
- [x] Prevent double counting when a measured background already contains
  those components.

### Horizon and observer

- [x] Add a caller-supplied azimuth/elevation horizon profile.
- [x] Define profile interpolation, wraparound, resolution, and validation.
- [x] Preserve the scalar horizon input as a compatibility path.
- [x] Resolve the observer-factor contract: keep the physical protocol at the
  source-receipted singleton `F = 2`, with no generic skill/probability input.
- [x] Prove that the current fixed-environment pack cannot truthfully supply
  atmospheric sensitivity and freeze the separate-scenario-pack architecture.
- [ ] Generate and admit immutable atmospheric scenario packs, rerun the full
  event search per pack, and form an interval only for comparable owned events.

### Phase 4 Jones source-audit checkpoint - 2026-07-31

The bounded source audit is complete. It checksum-locks the 431,651,392-byte
official ESO SM-01 release and all 18 required source, data, parameter, and
regression members, including the default aerosol phase function selected by
the package dependency map, without copying external GPL bytes into the
repository.
The official package fixture derives to a 102.1-degree lunar phase angle, so it
is outside the first candidate's 1.55–97-degree empirical ROLO domain and is
classified as official-lineage evidence rather than an admission golden.

An isolated SkyCalc 2.0.9 `flux_sml` capture at 50 degrees is locked as an
in-domain operational comparison. It is source-owned evidence, not an
independent oracle. The candidate remains `not_admitted`; no runtime, public
API, data-pack, dependency, network, download, or legacy behavior changed.

The source audit exposed a required input-authority gate before pilot
generation. That gate is now closed by the checkpoint below. See
[PHYSICAL_HELIACAL_VISIBILITY_PHASE4_JONES_SOURCE_AUDIT_CHECKPOINT_2026-07-31.md](../../05_research/heliacal_visibility/PHYSICAL_HELIACAL_VISIBILITY_PHASE4_JONES_SOURCE_AUDIT_CHECKPOINT_2026-07-31.md).

### Phase 4 Jones input-authority checkpoint - 2026-07-31

The solar and lunar inputs are now independently bound in the candidate
domain. The audit compares 1,467 ESO solar rows to the STIS reference and
locks the 32 published ROLO wavelength rows plus the 1.55-97 degree empirical
phase boundary.

The published Jones particle parameters and identified Oxford EODG Mie
routine do not reproduce ESO's selected `mie_m15s1.dat` table. The table is
therefore classified as an exact source-owned external input whose public
reconstruction recipe is unavailable. It may be used by the independent
radiative-transfer pilot with that limitation visible; it may not support an
independent aerosol-microphysics claim, and its bytes may not enter the
repository.

The next moonlight gate is to freeze and generate the libRadtran 2.0.6 MYSTIC
pilot matrix over all six candidate axes. Pilot results must establish
numerical and interpolation thresholds before a production artifact, engine
implementation, or public surface can be admitted. Any derived artifact also
requires a separate release/distribution disposition. See
[PHYSICAL_HELIACAL_VISIBILITY_PHASE4_JONES_INPUT_AUTHORITY_CHECKPOINT_2026-07-31.md](../../05_research/heliacal_visibility/PHYSICAL_HELIACAL_VISIBILITY_PHASE4_JONES_INPUT_AUTHORITY_CHECKPOINT_2026-07-31.md).

### Phase 4 exit gate

- [ ] Every environmental component has a named source and validity domain.
- [ ] Site-bound sources remain visibly site bound.
- [x] Measured and modeled backgrounds cannot be accidentally combined twice.
- [x] Horizon and observer assumptions survive into the event receipt.
- [ ] A Phase 4 closure receipt is added to this document.

## Phase 5 - Public Contract Parity

### Python surfaces

- [ ] Export all admitted public types from their owning module.
- [ ] Preserve curated root exports in `moira`.
- [ ] Preserve `moira.sky` visibility re-exports.
- [ ] Add `physical_visibility_assessment()` and
  `physical_visibility_event()` without changing legacy functions.
- [ ] Add matching `Moira` methods for the two new physical surfaces.
- [ ] Ensure facade functions forward the complete policy without narrowing it.
- [ ] Add identity-preserving public-surface tests.

### REST surfaces

- [ ] Add dedicated `/v1/visibility/physical-assessment` and
  `/v1/visibility/physical-event` routes.
- [ ] Forward the full physical policy unchanged through router, service, and
  engine.
- [ ] Add typed physical assessment and event request/response models.
- [ ] Bind the data-pack path through server configuration; never accept an
  arbitrary client filesystem path.
- [ ] Keep `/v1/visibility/assessment` and
  `/v1/heliacal/visibility-event` exact.
- [ ] Do not add physical-only fields to legacy responses.
- [ ] Keep strict response models and validation envelopes.
- [ ] Regenerate and verify OpenAPI.

### Affected transport files

- `moira_server/models/visibility.py`
- `moira_server/models/phenomena.py`
- `moira_server/services/visibility.py`
- `moira_server/services/phenomena.py`
- `moira_server/serializers/visibility.py`
- `moira_server/serializers/phenomena.py`
- `moira_server/routers/visibility.py`
- `moira_server/routers/phenomena.py`

The exact edit set must be re-established from the checkout at Phase 5 start.
This list is an inventory, not permission to modify every file.

### Phase 5 exit gate

- [ ] Root, sky, facade, `Moira`, serializer, REST, and OpenAPI surfaces expose
  the same effective models.
- [ ] Every transport preserves table, model, validity, dependency, and solver
  receipts.
- [ ] Legacy request and response fixtures remain unchanged.
- [ ] New request and response fixtures are fully typed.
- [ ] A Phase 5 closure receipt is added to this document.

## Phase 6 - Optional Native Strengthening

### Admission decision

- [ ] Benchmark the admitted Python implementation with representative
  single-epoch and event workloads.
- [ ] Record the performance budget and benchmark environment.
- [ ] Decide whether native work is justified.
- [ ] If native work is not justified, record that decision and close this
  phase without a port.

### Candidate native work

- [ ] Port only proven hot numerical kernels.
- [ ] Keep manifest, policy, domain, and provenance decisions in Python.
- [ ] Preserve the Python implementation as the differential reference.
- [ ] Validate the full environmental grid.
- [ ] Validate event results and invalid-domain behavior.
- [ ] Validate thread safety and deterministic concurrency.
- [ ] Record numerical tolerances and performance evidence separately.

### Phase 6 exit gate

- [ ] The benchmark decision is recorded.
- [ ] If native code is admitted, Python/native differential tests pass across
  the complete admitted domain.
- [ ] No public semantics moved into C++.
- [ ] A Phase 6 closure or no-port receipt is added to this document.

## Phase 7 - Validation, Admission, Release, and Documentation

### Evidence classes

- [ ] Primary-source equation validation.
- [ ] Independent libRadtran holdouts not used to build the LUT.
- [ ] Modern observational comparison cases.
- [ ] Historical event cases used only within their defensible uncertainty.
- [ ] Property and invariant testing.
- [ ] Legacy regression fixtures.
- [ ] Public-contract and OpenAPI parity tests.
- [ ] Wheel, sdist, manifest, and clean-install tests.
- [ ] Native differential evidence if Phase 6 admits a port.

Agreement with another engine is corroboration, not primary authority.
Snapshots are regression evidence, not scientific truth.

### Tolerance law

- [ ] Derive interpolation tolerances from independent reference runs.
- [ ] Record source-solver or Monte Carlo uncertainty.
- [ ] Record storage and interpolation error.
- [ ] Record root-solver residual and time tolerance.
- [ ] Quantify how component error affects limiting magnitude and event time.
- [ ] Do not invent one aggregate tolerance that hides these different errors.

### Documentation and release

- [ ] Generate a current capability matrix.
- [ ] Generate or update the public API inventory.
- [ ] Regenerate REST reference material.
- [ ] Replace or archive stale heliacal closure claims.
- [ ] Update the heliacal validation matrix.
- [ ] Update package provenance and notices.
- [ ] Document the new policy as opt-in.
- [ ] Document its validity domain and typed unsupported cases.
- [ ] Document runtime data-pack requirements, if any.
- [ ] Verify normal execution remains offline.
- [ ] Prepare compatibility and release notes.
- [ ] Update website documentation only after the engine release gate passes.

### Phase 7 exit gate

- [ ] Every admitted claim has a named evidence class.
- [ ] The packaged artifact contains or resolves the exact admitted data
  identity.
- [ ] Clean-wheel and clean-sdist tests pass.
- [ ] Strict known-issues validation passes.
- [ ] Documentation describes current executable behavior without stale
  completion claims.
- [ ] A final completion receipt is added to this document.

## Cross-Phase Validation Inventory

The working validation surface includes:

- `tests/unit/test_visibility_physics.py`;
- `tests/unit/test_heliacal_visibility_policy.py`;
- `tests/unit/test_planet_heliacal.py`;
- `tests/unit/test_stars_heliacal.py`;
- `tests/integration/test_visibility_validation.py`;
- `tests/server/test_server_visibility_routes.py`;
- `tests/server/test_server_phenomena_routes.py`; and
- native visibility/parity tests if Phase 6 proceeds.

Each phase must re-inventory the current test tree before changing it. New
tests should be placed beside the owning layer instead of accumulating in one
unscoped integration file.

## Quarantined Scope

The following are closed exclusions from this roadmap:

- cloudy-sky radiative transfer;
- live weather or forecast integration;
- telescopic visibility;
- extended-object visibility;
- solar visibility through the point-source model;
- lunar-crescent visibility through the point-source model;
- globally authoritative airglow inferred from one observatory;
- global satellite-derived artificial-light prediction;
- runtime libRadtran execution;
- automatic data downloads;
- mesopic astronomical-detection claims without direct validation;
- observer-population probability or confidence claims;
- interpretive or astrological meaning derived from visibility; and
- changing the default visibility model during the current major version.

Reopening one of these requires:

1. an identified source and validity domain;
2. a separate policy and contract proposal;
3. explicit authorization;
4. independent validation evidence; and
5. a new admission receipt.

It must not be added to a later phase as if it were forgotten work.

## Work Protocol

At the beginning of each phase:

- [ ] Re-read repository instructions and protected-zone rules.
- [ ] Confirm the checkout and branch.
- [ ] Confirm `git status` and protect unrelated work.
- [ ] Re-audit the named implementation surface.
- [ ] State the minimum proposed edit set.
- [ ] Record unresolved doctrine or source questions before coding.

At the end of each phase:

- [ ] Run focused tests for the owning layer.
- [ ] Run affected integration and public-contract tests.
- [ ] Run strict known-issues validation appropriate to the change.
- [ ] Run documentation consistency checks when documentation changes.
- [ ] Run `git diff --check`.
- [ ] Review the final diff for accidental policy or API changes.
- [ ] Update the phase status and receipt in this document.
- [ ] Commit the implementation and its receipt together when a commit is
  requested.

## Completion Receipt Template

Append one receipt for every closed phase:

```text
### Phase N Closure Receipt

Date:
Commit:
Runtime:
Implemented:
Explicitly unchanged:
Source/data identities:
Tests:
Independent validation:
Known limitations:
Next authorized phase:
```

The project is complete only when all required phases carry closure receipts,
all required checkboxes are satisfied, and the released artifact preserves the
exact admitted engine, data, transport, and documentation identity.
