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

- [ ] Introduce a typed kernel requirement with optional:
  - product;
  - content identity;
  - interval;
  - bodies;
  - target/center pairs;
  - frame;
  - segment types;
  - native capability.
- [ ] Preserve a generic "any admitted planetary kernel" requirement only for
  genuinely identity-independent invariants.
- [ ] Resolve resource capability once per process.
- [ ] Build identity from opened kernel/catalog content, never filename.
- [ ] Record a resource receipt for run, skip, and failure paths.

#### Task 5.2 — Explicit reader fixtures

- [ ] Remove the session-autouse kernel singleton bootstrap.
- [ ] Provide explicit fixtures:
  - `planetary_kernel_path`;
  - `planetary_kernel_receipt`;
  - `planetary_reader`;
  - `configured_global_reader` only for legacy singleton-specific tests;
  - `moira_engine` with explicit ownership and teardown.
- [ ] Use `yield` and close/reset every fixture-owned reader.
- [ ] Do not hot-swap global reader state during concurrent tests.
- [ ] Inventory direct `get_reader()` callers before removing ambient setup.

#### Task 5.3 — Resource selection integrity

- [ ] A required mismatched identity fails or skips with a named capability
  receipt according to the lane's policy.
- [ ] A corrupt resource never becomes "available" through an existence check.
- [ ] Kernel-free tests prove that no planetary reader is opened.
- [ ] Cache capability checks without caching a stale reader across lawful
  reset boundaries.

**Gates:**

```powershell
.\.venv\Scripts\python.exe -m pytest tests\harness_meta\test_resource_policy.py tests\unit\test_spk_kernel_identity.py -q -p pytester
.\.venv\Scripts\python.exe -m pytest tests\unit\test_conftest_smoke.py -q -k "jd_j2000 or network_blocked" --durations=5
.\.venv\Scripts\python.exe -m pytest tests\unit\test_conftest_smoke.py -q --durations=10
```

The JD-only setup must no longer acquire the planetary kernel. Record before
and after timing as performance evidence only.

---

### Phase 6 — Real execution classification and serial semantics

**Purpose:** ensure selectors and concurrency labels have enforceable meaning.

- [ ] Derive paths relative to `tests/`, never from absolute checkout parents.
- [ ] Define one primary class per case and fail on contradiction.
- [ ] Add strict marker and strict configuration enforcement.
- [ ] Remove automatic `parallel`; absence of `serial` is not proof of
  concurrency safety.
- [ ] Inventory explicit global-state, singleton, filesystem-lock, shared-cache,
  and resource-mutation tests.
- [ ] Run non-serial tests under xdist and serial tests in a separate `-n 0`
  lane.
- [ ] Fail an xdist invocation that selects a `serial` test unless an admitted
  scheduler actually enforces the contract.
- [ ] Fail on empty parametrization for required base-engine enumerations.
- [ ] Record collected, selected, deselected, skipped, and primary-class counts.

**Gates:**

```powershell
.\.venv\Scripts\python.exe -m pytest tests\harness_meta\test_xdist_policy.py -q -p pytester
.\.venv\Scripts\python.exe -m pytest tests\harness_meta -n 2 -q -p pytester -m "not serial"
.\.venv\Scripts\python.exe -m pytest tests\harness_meta -n 0 -q -p pytester -m "serial"
```

---

### Phase 7 — Controller-owned lifecycle, artifacts, and replay

**Purpose:** make failures and execution receipts exact and crash-visible.

#### Task 7.1 — Full lifecycle reports

- [ ] Record setup, call, and teardown outcome/duration separately.
- [ ] Aggregate full lifecycle duration by node.
- [ ] Enforce a case budget only after the full lifecycle is known.
- [ ] Preserve an existing failure and attach budget information as a report
  section.
- [ ] Use `time.perf_counter()` for session duration.
- [ ] Validate all budgets as finite and nonnegative.
- [ ] Finalize evidence before applying a total-budget failure status.
- [ ] Rename ordinary failure counts; reserve "flake" for observed fail-then-pass
  attempts under the same receipt.

#### Task 7.2 — Safe ephemeral artifacts

- [ ] Default to `.pytest_cache/moira-artifacts/<controller-uuid>/`.
- [ ] Reject caller-supplied IDs outside a narrow single-component alphabet.
- [ ] Create an `INCOMPLETE` sentinel before execution and replace it with
  `COMPLETE` only after successful finalization.
- [ ] Use atomic temporary-write plus replace.
- [ ] Apply per-record and per-run size limits.
- [ ] Redact known secret-bearing environment names and request headers.
- [ ] Never write transient diagnostics beneath `tests/artifacts/`.

#### Task 7.3 — Structured controller receipt

- [ ] Emit:
  - `run.json`;
  - `collection.json`;
  - `resources.json`;
  - `reports.jsonl`;
  - `failures.json`;
  - `durations.json`;
  - `rerun-nodeids.json`.
- [ ] Let the controller consume xdist log reports and worker shutdown status.
- [ ] Eliminate worker competition over shared files.
- [ ] Surface merge/finalization errors in exit status.
- [ ] Remove the bespoke coverage controller and use `pytest-cov`.

#### Task 7.4 — Replay

- [ ] Replace generated executable PowerShell with checked-in
  `scripts/replay_test_receipt.py`.
- [ ] Require invocation through:

  ```powershell
  .\.venv\Scripts\python.exe scripts\replay_test_receipt.py <path-to-run.json>
  ```

- [ ] Load node IDs from JSON as data.
- [ ] Verify repository root and `.venv` interpreter.
- [ ] Refuse a receipt from a different repository unless explicitly permitted.
- [ ] Report Git/native/resource mismatches before rerunning.

**Gates:**

```powershell
.\.venv\Scripts\python.exe -m pytest tests\harness_meta\test_lifecycle_policy.py tests\harness_meta\test_artifact_policy.py tests\harness_meta\test_xdist_policy.py -q -p pytester
.\.venv\Scripts\python.exe scripts\replay_test_receipt.py <focused-failure-receipt>
```

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

- [ ] run its harness-meta test before editing;
- [ ] move only one policy;
- [ ] register it from root `tests/conftest.py`;
- [ ] use `pytest.StashKey`;
- [ ] rerun its meta test and the existing smoke;
- [ ] run `git diff --check`;
- [ ] inspect the diff for accidental behavior changes;
- [ ] record the checkpoint before continuing.

Do not set an arbitrary line-count target. The desired property is that
`tests/conftest.py` becomes a legible registration and shared-fixture surface,
not merely a shorter file.

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
for authority, oracle, protected golden, release-claim, and selected
protected-zone validation surfaces.

#### Task 9.2 — Exemplar admission

Start with four exemplars:

1. content-derived SPK identity;
2. a coordinate-transform invariant;
3. a source-owned astrology doctrine case;
4. one admitted Python/native parity surface.

For each exemplar:

- [ ] name what the test proves;
- [ ] name what it does not prove;
- [ ] validate the schema during collection;
- [ ] emit the contract in the run receipt;
- [ ] generate an assurance-matrix row.

#### Task 9.3 — Evidence-aware coverage

- [ ] Use pytest-cov/coverage contexts to associate executed code with test or
  evidence class.
- [ ] Report protected code reached only by regression snapshots.
- [ ] Do not turn line or branch coverage percentage into a scientific gate.
- [ ] Gate missing required evidence cells, not an arbitrary global percentage.

**Gate:**

```powershell
.\.venv\Scripts\python.exe -m pytest tests\harness_meta tests\unit\test_spk_kernel_identity.py <selected-exemplar-files> -q
.\.venv\Scripts\python.exe scripts\build_test_assurance_matrix.py --check
```

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

For every relation:

- [ ] name the mathematical/doctrinal object;
- [ ] provide derivation or primary source;
- [ ] define ambiguity and branch policy;
- [ ] define conditioning domain and exclusions;
- [ ] define units and tolerance;
- [ ] prove the relation fails under at least one appropriate canary mutation.

Use targeted Hypothesis metrics such as maximum residual, iteration count,
condition number, or proximity to a declared boundary. Do not use unguided
randomness as the sole boundary strategy.

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

Run source mutations only in a disposable worktree, isolated copy, or admitted
mutation tool environment. Never mutate the user's working tree in place.
Evaluate any new mutation dependency as development tooling; do not add it to
base runtime.

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
