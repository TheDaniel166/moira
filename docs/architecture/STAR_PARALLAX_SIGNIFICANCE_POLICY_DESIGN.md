# Star Parallax Uncertainty Policy: Design and Execution Plan

Status: PROPOSED v2 (2026-11-03). Supersedes the v1 significance-gate proposal. No code or data
has been changed.
Finding: catalog-wide fixed-star attack, `tests/integration/test_stars_catalog_wide_attack.py`.
Governs: `moira/stars.py`, `moira/star_types.py`, `moira/data/star_registry.csv`,
`moira/data/star_provenance.json`, `moira_server/` star models, the ingestion script and the
standard (all PROTECTED zones; each step below is declared before it is made).
Standard to amend on acceptance: `wiki/02_standards/FIXED_STARS_BACKEND_STANDARD.md`.

## 0. End goal

Moira never states a star's distance, or a position that depends on it, with more confidence than
the catalog measurement supports, and every such number carries its basis. The work is designed
so that **Gaia DR4 is a data refresh only**: re-run the ingestion, freeze a new fixture, no
engine change.

Not in scope: changing the astrometric or apparent products' method, or any technique module.

## 1. The defect, its origin and its reach

The registry stores a parallax and no uncertainty. The engine treats every positive parallax as a
distance (`distance_ly = 3261.56/ϖ`) and applies one light-travel time of proper motion for it.

| Star | ϖ (mas) | σ (mas) | Implied distance | Implied M_V |
|---|---|---|---|---|
| β Phe | 0.12 | 14.62 | 27,000 ly | −11.3 |
| Polis (μ Sgr) | 0.09 | 0.28 | 36,000 ly | −11.4 |
| Garnet Star (μ Cep) | 0.119 | 0.264 | 27,000 ly | −10.5 |
| ο Cas | 0.512 | 0.734 | 6,400 ly | −7.0 |

β Phe's `geometric` product moves 2,393 arcsec (0.66°). The true displacement is not known from this repo's data: the only parallax in it is 0.12 ± 14.62 mas, which is consistent with zero and with any distance beyond about 70 ly (3σ). (An earlier draft said about 17 arcsec, from recollection of a literature distance of roughly 200 ly. That figure is not sourced here and is withdrawn.)

- **Age.** Not a 6.12.0 regression. `distance_ly`, `_distance_ly_from_parallax` and
  `star_light_time_split` are in v6.11.1 with the same rule and trace to the March 2026 catalog
  commits (`6fde2ae`, `291e164`). Phase 3 (`59e5a02`) added the named `geometric` product on top.
- **Cause.** The ingestion query (`_QUERY`) selects `plx_value` and never `plx_err`. SIMBAD's data
  is right (1,790 of 1,808 resolved rows equal SIMBAD's parallax); the registry kept half the
  measurement. The ERFA validation covered the apparent product; the geometric product had no
  external authority and no plausibility check.
- **Reach.** No module outside `stars.py` reads `distance_ly`. Exposure: `FixedStar.distance_ly`,
  `star_light_time_split`, the `geometric` product, and REST `product=geometric` (REST does not
  expose `distance_ly`). Technique modules use astrometric or apparent.
- **Stage 1 is not affected in practice.** Setting each problem parallax to 0 moves the
  astrometric position by at most 0.37 mas over 5,000 years (Garnet Star; Polis 0.008 mas):
  parallax enters stage 1 only through linear perspective terms.
- **The v1 gate was too weak.** The geometric product's own first-order uncertainty
  (μ · τ · σ/ϖ) exceeds 0.1 arcsec for 1,274 of 1,791 stars and 1 arcsec for 204. A ϖ/σ ≥ 5 gate
  protects 35 of them. Mira passes it at ϖ/σ = 8.9 and its shift is 71″ ± 8″.

## 2. Governing object

Two quantities derive from one measurement, and only one is fragile.

1. **Parallax shift** (apparent product). Linear in ϖ. The measured ϖ is an unbiased estimate of
   the shift at any signal-to-noise. It is used as measured, with its bound reported.
2. **Distance and light-travel time** (`distance_ly`, geometric product). Proportional to 1/ϖ.
   With fractional error f = σ/ϖ, E[1/ϖ] ≈ (1/ϖ)(1 + f²): the estimate is biased by f² while its
   own 1σ error is f. Beyond small f it is not a function of the measurement alone; it depends on
   a prior (Bailer-Jones 2015, PASP 127, 994; Astraatmadja and Bailer-Jones 2016, ApJ 832, 137).

The geometric position is therefore an **estimate with a stated uncertainty**, and the engine
publishes the uncertainty. It withholds the light-time correction only where the estimate is not
defined by the measurement.

## 3. Policy

For each star the registry carries an adopted parallax ϖ, its uncertainty σ, and its source.

- **Regime `linear`:** ϖ > 0 and σ/ϖ ≤ F_MAX. Distance d = 1/ϖ is published. The light time is
  τ = d/c. The vessel carries the first-order uncertainties
  σ_τ = τ·σ/ϖ and σ_θ = μ·σ_τ (position, arcsec).
- **Regime `unbounded`:** ϖ > 0 and σ/ϖ > F_MAX. The distance depends on a prior the engine does
  not own. `distance_ly` is NaN; geometric coincides with astrometric and the vessel says why.
- **Regime `none`:** no source value (ϖ ≤ 0 or missing). Same behaviour as `unbounded`.

**F_MAX = 0.2**, derived rather than conventional: the bias of 1/ϖ relative to its 1σ error is
f²/f = f, so at f = 0.2 the neglected second-order term is 20% of the stated uncertainty.
The constant lives in one place with this derivation; changing the tolerated fraction changes it.

This is a validity limit on a stated approximation, and it replaces the ϖ/σ ≥ 5 convention of v1
(same number, 5 = 1/0.2, but now a consequence of an error budget).

The apparent product keeps the measured ϖ. Its vessel reports the parallax-term bound
σ · sin(elongation) so a 14 mas error on β Phe is visible instead of implied.

## 4. Data: primary sources, combined per star

SIMBAD becomes a cross-check. Values come from the primary catalogs through the Gaia archive
(`https://gea.esac.esa.int/tap-server/tap/sync`, the service `fetch_hg` already uses) and
Hipparcos new reduction (van Leeuwen 2007, `public.hipparcos_newreduction`).

### 4.1 Dry-run results (2026-11-03, read-only, all 1,809 rows; scratchpad `dryrun_*.json`)

- **The registry's `gaia_dr3_id` column is the placeholder `0` in every row.** The Gaia identifier
  must be cross-matched. SIMBAD's identifier list gives it for 1,656 rows and a Hipparcos number
  for 1,709. The cross-match checks out: registry J2000 position against Gaia propagated back
  16 years has median offset 0.000″, worst 1.1″ (ρ Gem), and no row has two Gaia identifiers.
- **The catalog is mostly naked-eye stars.** Of 1,546 Gaia candidates, 1,405 are brighter than
  G = 6, where Gaia's published zero-point correction (Lindegren et al. 2021) is undefined.
  Only 132 are in the calibrated domain with RUWE ≤ 1.4.
- **For G < 6 the two catalogs disagree beyond their formal errors.** Over 1,384 Gaia/Hipparcos pairs
  the median |z| is 1.6 (a calibrated pair gives 0.67) and 22% exceed 3σ (expected 0.3%). Gaia
  minus Hipparcos has median −0.17 mas. A constant systematic floor does not repair this: even
  0.3 mas leaves about 10% beyond 3σ. The disagreement is heavy-tailed and star-specific.
  Examples: γ CMi (Gaia 3.13 ± 0.17, Hipparcos 10.25 ± 0.47), HD 10307 (68.0 vs 78.5, RUWE 2.9).
- **For G ≥ 6 they agree** (median |z| 0.84 for 77 stars, 0.63 for 12) and Gaia is far more
  precise (σ 0.02 mas against Hipparcos 0.74 and 1.74).
- **The registry's current parallaxes** (SIMBAD's adopted values, mostly Gaia) differ from the
  primary-catalog choice by more than 1 mas for 359 stars, more than 3 mas for 56, and more than
  10 mas for 3. This is a second defect: a parallax error of that size is also an error in the
  apparent product of up to the same number of milliarcseconds.
- **36 rows have a registry value but no Gaia or Hipparcos candidate** through these routes
  (Orkaria 68.3 mas, Bodu, several binary components).
- The zero-point package (`gaiadr3-zeropoint` 0.1.0) fails on Python scalars under NumPy 2 and
  works on arrays. The ingestion tool uses arrays and pins the version in the script header.

The v2 rule (smaller σ among candidates admitted by RUWE ≤ 1.4) is withdrawn. It selected
Hipparcos for 1,622 stars by discarding Gaia on a RUWE test that is not meaningful for bright
stars, and it did not use the information in a disagreement.

### 4.2 Adoption rule (v3)

Per star, candidates are formed and combined as below. Every candidate and the rule applied are
recorded so the choice is re-derivable.

1. **Gaia candidate** (when the cross-match exists, `astrometric_params_solved` is 31 or 95).
   - Zero-point defined (G ≥ 6 and inside the colour range): ϖ_G = ϖ_raw − Z, and
     σ_G = `parallax_error` × max(1, RUWE).
   - Zero-point undefined (G < 6): ϖ_G = ϖ_raw, no correction is claimed, and the candidate is
     marked `uncalibrated`.
2. **Hipparcos candidate:** ϖ_H = `plx`, σ_H = `e_plx`.
3. **Combination** (both present): z = |ϖ_G − ϖ_H| / √(σ_G² + σ_H²).
   - z ≤ 3: inverse-variance weighted mean, σ = (Σ 1/σ²)^(−1/2).
   - z > 3: the catalogs conflict beyond their stated errors, so those errors cannot weight them.
     The adopted value is the midpoint, (ϖ_G + ϖ_H)/2, with error |ϖ_G − ϖ_H|/2. That interval
     spans both measurements exactly and is correct whichever of the two is the wrong one. The
     row is marked `discordant` and listed. (An earlier draft kept the weighted mean and widened
     only the error; a unit test showed that interval covers only the nearer measurement.)
4. **One candidate:** it is adopted as is.
5. **Neither:** the SIMBAD value with its `plx_err` and bibcode is adopted, marked `simbad_fallback`.
   No value at all: `none`.
6. **Curated binary components** (Sirius, α Cen A and B) keep their orbit-solution parallax and
   its published error (Bond et al. 2017; Akeson et al. 2021). δ Indi and σ² UMa follow §3.3.

The discordant error in step 3 uses the star's own disagreement, so it needs no fitted constant
and cannot understate the uncertainty when the catalogs conflict. Such stars fall into the
`unbounded` regime when the widened σ/ϖ exceeds F_MAX, which is the right outcome.

### 4.3 Results from the frozen fixture (step 2, `tests/fixtures/star_parallax_primary_2026_11_03.json`)

Fetched 2026-11-03 for all 1,809 rows (SIMBAD CfA mirror, Gaia archive), adoption per §4.2.

| Source | Rows |
|---|---|
| Gaia and Hipparcos combined (agree) | 1,331 |
| combined, discordant (midpoint, half-gap error) | 151 |
| Hipparcos only | 236 |
| Gaia only, corrected | 51 |
| Gaia only, uncalibrated (G < 6) | 13 |
| SIMBAD fallback | 8 |
| no value | 19 |

| Regime (F_MAX = 0.2) | Stars |
|---|---|
| `linear` (distance published with uncertainty) | 1,736 |
| `unbounded` (distance withheld) | 51 |
| `none` | 19 |
| curated binary components | 3 |

- **M_V invariant holds.** Most luminous `linear` star: Atakoraka at M_V = −7.8 (Rigel −7.0,
  Deneb −6.9); none below −8. Today three stars fail at −10.
- **Position uncertainty of the geometric product:** median 0.24″; 1,254 above 0.1″, 227 above
  1″, none above 10″.
- **Change against today's registry** (the apparent product moves by at most this): more than
  0.3 mas for 654 stars, more than 1 mas for 195, more than 3 mas for 35, more than 10 mas for 1;
  maximum 13.2 mas.
- **Withheld distances:** 70 (51 `unbounded` plus 19 `none`).
- **Cross-match:** every Gaia identifier from SIMBAD places its star within 2″ of the registry
  position after proper-motion propagation; no row has two Gaia identifiers.
- **Corroboration against Bailer-Jones et al. 2021** (published 16–84% intervals, 1,503 `linear`
  stars with an estimate): where Gaia's zero-point is defined (G ≥ 6) our distance lies inside the
  interval for 98.6% of 141 stars. For G < 6 it is 39.6% of 1,362, with a median offset of
  about 0% but intervals only about ±1.2% wide, because they trust Gaia's formal errors, which the
  Gaia/Hipparcos comparison in §4.1 shows are optimistic for bright stars. The permanent test
  asserts the calibrated case only.

## 5. Registry and engine

Registry (additive columns, same pattern as `radial_velocity_status`): `parallax_error_mas`,
`parallax_source`. `parallax_mas` becomes the adopted value (after zero-point correction where
applied). `parallax_regime` is not stored: the engine derives it from ϖ, σ and F_MAX, so changing
F_MAX needs no data change.

`moira/stars.py`:
- `_SovereignStarRecord` gains `parallax_error_mas` and `parallax_source`.
- `_light_time_days` returns 0 unless the regime is `linear`; `distance_ly` is NaN otherwise.
- `FixedStarTruth` gains `parallax_error_mas`, `parallax_source`, `parallax_regime`,
  `light_time_uncertainty_years`, `position_uncertainty_arcsec`.
- `star_light_time_split` keeps its documented coincidence behaviour and now names the regime.
- The engine reads these columns only. It contains no reference to Gaia, so DR4 replaces data,
  not code.

REST (additive only): the star provenance response gains the same fields. No route, request model
or default changes. Release placement is the owner's call.

## 6. Behaviour change, disclosed

| Surface | Before | After |
|---|---|---|
| `distance_ly` | numeric for every positive parallax | NaN where σ/ϖ > 0.2: 52 stars, plus 18 with no value (§4.3) |
| `geometric` product | shifted by light time, no uncertainty | same for `linear`, now with σ; equals astrometric otherwise |
| adopted ϖ | SIMBAD's copy | primary catalog value, zero-point corrected for Gaia rows; shift bounded in §8 |
| `astrometric` | unchanged | unchanged except the ≤ 0.4 mas bounded drift from the changed ϖ |
| `apparent` | unchanged | changes by at most the parallax correction (disclosed, tested) |

Because the adopted parallax changes for Gaia rows (zero-point is about −0.02 to −0.04 mas), the
v1 requirement that apparent output be bit-identical is replaced by a **bound**: apparent shifts
by at most |Δϖ| and the ERFA agreement test still passes at 0.001 arcsec.

## 7. Execution order

Each step is its own commit to `main`, declared against the protected zones it touches.

1. **Dry run: done 2026-11-03** (§4.1). It withdrew the v2 rule and produced v3. Repeat it with the
   v3 rule to obtain the regime and source counts before any data changes.
2. **Ingestion tooling: done 2026-11-03.** `fetch-plx` and `derive-plx` (offline re-derivation after
   a rule change), the pure `adopt_parallax`, `gaia_zero_point`, the frozen fixture (which also
   freezes the Bailer-Jones 2021 distances), 27 unit and 16 fixture test cases. No registry change.
   `apply-plx` belongs to step 3.
3. **Data apply.** Registry columns, provenance blocks, `PROVENANCE.md`. A re-derivation test
   ties every row to the fixture.
4. **Engine.** Fields, regime logic, vessel, `star_light_time_split`.
5. **REST.** Additive provenance fields and tests.
6. **Standard and ledger.** Amend `FIXED_STARS_BACKEND_STANDARD.md` (adoption rule, F_MAX derivation,
   stated limits); record the defect and repair in the defect ledger.

## 8. Verification (each class of evidence named)

| Test | Evidence class |
|---|---|
| Every row re-derived from the frozen fixture (candidates, rule, zero-point) | regression parity |
| Adoption rule on synthetic candidate sets: tie, RUWE 1.4 boundary, params 31/95/other, Hipparcos only, none | invariants |
| Regime boundary at σ/ϖ = 0.1999, 0.2, 0.2001; ϖ = 0, < 0; σ = 0; σ missing | invariants |
| Linear-regime stars: geometric equals the pre-change implementation given the same adopted ϖ | regression parity |
| First-order σ_θ against a Monte Carlo over ϖ ~ N(ϖ, σ) at several σ/ϖ ≤ 0.2 | authority validation (numerical) |
| `linear` distances against Bailer-Jones 2021 intervals: fraction inside [r_lo, r_hi], and a listed set of disagreements | cross-engine corroboration |
| M_V = V − 5 log10(d/10) > −10 for every star with a distance claim (fails today for 3 stars) | invariants |
| Apparent: ERFA agreement at 0.001″ for all stars; drift from the old output ≤ the parallax change | authority validation, bound |
| Catalog-wide attack file keeps passing; the engine source contains no catalog-specific branch | invariants |
| **DR4 readiness:** a synthetic fixture with different catalog labels and errors loads and drives all regimes with no engine edit | invariants |
| REST provenance carries every new field and nothing else changes | regression parity |

## 9. Known limits (stated, not hidden)

- Gaia formal errors for bright stars are optimistic. The F_MAX margin is the allowance; no
  inflation factor is applied.
- The first-order σ_θ is valid inside the `linear` regime only, which is why the regime exists.
- Binary and variable-star photocentre effects are not modelled beyond the curated components.
- Out of scope, noted during the attack: 19 stale `ecl_lon_deg` entries (7–10 arcsec off their own
  RA/Dec, not used for positions), and the raw `SpkReader` raising bare `ValueError` where
  `KernelPool` raises `OutOfRangeError`.

## 10. Decisions for the owner

1. **Zero-point correction in the adopted parallax.** Recommended: apply it, store the raw value
   and Z in provenance, so there is one parallax per star and it is the best estimate. Alternative:
   store raw and apply Z only for the distance claim, keeping the apparent product unchanged.
2. **Adoption rule v3** (§4.2): combine, widen on disagreement, SIMBAD as fallback. Confirm before the
   v3 dry run.
3. **F_MAX = 0.2** (bias at 20% of the error). A stricter value withholds more distances.
4. **Release placement.** This document does not propose a version.
