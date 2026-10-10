# Shadbala Backend Standard

**Status:** Current contract, adversarial repairs 9 October 2026
**Authority:** `moira/shadbala.py`  
**Source:** Selected Raman 1996 and BPHS Santhanam component rules; see [source and compatibility receipt](../03_validation/VEDIC_ADVERSARIAL_REPAIR_VALIDATION_2026-10-09.md).

---

## Part I — Architecture Standard

### 1. Governing Principle

The Shadbala subsystem is an astronomical-truth-first computation of the six
sources of planetary strength (*bala*) used in classical Vedic astrology.

Source attribution is component-specific. Selected Saptavargaja, Kala and war rules have independently transcribed arithmetic witnesses. Retained thresholds, ingress-based Abda/Masa, osculating Chesta and sign-based Drig are identified separately; neither named Saptavargaja scale claims an entire textbook worked chart.

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
| `chesta_bala` | Motional Strength | Ch. 6 (non-luminaries), Ch. 10 §§136–137 (luminaries) |
| Naisargika Bala | Natural/Fixed Strength (constant) | Ch. 5 |
| `drig_bala` | Aspectual Strength | Ch. 6 |
| `shadbala` | Grand total (all 7 planets) | Ch. 1 |
| `bhava_dig_bala` | Bhava Digbala (house directional strength) | Part II |
| `bhava_drishti_bala` | Bhava Drishti Bala (aspect on bhava madhya) | Part II |
| `bhava_bala` | Bhava Bala grand total (all 12 houses) | Part II |

### 4. Computational Policies

#### Chesta Bala

Retained motion convention (not selected by the Saptavargaja scale):
- **Sun**: Chapter X (§136, pp. 101–103).  Sayana (tropical) longitude + 90°, reduced to ≤ 180° and divided by 3 Shashtiamsas.  Maximum 60 Sha at Cancer ingress (northern solstice), 0 Sha at Capricorn ingress (southern solstice), 30 Sha at equinoxes.
- **Moon**: Chapter X (§137, pp. 101–103).  Elongation |lon_Moon − lon_Sun|, reduced to ≤ 180° and divided by 3 Shashtiamsas.  Maximum 60 Sha at Full Moon (opposition), 0 Sha at New Moon (conjunction), 30 Sha at quarters.
- **Five non-luminaries (Mars, Mercury, Jupiter, Venus, Saturn)**: Chapter VI (*Chesta Bala or Motional Strength*, pp. 64–79).  Derived from Chesta Kendra = (Seeghrochcha − (mean_lon + true_lon) / 2) mod 360°, reduced to ≤ 180° and divided by 3 Shashtiamsas.  For superior planets (Mars, Jupiter, Saturn), Seeghrochcha is the Sun's longitude and mean longitude is the planet's mean orbital longitude evaluated from the strict orbital core.  For inferior planets (Mercury, Venus), Seeghrochcha is the planet's heliocentric longitude and the mean planet is the Sun.
- **Speed-ratio fallback**: preserved for callers without positions or ephemeris access (retrograde gives 60 Sha; standstill gives 0 Sha).

#### Explicit geometry and source components

Full calculation requires immutable `ShadbalaContext`: UT epoch, named ayanamsa,
seven apparent geocentric sidereal longitudes, seven true-equatorial tropical
declinations, Chesta inputs, local apparent solar fraction, sunrise/set/next
sunrise, named year/month/day/hour lords and provenance. `derive_shadbala_context`
and `Moira.shadbala_context` bind the serving reader for all dependencies.
Supplied contexts perform no hidden ephemeris lookup. Missing polar solar events
remain inspectable and raise `ShadbalaContextError` for full strength.

Saptavargaja defaults to `raman_1996`; `bphs_santhanam_27` changes only the seven
awards. Both use the explicit Raman D1-only Moolatrikona convention, actual D1
degrees, and D1 compound relationships. Temporary friendship is houses
2,3,4,10,11,12. Source D7 counts from own/seventh for odd/even signs, D12 from
own sign, and D30 uses unequal planetary spans. Public generic harmonic
selectors are separate. `SaptavargajaEntry` preserves each sign/lord/state/award.
Mercury receives both odd-sign Ojayugma contributions like Sun/Mars/Jupiter/Saturn.

Nathonnatha is linear in apparent solar hour angle; Mercury always receives60.
Paksha uses continuous Sun–Moon phase, with Moon doubling. The named Moira
nature convention treats Moon as benefic on [84,264) degrees and Mercury as
malefic when sharing a D1 sign with Sun/Mars/Saturn or a malefic Moon. A supplied
context may explicitly select Mercury benefic/malefic. These endpoint and
association choices are declared interpretations, not an undisputed universal.
Tribhaga divides actual day/night arcs in thirds: Mercury/Sun/Saturn by day,
Moon/Venus/Mars by night; Jupiter always 60. Half-open boundaries assign the
new third. Ayana applies `(24 + signed_declination)*60/48`; Sun is doubled,
Mercury uses absolute declination, Moon/Saturn reverse sign. Declinations beyond
24 degrees retain the formula's signed result rather than an undocumented cap.

#### Kala Bala — Yuddha Bala (Graha Yuddha)

Only Mars/Mercury/Jupiter/Venus/Saturn participate, at separation strictly below
one degree. Raman 1996 articles 76–77 select lesser normalized longitude and
`abs(raw_aggregate_difference)/abs(source_disc_diameter_difference)`. Raw
aggregate is Sthana+Dig+Kala through Hora, excluding Ayana. Fixed source disc
values are9.4,6.6,190.4,16.6,158.0 arcseconds respectively; they are not modern
observed angular diameters. Winner gains and loser loses the same Kala amount;
Chesta is unchanged.

`moira_simultaneous_raman_raw_pairs_v1` evaluates every pair once against
immutable pre-war components, accumulates all credits/debits, and retains
signed net values. Exact equal longitude pairs have a stable lexical label
and zero adjustment. These tie/multi-way choices are Moira composition rules;
the inspected source passages prescribe two-body behavior only. `WarResolution`
is canonical for final totals, chart/network/Bhava/full and Lagna consumers.

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
used; war adjustments leave the displayed Chesta unchanged.

#### Graha Yuddha transfer disclosure

`GrahaYuddha.adjustment_shashtiamsas` carries the actual resolved Kala amount.
Detection-only pairs carry None. Deprecated `chesta_transferred` remains a
legacy construction field and is never populated by current calculation.
REST retains `shashtiamsas_transferred`, with `adjustment_component=kala_yuddha`.
The full ledger exposes raw totals, bases, Chesta, credits/debits and net values.

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
4. Detected separation is `0 <= separation_deg < 1.0`; the legacy vessel still permits1.0, but canonical ledger validation rejects such a fabricated detection.

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
- `chesta_bala`: Raman Ch. X luminary solstices/elongations, Raman Ch. VI non-luminary Chesta Kendra, and backward-compatible speed-ratio cases.
- `drig_bala`: Jupiter/Saturn 7th-sign opposition, Mars special aspects, no-aspect → 0.
- `kala_bala`: local solar time, continuous phase/nature, actual thirds, declination rules and explicit AMVH inputs.
- `sthana_bala`: sub-component sum equals total.
- `dig_bala`: float in [0, 60]; at strong cusp → maximum.
- `shadbala` integration: 7 planets present; total_rupas = total_shashtiamsas / 60; is_sufficient correct; invalid tithi raises.
- Vessel invariants: all vessels frozen, slots=True.
- `__all__` surface: all exported names importable.
- `validate_shadbala_output`: valid result does not raise; planet-key mismatch raises.

The repair acceptance adds independent pair arithmetic, permutations, corrupted-ledger rejection and real May2000/December2020 chart/full/Lagna HTTP witnesses. See the linked current validation receipt.

---

*Document produced at constitutional freeze (P11), April 2026.*

## REST admission and reader ownership — 8 October 2026

All six chart/result/profile/network/condition/Bhava/full routes use the
owning engine's reader-bound Shadbala call. They expose requested/applied
ayanamsa and requested/resolved/effective house systems in `policy_receipt`,
including actual polar fallback. Unknown house systems reject; registered
names and codes are admitted. That admission checkpoint did not change numerical Bala rules; the subsequent October9 repair above does. See the
[VED-005 admission standard](VEDIC_REST_ADMISSION_STANDARD.md) and its
[verification receipt](../03_validation/VEDIC_REST_ADMISSION_VALIDATION_2026-10-08.md).

## Direct-call and REST migration — 9 October 2026

`shadbala(..., context=ctx)` and `kala_bala(..., context=ctx)` now reject missing,
partial or contradictory context. `sthana_bala` requires all seven D1 positions
through `sidereal_longitudes`. Dated facade callers supply observer coordinates
or a context; REST derives one per request. REST strength planets are now
apparent **geocentric** positions; observer location controls houses and solar
geometry. Older topocentric REST positions were incompatible with that contract.

Output validation checks typed components, sums, Rupas, thresholds, context,
Saptavargaja evidence and every war ledger entry. Negative Ayana requires its
declination context; nonzero Yuddha requires its canonical ledger. Existing
legacy manually constructed zero-war results remain structurally admissible.
An internally inconsistent service result is a server error, not client 422.
Polar full-strength unavailability is typed 422 `shadbala_context_unavailable`;
Lagna keeps its independent evidence and explicit unavailable strength basis.

The public surface also includes `ShadbalaContext`, `ShadbalaContextError`,
`derive_shadbala_context`, `SaptavargajaEntry`, `saptavargaja_breakdown` and
`WarResolution`. Exact exports are tested. Required Rupas retain their existing
values, including Sun 6.5, as a separate Moira threshold convention.

## Second adversarial pass: composition and receipt validation

Derived contexts declare `vara_basis="civil_utc_midnight"` and `vara_jd_utc`.
This preserves dated Panchanga's UTC weekday convention while all geometry
continues to use UT1. Dated adapters pass the original UTC JD; direct UT1
context derivation uses the time owner's inverse. The context checks that
the UTC evidence converts to its exact UT1 epoch and selects its Vara lord.
Legacy synthetic contexts retain `vara_basis="supplied"` with no UTC claim.
This does not attribute a UTC-midnight convention to a classical source;
ingress-based Abda/Masa conventions remain separately declared.

Context-backed validation recomputes Uchcha, Ojayugma, Drekkana and Drig from
the accepted positions, as well as the existing Kala, Chesta, Saptavargaja
and war checks. Positional ranges and discrete awards are enforced. Balanced
component changes cannot pass merely by preserving sums. House-independent
positional calculation and validation share one formula owner. Kendradi
membership and Dig's range are checked, but their exact values cannot be
reconstructed without house evidence, which is not carried in this context.
Legacy context-free results receive structural validation; neither kind of
supplied receipt proves the observational authenticity of caller data.

After compatibility checking, Lagna and Bhava consumers use the accepted
context positions before discrete sign, Navamsa, house or aspect decisions.
The 1e-9-degree comparison tolerance is unchanged. Lagna retains missing
bodies and caller-supplied nodes; context evidence does not fill input gaps.
