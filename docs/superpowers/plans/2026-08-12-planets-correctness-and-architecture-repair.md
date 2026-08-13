# Planetary Correctness And Architecture Repair Plan

**Date:** 2026-08-12

**Status:** Ready for staged implementation; not a release record

**Baseline:** `origin/main` at `f437e5fdf4c4d3d9664fb46090e0992cee93422e`

**Audit candidate:** local, uncommitted worktree
`C:\dev\moira-planets-architecture-audit-20260812`

**Primary protected zones:** `moira/planets.py`, `moira/spk_reader.py`,
`moira/asteroids.py`, planetary/SPK tests

## Purpose

Close the verified correctness and architecture risks found in the 2026-08-12
planetary audit without turning a bounded repair into a rewrite of Moira's
planetary substrate.

The plan covers seven workstreams:

1. isolate explicit TT overrides from ordinary UT-derived memoization
2. validate the provenance of injected reduction contexts
3. give reader memoization unambiguous per-reader, per-thread ownership
4. narrow exception handling at optional cache and native-optimization seams
5. separate the public planetary API from internal reduction workspaces
6. replace opaque native-admission booleans with internal structured decisions
7. centralize the asteroid-specific apparent-vector adapter without changing
   asteroid astronomy

The first four are correctness or reliability work. The last three are
compatibility-safe architecture cleanup and must not delay the first release
if their independent gates are not ready.

---

## Executive Decision

### Mandatory before the next planetary release

- Explicit `jd_tt` calls must never seed or overwrite a cache entry used by a
  later call whose TT is derived from `jd_ut`.
- An injected reduction context must be rejected unless its reader identity,
  TT epoch, apparent/geometric mode, and nutation mode match the consuming
  call.
- Mutable memoization attached to a shared reader must not be shared between
  worker threads.
- Optimization fallback must catch only known capability/attachment failures;
  scientific, kernel, and programming failures must propagate.
- Regression tests must prove call-order independence, reader/thread isolation,
  native/Python equivalence on the admitted surface, and unchanged topocentric
  asteroid vectors.

### Recommended follow-up, independently landable

- Move internal cache/context hooks out of `planet_at()`'s public signature.
- Introduce an internal, structured native-admission decision/plan so fallback
  causes can be tested without logging or public API expansion.
- Add one asteroid-owned adapter around the existing generic apparent-vector
  pipeline so identity/deflector assembly is not duplicated in `planets.py`.

### Claims this plan intentionally does not adopt

The audit did **not** establish numerical order dependence among planetary
bodies, catastrophic concurrent corruption, an unsound native implementation,
or incorrect asteroid math. Those claims are not repair requirements.

- Planet order permutations were exact in the audited samples.
- Shared-reader concurrent calls matched serial results in the audited run.
- The native and Python products agreed exactly on the installed build across
  the tested epochs and ten planetary bodies.
- The topocentric asteroid spherical adapter preserved the underlying vector
  within floating-point noise.
- Ceremonial `RITE`, `THEOREM`, and `MACHINE_CONTRACT` documentation is not a
  defect and must be preserved.

---

## Governing Object And Authority

### Governing computational object

The governing object is one planetary reduction workspace bound to:

- one `KernelReader` identity
- one exact TT epoch
- one apparent/geometric policy
- one nutation policy
- the derived Earth state, nutation values, rotation matrix, and vector cache
  for that exact tuple

It is not a generic bag of cached vectors and it is not valid merely because
its numerical fields have compatible shapes.

### Ambiguity policy

- `jd_ut` is the public time input.
- `jd_tt` is an explicit public override for the current call only.
- A custom `DeltaTPolicy` is part of the UT-to-TT derivation identity.
- Exact floating-point JDs remain exact cache keys; this plan does not add
  rounding or epoch normalization.
- A caller-supplied internal workspace either matches exactly or fails loudly.
  Moira must not silently repair or partially reuse a mismatched workspace.

### Evidence classes

- **Regression invariants:** cache isolation, permutation independence,
  signature governance, thread ownership, and exact same-path equality.
- **Internal differential evidence:** native versus Python planetary output
  under identical JPL kernel, frame, time, and correction semantics.
- **Stored authority evidence:** the tracked JPL Horizons asteroid fixture where
  the asteroid phase is exercised.
- **Primary substrate:** the discovered JPL DE441 kernel and admitted
  supplemental small-body manifests.

Swiss Ephemeris and `jplephem` are not runtime dependencies or primary oracles
for this work.

---

## Issue Register

| ID | Issue | Class | Severity | Required outcome |
|---|---|---|---|---|
| P-01 | Explicit `jd_tt` can poison a later UT-derived cache lookup | Confirmed correctness defect | P0 | Explicit overrides bypass ordinary call-cache read/write |
| P-02 | Injected `_context` and private workspace fragments lack provenance enforcement | Confirmed correctness defect | P0 | Exact reader/epoch/policy/workspace validation |
| P-03 | Reader-attached mutable LRU/context state has shared cross-thread ownership | Confirmed architecture risk | P1 | Per-reader, per-thread bounded caches |
| P-04 | Broad fallback catches can hide defects | Confirmed reliability risk | P1 | Exception decision table and narrow catches |
| P-05 | `planet_at()` exposes internal mutable reduction hooks in its callable signature | API design debt | P2 | Public wrapper plus private implementation/workspace |
| P-06 | Native admission returns only result-or-`None`, obscuring why Python ran | Diagnostics debt | P2 | Internal structured admission plan/reason |
| P-07 | Asteroid identity/deflector/vector assembly crosses module ownership | Maintainability debt | P3 | One asteroid-owned vector adapter, exact output parity |
| D-01 | Cartesian/SPK prose overstates frame or cache/handle behavior | Documentation defect | P1 | Prose aligned with executable contracts |

P0/P1 are release work. P2/P3 are separate refactors and must be revertible
without undoing P0/P1.

---

## Non-Negotiable Invariants

Every implementation phase must preserve these laws:

1. **History independence:** a result depends on its declared inputs, not on a
   previous call's TT override, body order, or thread.
2. **Reader provenance:** no context or cache entry crosses reader identity.
3. **Epoch provenance:** a workspace for TT `A` cannot serve TT `B`.
4. **Policy provenance:** apparent and nutation modes are part of workspace
   identity.
5. **Thread ownership:** concurrently admitted reads may share the stable
   reader/kernel, but not mutable Python LRU/workspace containers.
6. **Failure visibility:** missing optional optimization capability may fall
   back; bad data, invalid state, and unexpected runtime failures may not.
7. **Public stability:** `jd_tt` and `delta_t_policy` remain supported public
   options. Internal cache/nutation hooks are not converted into public policy.
8. **Numerical continuity:** architecture refactors do not change the declared
   planetary or asteroid product.
9. **No hidden I/O:** diagnostics and cache ownership add no network, download,
   or ambient logging side effect.
10. **Ceremonial preservation:** touched machine contracts and theorem prose
    remain intact and factually corrected where necessary.

---

## Target Architecture

### Public boundary

`planet_at()` remains the stable public function and owns:

- argument validation
- active-reader resolution
- UT/TT policy selection
- small-body routing
- construction of a private reduction request
- return of `PlanetData` or `CartesianPosition`

It must eventually stop exposing `_dpsi_deg`, `_deps_deg`, `_rot_mat`,
`_vector_cache`, and `_context` in its public signature.

### Private reduction boundary

Introduce one private entry point, provisionally named `_planet_at_impl()`,
whose only reusable workspace input is an opaque `_ApparentContext` (or a
renamed `_PlanetReductionWorkspace`). Individual matrix, nutation, and cache
fragments must not cross this boundary separately.

The workspace carries:

```python
reader: KernelReader
jd_tt: float
apparent: bool
nutation: bool
dpsi_deg: float
deps_deg: float
obliquity: float
rot_mat: object | None
vector_cache: dict
earth_ssb: Vec3 | None
earth_vel: Vec3 | None
```

### Cache boundary

The stable `KernelReader` may own one lazily initialized `threading.local()`
container. Each thread receives independent bounded `OrderedDict` instances
for:

- UT-derived planetary call contexts
- apparent reduction contexts

The reader's existing lifecycle contract remains unchanged: concurrent reads
on an already-open reader are admitted; close/hot-swap during active reads is
not.

### Native boundary

Native selection remains an optimization choice, not astronomical policy. An
internal immutable admission vessel should identify:

- selected backend: native evaluator, native batch substrate, or Python
- admitted/rejected state
- stable reason code
- prepared route data needed by execution, where carrying it avoids duplicate
  segment discovery

It must not print, log, mutate global state, or become a public API by accident.

### Asteroid boundary

The existing generic `_apparent_geocentric_equatorial_vector()` remains the
single reduction math. Add only a small asteroid-owned adapter that supplies:

- asteroid NAIF identity
- SSB position callback
- asteroid deflectors
- Earth state and rotation inputs
- correction switches

Topocentric conversion, horizontal coordinates, and refraction remain owned by
the sky/topocentric layer. The planetary asteroid adapter must continue to call
that path with refraction disabled.

---

## Phase 0 — Freeze, Reproduce, And Record

### Objective

Establish a trustworthy before-state and protect unrelated work.

### Steps

- [ ] Work in a clean isolated worktree from current `origin/main`.
- [ ] Record branch, commit, `git status --short --branch`, Python version,
      native backend path, and discovered kernel path.
- [ ] Read `tests/KNOWN_ISSUES.yml` and enable strict expiry checking.
- [ ] Set `MOIRA_TEST_MODE=1`, `MOIRA_STRICT_KNOWN_ISSUES=1`, and
      `MOIRA_NO_DOWNLOAD=1`.
- [ ] Preserve the original dirty checkout exactly; do not stash, reset, or
      stage it.
- [ ] Run the existing planetary/time baseline before edits.
- [ ] Run focused reproducers that demonstrate P-01 and P-02 on the unmodified
      baseline; record numerical deltas without turning those deltas into new
      golden files.

### Required baseline commands

```powershell
$env:MOIRA_TEST_MODE = "1"
$env:MOIRA_STRICT_KNOWN_ISSUES = "1"
$env:MOIRA_NO_DOWNLOAD = "1"
.\.venv\Scripts\python.exe -m pytest `
  tests\unit\test_planet_position_switches.py `
  tests\unit\test_ephemeris_time.py -q
```

### Stop conditions

- Kernel discovery is not deterministic with downloads disabled.
- The installed native extension does not match the source/build state.
- A baseline failure intersects the intended repair and cannot be separated
  from the new work.

---

## Phase 1 — Correctness Closure: TT And Context Provenance

### Objective

Fix P-01 and P-02 before any structural cleanup.

### Files

- Modify: `moira/planets.py`
- Add or modify: `tests/unit/test_planets_architecture_invariants.py`

### Task 1.1 — Isolate explicit TT overrides

- [ ] Record `explicit_jd_tt = jd_tt is not None` before cache lookup.
- [ ] Permit the ordinary planetary call cache only when TT is being derived
      from `jd_ut` under the supplied `DeltaTPolicy`.
- [ ] Never insert an explicit TT override into that ordinary call cache.
- [ ] Keep explicit TT eligible for the exact-epoch apparent-context cache only
      when its complete key includes exact TT, apparent mode, and nutation mode.
- [ ] Do not round or normalize JD keys.

#### Required regression

1. Compute a normal UT-derived Moon result with a fresh reader.
2. On a separate reader, call `planet_at()` at the same `jd_ut` with a materially
   different explicit `jd_tt`.
3. Call `planet_at()` again without `jd_tt`.
4. Assert the final result exactly equals the fresh-reader normal result and
   does not equal the explicit-TT product.

Add a second regression using two custom `DeltaTPolicy` instances to prove
their UT-derived cache identities remain distinct.

### Task 1.2 — Validate opaque context provenance

- [ ] Extend `_ApparentContext` with reader identity, apparent mode, and
      nutation mode in addition to TT epoch.
- [ ] Add `_validate_apparent_context()`.
- [ ] Reject a context built for a different reader by object identity.
- [ ] Reject a context whose TT epoch differs exactly.
- [ ] Reject apparent/geometric and nutation-policy mismatches.
- [ ] Validate before any cached field is consumed.
- [ ] Do not clone, mutate, or silently repair a bad context.

### Task 1.3 — Reject detached workspace fragments

During the compatibility phase, callers may still see the retained private
parameters. They must be governed as a coherent workspace:

- [ ] `_vector_cache` must be the exact cache owned by `_context`.
- [ ] `_dpsi_deg`, `_deps_deg`, and `_rot_mat` must equal the context values.
- [ ] Any supplied private fragment without a context raises `ValueError`.
- [ ] Error text identifies the consuming surface and mismatched provenance,
      but does not dump kernel data.

### Phase 1 acceptance

- [ ] Explicit-TT poison reproducer is red before and green after.
- [ ] Wrong epoch, wrong reader, wrong nutation, and detached cache tests fail
      closed.
- [ ] Custom Delta-T policies retain distinct outputs/cache entries.
- [ ] Existing `planet_at`, `sky_position_at`, and `all_planets_at` tests pass.
- [ ] No numerical output changes for valid calls.

### Commit boundary

One focused commit:

```text
fix(planets): isolate TT overrides and validate reduction contexts
```

Do not combine the public signature refactor with this commit.

---

## Phase 2 — Per-Thread Reader Cache Ownership

### Objective

Close P-03 while preserving the admitted stable-reader concurrency contract.

### Files

- Modify: `moira/planets.py`
- Modify: `moira/spk_reader.py` only for factual contract prose
- Modify: `tests/unit/test_planets_architecture_invariants.py`
- Review: `docs/threading.md`; edit only if the public contract actually
  changes (the proposed implementation does not change it)

### Design

- [ ] Define `_ReaderThreadCaches` with bounded call-context and
      apparent-context `OrderedDict` instances.
- [ ] Attach one `threading.local()` to a mutable reader under a private,
      collision-resistant attribute name.
- [ ] Guard only first attachment with a reader-owned/module `RLock` so the
      design remains valid on free-threaded CPython as well as GIL builds.
- [ ] Create each thread's `_ReaderThreadCaches` lazily inside the
      `threading.local()` namespace.
- [ ] If a test double or immutable reader cannot accept the attribute, disable
      memoization for that reader rather than switching to a global cache.
- [ ] Catch only `AttributeError` and `TypeError` at that optional attachment
      seam.
- [ ] Retain existing LRU bounds and eviction behavior inside each thread.

### Required regressions

- [ ] Two threads using the same reader receive distinct mutable cache objects.
- [ ] Repeated calls in one thread reuse that thread's bounded context.
- [ ] Reader A never sees Reader B's contexts, even at identical epochs.
- [ ] A shared real `SpkReader` produces results identical to a serial baseline
      under a bounded `ThreadPoolExecutor` sweep.
- [ ] All six permutations of Mars/Jupiter/Saturn at two epochs are exact,
      proving the cache hardening did not create order-sensitive deflector
      state.
- [ ] Jupiter and Saturn are never included as their own deflectors.

### Concurrency claim boundary

The local CPython 3.14 runtime may still have the GIL enabled. Passing that run
does not prove every free-threaded deployment. If a supported 3.14t CI runner
exists, repeat the concurrency slice there. Otherwise record it as an
unexercised environment, not a blocker to the GIL-build repair.

### Phase 2 acceptance

- [ ] No mutable Python reduction cache is shared across threads.
- [ ] Concurrent read results equal the serial baseline.
- [ ] No claim is made that `close()` or reader hot-swap is safe in flight.
- [ ] `docs/threading.md`, `SpkReader` prose, and machine contracts agree.

### Commit boundary

```text
fix(planets): namespace memoization by reader and thread
```

---

## Phase 3 — Exception And Documentation Hygiene

### Objective

Close P-04 and D-01 without converting optional optimization fallback into a
blanket error sink.

### Exception decision table

| Seam | May fall back on | Must propagate |
|---|---|---|
| Attaching thread-local cache state | `AttributeError`, `TypeError` | `MemoryError`, unexpected runtime/programming errors |
| Constructing optional native evaluator | documented capability mismatch such as `RuntimeError`/`TypeError` from the constructor | kernel range/data errors after execution begins, invalid values, unexpected exceptions |
| Caching evaluator on mutable kernel wrapper | `AttributeError`, `TypeError` | unexpected failures unrelated to attribute capability |
| One-sided rate sample at kernel boundary | the existing explicit `OutOfRangeError` | all unrelated exceptions |
| Reader/handle cleanup | retain deliberate best-effort cleanup catches with comments | constructor/open failures still re-raise after cleanup |
| Optional supplemental catalog discovery | separately review; do not widen this task automatically | programming defects should not be newly hidden |

### Steps

- [ ] Inventory every `except` in the touched functions.
- [ ] Replace broad catches only where the allowed failure class is known.
- [ ] Add fakes that raise one admitted fallback exception and one unexpected
      exception; prove only the admitted exception falls back.
- [ ] Do not globally rewrite `spk_reader.py` cleanup logic.
- [ ] Correct `CartesianPosition` frame prose to mean/true
      equatorial-of-date where that is the actual product.
- [ ] Correct `SpkReader` prose: methods do not cache computed positions, but
      higher layers may attach namespaced memoization.
- [ ] Correct handle wording to one reader-owned handle per live reader, not
      one global handle.
- [ ] State that the native reader is required and `jplephem` is at most an
      optional development parity probe.
- [ ] Preserve ceremonial sections and machine-contract structure.

### Phase 3 acceptance

- [ ] No broad `except Exception` remains in the repaired planetary cache or
      native-optimization seams.
- [ ] Deliberate cleanup catches remain documented and behaviorally unchanged.
- [ ] Unexpected scientific/runtime errors reach the caller.
- [ ] Touched prose describes actual frames, caches, handles, and dependencies.

### Commit boundary

```text
fix(planets): narrow optimization fallback and correct substrate contracts
```

This may be combined with Phase 2 only if review confirms that the prose and
exception edits are inseparable from the cache ownership change.

---

## Phase 4 — Public/Private Signature Separation

### Objective

Close P-05 after correctness is already protected by tests.

### Compatibility policy

`jd_tt` and `delta_t_policy` are legitimate public parameters and remain.
Only these internal fragments are scheduled for removal from the public
signature:

- `_dpsi_deg`
- `_deps_deg`
- `_rot_mat`
- `_vector_cache`
- `_context`

Repository scanning found no caller outside `moira/planets.py` supplying these
hooks. Because published consumers may still introspect or use underscored
parameters, use one explicit compatibility cycle rather than silently removing
them in the same commit as P-01/P-02.

### Release A — internalize all repository callers

- [ ] Introduce `_planet_at_impl()` with one opaque workspace/context input.
- [ ] Make public `planet_at()` a validation and routing wrapper.
- [ ] Move `all_planets_at()`, `_sky_position_at_impl()`, rate helpers, and
      other internal calls to `_planet_at_impl()`.
- [ ] Stop passing individual nutation/matrix/cache fragments internally.
- [ ] Keep the old private arguments temporarily on `planet_at()`.
- [ ] When a non-`None` private hook is supplied through the public wrapper,
      validate it and emit a targeted `DeprecationWarning` with the planned
      removal boundary.
- [ ] Do not add a permissive `**kwargs` sink.

### Release B — remove the compatibility hooks

- [ ] Remove the five private parameters from `planet_at()`.
- [ ] Remove transition-only fragment validation if it is no longer called.
- [ ] Retain context provenance validation on `_planet_at_impl()`.
- [ ] Update API reference/signature governance and migration notes.
- [ ] Search the entire repository, examples, docs, and packaged mirrors before
      removal.

### Required regressions

- [ ] Public signature contains all supported public parameters and none of the
      five private workspace hooks after Release B.
- [ ] `_planet_at_impl()` is not exported from `moira.facade` or package
      `__all__` surfaces.
- [ ] AST/source audit prevents new external repository calls to the private
      implementation.
- [ ] Public wrapper and private implementation return exact-equal products for
      representative default, geometric, barycentric, cartesian, and
      topocentric cases.
- [ ] All eleven legitimate repository `jd_tt=` call sites continue to work.

### Commit boundaries

```text
refactor(planets): separate public API from reduction workspace
```

and, only at the approved removal boundary:

```text
refactor(planets): remove deprecated private signature hooks
```

---

## Phase 5 — Structured Native Admission Diagnostics

### Objective

Close P-06 without changing which backend is selected or exposing a new public
API.

### Design

Replace the mode-only Boolean and result-or-`None` ambiguity with an internal
immutable decision/plan. Suggested shape:

```python
@dataclass(frozen=True)
class _NativeAllPlanetsPlan:
    backend: Literal["native_evaluator", "native_batch", "python"]
    admitted: bool
    reason: _NativeAdmissionReason
    route_specs: tuple | None = None
    body_route_specs: dict | None = None
```

Reason codes must be stable enough for tests but remain private. Cover at
least:

- empty or unsupported body set
- non-default correction policy
- non-geocentric center
- topocentric request
- custom Delta-T policy
- unsupported reader type
- missing batch handle/capability
- unavailable public route at the requested epoch
- unavailable per-body route
- unavailable rate-sample route
- native evaluator unavailable with admitted native-batch fallback
- admitted native evaluator
- admitted native batch substrate

### Steps

- [ ] Make condition ordering explicit and deterministic.
- [ ] Carry prepared route specs in the plan if doing so avoids repeating
      segment discovery.
- [ ] Keep all diagnostics in memory; no ambient logs or metrics.
- [ ] Preserve the existing Python fallback result exactly.
- [ ] Treat nonzero elevation without observer coordinates according to public
      semantics: if the Python path truly ignores it, normalize it before
      admission or document the conservative fallback. Any optimization change
      requires exact native/Python parity evidence.
- [ ] Do not catch runtime computation failures merely to produce a reason
      code; the decision explains eligibility, not scientific failure.

### Required regressions

- [ ] One test per rejection reason.
- [ ] One test for native-evaluator selection and one for native-batch fallback.
- [ ] Public `all_planets_at()` results remain exact-equal before and after.
- [ ] Native/Python comparison covers 1900, J2000, and a modern epoch, all ten
      admitted bodies, longitude, latitude, distance, speed, and retrograde.
- [ ] Tests do not assert that native execution is intrinsically more correct
      than Python execution.

### Commit boundary

```text
refactor(planets): make native admission decisions inspectable
```

---

## Phase 6 — Shared Asteroid Vector Adapter

### Objective

Close P-07 as a pure ownership/duplication cleanup. There is no demonstrated
asteroid numerical defect to repair.

### Current truth

`moira/planets.py` already owns the generic
`_apparent_geocentric_equatorial_vector()` and
`_apparent_geocentric_ecliptic()` mathematics. `moira/asteroids.py` already
owns asteroid identity and deflector assembly. The remaining smell is that the
topocentric sky path locally reassembles asteroid-specific inputs across the
module boundary.

### Design

- [ ] Add an asteroid-owned private adapter, provisionally
      `_asteroid_apparent_equatorial_vector()`.
- [ ] Keep it a thin adapter over the existing generic planetary vector helper;
      do not duplicate light-time, deflection, aberration, frame bias,
      precession, or nutation math.
- [ ] Accept explicit TT, reader, correction switches, Earth state, and rotation
      context needed by the caller.
- [ ] Resolve identity and deflectors in `asteroids.py`.
- [ ] Import it lazily from `planets.py` to avoid a module import cycle.
- [ ] Route the asteroid branch of `_sky_position_at_impl()` through it.
- [ ] Optionally route `_asteroid_at_with_flags()` through the same adapter only
      if the ecliptic projection remains exact and the change reduces, rather
      than increases, private coupling.
- [ ] Keep refraction outside the vector helper and disabled in the planetary
      topocentric adapter.

### Required regressions

- [ ] Direct vector-to-ecliptic projection and public topocentric asteroid
      result agree within `1e-12` degrees for longitude/latitude and exactly for
      distance where current arithmetic permits.
- [ ] A spy proves the planetary adapter does not invoke refraction.
- [ ] Stored JPL Horizons asteroid fixture remains within its existing declared
      tolerance; do not relax the fixture tolerance.
- [ ] Apparent/geometric, aberration, deflection, and nutation switch tests pass.
- [ ] Ceres works through the unified planetary front door and direct asteroid
      API with no identity drift.
- [ ] No new public function or result vessel is introduced.

### Stop condition

If the adapter creates a circular import, duplicates the generic reduction
pipeline, or changes any product beyond floating-point evaluation order, stop
and retain the already-correct implementation. Deleting duplication is not
worth weakening ownership or validation.

### Commit boundary

```text
refactor(asteroids): centralize apparent vector assembly
```

---

## Phase 7 — Integration, Documentation, And Release Gate

### Documentation

- [ ] Update only the minimum public/API docs affected by signature removal.
- [ ] Keep `docs/threading.md` unchanged unless the public concurrency contract
      changes; implementation detail alone is not a contract change.
- [ ] Correct touched `SpkReader` and Cartesian frame prose.
- [ ] Do not hand-edit `moira.wiki/`; use the repository sync process only if a
      canonical `wiki/` source is changed.
- [ ] Add a release note describing the explicit-TT isolation bug and context
      validation without overstating affected numerical surfaces.
- [ ] State whether private hook removal is in the current release or a later
      compatibility boundary.

### Focused verification ladder

Run each tier only after the previous tier passes.

#### Tier 1 — syntax and architecture regressions

```powershell
.\.venv\Scripts\python.exe -m py_compile `
  moira\planets.py moira\spk_reader.py moira\asteroids.py

.\.venv\Scripts\python.exe -m pytest `
  tests\unit\test_planets_architecture_invariants.py -q
```

#### Tier 2 — planetary API, time, reader, and frame behavior

```powershell
.\.venv\Scripts\python.exe -m pytest `
  tests\unit\test_planet_position_switches.py `
  tests\unit\test_ephemeris_time.py `
  tests\unit\test_planetary_frame_contracts.py `
  tests\unit\test_spk_reader.py `
  tests\unit\test_threading_contract_audit.py -q
```

#### Tier 3 — asteroid and native differential evidence

```powershell
.\.venv\Scripts\python.exe -m pytest `
  tests\unit\test_asteroid_api.py `
  tests\unit\test_chiron_planet_bridge.py `
  tests\integration\test_horizons_asteroid_apparent.py `
  tests\unit\test_native_evaluator_thread_safety_audit.py `
  tests\unit\test_planetary_native_ownership_snapshot.py -q
```

The asteroid Horizons test uses its tracked fixture and does not authorize a
live network refresh.

#### Tier 4 — bounded relevant suite

Select all directly affected planetary, SPK, time, small-body, native parity,
and facade tests. Record exact file/test/pass/skip counts. Any skipped
`jplephem` comparison is an unavailable optional development comparator, not
evidence for or against Moira's runtime correctness.

#### Tier 5 — full configured suite

Run only after all focused phases are final and the cost/effects are intended:

```powershell
.\.venv\Scripts\python.exe -m pytest
```

External-network tests remain denied unless separately authorized. Report
their skips explicitly.

#### Static/document gates

```powershell
.\.venv\Scripts\ruff.exe check `
  moira\planets.py moira\spk_reader.py moira\asteroids.py `
  tests\unit\test_planets_architecture_invariants.py --no-fix

.\.venv\Scripts\python.exe scripts\check_doc_consistency.py
git diff --check
```

Compare touched-file Ruff output to `HEAD`; do not hide pre-existing baseline
findings and do not run broad auto-fix.

---

## Verification Matrix

| Requirement | Primary test/evidence | Acceptance |
|---|---|---|
| Explicit TT isolation | `test_explicit_jd_tt_cannot_contaminate_later_derived_call` | Clean and post-override normal calls exact-equal |
| Delta-T policy isolation | custom policy regression | Distinct TT policies do not share call context |
| Context provenance | epoch/reader/nutation mismatch test | Every mismatch raises before use |
| Detached workspace rejection | private fragment test | Fragment without matching context raises |
| Per-thread cache ownership | thread-local identity test | Mutable caches differ by thread and reader |
| Order independence | all Mars/Jupiter/Saturn permutations | Exact equality at both epochs |
| Deflector identity | Jupiter/Saturn test | No body deflects itself |
| Concurrent read behavior | serial vs thread pool | Exact public product equality |
| Native/Python equivalence | three epochs, ten bodies | Existing product-owned tolerances; record actual max residual |
| Public/private API split | signature/export/call-site audits | No private hooks on final public signature |
| Native reason coverage | reason-code parameterization | Every branch has deterministic reason/backend |
| Asteroid adapter | vector equivalence and Horizons fixture | No tolerance relaxation; no refraction call |
| Documentation truth | doc consistency + source review | No stale frame/cache/handle/dependency claims |

---

## Rollback And Bisect Strategy

Each phase must be independently revertible.

- Reverting Phase 6 must leave the topocentric asteroid numerical fix
  (`refraction=False`) and P0/P1 work intact.
- Reverting Phase 5 must restore opaque Python fallback selection without
  changing results.
- Reverting Phase 4 must restore only the compatibility signature, not remove
  P-01/P-02 validation.
- Phase 3 exception narrowing may be reverted separately from thread-local
  cache ownership if an environment-specific capability mismatch is found.
- Phase 1 and Phase 2 should not be reverted for performance reasons without a
  new correctness design and equivalent regression proof.

Do not squash all phases into one unreviewable commit. A bisect must be able to
answer whether a failure came from correctness, cache ownership, API cleanup,
native diagnostics, or asteroid ownership.

---

## Local Implementation and Oracle Checkpoint — 2026-08-13

The isolated repair candidate implements every phase that can safely land in
Release A. It remains local, uncommitted, unpublished, and unreleased.

### Implemented on the isolated candidate

- P-01 explicit-TT call-cache isolation, including a permanent poisoning
  reproducer and custom Delta-T policy separation.
- P-02 exact reader/epoch/apparent/nutation provenance validation for injected
  apparent contexts and rejection of detached private fragments.
- P-03 bounded per-reader, per-thread cache ownership with concurrent public
  product equality coverage.
- P-04 narrowed cache/evaluator capability exceptions plus regressions proving
  unexpected runtime failures propagate.
- P-05 Release A: `_planet_at_impl()` owns the internal reduction entry point;
  repository bulk callers pass one opaque `_PlanetReductionWorkspace`; the
  public wrapper retains the five legacy underscored hooks for one explicit
  compatibility release, validates them, and emits `DeprecationWarning` when
  they are used.
- P-06 deterministic internal native backend/reason plans for every admission,
  route, evaluator, and batch branch, without a public schema or logging change.
- P-07 asteroid identity, deflector, and apparent-vector assembly behind one
  asteroid-owned adapter using the existing generic reduction helper, with
  exact equality against the pre-existing full-correction product.
- D-01 Cartesian/SPK prose corrected to match executable frame, handle, and
  cache behavior.
- The two major-planet Horizons fixtures now bind the oracle to the exact
  centre or system-barycentre endpoint exposed by Moira's DE441 route and send
  explicit discrete ephemeris epochs. The retired kilometre-scale residuals
  were comparator target/time errors, not planetary calculation errors.

### Verification recorded on this candidate

- Syntax gate: `py_compile` passed for the changed source and regression files.
- Focused architecture/API gate: 3 files, 122 tests passed.
- Bounded relevant gate: 11 files, 415 tests collected; 413 passed and 2 skipped
  because the optional `jplephem` development comparator is unavailable.
- Resource receipts: DE441 279/279 run with zero skip/failure; supplemental
  small-body receipt 1/1 with 2 manifests, 419 shards, and 10,471 bodies.
- Corrected external planetary oracle gate: 200/200 passed (120 apparent and
  80 geometric-vector cases). Apparent maxima were `0.277781"` and
  `0.066846 km`; geometric ICRF maxima were `0.000021829"` and `0.002937 km`.
- Post-correction local architecture/oracle gate: 65/65 passed. The request-
  shape regressions prove explicit Horizons `TLIST` and time-type contracts,
  and the target guards fail if an oracle command diverges from the active
  Moira route endpoint.
- Changed-file Ruff has no new finding. The six `E702` and one `F841` finding in
  `moira/planets.py`, plus one `E402` and one `E731` finding in
  `moira/spk_reader.py`, reproduce exactly against `HEAD`.
- `git diff --check` passes for tracked changes. Untracked plan/test whitespace
  is checked separately because Git does not include untracked files there.
- Canonical documentation and website publication metadata were refreshed from
  their owning sources. `scripts/build_website_docs_bundle.py` regenerated the
  v6.1.0 publication manifest for 25 documents and 10 releases.
- `scripts/sync_git_wiki.py` generated the four changed Git-wiki pages
  (`Home`, `PLANETARY_REDUCTION_PIPELINE`, `SERVICE_LAYER_GUIDE`, and
  `VALIDATION_ASTRONOMY`); no mirror file was hand-edited. Its final `--check`
  mode, `scripts/build_website_docs_bundle.py --check`, and
  `scripts/check_doc_consistency.py` all pass.

### Deliberately deferred boundaries

- P-05 Release B must occur only after the promised compatibility release. It
  removes the five deprecated underscored parameters and transition-only
  validation; it is not folded into Release A merely to make the final public
  signature look cleaner.
- A public release note/version statement belongs to the separately authorized
  release that carries this repair. No version, tag, package, or deployment is
  changed by this candidate.
- A full configured repository-suite attempt was started only after the focused
  gates passed, but was manually stopped after roughly 58 minutes at the user
  stop boundary. Pytest had emitted no failure output, but quiet-mode output was
  buffered and the run did not complete, so it provides no pass claim. The two
  owned launcher/child processes were explicitly terminated and verified absent.
  The completed evidence for this checkpoint remains the 415-test bounded
  relevant suite above.

This checkpoint is implementation evidence, not release authorization.

---

## Definition Of Done

This repair is complete only when:

- [ ] P-01 through P-04 are merged with focused and bounded relevant gates
      green.
- [ ] The original explicit-TT and context mismatch reproducers are permanent
      regressions.
- [ ] Reader caches have documented per-thread ownership and concurrent read
      results match serial results.
- [ ] Unexpected optimization/runtime failures are no longer swallowed by the
      repaired seams.
- [ ] P-05 completes its declared compatibility cycle; no private workspace
      fragments remain on the final public signature.
- [ ] P-06 has deterministic internal reason coverage with no public/logging
      expansion.
- [ ] P-07 either lands with exact numerical evidence or is explicitly closed
      as unnecessary because the current shared generic vector path is already
      the smaller, clearer design.
- [ ] Cartesian/SPK documentation matches runtime truth.
- [ ] Native/Python and asteroid evidence is reported with bodies, epochs,
      frame, timescale, correction regime, units, tolerances, and exclusions.
- [ ] Full-suite status, skips, unavailable comparators, and network boundary
      are truthfully recorded.
- [ ] No unrelated worktree content, kernel data, generated wiki mirror, or
      public result schema is changed.
- [ ] Commit, tag, publish, or deployment occurs only under separate explicit
      authorization.

## Bottom Line

The safest repair is not a planetary rewrite. It is a staged closure:

1. fix the two demonstrated correctness defects
2. make cache and failure ownership explicit
3. prove history, reader, thread, and backend independence
4. then simplify the internal API and diagnostics behind those tests
5. refactor asteroid ownership only if exact output equivalence remains visible

That ordering protects astronomical truth first while still producing the
cleaner architecture the audit reasonably called for.
