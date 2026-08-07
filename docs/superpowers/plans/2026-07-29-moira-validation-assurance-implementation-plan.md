# Moira Validation Harness and Assurance System — Implementation Plan

**Plan date:** 2026-07-29
**Implementation start:** 2026-07-30
**Status:** required first tranche implemented and verified; later phases remain planned
**Repository:** `C:\Users\nilad\OneDrive\Desktop\Moira C++`

> **Execution rule:** implement this plan in order. Do not use the later
> assurance work to avoid first repairing the harness paths that can currently
> create false-green results.

## 1. Goal

Turn Moira's test infrastructure from a large collection of fixtures and hooks
into a fail-closed validation system that can answer four separate questions:

1. Did the selected tests execute under the declared runtime and resource
   policy?
2. What computational or doctrinal claim did each validation test exercise?
3. What class of evidence supports that claim?
4. Can the suite detect plausible wrong answers rather than merely execute the
   relevant lines?

The intended end state is a thin `tests/conftest.py`, independently tested
pytest policy plugins, explicit resource and network contracts, controller-owned
run receipts, and dedicated metamorphic, mutation, fuzz, and chaos lanes.

This is a testing-infrastructure program. It does not authorize changes to
engine mathematics, public result semantics, native computation, oracle
corpora, scientific tolerances, or admitted golden values.

## 2. Completion boundary

This program is complete only when:

- invalid harness configuration fails before collection with a useful
  `pytest.UsageError`;
- kernel-free tests do not open a planetary kernel;
- resource-dependent tests run only against a matching capability receipt or
  produce an explicit missing-capability record;
- loopback and external network access are distinct policies;
- external network execution requires both a marker and explicit command-line
  permission;
- `serial` means actual non-concurrent execution;
- setup, call, and teardown failures and durations are preserved;
- xdist produces the same semantic receipt as serial execution for an admitted
  deterministic canary corpus;
- ordinary pytest cannot rewrite snapshots, goldens, oracle fixtures, or
  admitted evidence;
- transient diagnostics never enter the protected scientific-evidence tree;
- exact failed node IDs can be replayed through the project `.venv`;
- validation tests can declare evidence class, authority, semantics, resources,
  units, tolerance, and exclusions;
- protected products have a visible assurance matrix showing which evidence
  classes are present or absent;
- critical curated scientific mutants are killed by their intended tests;
- every completed phase has a verification receipt containing exact commands,
  outcomes, skips, prerequisites, and unresolved gaps.

Passing tests alone do not satisfy this completion boundary.

## 3. Reading rule and authority

Read and apply these sources before implementation:

- `AGENTS.md` — binding runtime, protected-zone, authority, validation, and
  completion laws.
- `wiki/03_release/PROTECTED_ZONE_REGRESSION_DISCIPLINE.md` — minimum protected
  regression discipline.
- `wiki/03_validation/VALIDATION_ASTRONOMY.md` — current astronomy validation
  claims; verify every claim against current tests before reusing it.
- `wiki/03_validation/VALIDATION_ASTROLOGY.md` — current astrology validation
  claims and source/invariant boundaries.
- `wiki/03_validation/KILLER_VALIDATION_INDEX.md` — existing high-value
  validation surfaces.
- `wiki/03_validation/NATIVE_DAF_READER_ADVERSARIAL_VALIDATION.md` — current
  synthetic native-reader attack surface.
- `wiki/03_validation/RESOURCE_BINDING_LEDGER_2026-05-04.md` — historical
  resource evidence, not proof of current process RSS, handle, or concurrency
  behavior.
- `docs/threading.md` — current reader lifecycle, singleton, concurrency, and
  GIL contract.
- `docs/architecture/MOIRA_PYTHON_GOVERNED_NATIVE_STRENGTHENING.md` — native
  admission and parity boundary.
- `.github/workflows/release-hardening.yml` and
  `.github/workflows/release-acceptance.yml` — current CI consumers.

When documents and executable behavior disagree, record the drift and follow
current code plus `AGENTS.md`. Do not silently preserve a stale validation
claim.

## 4. Relationship to earlier plans

### 4.1 Superseded plan

This plan supersedes:

- `docs/superpowers/plans/2026-05-04-conftest-fixture-adoption.md`

Do not execute that plan as written. It proposes broad adoption of
`moira_engine`, `moira_approx`, `reference_epoch`, and `any_house_system`, but
the 2026-07-29 audit established that:

- `moira_engine` participates in unnecessary kernel initialization and an
  additional reader lifecycle;
- `moira_approx` does not model circular longitude or explicit distance units;
- `reference_epoch` contains materially incorrect identities;
- `any_house_system` converts broad import failures into empty-parameter skips
  and currently has no discovered consumers.

The old plan may be used only as a historical inventory of candidate callers.
No fixture migration may occur until the fixture itself has a proved contract.

### 4.2 Qualified historical design

The following remain useful attack inventories but are not implementation
authority for this program:

- `docs/superpowers/specs/2026-05-20-adversarial-singularity-tests-design.md`
- `docs/superpowers/plans/2026-05-20-adversarial-singularity-tests.md`

In particular, do not inherit these unsafe rules:

- that every first-run adversarial failure is automatically an engine defect;
- that all numeric comparisons should use the generic `moira_approx` fixture;
- that all engine-facing tests should use an ambient session engine;
- that a snapshot witness becomes canonical truth.

Every adversarial relation must first prove its governing object, lawful domain,
ambiguity policy, conditioning, and tolerance.

## 5. Protected-zone declaration

The program directly implicates these protected anchors:

- `tests/conftest.py`
- `tests/KNOWN_ISSUES.yml`
- `tests/oracle/`
- `tests/golden/`
- `tests/snapshots/`
- `tests/artifacts/oracle/`
- `tests/artifacts/benchmarks/`
- `pyproject.toml`
- `.github/workflows/release-hardening.yml`
- `.github/workflows/release-acceptance.yml`

Later native fuzz and sanitizer phases may implicate:

- `src/native/`
- `CMakeLists.txt`
- `setup.py`
- `moira/spk_reader.py`
- `moira/_spk_body_kernel.py`
- `moira/_kernel_paths.py`
- `moira/daf_writer.py`

Before each phase:

1. state the requested behavior change;
2. list the minimum files;
3. re-run `git status --short --branch`;
4. identify overlapping user changes;
5. name the governing object, ambiguity policy, authority, provenance, and
   required resources;
6. run the smallest characterization test before editing;
7. stop if the work requires a protected engine or native change not explicitly
   included in that phase.

No failing test created by this program grants implicit authority to repair the
engine in the same change.

## 6. Current verified baseline

The 2026-07-29 audit established the following current behavior:

- `tests/conftest.py` is 905 lines and combines governance, resource discovery,
  network policy, determinism, fixtures, coverage, budgets, artifacts, rerun
  generation, and xdist behavior.
- `.venv` uses Python 3.14.3.
- `tests/KNOWN_ISSUES.yml` currently contains `known_issues: []`.
- the local no-download kernel resolver finds DE441;
- the native import resolves to the current CPython 3.14 extension;
- `tests/unit/test_conftest_smoke.py` passes eight cases but does not exercise
  most harness policy;
- a trivial `jd_j2000` test incurred approximately 15.78 seconds of setup;
- a `moira_engine` smoke incurred approximately 30.53 seconds of setup;
- a Hypothesis test configured for 50 test-mode examples executed 100 examples;
- 1,320 of 1,463 collected server cases were excluded by
  `-m "not network"` because loopback and external egress share one marker;
- a natural unquoted YAML expiry becomes `datetime.date` and crashes current
  parsing;
- malformed known-issue shapes and path escapes can pass silently;
- the value labelled J2100 converts to calendar year 3000;
- `serial` and `parallel` markers do not affect xdist scheduling;
- worker artifacts are searched from the wrong directory;
- worker coverage writes are not safely combined;
- the generated PowerShell rerun assignment is syntactically invalid and uses
  the wrong interpreter;
- call-only budgets omit the dominant setup cost and can overwrite the original
  failure;
- transient artifacts can be written into the protected repository artifact
  tree;
- ordinary environment variables can rewrite snapshots and goldens.

These observations are the characterization baseline, not permanent expected
behavior.

## 7. Assurance laws

### 7.1 Evidence classes remain distinct

The harness recognizes these evidence classes:

| Class | Meaning | Cannot establish |
|---|---|---|
| `regression` | Agreement with an admitted prior Moira artifact | External truth |
| `authority` | Agreement with a product-relevant primary authority under named semantics | Unexamined products or intervals |
| `corroboration` | Agreement with an independent secondary engine | Primary authority |
| `invariant` | Satisfaction of independently derived structural or physical relations | External truth where an authority governs |
| `native_parity` | Agreement between admitted Python/native counterparts | External truth or universal native coverage |
| `harness` | Proof that test infrastructure enforces its own policy | Scientific correctness |
| `performance` | Timing, memory, handle, or throughput evidence | Scientific correctness |

No majority vote among weak evidence classes upgrades a claim.

### 7.2 Tolerance belongs to a product

No generic fixture may imply one universal meaning for:

- longitude;
- distance;
- time;
- ratio;
- event residual;
- external-authority agreement.

Every scientific comparison must declare:

- metric;
- units;
- absolute, relative, circular, vector, or interval comparison rule;
- tolerance value;
- derivation or authority for that tolerance;
- conditioning domain and exclusions.

### 7.3 Resources are capabilities, not paths

`Path.exists()` is not a resource proof. A resource requirement may include:

- content-derived kernel identity;
- DAF/SPK type;
- required target/center pairs;
- coverage interval;
- bodies;
- frame;
- relevant manifest identity;
- native-reader capability;
- no-download policy.

### 7.4 Baselines are read-only in pytest

Ordinary pytest may compare against admitted snapshots, goldens, and oracle
fixtures. It may not create or modify them. Candidate generation and evidence
promotion are separate reviewed commands.

### 7.5 Incomplete execution is never green

Worker death, controller interruption, artifact write failure, missing required
resources, evidence-schema failure, or receipt finalization failure must remain
visible in the exit status and run receipt.

## 8. Target architecture

```text
tests/conftest.py
    thin plugin registration and only truly shared fixture exports
        |
        +-- tests/_pytest_plugins/configuration.py
        +-- tests/_pytest_plugins/known_issues.py
        +-- tests/_pytest_plugins/determinism.py
        +-- tests/_pytest_plugins/network_policy.py
        +-- tests/_pytest_plugins/resources.py
        +-- tests/_pytest_plugins/classification.py
        +-- tests/_pytest_plugins/lifecycle.py
        +-- tests/_pytest_plugins/artifacts.py
        +-- tests/_pytest_plugins/xdist_coordination.py
        +-- tests/_pytest_plugins/evidence.py

tests/harness_meta/       black-box tests of the pytest plugins
tests/support/            typed numeric assertions and safe test helpers
tests/evidence/           evidence-contract and receipt schemas
tests/metamorphic/        source-owned mathematical relations
tests/adversarial/        deterministic hostile cases
tests/fuzz/               bounded parser and input fuzz harnesses
tests/chaos/              process, worker, I/O, and scheduling attacks
tests/corpora/regressions/ reviewed minimized reproductions
```

Use `pytest.StashKey` for pytest-owned state. Workers never compete over shared
JSON or coverage files. The controller owns run finalization.

## 9. Planned file surface

### 9.1 Initial hardening

Modify:

- `tests/conftest.py`
- `tests/unit/test_conftest_smoke.py`
- `tests/tools/snapshots.py`
- `tests/tools/golden.py`
- `tests/tools/ritual.py`
- `tests/tools/merge_worker_artifacts.py`
- `pyproject.toml`

Create:

- `tests/harness_meta/test_known_issues_policy.py`
- `tests/harness_meta/test_configuration_policy.py`
- `tests/harness_meta/test_hypothesis_policy.py`
- `tests/harness_meta/test_network_policy.py`
- `tests/harness_meta/test_resource_policy.py`
- `tests/harness_meta/test_lifecycle_policy.py`
- `tests/harness_meta/test_artifact_policy.py`
- `tests/harness_meta/test_xdist_policy.py`
- `tests/harness_meta/test_baseline_policy.py`

The exact server-marker migration list must be generated and reviewed before
editing. Do not blindly change every file containing `network`.

### 9.2 Plugin extraction

Create:

- `tests/_pytest_plugins/__init__.py`
- each plugin shown in the target architecture;
- focused unit/meta tests for each plugin.

Delete only after replacement and contract coverage:

- obsolete code sections from `tests/conftest.py`;
- `tests/tools/merge_worker_artifacts.py`, if controller-owned reports make it
  unnecessary.

### 9.3 Assurance MVP

Create:

- `tests/evidence/__init__.py`
- `tests/evidence/contracts.py`
- `tests/evidence/receipts.py`
- `tests/support/numeric_assertions.py`
- `scripts/replay_test_receipt.py`
- `scripts/build_test_assurance_matrix.py`

Modify a small exemplar set only:

- `tests/unit/test_spk_kernel_identity.py`
- one admitted coordinate-transform invariant surface;
- one doctrine/source-owned astrology surface;
- one Python/native parity surface.

The exemplar files are selected during Phase 4 after confirming current
authority and semantics. Do not mass-annotate the suite first.

### 9.4 Later assurance lanes

Create dedicated tests under:

- `tests/metamorphic/`
- `tests/fuzz/`
- `tests/chaos/`
- `tests/mutations/` if a repository-owned semantic mutation runner is admitted.

CI changes occur only after local gates are stable.

## 10. Execution phases

### Phase 0 — Re-establish the baseline and freeze scope

**Purpose:** ensure tomorrow starts from known source and runtime state.

- [x] Run `git status --short --branch`.
- [x] Record every unrelated modified and untracked path.
- [x] Confirm `.\.venv\Scripts\python.exe` exists and report its version.
- [x] Read `tests/KNOWN_ISSUES.yml`.
- [x] Set:

  ```powershell
  $env:MOIRA_NO_DOWNLOAD = "1"
  $env:MOIRA_TEST_MODE = "1"
  $env:MOIRA_STRICT_KNOWN_ISSUES = "1"
  ```

- [x] Run the import/native receipt:

  ```powershell
  .\.venv\Scripts\python.exe -c "import moira; from moira import moira_native as mn; print(moira.__version__, mn.__backend_file__)"
  ```

- [x] Resolve the planetary resource without downloads:

  ```powershell
  .\.venv\Scripts\python.exe -c "from moira._kernel_paths import find_planetary_kernel; print(find_planetary_kernel())"
  ```

- [x] Run the current harness smoke:

  ```powershell
  .\.venv\Scripts\python.exe -m pytest tests\unit\test_conftest_smoke.py -q --durations=10
  ```

- [x] Run the bare-Hypothesis characterization:

  ```powershell
  .\.venv\Scripts\python.exe -m pytest tests\unit\test_physics_layer.py::test_pbt_nutation_deps_bounded -q --hypothesis-show-statistics
  ```

- [x] Collect server cases with and without the current network marker:

  ```powershell
  .\.venv\Scripts\python.exe -m pytest tests\server --collect-only -q
  .\.venv\Scripts\python.exe -m pytest tests\server --collect-only -q -m "not network"
  ```

- [x] Confirm no pre-existing diff overlaps the planned first tranche.

**Stop conditions:**

- the active interpreter is not the project `.venv`;
- `tests/conftest.py`, `pyproject.toml`, or intended helper files contain
  unrelated user changes;
- strict known-issue validation already fails for an unrelated reason;
- the native extension or editable metadata is stale relative to source.

**Exit evidence:** a short baseline receipt with commands, counts, setup/call
durations, current kernel path, current native binary, and preserved dirty
paths.

---

### Phase 1 — Characterize the harness before extraction

**Purpose:** make each current false-green path executable in an isolated test
before changing production harness code.

Use pytest's built-in `pytester` plugin. Enable it from the root tests plugin
surface or invoke the meta suite with `-p pytester`; do not add a nested
deprecated `pytest_plugins` declaration.

#### Task 1.1 — Known-issue attack matrix

- [x] Create subprocess cases for:
  - missing `KNOWN_ISSUES.yml`;
  - missing or misspelled top-level key;
  - bare top-level list;
  - scalar list member;
  - missing required field;
  - blank string field;
  - duplicate ID;
  - unquoted YAML date;
  - exact quoted `YYYY-MM-DD`;
  - timestamp instead of date;
  - invalid calendar date;
  - expired entry in normal and strict modes;
  - `..`, absolute, drive-relative, UNC, symlink escape, directory, and missing
    paths.
- [x] Assert exact exit class and a stable diagnostic substring.

#### Task 1.2 — Configuration attack matrix

- [x] Test empty, malformed, negative, `nan`, `inf`, and valid budget values.
- [x] Test contradictory `MOIRA_TEST_MODE=1` and `MOIRA_NO_DOWNLOAD=0`.
- [x] Test invalid seed values.
- [x] Test strict-marker and strict-config behavior.

#### Task 1.3 — Hook-order characterizations

- [x] Prove the current Hypothesis profile is late.
- [ ] Probe collection-time, session-fixture, module-fixture, setup, call, and
  teardown network attempts.
- [ ] Probe cached socket aliases, DNS, loopback, and a subprocess attempt.
- [ ] Prove setup and teardown failures are absent from current artifacts.

#### Task 1.4 — Xdist and artifact characterizations

- [ ] Run synthetic suites with `-n 0` and `-n 2`.
- [ ] Prove current `serial` markers do not serialize.
- [ ] Prove current worker merge path misses worker output.
- [ ] Prove the controller lacks worker duration data.
- [ ] Prove unsafe run IDs are rejected by the future contract.
- [ ] Parse the currently generated PowerShell helper and capture its failure.

**Gate:**

```powershell
.\.venv\Scripts\python.exe -m pytest tests\harness_meta -q -p pytester
```

At the beginning of this phase, tests that characterize known defects may be
marked with an explicit temporary expectation. Remove each expectation in the
same task that repairs the behavior. Do not leave a permanent xfail ledger.

---

### Phase 2 — Repair fail-closed configuration

**Purpose:** remove configuration paths that silently weaken the suite.

#### Task 2.1 — Strict known-issue schema

- [x] Use the declared PyYAML development dependency; remove the YAML-lite
  fallback.
- [x] Require one top-level mapping with exactly the admitted key set.
- [x] Require `known_issues` to be a list of mappings.
- [x] Validate required fields as nonempty strings.
- [x] Require unique IDs.
- [x] Accept a YAML `date` or an exact `YYYY-MM-DD` string and normalize to
  `datetime.date`; reject datetimes and alternate formats.
- [x] Reject rooted, drive-relative, UNC, `..`, and NUL-containing paths before
  filesystem access.
- [x] Resolve locally, require containment under `tests/`, and require a regular
  file.
- [x] Preserve the current rule that a known issue never skips or xfails a test.
- [x] Raise `pytest.UsageError` with the issue index/ID and failing field.
- [x] Preserve strict-expiry behavior and test both strict and reporting modes.

#### Task 2.2 — Typed environment configuration

- [x] Centralize boolean, integer, and nonnegative finite-float parsing.
- [x] Fail on contradictory no-download/test-mode settings instead of allowing
  inherited state to weaken test mode.
- [x] Store parsed configuration in typed objects and `pytest.StashKey`.
- [x] Do not mutate unrelated environment variables.

#### Task 2.3 — Early Hypothesis policy

- [x] Register named profiles at conftest import so standard CLI selection can
  resolve them, then load the selected profile inside `pytest_configure` before
  test module collection.
- [x] Define separate explicit profiles:
  - deterministic CI/test mode;
  - exploratory local mode;
  - extended nightly mode.
- [x] Record selected profile, example limit, database policy, and
  derandomization in the run receipt.
- [x] Prove a bare `@given` test sees the selected settings.

**Gate:**

```powershell
.\.venv\Scripts\python.exe -m pytest tests\harness_meta\test_known_issues_policy.py tests\harness_meta\test_configuration_policy.py tests\harness_meta\test_hypothesis_policy.py -q -p pytester
.\.venv\Scripts\python.exe -m pytest tests\unit\test_conftest_smoke.py tests\unit\test_physics_layer.py::test_pbt_nutation_deps_bounded -q --hypothesis-show-statistics
```

**Rollback boundary:** configuration repairs form one checkpoint. Do not mix
network, resource, or artifact changes into it.

#### 2026-07-30 required-first-tranche checkpoint

- **Scope completed:** Phase 0; the Phase 1 known-issue, configuration, and
  Hypothesis characterizations; and Phase 2.
- **Harness contracts:** 104 isolated subprocess cases collected:
  30 configuration, 4 Hypothesis, and 70 known-issue cases.
- **Combined gate:** those 104 contracts plus the 8 existing conftest smoke
  cases completed successfully with no reported skip or failure.
- **Property-policy proof:** the real
  `test_pbt_nutation_deps_bounded` consumer executed 50 passing examples and
  stopped because `settings.max_examples=50`; the pre-repair receipt executed
  100.
- **Profile proof:** `moira-ci`, `moira-local`, `moira-nightly`, and a
  CLI-derived verbosity profile are observed before test-module collection.
- **Worker smoke:** the focused `-n 2` `jd_j2000`/network-block pair passed.
- **Runtime/resource receipt:** project `.venv` Python 3.14.3, Moira 6.1.0,
  the current CPython 3.14 native extension, and no-download DE441 discovery at
  `C:\Users\nilad\.moira\kernels\de441.bsp`.
- **Evidence class:** harness-policy verification. No astronomical accuracy,
  external authority, Python/native numerical parity, or scientific tolerance
  claim is made by this checkpoint.
- **Protected boundaries preserved:** no engine, native, kernel, oracle,
  golden, snapshot, network-policy, artifact-policy, CI, or heliacal file was
  changed.
- **Deliberate remaining work:** strict marker/config enforcement is still
  Phase 6; network, resource lifecycle, xdist scheduling/artifacts, plugin
  decomposition, evidence contracts, fuzz, mutation, sanitizer, and CI lanes
  remain separately scoped. The subprocess mini-project loader must be updated
  when plugin decomposition begins.

Exact final commands and outcomes:

```powershell
$env:MOIRA_NO_DOWNLOAD = "1"
$env:MOIRA_TEST_MODE = "1"
$env:MOIRA_STRICT_KNOWN_ISSUES = "1"

# 30 configuration + 4 Hypothesis + 70 known-issue contracts collected.
.\.venv\Scripts\python.exe -m pytest tests\harness_meta --collect-only -q

# 104 harness-meta contracts + 8 existing smoke cases:
# 112 passed, 0 failed, 0 skipped.
.\.venv\Scripts\python.exe -m pytest tests\harness_meta tests\unit\test_conftest_smoke.py -q --tb=short

# 1 passed; 50 passing examples; stopped at settings.max_examples=50.
.\.venv\Scripts\python.exe -m pytest tests\unit\test_physics_layer.py::test_pbt_nutation_deps_bounded -q --hypothesis-show-statistics

# 2 passed under two xdist workers; 0 failed, 0 skipped.
.\.venv\Scripts\python.exe -m pytest tests\unit\test_conftest_smoke.py -q -k "jd_j2000 or network_blocked" -n 2

# 2 expiry-policy contracts passed after restoring runner-local date semantics.
.\.venv\Scripts\python.exe -m pytest tests\harness_meta\test_known_issues_policy.py -q -k "expired_issue" --tb=short

# All touched Python files compiled; Ruff reported "All checks passed!".
.\.venv\Scripts\python.exe -m py_compile conftest.py tests\conftest.py tests\harness_meta\test_configuration_policy.py tests\harness_meta\test_hypothesis_policy.py tests\harness_meta\test_known_issues_policy.py
.\.venv\Scripts\ruff.exe check conftest.py tests\conftest.py tests\harness_meta --no-fix

# Passed; line-ending notices were informational and no whitespace error was reported.
git diff --check
```

---

### Phase 3 — Correct semantic test helpers and baseline policy

**Purpose:** prevent shared helpers from spreading incorrect scientific or
epistemic semantics.

#### Task 3.1 — Reference epochs

- [x] Replace loose labels with exact declared objects:
  - exact J2000.0;
  - exact B1900.0, if still required;
  - explicitly named civil calendar anchors;
  - exact J2100.0, if still required.
- [x] Do not label a Gregorian conversion as proleptic Julian.
- [x] Validate the constants against an admitted independent reference library
  in development tests and internal calendar round trips.
- [x] Run every discovered consumer:

  ```powershell
  .\.venv\Scripts\python.exe -m pytest tests\unit\test_vertex_oracle.py tests\unit\test_lunar_occultation_contacts.py tests\integration\test_delta_t_hybrid.py -q
  ```

- [x] Treat any newly exposed engine discrepancy as a separate protected task.

#### Task 3.2 — Typed numeric assertions

- [x] Create product-owned helpers for:
  - circular degrees;
  - vector angular separation;
  - scalar degrees;
  - AU;
  - kilometres;
  - days;
  - seconds;
  - dimensionless ratios;
  - event-function residuals.
- [x] Reject booleans, NaN, and infinity unless a test explicitly asserts their
  rejection behavior.
- [x] Require each helper call to supply or inherit a named tolerance contract.
- [x] Inventory the current nine external consumers of `moira_approx`.
- [x] Migrate one product at a time; do not mechanically translate tolerances.
- [x] Deprecate `moira_approx`; remove it only after the inventory is empty.

#### Task 3.3 — Snapshot, golden, and ritual honesty

- [x] Remove environment-controlled writes from ordinary pytest.
- [x] Remove direct `update=True` bypasses.
- [x] Validate names as safe slugs and enforce resolved-path containment.
- [x] Read existing baselines without mutating them.
- [x] Correct ritual language:
  - snapshot = regression witness;
  - golden = storage channel whose authority comes from adjacent provenance;
  - cross-path agreement = parity/invariant evidence, not external truth.
- [x] Refuse baseline update mode under CI and xdist.
- [x] Define the separate future candidate-generation contract: it must write a
  new candidate tree atomically and remain outside ordinary pytest.
- [x] Require reviewed promotion before protected evidence changes.

#### Task 3.4 — Dead or misleading fixtures

- [x] Reconfirm consumers for `any_house_system`, `test_env_vars`, `qapp`, and
  `qapp_session`.
- [x] Remove unused fixtures rather than preserving unproved abstractions.
- [x] If a fixture must remain, give it a direct contract test and fail closed
  on base-runtime import defects.

**Gate:**

```powershell
.\.venv\Scripts\python.exe -m pytest tests\harness_meta\test_baseline_policy.py tests\unit\test_conftest_smoke.py -q -p pytester
.\.venv\Scripts\python.exe -m pytest tests\unit\test_vertex_oracle.py tests\unit\test_lunar_occultation_contacts.py tests\integration\test_delta_t_hybrid.py -q
```

No baseline file may appear in `git status` after this phase.

#### Phase 3 completion checkpoint — 2026-07-30

- Replaced the loose fixture tuples with immutable reference objects under
  `tests/support/reference_epochs.py`. The admitted set is exact J2000.0,
  exact B1900.0, two explicitly proleptic-Gregorian civil anchors, and exact
  J2100.0. ERFA independently defines every JD; Moira's proleptic-Gregorian
  conversion round-trips every calendar rendering.
- Kept the reference records out of ambient `conftest.py`: the two real
  consumers now parameterize explicitly. The broader phase gate still runs the
  lunar-contact and delta-T confidence slices, but they were not falsely
  described as fixture consumers.
- Added a pure assertion layer with named, frozen tolerance contracts, explicit
  units, explicit residual semantics, stable vector-angle calculation, and
  fail-closed handling for booleans, non-finite values, zero vectors, and
  contract/helper mismatches. The hostile-float cases reduce circular operands
  before subtraction, scale vectors before normalization, and bound iterable
  consumption before materialization.
- Audited all nine external `moira_approx` files: 50 calls remain
  (37 longitude, 8 overloaded `distance`, and 5 overloaded `angle` calls).
  Only the equatorial/ecliptic house round-trip was migrated, to a named
  circular `1e-12 deg` internal-geometry contract. The legacy fixture is
  visibly deprecated; mass migration and removal remain forbidden.
- Made snapshot and golden helpers read-only, removed their update arguments
  and write paths, rejected legacy update environments at pytest
  configuration, and added shared safe-slug, Windows-device-name,
  resolved-containment, symlink, regular-file, strict-UTF-8, duplicate-key,
  non-finite-JSON, and exact-schema validation. Stable-open checks bind the
  validated directory entry to the opened file and reject swaps or mutation
  during the read. Baseline-root identity is revalidated across traversal so a
  directory swap cannot redirect one evidence channel into another. Baseline
  roots and candidates reject reparse/name-surrogate paths, and typed JSON
  comparison prevents Python's `True == 1` rule from erasing the distinction
  between booleans and numbers.
- Hardened the policy surfaces around those helpers: known-issue identifiers
  now use an ASCII log-safe slug law, the known-issues policy file receives the
  same stable-open protection, and the root import sanitizer evicts foreign
  `tests`, `moira`, `tools`, and `support` packages before collection.
- Corrected ritual and fixture language: snapshots are regression witnesses,
  goldens are storage governed by adjacent provenance, and cross-path agreement
  is parity/invariant evidence rather than external truth.
- Removed the four zero-consumer fixtures. `any_house_system` was additionally
  proved defective: `HouseSystem` is not iterable and its broad exception
  handler silently produced an empty parameter set.
- The future candidate-generation surface is deliberately not implemented in
  this phase. Its declared boundary is a separate command, a new candidate
  tree, atomic writes, and reviewed promotion into protected evidence.
- Verification receipts:
  - `62 passed` — reference-epoch and typed-numeric contracts.
  - `98 passed` — adversarial baseline-policy contracts.
  - `106 passed` — required baseline-policy plus conftest-smoke gate.
  - `143 passed` — vertex, lunar-occultation-contact, and delta-T phase gate.
  - `26 passed` — full house-projection geometry file.
  - `28 passed, 1 skipped` — direct baseline consumers; the skip requires the
    absent `.venv-swiss-314` comparator environment.
  - `226 passed` — complete harness-meta suite.
  - Full `tests/` collection completed successfully.
- A twelve-pass, two-perspective adversarial static review was run across
  architecture, security, performance, quality, requirements, and likely-bug
  criteria. Confirmed findings became tests and repairs: hostile finite-angle
  overflow, hostile vector-norm overflow, unbounded vector iterables,
  baseline-file, baseline-root, and policy-file swap races, typed-JSON
  boolean/number aliasing, foreign `support` import shadowing, ambient
  legacy-update variables in subprocess tests, exact exception contracts,
  log-spoofable known-issue identifiers, and opaque Windows reparse masks. The
  root-identity and typed-JSON repairs then received a final independent
  bypass-oriented re-review with no further finding. Phase 4 marker/network
  work, Phase 6 strict marker/config enforcement, plugin decomposition, and
  broad helper migration remained explicit deferrals rather than being
  smuggled into Phase 3.
- `git status --short -- tests/snapshots tests/golden` remained empty. No
  baseline JSON, engine module, tolerance outside the single exemplar, network
  policy, or unrelated visibility work was changed.
- Adjacent mislabeled epoch matrices and the `tests/oracle/oracle_policy.py`
  MJD/J2000 metadata defect were recorded as separate protected validation
  debt; they were not folded into this tranche.

---

### Phase 4 — Separate loopback from external network

**Purpose:** retain server coverage without granting external egress.

#### Task 4.1 — Inventory and marker law

- [x] Add marker definitions:
  - `loopback`: local IPC only;
  - `external_network`: external access, explicit opt-in;
  - retain `network` only as a temporary migration error or deprecated alias.
- [x] Inventory every current `network` marker.
- [x] Classify each use by actual requirement, not directory.
- [x] Retag TestClient/socket-pair cases as `loopback`.
- [x] Retag true live-oracle acquisition as `external_network`.
- [x] Fail collection when an unclassified legacy `network` marker remains at
  the end of migration.

#### Task 4.2 — Permission model

- [x] Add `--run-external-network`.
- [x] Require both `external_network` and the command-line option.
- [x] Deselect or skip external cases with an explicit count and reason when
  permission is absent.
- [x] Permit only loopback destinations for `loopback`.
- [x] Block accidental external connections for unmarked and loopback tests.
- [x] Test IPv4, IPv6, DNS, UDP, cached aliases, raw `_socket`, common Python
  clients, and spawned child processes.
- [x] State honestly that Python interception does not contain native code or a
  hostile subprocess.

#### Task 4.3 — CI containment

- [ ] **DEFERRED — separate approval required.** Add process/runner egress
  denial in a dedicated CI change; `.github/` remains untouched in Phase 4.
- [x] Keep a permitted loopback path for server tests.
- [x] Add Python-layer canaries that attempt external egress and must fail.
  The runner/firewall canary remains part of the separately approved CI
  containment change.

**Gates:**

```powershell
.\.venv\Scripts\python.exe -m pytest tests\harness_meta\test_network_policy.py -q -p pytester
.\.venv\Scripts\python.exe -m pytest tests\server -q -m "loopback or not external_network"
.\.venv\Scripts\python.exe -m pytest tests\server --collect-only -q -m "external_network"
```

The second command must no longer discard most server coverage merely because
TestClient needs local IPC.

The third command is a negative collection assertion: because server tests
must not require external egress, zero selected items with pytest exit code 5
is the expected result. Treat any selected server node as failure; do not
misreport the expected no-tests exit as a conventional green pytest run.

#### Phase 4 completion checkpoint — 2026-07-30

- Replaced the overbroad `network` capability with three explicit states:
  unmarked deny, numeric-loopback/local-IPC only, and separately authorized
  external access. External access requires the marker, the
  `--run-external-network` option, and an external-only selected item set; the
  flag alone grants nothing.
- Migrated the exact HEAD baseline of 157 executable legacy-marker occurrences
  across 125 files. The final tree has 130 `loopback` occurrences across 102
  files, 39 `external_network` occurrences across 20 files, and zero
  executable legacy occurrences. The registered legacy marker remains only to
  produce an explicit collection error.
- Server classification is exact: 112 modules total; 100 contain
  `TestClient`, and exactly those same 100 carry loopback permission. All 120
  direct TestClient constructions are covered. The other 12 modules are
  unmarked and contain no TestClient. Server tests contain 113 loopback
  occurrences and zero external markers.
- Removed four stale server capabilities rather than retagging by directory:
  `test_hellenistic_contract_openapi.py`,
  `test_server_pancha_pakshi_service.py`,
  `test_server_phase9_umbrella_exclusions.py`, and
  `test_server_sidereal_context.py`.
- Installed process-global CPython guards before repository test collection,
  across setup/call/teardown, and in cooperative Python children. The policy
  rejects wildcard and non-loopback bind/connect/send paths, hostname and
  reverse-DNS resolution, raw `_socket` construction, retained public-socket
  writes, cross-platform `asyncio.sock_sendfile`, and Windows Proactor/IOCP
  connect, send, sendfile, and connected sendto paths. Audit-hook,
  bootstrap-import, and bootstrap-path failures abort rather than silently
  weakening interception.
- The legacy source scan uses Python's declared source encoding, recognizes
  ordinary `pytest` and `mark` aliases even in import-skipped modules, and
  fails collection if any source file cannot be read or parsed. An ignored
  malformed-module regression proves that the scan no longer fails open.
- The adversarial network-policy suite collects 66 cases: 64 passed and two
  were skipped because `socket.sendmsg` is unavailable on this Windows
  runtime. Coverage includes IPv4/IPv6 TCP, UDP, DNS, wildcard/listen,
  socketpair, cached aliases, raw/subclass construction, common HTTP clients,
  FastAPI portal threads, async TCP/UDP, retained writes, child inheritance,
  `python -S`/shadowing boundaries, fail-closed installation, marker
  conflicts, selection receipts, lifecycle reset, collection-time denial, and
  xdist worker isolation.
- Final verification receipts, all with project `.venv` Python 3.14.3,
  `MOIRA_TEST_MODE=1`, `MOIRA_NO_DOWNLOAD=1`, and
  `MOIRA_STRICT_KNOWN_ISSUES=1`:
  - `138 passed` — baseline/configuration/Hypothesis harness policies.
  - `88 passed` — import sanitizer, known-issues, and reference-epoch policies.
  - `8 passed` — conftest smoke, including deny and loopback behavior.
  - `378 skipped` — every selected repository external item was held in deny
    mode without the explicit option; no live external run was performed.
  - unrestricted and permitted server collection each produced the same 1,463
    node IDs, with a zero-node diff.
  - server `-m external_network` selected zero nodes and returned the expected
    no-tests exit code 5.
  - the final exact server gate emitted 1,463 pass symbols, no other outcome
    symbols, and exit code 0. Its harness receipt reported
    `default=deny`, `loopback=marked-only`, and `external=disabled`; wall time
    was 68 minutes 3.978 seconds.
- Restored server coverage exposed two pre-existing stale assertions, not
  network-policy failures. The exact electional inventory omitted seven routes
  added after its last update, and the website pipeline still described eight
  stages after canonical stage 8, topocentric diurnal aberration, was admitted.
  Both assertions were strengthened to current exact truth. The two failures
  then passed directly, both complete files passed (`20 passed`), and an
  independent read-only review found exact 18-for-18 route parity and exact
  stage 0–8 order before the full green rerun.
- Scoped Ruff and compile checks passed for the Phase 4 harness, policy,
  bootstrap, smoke, and repaired server-test files. Independent adversarial
  reviews found no remaining Phase 4 implementation defect.
- The Python layer remains accidental-egress protection for cooperative
  CPython, not a security sandbox. Cached pre-install/raw descriptors,
  SSL/native/ctypes writes, pre-conftest plugin activity, `python -S`, hostile
  children, and foreign inherited descriptors require the separately approved
  runner firewall. Local Windows 3.14 Proactor paths were exercised; Windows
  3.10 and Windows CI harness coverage remain unverified.
- Task 4.3 runner containment is deliberately deferred. `.github/`,
  `tests/snapshots`, and `tests/golden` remain untouched, as does unrelated
  visibility-reference work. Canonical validation documentation now names
  `external_network`; generated `moira.wiki/VALIDATION_ASTRONOMY.md` still
  awaits a governed sync because that generated checkout contains unrelated
  concurrent edits and must not be hand-edited.

---

### Phase 5 — Make resource use explicit

**Purpose:** eliminate hidden kernel work and identity-free resource admission.

#### Task 5.1 — Resource contracts

- [x] Introduce a typed kernel requirement with optional:
  - product;
  - content identity;
  - interval;
  - bodies;
  - target/center pairs;
  - frame;
  - segment types;
  - native capability.
- [x] Preserve a generic "any admitted planetary kernel" requirement only for
  genuinely identity-independent invariants.
- [x] Resolve resource capability once per process.
- [x] Build identity from opened kernel/catalog content, never filename.
- [x] Record a resource receipt for run, skip, and failure paths.

#### Task 5.2 — Explicit reader fixtures

- [x] Remove the session-autouse kernel singleton bootstrap.
- [x] Provide explicit fixtures:
  - `planetary_kernel_path`;
  - `planetary_kernel_receipt`;
  - `planetary_reader`;
  - `configured_global_reader` only for legacy singleton-specific tests;
  - `moira_engine` with explicit ownership and teardown.
- [x] Use `yield` and close/reset every fixture-owned reader.
- [x] Do not hot-swap global reader state during concurrent tests.
- [x] Inventory direct `get_reader()` callers before removing ambient setup.

#### Task 5.3 — Resource selection integrity

- [x] A required mismatched identity fails or skips with a named capability
  receipt according to the lane's policy.
- [x] A corrupt resource never becomes "available" through an existence check.
- [x] Kernel-free tests prove that no planetary reader is opened.
- [x] Cache capability checks without caching a stale reader across lawful
  reset boundaries.

**Gates:**

```powershell
.\.venv\Scripts\python.exe -m pytest tests\harness_meta\test_resource_policy.py tests\unit\test_spk_kernel_identity.py -q -p pytester
.\.venv\Scripts\python.exe -m pytest tests\unit\test_conftest_smoke.py -q -k "jd_j2000 or network_blocked" --durations=5
.\.venv\Scripts\python.exe -m pytest tests\unit\test_conftest_smoke.py -q --durations=10
```

The JD-only setup must no longer acquire the planetary kernel. Record before
and after timing as performance evidence only.

#### Phase 5 completion checkpoint — 2026-07-30

- Added immutable typed planetary contracts in
  `tests/support/resource_policy.py` for product, opened-content identity,
  interval, bodies, target/center routes, frame, segment types, and native
  capability. The ordinary `requires_ephemeris` marker now means an admitted,
  content-identified DE441 resource; only an explicit `generic=True` request
  is identity-independent. Invalid or contradictory requirements fail during
  collection.
- Resource discovery is lazy and process-local. A thread-safe resolver opens
  one probe reader, derives capability from the opened SPK catalog, verifies
  stable file identity before and after probing, closes the probe, and caches
  immutable capability rather than a live reader. Fixture readers are checked
  against the receipt and current fingerprint before use.
- Removed the session-autouse global-reader bootstrap. Marked consumers now
  receive typed admission plus explicit `planetary_kernel_receipt`,
  `planetary_kernel_path`, `planetary_reader`, compatibility `reader`,
  primary-only `configured_global_reader`, and owned `moira_engine` fixtures.
  Fixture-owned readers are yielded and closed; owned singleton state is reset
  on teardown. The legacy-global fixture refuses to replace foreign
  pre-existing state instead of hot-swapping it.
- Added RUN, SKIP, and FAILURE receipts for discovery, admission, live use,
  and teardown, including xdist serialization and merge. Skipped and xfailed
  items are decided before acquisition, corrupt files cannot pass an existence
  check, and stateful `skipif` expressions are not evaluated twice.
- Added a separate release-bound supplemental-resource contract in
  `tests/support/small_body_resource_policy.py`. It accepts only released
  manifests that pass production `verify_release()` SHA-256 integrity,
  validates catalog/version/source-revision identity and exact body, interval,
  segment, and native capability, opens shards one at a time, and records a
  terminal lifecycle receipt.
- Migrated reader-capable planetary and small-body tests to pass admitted
  handles directly. APIs without a reader parameter use the narrow
  per-test ContextVar bridge. The final direct `get_reader()` inventory is
  limited to harness fakes, the intentional singleton-routing contract in
  `test_sovereign_small_body_manifest_routing.py`, and lifecycle tests in
  `test_spk_reader.py`; the standalone stress audit now requires an explicit
  kernel path.
- Verification receipts, all with project `.venv` Python 3.14.3,
  `MOIRA_TEST_MODE=1`, `MOIRA_NO_DOWNLOAD=1`, and
  `MOIRA_STRICT_KNOWN_ISSUES=1`:
  - `78 passed` — typed planetary policy plus SPK content-identity gate.
  - `32 passed` — supplemental manifest admission, cleanup, receipt, and xdist
    policy.
  - `2 passed` — JD/network kernel-free smoke; zero resource receipts or
    probes. The audited pre-phase JD setup was approximately 15.78 seconds;
    final per-test setup was 0.001 and 0.000 seconds, with all reported
    durations below 0.005 seconds. These are performance observations only.
  - `8 passed` — full conftest smoke; six planetary RUN receipts, one DE441
    content probe, and no skip or failure receipt.
  - `21 passed` — Chiron and Type-13 focused slices; one terminal supplemental
    RUN receipt admitted two released manifests, 419 shards, and 10,471 unique
    bodies.
  - `544 passed, 1 skipped` — broad rise/set, parans, Shadbala, server-service,
    occultation, magnitude, and void-of-course regression slice. The one
    RULE-06 skip reports that the fixed 30-day corpus contained no no-aspect
    window.
  - Full strict/no-download collection passed with 14,063 items. It acquired no
    planetary or supplemental resource; all 378 external-network items remained
    held in deny mode.
- The admitted supplemental release identities were
  `moira-asteroids@2026.07.27.1:0560302f877a46cebc550376ae70665fefab84801078181cf3c4199ce86d49d0`
  and
  `moira-comets@2026.07.28.1:31fbbedbb3ea7ba276fa9d49d52211ae41d90f76c74fb49ec0a6bafb014f07a1`.
- Adversarial coverage exercised malformed and contradictory markers, filename
  spoofing, identity and capability mismatch, corrupt resources, continuous
  route coverage, concurrent exactly-once probing, skip/xfail ordering,
  acquisition and teardown failures, foreign singleton state, xdist report
  merging, released-manifest integrity, path escape, partial construction, and
  supplemental cleanup. An independent final review returned APPROVE with high
  confidence and no remaining actionable Phase 5 finding.
- Every Phase 5 Python file compiled. Ruff passed on the harness and both policy
  modules and their meta-suites; the full migrated-file comparison introduced
  zero new Ruff diagnostics relative to HEAD. The broader touched-file run
  still reports 69 inherited repository-baseline diagnostics. Scoped
  `git diff --check` passed, apart from line-ending conversion warnings.
- The boundary remains explicit. Full collection found 1,063 typed
  `requires_ephemeris` items whose legacy APIs still receive the admitted
  reader through a function-scoped ContextVar; this phase does not claim
  repository-wide direct handle propagation. All direct `Moira()`
  construction was not rewritten. Live external comparisons, the complete
  numerical suite, and the deferred Task 4.3 nested-runner firewall were not
  run or implemented.
- `SmallBodyKernel.close()` suppresses its own internal close errors, so the
  harness proves invocation but cannot surface an error hidden by that
  implementation. A constructor that allocates and raises before returning
  must still clean itself, and manifest verification followed by shard opening
  is not a hostile-filesystem lock against post-verification mutation.
- At the Phase 5 checkpoint, Phase 6 had not started. No production/native
  computation, scientific baseline, `.github/` workflow, generated
  `moira.wiki/`, or unrelated visibility-reference work was changed by
  Phase 5.

---

### Phase 6 — Real execution classification and serial semantics

**Purpose:** ensure selectors and concurrency labels have enforceable meaning.

- [x] Derive paths relative to `tests/`, never from absolute checkout parents.
- [x] Define one primary class per case and fail on contradiction.
- [x] Add strict marker and strict configuration enforcement.
- [x] Remove automatic `parallel`; absence of `serial` is not proof of
  concurrency safety.
- [x] Inventory explicit global-state, singleton, filesystem-lock, shared-cache,
  and resource-mutation tests.
- [x] Run explicitly admitted `parallel` tests under xdist and `serial` tests
  in a separate `-n 0` lane; unclassified tests remain `local_only`.
- [x] Fail an xdist invocation that selects a `serial` or `local_only` test
  unless an admitted scheduler actually enforces the contract.
- [x] Fail on empty parametrization for required base-engine enumerations.
- [x] Record collected, selected, deselected, skipped, and primary-class counts.

**Gates:**

```powershell
.\.venv\Scripts\python.exe -m pytest tests\harness_meta\test_xdist_policy.py -q -p pytester
.\.venv\Scripts\python.exe -m pytest tests\harness_meta -n 2 --dist=load -q -p pytester -m "parallel"
.\.venv\Scripts\python.exe -m pytest tests\harness_meta -n 0 -q -p pytester -m "serial"
```

#### Phase 6 completion checkpoint — 2026-07-30

- Execution classification is now an enforced collection contract, not a
  descriptive tag. Every case receives exactly one path-derived primary class
  from the resolved path relative to `tests/`: `legacy_root`, `governance`,
  `harness`, `integration`, `oracle`, `server`, `stress`, or `unit`.
  `legacy_root` deliberately names the location of the eight historical
  root-level test modules; it does not claim to mean every engine test.
  Unknown directories, path escapes, contradictory declarations, marker
  arguments, duplicate node IDs, and late classification-marker mutation fail
  closed.
- Native pytest `strict_config` and `strict_markers` must be effectively true,
  including under an alternate `-c` file; explicit `-o` weakening is rejected.
  The harness also checks attached marker registrations itself. Synthetic
  harness projects now opt into the same strict contract.
- Concurrency has three disjoint meanings. Unmarked cases are `local_only`;
  `parallel(reason=...)` is a narrow, reason-enumerated xdist admission; and
  `serial(reason=...)` is a reason-enumerated local-process lane. There is no
  automatic parallel marker. Xdist treats worker presence as authoritative,
  admits only selected `parallel` cases, rejects `--dist=each`, freezes each
  selected classification through collection finish and fixture setup, and
  requires every worker to emit an identical SHA-256 manifest. Its scheduler
  mode is frozen at admission and rechecked at scheduler construction; the
  returned scheduler must have the exact xdist class admitted for that mode.
  The scheduler-hook chain is closed to Moira's guard and xdist's own
  `DSession` implementation, so a late direct or wrapper hook cannot substitute
  duplicate-everything scheduling. The controller independently rejects any
  receipt containing a selected `local_only` or `serial` case.
- The current explicit serial inventory is seven collected cases: the local
  harness canary; one LOLA tile-cache case; two IOTA/Spica topology parameters;
  one LOLA query-width case; and two SPICE time-admission cases. The six
  production cases are all `external_network` and remain held in deny mode.
  Their live bodies were therefore not exercised in this phase; only their
  classification, selection, skip, and receipt behavior was proved.
- Parallel admission remains intentionally small: the harness meta-suite,
  the worker-isolated supplemental-manifest routing test, and two
  temporary-directory lunar-limb lock tests. The remaining non-serial
  repository is `local_only` until an explicit concurrency proof is added.
- Required enumerations now fail if pytest materializes an empty parameter set.
  Intentionally empty families require
  `optional_enumeration(reason=...)` and remain visible in the receipt. The
  current optional family is the Yallop Q outlier corpus, whose source fixture
  presently contains no admitted outlier rows.
- The immutable semantic receipt records collected, selected, deselected,
  primary-class, concurrency, optional-empty, and SHA-256 manifest data.
  Terminal reporting counts unique collection- and runtime-phase skips.
  Serial and two-worker executions of the same deterministic canary corpus
  produce identical visible semantic receipts.
- Removed three false-green collection paths. The scratch diurnal-aberration
  script and resource-binding stress script were renamed outside pytest's
  `test_*.py` discovery; both remain explicit manual tools. The diurnal probe
  now raises on missing exceptions, uses a two-sided physical bound, is safe in
  the canonical Windows console, and passed manually with checks still active
  under Python optimization. The resource stress audit requires an explicit
  kernel path, uses optimization-independent handle checks, and was not run.
  The nested preservation-governance test that launched a broad pytest
  subprocess,
  ignored its status, and always passed was removed.
- Adversarial subprocess coverage now includes checkout-parent name leakage,
  unknown path classes, path escape, primary/concurrency/enumeration
  contradictions, omitted or weakened strictness, implicit-parallel rejection,
  `serial` and `local_only` xdist admission attempts, `--dist=each`, late
  marker mutation, mutation plus deselection, collection-finish mutation,
  mutable worker metadata, late scheduler-mode mutation, direct and wrapped
  scheduler substitution in both inner and outer hook order, worker receipt
  and reason disagreement, required and optional empty enumeration, and
  collection-phase skip accounting.
- Verification used project `.venv` Python 3.14.3 with
  `MOIRA_TEST_MODE=1`, `MOIRA_NO_DOWNLOAD=1`, and
  `MOIRA_STRICT_KNOWN_ISSUES=1`. The focused execution-policy suite passed
  44 cases. The complete harness parallel lane collected 436 cases, selected
  435, and exited successfully with `433 passed, 2 skipped`; both skips are
  Windows `socket.sendmsg` capability absences. The serial lane selected seven
  cases and reported `1 passed, 6 skipped`, with all six skips caused by
  explicit external-network denial. Full strict/no-download collection of the
  current whole worktree passed with 14,199 cases: 13,754 `local_only`, 438
  `parallel`, and seven `serial`; that snapshot includes concurrent visibility
  additions outside Phase 6. The 378 external-network cases remained held in
  deny mode and no resource was acquired. The enumeration lane reported
  `207 passed, 1 skipped`; the skip was the intentionally empty Yallop family.
  Conftest smoke reported eight passes with six DE441 RUN receipts and one
  content probe. The three admitted production parallel cases passed under two
  workers. The existing diurnal-aberration unit file reported 24 passes, and
  its repaired manual probe also exited successfully.
- This checkpoint does not claim the literal full suite, live external
  comparisons, production serial-body execution, or Phase 7 controller-owned
  lifecycle/artifact/replay work. No production/native computation,
  scientific baseline, `.github/` workflow, or generated `moira.wiki/` was
  changed by Phase 6. Concurrent visibility implementation and data work was
  preserved; Phase 6 touched only the optional-enumeration marker on its
  existing Yallop outlier family.

---

### Phase 7 — Controller-owned lifecycle, artifacts, and replay

**Purpose:** make failures and execution receipts exact and crash-visible.

#### Task 7.1 — Full lifecycle reports

- [x] Record setup, call, and teardown outcome/duration separately.
- [x] Aggregate full lifecycle duration by node.
- [x] Enforce a case budget only after the full lifecycle is known.
- [x] Preserve an existing failure and attach budget information as a report
  section.
- [x] Use `time.perf_counter()` for session duration.
- [x] Validate all budgets as finite and nonnegative.
- [x] Finalize evidence before applying a total-budget failure status.
- [x] Rename ordinary failure counts; reserve "flake" for observed fail-then-pass
  attempts under the same receipt.

#### Task 7.2 — Safe ephemeral artifacts

- [x] Default to `.pytest_cache/moira-artifacts/<controller-uuid>/`.
- [x] Reject caller-supplied IDs outside a narrow single-component alphabet.
- [x] Create an `INCOMPLETE` sentinel before execution and replace it with
  `COMPLETE` only after successful finalization.
- [x] Use atomic temporary-write plus replace.
- [x] Apply per-record and per-run size limits.
- [x] Redact known secret-bearing environment names and request headers.
- [x] Never write transient diagnostics beneath `tests/artifacts/`.

#### Task 7.3 — Structured controller receipt

- [x] Emit:
  - `run.json`;
  - `collection.json`;
  - `resources.json`;
  - `reports.jsonl`;
  - `failures.json`;
  - `durations.json`;
  - `rerun-nodeids.json`.
- [x] Let the controller consume xdist log reports and worker shutdown status.
- [x] Eliminate worker competition over shared files.
- [x] Surface merge/finalization errors in exit status.
- [x] Remove the bespoke coverage controller and use `pytest-cov`.

#### Task 7.4 — Replay

- [x] Replace generated executable PowerShell with checked-in
  `scripts/replay_test_receipt.py`.
- [x] Require invocation through:

  ```powershell
  .\.venv\Scripts\python.exe scripts\replay_test_receipt.py <path-to-run.json>
  ```

- [x] Load node IDs from JSON as data.
- [x] Verify repository root and `.venv` interpreter.
- [x] Refuse a receipt from a different repository unless explicitly permitted.
- [x] Report Git/native/resource mismatches before rerunning.

**Gates:**

```powershell
.\.venv\Scripts\python.exe -m pytest tests\harness_meta\test_lifecycle_policy.py tests\harness_meta\test_artifact_policy.py tests\harness_meta\test_xdist_policy.py tests\harness_meta\test_replay_receipt_policy.py -q -p pytester
.\.venv\Scripts\python.exe scripts\replay_test_receipt.py <focused-failure-receipt>
```

#### Phase 7 completion checkpoint — 2026-07-30

- Lifecycle evidence now records setup, call, and teardown outcomes and
  `perf_counter()` durations independently, aggregates complete attempts by
  node ID, distinguishes non-running phases from skips, and applies finite,
  nonnegative case budgets only after teardown. An existing test failure
  remains primary while a budget overrun is attached as evidence. Total-budget
  status is decided only after inner session finalizers and receipt
  finalization.
- Retry grouping is lifecycle-derived rather than phase-counter-derived.
  A fail-then-pass attempt under the same receipt is the only condition called
  a flake; fail-then-skip and ordinary failures remain failures. Collection
  errors, teardown failures, worker crashes, and interrupted worker shutdowns
  remain visible, and crash node IDs are admitted to the exact rerun set.
- Ephemeral evidence is controller-owned beneath
  `.pytest_cache/moira-artifacts/<run-id>/`. Run IDs are strict single path
  components; collisions, symlinks/reparse points, and unsafe paths fail
  closed. `INCOMPLETE` is created before execution and replaced by a
  content-binding `COMPLETE` marker only after the exact fixed artifact set has
  been written through exclusive temporary files, flushed, size-checked, and
  atomically replaced. No transient receipt is written beneath
  `tests/artifacts/`.
- The fixed receipt comprises `run.json`, `collection.json`,
  `resources.json`, `reports.jsonl`, `failures.json`, `durations.json`, and
  `rerun-nodeids.json`. Per-record and per-run limits are enforced. Structured
  redaction covers secret-bearing environment names, headers, cookies, bearer
  credentials, URL credentials, assignment tokens, command-line secret
  arguments, and fixture-scoped secrets across the complete lifecycle.
- The controller consumes canonical xdist reports and worker terminal state.
  Worker-provided classification, planetary-resource, and small-body-resource
  evidence is resealed after inner session-finish hooks and independently
  reconciled; a worker cannot spoof absent resource evidence. Workers never
  compete over shared artifact files. The obsolete merge helper and bespoke
  coverage controller were removed; coverage remains the responsibility of
  `pytest-cov`.
- Resource receipts carry structured requirements and capabilities.
  Planetary artifacts are bound by stable metadata plus a streaming content
  SHA-256 digest, and replay detects same-size content substitution even when
  timestamps are restored. Repository state includes HEAD, binary diff, and
  length-delimited stable untracked content; native identity includes resolved
  path, locality, size, hash, and version. Ambient execution switches that can
  select native or Python paths are recorded explicitly.
- `scripts/replay_test_receipt.py` treats every receipt field as hostile data:
  bounded strict JSON rejects duplicate keys, non-finite values, excess depth,
  and oversized inputs; the exact completed file set and every sidecar digest
  are verified; recorded commands and paths are never executed or
  dereferenced. Exact node IDs are passed after `--` through a non-shell
  subprocess. Repository, `.venv`, Git, native, execution-switch, and resource
  identities must match unless their specific mismatch is acknowledged.
  Resource state is resealed immediately before launch, and the child
  environment is sanitized and rebuilt from the recorded policy.
- Verification used project `.venv` Python 3.14.3 with
  `MOIRA_TEST_MODE=1`, `MOIRA_NO_DOWNLOAD=1`, and
  `MOIRA_STRICT_KNOWN_ISSUES=1`. The consolidated lifecycle, artifact, xdist,
  and replay-policy gate passed 110 cases. The planetary and small-body
  resource-policy gate passed 100 cases. The replay-policy lane passed all 33
  cases under two workers, and the conftest smoke passed eight cases with six
  DE441 RUN receipts. A deliberate one-node case-budget failure produced a
  COMPLETE receipt, passed all replay preflight checks, and replayed the exact
  node successfully after replay sanitized the deliberate budget.
- This checkpoint does not claim the literal full suite, live external-network
  comparison, authority/oracle validation, or new scientific precision.
  Phase 7 changed test policy, harness-meta evidence, replay tooling, and this
  checkpoint only. Engine computation, native substrate, protected scientific
  baselines, release workflows, and unrelated concurrent work were left
  untouched.

---

### Phase 8 — Extract the monolith one proved policy at a time

**Purpose:** improve architecture without hiding behavioral changes inside a
large refactor.

Extraction order:

1. configuration and known issues;
2. determinism;
3. network policy;
4. resource policy;
5. classification;
6. lifecycle and budgets;
7. artifacts and xdist;
8. evidence;
9. remaining domain fixtures.

For each extraction:

- [x] run its harness-meta test before editing;
- [x] move only one policy;
- [x] register it from root `tests/conftest.py`;
- [x] use `pytest.StashKey`;
- [x] rerun its meta test and the existing smoke;
- [x] run `git diff --check`;
- [x] inspect the diff for accidental behavior changes;
- [x] record the checkpoint before continuing.

Do not set an arbitrary line-count target. The desired property is that
`tests/conftest.py` becomes a legible registration and shared-fixture surface,
not merely a shorter file.

#### Phase 8 in-progress stopping checkpoint — 2026-07-30

**Status:** deliberately paused after extraction step 7. Phase 8 is not
complete.

- Extraction steps 1 through 7 now have dedicated owners:
  `configuration.py`, `known_issues.py`, `determinism.py`,
  `network_policy.py`, `resources.py`, `classification.py`, `lifecycle.py`,
  `artifacts.py`, and `xdist_coordination.py`. `_state.py` owns the shared
  dataclasses and `pytest.StashKey` identities; `_common.py` owns the small
  secure-filesystem primitive shared by resource and artifact policy.
- Repository-root `conftest.py` now sanitizes the `_pytest_plugins` namespace,
  bridges historic option registration, and fail-closed registers the exact
  required plugin manifest. Blocking a required plugin with `-p no:...`,
  loading it from a foreign origin, loading it under a second alias, or
  unregistering it late is rejected.
- Xdist controller and worker state no longer uses ad hoc attributes on
  `pytest.Config`. Classification aggregation, violation buffers, expected and
  reported workers, and merged planetary and small-body reports use canonical
  typed stash keys. Wire dictionaries remain limited to the explicit
  worker-input and worker-output transport boundary.
- Lifecycle and artifact report wrappers have an explicit tested order:
  lifecycle observes all inner report mutations and seals setup/call/teardown
  and budget evidence; the later-registered artifact wrapper then creates the
  redacted shadow. Artifact collection and finalization are controller-owned;
  xdist owns the one explicit session-finish coordinator.
- `tests/conftest.py` is now the standalone-registration guard, `collect_ignore`
  declaration, tests-scoped resource/domain/evidence fixture export surface,
  and terminal presentation surface. This is an ownership checkpoint, not a
  line-count claim.
- `evidence.py` is intentionally still a placeholder. Snapshot, golden,
  ritual, numeric-domain fixtures, and terminal presentation have not yet been
  assigned their final Phase 8 ownership. No fixture has been made globally
  visible merely to shorten `tests/conftest.py`.

**Verified stopping seam:**

- `44 passed` — execution-classification and xdist scheduling, worker
  resealing, controller reconciliation, and serial/parallel semantic receipts;
- `24 passed` — controller-owned artifacts, redaction, limits, collision and
  reparse refusal, worker crashes, and xdist artifact ownership;
- `9 passed` — setup/call/teardown lifecycle and case/total-budget ordering;
- `100 passed` — planetary and supplemental small-body resource admission,
  reporting, and xdist aggregation after the stash-key migration;
- `17 passed` — required-plugin suppression attacks, canonical-origin and
  import-sanitizer attacks, and hostile determinism reset cases;
- `33 passed` — exact receipt replay and hostile receipt parsing;
- `98 passed` — immutable snapshot/golden baseline contracts, establishing the
  pre-extraction evidence baseline for tomorrow;
- `8 passed` — the existing conftest smoke, including six DE441 RUN receipts.

The project `.venv` was Python 3.14.3. All stopping-seam runs used
`MOIRA_TEST_MODE=1`, `MOIRA_NO_DOWNLOAD=1`, and
`MOIRA_STRICT_KNOWN_ISSUES=1`. Focused Ruff returned clean, every current
plugin and conftest compiled, all current plugin sources parsed with the Python
3.10 grammar, and `git diff --check` passed. The earlier focused network
extraction gate passed 66 cases with two expected platform skips where
`socket.sendmsg` is unavailable.

**Resume here:**

1. Re-run `git status --short --branch`, confirm
   `.\.venv\Scripts\python.exe --version`, and read
   `tests\KNOWN_ISSUES.yml`.
2. Re-run the 98-case baseline-policy gate before editing evidence ownership:

   ```powershell
   $env:MOIRA_TEST_MODE = "1"
   $env:MOIRA_NO_DOWNLOAD = "1"
   $env:MOIRA_STRICT_KNOWN_ISSUES = "1"
   .\.venv\Scripts\python.exe -m pytest tests\harness_meta\test_baseline_policy.py -q -p pytester
   ```

3. Extract evidence policy without widening fixture visibility. Add focused
   registration contracts for `ritual`, `moira_approx`, `assert_longitude`,
   and `eclipse_calculator` before moving or re-exporting them.
4. Strengthen `test_plugin_architecture_policy.py` to prove hook flags and
   unique hook/fixture ownership, absence of extracted duplicate hooks in
   `tests/conftest.py`, and one canonical identity for every shared stash key.
5. Prove real-checkout registration under no positional argument, `tests`,
   `.`, an exact node ID, and alternate `-c` configuration.
6. Run the final parallel and serial harness-meta gates, the conftest smoke,
   focused Ruff/compile/Python-3.10 parsing, and `git diff --check`; only then
   mark Phase 8 complete.

This checkpoint does not claim the full harness-meta matrix, the literal full
configured suite, live external-network execution, scientific oracle or
authority validation, native parity, or Phase 8 completion. No commit, push,
tag, pull request, release, or deployment was performed. Engine computation,
native substrate, protected scientific baselines, and unrelated concurrent
worktree changes were intentionally left untouched.

#### Phase 8 completion checkpoint — 2026-07-31

**Status:** complete.

- `tests/_pytest_plugins/evidence.py` is the single owner of
  `pytest_terminal_summary`. The hook retains ordinary, non-wrapper ordering
  and presents harness configuration, network, execution classification,
  resource, lifecycle, case-budget, duration, and regression evidence.
  `tests/conftest.py` no longer contains a second terminal-summary hook or its
  presentation-only imports.
- Snapshot, golden, ritual, numeric-domain, eclipse, epoch, chart, and
  resource fixtures intentionally remain in `tests/conftest.py`. This is the
  final tests-scoped shared-fixture surface, not an unfinished extraction.
  Moving fixture decorators into a root-registered plugin would widen their
  visibility. Architecture contracts prove that `snapshot`, `golden`,
  `ritual`, `moira_approx`, `assert_longitude`, and `eclipse_calculator` each
  have exactly one owner beneath the `tests` base ID, with their original
  function or session scope.
- The architecture policy now admits an exact hook manifest for every required
  plugin, including function identity, wrapper versus legacy hookwrapper
  semantics, `tryfirst`/`trylast`, and optional-hook status. It rejects
  uncontracted hooks, duplicate conftest policy hooks, fixture re-export,
  wrapper-order drift, any `pytest.StashKey` construction outside `_state.py`,
  duplicate stash identities, and noncanonical imported key objects. Static
  source admission covers every module and auxiliary-object
  `@pytest.hookimpl`, closing the optional-hook/no-HookCaller escape.
- Controller report and lifecycle evidence is sealed and validated exactly
  once during session finalization, before artifact policy branches on whether
  output is enabled. Pre-existing collector-integrity errors, duplicate
  phases, cross-worker cases, and contradictory duration or budget evidence
  now elevate an otherwise successful session even when
  `MOIRA_TEST_ARTIFACTS=0`; terminal presentation and artifact materialization
  consume the same sealed payload. Hostile pre-seal-error and duplicate-call
  probes prove this fail-closed behavior without creating an artifact
  directory.
- Real-checkout serial canaries prove required-plugin registration with no
  positional path, `tests`, `.`, an exact node ID, and an alternate explicit
  `-c` file. The children use the invoking interpreter, disable ambient plugin
  autoload, scrub inherited pytest/xdist/policy switches plus `PYTEST_PLUGINS`
  and `PYTHONPATH`, perform no downloads, and collect only the architecture
  module. They require one explicit `PASSED` record for the exact manifest
  probe and reject skip/xfail/xpass outcomes. This avoids both outcome
  false-greens and a recursively self-running canary while still exercising
  real conftest discovery.

**Verification receipt:**

- The pre-edit and post-extraction immutable-baseline gate each passed all
  `98` cases.
- The final plugin-architecture gate passed all `66` cases, including the
  single-emission terminal receipt, exact hook flags and ownership, fixture
  ownership, stash identity, static optional-hook closure, auxiliary collector
  hooks, required-plugin suppression attacks, and local module identity.
- The focused lifecycle, artifact, and xdist regression gate passed all `79`
  cases, including artifact-disabled pre-seal and lifecycle-corruption
  attacks.
- The five direct invocation-shape canaries passed. In the final serial
  harness-meta lane they ran alongside the serial-lane canary: `6` selected
  and `6` passed.
- The complete parallel harness-meta lane collected `581`, selected `575`
  parallel cases, and completed with `573` passed plus two expected
  platform skips because `socket.sendmsg` is unavailable. The complementary
  serial lane selected the remaining `6`, so every collected harness-meta
  case was admitted to exactly one lane.
- The conftest smoke passed all `8` cases and recorded six successful DE441
  planetary-resource receipts from one content probe.
- Focused Ruff, bytecode compilation, Python 3.10 grammar parsing, and scoped
  whitespace checks passed for the Phase 8 Python files. `git diff --check`
  reported no whitespace error. The scoped run emitted an LF-to-CRLF warning
  for `tests/conftest.py`; the repository-wide run likewise emitted only
  line-ending normalization warnings across the existing dirty worktree.
- One interim parallel rerun encountered a transient unmatched parenthesis in
  unrelated concurrent `moira/heliacal.py` work during collection. Phase 8 did
  not edit or restore that file. After the concurrent edit settled,
  `py_compile` succeeded and the final exact-state parallel and serial lanes
  passed with the matching `581`-item collection digest.

All commands used the project `.venv` under Python 3.14.3 with
`MOIRA_TEST_MODE=1`, `MOIRA_NO_DOWNLOAD=1`, and
`MOIRA_STRICT_KNOWN_ISSUES=1`. This checkpoint does not claim the literal full
configured suite, live external-network execution, scientific
oracle/authority validation, native parity, or any new astronomical
precision. No commit, push, tag, pull request, release, or deployment was
performed. Engine computation, native substrate, approved scientific
baselines, and unrelated concurrent worktree changes were intentionally left
untouched.

---

### Phase 9 — Evidence contracts and the assurance matrix

**Purpose:** make validation claims machine-checkable.

#### Task 9.1 — Contract schema

For admitted validation tests, support:

- stable claim ID;
- product or public surface;
- evidence class;
- governing object;
- authority, fixture, corpus, and version/hash where applicable;
- frame;
- origin;
- timescale;
- correction policy;
- units and metric;
- tolerance plus derivation;
- bodies and interval;
- resource capability;
- Python/native path;
- exclusions;
- expected refusal behavior.

Not every ordinary unit test requires a full scientific contract. Require it
when newly admitting or deliberately migrating an authority, oracle, protected
golden, release-claim, or selected protected-zone validation surface. Legacy
surfaces outside the four Phase 9 exemplars remain explicit migration debt;
their existence does not silently admit them into this matrix.

#### Task 9.2 — Exemplar admission

Start with four exemplars:

1. content-derived SPK identity;
2. a coordinate-transform invariant;
3. a source-owned astrology doctrine case;
4. one admitted Python/native parity surface.

For each exemplar:

- [x] name what the test proves;
- [x] name what it does not prove;
- [x] validate the schema during collection;
- [x] emit the contract in the run receipt;
- [x] generate an assurance-matrix row.

#### Task 9.3 — Evidence-aware coverage

- [x] Use pytest-cov/coverage contexts to associate executed code with test or
  evidence class.
- [x] Implement and adversarially test reporting for reviewed protected targets
  reached only by regression snapshots. No regression contract is among the
  four currently admitted exemplars, so the current result is an empty list
  scoped only to declared protected assurance targets.
- [x] Do not turn line or branch coverage percentage into a scientific gate.
- [x] Gate missing required evidence cells, not an arbitrary global percentage.

**Static and broad policy gate:**

```powershell
$env:MOIRA_TEST_MODE = "1"
$env:MOIRA_NO_DOWNLOAD = "1"
$env:MOIRA_STRICT_KNOWN_ISSUES = "1"
$env:MOIRA_TEST_ARTIFACTS = "0"
.\.venv\Scripts\python.exe -m pip install -e .
.\.venv\Scripts\python.exe scripts\build_test_assurance_matrix.py --check-static
.\.venv\Scripts\python.exe -m pytest tests\harness_meta tests\unit\test_spk_kernel_identity.py tests\unit\test_house_projection_geometry.py tests\unit\test_hellenistic_source_goldens.py tests\unit\test_native_nutation_2000a.py -q
```

**Serial assurance receipt:**

```powershell
$phase9Root = (Resolve-Path .).Path
$env:MOIRA_TEST_MODE = "1"
$env:MOIRA_NO_DOWNLOAD = "1"
$env:MOIRA_STRICT_KNOWN_ISSUES = "1"
$env:MOIRA_TEST_ARTIFACTS = "1"
$env:MOIRA_TEST_RUN_ID = "phase9-assurance-serial-20260731-f"
$env:COVERAGE_CORE = "ctrace"
$env:COVERAGE_FILE = Join-Path $phase9Root ".pytest_cache\phase9-assurance-serial-20260731-f.coverage"
$phase9Receipt = Join-Path $phase9Root ".pytest_cache\moira-artifacts\phase9-assurance-serial-20260731-f"
.\.venv\Scripts\python.exe -m pytest --cov=moira --cov-config=pyproject.toml --cov-context=test --cov-report= tests\unit\test_spk_kernel_identity.py tests\unit\test_house_projection_geometry.py tests\unit\test_hellenistic_source_goldens.py tests\unit\test_native_nutation_2000a.py -q
.\.venv\Scripts\python.exe scripts\build_test_assurance_matrix.py --check --receipt-dir $phase9Receipt --coverage-file $env:COVERAGE_FILE
```

**xdist assurance receipt:**

```powershell
$phase9Root = (Resolve-Path .).Path
$env:MOIRA_TEST_MODE = "1"
$env:MOIRA_NO_DOWNLOAD = "1"
$env:MOIRA_STRICT_KNOWN_ISSUES = "1"
$env:MOIRA_TEST_ARTIFACTS = "1"
$env:MOIRA_TEST_RUN_ID = "phase9-assurance-xdist-20260731-f"
$env:COVERAGE_CORE = "ctrace"
$env:COVERAGE_FILE = Join-Path $phase9Root ".pytest_cache\phase9-assurance-xdist-20260731-f.coverage"
$phase9Receipt = Join-Path $phase9Root ".pytest_cache\moira-artifacts\phase9-assurance-xdist-20260731-f"
.\.venv\Scripts\python.exe -m pytest -n 2 --dist=load -m parallel --cov=moira --cov-config=pyproject.toml --cov-context=test --cov-report= tests\unit\test_spk_kernel_identity.py tests\unit\test_house_projection_geometry.py tests\unit\test_hellenistic_source_goldens.py tests\unit\test_native_nutation_2000a.py -q
.\.venv\Scripts\python.exe scripts\build_test_assurance_matrix.py --check --receipt-dir $phase9Receipt --coverage-file $env:COVERAGE_FILE
```

#### Phase 9 completion record — 2026-07-31

Phase 9 admits exactly four reviewed claims: SPK content identity, the
equatorial/ecliptic house-helper round trip, the Pingree 1976 Dorothean
triplicity table, and the packaged nutation Python/native parity boundary.
This is an explicit exemplar admission boundary, not a claim that every legacy
oracle, golden, or release-facing validation test has already migrated to a
machine contract.

The implemented contract layer now fails closed on missing markers for a
reviewed node, unknown or duplicate claim IDs, nonexistent test callables,
stale scoped executable-protocol digests, malformed fields, conflicting or
duplicate report properties, post-collection marker mutation, missing
selected-item reports, and worker receipts that contradict the controller's
current registry. Executable protocols use a canonical, dependency-closed AST
digest: line endings, comments, formatting, and unrelated functions do not
change it; non-introspected function/class docstrings and unrelated rebound
names are also excluded. Parametrization, decorators, runtime assertion text,
assertions, referenced local helpers/constants, import bindings, and the house
exemplar's shared numeric assertion implementation do change it. Selected or
dependency-closed rebinding is rejected. Byte hashes remain authoritative for
the actual golden and coefficient assets. Contract comparison objects are the
executable tolerance source for the admitted house and native assertions; the
native exemplar uses direct absolute residual comparisons rather than ambient
`pytest.approx` relative semantics. The independently reviewed required cell
also pins the complete contract digest.
The native exemplar additionally checks exact parsed term counts, j=0
boundaries, and term shape, while its contract expressly does not claim
independent IERS/parser authenticity.

The independent assurance requirements pin all 24 full parametrized node IDs,
not base-node counts. A same-count parameter replacement therefore fails. The
runtime join requires every passed node bound to a claim to reach every target
declared by that claim under its own `|run` context. Coverage 7.13.5's default
Python 3.14 SysMonitor core was adversarially demonstrated to lose repeated
dynamic contexts, so the gate requires explicit `COVERAGE_CORE=ctrace`. It
does not trust that request as proof: the receipt captures pytest-cov's active
`Coverage` object before shutdown, requires the resolved tracer to be
`CTracer`, and records one attestation from the controller and every xdist
worker. The finalized xdist shutdown roster must exactly equal that worker
attestation set; missing, duplicate, failed, or unfinalized workers fail the
gate. Each contributor seals both start and finish run contexts, including its
repository, interpreter, native backend, execution switches, and toolchain,
and must equal the controller. This deliberately admits the local `-n` lane,
not path-divergent remote workers. A `timid=true` canary proves that a requested
`ctrace` can otherwise resolve to `PyTracer` and is rejected.

The controller seals the exact coverage path, byte count, SHA-256, mtime,
active tracer, effective coverage configuration, actual configuration-file
path/hash, pytest-cov options, Python executable bytes/hash, toolchain versions,
and controller/worker identities in `run.json`. The assurance command names
`pyproject.toml` explicitly; ambient `COVERAGE_RCFILE`,
`COVERAGE_FORCE_CONFIG`, and process-start configuration are forbidden. Runtime
evaluation rejects a copied, rewritten, postdated, appended, or otherwise
unsealed coverage database; source, git, interpreter, execution-switch,
native-backend, config, or toolchain drift; non-project-venv execution;
non-strict known issues; downloads; and external-network admission. Durable
`reports.jsonl` identities are reconciled independently, and artifact redaction
cannot change evidence or coverage identity. The receipt remains self-hashed
cooperative evidence, not a cryptographic signature or security sandbox.

Native identity is not inferred from extension freshness. A deterministic
schema-v2 manifest covers `CMakeLists.txt`, `setup.py`, the manifest algorithm,
the build-affecting `pyproject.toml` sections, and every admitted native
source/header/build suffix beneath `src/native`. Its no-follow traversal rejects
links, junctions, and reparse points before descent while ignoring unrelated
native-tree files and pytest-only configuration. The editable build copies the
exact manifested inputs into a private snapshot, verifies that snapshot, builds
only from it, and checks the source manifest again after compilation. The
extension embeds one tagged manifest SHA-256. Runtime identity requires the raw
module, spec, `ExtensionFileLoader` filename/path, and extension file to agree;
it scans the loader-owned binary and requires that disk marker to match the
already-loaded built-in marker. The receipt records the binary identity and
every current input path/byte count/hash, then independently recomputes and
requires exact equality. A stale, foreign, path-forged, or source-raced `.pyd`
therefore cannot fill the native-parity cell merely because it remains
importable. This is still cooperative in-process attestation, not a defense
against arbitrary hostile code that already controls the Python process.

The final combined harness-meta and exemplar regression gate collected `699`
cases: `697` passed and the two `socket.sendmsg` cases skipped because that API
is unavailable on this platform. It selected all `24` reviewed evidence items
under four contracts. The static assurance generator reported all four required
cells present. The exact final serial and xdist receipt IDs, paths, and commands
are fixed above; their coverage hashes live in the self-hashed `run.json` and
runtime matrix output rather than being copied back into this mutable plan.
No global line or branch percentage is used as scientific evidence.

---

### Phase 10 — Metamorphic and numerical-boundary assurance

**Purpose:** discover unknown numerical failures without inventing expected
values.

Candidate relations:

- coordinate round trips measured by vector angular separation;
- center-chain vector composition;
- longitude periodicity under lawful normalization;
- TT/UT conversion round trips;
- velocity versus conditioned finite-difference position;
- event root residual at the reported solution;
- bracket-refinement stability;
- step-halving convergence;
- explicit default versus named-default equivalence;
- serialization preserving policy and provenance;
- Python/native agreement on admitted shared semantics.

Boundary atlas:

- exact 0°, 360°, and ±180° seams;
- `nextafter()` on both sides of thresholds;
- signed zero and subnormal magnitudes;
- poles, antipodes, tangent/double roots, and grazing events;
- calendar and timescale boundaries;
- kernel segment starts, ends, gaps, and overlaps;
- NaN, infinity, and extreme finite input rejection;
- fallback-policy thresholds.

For every admitted relation:

- [x] name the mathematical/doctrinal object;
- [x] provide derivation or primary source;
- [x] define ambiguity and branch policy;
- [x] define conditioning domain and exclusions;
- [x] define units and tolerance;
- [x] prove the relation fails under at least one appropriate canary mutation.

Use targeted Hypothesis metrics such as maximum residual, iteration count,
condition number, or proximity to a declared boundary. Do not use unguided
randomness as the sole boundary strategy.

#### Phase 10 bounded admission and verification

Phase 10 admits three kernel-free invariant claims. Candidate relations not
listed here remain future migration work; the candidate catalogue was not
silently converted into an assertion that every numerical surface is now
metamorphically assured.

1. `MOIRA-COORD-ECLIPTIC-EQUATORIAL-SPHERE-INVERSE-V1` governs a unit
   direction acted on by the public ecliptic/equatorial x-axis obliquity
   rotation and its inverse. Both transform directions are compared by stable
   Cartesian vector angular separation, never scalar longitude at a pole. The
   generated interior domain uses source latitudes and declinations in
   `[-89, 89]` degrees, quotient angles in `[-1440, 1440]` degrees, and
   obliquity in `[-30, 30]` degrees with an absolute `1e-10` degree vector
   bound. A separate exact/`nextafter()` seam and polar atlas through
   `+/-90` degrees uses the explicitly conditioned `2e-6` degree bound. A
   finite one-degree recovered-latitude observation mutant must fail the same
   typed maximum-vector-separation predicate used by production observations.
2. `MOIRA-COORD-LONGITUDE-QUOTIENT-V1` governs the quotient circle
   `S1 = R / 360Z` represented by `[0, 360)` degrees. It checks canonical
   membership, exact idempotence, positive-zero ownership, and period shifts
   from `-16` through `+16` over generated base angles `[-360, 360]`, plus
   exact/`nextafter()` 0, 180, and 360 degree seams. The circular period-shift
   limit is `1e-12` degrees. A zero-to-360 observation mutant must fail the
   exact half-open-range predicate.
3. `MOIRA-TIMESCALE-HYBRID-UT1-TT-INVERSE-V1` governs the clock graph
   `F(u) = u + DeltaT(u) / 86400` from JD UT1 to JD TT and its inverse on the
   same default hybrid source-selection surface. Omitted policy and explicit
   `DeltaTPolicy(model="hybrid")` must be bit-identical in both directions;
   recovered UT1 must be within two maximum coordinate ULPs. The admitted
   interval is JD `[1355817.5, 3547272.5]`, proleptic years `-1000` through
   `5000`, with exact and adjacent `nextafter()` probes at the named historical
   and model seams. Both public clock transforms separately reject NaN,
   infinities, and grossly unrepresentable finite JDs. A finite one-second
   recovered-UT1 observation mutant must fail the same typed ULP predicate.

Each claim binds the exact test protocol, its observation/assertion support,
and the shared typed `MetamorphicViolation` primitive with dependency-closed
canonical Python AST hashes. Numeric limits come from the reviewed evidence
contracts rather than duplicate test-owned tolerances. Every canary mutates an
immutable finite observation after the production calls return; none edits an
engine file or compiled extension, and none is presented as Phase 11 source
mutation. Contract-bound Hypothesis tests must inherit the receipted harness
profile: collection now rejects an explicit test-level `@settings(...)`
because the former receipt recorded only the global profile and could
otherwise overstate the executed example count. `tests/metamorphic/` is a
first-class primary execution class and every admitted item is explicitly
parallel/read-only.

The independent matrix now requires seven cells and 38 exact bound items: the
four retained Phase 9 claims plus 14 Phase 10 items under these three new
claims. The generated JSON/Markdown matrix remains percentage-free. Its
admission scope is `phase9_and_phase10_reviewed_claims`.

**Broad serial regression gate:**

```powershell
$env:MOIRA_TEST_MODE = "1"
$env:MOIRA_NO_DOWNLOAD = "1"
$env:MOIRA_STRICT_KNOWN_ISSUES = "1"
$env:MOIRA_TEST_ARTIFACTS = "0"
.\.venv\Scripts\python.exe -m pytest tests\harness_meta tests\metamorphic tests\unit\test_spk_kernel_identity.py tests\unit\test_house_projection_geometry.py tests\unit\test_hellenistic_source_goldens.py tests\unit\test_native_nutation_2000a.py tests\unit\test_julian_delta_t.py tests\unit\test_low_level_helpers.py tests\unit\test_conftest_smoke.py -q
```

This collected 880 cases: 878 passed and the two `socket.sendmsg` capability
cases skipped because that API is unavailable on this platform. All 38
reviewed items were selected under seven contracts. The scoped Ruff gate over
all Phase 10 Python changes passed, the static matrix reported seven cells,
and the loaded native schema-v2 build-input digest still exactly matched the
current checkout (`7daa131c671611e82fc00c94aee65f8cde61d0f200a37c4a7138d675f2c4c735`),
so pytest-only configuration did not require a native rebuild.

**Serial assurance receipt:**

```powershell
$phase10Root = (Resolve-Path .).Path
$env:MOIRA_TEST_MODE = "1"
$env:MOIRA_NO_DOWNLOAD = "1"
$env:MOIRA_STRICT_KNOWN_ISSUES = "1"
$env:MOIRA_TEST_ARTIFACTS = "1"
$env:MOIRA_TEST_RUN_ID = "phase10-assurance-serial-20260801-b"
$env:COVERAGE_CORE = "ctrace"
$env:COVERAGE_FILE = Join-Path $phase10Root ".pytest_cache\phase10-assurance-serial-20260801-b.coverage"
$phase10Receipt = Join-Path $phase10Root ".pytest_cache\moira-artifacts\phase10-assurance-serial-20260801-b"
.\.venv\Scripts\python.exe -m pytest --cov=moira --cov-config=pyproject.toml --cov-context=test --cov-report= tests\unit\test_spk_kernel_identity.py tests\unit\test_house_projection_geometry.py tests\unit\test_hellenistic_source_goldens.py tests\unit\test_native_nutation_2000a.py tests\metamorphic -q
.\.venv\Scripts\python.exe scripts\build_test_assurance_matrix.py --check --receipt-dir $phase10Receipt --coverage-file $env:COVERAGE_FILE
```

All 66 selected-file tests passed, including the exact 38 contract-bound
items. The runtime matrix filled all seven required cells with CTracer
per-test contexts. The exact coverage SHA-256 remains sealed in the immutable
receipt rather than being copied into this mutable plan; the 26 unattributed
contexts are ordinary non-contract tests co-located in the four Phase 9
exemplar files.

**xdist assurance receipt:**

```powershell
$phase10Root = (Resolve-Path .).Path
$env:MOIRA_TEST_MODE = "1"
$env:MOIRA_NO_DOWNLOAD = "1"
$env:MOIRA_STRICT_KNOWN_ISSUES = "1"
$env:MOIRA_TEST_ARTIFACTS = "1"
$env:MOIRA_TEST_RUN_ID = "phase10-assurance-xdist-20260801-b"
$env:COVERAGE_CORE = "ctrace"
$env:COVERAGE_FILE = Join-Path $phase10Root ".pytest_cache\phase10-assurance-xdist-20260801-b.coverage"
$phase10Receipt = Join-Path $phase10Root ".pytest_cache\moira-artifacts\phase10-assurance-xdist-20260801-b"
.\.venv\Scripts\python.exe -m pytest -n 2 --dist=load -m parallel --cov=moira --cov-config=pyproject.toml --cov-context=test --cov-report= tests\unit\test_spk_kernel_identity.py tests\unit\test_house_projection_geometry.py tests\unit\test_hellenistic_source_goldens.py tests\unit\test_native_nutation_2000a.py tests\metamorphic -q
.\.venv\Scripts\python.exe scripts\build_test_assurance_matrix.py --check --receipt-dir $phase10Receipt --coverage-file $env:COVERAGE_FILE
```

The distributed lane collected 66, selected the exact 38 parallel reviewed
items, deselected 28 ordinary/local items, and passed all 38. The reconciled
runtime matrix again filled all seven cells. The exact coverage SHA-256 is
sealed in that immutable receipt; one import-time coverage context was
intentionally unattributed.

#### Phase 10 adversarial findings and explicit deferrals — 2026-08-01

The attempted equatorial/horizontal inverse relation discovered a real
protected engine defect and was refused from admission. At observer latitude
`40` degrees with `LST = RA = 100` degrees and input declination `+90`
degrees, `equatorial_to_horizontal()` returns azimuth `0` and altitude `40`.
`horizontal_to_equatorial(0, 40, 100, 40)` then takes the compatibility branch
that calls this pair a legacy zenith surrogate and returns declination `40`
instead of the north celestial pole at `+90`: a 50-degree direction error.
True zenith has altitude `+90`; `(azimuth=0, altitude=observer latitude)` is the
north celestial pole for a nonpolar observer. The existing low-level test
encodes the false compatibility behavior, and the lineage tracker still marks
this inverse as rewritten-pending-oracle. Neither engine code nor that test was
changed under this testing-infrastructure phase. Repair requires a separate
protected coordinate decision, correction, external-oracle review, and
targeted regression admission.

Calendar conversion refusal is also deferred. `julian_day()`,
`calendar_from_jd()`, and their native counterparts currently declare no
input-validation contract; raw invalid native calendar probes can reach
unchecked floating-to-integer casts. Phase 10 did not invent rejection
semantics or execute unsafe invalid-native cases. Server serialization remains
deferred because the current assurance coverage source is exactly `moira`,
while serialization lives in `moira_server` and the base development surface
does not guarantee the server optional dependency. Center-chain, event-root,
finite-difference, kernel-segment, default-house-policy, and extended
Python/native candidates remain explicit later Phase 10 expansion work rather
than unverified claims.

This bounded Phase 10 admission changed only validation infrastructure,
contracts, generated assurance policy, tests/support, and this plan. It did
not change engine mathematics, public semantics, native code, scientific
tables, oracle/golden baselines, or approved tolerances outside the three new
contracts. No commit, push, tag, pull request, release, or deployment was
performed, and unrelated dirty-worktree changes were preserved.

---

### Phase 11 — Scientific mutation assurance

**Purpose:** test whether the suite can distinguish plausible wrong answers.

Initial curated mutation catalogue:

- UT substituted for TT;
- ΔT applied twice;
- observer/target or target/center reversal;
- degrees/radians exchange;
- seconds/days or kilometres/AU conversion removal;
- apparent/geometric or topocentric/geocentric exchange;
- omission of a declared correction stage;
- sign or frame reversal;
- SPK coefficient or endian reversal;
- inclusive/exclusive coverage endpoint change;
- longitude normalization defect;
- solver tolerance weakened by ten times;
- requested/effective house policy exchange;
- stale native-dispatch cache.

Mutation result schema:

```text
fault archetype
→ mutant ID
→ expected killing test/claim
→ actual killing test
→ evidence class
→ outcome
```

Critical mutants must be killed by the intended evidence test, not by import
failure or an unrelated assertion.

`critical` and `supplemental` are assurance-admission tiers, not estimates of
scientific, product, or user-impact severity. A critical admission must be
killed by its exact contract-bound typed metamorphic witness. A supplemental
admission may instead be killed by its exact named authority, invariant, or
Python/native-parity vessel, but receives no weaker source, execution, or
receipt scrutiny. Neither label ranks the underlying production fault.

Run source mutations only in a disposable worktree, isolated copy, or admitted
mutation tool environment. Never mutate the user's working tree in place.
Evaluate any new mutation dependency as development tooling; do not add it to
base runtime.

#### Phase 11 bounded admission — 2026-08-01

Phase 11 admits six reviewed Python-source mutants. It is an all-declared gate,
not a mutation-score percentage and not a claim that every candidate archetype
above is now covered. Three mutants are critical typed-metamorphic probes and
three are supplemental authority, invariant, or Python/native-parity probes.
Each mutant binds one exact source target, one exact leaf test, one evidence
contract digest, one expected exception/witness, and explicit exclusions.

| Mutant | Class | Production fault | Intended killer and evidence class |
|---|---|---|---|
| `P11-COORD-INVERSE-LATITUDE-CROSS-TERM-SIGN` | critical | reverse the obliquity cross-term sign in the ecliptic-latitude numerator of `equatorial_to_ecliptic()` | spherical boundary atlas; invariant |
| `P11-DOROTHEAN-SECT-RULERS-SWAPPED` | supplemental | exchange day/night Dorothean rulers in `triplicity_assignment_for()` | named Pingree-table golden; authority |
| `P11-LONGITUDE-ENDPOINT-EXCLUSION-LOST` | critical | change the `360` endpoint guard in `normalize_degrees()` from inclusive to exclusive | longitude quotient boundary atlas; invariant |
| `P11-NUTATION-PY-DPSI-SIGN-REVERSED` | supplemental | reverse Python scalar `dpsi` in `_nutation_python()` | exact J2000 Python/native leaf; native parity |
| `P11-SPK-FIRST-SUMMARY-WINS` | supplemental | replace mixed-content identity refusal with first-summary selection | mixed-summary refusal/release leaf; invariant |
| `P11-TIMESCALE-DELTA-T-DOUBLE-FORWARD` | critical | apply Delta-T twice in `ut_to_tt()` | hybrid UT1/TT boundary atlas; invariant |

The authoritative catalogue is `tests/mutations/catalogue.json`, schema 1,
with SHA-256
`831ca1c0b75dd7d8b8dd8a0cd2187360f62b5c88b7e1e6bb2f6bec49d55f32f0`.
Its source-file identities use `utf8_lf_v1`: strict UTF-8 with CRLF and lone CR
normalized to LF. The runtime separately records the exact raw snapshot hash,
so the same reviewed mutant is portable to LF and CRLF checkouts without
discarding proof of the bytes the interpreter actually loaded. Mutation
fragments themselves must be canonical LF, must occur exactly once across the
LF/CRLF representations, and are replaced atomically while retaining the
snapshot's line-ending representation. Full canonical source, target AST,
target `python_code_v1`, and patch digests must all match their declared pre-
and postimages before execution can receive credit.

#### Phase 11 isolation, execution, and adjudication contract

`scripts/run_scientific_mutations.py` runs only under the project `.venv`. It
freezes the current tracked and untracked test-relevant checkout state, named
tracked deletions, and the exact already-loaded native backend. Native-parity
credit additionally requires the backend's embedded build-input manifest to
equal the manifest recomputed from the current declared C++/binding/build
inputs. Each mutant receives a fresh plain-file copy; links, reparse points,
hard links, case-colliding paths, missing/extra files, byte drift, and live
checkout drift fail closed. The native extension is copied unchanged and is
never rebuilt or mutated. No production source in the user's checkout is
written.

The parent rejects preloaded evidence/adjudication modules, disables bytecode
writes, imports through an empty isolated bytecode-cache prefix, proves module
`__file__` and spec origins, and receipts the exact runner, contracts,
adjudicator, evidence-schema, and toolchain source identities. The parent and
every child also bind the exact project interpreter and the active
pytest/Hypothesis/PyYAML dependency closure: declared import trees, complete
dist-info trees, versions, byte counts, per-distribution digests, entry-module
bytes, and loaded source/extension loader origins. Unreviewed or duplicate
dependencies, same-version byte edits, foreign shadows, unrecorded files,
links, reparse points, hardlinks, case-colliding paths, and ambient bytecode
state fail closed. The child proves that this toolchain is unchanged from
session construction through report publication and exactly matches the
parent admission.

A child runs one exact leaf serially with `-P -B`, an execution-ID-specific
absolute pycache prefix, plugin autoload disabled, the repository reporter
loaded explicitly, role-separated deterministic execution IDs, a seed derived
from the full mutant ID, downloads disabled, and cooperative network mode
`deny`. The child reports exact source, module, and interpreter byte counts in
addition to their digests. Stdout and stderr are drained concurrently with
only 128 KiB per stream retained; full-stream SHA-256 continues across
discarded bytes. Process-tree termination and pipe closure use bounded waits
on every normal, timeout, setup-failure, and `BaseException` path. Windows
children start suspended, enter a kill-on-close Job Object, and only then
resume. Linux children run under a process-wide serialized subreaper that
kills and reaps descendants which escape the original session; unsupported
non-Linux POSIX hosts fail closed. Real noisy-child and descendant-escape
canaries exercise these boundaries, while a real disposable pytest subprocess
canary exercises reporter hooks, atomic publication, selection, three phases,
target tracing, and baseline adjudication.

An unmutated baseline must first select only the declared item, pass
setup/call/teardown, execute the exact declared target code, and exit green.
Mutation credit then requires all of the following:

- the canonical postimage and exact raw snapshot postimage are proved;
- the one intended node is the entire selected set;
- collection and internal-error lists are empty;
- setup and teardown pass without exceptions;
- only call fails, with no xfail or rerun evidence;
- parent return code and structured pytest exit status are both exactly
  `TESTS_FAILED`;
- the loaded target module, source file, traced frame, qualified code object,
  and `python_code_v1` digest are the declared postimage;
- the evidence claim ID and contract digest are present on every phase;
- the call exception, message/longrepr fragments, and typed metamorphic witness
  match the catalogue exactly; and
- the outcome is `killed_intended`. Import, collection, setup, teardown,
  timeout, truncation, foreign module, wrong assertion, survivor, xfail, rerun,
  or contradictory passed-phase exception receives zero credit.

Every baseline and mutant adjudication has an exact schema and its own
`adjudication_sha256`. Sealing and later receipt verification independently
replay the cross-field rules above; outcome labels cannot mint a green receipt.
The process record retains the parsed but unadmitted child report for red-run
forensics while `child_report` remains only the report that passed admission.

The separate receipt contains exactly `baselines.json`, `catalogue.json`,
`mutants.json`, `run.json`, `snapshot.json`, and `COMPLETE`. The COMPLETE
manifest binds every data-file byte count and SHA-256; the snapshot manifest is
recomputed; catalogue IDs, run summary, boundaries, interpreter, parent-module
identities, test-toolchain closure, native build-input provenance,
process/report digests, and adjudication records are revalidated. Canonical
timestamps are rejected before any artifact directory is created. A complete
candidate is written below an explicitly incomplete staging container, fully
replayed while still staged, and atomically renamed to its final run ID only
after that replay succeeds. Run and verify modes recompute the current
snapshot, interpreter/toolchain, and native-build identities before and after
their critical operation and reject drift. This is tamper evidence, not signed
authenticity, and is stated as such in the receipt.

#### Phase 11 adversarial findings closed

The implementation was not accepted after its first apparent green result.
Adversarial review found and closed these false-assurance paths:

- the initial child allowlist omitted Windows home variables, so all six
  baselines blocked in `Path.home()`; red receipt `phase11-20260801-a`
  preserved the failure and granted zero kill credit;
- a label-only mapping could previously seal and revalidate as green;
- raw CRLF catalogue hashes and a CRLF mutation fragment made the catalogue
  fail on canonical LF/Linux checkouts;
- `communicate()` retained unbounded child output, and one failed Windows
  tree-kill path could enter an unbounded pipe wait;
- invalid parsed child reports were discarded instead of retained as explicitly
  unadmitted diagnostics;
- the standalone parent did not bind loaded adjudication/contract code or
  exclude stale/preloaded modules;
- reporter behavior had only manufactured-dictionary tests rather than a real
  subprocess integration canary;
- the declared `invalid_mutation` outcome was unreachable; mutation
  materialization failures now abort without sealing rather than advertising a
  dead result class; and
- passed setup/teardown phases could carry contradictory exception payloads and
  still allow live kill credit. Both live adjudication and offline receipt
  replay now reject that state.

A second adversarial pass then treated the first green receipt as hostile
input and found additional ways it could overstate assurance:

- setup failures and non-`Exception` interruptions after `Popen` could bypass
  complete child-tree and pipe cleanup;
- a POSIX descendant could leave the child's session, redirect its descriptors,
  and survive a process-group kill, while a Windows child could execute before
  Job Object assignment;
- execution IDs, seeds, interpreter runtime fields, pycache location, and
  reported file byte counts were not all independently derived and replayed;
- the parent recorded its interpreter but not the exact installed pytest,
  Hypothesis, PyYAML, and transitive dependency bytes or loaded import origins;
- copied native bytes could be exact yet stale relative to their declared
  native build inputs;
- a candidate receipt could be published before its full semantic replay, and
  run/verify mode did not bracket the operation with complete current-identity
  recomputation; and
- the coordinate mutant's old name overstated its production change: it
  reverses one latitude-numerator cross-term, not the whole obliquity rotation.

The execution, provenance, naming, staging, and replay contracts above close
those paths. Cleanup failures remain failures; they can never be converted into
mutation credit.

An intermediate frozen run, `phase11-20260801-c`, killed the first five mutants
but detected that `tests/harness_meta/test_mutation_runner_policy.py` changed
while another adversarial test was being added. Materialization of the sixth
snapshot failed closed with `snapshot input changed during materialization`;
no receipt was sealed. This is retained as direct evidence that live-checkout
drift cannot be hidden inside a nominally green pack.

#### Phase 11 verification receipt

The earlier `phase11-20260801-d` receipt proved the preceding contract, but is
superseded and non-authoritative after the catalogue rename and receipt,
runtime, toolchain, cleanup, and native-provenance schema hardening. Current
verification must reject it as stale. A fresh schema-3 all-declared receipt is
required before Phase 11 returns to complete status.

The superseded run was:

```powershell
$env:MOIRA_TEST_MODE = "1"
$env:MOIRA_STRICT_KNOWN_ISSUES = "1"
.\.venv\Scripts\python.exe scripts\run_scientific_mutations.py --run-id phase11-20260801-d
.\.venv\Scripts\python.exe scripts\run_scientific_mutations.py --verify-receipt .pytest_cache\moira-mutation-artifacts\phase11-20260801-d
```

All six baselines passed and all six mutants were `killed_intended` under that
older contract. Its historical sealed receipt is
`.pytest_cache/moira-mutation-artifacts/phase11-20260801-d`; its snapshot
contains 1,424 exact files with manifest SHA-256
`9d00dee51b8311449c22309c48aee22d199268da5632aa7427e0ebbbb6ab9984`.
Independent receipt replay then returned `6/6 killed intended`; that historical
result is not current proof after the hardening above.

The adversarial harness gate passed 75 tests: 73 catalogue, isolation,
mutation, adjudication, diagnostic, receipt, and tamper-policy tests plus two
real runtime/reporter subprocess canaries. Nine green-record tamper classes are
tested at both seal and later validation boundaries: selection, phase,
passed-phase exception, source, code, exception witness, process, report digest,
and adjudication digest. Label-only green records are rejected at both
boundaries.

The broad serial regression gate was:

```powershell
$env:MOIRA_TEST_MODE = "1"
$env:MOIRA_NO_DOWNLOAD = "1"
$env:MOIRA_STRICT_KNOWN_ISSUES = "1"
$env:MOIRA_TEST_ARTIFACTS = "0"
.\.venv\Scripts\python.exe -m pytest tests\harness_meta tests\metamorphic tests\unit\test_spk_kernel_identity.py tests\unit\test_house_projection_geometry.py tests\unit\test_hellenistic_source_goldens.py tests\unit\test_native_nutation_2000a.py tests\unit\test_julian_delta_t.py tests\unit\test_low_level_helpers.py tests\unit\test_conftest_smoke.py -q
```

It collected 955 tests: 953 passed and the two expected `socket.sendmsg`
capability cases skipped because that API is unavailable. The selected set was
724 harness, 14 metamorphic, and 217 unit cases; all 38 evidence items remained
bound across seven contracts.

The distributed canary ran both Phase 11 harness files plus the Phase 9/10
evidence files under `-n 2 --dist=load -m parallel`. It collected 141, selected
113 parallel items, deselected 28 ordinary/local items, and passed all 113.
The selected set contained all 75 Phase 11 harness items and all 38 reviewed
evidence items. The static assurance matrix still passed seven required cells;
scoped Ruff passed; `git diff --check` passed for the Phase 11 files; and the
project import smoke loaded Moira `6.1.0` from the checkout's
`_moira_native.cp314-win_amd64.pyd`.

#### Phase 11 pause checkpoint — 2026-08-02

**Status: paused, adversarially red, and not admitted.** No current Phase 11
receipt may be minted or presented as assurance evidence from this checkpoint.
The reserved next run ID is `phase11-20260802-a`; it must remain unused until
all restart gates below are green. `phase11-20260801-d` remains historical and
non-authoritative. No commit, push, tag, release, or deployment was performed
at this checkpoint.

The present uncommitted implementation advances the receipt and toolchain
contract to schema 3. It includes exact parent-owned intended-test source bytes,
canonical Base64 and SHA-256, pytest assertion-rewrite policy, a deterministic
`python_code_structural_v1` digest for the rewritten intended test, exact
function/module/loader/code identities, exact traced frame globals, a frozen
eight-file stage-one parent loader, and expanded byte/code/binding provenance
for the active test-toolchain closure. Production target functions deliberately
remain on `python_code_v1`; migrating those catalogue identities is a separate
schema/catalogue/history migration, not an incidental checkpoint edit.

The following checks are current at the pause boundary:

- scoped `py_compile` passed for the runner, reporter, assurance/toolchain
  support, and three Phase 11 harness modules;
- scoped Ruff passed with `--no-fix` for the same seven files;
- catalogue validation passed for all six mutants at SHA-256
  `831ca1c0b75dd7d8b8dd8a0cd2187360f62b5c88b7e1e6bb2f6bec49d55f32f0`;
- `tests/harness_meta/test_mutation_runner_policy.py` passed all 173 collected
  tests, with zero deselections and zero skips;
- the final, `.incomplete`, and `.revoked` artifact paths for reserved run ID
  `phase11-20260802-a` were all confirmed absent; and
- the current-toolchain identity smoke intentionally remains red. It fails at
  `hypothesis.strategies._internal.core._maybe_nil_uuids` with `loaded source
  callable binding changed` after the exact source-derived admission of all six
  `Shrinker.derived_value` descriptors.

Two additional P1 false-green paths were found by the final read-only review and
are not yet closed:

1. The reporter proves the captured intended-test and target module objects,
   functions, code objects, paths, and globals, but does not yet prove that each
   captured module is still the exact live `sys.modules[module_name]` binding.
   Initial capture, stability checks, and final identity assembly must join to
   the same module object for both roles.
2. The reporter currently proves that the exact intended-test frame and exact
   target frame both occurred during the pytest call phase, but not that the
   target call descended from that intended-test frame. For the six synchronous
   killers, target credit must require an `f_back` ancestry containing the exact
   captured intended-test code object and module globals. A hook that calls the
   target before or after the test must receive zero credit.

One requested regression is also still absent: a focused
`_Reporter._prepare_target` test must reject non-exact `FunctionType` targets and
arbitrary `__wrapped__` proxies. The runner-policy source-receipt and POSIX
lexical-versus-resolved-executable additions are now covered by the 173-test
green run; the real POSIX behavior itself was not exercised on this Windows
host.

Restart in this order:

1. Close the live-`sys.modules` coherence and causal-frame-ancestry findings in
   the reporter, with direct adversarial regressions for detached module clones
   and out-of-band pytest-hook target calls.
2. Add the missing target-wrapper regression.
3. Continue the toolchain binding audit from `_maybe_nil_uuids`, admitting only
   transformations derived exactly from sealed source/decorator/closure
   structure. Do not add a broad callable-proxy or wrapper escape. Repeat until
   the current-toolchain identity smoke is green.
4. Run the focused toolchain regressions, all 173 runner-policy tests, the real
   reporter/runtime canaries, and then the combined three-file Phase 11 harness.
5. Run the proportional broad serial and xdist evidence gates and re-run scoped
   Ruff, `py_compile`, catalogue validation, and `git diff --check`.
6. Only after all gates are green, confirm that the final, incomplete, and
   revoked forms of `phase11-20260802-a` do not already exist; execute the six
   baselines and mutants; independently replay the sealed receipt; inspect its
   schema, counts, identities, digests, outcomes, skips, and boundaries; and
   replace this red checkpoint with the exact fresh verification receipt.

No engine mathematics, public semantics, native source, compiled-extension
bytes, scientific table, oracle/golden baseline, tolerance, dependency, or
packaging authority is admitted by this work-in-progress checkpoint. The large
pre-existing dirty worktree remains unstaged and must be preserved during the
restart.

#### Phase 11 recovery checkpoint — 2026-08-04

**Status: paused, adversarially red, and not admitted.** This checkpoint
supersedes the previous toolchain restart frontier, but it does not authorize a
Phase 11 receipt. The reserved run ID remains `phase11-20260802-a`; its final,
`.incomplete`, `.revoked`, `.invalidated`, and root-claim paths were all
confirmed absent after the host restart. No mutation campaign, commit, push,
tag, release, or deployment was performed.

The interrupted semantic-state repair now models 45 stable exact
`functools._lru_cache_wrapper` objects plus one logical
`importlib.metadata.FastPath.lookup` instance-cache family. The implementation
binds the non-module `typing._caches` and `_cleanups` containers, four
`ipaddress` property getters, two Hypothesis descriptor functions,
`FastPath.__new__`, the original `FastPath.lookup` closure method, exact
`CacheInfo` controls, and exact `collections._tuplegetter` reduction controls.
Normalization is phased: validate every owner first, clear every admitted
cache second, and perform a final non-mutating global pass so a destructor or
weakref callback cannot repopulate an earlier cache and still receive a green
receipt. Distribution discovery now enumerates exact immediate metadata
directories directly rather than invoking `importlib.metadata`'s global
`FastPath` cache. On this `.venv`, the direct enumeration and the former
metadata enumerator both selected the same 118 `.dist-info` paths.

A fresh standalone project-venv process imported and normalized this registry
successfully. Its portable logical receipt contained 46 sorted providers with
SHA-256
`9d0c1e676f08dcbef18a8ce60a08c9846cfd413c0941ab55a3cc63b0b88678f9`.
That result proves only the standalone registry; it is not the real-child
completeness result.

Checkpoint verification used the project `.venv` under Python 3.14.3 with
`MOIRA_TEST_MODE=1`, `MOIRA_NO_DOWNLOAD=1`,
`MOIRA_STRICT_KNOWN_ISSUES=1`, and `MOIRA_TEST_ARTIFACTS=0` where pytest or the
ordered lifecycle was involved:

- scoped `py_compile` passed for `mutation_toolchain.py`, its harness meta-test,
  and `mutation_reporter.py`;
- scoped Ruff passed for the same three files with `--no-fix`;
- the focused LRU/FastPath slice collected 115 tests, selected nine, deselected
  106, passed eight, and intentionally remained red on the isolated
  garbage-collector completeness canary; and
- the exact standalone order
  `normalize -> project_test_toolchain_identity -> normalize ->
  loaded_test_toolchain_attestation` remained red after 33.4 seconds at
  `collections._tuplegetter provider changed`. The immediate cause is an
  over-strict identity comparison against a newly returned class
  `mappingproxy`; the verifier must compare the retained exact member sequence,
  not require two `mappingproxy` view objects to be identical.

The garbage-collector canary found one real-pytest-only exact LRU wrapper beyond
the 45 stable objects after normalization:

- `_pytest.config.PytestPluginManager._get_directory`, created per plugin-manager
  instance by `lru_cache(256)(_get_directory)` in
  `PytestPluginManager.__init__`.

This is a genuine P1 completeness failure, not disposable test pollution. The
current production normalizer cannot discover that instance family without
`gc`, so the 46-provider design must not be called complete in a real mutation
child. Production discovery must remain no-`gc`; the exact active plugin
manager is available through pytest `Config` and must be passed across an
explicit reviewed boundary. The eventual portable registry will require a
second logical dynamic-family entry, but its label, provider count, and digest
must be derived only after that design and its parent/child semantics are
implemented.

Restart in this order:

1. Repair the exact `_tuplegetter` verifier so repeated `mappingproxy` views are
   compared by retained exact members, and add a zero-callback tamper canary.
2. Define the `PytestPluginManager._get_directory` governing object and explicit
   caller contract. In a real child, bind the exact active plugin manager from
   pytest `Config`, its exact class, original `_get_directory` function, owned
   wrapper, cache controls, and lifecycle. The standalone parent must retain
   the same logical family name without fabricating a physical instance.
3. Add live identity-replacement canaries for copied `typing` containers,
   property, staticmethod, classmethod, `FastPath.__new__`, plugin-manager
   ownership, hostile `CacheInfo.__len__`, and a fresh-child pre/post physical
   completeness audit. The existing path-label and endpoint canaries are not a
   substitute for all of these live-path attacks.
4. Re-run the focused LRU/FastPath/plugin-manager slice and require every
   completeness canary green. Then re-run the exact ordered lifecycle and
   require identical logical receipts with all admitted caches empty.
5. Run
   `test_real_reporter_child_emits_atomic_exact_trace_receipt`; the existing
   ambient standalone-parent/plain-pytest bridge remains an import-order canary,
   not frozen-runner or reporter admission evidence.
6. Only then resume the combined runner/reporter/toolchain suites, proportional
   broad serial and xdist gates, catalogue/static-matrix checks, and the reserved
   six-mutant campaign.

The focused red canary is the restart boundary. Do not delete, xfail, weaken,
or list it in `KNOWN_ISSUES.yml`. No engine mathematics, public semantics,
native source, compiled-extension bytes, scientific table, oracle/golden
baseline, tolerance, dependency, or packaging authority changed in this
recovery work.

#### Phase 11 Hypothesis coverage checkpoint — 2026-08-05

**Status: paused, adversarially red, and not admitted.** The reserved run ID
remains `phase11-20260802-a`. No six-mutant campaign, receipt, commit, push,
tag, release, or deployment was performed. This checkpoint supersedes the
older `_tuplegetter` restart frontier for the current toolchain audit, but it
does not claim that the latest coverage changes pass the canonical identity
gate.

The compatibility-alias tranche is green. Exact, callback-free source-record
reading and provider verification now cover the inactive
`hypothesis.internal.compat` aliases for `dataclass_asdict` and `batched`,
including hostile metadata, verifier/dispatcher self-blessing, slot-descriptor
replacement, and pre-import provider/module substitution. The focused
compatibility slice passed 28 tests with 485 deselections and zero skips; the
profile/provider regression slice passed 104 tests with 381 deselections and
zero skips.

The next source frontier was the exact disabled outcome in
`hypothesis.internal.coverage`. The current work-in-progress now retains the
14-part early bootstrap graph: coverage module and false flag, exact `os`
provider, `getenv` and its code, `os.environ`, `check_function` and its code,
the public context-manager `check` and its code, the raw wrapped `check` and its
code, the exact public closure tuple/cell, and both loaded consumer aliases.
The toolchain record also carries four function fingerprints and default-binds
the source-byte/hash/AST and fingerprint verifiers so simple helper replacement
cannot bless a changed outcome. This closes the structural mismatch that had
left the dataclass newer than its constructor and old eight-slot anchor checks.

Checkpoint-only verification under the project `.venv` and Python 3.14.3:

- `python -m py_compile` passed for
  `tests/_pytest_plugins/determinism.py`,
  `tests/support/mutation_toolchain.py`, and
  `tests/harness_meta/test_mutation_toolchain.py`;
- a fresh standalone import with
  `HYPOTHESIS_INTERNAL_COVERAGE` absent passed the builtin-only coverage
  verifier and reported four function fingerprints; and
- pytest's real loader collected all 513 tests in
  `tests/harness_meta/test_mutation_toolchain.py` with zero skips. Collection
  proves the real harness import/bootstrap shape only; those 513 tests were not
  executed at this checkpoint.

One manual smoke that imported `_pytest_plugins.determinism` outside pytest's
normal plugin topology failed the pre-existing profile-owner topology guard.
That invocation is not an admitted harness path and is not a product failure;
the subsequent real pytest collection is the relevant bootstrap smoke.

Restart in this order:

1. Finish exact coverage source-policy topology validation for the four sealed
   bindings (`check`, `check_block`, `check_function`, and `record_branch`).
2. Default-bind and identity-check the guard dispatch chain
   `_closed_source_expression_value -> _closed_source_reference`,
   `_active_source_binding_candidate`, and `_verify_loaded_bindings`; validate
   exact record/scalar types before any equality, hashing, or iteration.
3. Add the focused coverage canaries for coordinated raw-wrapper/closure
   substitution, in-place code replacement, enabled-only residue, consumer
   drift, `getenv` clone/metadata changes, post-import environment changes,
   record/verifier/dispatcher self-blessing, and hostile metadata with zero
   callbacks. Include fresh-child pre-import enabled and environment-scrubbed
   cases.
4. Run only that focused coverage slice first. Then rerun the canonical compact
   toolchain identity command. Before the latest hardening edit, the canonical
   command had advanced beyond `IN_COVERAGE_TESTS` to the next reported frontier,
   `hypothesis.internal.entropy.RandomLike`; this must be reconfirmed and is not
   yet current proof.
5. Continue one exact frontier at a time. Run the broader static/harness gates
   only after the focused canaries are green. Keep the six-mutant campaign and
   receipt last.

The broad dirty worktree remains unstaged and must be preserved. This tranche
touches validation-policy infrastructure only; it changes no engine
mathematics, public semantics, native source, compiled extension, scientific
table, oracle/golden baseline, tolerance, dependency, or packaging authority.

#### Phase 11 iniconfig closure and packaging frontier checkpoint — 2026-08-07

**Status: paused, adversarially red, and not admitted.** The reserved run ID
remains `phase11-20260802-a`. No six-mutant campaign, receipt, coverage
database, tag, release, or deployment was produced. This is a source
checkpoint, not current evidence that Phase 11 passes its canonical closure
gate.

The exact Python 3.14 annotation-scope cell retained by
`iniconfig._parse.ParsedLine.__annotate_func__` is now closed. The toolchain
admits exactly two wrapped source class-dictionary cells: the existing
`hypothesis.internal.filtering.ConstructivePredicate` cell and the new
`iniconfig._parse.ParsedLine` cell. Selection is by retained cell identity,
not by generic `NamedTuple` topology. The records retain the exact source
module, class, `typing.NamedTupleMeta.__new__` factory, wrapper, hidden original
annotation function, closure cells, hidden class dictionary, cell descriptor,
and ordered identity-bearing dictionary entries.

The admission also closes two false-green paths found during adversarial
review. The immediate `CellType` dispatcher now default-binds and verifies the
class-dictionary shape helper and its callable fingerprints before invocation,
so replacing the mutable global cannot return a forged valid shape. Provenance
lookups for `sys.modules`, source/provider module dictionaries, class mapping
proxies, `CellType`, and hidden class-dictionary backreferences use exact item
scans. Equal hostile `str` subclasses are rejected before equality, hashing,
or representation callbacks. A post-shape verification sandwich rechecks the
registry, closure graph, module routes, class namespaces, cell contents, and
ordered dictionary identities without executing either deferred annotation
function.

Checkpoint verification used the project `.venv` under Python 3.14.3 with
`MOIRA_TEST_MODE=1`, `MOIRA_NO_DOWNLOAD=1`,
`MOIRA_STRICT_KNOWN_ISSUES=1`, and `MOIRA_TEST_ARTIFACTS=0`:

- final `py_compile` and scoped Ruff checks passed for
  `tests/support/mutation_toolchain.py` and
  `tests/harness_meta/test_mutation_toolchain.py`;
- the focused matrix passed 20 tests with zero skips, covering the existing
  Hypothesis cell, the exact iniconfig cell, 15 identity attacks, an unrelated
  `NamedTuple` rejection, the mutable-dispatcher bypass, and a hostile
  `sys.modules` key with zero callbacks;
- a separate fresh-process iniconfig reseal passed one test with zero skips;
  and
- an independent read-only review found no remaining actionable finding in
  this exact tranche.

The one permitted canonical closure run advanced past the prior iniconfig
failure and then failed after selecting one harness test with zero skips:

```text
MutationToolchainError: inactive source binding is unexpectedly present:
packaging.version._deprecated
```

The installed `packaging.version` source selects
`from warnings import deprecated as _deprecated` when
`sys.version_info >= (3, 13)`. Under Python 3.14.3 that branch is active, but
the sealed source policy currently classifies `_deprecated` as inactive. This
is the next exact frontier; it was checkpointed rather than implemented or
silently admitted. The canonical test took 125.792 seconds and retained
classification-manifest SHA-256
`5c6459c715cac430653c5e19a2707b51badd49d427c2b0191e23164f7068859e`.

Restart in this order:

1. Map the sealed candidates and active-guard proof for
   `packaging.version._deprecated`, including the `sys.version_info >= (3, 13)`
   branch and exact `warnings.deprecated` provider binding.
2. Define the branch and provider authority before changing admission logic;
   do not weaken inactive-binding rejection globally.
3. Add focused active/inactive branch, equal-distinct version information,
   provider substitution, dispatcher self-blessing, and hostile-key canaries
   that execute no decorator or warning callback.
4. Run the focused packaging slice, a fresh clean reseal, static checks, and
   then the canonical closure exactly once. If it exposes another frontier,
   checkpoint that frontier rather than beginning a mutation campaign.
5. Keep the six-mutant campaign and final receipt last. Phase 11 remains red
   until the canonical closure, campaign, and receipt gates all pass.

#### Phase 11 boundaries and future expansion

This phase changes validation infrastructure only: the runner, reporter,
catalogue, harness meta-tests, and this plan. It changes no engine mathematics,
public semantics, native source, scientific table, oracle/golden baseline,
tolerance, dependency, or packaging authority. The six mutations occur only
inside disposable copies. No commit, push, tag, release, or deployment was
performed.

The admitted pack is intentionally Python-source-only and cannot prove
completeness. It does not yet mutate native SPK coefficients/endian decoding,
the distinct UT-for-TT substitution archetype, observer/target center chains,
degrees/radians and unit conversions, correction stage omission,
apparent/geometric or topocentric/geocentric policy, solver tolerances,
requested/effective house policy, or native-dispatch cache state.
Those remain candidate Phase 11 expansion work and require their own governing
objects, exact intended killers, and isolation strategy. Python/native parity
is corroboration of two paths, not external authority. Cooperative CPython
network denial is accidental-egress containment, not a hostile security
sandbox; native/ctypes/inherited-descriptor denial remains a runner-level
boundary. Receipt SHA-256 detects accidental or uncoordinated tampering but is
not a signature or independent trust anchor.

---

### Phase 12 — Fuzz, corruption, and chaos

#### Task 12.1 — DAF/SPK corruption laboratory

Extend the existing synthetic Type-13 writer surface with bounded corruptions:

- truncation at record boundaries;
- damaged headers and summary counts;
- endian flips;
- invalid addresses;
- reversed coverage;
- overlap and duplicate segments;
- NaN coefficients;
- sparse oversized files;
- file replacement while open;
- short reads and permission denial.

Run every candidate in a time- and memory-bounded subprocess. Required
outcomes:

- no native crash or hang;
- no partial resource admission;
- deterministic typed error;
- no poisoned reader/cache afterward;
- a valid synthetic kernel still succeeds in a fresh call.

#### Task 12.2 — Native sanitizers

AddressSanitizer, UndefinedBehaviorSanitizer, ThreadSanitizer, and
sanitizer-backed fuzzing require a separate protected-native declaration,
native build review, and Linux CI design. They are not part of the initial
harness change.

#### Task 12.3 — Xdist and I/O chaos

Attack:

- `-n 0`, `-n 2`, and higher worker counts;
- randomized worker scheduling;
- worker death during setup, call, teardown, and artifact emission;
- controller interruption;
- clock rollback;
- disk-full/short-write behavior;
- Windows sharing violations;
- locked kernel files;
- long, Unicode, case-colliding, junction, drive-relative, UNC, and
  OneDrive-style replacement paths.

An interrupted run must remain incomplete and non-green. Previously admitted
evidence must remain byte-identical.

---

### Phase 13 — CI and release admission

Add lanes only after their local contracts pass.

#### Every pull request

- harness-meta tests;
- kernel-free unit/invariant slice;
- offline admitted authority fixtures;
- loopback server slice;
- serial-selection integrity;
- small `-n 2` semantic-equivalence canary;
- critical semantic mutation canaries.

#### Nightly

- extended targeted Hypothesis;
- xdist scheduling permutations;
- global-state contamination detection;
- bounded parser fuzzing;
- resource handle/RSS loops;
- Windows path and locking matrix;
- larger mutation subset.

#### Weekly or release candidate

- full curated mutation pack;
- sanitizer builds;
- chaos drills;
- exact wheel/sdist import tests outside the checkout;
- base-runtime import test without development or optional packages;
- controlled-host DE441 validation with resource receipt.

#### Manual acquisition only

Live external-oracle refresh is never part of ordinary pytest. It creates a
candidate fixture plus provenance and semantics. A separate review admits or
rejects that candidate.

## 11. Tomorrow's recommended stopping points

Do not try to hide a week-scale assurance program inside one unreviewable
change.

### Required first tranche

Complete:

- Phase 0;
- Phase 1 known-issue/configuration/Hypothesis characterizations;
- Phase 2 strict configuration repairs;
- the matching focused gates.

This tranche is valuable independently and has the smallest blast radius.

### Second tranche, only if the first is green and reviewed

Complete:

- Phase 3 reference-epoch and baseline-policy repairs;
- no baseline value updates;
- no mass numeric-helper migration.

### Third tranche, only if collection counts and server inventory are explicit

Begin:

- Phase 4 loopback/external-network migration.

### Explicitly defer from the first day

- global-reader lifecycle redesign;
- xdist scheduler and artifact rewrite;
- plugin decomposition;
- evidence-contract rollout;
- mutation, fuzz, native sanitizer, and CI expansion.

These remain fully designed above, but their protected-zone and concurrency
risks deserve separate checkpoints.

## 12. Verification ladder

Run the smallest affected command first. Every local command uses
`.\.venv\Scripts\python.exe`.

### Per-task

1. focused harness-meta file;
2. affected current consumer;
3. `tests/unit/test_conftest_smoke.py`;
4. touched-file Ruff:

   ```powershell
   .\.venv\Scripts\ruff.exe check <touched-python-files> --no-fix
   ```

5. `git diff --check`.

### Per-phase

```powershell
$env:MOIRA_NO_DOWNLOAD = "1"
$env:MOIRA_TEST_MODE = "1"
$env:MOIRA_STRICT_KNOWN_ISSUES = "1"
.\.venv\Scripts\python.exe -m pytest tests\harness_meta tests\unit\test_conftest_smoke.py -q -p pytester
```

Add the phase-specific commands documented above.

### After harness phases stabilize

Kernel-free native baseline:

```powershell
.\.venv\Scripts\python.exe -m pytest tests\test_native_parity.py tests\test_native_sidereal_phase1.py tests\unit\test_native_import_resolution.py tests\unit\test_native_nutation_2000a.py -q
```

Relevant adversarial/native reader baseline:

```powershell
.\.venv\Scripts\python.exe -m pytest tests\unit\test_adversarial_native_daf_reader.py tests\unit\test_spk_kernel_identity.py -q
```

Normal deterministic network-excluding suite only after targeted gates:

```powershell
.\.venv\Scripts\python.exe -m pytest -m "not external_network" -q
```

Do not run the literal full configured suite until its network/resource effects
are intended and prerequisites are declared.

## 13. Risk register

| Risk | Mitigation | Stop condition |
|---|---|---|
| Characterization accidentally blesses defective behavior | Tests assert desired policy and temporarily document current failure | Unclear governing policy |
| Network migration removes server coverage | Compare collection manifests before/after and distinguish loopback | Unexpected deselection |
| Removing ambient kernel setup breaks legacy callers | Inventory direct `get_reader()` use and add explicit fixture | Unclassified caller |
| New epoch values expose engine discrepancies | Separate harness repair from engine repair | Protected engine change required |
| Numeric-helper migration weakens tolerances | Product-by-product review with units and derivation | Unnamed tolerance |
| Xdist reports differ from serial | Controller-owned structured reports and semantic canary | Missing/duplicate node report |
| Artifact hardening loses diagnostics | Atomic structured output plus bounded full traceback field | Receipt cannot replay |
| Baseline lockout blocks legitimate regeneration | Separate candidate generator and reviewed promotion | Ordinary pytest writes baseline |
| Mutation score becomes vanity metric | Curated critical mutants and intended-killer mapping | Mutant dies for unrelated reason |
| Fuzzing creates nondeterministic failures | Persist seed/input and minimize before admission | Failure cannot replay |
| Sanitizer work widens native scope | Separate protected-native task and build receipt | Native edit required |
| Existing dirty work is overwritten | Recheck worktree before every tranche; never stage broadly | Overlap with user file |

## 14. Rollback and checkpoint policy

- Keep each phase independently revertible.
- Do not combine behavior repair and plugin extraction in one checkpoint.
- Do not combine harness repair and engine repair.
- Do not combine baseline admission with test code changes.
- Do not combine marker migration with CI enforcement until local collection
  receipts are stable.
- Preserve exact failed commands and artifact receipts before rollback.
- No commit, push, tag, pull request, release, or deployment occurs unless the
  user separately requests it.

## 15. Phase completion receipt template

For every completed phase, report:

```text
Phase:
Requested behavior:
Files changed:
Protected zones:
Unrelated work preserved:
Governing object/policy:
Evidence class:
Authority/fixture/corpus:
Resource identity/capability:
Python/native path:
Exact commands:
Pass/fail/skip counts:
Setup/call/teardown scope:
Tolerance and units:
Collection changes:
Artifacts/receipt path:
Known gaps:
Newly discovered engine defects:
Separate authorization required:
```

## 16. Final acceptance

Before declaring the program complete:

- [ ] every audit finding is mapped to a repaired contract test, an explicit
  rejection, or a documented separately scoped deferral;
- [ ] no old fixture-adoption task can reintroduce the audited defects;
- [ ] all policy plugins have black-box subprocess tests;
- [ ] kernel-free, loopback, external-network, serial, parallel, and
  resource-required lanes are mechanically distinct;
- [ ] exact run replay succeeds from a controller receipt;
- [ ] protected evidence is immutable under ordinary pytest;
- [ ] the assurance matrix distinguishes authority, corroboration, regression,
  invariant, native parity, harness, and performance evidence;
- [ ] critical scientific mutations are killed by intended tests;
- [ ] corrupted native resources fail safely in bounded subprocesses;
- [ ] CI lane claims match what each lane actually executes;
- [ ] validation-facing documentation is updated only with measured completion
  receipts;
- [ ] `git diff --check` passes;
- [ ] unrelated worktree changes remain untouched.

Only then may the new harness be described as an assurance system rather than a
pytest convenience layer.
