# Dasha Backend Standard

**Subsystem:** `moira/dasha.py`
**Computational Domain:** Vimshottari Dasha
**Constitutional Phase:** 11 — Architecture Freeze and Validation Codex
**Status:** Constitutional

---

## Part I — Architecture Standard

### §1. Computational Definitions

#### §1.1 Vimshottari Dasha

Vimshottari Dasha is the canonical Jyotish time-lord technique. Nine planetary lords
are assigned periods in a fixed sequence totaling 120 years. The entry point into
the sequence is determined by the natal Moon's nakshatra (lunar mansion) and the
fraction of that nakshatra already elapsed at birth, which produces a partial first
Mahadasha (major period).

The authoritative engine is `vimshottari(moon_tropical_lon, natal_jd)`. It accepts
the Moon's tropical longitude, a Julian Day number, and an optional `levels`
parameter controlling how many recursive levels of sub-periods are computed. It
returns a flat list of `DashaPeriod` records covering the full 120-year sequence
from birth at all requested levels.

**Dasha lords and their year allocations (`VIMSHOTTARI_YEARS`):**

| Planet | Years |
|---|---|
| Ketu | 7 |
| Venus | 20 |
| Sun | 6 |
| Moon | 10 |
| Mars | 7 |
| Rahu | 18 |
| Jupiter | 16 |
| Saturn | 19 |
| Mercury | 17 |

The sequence repeats cyclically. Total = 120 years.

**Recursive levels (Dasha hierarchy):**

| Level | Name |
|---|---|
| 1 | Mahadasha (major) |
| 2 | Antardasha (sub) |
| 3 | Pratyantardasha (sub-sub) |
| 4 | Sookshma |
| 5 | Prana |

Sub-period durations at each level are proportional to the lord's share of the
parent period. Level 1 periods sum to the lord's full `VIMSHOTTARI_YEARS` allocation
(adjusted for the birth nakshatra fraction in the first Mahadasha). At each deeper
level, the sub-lord's proportion of the parent is its `VIMSHOTTARI_YEARS` divided by
120, applied to the parent's duration.

**Year basis:** Two year-basis doctrines exist for converting Julian Day durations
to calendar years. The `year_basis` field on `DashaPeriod` identifies which was used.
This is a doctrinal flag preserved from the engine; both doctrines use the same
proportional structure.

**Lord types (`DashaLordType`):**

| Value | Planets |
|---|---|
| `LUMINARY` | Sun, Moon |
| `INNER` | Mercury, Venus, Mars |
| `OUTER` | Jupiter, Saturn |
| `NODE` | Rahu, Ketu |

Lord type is a structural classification based on the planet's astronomical category
within Jyotish doctrine. It is not a dignity or condition assessment.

---

### §2. Layer Structure

The dasha subsystem is organized into ten layers, each building on the prior
according to the constitutional dependency graph.

| Layer | Phase | Vessel / Function |
|---|---|---|
| 0 | Core | `vimshottari()` |
| 1 | Truth Preservation | `DashaPeriod` |
| 2 | Classification | `DashaLordType` |
| 3 | Inspectability | `is_active_at()`, duration properties, `current_dasha()` |
| 4 | Policy | `levels` parameter, `year_basis` |
| 5 | Relational Formalization | `DashaActiveLine`, `dasha_active_line()` |
| 6 | Relational Hardening | temporal containment guard, `lord_types`, `is_node_chain`, `is_complete` |
| 7 | Integrated Local Condition | `DashaConditionProfile`, `dasha_condition_profile()` |
| 8 | Aggregate Intelligence | `DashaSequenceProfile`, `dasha_sequence_profile()` |
| 9 | Network Intelligence | `DashaLordPair`, `dasha_lord_pair()` |
| 10 | Hardening | `validate_vimshottari_output()` |

---

### §3. Delegated Assumptions

The dasha subsystem does not compute the following. Callers are responsible for
supplying correct values.

- `moon_tropical_lon`: the tropical longitude of the natal Moon, computed externally
  from an ephemeris
- `natal_jd`: a valid Julian Day number representing the moment of birth
- Ayanamsa application: the subsystem receives a tropical longitude and applies the
  configured ayanamsa internally to derive the sidereal position for nakshatra
  assignment; the ayanamsa choice is a system-level configuration, not a per-call
  parameter
- `levels`: how many recursive levels of sub-periods to compute; the caller controls
  depth; the subsystem does not enforce a maximum

---

### §4. Doctrine Surface

The doctrinal choices made by the dasha subsystem are explicit and located.

| Choice | Location | Default |
|---|---|---|
| Dasha sequence order | `VIMSHOTTARI_SEQUENCE` module constant | Ketu-Venus-Sun-Moon-Mars-Rahu-Jupiter-Saturn-Mercury |
| Year allocations | `VIMSHOTTARI_YEARS` module constant | Canonical 120-year totals |
| Nakshatra-to-lord mapping | `NAKSHATRA_LORD` module constant | 27 nakshatras mapped to 9 lords cyclically |
| Year basis | `DashaPeriod.year_basis` field | Preserved from engine; two doctrines supported |
| Levels computed | `vimshottari()` `levels` parameter | Caller-controlled |
| Lord type classification | `DashaLordType` enum, `DashaConditionProfile.lord_type` field | LUMINARY / INNER / OUTER / NODE |

---

### §5. Public Vessels

The following are the constitutional public vessels of the dasha subsystem.

**Enumerations:**
- `DashaLordType` — classifies a dasha lord as LUMINARY, INNER, OUTER, or NODE

**Truth-preservation vessels:**
- `DashaPeriod` — a single Vimshottari period at any level

**Relational vessels:**
- `DashaActiveLine` — the full chain of active periods from Mahadasha to the deepest
  active level at a point in time

**Condition vessels:**
- `DashaConditionProfile` — integrated doctrinal summary for one `DashaPeriod`

**Aggregate vessels:**
- `DashaSequenceProfile` — chart-wide summary of a full Mahadasha sequence

**Network vessels:**
- `DashaLordPair` — the Mahadasha/Antardasha lord pair derived from a `DashaActiveLine`

**Computational functions:**
- `vimshottari(moon_tropical_lon, natal_jd, ...)` — core Vimshottari Dasha engine
- `current_dasha(moon_tropical_lon, natal_jd, current_jd)` — convenience function
  returning the active period chain at a given Julian Day
- `dasha_active_line(active_periods)` — relational line from a list of active periods
- `dasha_condition_profile(period)` — condition profile for one Dasha period
- `dasha_sequence_profile(periods)` — aggregate profile for a Mahadasha sequence
- `dasha_lord_pair(line)` — network pair from a `DashaActiveLine`
- `validate_vimshottari_output(periods)` — invariant guard for Vimshottari output

---

## Part II — Terminology Standard

### §6. Required Terms

The following terms carry specific meanings within this subsystem and must not be
used loosely.

| Term | Normative Meaning |
|---|---|
| **Mahadasha** | A `DashaPeriod` with `level=1`; one of the nine 120-year sequence allocations |
| **Antardasha** | A `DashaPeriod` with `level=2`; a sub-period within a Mahadasha |
| **Pratyantardasha** | A `DashaPeriod` with `level=3` |
| **Sookshma** | A `DashaPeriod` with `level=4` |
| **Prana** | A `DashaPeriod` with `level=5` |
| **level** | The 1-based integer depth of a `DashaPeriod`; 1 is the outermost |
| **lord** | The planet assigned to a `DashaPeriod`; drawn from the nine Vimshottari lords |
| **lord type** | The `DashaLordType` classification of a lord: LUMINARY, INNER, OUTER, or NODE |
| **nakshatra** | The lunar mansion (1 of 27) in which the natal Moon resides; determines entry point into the Dasha sequence |
| **nakshatra fraction** | The proportion of the birth nakshatra already elapsed at birth; determines the duration of the first (partial) Mahadasha |
| **year basis** | The doctrinal convention used to convert Julian Day differences to calendar years; preserved as a string on `DashaPeriod` |
| **active line** | A `DashaActiveLine`; the chain of periods active at a specific moment, from Mahadasha down to the deepest computed level |
| **depth** | The number of non-`None` levels populated in a `DashaActiveLine`; equivalent to the level of the deepest active period |
| **condition profile** | A flat doctrinal summary of a single `DashaPeriod`, integrating all layers |
| **sequence profile** | A chart-wide aggregate across all Mahadasha-level periods and their condition profiles |
| **lord pair** | The Mahadasha/Antardasha combination at a moment; a network node derived from a `DashaActiveLine` |

---

### §7. Forbidden Conflations

The following pairs must not be equated.

**`DashaPeriod` and `DashaConditionProfile`**
A `DashaPeriod` is the raw truth-preservation vessel from the engine. A
`DashaConditionProfile` is a derived doctrinal summary. One is the source; the other
is a projection of it.

**`level` and `depth`**
`level` is the field on a single `DashaPeriod`. `depth` is the property on a
`DashaActiveLine` counting how many levels are populated. They are related but not
interchangeable.

**`lord_type` and planet name**
`DashaLordType` classifies a planet into a structural category. It is not the planet
name and must not be used to identify a specific planet. Two planets can share a lord
type (e.g., Rahu and Ketu are both NODE).

**`is_node_chain` and `is_node_dasha`**
`DashaActiveLine.is_node_chain` is `True` only when every non-`None` level in the
line has a node lord. `DashaConditionProfile.is_node_dasha` is `True` only when that
specific period's lord is a node. One is a chain-level property; the other is a
period-level property.

**`DashaActiveLine` and `DashaLordPair`**
A `DashaActiveLine` is the full active period chain up to five levels deep. A
`DashaLordPair` is the network projection of that chain down to only the Mahadasha
and Antardasha lords. One is the full structural record; the other is a two-node
network edge.

**`DashaSequenceProfile` and `DashaActiveLine`**
A `DashaSequenceProfile` is a chart-wide aggregate over all Mahadasha periods. A
`DashaActiveLine` is a point-in-time slice of the active period chain. One is a
global summary; the other is a temporal snapshot.

**`nakshatra` and `birth_nakshatra`**
`nakshatra` is an astronomical concept (27 lunar mansions). `birth_nakshatra` on
`DashaConditionProfile` is the specific nakshatra the natal Moon occupied. Only
Mahadasha-level condition profiles carry a meaningful `birth_nakshatra`; sub-period
profiles carry `None`.

**`year_basis` and duration**
`year_basis` is a doctrinal identifier for the year-conversion convention. It is not
a duration and must not be used in arithmetic. Duration in years is stored in
`DashaPeriod.years`; duration in days in `DashaPeriod.days`.

---

## Part III — Invariant Register

### §8.1 Vessel Invariants

**`DashaPeriod`:**
- `level` is an integer ≥ 1
- `planet` is a recognized Vimshottari lord name
- `start_jd < end_jd`
- `years > 0` and `days > 0`
- `parent_planet`, if set, identifies a recognized Vimshottari lord

**`DashaActiveLine`:**
- `mahadasha` is always present and non-`None`
- Each subsequent level field is `None` unless the preceding level is also non-`None`
  (no gaps: `pratyantardasha` cannot be set if `antardasha` is `None`)
- All present periods are in strict level order: Mahadasha contains Antardasha
  contains Pratyantardasha contains Sookshma contains Prana (±1e-6 tolerance)
- Temporal containment is enforced in `__post_init__`: each child's `start_jd` ≥
  parent's `start_jd` − 1e-6, and child's `end_jd` ≤ parent's `end_jd` + 1e-6

**`DashaConditionProfile`:**
- `lord_type` is a valid `DashaLordType` value or `None`
- `years > 0` and `days > 0`
- `is_node_dasha` and `is_luminary_dasha` are mutually exclusive (both cannot be `True`)
- `birth_nakshatra` and `nakshatra_fraction` are both `None` or both non-`None`

---

### §8.2 Truth Invariants

- `VIMSHOTTARI_YEARS` is immutable. No function modifies or overrides it at runtime.
- `VIMSHOTTARI_SEQUENCE` is immutable. The order of the nine lords is fixed.
- `DashaPeriod.planet` is validated against `VIMSHOTTARI_SEQUENCE` in `__post_init__`.
  A `DashaPeriod` with an unrecognized planet name cannot be constructed.
- The first Mahadasha in any `vimshottari()` output may be shorter than its canonical
  `VIMSHOTTARI_YEARS` allocation due to the birth nakshatra fraction.
- Sub-period durations are proportional to the lord's share of the parent. This
  proportionality is preserved in `DashaPeriod.years` without rounding.

---

### §8.3 Aggregate Invariants

**`DashaSequenceProfile`:**
- `luminary_count + inner_count + outer_count + node_count == mahadasha_count`
- `profile_count == len(profiles) == mahadasha_count`
- `total_years > 0`
- `total_years ≤ VIMSHOTTARI_TOTAL` (120 years); may be less if the first Mahadasha
  is partial

---

### §8.4 Network Invariants

**`DashaLordPair`:**
- `maha_profile` is always present
- `antar_profile` is `None` if and only if the source `DashaActiveLine` has no
  Antardasha
- `is_same_lord` is meaningful only when `has_antar` is `True`
- `both_are_nodes` implies `involves_node`; `involves_node` does not imply
  `both_are_nodes`

---

## Part IV — Failure Doctrine

### §9.1 Invalid Inputs

- Passing a non-finite `moon_tropical_lon` to `vimshottari()` raises `ValueError`.
- Passing a non-finite `natal_jd` to `vimshottari()` raises `ValueError`.
- Constructing a `DashaPeriod` with an unrecognized planet name raises `ValueError`
  (enforced in `DashaPeriod.__post_init__`).
- Constructing a `DashaActiveLine` with a `None` Mahadasha raises `TypeError`.
- Constructing a `DashaActiveLine` with a level gap (e.g., Pratyantardasha set but
  Antardasha `None`) raises `ValueError`.
- Constructing a `DashaActiveLine` where a child period falls outside its parent's
  temporal bounds (beyond the ±1e-6 tolerance) raises `ValueError`.

---

### §9.2 Search Exhaustion

- `current_dasha()` returns an empty list if the queried `current_jd` falls outside
  the computed 120-year period range. This is not an error.
- `dasha_active_line()` receiving an empty list raises `ValueError`.

---

### §9.3 Invariant Failure

- `validate_vimshottari_output()` raises `ValueError` with a descriptive message if:
  - any two adjacent level-1 periods (Mahadashas) overlap in Julian Day
  - any level-1 period is out of chronological order relative to its predecessor
  - any sub-period at any level is not temporally contained within its parent
  - any sub-periods within a parent are out of chronological order or overlap
- `DashaSequenceProfile.__post_init__` raises `ValueError` if the sum
  `luminary_count + inner_count + outer_count + node_count` does not equal
  `mahadasha_count`.

---

## Part V — Determinism Standard

### §10. Determinism Guarantees

- `vimshottari()` is fully deterministic: given the same `moon_tropical_lon`,
  `natal_jd`, and `levels`, the output list is identical in every call with no
  dependency on external state beyond the configured ayanamsa.
- The flat list returned by `vimshottari()` is ordered by `(level, start_jd)`.
- All nine Mahadasha periods and all their sub-periods appear in chronological order
  within their level.
- `dasha_active_line()`, `dasha_condition_profile()`, `dasha_sequence_profile()`,
  and `dasha_lord_pair()` are pure functions with no side effects.
- Floating-point accumulation across deeply nested sub-periods may produce `end_jd`
  values that differ from the parent's `end_jd` by a small epsilon. The containment
  tolerance of ±1e-6 JD in `DashaActiveLine.__post_init__` accommodates this. This
  is the only permitted numeric approximation in the subsystem.
- The ayanamsa value used to convert tropical Moon longitude to sidereal longitude
  for nakshatra assignment is drawn from the system-level configured ayanamsa. It is
  not a per-call parameter. Two calls with the same inputs but different ayanamsa
  configurations may produce different nakshatra assignments and therefore different
  Dasha sequences. This is a system-level dependency, not a non-determinism in the
  subsystem itself.

---

## Part VI — Validation Codex

### §11. Minimum Validation Commands

The following commands must pass without error on any constitutionally correct
installation of this subsystem:

```
python -m pytest tests/unit/test_dasha.py -v
```

All tests in `test_dasha.py` must pass. The test suite validates:
- `vimshottari()` structural correctness (level distribution, sequence order)
- `DashaPeriod` field fidelity and `__post_init__` guards
- `DashaActiveLine` construction, depth property, `as_list()` round-trip
- `DashaActiveLine` temporal containment rejection
- `lord_types`, `is_node_chain`, `is_complete` properties
- `DashaConditionProfile` field fidelity, `level_name`, `birth_nakshatra`,
  `nakshatra_fraction`, exclusivity invariant
- `DashaSequenceProfile` counts, canonical lord distribution, `total_years` bounds,
  invariant rejection
- `DashaLordPair` construction, `has_antar`, `is_same_lord`, `involves_node`,
  `both_are_nodes`
- `validate_vimshottari_output()` correctness, overlap detection, sub-containment
  detection

---

### §12. Required Validation Themes

Any validation suite for this subsystem must demonstrate the following:

**Truth preservation:**
- A `DashaPeriod` from `vimshottari()` carries `planet`, `level`, `parent_planet`,
  `start_jd`, `end_jd`, `years`, `days`, `year_basis`, and `birth_nakshatra` (for
  the first Mahadasha) without truncation or flattening.

**Relational integrity:**
- A `DashaActiveLine` constructed from active periods preserves `mahadasha` through
  the deepest active level without reordering.
- Temporal containment is enforced: a child period outside its parent's bounds causes
  `ValueError` at construction time.

**Classification correctness:**
- `DashaLordType.NODE` applies to Rahu and Ketu and only to Rahu and Ketu.
- `DashaLordType.LUMINARY` applies to Sun and Moon and only to Sun and Moon.
- `is_luminary_dasha` and `is_node_dasha` are mutually exclusive.

**Aggregate integrity:**
- `luminary_count + inner_count + outer_count + node_count == mahadasha_count`
  in any `DashaSequenceProfile` constructed from a valid sequence.
- `total_years ≤ 120.0` for any valid sequence.

**Network correctness:**
- `DashaLordPair.is_same_lord` is `True` when Mahadasha and Antardasha lords are
  identical.
- `DashaLordPair.involves_node` detects node lords at either level.
- `DashaLordPair` raises `ValueError` if constructed from an invalid `DashaActiveLine`.

**Hardening:**
- `validate_vimshottari_output()` detects overlapping Mahadashas.
- `validate_vimshottari_output()` detects sub-periods outside their parent.
- `validate_vimshottari_output()` passes silently on valid output.

---

## Part VII — Future Boundary

### §13. Explicit Non-Goals

The following are explicitly outside the scope of this subsystem as constitutionalized.

**Not in scope:**

- **Chart calculation.** The subsystem does not compute natal Moon positions,
  house cusps, or ascendants. These are delegated to the chart engine.

- **Ayanamsa selection.** The ayanamsa used to derive the sidereal Moon longitude
  is a system-level configuration. The subsystem consumes a tropical longitude and
  applies the configured ayanamsa internally, but the selection of which ayanamsa
  to use is outside this standard.

- **Nakshatra calculation beyond birth entry.** The subsystem uses the natal
  nakshatra only to determine the Dasha sequence entry point and the first
  Mahadasha's partial duration. Ongoing transit-based nakshatra tracking is not
  part of this subsystem.

- **Predictive interpretation.** The subsystem produces structural timing data.
  It does not assess whether a Dasha lord is beneficial or malefic, strong or weak.
  Interpretation is a higher-level concern.

- **Ashtottari Dasha or other Dasha systems.** This subsystem constitutionalizes
  Vimshottari Dasha only. Other Jyotish Dasha systems (Ashtottari, Yogini, etc.)
  are separate techniques requiring separate constitutionalization.

- **Graha Bala or Shadbala.** Planetary strength assessment is a separate dignities
  or condition subsystem concern and is not part of this standard.

- **Transit and progression overlay.** Correlating Dasha periods with transit or
  natal chart positions is a cross-subsystem concern and is not part of this standard.

- **Conditional Dasha activation.** Whether a Dasha lord is considered "activated"
  by transit triggers or other conditional doctrines is an interpretive layer above
  this standard.

- **Dasha rectification.** The subsystem does not provide tools for adjusting birth
  time based on Dasha periods. That is a separate diagnostic concern.

Any future extension that crosses these boundaries requires a new constitutional phase or a
separate subsystem constitutionalization, not an in-place amendment to this standard.

