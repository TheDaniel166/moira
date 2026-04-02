# Lord of the Orb Backend Standard

**Subsystem:** `moira/lord_of_the_orb.py`
**Computational Domain:** Abu Ma'shar's Lord of the Orb Annual Time-Lord
**Constitutional Phase:** 11 — Architecture Freeze and Validation Codex
**Status:** Constitutional

---

## Part I — Architecture Standard

### §1. Computational Definition

#### §1.1 What the Lord of the Orb Is

The Lord of the Orb is a planetary-hour–based annual time-lord technique. The
planet governing the birth planetary hour becomes the Lord of the Orb for year
1 of the native's life and governs the significations of the 1st house for that
year. Each subsequent year, the next planet in the Chaldean order becomes Lord
of the Orb for the next house, producing two independent modular cycles.

**Doctrine basis:** Abu Ma'shar, *Kitāb taḥāwil sinī al-mawālīd*. Cycle
variants confirmed from: Benjamin N. Dykes, *Persian Nativities IV* (Cazimi
Press, 2019), pp. 126–128; Anthony Louis, blog (2021) — Diego de Torres
*Opus Astrologicum* (Salamanca, late 1480s–1490s).

**Ranking in Abu Ma'shar's annual hierarchy:** 6th of 8 annual indicators.
The Lord of the Orb is a participating signifier for the year, evaluated
alongside the Lord of the Year (profection lord, rank 1), Fardār lord (rank 5),
and five other indicators.

#### §1.2 Chaldean Order

The seven classical planets in Chaldean order (slowest to fastest):

| Index | Planet |
|---|---|
| 0 | Saturn |
| 1 | Jupiter |
| 2 | Mars |
| 3 | Sun |
| 4 | Venus |
| 5 | Mercury |
| 6 | Moon |

The sequence wraps modulo 7.

#### §1.3 Cycle Variants

Two cycle variants are admitted. Both agree on years 1–12 and diverge from
year 13 onward.

**CONTINUOUS_LOOP (default — Torres, Giuntini):**

```
planet_index = (birth_planet_index + year - 1) % 7
house        = ((year - 1) % 12) + 1
```

The 7-planet Chaldean sequence and the 12-house cycle are independent modular
counters. The full combined pattern repeats at LCM(7, 12) = 84 years (year 85
equals year 1 in both planet and house).

**Torres's verification:** with Venus as birth planet (index 4), years 1, 8,
15, 22, 29, 36 … all return Venus. The engine includes this as a built-in
validation check.

**SINGLE_CYCLE (Abu Ma'shar — ambiguous reading):**

```
cycle_position = (year - 1) % 12
planet_index   = (birth_planet_index + cycle_position) % 7
house          = cycle_position + 1
```

Both cycles reset together every 12 years. The planet for year 1 and year 13
are always identical. This reading is defensible from Abu Ma'shar's Arabic text
but is not confirmed in any worked example.

#### §1.4 House Significations

Each year's Lord of the Orb governs the traditional domain of the corresponding
house:

| House | Domain |
|---|---|
| 1 | Life, body, disposition |
| 2 | Wealth, substance, livelihood |
| 3 | Siblings, communications, short travel |
| 4 | Parents, home, foundations, end of matter |
| 5 | Children, pleasures, creativity |
| 6 | Health, illness, service, subordinates |
| 7 | Marriage, partnerships, open enemies |
| 8 | Death, transformation, others' resources |
| 9 | Religion, long travel, philosophy, dreams |
| 10 | Career, reputation, authority, public life |
| 11 | Friends, hopes, benefactors |
| 12 | Hidden enemies, imprisonment, sorrow, self-undoing |

#### §1.5 Night Determination

The Lord of the Orb is seeded from the birth planetary hour. The caller is
responsible for supplying `birth_planet` — the planet ruling the birth hour as
determined from `moira.planetary_hours.PlanetaryHour.ruler` for the birth JD.
This module does not own planetary hour calculation.

---

### §2. Public API

#### §2.1 Primary Entry Point

```python
def lord_of_orb(
    birth_planet: str,
    years: int,
    policy: LordOfOrbPolicy = DEFAULT_LORD_OF_ORB_POLICY,
) -> LordOfOrbAggregate
```

**Parameters:**

| Parameter | Type | Description |
|---|---|---|
| `birth_planet` | `str` | Planet ruling the birth planetary hour |
| `years` | `int` | Number of years to compute (>= 1; pass 84 for one full cycle) |
| `policy` | `LordOfOrbPolicy` | Doctrinal configuration |

**Valid birth_planet values:** `'Saturn'`, `'Jupiter'`, `'Mars'`, `'Sun'`,
`'Venus'`, `'Mercury'`, `'Moon'`.

**Returns:** `LordOfOrbAggregate` — complete result with all periods, condition
profiles, and aggregate intelligence.

**Raises:** `ValueError` if `birth_planet` is not a Chaldean planet or
`years < 1`.

#### §2.2 Convenience Function

```python
def current_lord_of_orb(
    birth_planet: str,
    age: int,
    policy: LordOfOrbPolicy = DEFAULT_LORD_OF_ORB_POLICY,
) -> LordOfOrbPeriod
```

Returns the active Lord of the Orb period for a native of the given completed
age. Age 0 maps to year 1; age N maps to year N + 1.

#### §2.3 Validation Entry Point

```python
def validate_lord_of_orb_output(aggregate: LordOfOrbAggregate) -> list[str]
```

Returns a list of failure strings. Empty list = fully consistent. See §4.

---

### §3. Type Surface

#### §3.1 Classification

| Type | Values | Purpose |
|---|---|---|
| `LordOfOrbCycleKind` | `CONTINUOUS_LOOP`, `SINGLE_CYCLE` | Which cycle variant governs the sequence |

#### §3.2 Policy Surface

```python
@dataclass(frozen=True)
class LordOfOrbPolicy:
    cycle_kind: LordOfOrbCycleKind = LordOfOrbCycleKind.CONTINUOUS_LOOP
```

`DEFAULT_LORD_OF_ORB_POLICY` is the module-level default (CONTINUOUS_LOOP).

#### §3.3 Primary Result Vessel — LordOfOrbPeriod

| Field | Type | Description |
|---|---|---|
| `year` | `int` | Year of life (>= 1) |
| `planet` | `str` | Lord of the Orb for this year |
| `house` | `int` | House governed (1–12) |
| `chaldean_index` | `int` | 0-based index in Chaldean order (0–6) |
| `cycle_kind` | `LordOfOrbCycleKind` | Cycle variant used |
| `house_signification` | `str` | Traditional domain of the house |

**Invariants:** `year >= 1`; `house` in [1, 12]; `chaldean_index` in [0, 6];
`CHALDEAN_ORDER[chaldean_index] == planet`.

**Phase 3 properties:**

| Property | Returns | Description |
|---|---|---|
| `house_zero_indexed` | `int` | 0-based house index |
| `is_year_one_planet` | `bool` | True every 7 years (planet recurrence) |
| `is_house_cycle_start` | `bool` | True when house == 1 |
| `years_until_next_same_planet` | `int` | Always 7 |

#### §3.4 Relational Vessel — LordOfOrbSequence

| Field | Type | Description |
|---|---|---|
| `birth_planet` | `str` | Birth-hour planet |
| `periods` | `list[LordOfOrbPeriod]` | All periods in year order |
| `cycle_kind` | `LordOfOrbCycleKind` | Cycle variant |

**Invariants:** non-empty; consecutive years from 1; year 1 planet == birth_planet;
all periods share the same cycle_kind.

**Methods:** `get(year)`, `years_for_planet(planet)`, `years_for_house(house)`.

**Phase 6 properties:** `span`, `planets_in_sequence`, `is_full_84_year_cycle`.

#### §3.5 Condition Vessel — LordOfOrbConditionProfile

| Field | Type | Description |
|---|---|---|
| `period` | `LordOfOrbPeriod` | The period |
| `house_signification` | `str` | Traditional house domain |
| `hierarchy_rank` | `int` | Always 6 (Abu Ma'shar) |
| `house_cycle_number` | `int` | Which 12-year house cycle (1-based) |
| `planet_cycle_number` | `int` | Which 7-year Chaldean cycle (1-based) |

**Properties:** `is_cycle_coincidence`, `is_benefic_planet`, `is_malefic_planet`.

#### §3.6 Aggregate Vessel — LordOfOrbAggregate

| Field | Type | Description |
|---|---|---|
| `sequence` | `LordOfOrbSequence` | The complete period sequence |
| `condition_profiles` | `list[LordOfOrbConditionProfile]` | One per year |
| `policy` | `LordOfOrbPolicy` | Policy used |

**Properties:** `benefic_years`, `malefic_years`, `planet_year_counts`,
`cycle_coincidence_years`.

**Methods:** `get_profile(year)`.

---

### §4. Validation Codex

`validate_lord_of_orb_output(aggregate)` checks:

| # | Check |
|---|---|
| 1 | Year 1 planet matches birth_planet |
| 2 | All years are consecutive from 1 |
| 3 | All cycle_kind fields match the aggregate cycle_kind |
| 4 | All houses in [1, 12] |
| 5 | All chaldean_index values in [0, 6] |
| 6 | All chaldean_index values match the planet name |
| 7 | (CONTINUOUS_LOOP) Planet recurs every 7 years |
| 8 | (CONTINUOUS_LOOP) House recurs every 12 years |
| 9 | (SINGLE_CYCLE) Planet for year N == planet for year N+12 |
| 10 | Condition profile count matches period count |
| 11 | All hierarchy_rank values are 6 |
| 12 | (CONTINUOUS_LOOP + Venus + span >= 36) Torres's worked example verified |

---

### §5. Doctrine Boundaries

#### §5.1 What This Module Owns

- Chaldean order arithmetic and both cycle variants
- House signification mapping
- Period, sequence, condition, and aggregate result vessels
- Torres's verification check in the validation codex

#### §5.2 What This Module Does Not Own

- Birth planetary hour calculation (delegated to `moira.planetary_hours`)
- Solar return chart construction
- Annual hierarchy orchestration (Phase 2 — the Lord of the Orb's interaction
  with the Lord of the Year, Fardār lord, and other indicators)
- Natal chart dignity evaluation of the Lord of the Orb planet

#### §5.3 Deferred (Phase 2)

Integration of the Lord of the Orb as indicator #6 in Abu Ma'shar's eight-
indicator annual hierarchy alongside profections (indicator #1) and firdaria
(indicator #5). The hierarchy interface requires a separate doctrinal design
note before implementation.

---

## Part II — Implementation Notes

### §6. Module Location

`moira/lord_of_the_orb.py` — standalone module.

Rationale: keeps the Lord of the Orb distinct from `timelords.py` (which owns
firdaria and zodiacal releasing), from `profections.py` (which owns the Lord
of the Year), and from `planetary_hours.py` (which owns birth hour calculation).
The technique is mathematically self-contained once the birth planet is supplied.

### §7. Relation to planetary_hours.py

The `_CHALDEAN` sequence in `planetary_hours.py` and the `CHALDEAN_ORDER`
constant in this module are equivalent. They are defined independently to avoid
an import dependency on `planetary_hours.py`'s private internals.

The caller connects the two modules: `planetary_hours.planetary_hours(birth_jd,
lat, lon)` → `PlanetaryHoursDay` → `PlanetaryHour.ruler` for the birth hour →
pass as `birth_planet` to `lord_of_orb()`.

---

## Part III — Change Policy

### §8. Stability Guarantees

**Frozen:**
- `CHALDEAN_ORDER` tuple and its index mapping
- `LordOfOrbCycleKind` enum values and semantics
- `LordOfOrbPeriod` field set and invariants
- Torres's verification in the validation codex

**Internal (may change):**
- `_CHALDEAN_INDEX`, `_VALID_PLANETS`
- `_validate_lord_of_orb_inputs`

### §9. Extension Points

To add annual hierarchy integration (Phase 2):

1. Design the eight-indicator hierarchy vessel in a separate doctrinal note
2. Add a `hierarchy_context(aggregate, profection_lord, firdar_lord, ...)`
   function that returns a combined annual assessment
3. Do not modify any existing Phase 1–8 vessels or the primary engine

