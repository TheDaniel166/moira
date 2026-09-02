# Delta-T Future Scenario Recalibration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Recalibrate the default post-`Y0` ΔT mean to `D0 + 29.09·(h/100)²` with sourced tidal 43.7 s/cy² and GIA −14.61 s/cy², drop the linear `m0` term, and keep C0 without claiming C1.

**Architecture:** `delta_t_physical.py` remains the future-scenario owner. Source-era totals still copy `julian.delta_t`. Only the public curvature coefficients, the future bridge (no `m0·h`), and the matching coefficient scales in `sigma` change. Default `julian.delta_t` after `Y0` follows automatically through the existing deferred import of `delta_t_hybrid`.

**Tech Stack:** Python 3.10+, `moira.delta_t_physical`, `moira.julian._delta_t_observation_boundary`, pytest, project `.venv`.

**Spec:** `docs/superpowers/specs/2026-08-27-delta-t-future-scenario-recalibration-design.md`

## Global Constraints

- `ΔT(year > Y0) = D0 + (TIDAL_COEFF + GIA_COEFF) · (h/100)²` with `h = year − Y0`.
- `TIDAL_COEFF = 43.7` (Morrison et al. 2021, their ΔT coefficient). Do not re-derive 2.40 × 18.2625 = 43.83.
- `_GIA_LOD_RATE_MS_PER_CY = -0.80` (Shahvandi et al. 2024). `GIA_COEFF = _GIA_LOD_RATE_MS_PER_CY * JULIAN_YEAR / 20.0` (−14.61).
- No linear term. Physical mean must not read `_delta_t_observation_boundary().slope`.
- C0 at `Y0` is required. C1 is not claimed.
- No climate/barystatic term. No new `DeltaTPolicy` name. This is the default clock after `Y0`.
- `delta_t_hybrid(y) == julian.delta_t(y)` remains exact for every `y ≤ Y0`.
- `REFERENCE_LOD` stays `69.11474233219883`. `REFERENCE_YEAR` stays the import-time `Y0` snapshot.
- Future `sigma` stays arithmetic policy scale: `0.06 + 0.2·q² + 1.82625·q² + σ_OU(h)`. Do not retune the O-U constants. Do not switch to quadrature. Do not claim coverage probability.
- Do not re-admit GRACE, C04, AAM, or OAM. Do not remove dead research helpers. Do not refresh HPIERS 2016. Do not retarget `REFERENCE_LOD` to `D0`. Do not change EOP, NASA-canon, domain bounds, era labels, `DeltaTBreakdown` fields, or native code.
- Do not change `_delta_t_observation_boundary()`. Do not hand-edit `moira.wiki/`.
- PROTECTED zone: `moira/julian.py`, `moira/delta_t_physical.py`, `moira/data/`, `tests/` validation, `wiki/03_validation/`. State the zone before editing.
- Author in `C:\dev\moira` on a feature branch. Use `.\.venv\Scripts\python.exe` for every command. Write CHANGELOG under `[Unreleased]`. Do not pick a version number.

---

## File map

**Modify**

- `moira/delta_t_physical.py` — coefficients, future bridge, uncertainty scales, module/function docstrings
- `tests/unit/test_delta_t_physical.py` — constants, formula, C0/right-slope, 2100, slope-ignored, sigma scales
- `tests/integration/test_delta_t_hybrid.py` — future helper, handoff test
- `scripts/validate_delta_t_hybrid.py` — future helper, C0-only handoff receipt
- `wiki/02_standards/DELTA_T_HYBRID_MODEL.md` — §§3, 4, 6, 9, 10, 11; version 3.3
- `CHANGELOG.md` — `[Unreleased]` Changed

**Do not modify**

- `moira/julian.py` (no comment currently states `D0 + m0·h + 28 q²`)
- `wiki/02_standards/API_REFERENCE.md` (does not state 31 / −3 / 28)
- `moira/data/delta_t_manifest.json`
- `moira.wiki/` by hand (regenerate with `scripts/sync_git_wiki.py`)
- Native code, EOP, HPIERS table, REST

**Do not create**

- No new public function, policy name, or data file.

---

### Task 1: Rewrite unit contracts so the old scenario fails

**Files:**
- Modify: `tests/unit/test_delta_t_physical.py`
- Test: `tests/unit/test_delta_t_physical.py`

**Interfaces:**
- Consumes: existing `dtp` import, `julian_module._delta_t_observation_boundary`, `JULIAN_YEAR`
- Produces: unit tests that require `TIDAL_COEFF == 43.7`, `GIA_COEFF == -14.61`, future mean `D0 + (TIDAL_COEFF + GIA_COEFF)·q²` with no `m0`, C0 plus right-hand slope ≈ 0, and coefficient sigmas `0.2` / `1.82625`

- [ ] **Step 1: Create the feature branch**

```powershell
Set-Location C:\dev\moira
git checkout main
git pull --ff-only
git checkout -b delta-t-future-scenario-recalibration
```

- [ ] **Step 2: Replace the unit contracts**

In `tests/unit/test_delta_t_physical.py`, replace these functions in full (keep every other test in the file).

Replace `test_public_constants_preserve_the_established_surface`:

```python
def test_public_constants_preserve_the_established_surface() -> None:
    assert dtp.TIDAL_COEFF == 43.7
    assert dtp._GIA_LOD_RATE_MS_PER_CY == -0.80
    assert dtp.GIA_COEFF == pytest.approx(
        dtp._GIA_LOD_RATE_MS_PER_CY * JULIAN_YEAR / 20.0, abs=1e-12
    )
    assert dtp.GIA_COEFF == pytest.approx(-14.61, abs=1e-12)
    assert dtp._TIDAL_COEFF_SIGMA == 0.2
    assert dtp._GIA_COEFF_SIGMA == pytest.approx(0.10 * JULIAN_YEAR / 20.0, abs=1e-12)
    assert dtp.REFERENCE_LOD == pytest.approx(69.11474233219883, abs=1e-12)
    assert dtp.REFERENCE_YEAR == pytest.approx(
        julian_module._monthly_mean_representative_epoch(2026, 4), abs=1e-12
    )
```

Replace `_future_formula` so it has no slope term:

```python
def _future_formula(year: float) -> float:
    boundary = julian_module._delta_t_observation_boundary()
    horizon = year - boundary.year
    curvature = dtp.TIDAL_COEFF + dtp.GIA_COEFF
    return boundary.total + curvature * (horizon / 100.0) ** 2
```

Replace `test_current_2100_scenario_is_not_the_rejected_historical_slope_path`:

```python
def test_current_2100_scenario_is_not_the_rejected_historical_slope_path() -> None:
    assert dtp.delta_t_hybrid(2100.0) == pytest.approx(_future_formula(2100.0), abs=1e-12)
    assert dtp.delta_t_hybrid(2100.0) < 100.0
```

Replace `test_reference_handoff_is_c1` with:

```python
def test_reference_handoff_is_c0_and_right_slope_is_the_parabola() -> None:
    step = 1e-3
    at = dtp.delta_t_hybrid(dtp.REFERENCE_YEAR)
    left_slope = (at - dtp.delta_t_hybrid(dtp.REFERENCE_YEAR - step)) / step
    right_slope = (dtp.delta_t_hybrid(dtp.REFERENCE_YEAR + step) - at) / step
    table_slope = julian_module._delta_t_observation_boundary().slope
    curvature = dtp.TIDAL_COEFF + dtp.GIA_COEFF
    parabola_slope = 2.0 * curvature * step / 10_000.0
    assert left_slope == pytest.approx(table_slope, abs=1e-8)
    assert right_slope == pytest.approx(parabola_slope, abs=3e-6)
```

Replace the docstring assertions inside `test_future_uncertainty_is_an_arithmetic_uncalibrated_policy_scale` so they match the new caveat (keep the `math.fsum` arithmetic check):

```python
    assert dtp.delta_t_hybrid_uncertainty(year) == pytest.approx(expected, abs=1e-12)
    doc = dtp.delta_t_hybrid_uncertainty.__doc__ or ""
    assert "uncalibrated" in doc
    assert "core-anomaly persistence" in doc
    assert "boundary slope" not in doc
```

Insert this new test immediately after `test_physical_model_consumes_the_dynamic_annual_boundary`:

```python
def test_future_mean_ignores_observation_boundary_slope(monkeypatch) -> None:
    original = julian_module._delta_t_observation_boundary()

    def fake_boundary() -> julian_module._DeltaTObservationBoundary:
        return julian_module._DeltaTObservationBoundary(
            year=original.year,
            total=original.total,
            slope=original.slope + 1.0,
        )

    monkeypatch.setattr(julian_module, "_delta_t_observation_boundary", fake_boundary)
    year = original.year + 10.0
    expected = original.total + (dtp.TIDAL_COEFF + dtp.GIA_COEFF) * (10.0 / 100.0) ** 2
    assert dtp.delta_t_hybrid(year) == pytest.approx(expected, abs=1e-12)
```

Keep `test_physical_model_consumes_the_dynamic_annual_boundary` as it is, including its `_reference_slope()` assertion. That function still documents the julian table diagnostic. After `_future_formula` drops `m0`, that test’s hybrid assertion will require the new mean.

Do not edit `test_secular_trend_is_reference_anchored_curvature`. It already uses `TIDAL_COEFF + GIA_COEFF`.

- [ ] **Step 3: Run the rewritten unit tests and confirm they fail**

```powershell
Set-Location C:\dev\moira
.\.venv\Scripts\python.exe -m pytest tests/unit/test_delta_t_physical.py::test_public_constants_preserve_the_established_surface tests/unit/test_delta_t_physical.py::test_current_2100_scenario_is_not_the_rejected_historical_slope_path tests/unit/test_delta_t_physical.py::test_reference_handoff_is_c0_and_right_slope_is_the_parabola tests/unit/test_delta_t_physical.py::test_future_mean_ignores_observation_boundary_slope tests/unit/test_delta_t_physical.py::test_future_uncertainty_is_an_arithmetic_uncalibrated_policy_scale tests/unit/test_delta_t_physical.py::test_future_mean_is_boundary_conditioned_formula -q
```

Expected: FAIL. Constants still 31 / −3; 2100 still includes `m0`; C1 test name is the new one and right slope still matches the table; docstring still says “boundary slope”.

- [ ] **Step 4: Commit the failing tests**

```powershell
git add tests/unit/test_delta_t_physical.py
git commit -m "test: lock sourced Delta-T future curve without m0"
```

---

### Task 2: Recalibrate the physical future mean

**Files:**
- Modify: `moira/delta_t_physical.py` (module docstring lines 1–26; constants 67–92; `_future_bridge_delta_t` 343–349; `delta_t_hybrid_uncertainty` docstring 626–636)
- Test: `tests/unit/test_delta_t_physical.py`

**Interfaces:**
- Consumes: `JULIAN_YEAR`, `_delta_t_observation_boundary().year` / `.total` (not `.slope`)
- Produces: `TIDAL_COEFF: float = 43.7`, `GIA_COEFF: float` from signed GIA LOD rate, `_future_bridge_delta_t(year: float) -> float` with no linear term, `_TIDAL_COEFF_SIGMA = 0.2`, `_GIA_COEFF_SIGMA = 0.10 * JULIAN_YEAR / 20.0`

- [ ] **Step 1: State the protected-zone ritual (do not skip)**

Before editing, record in the commit message body or the working notes:

1. Change: sourced tidal/GIA coefficients, drop `m0` from the future mean, update coefficient `sigma` scales.
2. Files: `moira/delta_t_physical.py` only in this task.
3. Zone: PROTECTED time-scale (`moira/delta_t_physical.py`).
4. Governing object: post-`Y0` ΔT scenario mean. Authority: Morrison et al. 2021 and Shahvandi et al. 2024 for coefficients; USNO aggregate table for `Y0`/`D0`.
5. Fixtures: `tests/unit/test_delta_t_physical.py`.
6. Verify with project `.venv` pytest.

- [ ] **Step 2: Replace the module docstring claims**

Replace the third and fourth bullets of the module docstring (the “After the reference epoch” and “HPIERS-owned historical uncertainty” bullets) with:

```python
* After the reference epoch, the mean is a boundary-conditioned scenario:
  the admitted value at the hand-off plus the declared tidal/GIA curvature.
  The provisional aggregate-epoch slope is not consumed.  The scenario is
  not a geophysical component inversion.  Values after 2150 are
  mathematical continuation of that scenario, not a validated forecast.
* HPIERS-owned historical uncertainty comes from that source table's error
  column. The source bridge and aggregate era use the modern policy floor. The
  future ``sigma`` field is an uncalibrated policy scale: it has no stated
  coverage probability and omits unquantified handoff-value uncertainty and
  core-anomaly persistence.
```

- [ ] **Step 3: Replace the coefficient block**

Replace `TIDAL_COEFF` through `_GIA_COEFF_SIGMA` with:

```python
# Morrison, Stephenson, Hohenkerk & Zawilski (2021), Proc. R. Soc. A 477,
# 20200776: published tidal Delta-T coefficient in s/cy².  Do not re-derive
# this from 2.40 ms/cy × JULIAN_YEAR / 20 (that product is 43.83).
TIDAL_COEFF: float = 43.7
# Shahvandi, Adhikari, Dumberry, Borsa & Soja (2024), PNAS 121, e2406930121:
# GIA LOD rate in ms/cy (negative = Earth spinning up).  Converted to Delta-T
# s/cy² with JULIAN_YEAR / 20.
_GIA_LOD_RATE_MS_PER_CY: float = -0.80
GIA_COEFF: float = _GIA_LOD_RATE_MS_PER_CY * JULIAN_YEAR / 20.0

# Compatibility name: this value is a Delta-T baseline in seconds, not a
# length-of-day measurement.  Renaming the exported symbol would break the
# established Python surface, so the truthful meaning is documented here.
REFERENCE_LOD: float = 69.11474233219883
# Compatibility snapshot of the source-owned aggregate boundary at import time.
# Runtime routing reads the same boundary vessel dynamically, so refreshing
# the annual table cannot leave the model anchored to an independent literal.
REFERENCE_YEAR: float = _delta_t_observation_boundary().year

_PHYSICAL_SOURCE_START: float = -2000.0
_FORECAST_VALID_THROUGH: float = 2150.0
_SMH_FINAL_YEAR: float = 2016.0
# Uncalibrated bridge/aggregate policy scale.  The 0.06-second value covers
# the measured 0.052808-second maximum daily residual of the representative-
# epoch aggregate interpolation against the bundled EOP snapshot.
_MODERN_SOURCE_ERROR_FLOOR: float = 0.06

# Future coefficient scales follow the same two papers.  They are not a
# complete 2100 error budget and are not probability-standard-deviation
# claims.  Handoff-value uncertainty and core-anomaly persistence are omitted.
_TIDAL_COEFF_SIGMA: float = 0.2
_GIA_COEFF_SIGMA: float = 0.10 * JULIAN_YEAR / 20.0
_LOD_RANDOM_WALK_SIGMA_MS_PER_DAY_SQRT_YEAR: float = 0.2379
_LOD_OU_REVERSION_RATE: float = 0.1
```

Leave `_PHYSICAL_SOURCE_START` through `_MODERN_SOURCE_ERROR_FLOOR` as in that block (same values as today). Do not change `_LOD_RANDOM_WALK_SIGMA_MS_PER_DAY_SQRT_YEAR` or `_LOD_OU_REVERSION_RATE`.

- [ ] **Step 4: Drop `m0` from the future bridge**

Replace `_future_bridge_delta_t` with:

```python
def _future_bridge_delta_t(year: float) -> float:
    value = _coerce_model_year(year)
    if value <= _reference_year():
        return 0.0
    return _reference_total() - REFERENCE_LOD
```

Keep `_reference_slope()` defined. Tests and the julian boundary diagnostic still call it. The admitted mean must not call it.

- [ ] **Step 5: Update the uncertainty docstring**

Replace `delta_t_hybrid_uncertainty`’s docstring with:

```python
    """Return a source error or explicitly uncalibrated policy scale.

    HPIERS-era values use the table's published error. Later source-bridge and
    aggregate rows use a 0.06-second policy scale that covers the verified
    first-of-month residuals against the bundled EOP snapshot; the aggregate
    table carries no row-level errors. Future values add sourced curvature
    coefficient scales (Morrison et al. 2021 ±0.2 s/cy²; Shahvandi et al. 2024
    ±0.10 ms/cy) and the stochastic policy term arithmetically. The result has
    no calibrated coverage interpretation. It omits unquantified handoff-value
    uncertainty and core-anomaly persistence.
    """
```

Do not change the function body. The body already multiplies `_TIDAL_COEFF_SIGMA` and `_GIA_COEFF_SIGMA` by `q²` and `fsum`s them with the floor and O-U term.

- [ ] **Step 6: Run the unit file**

```powershell
Set-Location C:\dev\moira
.\.venv\Scripts\python.exe -m pytest tests/unit/test_delta_t_physical.py -q
```

Expected: PASS. `ΔT(2100)` is about 85.00 s and `< 100`.

- [ ] **Step 7: Commit**

```powershell
git add moira/delta_t_physical.py
git commit -m "fix: source tidal/GIA curvature and drop future m0"
```

---

### Task 3: Align integration proofs and the validate receipt

**Files:**
- Modify: `tests/integration/test_delta_t_hybrid.py`
- Modify: `scripts/validate_delta_t_hybrid.py`
- Test: `tests/integration/test_delta_t_hybrid.py`

**Interfaces:**
- Consumes: `dtp.TIDAL_COEFF`, `dtp.GIA_COEFF`, `_delta_t_observation_boundary().year` / `.total`
- Produces: integration and receipt checks of `D0 + (TIDAL_COEFF + GIA_COEFF)·q²` and C0-only handoff

- [ ] **Step 1: Replace the integration future helper and handoff test**

In `tests/integration/test_delta_t_hybrid.py`, replace `test_future_scenario_is_boundary_conditioned_and_continues_past_confidence_boundary` with:

```python
def test_future_scenario_is_boundary_conditioned_and_continues_past_confidence_boundary() -> None:
    boundary = julian_module._delta_t_observation_boundary()
    reference = boundary.total
    curvature = dtp.TIDAL_COEFF + dtp.GIA_COEFF

    for year in (2027.0, 2030.0, 2050.0, 2100.0, 2150.0, 2150.0001, 2200.0):
        horizon = year - boundary.year
        expected = reference + curvature * (horizon / 100.0) ** 2
        assert dtp.delta_t_hybrid(year) == pytest.approx(expected, abs=1e-12)
```

Replace `test_future_handoff_matches_value_and_observed_boundary_slope` with:

```python
def test_future_handoff_matches_value_and_does_not_use_table_slope() -> None:
    step = 1e-3
    reference = dtp.delta_t_hybrid(dtp.REFERENCE_YEAR)
    left_slope = (reference - dtp.delta_t_hybrid(dtp.REFERENCE_YEAR - step)) / step
    right_slope = (dtp.delta_t_hybrid(dtp.REFERENCE_YEAR + step) - reference) / step
    source_slope = julian_module._delta_t_observation_boundary().slope
    curvature = dtp.TIDAL_COEFF + dtp.GIA_COEFF
    parabola_slope = 2.0 * curvature * step / 10_000.0
    assert reference == pytest.approx(julian_module._delta_t_observation_boundary().total, abs=1e-12)
    assert left_slope == pytest.approx(source_slope, abs=1e-8)
    assert right_slope == pytest.approx(parabola_slope, abs=3e-6)
```

- [ ] **Step 2: Run the integration file and confirm the old C1 name is gone**

```powershell
Set-Location C:\dev\moira
.\.venv\Scripts\python.exe -m pytest tests/integration/test_delta_t_hybrid.py tests/integration/test_delta_t_model_comparison.py tests/unit/test_delta_t_policy.py tests/unit/test_julian_delta_t.py tests/unit/test_delta_t_data_integrity.py -q
```

Expected: PASS. `test_delta_t_model_comparison.py` compares hybrid vs physical vs nasa vs fixed and does not pin 83.294.

- [ ] **Step 3: Update the validate-script formula and handoff receipt**

In `scripts/validate_delta_t_hybrid.py`, replace `_future_expected` with:

```python
def _future_expected(year: float) -> float:
    boundary = _delta_t_observation_boundary()
    horizon = year - boundary.year
    curvature = dtp.TIDAL_COEFF + dtp.GIA_COEFF
    return boundary.total + curvature * (horizon / 100.0) ** 2
```

Replace the C0/C1 handoff `record(...)` block with:

```python
    step = 1e-3
    reference = dtp.delta_t_hybrid(boundary.year)
    left_slope = (reference - dtp.delta_t_hybrid(boundary.year - step)) / step
    right_slope = (dtp.delta_t_hybrid(boundary.year + step) - reference) / step
    curvature = dtp.TIDAL_COEFF + dtp.GIA_COEFF
    parabola_slope = 2.0 * curvature * step / 10_000.0
    record(
        f"{boundary.year:g} C0 handoff",
        reference == boundary.total and abs(right_slope - parabola_slope) < 3e-6,
        (
            f"value={reference:.9f} s; left slope={left_slope:.9f}; "
            f"right slope={right_slope:.9f} s/year"
        ),
    )
```

- [ ] **Step 4: Run the validate receipt**

```powershell
Set-Location C:\dev\moira
.\.venv\Scripts\python.exe scripts/validate_delta_t_hybrid.py
```

Expected: process exit 0. Printed `Delta-T(2100)` about 85.00 s. Handoff check named `C0 handoff`.

- [ ] **Step 5: Commit**

```powershell
git add tests/integration/test_delta_t_hybrid.py scripts/validate_delta_t_hybrid.py
git commit -m "test: prove C0 future handoff without table slope"
```

---

### Task 4: Doctrine, changelog, wiki mirror

**Files:**
- Modify: `wiki/02_standards/DELTA_T_HYBRID_MODEL.md`
- Modify: `CHANGELOG.md` (`[Unreleased]` / `### Changed`)
- Generate: `moira.wiki/DELTA_T_HYBRID_MODEL.md` via `scripts/sync_git_wiki.py`

**Interfaces:**
- Consumes: the locked formula from Task 2
- Produces: wiki version 3.3 describing `D0 + 29.09 q²`, no `m0`, no C1, no climate term, sourced `sigma` scales

- [ ] **Step 1: Update the wiki header and §3**

In `wiki/02_standards/DELTA_T_HYBRID_MODEL.md` set:

```markdown
**Version:** 3.3

**Date:** 2026-08-27
```

Replace all of `## 3. Future mean scenario` with the following section. Keep the two inner `text` fences as they appear here:

````markdown
## 3. Future mean scenario

Let the final aggregate representative epoch define a boundary vessel

```text
Y0 = final aggregate representative epoch # currently about 2026.123
D0 = final aggregate Delta T
h  = year - Y0                           # years after the handoff
```

The post-handoff mean is

```text
Delta T scenario(year) = D0 + 29.09*(h/100)^2
```

`29.09 s/cy²` is the declared sum of a `+43.7 s/cy²` tidal term (Morrison,
Stephenson, Hohenkerk, and Zawilski 2021, their published Delta-T
coefficient) and a `−14.61 s/cy²` GIA term (Shahvandi et al. 2024 GIA LOD
rate `−0.80 ms/cy`, converted with `JULIAN_YEAR / 20`). It is forecast
doctrine, not an observation and not a fitted decomposition of the
historical source total.

The construction preserves the admitted value at the handoff (C0). It does
not consume the slope of the final two aggregate epochs. That slope remains
a table diagnostic on the boundary vessel. The current final product is a
Jan–Apr 2026 partial mean; treating it as a century derivative would
extrapolate the present core-driven flattening. The right-hand derivative
at `Y0` is therefore the parabola’s derivative, which is zero. C1 is not
claimed.

No climate or barystatic ice-melt term is included. Shahvandi et al. 2024
project a climate-induced LOD rate of about `+1.33 ms/cy` since 2000 and
up to `+2.62 ms/cy` by 2100 under high emissions. That process is omitted
from this clock by explicit decision, not because it is zero.

The scenario is useful for deterministic future computation, but Earth
rotation remains unpredictable. No value after the current final aggregate epoch is
described as observed merely because it is produced by the scenario.
No value after 2150 is described as a validated forecast.
````

- [ ] **Step 2: Update wiki §§4, 6, 9, 10, 11**

In §4, replace the `bridge` bullet with:

```markdown
- `bridge` is the explicit reconciliation between the declared curvature
  baseline and the admitted total. In the future it carries the boundary
  value offset `D0 − REFERENCE_LOD` only. It is arithmetic accounting, not
  a fitted physical cause.
```

Replace the future-`sigma` display in §6 with:

```text
sigma(year) = 0.06 s
            + 0.2 s/cy² * q²
            + 1.82625 s/cy² * q²
            + sigma_OU(h)
```

and replace the paragraph that currently says “The handoff value's source error and the uncertainty of the final-row slope are not propagated” with:

```markdown
The O-U term is conditional on the declared `theta = 0.1/year` and
diffusion scale. Those stochastic coefficients do not have a complete
traceable calibration record in the module. The `0.2 s/cy²` and
`0.10 ms/cy` figures are literature coefficient scales, not a complete
2100 error budget. The handoff value's source error and core-anomaly
persistence (the meaning of setting the linear term to zero) are not
propagated. Accordingly, the result is explicitly an **uncalibrated
policy scale**: it has no asserted 68-percent or other coverage
probability and is not a proof of independent causal errors. The stable
field name `sigma` is compatibility vocabulary, not a calibration claim.
```

In §9, replace the boundary-tests bullet with:

```markdown
- boundary tests prove C0 value continuity at the source-owned final
  aggregate representative epoch, including synthetic source extension and
  contraction; they prove the right-hand slope is the parabola, not the
  table slope;
```

In §10, replace item 4 with:

```markdown
4. let the boundary vessel derive `Y0` and `D0` directly from the final
   admitted row; do not add a second literal handoff year. The table slope
   of the final two rows remains a diagnostic and is not a scenario input;
```

In §11, add these two bullets after the Stephenson 2016 bullet, and keep Caron et al. 2018:

```markdown
- Morrison, L. V., Stephenson, F. R., Hohenkerk, C. Y., and Zawilski, M.
  (2021), *Addendum 2020 to ‘Measurement of the Earth’s rotation: 720 BC
  to AD 2015’*, for the tidal Delta-T coefficient `43.7 ± 0.2 s/cy²`.
  This paper does not replace the packaged HPIERS 2016 mean table.
- Shahvandi, M. K., Adhikari, S., Dumberry, M., Borsa, A., and Soja, B.
  (2024), *The increasingly dominant role of climate change on length of
  day variations*, DOI `10.1073/pnas.2406930121`, for the GIA LOD rate
  `−0.80 ± 0.10 ms/cy` used in the future curvature. The paper’s climate
  ice-melt projection is not admitted into the default clock.
```

- [ ] **Step 3: Add the changelog entry**

Under `CHANGELOG.md` `## [Unreleased]` / `### Changed`, add this bullet first:

```markdown
- Recalibrated the default post-observation Delta-T scenario to
  `D0 + 29.09·((year − Y0)/100)²` using Morrison et al. 2021 tidal
  `43.7 s/cy²` and Shahvandi et al. 2024 GIA `−0.80 ms/cy`
  (`−14.61 s/cy²`). The linear handoff slope is no longer consumed
  (C0 kept, C1 not claimed). No climate ice-melt term is included.
  `ΔT(2100)` moves from 83.29 s to about 85.00 s. Source-era totals,
  quarantined component fields, EOP, and `DeltaTPolicy` names are
  unchanged.
```

- [ ] **Step 4: Sync the generated Git wiki mirror**

```powershell
Set-Location C:\dev\moira
.\.venv\Scripts\python.exe scripts/sync_git_wiki.py
```

Expected: `moira.wiki/DELTA_T_HYBRID_MODEL.md` matches the canonical wiki text. Do not edit `moira.wiki/` by hand.

- [ ] **Step 5: Run the full Delta-T verification set**

```powershell
Set-Location C:\dev\moira
.\.venv\Scripts\python.exe -m pytest tests/unit/test_delta_t_physical.py tests/integration/test_delta_t_hybrid.py tests/unit/test_julian_delta_t.py tests/integration/test_delta_t_model_comparison.py tests/unit/test_delta_t_policy.py tests/unit/test_delta_t_data_integrity.py -q
.\.venv\Scripts\python.exe scripts/validate_delta_t_hybrid.py
.\.venv\Scripts\python.exe scripts/sync_git_wiki.py --check
```

Expected: all pytest PASS, validate exit 0, wiki `--check` clean.

- [ ] **Step 6: Commit**

```powershell
git add wiki/02_standards/DELTA_T_HYBRID_MODEL.md CHANGELOG.md moira.wiki/DELTA_T_HYBRID_MODEL.md
git commit -m "docs: declare sourced Delta-T future scenario without m0"
```

---

## Self-review (plan vs spec)

| Spec requirement | Task |
|---|---|
| `TIDAL_COEFF = 43.7`, GIA from −0.80 ms/cy | Task 2 |
| No `m0`; physical mean must not read `.slope` | Tasks 1 (ignore-slope test), 2 |
| C0 yes, C1 no | Tasks 1, 3 |
| No climate term | Global constraints; wiki §3 |
| Default clock, no new policy | Global constraints |
| `sigma` arithmetic with 0.2 and 1.82625; OU untouched | Task 2 |
| Docstring: core-anomaly persistence, not handoff-slope | Tasks 1, 2, 4 |
| Source-era identity exact | Unchanged tests, Task 3 full run |
| 2100 vs live formula, `< 100`, no 83.294 pin | Task 1 |
| Wiki §§3, 4, 6, 9, 10, 11; CHANGELOG; no hand-edit of `moira.wiki/` | Task 4 |
| Do not change `julian._delta_t_observation_boundary` | File map |
| PROTECTED ritual | Task 2 Step 1 |
| Verification commands | Task 4 Step 5 |
