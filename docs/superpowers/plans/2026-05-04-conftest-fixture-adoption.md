# Conftest Fixture Adoption Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Eliminate the six categories of conftest under-use identified in the fixture audit so that every test in the suite uses the shared infrastructure it was designed to use.

**Architecture:** Each task is a mechanical substitution — no logic changes, no new tests created. All tests must pass before and after each task. Tasks are fully independent and can be executed in any order, but the recommended order minimises risk (simplest first).

**Tech Stack:** pytest, conftest.py fixtures, `moira_approx`, `jd_j2000`, `moira_engine`, `assert_longitude`, `reference_epoch`, `any_house_system`

---

## Task Index

| # | What | Files affected | Risk |
|---|---|---|---|
| 1 | Replace `_JD = 2451545.0` with `jd_j2000` fixture | 6 | Low |
| 2 | Replace direct `Moira()` construction with `moira_engine` | 12 | Medium |
| 3 | Replace hardcoded `pytest.approx(abs=…)` with `moira_approx` | ~52 | Medium |
| 4 | Replace manual `0 <= x < 360` checks with `assert_longitude` | ~10 | Low |
| 5 | Activate `reference_epoch` in house invariant tests | 5 | Low |
| 6 | Activate `any_house_system` in house structural tests | 5 | Low |

---

## Task 1: Replace `_JD = 2451545.0` with `jd_j2000` fixture

**Files to modify:**
- `tests/unit/test_house_membership.py` — line 34
- `tests/unit/test_house_boundary.py` — line 35
- `tests/unit/test_house_angularity.py` — line 35
- `tests/unit/test_house_distribution.py` — line 42
- `tests/unit/test_house_comparison.py` — line 40
- `tests/unit/test_cycles.py` — line 187

There are three structural patterns in these files. Apply the right one per file.

---

### Pattern A — module constant used by standalone functions (test_house_membership.py, test_house_boundary.py, test_house_angularity.py, test_house_distribution.py)

- [ ] **Step 1: Run the baseline to confirm all tests pass**

```
pytest tests/unit/test_house_membership.py tests/unit/test_house_boundary.py tests/unit/test_house_angularity.py tests/unit/test_house_distribution.py -q
```
Expected: all pass.

- [ ] **Step 2: Delete the module-level constant**

In each of the four files, remove the line:
```python
_JD  = 2451545.0
```
(Keep `_LAT` and `_LON` — those are not duplicating a fixture.)

- [ ] **Step 3: Convert `setup_method` to an autouse fixture in every class that used `_JD`**

Before (example from `test_house_membership.py`):
```python
class TestHousePlacementStructure:
    def setup_method(self):
        self.hc = calculate_houses(_JD, _LAT, _LON, HouseSystem.PORPHYRY)
        self.pl = assign_house(0.0, self.hc)
```

After:
```python
class TestHousePlacementStructure:
    @pytest.fixture(autouse=True)
    def _setup(self, jd_j2000):
        self.hc = calculate_houses(jd_j2000, _LAT, _LON, HouseSystem.PORPHYRY)
        self.pl = assign_house(0.0, self.hc)
```

Apply the same transformation to every class in all four files that has a `setup_method` referring to `_JD`.

- [ ] **Step 4: Update any standalone test functions that referenced `_JD` directly**

Before:
```python
def test_something():
    hc = calculate_houses(_JD, _LAT, _LON, HouseSystem.PORPHYRY)
```

After:
```python
def test_something(jd_j2000):
    hc = calculate_houses(jd_j2000, _LAT, _LON, HouseSystem.PORPHYRY)
```

- [ ] **Step 5: Run and confirm**

```
pytest tests/unit/test_house_membership.py tests/unit/test_house_boundary.py tests/unit/test_house_angularity.py tests/unit/test_house_distribution.py -q
```
Expected: same number of tests, all pass.

- [ ] **Step 6: Commit**

```bash
git add tests/unit/test_house_membership.py tests/unit/test_house_boundary.py tests/unit/test_house_angularity.py tests/unit/test_house_distribution.py
git commit -m "test: replace _JD module constants with jd_j2000 fixture in house tests"
```

---

### Pattern B — module constant captured by a helper function (test_house_comparison.py)

`test_house_comparison.py` has a module-level helper `_hc(system, lat=_LAT)` that closes over `_JD`. Classes then call `_hc(system)` inside `setup_method`.

- [ ] **Step 7: Run baseline for test_house_comparison.py**

```
pytest tests/unit/test_house_comparison.py -q
```

- [ ] **Step 8: Add `jd` parameter to `_hc()`**

Before (`test_house_comparison.py` line 49):
```python
def _hc(system: str, lat: float = _LAT) -> HouseCusps:
    return calculate_houses(_JD, lat, _LON, system)
```

After:
```python
def _hc(jd: float, system: str, lat: float = _LAT) -> HouseCusps:
    return calculate_houses(jd, lat, _LON, system)
```

- [ ] **Step 9: Delete `_JD = 2451545.0` from test_house_comparison.py**

- [ ] **Step 10: Convert every class `setup_method` that calls `_hc()` to an autouse fixture**

Before:
```python
class TestHouseSystemComparisonStructure:
    def setup_method(self):
        self.cmp = compare_systems(_hc(HouseSystem.PORPHYRY), _hc(HouseSystem.PLACIDUS))
```

After:
```python
class TestHouseSystemComparisonStructure:
    @pytest.fixture(autouse=True)
    def _setup(self, jd_j2000):
        self.cmp = compare_systems(
            _hc(jd_j2000, HouseSystem.PORPHYRY),
            _hc(jd_j2000, HouseSystem.PLACIDUS),
        )
```

Apply to every class in the file that calls `_hc()`.

- [ ] **Step 11: Run and confirm**

```
pytest tests/unit/test_house_comparison.py -q
```

- [ ] **Step 12: Commit**

```bash
git add tests/unit/test_house_comparison.py
git commit -m "test: replace _JD closure in _hc() helper with jd_j2000 fixture"
```

---

### Pattern C — class attribute (test_cycles.py)

`TestFirdar` uses `self.BIRTH_JD = 2451545.0` as a class attribute passed to every test method.

- [ ] **Step 13: Run baseline for test_cycles.py**

```
pytest tests/unit/test_cycles.py -q
```

- [ ] **Step 14: Replace class attribute with autouse fixture**

Before (`test_cycles.py` line 186–188):
```python
class TestFirdar:
    BIRTH_JD = 2451545.0  # J2000.0

    def test_diurnal_sequence_sum_is_75(self):
        series = firdar_series(self.BIRTH_JD, is_day_birth=True)
```

After:
```python
class TestFirdar:
    @pytest.fixture(autouse=True)
    def _jd(self, jd_j2000):
        self.birth_jd = jd_j2000

    def test_diurnal_sequence_sum_is_75(self):
        series = firdar_series(self.birth_jd, is_day_birth=True)
```

Replace `self.BIRTH_JD` with `self.birth_jd` in every test method in `TestFirdar`.

- [ ] **Step 15: Run and confirm**

```
pytest tests/unit/test_cycles.py -q
```

- [ ] **Step 16: Commit**

```bash
git add tests/unit/test_cycles.py
git commit -m "test: replace BIRTH_JD class attribute with jd_j2000 fixture in TestFirdar"
```

---

## Task 2: Replace direct `Moira()` construction with `moira_engine` fixture

**Files to modify (12):**
- `tests/unit/test_chiron_planet_bridge.py` — 1 instance (line 56)
- `tests/unit/test_moira_synastry.py` — 17 instances
- `tests/unit/test_moira_bce_time_support.py` — 1 instance (line 26)
- `tests/unit/test_polar_chart_public_gauntlet.py` — 1 instance (line 136)
- `tests/unit/test_chart_metadata_truth.py`
- `tests/unit/test_doctrine_alignment.py`
- `tests/unit/test_galactic_houses_public_api.py`
- `tests/unit/test_moira_polar_houses.py`
- `tests/unit/test_harmogram_bridges.py`
- `tests/unit/test_multiple_stars.py`
- `tests/test_api_reference_validation.py`

**Skip:** `tests/unit/test_moira_kernel_readiness.py` — legitimately constructs its own `Moira()` to test kernel loading behaviour.

The substitution is mechanical: remove `engine = Moira()` from the test body and accept `moira_engine` as a fixture parameter instead.

- [ ] **Step 1: Run baseline**

```
pytest tests/unit/test_chiron_planet_bridge.py tests/unit/test_moira_synastry.py tests/unit/test_moira_bce_time_support.py tests/unit/test_polar_chart_public_gauntlet.py -q
```
Expected: all pass.

- [ ] **Step 2: Migrate standalone test functions**

For any test function that contains `engine = Moira()` or `Moira()` directly:

Before:
```python
@pytest.mark.requires_ephemeris
def test_moira_chart_accepts_explicit_chiron_body_request() -> None:
    engine = Moira()
    chart = engine.chart(
        datetime(2000, 1, 1, 12, 0, tzinfo=timezone.utc),
        bodies=[Body.SUN, Body.CHIRON],
    )
    assert set(chart.planets) == {Body.SUN, Body.CHIRON}
```

After:
```python
@pytest.mark.requires_ephemeris
def test_moira_chart_accepts_explicit_chiron_body_request(moira_engine) -> None:
    chart = moira_engine.chart(
        datetime(2000, 1, 1, 12, 0, tzinfo=timezone.utc),
        bodies=[Body.SUN, Body.CHIRON],
    )
    assert set(chart.planets) == {Body.SUN, Body.CHIRON}
```

The `from moira import Moira` import can be removed from the file if `Moira` is no longer referenced anywhere else in it.

- [ ] **Step 3: Migrate class-based tests in test_moira_synastry.py**

`test_moira_synastry.py` has 17 direct constructions — many are in class `setup_method` blocks. Convert each `setup_method` to an autouse fixture:

Before:
```python
class TestSomeSynastry:
    def setup_method(self):
        self.engine = Moira()
        self.chart_a = self.engine.chart(...)
```

After:
```python
class TestSomeSynastry:
    @pytest.fixture(autouse=True)
    def _setup(self, moira_engine):
        self.chart_a = moira_engine.chart(...)
```

For test methods that constructed their own engine inline, add `moira_engine` as a parameter:
```python
def test_something(self, moira_engine):
    result = moira_engine.some_method(...)
```

- [ ] **Step 4: Verify no remaining `Moira()` in modified files**

```
grep -n "Moira()" tests/unit/test_chiron_planet_bridge.py tests/unit/test_moira_synastry.py tests/unit/test_moira_bce_time_support.py tests/unit/test_polar_chart_public_gauntlet.py
```
Expected: no output.

- [ ] **Step 5: Run and confirm**

```
pytest tests/unit/test_chiron_planet_bridge.py tests/unit/test_moira_synastry.py tests/unit/test_moira_bce_time_support.py tests/unit/test_polar_chart_public_gauntlet.py -q
```

- [ ] **Step 6: Migrate remaining 7 files using the same patterns above**

```
pytest tests/unit/test_chart_metadata_truth.py tests/unit/test_doctrine_alignment.py tests/unit/test_galactic_houses_public_api.py tests/unit/test_moira_polar_houses.py tests/unit/test_harmogram_bridges.py tests/unit/test_multiple_stars.py tests/test_api_reference_validation.py -q
```
Run after each file to catch regressions early.

- [ ] **Step 7: Full run and commit**

```
pytest tests/ -q --ignore=tests/integration
git add tests/unit/test_chiron_planet_bridge.py tests/unit/test_moira_synastry.py tests/unit/test_moira_bce_time_support.py tests/unit/test_polar_chart_public_gauntlet.py tests/unit/test_chart_metadata_truth.py tests/unit/test_doctrine_alignment.py tests/unit/test_galactic_houses_public_api.py tests/unit/test_moira_polar_houses.py tests/unit/test_harmogram_bridges.py tests/unit/test_multiple_stars.py tests/test_api_reference_validation.py
git commit -m "test: replace direct Moira() construction with moira_engine fixture"
```

---

## Task 3: Replace hardcoded `pytest.approx(abs=…)` with `moira_approx`

**Files affected:** ~52 files across `tests/unit/` and `tests/integration/`.

The `moira_approx` fixture returns a callable: `moira_approx(value, kind="longitude")`. The tolerance kinds map directly to physical domains:

| Kind | Tolerance | Use for |
|---|---|---|
| `"longitude"` | 1e-6° | ecliptic longitudes, latitudes, house cusps |
| `"distance"` | 1e-9 AU | heliocentric / geocentric distances |
| `"angle"` | 1e-4° | aspects, separations, arc lengths |
| `"time"` | 1e-8 days | Julian Dates, transit times |
| `"ratio"` | 1e-9 | unitless ratios, magnitude differences |

- [ ] **Step 1: Find all files with hardcoded tolerances**

```
grep -rl "pytest.approx" tests/ --include="*.py"
```

Save the list. Work through files one at a time.

- [ ] **Step 2: For each file, add `moira_approx` fixture parameter**

Before (example from `test_chiron_planet_bridge.py`):
```python
def test_planet_at_chiron_matches_asteroid_oracle() -> None:
    jd_ut = 2451545.0
    bridged = planet_at(Body.CHIRON, jd_ut)
    reference = asteroid_at(Body.CHIRON, jd_ut)

    assert bridged.longitude == pytest.approx(reference.longitude, abs=1e-12)
    assert bridged.latitude  == pytest.approx(reference.latitude,  abs=1e-12)
    assert bridged.distance  == pytest.approx(reference.distance,  abs=1e-6)
    assert bridged.speed     == pytest.approx(reference.speed,     abs=1e-9)
```

After:
```python
def test_planet_at_chiron_matches_asteroid_oracle(jd_j2000, moira_approx) -> None:
    bridged = planet_at(Body.CHIRON, jd_j2000)
    reference = asteroid_at(Body.CHIRON, jd_j2000)

    assert bridged.longitude == moira_approx(reference.longitude, kind="longitude")
    assert bridged.latitude  == moira_approx(reference.latitude,  kind="longitude")
    assert bridged.distance  == moira_approx(reference.distance,  kind="distance")
    assert bridged.speed     == moira_approx(reference.speed,     kind="ratio")
```

- [ ] **Step 3: For bare `pytest.approx()` (no explicit abs) — use `moira_approx` with the appropriate kind**

Before:
```python
assert ms.angular_separation_at(castor, J2000) == pytest.approx(
    ms.angular_separation_at(castor, J2035)
)
```

After:
```python
assert ms.angular_separation_at(castor, J2000) == moira_approx(
    ms.angular_separation_at(castor, J2035), kind="angle"
)
```

- [ ] **Step 4: Run after each file**

```
pytest <file> -q
```

- [ ] **Step 5: Final sweep — confirm no hardcoded abs tolerances remain**

```
grep -rn "pytest.approx.*abs=" tests/ --include="*.py"
```
Expected: no output (or only in files that have documented reasons to stay as-is).

- [ ] **Step 6: Commit**

```bash
git add tests/
git commit -m "test: replace hardcoded pytest.approx tolerances with moira_approx"
```

---

## Task 4: Standardize structural invariants with `assert_longitude`

**Pattern:** Replace any manual `assert 0 <= x < 360` or `assert 0.0 <= cusp < 360.0` with `assert_longitude(x)`.

This is most prevalent in house tests and any test iterating over cusp lists.

- [ ] **Step 1: Find all manual range checks**

```
grep -rn "0 <= .* < 360\|0\.0 <= .* < 360" tests/ --include="*.py"
```

- [ ] **Step 2: Replace each with assert_longitude**

Before:
```python
def test_all_cusps_in_valid_range(natal_houses):
    for cusp in natal_houses.cusps:
        assert 0.0 <= cusp < 360.0
```

After:
```python
def test_all_cusps_in_valid_range(natal_houses, assert_longitude):
    for cusp in natal_houses.cusps:
        assert_longitude(cusp)
```

Before (with label):
```python
for body, pos in chart.positions.items():
    assert 0 <= pos.longitude < 360, f"{body} longitude out of range"
```

After:
```python
for body, pos in chart.positions.items():
    assert_longitude(pos.longitude, label=body)
```

(`assert_longitude` accepts an optional `label=` kwarg for failure messages.)

- [ ] **Step 3: Run the affected files**

```
pytest tests/ -q -k "cusp or longitude or house" 
```

- [ ] **Step 4: Commit**

```bash
git add tests/
git commit -m "test: replace manual 0<=lon<360 checks with assert_longitude fixture"
```

---

## Task 5: Activate `reference_epoch` parametrization in house invariant tests

`reference_epoch` parametrizes over 5 well-known epochs: J2000.0, B1900.0, Julian reform (1582-10-15), Julian epoch, J2100.0. Any test that asserts a structural invariant (cusp count, range, ordering) should use it.

**Target files:**
- `tests/unit/test_house_membership.py` — cusp count and range invariants
- `tests/unit/test_house_boundary.py` — boundary structure invariants
- `tests/unit/test_house_angularity.py` — angularity structure invariants
- `tests/unit/test_house_comparison.py` — comparison structure invariants
- `tests/unit/test_house_distribution.py` — distribution structure invariants

- [ ] **Step 1: Identify which tests in each file assert structural invariants (not values)**

Structural invariants are: cusp count == 12, cusps in [0, 360), asc == cusps[0] for quadrant systems, etc. Value tests (exact float comparisons against reference data) should NOT use `reference_epoch`.

- [ ] **Step 2: Extract invariant tests into parametrized functions**

Before (a test that only checks J2000.0):
```python
def test_always_twelve_cusps(natal_houses):
    assert len(natal_houses.cusps) == 12
```

After (checks the same invariant across all 5 epochs):
```python
def test_always_twelve_cusps(moira_engine, reference_epoch, assert_longitude):
    jd, label = reference_epoch
    result = calculate_houses(jd, 51.5, 0.0, HouseSystem.PLACIDUS)
    assert len(result.cusps) == 12, f"Failed at {label}"
    for cusp in result.cusps:
        assert_longitude(cusp, label=f"{label} cusp")
```

- [ ] **Step 3: Run and confirm — 5× more test cases, all green**

```
pytest tests/unit/test_house_membership.py tests/unit/test_house_boundary.py -v
```
Expect test IDs like `test_always_twelve_cusps[J2000.0]`, `test_always_twelve_cusps[B1900.0]`, etc.

- [ ] **Step 4: Commit**

```bash
git add tests/unit/test_house_membership.py tests/unit/test_house_boundary.py tests/unit/test_house_angularity.py tests/unit/test_house_comparison.py tests/unit/test_house_distribution.py
git commit -m "test: activate reference_epoch parametrization for house invariant tests"
```

---

## Task 6: Activate `any_house_system` parametrization in structural house tests

`any_house_system` parametrizes over every `HouseSystem` enum value. Use it for tests that assert invariants that must hold regardless of which system is used — cusp count, range validity, fallback field types, etc.

**Target files:**
- `tests/unit/test_house_membership.py`
- `tests/unit/test_house_boundary.py`
- `tests/unit/test_house_angularity.py`
- `tests/unit/test_house_comparison.py`
- `tests/unit/test_house_distribution.py`

- [ ] **Step 1: Identify tests that are currently hardcoded to one system**

Look for tests that call `calculate_houses(..., HouseSystem.PORPHYRY)` or `calculate_houses(..., HouseSystem.PLACIDUS)` in a way that is asserting a universal structural invariant, not a system-specific value.

- [ ] **Step 2: Parametrize with `any_house_system`**

Before:
```python
def test_cusp_count_is_always_twelve(jd_j2000):
    result = calculate_houses(jd_j2000, 51.5, 0.0, HouseSystem.PORPHYRY)
    assert len(result.cusps) == 12
```

After:
```python
def test_cusp_count_is_always_twelve(jd_j2000, any_house_system, assert_longitude):
    result = calculate_houses(jd_j2000, 51.5, 0.0, any_house_system)
    assert len(result.cusps) == 12, f"Failed for {any_house_system}"
    for cusp in result.cusps:
        assert_longitude(cusp, label=any_house_system)
```

Combine with `reference_epoch` from Task 5 where both apply:
```python
def test_cusp_count_all_systems_all_epochs(moira_engine, reference_epoch, any_house_system, assert_longitude):
    jd, label = reference_epoch
    result = calculate_houses(jd, 51.5, 0.0, any_house_system)
    assert len(result.cusps) == 12, f"Failed for {any_house_system} at {label}"
    for cusp in result.cusps:
        assert_longitude(cusp, label=f"{any_house_system} @ {label}")
```

- [ ] **Step 3: Run and confirm — N_systems × test_count cases, all green**

```
pytest tests/unit/test_house_membership.py -v --co | head -40
```
Verify the parametrize IDs include system names.

```
pytest tests/unit/test_house_membership.py tests/unit/test_house_boundary.py tests/unit/test_house_angularity.py tests/unit/test_house_comparison.py tests/unit/test_house_distribution.py -q
```
Expected: all pass.

- [ ] **Step 4: Commit**

```bash
git add tests/unit/test_house_membership.py tests/unit/test_house_boundary.py tests/unit/test_house_angularity.py tests/unit/test_house_comparison.py tests/unit/test_house_distribution.py
git commit -m "test: activate any_house_system parametrization for structural house invariants"
```

---

## Self-review

**Spec coverage:**
- Task 1 covers `jd_j2000` adoption (6 files, 3 structural patterns) ✓
- Task 2 covers `moira_engine` adoption (12 files, `setup_method` + standalone patterns) ✓
- Task 3 covers `moira_approx` adoption (~52 files, 2 sub-patterns) ✓
- Task 4 covers `assert_longitude` adoption ✓
- Task 5 covers `reference_epoch` activation ✓
- Task 6 covers `any_house_system` activation ✓

**Placeholder scan:** No TBD, TODO, or "similar to task N" present.

**Type consistency:** `jd_j2000` fixture returns `float` throughout. `moira_engine` is `Moira`. `reference_epoch` yields `(float, str)` tuple unpacked as `jd, label`. `any_house_system` yields a `HouseSystem` string value.
