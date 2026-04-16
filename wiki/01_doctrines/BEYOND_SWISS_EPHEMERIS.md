# Beyond Swiss Ephemeris

**Swiss Ephemeris** was built in 1997 by Alois Treindl and Dieter Koch at Astrodienst.
It is a genuine achievement — a compressed, accurate, carefully designed C library that
served astrological computation for a generation.

It was also built in a different world.

The stellar catalog it uses was compiled from a satellite launched in 1989.
The asteroid count it was designed around was roughly 10,000 bodies.
The trans-Neptunian landscape it knew was Pluto and Chiron.
Its model of Earth's rotation is a polynomial fit.
It has no concept of stellar parallax for fixed stars.
It cannot name a body it was not pre-built for.

Moira is not built on those constraints.

This document describes where Moira extends beyond the design envelope of Swiss Ephemeris,
and where it makes different modern data and policy choices. It is not written to diminish
Swiss Ephemeris, but to describe what Moira actually computes and why.

---

## I. The Data That Did Not Exist

### Stars — Hipparcos to Gaia

Swiss Ephemeris draws its fixed-star data from the **Hipparcos catalog (1997)**:
118,218 stars, milliarcsecond astrometry, no parallax distances for the majority.

In June 2022, ESA released **Gaia DR3**: 1.46 billion stars with full parallax and proper
motion, radial velocities for 33.8 million, photometric color indices for 470 million.
Parallax precision for bright stars: **0.02 milliarcseconds** — fifty times better than
Hipparcos.

Moira's fixed-star surface is a **sovereign local registry of 1,809 curated named stars**,
every record sourced from Gaia DR3 at build time: ecliptic positions propagated to a
consistent epoch, proper motions, parallax distances, and BP-RP photometric color,
all embedded locally. Moira does not query Gaia at runtime. The data is owned.

What Gaia provenance changes is not cosmetic. It makes categories of computation possible
that simply did not exist before.

---

### Asteroids — Ten Thousand to Nearly a Million

When Swiss Ephemeris was built, roughly **10,000–15,000** asteroids were numbered.

The Minor Planet Center today lists **887,103 numbered minor planets**.
JPL Horizons tracks **1,479,000** in total.

This is not a quantitative improvement on the same landscape.
Every figure from Greek, Roman, Norse, Egyptian, Mesopotamian, Hindu, Celtic, Aztec,
and Polynesian mythology now has an asteroid. Thousands are named for scientists,
composers, cities, rivers, historical figures. The mythological substrate of the solar
system has expanded beyond anything the founders of modern astrology could have imagined.

**Moira ships 368 named bodies callable by name with no configuration required** —
the full classical main-belt canon from 1 Ceres through 1467 Mashona, all six centaurs,
and every named trans-Neptunian object in the bundled kernels:

```
asteroid_at("Eris", jd_tt)
asteroid_at("Sedna", jd_tt)
asteroid_at("Gonggong", jd_tt)
```

Swiss Ephemeris ships direct built-in support for Ceres, Pallas, Juno, Vesta, Chiron,
and Pholus. Additional asteroid coverage depends on separate asteroid ephemeris files,
with named lookup handled through catalog-number conventions and the `seasnam.txt` name
list rather than a bundled high-level named-body registry.

---

### New Worlds — A Solar System Discovered After 1997

The entire trans-Neptunian landscape was effectively invisible when Swiss Ephemeris was built.

| Body | Discovery | Notes |
|---|---|---|
| Quaoar | 2002 | Dwarf planet candidate; SPK kernel available |
| Sedna | 2003 | 11,400-year orbital period; 76 AU perihelion |
| Haumea | 2004 | Rings, two moons, rapid rotation |
| Eris | 2005 | More massive than Pluto; caused the reclassification |
| Makemake | 2005 | Dwarf planet |
| Gonggong | 2007 | Named 2020 for Chinese water deity |

Beyond dwarf planets, a category of object that could not have been anticipated:

**Interstellar visitors.** 1I/'Oumuamua (2017), 2I/Borisov (2019), and 3I/ATLAS (2025)
are confirmed objects from outside the solar system. Each passed through the inner solar
system on a hyperbolic trajectory. Each has an ecliptic longitude at every moment of its
passage. These bodies will never appear in Swiss Ephemeris's fixed data files.
Moira can compute their positions.

---

### Earth Rotation — Physics Over Polynomial

Swiss Ephemeris uses polynomial approximations for ΔT (TT − UT1) and treats Earth's
rotation as a smooth, predictable function.

The **IERS** (International Earth Rotation and Reference Systems Service) publishes
weekly Bulletin A updates — polar motion, UT1-UTC, celestial pole offsets — and monthly
definitive Bulletin B values. Earth's rotation is not smooth. It responds to atmospheric
loading, ocean tides, seismic events, and inner-core dynamics.

Moira uses a four-component physical model: secular trend from tidal braking and glacial
isostatic adjustment, core-mantle angular momentum from the Gillet et al. series,
cryosphere/hydrosphere contribution from GRACE/GRACE-FO LOD integrals, and an IERS
residual spline fitted to Bulletin B annual values. All source data is bundled locally.
Beyond the table epoch, the model extrapolates using only physical components, and
reports a calibrated ±1σ uncertainty via `delta_t_hybrid_uncertainty(year)`.

This is not a polynomial fit. It is a physical model of the Earth.

---

## II. What the New Data Makes Possible

### True Topocentric Fixed Stars

In 1997, "fixed stars" were treated as points on an infinite celestial sphere.
The concept of a topocentric correction for a star was meaningless because no one knew
how far most stars were.

We know now. Sirius is 8.6 light-years away. Procyon is 11.4 ly. Vega is 25 ly.
Arcturus is 37 ly.

For nearby stars, the parallax displacement between the geocenter and an observer on
Earth's surface is real and measurable. More significantly, the concept becomes exact:
when does this star actually rise *for you*, at your precise location?
With Gaia parallax, that computation is possible. Without it, it was not.

Every star in Moira's 1,809-star registry has a true topocentric position available
at any observer location.

---

### Stellar Color as Measured Spectral Fact

Ptolemy in the *Tetrabiblos* assigned astrological qualities to stars partly by color:
red stars like Antares carry Mars character; pale stars like Sirius carry Jupiter-Venus
character; yellow stars like Arcturus carry Saturn character. This was observational
and qualitative.

Gaia DR3 provides **BP-RP photometric color indices** for hundreds of millions of stars.
Every star in Moira's sovereign registry carries measured BP-RP color sourced from Gaia —
quantitative, not estimated. The classical color-quality mapping can be applied to
measured spectral reality rather than naked-eye impression.

---

### Light-Time and the Question of Now

When you observe Arcturus at a given ecliptic degree, you are seeing light that left
that star **37 years ago**. Sirius's light is 8.6 years old. The Moon's is 1.3 seconds.

All serious ephemerides correct for light travel time in positional calculations —
Moira does this in `corrections.py`. What Gaia makes newly possible is a further question:
*where is this star right now, physically, as opposed to where its light says it was?*

`star_light_time_split(name, jd_tt)` in `stars.py` returns `(observed, true)` —
a pair of `FixedStar` vessels. The observed position propagates proper motion to the
emission epoch; the true position propagates to the current moment. For stars without
valid parallax, the distinction is undefined and both positions are identical.

The choice between observed and true position is a philosophical question that
traditional astrology never had to confront because the data to ask it did not exist.
Moira can offer both.

---

### Asteroid Families — Physical Origin as Astrological Qualifier

The Hirayama asteroid families are clusters of bodies sharing nearly identical orbital
parameters — fragments of the same parent body shattered by collision billions of years
ago. Every member of the Koronis family, the Flora family, the Vesta family, the
Nysa-Polana complex: physically made of the same rock.

Moira bundles the **Nesvorný et al. (2015) catalog**: 143,711 numbered asteroids
assigned to 119 dynamical families.

```
asteroid_family(158)              → "Koronis(2)"
family_members("Vesta")           → 15,252 asteroid numbers
families_in_chart([158, 832, 4])  → {"Karin": [832], "Koronis(2)": [158], "Vesta": [4]}
```

When two asteroids of the same family form an aspect, that aspect carries a qualifier
beyond its geometry: both bodies are fragments of the same shattered world.
`find_resonant_aspects()` and `resonance_network()` implement this as a post-processing
layer on top of any aspect list — additive, not intrusive.

There is no precedent for this in any astrological software.

---

### Orbital Elements on Demand

Swiss Ephemeris works from pre-computed, compressed data files.
For anything not in those tables, it cannot compute.

`orbital_elements_at(body, jd_ut, reader)` in `orbits.py` extracts osculating Keplerian
elements — semi-major axis, eccentricity, inclination, argument of perihelion, longitude
of ascending node, mean anomaly, true anomaly — from SPICE state vectors at any epoch.
Any body with a kernel has its complete orbital element set available on demand,
without pre-tabulation.

---

## III. What Computation Recovers

### Primary Directions at Their Intended Precision

Primary directions are the oldest surviving method of astrological prediction.
They appear in Ptolemy's *Tetrabiblos*, were refined through medieval Arabic astronomy,
brought to systematic geometric form by Regiomontanus in 1467, and extended through
the 18th century.

The technique requires precise oblique ascension under the pole of the horizon,
semi-arc calculations for planets above and below the horizon, explicit treatment
of planetary latitude, and house-system-dependent geometry. In 1997, software
implementations almost universally ignored latitude or simplified it, supported
one or two house systems, and could not extend directions beyond the traditional planets.

Moira's primary directions engine provides explicit latitude doctrine, broad house-system
support, and a clear policy surface. The fixed-star promissor layer uses sub-arcsecond
Gaia positions — a precision no historical astrologer achieved and no 1997 software attempted.

---

### Heliacal Phenomena — The Babylonian Timing System Recovered

Before horoscopic astrology, the Babylonians organized time around heliacal phenomena:
the first morning visibility of a star after solar invisibility, and the last evening
visibility before disappearance. The heliacal rising of Sirius marked the Egyptian new
year. The Mul.Apin tablets (encoding observations from ~1000 BC) are organized around
these events as their primary calendar system.

Computing heliacal phenomena precisely requires star brightness, solar elongation,
observer latitude, atmospheric extinction, and the arcus visionis — the minimum solar
depression angle at which a body of given magnitude becomes visible. Ptolemy attempted
this computation in the *Tetrabiblos*. Modern researchers (Schaefer 1985, Helmantel 2000)
refined it into tractable formulas. The floating-point cost is trivial in Python and
was genuinely expensive in 1997 C.

Moira computes planetary and stellar heliacal and acronychal events for any observer
location on any date through the full Schaefer arcus visionis model. This is the
recovery of a timing system a millennium older than the horoscope, computed with
a precision the Babylonians could not have imagined.

---

### Exact Event Timing

In 1997, finding the exact moment of a planetary station required interpolation from
pre-tabulated data — typically ±1 day precision. Finding the exact cazimi required
careful table work.

Bisection search on a smooth ephemeris function converges to sub-second precision in
under 50 iterations. This transforms what was once laborious approximation into
routine computation.

Currently implemented with clean public APIs:

- **Planetary stations** — `find_stations()`, `next_station()`, `retrograde_periods()`:
  bisection on apparent longitude speed to the exact second
- **Solar conjunctions and phase events** — `next_conjunction()`, `moon_phases_in_range()`:
  bisection on angular separation or Moon-Sun phase angle
- **Perihelion and aphelion** — `perihelion()`, `aphelion()`: golden-section search on
  heliocentric distance
- **Greatest elongation** — `greatest_elongation()`
- **Solar condition thresholds** — cazimi, combustion, under the beams:
  `find_phasis()` scans for the exact crossing of any solar-beam threshold
- **Eclipse contacts** — `eclipse_contacts.py`: first, second, maximum, third, fourth
  contacts for any solar or lunar eclipse at any observer location

---

### Declination as a First-Class Coordinate

Most astrological software treats the chart as a one-dimensional object: ecliptic longitude.
Declination — the angular distance north or south of the celestial equator — is either
ignored or offered as a minor add-on. This is a software convention that became a
conceptual habit. Ptolemy recognized parallels of declination as equivalent in strength
to conjunctions.

With full 3D Cartesian position vectors from SPICE, declination costs nothing extra.

`SkyPosition` in `planets.py` carries right ascension and declination as first-class
fields, populated by the full 8-step apparent-position pipeline. `find_declination_aspects()`
detects parallels and contraparallels from any set of declinations. `find_out_of_bounds()`
detects bodies exceeding the Sun's maximum declination of ±23°26', returning signed
declination, obliquity used, and excess beyond the boundary.

---

## IV. New Territory

### Sedna — A Chart That Cannot Recurse

Sedna has an orbital period of approximately **11,400 years** and a perihelion distance
of 76 AU. It will not return to the inner solar system for eleven millennia.

Every classical astrological cycle is a return cycle — Saturn's at 29.5 years,
Chiron's at 50, Uranus half-return at 42. These recur within a human life.

Sedna's return occurs over civilizational timescales. Near perihelion in ~11,000 BC,
during the end of the last Ice Age and the dawn of agriculture. Current perihelion
passage around 2076. Next perihelion: approximately 13,400 AD.

Standard astrological concepts nearly break down at this scale. The computation is
perfectly precise. This is genuinely uncharted territory.

---

### Exoplanet Directions — Known Worlds Beyond the Solar System

Swiss Ephemeris contains no exoplanets. None were catalogued in usable form when it
was built. The first confirmed exoplanet around a Sun-like star — 51 Pegasi b —
was announced in October 1995, two years before SwissEph's release, into an essentially
empty catalog.

As of 2025, NASA's Exoplanet Archive lists **5,600+ confirmed exoplanets**.
Each has a host star. Each host star has a known ecliptic position.

| Body | Host Star | Distance | Notes |
|---|---|---|---|
| Proxima Centauri b | Proxima Centauri | 4.24 ly | Nearest known exoplanet; habitable zone |
| TRAPPIST-1e, f, g | TRAPPIST-1 | 40 ly | Three habitable-zone worlds in one system |
| Kepler-186f | Kepler-186 | 582 ly | First confirmed Earth-size planet in habitable zone |
| LHS 1140 b | LHS 1140 | 48 ly | Dense super-Earth; water candidate |

The direction of Proxima Centauri b from Earth is a fixed, computable ecliptic point.
A chart can note whether a planet is conjunct the direction of the nearest known world
outside the solar system. The philosophical implications for natal and mundane astrology
are genuinely open. The computation is exact, and the data exists in a form that
was not available when Swiss Ephemeris was written.

---

### The Galactic Frame

Swiss Ephemeris acknowledges the galactic center as a special point.
It does not work in galactic coordinates.

Moira computes galactic longitude and latitude for every planet, asteroid, and star —
transforming any chart into a galactic frame. The galactic center, anti-center,
and North Galactic Pole are available as chart angles. Galactic latitude of a planet
places it in context: within the dense stellar plane, or clear of it.

No mainstream astrological software works in this frame.

---

## Summary

| Capability | Impossible in 1997 | Now Possible |
|---|---|---|
| True topocentric fixed-star positions | No stellar parallax for most stars | Gaia DR3 parallax in sovereign 1,809-star registry |
| Stellar color as measured spectral fact | No photometric catalog at scale | Gaia BP-RP embedded per star |
| Light-time vs. true star position | No stellar distances | Gaia parallax; `star_light_time_split()` |
| 368 named asteroids, no setup | Default SwissEph: 4 + Chiron/Pholus | Four bundled kernels + named registry |
| Asteroid family physical-origin layer | Nesvorný catalog not compiled for software | 143,711 bodies, 119 families, bundled; `find_resonant_aspects()` |
| Orbital elements for any kernel body | Pre-tabulated data only | `orbital_elements_at()` in `orbits.py` |
| Eris, Sedna, Makemake, Haumea, Gonggong | Undiscovered | Discovered 2002–2007; SPK kernels available |
| Interstellar object charts | Unknown objects | 'Oumuamua (2017), Borisov (2019), 3I/ATLAS (2025) |
| Physics-based hybrid ΔT with uncertainty | Polynomial approximation only | Four-component physical model; ±1σ uncertainty |
| Primary directions with latitude doctrine | Latitude ignored or simplified | Explicit latitude and house-system policy |
| Heliacal phenomena (full Schaefer model) | Computationally expensive; rarely complete | Full arcus visionis for any body, any location, any date |
| Sub-second exact event timing | Interpolation from tables, ±1 day | Bisection on ephemeris function; <50 iterations |
| Declination as first-class coordinate | Software convention, not impossibility | Full pipeline; parallels, contraparallels, OOB for all bodies |
| Sedna civilizational timescale | Unknown body | Discovered 2003; orbital period ~11,400 years |
| Exoplanet directions | No catalog | 5,600+ confirmed; host-star ecliptic positions computable |
| Galactic coordinate frame for all bodies | Insufficient galactic structure data | Full galactic coordinates from SPICE state vectors |

---

## Architectural Directions

The following capabilities are valid extensions of the engine's current design
and will become public runtime surfaces as development continues:

- Full Gaia catalog expansion beyond the 1,809-star sovereign registry
- Live on-demand Horizons API fetch for arbitrary newly discovered objects
- Arbitrary orbit integration from initial conditions (for hypothetical bodies,
  newly discovered objects without SPK kernels, or encounter analysis)
- Full TNO and asteroid nodal positions at catalog scale
- Synodic phase cycle computation across the extended body catalog
