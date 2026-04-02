# Variable Stars Backend Standard

**Subsystem:** `moira/variable_stars.py`
**Computational Domain:** Astrologically significant variable stars — brightness phase,
light curve modeling, astrological quality, catalog access
**Constitutional Phase:** 11 — Architecture Freeze and Validation Codex
**Status:** Constitutional

---

## Part I — Architecture Standard

### §1. Computational Definitions

#### §1.1 The Variable Star Oracle

The Variable Star Oracle (`variable_stars.py`) is an astrological timing engine
specialized for variable stars. It owns:

- The catalog of astrologically significant variable stars (`_CATALOG`).
- Linear ephemeris phase computation: `phase = ((JD − epoch) / period) % 1`.
- Per-type light curve models (EA trapezoid, Cepheid sawtooth, sinusoidal Mira/SR,
  continuous EB, rapid-rise RR Lyrae).
- Astrological quality scoring (malefic intensity, benefic strength).
- Eclipse detection for eclipsing binary types.
- Extremum finders (next minimum, next maximum, ranges).
- Convenience wrappers for the most frequently used star (Algol).

The authoritative oracle for all variable star computation within Moira is this module.
No other module computes variable star phases or brightness estimates.

#### §1.2 Phase Convention

Phase is always in `[0.0, 1.0)`, computed by the linear ephemeris:

```
phase = ((JD − epoch_jd) / period_days) % 1.0
```

Phase zero is defined differently by variability type:

| Type | Phase 0 | `epoch_is_minimum` |
|---|---|---|
| EA, EB, EW | Primary minimum (faintest) | `True` |
| DCEP, RRAB | Maximum light (brightest) | `False` |
| M, SRc, SRb | Maximum light (brightest) | `False` |

This convention is invariant across the module. All functions respect it.

#### §1.3 Variability Types (`VarType`)

| Constant | GCVS Code | Description |
|---|---|---|
| `ECLIPSING_ALGOL` | EA | Algol-type: flat light curve, sharp primary eclipse |
| `ECLIPSING_BETA` | EB | Beta Lyrae: continuously varying contact binary |
| `ECLIPSING_W_UMA` | EW | W UMa: shallow rapid contact binary |
| `CEPHEID` | DCEP | Classical (δ) Cepheid: asymmetric pulsation |
| `RR_LYRAE` | RRAB | RR Lyrae fundamental mode: very fast rise |
| `MIRA` | M | Mira long-period variable |
| `SEMI_REG_SG` | SRc | Semi-regular supergiant |
| `SEMI_REG` | SRb | Semi-regular with multiple periods |

#### §1.4 Classical Quality

Each catalog star carries a `classical_quality` field with one of four values:

| Value | Meaning |
|---|---|
| `malefic` | Traditionally harmful or challenging; most intense at minimum |
| `benefic` | Traditionally favorable; most potent at maximum |
| `neutral` | No strong traditional astrological character |
| `mixed` | Competing traditional attributions (e.g. Beta Lyrae) |

This field is an editorial doctrinal designation, not a computed value.

#### §1.5 Eclipse Threshold Doctrine

The `eclipse_threshold` (default `0.05` mag) is the minimum brightness drop above
`mag_max` required for an eclipsing star to be classified as currently in eclipse.
It is the only free doctrinal parameter in this subsystem and is governed by
`VarStarPolicy`.

---

### §2. Layer Structure

| Layer | Phase | Content |
|---|---|---|
| 0 | Core | `phase_at()`, `magnitude_at()`, `_ea_magnitude()`, `next_minimum()`, `next_maximum()`, `minima_in_range()`, `maxima_in_range()`, `malefic_intensity()`, `benefic_strength()`, `is_in_eclipse()` |
| 1 | Truth Preservation | `VariableStar` frozen dataclass, `_CATALOG`, `_reg()`, `variable_star()`, `list_variable_stars()`, `variable_stars_by_type()` |
| 2 | Classification | `VarType` namespace |
| 3 | Inspectability | `VariableStar` properties: `amplitude`, `is_eclipsing`, `is_pulsating`, `is_long_period`, `is_irregular`, `is_malefic`, `is_benefic`, `type_class` |
| 4 | Policy | `VarStarPolicy`, `DEFAULT_VAR_STAR_POLICY` |
| 5/6 | Relational + Hardening | `StarPhaseState`, `star_phase_state()`, `__post_init__` guards |
| 7 | Condition | `StarConditionProfile`, `star_condition_profile()` |
| 8 | Aggregate | `CatalogProfile`, `catalog_profile()` |
| 9 | Network | `StarStatePair`, `star_state_pair()` |
| 10 | Hardening | `validate_variable_star_catalog()` |

---

### §3. Delegated Assumptions

The Variable Star Oracle does not compute the following. Callers are responsible.

- **Julian Day of query.** Callers supply `jd`. The module does not convert
  calendar dates to Julian Days.
- **Catalog completeness.** The 20 registered stars are the current editorial
  selection. The module does not claim to be an exhaustive variable star catalog.
- **Real-time ephemeris correction.** Mira and semi-regular variables have drifting
  periods. Predicted maxima/minima for these types are approximate (±days to ±weeks).
  The module does not fetch live AAVSO observations.
- **Ecliptic position.** `VariableStar` carries no positional data. Ecliptic
  longitude, conjunction with natal planets, and chart overlay are computed
  externally (via `fixed_stars.py` or `stars.py`).

---

### §4. Doctrine Surface

| Choice | Location | Default |
|---|---|---|
| Eclipse threshold | `VarStarPolicy.eclipse_threshold` | `0.05` mag |
| EA eclipse half-width flat-bottom fraction | `_ea_magnitude()` constant `0.3` | hardcoded |
| Cepheid fast-rise fraction | `magnitude_at()` constant `0.10` | hardcoded |
| RR Lyrae fast-rise fraction | `magnitude_at()` constant `0.05` | hardcoded |
| Phase zero convention by type | `epoch_is_minimum` field | per-star in catalog |

The only run-time-configurable doctrinal choice is `eclipse_threshold` via
`VarStarPolicy`. All light curve shape constants are frozen architecture.

---

### §5. Public Vessels

**Classification:**
- `VarType` — GCVS variability type constants

**Truth-preservation:**
- `VariableStar` — frozen catalog record for one variable star

**Policy:**
- `VarStarPolicy` — eclipse threshold doctrine
- `DEFAULT_VAR_STAR_POLICY` — default policy instance

**Relational:**
- `StarPhaseState` — computed state of one star at one JD

**Condition:**
- `StarConditionProfile` — integrated doctrinal summary for one star at one JD

**Aggregate:**
- `CatalogProfile` — chart-wide summary of all catalog stars at one JD

**Network:**
- `StarStatePair` — structural relationship between two star states at one JD

**Computational functions:**
- `phase_at(star, jd)`, `magnitude_at(star, jd)`
- `next_minimum(star, jd_start)`, `next_maximum(star, jd_start)`
- `minima_in_range(star, jd_start, jd_end)`, `maxima_in_range(star, jd_start, jd_end)`
- `malefic_intensity(star, jd)`, `benefic_strength(star, jd)`, `is_in_eclipse(star, jd)`
- `variable_star(name)`, `list_variable_stars()`, `variable_stars_by_type(var_type)`
- `algol_phase(jd)`, `algol_magnitude(jd)`, `algol_next_minimum(jd_start)`, `algol_is_eclipsed(jd)`
- `star_phase_state(star, jd, *, policy)`, `star_condition_profile(star, jd, *, policy)`
- `catalog_profile(jd, *, policy)`, `star_state_pair(star_a, star_b, jd, *, policy)`
- `validate_variable_star_catalog()`

---

## Part II — Terminology Standard

### §6. Required Terms

| Term | Normative Meaning |
|---|---|
| **phase** | A float in `[0.0, 1.0)` derived from the linear ephemeris. Phase 0 is primary minimum for eclipsing types; maximum light for pulsating and long-period types. |
| **epoch** | The reference Julian Day (`epoch_jd`) at which phase = 0 by definition. |
| **amplitude** | The brightness range `mag_min − mag_max` in magnitudes. Always positive for genuine variable stars. |
| **type class** | The high-level grouping: `'eclipsing'`, `'pulsating'`, or `'long_period'`. Derived from `var_type`. |
| **classical quality** | The editorial astrological designation: `'malefic'`, `'benefic'`, `'neutral'`, or `'mixed'`. |
| **malefic score** | A float in `[0.0, 1.0]` computed by `malefic_intensity()`: 1.0 at peak malefic state (faintest for malefic stars in eclipse), 0.0 for non-malefic stars. |
| **benefic score** | A float in `[0.0, 1.0]` computed by `benefic_strength()`: 1.0 at maximum brightness for benefic/neutral stars. |
| **eclipse threshold** | The minimum magnitude drop above `mag_max` required to classify a star as currently in eclipse. Governed by `VarStarPolicy.eclipse_threshold`. |
| **condition profile** | A flat doctrinal summary of a single star at a single JD, integrating all layers from truth preservation through relational hardening. |
| **catalog profile** | A chart-wide aggregate derived from all registered variable stars at a given JD. |

---

### §7. Forbidden Conflations

**`magnitude` and `amplitude`**
`magnitude` is the estimated brightness at a specific JD. `amplitude` is the
total brightness range of the star's variation. One is instantaneous; the other
is a catalog constant.

**`phase` and `classical_quality`**
`phase` is a computed arithmetic value in `[0, 1)`. `classical_quality` is an
editorial doctrinal designation. Phase does not determine quality; quality modulates
the interpretation of phase.

**`malefic_score` and `malefic_intensity()`**
`malefic_intensity()` is the function that computes the score. `malefic_score` is
the stored result on `StarPhaseState` and `StarConditionProfile`. They are the same
value; neither replaces the other in meaning.

**`is_in_eclipse` and `epoch_is_minimum`**
`is_in_eclipse` is a computed boolean (is the star currently in eclipse at this JD?).
`epoch_is_minimum` is a catalog field (was the reference epoch a primary minimum?).
They answer different questions.

**`VariableStar` and `StarConditionProfile`**
`VariableStar` is the immutable catalog record — it never changes. `StarConditionProfile`
is a derived per-moment summary. One is the source; the other is a projection.

**`type_class` and `var_type`**
`var_type` is the precise GCVS classification (`'EA'`, `'DCEP'`, etc.). `type_class`
is the coarser three-way grouping (`'eclipsing'`, `'pulsating'`, `'long_period'`).
Both are preserved; neither replaces the other.

---

## Part III — Invariant Register

### §8.1 Vessel Invariants

**`VariableStar`:**
- `mag_max < mag_min` (maximum is numerically smaller — it is brighter)
- `amplitude > 0` (all catalog stars are genuinely variable)
- `period_days > 0` (all catalog stars have a known dominant period)
- `epoch_jd > 0` (valid Julian Day)
- For `var_type == ECLIPSING_ALGOL`: `eclipse_width > 0`
- For non-eclipsing types: `eclipse_width == 0.0`
- `classical_quality` is one of `{'malefic', 'benefic', 'neutral', 'mixed'}`
- `var_type` is a recognized `VarType` constant
- `is_eclipsing`, `is_pulsating`, `is_long_period` are mutually exclusive; exactly one is True

**`StarPhaseState`:**
- `jd` is finite
- `phase` in `[0.0, 1.0)`
- `malefic_score` in `[0.0, 1.0]`
- `benefic_score` in `[0.0, 1.0]`

**`CatalogProfile`:**
- `star_count == len(profiles)`
- `eclipsing_count + pulsating_count + long_period_count == star_count`
- `malefic_count + benefic_count + neutral_count + mixed_count == star_count`

---

### §8.2 Truth Invariants

- The `_CATALOG` dict is populated at import time; no I/O occurs. Its contents
  are stable across the module's lifetime unless deliberately modified.
- `phase_at(star, star.epoch_jd)` is always `0.0` (or within floating-point
  tolerance of `0.0`) for any star with `period_days > 0`.
- `magnitude_at(star, jd)` always returns a value in the interval
  `[mag_max − ε, mag_min + ε]` for small ε (model approximation tolerance).
- `malefic_intensity()` always returns `0.0` for stars where
  `classical_quality not in ('malefic', 'mixed')`.

---

### §8.3 Aggregate Invariants

- `catalog_profile(jd).star_count` equals `len(list_variable_stars())`.
- The type count triple `(eclipsing, pulsating, long_period)` always sums to
  `star_count`.
- The quality count quadruple `(malefic, benefic, neutral, mixed)` always sums
  to `star_count`.

---

### §8.4 Network Invariants

- `StarStatePair.both_malefic` is True if and only if both
  `primary.is_malefic` and `secondary.is_malefic` are True.
- `StarStatePair.quality_conflict` is True if and only if exactly one of the two
  stars is malefic and the other is benefic.
- `StarStatePair.both_in_eclipse` is True if and only if both
  `primary.in_eclipse` and `secondary.in_eclipse` are True.

---

## Part IV — Failure Doctrine

### §9.1 Invalid Inputs

- Passing a non-finite `jd` to `star_phase_state()` raises `ValueError`.
- Passing an unrecognized star name to `variable_star()` raises `KeyError` with
  a message listing the suggestion to call `list_variable_stars()`.
- `catalog_profile()` and all condition/network functions propagate `ValueError`
  from `star_phase_state()` if `jd` is not finite.

---

### §9.2 Search Exhaustion

- `next_minimum()` and `next_maximum()` return `None` for stars with
  `period_days <= 0` (irregular variables). This is not an error.
- `minima_in_range()` and `maxima_in_range()` return an empty list for
  zero-period stars. This is not an error.
- `variable_star()` raises `KeyError` (not `None`) when a name is not found.
  There is no soft-not-found return.

---

### §9.3 Invariant Failure

- `StarPhaseState.__post_init__` raises `ValueError` if `jd` is not finite,
  or if `phase`, `malefic_score`, or `benefic_score` are out of range.
- `CatalogProfile.__post_init__` raises `ValueError` if any of the three
  count invariants are violated.
- `validate_variable_star_catalog()` raises `ValueError` on the first catalog
  entry that fails any structural invariant.

---

## Part V — Determinism Standard

### §10. Determinism Guarantees

- `phase_at()`, `magnitude_at()`, `malefic_intensity()`, `benefic_strength()`,
  `is_in_eclipse()`, `next_minimum()`, `next_maximum()` are all fully deterministic:
  given the same `star` and `jd`, the result is identical in every call.
- `star_phase_state()`, `star_condition_profile()`, `catalog_profile()`, and
  `star_state_pair()` are fully deterministic given the same inputs and policy.
- `list_variable_stars()` returns stars in a stable sorted order.
- `catalog_profile()` returns profiles in `list_variable_stars()` order.
- The light curve model constants (Cepheid rise fraction `0.10`, RR Lyrae rise
  fraction `0.05`, EA flat-bottom fraction `0.3`) are frozen architecture;
  they are not configurable at runtime.
- Floating-point rounding is the only source of non-exact equality between
  computed values and analytical expectations.

---

## Part VI — Validation Codex

### §11. Minimum Validation Commands

```
.venv/Scripts/python -m pytest tests/unit/test_variable_stars.py -v
```

All tests in `test_variable_stars.py` must pass. The suite validates:
- Catalog integrity (20 stars, correct fields, self-consistent values)
- Phase arithmetic invariants for all 20 stars
- Light curve qualitative correctness by type
- Extremum finders: next minimum/maximum, range queries
- Astrological quality scores bounded and correct at extremes
- Eclipse detection for EA stars at epoch; non-detection for pulsating types
- Algol convenience functions consistent with generic API
- Inspectability properties: amplitude, type class, mutual exclusivity
- Policy construction and frozenness
- `StarPhaseState` construction, guards (non-finite JD, out-of-range values)
- `StarConditionProfile` field fidelity for malefic and benefic stars
- `CatalogProfile` type/quality counts and invariant rejection
- `StarStatePair` structural properties across complementary and conflicting stars
- `validate_variable_star_catalog()`: valid catalog passes; bad entries detected

---

### §12. Required Validation Themes

Any validation suite for this subsystem must demonstrate:

**Truth preservation:**
- `VariableStar` fields are preserved without modification from catalog through
  `VariableStar`, `StarPhaseState`, `StarConditionProfile`, and `StarStatePair`.

**Phase arithmetic:**
- `phase_at(star, star.epoch_jd) ≈ 0.0` for all catalog stars.
- Phase is in `[0.0, 1.0)` for any JD.

**Light curve correctness:**
- EA stars are faintest at phase 0 and brightest between eclipses.
- Cepheid and Mira stars are brightest at phase 0.

**Classification correctness:**
- `is_eclipsing`, `is_pulsating`, `is_long_period` are mutually exclusive and cover all types.

**Aggregate integrity:**
- Type count triple sums to `star_count` in any `CatalogProfile`.
- Quality count quadruple sums to `star_count` in any `CatalogProfile`.

**Hardening:**
- `validate_variable_star_catalog()` detects inverted `mag_max`/`mag_min`.
- `validate_variable_star_catalog()` detects EA stars with zero `eclipse_width`.
- `StarPhaseState` rejects non-finite `jd`.
- `CatalogProfile` rejects mismatched `star_count`.

---

## Part VII — Future Boundary

### §13. Explicit Non-Goals

The following are explicitly outside the scope of this subsystem.

**Not in scope:**

- **Ecliptic position.** The Variable Star Oracle computes brightness phases, not
  positional data. Ecliptic longitude, right ascension, or conjunction with natal
  planets is a concern for `fixed_stars.py` and `stars.py`.

- **Real-time ephemeris updates.** Mira and semi-regular stars have drifting periods.
  The module uses fixed catalog epochs and periods. Fetching current AAVSO data is
  not a function of this subsystem.

- **Exhaustive GCVS catalog.** The 20 registered stars are an astrologically curated
  selection. Completeness relative to the full GCVS is not a goal.

- **Secondary eclipse timing.** `next_minimum()` returns primary-eclipse timing only.
  Secondary eclipse prediction (EA phase 0.5) is not a dedicated output.

- **Multi-period interference modeling.** Semi-regular variables (SRb type, e.g. W Cygni)
  have multiple interfering periods. The module uses the dominant period only.
  Accurate multi-period modeling requires time-frequency analysis beyond this engine.

- **Photometric calibration.** Magnitude estimates are model-based (sinusoidal, sawtooth,
  trapezoid). They are not calibrated against observed light curves and should not
  be used for photometric research.

- **Astrological interpretation.** The module produces scores and profiles. It does not
  assess whether a given variable star state is significant for a natal chart or
  transit moment. Interpretation is a higher-level concern.

Any future extension that crosses these boundaries requires a new constitutional phase or a
separate subsystem constitutionalization, not an in-place amendment to this standard.

