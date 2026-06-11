# Moira Alternate Dashas Backend Standard

Version: 1.0
Date: 2026-06-11
Status: Current implementation truth; P9-10 REST admission prerequisite

## Governing Principle

The Moira alternate-dasha backend is a Vedic time-lord subsystem for
non-Vimshottari dasha systems currently implemented in `moira/dasha_systems.py`.
It preserves Ashtottari and Yogini sequence truth, year-basis policy, ayanamsa
policy, nested sub-period arithmetic, local period profiles, and sequence
profiles.

This document reflects current implementation truth. It does not expand the
engine beyond Ashtottari and Yogini, and it does not claim that Kalachakra,
Chara Dasha, or other alternate systems are implemented.

---

## Part I - Architecture Standard

### 1. Authoritative Computational Definitions

#### 1.1 Alternate dasha period

An **alternate dasha period** in Moira is:

> One time interval in an implemented non-Vimshottari dasha sequence.

| Field | Meaning |
|---|---|
| `system` | `ashtottari` or `yogini` |
| `level` | 1-based hierarchy level; `1` is Mahadasha |
| `lord` | Ashtottari planetary lord or Yogini name |
| `start_jd` | Julian Day when the period begins |
| `end_jd` | Julian Day when the period ends |
| `sub` | Nested sub-periods, when requested |

#### 1.2 Ashtottari Dasha

An **Ashtottari sequence** in Moira is:

> A 108-year cycle with eight lords, entered by the Moon's birth nakshatra.

The current lord sequence is:

```text
Sun, Moon, Mars, Mercury, Saturn, Jupiter, Rahu, Venus
```

The current year allocations sum to `108`:

| Lord | Years |
|---|---:|
| Sun | 6 |
| Moon | 15 |
| Mars | 8 |
| Mercury | 17 |
| Saturn | 10 |
| Jupiter | 19 |
| Rahu | 12 |
| Venus | 21 |

The nakshatra-to-lord mapping cycles those eight lords across the 27
nakshatras, beginning with Ashwini as Sun.

#### 1.3 Yogini Dasha

A **Yogini sequence** in Moira is:

> A 36-year cycle with eight Yoginis, entered by `nakshatra_index % 8`.

The current Yogini sequence is:

```text
Mangala, Pingala, Dhanya, Bhramari, Bhadrika, Ulka, Siddha, Sankata
```

The current year allocations sum to `36`:

| Yogini | Years | Planet |
|---|---:|---|
| Mangala | 1 | Moon |
| Pingala | 2 | Sun |
| Dhanya | 3 | Jupiter |
| Bhramari | 4 | Mars |
| Bhadrika | 5 | Mercury |
| Ulka | 6 | Saturn |
| Siddha | 7 | Venus |
| Sankata | 8 | Rahu |

#### 1.4 Sub-period arithmetic

Both implemented systems use proportional subdivision:

```text
sub_years = (sub_lord_years / system_total_years) * parent_period_years
```

The first Mahadasha is shortened by the fraction of the Moon's birth nakshatra
already elapsed.

---

### 2. Layer Structure

The backend is organized around the current constitutional phases declared in
`moira/dasha_systems.py`:

```text
P1  - Truth preservation             (AlternateDashaPeriod)
P2  - Classification constants       (AlternateDashaSystem)
P3  - Inspectability                 (years, is_terminal)
P4  - Policy surface                 (AshtottariPolicy, YoginiPolicy)
P7  - Local condition profile        (AlternatePeriodProfile)
P8  - Aggregate sequence profile     (AlternateDashaSequenceProfile)
P10 - Hardening                      (__post_init__ guards, validate_alternate_dasha_output)
P12 - Public API curation            (__all__, root/vedic/facade exports)
```

Layer boundary rules:

- `ashtottari(...)` and `yogini_dasha(...)` consume the natal Moon's tropical
  longitude and natal Julian Day.
- The module applies the policy ayanamsa to determine the Moon's sidereal
  nakshatra entry point.
- The module does not compute the natal Moon longitude from a chart datetime.
- Profile builders consume existing `AlternateDashaPeriod` vessels.
- The sequence profile consumes Mahadasha-level periods and does not recompute
  the sequence from ad hoc fields.

---

### 3. Doctrine and Policy Surface

`AshtottariPolicy` currently exposes:

| Field | Default | Meaning |
|---|---|---|
| `year_basis` | `julian_365.25` | Year-length convention |
| `ayanamsa_system` | `Lahiri` | Ayanamsa used for Moon nakshatra conversion |
| `bypass_eligibility` | `False` | Skip Ashtottari eligibility check |
| `lagna_sign_index` | `None` | Ascendant sign index for future eligibility doctrine |

Current implementation truth:

- If `lagna_sign_index` is supplied while `bypass_eligibility=False`, the
  engine raises because full Rahu/Lagna eligibility checking is not yet
  implemented.
- REST transport must therefore either require `bypass_eligibility=True` for
  first admission or expose the engine's current rejection honestly.

`YoginiPolicy` currently exposes:

| Field | Default | Meaning |
|---|---|---|
| `year_basis` | `julian_365.25` | Year-length convention |
| `ayanamsa_system` | `Lahiri` | Ayanamsa used for Moon nakshatra conversion |

Supported year bases:

- `julian_365.25`
- `savana_360`
- `tropical_365.2422`
- `sidereal_365.2564`

---

### 4. Public Surface

All public names are declared in `moira/dasha_systems.py`.

#### Constants and registries

| Name | Meaning |
|---|---|
| `AlternateDashaSystem` | Supported system labels |
| `ASHTOTTARI_YEARS` | Ashtottari lord-year table |
| `ASHTOTTARI_SEQUENCE` | Ashtottari lord order |
| `ASHTOTTARI_NAKSHATRA_LORD` | 27-entry nakshatra-to-lord mapping |
| `ASHTOTTARI_TOTAL` | Ashtottari total cycle years |
| `YOGINI_YEARS` | Yogini year table |
| `YOGINI_SEQUENCE` | Yogini order |
| `YOGINI_PLANETS` | Yogini-to-planet mapping |
| `YOGINI_TOTAL` | Yogini total cycle years |

#### Frozen dataclass vessels

| Vessel | Primary fields |
|---|---|
| `AlternateDashaPeriod` | system, level, lord, start/end JD, sub-periods |
| `AshtottariPolicy` | year basis, ayanamsa, eligibility flags |
| `YoginiPolicy` | year basis, ayanamsa |
| `AlternatePeriodProfile` | system, lord, planet, duration, node/luminary flags |
| `AlternateDashaSequenceProfile` | system, total years, Mahadasha count, profiles |

#### Computation functions

| Function | Signature | Meaning |
|---|---|---|
| `ashtottari` | `(moon_tropical_lon, natal_jd, levels=2, policy=None) -> list[AlternateDashaPeriod]` | Compute Ashtottari periods |
| `yogini_dasha` | `(moon_tropical_lon, natal_jd, levels=2, policy=None) -> list[AlternateDashaPeriod]` | Compute Yogini periods |
| `alternate_period_profile` | `(period) -> AlternatePeriodProfile` | Build local period profile |
| `alternate_sequence_profile` | `(periods) -> AlternateDashaSequenceProfile` | Build sequence profile |
| `validate_alternate_dasha_output` | `(periods) -> None` | Validate Mahadasha-level output |

---

### 5. Determinism and Failure Doctrine

#### 5.1 Determinism

- System labels are fixed: `ashtottari` and `yogini`.
- Levels are clamped by the engine to `[1, 4]`.
- Sequence entry is determined by the sidereal Moon's nakshatra after applying
  the policy ayanamsa.
- Periods are emitted chronologically.
- Nested sub-periods preserve proportional duration within the parent period.
- Profile functions are pure projections over period vessels.

#### 5.2 Failure doctrine

The subsystem fails loudly on:

- invalid `AlternateDashaPeriod.system`
- non-positive levels on period vessel construction
- empty period lord names
- non-finite period boundaries
- `start_jd >= end_jd`
- invalid year-basis policy values
- empty ayanamsa labels
- non-finite natal JD inputs
- empty sequence-profile input
- invalid output sequence structure in `validate_alternate_dasha_output`
- current Ashtottari eligibility requests that provide `lagna_sign_index`
  without bypassing eligibility

---

## Part II - Validation Codex

### 6. Validation Scope

The alternate-dasha backend is currently validated through:

- `tests/unit/test_dasha_systems.py`
- public API surface checks in `tests/unit/test_api_surface_adversarial_audit.py`
- public doctrine surface checks in `tests/unit/test_public_doctrine_surfaces.py`

### 7. Validation Claims

The following claims are currently verified:

1. Ashtottari and Yogini year tables sum to their canonical totals.
2. Sequence lengths, uniqueness, and Yogini planet mappings are coherent.
3. Ashtottari output spans a 108-year cycle under the selected year basis.
4. Yogini output spans a 36-year cycle under the selected year basis.
5. Periods and sub-periods are chronologically contiguous.
6. Level-2 sub-period spans sum to their parent Mahadasha spans.
7. Year-basis policy changes alter total day span as expected.
8. Vessel invariants reject invalid systems, levels, lords, and time bounds.
9. Policy invariants reject invalid year bases and empty ayanamsa labels.
10. Period profiles preserve system, lord, derived planet, duration, and
    node/luminary flags.
11. Sequence profiles preserve total-year and Mahadasha-count truth.
12. `validate_alternate_dasha_output(...)` accepts valid sequences and catches
    invalid lord or gap/overlap structures.
13. Public exports remain visible through `moira`, `moira.vedic`, and
    `moira.facade`.

### 8. Validation Commands

The minimum verification slice for this standard is:

```powershell
.\.venv\Scripts\python.exe -m py_compile moira\dasha_systems.py tests\unit\test_dasha_systems.py
.\.venv\Scripts\python.exe -m pytest tests\unit\test_dasha_systems.py tests\unit\test_public_doctrine_surfaces.py -q
.\.venv\Scripts\python.exe -m pytest tests\unit\test_api_surface_adversarial_audit.py -q
```

---

## Part III - REST Admission Frontier

P9-10 may proceed to REST transport design after this standard.

First admitted REST shape should be direct computation:

- caller-supplied natal Moon tropical longitude
- caller-supplied natal Julian Day
- explicit policy object
- Ashtottari sequence route
- Yogini sequence route
- period-profile route
- sequence-profile route

Chart-backed convenience routes should be deferred until the server adapter
explicitly owns natal Moon derivation and policy provenance for the birth chart.

Ashtottari REST admission must preserve the current eligibility truth: full
Rahu/Lagna eligibility checking is not implemented, so first admission should
either require `bypass_eligibility=True` or expose the current engine rejection
for `lagna_sign_index` without bypass.
