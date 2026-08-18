# Moira 6.3.0 - Hellenistic Computation Deepening

**Release date:** 2026-08-18

**Public upgrade path:** 6.2.2 to 6.3.0.

Moira 6.3.0 is a Hellenistic *computation* minor. Ancient arithmetic stays
the default. Revival display is an explicit named policy. The unified
profile method remains `moira.hellenistic_chart_profile.v2`. The four
foundational lots and the singular `zodiacal_releasing` object do not
move. Valid 6.2.2 `POST /v1/hellenistic/chart-profile` requests keep
working.

## In this release

- **Natal twelfth-parts** — ordinary 12× / 2°30′ dodekatemorion
  (`twelfth_part_of`). Not Vedic Dwadashamsa and not Sahl/Dorotheus
  electional clauses.
- **Assemble-condition** — score-free testimony, tenth-sign overcoming,
  malefic enclosure, and applying/exact adherence. Aktinobolia is
  `not_evaluable` / `doctrine_not_admitted`.
- **Supporting lots** — sect-selected Exaltation and Basis (Valens)
  outside `HELLENISTIC_PROFILE_LOTS`.
- **ZR revival display** — omitted `levels` is now **2** (L1/L2). Explicit
  3 or 4 still compute. Three-grade peak projection sits beside
  `is_peak_period`. Dual ZR is an opt-in Fortune companion.
- **Optional profile overlays** — `revival` and `overlays` on the v2
  policy, all default off. Sign-per-month is a named sibling; civil
  twelfths stay dated authority.
- **Circumambulations** — caller-named significator through Egyptian
  bounds. Only admitted year key: bound-lord minor years. Rising-time
  and equatorial/PD keys fail closed.
- **Transmissions** — from→to graph from profection, Decennials, ZR, and
  natal place. No effect prose.
- **Offices** — candidate hunt only. Predominator and house-master stay
  unselected. Does not call `find_hyleg` or `calculate_longevity`.

## REST contracts

```text
POST /v1/hellenistic/twelfth-parts
POST /v1/hellenistic/condition
POST /v1/hellenistic/circumambulations
POST /v1/hellenistic/transmissions
POST /v1/hellenistic/offices
```

`POST /v1/hellenistic/chart-profile` is unchanged as a required contract.
New policy fields have defaults. Extra request keys remain 422.

## Not in 6.3.0

- Profile method `v3`, a fifth profile lot, or required dual ZR
- Hermetic geometry or product transport
- Decennial L3/L4 as admitted doctrine
- Firdaria inside the Hellenistic profile
- Valens interpretive effect tables
- Triacontaeteris
- Bonatti hyleg as predominator
- Unscoped primary directions as aphesis
- Chart-wide scores or narrative
- Website or Urania Workspace surfaces

Admission packets live under
`wiki/01_doctrines/hellenistic_6_3/`. The operational pointer is
`wiki/06_roadmap/hellenistic_completion/HELLENISTIC_6_3_0_ADMISSION_PROGRAM.md`.

## Install

```text
pip install moira-astro==6.3.0
```

```python
from moira import twelfth_part_of, assemble_hellenistic_condition
from moira import HellenisticProfilePolicy, HellenisticRevivalPolicy
from moira import circumambulate, valens_transmission_graph, hunt_hellenistic_offices
```

Read `COMPATIBILITY_NOTES_6.3.0.md` before regenerating OpenAPI clients
or assuming omitted ZR `levels` still means 4.
