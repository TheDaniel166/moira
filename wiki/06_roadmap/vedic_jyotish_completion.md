# Vedic Jyotish Systems — Pre-Phase 1 Implementation Roadmap

## Codebase State (Verified)

Present and usable:
- `moira/sidereal.py` — `tropical_to_sidereal`, `nakshatra_of`, `Ayanamsa`, `NAKSHATRA_LORDS`
- `moira/varga.py` — `calculate_varga`, wrappers for D7, D9, D10, D12, D30 only
- `moira/dasha.py` — Vimshottari only; no alternative systems
- `moira/decanates.py` — D3 via `vedic_drekkana()`
- `moira/dignities.py` — Western only; nothing Vedic
- `moira/cycles.py` — `_jd_to_weekday()`, `planetary_day_ruler()` available
- `moira/chart.py` — `ChartContext.planets`, `.nodes`, `.houses`, `.jd_ut`, `.is_day`

None of the 7 target systems exist in any form.

---

## Implementation Sequence (Dependency Order)

```
1. Shodashvarga Completion (varga.py extension)   — no upstream deps
2. Vedic Planetary Dignities (new module)          — no upstream deps
3. Jaimini Karakas (new module)                    — sidereal.py only
4. Panchanga (new module)                          — sidereal.py, cycles.py
5. Alternative Dasha Systems (new module)          — sidereal.py, dasha.py patterns
6. Ashtakavarga (new module)                       — vedic_dignities.py (for Shodhana)
7. Shadbala (new module)                           — all of the above
```

Rationale: Shadbala is the most downstream — Saptavargaja Bala requires all 7 varga sign positions, Kala Bala requires Panchanga elements (Vara, Paksha, Hora), and Drig Bala optionally uses Ashtakavarga scores. Everything else is self-contained.

---

## System 1 — Shodashvarga Completion

### Primary Authority
Parashara, *Brihat Parashara Hora Shastra*, Shodashavarga Adhyaya (Ch. 6–22).

### Validation Reference
Jhora (Jagannatha Hora), Parashara Light 9.x; B.V. Raman, *How to Judge a Horoscope*.

### File
Extend `moira/varga.py`.

### Missing Wrappers
D2, D4, D6, D8, D16, D20, D24, D27, D40, D45, D60.

### Non-Generic Parashari Rules

| Varga | Rule |
|---|---|
| **D2 Hora** | Odd signs: 1st half (0°–15°) → Leo, 2nd half → Cancer. Even signs reversed. |
| **D4 Chaturthamsha** | `d4_sign = (sign_idx + segment_in_sign) % 12` — starts from own sign, not Aries. |
| **D27 Saptavimshamsha** | Start from Aries (fire), Cancer (earth), Libra (air), Capricorn (water). |
| **D40 Khavedamsha** | Odd signs start Aries; even signs start Libra. |
| **D45 Akshavedamsha** | Odd signs start Aries; even signs start Capricorn. |

Remaining (D6, D8, D16, D20, D24, D60): generic `calculate_varga(lon, n)`.

> **Critical**: The existing `calculate_varga(lon, 4)` does not match Parashari D4. The `chaturthamsha()` wrapper must use the sign-offset formula, not the generic call.

### Key Formulas

```python
# D2 Hora
sign_idx = int(sidereal_lon // 30)
deg_in_sign = sidereal_lon % 30
half = 0 if deg_in_sign < 15 else 1
is_odd_sign = (sign_idx % 2 == 0)   # 0-based: Aries=0 is 1st (odd) sign
if is_odd_sign:
    hora_sign = 4 if half == 0 else 3    # Leo(4) or Cancer(3)
else:
    hora_sign = 3 if half == 0 else 4    # Cancer(3) or Leo(4)

# D4 Chaturthamsha
segment_within_sign = int((sidereal_lon % 30) / 7.5)   # 0–3
d4_sign = (sign_idx + segment_within_sign) % 12

# D27 Saptavimshamsha
TRIPLICITY_START = {"fire": 0, "earth": 3, "air": 6, "water": 9}
SIGN_ELEMENT = ["fire","earth","air","water"] * 3   # Aries→Pisces
start = TRIPLICITY_START[SIGN_ELEMENT[sign_idx]]
segment = int((sidereal_lon % 30) / (30/27))
d27_sign = (start + segment) % 12

# D40 Khavedamsha
seg_40 = int((sidereal_lon % 30) / 0.75)
start_40 = 0 if (sign_idx % 2 == 0) else 6      # Aries or Libra
d40_sign = (start_40 + seg_40) % 12

# D45 Akshavedamsha
seg_45 = int((sidereal_lon % 30) / (30/45))
start_45 = 0 if (sign_idx % 2 == 0) else 9      # Aries or Capricorn
d45_sign = (start_45 + seg_45) % 12
```

### Proposed Public Surface (additions to varga.py)

```python
def hora(sidereal_longitude: float) -> VargaPoint: ...             # D2
def chaturthamsha(sidereal_longitude: float) -> VargaPoint: ...    # D4
def shashthamsha(sidereal_longitude: float) -> VargaPoint: ...     # D6
def ashtamsha(sidereal_longitude: float) -> VargaPoint: ...        # D8
def shodashamsha(sidereal_longitude: float) -> VargaPoint: ...     # D16
def vimshamsha(sidereal_longitude: float) -> VargaPoint: ...       # D20
def chaturvimshamsha(sidereal_longitude: float) -> VargaPoint: ... # D24
def saptavimshamsha(sidereal_longitude: float) -> VargaPoint: ...  # D27
def khavedamsha(sidereal_longitude: float) -> VargaPoint: ...      # D40
def akshavedamsha(sidereal_longitude: float) -> VargaPoint: ...    # D45
def shashtiamsha(sidereal_longitude: float) -> VargaPoint: ...     # D60
```

### Tricky Edge Cases
- `sign_idx % 2 == 0` means "odd sign" in 0-based indexing (Aries=0 is the 1st, which is odd). This is counterintuitive — document clearly.
- D60 sign assignment is generic; the optional named Shashtiamsha lords (60 traditional names from BPHS) are future enrichment.
- Use `int(lon % 30 // (30/n))` not rounding at segment boundaries.

### Estimated Complexity
Moderate. Most wrappers are trivial; D2/D4/D27/D40/D45 require careful offset arithmetic and Jhora spot-checks.

---

## System 2 — Vedic Planetary Dignities

### Primary Authority
Parashara, *BPHS* Ch. 3, 26, 28. Kalyana Varma, *Saravali* Ch. 5–6.

### Validation Reference
Jhora (dignity display + Panchadha Maitri grid); Raman, *A Manual of Hindu Astrology*.

### File
`moira/vedic_dignities.py`

### Exaltation and Debilitation

| Planet | Exaltation | Deepest degree | Debilitation |
|---|---|---|---|
| Sun | Aries | 10° | Libra |
| Moon | Taurus | 3° | Scorpio |
| Mars | Capricorn | 28° | Cancer |
| Mercury | Virgo | 15° | Pisces |
| Jupiter | Cancer | 5° | Capricorn |
| Venus | Pisces | 27° | Virgo |
| Saturn | Libra | 20° | Aries |

### Mulatrikona Ranges

| Planet | Sign | Range |
|---|---|---|
| Sun | Leo | 0°–20° |
| Moon | Taurus | 3°–30° |
| Mars | Aries | 0°–12° |
| Mercury | Virgo | 15°–20° |
| Jupiter | Sagittarius | 0°–10° |
| Venus | Libra | 0°–15° |
| Saturn | Aquarius | 0°–20° |

### Dignity Rank Order
Exaltation > Mulatrikona > Swakshetra > Friend's sign > Neutral's sign > Enemy's sign > Debilitation

### Natural Friendship (Naisargika Maitri — BPHS Ch. 3)

| Planet | Friends | Neutral | Enemies |
|---|---|---|---|
| Sun | Moon, Mars, Jupiter | Mercury | Venus, Saturn |
| Moon | Sun, Mercury | Mars, Jupiter, Venus, Saturn | — |
| Mars | Sun, Moon, Jupiter | Venus, Saturn | Mercury |
| Mercury | Sun, Venus | Mars, Jupiter, Saturn | Moon |
| Jupiter | Sun, Moon, Mars | Saturn | Mercury, Venus |
| Venus | Mercury, Saturn | Mars, Jupiter, Moon | Sun |
| Saturn | Mercury, Venus | Jupiter | Sun, Moon, Mars |

### Temporary Friendship Formula
`distance = (sign_B - sign_A) % 12`
- Distances {1,2,3,9,10,11}: temporary friend
- Distances {0,4,5,6,7,8}: temporary enemy
- Distance 0 (self): excluded

### Panchadha Maitri (Compound Relationship)

| Natural + Temporary | Compound |
|---|---|
| Friend + Friend | Adhi Mitra (Great Friend) |
| Friend + Enemy | Sama (Neutral) |
| Neutral + Friend | Mitra (Friend) |
| Neutral + Enemy | Shatru (Enemy) |
| Enemy + Friend | Sama (Neutral) |
| Enemy + Enemy | Adhi Shatru (Great Enemy) |

### Proposed Public Surface

```python
EXALTATION_SIGN: dict[str, int]
EXALTATION_DEGREE: dict[str, float]
DEBILITATION_SIGN: dict[str, int]
MULATRIKONA_SIGN: dict[str, int]
MULATRIKONA_START: dict[str, float]
MULATRIKONA_END: dict[str, float]
OWN_SIGNS: dict[str, list[int]]
NATURAL_FRIENDS: dict[str, set[str]]
NATURAL_NEUTRALS: dict[str, set[str]]
NATURAL_ENEMIES: dict[str, set[str]]

class VedicDignityRank:
    EXALTATION   = "exaltation"
    MULATRIKONA  = "mulatrikona"
    OWN_SIGN     = "own_sign"
    FRIEND_SIGN  = "friend_sign"
    NEUTRAL_SIGN = "neutral_sign"
    ENEMY_SIGN   = "enemy_sign"
    DEBILITATION = "debilitation"

class CompoundRelationship:
    GREAT_FRIEND = "adhi_mitra"
    FRIEND       = "mitra"
    NEUTRAL      = "sama"
    ENEMY        = "shatru"
    GREAT_ENEMY  = "adhi_shatru"

@dataclass(frozen=True, slots=True)
class VedicDignityResult:
    planet: str
    sidereal_longitude: float
    sign_index: int
    sign: str
    dignity_rank: str
    is_exalted: bool
    is_debilitated: bool
    is_mulatrikona: bool
    is_own_sign: bool
    exaltation_score: float  # 0.0 at debilitation, 1.0 at deepest exaltation

@dataclass(frozen=True, slots=True)
class PlanetaryRelationship:
    from_planet: str
    to_planet: str
    natural: str    # "friend" / "neutral" / "enemy"
    temporary: str  # "friend" / "enemy"
    compound: str   # CompoundRelationship constant

def vedic_dignity(
    planet: str,
    sidereal_longitude: float,
) -> VedicDignityResult: ...

def planetary_relationships(
    sidereal_longitudes: dict[str, float],
) -> list[PlanetaryRelationship]: ...
```

### Tricky Edge Cases
- Mercury at Virgo 15° is at deepest exaltation AND at the start of its Mulatrikona range. Check exaltation before Mulatrikona in the cascade.
- Moon's Mulatrikona: Parashara gives 3°–30°; some commentators give 4°–30°. Use 3° (primary source), document variant.
- Scope: 7 classical planets only. Rahu and Ketu are not subjects of this system.

### Estimated Complexity
Moderate.

---

## System 3 — Jaimini Karakas

### Primary Authority
Jaimini, *Jaimini Sutras*, Adhyaya 1, Pada 1, Sutras 1–14.

### Validation Reference
Jhora (7/8-karaka mode); Sanjay Rath, *Jaimini Maharishi's Upadesa Sutras* (2002).

### File
`moira/jaimini.py`

### Core Algorithm

```python
# 7-karaka scheme
planets_7 = ["Sun", "Moon", "Mars", "Mercury", "Jupiter", "Venus", "Saturn"]
degrees = {p: sidereal_lon[p] % 30.0 for p in planets_7}
sorted_planets = sorted(planets_7, key=lambda p: degrees[p], reverse=True)
# sorted_planets[0] = Atmakaraka, [1] = Amatyakaraka, ..., [6] = Darakaraka
```

**Rahu** (8-karaka scheme only): `degree_in_sign = 30 - (rahu_sidereal_lon % 30)` — inverted because Rahu moves retrograde.

### Karaka Sequences

| Rank | 7-karaka | 8-karaka |
|---|---|---|
| 1 | Atmakaraka (AK) | Atmakaraka (AK) |
| 2 | Amatyakaraka (AmK) | Amatyakaraka (AmK) |
| 3 | Bhratrikaraka (BK) | Bhratrikaraka (BK) |
| 4 | Matrikaraka (MaK) | Matrikaraka (MaK) |
| 5 | Pitrikaraka (PiK) | Pitrikaraka (PiK) |
| 6 | Gnatikaraka (GK) | Putrakaraka (PuK) |
| 7 | Darakaraka (DK) | Gnatikaraka (GK) |
| 8 | — | Darakaraka (DK) |

### Proposed Public Surface

```python
KARAKA_NAMES_7: list[str]
KARAKA_NAMES_8: list[str]

@dataclass(frozen=True, slots=True)
class KarakaAssignment:
    karaka_name: str
    karaka_rank: int            # 1-based
    planet: str
    degree_in_sign: float       # effective degree used for sorting
    sidereal_longitude: float
    is_rahu_inverted: bool

@dataclass(frozen=True, slots=True)
class JaiminiKarakaResult:
    assignments: list[KarakaAssignment]
    scheme: int                              # 7 or 8
    atmakaraka: str                          # convenience accessor
    tie_warnings: list[tuple[str, str]]      # planet pairs with equal degrees

def jaimini_karakas(
    sidereal_longitudes: dict[str, float],
    scheme: int = 7,
) -> JaiminiKarakaResult: ...

def atmakaraka(
    sidereal_longitudes: dict[str, float],
    scheme: int = 7,
) -> str: ...
```

### Tricky Edge Cases
- Ketu is always excluded, even in the 8-karaka scheme. Only Rahu is the 8th candidate.
- Ties: astronomically rare, but expose a `tie_warning` and apply a deterministic tiebreaker (document as indeterminate).
- Atmakaraka at 29°59': valid edge case — no special handling needed, `% 30` arithmetic handles it correctly.

### Estimated Complexity
Simple. Core is a single sort with one special case (Rahu inversion).

---

## System 4 — Panchanga

### Primary Authority
Parashara, *BPHS* (Muhurta chapters). Varahamihira, *Brihat Samhita* Ch. 98–104.

### Validation Reference
Jhora, Kala software.

### File
`moira/panchanga.py`

### Five Elements

| Element | Formula | Span |
|---|---|---|
| **Tithi** | `int((moon_sid - sun_sid) % 360 / 12) + 1` | 12° each, 30 total |
| **Vara** | `int(jd + 1.5) % 7` → Sun, Moon, Mars, Mercury, Jupiter, Venus, Saturn | 1 day |
| **Nakshatra** | delegate to `sidereal.nakshatra_of(moon_tropical_lon, jd)` | 13.33° each |
| **Yoga** | `int((sun_sid + moon_sid) % 360 / (360/27)) + 1` | 13.33° each, 27 total |
| **Karana** | half-Tithi (`int(diff / 6)`); 60 per month | 6° each |

**Karana mapping**: position 0 = Kimstughna (fixed); positions 1–56 cycle 7 movable Karanas; positions 57–59 = Shakuni, Chatushpada, Naga (fixed).

Each element should return `degrees_elapsed` and `degrees_remaining` to enable muhurta "time until next X" calculations.

### Proposed Public Surface

```python
TITHI_NAMES: list[str]     # 30 names: Pratipada … Amavasya
YOGA_NAMES: list[str]      # 27 names: Vishkumbha … Vaidhriti
KARANA_NAMES: list[str]    # 11 names
VARA_LORDS: list[str]      # 7 lords, Sunday-origin

@dataclass(frozen=True, slots=True)
class PanchangaElement:
    name: str
    index: int              # 0-based
    number: int             # 1-based
    degrees_elapsed: float
    degrees_remaining: float

@dataclass(frozen=True, slots=True)
class PanchangaResult:
    jd: float
    tithi: PanchangaElement
    vara: PanchangaElement
    vara_lord: str
    nakshatra: NakshatraPosition    # from sidereal.nakshatra_of
    yoga: PanchangaElement
    karana: PanchangaElement
    ayanamsa_system: str

def panchanga_at(
    sun_tropical_lon: float,
    moon_tropical_lon: float,
    jd: float,
    ayanamsa_system: str = Ayanamsa.LAHIRI,
) -> PanchangaResult: ...
```

### Tricky Edge Cases
- **Vara boundary**: The Vedic day begins at sunrise, not midnight. The base implementation operates on the astronomical JD and documents this limitation; sunrise-corrected Vara is a future policy parameter.
- **Yoga skipping**: True fast Moon can skip a 13.33° Yoga window in a day. Use true positions (doctrine-consistent), note the skip possibility in the docstring.
- **Karana table boundary**: The fixed Karanas at Amavasya/Pratipada are asymmetrically placed. Verify against Jhora at month boundaries.

### Estimated Complexity
Moderate. Arithmetic is simple; Karana fixed/movable boundary requires careful table construction and validation.

---

## System 5 — Alternative Dasha Systems

### Primary Authority
- **Ashtottari**: BPHS (Ashtottari Dasha chapter); Raman, *A Manual of Hindu Astrology* pp. 201–210.
- **Yogini**: K.N. Rao, *Yogini Dasha* (1993); brief BPHS reference.
- **Kalachakra**: BPHS (Kalachakra Dasha chapter); Sanjay Rath commentary.

### Validation Reference
Jhora, Kala software. Kalachakra: Jhora is the primary cross-check.

### File
`moira/dasha_systems.py`

### Ashtottari (108-year cycle)

```
Sun:6, Moon:15, Mars:8, Mercury:17, Saturn:10, Jupiter:19, Rahu:12, Venus:21
```

Starting lord is from Moon's nakshatra — different mapping table from Vimshottari. Eligibility condition (Parashara): "Rahu not in 1st/5th/9th from Lagna" — expose `bypass_eligibility: bool` flag.

### Yogini (36-year cycle)

```
Mangala (Moon):1, Pingala (Sun):2, Dhanya (Jupiter):3, Bhramari (Mars):4,
Bhadrika (Mercury):5, Ulka (Saturn):6, Siddha (Venus):7, Sankata (Rahu):8
```

Starting Yogini: `nakshatra_index % 8`. No eligibility condition. Sub-periods proportional (identical arithmetic to Vimshottari).

### Kalachakra
Navamsha-based, Savya/Apasavya traversal direction, variable cycle length. **Defer to Phase 2 within this module.**

### Proposed Public Surface

```python
@dataclass(frozen=True, slots=True)
class AlternateDashaPeriod:
    system: str         # "ashtottari" | "yogini" | "kalachakra"
    level: int
    lord: str
    start_jd: float
    end_jd: float
    sub: list["AlternateDashaPeriod"]

@dataclass(frozen=True, slots=True)
class AshtottariPolicy:
    year_basis: str = "julian_365.25"
    ayanamsa_system: str = Ayanamsa.LAHIRI
    bypass_eligibility: bool = False
    lagna_sign_index: int | None = None   # required if bypass_eligibility=False

@dataclass(frozen=True, slots=True)
class YoginiPolicy:
    year_basis: str = "julian_365.25"
    ayanamsa_system: str = Ayanamsa.LAHIRI

def ashtottari(
    moon_tropical_lon: float,
    natal_jd: float,
    levels: int = 2,
    policy: AshtottariPolicy | None = None,
) -> list[AlternateDashaPeriod]: ...

def yogini_dasha(
    moon_tropical_lon: float,
    natal_jd: float,
    levels: int = 2,
    policy: YoginiPolicy | None = None,
) -> list[AlternateDashaPeriod]: ...
```

### Estimated Complexity
- Ashtottari: Simple (structurally identical to Vimshottari, different tables + one eligibility condition)
- Yogini: Simple (8 lords, proportional sub-periods, no eligibility)
- Kalachakra: Complex (Savya/Apasavya traversal, Navamsha-sign mapping, variable cycle) — Phase 2

---

## System 6 — Ashtakavarga

### Primary Authority
Parashara, *BPHS* Ashtakavarga Adhyaya. Vaidyanatha Dikshita, *Jataka Parijata* (14th c.).

### Engineering Reference
B.V. Raman, *Ashtakavarga System of Prediction* (1981) — the canonical English-language reference with verified tables. Commit to Raman as the authoritative table source; document it explicitly.

### Validation Reference
Jhora (Bhinnashtakavarga display), Kala software.

### File
`moira/ashtakavarga.py`

### Algorithm

```python
for planet_P in seven_planets:
    bhinna_AV[planet_P] = [0] * 12
    for sign_i in range(12):
        for ref in [*seven_planets, "Lagna"]:
            distance = (sign_i - sign_index[ref]) % 12 + 1   # 1–12
            if distance in REKHA_TABLES[planet_P][ref]:
                bhinna_AV[planet_P][sign_i] += 1

sarva[sign_i] = sum(bhinna_AV[P][sign_i] for P in seven_planets)
```

The `REKHA_TABLES` are 7 × 8 fixed lookup tables — 672 individual rekha/no-rekha values that must be encoded verbatim from Raman's reference and verified sign-by-sign against Jhora.

**Phase 1**: Unreduced Bhinnashtakavarga + Sarvashtakavarga.  
**Phase 2**: Trikona Shodhana and Ekadhipatya Shodhana (reductions).

### Proposed Public Surface

```python
REKHA_TABLES: dict[str, dict[str, frozenset[int]]]  # 7 planets × 8 references

@dataclass(frozen=True, slots=True)
class BhinnashtakavargaResult:
    planet: str
    rekhas: tuple[int, ...]     # 12 counts, 0=Aries…11=Pisces
    total_rekhas: int           # sum (always 0–56)

@dataclass(frozen=True, slots=True)
class AshtakavargaResult:
    jd: float
    ayanamsa_system: str
    bhinnashtakavarga: dict[str, BhinnashtakavargaResult]
    sarvashtakavarga: tuple[int, ...]    # 12 aggregate counts

def bhinnashtakavarga(
    planet: str,
    sign_indices: dict[str, int],       # planet/lagna → sign index (0–11)
) -> BhinnashtakavargaResult: ...

def ashtakavarga(
    sidereal_longitudes: dict[str, float],   # includes "Lagna" key
) -> AshtakavargaResult: ...

def transit_strength(
    planet: str,
    transit_sign_index: int,
    bhinna: BhinnashtakavargaResult,
) -> int: ...    # 0–8
```

### Tricky Edge Cases
- Table variants: different BPHS editions have minor discrepancies. Commit to Raman (1981) and document.
- Lagna participates as a sign index only — no longitude precision needed.
- Rahu/Ketu: excluded from core system. Scope to 7 planets + Lagna. Document as future extension.

### Estimated Complexity
Moderate. Algorithm is simple; table transcription is the primary failure mode.

---

## System 7 — Shadbala

### Primary Authority
Parashara, *BPHS* Shadbala Adhyaya.

### Engineering Reference
B.V. Raman, *Graha and Bhava Balas* (1959) — fully worked example chart verifiable to 2 decimal places in Rupas. Use this as the primary test fixture.

### Validation Reference
Jhora full Shadbala display.

### File
`moira/shadbala.py`

### Unit
Shashtiamsas (Sha). 60 Sha = 1 Rupa.

### Six Components

#### 1. Sthana Bala (Positional Strength) — 5 sub-components

**(a) Uchcha Bala**
```python
dist = abs(sidereal_lon - exaltation_lon)
if dist > 180: dist = 360 - dist
uchcha_bala = (180 - dist) / 3.0    # Sha, max 60
```

**(b) Saptavargaja Bala** — dignity in each of D1, D2, D3, D7, D9, D12, D30

| Dignity in varga | Shashtiamsas |
|---|---|
| Exaltation | 20 |
| Own sign | 15 |
| Adhi Mitra (great friend) | 10 |
| Mitra (friend) | 7.5 |
| Sama (neutral) | 5 |
| Shatru (enemy) | 2.5 |
| Adhi Shatru (great enemy) | 1.25 |
| Debilitation | 0 |

Sum across 7 vargas. Max = 140 Sha.

**(c) Ojayugmarasyamsa Bala** — odd/even sign strength  
Sun, Mars, Jupiter, Saturn: 15 Sha in odd D1/D9 signs. Moon, Venus: 15 Sha in even signs.

**(d) Kendradi Bala** — angular house  
Kendra (1,4,7,10): 60 Sha. Panapara (2,5,8,11): 30 Sha. Apoklima (3,6,9,12): 15 Sha.

**(e) Drekkana Bala**  
Male planets (Sun, Mars, Jupiter) in 1st drekkana: 15 Sha. Hermaphrodite (Mercury, Saturn) in 2nd: 15 Sha. Female (Moon, Venus) in 3rd: 15 Sha.

#### 2. Dig Bala (Directional Strength)

Strong direction by planet:
```
Sun, Mars:         10th house cusp
Jupiter, Mercury:  1st house cusp (Ascendant)
Moon, Venus:       4th house cusp
Saturn:            7th house cusp
```
```python
dist = abs(sidereal_lon - strong_cusp_lon)
if dist > 180: dist = 360 - dist
dig_bala = (180 - dist) / 3.0    # Sha, max 60
```

#### 3. Kala Bala (Temporal Strength) — 6 sub-components

| Sub-component | Key |
|---|---|
| Nathonnatha | Day planets (Sun, Jupiter, Venus) max at noon; night planets (Moon, Mars, Saturn) max at midnight; Mercury always strong. |
| Paksha | Tithi 1–15: `shukla = tithi`. Tithi 16–30: `shukla = 30 - tithi`. Benefics: `shukla * 4` Sha. Malefics: `(15 - shukla) * 4` Sha. |
| Tribhaga | Jupiter: 1st third of day; Sun: 2nd; Saturn: 3rd. Moon: 1st third of night; Venus: 2nd; Mars: 3rd. Mercury: always. Value: 60 Sha in strong period, 0 otherwise. |
| Abda/Masa/Vara/Hora | Lord of current solar year, month, weekday, hour each receive 15 Sha. |
| Ayana | `ayana_bala = 24 * sin(Sun_declination)`. `sin(dec) = sin(obliquity) × sin(sun_lon)`. |
| Yuddha | Planets within 1° in same sign: victor (smaller longitude) gains loser's Yuddha Bala. |

#### 4. Chesta Bala (Motional Strength)
Speed-based score vs mean speed. Retrograde = maximum (60 Sha). Sun and Moon: distance from apogee/perigee.

#### 5. Naisargika Bala (Natural Fixed Strength — never changes)

| Planet | Sha |
|---|---|
| Sun | 60.00 |
| Moon | 51.43 |
| Venus | 42.85 |
| Jupiter | 34.28 |
| Mercury | 25.70 |
| Mars | 17.14 |
| Saturn | 8.57 |

#### 6. Drig Bala (Aspectual Strength)
Sum weighted benefic aspects received; subtract weighted malefic aspects. Vedic aspect weights: full (7th sign) = 1.0; three-quarter (Mars: 4th/8th; Jupiter: 5th/9th; Saturn: 3rd/10th) = 0.75; half (5th/9th regular) = 0.5; quarter (3rd/10th regular) = 0.25.

### Required Minimum Rupas

| Planet | Min Rupas |
|---|---|
| Sun | 6.5 |
| Moon | 6.0 |
| Mars | 5.0 |
| Mercury | 7.0 |
| Jupiter | 6.5 |
| Venus | 5.5 |
| Saturn | 5.0 |

### Proposed Public Surface

```python
@dataclass(frozen=True, slots=True)
class SthanaBala:
    uchcha: float; saptavargaja: float; ojayugma: float
    kendradi: float; drekkana: float; total: float

@dataclass(frozen=True, slots=True)
class KalaBala:
    nathonnatha: float; paksha: float; tribhaga: float
    abda_masa_vara_hora: float; ayana: float; yuddha: float; total: float

@dataclass(frozen=True, slots=True)
class PlanetShadbala:
    planet: str
    sthana_bala: SthanaBala
    dig_bala: float
    kala_bala: KalaBala
    chesta_bala: float
    naisargika_bala: float
    drig_bala: float
    total_shashtiamsas: float
    total_rupas: float
    required_rupas: float
    is_sufficient: bool

@dataclass(frozen=True, slots=True)
class ShadbalaResult:
    jd: float
    ayanamsa_system: str
    planets: dict[str, PlanetShadbala]   # 7 planets

def shadbala(
    sidereal_longitudes: dict[str, float],
    planet_speeds: dict[str, float],
    houses: "HouseCusps",
    jd: float,
    latitude: float,
    longitude: float,
    ayanamsa_system: str = Ayanamsa.LAHIRI,
) -> ShadbalaResult: ...

# Individual sub-component functions for testing:
def sthana_bala(planet: str, sidereal_lon: float, ...) -> SthanaBala: ...
def dig_bala(planet: str, sidereal_lon: float, houses: "HouseCusps") -> float: ...
def kala_bala(planet: str, jd: float, latitude: float, longitude: float, ...) -> KalaBala: ...
def chesta_bala(planet: str, speed: float, mean_speed: float) -> float: ...
def drig_bala(planet: str, sidereal_longitudes: dict[str, float]) -> float: ...
```

### Tricky Edge Cases
- **Saptavargaja requires completed varga.py** (all 7 vargas, especially D2 Hora with Parashari rule). This is the hard dependency on System 1.
- **Kala Bala requires sunrise/sunset** — lat/lon input is mandatory. This makes Shadbala the only system with an indirect dependency on `moira.rise_set`.
- **Ayana Bala declination**: `sin(dec) = sin(obliquity) × sin(sun_lon)`. Use `moira.obliquity.mean_obliquity(jd)`.
- **Chesta Bala for luminaries**: Sun uses distance from aphelion; Moon uses distance from perigee. Requires mean anomaly from `moira.planets` speed data or `moira.nodes`.
- **Yuddha threshold**: Planetary war is restricted to same-sign conjunctions within 1°.
- **Bhava Bala** (house strength) is a related but separate system — keep out of scope.

### Estimated Complexity
Complex. Highest sub-component count and most input dependencies of all 7 systems. Implement each sub-component as an isolated function with its own test fixture from Raman's *Graha and Bhava Balas* reference chart.

---

## Consolidated Dependency Map

```
moira/sidereal.py      — complete; provides tropical_to_sidereal, nakshatra_of, Ayanamsa
moira/varga.py         — extend with 11 missing wrappers (D2/D4/D6/D8/D16/D20/D24/D27/D40/D45/D60)
moira/cycles.py        — complete; weekday ruler available
moira/rise_set.py      — complete; sunrise/sunset (required by Shadbala Kala Bala)

moira/panchanga.py        ← sidereal.py, cycles.py
moira/vedic_dignities.py  ← sidereal.py, constants.py
moira/jaimini.py          ← sidereal.py
moira/dasha_systems.py    ← sidereal.py (patterns from dasha.py)
moira/ashtakavarga.py     ← vedic_dignities.py (needed for Shodhana; not for base)
moira/shadbala.py         ← varga.py (all 7), vedic_dignities.py, panchanga.py,
                             ashtakavarga.py (optional Drig Bala variant),
                             rise_set.py, nodes.py (Moon apogee for Chesta Bala)
```

---

## Authority Source Quick Reference

| System | Primary Canon | Engineering Reference |
|---|---|---|
| Shodashvarga | BPHS Ch. 6–22 | Jhora, Parashara Light 9.x |
| Vedic Dignities | BPHS Ch. 3, 26, 28; Saravali Ch. 5–6 | Raman, *A Manual of Hindu Astrology* |
| Jaimini Karakas | Jaimini Sutras, Adhyaya 1, Pada 1 | Sanjay Rath commentary; Jhora |
| Panchanga | BPHS Muhurta chapters; Brihat Samhita Ch. 98–104 | Jhora, Kala |
| Alt. Dashas | BPHS (Ashtottari/Kalachakra chapters); Rao, *Yogini Dasha* | Jhora, Kala |
| Ashtakavarga | BPHS Ashtakavarga Adhyaya; Jataka Parijata | Raman, *Ashtakavarga System of Prediction* (1981) |
| Shadbala | BPHS Shadbala Adhyaya | Raman, *Graha and Bhava Balas* (1959) |
