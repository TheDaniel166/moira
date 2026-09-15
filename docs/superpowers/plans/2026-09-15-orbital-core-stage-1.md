# Orbital Core Stage 1 Implementation Plan

> **For agentic workers:** Execute this plan task by task. Keep the three gates
> independently reviewable and revertible. Do not begin a later gate until the
> earlier gate's receipt is green.

**Date:** 2026-09-15

**Status:** Ready for staged implementation; not an implementation or release
record

**Baseline:** `origin/main` at
`29dd164c80c2a6788aa598a832eff3d4fd8e727a`

**Governing spec:**
`docs/superpowers/specs/2026-09-15-orbital-core-design.md`, SHA-256
`fba918c2755181f5d467ed957891278fb249bfde19931ecd310baf6019329a38`

**Goal:** Deliver Stage 1 of the orbital core as three separately reviewable
gates: correct every built-in SPK boundary to evaluate TDB behind preserved
TT-facing interfaces; give every selected date-frame transform one and only one
owner of ICRS frame bias; then add the strict, source-receipted
`osculating_elements` API while preserving the admitted legacy, Shadbala,
facade, and planet-only REST contracts.

**Architecture:** Python owns time policy, source selection, error semantics,
body/center admission, frame routing, element extraction, and public vessels.
The native layer remains the required dense SPK evaluator and gains a small
TT-facing adapter around explicitly TDB-facing raw evaluators. Strict orbital
calls bind one immutable reader-pool snapshot, planetary clock identity, exact
route receipt, gravity snapshot, and frame construction before extracting
elements. Legacy wrappers adapt that core without silently broadening their
body set.

**Tech stack:** Python 3.10+ (active plan baseline: 3.14.3), stdlib-only engine
runtime, C++17/pybind11 native extension, JPL DE440/DE441 SPK, sovereign
small-body manifests, FastAPI/Pydantic optional server surface, pytest, and the
project `.venv`.

---

## 1. Authorization And Release Boundary

This plan authorizes no code change by itself. When implementation is
separately authorized:

- author in an isolated feature branch or worktree rooted at the then-current
  `origin/main`;
- preserve unrelated work, including the current untracked aspect-pattern
  draft;
- use `apply_patch` for hand edits and the named repository generators for
  mechanical/generated artifacts;
- use only the project `.venv` for Python, pytest, Ruff, CMake-driven editable
  installation, and documentation tooling;
- do not add a base dependency; the runtime remains stdlib plus Moira's native
  extension;
- do not tag, publish, push a release, update deployment pins, stage, or deploy
  production without a separate explicit release authorization.

Stage 1 implementation writes `CHANGELOG.md` under `[Unreleased]`. It does not
change `pyproject.toml` or `moira.facade.__version__` from 6.6.0. Version 6.7.0
is a later release action after every release gate in section 13 passes.

### Included

1. **Gate 1A — reader clock**
   - pinned NAIF-LSK TT↔TDB conversion;
   - explicit private TDB reader/evaluator operations;
   - preserved public TT reader/evaluator contracts;
   - exact disjoint coverage and atomic source receipts;
   - pool snapshot/generation/read-lease semantics;
   - velocity-capable center chaining;
   - complete reader/evaluator consumer migration and measured shift receipt.
2. **Gate 1B — frame ownership**
   - frozen official SOFA matrix fixtures;
   - the orbital frame router;
   - a bias-inclusive equatorial precession route;
   - complete frame-consumer classification;
   - the protected chart-stack single-bias repair and measured shift receipt.
3. **Gate 1C — orbital elements**
   - error hierarchy and compatible missing-kernel relocation;
   - pinned Horizons GM policy;
   - body resolution, center admission, state routing, and provenance;
   - conic extraction and singularity semantics;
   - `osculating_elements`, legacy adapters, facade and exports;
   - the existing planet-only `/v1/orbits/elements` transport upgrade;
   - primary-source, kernel, catalog, API, and documentation evidence.

### Explicitly deferred

- Stage 2 `apsidal_passages` and migration of `distance_extremes_at` and
  `phenomena.perihelion`/`aphelion`;
- Stage 3 `planetary_nodes.geometric_node` migration;
- the source-correct Stage 4 Shadbala redesign;
- Stage 5 asteroid orbit classification;
- Stage 6 REST admission of asteroids, comets, the Moon, or EMB;
- solar-system-barycentric elements;
- arbitrary public centers or frames;
- catalog rebuilds or retrospective edits to released small-body manifests.

---

## 2. Repository-Fit Decisions

These decisions resolve the places where the design cannot be implemented by a
literal local substitution.

1. **TT compatibility is conversion, not relabelling.** Existing
   `KernelReader.position`, `position_and_velocity`, `has_segment_at`,
   `SpkReader.evaluator`, and `KernelPool.evaluator` remain TT-facing. Built-in
   readers convert once and delegate to explicitly TDB-named internals.
2. **Raw native evaluators stay TDB-facing.** Add one native composite evaluator
   that accepts TT, converts once, and delegates to a raw TDB `IEvaluator`.
   Compose raw TDB evaluators first, then wrap the final composite; never wrap
   each route leg independently.
3. **Direct native handle paths are in scope.** `moira/planets.py` currently
   calls `_segment_for`, `batch_segment_position_and_velocity`,
   `batch_segment_position_requests`, and `NativePlanetaryEvaluator` directly.
   `moira/transits_aspects.py` also loads raw segment evaluators. Each must
   either use the TT adapter or carry a value explicitly named `epoch_tdb`.
4. **Low-level receipt types live below the orbital state module.**
   `spk_reader.py` owns private frozen SPK segment/source/snapshot vessels so it
   does not import `_orbital_state.py`. `_orbital_state.py` converts those
   low-level receipts into the orbital provenance vessels returned by the
   public core.
5. **Pool mutation is snapshot-safe.** `add` increments a generation and does
   not alter an already captured ordered-reader tuple. `close` waits for active
   read leases before closing readers. A route plan uses one snapshot for clock
   identity, source selection, and every route leg.
6. **Released small-body manifests are not rewritten.** The current asteroid,
   comet, and wheel manifests identify JDTDB state sources but do not declare a
   DE440/DE441 planetary ephemeris identity. A standalone such reader therefore
   fails the strict API with `OrbitalSourceReceiptError`. The normal
   DE441-plus-small-body pool obtains its clock/gravity identity from the
   planetary reader while preserving the sovereign small-body source receipt.
7. **Frame bias is route-specific.** Correct `precession_matrix` to be
   bias-inclusive on both its `Pmat06` and long-term `Ltpb` branches. Remove an
   explicit `apply_frame_bias` only where that bias-inclusive matrix immediately
   consumes the same raw ICRF vector. Standalone fixed-frame bias uses are not
   deleted.
8. **Engine and REST admission differ intentionally.** The new engine function
   requires explicit `center` and `frame` and admits all Stage 1 bodies. The
   existing REST request remains exactly `{body, jd_ut}` and remains
   planet-only, selecting `SUN` and `J2000_ECLIPTIC` internally.
9. **The REST stages remain separated.** Upgrade the elements route's time and
   provenance models without changing the distance-extremes route's current
   response semantics. Use distinct transport time models (or an equivalently
   explicit per-envelope model) so Stage 2 is not landed accidentally.
10. **Legacy extraction and Shadbala remain stable for the same state.**
    `_keplerian_from_state` and `_rot_eq_to_ecl` keep their names, positional
    signatures, units, result fields, and numerical behavior for identical
    inputs. End-to-end Shadbala may move only by the separately measured shared
    reader-clock correction.
11. **Primary sources alone set numerical truth.** JPL Horizons/NAIF and the
    official IAU SOFA source are the authorities. PyERFA, jplephem, existing
    Moira outputs, and chart fixtures may be secondary parity or compatibility
    witnesses only.

---

## 3. Current Baseline Receipt

Re-verify this at implementation start; do not treat it as a future release
receipt.

- Repository: `C:\dev\moira`
- Branch: `main` tracking `origin/main`
- Commit: `29dd164c80c2a6788aa598a832eff3d4fd8e727a`
- Python: 3.14.3
- Imported Moira/native build: 6.6.0 /
  `C:\dev\moira\moira\_moira_native.cp314-win_amd64.pyd`
- Planetary kernel with downloads disabled:
  `C:\Users\nilad\.moira\kernels\de441.bsp`
- `tests/KNOWN_ISSUES.yml`: `known_issues: []`
- Existing unrelated/uncommitted files to preserve:
  - `docs/architecture/ASPECT_PATTERN_QUALITATIVE_SCORING_V1_DRAFT.md`
  - `docs/superpowers/specs/2026-09-15-orbital-core-design.md`
- Baseline focused slice:

  `tests/unit/test_spk_reader.py`,
  `tests/unit/test_ephemeris_time.py`,
  `tests/unit/test_orbital_elements.py`, and
  `tests/server/test_server_orbits_routes.py` pass on the installed native
  build; two optional jplephem comparisons skip because that development oracle
  is unavailable.
- Release-evidence host: `ADYTON`.
  - DE441 is installed.
  - Full comet release `moira-comets@2026.07.28.1` is installed at the normal
    user kernel root.
  - The packaged 25-body asteroid wheel
    `moira-asteroids-wheel@2026.08.14.1` is installed.
  - The full 10,025-body asteroid release
    `moira-asteroids@2026.08.12.1` is not currently discoverable. Its verified
    installation is a release blocker, not a reason to weaken or skip the
    implementation tests.

Baseline command:

```powershell
Set-Location C:\dev\moira
$env:MOIRA_TEST_MODE = "1"
$env:MOIRA_STRICT_KNOWN_ISSUES = "1"
$env:MOIRA_NO_DOWNLOAD = "1"
.\.venv\Scripts\python.exe -m pytest tests\unit\test_spk_reader.py tests\unit\test_ephemeris_time.py tests\unit\test_orbital_elements.py tests\server\test_server_orbits_routes.py -q -p no:cacheprovider
```

---

## 4. Protected Zones And Pre-Edit Ritual

Every gate touches protected astronomy or public-contract code. Before each
gate, record these six items in the implementation notes and its commit body:

1. the concrete change;
2. the minimum files to touch and unrelated work to preserve;
3. the implicated protected zones;
4. governing object, ambiguity policy, primary authority, provenance, and
   resource identity;
5. the existing and new fixtures that prove the change;
6. the smallest-to-broadest verification path, using `.\.venv`.

Protected anchors include:

- `moira/julian.py` and `moira/_ephemeris_time.py` — time scales;
- `moira/spk_reader.py`, `moira/_spk_body_kernel.py`, `moira/_kernel_paths.py`,
  `src/native/` — SPK/native/resource boundary;
- `moira/precession.py`, `moira/coordinates.py`, `moira/obliquity.py`,
  `moira/nutation_2000a.py`, `moira/corrections.py` — frames;
- `moira/planets.py`, eclipse/occultation/sky consumers, `moira/orbits.py` —
  planetary and orbital reductions;
- `moira/shadbala.py` — doctrine compatibility;
- `moira/facade.py`, `moira/_facade_predictive.py`, `moira/__init__.py`,
  `moira/predictive.py`, `moira_server/` — public and REST contracts;
- `moira/data/`, `moira/kernels/`, `PROVENANCE.md`, `tests/fixtures/`,
  `tests/artifacts/`, and `wiki/03_validation/` — scientific provenance and
  validation.

Do not hand-edit `moira.wiki/` or `website_docs/publication.json`. Regenerate
them only from their canonical inputs.

---

## 5. Primary Authority Corpus

The implementation must verify the exact downloaded source bytes before
parsing or compiling them:

| Artifact | Official owner | Bytes | SHA-256 |
|---|---|---:|---|
| `gm_Horizons.pck` | JPL Solar System Dynamics | 15,428 | `169cfed3b0927e73929d0a1b5c931f9afb5167a83b921064127ffc54a673df0c` |
| `naif0012.tls` | NASA/JPL NAIF | 5,257 | `678e32bdb5a744117a467cd9601cd6b373f0e9bc9bbde1371d5eee39600a039b` |
| `sofa_c-20231011.zip` | IAU SOFA Board | 3,686,708 | `375729d8c0a254fd27c55484de5c8b83cccef351e1ef19d9cf7f26f5485e5538` |

Rules:

- derived fixtures record source URL, retrieval UTC, byte count, source
  SHA-256, exact request, response SHA-256, and the extraction program version;
- official SOFA C routines, not PyERFA, generate the authoritative frame
  matrices;
- Horizons `VECTORS` and `ELEMENTS` records use the identical explicit JDTDB
  instant and record center, reference plane, `TIME_TYPE`, and Keplerian GM;
- calibration and holdout body/epoch sets are disjoint and frozen before
  tolerances are accepted;
- fixture generators write candidates under `tmp/` and never overwrite tracked
  fixtures automatically;
- accepting a candidate fixture is a separately reviewed source-data diff;
- no test reaches the network unless marked `external_network` and invoked in
  the isolated live-audit command.

---

## 6. File Map

### New engine files

- `moira/_orbital_errors.py` — error hierarchy and structured attributes.
- `moira/_ephemeris_gm.py` — pinned Horizons GM snapshot and identity-bound
  selection.
- `moira/_orbital_state.py` — body resolution, center admission, stable time
  binding, routed ICRF state, exact coverage, and provenance adaptation.
- `moira/_orbital_frames.py` — fixed/mean/true ecliptic frame matrices and
  provenance.

### Existing engine/native files likely modified

- `moira/julian.py`
- `moira/_ephemeris_time.py`
- `moira/spk_reader.py`
- `moira/_spk_body_kernel.py`
- `moira/precession.py`
- `moira/coordinates.py`
- `moira/planets.py`
- only the classified reader/frame consumers identified by Task 1
- `moira/orbits.py`
- `moira/shadbala.py` only if an import adapter/docstring must be adjusted;
  no doctrine or formula change
- `moira/_facade_predictive.py`
- `moira/facade.py`
- `moira/predictive.py`
- `moira/__init__.py`
- `src/native/include/evaluators.hpp`
- `src/native/include/planetary_evaluator.hpp`
- `src/native/bindings/moira_native.cpp`

### Server files

- `moira_server/models/orbits.py`
- `moira_server/services/orbits.py`
- `moira_server/errors.py`
- `moira_server/routers/orbits.py` only if type imports change; route paths and
  methods do not change

### New evidence/generator files

- `scripts/audit_orbital_stage1_consumers.py`
- `scripts/build_orbital_authority_fixtures.py`
- `scripts/build_orbital_elements_fixtures.py`
- `scripts/measure_orbital_stage1_compatibility.py`
- `docs/architecture/ORBITAL_CORE_STAGE1_CONSUMER_INVENTORY.md`
- `tests/fixtures/orbital_time_naif0012_reference.json`
- `tests/fixtures/orbital_frames_sofa_20231011_reference.json`
- `tests/fixtures/horizons_orbital_elements_calibration.json`
- `tests/fixtures/horizons_orbital_elements_holdout.json`
- `tests/fixtures/horizons_orbital_elements_catalog_holdout.json`
- `tests/artifacts/release/orbital_core_stage1_reader_clock_shift_2026-09-15.json`
- `tests/artifacts/release/orbital_core_stage1_frame_shift_2026-09-15.json`
- `tests/artifacts/release/orbital_core_stage1_validation_2026-09-15.json`

### New/extended tests

- `tests/unit/test_orbital_fixture_governance.py`
- `tests/unit/test_orbital_time_scales.py`
- `tests/unit/test_orbital_state_routes.py`
- `tests/unit/test_orbital_frames.py`
- `tests/unit/test_orbital_errors.py`
- `tests/unit/test_ephemeris_gm.py`
- `tests/unit/test_orbital_extraction.py`
- `tests/unit/test_orbital_stage1_consumer_inventory.py`
- `tests/integration/test_orbital_elements_kernels.py`
- `tests/integration/test_orbital_elements_full_catalog.py`
- `tests/integration/test_horizons_orbits.py`
- existing SPK, time, planetary-frame, orbital, Shadbala, facade/API, and server
  regression tests named in the tasks below

### Documentation

- `wiki/02_standards/ORBITAL_ELEMENTS_BACKEND_STANDARD.md`
- `wiki/03_validation/VALIDATION_ASTRONOMY.md`
- `wiki/02_standards/API_REFERENCE.md`
- `wiki/02_services/REST_API_REFERENCE.md`
- `docs/architecture/P-GAP-03_ORBITAL_ELEMENTS_TRANSPORT_DESIGN.md`
- `PROVENANCE.md`
- `CHANGELOG.md`
- generated matching pages under `moira.wiki/`
- generated `website_docs/publication.json`

---

## 7. Gate And Commit Graph

```text
Task 0 primary-source freeze + inventories
  |
  +--> Gate 1A reader clock
  |      A1 time tests -> A2 Python converter -> A3 reader capabilities
  |      -> A4 pool snapshot/chain -> A5 native evaluator
  |      -> A6 consumer migration + receipt
  |
  +--> Gate 1B frame ownership (requires 1A green)
  |      B1 SOFA fixtures/tests -> B2 frame router
  |      -> B3 chart-stack repair + receipt
  |
  +--> Gate 1C elements (requires 1A and 1B green)
         C1 errors -> C2 gravity -> C3 state routing
         -> C4 extraction -> C5 public/facade/legacy
         -> C6 REST -> C7 evidence/docs/combined gate
```

Each gate's commits may depend on earlier gates but must not mix later-gate
changes. Reverting Gate 1C must leave the corrected reader and frame contracts
intact; reverting Gate 1B must leave Gate 1A intact.

### Execution checklist

- [ ] Task 0.1 — branch from the verified baseline and preserve unrelated work.
- [ ] Task 0.2 — freeze the primary-source candidate corpus and governance.
- [ ] Task 0.3 — generate and classify the complete consumer inventory.
- [ ] Task 1A.1 — land the failing TT↔TDB contracts.
- [ ] Task 1A.2 — implement the pinned Python conversion and stable identity
      binding.
- [ ] Task 1A.3 — add exact TDB state, coverage, and receipt capabilities.
- [ ] Task 1A.4 — make `KernelPool` snapshot-safe and velocity-chain capable.
- [ ] Task 1A.5 — rebuild with the native TT-facing evaluator adapter.
- [ ] Task 1A.6 — migrate all reader consumers and approve the 1A shift receipt.
- [ ] Task 1B.1 — land the failing official SOFA frame contracts.
- [ ] Task 1B.2 — implement the orbital frame router and bias-inclusive
      precession.
- [ ] Task 1B.3 — repair classified chart-frame consumers and approve the 1B
      shift receipt.
- [ ] Task 1C.1 — implement and freeze the compatible orbital error hierarchy.
- [ ] Task 1C.2 — implement the identity-bound Horizons gravity snapshot.
- [ ] Task 1C.3 — implement strict body/center/state routing.
- [ ] Task 1C.4 — implement shape-safe element extraction and legacy helpers.
- [ ] Task 1C.5 — publish the strict function, facade method, and exports.
- [ ] Task 1C.6 — upgrade only the existing planet-elements REST adapter.
- [ ] Task 1C.7 — complete kernel, catalog, live-primary, and compatibility
      evidence.
- [ ] Task 1C.8 — update canonical documentation and generated mirrors.
- [ ] Combined gate — run section 12 and write the AGENTS.md completion receipt.
- [ ] Release readiness — satisfy section 13 before requesting any 6.7.0 action.

---

## 8. Task 0 — Freeze Inputs, Inventories, And Before-State

### Task 0.1: Create the implementation branch and preserve the current work

**Files:** no engine changes

- [ ] Record `git status --short --branch`, `git rev-parse HEAD`,
      `git rev-parse origin/main`, Python version, Moira version, native module
      path, kernel path, and `tests/KNOWN_ISSUES.yml`.
- [ ] Verify the governing spec hash exactly matches the value in this plan.
- [ ] Create an isolated branch/worktree without cleaning or overwriting the
      two untracked design documents.
- [ ] Add the reviewed spec and this plan in a documentation-only commit before
      engine work begins.

```powershell
Set-Location C:\dev\moira
git fetch origin
git status --short --branch
git rev-parse HEAD
git rev-parse origin/main
Get-FileHash -Algorithm SHA256 docs\superpowers\specs\2026-09-15-orbital-core-design.md
.\.venv\Scripts\python.exe --version
.\.venv\Scripts\python.exe -c "import moira; from moira import moira_native as mn; print(moira.__version__); print(mn.__backend_file__)"
git switch -c orbital-core-stage1
```

Stop if `origin/main` moved: rebase the plan's file/contract assumptions against
the new tree before coding. If that branch name already exists, inspect it
before choosing a new exact name; do not delete or overwrite it. Do not use
`git reset --hard` or `git clean`.

Suggested commit after review:

```powershell
git add docs\superpowers\specs\2026-09-15-orbital-core-design.md docs\superpowers\plans\2026-09-15-orbital-core-stage-1.md
git commit -m "docs: lock orbital core stage 1 design"
```

### Task 0.2: Build the primary-source candidate corpus

**Files:**

- Create: `scripts/build_orbital_authority_fixtures.py`
- Create: `scripts/build_orbital_elements_fixtures.py`
- Create: `tests/unit/test_orbital_fixture_governance.py`
- Create after review: the five fixture JSON files in section 6

**Required behavior:**

- `build_orbital_authority_fixtures.py` verifies the three exact source hashes
  before use, parses the NAIF LSK and Horizons PCK, compiles/runs a temporary
  harness against the official SOFA C source, and writes candidate time/frame/GM
  records under an explicit output directory.
- `build_orbital_elements_fixtures.py` uses `tests/tools/horizons.py` transport,
  adds an exact-JDTDB `VECTORS`/`ELEMENTS` query surface, and writes separate
  calibration, planet holdout, and catalog holdout candidates.
- Both scripts use stdlib transport and hashing. Neither imports engine results
  to construct expected values.
- The governance test rejects overlapping calibration/holdout keys, a source
  hash mismatch, absent request/response receipts, non-TDB Horizons requests,
  local paths, or an unreviewed schema version.

Run candidate generation outside pytest:

```powershell
Set-Location C:\dev\moira
$orbitalSourceRoot = 'C:\dev\moira-orbital-primary-sources'
$candidateRoot = 'C:\dev\moira\tmp\orbital-core-stage1-candidates'
Get-FileHash -Algorithm SHA256 -LiteralPath "$orbitalSourceRoot\gm_Horizons.pck"
Get-FileHash -Algorithm SHA256 -LiteralPath "$orbitalSourceRoot\naif0012.tls"
Get-FileHash -Algorithm SHA256 -LiteralPath "$orbitalSourceRoot\sofa_c-20231011.zip"
.\.venv\Scripts\python.exe scripts\build_orbital_authority_fixtures.py --gm-pck "$orbitalSourceRoot\gm_Horizons.pck" --lsk "$orbitalSourceRoot\naif0012.tls" --sofa-zip "$orbitalSourceRoot\sofa_c-20231011.zip" --output-dir "$candidateRoot\authority"
.\.venv\Scripts\python.exe scripts\build_orbital_elements_fixtures.py --output-dir "$candidateRoot\horizons"
```

Review the JSON diff, freeze gates using calibration only, then copy accepted
records into `tests/fixtures/`. Run:

```powershell
.\.venv\Scripts\python.exe -m pytest tests\unit\test_orbital_fixture_governance.py -q -p no:cacheprovider
```

Expected: PASS without network. Commit fixture generators, receipts, and
accepted fixtures together:

```powershell
git add scripts\build_orbital_authority_fixtures.py scripts\build_orbital_elements_fixtures.py tests\unit\test_orbital_fixture_governance.py tests\fixtures\orbital_time_naif0012_reference.json tests\fixtures\orbital_frames_sofa_20231011_reference.json tests\fixtures\horizons_orbital_elements_calibration.json tests\fixtures\horizons_orbital_elements_holdout.json tests\fixtures\horizons_orbital_elements_catalog_holdout.json
git commit -m "test: freeze primary orbital authority corpus"
```

### Task 0.3: Generate and classify the complete consumer inventory

**Files:**

- Create: `scripts/audit_orbital_stage1_consumers.py`
- Create: `docs/architecture/ORBITAL_CORE_STAGE1_CONSUMER_INVENTORY.md`
- Create: `tests/unit/test_orbital_stage1_consumer_inventory.py`

The audit must scan Python AST plus the native binding sources for:

- calls to `position`, `position_and_velocity`, `has_segment_at`, `coverage`,
  `evaluator`, `_segment_for`, `_load_native_evaluator`,
  `load_segment_evaluator`, `NativePlanetaryEvaluator`, and native batch segment
  methods;
- calls to `apply_frame_bias` in both Python and C++, `precession_matrix`,
  `precession_matrix_equatorial`, `icrf_to_true_ecliptic`, and manual
  precession/nutation matrix composition.

Each inventory row records file, symbol, current input scale/frame, selected
Stage 1 route, whether numerical output is expected to move, fixture/test owner,
and final disposition. At minimum classify every file listed in the governing
spec's reader/evaluator and frame-transform inventories. The guard test fails
if a discovered call site has no row or a supposedly eliminated raw bypass
returns.

```powershell
.\.venv\Scripts\python.exe scripts\audit_orbital_stage1_consumers.py --write docs\architecture\ORBITAL_CORE_STAGE1_CONSUMER_INVENTORY.md
.\.venv\Scripts\python.exe -m pytest tests\unit\test_orbital_stage1_consumer_inventory.py -q -p no:cacheprovider
```

Commit:

```powershell
git add scripts\audit_orbital_stage1_consumers.py docs\architecture\ORBITAL_CORE_STAGE1_CONSUMER_INVENTORY.md tests\unit\test_orbital_stage1_consumer_inventory.py
git commit -m "test: inventory orbital clock and frame consumers"
```

---

## 9. Gate 1A — Reader Clock

### Task 1A.1: Lock the Python TT↔TDB contract with failing tests

**Files:**

- Create: `tests/unit/test_orbital_time_scales.py`
- Modify: `tests/unit/test_ephemeris_time.py`
- Modify: `tests/unit/test_julian_delta_t.py`

Tests must require:

- the exact `naif0012.tls` constants and source hash;
- implicit `TDB - TT = K sin(M + EB sin M)` with the argument in TDB seconds
  from J2000;
- a bounded fixed-point solution with a named iteration/residual policy;
- the inverse from the same policy;
- finite/non-Boolean input and representability guards;
- offset computation before adding the single-part JD;
- forward/inverse round trips with an explicit binary64 ULP budget;
- exact frozen NAIF reference values;
- recorded, non-authoritative difference from official SOFA `Dtdb` values only
  over 1950-01-01 through 2050-12-31, bounded by 50 µs;
- stable UT1→TT→TDB identity iteration at a synthetic pool boundary;
- a private structured ephemeris-time failure when the identity oscillates or
  cannot be resolved. Task 1C.3 translates that low-level failure to the public
  `OrbitalTimeBasisError` at the strict orbital boundary.

Run before implementation:

```powershell
.\.venv\Scripts\python.exe -m pytest tests\unit\test_orbital_time_scales.py tests\unit\test_ephemeris_time.py tests\unit\test_julian_delta_t.py -q -p no:cacheprovider
```

Expected: new tests FAIL because `tt_to_tdb` is the old two-sine
approximation, no inverse exists, and stable identity binding is absent.

Commit only the failing contract:

```powershell
git add tests\unit\test_orbital_time_scales.py tests\unit\test_ephemeris_time.py tests\unit\test_julian_delta_t.py
git commit -m "test: lock the NAIF TT TDB clock boundary"
```

### Task 1A.2: Implement the pure pinned conversion and stable time binding

**Files:**

- Modify: `moira/julian.py`
- Modify: `moira/_ephemeris_time.py`

**Interfaces:**

```python
def tt_to_tdb(jd_tt: float) -> float: ...
def tdb_to_tt(jd_tdb: float) -> float: ...
```

Keep `tt_to_tdb` at its existing import path. Add the inverse to `julian.py`
without root-exporting it unless the governing spec is amended. Put
policy/version/source metadata beside the constants so orbital provenance does
not duplicate literals. Use `math.fsum` or an equivalent compensated
single-part-JD assembly and expose the seconds offset internally for the result
receipt.

Extend `_ephemeris_time.py` with one internal operation that:

1. resolves the source-owned Delta-T product;
2. forms provisional TT and TDB;
3. selects the planetary identity at the TDB epoch through a supplied immutable
   reader snapshot;
4. applies the identity's tidal-basis correction;
5. recomputes TT/TDB and proves identity stability, with a fixed iteration
   bound;
6. returns the bound identity and all numeric/source receipt fields.

Define its low-level instability/unavailable failure privately in
`_ephemeris_time.py` with structured attributes. This module must not import the
later public orbital hierarchy; `_orbital_state.py` performs that boundary
translation in Task 1C.3.

Do not import `spk_reader` from `julian.py`. Do not change public Delta-T
policy names or UTC/UT1 behavior.

Run:

```powershell
.\.venv\Scripts\python.exe -m pytest tests\unit\test_orbital_time_scales.py tests\unit\test_ephemeris_time.py tests\unit\test_julian_delta_t.py -q -p no:cacheprovider
.\.venv\Scripts\ruff.exe check moira\julian.py moira\_ephemeris_time.py tests\unit\test_orbital_time_scales.py tests\unit\test_ephemeris_time.py tests\unit\test_julian_delta_t.py --no-fix
```

Expected: PASS; no network and no kernel are needed for pure conversion tests.

Commit:

```powershell
git add moira\julian.py moira\_ephemeris_time.py
git commit -m "fix: bind ephemeris evaluation to the NAIF TDB clock"
```

### Task 1A.3: Add exact TDB state, coverage, and source-receipt capabilities

**Files:**

- Modify: `moira/spk_reader.py`
- Modify: `moira/_spk_body_kernel.py`
- Modify: `tests/unit/test_spk_reader.py`
- Create/extend: `tests/unit/test_orbital_state_routes.py`
- Modify: `tests/unit/test_spk_kernel_identity.py`

Add private capabilities to built-in readers only; do not add them to the
runtime-checkable public `KernelReader` protocol:

```python
position_tdb(center: int, target: int, epoch_tdb: float) -> Vec3
position_and_velocity_tdb(center: int, target: int, epoch_tdb: float) -> tuple[Vec3, Vec3]
has_segment_at_tdb(center: int, target: int, epoch_tdb: float) -> bool
coverage_intervals_tdb(center: int, target: int) -> tuple[tuple[float, float], ...]
evaluator_tdb(target: int, center: int = 0, *, epoch_tdb: float, epoch_end_tdb: float | None = None) -> IEvaluator
```

Use repository-consistent private names if needed, but preserve the explicit
`tdb` suffix and semantics.

Define private frozen low-level vessels in `spk_reader.py` for:

- stable kernel/source identity;
- exact segment receipt (center, target, type, inclusive TDB interval, content
  hash or manifest digest, deterministic pool index);
- routed state plus ordered legs;
- ordered pool snapshot and generation.

Requirements:

- merge only truly overlapping/adjacent intervals under an explicit endpoint
  rule; retain real gaps;
- source selection and state evaluation are atomic;
- reverse routes negate both position and velocity and identify the original
  serving segment;
- hash once at open/admission, cache the identity, and never expose an absolute
  path in public provenance;
- `small_body_readers_from_manifest` preserves verified `catalog_id`,
  `catalog_version`, manifest hash, release UTC, release integrity identity,
  and observed-arc coverage status on each opened reader;
- standalone released small-body readers without a planetary ephemeris identity
  remain numerically usable by legacy surfaces but fail strict source/clock
  admission;
- current `coverage()` retains its one-span-per-pair compatibility shape, with
  TT endpoints; strict code uses exact TDB intervals.

Public `position`, `position_and_velocity`, and `has_segment_at` convert TT once
and delegate. `has_segment` remains date-free. Tests must prove no
double-conversion using a spy raw evaluator and an epoch where TDB−TT is
non-zero.

Run:

```powershell
.\.venv\Scripts\python.exe -m pytest tests\unit\test_spk_reader.py tests\unit\test_spk_kernel_identity.py tests\unit\test_orbital_state_routes.py tests\unit\test_orbital_time_scales.py -q -p no:cacheprovider
```

Commit:

```powershell
git add moira\spk_reader.py moira\_spk_body_kernel.py tests\unit\test_spk_reader.py tests\unit\test_spk_kernel_identity.py tests\unit\test_orbital_state_routes.py
git commit -m "feat: add receipted TDB SPK capabilities"
```

### Task 1A.4: Make `KernelPool` snapshot-safe and velocity-chain capable

**Files:**

- Modify: `moira/spk_reader.py`
- Modify: `tests/unit/test_orbital_state_routes.py`
- Modify: `tests/unit/test_spk_reader.py`

Implement an immutable ordered-reader snapshot with a monotonically increasing
generation and read lease. Use a `threading.Condition` over an `RLock` or an
equivalent simple lifecycle:

- a call/plan captures readers and generation once;
- `add` publishes a new tuple and generation; existing snapshots are unchanged;
- `close` blocks new leases and waits for existing leases before closing each
  reader exactly once;
- an exception releases its lease;
- clock identity, precedence, route legs, and exact coverage all use the same
  snapshot;
- no user callback runs while the pool's mutation lock is held.

Give `KernelPool.position_and_velocity` the same deterministic direct,
reverse, and chained behavior as `position`. Add the private atomic
`position_and_velocity_tdb_with_receipt` and interval route-plan operation.

Test direct, reverse, one-hop and multi-hop chains; velocity sign/addition;
reader precedence; interleaved `add`; close waiting; exception cleanup;
disjoint coverage intersections; and an identity boundary crossed during the
provisional clock calculation.

```powershell
.\.venv\Scripts\python.exe -m pytest tests\unit\test_orbital_state_routes.py tests\unit\test_spk_reader.py -q -p no:cacheprovider
```

Commit:

```powershell
git add moira\spk_reader.py tests\unit\test_orbital_state_routes.py tests\unit\test_spk_reader.py
git commit -m "fix: freeze pooled SPK routing per computation"
```

### Task 1A.5: Add the native TT-facing evaluator adapter

**Files:**

- Modify: `src/native/include/evaluators.hpp`
- Modify: `src/native/bindings/moira_native.cpp`
- Modify: `moira/spk_reader.py`
- Modify: `moira/moira_native.py` only if its bound-surface registry requires it
- Extend: `tests/unit/test_orbital_time_scales.py`
- Extend: `tests/unit/test_spk_reader.py`
- Extend: `tests/unit/test_adversarial_native_runtime_verification.py`

Add a C++ `IEvaluator` implementation provisionally named
`TtToTdbEvaluator`. It stores one raw TDB evaluator, applies the same pinned
NAIF constants/iteration policy as Python to each TT epoch, and delegates. Bind
the converter or an inspection method needed to prove Python/native parity.

Construction rules:

- `SpkReader.evaluator_tdb` returns the raw native evaluator.
- `KernelPool.evaluator_tdb` composes raw evaluators for the selected route.
- The public evaluator converts TT interval endpoints for selection and wraps
  the final raw composite once.
- Native eclipse/star searches continue to pass TT scan epochs; only their SPK
  polynomial evaluation is converted.

Rebuild and verify:

```powershell
.\.venv\Scripts\python.exe -m pip install -e ".[dev,server]"
.\.venv\Scripts\python.exe -c "from moira import moira_native as mn; print(mn.__backend_file__)"
.\.venv\Scripts\python.exe -m pytest tests\unit\test_orbital_time_scales.py tests\unit\test_spk_reader.py tests\unit\test_adversarial_native_runtime_verification.py tests\test_native_parity.py tests\unit\test_native_import_resolution.py -q -p no:cacheprovider
```

Tests require Python/native conversion agreement, endpoint selection in TDB,
one conversion per composite evaluation, lifetime safety after pool planning,
and native/Python state parity.

Commit:

```powershell
git add src\native\include\evaluators.hpp src\native\bindings\moira_native.cpp moira\spk_reader.py moira\moira_native.py tests\unit\test_orbital_time_scales.py tests\unit\test_spk_reader.py tests\unit\test_adversarial_native_runtime_verification.py
git commit -m "feat: adapt native SPK evaluators from TT to TDB"
```

Omit `moira/moira_native.py` from `git add` if the registry does not need a
change.

### Task 1A.6: Migrate every reader/evaluator consumer and freeze the shift

**Files:**

- Modify: every classified reader/evaluator consumer that needs a semantic
  change, especially `moira/planets.py` and `moira/transits_aspects.py`
- Modify: `src/native/include/planetary_evaluator.hpp` and
  `src/native/bindings/moira_native.cpp` for the admitted native all-planets
  substrate
- Modify: `docs/architecture/ORBITAL_CORE_STAGE1_CONSUMER_INVENTORY.md`
- Create: `scripts/measure_orbital_stage1_compatibility.py`
- Create:
  `tests/artifacts/release/orbital_core_stage1_reader_clock_shift_2026-09-15.json`
- Extend: `tests/unit/test_orbital_stage1_consumer_inventory.py`
- Extend the affected focused tests

Before editing, regenerate the inventory. For each call site choose exactly one:

- public TT adapter;
- private explicit TDB call with a variable named `epoch_tdb`/`jd_tdb`;
- date-free capability;
- documented no-change.

For `planets.py`, remove every TT value passed directly to raw native handle
batch/evaluator methods. Keep TT for precession, nutation, obliquity, sidereal,
and chart cache keys. Rename the native all-planets evaluator's SPK epoch
argument to `epoch_tdb`/`jd_tdb` in C++ and the binding; its supplied
obliquity/rotation matrix remains computed at TT. Its light-time iterations
subtract days from TDB. For `transits_aspects.py`, stop constructing raw
segment evaluators from TT endpoints. Confirm `eclipse.py` and `stars.py` use
the public TT wrapper unless a fully explicit TDB-native surface is deliberately
introduced.

The compatibility script runs the pre-1A baseline commit and the candidate at
the same epochs/resources, records stable logical inputs and numeric deltas,
and emits no local absolute paths. Cover at least:

- `planet_at` and `all_planets_at`, native and Python-admitted paths;
- asteroid/comet positions;
- aspect/transit search;
- fixed-star native search;
- solar and lunar eclipse representative computations;
- lunar limb and occultation representatives;
- phase/phenomena representatives;
- Shadbala end-to-end values.

Existing outputs need not be identical: the receipt must show that movement is
consistent with the one TT→TDB correction and that no second conversion exists.
Do not update unrelated astronomical golden files merely to make them green.

Focused command:

```powershell
.\.venv\Scripts\python.exe -m pip install -e ".[dev,server]"
.\.venv\Scripts\python.exe scripts\audit_orbital_stage1_consumers.py --check docs\architecture\ORBITAL_CORE_STAGE1_CONSUMER_INVENTORY.md
.\.venv\Scripts\python.exe -m pytest tests\unit\test_orbital_stage1_consumer_inventory.py tests\unit\test_planets_architecture_invariants.py tests\unit\test_transits_aspects_native_numeric.py tests\unit\test_eclipse_clock_boundaries.py tests\unit\test_stars_heliacal.py tests\unit\test_comets.py tests\unit\test_phase2_helpers.py tests\unit\test_phenomena_regressions.py tests\unit\test_shadbala.py -q -p no:cacheprovider
```

Gate 1A command:

```powershell
.\.venv\Scripts\python.exe -m pytest tests\unit\test_orbital_fixture_governance.py tests\unit\test_orbital_time_scales.py tests\unit\test_ephemeris_time.py tests\unit\test_julian_delta_t.py tests\unit\test_spk_reader.py tests\unit\test_spk_kernel_identity.py tests\unit\test_orbital_state_routes.py tests\unit\test_orbital_stage1_consumer_inventory.py tests\unit\test_adversarial_native_runtime_verification.py tests\unit\test_planets_architecture_invariants.py tests\unit\test_transits_aspects_native_numeric.py tests\unit\test_eclipse_clock_boundaries.py tests\unit\test_stars_heliacal.py tests\unit\test_comets.py tests\unit\test_shadbala.py -q -p no:cacheprovider
```

Commit the consumer migration and receipt separately from the native adapter:

```powershell
git add moira\planets.py moira\transits_aspects.py src\native\include\planetary_evaluator.hpp src\native\bindings\moira_native.cpp docs\architecture\ORBITAL_CORE_STAGE1_CONSUMER_INVENTORY.md scripts\measure_orbital_stage1_compatibility.py tests\unit\test_orbital_stage1_consumer_inventory.py tests\unit\test_planets_architecture_invariants.py tests\unit\test_transits_aspects_native_numeric.py tests\unit\test_eclipse_clock_boundaries.py tests\unit\test_stars_heliacal.py tests\unit\test_comets.py tests\unit\test_phase2_helpers.py tests\unit\test_phenomena_regressions.py tests\unit\test_shadbala.py tests\artifacts\release\orbital_core_stage1_reader_clock_shift_2026-09-15.json
git commit -m "fix: evaluate every built-in SPK route on TDB"
```

If the regenerated inventory identifies another code consumer that requires a
change, add that exact path to both the plan's inventory row and this staging
list before committing. Do not substitute broad `git add moira` or
`git add tests`. Inspect `git diff --cached --name-only` and unstage any file
outside the classified 1A set. **Gate 1A is green only after its scoped receipt
is reviewed.**

---

## 10. Gate 1B — Frame Ownership

### Task 1B.1: Lock official SOFA matrices and boundary behavior

**Files:**

- Extend: `tests/fixtures/orbital_frames_sofa_20231011_reference.json`
- Create: `tests/unit/test_orbital_frames.py`
- Modify: `tests/unit/test_planetary_frame_contracts.py`

Write failing tests for:

- `J2000_ECLIPTIC` = passive x rotation by 84381.448 arcsec with no frame bias;
- official `iauEcm06` matrices on and inside TT JD 2415020.0–2488070.0;
- official `iauLtecm` matrices outside that closed interval, within SOFA's
  Julian epoch −200000.0 to +200000.0 range;
- `Rx(epsa + deps) * iauPnm06a` for true ecliptic of date on and inside the
  closed modern interval;
- explicit private structured range failure immediately outside the true-frame
  interval; Task 1C.1 replaces/translates this with
  `OrbitalFrameUnavailableError` before the public API is admitted;
- exact inclusion at both endpoints;
- matrix orthogonality/determinant and position/velocity same-matrix behavior;
- invariant scalar elements across frames;
- expected ~0.042 arcsec distinction between mean-of-date and fixed J2000 at
  J2000;
- `precession_matrix` matching `Pmat06` in the modern branch and `Ltpb`, not
  `Ltp`, in the long-term branch.

```powershell
.\.venv\Scripts\python.exe -m pytest tests\unit\test_orbital_frames.py tests\unit\test_planetary_frame_contracts.py -q -p no:cacheprovider
```

Expected: FAIL because the orbital router is absent and the long-term chart
precession route omits bias.

Commit tests:

```powershell
git add tests\fixtures\orbital_frames_sofa_20231011_reference.json tests\unit\test_orbital_frames.py tests\unit\test_planetary_frame_contracts.py
git commit -m "test: lock SOFA orbital frame ownership"
```

### Task 1B.2: Implement the orbital frame router and bias-inclusive precession

**Files:**

- Create: `moira/_orbital_frames.py`
- Modify: `moira/precession.py`
- Modify only if shared matrix primitives need truthful contracts:
  `moira/coordinates.py`

Define one private result vessel carrying:

- selected stable internal frame key (the public `OrbitalFrame` enum does not
  exist until Gate 1C and must not be imported back into this lower module);
- 3×3 ICRS/ICRF-to-ecliptic matrix;
- exact routine/model label;
- router branch;
- admitted TT interval or `None` for fixed J2000.

Implementation:

- fixed J2000 is the stated x rotation only;
- modern mean uses a stdlib/native-independent port of official SOFA `Ecm06`;
- long-term mean uses official `Ltecm` construction;
- modern true uses the exact `Obl06`/`Nut06a`/`Pnm06a` composition;
- the frame matrix rotates position and velocity identically; do not add a
  moving-frame derivative;
- `precession_matrix` keeps its public name but becomes bias-inclusive on both
  branches by using `Pmat06` and `Ltpb` semantics.

Until Gate 1C installs the public error hierarchy, an out-of-range true-frame
request raises one private structured `ValueError` subclass from
`_orbital_frames.py`. Task 1C.1 replaces that internal class with
`OrbitalFrameUnavailableError` and reruns the same boundary fixture. Do not
expose the temporary class from any public module.

Do not call the existing high-level chart transform as the orbital oracle. It
may share individually validated low-level routines after their SOFA parity is
proved.

Run:

```powershell
.\.venv\Scripts\python.exe -m pytest tests\unit\test_orbital_frames.py tests\unit\test_planetary_frame_contracts.py tests\integration\test_erfa_validation.py -q -p no:cacheprovider
.\.venv\Scripts\ruff.exe check moira\_orbital_frames.py moira\precession.py moira\coordinates.py tests\unit\test_orbital_frames.py tests\unit\test_planetary_frame_contracts.py --no-fix
```

The ERFA comparison is secondary parity only; the frozen official SOFA C
fixture is the admission oracle.

Commit:

```powershell
git add moira\_orbital_frames.py moira\precession.py moira\coordinates.py
git commit -m "feat: add primary-source orbital frame routing"
```

Omit untouched files from `git add`.

### Task 1B.3: Repair the protected chart stack one call site at a time

**Files:**

- Modify only classified frame consumers
- Modify: `src/native/include/planetary_evaluator.hpp` for the native
  all-planets frame path
- Modify: `docs/architecture/ORBITAL_CORE_STAGE1_CONSUMER_INVENTORY.md`
- Extend: `scripts/measure_orbital_stage1_compatibility.py`
- Create:
  `tests/artifacts/release/orbital_core_stage1_frame_shift_2026-09-15.json`
- Extend: `tests/unit/test_orbital_stage1_consumer_inventory.py`
- Extend affected frame/consumer tests

For each explicit `apply_frame_bias`:

1. identify the input frame;
2. identify the next matrix and whether it already owns bias;
3. retain the explicit bias when no later bias-inclusive ICRS matrix owns it;
4. remove it only when the same vector immediately enters the now
   bias-inclusive `precession_matrix`/`Pnm06a` route;
5. freeze the disposition in the inventory and static guard.

Apply the same classification to
`NativePlanetaryEvaluator::evaluate_all_planets_apparent_geocentric_ecliptic`:
its current explicit native `apply_frame_bias` must not precede the corrected
bias-inclusive matrix. Remove that operation only after native/Python parity
tests prove the same raw ICRF input and TT frame matrix on both paths.

At minimum inspect every spec-listed frame consumer:
`comets.py`, `coordinates.py`, `corrections.py`, `eclipse.py`,
`eclipse_besselian.py`, `galactic.py`, `lunar_eclipse_global.py`,
`lunar_limb.py`, `nodes.py`, `occultations.py`, `planetary_nodes.py`,
`planets.py`, `precession.py`, and `sky/position.py`.

Measure before/after values across modern, exact 1900/2100 boundaries, ancient,
and far-future epochs. Separate intended single-bias corrections from the
already accepted 1A clock movement. Include planetary longitude/latitude,
cartesian states, eclipse/occultation representatives, lunar limb, nodes,
galactic positions, and sky positions. Do not claim Horizons date-frame parity;
SOFA matrices are the frame authority.

```powershell
.\.venv\Scripts\python.exe -m pip install -e ".[dev,server]"
.\.venv\Scripts\python.exe scripts\audit_orbital_stage1_consumers.py --check docs\architecture\ORBITAL_CORE_STAGE1_CONSUMER_INVENTORY.md
.\.venv\Scripts\python.exe -m pytest tests\unit\test_orbital_frames.py tests\unit\test_planetary_frame_contracts.py tests\unit\test_orbital_stage1_consumer_inventory.py tests\unit\test_planetary_native_ownership_snapshot.py tests\unit\test_adversarial_native_runtime_verification.py tests\unit\test_eclipse_clock_boundaries.py tests\unit\test_eclipse_cartography.py tests\unit\test_lunar_limb_event_profile.py tests\unit\test_comets.py -q -p no:cacheprovider
```

Gate 1B command:

```powershell
.\.venv\Scripts\python.exe -m pytest tests\unit\test_orbital_frames.py tests\unit\test_planetary_frame_contracts.py tests\unit\test_orbital_stage1_consumer_inventory.py tests\unit\test_planetary_native_ownership_snapshot.py tests\unit\test_adversarial_native_runtime_verification.py tests\integration\test_erfa_validation.py tests\unit\test_eclipse_clock_boundaries.py tests\unit\test_eclipse_cartography.py tests\unit\test_lunar_limb_event_profile.py tests\unit\test_comets.py -q -p no:cacheprovider
```

Commit:

```powershell
git add moira\comets.py moira\coordinates.py moira\corrections.py moira\eclipse.py moira\eclipse_besselian.py moira\galactic.py moira\lunar_eclipse_global.py moira\lunar_limb.py moira\nodes.py moira\occultations.py moira\planetary_nodes.py moira\planets.py moira\precession.py moira\sky\position.py src\native\include\planetary_evaluator.hpp docs\architecture\ORBITAL_CORE_STAGE1_CONSUMER_INVENTORY.md scripts\measure_orbital_stage1_compatibility.py tests\unit\test_orbital_frames.py tests\unit\test_planetary_frame_contracts.py tests\unit\test_orbital_stage1_consumer_inventory.py tests\unit\test_planetary_native_ownership_snapshot.py tests\unit\test_adversarial_native_runtime_verification.py tests\unit\test_eclipse_clock_boundaries.py tests\unit\test_eclipse_cartography.py tests\unit\test_lunar_limb_event_profile.py tests\unit\test_comets.py tests\artifacts\release\orbital_core_stage1_frame_shift_2026-09-15.json
git commit -m "fix: assign frame bias exactly once"
```

Unchanged paths in that explicit list are harmless. If the regenerated
inventory adds a required consumer, update its row and add only that exact path.
Inspect `git diff --cached --name-only`; do not substitute a directory-wide
stage. **Gate 1B is green only after its SOFA and compatibility receipts are
reviewed.**

---

## 11. Gate 1C — Orbital Elements

### Task 1C.1: Implement the structured, compatible error hierarchy

**Files:**

- Create: `moira/_orbital_errors.py`
- Modify: `moira/spk_reader.py`
- Modify: `moira/_orbital_frames.py`
- Modify: `moira/facade.py`
- Create: `tests/unit/test_orbital_errors.py`
- Modify: `tests/unit/test_orbital_frames.py`
- Modify: `tests/unit/test_api_surface_adversarial_audit.py`

First capture an old 6.6.0 pickle fixture for
`moira.facade.MissingEphemerisKernelError`. Then move the class definition to
`spk_reader.py` and re-export the identical object from `facade.py` and
`moira.__init__`.

Implement the Stage 1 errors and exact compatibility bases from the spec:

- `OrbitalError`;
- `OrbitalInputError`;
- `OrbitalBodyNotFoundError`;
- `OrbitalAmbiguousBodyError`;
- `OrbitalBodyNotSupportedError`;
- `OrbitalCenterNotAllowedError`;
- `OrbitalFrameUnavailableError`;
- `OrbitalLegacyBodyNotAllowedError`;
- `OrbitalBodyNotLoadedError`;
- `OrbitalCoverageError`;
- `OrbitalKernelMissingError`;
- `OrbitalGravityModelError`;
- `OrbitalTimeBasisError`;
- `OrbitalSourceReceiptError`;
- `OrbitalStateDegenerateError`.

Do not add the Stage 2 search/passage errors yet. Freeze class declarations,
MRO, cooperative constructors, `args`, attributes, messages, unquoted
`KeyError.__str__` behavior, pickle round trips, old facade pickle loading, and
all promised import identities. Every structured detail is a stable scalar or
tuple suitable for allowlisted REST serialization.

Replace the private Gate 1B range failure with
`OrbitalFrameUnavailableError` at this point. Keep the low-level
`_ephemeris_time.py` failure private; Task 1C.3 maps it to
`OrbitalTimeBasisError` at the public orbital boundary.

```powershell
.\.venv\Scripts\python.exe -m pytest tests\unit\test_orbital_errors.py tests\unit\test_orbital_frames.py tests\unit\test_api_surface_adversarial_audit.py -q -p no:cacheprovider
```

Commit:

```powershell
git add moira\_orbital_errors.py moira\spk_reader.py moira\_orbital_frames.py moira\facade.py tests\unit\test_orbital_errors.py tests\unit\test_orbital_frames.py tests\unit\test_api_surface_adversarial_audit.py
git commit -m "feat: add compatible orbital error semantics"
```

### Task 1C.2: Add the pinned Horizons gravity policy

**Files:**

- Create: `moira/_ephemeris_gm.py`
- Create: `tests/unit/test_ephemeris_gm.py`
- Use: accepted GM/source records in the calibration fixture

Encode the exact `gm_Horizons.pck` snapshot, source URL/date/bytes/hash, and
selection rules:

- Sun plus target body for Mercury, Venus, and Earth;
- Sun plus the served planetary-system barycenter for Mars through Pluto;
- Sun plus EMB for the Earth–Moon barycenter;
- Earth plus Moon for the Moon-about-Earth pair;
- Sun alone for massless asteroid/comet elements.

Bind the snapshot only to content-derived DE440 or DE441 identities. Filename
inference is forbidden. The strict core raises `OrbitalGravityModelError` for
another or unidentified planetary identity. The separately named
`LEGACY_ORBITS_V1` policy exists only for a third-party reader accepted by the
old wrapper and never claims Horizons parity.

Test every rule, every component NAIF ID, units conversion from km³/s² to
km³/day², source receipt, identity admission, and unknown identity.

```powershell
.\.venv\Scripts\python.exe -m pytest tests\unit\test_ephemeris_gm.py tests\unit\test_orbital_fixture_governance.py -q -p no:cacheprovider
```

Commit:

```powershell
git add moira\_ephemeris_gm.py tests\unit\test_ephemeris_gm.py
git commit -m "feat: bind orbital gravity to the Horizons snapshot"
```

### Task 1C.3: Resolve bodies and construct one strict routed state

**Files:**

- Create: `moira/_orbital_state.py`
- Modify: `moira/small_body_identity.py` only if an adapter is required; do not
  alter catalog identities
- Extend: `tests/unit/test_orbital_state_routes.py`
- Extend: `tests/unit/test_orbital_errors.py`
- Modify: `tests/conftest.py` only for a typed orbital fixture

Add frozen `OrbitalBodyIdentity` and private provenance/state vessels. The
identity may be physically defined in this lower module to avoid an import
cycle, then re-exported publicly from `moira.orbits` in Task 1C.5. Resolve:

- Mercury/Venus/Earth body IDs 199/299/399;
- EMB ID 3 and aliases;
- Mars through Pluto system barycenters IDs 4–9;
- Moon ID 301;
- asteroid/comet names, aliases, qualified names, and admitted NAIF IDs through
  `small_body_identity`.

Reject `bool` as an integer ID. Distinguish malformed input, unknown identity,
ambiguous small-body name, known non-orbital point, catalogued-but-not-loaded
body, and date outside exact route coverage.

Implement the one-call state flow:

1. validate the raw body and a normalized internal center key (the public enum
   validation remains owned by `moira.orbits` in Tasks 1C.4–1C.5);
2. resolve body and allowed center;
3. bind explicit reader or `get_active_reader()` without triggering a download;
4. lease one pool snapshot;
5. bind UT1/TT/TDB and planetary identity to that snapshot;
6. select gravity;
7. plan and evaluate the exact state route in TDB;
8. translate low-level failures to one `OrbitalError`;
9. return km/km-day ICRF state, exact common coverage, and a path-free receipt.

Route rules:

- planets/EMB about Sun: target barycentric route minus SSB→Sun;
- Earth about Sun: Earth body route minus SSB→Sun;
- Moon about Earth: EMB→Moon minus EMB→Earth;
- small body about Sun: direct sovereign segment, or chain its actual segment
  center through the leased planetary snapshot.

Tests include direct, reverse, chained, ambiguous, unknown, unsupported,
not-loaded, gap, pool priority, unidentified standalone third-party reader,
standalone released small-body reader without integration identity, and normal
DE441-plus-small-body pooled success.

```powershell
.\.venv\Scripts\python.exe -m pytest tests\unit\test_orbital_state_routes.py tests\unit\test_orbital_errors.py tests\unit\test_small_body_packaged_manifest_receipts.py tests\unit\test_asteroid_identity_catalog.py tests\unit\test_comet_identity_catalog.py -q -p no:cacheprovider
```

Commit:

```powershell
git add moira\_orbital_state.py moira\small_body_identity.py tests\unit\test_orbital_state_routes.py tests\unit\test_orbital_errors.py tests\conftest.py
git commit -m "feat: route orbital states with exact source receipts"
```

Omit untouched files from `git add`.

### Task 1C.4: Implement shape-safe element extraction

**Files:**

- Rewrite: `moira/orbits.py`
- Create: `tests/unit/test_orbital_extraction.py`
- Modify: `tests/unit/test_orbital_elements.py`
- Modify: `tests/unit/test_distance_extremes.py` only to preserve Stage 1
  compatibility; no passage migration
- Modify: `tests/unit/test_shadbala.py`

Add the Stage 1 enums and frozen slotted vessels:

- `OrbitalCenter`, `OrbitalFrame`, `OrbitShape`, `OrbitalBodyKind`,
  `UndefinedElementReason`;
- `UndefinedElement`, `OsculatingElements`, and its nested provenance vessels.

Implement the spec's scale-free circular/equatorial/rectilinear classification,
elliptic/parabolic/hyperbolic extraction, undefined-element receipts, signed
hyperbolic anomaly, Barker variable for parabolic time of pericenter, nearest
elliptic periapsis branch with the exact 180° tie rule, pericenter vector
longitude/latitude, and explicit optional fields. Do not return 0 or infinity
as a placeholder for an undefined value.

Calibrate singularity thresholds only from analytic floating-point behavior and
the calibration corpus; freeze them before running holdout. Tests cover:

- exact circular, equatorial prograde/retrograde, parabolic, hyperbolic, and
  simultaneous singularities;
- near-boundary values on both sides;
- zero position, zero velocity, and dimensionlessly rectilinear state errors;
- frame invariants;
- closed-form recovery from constructed elements;
- Horizons calibration, then untouched holdout;
- analytic conic time-of-pericenter fields in TDB and TT.

Preserve:

- `KeplerianElements` and `DistanceExtremes` public fields;
- `_rot_eq_to_ecl(x, y, z, obliquity_deg)`;
- `_keplerian_from_state(r, v, mu, name, epoch_jd)`;
- identical legacy helper output for the same state;
- the current Stage 1 behavior of `distance_extremes_at`;
- complete pre-Stage-1 Shadbala output for frozen input states.

```powershell
.\.venv\Scripts\python.exe -m pytest tests\unit\test_orbital_extraction.py tests\unit\test_orbital_elements.py tests\unit\test_distance_extremes.py tests\unit\test_shadbala.py -q -p no:cacheprovider
```

Commit:

```powershell
git add moira\orbits.py tests\unit\test_orbital_extraction.py tests\unit\test_orbital_elements.py tests\unit\test_distance_extremes.py tests\unit\test_shadbala.py
git commit -m "feat: extract explicit osculating conics"
```

### Task 1C.5: Add the strict public API, legacy adapter, facade, and exports

**Files:**

- Modify: `moira/orbits.py`
- Modify: `moira/_facade_predictive.py`
- Modify: `moira/facade.py`
- Modify: `moira/predictive.py`
- Modify: `moira/__init__.py`
- Modify: `tests/unit/test_api_surface_adversarial_audit.py`
- Extend: `tests/unit/test_orbital_elements.py`
- Add/extend the existing facade contract test selected by repository search

Implement:

```python
def osculating_elements(
    body: str | int,
    jd_ut: float,
    *,
    center: OrbitalCenter,
    frame: OrbitalFrame,
    reader: KernelReader | None = None,
) -> OsculatingElements: ...
```

`center` and `frame` are required keywords with no defaults. Accept enum members
or exact string values under the spec's validation rules. Resolve `reader=None`
through the active reader context and raise `OrbitalKernelMissingError` when
none exists.

Add `Moira.osculating_elements` to `PredictiveFacadeMixin`, passing
`self._reader` explicitly. Freeze `inspect.signature` and prove direct/facade
result equality and reader ownership.

Adapt `orbital_elements_at(body, jd_ut, reader)`:

- same positional signature and planet list;
- internally selects `SUN` and `J2000_ECLIPTIC`;
- returns `KeplerianElements`;
- sets `epoch_jd` to TT, not input UT1;
- uses pinned Horizons gravity for DE440/441;
- permits a historical-protocol third-party reader through
  `LEGACY_ORBITS_V1` without claiming strict provenance;
- produces the spec's compatible typed errors.

Export all Stage 1 enums, vessels, function, and errors from `moira.orbits`,
`moira.predictive`, `moira.facade`, and root `moira` exactly as specified.
Do not export private route/GM/frame helpers or Stage 2/5 names.

```powershell
.\.venv\Scripts\python.exe -m pytest tests\unit\test_orbital_elements.py tests\unit\test_orbital_errors.py tests\unit\test_api_surface_adversarial_audit.py -q -p no:cacheprovider
```

Commit:

```powershell
git add moira\orbits.py moira\_facade_predictive.py moira\facade.py moira\predictive.py moira\__init__.py tests\unit\test_orbital_elements.py tests\unit\test_orbital_errors.py tests\unit\test_api_surface_adversarial_audit.py
git commit -m "feat: publish the strict osculating elements API"
```

### Task 1C.6: Upgrade only the existing elements REST adapter

**Files:**

- Modify: `moira_server/models/orbits.py`
- Modify: `moira_server/services/orbits.py`
- Modify: `moira_server/errors.py`
- Modify only if imports require: `moira_server/routers/orbits.py`
- Modify: `tests/server/test_server_orbits_routes.py`
- Create: `tests/server/test_error_mapping.py`

Keep the request and admission boundary:

- `POST /v1/orbits/elements`;
- body and finite `jd_ut` only;
- `ADMITTED_ORBIT_BODIES` remains Mercury–Pluto plus Earth;
- extra `center` or `frame` remains 422;
- service selects `SUN`/`J2000_ECLIPTIC` and uses the engine-owned reader;
- no small-body REST admission.

Preserve the existing element result field names while correcting
`epoch_jd` to TT. The elements envelope gains a truthful time block:

- `input_time_scale = "UT1_JD"`;
- `state_evaluation_scale = "TDB_JD"`;
- `output_time_scale = "TT_JD"`;
- numeric input UT1, epoch TT, epoch TDB, Delta-T seconds, and TDB−TT seconds;
- conversion policy/version/source receipt.

Provenance gains the gravity rule, GM and units, frame construction, and stable
source/segment receipt. Serialize only allowlisted public fields; no local
paths, raw reprs, tracebacks, or kernel handles.

Do not change `/v1/orbits/distance-extremes` time/output semantics in this
stage. Split the time response model if necessary to prevent the shared current
`OrbitTimeResponse` from silently upgrading that route ahead of Stage 2.

Register specific orbital handlers before generic `ValueError`/`KeyError`
handlers and assert the full mapping table from the spec. Computation failures
are logged with request ID and return no internal detail; configuration/source
failures use 503; input/coverage/legacy admission use the specified 422 codes.

```powershell
.\.venv\Scripts\python.exe -m pytest tests\server\test_server_orbits_routes.py tests\server\test_error_mapping.py -q -p no:cacheprovider
```

Commit:

```powershell
git add moira_server\models\orbits.py moira_server\services\orbits.py moira_server\errors.py moira_server\routers\orbits.py tests\server\test_server_orbits_routes.py tests\server\test_error_mapping.py
git commit -m "feat: expose receipted planet elements over REST"
```

Omit `routers/orbits.py` if untouched.

### Task 1C.7: Prove kernel, catalog, live-primary, and compatibility behavior

**Files:**

- Create: `tests/integration/test_orbital_elements_kernels.py`
- Create: `tests/integration/test_orbital_elements_full_catalog.py`
- Extend: `tests/integration/test_horizons_orbits.py`
- Extend: `scripts/measure_orbital_stage1_compatibility.py`
- Create:
  `tests/artifacts/release/orbital_core_stage1_validation_2026-09-15.json`

Layer 2 kernel tests cover:

- every admitted planet, Earth, EMB, and Moon center pairing;
- all packaged 25 small bodies through a DE441 pool;
- exact TDB state and TT wrapper parity;
- source/gravity/time/frame receipts;
- segment seams, gaps, reverse/chained routes, and boundary epochs;
- frozen Horizons holdout values at identical JDTDB instants.

Layer 3 full-catalog tests cover every installed asteroid and comet for:

- deterministic resolution;
- finite state and velocity at a representative covered epoch;
- non-empty exact coverage intervals;
- exact manifest/shard/source receipt;
- successful Sun-centered J2000 element extraction through a DE441 pool.

Detailed numerical catalog holdouts include the spec's named representative
comets, observed-arc asteroids, Hektor, Atira, and orbit-shape edge cases.

Layer 4 live tests query official JPL Horizons only. They regenerate candidates,
compare source/API/GM drift with the reviewed frozen corpus, and never rewrite
accepted fixtures. A drift report fails release review; it does not
automatically widen gates.

Kernel/local command:

```powershell
$env:MOIRA_TEST_MODE = "1"
$env:MOIRA_STRICT_KNOWN_ISSUES = "1"
$env:MOIRA_NO_DOWNLOAD = "1"
.\.venv\Scripts\python.exe -m pytest tests\integration\test_orbital_elements_kernels.py tests\unit\test_orbital_elements.py tests\unit\test_orbital_extraction.py -q -p no:cacheprovider
```

Full-catalog release-host preflight on `ADYTON`:

```powershell
$orbitalKernelRoot = 'C:\Users\nilad\.moira\kernels'
.\.venv\Scripts\python.exe -m moira.small_body_catalog_release verify "$orbitalKernelRoot\asteroids"
.\.venv\Scripts\python.exe -m moira.small_body_catalog_release verify "$orbitalKernelRoot\comets"
$env:MOIRA_KERNELS_DIR = $orbitalKernelRoot
.\.venv\Scripts\python.exe -m pytest tests\integration\test_orbital_elements_full_catalog.py -q -p no:cacheprovider
```

If the full asteroid directory is absent, record `NOT RUN — full
moira-asteroids@2026.08.12.1 release not installed`. Implementation review may
continue, but section 13's release gate remains blocked.

Isolated live-primary audit:

```powershell
.\.venv\Scripts\python.exe -m pytest -m "external_network" --run-external-network tests\integration\test_horizons_orbits.py -q -p no:cacheprovider
```

Commit after reviewed receipts:

```powershell
git add tests\integration\test_orbital_elements_kernels.py tests\integration\test_orbital_elements_full_catalog.py tests\integration\test_horizons_orbits.py scripts\measure_orbital_stage1_compatibility.py tests\artifacts\release\orbital_core_stage1_validation_2026-09-15.json
git commit -m "test: validate orbital core stage 1"
```

### Task 1C.8: Update canonical documentation and generated mirrors

**Files:** documentation list in section 6

Document:

- body/center/frame admission;
- exact time scales and conversion source;
- gravity rules and source hash;
- shape and undefined-field semantics;
- state/source receipts and exact coverage;
- new API/facade signatures and legacy behavior;
- planet-only REST admission and error mapping;
- measured planet, chart, eclipse, and Shadbala compatibility shifts;
- every deferred stage and the full-catalog release blocker.

Correct the older P-GAP transport document's `UT_JD`/`TT_internal` claims. Make
the Stage 1/Stage 2 split explicit so distance-extremes is not documented as
already migrated. Write only canonical `wiki/` sources, then generate:

```powershell
.\.venv\Scripts\python.exe scripts\sync_git_wiki.py
.\.venv\Scripts\python.exe scripts\build_website_docs_bundle.py
.\.venv\Scripts\python.exe scripts\check_doc_consistency.py
.\.venv\Scripts\python.exe scripts\sync_git_wiki.py --check
.\.venv\Scripts\python.exe scripts\build_website_docs_bundle.py --check
```

Commit:

```powershell
git add wiki\02_standards\ORBITAL_ELEMENTS_BACKEND_STANDARD.md wiki\03_validation\VALIDATION_ASTRONOMY.md wiki\02_standards\API_REFERENCE.md wiki\02_services\REST_API_REFERENCE.md docs\architecture\P-GAP-03_ORBITAL_ELEMENTS_TRANSPORT_DESIGN.md PROVENANCE.md CHANGELOG.md moira.wiki\ORBITAL_ELEMENTS_BACKEND_STANDARD.md moira.wiki\VALIDATION_ASTRONOMY.md moira.wiki\API_REFERENCE.md moira.wiki\REST_API_REFERENCE.md website_docs\publication.json
git commit -m "docs: publish orbital core stage 1 contracts"
```

Verify those four generated flat mirror files changed and do not stage unrelated
documentation.

---

## 12. Combined Stage 1 Verification

Run from a clean candidate worktree with the newly rebuilt native extension:

```powershell
Set-Location C:\dev\moira
$env:MOIRA_TEST_MODE = "1"
$env:MOIRA_STRICT_KNOWN_ISSUES = "1"
$env:MOIRA_NO_DOWNLOAD = "1"
.\.venv\Scripts\python.exe -m pip install -e ".[dev,server]"
.\.venv\Scripts\python.exe -c "import moira; from moira import moira_native as mn; print(moira.__version__); print(mn.__backend_file__)"
.\.venv\Scripts\python.exe -m pytest tests\unit\test_orbital_fixture_governance.py tests\unit\test_orbital_time_scales.py tests\unit\test_ephemeris_time.py tests\unit\test_julian_delta_t.py tests\unit\test_spk_reader.py tests\unit\test_spk_kernel_identity.py tests\unit\test_orbital_state_routes.py tests\unit\test_orbital_frames.py tests\unit\test_planetary_frame_contracts.py tests\unit\test_orbital_errors.py tests\unit\test_ephemeris_gm.py tests\unit\test_orbital_extraction.py tests\unit\test_orbital_elements.py tests\unit\test_distance_extremes.py tests\unit\test_shadbala.py tests\unit\test_orbital_stage1_consumer_inventory.py tests\unit\test_api_surface_adversarial_audit.py tests\integration\test_orbital_elements_kernels.py tests\server\test_server_orbits_routes.py tests\server\test_error_mapping.py -q -p no:cacheprovider
.\.venv\Scripts\python.exe -m pytest tests\test_native_parity.py tests\test_native_sidereal_phase1.py tests\unit\test_native_import_resolution.py tests\unit\test_native_nutation_2000a.py tests\unit\test_adversarial_native_runtime_verification.py -q -p no:cacheprovider
.\.venv\Scripts\python.exe -m pytest -m "not external_network" -p no:cacheprovider
.\.venv\Scripts\python.exe scripts\check_doc_consistency.py
.\.venv\Scripts\python.exe scripts\sync_git_wiki.py --check
.\.venv\Scripts\python.exe scripts\build_website_docs_bundle.py --check
.\.venv\Scripts\ruff.exe check moira\julian.py moira\_ephemeris_time.py moira\spk_reader.py moira\_spk_body_kernel.py moira\_orbital_errors.py moira\_ephemeris_gm.py moira\_orbital_state.py moira\_orbital_frames.py moira\precession.py moira\coordinates.py moira\orbits.py moira\_facade_predictive.py moira\facade.py moira\predictive.py moira\__init__.py moira_server\models\orbits.py moira_server\services\orbits.py moira_server\errors.py tests\unit\test_orbital_fixture_governance.py tests\unit\test_orbital_time_scales.py tests\unit\test_orbital_state_routes.py tests\unit\test_orbital_frames.py tests\unit\test_orbital_errors.py tests\unit\test_ephemeris_gm.py tests\unit\test_orbital_extraction.py tests\integration\test_orbital_elements_kernels.py tests\integration\test_orbital_elements_full_catalog.py scripts\audit_orbital_stage1_consumers.py scripts\build_orbital_authority_fixtures.py scripts\build_orbital_elements_fixtures.py scripts\measure_orbital_stage1_compatibility.py --no-fix
git diff --check
git status --short --branch
```

Acceptance:

- all targeted and non-network tests pass;
- optional skips are itemized with reason and are not new failures;
- repository-wide Ruff debt is not silently folded into the gate; changed-file
  Ruff is green;
- consumer inventory has no unclassified or forbidden bypass;
- Gate 1A and 1B receipts remain unchanged and green after 1C;
- the Shadbala same-state adapter surface is exact, and any end-to-end movement
  equals the reviewed clock receipt only;
- no absolute path appears in public result/REST provenance;
- no `KNOWN_ISSUES.yml` entry masks this change;
- no version, tag, publish, staging, or production mutation occurred.

---

## 13. Release Readiness Gate — Not Part Of Implementation Authorization

Do not call Stage 1 releasable until all of these are true:

- combined section 12 verification is green on the exact candidate commit;
- live JPL Horizons audit is green on that commit;
- `ADYTON` (or a newly recorded replacement release host) has verified
  `moira-asteroids@2026.08.12.1` and `moira-comets@2026.07.28.1` release
  directories;
- the inventory-wide full-catalog test is green;
- all three release receipts record commit, Python/native identity, DE441
  identity, manifest identities/hashes, commands, counts, skips, and no-download
  status;
- primary fixture candidates show no unexplained source drift;
- generated docs are in sync;
- the AGENTS.md completion receipt is written;
- a human has reviewed intended numerical shifts and frozen tolerances;
- there is separate explicit authorization to version/tag/publish.

Only then may a separate release task:

1. set 6.7.0 in the repository's version owners;
2. rerun exact-artifact release tests;
3. commit and push;
4. create/push the tag that drives PyPI;
5. verify the published wheel/native identity;
6. update the guarded box pin through staging;
7. promote the exact staged artifact to production;
8. verify service health, artifact identity, and public endpoints.

A local wheel, a green build, or a pushed branch is not a production release.

---

## 14. Stop Conditions

Stop and return to design/review if:

- the governing spec hash changes;
- an official source artifact hash differs;
- calibration and holdout records overlap;
- a holdout fails and the proposed response is to widen a tolerance;
- any built-in raw SPK path still consumes a TT-labelled scalar;
- a TT-facing evaluator converts more than once;
- a pool call re-reads mutable order after taking its snapshot;
- a source receipt needs a local path or guessed DE identity;
- a released small-body manifest would need retrospective editing;
- frame construction mixes explicit bias with a bias-inclusive matrix;
- a true-date result outside the admitted interval would require a hybrid model;
- the strict API needs a third-party legacy reader without a TDB/source
  capability;
- the old `MissingEphemerisKernelError` pickle/import identity breaks;
- same-state Shadbala adapter output moves;
- Stage 2, 3, 4, 5, or 6 behavior is required to make Stage 1 tests pass;
- the full asteroid release or live JPL evidence is unavailable when a 6.7.0
  tag is requested.

---

## 15. Definition Of Done

Stage 1 implementation is done—not released—when:

- Gate 1A proves TT-facing compatibility over exactly-once TDB evaluation,
  exact coverage, atomic receipts, and stable pool snapshots;
- Gate 1B proves every selected matrix against official SOFA and every
  protected chart route owns bias exactly once;
- Gate 1C returns source-receipted, shape-safe osculating elements for every
  admitted engine body/center pair;
- legacy planet functions, helper imports, Shadbala same-state math, facade, and
  planet-only REST admission are preserved under their documented corrections;
- every public failure is a structured `OrbitalError` and REST maps it
  intentionally;
- calibration, holdout, packaged-kernel, full-catalog, and live-primary
  evidence are clearly separated;
- the three gate receipts and final completion receipt list exact commands,
  results, skips, resources, authority, and intended numerical changes;
- deferred stages remain deferred;
- no release or deployment action has been taken.
