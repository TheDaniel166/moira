# Orbital Core Stage 3 Implementation Plan

> **Execution boundary:** Implement and validate Stage 3 on top of the
> uncommitted Stage 1/2 worktree. This plan does not authorize a commit,
> version change, tag, package publication, push, server pin, or deployment.

**Date:** 2026-09-16

**Status:** Implementation complete and review-ready; release remains blocked

**Baseline:** `orbital-core-stage1` at committed base
`dfad306f47901596e9edc254116ac3c6d47a3764`, plus the preserved uncommitted
Stage 1 and Stage 2 implementation.

**Governing spec:**
`docs/superpowers/specs/2026-09-15-orbital-core-design.md`, SHA-256
`fba918c2755181f5d467ed957891278fb249bfde19931ecd310baf6019329a38`.

**Goal:** Move `planetary_nodes.geometric_node` onto the strict orbital core,
preserve the public signature and `OrbitalNode` vessel, expose truthful
Stage 1 source/time/frame/gravity receipts through `/v1/nodes/geometric`, and
admit every resolvable asteroid or comet whose loaded kernel covers the
requested epoch.

## 1. Governing object and policy

The governing object is the instantaneous osculating orbital plane of a body
about the Sun, expressed in Moira's `TRUE_ECLIPTIC_OF_DATE` frame. The
ascending node is the positive crossing of that frame's ecliptic plane. The
perihelion longitude carried by `OrbitalNode` is the projected direction of
the eccentricity vector in that same ecliptic frame. It is not the inclined
orbit's dogleg angle `Omega + omega`.

The computation is exactly:

```text
osculating_elements(
    body,
    jd_ut,
    center=OrbitalCenter.SUN,
    frame=OrbitalFrame.TRUE_ECLIPTIC_OF_DATE,
    reader=reader,
)
```

The core owns body resolution, UT1 -> TT -> TDB conversion, immutable source
routing, Horizons-derived gravity rules, SOFA-derived frame routing,
singularity policy, and typed errors. `planetary_nodes` owns only the legacy
`OrbitalNode` adaptation.

### Mapping into the unchanged vessel

| `OrbitalNode` field | Strict core field |
|---|---|
| `planet` | `elements.body.name` |
| `ascending_node` | `elements.lon_ascending_node_deg` |
| `perihelion` | `elements.pericenter_ecliptic_lon_deg` |
| `aphelion` | `(perihelion + 180) % 360` |
| `inclination` | `elements.inclination_deg` |
| `eccentricity` | `elements.eccentricity` |
| `semi_major_axis` | `elements.semi_major_axis_au` |

If the unchanged vessel requires an element that the strict core correctly
marks undefined, the adapter raises the existing typed
`OrbitalStateDegenerateError`; it never emits a fabricated zero or a direction
from floating-point noise.

## 2. Authority and evidence

- Runtime state: JPL DE441 and receipted small-body SPK releases.
- Gravity: the pinned official JPL Horizons GM snapshot already admitted by
  Stage 1.
- Time: the source-owned Delta-T policy plus pinned NAIF LSK TT/TDB model
  already admitted by Stage 1.
- Frame: the Stage 1 IAU SOFA-derived true-ecliptic-of-date construction,
  admitted only for JD(TT) 2415020.0 through 2488070.0.
- Small-body numeric holdout: the frozen official NASA/JPL Horizons
  `horizons_orbital_elements_catalog_holdout.json` vectors/elements, combined
  with the already verified Stage 1 frame router.

The legacy `geometric_node` implementation is a regression witness only. Its
DE405-era Sun GM, planet-only route table, and hand-built frame path are not an
authority.

## 3. Protected-zone declaration and minimum files

Protected files required by the requested change:

- `moira/planetary_nodes.py`: replace duplicate state/frame/conic math with a
  strict-core adapter; keep mean-node code and `OrbitalNode` unchanged.
- `moira_server/models/nodes.py`, `services/nodes.py`, and `routers/nodes.py`:
  preserve existing routes while adding allowlisted geometric-node time,
  gravity, frame, and state-source receipts.
- `tests/`: new node-core unit/integration/full-catalog checks and updated
  server contract tests.
- `wiki/02_standards/PLANETARY_NODES_BACKEND_STANDARD.md`, the minimum REST,
  API, validation and changelog sections, followed by generated documentation
  synchronization.

Unrelated Stage 1/2 files and the untracked aspect-pattern draft remain
untouched except where documentation generation owns a derived copy.

## 4. Implementation sequence

1. Add one private computation vessel in `planetary_nodes` that carries both
   the unchanged public `OrbitalNode` and its strict `OsculatingElements`
   receipt. Keep `geometric_node` as the public result-only wrapper.
2. Remove the duplicate GM, barycentric lookup, precession/nutation and conic
   extraction path from `planetary_nodes.geometric_node`.
3. Update the geometric REST route to consume the private computation once,
   avoiding a second state evaluation, and serialize only allowlisted logical
   identities/hashes—never local paths.
4. Keep mean-node endpoints and the four-route family unchanged.
5. Add tests for exact core policy forwarding, field mapping, canonical
   identity, undefined-element failure, true-frame interval errors, planetary
   kernels, representative asteroid/comet kernels, REST provenance, and every
   installed full-catalog body with modern-frame coverage.
6. Record unavailable full-catalog prerequisites rather than substituting the
   25-body wheel for the required full asteroid release.
7. Update documentation and write a machine-checked Stage 3 validation receipt.

## 5. Verification order

All commands use `.venv`, `MOIRA_TEST_MODE=1`,
`MOIRA_STRICT_KNOWN_ISSUES=1`, and `MOIRA_NO_DOWNLOAD=1` unless an isolated
test explicitly authorizes external network access.

1. New kernel-free adapter and error tests.
2. Existing and updated node REST tests.
3. DE441 planet and representative loaded asteroid/comet tests.
4. Installed catalog inventory test; record missing releases explicitly.
5. Stage 1/2 orbital regression slices.
6. A separately isolated official Horizons live slice if its exact
   prerequisites are available; otherwise record it as not run.
7. `pytest -m "not external_network"` until either green or a baseline failure
   is reproduced and identified.
8. Scoped Ruff, documentation consistency, generated wiki/bundle checks, and
   `git diff --check`.

Completion reports exact counts, bodies, epochs, centers, frames, time scales,
catalog identities, skips, inherited blockers, and the absence of release
actions. Passing Stage 3 is an implementation checkpoint, not a release.

## 6. Completion checkpoint

Stage 3 is implemented in the uncommitted Stage 1/2 worktree and is bound to
`tests/artifacts/release/orbital_core_stage3_validation_2026-09-16.json`.
`geometric_node` now contains only strict-core policy selection and adaptation;
the duplicate state, GM, frame, and conic pipeline is gone. The unchanged
`OrbitalNode` maps the projected pericenter-vector longitude rather than
`Omega + omega`, and the REST route serializes the same core computation's
allowlisted time, gravity, frame, state-source, and singularity receipts.

The Stage 3 focused gate collects 42 cases: 36 pass and six are explicit
catalog-admission skips. All nine planet targets pass exact true-date core
mapping, both frame-boundary failures retain their typed identity, and Ceres,
Hektor, Atira, Apophis, 1P/Halley, and 2P/Encke pass loaded-catalog mapping. All
six frozen catalog authority comparisons remain `NOT RUN` because the installed
manifests carry no reviewed Stage 3 admission bound to the exact fixture hash
and gates.

The full `moira-asteroids@2026.08.12.1` and
`moira-comets@2026.07.28.1` inventories pass for all 10,522 sovereign bodies;
the 25-body wheel is not substituted for either full release. The combined
orbital regression gate passes
440 of 452 collected cases with 12 explicit catalog-admission skips. The
Stage 3 receipt governance adds three passing checks. Scoped Ruff and all
documentation generation/consistency gates pass.

The repository-wide non-network gate still stops at the pre-existing nested
pytest-project import defect for `support.small_body_resource_policy`. The
broad 66-file changed-tree Ruff audit reports 99 inherited findings; all scoped
Stage 3 Python files are clean. A Stage 3-specific live Horizons audit was not
run at this implementation checkpoint. No commit, version change, tag, package
publication, push, or deployment was performed.
