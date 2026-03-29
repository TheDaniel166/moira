# Lord of the Turn Backend Standard

**Subsystem:** `moira/lord_of_the_turn.py`
**Computational Domain:** Annual Time-Lord via Profected Ascendant (Al-Qabisi and Egyptian/Al-Sijzi)
**SCP Phase:** 11 — Architecture Freeze and Validation Codex
**Status:** Constitutional

---

## Epistemic Classification Legend

Statements in this document are marked with one of three epistemic labels:

| Label | Meaning |
|---|---|
| **[DS]** DIRECTLY SOURCED | Closely follows the explicit wording of the named historical source |
| **[HGR]** HISTORICALLY GROUNDED RECONSTRUCTION | Consistent with the tradition but fills a gap not explicitly resolved in extant source text |
| **[MF]** MOIRA FORMALIZATION | A computational choice made by Moira to operationalize ambiguous or silent doctrine |

---

## Part I — Architecture Standard

### §1. Computational Definition

#### §1.1 What the Lord of the Turn Is

The Lord of the Turn is an annual time-lord technique that identifies the planet
governing a native's solar-return year. The natal Ascendant is profected one
sign per year; the planet ruling the resulting *Sign of the Year* in the Solar
Return chart, selected by method-specific condition rules, becomes the Lord of
the Turn for that year.

**Doctrine basis:**
- Al-Qabisi method: Al-Qabisi (Alcabitius), *Al-Madkhal ilā Ṣinā'at Aḥkām
  al-Nujūm* (Introduction to the Art of Astrology). Translation: Charles
  Burnett, Keiji Yamamoto, Michio Yano (Warburg Institute, 2004).
- Egyptian/Al-Sijzi method: Egyptian bound-lord tradition as transmitted in
  Al-Sijzi, *Introduction to the Book of the Indications of the Celestial Signs*.

**Naming note:** Historical sources use *dominus conversionis* (Lord of the
Turn), *dominus orbis* (Lord of the Orb), and *dominus circuli* (Lord of the
Circle) interchangeably. In Moira these are **distinct techniques**: the Lord
of the Turn is seeded from the profected ASC; the Lord of the Orb is seeded
from the birth planetary hour.

#### §1.2 Profection Formula

```
profected_longitude = (age * 30.0 + natal_asc) % 360.0
```

**[DS]** Age 0 = first year of life. Each year advances one sign (30°). The
cycle repeats every 12 years.

#### §1.3 Al-Qabisi Succession Hierarchy

**[DS]** The primary candidate is the domicile lord of the Sign of the Year;
if blocked, the search falls back through a dignity hierarchy.

| Step | Candidate | Acceptance condition |
|---|---|---|
| 1 | Domicile lord of Sign of the Year | In a good SR house (1,2,4,5,7,10,11), not combust, not retrograde |
| 2 | Exaltation lord of Sign of the Year | Same three conditions |
| 3 | Sect triplicity ruler of Sign of the Year | Angular in SR (houses 1,4,7,10) **[HGR]** |
| 4 | Bound lord of profected degree | Last resort — no condition applied |

**Good-house list {1,2,4,5,7,10,11}:** **[HGR]** The traditional distinction
between angular/succedent versus cadent houses is well attested; the precise
list is a reconstruction consistent with Al-Qabisi's period.

**Triplicity: angular only:** **[HGR]** Al-Qabisi names triplicity rulers as
candidates, but the stricter "angular only" test is a Moira reconstruction.
The source wording is ambiguous between requiring angular placement and
requiring the standard good-house condition.

**Blockers:** a candidate is rejected when any of these apply:
- `CADENT_IN_SR` — in SR house 3, 6, 9, or 12
- `COMBUST` — within `combust_orb` of the SR Sun (default 8.5° **[MF]**)
- `RETROGRADE` — listed in `sr_chart.retrograde_planets`

Sun and Moon are never counted as combust. **[DS]**

**On tiebreaking:** The succession model is inherently sequential — the engine
returns as soon as the first qualifying candidate is found, so no two
candidates are ever simultaneously "well-placed." Tiebreaker language appearing
in some source readings likely reflects a simultaneous almuten-scoring reading
of the technique. Moira implements the sequential model. **[MF]**

#### §1.4 Egyptian / Al-Sijzi Testimony Method

**[DS]** The bound lord of the profected degree is primary (Egyptian tradition).
Al-Sijzi refines this by requiring the lord to "witness" the SR chart's focal
points.

| Step | Logic |
|---|---|
| 1 | Primary: bound lord of the profected degree |
| 2 | Bound lord witnesses SR ASC or sect light → `BOUND_PRIMARY_WITNESSING` **[DS]** |
| 3 | Bound lord does not witness: rank all seven classical planets by testimony count |
| 4 | Highest-count planet that witnesses SR ASC or sect light → `TESTIMONY_WINNER_WITNESSING` **[HGR]** |
| 5 | If none witness → bound lord returned as `BOUND_FALLBACK` |

**Witnessing (whole-sign Ptolemaic):** **[DS]** A planet witnesses a target
when its sign casts a major aspect to the target sign. Aspect diffs
`(planet_sign_idx − target_sign_idx) mod 12` that count as witnessing:
`{0, 2, 3, 4, 6, 8, 9, 10}` (conjunction, sextile, square, trine, opposition
and their retrograde counterparts).

**Witnessing target = SR ASC or sect light:** **[DS]** Al-Sijzi's text
specifies the SR Ascendant and the sect light (Sun for day charts, Moon for
night charts) as the focal points. `LordOfTurnCandidateAssessment.witnesses_target`
encodes this directly. The `LordOfTurnConditionProfile.lord_witnesses_sr_asc`
field provides the SR-ASC-only component for interpretive use.

**Testimony count is binary:** **[HGR]** One point per dignity type held at
the profected longitude (domicile, exaltation, triplicity, bound, face;
maximum 5). This binary (holds / does not hold) model is consistent with
Al-Qabisi's hierarchical testimony doctrine. The classic 5/4/3/2/1 numeric
weighting scheme is an alternative reading. **[MF]** Alphabetical tiebreak
among equal testimony counts for determinism.

#### §1.5 DOMICILE_ONLY Mode

**[MF]** When `LordOfTurnSRChart.house_placements` is empty the engine skips
all SR condition checks and returns the domicile lord with reason `DOMICILE_ONLY`.
There is no historical equivalent for this degenerate mode; it exists to
support pre-SR-chart research and test scenarios. In this mode: `is_combust`
and `is_retrograde` are set to `False` (no position data available for
reliable evaluation); `is_well_placed` is set to `True`; `witnesses_target`
is computed against SR ASC and sect light if planet longitudes are supplied.

#### §1.6 Boundary Conditions

The engine operates on a supplied `LordOfTurnSRChart` vessel. It does **not**
compute:
- Solar return chart construction or house calculation
- Planetary ephemeris positions
- SR Lot of Fortune (caller supplies `sr_lot_fortune` if available)

---

### §2. Public API

#### §2.1 Primary Entry Point

```python
def lord_of_turn(
    natal_asc: float,
    age: int,
    sr_chart: LordOfTurnSRChart,
    policy: LordOfTurnPolicy = DEFAULT_LORD_OF_TURN_POLICY,
) -> LordOfTurnConditionProfile
```

Dispatches to the method engine selected by `policy.method`.

#### §2.2 Method-Specific Entry Points

```python
def lord_of_turn_al_qabisi(
    natal_asc: float,
    age: int,
    sr_chart: LordOfTurnSRChart,
    policy: LordOfTurnPolicy = DEFAULT_LORD_OF_TURN_POLICY,
) -> LordOfTurnResult

def lord_of_turn_egyptian_al_sijzi(
    natal_asc: float,
    age: int,
    sr_chart: LordOfTurnSRChart,
    policy: LordOfTurnPolicy = DEFAULT_LORD_OF_TURN_POLICY,
) -> LordOfTurnResult
```

**Parameters:**

| Parameter | Type | Description |
|---|---|---|
| `natal_asc` | `float` | Natal Ascendant longitude [0, 360) |
| `age` | `int` | Native's completed age in years (>= 0) |
| `sr_chart` | `LordOfTurnSRChart` | Solar Return chart data vessel |
| `policy` | `LordOfTurnPolicy` | Doctrinal configuration |

**Raises:** `ValueError` if `natal_asc` is non-finite or `age < 0`.

#### §2.3 Validation Entry Point

```python
def validate_lord_of_turn_output(profile: LordOfTurnConditionProfile) -> list[str]
```

Returns a list of failure strings. Empty list = fully consistent. See §4.

---

### §3. Type Surface

#### §3.1 Classification Enums

| Type | Values | Purpose |
|---|---|---|
| `LordOfTurnMethod` | `AL_QABISI`, `EGYPTIAN_AL_SIJZI` | Which algorithm |
| `LordOfTurnSelectionReason` | See §3.1a | Why this planet was selected |
| `LordOfTurnBlockerReason` | `CADENT_IN_SR`, `COMBUST`, `RETROGRADE`, `NOT_WITNESSING`, `NO_TESTIMONY` | Why a candidate was rejected |

**§3.1a LordOfTurnSelectionReason values:**

| Value | Meaning |
|---|---|
| `DOMICILE_WELL_PLACED` | Al-Qabisi: domicile lord passed condition check |
| `EXALTATION_FALLBACK` | Al-Qabisi: domicile blocked; exaltation lord passed |
| `TRIPLICITY_FALLBACK` | Al-Qabisi: domicile and exaltation blocked; sect triplicity lord angular |
| `BOUND_FALLBACK` | Al-Qabisi: all above blocked; bound lord as last resort. Also Egyptian fallback |
| `BOUND_PRIMARY_WITNESSING` | Egyptian/Al-Sijzi: bound lord witnesses SR ASC or sect light |
| `TESTIMONY_WINNER_WITNESSING` | Egyptian/Al-Sijzi: testimony winner witnesses |
| `DOMICILE_ONLY` | No SR house data; domicile lord returned unconditionally **[MF]** |

#### §3.2 Policy Surface

```python
@dataclass(frozen=True, slots=True)
class LordOfTurnPolicy:
    method:      LordOfTurnMethod = LordOfTurnMethod.AL_QABISI
    combust_orb: float            = 8.5   # [MF] computational choice
```

`DEFAULT_LORD_OF_TURN_POLICY` is the module-level default (AL_QABISI, 8.5°).

#### §3.3 Input Vessel — LordOfTurnSRChart

| Field | Type | Description |
|---|---|---|
| `sr_asc` | `float` | SR Ascendant longitude [0, 360) |
| `planets` | `dict[str, float]` | SR planet longitudes |
| `house_placements` | `dict[str, int]` | Planet → SR house (1–12). Empty = DOMICILE_ONLY mode |
| `is_night` | `bool` | True when SR Sun is below the SR horizon |
| `retrograde_planets` | `frozenset[str]` | Planets retrograde in SR |
| `sr_lot_fortune` | `float \| None` | SR Lot of Fortune (caller computes with sect reversal) |

**Properties:** `sect_light` (`'Sun'` or `'Moon'`), `sect_light_longitude`.

**Invariant:** `sr_asc` and all planet longitudes must be finite.

#### §3.4 Truth-Preservation Vessel — LordOfTurnProfection

| Field | Type | Description |
|---|---|---|
| `natal_asc` | `float` | Natal ASC used |
| `age` | `int` | Completed age |
| `profected_longitude` | `float` | `(age * 30 + natal_asc) % 360` |
| `profected_sign` | `str` | Sign of the Year |
| `profected_degree_in_sign` | `float` | Degree within sign [0, 30) |
| `profected_sign_index` | `int` | 0-based index (0 = Aries) |

#### §3.5 Candidate Vessel — LordOfTurnCandidateAssessment

| Field | Type | Description |
|---|---|---|
| `planet` | `str` | Candidate planet |
| `role` | `str` | `'domicile'`, `'exaltation'`, `'triplicity'`, `'bound'`, `'testimony'` |
| `sr_house` | `int \| None` | SR house (1–12), or None if not provided |
| `is_combust` | `bool` | Within combust_orb of SR Sun |
| `is_retrograde` | `bool` | Retrograde in SR |
| `is_well_placed` | `bool` | In good house AND not combust AND not retrograde |
| `blocker_reasons` | `tuple[LordOfTurnBlockerReason, ...]` | Which blockers fired |
| `witnesses_target` | `bool` | **[DS/MF]** Planet witnesses the SR Ascendant OR the SR sect light sign (whole-sign Ptolemaic). Primary selection criterion for Egyptian/Al-Sijzi; informational for Al-Qabisi |
| `testimony_count` | `int` | **[HGR]** Dignity types held at profected longitude (0–5, binary count) |

**Invariant:** `is_well_placed` must be consistent with `sr_house`, `is_combust`,
`is_retrograde` — enforced in `__post_init__`.

#### §3.6 Primary Result Vessel — LordOfTurnResult

| Field | Type | Description |
|---|---|---|
| `lord` | `str` | The Lord of the Turn planet |
| `method` | `LordOfTurnMethod` | Algorithm used |
| `profection` | `LordOfTurnProfection` | Profection step result |
| `selection_reason` | `LordOfTurnSelectionReason` | Why this planet was chosen |
| `candidates` | `tuple[LordOfTurnCandidateAssessment, ...]` | All assessed candidates |

**Phase 3 properties:** `sign_of_year`, `age`, `winning_candidate`,
`blocked_candidates`, `is_fallback`.

**Invariants:** `lord` is a classical planet; `candidates` is non-empty.

**On candidate count:** In Al-Qabisi sequential mode the candidates tuple
contains only planets that were actually assessed before the engine returned;
candidates beyond the winning planet are always planets that were blocked.
**[MF]**

#### §3.7 Condition Profile — LordOfTurnConditionProfile

| Field | Type | Description |
|---|---|---|
| `result` | `LordOfTurnResult` | Primary result |
| `sr_is_night` | `bool` | Whether SR was nocturnal |
| `sect_light` | `str` | `'Sun'` or `'Moon'` |
| `lord_witnesses_sr_asc` | `bool` | Lord's sign witnesses the SR ASC sign specifically (SR-ASC-only component of the winning candidate's `witnesses_target`) |
| `lord_sr_house` | `int \| None` | Lord's SR house |

**Properties:** `is_fallback`, `lord`, `sign_of_year` (delegations to `result`).

---

### §4. Validation Codex

`validate_lord_of_turn_output(profile)` checks:

| # | Check |
|---|---|
| 1 | `result.lord` is a classical planet |
| 2 | `profected_longitude` in [0, 360) |
| 3 | `profected_degree_in_sign` in [0, 30) |
| 4 | `profected_sign` matches `sign_of(profected_longitude)` |
| 5 | `candidates` is non-empty |
| 6 | A candidate with `planet == lord` exists in candidates |
| 7 | All `sr_house` values in [1, 12] or None |
| 8 | All `testimony_count` values >= 0 |
| 9 | `is_well_placed=True` candidates have no `blocker_reasons` |
| 10 | `profile.sect_light` is `'Sun'` or `'Moon'` |

---

### §5. Doctrine Boundaries

#### §5.1 What This Module Owns

- Profection arithmetic
- Al-Qabisi succession hierarchy (domicile → exaltation → triplicity → bound)
- Egyptian/Al-Sijzi testimony ranking and witnessing check
- Condition assessment vessels for each candidate
- Integrated condition profile including lord's SR ASC witnessing

#### §5.2 What This Module Does Not Own

- Solar return chart construction (`moira.solar_returns`, deferred)
- Planetary ephemeris positions
- House calculation
- Annual hierarchy orchestration (Lord of the Turn as one of Abu Ma'shar's eight
  annual indicators alongside profections, firdaria, etc.)
- Natal chart dignity evaluation of the Lord of the Turn planet

#### §5.3 Deferred (Phase 2)

Integration of the Lord of the Turn within Abu Ma'shar's eight-indicator annual
hierarchy. The hierarchy interface requires a separate doctrinal design note.

---

## Part II — Implementation Notes

### §6. Module Location

`moira/lord_of_the_turn.py` — standalone module.

Rationale: distinct from `timelords.py` (firdaria, zodiacal releasing),
`profections.py` (Lord of the Year / profection lord), and `lord_of_the_orb.py`
(planetary-hour–based lord). The Lord of the Turn requires SR chart data that
the other modules do not need.

### §7. Dependency Graph

```
lord_of_the_turn.py
  ├─ moira.constants      sign_of, SIGNS
  ├─ moira.dignities      DOMICILE, EXALTATION
  ├─ moira.egyptian_bounds  EGYPTIAN_BOUNDS
  └─ moira.longevity      TRIPLICITY_RULERS, FACE_RULERS
```

Caller connects: SR chart construction (deferred) → `LordOfTurnSRChart`.

### §8. DOMICILE_ONLY Mode

**[MF]** When `LordOfTurnSRChart.house_placements` is empty the engine skips
all condition checks and returns the domicile lord with reason `DOMICILE_ONLY`.
All three condition checks (house, combust, retrograde) are skipped. The
`witnesses_target` field is still computed if planet longitudes are present
(uses SR ASC and sect light as targets). This mode supports pre-SR-chart
research and test scenarios.

### §9. Witnessing Target: SR ASC or Sect Light

The witnessing target inside `_build_candidate()` is the **SR Ascendant sign**
OR the **SR sect light sign**. This applies uniformly to both Al-Qabisi and
Egyptian/Al-Sijzi modes.

**[DS]** for Egyptian/Al-Sijzi: Al-Sijzi explicitly requires the lord to
witness the SR ASC or sect light.

**[MF]** for Al-Qabisi: witnessing is informational only in Al-Qabisi mode —
the sequential succession architecture makes a witnessing tiebreaker
inapplicable. The `witnesses_target` field is populated for interpretive value
even when it does not drive the selection.

The `LordOfTurnConditionProfile.lord_witnesses_sr_asc` field provides the
SR-ASC-only component (not including the sect light).

---

## Part III — Change Policy

### §10. Stability Guarantees

**Frozen:**
- `LordOfTurnProfection` field set and arithmetic invariants
- `LordOfTurnCandidateAssessment` field set, `is_well_placed` consistency invariant,
  and `witnesses_target` semantics (SR ASC or sect light)
- `LordOfTurnResult` field set and selection reason semantics
- `LordOfTurnSelectionReason` and `LordOfTurnBlockerReason` enum values
- The four-step Al-Qabisi succession order
- The Egyptian/Al-Sijzi three-path selection logic

**Internal (may change):**
- `_GOOD_HOUSES`, `_CADENT_HOUSES`, `_WITNESSING_DIFFS` constants
- `_build_candidate`, `_testimony_count`, `_compute_profection` helpers
- `_validate_inputs`

### §11. Extension Points

To integrate the Lord of the Turn with Abu Ma'shar's annual hierarchy (Phase 2):

1. Design the eight-indicator hierarchy vessel in a separate doctrinal note
2. Add an `annual_hierarchy(lot_result, profection_lord, firdar_lord,
   lord_of_turn_profile, ...)` function that returns a combined assessment
3. Do not modify any existing Phase 1–8 vessels or the primary engines

---

## Part IV — Historically Uncertain Areas

The following aspects of this subsystem remain historically uncertain and are
therefore marked as reconstruction or formalization:

1. **Triplicity angular requirement** — Al-Qabisi mentions triplicity rulers but
   the "angular only" condition is not explicitly stated. The stricter test is
   adopted from general Arabic tradition; a broader good-place condition would
   also be defensible.

2. **Combust orb = 8.5°** — Traditional combust orbs range from 6° to 15°
   depending on source. 8.5° is a mid-range computational choice.

3. **Binary vs. numeric testimony count** — Some sources use the 5/4/3/2/1
   weighting for dignity levels; others treat each dignity type as binary. This
   subsystem uses binary counting as the better match for Al-Qabisi's
   testimony doctrine.

4. **Alphabetical tiebreak in Egyptian testimony ranking** — No historical source
   specifies how to break a tie when two planets have equal testimony counts.
   The alphabetical rule exists purely for computational determinism.

5. **DOMICILE_ONLY mode** — Entirely a Moira invention with no historical
   precedent. The historical technique always presupposes a computed SR chart.
