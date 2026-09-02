# Delta-T Future Scenario Recalibration

**Date:** 2026-08-27
**Status:** Draft, pending user review
**Zone:** PROTECTED (`moira/delta_t_physical.py`, `moira/julian.py` comments/docs only, Delta-T tests, wiki doctrine)

## Problem

`delta_t_physical.py` owns Moira’s post-observation ΔT mean. After the last
USNO aggregate epoch `Y0` it currently evaluates

```text
ΔT(year) = D0 + m0·h + 28·(h/100)²
h  = year − Y0
28 = TIDAL_COEFF + GIA_COEFF = 31 + (−3)
m0 = slope of the last two aggregate representative epochs
```

That structure (local parabola glued to the last admitted total) is correct.
Three of its numbers are not:

1. **31 / −3 are the wrong split.** Morrison, Stephenson, Hohenkerk & Zawilski
   (2021) give the tidal ΔT coefficient as **43.7 ± 0.2 s/cy²** (LOD
   +2.40 ± 0.01 ms/cy). Shahvandi, Adhikari, Dumberry, Borsa & Soja (PNAS
   2024) recover GIA at **−0.80 ± 0.10 ms/cy**. Converted with Moira’s
   `JULIAN_YEAR = 365.25`, that is **−14.61 s/cy²**. The *net* 28 vs 29.09
   is close; the public split is not.
2. **`m0` is a 4-month core flattening, not a century derivative.** The last
   knot is the Jan–Apr 2026 partial mean. The last two rows give
   `m0 ≈ −0.015 s/year`. Agnew (Metrologia 2026) shows that over decades the
   irregular core term dominates the tidal quadratic; Kasyanov (2024) and
   USNO practice treat the recent mantle speedup as transient. Extrapolating
   that slope to 2100 is the one current term that is actively misleading,
   even though it is only about −1.1 s at 2100.
3. Tests treat `31`, `−3`, C1 against `m0`, and `ΔT(2100) = 83.294…` as
   contracts of Earth rotation. They are contracts of the old scenario.

The module is otherwise doctrinally mature: source totals govern through
`Y0`, candidate core/cryo/fluid fields stay quarantined zeros, and the
future is an explicit scenario rather than a claimed inversion. This spec
does not reopen that.

## Decision

Recalibrate the **single default future curve**. Keep one number per year.
Change the default `julian.delta_t` after `Y0`.

```text
ΔT(year > Y0) = D0 + (TIDAL_COEFF + GIA_COEFF) · (h/100)²
```

- `TIDAL_COEFF = 43.7` s/cy² (Morrison et al. 2021, their published ΔT
  coefficient — do not re-derive 2.40 × 18.2625 = 43.83).
- `GIA_COEFF = −0.80 × JULIAN_YEAR / 20.0 = −14.61` s/cy².
- Net curvature **29.09 s/cy²**.
- **No linear term.** `m0` is not consumed. C0 at `Y0` is required. C1 is
  not claimed.
- **No climate/barystatic term.** Ice-melt (Shahvandi/Soja 2024, +1.33 ms/cy
  recent, RCP 8.5 up to 2.62 ms/cy by 2100) is a documented non-goal, not a
  silent zero in the science. It stays out of the clock.

On the current table this moves `ΔT(2100)` from 83.29 s to about **85.00 s**.

## Goals

- Post-`Y0` mean is `D0 + 29.09·(h/100)²` with the sourced split above.
- `delta_t_hybrid(y) == julian.delta_t(y)` remains **exact** for every
  `y ≤ Y0`.
- Value continuity (C0) at `Y0` is preserved to the existing 1e-6 tolerance.
- Right-hand derivative at `Y0` is the parabola’s derivative, which is 0.
  Left-hand derivative remains the table slope. Tests assert this split
  instead of C1.
- `TIDAL_COEFF` and `GIA_COEFF` remain the public names. Their values
  change. `REFERENCE_LOD` and `REFERENCE_YEAR` keep their present roles.
- Future `sigma` keeps the arithmetic policy-scale structure. Coefficient
  scales follow the same two papers. The Ornstein–Uhlenbeck term, the 0.06 s
  floor, and “not a coverage probability” stay.
- Wiki doctrine, module docstring, validate script, and CHANGELOG describe
  the new formula, the dropped C1 claim, and the omitted climate term.
- Quarantined artifacts remain unloaded by the admitted mean.

## Non-goals

- Climate / RCP / SSP scenario family.
- Monte Carlo / Agnew-style ensemble as the 2100 product.
- New `DeltaTPolicy` model name; this *is* the default clock after `Y0`.
- Re-admitting GRACE, C04 total-LOD, AAM, or OAM as `cryo` / `core` /
  `fluid`.
- Removing dead research helpers (`_cosine_taper`, dual HPIERS loaders, …).
- Calibrating `sigma` as 68% coverage, switching to quadrature, or
  propagating handoff-value uncertainty.
- Changing source-era routing, EOP, NASA-canon, domain bounds, era labels,
  `DeltaTBreakdown` field names, or native code.
- Refreshing the HPIERS 2016 table to Morrison et al. 2021 spline knots.
- Retargeting `REFERENCE_LOD` to `D0` (the 5 ms split is accounting only
  and cancels in the total).

## Formula

Let `Y0, D0` be `_delta_t_observation_boundary().year` and `.total`.
Let `h = year − Y0` and `q = h / 100`.

**Source era (`year ≤ Y0`):** unchanged. `delta_t_hybrid` copies
`julian.delta_t`. Breakdown `bridge = total − secular`.

**Future (`year > Y0`):**

```text
secular_trend(year) = REFERENCE_LOD + (43.7 − 14.61) · q²
bridge(year)        = D0 − REFERENCE_LOD
total(year)         = D0 + 29.09 · q²
```

`_future_bridge_delta_t` drops `_reference_slope() * horizon`.
`julian._delta_t_observation_boundary().slope` remains a table diagnostic.
The physical mean must not read it.

2150 remains a forecast-confidence label. Years after 2150 keep the same
formula and stay finite.

### Conversion

```text
s/cy² = (ms/cy) × JULIAN_YEAR / 20
      = (ms/cy) × 18.2625
```

This is the integral of a linear LOD rate over a Julian century, with LOD
in milliseconds per day. Use it for GIA (published as an LOD rate). Do not
use it to replace Morrison’s 43.7.

### 2100 check (current `_DELTA_T_ANNUAL`)

```text
Y0 ≈ 2026.123287671233
D0 = 69.12
h  ≈ 73.876712328767
q² ≈ 0.5457769
29.09 × q² ≈ 15.8766
ΔT(2100) ≈ 85.00 s
```

Tests must compare to the live formula at 1e-12, not to a hand-copied
literal that drifts if `Y0` moves. Keep `ΔT(2100) < 100` as the guard
against the rejected historical-slope path.

## Constants

In `moira/delta_t_physical.py`:

```python
TIDAL_COEFF: float = 43.7
_GIA_LOD_RATE_MS_PER_CY: float = -0.80  # Shahvandi et al. 2024; LOD decreasing
GIA_COEFF: float = _GIA_LOD_RATE_MS_PER_CY * JULIAN_YEAR / 20.0  # −14.61
_TIDAL_COEFF_SIGMA: float = 0.2
_GIA_COEFF_SIGMA: float = 0.10 * JULIAN_YEAR / 20.0  # 1.82625
```

Cite Morrison et al. 2021 next to `TIDAL_COEFF` and Shahvandi et al. 2024
next to `_GIA_LOD_RATE_MS_PER_CY`. Store the GIA LOD rate with its published
sign. `GIA_COEFF` is computed so a change to `JULIAN_YEAR` cannot silently
desynchronize the conversion. The 0.10 in `_GIA_COEFF_SIGMA` is the
published ±0.10 ms/cy, converted the same way.

`REFERENCE_LOD` stays `69.11474233219883`.
`REFERENCE_YEAR` stays the import-time snapshot of `Y0`.
Runtime routing continues to call `_reference_year()` / `_reference_total()`
dynamically.

## Uncertainty

`delta_t_hybrid_uncertainty` structure is unchanged:

| Era | Scale |
|---|---|
| HPIERS-owned mean | table quoted error |
| Source bridge through `Y0` | `0.06` s floor |
| `year > Y0` | `0.06 + 0.2·q² + 1.82625·q² + σ_OU(h)` |

Still `math.fsum` arithmetic, not quadrature. Still no coverage
probability. `DeltaTDistribution.pdf` / `interval` remain conveniences.

Docstring replacements:

- Remove “omits … handoff-slope uncertainty” as a used-input caveat.
- State that **m = 0 omits unquantified core-anomaly persistence**.
- Still omit unquantified handoff-value uncertainty.
- Name the 0.2 and 0.10 ms/cy figures as literature coefficient scales,
  not as a complete 2100 error budget.

Do not retune `_LOD_OU_REVERSION_RATE` or
`_LOD_RANDOM_WALK_SIGMA_MS_PER_DAY_SQRT_YEAR`.

## Continuity and error handling

- C0 at `Y0`: left, at, and right totals agree to the existing 1e-6
  (unit) / 1e-5 (integration seam) tolerances.
- C1 is **not** required. A new test proves the right-hand finite
  difference over `step = 1e-3` year equals
  `2 × 29.09 × step / 10000` (≈ 0) to the current right-side
  tolerance `3e-6`.
- Public year surfaces still reject non-finite, `< −2000`, and
  unrepresentable future years.
- Fail-closed residual spline, quarantined loaders, and HPIERS parser
  policy are untouched.

## Tests to rewrite

`tests/unit/test_delta_t_physical.py`

- `test_public_constants_preserve_the_established_surface`: 43.7 and
  `GIA_COEFF == pytest.approx(-14.61, abs=1e-12)`.
- `test_secular_trend_is_reference_anchored_curvature`: at `Y0+100`,
  `REFERENCE_LOD + TIDAL_COEFF + GIA_COEFF`.
- `_future_formula`: drop `reference_slope * horizon`.
- `test_reference_handoff_is_c1` → rename and assert C0 plus right-hand
  slope ≈ 0 as above.
- `test_current_2100_scenario_is_not_the_rejected_historical_slope_path`:
  formula agreement and `< 100`; delete the 83.294… pin.
- Uncertainty tests that expand `_TIDAL_COEFF_SIGMA` / `_GIA_COEFF_SIGMA`.

`tests/integration/test_delta_t_hybrid.py`

- Future expected-value helper matches the new formula.
- `test_future_handoff_matches_value_and_observed_boundary_slope` becomes
  C0 plus “right slope is not the table slope”.

`scripts/validate_delta_t_hybrid.py`: same formula.

Keep every source-priority identity, quarantine, loader, floor, domain,
vessel-field, and facade-export test.

## Documentation

- `wiki/02_standards/DELTA_T_HYBRID_MODEL.md` §3: new formula; no `m0`;
  C1 dropped; climate explicitly omitted. §6: new coefficient scales;
  core-persistence caveat. §10 maintenance rule: boundary still owns
  `Y0` and `D0`; it no longer feeds `m0` into the scenario. §11: add
  Morrison et al. 2021 and Shahvandi et al. 2024 as forecast-coefficient
  authorities (they do not govern the HPIERS 2016 mean table).
- `moira/delta_t_physical.py` module docstring and `secular_trend` /
  `_future_bridge_delta_t` / uncertainty docstrings.
- `CHANGELOG.md` entry: default post-`Y0` clock moves; 2100 ~+1.7 s.
- `wiki/02_standards/API_REFERENCE.md` only if it states 31 / −3 / 28.
- After wiki edit, the generated `moira.wiki/` copy is produced by
  `scripts/sync_git_wiki.py` — do not hand-edit `moira.wiki/`.

## Files

| File | Change |
|---|---|
| `moira/delta_t_physical.py` | coefficients, future bridge, docstrings, uncertainty scales |
| `tests/unit/test_delta_t_physical.py` | contracts above |
| `tests/integration/test_delta_t_hybrid.py` | contracts above |
| `scripts/validate_delta_t_hybrid.py` | future formula |
| `wiki/02_standards/DELTA_T_HYBRID_MODEL.md` | doctrine |
| `wiki/02_standards/API_REFERENCE.md` | only if coefficients are stated |
| `CHANGELOG.md` | user-visible clock change |

`moira/julian.py` is not required unless a comment still describes the
physical future as `D0 + m0·h + 28 q²`. If such a comment exists, update
it. Do not change `_delta_t_observation_boundary()`.

## Verification

PROTECTED pre-edit ritual applies. Use the project `.venv`.

```text
python -m pytest tests/unit/test_delta_t_physical.py tests/integration/test_delta_t_hybrid.py tests/unit/test_julian_delta_t.py tests/integration/test_delta_t_model_comparison.py tests/unit/test_delta_t_policy.py tests/unit/test_delta_t_data_integrity.py -q
python scripts/validate_delta_t_hybrid.py
```

No browser. No native rebuild. No EOP refresh.

## Impact

- `ΔT(2100)` ≈ **+1.7 s** vs today (~0.8 km of Earth rotation at the
  equator). `ΔT(2030)` curvature change is milliarcseconds.
- C1 drop: ~0.015 s/year derivative mismatch at the knot; ~15 ms of ΔT
  after one year.
- Every default `delta_t()` / `ut_to_tt()` call **outside EOP coverage**
  after `Y0` uses the new mean. Inside EOP coverage the daily DUT1 path
  is unchanged. `DeltaTPolicy(model="physical")` follows the new mean
  everywhere.

## Key decisions (locked)

1. Single deterministic curve, default clock, not a new policy name.
2. Sourced tidal 43.7 and GIA −14.61; net 29.09 s/cy².
3. No climate term.
4. No extra linear slope (`m = 0`).
5. C0 yes, C1 no.
6. Uncertainty structure kept; coefficient scales updated; OU untouched.
7. Quarantine and source-era identity untouched.
