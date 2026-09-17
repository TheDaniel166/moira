# Orbital Core Stage 2 Implementation Plan

> **For agentic workers:** Execute this plan in order. Stage 2 is an
> implementation checkpoint on top of the uncommitted Stage 1 worktree; it is
> not authorization to commit, version, tag, publish, push, or deploy.

**Date:** 2026-09-15

**Status:** Implementation complete; validation review-ready; release blocked;
release actions not authorized

**Baseline:** Stage 1 working tree on `orbital-core-stage1`, whose committed
base is `dfad306f47901596e9edc254116ac3c6d47a3764` and whose repository baseline
is `origin/main` at `29dd164c80c2a6788aa598a832eff3d4fd8e727a`

**Governing spec:**
`docs/superpowers/specs/2026-09-15-orbital-core-design.md`, SHA-256
`fba918c2755181f5d467ed957891278fb249bfde19931ecd310baf6019329a38`

**Goal:** Add a versioned, source-receipted apsidal-passage search over the
Stage 1 TDB state substrate; expose next and previous pericenter/apocenter
outcomes for every admitted body/center pair; preserve the legacy
planet-only `DistanceExtremes` and `PhenomenonEvent` contracts with their
correct TT and UT1 output scales; and upgrade the existing planet-only REST
distance-extremes route without widening its body admission.

**Governing object:** An apsidal passage is an isolated, two-sided local
extremum of center-relative distance. It is located as a zero of
`dot(r, v_day) / |r|` on one immutable TDB route plan, classified from the
chronological sign crossing, and independently witnessed by distances on both
sides. An osculating conic supplies a search scale, never the event itself.

**Authority:** JPL DE441 supplies runtime states; NAIF supplies TT/TDB time
policy; official JPL Horizons `VECTORS` output supplies external event
validation. Existing Moira passage results are regression witnesses only.

---

## 1. Boundaries

### Included

1. Public enums, outcomes, result and provenance vessels for Stage 2.
2. `apsidal_passages(...)` with required `center` and `direction` policies.
3. One leased reader snapshot, one bound clock identity and one frozen route
   schedule per search.
4. Directional, inclusive radial-velocity sampling; safeguarded bracketed
   refinement; two-sided distance confirmation; fixed evaluation budget.
5. Explicit `FOUND`, `BEYOND_COVERAGE`, and `NOT_IN_WINDOW` outcomes.
6. `OrbitalSearchError` and `OrbitalPassageUnavailableError`, including built-in
   compatibility, attributes, pickling, exports and server mappings.
7. `distance_extremes_at` migration, preserving its planet-only signature and
   returning TT in both `*_jd` fields.
8. `phenomena.perihelion` and `phenomena.aphelion` migration for every admitted
   body with its only lawful center, preserving verified UT1 in `jd_ut`.
9. Facade, predictive exports, API audit and the existing planet-only REST
   `/v1/orbits/distance-extremes` response upgrade.
10. Deterministic synthetic tests, DE441 integration tests, primary-source
    Horizons fixtures/tooling, documentation and a Stage 2 verification
    receipt.

### Excluded

- Stage 3 node migration, Stage 4 Shadbala redesign, Stage 5 orbit classes and
  Stage 6 REST small-body admission.
- A new numerical dependency or derivative-free fallback.
- Rewriting catalog manifests or unrelated Stage 1 code.
- Any commit, version bump, tag, package publication, push or deployment.

### Unrelated work to preserve

- `docs/architecture/ASPECT_PATTERN_QUALITATIVE_SCORING_V1_DRAFT.md`
- all existing Stage 1 source, test, documentation and receipt changes
- untracked Stage 1 temporary comparison trees

---

## 2. Frozen Search Policy

The implementation freezes these values under
`MOIRA_APSIDAL_PASSAGES_V1` after calibration and before holdout validation:

- root time tolerance: `1e-8` day;
- maximum root iterations: `96`;
- evaluation budget: `20_000` state evaluations;
- initial period fraction: `1/256`;
- local radial-timescale fraction: `1/20`;
- minimum sampling step: `0.05` day;
- maximum sampling step: `32` days;
- two-sided witness offset: the larger of eight root tolerances, one tenth of
  the minimum sampling step, and `1e-4` of the local `|r|/|v|` motion
  timescale, capped at one day; both witnesses must remain in route coverage;
- seam continuity gates: explicit position and velocity residual limits,
  recorded with every attempted source seam.

These constants are implementation policy, not accuracy claims. Holdout
failure returns the change to investigation; tolerances are not widened to
absorb failures.

---

## 3. Implementation Sequence

### Task 1 — Route-plan substrate

- Factor route evaluation in `spk_reader.py` so a preselected route can be
  evaluated repeatedly against one `_PoolSnapshot`.
- Build an internal route schedule from exact closed coverage intervals.
- Keep brackets inside one schedule entry. At a touching source boundary,
  compare independently evaluated left/right states; admit continuation only
  when the published seam gates pass.
- Freeze plan identity from center, target, generation, ordered route/source
  identities and exact intervals. Record actual per-segment evaluation counts.

### Task 2 — Clock inverse and errors

- Allow the existing TDB -> TT -> UT1 inverse to retain the leased snapshot.
- Translate non-closing inversions into `OrbitalTimeBasisError`.
- Add the two Stage 2 errors and freeze MRO, constructor, attributes, message,
  `args`, pickle round-trip and all promised re-exports.

### Task 3 — Core passage search

- Add the public enums and vessels in `moira.orbits`.
- Validate body, epoch, center, direction and `max_days` before search.
- Bind one start state and derive only the sampling/window scale from its
  osculating shape.
- Search in chronological TDB geometry for the requested direction; classify
  `- -> +` as pericenter and `+ -> -` as apocenter regardless of traversal
  direction.
- Require the event epoch to lie inside the directional request window and
  require both witnesses to lie inside admitted route coverage.
- Return complete, mutually exclusive outcome fields and provenance.

### Task 4 — Compatibility surfaces

- Migrate `distance_extremes_at` to `NEXT`, `SUN`, preserve the current legacy
  planet list, place verified TT in `DistanceExtremes.*_jd`, and raise
  `OrbitalPassageUnavailableError` unless both outcomes are `FOUND`.
- Migrate `phenomena.perihelion`/`aphelion`; select `EARTH` for the Moon and
  `SUN` otherwise; return `None` for a legitimate non-found outcome; preserve
  UT1 in `PhenomenonEvent.jd_ut`.
- Add `Moira.apsidal_passages` and root/facade/predictive exports.

### Task 5 — REST transport

- Keep `ADMITTED_ORBIT_BODIES` unchanged.
- Replace the provisional distance-extremes time labels with UT1 input, TDB
  state, TT output and the bound conversion receipt.
- Serialize the passage search provenance, route schedule and outcomes through
  explicit Pydantic models; do not expose paths or arbitrary exception text.
- Map Stage 2 orbital errors before generic `ValueError`/`ArithmeticError`.

### Task 6 — Validation and documentation

- Add synthetic circular/elliptic/unbound, exact-start, forward/reverse,
  explicit-window, coverage-edge, gap, flat-signal, budget and seam tests.
- Add DE441 planet, Pluto target, Earth-versus-EMB and loaded small-body checks.
- Produce `horizons_apsidal_passages_reference.json` only from official
  Horizons `VECTORS` data with request/response hashes, center, timescale,
  refinement method and tolerances.
- Keep calibration and holdout cases disjoint. Record unavailable catalog or
  live-network prerequisites rather than substituting weaker evidence.
- Update the minimum canonical wiki/REST/validation/changelog documents and
  regenerate `moira.wiki` through `scripts/sync_git_wiki.py`.

---

## 4. Verification Order

All commands use `C:\dev\moira\.venv\Scripts\python.exe`, with
`MOIRA_TEST_MODE=1`, `MOIRA_STRICT_KNOWN_ISSUES=1` and
`MOIRA_NO_DOWNLOAD=1` unless a selected test explicitly authorizes external
network access.

1. New kernel-free passage-search and error tests.
2. Changed route, time, legacy wrapper, phenomena, facade and server tests.
3. DE441 passage and distance-extremes tests.
4. Existing Stage 1 orbital, kernel and compatibility receipt tests.
5. Exact live Horizons Stage 2 slice, separately authorized by pytest marker.
6. Full catalog matrix when the exact released asteroid/comet resources are
   installed; otherwise record the missing prerequisite.
7. `pytest -m "not external_network"`, documentation consistency and scoped
   Ruff audit, with baseline-reproduced unrelated failures identified.

Completion reports exact commands, cases, timescales, centers, tolerances,
skips and unresolved validation gaps. A passing implementation checkpoint is
not a release receipt.

---

## 5. Implementation Checkpoint

Stage 2 is implemented in the uncommitted Stage 1 worktree and is bound to
`MOIRA_APSIDAL_PASSAGES_V1`. The machine-checked validation receipt is
`tests/artifacts/release/orbital_core_stage2_validation_2026-09-15.json`.

The frozen official NASA/JPL Horizons fixture contains 16 disjoint calibration
and holdout records and 29 events. All ten DE441 planet/system authority cases
pass the frozen `1e-4` day and `1e-9` AU gates. The marked live Horizons slice
passes for Earth and Neptune. Synthetic direction, exact-start, window,
coverage, seam, budget and witness semantics pass.

Six small-body authority comparisons remain explicitly `NOT RUN`: the
installed comet and asteroid-wheel manifests do not yet carry reviewed Stage 2
accuracy admission bound to this exact fixture and its gates. Eros supplies a
runnable loaded-catalog smoke test only; it is not described as authority
parity. The full asteroid release is also unavailable in this environment.

The focused Stage 2 gate passes 204 tests with those six admission skips. The
finished-tree consolidated Stage 2 gate passes 289 tests with six catalog
admission skips and two unavailable `jplephem` comparison prerequisites. The
Stage 1 regression slice passes 210 tests with three prerequisite skips. The
broader non-external-network suite still stops at the baseline nested-project
test-harness import defect for `support.small_body_resource_policy`, before a
Stage 2 orbital assertion is reached. Stage 2 scoped Ruff and documentation
gates pass; the broad changed-file Ruff result remains the 66 inherited Stage 1
findings.

No commit, version change, tag, package publication, push, or deployment has
been performed. Release remains blocked pending reviewed catalog admissions,
the unavailable full asteroid prerequisite, and disposition of the inherited
repository-wide gates.
