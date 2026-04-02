# Timelords Backend Standard

**Subsystem:** `moira/timelords.py`
**Computational Domains:** Firdaria, Zodiacal Releasing
**Constitutional Phase:** 11 — Architecture Freeze and Validation Codex
**Status:** Constitutional

---

## Part I — Architecture Standard

### §1. Computational Definitions

#### §1.1 Firdaria

Firdaria is a Hellenistic time-lord technique assigning rulership of life-periods to
the seven classical planets and the lunar nodes in a fixed Chaldean-order sequence.
The complete cycle spans 75 years.

The authoritative engine is `firdaria(natal_jd, is_day_chart)`. It accepts a Julian
Day number and a sect indicator and returns a list of `FirdarPeriod` records covering
the full 75-year cycle from birth. Each record preserves the planet, level, major
planet, start and end Julian Day, duration in years, and the sequence kind that
generated it.

**Sequence kinds (`FirdarSequenceKind`):**

| Value | Meaning |
|---|---|
| `DIURNAL` | Day chart: Sun-led sequence |
| `NOCTURNAL_STANDARD` | Night chart: Moon-led, traditional ordering |
| `NOCTURNAL_BONATTI` | Night chart: Moon-led, Bonatti variant ordering |

The `sequence_kind` field is set only on major-period (`level=1`) records. Sub-period
records do not repeat it; they inherit structural context through their `major_planet`
field.

The nocturnal variant (standard vs. Bonatti) is a doctrinal choice expressed at call
time. The default is `NOCTURNAL_STANDARD`. Both variants share the same computational
structure; only the planet ordering changes.

#### §1.2 Zodiacal Releasing

Zodiacal Releasing is a Hellenistic predictive technique that releases from a natal
Lot (Spirit or Fortune) through the twelve signs of the zodiac. Periods are assigned
by sign in sequence, with duration determined by the sign's `MINOR_YEARS` value.
The technique recurses through four levels of releasing simultaneously.

The authoritative engine is `zodiacal_releasing(lot_longitude, natal_jd)`. It accepts
a Lot's ecliptic longitude and a Julian Day number and returns a list of
`ReleasingPeriod` records. Each record preserves the releasing sign, its ruler, the
level of releasing, the lot name, duration in years, the Loosing of the Bond flag,
the angularity from Fortune, and the year-basis.

**MINOR_YEARS:** The canonical sign-to-duration mapping is an immutable constant in
the module. It assigns years-per-sign based on planetary minor years under the
Hellenistic system. This mapping is the foundational arithmetic of the technique and
is not configurable at call time.

**Loosing of the Bond:** When the Level-1 and Level-2 releasing signs are the same or
are in a relationship defined by the technique's doctrine, a Loosing of the Bond
condition fires. The `is_loosing_of_bond` field on `ReleasingPeriod` preserves this
designation; it is not recomputed from the sign names after the fact.

**Angularity from Fortune:** Each sign's relationship to the natal Lot of Fortune
determines its angularity class. Angular signs (1, 4, 7, 10 from Fortune) carry the
`ANGULAR` classification; the following signs carry `SUCCEDENT`; the remaining carry
`CADENT`. This classification is preserved as an integer (1-based distance) and a
typed `ZRAngularityClass` on each period.

| `ZRAngularityClass` Value | Meaning |
|---|---|
| `ANGULAR` | 1st, 4th, 7th, or 10th sign from Fortune |
| `SUCCEDENT` | 2nd, 5th, 8th, or 11th sign from Fortune |
| `CADENT` | 3rd, 6th, 9th, or 12th sign from Fortune |

**Levels:** Four levels of releasing are computed simultaneously. Level 1 is the
outermost (slowest), Level 4 is the innermost (fastest). All four are returned in a
single flat list discriminated by the `level` field.

---

### §2. Layer Structure

The timelords subsystem is organized into ten layers, each building on the prior
according to the constitutional dependency graph.

| Layer | Phase | Firdaria | Zodiacal Releasing |
|---|---|---|---|
| 0 | Core | `firdaria()` | `zodiacal_releasing()` |
| 1 | Truth Preservation | `FirdarPeriod` | `ReleasingPeriod` |
| 2 | Classification | `FirdarSequenceKind` | `ZRAngularityClass` |
| 3 | Inspectability | `is_active_at()`, duration properties | `is_active_at()`, duration properties |
| 4 | Policy | `sequence_kind` parameter | `lot_name`, `use_loosing_of_bond` |
| 5 | Relational Formalization | `FirdarMajorGroup`, `group_firdaria()` | `ZRPeriodGroup`, `group_releasing()` |
| 6 | Relational Hardening | subset properties, chronological guard | containment guard, `is_leaf`, `all_periods_flat()` |
| 7 | Integrated Local Condition | `FirdarConditionProfile`, `firdar_condition_profile()` | `ZRConditionProfile`, `zr_condition_profile()` |
| 8 | Aggregate Intelligence | `FirdarSequenceProfile`, `firdar_sequence_profile()` | `ZRSequenceProfile`, `zr_sequence_profile()` |
| 9 | Network Intelligence | `FirdarActivePair`, `firdar_active_pair()` | `ZRLevelPair`, `zr_level_pair()` |
| 10 | Hardening | `validate_firdaria_output()` | `validate_releasing_output()` |

---

### §3. Delegated Assumptions

The timelords subsystem does not compute the following. Callers are responsible for
supplying correct values.

**For Firdaria:**
- `natal_jd`: a valid Julian Day number representing the moment of birth
- `is_day_chart`: the sect determination (diurnal or nocturnal), computed externally
  from the chart's sun/ascendant relationship
- nocturnal variant selection: the caller's choice of `NOCTURNAL_STANDARD` vs.
  `NOCTURNAL_BONATTI` is not validated against any external authority

**For Zodiacal Releasing:**
- `lot_longitude`: the ecliptic longitude of the Lot, computed externally via the
  Lot formula (typically `Asc + Fortune/Spirit − Sun/Moon`)
- `natal_jd`: a valid Julian Day number representing the moment of birth
- the Lot used (Spirit vs. Fortune vs. other) is identified only by the `lot_name`
  string passed at call time; the subsystem does not verify it

---

### §4. Doctrine Surface

The doctrinal choices made by the timelords subsystem are explicit and located.

**Firdaria doctrine:**

| Choice | Location | Default |
|---|---|---|
| Nocturnal ordering variant | `firdaria()` parameter `sequence_kind` | `NOCTURNAL_STANDARD` |
| Sub-period major identification | `FirdarPeriod.major_planet` field | always set |
| Node treatment | `_FIRDARIA_NODES` constant | `['North Node', 'South Node']` |
| Luminary classification | `_FIRDARIA_LUMINARIES` constant | `['Sun', 'Moon']` |

**Zodiacal Releasing doctrine:**

| Choice | Location | Default |
|---|---|---|
| Minor years mapping | `MINOR_YEARS` module constant | Hellenistic standard |
| Loosing of the Bond | `ReleasingPeriod.is_loosing_of_bond` field | computed at engine time |
| Angularity from Fortune | `ReleasingPeriod.angularity_from_fortune` field | computed at engine time |
| `use_loosing_of_bond` flag | `ReleasingPeriod.use_loosing_of_bond` field | always preserved |

---

### §5. Public Vessels

The following are the constitutional public vessels of the timelords subsystem.

**Enumerations:**
- `FirdarSequenceKind` — discriminates the Firdaria sequence variant
- `ZRAngularityClass` — discriminates the angularity of a releasing period from Fortune

**Truth-preservation vessels:**
- `FirdarPeriod` — a single Firdaria period at any level
- `ReleasingPeriod` — a single Zodiacal Releasing period at any level

**Relational vessels:**
- `FirdarMajorGroup` — a major Firdaria period with its associated sub-periods
- `ZRPeriodGroup` — a releasing period at any level with its nested sub-groups

**Condition vessels:**
- `FirdarConditionProfile` — integrated doctrinal summary for one `FirdarPeriod`
- `ZRConditionProfile` — integrated doctrinal summary for one `ReleasingPeriod`

**Aggregate vessels:**
- `FirdarSequenceProfile` — chart-wide summary of a full Firdaria sequence
- `ZRSequenceProfile` — sequence-wide summary of releasing periods at a given level

**Network vessels:**
- `FirdarActivePair` — the major/sub lord pair active at a point in time
- `ZRLevelPair` — structural edge between two adjacent releasing levels

**Computational functions:**
- `firdaria(natal_jd, is_day_chart, ...)` — core Firdaria engine
- `zodiacal_releasing(lot_longitude, natal_jd, ...)` — core Zodiacal Releasing engine
- `group_firdaria(periods)` — relational grouping for Firdaria
- `group_releasing(periods)` — relational grouping for Zodiacal Releasing
- `firdar_condition_profile(period)` — condition profile for a Firdaria period
- `zr_condition_profile(period)` — condition profile for a Releasing period
- `firdar_sequence_profile(periods)` — aggregate profile for a Firdaria sequence
- `zr_sequence_profile(periods, level)` — aggregate profile for a Releasing sequence
- `firdar_active_pair(periods, jd)` — network node active at a Julian Day
- `zr_level_pair(upper, lower)` — network edge between two releasing levels
- `validate_firdaria_output(periods)` — invariant guard for Firdaria output
- `validate_releasing_output(periods)` — invariant guard for Releasing output

---

## Part II — Terminology Standard

### §6. Required Terms

The following terms carry specific meanings within this subsystem and must not be
used loosely.

| Term | Normative Meaning |
|---|---|
| **major period** | A `FirdarPeriod` with `level=1`; one of the 9 time-lord allocations spanning the full 75-year cycle |
| **sub-period** | A `FirdarPeriod` with `level=2`; a subdivision of a major period |
| **sequence kind** | The `FirdarSequenceKind` value determining which planet leads the Firdaria sequence |
| **level** | An integer 1–4 in Zodiacal Releasing or 1–2 in Firdaria, identifying the recursive depth of a period |
| **Loosing of the Bond** | The specific Hellenistic condition where Level-1 and Level-2 releasing align according to doctrine; preserved as a boolean on `ReleasingPeriod` |
| **angularity from Fortune** | The 1-based sign distance of a releasing period's sign from the natal Lot of Fortune; typed as `ZRAngularityClass` |
| **lot** | The natal Lot (Spirit, Fortune, or other) from which releasing proceeds; identified by `lot_name` only |
| **MINOR_YEARS** | The immutable sign-to-duration mapping; the arithmetic basis of the releasing technique |
| **lord type** | The doctrinal classification of a Firdaria planet: `luminary`, `planet`, or `node`; not a concept in Zodiacal Releasing |
| **condition profile** | A flat doctrinal summary of a single period, integrating all layers from truth preservation through relational hardening |
| **sequence profile** | A chart-wide or sequence-wide aggregate derived from a full list of condition profiles |
| **active pair** | The simultaneous major/sub lord combination at a point in time; a network node in Firdaria |
| **level pair** | The structural edge between two adjacent releasing levels at a point in time |

---

### §7. Forbidden Conflations

The following pairs must not be equated.

**`FirdarPeriod` and `FirdarConditionProfile`**
A `FirdarPeriod` is the raw truth-preservation vessel. A `FirdarConditionProfile` is
a derived doctrinal summary. One is the source; the other is a projection.

**`level` and `depth`**
`level` is a 1-based integer field on the period vessel. It is not a synonym for
recursive depth, tree depth, or nesting order. Level 1 is the outermost; Level 4 is
the innermost in Releasing.

**`major_planet` and `planet`**
`FirdarPeriod.planet` is the time-lord for that period. `FirdarPeriod.major_planet`
is the planetary anchor of the major grouping to which a sub-period belongs. For
major periods, these are equal. For sub-periods, they differ.

**`is_loosing_of_bond` and `is_peak_period`**
`is_loosing_of_bond` is a doctrinal Hellenistic designation preserved from the
engine. `is_peak_period` on `ZRConditionProfile` is a derived convenience boolean
(always equal to `is_loosing_of_bond` for the period it summarizes). The former is
canonical; the latter is a profile convenience.

**`angularity_from_fortune` and `ZRAngularityClass`**
`angularity_from_fortune` is the raw 1-based integer distance. `ZRAngularityClass`
is the typed classification derived from that integer. Both are preserved; neither
replaces the other.

**`FirdarMajorGroup` and `FirdarSequenceProfile`**
A `FirdarMajorGroup` is a relational grouping of one major period with its subs. A
`FirdarSequenceProfile` is a chart-wide aggregate across all major periods. One is a
local relational structure; the other is a global summary.

**`sequence_kind` (Firdaria) and `lot_name` (Releasing)**
These are both doctrinal identifiers for their respective techniques but they govern
entirely different subsystems and must not be confused or referenced across domains.

---

## Part III — Invariant Register

### §8.1 Vessel Invariants

**`FirdarPeriod`:**
- `level` is either 1 or 2
- `planet` is a recognized classical planet or node name
- `start_jd < end_jd`
- `level=1` periods have `major_planet == planet`
- `level=2` periods have `major_planet` identifying a recognized level-1 planet

**`ReleasingPeriod`:**
- `level` is 1, 2, 3, or 4
- `start_jd < end_jd`
- `angularity_from_fortune`, if set, is an integer in the range [1, 12]
- `angularity_class`, if set, is a valid `ZRAngularityClass` value

**`FirdarMajorGroup`:**
- `subs` contains only `FirdarPeriod` records with `major_planet == self.period.planet`
- `subs` is in strict chronological order (enforced in `__post_init__`)
- no two adjacent subs overlap in Julian Day

**`ZRPeriodGroup`:**
- all sub-groups are temporally contained within `self.period` (±1e-6 tolerance)
- `level` equals `self.period.level`

**`FirdarConditionProfile`:**
- `lord_type` is one of `'luminary'`, `'planet'`, `'node'`
- `years > 0` and `days > 0`
- `is_node_period` is mutually exclusive with `lord_type == 'luminary'`

**`ZRConditionProfile`:**
- `years > 0` and `days > 0`
- `angularity_class` is `None` if and only if `angularity_from_fortune` is `None`

**`DashaActiveLine` (dasha domain — not in scope here):** see `DASHA_BACKEND_STANDARD.md`

---

### §8.2 Truth Invariants

- The `MINOR_YEARS` mapping is immutable. No function in this subsystem modifies or
  overrides it at runtime.
- `FirdarPeriod.sequence_kind` is `None` for all level-2 (sub) periods. It is set
  only on level-1 periods.
- `ReleasingPeriod.is_loosing_of_bond` is set by the engine at computation time. It
  is not a derived property and must not be recomputed from sign names.
- The sum of all level-1 Firdaria period durations in a complete sequence equals
  exactly 75 years (modulo floating-point accumulation).

---

### §8.3 Aggregate Invariants

**`FirdarSequenceProfile`:**
- `luminary_major_count + planet_major_count + node_major_count == major_count`
- `len(profiles) == major_count` (or greater if sub-profiles are included)
- `total_major_years > 0`

**`ZRSequenceProfile`:**
- `angular_count + succedent_count + cadent_count == peak_period_count`
- `period_count == len(profiles)`
- `total_years > 0`

---

### §8.4 Network Invariants

**`FirdarActivePair`:**
- `major_profile` is always present
- `sub_profile` is `None` if and only if no sub-period is active at the queried JD
- `is_same_lord` is meaningful only when `has_sub` is `True`

**`ZRLevelPair`:**
- `house_distance` is in the range [1, 12]
- `house_distance = (lower_sign_index − upper_sign_index) % 12 + 1`
- `signs_are_identical` is `True` if and only if `house_distance == 1` and the
  signs are the same (i.e., the lower level is in the same sign as the upper level)

---

## Part IV — Failure Doctrine

### §9.1 Invalid Inputs

**Firdaria:**
- Passing a non-finite `natal_jd` to `firdaria()` raises `ValueError`.
- Passing an unrecognized `sequence_kind` value raises `ValueError`.
- Passing an empty periods list to `group_firdaria()`, `firdar_condition_profile()`,
  or aggregate/network functions raises `ValueError`.

**Zodiacal Releasing:**
- Passing a `lot_longitude` outside [0, 360) may produce incorrect sign assignments.
  The subsystem does not clamp or validate this; the caller is responsible.
- Passing an empty periods list to aggregate or network functions raises `ValueError`.

**Common:**
- Passing a non-finite `jd` to `firdar_active_pair()` raises `ValueError`.

---

### §9.2 Search Exhaustion

- `firdar_active_pair()` returns `None` if no major period is active at the queried JD.
  This is not an error; it means the queried JD lies outside the 75-year sequence.
- `ZRPeriodGroup.active_sub_at(jd)` returns `None` if no sub-group contains the JD.

---

### §9.3 Invariant Failure

- `validate_firdaria_output()` raises `ValueError` with a descriptive message if:
  - any level-1 period is out of chronological order
  - any two adjacent level-1 periods overlap
  - any level-2 sub-period references a `major_planet` that has no corresponding
    level-1 period in the list
  - any level-2 sub-periods within a major group are out of chronological order
    or overlap
- `validate_releasing_output()` raises `ValueError` with a descriptive message if:
  - periods at any level are out of chronological order
  - any level-N+1 period is not temporally contained within its enclosing level-N
    period
- `FirdarMajorGroup.__post_init__` raises `ValueError` if subs are not in
  chronological order.
- `ZRPeriodGroup.__post_init__` raises `ValueError` if any sub-group falls outside
  the parent period's temporal bounds.

---

## Part V — Determinism Standard

### §10. Determinism Guarantees

- `firdaria()` is fully deterministic: given the same `natal_jd` and `is_day_chart`,
  the output list is identical in every call with no dependency on external state.
- `zodiacal_releasing()` is fully deterministic: given the same `lot_longitude` and
  `natal_jd`, the output list is identical in every call.
- Period lists returned by both engines are in strict chronological order by
  `start_jd` within each level. The flat list returned by `zodiacal_releasing()`
  is ordered by `(level, start_jd)`.
- `group_firdaria()` and `group_releasing()` are deterministic: they produce
  identical groupings for identical inputs.
- `firdar_active_pair()` is deterministic: given the same periods list and `jd`,
  the result is always the same.
- All condition, aggregate, and network functions are pure (no side effects, no
  hidden state).
- Floating-point accumulation across Firdaria sub-period boundaries may produce
  `end_jd` values that differ from the major's `end_jd` by up to a small epsilon.
  The containment tolerance in `ZRPeriodGroup` and `DashaActiveLine` is `1e-6` JD
  to accommodate this. This tolerance is the only permitted numeric approximation
  in the subsystem.

---

## Part VI — Validation Codex

### §11. Minimum Validation Commands

The following commands must pass without error on any constitutionally correct
installation of this subsystem:

```
python -m pytest tests/unit/test_timelords.py -v
```

All tests in `test_timelords.py` must pass. The test suite validates:
- `firdaria()` and `zodiacal_releasing()` correctness
- `FirdarMajorGroup` grouping and `group_firdaria()` fidelity
- `ZRPeriodGroup` nesting and `group_releasing()` fidelity
- Chronological ordering guards in `FirdarMajorGroup.__post_init__`
- Containment guards in `ZRPeriodGroup.__post_init__`
- Subset properties: `luminary_subs`, `node_subs`, `planet_subs`, `is_complete`
- `ZRPeriodGroup` properties: `is_leaf`, `angularity_class`, `all_periods_flat()`
- `FirdarConditionProfile` and `ZRConditionProfile` field fidelity
- Lord type classification: luminary / planet / node
- `FirdarSequenceProfile` and `ZRSequenceProfile` counts, totals, and invariant rejection
- `FirdarActivePair` boundary behavior, `None` return, non-finite JD rejection
- `ZRLevelPair` house distance, sign identity, peak pair detection
- `validate_firdaria_output()` correctness and rejection cases
- `validate_releasing_output()` correctness and rejection cases

---

### §12. Required Validation Themes

Any validation suite for this subsystem must demonstrate the following:

**Truth preservation:**
- A `FirdarPeriod` returned by `firdaria()` carries `planet`, `level`, `major_planet`,
  `start_jd`, `end_jd`, `years`, and `sequence_kind` without truncation or flattening.
- A `ReleasingPeriod` returned by `zodiacal_releasing()` carries `sign`, `ruler`,
  `level`, `lot_name`, `years`, `is_loosing_of_bond`, and `angularity_from_fortune`
  without truncation.

**Relational integrity:**
- All sub-periods in a `FirdarMajorGroup` have `major_planet` matching the group's
  major period's `planet`.
- All `ZRPeriodGroup` sub-groups are temporally contained within the parent.

**Classification correctness:**
- `FirdarSequenceKind` discriminates DIURNAL vs. NOCTURNAL variants correctly.
- `ZRAngularityClass` discriminates ANGULAR / SUCCEDENT / CADENT based on the
  1-based distance from Fortune.

**Aggregate integrity:**
- `luminary_major_count + planet_major_count + node_major_count == major_count`
  in any `FirdarSequenceProfile` constructed from a valid sequence.
- `angular_count + succedent_count + cadent_count == peak_period_count`
  in any `ZRSequenceProfile` constructed from a valid sequence.

**Network correctness:**
- `firdar_active_pair()` returns `None` for JDs outside the sequence.
- `firdar_active_pair()` raises `ValueError` for non-finite JDs.
- `ZRLevelPair.house_distance` is computed as `(lower − upper) % 12 + 1`.

**Hardening:**
- `validate_firdaria_output()` detects out-of-order level-1 periods.
- `validate_firdaria_output()` detects overlapping level-1 periods.
- `validate_firdaria_output()` detects sub-periods outside their major group.
- `validate_releasing_output()` detects level-N+1 periods outside level-N boundaries.
- `validate_releasing_output()` detects out-of-order periods at any level.

---

## Part VII — Future Boundary

### §13. Explicit Non-Goals

The following are explicitly outside the scope of this subsystem as constitutionalized.

**Not in scope:**

- **Chart calculation.** The subsystem does not compute natal positions, house cusps,
  ascendants, or Lot longitudes. These are delegated to the chart engine.

- **Sect determination.** Whether a chart is diurnal or nocturnal is computed
  externally and passed as `is_day_chart`. The subsystem does not verify this.

- **Lot formula.** The formula for computing the Lot of Fortune or Spirit is not
  defined here. Only the resulting longitude is consumed.

- **Predictive interpretation.** The subsystem produces structural timing data.
  It does not assess whether a period is favorable, challenging, or significant.
  Interpretation is a higher-level concern.

- **Tropical vs. sidereal zodiac.** Zodiacal Releasing is computed over the zodiac
  defined by the caller's longitude input. The subsystem does not enforce a zodiacal
  framework.

- **Multi-lot releasing.** This subsystem constitutionalizes releasing from a single
  Lot per call. Simultaneous releasing from Spirit and Fortune is an aggregation
  concern above this layer.

- **Primary Directions.** This subsystem covers Firdaria and Zodiacal Releasing only.
  Primary Directions are a separate technique and a separate subsystem.

- **Transit and progression overlay.** Correlating time-lord periods with transit or
  progression charts is a cross-subsystem concern and is not part of this standard.

- **Hellenistic bound lord or triplicity lord at period boundaries.** These are
  additional doctrinal overlays that could be computed from natal positions and period
  boundaries but are not part of the current Firdaria or Releasing subsystems.

Any future extension that crosses these boundaries requires a new constitutional phase or a
separate subsystem constitutionalization, not an in-place amendment to this standard.

