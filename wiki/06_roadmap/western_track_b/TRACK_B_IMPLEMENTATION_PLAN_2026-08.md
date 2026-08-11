# Track B Western Horary and Mundane Implementation Plan

Status: **complete at the Track B admission checkpoint; not released or deployed**
Date: 2026-08-11
Baseline: `24e90f9fa4cdbe9692d6f70469df7863f4b15d36`

This plan implements Track B from
`wiki/07_audit/ASTROLOGY_COVERAGE_FRONTIER_AUDIT_2026-08.md`. Horary and Mundane
remain separate domains and never share a generic judgement layer.

## B0. Source and ambiguity gates

- [x] Identify Lilly 1647 edition and scan authority.
- [x] Define the narrowed finite Horary question/significator/perfection boundary.
- [x] Record Horary conflicts and explicit deferrals.
- [x] Select source-owned Horary fixtures.
- [x] Identify Ptolemy/Ramesey Mundane selection authorities.
- [x] Define finite ingress/syzygy/eclipse/great-conjunction event taxonomy.
- [x] Record location and chart-selection ambiguity policy.
- [x] Select independent modern astronomical fixtures.
- [x] Source-lock Lilly's triplicity/nature hour-agreement tables and semantics
  to CA 1647 pp.57-81 and 121-122; the worked examples control the lookup.
- [x] Source-lock Regiomontanus construction to CA 1647 pp.491 and 519-523 as an
  optional deterministic Lilly-compatible policy, not mandatory ordinary-Horary
  doctrine.
- [x] Harden neutral ingress, eclipse-epoch, and Jupiter-Saturn conjunction truth
  receipts before profile composition.
- [x] Source-lock the neutral Ptolemy quarterly/weather selector to Robbins 1940,
  *Tetrabiblos* II.10 and II.12, printed pp.199-209, with explicit target location.
- [x] Source-lock Ramesey's Aries-ingress cadence to the original 1653 edition,
  Book IV, section I, chapter I, printed pp.214-215, with explicit target location.

B0 source admission did not itself imply implementation, fixture, validation,
export, serializer, REST, OpenAPI, or public API completion. Those executable
admission gates are now closed separately in B1-B4 below.

Canonical dossiers:

- `wiki/05_research/horary/TRACK_B_HORARY_SOURCE_AND_AMBIGUITY_DOSSIER_2026-08.md`
- `wiki/05_research/mundane/TRACK_B_MUNDANE_SOURCE_AND_CHART_SELECTION_DOSSIER_2026-08.md`

## B1. Horary atomic evidence

- [x] Add `moira.horary` with immutable, typed question, turned-house,
  significator, radicality, consideration, and provenance vessels.
- [x] Require explicit topic house and question-time basis.
- [x] Consume provenance-bearing precomputed `HouseCusps` plus an exact
  caller-selected house-system and strict no-fallback policy receipt.
- [x] Resolve only classical domicile rulers and preserve Moon separately.
- [x] Implement all three source-locked Lilly hour-agreement paths: same planet;
  hour lord governing the rising sign's day/night triplicity; and same primary
  hot/cold plus moist/dry nature under Lilly's tables.
- [x] Represent same-body collisions as typed not-evaluable perfection.
- [x] Compose `ClassicalPerfectionAnalysis`; do not duplicate its six mechanisms.
- [x] Preserve only reception evidence already owned by the supplied
  `ClassicalPerfectionAnalysis`; do not invoke an unnamed dignity default.
- [x] Add source-owned and adversarial unit fixtures.
- [x] Prove no NumPy/SciPy/jplephem/Swiss import or runtime dependency.

Atomic admission gate:

```powershell
.\.venv\Scripts\python.exe -m pytest `
  tests\unit\test_horary.py `
  tests\unit\test_classical_perfection.py `
  tests\unit\test_derived_houses.py -q
```

## B2. Horary contract parity

- [x] Add curated root exports only after B1 is green.
- [x] Add `Moira` reader-bound convenience methods without ownership changes.
- [x] Add strict REST models, service, serializer, and router.
- [x] Preserve engine enums and typed states through JSON/OpenAPI.
- [x] Add public API, star-import, facade, route-discovery, and OpenAPI tests.
- [x] Regenerate canonical REST/API inventories only after behavior is stable.

No Horary website or Workspace work is authorized by this plan.

## B3. Mundane atomic evidence and substrate hardening

- [x] Add/harden neutral event receipts with frame, correction, timescale,
  content-derived reader identity, residual, and motion truth before composition.
- [x] Make Moira's IAU 2006 P03 / IAU 2000A apparent true-of-date product the
  engine authority; retain Horizons IAU76/80 and USNO as labeled independent
  comparators rather than relabeling either frame.
- [x] Bind every Moira event to content-derived active-reader identity; keep any
  artifact digest explicitly caller/release-receipt owned and never hash DE441
  per event.
- [x] Preserve an engine-owned event clock receipt with UT1, TT, Delta-T source,
  retargeting, and typed UTC realization status.
- [x] Use a tagged event-receipt union; no optional-field event bag.
- [x] Add `moira.mundane` with immutable global-event, location-selection, local
  projection, and profile vessels.
- [x] Compose existing ingress, prenatal syzygy, eclipse, great-conjunction,
  chart, and house primitives without forking their solvers.
- [x] Admit four-cardinal-ingress enumeration and the separately named,
  source-locked Ramesey cadence policy without introducing interpretation or
  automatic capital selection.
- [x] Compute the Ramesey Aries-ingress Ascendant independently of house-system
  selection so a strict polar house failure cannot erase valid angle truth.
- [x] Implement strictly-preceding syzygy semantics.
- [x] Keep eclipse epoch meanings separate.
- [x] Preserve every Jupiter-Saturn root; do not invent cluster identity.
- [x] Require an explicit eclipse `chart_epoch_kind` for local projection.
- [x] Require explicit location role/source/validity and house system.
- [x] Keep global event evaluated when local projection is not evaluable.
- [x] Add USNO/NASA/IMCCE-backed fixtures and adversarial unit tests.

Atomic admission gate:

```powershell
.\.venv\Scripts\python.exe -m pytest `
  tests\unit\test_mundane.py `
  tests\unit\test_transits.py `
  tests\unit\test_cycles.py `
  tests\unit\test_eclipse_clock_boundaries.py `
  tests\unit\test_eclipse_contact_solver.py -q
```

The exact regression nodes may be narrowed after mapping current filenames; a
missing broad file is not a reason to run the full repository suite first.

## B4. Mundane contract parity

- [x] Add curated root/facade exports only after B3 is green.
- [x] Add strict REST models, service, serializer, and router.
- [x] Add route/OpenAPI/public-contract tests.
- [x] Regenerate API inventories and canonical Wiki mirrors.
- [x] Amend the frontier audit with exact admitted and deferred scope.
- [x] Run scoped Ruff F401 and document consistency gates.

No Mundane interpretation, website, Workspace, release, tag, or deployment is
authorized by this plan.

## B5. Completion gate

Track B is complete only when:

- [x] both atomic profiles preserve source and computation receipts;
- [x] every missing dependency has a typed state;
- [x] source-owned and independent fixtures pass;
- [x] public Python and REST contracts are parity-checked;
- [x] generated documentation checks are clean;
- [x] the frontier audit records admitted and remaining gaps; and
- [x] the active external testing-environment checkout remains untouched.

Commit, push, version bump, release, and deployment remain separately authorized
actions.

## Checkpoint receipt

The bounded admission checkpoint closes Track B without creating a shared judgement
layer:

- Horary atomic/classical/derived-house/public Python gate: 160 passed.
- Mundane atomic gate: 63 passed, with 13 DE441 resource receipts and no skips
  or failures.
- Adjacent cycles/eclipse regression gate: 121 passed, with 15 DE441 resource
  receipts and no skips or failures.
- Combined Horary/Mundane/public export drift gate: 52 passed.
- Dedicated Horary REST/OpenAPI gate: 19 passed.
- Dedicated Mundane REST/OpenAPI gate: 20 passed.
- Combined Track B route/OpenAPI/discovery/startup gate: 50 passed.
- Scoped changed-source Ruff F401 gate: clean.
- Generated REST, Hellenistic global-count, website publication, Git Wiki, and
  document-consistency checks: clean.
- Registered OpenAPI truth: 447 paths/operations, comprising 35 GET, 412 POST,
  four operational/meta paths, and 443 `/v1` paths.

The Hellenistic inventory remains a 49-operation Hellenistic/supporting subset;
only its whole-application operation count changed from 445 to 447. The
generator now forces the repository that owns the script ahead of any stale
editable-install checkout, preventing a multi-worktree false green.

The active validation-assurance checkout remains separate and untouched. The
known pre-existing duplicate `SolarConditionTruthResponse` import in
`moira_server/models/__init__.py` remains outside this scope. No full repository
suite, version bump, commit, push, tag, release, website application change,
Workspace adoption, or deployment is claimed by this checkpoint.
