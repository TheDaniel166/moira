# Lord of the Orb Roadmap

## Purpose

This document defines the implementation roadmap for Moira's Lord of the Orb
subsystem.

It assumes the companion doctrine document exists:

- [lord_of_the_orb_doctrine.md](lord_of_the_orb_doctrine.md)

This is an **additive roadmap**. The Lord of the Orb is a new technique with
no existing implementation in Moira. The required infrastructure (planetary
hours, Chaldean order) already exists in `moira/planetary_hours.py`.

The technique belongs to the annual timing family alongside profections and
firdaria. Its output is an annual participating signifier within a solar
return analysis.


## Current Moira State

Relevant implementation files:

- `moira/planetary_hours.py` — planetary hour calculation; Chaldean order
- `moira/timelords.py` — firdaria and zodiacal releasing; annual period model
- `moira/profections.py` — annual profections; Lord of the Year

Lord of the Orb: `NOT IMPLEMENTED`.

Infrastructure available:

- `PlanetaryHour` and `PlanetaryHoursDay` in `planetary_hours.py` — the birth
  planetary hour is computable from these
- Chaldean order already encoded in `planetary_hours.py`
- Annual period vessel patterns established in `timelords.py`

Current SCP status: `P0` — pre-constitutionalization.


## Core Insight

The Lord of the Orb is a two-cycle system: the 7-planet Chaldean sequence and
the 12-house sequence advance independently. The only doctrinal ambiguity is
whether the Chaldean sequence resets with the house cycle (single cycle) or
runs as a fully independent modular counter (continuous loop).

The continuous loop variant is the better-attested reading (Torres, Giuntini).
Both variants should be implemented as named options.

The birth planetary hour is the only natal input beyond the chart itself.
Everything else is arithmetic.


## Truth Domain Axes

### 1. Cycle Variant

Governs how the Chaldean planetary sequence and the 12-house sequence relate.

Values:

- `continuous_loop` — planetary sequence and house cycle are independent modular
  counters; full combined pattern repeats at LCM(7, 12) = 84 years; **default**
- `single_cycle` — both cycles reset together at year 13; Year 13 planet
  equals Year 1 planet; historically ambiguous in Abu Ma'shar

### 2. Night Definition

The birth planetary hour requires knowing whether the birth is diurnal or
nocturnal. This is already handled by `planetary_hours.py` (sunrise/sunset
aware). No new logic needed.

### 3. House Signification

Year N → house ((N − 1) mod 12) + 1

This is a pure arithmetic mapping, not a house-system calculation.


## Implementation Phases

### Phase 1 — Core Lord of the Orb Engine

**Scope:** compute the Lord of the Orb for any year of life from a natal chart.

**Module:** `moira/timelords.py` (alongside firdaria and profections as the
natural home for annual time-lord techniques)

**Tasks:**

1. Add `LordOfOrbCycleKind` enum: `CONTINUOUS_LOOP`, `SINGLE_CYCLE`
2. Add `LordOfOrbPeriod` data vessel:
   - `year: int`
   - `planet: str`
   - `house: int`
   - `cycle_kind: LordOfOrbCycleKind`
3. Add `lord_of_orb(chart, birth_planetary_hour_planet, years, cycle_kind)`
   function returning `list[LordOfOrbPeriod]`
4. Add `current_lord_of_orb(chart, birth_date, target_date, cycle_kind)`
   convenience function returning the active `LordOfOrbPeriod`
5. Expose the birth planetary hour planet as a named output so callers can
   verify it

**Cycle logic:**

```
# continuous_loop
planet_index = (birth_planet_index + year - 1) % 7
house = ((year - 1) % 12) + 1

# single_cycle
cycle_position = (year - 1) % 12   # 0–11
planet_index = (birth_planet_index + cycle_position) % 7
house = cycle_position + 1
```

Where `birth_planet_index` is the 0-based position of the birth-hour planet
in the Chaldean order: Saturn(0), Jupiter(1), Mars(2), Sun(3), Venus(4),
Mercury(5), Moon(6).

**Acceptance criteria:**

- for Venus as birth-hour planet, years 1, 8, 15, 22, 29, 36 all return
  Venus (continuous loop) — confirms Torres's worked example
- year 1 → house 1, year 12 → house 12, year 13 → house 1 (both variants)
- year 13 → Venus (continuous loop) vs. Venus (single cycle coincides here;
  divergence begins at year 14 where continuous returns Mercury, single
  returns Jupiter)
- full 84-year cycle produces no duplicates (continuous loop)

**SCP target:** P1 COMPLETE after this phase.

---

### Phase 2 — Annual Hierarchy Integration

**Scope:** integrate Lord of the Orb as a named indicator within Moira's
annual solar return analysis.

**Prerequisite:** Phase 1 complete.

**Tasks:**

1. Define the Abu Ma'shar eight-indicator annual hierarchy as a named
   structure (if not already done by profections or other annual work)
2. Add Lord of the Orb as indicator #6 in the hierarchy
3. Add evaluation frame: expose the Lord of the Orb planet's natal condition
   and its solar return position for interpretation

**Note:** the annual hierarchy is a documentary and output-structuring task,
not a computation task. The computation is fully covered by Phase 1.

**SCP target:** P2 COMPLETE after this phase.


## Relationship to Other Subsystems

| Subsystem | Relationship |
|---|---|
| `planetary_hours.py` | provides birth-hour planet; shared Chaldean order |
| `timelords.py` | natural home; same annual period model as firdaria |
| `profections.py` | Lord of the Year is indicator #1 in the same hierarchy |
| Lord of the Turn | separate technique; shares naming hazard only |

The Lord of the Orb does not depend on solar return chart calculation. It
depends only on the birth planetary hour and the native's age.


## Open Questions

1. Should `lord_of_orb()` live in `timelords.py` or in a new
   `annual_indicators.py` module? Decision deferred to SCP Phase 3 (module
   boundary formalization).
2. Should both cycle variants always be computed and returned, or should the
   caller specify one? Recommendation: caller specifies; default to
   `CONTINUOUS_LOOP`.


## Research Sources

- Benjamin N. Dykes, *Persian Nativities IV* (Cazimi Press, 2019) — Abu
  Ma'shar's core; pages 126–128 for cycle variant ambiguity
- Anthony Louis, "Lord of the Orb in Annual Revolutions" (blog, 2021) —
  Torres manuscript; Venus worked example confirming continuous loop
- `moira/planetary_hours.py` — Chaldean order and birth-hour infrastructure
