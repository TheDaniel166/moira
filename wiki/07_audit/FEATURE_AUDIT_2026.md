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
to ARMC + 90° with negated latitude) and exposed as `HouseResult.vertex` / `anti_vertex`.
East Point / Equatorial ASC is absent as a computed output point — the only reference in
`houses.py` line 1355 is a docstring comment on Morinus internal math. Galactic Center
and Super-Galactic Center are both present in `galactic.py` as ecliptic-longitude
sensitive points.

| Feature | Moira | Solar Fire | Sirius | Janus | Astro.com | Astro-Seek | Morinus | Co-Star | TimePassages |
|---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| Lot of Fortune | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✗ | ✓ |
| Lot of Spirit | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✗ | ✗ |
| Full Arabic lots catalog (100+) | ✓ (~512) | ~ (~50) | ✓ (~97) | ~ (~40) | ~ | ✓ | ✗ | ✗ | ✗ |
| Day/night sect reversal for lots | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ~ | ✗ | ✗ |
| Derived lot references | ✓ | ~ | ✓ | ✗ | ✗ | ~ | ✗ | ✗ | ✗ |
| Nine Parts / Novenaria | ✓ | ✗ | ✓ | ✓ | ✗ | ✓ | ✗ | ✗ | ✗ |
| Lunar Mansions (Manazil) | ✓ | ~ | ✓ | ~ | ✗ | ✓ | ✗ | ✗ | ✗ |
| Vertex | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✗ | ✓ |
| East Point / Equatorial ASC | ✗ | ✓ | ✓ | ✓ | ✗ | ✓ | ✓ | ✗ | ✗ |
| Prenatal syzygy degree | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✗ | ✗ |
| Galactic Center as sensitive point | ✓ | ~ | ✓ | ✗ | ✗ | ~ | ✗ | ✗ | ✗ |
| Super-Galactic Center | ✓ | ✗ | ~ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ |

**Gap notes:**  
Moira's lots coverage is the deepest in the comparison set at 512 entries. The docstring
claiming ~430 is stale and should be updated.

The prenatal syzygy is a minor depth gap: `prenatal_syzygy()` returns a Julian date rather
than an ecliptic longitude directly. The longitude must be derived via a separate ephemeris
call at that JD before passing it into the lots engine as `syzygy: float`. The feature is
fully functional but requires two steps; Type B, low severity.

- **East Point absent — Type A, D=2, C=5, T=2 → score 7 → P1.** The East Point
  (Equatorial Ascendant / ARMC + 90° projected to ecliptic at zero latitude) is not
  returned as a named output point in `HouseResult`. Solar Fire, Sirius, Janus, Astro-Seek,
  and Morinus all expose it (5 of 8 competitors). Implementation is trivial — it is already
  computed internally as the Morinus starting point.

## 6. Predictive — Transits & Returns

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
| Converse transits | ✗ | ✓ | ✓ | ✓ | ✗ | ✓ | ✓ | ✗ | ✗ |
| Sign ingresses | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✗ | ✓ |
| Annual ingresses (Aries ingress, etc.) | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✗ | ✓ |
| Solar return | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✗ | ✓ |
| Lunar return | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✗ | ✓ |
| Planetary returns (all bodies) | ✓ | ✓ | ✓ | ✓ | ~ | ✓ | ~ | ✗ | ~ |
| Diurnal chart (daily solar return) | ✗ | ✓ | ✓ | ✓ | ✗ | ~ | ✗ | ✗ | ✗ |
| Eclipse hit list (upcoming eclipses to natal) | ✗ | ✓ | ✓ | ✓ | ✗ | ✓ | ✗ | ✗ | ✗ |
| Prenatal syzygy | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✗ | ✗ |

**Gap notes:**  
**Converse transits** confirmed absent — `find_transits()` has no `converse`, `direction`, or `backward` parameter; the function always scans forward in time. Type A, D=3, C=5, T=3 → score 9 → **P1**.  
**Diurnal chart** confirmed absent — all `diurnal` references in the codebase relate to sect (day/night classification), Gauquelin diurnal sectors, or topocentric diurnal aberration corrections; no daily solar return chart function exists. Type A, D=2, C=4, T=3 → score 7 → **P1**.  
**Eclipse hit list** confirmed absent — `eclipse_search.py` exposes only `refine_minimum`, `refine_lunar_greatest_eclipse`, and `refine_solar_greatest_eclipse`; no function matches upcoming eclipses to natal positions. Type A, D=2, C=4, T=2 → score 6 → **P2**.

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
Bonatti) and Zodiacal Releasing (with angularity classification). `profections.py`
governs annual and monthly profections. `lord_of_the_orb.py` implements Abu
Ma'shar's Lord of the Orb using planetary hour determination and Chaldean sequence
arithmetic. `lord_of_the_turn.py` implements the annual Lord of the Turn via
Al-Qabisi's succession-hierarchy method and the Egyptian/Al-Sijzi testimony method.
`dasha.py` governs Vimshottari Dasha. `dasha_systems.py` governs Ashtottari and
Yogini Dasha. Jaimini Chara Dasha is absent — `jaimini.py` covers only Chara Karakas.
The three classical Hellenistic time lord systems — Decennials, Triacontaeteris, and
Aphesis/Distributions — are absent from the codebase.

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
| Decennials | ✗ | ✗ | ✓ | ✓ | ✗ | ~ | ✗ | ✗ | ✗ |
| Triacontaeteris (30-yr periods) | ✗ | ✗ | ✓ | ~ | ✗ | ✗ | ✗ | ✗ | ✗ |
| Hellenistic aphesis / distributions | ✗ | ✗ | ✓ | ✓ | ✗ | ~ | ✗ | ✗ | ✗ |
| Vimshottari dasha | ✓ | ✓ | ✓ | ✓ | ✗ | ✓ | ✗ | ✗ | ✗ |
| Multiple Vedic dasha systems | ✓ | ~ | ✓ | ~ | ✗ | ~ | ✗ | ✗ | ✗ |
| Jaimini Chara Dasha | ✗ | ✗ | ✓ | ~ | ✗ | ✗ | ✗ | ✗ | ✗ |

**Gap notes:**

Monthly profections are present (`monthly_profection` in `profections.py`); no gap.

**Decennials absent — Type A, D=2, C=3, T=3 → score 8 → P1.** The Hellenistic
10-year planetary time lord system (Decennials) is not implemented anywhere in the
codebase. Sirius and Janus both support it; Astro-Seek offers partial coverage. Two of
the eight competitors provide full support.

**Triacontaeteris absent — Type A, D=1, C=2, T=3 → score 6 → P2.** The 30-year
Hellenistic period system is absent. Only Sirius fully supports it; Janus offers partial
coverage. Lower competitor penetration justifies P2.

**Hellenistic aphesis / distributions absent — Type A, D=2, C=3, T=2 → score 7 → P1.**
The Hellenistic planetary distributions (aphesis) system is not implemented. Sirius and
Janus both support it; Astro-Seek offers partial coverage. This technique is closely
related to Zodiacal Releasing (which is present) and shares the same doctrinal corpus,
making its absence a meaningful gap relative to the Hellenistic feature set Moira
otherwise covers well.

**Jaimini Chara Dasha absent — Type A, D=2, C=3, T=3 → score 8 → P1.** `jaimini.py`
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

**Progressed synastry absent — Type B, D=2, C=4, T=2 → score 8 → P1.** No function in
`synastry.py` accepts a progressed chart as input for cross-chart comparison. No
`progressed_` parameter prefix or `jd_progressed` parameter exists in any synastry
entrypoint. Solar Fire, Sirius, and Janus all support progressed-chart-vs-natal synastry;
TimePassages offers partial coverage (4 of 8 competitors). This is a depth gap over the
existing synastry engine (core cross-chart aspects are present) — Type B.

**Transits to composite / Davison absent — Type B, D=2, C=3, T=2 → score 7 → P1.**
No function in `synastry.py`, `transits.py`, `transits_aspects.py`, or
`transits_houses.py` accepts a `CompositeChart` or `DavisonInfo` as a transit target.
The transit engine operates exclusively against natal charts. Solar Fire, Sirius, and
Janus support transiting a third (composite or Davison) chart (3 of 8 competitors).
This is a depth gap over the existing composite and Davison infrastructure — Type B.

**Synastry aspect patterns absent — Type B, D=1, C=4, T=2 → score 7 → P1.** No
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
| Cazimi / combust / under beams | ~ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✗ | ~ |
| Phase angles (elongation, illumination %) | ✓ | ✓ | ✓ | ✓ | ~ | ✓ | ~ | ✗ | ~ |
| Lunar phase (new, crescent, quarter, etc.) | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| Planetary visibility windows | ~ | ✓ | ✓ | ✓ | ✗ | ~ | ✗ | ✗ | ✗ |
| Rise / set / culmination times | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✗ | ✓ |

**Gap notes:**  
**Eclipse canon (~ for Moira):** `eclipse_canon.py` implements NASA-canon algorithmic geometry
in TT (gamma, contact solving, method comparison against the Espenak & Meeus Five Millennium
Canon). This is a NASA-compatibility layer for validation, not a pre-computed historical
catalog of past eclipses. Moira has no embedded lookup table of eclipse dates for arbitrary
historical queries. Type B gap. D=2, C=3, T=2 → P2.

**Cazimi / combust / under beams (~ for Moira):** These are computed inside `dignities.py`
as part of accidental dignity scoring (lines 1113–1118 — `SolarConditionTruth` with cazimi
≤0.283°, combust ≤8°, under sunbeams ≤17°). `phenomena.py` has no standalone functions
for these conditions. They are accessible via `DignitiesService` but not as independent
phenomena events. This is a design concern (no standalone query path), not a blocking gap
since the values are reachable. Not a Type A gap; minor Type B.

**Planetary visibility windows (~ for Moira):** `heliacal.py` returns event-point dates —
`planet_heliacal_rising()`, `planet_heliacal_setting()`, `planet_acronychal_rising()`,
`planet_acronychal_setting()` — each returning a single `jd_ut` crossing. No function
returns a date range (start–end window) of continuous planetary visibility in the evening
or morning sky. Type B gap. D=2, C=4, T=2 → P2.

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
| Relocated chart generation | ✗ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |

**Gap notes:**

**ACG Zenith / Nadir lines absent — Type A, D=2, C=4, T=2 → score 8 → P1.** `astrocartography.py`
produces only MC, IC, ASC, and DSC lines; no Zenith or Nadir line is computed. Solar Fire,
Sirius, and Janus offer full Zenith/Nadir support; Astro.com and Astro-Seek offer partial
coverage (5 of 8 competitors). Zenith lines (where a planet passes directly overhead) are
a standard ACG map layer used alongside the MC line.

**Relocated chart generation absent — Type A, D=3, C=8, T=2 → score 11 → P1.** No function
exists that takes a natal Julian Day and a new geographic latitude/longitude and returns a
full chart with recalculated house cusps, ASC, MC, and planet positions. All 8 competitors
offer this feature — it is the single largest ACG-domain gap by competitor penetration.
`_facade_spatial.py` and `astrocartography.py` only compute ACG line curves over a map; they
do not recast the natal chart at a new location.

**ACG for asteroids / fixed stars absent — Type A, D=2, C=3, T=2 → score 7 → P1.**
`sky_position_at()` accepts only the 10 bodies in `NAIF_ROUTES`; `AsteroidData` carries no
RA/Dec; no path exists to compute ACG lines for the 369-entry asteroid catalog or the 1,809
fixed stars. Sirius supports ACG for fixed stars; Solar Fire, Janus, and Astro-Seek offer
partial coverage. The `acg_lines()` core is body-agnostic, so adding an RA/Dec source for
asteroids and stars would be the primary implementation requirement.

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
