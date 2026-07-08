# Shadbala Backend Standard

**Status:** Constitutional freeze — P11  
**Authority:** `moira/shadbala.py`  
**Source:** BPHS Shadbala Adhyaya; B.V. Raman, *Graha and Bhava Balas* (1959)

---

## Part I — Architecture Standard

### 1. Governing Principle

The Shadbala subsystem is an astronomical-truth-first computation of the six
sources of planetary strength (*bala*) used in classical Vedic astrology.

Each sub-component is derived from an explicit, traceable source.  Policy is
explicit.  Output is deterministic for fixed inputs.  No hidden defaults govern
any sub-component computation.

### 2. Layer Structure

The subsystem is organised into twelve constitutional phases.  Each phase
consumes only outputs produced by earlier phases.  No phase reaches upward.

```
Phase  0  — Core computation (sthana_bala, dig_bala, kala_bala, chesta_bala,
            naisargika_bala, drig_bala, shadbala)
Phase  1  — Truth preservation     (SthanaBala, KalaBala, PlanetShadbala,
                                    ShadbalaResult)
Phase  2  — Classification          (ShadbalaTier)
Phase  3  — Inspectability          (PlanetShadbala.strength_ratio)
Phase  4  — Policy surface          (ShadbalaPolicy)
Phase  5  — Relational formalization (GrahaYuddha, graha_yuddha_pairs)
Phase  6  — Relational hardening    (GrahaYuddha.__post_init__ invariants)
Phase  7  — Local condition         (ShadbalaConditionProfile,
                                    shadbala_condition_profile)
Phase  8  — Aggregate intelligence  (ShadbalaChartProfile,
                                    shadbala_chart_profile)
Phase  9  — Network intelligence    (ShadbalaNetworkProfile,
                                    shadbala_network_profile)
Phase 10  — Full-subsystem hardening (PlanetShadbala.__post_init__,
                                    ShadbalaResult.__post_init__,
                                    validate_shadbala_output)
Phase 11  — Architecture freeze (this document)
Phase 12  — Public API curation (__all__, module docstring)
```

#### Layer boundary rules

- A phase-N function may consume vessels from any phase below N.
- A phase-N function may not mutate a lower-phase vessel.
- A phase-N function may not silently switch doctrine.
- A phase-N function may not bypass or re-derive a computation already
  produced by a lower phase.

### 3. Admitted Computation Surface

The following core computations are admitted and constitutionally frozen:

| Function | Sub-component | Raman Ch. |
|---|---|---|
| `sthana_bala` | Positional Strength (5 sub-components) | Ch. 2–3 |
| `dig_bala` | Directional Strength | Ch. 3 |
| `kala_bala` | Temporal Strength (6 sub-components) | Ch. 4 |
| `chesta_bala` | Motional Strength | Ch. 9 |
| Naisargika Bala | Natural/Fixed Strength (constant) | Ch. 5 |
| `drig_bala` | Aspectual Strength | Ch. 6 |
| `shadbala` | Grand total (all 7 planets) | Ch. 1 |
| `bhava_dig_bala` | Bhava Digbala (house directional strength) | Part II |
| `bhava_drishti_bala` | Bhava Drishti Bala (aspect on bhava madhya) | Part II |
| `bhava_bala` | Bhava Bala grand total (all 12 houses) | Part II |

### 4. Computational Policies

#### Chesta Bala

- **Sun and Moon**: Raman Ch. 9 apogee-distance method.  Strength = `(180 − arc(planet_lon, mandoccha)) / 3` Shashtiamsas.  Maximum 60 Sha at perigee; 0 Sha at apogee.
- **Sun mandoccha**: derived from Earth's osculating heliocentric perihelion longitude via `moira.orbits.orbital_elements_at(Body.EARTH)`, then + 180°, converted to sidereal.
- **Moon mandoccha**: derived from geocentric osculating elements via kernel pairs (3, 301) and (3, 399), then `lon_ascending_node + arg_perihelion`, converted to sidereal.
- **Five non-luminaries**: speed-ratio approximation (Raman Ch. 9 reserves the apogee-distance method for luminaries only).

#### Kala Bala — Yuddha Bala (Graha Yuddha)

- Only the five non-luminaries (Mars, Mercury, Jupiter, Venus, Saturn) participate.
- War condition: two war-eligible planets within 1° sidereal longitude.
- Victor determination: greater geocentric latitude; fallback = greater sidereal longitude when `planet_latitudes` is not supplied.
- Victor's `KalaBala.yuddha` receives the loser's raw Chesta Bala.
- Loser's `chesta_bala` is set to 0.

#### Drig Bala

Sign-based Vedic aspect doctrine (not degree-based):
- 4th/8th aspects of Mars score ½ weight; 7th aspect scores full weight.
- Saturn's 3rd/10th aspects score ½ weight; 7th scores full weight.
- Jupiter's 5th/9th aspects score ½ weight; 7th scores full weight.
- All other planet–planet aspects (7th house opposition) score full weight.

#### Kala Bala — Abda and Masa

Located by bisection on the Sun's actual apparent sidereal longitude from the
kernel (`moira.planets.planet_at`), pinning the Sankranti JD to 1-second
precision.  Not from mean-motion approximation.

#### Bhava Bala (Raman Part II)

Three components per house, summed to `total_shashtiamsas`:

- **Bhavadhipati Bala** — the total Shadbala piṇḍa of the house lord.  The
  lord is the classical lord of the rasi holding the bhava madhya (no nodal
  lordships).  The chart's jd and ayanamsa are taken from the supplied
  `ShadbalaResult` so the two computations cannot disagree.
- **Bhava Digbala** — the madhya rasi's locomotion class fixes the strong
  house (nara → H1, jalachara → H4, keeta → H7, chatushpada → H10);
  60 Sha there, −10 Sha per house of shortest circular distance, 0 opposite.
  Half-sign splits: Sagittarius 1st half nara / 2nd half chatushpada;
  Capricorn 1st half chatushpada / 2nd half jalachara.
- **Bhava Drishti Bala** — the bhava madhya is the aspected point, all seven
  classical planets aspecting, using the same sign-based aspect doctrine as
  Drig Bala (shared core: `_sign_aspect_drig_sha`).

Bhava madhya policy (explicit): the chart's house cusps are taken as the
madhya reference points, mirroring the module-wide house doctrine used by
`dig_bala`; equal houses from the Ascendant are the fallback when cusps are
unavailable.  Houses are ranked 1–12 by total strength (ties broken by lower
house number).

No required/threshold marker exists for houses: the tradition defines
required Rupas for planets only, so Bhava Bala is reported as raw strength
plus rank — no pass/fail is invented.

#### Ishta / Kashta Phala (BPHS Ch. 27)

Exposed as P3 inspectability properties on `PlanetShadbala`, derived — never
stored — from the vessel's own displayed components:

- `ishta_phala`  = √(Uchcha Bala × Chesta Bala)
- `kashta_phala` = √((60 − Uchcha) × (60 − Chesta))

Both on the 0–60 Shashtiamsa scale.  Policy: the *displayed* Chesta Bala is
used, so the Sun and Moon consume the Raman apogee-distance Chesta and a war
loser's zeroed Chesta flows through honestly.

#### Graha Yuddha transfer disclosure

`GrahaYuddha.chesta_transferred` records the Shashtiamsas moved by a war
(loser's raw Chesta Bala; victor gains it in `KalaBala.yuddha`, loser
forfeits it).  It is `None` — unknown, not silently 0 — when planet speeds
were not supplied to `graha_yuddha_pairs`.

---

## Part II — Vessel Inventory

### Core vessels (Phase 1)

| Vessel | Frozen | Slots | Notes |
|---|---|---|---|
| `SthanaBala` | ✅ | ✅ | Five sub-components + total |
| `KalaBala` | ✅ | ✅ | Six sub-components + total |
| `PlanetShadbala` | ✅ | ✅ | All 6 bala + totals + is_sufficient |
| `ShadbalaResult` | ✅ | ✅ | Full chart: jd, ayanamsa_system, planets |
| `BhavaBala` | ✅ | ✅ | One house: 3 components + totals + rank |
| `BhavaBalaResult` | ✅ | ✅ | All 12 houses + strongest/weakest |

### Constitutional-layer vessels

| Vessel | Phase | Notes |
|---|---|---|
| `ShadbalaTier` | P2 | `SUFFICIENT` / `INSUFFICIENT` class constants |
| `GrahaYuddha` | P5/P6 | War-pair record: victor, loser, separation_deg |
| `ShadbalaPolicy` | P4 | ayanamsa_system governance |
| `ShadbalaConditionProfile` | P7 | Per-planet condition summary |
| `ShadbalaChartProfile` | P8 | Aggregate chart strength summary |
| `ShadbalaNetworkProfile` | P9 | Strength ranking + war network |

---

## Part III — Public API

The following names are exported via `__all__` and constitute the stable
public surface of this module.

### Constants
- `NAISARGIKA_BALA` — natural fixed strength values (Shashtiamsas)
- `REQUIRED_RUPAS` — minimum Rupa thresholds per planet (Parashara)
- `MEAN_DAILY_MOTION` — classical mean daily motions (°/day)

### Vessels
- `ShadbalaTier`, `SthanaBala`, `KalaBala`, `PlanetShadbala`, `ShadbalaResult`
- `ShadbalaPolicy`, `GrahaYuddha`
- `ShadbalaConditionProfile`, `ShadbalaChartProfile`, `ShadbalaNetworkProfile`

### Functions
- `sthana_bala`, `dig_bala`, `kala_bala`, `chesta_bala`, `drig_bala`
- `shadbala` — full chart computation (all 7 planets)
- `hora_lord_at` — planetary hora lord at a birth moment
- `graha_yuddha_pairs` — public war-pair detection
- `shadbala_condition_profile`, `shadbala_chart_profile`, `shadbala_network_profile`
- `validate_shadbala_output`

---

## Part IV — Invariant Register

### `GrahaYuddha`
1. `victor` ∈ `{Mars, Mercury, Jupiter, Venus, Saturn}`
2. `loser` ∈ `{Mars, Mercury, Jupiter, Venus, Saturn}`
3. `victor ≠ loser`
4. `0 < separation_deg ≤ 1.0`

### `PlanetShadbala`
1. `total_shashtiamsas = sthana_bala.total + dig_bala + kala_bala.total + chesta_bala + naisargika_bala + drig_bala`
2. `total_rupas = total_shashtiamsas / 60.0`
3. `is_sufficient ↔ total_rupas ≥ required_rupas`

### `ShadbalaResult`
1. `ayanamsa_system` must be non-empty.
2. `jd` must be a finite float.

### `validate_shadbala_output` checks
1. Each `planets[key].planet == key`.
2. `total_rupas ≈ total_shashtiamsas / 60` (tolerance 1e-6).
3. `is_sufficient` consistent with `total_rupas` vs `required_rupas`.

---

## Part V — Delegation Boundaries

| Responsibility | Delegated to |
|---|---|
| Vedic dignity rank | `moira.vedic_dignities` |
| Varga sign indices | `moira.varga` |
| Panchanga elements (Vara, Paksha) | `moira.panchanga` |
| Sunrise / sunset | `moira.rise_set` |
| Orbital elements (mandoccha) | `moira.orbits` |
| Sidereal conversion (tropical → sidereal) | `moira.sidereal` |
| Kernel state vectors | `moira.spk_reader` |

The core `shadbala()` function does not perform sidereal conversion.  The
caller is responsible for supplying sidereal longitudes.

---

## Part VI — Failure Doctrine

| Condition | Behavior |
|---|---|
| `tithi_number` not in [1, 30] | `ValueError` via `shadbala()` |
| Required planet absent from `sidereal_longitudes` or `planet_speeds` | `KeyError` propagated |
| `ShadbalaResult.ayanamsa_system` empty | `ValueError` in `__post_init__` |
| `ShadbalaResult.jd` non-finite | `ValueError` in `__post_init__` |
| `GrahaYuddha` invariant breach | `ValueError` in `__post_init__` |
| `validate_shadbala_output` inconsistency | `ValueError` |
| `shadbala_network_profile` with empty planets | `ValueError` |

---

## Part VII — Validation Notes

The following are verified by the test suite (`tests/unit/test_shadbala.py`,
92 tests as of P11 freeze):

- All NAISARGIKA_BALA, REQUIRED_RUPAS, MEAN_DAILY_MOTION canonical values.
- `chesta_bala`: retrograde, standstill, mean-speed, capped-maximum cases.
- `drig_bala`: Jupiter/Saturn 7th-sign opposition, Mars special aspects, no-aspect → 0.
- `kala_bala`: Mercury always-60 fields, Vara lord bonus, Paksha Bala benefic/malefic, tithi boundary.
- `sthana_bala`: sub-component sum equals total.
- `dig_bala`: float in [0, 60]; at strong cusp → maximum.
- `shadbala` integration: 7 planets present; total_rupas = total_shashtiamsas / 60; is_sufficient correct; invalid tithi raises.
- Vessel invariants: all vessels frozen, slots=True.
- `__all__` surface: all exported names importable.
- `validate_shadbala_output`: valid result does not raise; planet-key mismatch raises.

Yuddha Bala correctness is verified by targeted `_detect_wars` / `graha_yuddha_pairs`
functional checks.  A chart-level integration test with a known war is not
yet included in the test baseline.

---

*Document produced at constitutional freeze (P11), April 2026.*
