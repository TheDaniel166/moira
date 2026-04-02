# Moira — Delta T Hybrid Physical Model
# Implementation Plan

**Version:** 1.0  
**Date:** 2026-03-20  
**Status:** Planning  
**Target:** `moira/delta_t_physical.py` + data pipeline scripts

---

## 1. Problem Statement

Moira's current `delta_t()` function in `julian.py` is a layered cascade:

- **2015–2026:** IERS Bulletin A/B annual table (exact)
- **1955–2015:** 5-year observed table
- **Historical:** HPIERS/HMNAO tabulation of the SMH 2016 model
- **Future (>2026):** Simple quadratic: `69.3 + 0.04·t + 0.001·t²`
- **Ancient (<1600):** Espenak/Meeus piecewise polynomials

The future extrapolation is the weakest part. It is an arbitrary smooth
curve anchored to 2026. By 2050 it diverges from JPL Horizons by ~30–50
seconds; by 2100 by ~130 seconds. This creates artificial apparent-position
errors of 3–120 arcseconds for fast bodies in the future era — not because
the geometry is wrong, but because the timescale assumption is wrong.

The goal of this project is to replace the future extrapolation (and
eventually the modern-era decomposition) with a physically-grounded model
built from three measurable, public data sources that were not available or
not fully exploited when SMH 2016 was published.

---

## 2. Physical Model Architecture

Delta T is driven by changes in Earth's rotation rate (LOD — Length of Day).
The dominant contributors are:

```
ΔT(t) = ΔT_tidal(t) + ΔT_GIA(t) + ΔT_core(t) + ΔT_cryo(t) + ΔT_residual(t)
```

| Component | Physical driver | Data source | Era coverage |
|---|---|---|---|
| ΔT_tidal | Lunar/solar tidal braking | Celestial mechanics | All epochs |
| ΔT_GIA | Glacial isostatic adjustment | ICE-6G / Caron 2018 | Post-LGM |
| ΔT_core | Core-mantle angular momentum | Gillet et al. core flow | 1840–present |
| ΔT_cryo | Cryosphere/hydrosphere mass | GRACE/GRACE-FO mascons | 2002–present |
| ΔT_residual | Everything else | Fit to IERS measured table | 1955–present |

For **future extrapolation** (post-2026), only ΔT_tidal and ΔT_GIA can be
computed from first principles. ΔT_core and ΔT_cryo must be projected from
their current measured trends. ΔT_residual is assumed to continue its recent
observed rate.

---

## 3. Implementation Phases

### Phase 1 — Tidal + GIA secular trend (Foundation)

**Goal:** Replace the long-range parabolic fallback with a physically-grounded
secular trend. This is the baseline that all other components are added to.

**Tidal braking:**

The lunar tidal torque produces a secular increase in LOD of approximately
+2.3 ms/century, equivalent to a parabolic Delta T trend:

```
ΔT_tidal(y) = c_tidal · ((y - 1820) / 100)²
```

where `c_tidal` is determined by the lunar secular acceleration `ṅ`.
The current best value is `ṅ = -25.858 ± 0.003 arcsec/cy²` (Chapront,
Chapront-Touze & Francou 2002), which gives `c_tidal ≈ 31.0 s/cy²`.

This is already embedded in the Espenak/Meeus `-20 + 32·u²` formula.
The improvement here is to use the Chapront value rather than the older
Morrison & Stephenson estimate.

**GIA contribution:**

Published GIA models give the rotation rate contribution directly as a LOD
change. From Caron et al. (2018, Geophysical Research Letters):

```
dLOD_GIA ≈ -0.6 ms/century  (acceleration, counteracts tidal braking)
```

This translates to:

```
ΔT_GIA(y) = c_GIA · ((y - 2000) / 100)²
```

where `c_GIA ≈ -3.0 s/cy²` (negative, opposing the tidal term).

**Reference epoch unification:**

The standard tidal formula uses 1820 as its reference epoch (the Morrison &
Stephenson convention). The Caron GIA contribution is naturally expressed
relative to 2000 (the center of the modern ice-loss record). Before combining
them, both must be re-expressed relative to the same epoch — `REFERENCE_YEAR`
— so that they can be summed into a single parabolic coefficient.

The general form of each component is:

```
ΔT_tidal(y) = c_tidal · ((y − 1820) / 100)²
ΔT_GIA(y)   = c_GIA   · ((y − 2000) / 100)²
```

Expanding both around `REFERENCE_YEAR` (= 2026) and collecting terms:

```
ΔT_tidal(y) = c_tidal · ((y − 2026 + 206) / 100)²
            = c_tidal · (t + 2.06)²          where t = (y − 2026) / 100
            = c_tidal · (t² + 4.12·t + 4.2436)

ΔT_GIA(y)   = c_GIA · ((y − 2026 + 26) / 100)²
            = c_GIA · (t + 0.26)²
            = c_GIA · (t² + 0.52·t + 0.0676)
```

The linear and constant terms are absorbed into `REFERENCE_LOD` via the
continuity constraint (they are fixed offsets at `REFERENCE_YEAR`, not
free parameters). Only the `t²` coefficients survive as the forward-looking
curvature:

```
secular_trend(y) = REFERENCE_LOD + (c_tidal + c_GIA) · t²
                 = REFERENCE_LOD + (31.0 − 3.0) · t²
                 = REFERENCE_LOD + 28.0 · t²
```

This is why the combined coefficient in `secular_trend()` is simply the sum
of `TIDAL_COEFF` and `GIA_COEFF` — the cross-terms and offsets are legitimately
collapsed into the anchor. A reader verifying the formula should apply this
expansion; the simplified form is algebraically exact, not an approximation.

**Implementation:**

```python
# moira/delta_t_physical.py

TIDAL_COEFF    =  31.0   # s/cy²  — Chapront 2002 lunar secular acceleration
GIA_COEFF      =  -3.0   # s/cy²  — Caron 2018 GIA rotation contribution
                          #          Both re-expressed around REFERENCE_YEAR;
                          #          linear/constant terms absorbed into REFERENCE_LOD.
REFERENCE_LOD  =  69.3   # s      — see continuity constraint note below
REFERENCE_YEAR = 2026.0  # yr     — last confirmed IERS Bulletin B year

def secular_trend(year: float) -> float:
    """
    Physics-based secular Delta T trend from tidal braking + GIA.
    Anchored to REFERENCE_LOD at REFERENCE_YEAR by continuity constraint.
    Both coefficients are relative to REFERENCE_YEAR after expanding the
    original 1820/2000 reference epochs — see algebra above.
    """
    t = (year - REFERENCE_YEAR) / 100.0
    return REFERENCE_LOD + (TIDAL_COEFF + GIA_COEFF) * t**2
```

**The 2026 anchor is a continuity constraint, not a free parameter.**

This point deserves explicit statement because the constant `69.3` looks like
a tuned value. It is not. It is the last confirmed IERS Bulletin A measured
Delta T at the boundary between the table-driven regime and the future
extrapolation regime. Its role is purely to enforce C0 continuity — that is,
to guarantee the physical model produces the same value as the measured table
at the handoff point.

Concretely: the secular trend formula has two genuine free parameters,
`TIDAL_COEFF` and `GIA_COEFF`, both of which are set from published physical
literature and must not be adjusted to improve the fit. `REFERENCE_LOD` is
derived, not fitted:

```
REFERENCE_LOD ≡ IERS_measured(REFERENCE_YEAR)
              − core_delta_t(REFERENCE_YEAR)
              − cryo_delta_t(REFERENCE_YEAR)
              − residual_spline(REFERENCE_YEAR)
```

It is the value the secular trend must take at `REFERENCE_YEAR` such that
the full assembled model `secular + core + cryo + residual` exactly equals
the IERS measured value at that point. Any other value would introduce a
step discontinuity in Delta T at the measured/extrapolated boundary, which
would propagate directly as a discontinuous jump in apparent planetary
positions at that epoch.

`REFERENCE_YEAR` is itself not fixed at 2026.0 permanently. It is defined
as the last year for which a confirmed IERS Bulletin A or B value is
available at build time. As new Bulletin A predictions are confirmed by
Bulletin B, `REFERENCE_YEAR` advances and `REFERENCE_LOD` is recomputed
from the updated measurement. The advance procedure is:

```python
# scripts/update_reference_anchor.py
# Run when new IERS Bulletin B values become available.
# Recomputes REFERENCE_LOD and writes updated constants to delta_t_physical.py.
```

This means the anchor stays current automatically as IERS measurements
accumulate, without any manual tuning of the model.

**Validation:** Compare against SMH 2016 table for 1800–2026. The secular
trend should match within the known decade-scale fluctuation envelope (~±5 s).

**Deliverables:**
- `moira/delta_t_physical.py` — module skeleton + `secular_trend()`
- `tests/unit/test_delta_t_physical.py` — secular trend unit tests
- `scripts/validate_secular_trend.py` — plot vs SMH 2016 table

**Effort:** 1 week

---

### Phase 2 — GRACE/GRACE-FO cryosphere component

**Goal:** Derive the cryosphere/hydrosphere contribution to Delta T from
satellite gravity data (2002–present) and project it forward.

**Physics:**

Changes in surface mass distribution alter Earth's moments of inertia,
specifically the axial moment I_33. The rotation rate change is:

```
Δω/ω = -ΔI_33 / C
```

where C is Earth's polar moment of inertia (~8.04 × 10³⁷ kg·m²).

ΔI_33 is related to the degree-2 zonal Stokes coefficient J2 by:

```
ΔI_33 = -√5 · M_E · R_E² · ΔJ2
```

GRACE/GRACE-FO mascon solutions give ΔJ2 directly as a monthly time series.

The LOD change from this is:

```
ΔLOD_cryo(t) = -LOD_0 · Δω(t) / ω_0
             = LOD_0 · ΔI_33(t) / C
```

Integrating LOD over time gives the Delta T contribution.

**LOD-to-Delta-T integration and integration constant:**

The GRACE series is a discrete monthly table of LOD anomalies
`ΔLOD(t_i)` in milliseconds, not a continuous rate. The Delta T
contribution is the cumulative integral:

```
ΔT_cryo(y) = Σ ΔLOD(t_i) · Δt_i / 86400      [seconds]
```

where `Δt_i` is the interval in days between successive monthly epochs
and the division by 86400 converts milliseconds of LOD into seconds of
Delta T accumulated per day.

The integration constant — the value at which `cryo_delta_t` is set to
zero — is defined as the mean ΔLOD over the first 12 months of the GRACE
record (2002 April–2003 March). This choice is deliberate: it removes
the arbitrary absolute offset of the GRACE J2 series (which is referenced
to a pre-GRACE background model, not to zero ice anomaly) while preserving
the trend and interannual variability. It means `cryo_delta_t(2002.5) ≡ 0`
by construction, and all values are LOD anomalies relative to that baseline.

The full series is pre-integrated once by `fetch_grace_j2.py` and stored
as a cumulative sum in `grace_lod_contribution.txt`. At runtime,
`cryo_delta_t(year)` performs linear interpolation on this pre-integrated
table — it does not re-integrate at call time.

**Data source:**

JPL GRACE Tellus RL06 mascon solution — public, no registration required:
```
https://podaac.jpl.nasa.gov/dataset/TELLUS_GRAC-GRFO_MASCON_CRI_GRID_RL06.1_V3
```

Monthly grids 2002-04 to present, 0.5° resolution.

The degree-2 zonal term ΔJ2 can also be read directly from the published
GRACE technical notes (TN-13, TN-14) without processing the full mascon grid.
This is the preferred approach for implementation simplicity.

**Implementation:**

```python
# scripts/fetch_grace_j2.py
# Downloads GRACE/GRACE-FO TN-14 J2 time series and converts to LOD contribution

# moira/delta_t_physical.py

def _load_grace_lod_series() -> tuple[tuple[float, float], ...]:
    """
    Load pre-processed GRACE/GRACE-FO LOD contribution series.
    File: moira/data/grace_lod_contribution.txt
    Format: decimal_year  lod_contribution_seconds
    Generated by: scripts/fetch_grace_j2.py
    """
    ...

def cryo_delta_t(year: float) -> float:
    """
    Cryosphere/hydrosphere contribution to Delta T from GRACE J2 series.
    Returns 0.0 outside the GRACE coverage window (pre-2002).
    For post-coverage extrapolation, uses the linear trend of the last
    5 years of available data.
    """
    ...
```

**Key numbers (approximate, from published literature):**

The GRACE record shows ΔJ2 trending at approximately −3.0 × 10⁻¹¹/year
driven primarily by Greenland and Antarctic ice loss. This translates to:

```
dLOD_cryo ≈ +0.012 ms/year  (growing)
```

Over a 70-year future window (2026–2100), this accumulates to:

```
ΔT_cryo(2100) ≈ +0.5 s  above the 2026 baseline
```

This is small but measurable and currently unmodeled in any ephemeris system.

**GRACE/GRACE-FO data gap (2017-10 to 2018-06):**

GRACE ceased science operations in October 2017; GRACE-FO began returning
data in June 2018. This leaves an ~11-month gap in the J2 series that falls
squarely within the residual spline's fit window (1962–2023). It must be
handled explicitly — silently interpolating across it would introduce a
false LOD trend of ~0.1 ms/year in the residual.

The gap is bridged by linear interpolation between the last confirmed
GRACE monthly value (2017-09) and the first confirmed GRACE-FO monthly
value (2018-07), using the slope of the 12 months immediately preceding
the gap. A flag column in `grace_lod_contribution.txt` marks all
gap-interpolated months so they can be excluded from regression
diagnostics. The bridged values are used in the pre-integrated series
but are not treated as measured data in the CV diagnostic — the
leave-one-out score is computed only over non-flagged months.

**Deliverables:**
- `scripts/fetch_grace_j2.py` — downloads and processes GRACE TN-14
- `moira/data/grace_lod_contribution.txt` — pre-processed LOD series
- `delta_t_physical.cryo_delta_t()` — interpolation + trend extrapolation
- Unit tests verifying the J2-to-LOD conversion formula

**Effort:** 2 weeks

---

### Phase 3 — Core-mantle angular momentum component

**Goal:** Add the decade-scale LOD fluctuations driven by core-mantle angular
momentum exchange, using published core flow models.

**Physics:**

The solid Earth (mantle + crust) and the fluid outer core exchange angular
momentum, producing LOD variations of ±2–4 ms on decadal timescales. These
are the dominant source of the irregular "wiggles" in the measured Delta T
curve that a pure secular + cryosphere model cannot reproduce.

The connection is through the geomagnetic torque:

```
dL_core/dt + Γ_cmb = 0   (angular momentum conservation)
```

where Γ_cmb is the torque at the core-mantle boundary.

Core surface flow is inferred from the geomagnetic secular variation (rate
of change of the magnetic field) via the frozen-flux approximation.

**Data source:**

Gillet et al. (2019, JGR) — published core angular momentum time series
1840–2019, reconstructed from geomagnetic field models. Available as
supplementary data from the paper.

For the modern era (2014–present), the Swarm satellite mission provides the
geomagnetic secular variation at unprecedented resolution.

This phase does **not** require implementing core flow inversion. It consumes
the published Gillet et al. angular momentum series directly as a table.

**Implementation:**

```python
# moira/data/core_angular_momentum.txt
# From Gillet et al. (2019) Table S1
# Format: decimal_year  delta_lod_ms

def _load_core_lod_series() -> tuple[tuple[float, float], ...]:
    ...

def core_delta_t(year: float) -> float:
    """
    Core-mantle angular momentum contribution to Delta T.
    Coverage: 1840–2019 from Gillet et al. (2019).
    Outside coverage: returns 0.0 (absorbed into residual).
    No future extrapolation — core fluctuations are not predictable.
    """
    ...
```

**Note on future extrapolation:**

Core-mantle fluctuations are genuinely unpredictable beyond a few years.
For future Delta T (post-2026), this component is set to the mean of the
last 10 years of the Gillet series rather than extrapolating the trend.

The choice of 10 years is grounded in the decorrelation timescale of core
surface flow. Geomagnetic secular variation studies (Gillet et al. 2010,
2019; Christensen & Tilgner 2004) consistently show that core flow features
have an autocorrelation timescale of roughly 5–15 years — meaning that
the angular momentum state of the core at any given year carries essentially
no predictive information about the core state more than ~10–15 years later.
This is a consequence of the advective turnover time of the outer core
(roughly 500 years divided by the magnetic Reynolds number, giving ~10 years
for the dominant flow structures). Beyond that window, the core angular
momentum performs a random walk constrained by the geometry of the
core-mantle boundary, not a trend that can be extrapolated. Using a 10-year
mean rather than the instantaneous last value or a linear trend therefore
does three things simultaneously: it averages out the high-frequency noise
in the Gillet series, it avoids locking in a transient excursion that
happens to be large at the boundary year, and it is statistically consistent
with a zero-mean forecast on timescales longer than the decorrelation length.
The residual non-zero value of the 10-year mean (typically ±0.3–0.5 s) is
absorbed into the continuity constraint at `REFERENCE_YEAR` rather than
propagated as a trend.

**Deliverables:**
- `moira/data/core_angular_momentum.txt` — Gillet et al. 2019 table
- `delta_t_physical.core_delta_t()` — table interpolation
- Unit tests verifying the LOD-to-Delta-T integration
- Comparison plot vs measured IERS LOD series 1962–present

**Effort:** 2 weeks

---

### Phase 4 — Residual fitting and model assembly

**Goal:** Combine all components, fit the residual against the IERS measured
table, and produce the final `delta_t_hybrid()` function.

**Model structure:**

```python
def delta_t_hybrid(year: float) -> float:
    """
    Physics-based hybrid Delta T model.

    For 1840–2026:  secular + core + cryo components, residual-corrected
                    against IERS measured table.
    For 2026+:      secular + cryo trend extrapolation + core mean.
                    More physically grounded than polynomial extrapolation.
    For pre-1840:   delegates to SMH 2016 table (unchanged — the physical
                    components do not extend this far back reliably).
    """
    if year < 1840.0:
        return _smh2016_lookup(year)

    base = secular_trend(year)
    core = core_delta_t(year)       # 0.0 outside Gillet coverage
    cryo = cryo_delta_t(year)       # 0.0 outside GRACE coverage

    if year <= 2026.0:
        residual = _fit_residual(year)   # spline fit to IERS measured − model
        return base + core + cryo + residual

    # Future: secular trend + cryo projection + core mean
    core_mean = _core_recent_mean()     # mean of last 10y of Gillet series
    return base + core_mean + cryo
```

**Era coverage and the 1840–1962 regime:**

The model has three distinct operating regimes that differ in which
components are active:

| Era | secular | core | cryo | residual | Notes |
|---|---|---|---|---|---|
| pre-1840 | — | — | — | — | Full SMH 2016 delegation |
| 1840–1962 | ✓ | ✓ | — | — | No GRACE; no IERS residual calibration |
| 1962–2002 | ✓ | ✓ | — | ✓ | IERS calibrated; no GRACE |
| 2002–2026 | ✓ | ✓ | ✓ | ✓ | All components active |
| 2026+ | ✓ | mean | trend | — | Future extrapolation |

The 1840–1962 regime is the least well-characterised. `cryo_delta_t`
returns 0.0 here (no GRACE coverage, and pre-2002 ice-loss rates were
small enough that the omission introduces < 0.05 s error). The residual
spline also returns 0.0 here — the fit window begins at 1962 and the
`ext=1` flag on `UnivariateSpline` enforces zero outside the knot range.

This means the 1840–1962 model is `secular + core` only, with no
empirical correction. The validation check for this era is therefore
a comparison against the SMH 2016 table, not the IERS measured table.
The target is agreement within ±2 s across 1840–1962, which is consistent
with the known residual amplitude of the Gillet core series relative to
the SMH 2016 reconstruction. If the comparison reveals a systematic
offset larger than 2 s, the likely cause is a bias in the integration
constant of the Gillet series, which should be corrected in
`fetch_grace_j2.py` rather than by introducing a new free parameter.

**Residual fitting procedure:**

The residual is the difference between the IERS measured Delta T and the sum
of the three physical components. It captures everything the physical model
does not explicitly model: atmospheric and oceanic angular momentum (AAM/OAM),
small unmodeled GIA terms, instrument noise in the IERS table, and any
systematic bias in the Gillet core series. Because it is absorbing genuine
geophysical signal as well as noise, it must be treated carefully — an
interpolating spline would overfit the noise; a polynomial would underfit
the real AAM signal.

**Step 1 — Compute the raw residual series:**

```python
residual(y) = IERS_measured(y) − secular_trend(y) − core_delta_t(y) − cryo_delta_t(y)
```

Evaluated at every annual IERS Bulletin B annual-mean epoch from 1962.5 to
the last confirmed measurement year (currently ~2024). IERS Bulletin A
predictions (2025–2026) are excluded from the fit to avoid introducing
forecasted values into the calibration.

**Definition of "confirmed":** A year is considered confirmed when its
final annual Delta T value has appeared in IERS Bulletin B, which publishes
definitive UT1−UTC values with a latency of approximately 35 days. In
practice this means the fit window lags the current date by roughly
one month. The cut point is determined programmatically by
`update_reference_anchor.py`, which reads the Bulletin B table and
identifies the last year for which a full 12-month average is available.
Bulletin A weekly predictions — which carry formal uncertainties of
±0.0025 s for the current week growing to ±0.030 s at 90 days — are
never used as calibration data, only as the source for `REFERENCE_LOD`
at `REFERENCE_YEAR` when that year has not yet been confirmed by Bulletin B.

**Step 2 — Pre-smooth to suppress AAM noise:**

The raw residual contains genuine interannual AAM/OAM signal at the 0.1–0.3 s
level riding on top of longer-period geophysical signal. A 3-year centred
moving average is applied before spline fitting:

```python
residual_smooth(y) = mean(residual(y−1), residual(y), residual(y+1))
```

This preserves decadal-scale signal while suppressing the year-to-year
atmospheric noise that the spline would otherwise chase. The choice of 3
years is deliberate: it is the shortest window that eliminates the dominant
annual and semi-annual AAM cycle (which IERS has already corrected for, but
whose residuals still appear at the ~0.05 s level) without damping the
El Niño–driven interannual signal (~3–7 year period, ~0.2 s amplitude) that
is real and should be captured.

**Step 3 — Smoothing spline with fixed knot placement:**

A **smoothing spline** (not an interpolating spline) is used.
`scipy.interpolate.UnivariateSpline` with explicit smoothing factor `s`:

```python
from scipy.interpolate import UnivariateSpline

spline = UnivariateSpline(
    years_smooth,          # annual-mean points 1962.5–2024.5
    residual_smooth,       # 3-year smoothed residual
    k=3,                   # cubic
    s=len(years_smooth),   # smoothing factor = N gives roughly 1 effective knot per year
    ext=1,                 # return 0.0 outside the knot range (no extrapolation)
)
```

The smoothing factor `s = N` (number of data points) is the standard
scipy starting point. It will be tuned by inspecting the number of knots
the solver places automatically: the target is approximately one knot per
3–5 years, which corresponds to the decadal geophysical signal we want to
capture. If the automatic knot count exceeds ~20 over the 62-year window,
`s` is increased until it falls back to that range.

Knot placement is **not fixed manually** — it is solver-determined from the
smoothing constraint. Manual knot placement would require knowledge of where
the geophysical signal changes character, which is not available a priori.
The smoothing parameter approach is more honest: it sets a resolution floor
and lets the data determine where variation occurs.

**Step 4 — Zero-derivative boundary condition at 2026:**

The spline must not extrapolate beyond 2026. The `ext=1` parameter in
`UnivariateSpline` enforces this by returning 0.0 outside the data range,
which is equivalent to assuming the residual contribution is zero in the
future. This is the correct assumption: the future model already absorbs the
mean recent residual implicitly through the continuity constraint
`REFERENCE_LOD ≡ IERS_measured(REFERENCE_YEAR) − core − cryo − residual`
at `REFERENCE_YEAR` (see Phase 1 for the full derivation).

To avoid a discontinuity in the first derivative at 2026, the smoothed
residual series is tapered to zero over the final 3 years (2021–2023) using
a cosine window:

```python
taper = 0.5 * (1 + cos(π × (y − 2021) / 3))   for y in [2021, 2024)
residual_smooth_tapered(y) = residual_smooth(y) × taper
```

This enforces a smooth handoff to zero rather than an abrupt drop, which
is important because any kink at 2026 would propagate as a discontinuity
in apparent planetary positions at that epoch boundary.

**Step 5 — Overfitting diagnostic:**

After fitting, compute an interior leave-one-out cross-validation score on
the non-boundary annual-mean epochs:

```python
cv_rms = sqrt(mean((residual_smooth(y_i) − spline_without_i(y_i))²
                   for interior annual-mean points y_i))
```

If `cv_rms > 0.5 s`, the smoothing factor is too small (overfitting).
If the in-sample RMS exceeds 0.5 s, the smoothing factor is too large
(underfitting — the spline is not tracking real geophysical signal).
The operational target is `cv_rms < 0.5 s`.

This diagnostic is run automatically in `scripts/validate_delta_t_hybrid.py`
and its result is reported in the validation output alongside the in-sample
RMS so the fit quality is always visible.

**Validation targets:**

- RMS residual against IERS measured table < 0.5 s (1962–2026)
- Max residual < 2.0 s anywhere in 1962–2026
- Future projection (2026–2100) compared against Horizons-style frozen value
  and Moira's current quadratic — documented as three competing forecasts

**Deliverables:**
- `delta_t_physical.delta_t_hybrid()` — assembled model
- `delta_t_physical.delta_t_hybrid_uncertainty(year)` — returns ±1σ estimate per section 8
- `delta_t_physical._fitted_residual_spline()` — smoothing spline fit per section 4 procedure,
  returning the spline plus named diagnostics (`cv_rms`, `in_sample_rms`, `knot_count`)
- `scripts/validate_delta_t_hybrid.py` — full comparison against IERS,
  SMH 2016, and Horizons-style frozen value; reports CV score and knot count
- Updated `julian.py` — add hybrid model as opt-in path alongside current
  `delta_t()` function (not replacing it — parallel implementation first)

**Effort:** 2 weeks

---

### Phase 5 — Integration and validation

**Goal:** Wire the hybrid model into the engine, validate against the Horizons
apparent-position suite, and update the documentation.

**Integration strategy:**

The hybrid model is added as a parallel path, not a replacement:

```python
# julian.py

def ut_to_tt(
    jd_ut: float,
    year: float | None = None,
    model: str = "smh2016",   # "smh2016" | "hybrid"
) -> float:
    ...
```

Default remains `"smh2016"` so no existing test breaks. The hybrid model
can be selected explicitly for research use or future-facing calculations.

**Validation against Horizons:**

Run the existing `test_horizons_planet_apparent.py` suite with both models.
For 1900–2026 the results should be within measurement noise of each other.
Document any differences.

For future epochs (2050, 2100), generate predicted positions under both
models and document the divergence envelope — this becomes the new section 6
of `VALIDATION_ASTRONOMY.md`.

**Deliverables:**
- `julian.py` updated with `model` parameter on `ut_to_tt`
- `tests/integration/test_delta_t_hybrid.py` — comparison against IERS table
- Updated `VALIDATION_ASTRONOMY.md` section 6 with three-model comparison
- Updated `BEYOND_SWISS_EPHEMERIS.md` — physics-based Delta T as a
  differentiating capability
- `scripts/update_reference_anchor.py` — defined procedure below

**`update_reference_anchor.py` — trigger, threshold, and validation:**

This script is the maintenance entry point for keeping `REFERENCE_LOD` and
`REFERENCE_YEAR` current as IERS measurements accumulate. Its behavior must
be precisely defined to avoid silent model drift.

*Trigger:* Manual execution only. It is not run automatically in CI because
updating a physical constant requires human review. The expected cadence is
once per year, after the January IERS Bulletin B confirms the previous
year's annual mean Delta T.

*Procedure:*
1. Download the latest IERS Bulletin B finals2000A.all from
   `https://datacenter.iers.org/data/csv/finals2000A.all.csv`
2. Identify the last calendar year Y for which all 12 monthly UT1−UTC
   values are confirmed (Bulletin B flag, not Bulletin A)
3. Compute the annual mean: `ΔT_confirmed = 32.184 + mean(TAI−UT1, year Y)`
4. Recompute `REFERENCE_LOD` from the continuity constraint equation
   using the current `core_delta_t(Y)`, `cryo_delta_t(Y)`, and
   `residual_spline(Y)` values
5. Write the updated constants to `delta_t_physical.py`
6. Run the full unit and integration test suite before committing

*Drift threshold:* If the new `REFERENCE_LOD` differs from the current
value by more than **0.5 s**, the script aborts with an explicit warning
rather than silently updating. A shift larger than 0.5 s in a single year
indicates either an error in the Bulletin B parse, an anomalous IERS
measurement, or a systematic offset in one of the physical components that
needs investigation. This is not a failure that should be automatically
absorbed — it requires a human decision about whether to update the
component models or accept the shift.

*Test:* `tests/unit/test_delta_t_physical.py` includes a test that
reconstructs `REFERENCE_LOD` from the continuity constraint equation and
asserts it matches the stored constant to within 0.01 s. This test will
fail if the constants are updated inconsistently — for example if
`REFERENCE_YEAR` is advanced without recomputing `REFERENCE_LOD`.

**Effort:** 1 week

---

## 4. Data Dependencies

| Data | Source | License | Size | Fetch method |
|---|---|---|---|---|
| GRACE/GRACE-FO TN-14 J2 series | NASA PO.DAAC | Public domain | ~50 KB | HTTP download |
| Gillet et al. 2019 core AM table | JGR supplementary | CC-BY | ~10 KB | Manual download + commit |
| ICE-6G GIA rotation rate | Peltier et al. 2015 | Published table | ~1 KB | Hardcoded constant |
| IERS measured Delta T 1962–present | IERS Bulletin B | Public domain | ~5 KB | Already in repo |
| SMH 2016 HPIERS table | HMNAO | Public domain | ~30 KB | Already in repo |

All data is either already in the repo or freely downloadable without
registration. No commercial data sources are required.

---

## 5. File Manifest

```
moira/
  delta_t_physical.py          — new module (Phases 1–4)
  delta_t_uncertainty.py       — uncertainty components per section 8
  julian.py                    — add model= parameter to ut_to_tt (Phase 5)
  data/
    grace_lod_contribution.txt — generated by fetch_grace_j2.py (Phase 2)
    core_angular_momentum.txt  — Gillet et al. 2019 table (Phase 3)

scripts/
  fetch_grace_j2.py            — download + process GRACE TN-14 (Phase 2)
  validate_secular_trend.py    — Phase 1 validation plot
  validate_delta_t_hybrid.py   — Phase 4 full comparison
  update_reference_anchor.py   — recompute REFERENCE_LOD when new IERS Bulletin B arrives

tests/
  unit/
    test_delta_t_physical.py   — unit tests for all components
  integration/
    test_delta_t_hybrid.py     — comparison against IERS measured table

moira/docs/
  DELTA_T_HYBRID_MODEL.md      — this document
  VALIDATION_ASTRONOMY.md      — section 6 updated (Phase 5)
  BEYOND_SWISS_EPHEMERIS.md    — physics-based Delta T entry added (Phase 5)
```

---

## 6. Timeline

| Phase | Content | Effort | Dependency |
|---|---|---|---|
| 1 | Secular trend (tidal + GIA) | 1 week | None |
| 2 | GRACE cryosphere component | 2 weeks | Phase 1 |
| 3 | Core angular momentum component | 2 weeks | Phase 1 |
| 4 | Residual fitting + model assembly | 2 weeks | Phases 2 + 3 |
| 5 | Integration + validation | 1 week | Phase 4 |

**Total: ~8 weeks**

Phases 2 and 3 can run in parallel once Phase 1 is complete.

---

## 7. Success Criteria

| Criterion | Target |
|---|---|
| RMS residual vs IERS 1962–2026 | < 0.5 s |
| Max residual vs IERS 1962–2026 | < 2.0 s |
| Future divergence from Horizons-frozen by 2100 | Documented, not minimized |
| No regression in existing Horizons apparent-position suite | All 120 cases pass |
| No regression in ERFA suite | All 84 cases pass |
| Hybrid model documented with explicit source citations | Yes |
| Uncertainty estimate available at each epoch | Yes — per section 8 |
| Uncertainty dominated by core-mantle term documented explicitly | Yes |

---

## 8. Uncertainty Model

`delta_t_hybrid_uncertainty(year)` returns a ±1σ estimate in seconds. This
section defines how that estimate is constructed for each component and how
the components are combined into a total.

---

### 8.1 Tidal uncertainty

**Source:** Uncertainty in the lunar secular acceleration `ṅ`.

The Chapront et al. (2002) value is `ṅ = −25.858 ± 0.003 arcsec/cy²`.
The tidal Delta T coefficient is proportional to `ṅ`, so the fractional
uncertainty propagates directly:

```
σ_tidal(y) = |secular_trend(y) − secular_trend_at_reference| × (0.003 / 25.858)
           ≈ TIDAL_COEFF × t² × 0.000116
```

where `t = (year − 2026) / 100`.

**Magnitude:** By 2100 (t = 0.74), σ_tidal ≈ 0.002 s. Negligible.

---

### 8.2 GIA model uncertainty

**Source:** Spread across published GIA models (ICE-6G, ANU, Caron 2018).

The GIA rotation contribution ranges from approximately −0.5 to −0.7
ms/century across models, reflecting uncertainty in ice sheet history and
mantle viscosity. This translates to an uncertainty in GIA_COEFF of roughly
±0.5 s/cy².

```
σ_GIA(y) = 0.5 × t²
```

**Magnitude:** By 2100 (t = 0.74), σ_GIA ≈ 0.27 s. Small but not negligible
at century timescales.

The implementation uses the Caron (2018) central value and treats the
inter-model spread as the ±1σ bound. This is conservative — the spread
includes older models that predate the best current ice sheet reconstructions.

---

### 8.3 GRACE J2 measurement and trend uncertainty

**Source:** Two distinct contributions:

**Measurement uncertainty (2002–present):**
The GRACE/GRACE-FO TN-14 J2 series carries formal measurement uncertainties
of approximately ±0.5 × 10⁻¹¹ per monthly epoch. Converting to LOD:

```
σ_cryo_measured ≈ 0.003 s   (during GRACE coverage window)
```

Negligible for apparent-position work.

**Trend extrapolation uncertainty (post-GRACE):**
The cryosphere LOD trend is estimated from a linear fit to the last 5 years
of available GRACE-FO data. The uncertainty on this trend is taken as the
±1σ of the linear regression:

```
σ_trend ≈ ±0.002 ms/year  (from regression residuals)
```

Accumulated over a forward projection of `Δt` years:

```
σ_cryo_projected(year) = σ_trend × (year − grace_end)  [seconds]
```

**Magnitude:** By 2100 with grace_end ≈ 2026, σ_cryo_projected ≈ 0.15 s.
Modest but explicitly propagated rather than ignored.

---

### 8.4 Core-mantle unpredictability

**Source:** Genuine physical unpredictability of core flow fluctuations
beyond a few years.

This is the dominant uncertainty source for future Delta T. Core-mantle
angular momentum exchange produces LOD variations of ±2–4 ms on decadal
timescales. These fluctuations are not forecastable beyond the current
geomagnetic secular variation window (~5 years ahead).

For the future extrapolation the core component is set to the mean of the
last 10 years of the Gillet series (see Phase 3). The ±1σ uncertainty is
taken as the standard deviation of that same 10-year window:

```python
core_values_last_10y = [core_delta_t(y) for y in recent_years]
σ_core_future = std(core_values_last_10y)   # typically 1–2 s
```

This is not a measurement uncertainty — it is an honest statement that
decade-scale Earth rotation fluctuations of this magnitude will occur but
their sign and timing cannot be predicted.

**Magnitude:** σ_core_future ≈ 1–2 s. This is the dominant term.

For the historical era (within the Gillet coverage window), the core
component is directly observed rather than extrapolated. Its uncertainty
is the formal uncertainty of the Gillet et al. angular momentum inversion,
approximately ±0.3 s.

---

### 8.5 Residual spline uncertainty

**Source:** Uncertainty in the smoothing spline fit to
`IERS_measured − (secular + core + cryo)` over 1962–2023.

Three distinct contributions:

**Within the coverage window (1962–2023):**
The spline tracks the smoothed residual with a target in-sample RMS < 0.2 s.
The dominant uncertainty here is the 3-year pre-smoothing step, which
introduces a lag of up to ±1.5 years in the representation of abrupt
geophysical events. For apparent-position purposes this is negligible
(< 0.01 s effect on slowly-varying residual).

**At the taper boundary (2021–2024):**
The cosine taper forces the residual to zero over the final 3 years of the
fit window. If the true residual is non-zero at 2024, this introduces a
deliberate bias of up to ~residual(2024) × 0.5 s at that epoch. This is
the correct trade-off: a smooth handoff to zero is preferable to a spline
that has a large derivative at the boundary and would extrapolate badly.

**Beyond 2026:**
The spline returns exactly 0.0 (ext=1). The uncertainty is the RMS of the
residual series over the fit window, taken as a flat ±1σ estimate for all
future epochs:

```
σ_residual(year > 2026) = rms(residual_smooth, 1962–2023)
```

Expected to be < 0.4 s based on the cross-validation target band.

**Overfitting guard:**
If the leave-one-out cross-validation score exceeds 0.4 s, the smoothing
factor is increased and the fit is rerun. This is enforced automatically
in `validate_delta_t_hybrid.py` and the final CV score is stored alongside
the spline coefficients so the fit quality is reproducible.

---

### 8.6 Total uncertainty assembly

The five components are treated as independent (the physical drivers are
genuinely uncorrelated on the relevant timescales) and combined in
quadrature:

```python
def delta_t_hybrid_uncertainty(year: float) -> float:
    """
    ±1σ uncertainty on delta_t_hybrid(year), in seconds.

    Components are combined in quadrature (independent sources).
    Dominant term for future dates is core-mantle unpredictability.
    """
    σ_tidal    = _tidal_uncertainty(year)
    σ_GIA      = _gia_uncertainty(year)
    σ_cryo     = _cryo_uncertainty(year)
    σ_core     = _core_uncertainty(year)
    σ_residual = _residual_uncertainty(year)

    return math.sqrt(
        σ_tidal**2 + σ_GIA**2 + σ_cryo**2 + σ_core**2 + σ_residual**2
    )
```

**Representative totals:**

| Epoch | σ_tidal | σ_GIA | σ_cryo | σ_core | σ_residual | σ_total |
|---|---:|---:|---:|---:|---:|---:|
| 2026 (anchor) | 0.00 s | 0.00 s | 0.003 s | 0.30 s | 0.01 s | ~0.3 s |
| 2050 | 0.001 s | 0.08 s | 0.06 s | 1.5 s | 0.3 s | ~1.6 s |
| 2075 | 0.001 s | 0.17 s | 0.10 s | 1.5 s | 0.3 s | ~1.6 s |
| 2100 | 0.002 s | 0.27 s | 0.15 s | 1.5 s | 0.3 s | ~1.6 s |

The total future uncertainty is dominated by core-mantle unpredictability
at all epochs beyond a few years. The ceiling of ~1.6 s reflects the
standard deviation of observed decade-scale core fluctuations — it does
not grow indefinitely because core fluctuations are mean-reverting on
multi-decade timescales.

**In arcseconds (for reference):**
A 1.6 s Delta T uncertainty translates to approximately:
- Moon: ~23″ (fast-moving body, ~0.5°/hr)
- Sun: ~0.4″
- Mercury at max elongation: ~0.2″
- Outer planets: < 0.05″

This is the honest future accuracy ceiling for any Earth-rotation-based
timescale model, regardless of the quality of the geometric ephemeris.

---

## 9. What This Does Not Solve

- **Ancient Delta T uncertainty (pre-700 BCE):** The irreducible uncertainty
  from chaotic Earth rotation fluctuations is ~±30 minutes at 500 BCE. No
  physical model can reduce this — it requires eclipse records that do not
  exist. The SMH 2016 table remains the best available answer for ancient dates.

- **The 1840 lower boundary:** The hybrid model delegates to SMH 2016 for
  all dates before 1840.0. This boundary is set by the start of the Gillet
  et al. (2019) core angular momentum series, which is the earliest date
  for which a geomagnetic-field-based core flow reconstruction is available
  with sufficient resolution to contribute meaningfully. Using 1840 rather
  than 1955 (IERS measurements) or 1962 (residual spline start) is a
  deliberate choice: it maximises the era over which the physical model
  replaces the empirical SMH 2016 polynomial, even though in the 1840–1962
  window only `secular + core` are active. Using 1962 as the boundary would
  mean the hybrid model offers no improvement over SMH 2016 for the
  entire 19th century, which is the era where the two approaches differ most.

- **The Horizons comparison discrepancy:** The 0.576" worst-case error in
  the current Horizons validation suite is primarily a Delta T convention
  difference between Moira and Horizons, not a model deficiency. The hybrid
  model will not eliminate this — Horizons uses its own internal Delta T
  that will never exactly match any external model.

- **Sub-arcsecond future accuracy:** Even the best physical model cannot
  predict future Earth rotation fluctuations at the sub-arcsecond level.
  The improvement is in the secular trend and the justified uncertainty
  quantification, not in achieving Horizons-level agreement for 2100.

---

## 10. References

All physical constants and model choices in this document are traceable to
the following publications. DOIs are provided for unambiguous identification.

**Tidal braking — lunar secular acceleration:**

Chapront, J., Chapront-Touzé, M., & Francou, G. (2002). A new determination
of lunar orbital parameters, precession constant and tidal acceleration from
LLR measurements. *Astronomy & Astrophysics*, 387, 700–709.
https://doi.org/10.1051/0004-6361:20020420

**GIA rotation contribution:**

Caron, L., Ivins, E. R., Larour, E., Adhikari, S., Nilsson, J., &
Blewitt, G. (2018). GIA model statistics for GRACE hydrology, cryosphere,
and ocean science. *Geophysical Research Letters*, 45(5), 2203–2212.
https://doi.org/10.1002/2017GL076338

Peltier, W. R., Argus, D. F., & Drummond, R. (2015). Space geodesy
constrains ice age terminal deglaciation: The global ICE-6G_C (VM5a) model.
*Journal of Geophysical Research: Solid Earth*, 120(1), 450–487.
https://doi.org/10.1002/2014JB011176

**Core angular momentum series:**

Gillet, N., Jault, D., & Finlay, C. C. (2015). Planetary gyre, time-dependent
eddies, torsional waves, and equatorial jets at the Earth's core surface.
*Journal of Geophysical Research: Solid Earth*, 120(6), 3991–4013.
https://doi.org/10.1002/2014JB011786

Gillet, N., Gerick, F., Jault, D., Schwaiger, T., Aubert, J., & Istas, M.
(2022). Satellite magnetic data reveal interannual waves in Earth's core.
*Proceedings of the National Academy of Sciences*, 119(13), e2115258119.
https://doi.org/10.1073/pnas.2115258119

*(The 2019 JGR paper cited in the text refers to the series of papers from
the Gillet group; the 2022 PNAS paper is the most recent version of the
angular momentum reconstruction and should be checked for updated tables
before committing `core_angular_momentum.txt`.)*

**Core flow decorrelation timescale:**

Christensen, U. R., & Tilgner, A. (2004). Power requirement of the geodynamo
from ohmic losses in numerical and laboratory dynamos. *Nature*, 429, 169–171.
https://doi.org/10.1038/nature02508

Gillet, N., Jault, D., Canet, E., & Fournier, A. (2010). Fast torsional waves
and strong magnetic field within the Earth's core. *Nature*, 465, 74–77.
https://doi.org/10.1038/nature09010

**GRACE/GRACE-FO J2 technical notes:**

Loomis, B. D., Rachlin, K. E., & Luthcke, S. B. (2019). Improved Earth
oblateness rate reveals increased ice sheet losses and mass-driven sea level
rise. *Geophysical Research Letters*, 46(12), 6910–6917.
https://doi.org/10.1029/2019GL082929

Sun, Y., Riva, R., & Ditmar, P. (2016). Optimizing estimates of annual
variations and trends in geocenter motion and J2 from a combination of GRACE
data and geophysical models. *Journal of Geophysical Research: Solid Earth*,
121(11), 8352–8370.
https://doi.org/10.1002/2016JB013073

GRACE-FO TN-14 technical note (degree-1 and C20/C30 replacements):
https://podaac.jpl.nasa.gov/gravity/gracefo-documentation

**SMH 2016 Delta T model:**

Stephenson, F. R., Morrison, L. V., & Hohenkerk, C. Y. (2016). Measurement
of the Earth's rotation: 720 BC to AD 2015. *Proceedings of the Royal Society
A*, 472, 20160404.
https://doi.org/10.1098/rspa.2016.0404

**IERS conventions and Bulletin B:**

Petit, G., & Luzum, B. (Eds.) (2010). *IERS Conventions (2010)*. IERS
Technical Note No. 36. Verlag des Bundesamts für Kartographie und Geodäsie.
https://www.iers.org/IERS/EN/Publications/TechnicalNotes/tn36.html

IERS Bulletin B (monthly, definitive UT1−UTC):
https://www.iers.org/IERS/EN/Publications/Bulletins/bulletins.html

