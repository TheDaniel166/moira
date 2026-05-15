# Moira Feature Audit 2026

**Audit date:** 2026-05-15  
**Moira commit:** 8fc17b8efb1fa38723458d4f851520183d93ecf9  
**Auditor:** TheDaniel166  
**Method:** 12-domain coverage matrix. Moira assessed from code inspection; competitors from public documentation (manuals, feature pages, tutorials).

**Cell scoring:** ✓ full | ~ partial | ✗ absent | ? unclear  
**Gap types:** A = missing feature | B = depth gap  
**Priority:** D + C + T score → P1 (7–9) | P2 (5–6) | P3 (3–4)

---

## 0. Executive Summary

*Written last — after all domain chapters are complete.*

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
| Solar sign frame (Sun on cusp 1) | ✗ | ✓ | ✓ | ✓ | ✓ | ✓ | ✗ | ✓ | ✓ |
| Derived houses (from any cusp) | ✗ | ✓ | ✓ | ✓ | ✗ | ✓ | ✗ | ✗ | ✗ |

**Gap notes:**  
Moira's house system breadth is strong — all 17 systems in `HouseSystem` (including
Alcabitius, Meridian, Azimuthal, Vehlow, Krusinski, Topocentric, Carter, APC, and
Sunshine) are confirmed in `_KNOWN_SYSTEMS` and fully operational. The Sunshine system
(code "N", Makransky 1988) places the Sun at cusp 12, which is a distinct variant from
the traditional solar sign frame where the Sun's sign occupies house 1.

Two gaps identified against the competitor matrix:

**Solar sign frame (Sun on cusp 1) — Type A gap:** The traditional solar sign/solar
house frame (ASC replaced by the Sun's sign cusp so that the Sun's sign = house 1) is
absent. Moira's SUNSHINE system is the structurally different Makransky variant (Sun at
cusp 12). Solar Fire, Sirius, Janus, Astro.com, Astro-Seek, Co-Star, and TimePassages
all offer the traditional solar sign frame (7 of 8 competitors). D=2, C=5, T=2 → P1.

**Derived houses (from any cusp) — Type A gap:** No module or function provides
derived/turned house calculation (rotating the house wheel so that any chosen cusp
becomes the new ASC/1st house). Solar Fire, Sirius, Janus, and Astro-Seek support
this (4 of 8 competitors). D=1, C=4, T=2 → P2.

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
<!-- Task 4 -->

## 5. Lots, Parts & Special Points
<!-- Task 5 -->

## 6. Predictive — Transits & Returns
<!-- Task 6 -->

## 7. Predictive — Progressions & Directions
<!-- Task 7 -->

## 8. Predictive — Time Lord Systems
<!-- Task 8 -->

## 9. Synastry & Relationship Charts
<!-- Task 9 -->

## 10. Astronomical Phenomena & Events
<!-- Task 10 -->

## 11. Astrocartography & Spatial Techniques
<!-- Task 11 -->

## 12. Vedic / Jyotish Suite
<!-- Task 12 -->

---

## 13. Master Gap List
<!-- Task 13 -->

---

## 14. Depth & Accuracy Gap Supplement
<!-- Task 14 -->

---

## 15. Executive Summary
<!-- Task 15 — written last -->

---

## Appendix A: Competitor Profiles
<!-- Task 16 -->

## Appendix B: Scoring Rationale
<!-- Task 16 -->
