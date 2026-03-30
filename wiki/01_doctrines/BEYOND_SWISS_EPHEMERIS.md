# Beyond Swiss Ephemeris
## What Moira Can Offer That Was Impossible for Its Creators

**Swiss Ephemeris** was built in 1997 by Alois Treindl and Dieter Koch at Astrodienst.
It is a masterwork of its era — an extraordinary feat of compression, accuracy, and design
for the hardware of the late 1990s. But it was built in a different world.

This document describes capabilities that are not merely *improvements* on what they did —
they are things that were **fundamentally impossible** in 1997, either because the underlying
data did not exist, because the computational paradigm did not exist, or because the
astronomical discoveries had not yet been made.

---

## Implementation Reality Note (March 2026)

This doctrine now mixes two layers:
- **Implemented now** in the current Moira codebase
- **Roadmap / near-term architecture** that is valid directionally but not yet runtime-complete

Current implementation truth (March 2026):
- Fixed stars are currently served by a sovereign local registry (~1,809 stars), not a live Gaia-DR3 runtime surface.
- The asteroid surface exposes 368 named bodies through bundled kernels and the `ASTEROID_NAIF` registry.
- Live on-demand Horizons API fetch for arbitrary newly discovered objects is not yet a public runtime path.
- Planetary and fixed-star heliacal computations are now exposed through the runtime; the current fixed-star surface is anchored to the sovereign registry rather than a live Gaia runtime.
- ΔT uses bundled/embedded IERS-derived tables and local interpolation; there is no runtime web fetch.
- Primary directions are implemented as an active engine and are no longer merely "under development".
- Interstellar-object, exoplanet-direction, and mass asteroid-node claims below should be read as roadmap vision unless explicitly tied to shipped APIs.

---

## I. The Data Revolution

### 1. A Billion Stars with Real Depth — Gaia DR3

Swiss Ephemeris uses the **Hipparcos catalog (1997)**: 118,218 stars, milliarcsecond precision,
no distances for most.

Gaia DR3 (June 2022):
- **1.812 billion** stellar sources
- **1.46 billion** stars with full parallax (true distance) and proper motion
- **33.8 million** stars with measured radial velocity (full 3D space motion)
- Parallax precision: **0.02 milliarcseconds** for bright stars — that is 50× better than Hipparcos

**What this changes for astrology:**

#### True Topocentric Fixed Stars

In 1997, "fixed stars" were treated as points on an infinite celestial sphere — effectively at
infinite distance. The concept of a topocentric correction for a star was meaningless because
no one knew how far most stars were.

Now we know. Sirius is 8.6 light-years away. Procyon is 11.4 ly. Vega is 25 ly. Arcturus is 37 ly.

For nearby stars, the **stellar parallax displacement** from the geocenter to an observer on
Earth's surface is measurable. Sirius shifts by approximately 0.02 arcseconds between the
geocenter and the limb of the Earth — genuinely sub-arcsecond, comparable to a tight planetary
transit orb. More importantly, the concept becomes philosophically significant: when does
the star actually rise *for you*, at your exact location? With Gaia parallax, that computation
is now exact.

The **True Topocentric Fixed Star** — the precise direction of a star as seen from your exact
location on Earth's surface, accounting for the star's known distance — was a calculation
that could not exist until Gaia.

#### Stellar Color and Spectral Quality

Ptolemy in the *Tetrabiblos* assigned astrological qualities to stars partly by their color:
fiery red stars like Antares carry Mars-like energy; pale white stars like Sirius carry
Jupiter-Venus character; yellow stars like Arcturus carry Saturn character. This was
observational and qualitative.

Gaia provides **photometric color indices (BP−RP)** and **effective temperature estimates**
for ~470 million stars. We can now compute a star's color quantitatively and formally
map it to its classical elemental character — not as guesswork but as measured spectral reality.

#### Every Star Has an Ephemeris

With 1.46 billion proper motions and parallaxes, every Gaia star can have its ecliptic
longitude computed at any epoch. Swiss Ephemeris knows ~1,500 fixed stars by name.
We can know **1.46 billion**. The era of "only named stars matter" is over. Any star
in the sky can have its exact astrological position computed on demand.

---

### 2. The Asteroid Revolution — 887,103 Bodies and Climbing

When Swiss Ephemeris was built, roughly **10,000–15,000** asteroids were numbered.
The Minor Planet Center today has **887,103 numbered minor planets** — nearly 60× more.
JPL Horizons tracks **1,479,000 asteroids** in total.

This is not merely quantitative. The mythological naming of asteroids has exploded:
- Every figure from Greek, Roman, Norse, Egyptian, Mesopotamian, Hindu, Celtic,
  Aztec, and Polynesian myth is now an asteroid.
- Thousands of asteroids are named after scientists, artists, writers, musicians,
  and historical figures.
- Entire thematic families exist: asteroids named after rivers, cities, concepts,
  national heroes, musicians.

**What this enables:**

A user can ask: *"Which asteroids named after Irish mythology are transiting my natal Moon
this year?"* or *"Is there an asteroid named after my patron saint, and where is it right now?"*

An **asteroid mythology database** tied to a live ephemeris — searchable by name, myth,
culture, and current sky position — was simply not possible in 1997.

#### 368 Named Bodies Immediately Accessible

Without generating any new kernel files, Moira's four bundled kernels (`asteroids.bsp`,
`sb441-n373s.bsp`, `centaurs.bsp`, `minor_bodies.bsp`) collectively cover **385 unique
bodies**. The `ASTEROID_NAIF` registry now maps **368 of these by name** — the full
classical main-belt canon from **1 Ceres through 1467 Mashona**, all six centaurs, and
the named trans-Neptunian objects (Eris, Sedna, Haumea, Makemake, Gonggong, Salacia,
Varda, Chaos). Every one of these is callable with a single function:

    asteroid_at("Eris", jd_tt)
    asteroid_at("Herculina", jd_tt)
    asteroid_at("Gonggong", jd_tt)

Swiss Ephemeris ships with pre-built data for roughly 20 asteroids. Moira ships with
368 named bodies accessible by name without configuration — and the architecture to
add any of the remaining 1.479 million on demand.

#### On-Demand Ephemeris from Orbital Elements

Swiss Ephemeris works from pre-computed, compressed data files. It cannot calculate a body
it was not pre-built for. Moira's architecture is designed to support **on-demand** ephemeris
expansion from orbital elements (and optional Horizons-fed kernel pipelines), but the current
public runtime path is still the bundled-kernel + registry surface. If an asteroid is
discovered tomorrow and named, support currently requires adding it to the registry/kernel
pipeline first.

---

### 3. New Worlds — Bodies That Did Not Exist as Known Objects in 1997

The entire trans-Neptunian landscape was invisible in 1997:

| Body | Discovery | Type | Notes |
|---|---|---|---|
| Quaoar | 2002 | Dwarf planet | Now has SPK kernel |
| Sedna | 2003 | Scattered disk | Extremely elongated orbit, ~11,400-year period |
| Haumea | 2004 | Dwarf planet | Rings, two moons, rapid rotation |
| Eris | 2005 | Dwarf planet | More massive than Pluto; caused the reclassification |
| Makemake | 2005 | Dwarf planet | |
| Gonggong | 2007 | Dwarf planet | Named 2020 after Chinese water deity |

**And beyond dwarf planets:**

#### Interstellar Objects — Visitors from Another Star System

- **1I/'Oumuamua** (October 2017) — the first known interstellar object to pass through
  the solar system. Hyperbolic trajectory. Origin: unknown. It passed through the inner
  solar system, approached closest to the Sun in September 2017, and is now departing.
- **2I/Borisov** (August 2019) — the first confirmed interstellar comet.
- **3I/ATLAS** (June 2025) — third known interstellar object.

An object from another star system, passing through our solar system, has an astrological
position. This has never been possible to calculate before. These bodies did not exist in
any catalog when Swiss Ephemeris was built. They will never be in its fixed data files.

We can compute the **ecliptic longitude of an interstellar visitor** at any moment of its
passage through the solar system. That is a genuinely new category of astronomical entity
in astrology.

---

### 4. Real-Time Earth Orientation — IERS Weekly Data

Swiss Ephemeris uses polynomial approximations for ΔT (TT − UT1) and treats the Earth's
rotation as a smoothly predictable function.

The **IERS** (International Earth Rotation and Reference Systems Service) publishes:
- **Bulletin A**: weekly updates — polar motion (x, y), UT1-UTC, celestial pole offsets
- **Bulletin B**: monthly final values, definitive to <0.001 arc-second

The Earth's rotation is not perfectly smooth. It jerks and wobbles due to atmospheric
loading, ocean tides, seismic events, and inner-core dynamics. In 1997, you used a
polynomial. In 2025, the actual measured values have been catalogued and modeled.

**What this means**: A chart cast for, say, a moment of geopolitical significance using
a ΔT value anchored to real Earth-rotation physics is more accurate than one computed
with a polynomial fit — by as much as 0.2–0.5 seconds of time, which translates to a
~0.1–0.3 arcminute shift in house cusps and a topocentric Moon correction.

For **mundane astrology** (charts for world events), this matters. Swiss Ephemeris uses
a polynomial approximation. Moira uses a physics-based hybrid model (`delta_t_physical.py`)
that decomposes ΔT into four explicit components: secular trend from tidal braking and
glacial isostatic adjustment, core-mantle angular momentum from the Gillet et al. series,
cryosphere/hydrosphere contribution from GRACE/GRACE-FO LOD integrals, and an IERS
residual spline fitted to Bulletin B annual values. All source data is bundled locally —
there is no runtime web fetch. Beyond the table epoch, the model extrapolates using only
the physical components, and reports a calibrated ±1σ uncertainty via
`delta_t_hybrid_uncertainty(year)`. See `DELTA_T_HYBRID_MODEL.md` for the full architecture.

---

## II. The Computational Revolution

### 5. Orbital Elements and On-Demand Orbit Analysis

Swiss Ephemeris's core planetary data comes from JPL's DE series — pre-integrated
n-body solutions. For anything not in those tables, SwissEph is helpless.

**What is currently implemented:** `orbits.py` provides `orbital_elements_at(body, jd_ut,
reader)` and `distance_extremes_at(body, jd_ut, reader)`. These extract osculating
Keplerian elements — semi-major axis, eccentricity, inclination, argument of perihelion,
longitude of ascending node, mean anomaly, and true anomaly — from the SPK state vectors
at any requested epoch. Any body with a kernel (planets, dwarf planets, centaurs, numbered
asteroids) has its full orbital element set available on demand without pre-tabulation.
Swiss Ephemeris has no equivalent for the extended body catalog.

**Roadmap:** Arbitrary orbit integration from initial conditions — for hypothetical bodies,
newly discovered objects without SPK kernels, or retrograde trajectory analysis through close
encounters — is not yet part of the public runtime. Modern Python tools (scipy, `rebound`,
`poliastro`) provide this capability and are architecturally compatible with Moira's
coordinate pipeline. The specific use cases that would become possible include:

- **Hypothetical planets**: Position of Planet Nine (Batygin & Brown 2016, refined 2024)
  from best-fit orbital elements derived from perturbed TNO clustering.
- **Custom test particles**: "If a body existed at these orbital parameters, where would it
  be in 2000 BC?"
- **Comet integration**: For a newly discovered comet not yet in Horizons, integrate from
  discovered position and velocity.
- **Encounter analysis**: Full numerical simulation of past and future trajectories including
  orbital discontinuities from planetary close approaches.

The ability to integrate any orbit from first principles, in-process, was computationally
prohibitive for a 1997 C library targeting consumer hardware.

---

### 6. Statistical Pattern Analysis Across Large Chart Corpora

The **Astro-Databank** (now maintained by Astro.com) contains over 60,000 birth charts of
notable individuals, events, and entities with Rodden Ratings for data quality.

With Moira as the calculation engine and modern data science tools, we can ask and answer
questions that were never computationally accessible:

- Which planetary configurations appear statistically more often than chance among
  musicians vs. athletes vs. political leaders? (Gauquelin's work, done by hand in the
  1950s with ~100 charts, revisited with 10,000+)
- What are the most common progressions active at the onset of major life transitions?
- Across all solar returns in the database where career advancement occurred, what house
  placements appear with anomalous frequency?

This is not a claim that astrology is statistically validated. It is a claim that
**the tools to investigate that question rigorously now exist** and can be integrated
directly with the ephemeris engine. Swiss Ephemeris is a C library — it has no pathway
to this kind of analysis.

---

### 7. Astrocartography for Any Body in the Kernel Set

Standard astrocartography software computes ACG lines for 10–15 traditional planets.
Moira's astrocartography engine (`astrocartography.py`) ships `acg_lines()` and
`acg_from_chart()`, which compute MC, IC, ASC, and DSC horizon lines for any body whose
ecliptic coordinates are available. The current bundled kernel set covers 368 named
bodies by name. The computation is architecturally identical for any body:

- Chiron lines, Ceres lines, Sedna lines — all computed by the same `acg_lines()` call
  as Sun lines
- An ACG map covering the full TNO/dwarf-planet set from the bundled kernels
- Lines for any body in the extended asteroid registry, including Eris, Gonggong,
  Haumea, Makemake

The mathematical algorithm is no different from Jupiter's MC line. What changes is the
breadth of bodies available. In 1997, drawing an ACG map for Chiron was exotic. Drawing
one for Gonggong, Eris, or a newly named asteroid was impossible. At full asteroid-catalog
scale (1.479M bodies), astrocartography requires the kernel-generation pipeline rather
than the bundled kernels alone.

---

### 8. The Galactic Frame — Full Galactic Coordinates for All Bodies

Swiss Ephemeris acknowledges the galactic center (approximately 26°54' Sagittarius) as a
special point. But it does not natively work in galactic coordinates.

The galactic coordinate system (galactic longitude ℓ, galactic latitude b) places the
center of the Milky Way at ℓ = 0°. Moira can compute galactic longitude and latitude
for every planet, asteroid, and star — transforming any chart into a galactic frame.

This enables:
- **Galactic latitude** of a planet — is it in the galactic plane (intense stellar density)
  or above/below it?
- **Galactic center, anti-center, North Galactic Pole** as chart angles
- The **Super-Galactic Center** (M87 virgo cluster center, ~2°19' Libra) as a named point
- **Galactic structure as astrological context**: the spiral arm positions,
  the galactic bulge direction

This is a frame of reference that no mainstream astrological software uses, and which
was not computationally accessible in 1997 because the galactic structure data was not
precise enough.

---

### 9. Near-Earth Object Proximity Events

The **Center for Near Earth Object Studies (CNEOS)** maintains continuously updated
approach data for all known NEAs (Near-Earth Asteroids). Asteroid **99942 Apophis**
will pass within **32,000 km** of Earth on **April 13, 2029** — closer than many
geostationary satellites.

The astrological chart for that moment — the exact second Apophis is at perigee —
can be computed with sub-arcsecond precision for any location on Earth. The question
of what an asteroid's closest approach means astrologically is open, but the computation
is now possible. It was not in 1997 because Apophis wasn't discovered until 2004.

More generally: for any chart, Moira can calculate **which asteroids are currently making
close passes to Earth** — their geocentric distances, angular velocities, and ecliptic
positions during their flybys. This produces a new category of astrological event:
*proximity conjunctions* — bodies whose physical nearness to Earth amplifies their
positional significance.

---

## III. The Conceptual Frontier

### 10. The Sedna Problem — A Chart That Cannot Recurse

Sedna has an orbital period of approximately **11,400 years** and a perihelion distance
of 76 AU (Pluto's average is 39 AU). It will not return to the inner solar system for
over eleven millennia.

In classical astrology, every planet's cycle is a return cycle — the Saturn return
(29.5 years), the Chiron return (50 years), the Uranus half-return (42 years). These
are meaningful because they recur within a human life.

Sedna's return occurs over civilizational timescales. It was near perihelion (closest to
Sun) in approximately **11,000 BC**, during the end of the last Ice Age and the dawn of
agriculture. Its next perihelion after the current passage (~2076) will occur around
**13,400 AD**.

Sedna occupies a position where standard astrological concepts (return, retrograde, cycle)
nearly break down — but the computation is perfectly precise. A chart can note whether a
person is born in the same "Sedna age" as Göbekli Tepe, the pyramids, or the far future.
This is a scale of time measurement that no astrological system has ever incorporated,
because the body was not known to exist.

---

### 11. Asteroid Families as Astrological Groupings

The Hirayama asteroid families are clusters of asteroids with nearly identical orbital
parameters — fragments of the same parent body destroyed by collision billions of years
ago. The **Koronis family**, the **Flora family**, the **Eos family** — each contains
thousands of members, all born from the same primordial body.

Moira can identify which asteroids in a chart belong to the same ancient parent. This
is an entirely new kind of astrological relationship: two asteroids may be in completely
different signs and houses, yet share a common origin — literally made of the same
rock. The astrological meaning of this is uncharted territory, but the calculation
is exact and the data exists.

This is now implemented. ``asteroid_families.py`` bundles the Nesvorný et al. (2015)
catalog: **143,711 numbered asteroids** assigned to **119 dynamical families**.

    asteroid_family(158)              → "Koronis(2)"
    family_members("Vesta")           → 15,252 asteroid numbers
    families_in_chart([158, 832, 4])  → {"Karin": [832], "Koronis(2)": [158], "Vesta": [4]}

Notable detail already visible in the data: **158 Koronis** (the family's namesake) is
in ``Koronis(2)`` — later dynamical analysis split the family into two groups, and the
namesake ended up in the secondary cluster. **832 Karin** is a sub-family of the Koronis
region, born from a second collision ~5.8 million years ago. A family within a family.
The largest family is **Nysa-Polana** at 19,073 members — two so entangled they cannot
be cleanly separated.

#### Family Resonance — A New Dimension of Aspect Qualification

When two asteroids of the same dynamical family form an aspect, that aspect carries a
qualifier beyond its geometric type: both bodies are fragments of the same ancient parent.
They are physically made of the same rock. The aspect is not merely a 120° angle between
two asteroids — it is a 120° angle between two fragments of the same shattered world.

This is the **family resonance layer**, now fully implemented. It operates as a
post-processing enrichment on top of any list of admitted aspects — the core aspect engine
(orbs, geometry) is unchanged; resonance is purely additive:

    find_resonant_aspects(aspects, body_catalog_numbers)
        → list[ResonantAspect], sorted by orb

    resonance_network(resonant_aspects)
        → dict[family_name → list[ResonantAspect]], per-family sub-graphs

Each ``ResonantAspect`` pairs an ``AspectData`` vessel with a ``FamilyResonance``
qualifier recording the shared family name and both catalog numbers. The ``resonance_network``
groups all resonant aspects by family, forming a sub-graph of the chart's aspect network
for each active family.

There is no precedent for this in any astrological software. The question of whether a
Flora-family trine *feels louder* than a trine between two unrelated bodies is genuinely
open astrological territory — but the calculation to ask that question is now exact, and
the data covering 119 families and 143,711 bodies is bundled with the library.

---

### 12. Light-Time Astrology

When you observe Jupiter at 15° Gemini, you are seeing Jupiter where it was
**43 minutes ago** (light travel time at average distance). The Moon you see is
1.3 seconds old. The Sun is 8.3 minutes old. Sirius is **8.6 years** old.

All serious ephemerides correct for light travel time in their positional calculations
(Moira does this in `corrections.py`). But a new question arises that no software
addresses: **what is the "now" position of a distant object?**

For planetary work this is trivial — the difference is small and well-defined. But
for fixed stars, the light you receive from Arcturus (37 ly away) left that star
in **1988**. The star may have changed. Gaia's proper motion lets us compute where
Arcturus is *right now* in space (its current true position) vs. where its light says
it was 37 years ago (its observed position).

The choice between **observed position** (what the light shows) and **true position**
(where the star physically is at this moment) is a philosophical one with no answer in
traditional astrology, because the data to ask the question did not exist. Moira can
offer both.

This is now implemented: `star_light_time_split(name, jd_tt)` in `stars.py` returns
`(observed, true)` — a pair of `FixedStar` vessels. The observed position propagates
proper motion to `jd_tt - distance_ly * 365.25` (the emission epoch); the true position
propagates to `jd_tt`. For stars without a valid parallax the distinction is undefined
and both positions are identical. `FixedStarTruth.true_position` records which was
computed.

---

### 13. The Exoplanet Catalog — Known Worlds Beyond the Solar System

Swiss Ephemeris contains no exoplanets. None existed in confirmed, catalogued form when it was built. The first confirmed exoplanet around a Sun-like star was 51 Pegasi b, discovered in **October 1995** — two years before SwissEph's release — and the catalog was essentially empty.

As of 2025, NASA's Exoplanet Archive lists **5,600+ confirmed exoplanets**. Each has a host star. Each host star has a known ecliptic position. This means every confirmed exoplanet has an astrological direction.

The ones that matter most astrologically are the nearest and most Earth-like:

| Body | Host Star | Distance | Notes |
|---|---|---|---|
| Proxima Centauri b | Proxima Centauri | 4.24 ly | Nearest known exoplanet; in habitable zone |
| Alpha Centauri system | Alpha Centauri A/B | 4.37 ly | Possible candidate bodies |
| TRAPPIST-1e, f, g | TRAPPIST-1 | 40 ly | Three habitable-zone worlds in same system |
| Kepler-186f | Kepler-186 | 582 ly | First confirmed Earth-size planet in habitable zone |
| LHS 1140 b | LHS 1140 | 48 ly | Dense super-Earth in habitable zone; water possible |

Astrologically, these are not merely abstract points. They are the known locations of other worlds — potentially inhabited ones. The direction of Proxima Centauri b from Earth is a fixed ecliptic position. A chart can note whether a planet is conjunct the direction of the nearest known world outside our solar system.

The philosophical implications for mundane and natal astrology are genuinely new territory. But the computation is exact, and the data exists in a form that did not exist when Swiss Ephemeris was written.

---

## IV. Analytical and Software Capabilities

### 14. Declination as a Full Chart Layer

Most astrological software treats the chart as a one-dimensional object: ecliptic longitude. Declination — the angular distance north or south of the celestial equator — is either ignored or offered as a minor addon.

This is a profound impoverishment. Ptolemy recognized **parallel aspects** (two bodies at the same declination) as equivalent in strength to conjunctions. Renaissance astrologers routinely worked with both longitude and declination. The reduction to longitude-only is a software limitation that became a conceptual habit.

With full 3D Cartesian position vectors from SPICE/JPL, Moira computes declination as naturally as ecliptic longitude. This enables:

- **Parallels of declination**: Two planets at the same declination, same hemisphere — Ptolemy's "parallel conjunction," often stronger than a longitudinal conjunction
- **Contraparallels**: Same declination, opposite hemispheres — equivalent to a longitudinal opposition
- **Out-of-bounds planets**: Any body exceeding the Sun's maximum declination of ±23°26' is beyond the Sun's apparent path — a condition associated with unconventional, boundary-breaking expression. Moira computes this precisely for every body including asteroids
- **Declination-based primary directions**: An entirely separate stream of directions operating in declination space rather than right ascension

Swiss Ephemeris returns longitude and latitude. The declination layer requires the full coordinate transformation pipeline that most software never bothers to expose. Moira does not make this choice — declination is a first-class coordinate in every calculation.

In practice, this is largely already built:
- `SkyPosition` (planets.py) carries `right_ascension` and `declination` as first-class fields, populated by the full 8-step apparent-position pipeline
- `find_declination_aspects()` (aspects.py) detects parallels and contraparallels from any dict of declinations
- `find_out_of_bounds()` (aspects.py) detects bodies exceeding the obliquity threshold, returning `OutOfBoundsBody` vessels with the signed declination, obliquity used, and excess beyond the boundary

The only thing that was genuinely missing was the OOB check. It is now implemented.

---

### 15. Synodic Phase Cycles for All Body Pairs

The Moon's synodic cycle — new moon, waxing crescent, first quarter, gibbous, full, waning — is the most familiar rhythmic structure in astrology. But every pair of bodies has a synodic cycle of the same structure.

Jupiter and Saturn complete a synodic cycle every **19.9 years**. At their conjunction (the "new" phase), a new cycle begins. At their opposition (the "full" phase), the cycle reaches its culmination. The waxing and waning hemispheres carry qualitatively different meanings — just as they do for the Moon.

Venus's synodic cycle — from inferior conjunction through greatest elongation as morning star, superior conjunction, greatest elongation as evening star, back to inferior conjunction — is one of the most storied cycles in ancient astrology. The Babylonians tracked every Venus elongation meticulously.

What changes with Moira:

- The **phase angle** between any two of the 1.479 million bodies can be computed precisely — not just the traditional planets
- The **synodic cycle position** (0° = conjunction, 180° = opposition) is a continuous value, not just a categorical label
- The exact moment of **maximum elongation**, **station within the synodic cycle**, and **phase transitions** can be computed via root-finding to second-level precision
- **Mutual phase** between two bodies that are not Sun-centered (e.g., Jupiter-Neptune phase from Earth's perspective) is computationally identical

Swiss Ephemeris exposes raw positions. Computing synodic phase requires the subtraction, normalization, and interpretation that Moira builds on top.

---

### 16. Exact Astronomical Event Computation

In 1997, finding the exact moment of a planetary station required interpolation from pre-tabulated ephemeris data — typically to ±1 day precision. Finding the exact moment of a cazimi (planet within 17' of the Sun's center) required careful table work.

Bisection search on a smooth ephemeris function converges to sub-second precision in under 50 iterations — effectively instantaneous on modern hardware. This transforms what was laborious approximation into routine computation.

The following events are currently implemented with clean public APIs:

- **Planetary station** — `find_stations()`, `next_station()`, `retrograde_periods()` in `stations.py`:
  bisection on apparent longitude speed to locate the exact second a planet turns retrograde or direct
- **Solar conjunctions and phase events** — `next_conjunction()`, `conjunctions_in_range()`,
  `next_moon_phase()`, `moon_phases_in_range()` in `phenomena.py`: bisection on angular separation
  or Moon-Sun phase angle
- **Perihelion and aphelion** — `perihelion()`, `aphelion()` in `phenomena.py`: golden-section
  search on heliocentric distance
- **Greatest elongation** — `greatest_elongation()` in `phenomena.py`
- **Heliacal and acronychal planetary visibility** — `planet_heliacal_rising()`,
  `planet_heliacal_setting()`, `planet_acronychal_rising()`, `planet_acronychal_setting()` in
  `heliacal.py`: arcus-visionis model (Schaefer) for any observer location and atmospheric
  conditions
- **Eclipse contacts** — `eclipse_contacts.py`: first, second, maximum, third, fourth contacts
  for any solar or lunar eclipse, for any location

The following operate through the dignity engine rather than as standalone event-timing functions:

- **Solar condition boundaries (cazimi, combustion, under the beams)** — computed instantaneously
  at any given moment by `calculate_dignities()` and `calculate_condition_profiles()` in
  `dignities.py`; `find_phasis()` (also in `dignities.py`) scans a date range for the exact
  moment a planet crosses a solar-beam threshold. The angular thresholds are explicit policy
  parameters in `SolarConditionPolicy`.

None of these required new data. What changed is that the computation is no longer expensive.

---

### 17. Geodetic Astrology — The Zodiac Mapped to Earth

Geodetic astrology assigns zodiacal positions to geographic locations: each longitude on Earth corresponds to a zodiacal degree. Several competing systems exist (Johndro, Sepharial, Grimm), but the core idea is that the zodiac encodes geography as well as time.

In practice, this means:
- Every city has a "natal" Ascendant and Midheaven based on its geographic coordinates
- A planet transiting that degree "activates" the corresponding region of Earth
- A natal chart can be relocated not just astrologically (Astrocartography) but geodetically — mapping which places resonate with which planets in the natal

What has changed since 1997 is not the algorithm (which is simple coordinate arithmetic) but the **precision of geographic data** and the **breadth of bodies available**:

- With 887K asteroids, the geodetic positions of bodies named after cities, rivers, countries, and peoples can be cross-referenced against the actual locations those names refer to
- An asteroid named "Roma" can be compared to the geodetic position of Rome
- Geodetic charts for any of the 1.479M bodies can be generated for any location on Earth

The conceptual system is traditional. The scale at which it can now be investigated is not.

---

## V. Classical Techniques Reclaimed

There is a category of astrological technique that was not impossible in 1997 for lack of data or computational paradigm — but was so laborious, so rarely implemented fully, and so imprecise in software form, that it existed in theory more than practice. Modern computation does not merely make these faster. It restores them to the precision their inventors intended, removes the approximations that degraded them, and extends them to bodies their inventors could not have imagined.

---

### 18. Primary Directions — The Oldest Predictive Technique

Primary directions are the oldest surviving method of astrological prediction. They appear in Claudius Ptolemy's *Tetrabiblos* (2nd century AD), were refined by medieval Arabic astrologers (al-Qabisi, Abu Ma'shar), brought to systematic form by Regiomontanus (1467), and extended by later European masters through the 18th century.

The technique works by rotating the celestial sphere — simulating the diurnal motion of the sky after birth — and measuring how far a chart point must travel to reach a sensitive position. That arc, converted by a time key, yields a predicted year.

The calculation is geometrically complex:
- It requires precise **oblique ascension** for each chart point under the pole of the horizon
- **Semi-arc** calculations for planets above and below the horizon
- **Latitude treatment**: a planet not on the ecliptic requires projection to the ecliptic — a step that involves either dropping latitude (Ptolemy's method) or carrying it through the mundane sphere (the full method)
- **House system dependency**: Regiomontanus directions use a different geometric base than Placidus directions. Campanus, Morinus, and topocentric systems each yield different arcs
- **Time keys**: Naibod (0°59'08" per year), Ptolemy (1°00'00"), solar arc, and others yield different timing

In 1997, software implementations of primary directions almost universally:
- Ignored planetary latitude entirely, or simplified it
- Supported only one or two house systems
- Offered only Naibod and Ptolemy keys
- Could not extend directions to bodies beyond the traditional planets

Moira's primary-directions engine now includes broad house-system and latitude-doctrine support with explicit policy surfaces. The extension to every catalog body remains a roadmap boundary; current production usage is strongest on classical planetary and admitted point sets.

The stars as promissors or significators in primary directions — computed with sub-arcsecond precision against Gaia positions rather than estimated catalog values — is a level of accuracy no historical astrologer achieved and no 1997 software attempted.

---

### 19. Heliacal Rising and Setting — The Babylonian Timing System

Before horoscopic astrology existed, the Babylonians practiced **observational astrology** centered on heliacal phenomena: the first morning visibility of a star after a period of invisibility (heliacal rising), and the last evening visibility before it disappears into the Sun's glare (heliacal setting).

The heliacal rising of Sirius — when it first appeared before dawn after 70 days of invisibility — marked the Egyptian new year and predicted the Nile flood. The Babylonian Mul.Apin tablets (700 BC, but encoding observations from ~1000 BC) are organized around heliacal risings and settings as the primary calendar system.

Computing heliacal phenomena precisely requires:

1. **Star brightness** — the star's apparent magnitude (Gaia provides this for 1.46B stars)
2. **Solar elongation** — how far the star is from the Sun at the moment of interest
3. **Observer latitude** — the angle at which objects rise affects visibility
4. **Atmospheric extinction** — the atmosphere absorbs light near the horizon; the extinction coefficient depends on altitude, humidity, and aerosol conditions
5. **Arcus visionis** — the minimum solar depression angle at which a star of given magnitude becomes visible; this varies by star brightness and atmospheric conditions

The **arcus visionis** computation is a multi-factor equation that Ptolemy attempted in the *Tetrabiblos* and that modern researchers (Schaefer 1985, Helmantel 2000) have refined into tractable formulas. It requires the kind of floating-point computation that is trivially fast in Python but was genuinely expensive in 1997 C.

Moira can currently compute, for any observer location on any date:
- Planetary morning/evening visibility events through the heliacal planetary layer
- The **phase of morning vs. evening visibility** for admitted planets (morning star, evening star, under the beams)
- Acronychal planetary visibility events under the same policy surface
- Fixed-star heliacal rising and setting events through `stars.py`, including
  typed event vessels that preserve the search and visibility classification

This is the recovery of a timing system that predates the horoscope by at least a millennium, computed with a precision the Babylonians could not have imagined.

---

### 20. Planetary Nodes — The Orbital Intersections

Every planet's orbit is tilted relative to the ecliptic. The two points where its orbital plane intersects the ecliptic are its **nodes**: ascending (North) and descending (South). These are the same concept as the Moon's nodes — applied to every planet.

The planetary nodes are:
- **Heliocentric** — the intersection of the planet's orbit with the ecliptic plane, measured from the Sun
- **Slowly precessing** — they move, but over centuries, not years
- **Geometrically meaningful** — a planet conjunct its own node is at a point where it crosses the ecliptic; a solar or lunar eclipse near a planetary node has additional resonance

The nodes are used in cosmobiology (Ebertin's work), Uranian astrology, and some Hellenistic approaches. For the traditional planets, the nodes can be computed from orbital elements in JPL's DE series. For the newly discovered dwarf planets and TNOs, the nodes are derivable from their SPICE kernels.

What is new:

- The **nodes of Eris, Sedna, Makemake, and Haumea** — bodies whose orbits were unknown in 1997 — can now be precisely computed
- The **node of Chiron** (known since 1977 but not well-implemented in software) passes through approximately 19° Libra — a point with documented mundane significance
- Asteroid nodes: for any of the 887K numbered asteroids, the nodal positions can be extracted from orbital elements — a dataset of nearly a million additional sensitive points on the ecliptic

The precision of modern orbital mechanics makes these computations exact where fully modeled. In current Moira runtime, planetary-node support is strongest for the classical planetary set; full TNO/asteroid-node scale remains roadmap work.

---

## VI. Summary — The Impossible Made Possible

| Capability | Impossible in 1997 because... | Now possible because... |
|---|---|---|
| True topocentric fixed star positions | No stellar parallax for most stars | Gaia DR3: parallax for 1.46B stars |
| Ephemeris for 887,103 asteroids | Only ~10K numbered; no API | MPC + JPL Horizons API |
| Interstellar object charts | Unknown objects | Oumuamua (2017), Borisov (2019), 3I/ATLAS (2025) |
| Eris, Sedna, Makemake, Haumea charts | Undiscovered | Discovered 2002–2007 |
| Gonggong, Quaoar precision ephemeris | Unknown / unresolved | Discovered 2002–2007, SPK kernels available |
| Algol binary eclipse timing | Data not compiled for software | GCVS + linear ephemeris |
| Stellar color → classical quality | No large-scale photometric catalog | Gaia BP−RP photometry |
| Keplerian orbital elements for any kernel body | Pre-tabulated data only; no element extraction | `orbital_elements_at()` in `orbits.py`; roadmap: arbitrary integration via scipy/rebound |
| Physics-based hybrid ΔT model | Polynomial approximation only | Four-component model (secular + core-mantle + cryo + IERS residual) with ±1σ uncertainty |
| Statistical analysis across 60K charts | No digital chart corpus | Astro-Databank + Moira batch API |
| Asteroid name/mythology search | Too few asteroids | 887K bodies, mythological tagging |
| NEO proximity events in charts | Most NEAs undiscovered | CNEOS API + JPL Horizons |
| Galactic coordinate charts | Insufficient galactic data | ESA Gaia + modern galactic catalogs |
| Planet Nine hypothetical position | Undiscovered, not theorized | Batygin & Brown 2016 orbital elements |
| Asteroid family origin groupings | Not catalogued | Nesvorný (2015) catalog: 143,711 bodies, 119 families, bundled |
| Aspect qualification by physical origin (family resonance) | Concept did not exist | `find_resonant_aspects` + `resonance_network`; purely additive layer |
| 368 named asteroids by name, no setup required | ~20 in Swiss Ephemeris | Four bundled kernels + expanded `ASTEROID_NAIF` registry |
| Light-time vs. true star position choice | No stellar distances | Gaia parallax |
| 1.8 billion named/nameable stars | Only 118K with positions | Gaia DR3 complete |
| Exoplanet directions (5,600+ known worlds) | None confirmed in catalog | NASA Exoplanet Archive + host star positions |
| Declination as full chart layer (parallels, OOB) | Software convention, not impossibility | Full 3D vectors via SPICE; no additional cost |
| Synodic phase angle for any body pair | Raw positions only; no phase layer | Moira computes continuous phase for all 1.479M bodies |
| Exact event computation (stations, conjunctions, heliacal, eclipse contacts) | Expensive interpolation; table-limited | Bisection on ephemeris function; converges in <50 iterations |
| Geodetic astrology at full asteroid scale | Too few bodies for meaningful mapping | 887K bodies including city/country/culture names |
| Primary directions with full latitude + all house systems | Computationally laborious; latitude dropped | Full mundane sphere geometry; all house systems |
| Heliacal rising/setting for 1.46B stars | No brightness catalog; arcus visionis expensive | Gaia magnitudes + Schaefer atmospheric model |
| Planetary nodes of TNOs and dwarf planets | Bodies undiscovered | Modern orbital elements (partial runtime coverage; full-catalog is roadmap) |

---

## Drift Guardrail

To keep this doctrine truthful, treat claims as **implemented** only when they map to an existing public API and at least one validation path in `tests/`.

Swiss Ephemeris is an achievement of the 20th century.
Moira is built for the 21st.
