# Moira Alternate Dashas Backend Standard

Version: 1.1
Date: 2026-09-27
Status: Current implementation truth; REST admitted

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

BPHS chapter 46, verses 17–22 begin the allocation at Ardra and alternate
groups of four and three counting places:

| Lord | Nakshatras |
|---|---|
| Sun | Ardra, Punarvasu, Pushya, Ashlesha |
| Moon | Magha, Purva Phalguni, Uttara Phalguni |
| Mars | Hasta, Chitra, Swati, Vishakha |
| Mercury | Anuradha, Jyeshtha, Mula |
| Saturn | Purva Ashadha, Uttara Ashadha, Abhijit, Shravana |
| Jupiter | Dhanishtha, Shatabhisha, Purva Bhadrapada |
| Rahu | Uttara Bhadrapada, Revati, Ashwini, Bharani |
| Venus | Krittika, Rohini, Mrigashira |

Each four-place group assigns one quarter of its lord's Mahadasha to each
place; each three-place group assigns one third. The first-period balance
therefore includes complete places already traversed within the current lord's
group as well as the elapsed fraction of the active place.

The BPHS passage requires 28 places but does not state Abhijit's zodiacal
boundaries. Moira names its separate traditional convention explicitly:
Abhijit spans 6°40'–10°53'20" sidereal Capricorn, combining the last quarter
of Uttara Ashadha with the first fifteenth of Shravana. This boundary must not
be attributed to the wording of BPHS 46.17–22.

#### 1.3 Yogini Dasha

A **Yogini sequence** in Moira is:

> A 36-year cycle with eight Yoginis, entered by adding three to the
> one-based birth-nakshatra number and reducing to a one-through-eight
> remainder.

With Moira's zero-based index, the equivalent expression is:

```text
(nakshatra_index + 3) % 8
```

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

For Yogini, the first Mahadasha is shortened by the fraction of the Moon's
birth nakshatra already elapsed. For Ashtottari, the first Mahadasha balance
uses the Moon's progress through the active three- or four-place lord group.

#### 1.5 Source authority and ambiguity policy

The normative computational readings are the Sanskrit verses in *Brihat
Parashara Hora Shastra*, chapter 46:

- verses 17–22 for Ashtottari allocation, lord order, years, and balance;
- verse 23 for an additional Ashtottari applicability statement;
- verses 195–200 for Yogini names, planetary identities, entry rule, years,
  and balance.

Digital Sanskrit witnesses used for collation:

- [SanskritDocuments, BPHS chapters 46–50](https://sanskritdocuments.org/doc_z_misc_sociology_astrology/par4650.html)
- [Sanskrit Wikisource, chapter 46](https://sa.wikisource.org/wiki/बृहत्पाराशरहोराशास्त्रम्/अध्यायः_४६_(दशाध्यायः))

These are edition/transcription witnesses, not an independent manuscript
stemma or modern critical edition. Translation headings and commentary do not
override the Sanskrit computational statements. The exact Abhijit span is a
separately provenance-labelled later convention, historically discussed with
the *Muhurta-Mala* rule in [Burgess and Whitney's notes to the *Surya
Siddhanta*](https://classicalastrologer.com/wp-content/uploads/2018/04/surya_siddhanta_english.pdf).

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
| `bypass_eligibility` | `False` | Explicitly compute without an engine eligibility determination |
| `lagna_sign_index` | `None` | Legacy Ascendant sign input; insufficient by itself for BPHS eligibility |

Current implementation truth:

- BPHS 46.17 describes Rahu in a kendra or trikona from the Lagna lord,
  excluding Lagna; verse 23 additionally names day birth in Krishna Paksha or
  night birth in Shukla Paksha. The current policy does not carry the complete
  Rahu, Lagna-lord, paksha, and day/night context needed to adjudicate these
  statements.
- If `lagna_sign_index` is supplied while `bypass_eligibility=False`, the
  engine raises rather than treating the incomplete legacy field as proof.
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
| `ASHTOTTARI_NAKSHATRA_LORD` | 27-entry ordinary-nakshatra projection of the BPHS mapping; computation separately admits Abhijit |
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
- Sequence entry is determined by the sidereal Moon after applying the policy
  ayanamsa. Ashtottari then applies its 28-place grouping and named Abhijit
  convention; Yogini applies the BPHS add-three/remainder-eight rule.
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
2. All 28 Ashtottari counting places produce the BPHS lord and quarter/third
   first-period balance, including the irregular Abhijit-region segments.
3. All 27 ordinary birth nakshatras produce the Yogini required by the BPHS
   add-three/remainder-eight rule and the correct half-nakshatra midpoint
   balance.
4. The Einstein Jyeshtha fixture starts Mercury Ashtottari and Bhadrika Yogini,
   with fixed expected balances.
5. Ashtottari output spans a 108-year cycle under the selected year basis.
6. Yogini output spans a 36-year cycle under the selected year basis.
7. Periods and sub-periods are chronologically contiguous.
8. Level-2 sub-period spans sum to their parent Mahadasha spans.
9. Year-basis policy changes alter total day span as expected.
10. Vessel invariants reject invalid systems, levels, lords, and time bounds.
11. Policy invariants reject invalid year bases and empty ayanamsa labels.
12. Period profiles preserve system, lord, derived planet, duration, and
    node/luminary flags.
13. Sequence profiles preserve total-year and Mahadasha-count truth.
14. `validate_alternate_dasha_output(...)` accepts valid sequences and catches
    invalid lord or gap/overlap structures.
15. Public exports remain visible through `moira`, `moira.vedic`, and
    `moira.facade`.

### 8. Validation Commands

The minimum verification slice for this standard is:

```powershell
.\.venv\Scripts\python.exe -m py_compile moira\dasha_systems.py tests\unit\test_dasha_systems.py
.\.venv\Scripts\python.exe -m pytest tests\unit\test_dasha_systems.py tests\unit\test_public_doctrine_surfaces.py -q
.\.venv\Scripts\python.exe -m pytest tests\unit\test_api_surface_adversarial_audit.py -q
```

---

## Part III - REST Surface

The admitted REST surface provides both direct-computation and chart-backed
sequence/profile routes for Ashtottari and Yogini, plus period-profile
projection.

Direct-computation routes accept:

- caller-supplied natal Moon tropical longitude
- caller-supplied natal Julian Day
- explicit policy object
- Ashtottari sequence route
- Yogini sequence route
- period-profile route
- sequence-profile route

Chart-backed routes derive the tropical Moon longitude and natal Julian Day
through the server's sidereal chart context and return that provenance with
the result.

Ashtottari REST admission must preserve the current eligibility truth: the
complete BPHS 46.17 and 46.23 applicability context is not represented, so the
transport should either require `bypass_eligibility=True` or expose the current
engine rejection for `lagna_sign_index` without bypass.
