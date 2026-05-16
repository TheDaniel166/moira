# Moira Feature Audit 2026

**Audit date:** 2026-05-15  
**Moira commit:** 8fc17b8efb1fa38723458d4f851520183d93ecf9  
**Auditor:** TheDaniel166  
**Method:** 12-domain coverage matrix. Moira assessed from code inspection; competitors from public documentation (manuals, feature pages, tutorials).

**Post-audit implementation update (2026-05-15):** Relocated chart generation has since been implemented in the live codebase via `moira.chart.relocated_chart()` and `Moira.relocated_chart()`. Converse transit search has also since been implemented across the live transit surfaces: `find_transits()` / `next_transit()` in `transits.py`, `find_aspect_transits()` in `transits_aspects.py`, `find_declination_transits()` in `transits_equatorial.py`, and `find_house_ingresses()` in `transits_houses.py`, all via an explicit reverse-time search mode. The traditional solar-sign frame has likewise been implemented in the live house engine as an explicit `HouseSystem.SOLAR_SIGN`, distinct from Sunshine. East Point / Equatorial Ascendant has now also been implemented in the live house engine as `HouseCusps.east_point`, computed from the Morinus-style equatorial projection of `ARMC + 90°`. A thin `solar_return_chart()` wrapper has now also been added on top of the existing return-time and chart-assembly substrate. Decennials has now also been fully implemented and constitutionalized in the live timelords subsystem, including the shared `L1/L2` core, `Valens` deep doctrine through `L4`, and `Hephaistio` through `L3`. The audit sections below are updated to reflect those closures.

**Cell scoring:** ✓ full | ~ partial | ✗ absent | ? unclear  
**Gap types:** A = missing feature | B = depth gap  
**Priority:** D + C + T score → P1 (7–9) | P2 (5–6) | P3 (3–4)

---

## 0. Executive Summary

**Overall assessment:** Moira is already one of the most computationally comprehensive astrology engines in the comparison set. Its strongest domains are body coverage, aspects, dignities, lots, and progressions/directions; its remaining thinnest areas are auxiliary predictive tooling, specialty doctrine layers such as KP, Tajika, and chart-yoga libraries, and the still-incomplete upper tier of spatial workflows beyond basic relocation.

### Domain Coverage Scores

| Domain | ✓ | ~ | ✗ | Score |
|---|:---:|:---:|:---:|:---:|
| 1. Body Coverage | 16 | 0 | 0 | 100.0% |
| 2. House Systems & Chart Frames | 20 | 0 | 0 | 100.0% |
| 3. Aspects, Midpoints & Antiscia | 12 | 0 | 0 | 100.0% |
| 4. Dignities, Strength & Rulership | 15 | 0 | 0 | 100.0% |
| 5. Lots, Parts & Special Points | 12 | 0 | 0 | 100.0% |
| 6. Predictive — Transits & Returns | 12 | 0 | 1 | 92.3% |
| 7. Predictive — Progressions & Directions | 22 | 0 | 0 | 100.0% |
| 8. Predictive — Time Lord Systems | 11 | 0 | 3 | 78.6% |
| 9. Synastry & Relationship Charts | 6 | 0 | 3 | 66.7% |
| 10. Astronomical Phenomena & Events | 11 | 2 | 0 | 91.7% |
| 11. Astrocartography & Spatial Techniques | 6 | 0 | 2 | 75.0% |
| 12. Vedic / Jyotish Suite | 10 | 0 | 4 | 71.4% |

### Top 10 Gaps by Priority

**Post-audit update:** Relocated chart generation and East Point / Equatorial Ascendant, both previously ranked gaps in this list, have now been implemented and verified in the live codebase. Standalone cazimi / combust / under-beams query surface (previously #7) has likewise been implemented via `solar_condition_at()` in `moira.phenomena` and `Moira.solar_condition_at()` on the facade. Derived houses (previously #18, score 5) has been implemented via `derived_houses(house_cusps, from_house)` in `moira.houses` — pure arithmetic rotation with no astronomical computation. The list below has been renumbered to show the current top 10 remaining gaps.

1. Eclipse hit list against natal positions - P2, score 6 - Moira can search eclipses, but not match them to natal targets.
2. Hellenistic aphesis / distributions - P2, score 6 - notably absent beside Zodiacal Releasing.
3. Jaimini Chara Dasha - P2, score 6 - predictive Jaimini timing remains absent.
4. Progressed synastry - P2, score 6 - synastry is present, but not against progressed charts.
5. Transits to composite / Davison - P2, score 6 - relationship charts cannot yet act as transit targets.
6. Eclipse canon as historical lookup catalog - P2, score 6 - canon validation exists, but not a historical query surface.
7. Planetary visibility windows - P2, score 6 - heliacal events exist, but not continuous visibility intervals.
8. ACG Zenith / Nadir lines - P2, score 6 - the cartography layer stops at MC/IC/ASC/DSC.
9. ACG for asteroids / fixed stars - P2, score 6 - `acg_lines()` is generic, but public RA/Dec supply paths stop at classical planets.
10. Yoga catalog - P2, score 6 - Panchanga yogas exist; natal chart-yoga detection does not.

### Quick Wins

- Eclipse hit list: eclipse search already exists, so the missing layer is natal-target matching rather than new eclipse astronomy.
- ~~Derived houses: turned-house rotation is conceptually simple and isolated from substrate astronomy.~~ *(resolved 2026-05-16 — `derived_houses()` in `moira.houses`)*

---
## 1. Body Coverage

Moira's body coverage spans the full solar system: all classical and modern planets
(Sun through Pluto), mean and true nodes (lunar + planetary), Black Moon Lilith (mean
and true osculating), a fixed-star catalog of 1,809 stars (star_registry.csv), 15
Behenian and 4 Royal stars, variable stars, 369-entry asteroid catalog (ASTEROID_NAIF),
classical asteroids (Ceres, Pallas, Juno, Vesta), 6 centaurs (Chiron, Pholus, Nessus,
Asbolus, Chariklo, Hylonome), TNOs (Eris, Sedna, Quaoar, Makemake, Haumea, Ixion,
Varuna, Orcus, Gonggong, and others in ASTEROID_NAIF), 5 periodic comets (Halley,
Encke, Tempel 1, Churyumov-Gerasimenko, Swift-Tuttle), multiple star systems with
orbital mechanics, and 9 Uranian/Hamburg hypothetical bodies (Cupido, Hades, Zeus,
Kronos, Apollon, Admetos, Vulkanus, Poseidon, Transpluto).

| Feature | Moira | Solar Fire | Sirius | Janus | Astro.com | Astro-Seek | Morinus | Co-Star | TimePassages |
|---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| Classical planets (Sun–Saturn) | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| Modern outer planets (Uranus–Pluto) | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| True & mean lunar nodes | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| Black Moon Lilith (mean & true) | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ~ | ~ | ✓ |
| Planetary nodes | ✓ | ~ | ✓ | ✓ | ✗ | ~ | ✗ | ✗ | ✗ |
| Fixed stars (large catalog) | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✗ | ~ |
| Variable stars | ✓ | ✗ | ~ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ |
| Classical asteroids (Ceres, Pallas, Juno, Vesta) | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✗ | ✓ | ✓ |
| Chiron & centaurs | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✗ | ✓ | ✓ |
| Extended centaurs (Pholus, Nessus, Chariklo) | ✓ | ~ | ✓ | ~ | ~ | ✓ | ✗ | ✗ | ✗ |
| TNOs (Eris, Sedna, Quaoar, Makemake, Haumea) | ✓ | ~ | ✓ | ~ | ~ | ✓ | ✗ | ✗ | ✗ |
| Main belt / extended asteroid catalog | ✓ | ~ | ✓ | ~ | ✗ | ✓ | ✗ | ✗ | ✗ |
| Comets | ✓ | ✗ | ~ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ |
| Uranian / Hamburg hypotheticals | ✓ | ✓ | ✓ | ✓ | ~ | ~ | ✗ | ✗ | ✗ |
| Multiple star systems | ✓ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ |
| Solar System Barycenter | ✓ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ |

**Gap notes:**

Moira's body coverage is exceptional — it exceeds all 8 competitors in catalog breadth. No Type A gaps identified. Possible Type B: Moira's extended asteroid catalog stands at 369 named bodies (ASTEROID_NAIF); Sirius claims the largest commercial catalog and may exceed this count — verify. Fixed star catalog at 1,809 entries (star_registry.csv) is competitive with commercial leaders. Variable stars, comets (5 periodic), multiple star systems with orbital mechanics, and SSB access are unique to Moira among this competitor set. Uranian suite covers all 8 Hamburg bodies plus Transpluto (9 total).

## 2. House Systems & Chart Frames

Moira implements house cusps via `houses.py` using ARMC, obliquity, and geographic
coordinates. The engine supports fallback from polar-incompatible systems (Placidus,
Koch) to Porphyry above the critical latitude (~66.56°). Huber houses are in a
separate module. Galactic, geodetic, local space, and Gauquelin sectors are also
separate specialized modules.

| Feature | Moira | Solar Fire | Sirius | Janus | Astro.com | Astro-Seek | Morinus | Co-Star | TimePassages |
|---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| Placidus | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| Koch | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✗ | ✓ |
| Regiomontanus | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✗ | ✓ |
| Campanus | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✗ | ✓ |
| Equal (ASC-based) | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| Whole Sign | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| Porphyry | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✗ | ✓ |
| Morinus | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✗ | ✗ |
| Alcabitius | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✗ | ✗ |
| Meridian / Axial Rotation | ✓ | ✓ | ✓ | ✓ | ✗ | ✓ | ✓ | ✗ | ✗ |
| Azimuthal / Horizontal | ✓ | ✓ | ✓ | ✓ | ✗ | ✓ | ✓ | ✗ | ✗ |
| Vehlow Equal | ✓ | ✓ | ✓ | ✓ | ✗ | ✓ | ✗ | ✗ | ✗ |
| Krusinski / Poli-Goeldi | ✓ | ✓ | ✓ | ~ | ✗ | ~ | ✗ | ✗ | ✗ |
| Huber / age progressions | ✓ | ✗ | ✓ | ~ | ✗ | ✗ | ✗ | ✗ | ✗ |
| Gauquelin sectors | ✓ | ✓ | ✓ | ✓ | ✗ | ~ | ✗ | ✗ | ✗ |
| Galactic houses | ✓ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ |
| Geodetic houses | ✓ | ✓ | ✓ | ✓ | ✗ | ✓ | ✗ | ✗ | ✗ |
| Local space frame | ✓ | ✓ | ✓ | ✓ | ✗ | ✓ | ✗ | ✗ | ✗ |
| Solar sign frame (Sun on cusp 1) | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✗ | ✓ | ✓ |
| Derived houses (from any cusp) | ✓ | ✓ | ✓ | ✓ | ✗ | ✓ | ✗ | ✗ | ✗ |

**Gap notes:**  
Moira's house system breadth is strong — the live `HouseSystem` surface now includes
the traditional solar-sign frame alongside Sunshine. The two solar doctrines are kept
explicitly distinct: Sunshine (code `N`) remains the Makransky variant with the Sun at
cusp 12, while `HouseSystem.SOLAR_SIGN` is the traditional sign-anchored frame where
house 1 begins at the start of the Sun's sign.

**Post-audit update — Solar sign frame implemented.** The traditional solar
sign/solar house frame is now present in the live codebase as an explicit
`HouseSystem.SOLAR_SIGN`, distinct from Sunshine. This gap is therefore closed in the
current implementation truth.

One remaining gap is identified against the competitor matrix:

**Derived houses (from any cusp) — resolved (2026-05-16).** `derived_houses(house_cusps, from_house)` is now present in `moira.houses` and exported from the top-level `moira` package. It accepts any `HouseCusps` and an integer 1–12, and returns a `DerivedHouseCusps` — a frozen dataclass with the rotated 12-cusp tuple, the pivot house number, and a back-reference to the source wheel. No astronomical computation is performed; the function is pure arithmetic rotation of the existing cusp longitudes. Covered by 21 unit tests in `tests/unit/test_derived_houses.py`.

## 3. Aspects, Midpoints & Antiscia

`aspects.py` handles longitudinal aspect detection. `midpoints.py` covers midpoint
trees and cosmobiology. `antiscia.py` covers solstice points and contra-antiscia.
`patterns.py` identifies aspect patterns (Grand Trine, T-Square, Grand Cross, Yod,
Mystic Rectangle, Kite, etc.). `transits_equatorial.py` covers declination-based
aspects (parallel, contra-parallel).

| Feature | Moira | Solar Fire | Sirius | Janus | Astro.com | Astro-Seek | Morinus | Co-Star | TimePassages |
|---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| Ptolemaic aspects (conjunction–opposition) | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| Modern aspects (quintile, septile, novile, etc.) | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ~ | ✓ |
| Parallel (declination) | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✗ | ✓ |
| Contra-parallel | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✗ | ✓ |
| Out-of-bounds planet flagging | ✓ | ✓ | ✓ | ✓ | ✗ | ✓ | ✗ | ✗ | ~ |
| Antiscia (solstice points) | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✗ | ~ |
| Contra-antiscia | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✗ | ✗ |
| Midpoints (full 45° sort) | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✗ | ~ |
| Cosmobiology (midpoint trees, pictures) | ✓ | ✓ | ✓ | ✓ | ✗ | ~ | ✗ | ✗ | ✗ |
| Aspect patterns (Grand Trine, T-Square, etc.) | ✓ | ✓ | ✓ | ✓ | ✗ | ✓ | ✗ | ~ | ✓ |
| Yod / Finger of God | ✓ | ✓ | ✓ | ✓ | ✗ | ✓ | ✗ | ✗ | ✓ |
| Declination aspect search (transit parallels) | ✓ | ✓ | ✓ | ✓ | ~ | ✓ | ✓ | ✗ | ~ |

**Gap notes:**  
No gaps identified in this domain. Parallel and contra-parallel detection are fully
implemented in both `aspects.py` (`find_declination_aspects`) for natal/synastry use
and `transits_equatorial.py` (`find_declination_transits`) for predictive transit
scanning, including a hybrid native-batch path for performance. Out-of-bounds flagging
is implemented in `aspects.py` via `find_out_of_bounds` and the `OutOfBoundsBody`
dataclass, comparing each body's declination against the true obliquity
(`moira.obliquity.true_obliquity`) with excess computed as
`abs(declination) − obliquity`. All Moira cells remain ✓ as templated.

## 4. Dignities, Strength & Rulership

`dignities.py` covers essential dignities (domicile, exaltation, detriment, fall).
`triplicity.py` covers triplicity lords across multiple systems (Ptolemaic, Dorothean,
Lilly). `egyptian_bounds.py` covers Egyptian and Ptolemaic bounds. `decanates.py`
and `hermetic_decans.py` cover decans/faces. The dispositorship module covers rulership
chains. `wiki/02_standards/DIGNITIES_BACKEND_STANDARD.md` is authoritative.

| Feature | Moira | Solar Fire | Sirius | Janus | Astro.com | Astro-Seek | Morinus | Co-Star | TimePassages |
|---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| Domicile / rulership | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| Exaltation / fall | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| Detriment | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| Triplicity lords (Ptolemaic) | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✗ | ~ |
| Triplicity lords (Dorothean / Lilly) | ✓ | ✓ | ✓ | ✓ | ~ | ✓ | ✓ | ✗ | ✗ |
| Egyptian / Ptolemaic bounds | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✗ | ✓ |
| Decanates / faces | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✗ | ✓ |
| Hermetic decanates | ✓ | ~ | ✓ | ~ | ✗ | ~ | ✗ | ✗ | ✗ |
| Almuten calculation | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✗ | ✗ |
| Peregrine status | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✗ | ✗ |
| Mutual reception | ✓ | ✓ | ✓ | ✓ | ~ | ✓ | ✓ | ✗ | ~ |
| Dispositor chain / final dispositor | ✓ | ✓ | ✓ | ✓ | ✗ | ✓ | ✓ | ✗ | ✗ |
| Accidental dignities (angularity, direct motion) | ✓ | ✓ | ✓ | ✓ | ~ | ~ | ~ | ✗ | ~ |
| Cazimi / combust / under beams | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✗ | ~ |
| Sect (diurnal/nocturnal) | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✗ | ✗ |

**Gap notes:**  
No gaps identified in this domain. All features are fully implemented in `dignities.py`
and supporting modules.

- **Almuten Figuris** (`almuten_figuris()` function, line 2233): scores essential
  dignities across key chart points to identify the planet with highest aggregate dignity.
- **Peregrine** (`SCORE_PEREGRINE`, `EssentialDignityKind.PEREGRINE`, line 1058):
  returned when a planet holds no essential dignity in its sign — a full member of
  `EssentialDignityTruth`.
- **Mutual reception** (`mutual_receptions()`, `_find_mutual_receptions()`, line 2276):
  supports both domicile and exaltation bases, configurable via `MutualReceptionPolicy`.
- **Dispositor chains** (`_build_dispositorship_chain()`, line 1970): genuine multi-step
  chain tracing via a `while True` walk through sign rulers, detecting final dispositors
  (planet in own sign), terminal cycles, and unresolved chains when out-of-scope planets
  appear. `DispositorshipTerminationKind` enumerates all outcomes.
- **Accidental dignities — angularity and motion** (`_get_accidental_dignities()`,
  line 1066): angular/succedent/cadent house placement scored at +4/+2/−2; direct/
  retrograde motion tracked and scored via `include_motion` policy flag.
- **Cazimi / combust / under beams** (lines 1113–1118): all three solar proximity
  thresholds implemented — cazimi (17′ = 0.283°), combust (8°), under sunbeams (17°) —
  with individual scores (SCORE_CAZIMI = +5, SCORE_COMBUST = −5, SCORE_SUNBEAMS).
- **Sect** (`SECT` table, `is_in_sect()`, `sect_light()`, `is_in_hayz()`, lines 227–299):
  diurnal/nocturnal sect membership fully implemented for all Classic 7, including
  Mercury's conditional sect rule (diurnal when rising before the Sun). Hayz and halb
  detection are also present.

## 5. Lots, Parts & Special Points

`lots.py` implements 512 named Arabic/Hellenistic lots (docstring says ~430 — outdated)
using ASC + Add − Subtract (mod 360°) with automatic day/night reversal (`reverse_at_night`
field per `PartDefinition`) and full support for derived lot references (26+ lots reference
other lots such as Fortune, Spirit, and Syzygy as formula operands). `nine_parts.py`
covers Abu Ma'shar's nine hermetic lots (novenaria). `manazil.py` covers the 28 Arabic
lunar mansions across five attribution traditions (al-Biruni default, Abenragel, Ibn
al-Arabi, Agrippa, Picatrix). `transits.py` computes the prenatal syzygy — it returns
`(jd_syzygy, phase)`, a Julian date and phase label; the syzygy ecliptic longitude must
be computed from the returned JD via a separate ephemeris call (lots engine accepts it as
`syzygy: float`). Vertex is fully computed in `houses.py` (via `_asc_from_armc` applied
to ARMC + 90? with negated latitude) and exposed as `HouseCusps.vertex` / `anti_vertex`.
East Point / Equatorial ASC is now computed as `HouseCusps.east_point`, using the
Morinus-style equatorial projection of `ARMC + 90?`. Galactic Center
and Super-Galactic Center are both present in `galactic.py` as ecliptic-longitude
sensitive points.

| Feature | Moira | Solar Fire | Sirius | Janus | Astro.com | Astro-Seek | Morinus | Co-Star | TimePassages |
|---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| Lot of Fortune | full | full | full | full | full | full | full | absent | full |
| Lot of Spirit | full | full | full | full | full | full | full | absent | absent |
| Full Arabic lots catalog (100+) | full (~512) | partial (~50) | full (~97) | partial (~40) | partial | full | absent | absent | absent |
| Day/night sect reversal for lots | full | full | full | full | full | full | partial | absent | absent |
| Derived lot references | full | partial | full | absent | absent | partial | absent | absent | absent |
| Nine Parts / Novenaria | full | absent | full | full | absent | full | absent | absent | absent |
| Lunar Mansions (Manazil) | full | partial | full | partial | absent | full | absent | absent | absent |
| Vertex | full | full | full | full | full | full | full | absent | full |
| East Point / Equatorial ASC | full | full | full | full | absent | full | full | absent | absent |
| Prenatal syzygy degree | full | full | full | full | full | full | full | absent | absent |
| Galactic Center as sensitive point | full | partial | full | absent | absent | partial | absent | absent | absent |
| Super-Galactic Center | full | absent | partial | absent | absent | absent | absent | absent | absent |

**Gap notes:**  
**Post-audit update - East Point implemented.** In the live codebase, East Point /
Equatorial Ascendant is now exposed as `HouseCusps.east_point`, computed from the
Morinus-style equatorial projection of `ARMC + 90 deg`.

Moira's lots coverage is the deepest in the comparison set at 512 entries. The docstring
claiming ~430 is stale and should be updated.

The prenatal syzygy is a minor depth gap: `prenatal_syzygy()` returns a Julian date rather
than an ecliptic longitude directly. The longitude must be derived via a separate ephemeris
call at that JD before passing it into the lots engine as `syzygy: float`. The feature is
fully functional but requires two steps; Type B, low severity.

## 6. Predictive ??? Transits & Returns
`transits.py` owns longitude-crossing detection, sign ingress search, solar/lunar/
planetary return computation, and prenatal syzygy. `transits_aspects.py` handles
transit-to-natal aspect events. `transits_equatorial.py` handles equatorial transits
including declination parallels. `transits_houses.py` handles transit-through-house events.

| Feature | Moira | Solar Fire | Sirius | Janus | Astro.com | Astro-Seek | Morinus | Co-Star | TimePassages |
|---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| Transits to natal (ecliptic) | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| Transits through houses | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ~ | ✓ |
| Transit aspects (aspect search) | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| Equatorial / declination transits | ✓ | ✓ | ✓ | ✓ | ~ | ✓ | ✓ | ✗ | ~ |
| Converse transits | ✓ | ✓ | ✓ | ✓ | ✗ | ✓ | ✓ | ✗ | ✗ |
| Sign ingresses | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✗ | ✓ |
| Annual ingresses (Aries ingress, etc.) | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✗ | ✓ |
| Solar return | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✗ | ✓ |
| Lunar return | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✗ | ✓ |
| Planetary returns (all bodies) | ✓ | ✓ | ✓ | ✓ | ~ | ✓ | ~ | ✗ | ~ |
| Diurnal chart (daily solar return) | ✓ | ✓ | ✓ | ✓ | ✗ | ~ | ✗ | ✗ | ✗ |
| Eclipse hit list (upcoming eclipses to natal) | ✗ | ✓ | ✓ | ✓ | ✗ | ✓ | ✗ | ✗ | ✗ |
| Prenatal syzygy | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✗ | ✗ |

**Gap notes:**  
**Post-audit update — Converse transits implemented.** The live codebase now exposes explicit reverse-time search across the transit surfaces: `find_transits()` / `next_transit()` in `transits.py`, `find_aspect_transits()` in `transits_aspects.py`, `find_declination_transits()` in `transits_equatorial.py`, and `find_house_ingresses()` in `transits_houses.py` all admit backward search. This gap is therefore closed in the current implementation truth.  
**Post-audit update — Solar return chart wrapper implemented.** The live codebase now exposes `solar_return_chart()` in `transits.py` plus `Moira.solar_return_chart()`, composing the pre-existing `solar_return()` search with `create_chart()` rather than adding new return mathematics. This closes the daily solar return chart gap in current implementation truth.  
**Eclipse hit list** confirmed absent — `eclipse_search.py` exposes only `refine_minimum`, `refine_lunar_greatest_eclipse`, and `refine_solar_greatest_eclipse`; no function matches upcoming eclipses to natal positions. Type A, D=2, C=2, T=2 → score 6 → **P2**.

## 7. Predictive — Progressions & Directions

`progressions.py` implements the full progression engine. Primary directions are
governed by their own backend standard and wiki doctrine. Both forward and converse
forms are available for all progression families.

| Feature | Moira | Solar Fire | Sirius | Janus | Astro.com | Astro-Seek | Morinus | Co-Star | TimePassages |
|---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| Secondary progressions | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✗ | ✓ |
| Converse secondary progressions | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✗ | ✗ |
| Tertiary progressions | ✓ | ✓ | ✓ | ✓ | ~ | ✓ | ✗ | ✗ | ✗ |
| Minor progressions | ✓ | ✓ | ✓ | ✓ | ✗ | ✓ | ✗ | ✗ | ✗ |
| Solar arc directions | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✗ | ✓ |
| Naibod arc | ✓ | ✓ | ✓ | ✓ | ✗ | ✓ | ✓ | ✗ | ✗ |
| Mean solar arc | ✓ | ✓ | ✓ | ✓ | ✗ | ~ | ✗ | ✗ | ✗ |
| One-degree arc | ✓ | ✓ | ✓ | ✓ | ✗ | ✓ | ✗ | ✗ | ✗ |
| Ascendant arc | ✓ | ✓ | ✓ | ✓ | ✗ | ✓ | ✗ | ✗ | ✗ |
| Vertex arc | ✓ | ~ | ✓ | ~ | ✗ | ✗ | ✗ | ✗ | ✗ |
| Declination progressions (Jayne) | ✓ | ✗ | ✓ | ~ | ✗ | ✗ | ✗ | ✗ | ✗ |
| Progressed house frames (daily houses) | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ~ | ✗ | ✓ |
| Primary directions — Placidus semi-arc | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✗ | ✗ |
| Primary directions — Regiomontanus | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✗ | ✗ |
| Primary directions — Campanus | ✓ | ✓ | ✓ | ✓ | ~ | ~ | ✓ | ✗ | ✗ |
| Primary directions — Topocentric | ✓ | ~ | ✓ | ✓ | ✗ | ~ | ✓ | ✗ | ✗ |
| Primary directions — Morinus | ✓ | ✓ | ✓ | ✓ | ✗ | ~ | ✓ | ✗ | ✗ |
| Primary directions — Zodiacal | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✗ | ✗ |
| Primary directions — Mundane | ✓ | ✓ | ✓ | ✓ | ~ | ✓ | ✓ | ✗ | ✗ |
| Primary directions — Parallels | ✓ | ✓ | ✓ | ✓ | ✗ | ~ | ✓ | ✗ | ✗ |
| Primary directions — Fixed stars as promissors | ✓ | ✓ | ✓ | ✓ | ✗ | ~ | ✓ | ✗ | ✗ |
| Converse primary directions | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✗ | ✗ |

**Gap notes:**  
Moira's progression and primary directions coverage is exceptional — matches or exceeds all competitors. The primary directions standard admits PLACIDUS_MUNDANE, PTOLEMY_SEMI_ARC, PLACIDIAN_CLASSIC_SEMI_ARC, MERIDIAN, MORINUS, REGIOMONTANUS, CAMPANUS, and TOPOCENTRIC as runtime-admitted methods; FIELD_PLANE and NEO_CONVERSE remain outside the current freeze and are Type B frontier items, not user-visible gaps. Morinus is admitted with an explicit doctrinal limit on its conjunction-style branch (shared with the equatorial family on current evidence), which is an internal precision note rather than a missing feature. No Type A gaps identified. No Type B gaps in primary directions for the current frozen surface.

## 8. Predictive — Time Lord Systems

`timelords.py` implements Firdaria (three sequence variants: diurnal, nocturnal,
Bonatti), Decennials, and Zodiacal Releasing (with angularity classification). `profections.py`
governs annual and monthly profections. `lord_of_the_orb.py` implements Abu
Ma'shar's Lord of the Orb using planetary hour determination and Chaldean sequence
arithmetic. `lord_of_the_turn.py` implements the annual Lord of the Turn via
Al-Qabisi's succession-hierarchy method and the Egyptian/Al-Sijzi testimony method.
`dasha.py` governs Vimshottari Dasha. `dasha_systems.py` governs Ashtottari and
Yogini Dasha. Jaimini Chara Dasha is absent — `jaimini.py` covers only Chara Karakas.
Of the three classical Hellenistic time-lord systems highlighted in the original
audit, Decennials is now implemented, while Triacontaeteris and
Aphesis/Distributions remain absent.

| Feature | Moira | Solar Fire | Sirius | Janus | Astro.com | Astro-Seek | Morinus | Co-Star | TimePassages |
|---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| Annual profections | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✗ | ✗ | ~ |
| Monthly profections | ✓ | ✓ | ✓ | ✓ | ✗ | ✓ | ✗ | ✗ | ✗ |
| Firdaria (diurnal) | ✓ | ✓ | ✓ | ✓ | ~ | ✓ | ✗ | ✗ | ✗ |
| Firdaria (nocturnal) | ✓ | ✓ | ✓ | ✓ | ~ | ✓ | ✗ | ✗ | ✗ |
| Firdaria (Bonatti variant) | ✓ | ~ | ✓ | ~ | ✗ | ~ | ✗ | ✗ | ✗ |
| Zodiacal Releasing | ✓ | ✗ | ✓ | ✓ | ~ | ✓ | ✗ | ✗ | ✗ |
| Lord of the Orb | ✓ | ✓ | ✓ | ✓ | ✗ | ~ | ✗ | ✗ | ✗ |
| Lord of the Turn | ✓ | ~ | ✓ | ✓ | ✗ | ✗ | ✗ | ✗ | ✗ |
| Decennials | ✓ | ✗ | ✓ | ✓ | ✗ | ~ | ✗ | ✗ | ✗ |
| Triacontaeteris (30-yr periods) | ✗ | ✗ | ✓ | ~ | ✗ | ✗ | ✗ | ✗ | ✗ |
| Hellenistic aphesis / distributions | ✗ | ✗ | ✓ | ✓ | ✗ | ~ | ✗ | ✗ | ✗ |
| Vimshottari dasha | ✓ | ✓ | ✓ | ✓ | ✗ | ✓ | ✗ | ✗ | ✗ |
| Multiple Vedic dasha systems | ✓ | ~ | ✓ | ~ | ✗ | ~ | ✗ | ✗ | ✗ |
| Jaimini Chara Dasha | ✗ | ✗ | ✓ | ~ | ✗ | ✗ | ✗ | ✗ | ✗ |

**Gap notes:**

Monthly profections are present (`monthly_profection` in `profections.py`); no gap.

**Post-audit update — Decennials implemented and constitutionalized.** The live
timelords subsystem now includes a full Decennials engine with constitutional
coverage through Phase 12. The admitted implementation boundary is:

- shared Decennials core: `L1 + L2`
- `Valens`: `L3 + L4`
- `Hephaistio`: `L3`

`Hephaistio L4` remains explicitly deferred, but the Decennials feature itself is now
present and this audit gap is closed.

**Triacontaeteris absent — Type A, D=1, C=1, T=3 → score 5 → P2.** The 30-year
Hellenistic period system is absent. Only Sirius fully supports it; Janus offers partial
coverage. Lower competitor penetration justifies P2.

**Hellenistic aphesis / distributions absent — Type A, D=2, C=2, T=2 → score 6 → P2.**
The Hellenistic planetary distributions (aphesis) system is not implemented. Sirius and
Janus both support it; Astro-Seek offers partial coverage. This technique is closely
related to Zodiacal Releasing (which is present) and shares the same doctrinal corpus,
making its absence a meaningful gap relative to the Hellenistic feature set Moira
otherwise covers well.

**Jaimini Chara Dasha absent — Type A, D=2, C=1, T=3 → score 6 → P2.** `jaimini.py`
implements Chara Karakas only; no Chara Dasha time lord system exists. `dasha_systems.py`
covers Ashtottari and Yogini but not Chara Dasha. Sirius fully supports it. This is the
primary Jaimini predictive technique and a meaningful gap in the Vedic suite.

## 9. Synastry & Relationship Charts

`synastry.py` implements cross-chart aspects, house overlays (both directions),
midpoint composite, reference-place composite, Davison chart (midpoint time +
corrected MC-preserving search). Governed by `wiki/02_standards/SYNASTRY_BACKEND_STANDARD.md`.

| Feature | Moira | Solar Fire | Sirius | Janus | Astro.com | Astro-Seek | Morinus | Co-Star | TimePassages |
|---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| Cross-chart aspects (synastry grid) | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| House overlays (A→B and B→A) | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ~ | ✓ |
| Midpoint composite chart | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✗ | ✓ |
| Reference-place composite | ✓ | ✓ | ✓ | ✓ | ✗ | ✗ | ✗ | ✗ | ✗ |
| Davison chart (midpoint time) | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✗ | ✓ |
| Davison chart (MC-corrected) | ✓ | ~ | ✓ | ~ | ✗ | ✗ | ✗ | ✗ | ✗ |
| Progressed synastry (prog. chart vs. natal) | ✗ | ✓ | ✓ | ✓ | ✗ | ✗ | ✗ | ✗ | ~ |
| Transits to composite / Davison | ✗ | ✓ | ✓ | ✓ | ✗ | ✗ | ✗ | ✗ | ✗ |
| Synastry aspect patterns | ✗ | ✓ | ✓ | ✓ | ✗ | ~ | ✗ | ✗ | ✗ |

**Gap notes:**

**Progressed synastry absent — Type B, D=2, C=2, T=2 → score 6 → P2.** No function in
`synastry.py` accepts a progressed chart as input for cross-chart comparison. No
`progressed_` parameter prefix or `jd_progressed` parameter exists in any synastry
entrypoint. Solar Fire, Sirius, and Janus all support progressed-chart-vs-natal synastry;
TimePassages offers partial coverage (4 of 8 competitors). This is a depth gap over the
existing synastry engine (core cross-chart aspects are present) — Type B.

**Transits to composite / Davison absent — Type B, D=2, C=2, T=2 → score 6 → P2.**
No function in `synastry.py`, `transits.py`, `transits_aspects.py`, or
`transits_houses.py` accepts a `CompositeChart` or `DavisonInfo` as a transit target.
The transit engine operates exclusively against natal charts. Solar Fire, Sirius, and
Janus support transiting a third (composite or Davison) chart (3 of 8 competitors).
This is a depth gap over the existing composite and Davison infrastructure — Type B.

**Synastry aspect patterns absent — Type B, D=1, C=2, T=2 → score 5 → P2.** No
cross-chart pattern detection exists in `synastry.py` — no Grand Trine, T-square, Yod,
or other multi-body configurations involving planets from both charts are detected. The
single-chart pattern engine (`patterns.py`) is not extended to the inter-chart domain.
Solar Fire, Sirius, and Janus support synastry aspect patterns; Astro-Seek offers
partial coverage (4 of 8 competitors). This is a depth gap over the existing
cross-chart aspect grid — Type B.

## 10. Astronomical Phenomena & Events

Eclipse suite: `eclipse.py` (contacts), `eclipse_geometry.py` (geometry), `eclipse_search.py`
(event search), `eclipse_canon.py` (historical catalog). Heliacal rises/sets: `heliacal.py`
(C++ native LOLA backend). Occultations: `occultations.py`. Station detection: `stations.py`.
Void of course: `void_of_course.py`. Planetary hours: `planetary_hours.py`. Phase angles:
`phase.py`. General phenomena: `phenomena.py`.

| Feature | Moira | Solar Fire | Sirius | Janus | Astro.com | Astro-Seek | Morinus | Co-Star | TimePassages |
|---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| Solar eclipses (search + contacts + geometry) | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✗ | ~ |
| Lunar eclipses | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✗ | ~ |
| Eclipse canon (historical catalog) | ~ | ~ | ✓ | ~ | ✓ | ~ | ✗ | ✗ | ✗ |
| Heliacal rises and sets | ✓ | ✓ | ✓ | ✓ | ✗ | ✓ | ✗ | ✗ | ✗ |
| Occultations | ✓ | ~ | ✓ | ~ | ✗ | ✗ | ✗ | ✗ | ✗ |
| Retrograde stations (Rx / Direct) | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| Void of course Moon | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ~ | ✓ |
| Planetary hours | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✗ | ✗ | ~ |
| Cazimi / combust / under beams | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✗ | ~ |
| Phase angles (elongation, illumination %) | ✓ | ✓ | ✓ | ✓ | ~ | ✓ | ~ | ✗ | ~ |
| Lunar phase (new, crescent, quarter, etc.) | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| Planetary visibility windows | ~ | ✓ | ✓ | ✓ | ✗ | ~ | ✗ | ✗ | ✗ |
| Rise / set / culmination times | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✗ | ✓ |

**Gap notes:**  
**Eclipse canon (~ for Moira):** `eclipse_canon.py` implements NASA-canon algorithmic geometry
in TT (gamma, contact solving, method comparison against the Espenak & Meeus Five Millennium
Canon). This is a NASA-compatibility layer for validation, not a pre-computed historical
catalog of past eclipses. Moira has no embedded lookup table of eclipse dates for arbitrary
historical queries. Type B gap. D=2, C=2, T=2 → score 6 → **P2**.

**Cazimi / combust / under beams — resolved (2026-05-16).** A standalone `solar_condition_at(planet, jd_ut)` function is now present in `phenomena.py` and exposed as `Moira.solar_condition_at()` on the facade. It returns a `SolarConditionTruth` directly from a planet name and Julian Day without requiring a `DignitiesService` call. Thresholds: cazimi ≤ 17′ (17/60°), combust ≤ 8°, under sunbeams ≤ 17°. Luminaries (Sun, Moon) return `present=False`. The function is covered by 10 unit tests in `tests/unit/test_solar_condition_at.py`.

**Planetary visibility windows (~ for Moira):** `heliacal.py` returns event-point dates —
`planet_heliacal_rising()`, `planet_heliacal_setting()`, `planet_acronychal_rising()`,
`planet_acronychal_setting()` — each returning a single `jd_ut` crossing. No function
returns a date range (start–end window) of continuous planetary visibility in the evening
or morning sky. Type B gap. D=2, C=2, T=2 → score 6 → **P2**.

## 11. Astrocartography & Spatial Techniques

`astrocartography.py` computes MC/IC/ASC/DSC lines with topocentric WGS-84 support;
Zenith/Nadir lines are not produced by the module.
`parans.py` covers latitude-based paran crossings (13-phase engine with field analysis
and contour extraction). `geodetic.py` provides geodetic MC/ASC equivalents (tropical and
sidereal). `local_space.py` provides azimuth/altitude-based local space charts.
The C++ native backend (`cartography.hpp`) provides low-level eclipse cartography
grid sweeps, not the ACG line engine.

`acg_lines()` accepts any `dict[str, (RA, Dec)]`, so it is body-agnostic in principle.
However `acg_from_chart()` defaults to `chart.planets.keys()` (the 10 classical planets
only), and `sky_position_at()` routes bodies via `NAIF_ROUTES` which contains only those
10 bodies. `asteroids.py` returns `AsteroidData` (ecliptic only — no RA/Dec); fixed stars
have no `sky_position_at` path. ACG lines for asteroids and fixed stars are therefore
absent from the current public surface.

No function in the codebase (in `astrocartography.py`, `synastry.py`, `chart.py`,
`houses.py`, or `_facade_spatial.py`) accepts a natal Julian Day plus a new geographic
location and returns a full recalculated chart (house cusps + planet positions). The
phrase "from a relocated chart" appears only in a `houses.py` docstring comment (line 3343)
describing a general ARMC-based overload — no `relocated_chart()` entrypoint exists.

**Post-audit implementation update:** The relocated-chart absence claim in this section
has been superseded. Moira now exposes `moira.chart.relocated_chart()` and
`Moira.relocated_chart()` as explicit relocated-chart entrypoints. The implementation
preserves the original chart moment and celestial snapshot, recomputes only the local
house frame for the new site, and was verified with targeted wrapper, policy-propagation,
facade-wiring, and live relocation tests.

In-mundo direction space (`IN_MUNDO` / `PrimaryDirectionSpace.IN_MUNDO`) is fully
implemented in `moira/primary_directions/spaces.py` and `__init__.py` for primary
direction computation, including mundane position perfection and preserved-latitude mode.
This is the canonical definition of in-mundo aspects (angular relationships in the sphere
of the houses, used in primary directions). It is present.

| Feature | Moira | Solar Fire | Sirius | Janus | Astro.com | Astro-Seek | Morinus | Co-Star | TimePassages |
|---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| ACG lines (MC / IC / ASC / DSC) | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✗ | ✗ |
| ACG Zenith / Nadir lines | ✗ | ✓ | ✓ | ✓ | ~ | ~ | ✗ | ✗ | ✗ |
| ACG for asteroids / fixed stars | ✗ | ~ | ✓ | ~ | ✗ | ~ | ✗ | ✗ | ✗ |
| Parans | ✓ | ✓ | ✓ | ✓ | ✗ | ✓ | ✗ | ✗ | ✗ |
| Local space charts | ✓ | ✓ | ✓ | ✓ | ✗ | ✓ | ✗ | ✗ | ✗ |
| Geodetic equivalents | ✓ | ✓ | ✓ | ✓ | ✗ | ✓ | ✗ | ✗ | ✗ |
| In-mundo aspects | ✓ | ✓ | ✓ | ✓ | ✗ | ✗ | ✓ | ✗ | ✗ |
| Relocated chart generation | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |

**Gap notes:**

**ACG Zenith / Nadir lines absent — Type A, D=2, C=2, T=2 → score 6 → P2.** `astrocartography.py`
produces only MC, IC, ASC, and DSC lines; no Zenith or Nadir line is computed. Solar Fire,
Sirius, and Janus offer full Zenith/Nadir support; Astro.com and Astro-Seek offer partial
coverage (5 of 8 competitors). Zenith lines (where a planet passes directly overhead) are
a standard ACG map layer used alongside the MC line.

**Relocated chart generation resolved (post-audit implementation update, 2026-05-15).**
Moira now provides this workflow explicitly through `moira.chart.relocated_chart()` and
`Moira.relocated_chart()`. The implementation uses the existing chart and house-policy
architecture rather than a parallel path: it preserves the original chart moment and
celestial snapshot while recalculating the local house frame for the new site. Targeted
tests were added to verify wrapper behavior, policy propagation, facade wiring, and the
expected invariant that planetary positions remain fixed while local angles change.

**ACG for asteroids / fixed stars absent — Type A, D=2, C=2, T=2 → score 6 → P2.**
`sky_position_at()` accepts only the 10 bodies in `NAIF_ROUTES`; `AsteroidData` carries no
RA/Dec; no path exists to compute ACG lines for the 369-entry asteroid catalog or the 1,809
fixed stars. Sirius supports ACG for fixed stars; Solar Fire, Janus, and Astro-Seek offer
partial coverage. The `acg_lines()` core is body-agnostic, so adding an RA/Dec source for
asteroids and stars would be the primary implementation requirement.

## 12. Vedic / Jyotish Suite

`vedic.py` provides the consolidated Vedic surface. `varga.py` implements all 16
Shodashvarga wrappers from D2 through D60; `panchanga.py` computes all five almanac
elements; `dasha.py` and `dasha_systems.py` cover Vimshottari, Ashtottari, and Yogini;
`jaimini.py` covers Chara Karakas only; `ashtakavarga.py` and `shadbala.py` are both
fully present. The remaining gaps are not in the astronomical substrate but in
specialized Jyotish doctrine layers beyond the current implemented surface.

| Feature | Moira | Solar Fire | Sirius | Janus | Astro.com | Astro-Seek | Morinus | Co-Star | TimePassages |
|---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| Vedic natal chart (sidereal) | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✗ | ✗ | ✓ |
| Vargas / divisional charts (D-1 to D-12) | ✓ | ✓ | ✓ | ✓ | ~ | ✓ | ✗ | ✗ | ~ |
| Extended vargas (D-16 to D-60) | ✓ | ~ | ✓ | ~ | ✗ | ~ | ✗ | ✗ | ✗ |
| Vimshottari dasha | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✗ | ✗ | ✓ |
| Multiple dasha systems | ✓ | ~ | ✓ | ~ | ✗ | ~ | ✗ | ✗ | ✗ |
| Jaimini Chara Dasha | ✗ | ✗ | ✓ | ~ | ✗ | ✗ | ✗ | ✗ | ✗ |
| Jaimini other techniques | ✓ | ✗ | ✓ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ |
| Shadbala (six-fold strength) | ✓ | ~ | ✓ | ~ | ✗ | ✗ | ✗ | ✗ | ✗ |
| Ashtakavarga | ✓ | ✓ | ✓ | ✓ | ✗ | ✓ | ✗ | ✗ | ✗ |
| Panchanga (all 5 elements) | ✓ | ~ | ✓ | ~ | ~ | ✓ | ✗ | ✗ | ✗ |
| Yoga catalog | ✗ | ~ | ✓ | ~ | ✗ | ~ | ✗ | ✗ | ✗ |
| Vedic dignities (uccha, neecha, etc.) | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✗ | ✗ | ✓ |
| KP System (Krishnamurti Paddhati) | ✗ | ~ | ✓ | ~ | ✗ | ✗ | ✗ | ✗ | ✗ |
| Tajika (Vedic annual return) | ✗ | ~ | ✓ | ~ | ✗ | ✗ | ✗ | ✗ | ✗ |

**Gap notes:**  
Moira's Vedic suite is substantial: all 16 Shodashvarga wrappers are present in
`varga.py`; all five Panchanga elements are present in `panchanga.py`; Vimshottari,
Ashtottari, and Yogini are present across `dasha.py` and `dasha_systems.py`; and both
`ashtakavarga.py` and `shadbala.py` are fully implemented. The missing items are
specialized doctrinal layers, not core Jyotish infrastructure.

**Jaimini Chara Dasha absent — see domain 8.** `jaimini.py` stops at Chara Karakas and
does not implement the Jaimini time-lord system itself. This is the same underlying gap
already counted under Predictive — Time Lord Systems and should not be double-counted in
the master list.

**Yoga catalog absent — Type A, D=2, C=2, T=2 → score 6 → P2.** Moira does not expose a
chart-yoga engine for named natal combinations (Raja Yogas, Dhana Yogas, Nabhasa Yogas,
and similar rule families). The only `yoga` surface in the codebase is the Panchanga
`YOGA_NAMES` table for the 27 calendrical Nitya Yogas, which is a different object from a
natal yoga catalog. Sirius is strong here; Solar Fire, Janus, and Astro-Seek offer
partial coverage.

**KP System absent — Type A, D=2, C=1, T=1 → score 4 → P3.** Moira supports the
Krishnamurti ayanamsa constant in `sidereal.py`, but no KP-specific computational layer
exists: no KP cusp workflow, no star-lord / sub-lord tables, no ruling planets, and no
significator logic. This is a real subsystem gap, not a parameter addition.

**Tajika absent — Type A, D=1, C=2, T=2 → score 5 → P2.** No Varshaphala / Tajika layer
exists: no Muntha, no Sahams, and no Tajika aspect or annual-return doctrine module.
Moira already has annual-return infrastructure in the Western predictive layer, so the
tractability is moderate rather than foundational, but it is still a new doctrinal
surface.

**Source notes for competitor rows:**  
- **Solar Fire:** Solar Fire's official help and manual publicly document sidereal/Vedic chart support and various Vedic divisional charts, which supports `✓` for sidereal natal and divisional-chart rows; they do not, in the public help surfaced here, provide equally explicit coverage for KP/Tajika, so those rows remain conservative at `~` rather than `✓`. Sources: [Casting a Vedic Chart](https://www.esotech.com.au/SFHelp/casting_a_vedic_chart.htm?printWindow=&toc=0), [Solar Fire Deluxe Manual PDF](https://alabe.com/ProgramDocs/SolarFireDeluxe_v6.pdf).
- **Sirius:** Sirius has the clearest official public Vedic feature list in the competitor set: its Vedic pages explicitly advertise Vargas, Dasas & Bhuktis, Panchanga, Muhurta, Ashtakavarga, Shad Bala, Chara Karaka, KP presentation, and Sahams. That is the main basis for the strong `✓` pattern across the Sirius column, including KP and broader annual-return doctrine support. Sources: [Vedic System in Sirius](https://www.astrosoftware.com/cpnew/m/software/sirius/features/vedic_system.html), [Vedic Astrology in Sirius](https://www.astrosoftware.com/cpnew/m/software/sirius/methods_vedic.html), [Vedic Chakras](https://astrosoftware.com/cpnew/m/software/sirius/features/vedic_chakras.html).
- **Janus:** Janus's official overview confirms a dedicated Vedic module and public release notes confirm divisional-chart presets and Dasa reporting. That is sufficient for `✓` on sidereal natal, base divisional charts, and Vimshottari, but because the public overview is thinner than Sirius on advanced doctrine, rows such as KP, Tajika, Shadbala, and Panchanga remain conservatively marked `~` unless the public Janus materials are more explicit. Sources: [Janus Overview](https://www.astrology-house.com/janus/index.cfm), [Janus Reviews / Vedic module description](https://www.astrology-house.com/janus/reviews.cfm?content_id=1067).
- **Astro-Seek:** Astro-Seek publicly exposes a Shodasha Varga calculator with D1–D60 coverage, which strongly supports `✓` for divisional charts and a broader sidereal/Vedic tool surface. Rows like Yoga catalog, KP, and Tajika stay partial or absent because the public pages surfaced in this pass are not explicit enough to justify stronger markings. Source: [Astro-Seek Shodasha Varga Calculator](https://horoscopes.astro-seek.com/divisional-charts-in-vedic-astrology-horoscope-calculator?no_mobile=1).
- **Astro.com:** Astrodienst's official public material clearly supports sidereal charts and multiple ayanamsha variants, but the public pages surfaced in this pass do not provide an equally explicit Vedic feature matrix for divisional charts, Panchanga, or Shadbala. For that reason, Astro.com remains conservative in this section: `✓` for sidereal natal and Vimshottari usage, `~` where sidereal/Vedic support is public but feature depth is less directly documented, and `✗` where no clear public evidence was found. Sources: [Sidereal Zodiac](https://www.astro.com/astrowiki/en/Sidereal_Zodiac), [Ayanamshas in Sidereal Astrology](https://www.astro.com/info/in_ayanamsha_e.htm), [Indian Astrology](https://www.astro.com/astrowiki/en/Indian_Astrology).
- **TimePassages:** TimePassages's official desktop manual/support documents sidereal charts and multiple ayanamshas, including Lahiri and Krishnamurti, but also makes clear that sidereal support differs by product tier. That supports a cautious `✓` for sidereal natal and conservative judgments elsewhere; the current Vedic row values should be read as desktop-oriented and low-confidence outside sidereal basics. Sources: [Desktop Manual TimePassages](https://support.astrograph.com/support/solutions/articles/66000476614-desktop-manual-timepassages), [Do we offer Sidereal charts in the TimePassages Web App?](https://support.astrograph.com/support/solutions/articles/66000476143-do-we-offer-sidereal-charts-in-the-timepassages-web-app-).

**Confidence note:** The desktop suites, especially Sirius, have much better public Vedic feature disclosures than Astro.com, Astro-Seek, and TimePassages. In this domain I therefore treated sparse public documentation as a reason to stay conservative, not to infer hidden support.

---

## 13. Master Gap List

**Post-audit update:** The original audit ranked relocated chart generation as gap `#1`. That item is now closed by the addition of `moira.chart.relocated_chart()` and `Moira.relocated_chart()`, with targeted verification added alongside the implementation. East Point / Equatorial Ascendant, originally listed as gap `#6`, is likewise now closed via `HouseCusps.east_point` in the live house engine. The resolved rows have been removed from the live gap table below; the remaining numbering still reflects the original audit artifact.

| # | Gap | Type | Domain(s) | D | C | T | Score | Priority | Note |
|---|---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|---|
| 7 | Eclipse hit list against natal positions | A | 6 | 2 | 2 | 2 | 6 | **P2** | Eclipse search exists, but not natal targeting. |
| 8 | Hellenistic aphesis / distributions | A | 8 | 2 | 2 | 2 | 6 | **P2** | Conspicuous omission beside Zodiacal Releasing. |
| 9 | Jaimini Chara Dasha | A | 8, 12 | 2 | 1 | 3 | 6 | **P2** | Predictive Jaimini layer absent; already reflected in both the time-lord and Vedic domains. |
| 10 | Progressed synastry | B | 9 | 2 | 2 | 2 | 6 | **P2** | Existing synastry engine does not accept progressed-chart inputs. |
| 11 | Transits to composite / Davison | B | 9 | 2 | 2 | 2 | 6 | **P2** | Composite and Davison charts cannot act as transit targets. |
| 12 | Eclipse canon as historical lookup catalog | B | 10 | 2 | 2 | 2 | 6 | **P2** | Algorithmic canon validation exists, but not embedded historical-query tables. |
| 13 | ~~Standalone cazimi / combust / under-beams query surface~~ | — | — | — | — | — | — | **Resolved 2026-05-16** | `solar_condition_at()` in `phenomena.py`; `Moira.solar_condition_at()` on the facade. |
| 14 | Planetary visibility windows | B | 10 | 2 | 2 | 2 | 6 | **P2** | Heliacal events are point-instants, not continuous visibility intervals. |
| 15 | ACG Zenith / Nadir lines | A | 11 | 2 | 2 | 2 | 6 | **P2** | Cartography layer stops at MC/IC/ASC/DSC. |
| 16 | ACG for asteroids / fixed stars | A | 11 | 2 | 2 | 2 | 6 | **P2** | `acg_lines()` is generic, but public RA/Dec supply paths stop at classical planets. |
| 17 | Yoga catalog | A | 12 | 2 | 2 | 2 | 6 | **P2** | Panchanga yogas exist; natal chart-yoga detection does not. |
| 18 | ~~Derived houses (from any cusp)~~ | — | — | — | — | — | — | **Resolved 2026-05-16** | `derived_houses()` + `DerivedHouseCusps` in `moira.houses`; pure rotation, no astronomy. |
| 19 | Triacontaeteris | A | 8 | 1 | 1 | 3 | 5 | **P2** | Niche but tractable Hellenistic period system. |
| 20 | Synastry aspect patterns | B | 9 | 1 | 2 | 2 | 5 | **P2** | Pattern engine is single-chart only. |
| 21 | Tajika / Varshaphala layer | A | 12 | 1 | 2 | 2 | 5 | **P2** | Annual-return substrate exists, but Tajika doctrine does not. |
| 22 | KP System | A | 12 | 2 | 1 | 1 | 4 | **P3** | Requires a dedicated KP subsystem, not a small extension. |

---
## 14. Depth & Accuracy Gap Supplement

These are features Moira implements, or nearly implements, but not yet at the depth or
surface completeness shown by the strongest competitors.

### B1 — Prenatal syzygy degree
**Current state:** `prenatal_syzygy()` returns the syzygy Julian date and phase.  
**Competitor standard:** Leading suites expose the syzygy as a directly usable degree or chart point.  
**Gap:** Moira requires a second ephemeris call to convert the returned JD into the longitude expected by `lots.py`.

### B2 — Progressed synastry
**Current state:** `synastry.py` covers natal-to-natal aspects, overlays, composites, and Davison charts.  
**Competitor standard:** Solar Fire, Sirius, and Janus allow one or both charts in a relationship comparison to be progressed.  
**Gap:** No synastry entrypoint accepts progressed longitudes or a progression date.

### B3 — Transits to composite / Davison
**Current state:** Moira can build midpoint composites and Davison charts, and it can compute transits to natal charts.  
**Competitor standard:** Professional suites also let the transit engine target the relationship chart itself.  
**Gap:** Transit target types stop at natal charts; composites and Davisons are not accepted as transit targets.

### B4 — Synastry aspect patterns
**Current state:** `patterns.py` detects complex single-chart patterns such as T-squares, Yods, and Grand Trines.  
**Competitor standard:** Some desktop suites extend those pattern searches across two charts in synastry.  
**Gap:** Moira does not detect inter-chart multi-body configurations.

### B5 — Eclipse canon as lookup catalog
**Current state:** `eclipse_canon.py` reproduces canon-style geometry for validation and comparison work.  
**Competitor standard:** Historical eclipse catalogs can be queried as data products in their own right.  
**Gap:** Moira lacks an embedded historical lookup surface for arbitrary past-eclipse retrieval.

### B6 — Standalone cazimi / combust / under-beams surface *(resolved 2026-05-16)*
**Current state:** `solar_condition_at(planet, jd_ut)` is now present in `phenomena.py` and exposed as `Moira.solar_condition_at()`. Returns a `SolarConditionTruth` directly without going through `DignitiesService`.  
**Resolution:** Gap closed. The dedicated phenomena query path now exists alongside the existing time-range event search (`solar_condition_events_in_range`).

### B7 — Planetary visibility windows
**Current state:** `heliacal.py` returns heliacal and acronychal event instants.  
**Competitor standard:** Visibility tools often return the full morning/evening visibility interval, not just the threshold crossing.  
**Gap:** Moira has the event points but not the continuous window abstraction.

---

## 15. Executive Summary

See section 0 for the full executive summary. The closing assessment is simple: Moira is
already stronger than most competitors in astronomical substrate, classical/traditional
coverage, lots, and direction/progression machinery, but it still lacks several user-facing
surfaces that professional astrologers expect, especially specialty doctrinal layers such as KP, Tajika, and chart-yoga
catalogs.

---

## Appendix A: Competitor Profiles

### Solar Fire
**Tier:** Professional desktop  
**Strengths:** Broad mainstream professional coverage, strong return/transit tooling, extensive house and direction support, solid Vedic basics.  
**Notable gaps vs. Moira:** Narrower body catalog, weaker exotic-object breadth, no Moira-equivalent multiple-star or SSB emphasis.

### Sirius
**Tier:** Professional desktop  
**Strengths:** The broadest direct feature rival in the set, especially across Hellenistic, Vedic, cosmobiology, and spatial work.  
**Notable gaps vs. Moira:** Moira still leads in some substrate-explicit and catalog-provenance areas, especially unusual body classes and inspectable computational policy.

### Janus
**Tier:** Professional desktop  
**Strengths:** Strong traditional/Hellenistic emphasis, good predictive tooling, meaningful Vedic support, broad professional charting surface.  
**Notable gaps vs. Moira:** Less breadth in unusual catalogs and specialized astronomical object classes; weaker frontier depth than Sirius.

### Astro.com
**Tier:** Web platform  
**Strengths:** Mainstream reference standard for online chart calculation, strong core natal/predictive/chart-frame coverage, trusted public baseline.  
**Notable gaps vs. Moira:** Shallower in specialized traditional, spatial, and exotic-body domains.

### Astro-Seek
**Tier:** Web platform  
**Strengths:** Exceptional free-tool breadth, especially for traditional techniques, divisional charts, and exploratory feature coverage.  
**Notable gaps vs. Moira:** Less consistent depth, fewer high-rigor specialty subsystems, and more partial coverage rows than the top desktop suites.

### Morinus
**Tier:** Open-source specialist desktop  
**Strengths:** Strong house-system and primary-directions orientation, serious traditional-method support, useful benchmark for classical features.  
**Notable gaps vs. Moira:** Very limited Vedic surface, narrower body coverage, and little support for modern spatial or catalog-rich work.

### Co-Star
**Tier:** Consumer mobile  
**Strengths:** Clean mainstream natal/transit consumer surface with broad public familiarity.  
**Notable gaps vs. Moira:** Sparse specialty coverage almost across the board: traditional methods, Vedic systems, spatial work, and advanced predictive tooling.

### TimePassages
**Tier:** Consumer/pro bridge  
**Strengths:** Strong core natal/transit/progression coverage in an accessible package; deeper than pure consumer apps.  
**Notable gaps vs. Moira:** Still much thinner in specialized traditional, Vedic, spatial, and catalog-heavy domains.

## Appendix B: Scoring Rationale

**Post-audit note:** The East Point / Equatorial Ascendant rationale row below is now historical. The gap was closed in the live codebase on 2026-05-16 via `HouseCusps.east_point`.

| Gap | D rationale | C rationale | T rationale |
|---|---|---|---|
| Relocated chart generation | Resolved post-audit on 2026-05-15 via explicit `relocated_chart()` public workflows | Historical competitor rationale unchanged: all 8 competitors expose it | Historical tractability rationale confirmed: existing chart + house infrastructure was sufficient |
| Converse transits | Resolved post-audit on 2026-05-15 via explicit backward-search support in `transits.py`, `transits_aspects.py`, `transits_equatorial.py`, and `transits_houses.py` | Historical competitor rationale unchanged: present in 5 of 8 competitors | Historical tractability rationale confirmed: existing transit surfaces were extended without a parallel engine |
| Solar sign frame | Resolved post-audit on 2026-05-15 via explicit `HouseSystem.SOLAR_SIGN` in the live house engine | Historical competitor rationale unchanged: present in 7 of 8 competitors | Historical tractability rationale confirmed: the frame fit the existing house-system architecture as a distinct solar doctrine |
| Decennials | Resolved post-audit on 2026-05-15 via a full constitutional Decennials subsystem in `moira/timelords.py` | Historical competitor rationale unchanged: supported fully or partially by 3 competitors | Historical tractability rationale confirmed: the existing time-lord architecture was sufficient |
| East Point / Equatorial Ascendant | Resolved post-audit on 2026-05-16 via explicit `HouseCusps.east_point` in the live house engine | Historical competitor rationale unchanged: present in 5 of 8 competitors | Historical tractability rationale confirmed: the geometry fit the existing Morinus-adjacent house math cleanly |
| Eclipse hit list | D=2: useful predictive auxiliary, not universal | C=2: present in 4 of 8 competitors | T=2: eclipse and natal-aspect infrastructure both exist, but are not connected |
| Hellenistic aphesis / distributions | D=2: important within Hellenistic practice | C=2: present fully or partially in 3 competitors | T=2: doctrinally new but adjacent to current time-lord work |
| Jaimini Chara Dasha | D=2: central Jaimini predictive method | C=1: only Sirius fully and Janus partially show support | T=3: time-lord infrastructure is mature already |
| Progressed synastry | D=2: meaningful relationship-analysis extension | C=2: present fully or partially in 4 competitors | T=2: reuse of progression and synastry infrastructure |
| Transits to composite / Davison | D=2: meaningful but specialist relationship workflow | C=2: present in 3 competitors | T=2: target-model extension rather than new astronomy |
| Eclipse canon as lookup catalog | D=2: useful research and historical-query feature | C=2: present fully or partially in 5 competitors | T=2: algorithmic layer exists, but data-product surface does not |
| ~~Standalone cazimi / combust / under-beams surface~~ | Resolved 2026-05-16 via `solar_condition_at()` in `phenomena.py` | Historical: C=3, most competitors expose the conditions directly | Historical: T=2, existing truth objects needed a dedicated public query path |
| Planetary visibility windows | D=2: important in observational/traditional work | C=2: present fully or partially in 4 competitors | T=2: built on top of heliacal event infrastructure |
| ACG Zenith / Nadir lines | D=2: standard professional cartography layer | C=2: present fully or partially in 5 competitors | T=2: extension of current line-generation logic |
| ACG for asteroids / fixed stars | D=2: specialist but real demand in advanced cartography | C=2: present fully or partially in 4 competitors | T=2: `acg_lines()` is generic, but public RA/Dec supply paths are missing |
| ~~Derived houses~~ | Resolved 2026-05-16 via `derived_houses()` + `DerivedHouseCusps` in `moira.houses` | Historical: C=2, present in 4 competitors | Historical: T=2, confirmed as pure rotation with no new astronomy |
| Triacontaeteris | D=1: niche Hellenistic method | C=1: only Sirius full and Janus partial | T=3: fits existing time-lord patterns cleanly |
| Synastry aspect patterns | D=1: specialist relationship-analysis extension | C=2: present fully or partially in 4 competitors | T=2: extend existing pattern logic to inter-chart graphs |
| Tajika / Varshaphala layer | D=1: specialist Vedic annual-return doctrine | C=2: partial/full support in 3 competitors | T=2: annual-return substrate exists but doctrine layer is absent |
| KP System | D=2: important to KP practitioners but not general Western demand | C=1: only Sirius full and Solar Fire/Janus partial at most | T=1: requires a dedicated KP subsystem rather than an incremental extension |
