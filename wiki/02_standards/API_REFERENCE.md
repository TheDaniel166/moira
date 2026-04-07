# Moira API Reference

**Version:** 1.0.3
**Coverage:** 13 200 BC → 17 191 AD (JPL DE441)
**Import surface:** `import moira` provides the curated stable root, while `from moira.facade import ...` exposes the complete direct-import surface.

---

## Table of Contents

1. [Quick Start](#1-quick-start)
2. [API Architecture — Four-Tier Entry Points](#2-api-architecture--four-tier-entry-points)
3. [Core Types](#3-core-types)
4. [Moira Facade](#4-moira-facade)
5. [Ephemeris & Positions](#5-ephemeris--positions)
6. [Alternative Reference Frames](#6-alternative-reference-frames)
7. [Chart Structure](#7-chart-structure)
8. [Classical Techniques](#8-classical-techniques)
9. [Timing Techniques](#9-timing-techniques)
10. [Planetary Cycles Engine](#10-planetary-cycles-engine)
11. [Huber Method](#11-huber-method)
12. [Relational Techniques](#12-relational-techniques)
13. [Geography](#13-geography)
14. [Fixed Stars](#14-fixed-stars)
15. [Eclipses & Phenomena](#15-eclipses--phenomena)
16. [Harmograms — Spectral Harmonic Analysis](#16-harmograms--spectral-harmonic-analysis)
17. [Constellation Oracle](#17-constellation-oracle)
18. [Calendar & Time](#18-calendar--time)
19. [Policy Objects](#19-policy-objects)

---

## Conventions

- Sections labeled `fields` are intended to be exhaustive for the documented vessel unless explicitly marked otherwise.
- Rows or examples that use `...` are abbreviated for width only; they are shorthand, not alternate signatures.
- When a section says `summary`, that label is intentional and means the section is highlighting the most important fields rather than restating every implementation detail inline.
- Unless a section explicitly targets `moira.essentials`, `moira.classical`, `moira.predictive`, or a specialty submodule, direct symbol imports in this reference should be read as `from moira.facade import ...`; the top-level `moira` package does not re-export the full low-level surface.
- This reference prioritizes callable surfaces, principal vessels, and major policy types. `moira.facade.__all__` also includes many public truth/classification/profile dataclasses and enums that are not all restated inline section-by-section.

---

## 1. Quick Start

### Installation & Kernel

Moira requires an installed JPL planetary kernel before kernel-dependent
computations can run. `Moira()` auto-detects the first installed planetary
kernel from the supported set `de430.bsp`, `de440.bsp`, `de441.bsp`,
`de432.bsp`, `de431.bsp`, searched in this order of locations:

1. `~/.moira/kernels/`
2. `moira/kernels/` inside the installed package
3. `kernels/` in a development checkout

The package does not read a `MOIRA_KERNEL_PATH` environment variable. Large
kernels such as `de441.bsp` still need to be present locally; use
`moira-download-kernels` or `Moira.download_missing_kernels()` to install the
missing files into the user kernel directory.

```python
from moira.facade import Moira
from datetime import datetime, timezone

m = Moira()                       # auto-detects the first installed planetary kernel
# or
m = Moira(kernel_path="/data/de441.bsp")
```

### First chart

```python
from moira.facade import Moira, Body, HouseSystem
from datetime import datetime, timezone

m = Moira()
dt = datetime(1988, 4, 4, 14, 30, tzinfo=timezone.utc)

chart = m.chart(dt)
for name, planet in chart.planets.items():
    print(f"{name:10s}  {planet.longitude:.4f}°  speed {planet.speed:+.4f}°/day")

houses = m.houses(dt, latitude=51.5074, longitude=-0.1278, system=HouseSystem.PLACIDUS)
print(f"ASC {houses.asc:.3f}°  MC {houses.mc:.3f}°")
```

### Aspects

```python
aspects = m.aspects(chart)
for a in aspects:
    print(f"{a.body1} {a.aspect} {a.body2}  orb {a.orb:+.2f}°")
```

### Transits to natal point

```python
from moira.facade import jd_from_datetime
from datetime import datetime, timezone

natal_sun = chart.planets["Sun"].longitude          # e.g. 14.7°
jd_start  = jd_from_datetime(datetime(2024, 1, 1, tzinfo=timezone.utc))
jd_end    = jd_from_datetime(datetime(2025, 1, 1, tzinfo=timezone.utc))

for event in m.transits(Body.JUPITER, natal_sun, jd_start, jd_end):
    print(event.jd_ut, event.relation.relation_kind)
```

---

## 2. API Architecture — Four-Tier Entry Points

Moira exposes its surface through four distinct import points. The tier modules are cumulative. The root package is intentionally curated, while `moira.facade` is the complete direct-import surface.

```
moira.essentials   ←  Beginner surface: chart, houses, aspects, sidereal
       ↓
moira.classical    ←  Adds: dignities, lots, fixed stars, time lords,
                           profections, Vedic, midpoints, mansions
       ↓
moira.predictive   ←  Adds: transits, progressions, synastry, eclipses,
                           returns, stations, void-of-course, electional
       ↓
moira.facade      ←  Complete direct-import surface: every subsystem

moira            ←  Curated stable root: Moira, core types, JD/sidereal helpers,
            selected visibility, harmogram, orbital, and policy surfaces
```

### `moira.essentials` — Beginner surface

```python
from moira.essentials import Moira, Chart, Body, HouseSystem
from moira.essentials import PlanetData, SkyPosition, CartesianPosition
from moira.essentials import NodeData, HouseCusps, AspectData
from moira.essentials import CalendarDateTime, DeltaTPolicy
from moira.essentials import julian_day, jd_from_datetime, datetime_from_jd
from moira.essentials import calendar_from_jd, calendar_datetime_from_jd
from moira.essentials import format_jd_utc, safe_datetime_from_jd, delta_t
from moira.essentials import calculate_houses, assign_house
from moira.essentials import find_aspects, AspectPolicy, DEFAULT_POLICY
from moira.essentials import Ayanamsa, ayanamsa, tropical_to_sidereal
from moira.essentials import sidereal_to_tropical, list_ayanamsa_systems
```

Use this when you only need: natal chart positions, house cusps, basic aspects, and sidereal conversions. It is suitable for first-time users and lightweight integrations.

### `moira.classical` — Traditional astrology surface

```python
from moira.classical import *   # includes everything from essentials, plus:
```

Adds the full classical and traditional toolkit:

| Added domain | Key symbols |
|---|---|
| Houses (full) | `HouseSystemFamily`, `HouseSystemCuspBasis`, `classify_house_system`, `HousePlacement`, `HouseBoundaryProfile`, `HouseAngularity`, `compare_systems`, `compare_placements`, `distribute_points`, `Quadrant`, `quadrant_emphasis`, `DiurnalQuadrant`, `diurnal_emphasis` |
| Aspects (full) | `AspectDefinition`, `ASPECT_TIERS`, `CANONICAL_ASPECTS`, `AspectDomain`, `AspectFamily`, `AspectTier`, `MotionState`, `AspectClassification`, `aspect_strength`, `aspect_motion_state`, `find_declination_aspects`, `find_patterns`, `DeclinationAspect` |
| Dignities | `calculate_dignities`, `calculate_receptions`, `EssentialDignityKind`, `AccidentalConditionKind`, `PlanetaryDignity`, `sect_light`, `is_day_chart`, `almuten_figuris`, `mutual_receptions` |
| Arabic Parts | `calculate_lots`, `ArabicPart`, `ArabicPartsService`, `list_parts` |
| Midpoints | `calculate_midpoints`, `Midpoint`, `MidpointsService`, `midpoint_tree`, `planetary_pictures` |
| Antiscia | `find_antiscia`, `AntisciaAspect`, `antiscion`, `contra_antiscion` |
| Fixed stars | `star_at`, `all_stars_at`, `FixedStar`, `list_stars`, `find_stars`, `star_magnitude` |
| Lunar mansions | `mansion_of`, `all_mansions_at`, `MANSIONS` |
| Profections | `annual_profection`, `monthly_profection`, `profection_schedule` |
| Time lords | `firdaria`, `zodiacal_releasing`, `vimshottari` |
| Vedic divisional | `navamsa`, `saptamsa`, `dashamansa`, `dwadashamsa`, `trimshamsa` |
| Planetary hours | `planetary_hours_for_day` |
| Huber | `house_zones`, `age_point`, `chart_intensity_profile` |

### `moira.predictive` — Forecasting surface

```python
from moira.predictive import *   # includes everything from classical, plus:
```

Adds the complete forecasting and relationship toolkit:

| Added domain | Key symbols |
|---|---|
| Transits | `find_transits`, `next_transit`, `find_ingresses`, `next_ingress`, `TransitEvent`, `IngressEvent`, `TransitSearchPolicy` |
| Progressions | `secondary_progression`, `solar_arc`, `solar_arc_right_ascension`, `naibod_longitude`, `tertiary_progression`, `tertiary_ii_progression`, `converse_*` variants, `minor_progression`, `daily_house_frame` |
| Primary directions | `speculum`, `find_primary_arcs`, `SpeculumEntry`, `PrimaryArc` |
| Synastry | `synastry_aspects`, `house_overlay`, `mutual_house_overlays`, `composite_chart`, `davison_chart`, `CompositeChart`, `DavisonChart` |
| Eclipses | `EclipseData`, `EclipseEvent`, `EclipseCalculator`, `LunarEclipseAnalysis`, `next_solar_eclipse_at_location` |
| Returns | `solar_return`, `lunar_return`, `planet_return`, `half_return_series`, `lifetime_returns` |
| Stations | `find_stations`, `is_retrograde`, `retrograde_periods`, `StationEvent` |
| Void of course | `void_of_course_window`, `is_void_of_course`, `next_void_of_course` |
| Phenomena | `greatest_elongation`, `perihelion`, `aphelion`, `next_moon_phase`, `moon_phases_in_range`, `next_conjunction` |

### `moira.facade` and `moira` — Complete surface vs curated root

```python
import moira                 # curated stable root, includes Moira and core types
from moira.facade import *   # complete direct-import surface
```

`moira.facade` adds every remaining subsystem not exposed by the predictive tier.
The top-level `moira` package does not mirror the entire facade export list; use
it when you want the primary facade class plus the curated stable root, and use
`moira.facade` when you want direct imports for the full low-level API.

The complete facade surface adds every remaining subsystem not exposed by the predictive tier:

- Heliacal visibility (5-criterion model)
- Parans and paran field analysis
- Astro*Carto*Graphy, local space, geodetic charts
- Galactic coordinates
- Uranian / Hamburg School bodies
- Occultations and close approaches
- Harmograms (spectral harmonic analysis)
- Solar System Barycenter chart
- Planetocentric positions
- Received-light (light-cone) positions
- Variable and multiple star systems
- Constellations oracle (48 IAU constellations)
- Sothic cycle, Egyptian calendar
- Longevity (hyleg/alcocoden)

---

## 3. Core Types


### `Body` — celestial body constants

```python
from moira.facade import Body

Body.SUN       Body.MOON      Body.MERCURY   Body.VENUS
Body.MARS      Body.JUPITER   Body.SATURN    Body.URANUS
Body.NEPTUNE   Body.PLUTO

Body.TRUE_NODE   Body.MEAN_NODE   Body.LILITH

Body.EARTH       # for heliocentric computations
```

### `HouseSystem` — house system constants

```python
from moira.facade import HouseSystem

HouseSystem.PLACIDUS       HouseSystem.KOCH         HouseSystem.CAMPANUS
HouseSystem.REGIOMONTANUS  HouseSystem.EQUAL        HouseSystem.WHOLE_SIGN
HouseSystem.PORPHYRY       HouseSystem.MORINUS      HouseSystem.ALCABITIUS
HouseSystem.TOPOCENTRIC    HouseSystem.MERIDIAN     HouseSystem.VEHLOW
HouseSystem.SUNSHINE       HouseSystem.AZIMUTHAL    HouseSystem.CARTER
HouseSystem.KRUSINSKI      HouseSystem.APC          HouseSystem.PULLEN_SD
HouseSystem.PULLEN_SR
```

### `Ayanamsa` — sidereal reference frame

```python
from moira.facade import Ayanamsa

Ayanamsa.LAHIRI         # IAU standard; default for Vedic work
Ayanamsa.FAGAN_BRADLEY
Ayanamsa.RAMAN
Ayanamsa.TRUE_CHITRAPAKSHA
Ayanamsa.KRISHNAMURTI
Ayanamsa.SASSANIAN
# + dozens more — see list_ayanamsa_systems()
```

### `AspectDefinition` and `ASPECT_TIERS`

`AspectDefinition` specifies a single aspect angle with its name, symbol, orb, and tier. Used to add custom aspects or override defaults.

```python
from moira.facade import AspectDefinition, ASPECT_TIERS

custom = AspectDefinition(name="Quintile", symbol="Q", angle=72.0, orb=2.0, tier=3)
```

`ASPECT_TIERS`: `dict[int, str]` mapping tier number → descriptive label (e.g. `{1: "Major", 2: "Minor", 3: "Harmonic"}`). Used to filter aspects by significance level via `AspectPolicy`.

### `Chart` — planetary snapshot vessel

Produced by `Moira.chart()`. Carries the full positional state of the sky at
one Julian Day.

| Field | Type | Description |
|---|---|---|
| `jd_ut` | `float` | Julian Day (UT) of the snapshot |
| `planets` | `dict[str, PlanetData]` | Geocentric ecliptic positions |
| `nodes` | `dict[str, NodeData]` | Lunar nodes and Lilith |
| `obliquity` | `float` | True obliquity of the ecliptic (°) |
| `delta_t` | `float` | ΔT in seconds |

**Properties:**

| Property | Returns | Description |
|---|---|---|
| `datetime_utc` | `datetime` | UTC datetime for this snapshot |
| `calendar_utc` | `CalendarDateTime` | BCE-safe calendar breakdown |

**Methods:**

| Method | Returns | Description |
|---|---|---|
| `longitudes(include_nodes=True)` | `dict[str, float]` | Flat dict of body → ecliptic longitude |
| `speeds()` | `dict[str, float]` | Body → daily longitude speed (°/day) |

### `PlanetData` — single planet position

| Field | Type | Description |
|---|---|---|
| `longitude` | `float` | Ecliptic longitude, tropical (°) |
| `latitude` | `float` | Ecliptic latitude (°) |
| `speed` | `float` | Daily motion in longitude (negative = retrograde) |
| `distance` | `float` | Distance from Earth (km) |

### `NodeData` — lunar node position

| Field | Type | Description |
|---|---|---|
| `longitude` | `float` | Ecliptic longitude (°) |
| `speed` | `float` | Daily motion (°/day) |

### `SkyPosition` — topocentric equatorial/horizontal

| Field | Type | Description |
|---|---|---|
| `right_ascension` | `float` | Apparent RA (°) |
| `declination` | `float` | Apparent Dec (°) |
| `altitude` | `float` | Altitude above horizon (°) |
| `azimuth` | `float` | Azimuth, North = 0° (°) |
| `distance` | `float` | Distance (km) |

### `HouseCusps` — computed house frame

| Field | Type | Description |
|---|---|---|
| `cusps` | `list[float]` | 12 house cusp longitudes (°), index 0 = cusp 1 |
| `asc` | `float` | Ascendant (°) |
| `mc` | `float` | Midheaven (°) |
| `armc` | `float` | ARMC — Sidereal time × 15 (°) |
| `vertex` | `float` | Vertex longitude (°) |
| `eq_asc` | `float` | Equatorial Ascendant (°) |
| `system` | `str` | HouseSystem constant used |

---

## 4. Moira Facade

`Moira(kernel_path=None)` is the primary entry point. All methods convert
`datetime` inputs to JD internally. Naïve datetimes are treated as UTC.

### Construction

```python
m = Moira()
m = Moira(kernel_path="/path/to/de441.bsp")
```

Construction is tolerant: if no planetary kernel is currently available, the
instance still initializes and defers failure until a kernel-dependent method
is called. Those calls raise `MissingEphemerisKernelError` with a diagnostic
message.

### Kernel readiness & management

| Member | Returns | Description |
|---|---|---|
| `is_kernel_available()` | `bool` | Whether a planetary kernel is ready right now |
| `get_kernel_status()` | `str` | Human-readable kernel readiness message |
| `kernel_status` | `str` | Property alias of `get_kernel_status()` |
| `available_kernels` | `list[str]` | Installed planetary and supplemental kernel filenames |
| `configure_kernel_path(path)` | `None` | Configure and validate an explicit planetary kernel path |
| `download_missing_kernels(interactive=False)` | `None` | Download missing kernels into the standard user directory |

### Core chart methods

| Method | Returns | Description |
|---|---|---|
| `chart(dt, bodies=None, include_nodes=True, observer_lat=None, observer_lon=None, observer_elev_m=0.0)` | `Chart` | Complete planetary snapshot; supply observer coords for topocentric Moon |
| `houses(dt, latitude, longitude, system=HouseSystem.PLACIDUS)` | `HouseCusps` | House cusps, angles, ARMC |
| `sky_position(dt, body, latitude, longitude, elevation_m=0.0)` | `SkyPosition` | Apparent topocentric RA/Dec + altitude/azimuth |
| `sidereal_chart(dt, ayanamsa_system=Ayanamsa.LAHIRI, bodies=None)` | `dict[str, float]` | Body → sidereal longitude |
| `heliocentric(dt, bodies=None)` | `dict[str, HeliocentricData]` | Heliocentric ecliptic positions |
| `phase(body, dt)` | `dict` | Phase angle, illumination, angular diameter, apparent magnitude |
| `twilight(dt, latitude, longitude)` | `TwilightTimes` | Civil/nautical/astronomical twilight times |

### Aspects & patterns

| Method | Returns | Description |
|---|---|---|
| `aspects(chart, orbs=None, include_minor=True)` | `list[AspectData]` | All natal aspects |
| `patterns(chart, orb_factor=1.0)` | `list[AspectPattern]` | Named aspect patterns built from the chart's positions and aspects |
| `midpoints(chart, planet_set="classic")` | `list[Midpoint]` | Planetary midpoints for the requested body set |
| `midpoints_to_point(chart, longitude, orb=1.5)` | `list[tuple[Midpoint, float]]` | Midpoints falling at a given longitude, paired with absolute orb |
| `harmonic(chart, number)` | `list[HarmonicPosition]` | Harmonic chart positions |
| `antiscia(chart, orb=1.0)` | `list[AntisciaAspect]` | Antiscia and contra-antiscia aspects |

### Dignities & essential condition

| Method | Returns | Description |
|---|---|---|
| `dignities(chart, houses)` | `list[PlanetaryDignity]` | Essential and accidental dignities |
| `lots(chart, houses)` | `list[ArabicPart]` | Arabic Parts / Hermetic Lots |
| `mutual_receptions(chart, by_exaltation=False)` | `list[tuple]` | `(planet_a, planet_b, type)` mutual reception triples |

### Classical techniques

| Method | Returns | Description |
|---|---|---|
| `profection(natal_asc, natal_dt, current_dt, natal_positions=None)` | `ProfectionResult` | Annual profection house and time lord |
| `nakshatras(chart, ayanamsa_system=Ayanamsa.LAHIRI)` | `dict[str, NakshatraPosition]` | Nakshatra for each planet |
| `planetary_hours(dt, latitude, longitude)` | `PlanetaryHoursDay` | Day and night planetary hour rulers |

### Timing techniques

| Method | Returns | Description |
|---|---|---|
| `transits(body, target_lon, jd_start, jd_end)` | `list[TransitEvent]` | All transits of a body to a natal point |
| `ingresses(body, jd_start, jd_end)` | `list[IngressEvent]` | All sign ingresses in a date range |
| `next_ingress(body, jd_start, max_days=None)` | `IngressEvent \| None` | Next sign ingress of any kind |
| `next_ingress_into(body, sign, jd_start, max_days=None)` | `IngressEvent \| None` | Next entry into a specific sign |
| `solar_return(natal_sun_lon, year)` | `float` | JD UT of the Solar Return in a calendar year |
| `lunar_return(natal_moon_lon, jd_start)` | `float` | JD UT of the next Lunar Return |
| `planet_return(body, natal_lon, jd_start, direction="direct")` | `float` | JD UT of the next planetary return |
| `syzygy(jd)` | `tuple[float, str]` | `(jd_ut, kind)` of prenatal syzygy |
| `stations(body, jd_start, jd_end)` | `list[StationEvent]` | Retrograde and direct stations |
| `retrograde_periods(body, jd_start, jd_end)` | `list[tuple[float, float]]` | List of `(jd_start, jd_end)` retrograde intervals |

### Progressions & directions

| Method | Returns | Description |
|---|---|---|
| `progression(natal_dt, target_dt, bodies=None)` | `ProgressedChart` | Secondary progression (1 day = 1 year) |
| `solar_arc_directions(natal_dt, target_dt, bodies=None)` | `ProgressedChart` | Solar Arc directed chart |
| `solar_arc_directions_ra(natal_dt, target_dt, bodies=None)` | `ProgressedChart` | Solar Arc in right ascension |
| `naibod_in_longitude(natal_dt, target_dt, bodies=None)` | `ProgressedChart` | Naibod directions in ecliptic longitude |
| `naibod_in_right_ascension(natal_dt, target_dt, bodies=None)` | `ProgressedChart` | Naibod directions in right ascension |
| `tertiary_progression(natal_dt, target_dt, bodies=None)` | `ProgressedChart` | Tertiary progression (1 day = 1 lunar month) |
| `tertiary_ii_progression(natal_dt, target_dt, bodies=None)` | `ProgressedChart` | Tertiary II / Klaus Wessel |
| `minor_progression(natal_dt, target_dt, bodies=None)` | `ProgressedChart` | Minor progression (1 lunar month = 1 year) |
| `ascendant_arc_directions(natal_dt, target_dt, latitude, longitude, bodies=None)` | `ProgressedChart` | Ascendant Arc directed chart |
| `daily_house_frame(natal_dt, target_dt, latitude, longitude, system=...)` | `HouseCusps` | Daily Houses progressed frame |
| `converse_progression(natal_dt, target_dt, bodies=None)` | `ProgressedChart` | Converse Secondary Progressed |
| `converse_solar_arc(natal_dt, target_dt, bodies=None)` | `ProgressedChart` | Converse Solar Arc |
| `converse_solar_arc_ra(natal_dt, target_dt, bodies=None)` | `ProgressedChart` | Converse Solar Arc in RA |
| `converse_naibod_in_longitude(natal_dt, target_dt, bodies=None)` | `ProgressedChart` | Converse Naibod in longitude |
| `converse_naibod_in_right_ascension(natal_dt, target_dt, bodies=None)` | `ProgressedChart` | Converse Naibod in RA |
| `converse_tertiary_progression(natal_dt, target_dt, bodies=None)` | `ProgressedChart` | Converse Tertiary |
| `converse_tertiary_ii_progression(natal_dt, target_dt, bodies=None)` | `ProgressedChart` | Converse Tertiary II |
| `converse_minor_progression(natal_dt, target_dt, bodies=None)` | `ProgressedChart` | Converse Minor |
| `duodenary_progression(natal_dt, target_dt, bodies=None)` | `ProgressedChart` | Duodenary progression |
| `converse_duodenary_progression(natal_dt, target_dt, bodies=None)` | `ProgressedChart` | Converse duodenary progression |
| `quotidian_solar_progression(natal_dt, target_dt, bodies=None)` | `ProgressedChart` | Solar quotidian progression |
| `converse_quotidian_solar_progression(natal_dt, target_dt, bodies=None)` | `ProgressedChart` | Converse solar quotidian progression |
| `quotidian_lunar_progression(natal_dt, target_dt, bodies=None)` | `ProgressedChart` | Lunar quotidian progression |
| `converse_quotidian_lunar_progression(natal_dt, target_dt, bodies=None)` | `ProgressedChart` | Converse lunar quotidian progression |
| `planetary_arc_directions(natal_dt, target_dt, arc_body, bodies=None)` | `ProgressedChart` | Planetary-arc directed chart |
| `converse_planetary_arc_directions(natal_dt, target_dt, arc_body, bodies=None)` | `ProgressedChart` | Converse planetary-arc directed chart |
| `speculum(chart, houses, geo_lat)` | `list[SpeculumEntry]` | Placidus mundane speculum |
| `primary_directions(chart, houses, geo_lat, max_arc=90.0, include_converse=True, significators=None, promissors=None)` | `list[PrimaryArc]` | Placidus mundane primary direction arcs |

### Hellenistic & Vedic time lords

| Method | Returns | Description |
|---|---|---|
| `firdaria(natal_dt, natal_chart, natal_houses=None)` | `list[FirdarPeriod]` | Persian Firdaria sequence from birth |
| `zodiacal_releasing(lot_longitude, natal_dt, levels=4)` | `list[ReleasingPeriod]` | Zodiacal Releasing from a Lot |
| `vimshottari_dasha(natal_chart, natal_dt, levels=2, ayanamsa_system=Ayanamsa.LAHIRI)` | `list[DashaPeriod]` | Vimshottari Dasha sequence from Moon nakshatra |

### Synastry & relationship charts

| Method | Returns | Description |
|---|---|---|
| `synastry_aspects(chart_a, chart_b, tier=2, orbs=None, orb_factor=1.0, include_nodes=True)` | `list[AspectData]` | Inter-aspects between two natal charts |
| `house_overlay(chart_source, target_houses, include_nodes=True, source_label="A", target_label="B")` | `SynastryHouseOverlay` | Place chart_source planets in target_houses |
| `mutual_house_overlays(chart_a, houses_a, chart_b, houses_b, include_nodes=True)` | `MutualHouseOverlay` | Both overlay directions in one call |
| `composite_chart(chart_a, chart_b, houses_a=None, houses_b=None)` | `CompositeChart` | Midpoint composite |
| `composite_chart_reference_place(chart_a, chart_b, houses_a, houses_b, reference_latitude, house_system=...)` | `CompositeChart` | Reference-place composite house method |
| `davison_chart(dt_a, lat_a, lon_a, dt_b, lat_b, lon_b, house_system=...)` | `DavisonChart` | Davison Relationship Chart (spherical midpoint time + location) |
| `davison_chart_uncorrected(...)` | `DavisonChart` | Davison with arithmetic midpoints |
| `davison_chart_reference_place(dt_a, dt_b, ref_lat, ref_lon, house_system=...)` | `DavisonChart` | Davison with midpoint time and explicit place |
| `davison_chart_spherical_midpoint(...)` | `DavisonChart` | Davison with midpoint time and spherical geographic midpoint |
| `davison_chart_corrected(...)` | `DavisonChart` | Davison with midpoint location and corrected time |

### Geography

| Method | Returns | Description |
|---|---|---|
| `astrocartography(chart, observer_lat=0.0, observer_lon=0.0, bodies=None, lat_step=2.0)` | `list[ACGLine]` | ACG lines (MC/IC/ASC/DSC) for all planets |
| `local_space(chart, latitude, longitude, bodies=None)` | `list[LocalSpacePosition]` | Horizon azimuth and altitude for each planet |
| `gauquelin_sectors(chart, latitude, longitude, bodies=None)` | `list[GauquelinPosition]` | Gauquelin sector placements for chart bodies at a location |

### Fixed stars, mansions & parans

| Method | Returns | Description |
|---|---|---|
| `fixed_star(name, dt)` | `FixedStar` | Unified star position enriched with Gaia DR3 data |
| `heliacal_rising(star_name, dt, latitude, longitude)` | `float \| None` | JD UT of the next heliacal rising |
| `heliacal_setting(star_name, dt, latitude, longitude)` | `float \| None` | JD UT of the next heliacal setting |
| `heliacal_rising_event(star_name, dt, latitude, longitude)` | `HeliacalEvent` | Full heliacal-rising event vessel with classification metadata |
| `heliacal_setting_event(star_name, dt, latitude, longitude)` | `HeliacalEvent` | Full heliacal-setting event vessel with classification metadata |
| `lunar_mansions(chart)` | `dict[str, MansionPosition]` | Arabic lunar mansion placement for chart bodies |
| `parans(natal_dt, latitude, longitude, bodies=None, orb_minutes=4.0)` | `list[Paran]` | Paran crossings for the chart date and location |

### Alternative frames & specialty coordinates

| Method | Returns | Description |
|---|---|---|
| `planetary_nodes(dt)` | `dict[str, OrbitalNode]` | Heliocentric orbital nodes and apsides for the planets |
| `planetocentric(observer, dt, bodies=None)` | `dict[str, PlanetocentricData]` | Positions as seen from the center of the observer body |
| `ssb_chart(dt, bodies=None)` | `dict[str, SSBPosition]` | Solar System barycenter positions in the standard of-date ecliptic frame |
| `received_light(dt, bodies=None)` | `dict[str, ReceivedLightPosition]` | Apparent received-light positions with explicit light-cone geometry |
| `galactic_chart(chart, bodies=None)` | `list[GalacticPosition]` | Galactic longitude/latitude for chart bodies |
| `galactic_angles(chart)` | `dict[str, tuple[float, float]]` | Ecliptic long/lat of major galactic reference points |
| `uranian(dt)` | `dict[str, UranianPosition]` | Positions of the eight Uranian/Hamburg School bodies |
| `geodetic(chart, zodiac="tropical", ayanamsa_system=None)` | `GeodeticChart` | Geodetic chart frame derived from planetary longitudes |
| `geodetic_planet_equivalents(chart, bodies=None, zodiac="tropical", ayanamsa_system=None)` | `dict[str, float]` | Geodetic longitude equivalents for selected bodies |
| `synodic_phase(body1, body2, dt)` | `dict[str, float \| str]` | Synodic separation, cycle fraction, and phase label for two bodies |

### Phenomena & occultations

| Method | Returns | Description |
|---|---|---|
| `phenomena(body, jd_start, jd_end)` | `list[PhenomenonEvent]` | Greatest elongations, perihelion, and aphelion events in a range |
| `moon_phases(jd_start, jd_end)` | `list[PhenomenonEvent]` | All eight standard Moon phases in a date range |
| `next_conjunction(body1, body2, jd_start, max_days=1200.0)` | `PhenomenonEvent \| None` | Next conjunction of two bodies |
| `conjunctions(body1, body2, jd_start, jd_end)` | `list[PhenomenonEvent]` | All conjunctions of two bodies in a date range |
| `resonance(body1, body2)` | `OrbitalResonance` | Best-fit orbital resonance relation between two bodies |
| `occultations(jd_start, jd_end, targets=None)` | `list[LunarOccultation]` | Lunar occultations of the default planet set or supplied targets |
| `close_approaches(body1, body2, jd_start, jd_end, max_sep_deg=1.0)` | `list[CloseApproach]` | Close approaches between two bodies in a date range |

### Traditional, historical & diagnostic methods

| Method | Returns | Description |
|---|---|---|
| `longevity(chart, houses)` | `HylegResult` | Traditional hyleg and alcocoden longevity analysis |
| `sothic_cycle(latitude, longitude, year_start, year_end, arcus_visionis=10.0)` | `list[SothicEntry]` | Year-by-year heliacal risings of Sirius across a date span |
| `sothic_epoch_finder(latitude, longitude, year_start, year_end, tolerance_days=1.0)` | `list[SothicEpoch]` | Candidate Sothic epochs across a year range |
| `egyptian_date(dt, epoch_jd=None)` | `EgyptianDate` | Egyptian civil calendar date for a datetime |

### Variable & multiple stars

| Method | Returns | Description |
|---|---|---|
| `variable_star_phase(name, dt)` | `float` | Current variable-star phase at a datetime |
| `variable_star_magnitude(name, dt)` | `float` | Estimated V magnitude at a datetime |
| `variable_star_next_minimum(name, dt)` | `float \| None` | JD of the next primary minimum |
| `variable_star_next_maximum(name, dt)` | `float \| None` | JD of the next maximum |
| `variable_star_minima(name, jd_start, jd_end)` | `list[float]` | All minima JDs in a range |
| `variable_star_maxima(name, jd_start, jd_end)` | `list[float]` | All maxima JDs in a range |
| `variable_star_quality(name, dt)` | `dict[str, float \| bool]` | Phase, magnitude, benefic/malefic quality metrics, and eclipse state |
| `multiple_star_separation(name, dt, aperture_mm=100.0)` | `dict` | Separation, PA, resolvability, and brightness summary |
| `multiple_star_components(name, dt)` | `dict` | Full component snapshot for a multiple star system |

### Void of Course Moon

| Method | Returns | Description |
|---|---|---|
| `moon_void_of_course(dt, modern=False)` | `VoidOfCourseWindow` | Void-of-course window for the Moon's current sign |
| `is_moon_void_of_course(dt, modern=False)` | `bool` | Whether the Moon is void of course at the given datetime |

### Electional search

| Method | Returns | Description |
|---|---|---|
| `electional_windows(dt_start, dt_end, latitude, longitude, predicate, policy=None)` | `list[ElectionalWindow]` | Search a date range for windows whose chart context satisfies the predicate |

Low-level JD-based electional search is also public:

```python
from moira.facade import ElectionalPolicy, ElectionalWindow
from moira.facade import find_electional_windows, find_electional_moments
```

| Function | Returns | Description |
|---|---|---|
| `find_electional_windows(jd_start, jd_end, latitude, longitude, predicate, policy=None, reader=None)` | `list[ElectionalWindow]` | Window search directly on Julian dates |
| `find_electional_moments(jd_start, jd_end, latitude, longitude, predicate, policy=None, reader=None)` | `list[float]` | Exact candidate JDs for matching electional moments |

### Julian Day utilities

| Method | Returns | Description |
|---|---|---|
| `jd(year, month, day, hour=0.0)` | `float` | JD from a proleptic Gregorian calendar date |
| `from_jd(jd)` | `datetime` | UTC datetime from a JD |
| `calendar_from_jd(jd)` | `CalendarDateTime` | BCE-safe calendar breakdown from a JD |

### Eclipse

| Method | Returns | Description |
|---|---|---|
| `eclipse(dt)` | `EclipseData` | Full eclipse geometry and classification for a datetime |

---

## 5. Ephemeris & Positions

### Planetary positions — low-level functions

```python
from moira.facade import planet_at, all_planets_at, sky_position_at
from moira.spk_reader import get_reader

reader = get_reader()
jd     = 2451545.0   # J2000.0

pos = planet_at("Jupiter", jd, reader=reader)
# PlanetData(longitude, latitude, speed, distance)

sky = sky_position_at("Mars", jd, observer_lat=51.5, observer_lon=-0.1, reader=reader)
# SkyPosition(right_ascension, declination, altitude, azimuth, distance)

chart_dict = all_planets_at(jd, reader=reader)
# dict[str, PlanetData] for all ten classical planets
```

| Function | Returns | Description |
|---|---|---|
| `planet_at(body, jd_ut, reader=None, observer_lat=None, observer_lon=None, observer_elev_m=0.0)` | `PlanetData` | Single planet geocentric ecliptic position |
| `all_planets_at(jd_ut, bodies=None, reader=None, ...)` | `dict[str, PlanetData]` | All (or specified) planets at one JD |
| `sky_position_at(body, jd_ut, observer_lat, observer_lon, observer_elev_m=0.0, reader=None)` | `SkyPosition` | Apparent topocentric equatorial + horizontal coords |
| `sun_longitude(jd_ut, reader=None)` | `float` | Sun ecliptic longitude only (faster than planet_at) |

### Lunar nodes

| Function | Returns | Description |
|---|---|---|
| `true_node(jd_ut, reader=None)` | `NodeData` | True (osculating) lunar node |
| `mean_node(jd_ut)` | `NodeData` | Mean lunar node |
| `mean_lilith(jd_ut)` | `NodeData` | Mean Black Moon Lilith |

### Nodes & apsides bundle

```python
from moira.facade import NodesAndApsides, nodes_and_apsides_at, next_moon_node_crossing
```

| Function | Returns | Description |
|---|---|---|
| `nodes_and_apsides_at(body, jd_ut)` | `NodesAndApsides` | Combined node/apsides vessel for the Moon or supported orbital bodies |
| `next_moon_node_crossing(jd_start, reader=None, ascending=True)` | `float` | JD UT of the next ascending or descending lunar node crossing |

### Heliocentric positions

```python
from moira.facade import heliocentric_planet_at, all_heliocentric_at, HeliocentricData
```

| Function | Returns | Description |
|---|---|---|
| `heliocentric_planet_at(body, jd_ut, reader=None)` | `HeliocentricData` | Heliocentric ecliptic longitude, latitude, distance |
| `all_heliocentric_at(jd_ut, bodies=None, reader=None)` | `dict[str, HeliocentricData]` | All planets heliocentrically |

### Asteroids

```python
from moira.facade import asteroid_at, all_asteroids_at, list_asteroids
from moira.facade import load_asteroid_kernel   # for non-DE441 bodies
```

| Function | Returns | Description |
|---|---|---|
| `asteroid_at(name_or_id, jd_ut, reader=None)` | `AsteroidData` | Single asteroid geocentric ecliptic position |
| `all_asteroids_at(jd_ut, reader=None)` | `dict[str, AsteroidData]` | All loaded asteroids |
| `list_asteroids()` | `list[str]` | Names of currently loaded asteroids |
| `available_in_kernel(kernel_path)` | `list[str]` | Asteroid names available in a kernel |
| `load_asteroid_kernel(path)` | — | Load a supplementary SPK kernel |
| `load_secondary_kernel(path)` | — | Load second SPK kernel |
| `load_tertiary_kernel(path)` | — | Load third SPK kernel |

### Planetary nodes (apsides)

| Function | Returns | Description |
|---|---|---|
| `planetary_node(body, jd_ut)` | `OrbitalNode` | Ascending node and perihelion for a planet |
| `all_planetary_nodes(jd_ut)` | `dict[str, OrbitalNode]` | All planetary nodes |

### Uranian planets (Hamburg School)

```python
from moira.facade import uranian_at, all_uranian_at, list_uranian, UranianBody, UranianPosition
```

| Function | Returns | Description |
|---|---|---|
| `uranian_at(body, jd_ut)` | `UranianPosition` | Single Uranian body position |
| `all_uranian_at(jd_ut)` | `dict[str, UranianPosition]` | All eight Uranian bodies |
| `list_uranian()` | `list[str]` | Uranian body names (Cupido through Poseidon) |

`UranianBody` constants: `CUPIDO  HADES  ZEUS  KRONOS  APOLLON  ADMETOS  VULKANUS  POSEIDON`

### Galactic coordinates

```python
from moira.facade import (
    galactic_position_of, all_galactic_positions, galactic_reference_points,
    equatorial_to_galactic, galactic_to_equatorial,
    ecliptic_to_galactic, galactic_to_ecliptic,
    GalacticPosition,
)
```

| Function | Returns | Description |
|---|---|---|
| `galactic_position_of(body, ecliptic_lon, ecliptic_lat, obliquity, jd_tt)` | `GalacticPosition` | Galactic longitude and latitude (IAU 1958) for one body from true-of-date ecliptic coordinates |
| `all_galactic_positions(body_data, obliquity, jd_tt)` | `list[GalacticPosition]` | Galactic positions for a dict of body -> (lon, lat) using the chart's TT epoch |
| `galactic_reference_points(obliquity, jd_tt)` | `dict[str, tuple[float, float]]` | GC, anti-GC, NGP, SGP, and super-galactic center in true ecliptic-of-date coordinates |
| `equatorial_to_galactic(ra, dec)` | `tuple[float, float]` | RA/Dec -> galactic (l, b) |
| `galactic_to_equatorial(l, b)` | `tuple[float, float]` | Galactic -> RA/Dec |
| `ecliptic_to_galactic(lon, lat, obliquity, jd_tt)` | `tuple[float, float]` | True ecliptic-of-date -> galactic, with TT epoch used for the J2000 frame bridge |
| `galactic_to_ecliptic(l, b, obliquity, jd_tt)` | `tuple[float, float]` | Galactic -> true ecliptic-of-date, with TT epoch used for the of-date frame bridge |

### Gauquelin sectors

```python
from moira.facade import gauquelin_sector, all_gauquelin_sectors, GauquelinPosition
```

| Function | Returns | Description |
|---|---|---|
| `gauquelin_sector(ra_deg, ramc_deg, body="", ecliptic_longitude=None)` | `GauquelinPosition` | Gauquelin sector (1-36) for a single RA/RAMC position |
| `all_gauquelin_sectors(planet_ra_dec, lat, lst)` | `list[GauquelinPosition]` | Gauquelin sectors for a dict of body -> (ra, dec) |

`GauquelinPosition`: `body`, `sector` (1-36), `degree_in_sector`, `zone`, `is_plus_zone`, `ecliptic_longitude`.

### Coordinate utilities

```python
from moira.facade import (
    icrf_to_ecliptic, icrf_to_equatorial, ecliptic_to_equatorial,
    equatorial_to_horizontal, horizontal_to_equatorial,
    cotrans_sp,
    atmospheric_refraction, atmospheric_refraction_extended,
    equation_of_time,
    angular_distance, normalize_degrees,
)
```

| Function | Signature | Description |
|---|---|---|
| `ecliptic_to_equatorial` | `(lon, lat, obliquity) -> (ra, dec)` | Ecliptic -> equatorial (degrees) |
| `equatorial_to_horizontal` | `(ha, dec, lat) -> (az, alt)` | Hour angle/Dec -> azimuth/altitude |
| `horizontal_to_equatorial` | `(azimuth_deg, altitude_deg, lst_deg, lat_deg) -> (ra, dec)` | Horizontal coordinates -> equatorial coordinates |
| `cotrans_sp` | `(lon, lat, dist, lon_speed, lat_speed, dist_speed, obliquity) -> tuple[...]` | Simultaneous spherical coordinate and speed transformation |
| `atmospheric_refraction` | `(altitude_deg, *, pressure_mbar=..., temperature_c=...) -> float` | Standard apparent-altitude refraction correction (degrees) |
| `atmospheric_refraction_extended` | `(altitude_deg, *, pressure_mbar=..., temperature_c=..., relative_humidity=..., observer_height_m=..., wavelength_micron=...) -> tuple[float, float]` | Extended refraction model with environmental parameters |
| `equation_of_time` | `(jd_tt) -> float` | Equation of time in minutes at the TT epoch |
| `angular_distance` | `(lon1, lat1, lon2, lat2) -> float` | Great-circle distance (degrees) |
| `normalize_degrees` | `(d) -> float` | Map any angle to [0, 360) |

### Phase & apparent magnitude

```python
from moira.facade import angular_diameter

ang_diam_arcsec = angular_diameter("Moon", jd)

# For full phase metrics use Moira.phase():
result = m.phase("Venus", dt)
# keys: phase_angle, illumination, angular_diameter_arcsec, apparent_magnitude
```

### Twilight

```python
from moira.facade import twilight_times, TwilightTimes

t = twilight_times(jd, latitude=51.5, longitude=-0.1)
# TwilightTimes: civil_dawn, civil_dusk, nautical_dawn, nautical_dusk,
#                astro_dawn, astro_dusk, sunrise, sunset  (all JD UT)
```

### Relative-motion, orbital, and event helpers

```python
from moira.facade import (
    planet_relative_to, next_heliocentric_transit,
    PlanetPhenomena, planet_phenomena_at,
    KeplerianElements, DistanceExtremes,
    orbital_elements_at, distance_extremes_at,
)
```

| Function | Returns | Description |
|---|---|---|
| `planet_relative_to(body, center_body, jd_ut, reader=None)` | `PlanetData` | Body position relative to another physical center body |
| `next_heliocentric_transit(body, target_lon, jd_start, reader=None, max_days=400.0)` | `float` | Next heliocentric longitude crossing of a target longitude |
| `planet_phenomena_at(body, jd_ut)` | `PlanetPhenomena` | Instantaneous elongation/phase-style observational summary for one body |
| `orbital_elements_at(body, jd_ut, reader)` | `KeplerianElements` | Osculating orbital elements at one epoch |
| `distance_extremes_at(body, jd_ut, reader)` | `DistanceExtremes` | Perihelion/aphelion-style distance-extrema summary at one epoch |

---

## 6. Alternative Reference Frames

Moira's default position products are geocentric ecliptic. Three additional engines surface different physical origins or light-cone geometry, each exposing the same true-of-date ecliptic frame for direct comparison.

### Solar System Barycenter (SSB) Chart

```python
from moira.ssb import SSBPosition, SSB_BODIES, ssb_position_at, all_ssb_positions_at
```

The SSB is the true inertial center-of-mass of the solar system. The Sun wanders up to ~2.2 solar radii (~0.010 AU) from the SSB, driven mainly by Jupiter's mass. All positions are expressed in the true-of-date geocentric ecliptic frame (precession + nutation applied) for comparability with standard Moira products.

| Symbol | Type | Description |
|---|---|---|
| `SSB_BODIES` | `frozenset[str]` | Bodies with well-defined barycentric state in DE441 |
| `ssb_position_at(body, jd_ut)` | `SSBPosition` | SSB-relative position of one body |
| `all_ssb_positions_at(jd_ut)` | `dict[str, SSBPosition]` | SSB-relative positions of all supported bodies |

#### `SSBPosition` fields

| Field | Type | Description |
|---|---|---|
| `name` | `str` | Body name |
| `longitude` | `float` | Ecliptic longitude (°), [0°, 360°) |
| `latitude` | `float` | Ecliptic latitude (°) |
| `distance` | `float` | Distance from SSB (km) |
| `speed` | `float` | Longitudinal speed (°/day) |
| `retrograde` | `bool` | True when speed < 0 |
| `sign` | `str` | Zodiac sign (derived) |
| `sign_symbol` | `str` | Sign glyph (derived) |
| `sign_degree` | `float` | Degree within sign (derived) |

**Property:** `distance_au` → distance from SSB in Astronomical Units.

```python
from moira.ssb import ssb_position_at, all_ssb_positions_at
from moira.facade import jd_from_datetime
from datetime import datetime, timezone

jd = jd_from_datetime(datetime(2000, 1, 1, 12, tzinfo=timezone.utc))

sun_ssb = ssb_position_at("Sun", jd)
print(f"Sun from SSB: {sun_ssb.longitude:.4f}°  dist {sun_ssb.distance_au:.6f} AU")

all_pos = all_ssb_positions_at(jd)
for name, pos in all_pos.items():
    print(f"{name:10s}  {pos.longitude:.4f}°")
```

---

### Planetocentric Positions

```python
from moira.planetocentric import (
    PlanetocentricData, VALID_OBSERVER_BODIES,
    planetocentric_at, all_planetocentric_at,
)
```

Positions of celestial bodies as seen from the center of a specified observer planet other than Earth. Any body with a barycentric state in the DE441 kernel can serve as the observer — including the Sun (heliocentric) and the Moon. Output is expressed in the same true-of-date geocentric ecliptic frame used by all other Moira position products.

Valid observers: `Body.SUN`, `Body.MOON`, `Body.MERCURY`, `Body.VENUS`, `Body.EARTH`, `Body.MARS`, `Body.JUPITER`, `Body.SATURN`, `Body.URANUS`, `Body.NEPTUNE`, `Body.PLUTO`

| Symbol | Type | Description |
|---|---|---|
| `VALID_OBSERVER_BODIES` | `frozenset[str]` | Bodies that may serve as observer or target |
| `planetocentric_at(observer, target, jd_ut)` | `PlanetocentricData` | Position of `target` as seen from `observer` |
| `all_planetocentric_at(observer, jd_ut)` | `dict[str, PlanetocentricData]` | All visible bodies from the observer |

#### `PlanetocentricData` fields

| Field | Type | Description |
|---|---|---|
| `observer` | `str` | Observer body name |
| `name` | `str` | Target body name |
| `longitude` | `float` | Ecliptic longitude (°), [0°, 360°) |
| `latitude` | `float` | Ecliptic latitude (°) |
| `distance` | `float` | Observer–target distance (km) |
| `speed` | `float` | Longitudinal speed (°/day) |
| `retrograde` | `bool` | True when speed < 0 |
| `sign` | `str` | Zodiac sign (derived) |
| `sign_symbol` | `str` | Sign glyph (derived) |
| `sign_degree` | `float` | Degree within sign (derived) |

**Property:** `distance_au` → observer–target distance in Astronomical Units.

```python
from moira.planetocentric import planetocentric_at, all_planetocentric_at

# Saturn as seen from Jupiter:
sat_from_jup = planetocentric_at("Jupiter", "Saturn", jd)

# All planets as seen from Mars:
mars_sky = all_planetocentric_at("Mars", jd)
```

---

### Received-Light (Light-Cone) Positions

```python
from moira.light_cone import (
    ReceivedLightPosition, RECEIVED_LIGHT_BODIES,
    received_light_at, all_received_light_at,
)
```

Standard astrological positions already incorporate light-time correction (the body's position is computed for t − τ, where τ is the one-way light travel time). This engine makes the light-cone geometry **explicit** by surfacing both the apparent position (where the body was when it emitted the arriving light) and the geometric position (where the body physically is at the birth moment).

Typical light travel times and longitude displacements:

| Body | Light time | Max displacement |
|---|---|---|
| Moon | ~1.3 s | < 0.0001° |
| Sun | ~8.3 min | ~0.02° |
| Jupiter | ~35–52 min | ~0.06° |
| Saturn | ~68–84 min | ~0.10° |
| Pluto | ~5.3 h | ~0.35° |

| Symbol | Type | Description |
|---|---|---|
| `RECEIVED_LIGHT_BODIES` | `frozenset[str]` | Physical bodies for which light-cone is meaningful (excludes computed points) |
| `received_light_at(body, jd_ut)` | `ReceivedLightPosition` | Received-light position for one body |
| `all_received_light_at(jd_ut)` | `dict[str, ReceivedLightPosition]` | Received-light positions for all supported bodies |

#### `ReceivedLightPosition` fields

| Field | Type | Description |
|---|---|---|
| `name` | `str` | Body name |
| `apparent_longitude` | `float` | Where body was when light emitted (°) — the standard astrological position |
| `apparent_latitude` | `float` | Ecliptic latitude at emission instant (°) |
| `geometric_longitude` | `float` | Where body physically is at birth moment (°) |
| `geometric_latitude` | `float` | Ecliptic latitude at birth moment (°) |
| `distance_km` | `float` | Earth–body distance at emission instant (km) |
| `light_travel_days` | `float` | One-way light travel time (τ) in days |
| `emission_jd` | `float` | Julian Date when photons were emitted (jd_ut − τ) |
| `speed` | `float` | Apparent longitudinal speed (°/day) |
| `retrograde` | `bool` | True when apparent speed < 0 |
| `sign` | `str` | Sign of apparent longitude (derived) |
| `sign_symbol` | `str` | Sign glyph (derived) |
| `sign_degree` | `float` | Degree within sign (derived) |

**Properties:**
- `light_travel_minutes` → one-way light travel time in minutes
- `longitude_displacement` → angular shift between apparent and geometric longitude (°), in (−180°, +180°]
- `distance_au` → Earth–body distance in Astronomical Units

```python
from moira.light_cone import received_light_at, all_received_light_at

pluto = received_light_at("Pluto", jd)
print(f"Pluto apparent:  {pluto.apparent_longitude:.4f}°")
print(f"Pluto geometric: {pluto.geometric_longitude:.4f}°")
print(f"Light travel:    {pluto.light_travel_minutes:.1f} min")
print(f"Displacement:    {pluto.longitude_displacement:+.4f}°")
```

---

## 7. Chart Structure

### Houses

```python
from moira.facade import calculate_houses, HouseCusps, HouseSystem
from moira.facade import (
    assign_house, describe_boundary, describe_angularity,
    compare_systems, compare_placements, distribute_points,
    HouseSystemFamily, HouseSystemCuspBasis, HouseSystemClassification,
    classify_house_system, HousePolicy,
    HousePlacement, HouseBoundaryProfile,
    HouseAngularity, HouseAngularityProfile,
    HouseSystemComparison, HousePlacementComparison,
    HouseOccupancy, HouseDistributionProfile,
)
```

| Function | Returns | Description |
|---|---|---|
| `calculate_houses(jd_ut, latitude, longitude, system=HouseSystem.PLACIDUS)` | `HouseCusps` | Compute house cusps and angles |
| `assign_house(longitude, cusps)` | `HousePlacement` | Find which house a longitude falls in |
| `describe_boundary(longitude, cusps, orb=2.0)` | `HouseBoundaryProfile` | Proximity to house cusp boundaries |
| `describe_angularity(longitude, cusps, orb=5.0)` | `HouseAngularity` | Angular/succedent/cadent classification |
| `compare_systems(jd_ut, latitude, longitude, systems)` | `HouseSystemComparison` | Side-by-side comparison of multiple systems |
| `compare_placements(body_lon, systems_cusps)` | `HousePlacementComparison` | How a body's house changes across systems |
| `distribute_points(longitudes, cusps)` | `HouseDistributionProfile` | Count of points per house |
| `classify_house_system(system)` | `HouseSystemClassification` | Family, cusp basis, polar behavior |

**House system families** (`HouseSystemFamily`):
`ECLIPTIC_BASED  EQUATORIAL  SPACE_BASED  TIME_BASED  EQUAL_HOUSE`

**`UnknownSystemPolicy`**: controls behavior when an unrecognized house system is passed — `RAISE` (raises `ValueError`) or `FALLBACK_TO_PLACIDUS` (silently returns Placidus). Set via `HousePolicy`.

**`PolarFallbackPolicy`**: controls behavior at polar latitudes where certain systems are not supported by default — `FALLBACK_TO_PORPHYRY`, `RAISE`, or `EXPERIMENTAL_SEARCH`. The experimental mode is explicit and currently attempts branch-aware high-latitude Placidus only. Set via `HousePolicy`.

### Aspects

```python
from moira.facade import (
    find_aspects, aspects_between, aspects_to_point,
    find_declination_aspects, find_patterns, build_aspect_graph,
    aspect_strength, aspect_motion_state, aspect_harmonic_profile,
    AspectData, AspectPolicy, AspectStrength, DeclinationAspect,
    AspectFamily, AspectDomain, AspectTier, MotionState,
    AspectGraph, AspectGraphNode, AspectFamilyProfile, AspectHarmonicProfile,
    CANONICAL_ASPECTS, DEFAULT_POLICY,
)
```

#### `AspectData` fields

| Field | Type | Description |
|---|---|---|
| `body1` | `str` | First body name |
| `body2` | `str` | Second body name |
| `aspect` | `str` | Human name, e.g. "Conjunction", "Sextile" |
| `symbol` | `str` | Glyph or short symbol for the aspect |
| `angle` | `float` | Exact aspect angle in degrees, e.g. 0, 60, 90, 120, 180 |
| `separation` | `float` | Actual angular separation between the bodies |
| `orb` | `float` | Actual orb (signed; negative = separating) |
| `allowed_orb` | `float` | Maximum allowed orb for this aspect |
| `applying` | `bool` | True if the aspect is applying |
| `stationary` | `bool` | True if a stationary motion state affects the aspect |
| `classification` | `AspectClassification` | Domain, family, tier, motion state, and strength metadata |

#### Core aspect functions

| Function | Returns | Description |
|---|---|---|
| `find_aspects(longitudes, orbs=None, include_minor=True, speeds=None)` | `list[AspectData]` | All aspects in a longitude dict |
| `aspects_between(lons_a, lons_b, orbs=None, include_minor=True)` | `list[AspectData]` | Cross-set aspects (synastry / transits) |
| `aspects_to_point(longitudes, point, orbs=None)` | `list[AspectData]` | Aspects to a single longitude |
| `find_declination_aspects(bodies_dec, orb=1.0)` | `list[DeclinationAspect]` | Parallel and contra-parallel aspects |
| `build_aspect_graph(aspects)` | `AspectGraph` | Graph structure of the aspect network |
| `aspect_strength(aspect)` | `AspectStrength` | Strength score based on orb and tier |
| `aspect_motion_state(aspect, speeds)` | `MotionState` | APPLYING / SEPARATING / EXACT |
| `aspect_harmonic_profile(longitudes, harmonic)` | `AspectHarmonicProfile` | Aspects visible at a given harmonic |

### Aspect Patterns

```python
from moira.facade import (
    find_all_patterns, find_t_squares, find_grand_trines, find_grand_crosses,
    find_yods, find_mystic_rectangles, find_kites, find_stelliums,
    find_minor_grand_trines, find_grand_sextiles, find_thors_hammers,
    find_boomerang_yods, find_wedges, find_cradles, find_trapezes,
    find_eyes, find_irritation_triangles, find_hard_wedges,
    find_dominant_triangles, find_grand_quintiles, find_quintile_triangles,
    find_septile_triangles,
    AspectPattern, PatternClassification,
)
```

All `find_*` functions accept `longitudes: dict[str, float]` and optional
`orb` parameters. They return `list[AspectPattern]`.

`find_all_patterns(longitudes, ...)` runs all detectors in one call.

#### `AspectPattern` fields

| Field | Type | Description |
|---|---|---|
| `name` | `str` | Pattern name, e.g. "T-Square", "Grand Trine", "Yod" |
| `bodies` | `list[str]` | Bodies participating in the pattern |
| `aspects` | `list[AspectData]` | Aspects forming the pattern |
| `apex` | `str \| None` | Apex body (for Yods, T-Squares, etc.) |
| `classification` | `PatternClassification` | Pattern classification metadata |
| `detection_truth` | `PatternDetectionTruth` | Detection-trace metadata for the pattern |
| `all_contributions` | `list[PatternAspectContribution]` | Full aspect/body contribution set |
| `contributions` | `list[PatternAspectContribution]` | Primary contribution set used for display |
| `condition_profile` | `PatternConditionProfile` | Consolidated pattern condition profile |

### Chart shape (Jones types)

```python
from moira.facade import classify_chart_shape, ChartShape, ChartShapeType

shape = classify_chart_shape(chart.longitudes(include_nodes=False))
# ChartShape(type, description, focal_point)
```

`ChartShapeType` constants: `BUNDLE  BOWL  BUCKET  LOCOMOTIVE  FAN  SEESAW  SPLASH  SPLAY`

### Midpoints

```python
from moira.facade import calculate_midpoints, midpoints_to_point, Midpoint, MidpointsService

mps = calculate_midpoints(chart.longitudes(), orb=1.5)
# list[Midpoint(body1, body2, midpoint_lon, activated_by)]

hits = midpoints_to_point(chart.longitudes(), target_lon=15.0, orb=1.5)

# Using the service class for chained access:
svc = MidpointsService(chart.longitudes(), orb=1.5)
all_mps   = svc.all()               # list[Midpoint]
at_point  = svc.to_point(15.0)      # midpoints within orb of 15°
dial      = svc.dial_90()           # midpoints projected to 90° dial
tree      = svc.tree(15.0)          # midpoints equidistant from 15°
```

### Harmonics

```python
from moira.facade import calculate_harmonic, HarmonicPosition, HARMONIC_PRESETS, HarmonicsService

h4 = calculate_harmonic(chart.longitudes(include_nodes=False), 4)
# list[HarmonicPosition(body, natal_lon, harmonic_lon)]

# Using the service class:
svc = HarmonicsService(chart.longitudes(include_nodes=False))
h5  = svc.harmonic(5)       # list[HarmonicPosition]
```

`HARMONIC_PRESETS`: dict of named harmonics, e.g. `{"4th": 4, "5th": 5, ...}`.

### Antiscia

```python
from moira.facade import find_antiscia, antiscia_to_point, AntisciaAspect

antiscia = find_antiscia(chart.longitudes(), orb=1.0)
# AntisciaAspect(body1, body2, kind, orb)
# kind: "antiscion" (solstice axis) or "contra-antiscion" (equinox axis)
```

### Void of Course Moon

```python
from moira.facade import (
    void_of_course_window, is_void_of_course,
    next_void_of_course, void_periods_in_range,
    LastAspect, VoidOfCourseWindow,
)

voc = void_of_course_window(jd_ut)
# VoidOfCourseWindow(start_jd, end_jd, last_aspect, ingress_sign)

voc_periods = void_periods_in_range(jd_start, jd_end)
```

---

## 8. Classical Techniques

### Dignities

```python
from moira.facade import (
    calculate_dignities, calculate_receptions,
    calculate_condition_profiles, calculate_chart_condition_profile,
    calculate_condition_network_profile,
    PlanetaryDignity, EssentialDignityKind, AccidentalConditionKind,
    DignitiesService,
    sect_light, is_day_chart, almuten_figuris, find_phasis,
    is_in_hayz, is_in_sect,
)
```

#### Quick helpers

| Function | Returns | Description |
|---|---|---|
| `is_day_chart(sun_lon, asc_lon)` | `bool` | True if Sun is above the horizon (diurnal sect) |
| `sect_light(sun_lon, asc_lon)` | `str` | "Sun" for day charts, "Moon" for night charts |
| `is_in_hayz(planet, sun_lon, asc_lon, chart_lons)` | `bool` | True if planet is in hayz |
| `is_in_sect(planet, sun_lon, asc_lon)` | `bool` | True if planet is in its preferred sect |
| `almuten_figuris(chart_lons, cusps, is_day)` | `str` | Almuten figuris (planet with most dignities at ASC/MC/prenatal syzygy) |
| `find_phasis(body, jd_start, jd_end, reader=None)` | `list[float]` | JDs of phasis (first/last visibility) for a body |

#### `EssentialDignityKind` values

`DOMICILE  EXALTATION  TRIPLICITY  TERM  FACE  DETRIMENT  FALL  PEREGRINE`

#### `AccidentalConditionKind` values

`DIRECT  RETROGRADE  STATIONARY  ORIENTAL  OCCIDENTAL  CAZIMI  COMBUST
 UNDER_BEAMS  FREE_OF_BEAMS  SWIFT  SLOW  IN_HAYZ  OUT_OF_HAYZ`

#### `PlanetaryDignity` fields

| Field | Type | Description |
|---|---|---|
| `planet` | `str` | Planet name |
| `sign` | `str` | Sign occupied by the planet |
| `degree` | `float` | Degree within the sign |
| `house` | `int` | House placement |
| `essential_dignity` | `EssentialDignityKind` | Primary essential dignity/debility |
| `essential_score` | `int` | Essential dignity score |
| `accidental_dignities` | `list[AccidentalDignityCondition]` | Active accidental dignity conditions |
| `accidental_score` | `int` | Accidental dignity score |
| `total_score` | `int` | Combined dignity score |
| `is_retrograde` | `bool` | Retrograde flag |
| `receptions` | `list[PlanetaryReception]` | Active receptions involving the planet |
| `condition_profile` | `PlanetaryConditionProfile` | Consolidated dignity/condition profile |
| `essential_truth` | `EssentialDignityTruth` | Essential dignity computation truth data |
| `accidental_truth` | `AccidentalDignityTruth` | Accidental dignity truth data |
| `sect_truth` | `SectTruth` | Sect evaluation truth data |
| `solar_truth` | `SolarConditionTruth` | Solar condition truth data |
| `all_receptions` | `list[PlanetaryReception]` | Full reception set prior to filtering |
| `mutual_reception_truth` | `MutualReceptionTruth` | Mutual reception truth data |
| `essential_classification` | `EssentialDignityClassification` | Essential dignity classification metadata |
| `accidental_classification` | `AccidentalDignityClassification` | Accidental dignity classification metadata |
| `sect_classification` | `SectClassification` | Sect classification metadata |
| `solar_classification` | `SolarConditionClassification` | Solar condition classification metadata |
| `reception_classification` | `ReceptionClassification` | Reception classification metadata |

#### Condition profiles & networks

```python
profiles = calculate_condition_profiles(chart_lons, house_cusps, is_day)
# list[PlanetaryConditionProfile]

chart_profile = calculate_chart_condition_profile(chart_lons, house_cusps, is_day)
# ChartConditionProfile

network = calculate_condition_network_profile(chart_lons, house_cusps, is_day)
# ConditionNetworkProfile — graph of planetary condition relationships
```

### Arabic Parts / Lots

```python
from moira.facade import (
    calculate_lots, calculate_lot_dependencies, calculate_all_lot_dependencies,
    calculate_lot_condition_profiles, calculate_lot_chart_condition_profile,
    calculate_lot_condition_network_profile,
    ArabicPart, ArabicPartsService, list_parts,
    LotReversalKind,
)
```

| Function | Returns | Description |
|---|---|---|
| `calculate_lots(lons, cusps, is_day)` | `list[ArabicPart]` | All classical Arabic Parts |
| `list_parts()` | `list[str]` | Names of all available parts |

#### `ArabicPart` fields

| Field | Type | Description |
|---|---|---|
| `name` | `str` | Part name, e.g. "Fortune", "Spirit" |
| `longitude` | `float` | Ecliptic longitude (degrees) |
| `formula` | `str` | Formula used to derive the part |
| `category` | `str` | Part category/classification label |
| `description` | `str` | Short textual description |
| `computation_truth` | `ArabicPartComputationTruth` | Truth data for the part computation |
| `classification` | `ArabicPartClassification` | Classification metadata |
| `all_dependencies` | `list[LotDependency]` | Full dependency graph slice for the part |
| `dependencies` | `list[LotDependency]` | Direct dependencies used by the part |
| `condition_profile` | `LotConditionProfile` | Computed condition profile |
| `sign` | `str` | Sign occupied by the part |
| `sign_symbol` | `str` | Sign glyph/symbol |
| `sign_degree` | `float` | Degree within the sign |

#### Using `ArabicPartsService`

```python
svc    = ArabicPartsService(lons, cusps, is_day)
fortune = svc.fortune()    # ArabicPart
spirit  = svc.spirit()
exalt   = svc.exaltation()
```

### Profections

```python
from moira.facade import (
    annual_profection, monthly_profection, profection_schedule,
    ProfectionResult,
)

result = annual_profection(natal_asc_lon, jd_natal, jd_now)
# ProfectionResult(house_number, sign, time_lord, activated_planets)
```

| Function | Returns | Description |
|---|---|---|
| `annual_profection(natal_asc, jd_natal, jd_now)` | `ProfectionResult` | Whole-sign annual profection |
| `monthly_profection(natal_asc, jd_natal, jd_now)` | `ProfectionResult` | Monthly subdivision |
| `profection_schedule(natal_asc, jd_natal, jd_now, natal_positions=None)` | `ProfectionResult` | Annual profection with activated-planet detection |

### Nakshatras (Vedic lunar mansions)

```python
from moira.facade import nakshatra_of, all_nakshatras_at, NakshatraPosition

pos = nakshatra_of(moon_longitude, jd_ut, ayanamsa_system=Ayanamsa.LAHIRI)
# NakshatraPosition(name, number, pada, lord, remaining_fraction)

all_naks = all_nakshatras_at(chart.longitudes(include_nodes=False), jd_ut)
# dict[str, NakshatraPosition]
```

### Arabic Lunar Mansions (Manazil)

```python
from moira.facade import mansion_of, all_mansions_at, moon_mansion, MansionPosition, MANSIONS

pos = mansion_of(moon_longitude)
# MansionPosition(number, name, start_lon, end_lon, ruling_planet)

moon_man = moon_mansion(moon_longitude)   # same, convenience alias
all_m    = all_mansions_at(chart.longitudes())
```

`MANSIONS`: tuple of 28 `MansionInfo` entries.

### Longevity (Hyleg / Alcocoden)

```python
from moira.facade import find_hyleg, calculate_longevity, HylegResult

hyleg = find_hyleg(chart_lons, cusps, is_day)
# HylegResult(hyleg, alcocoden, projected_years)

result = calculate_longevity(chart_lons, cusps, is_day)
print(result.projected_years)
```

### Gauquelin sectors

See Section 4 (Ephemeris & Positions).

### Planetary Hours

```python
from moira.facade import planetary_hours, PlanetaryHoursDay, PlanetaryHour

day = planetary_hours(jd_ut, latitude, longitude, reader=None)
# PlanetaryHoursDay(date, day_hours: list[PlanetaryHour], night_hours: list[PlanetaryHour])
# PlanetaryHour(ruler, start_jd, end_jd)
```

### Varga (Vedic divisional charts)

```python
from moira.facade import calculate_varga, navamsa, saptamsa, dashamansa, dwadashamsa, trimshamsa

d9  = navamsa(longitude)          # D9  — ninth division
d7  = saptamsa(longitude)         # D7  — seventh division
d10 = dashamansa(longitude)       # D10 — tenth division
d12 = dwadashamsa(longitude)      # D12 — twelfth division
d30 = trimshamsa(longitude)       # D30 — thirtieth division

# Generic:
pos = calculate_varga(longitude, divisor=9)
# VargaPoint(divisor, position_in_sign, sign_number, sign_name)
```

---

## 9. Timing Techniques

### Transits

```python
from moira.facade import (
    find_transits, next_transit, find_ingresses, next_ingress, next_ingress_into,
    solar_return, lunar_return, planet_return,
    last_new_moon, last_full_moon, prenatal_syzygy,
    transit_relations, ingress_relations,
    transit_condition_profiles, ingress_condition_profiles,
    transit_chart_condition_profile, transit_condition_network_profile,
    TransitEvent, IngressEvent, TransitSearchPolicy, TransitComputationPolicy,
)
```

#### `TransitEvent` fields

| Field | Type | Description |
|---|---|---|
| `body` | `str` | Transiting body |
| `longitude` | `float` | Exact longitude of the event |
| `jd_ut` | `float` | JD UT of the exact transit |
| `direction` | `str` | Search direction / crossing direction |
| `computation_truth` | `TransitComputationTruth` | Search/computation truth data |
| `classification` | `TransitComputationClassification` | Transit classification metadata |
| `relation` | `TransitRelation` | Target relation metadata |
| `condition_profile` | `TransitConditionProfile` | Transit condition profile |

#### `IngressEvent` fields

| Field | Type | Description |
|---|---|---|
| `body` | `str` | Body entering the sign |
| `sign` | `str` | Sign entered |
| `jd_ut` | `float` | JD UT of the ingress |
| `direction` | `str` | Ingress direction |
| `computation_truth` | `IngressComputationTruth` | Search/computation truth data |
| `classification` | `IngressComputationClassification` | Ingress classification metadata |
| `relation` | `TransitRelation` | Sign-ingress relation metadata |
| `condition_profile` | `TransitConditionProfile` | Ingress condition profile |

#### Core functions

```python
events = find_transits(Body.SATURN, natal_sun_lon, jd_start, jd_end, reader=reader)
ev     = next_transit(Body.JUPITER, natal_moon_lon, jd_now, reader=reader)

ingr   = find_ingresses(Body.SATURN, jd_start, jd_end, reader=reader)
next_i = next_ingress(Body.JUPITER, jd_now, reader=reader)
into   = next_ingress_into(Body.SATURN, "Aquarius", jd_now, reader=reader)

jd_sr  = solar_return(natal_sun_lon, year=2025, reader=reader)
jd_lr  = lunar_return(natal_moon_lon, jd_now, reader=reader)
jd_pr  = planet_return(Body.JUPITER, natal_jup_lon, jd_now, reader=reader)
jd_nm  = last_new_moon(jd_now, reader=reader)
jd_fm  = last_full_moon(jd_now, reader=reader)
jd_syn, kind = prenatal_syzygy(jd_natal, reader=reader)
```

### Stations & Retrograde

```python
from moira.facade import find_stations, next_station, is_retrograde, retrograde_periods, StationEvent

stations = find_stations(Body.MARS, jd_start, jd_end, reader=reader)
# StationEvent(jd, body, kind)  kind: "retrograde" | "direct"

retro_intervals = retrograde_periods(Body.MERCURY, jd_start, jd_end, reader=reader)
# list[(jd_start, jd_end)]
```

### Progressions & Directions

All progression functions share the signature:
`(jd_natal, target_dt, bodies=None, reader=None) → ProgressedChart`

```python
from moira.facade import (
    secondary_progression, solar_arc, solar_arc_right_ascension,
    naibod_longitude, naibod_right_ascension,
    tertiary_progression, tertiary_ii_progression,
    minor_progression, ascendant_arc, daily_houses,
    converse_secondary_progression, converse_solar_arc,
    converse_solar_arc_right_ascension,
    converse_naibod_longitude, converse_naibod_right_ascension,
    converse_tertiary_progression, converse_tertiary_ii_progression,
    converse_minor_progression,
    ProgressedChart, ProgressedPosition,
    ProgressionTimeKeyPolicy, ProgressionDirectionPolicy,
    ProgressionComputationPolicy,
)
```

| Technique | Function | Key rate |
|---|---|---|
| Secondary Progression | `secondary_progression` | 1 day = 1 year |
| Solar Arc | `solar_arc` | Sun's progressed daily motion applied to all bodies |
| Solar Arc (RA) | `solar_arc_right_ascension` | Solar Arc in right ascension |
| Naibod (longitude) | `naibod_longitude` | 0°59′08″/year |
| Naibod (RA) | `naibod_right_ascension` | Naibod in right ascension |
| Tertiary | `tertiary_progression` | 1 day = 1 lunar month |
| Tertiary II | `tertiary_ii_progression` | Klaus Wessel variant |
| Minor | `minor_progression` | 1 lunar month = 1 year |
| Ascendant Arc | `ascendant_arc` | ASC arc applied to all bodies |

All converse variants (moving backward) are prefixed with `converse_`.

#### `ProgressedChart` fields

| Field | Type | Description |
|---|---|---|
| `chart_type` | `str` | Progression technique identifier |
| `natal_jd_ut` | `float` | Natal JD UT |
| `progressed_jd_ut` | `float` | Progressed JD UT used for the positions |
| `target_date` | `datetime` | Target date requested by the user |
| `solar_arc_deg` | `float` | Solar arc applied when relevant |
| `positions` | `dict[str, ProgressedPosition]` | Body → progressed position |
| `computation_truth` | `ProgressionComputationTruth` | Progression computation truth data |
| `classification` | `ProgressionComputationClassification` | Progression classification metadata |
| `relation` | `ProgressionRelation` | Relation metadata for natal/progressed comparison |
| `condition_profile` | `ProgressionConditionProfile` | Consolidated progression profile |

`ProgressedPosition`: `longitude`, `latitude`, `speed`, `natal_longitude`.

### Primary Directions

```python
from moira.facade import speculum, find_primary_arcs, SpeculumEntry, PrimaryArc, DIRECT, CONVERSE

spec  = speculum(chart, houses, geo_lat=51.5)
arcs  = find_primary_arcs(chart, houses, geo_lat=51.5, max_arc=90.0, include_converse=True)
# list[PrimaryArc(significator, promissor, arc, direction)]
# arc.years()             → years by key "naibod" (default)
# arc.years("ptolemy")    → years by Ptolemy key
```

### Firdaria (Persian Time Lords)

```python
from moira.facade import (
    firdaria, current_firdaria, group_firdaria,
    firdar_condition_profile, firdar_sequence_profile, firdar_active_pair,
    validate_firdaria_output,
    FirdarPeriod, FirdarMajorGroup, FirdarConditionProfile,
    FirdarSequenceProfile, FirdarActivePair,
    FirdarSequenceKind, FirdarYearPolicy, TimelordComputationPolicy,
    DEFAULT_TIMELORD_POLICY,
    FIRDARIA_DIURNAL, FIRDARIA_NOCTURNAL, FIRDARIA_NOCTURNAL_BONATTI,
    CHALDEAN_ORDER, MINOR_YEARS,
)
```

| Function | Returns | Description |
|---|---|---|
| `firdaria(jd_natal, is_day, policy=None)` | `list[FirdarPeriod]` | Full Firdaria sequence from birth |
| `current_firdaria(jd_natal, jd_now, is_day, policy=None)` | `FirdarPeriod` | Active Firdaria period at jd_now |
| `group_firdaria(periods)` | `list[FirdarMajorGroup]` | Periods grouped by major lord |
| `firdar_condition_profile(period, chart_lons)` | `FirdarConditionProfile` | Condition analysis for one period |
| `firdar_sequence_profile(jd_natal, is_day, jd_now)` | `FirdarSequenceProfile` | Full condition profile across sequence |
| `firdar_active_pair(jd_natal, jd_now, is_day)` | `FirdarActivePair` | Major + minor lord pair at jd_now |

#### `FirdarPeriod` fields

| Field | Type | Description |
|---|---|---|
| `level` | `int` | Period level |
| `planet` | `str` | Active period lord |
| `start_jd` | `float` | Start JD |
| `end_jd` | `float` | End JD |
| `years` | `float` | Duration in years |
| `major_planet` | `str` | Parent major lord |
| `is_day_chart` | `bool` | True for diurnal sect sequence |
| `variant` | `str` | Variant used for the sequence |
| `sequence_kind` | `FirdarSequenceKind` | Sequence family metadata |
| `is_node_period` | `bool` | Whether the period belongs to the nodal sequence |

### Zodiacal Releasing

```python
from moira.facade import (
    zodiacal_releasing, current_releasing, group_releasing,
    zr_condition_profile, zr_sequence_profile, zr_level_pair,
    validate_releasing_output,
    ReleasingPeriod, ZRPeriodGroup, ZRConditionProfile,
    ZRSequenceProfile, ZRLevelPair,
    ZRAngularityClass, ZRYearPolicy,
)
```

| Function | Returns | Description |
|---|---|---|
| `zodiacal_releasing(lot_lon, jd_natal, levels=4)` | `list[ReleasingPeriod]` | Full ZR sequence from a Lot |
| `current_releasing(lot_lon, jd_natal, jd_now, levels=4)` | `ReleasingPeriod` | Active period at jd_now |
| `group_releasing(periods)` | `list[ZRPeriodGroup]` | Grouped by Level 1 sign |
| `zr_level_pair(lot_lon, jd_natal, jd_now)` | `ZRLevelPair` | Active Level 1 + Level 2 pair |

#### `ReleasingPeriod` fields

| Field | Type | Description |
|---|---|---|
| `level` | `int` | Period level (1-4) |
| `sign` | `str` | Releasing sign |
| `ruler` | `str` | Sign ruler |
| `start_jd` | `float` | Start JD |
| `end_jd` | `float` | End JD |
| `years` | `float` | Period length in years |
| `lot_name` | `str` | Lot used for the releasing sequence |
| `is_loosing_of_bond` | `bool` | Whether the period begins with a Loosing of the Bond |
| `is_peak_period` | `bool` | True at peak periods |
| `angularity_from_fortune` | `int` | Angularity offset from Fortune |
| `use_loosing_of_bond` | `bool` | Whether Loosing of the Bond is enabled |
| `angularity_class` | `ZRAngularityClass` | Angular / succedent / cadent class |

### Vimshottari Dasha

```python
from moira.facade import (
    vimshottari, current_dasha, dasha_balance,
    dasha_active_line, dasha_condition_profile, dasha_sequence_profile,
    dasha_lord_pair, validate_vimshottari_output,
    DashaPeriod, DashaActiveLine, DashaConditionProfile,
    DashaSequenceProfile, DashaLordPair, DashaLordType,
    VimshottariComputationPolicy, DEFAULT_VIMSHOTTARI_POLICY,
    VIMSHOTTARI_YEARS, VIMSHOTTARI_SEQUENCE, VIMSHOTTARI_TOTAL,
    VIMSHOTTARI_YEAR_BASIS, VIMSHOTTARI_LEVEL_NAMES,
)
```

| Function | Returns | Description |
|---|---|---|
| `vimshottari(moon_lon, jd_natal, levels=2, ayanamsa_system=Ayanamsa.LAHIRI)` | `list[DashaPeriod]` | Full Vimshottari sequence |
| `current_dasha(moon_lon, jd_natal, jd_now, levels=2)` | `DashaPeriod` | Active Dasha at jd_now |
| `dasha_balance(moon_lon, jd_natal)` | `float` | Remaining balance of natal Mahadasha (years) |
| `dasha_active_line(moon_lon, jd_natal, jd_now)` | `DashaActiveLine` | Active period at all requested levels |
| `dasha_lord_pair(moon_lon, jd_natal, jd_now)` | `DashaLordPair` | Mahadasha + Antardasha lords |

#### `DashaPeriod` fields

| Field | Type | Description |
|---|---|---|
| `level` | `int` | 1 = Mahadasha, 2 = Antardasha, 3 = Pratyantardasha |
| `planet` | `str` | Dasha lord (planet name) |
| `start_jd` | `float` | Start JD |
| `end_jd` | `float` | End JD |
| `year_days` | `float` | Duration expressed in days/year-basis units |
| `sub` | `list[DashaPeriod]` | Nested sub-periods (if levels > 1) |
| `year_basis` | `str` | Year basis used for the sequence |
| `birth_nakshatra` | `str` | Natal Moon nakshatra |
| `nakshatra_fraction` | `float` | Fraction of nakshatra elapsed at birth |
| `lord_type` | `DashaLordType` | Lord classification metadata |

`VIMSHOTTARI_YEARS`: dict of lord → years (Ketu=7, Venus=20, Sun=6, ...).

---

## 10. Planetary Cycles Engine

```python
from moira.cycles import (
    # Enums
    SynodicPhase, GreatMutationElement, PlanetaryAgeName,
    # Return series
    ReturnEvent, ReturnSeries,
    return_series, half_return_series, lifetime_returns,
    # Synodic cycles
    SynodicCyclePosition, synodic_cycle_position,
    # Great conjunctions
    GreatConjunction, GreatConjunctionSeries, MutationPeriod,
    great_conjunctions, mutation_period_at,
    # Planetary ages
    PlanetaryAgePeriod, PlanetaryAgeProfile,
    planetary_age_at, planetary_age_profile,
    # Firdar
    FirdarPeriod, FirdarSubPeriod, FirdarSeries,
    firdar_series, firdar_at,
    # Planetary days and hours
    PlanetaryDayInfo, PlanetaryHour, PlanetaryHoursProfile,
    planetary_day_ruler, planetary_hours_for_day,
)
```

`moira.cycles` governs cyclical timing frameworks grounded in astronomical periodicity. It is distinct from `moira.timelords` (Firdaria, Zodiacal Releasing, Vimshottari) and `moira.transits` (sign ingresses, transit events). The cycles engine focuses on the long-arc structure of planetary time: returns, synodic phases, the Jupiter–Saturn great conjunction doctrine, and Ptolemaic planetary ages.

### Return Series

A complete series of returns (or half-returns) for one body across a date range.

| Function | Returns | Description |
|---|---|---|
| `return_series(body, natal_lon, jd_start, jd_end)` | `ReturnSeries` | All direct returns of a body to its natal longitude |
| `half_return_series(body, natal_lon, jd_start, jd_end)` | `ReturnSeries` | Returns and half-returns (oppositions) interleaved |
| `lifetime_returns(body, natal_lon, jd_natal, age_years=90.0)` | `ReturnSeries` | Full-lifetime return sequence from birth |

#### `ReturnEvent` fields

| Field | Type | Description |
|---|---|---|
| `body` | `str` | The returning body |
| `return_number` | `int` | Ordinal (1 = first return) |
| `jd_ut` | `float` | JD UT of exact return |
| `longitude` | `float` | Natal longitude returned to (°) |
| `is_half` | `bool` | True for a half-return (opposition to natal) |

#### `ReturnSeries` fields

| Field | Type | Description |
|---|---|---|
| `body` | `str` | Body name |
| `natal_longitude` | `float` | Natal longitude (°) |
| `jd_start` | `float` | Start of search window |
| `jd_end` | `float` | End of search window |
| `returns` | `tuple[ReturnEvent, ...]` | All returns, chronological |
| `count` | `int` | Number of returns found |

### Synodic Cycles

```python
pos = synodic_cycle_position(body1, body2, jd_ut)
# SynodicCyclePosition
```

#### `SynodicCyclePosition` fields

| Field | Type | Description |
|---|---|---|
| `body1` | `str` | First body |
| `body2` | `str` | Second body |
| `jd_ut` | `float` | Moment of evaluation |
| `phase_angle` | `float` | Phase angle from body1 to body2 (°), [0°, 360°) — 0° = conjunction |
| `phase` | `SynodicPhase` | Eight-fold phase classification |
| `is_waxing` | `bool` | True if the phase angle is increasing (0°–180°) |
| `lon1` | `float` | Ecliptic longitude of body1 at evaluation (°) |
| `lon2` | `float` | Ecliptic longitude of body2 at evaluation (°) |

`SynodicPhase` values: `NEW  WAXING_CRESCENT  FIRST_QUARTER  WAXING_GIBBOUS  FULL  WANING_GIBBOUS  LAST_QUARTER  WANING_CRESCENT`

`SynodicPhase.from_angle(angle_deg)` classifies an arbitrary phase angle into one of the eight phases.

### Great Conjunctions

The Jupiter–Saturn 20/200/800-year conjunction doctrine (Abu Ma'shar, Kepler).

| Function | Returns | Description |
|---|---|---|
| `great_conjunctions(jd_start, jd_end)` | `GreatConjunctionSeries` | All Jupiter–Saturn conjunctions in a range |
| `mutation_period_at(jd_ut)` | `MutationPeriod` | Elemental mutation period enclosing a given moment |

#### `GreatConjunction` fields

| Field | Type | Description |
|---|---|---|
| `jd_ut` | `float` | JD UT of exact conjunction |
| `longitude` | `float` | Conjunction longitude (°) |
| `sign` | `str` | Zodiac sign name |
| `sign_symbol` | `str` | Zodiac sign glyph |
| `degree_in_sign` | `float` | Degree within the sign |
| `element` | `GreatMutationElement` | Elemental trigon: FIRE / EARTH / AIR / WATER |

`GreatMutationElement` values: `FIRE  EARTH  AIR  WATER`

#### `GreatConjunctionSeries` fields

| Field | Type | Description |
|---|---|---|
| `jd_start` | `float` | Start of search window |
| `jd_end` | `float` | End of search window |
| `conjunctions` | `tuple[GreatConjunction, ...]` | All conjunctions found, chronological |
| `count` | `int` | Number of conjunctions |
| `elements_represented` | `tuple[GreatMutationElement, ...]` | Distinct elements present, in order of first occurrence |

#### `MutationPeriod` fields

| Field | Type | Description |
|---|---|---|
| `element` | `GreatMutationElement` | Dominant element for this ~200-year period |
| `start_conjunction` | `GreatConjunction` | First conjunction that inaugurated this element period |
| `end_conjunction` | `GreatConjunction \| None` | Final conjunction in this element before mutation (None if period extends beyond the search window) |
| `conjunction_count` | `int` | Number of conjunctions in this element during this period |

### Planetary Ages (Ptolemy)

The seven-age model from *Tetrabiblos* I.10. Each planet governs a developmental stage.

| Function | Returns | Description |
|---|---|---|
| `planetary_age_at(age_years)` | `PlanetaryAgePeriod` | Which planet governs a given age |
| `planetary_age_profile(jd_natal, jd_now)` | `PlanetaryAgeProfile` | Full seven-period model with current period identified |

#### `PlanetaryAgePeriod` fields

| Field | Type | Description |
|---|---|---|
| `ruler` | `PlanetaryAgeName` | Governing planet |
| `start_age` | `float` | Age when this period begins (years) |
| `end_age` | `float \| None` | Age when this period ends (None for Saturn, which is open-ended) |
| `label` | `str` | Human-readable stage label (e.g. "Childhood", "Prime") |

`PlanetaryAgeName` values: `MOON  MERCURY  VENUS  SUN  MARS  JUPITER  SATURN`

Standard Ptolemaic durations: Moon 0–4, Mercury 4–14, Venus 14–22, Sun 22–41, Mars 41–56, Jupiter 56–68, Saturn 68+.

#### `PlanetaryAgeProfile` fields

| Field | Type | Description |
|---|---|---|
| `periods` | `tuple[PlanetaryAgePeriod, ...]` | All seven age periods in order |
| `current` | `PlanetaryAgePeriod \| None` | Active period for the queried age, or None if not queried |
| `queried_age` | `float \| None` | The age that was queried (years), or None |

### Firdar (cycles.py variant)

`moira.cycles` provides a streamlined Firdar engine. It is distinct from `moira.timelords.firdaria`, which adds condition profiles and reception network analysis on top of the same foundation.

Diurnal sequence (day births): Sun(10) → Venus(8) → Mercury(13) → Moon(9) → Saturn(11) → Jupiter(12) → Mars(7) → North Node(3) → South Node(2) = 75 years

Nocturnal sequence (night births): Moon(9) → Saturn(11) → Jupiter(12) → Mars(7) → Sun(10) → Venus(8) → Mercury(13) → North Node(3) → South Node(2) = 75 years

| Function | Returns | Description |
|---|---|---|
| `firdar_series(jd_natal, is_day)` | `FirdarSeries` | Complete 75-year Firdar sequence from birth |
| `firdar_at(jd_natal, jd_now, is_day)` | `FirdarPeriod` | Active Firdar period (major + sub) at jd_now |

#### `FirdarSeries` fields

| Field | Type | Description |
|---|---|---|
| `birth_jd` | `float` | Birth Julian Day |
| `is_day_birth` | `bool` | True for diurnal nativity |
| `periods` | `tuple[FirdarPeriod, ...]` | All 9 firdar major periods in sequence |
| `total_years` | `float` | Sum of all periods (~75 Julian years) |

#### `FirdarPeriod` fields (cycles.py vessel)

| Field | Type | Description |
|---|---|---|
| `ruler` | `str` | The planet (or node) governing this firdar |
| `start_jd` | `float` | Start JD UT of the major period |
| `end_jd` | `float` | End JD UT |
| `duration_years` | `float` | Duration in Julian years |
| `ordinal` | `int` | Position in the sequence (1–9) |
| `sub_periods` | `tuple[FirdarSubPeriod, ...] \| None` | 7 planetary sub-periods (None for nodal firdars) |

#### `FirdarSubPeriod` fields

| Field | Type | Description |
|---|---|---|
| `sub_ruler` | `str` | Governing planet for the sub-period |
| `start_jd` | `float` | Start JD UT |
| `end_jd` | `float` | End JD UT |
| `duration_years` | `float` | Duration in Julian years |

### Planetary Days and Hours

| Function | Returns | Description |
|---|---|---|
| `planetary_day_ruler(jd_ut)` | `PlanetaryDayInfo` | Chaldean day ruler for the given JD |
| `planetary_hours_for_day(jd_ut, latitude, longitude)` | `PlanetaryHoursProfile` | Full day and night planetary hour schedule |

#### `PlanetaryDayInfo` fields

| Field | Type | Description |
|---|---|---|
| `ruler` | `str` | Planet ruling this day (Chaldean order) |
| `weekday_name` | `str` | Name of the weekday |
| `weekday_number` | `int` | ISO weekday (1 = Monday, 7 = Sunday) |

#### `PlanetaryHour` fields

| Field | Type | Description |
|---|---|---|
| `hour_number` | `int` | 1–24 (1–12 = day hours, 13–24 = night hours) |
| `ruler` | `str` | Planet governing this hour |
| `start_jd` | `float` | Start of this hour (JD UT) |
| `end_jd` | `float` | End of this hour (JD UT) |
| `is_day_hour` | `bool` | True for a daytime (diurnal) hour |

#### `PlanetaryHoursProfile` fields

| Field | Type | Description |
|---|---|---|
| `day_info` | `PlanetaryDayInfo` | The day's ruler and weekday metadata |
| `sunrise_jd` | `float` | Sunrise JD used for the day's hours |
| `sunset_jd` | `float` | Sunset JD used |
| `next_sunrise_jd` | `float` | Next sunrise JD (used for nighttime hour duration) |
| `hours` | `tuple[PlanetaryHour, ...]` | All 24 hours in order (1–24) |
| `day_hour_length` | `float` | Duration of one daytime hour (days) |
| `night_hour_length` | `float` | Duration of one nighttime hour (days) |

---

## 11. Huber Method

```python
from moira.huber import (
    HouseZone,
    PHI, PHI_COMPLEMENT, CYCLE_YEARS, YEARS_PER_HOUSE,
    HouseZoneProfile, AgePointPosition, DynamicIntensity,
    PlanetIntensityScore, ChartIntensityProfile,
    house_zones, age_point, age_point_contacts,
    dynamic_intensity, intensity_at, chart_intensity_profile,
)
```

Implements the computational apparatus of the Huber method (Bruno and Louise Huber, Astrological Psychology Institute). Koch houses are prescribed by Huber doctrine; all functions accept any `HouseCusps` but note the doctrinal preference.

### Constants

| Constant | Value | Description |
|---|---|---|
| `PHI` | 0.6180... | Golden ratio fractional part |
| `PHI_COMPLEMENT` | 0.3819... | Complement of phi (1 − phi) |
| `CYCLE_YEARS` | 72.0 | Full Age Point cycle in years |
| `YEARS_PER_HOUSE` | 6.0 | Years the Age Point spends per house |

### `HouseZone` — golden-section zones

Each house is divided by the golden ratio into three developmental zones:

| Zone | Fraction | Quality |
|---|---|---|
| `CARDINAL` | 0.000 – 0.382 | Outward initiative, environmental engagement |
| `FIXED` | 0.382 – 0.618 | Consolidation, stable expression |
| `MUTABLE` | 0.618 – 1.000 | Transition, preparation for the next house |

### House Zone Analysis

```python
zones = house_zones(houses)
# list[HouseZoneProfile]  — one per house
```

#### `HouseZoneProfile` fields

| Field | Type | Description |
|---|---|---|
| `house` | `int` | House number (1–12) |
| `cusp_longitude` | `float` | Opening cusp longitude (°) |
| `next_cusp_longitude` | `float` | Next cusp longitude (°) |
| `house_size` | `float` | Angular size of the house (°) |
| `balance_point_longitude` | `float` | Balance Point longitude (cusp + 0.382 × size) |
| `low_point_longitude` | `float` | Low Point longitude (cusp + 0.618 × size) |
| `balance_point_fraction` | `float` | Always PHI_COMPLEMENT (~0.382) |
| `low_point_fraction` | `float` | Always PHI (~0.618) |

### Age Point

```python
ap = age_point(houses, jd_natal, jd_now)
# AgePointPosition
```

The Age Point progresses counterclockwise through the 12 houses over 72 years (6 years per house), starting from the Ascendant.

#### `AgePointPosition` fields

| Field | Type | Description |
|---|---|---|
| `age_years` | `float` | Age in years from birth |
| `cycle` | `int` | Which 72-year cycle (1 = first life, 2 = second…) |
| `house` | `int` | House number currently occupied (1–12) |
| `fraction_through_house` | `float` | 0.0 at cusp, 1.0 at next cusp |
| `longitude` | `float` | Ecliptic longitude of the Age Point (°) |
| `zone` | `HouseZone` | CARDINAL / FIXED / MUTABLE zone |
| `years_into_house` | `float` | Years elapsed since entering this house |
| `intensity` | `float` | Dynamic Intensity Curve value (0.0–1.0) |

```python
contacts = age_point_contacts(houses, jd_natal, jd_now, chart_longitudes, orb=2.0)
# list of bodies the Age Point is conjunct within orb
```

### Dynamic Intensity Curve

```python
di = dynamic_intensity(houses, longitude)
# DynamicIntensity(house, zone, fraction, intensity)

score = intensity_at(houses, longitude)
# float in [0.0, 1.0] — 1.0 at any cusp, minimum at the Low Point
```

### Chart Intensity Profile

```python
profile = chart_intensity_profile(houses, planet_longitudes)
# ChartIntensityProfile
```

Scores all natal planets against the Dynamic Intensity Curve and produces a chart-level summary.

#### `ChartIntensityProfile` fields

| Field | Type | Description |
|---|---|---|
| `scores` | `list[PlanetIntensityScore]` | Per-planet scores, highest first |
| `mean_intensity` | `float` | Mean intensity across all scored planets |
| `dominant_planet` | `str` | Planet with the highest intensity score |
| `dominant_zone` | `HouseZone` | Zone of the dominant planet |

`PlanetIntensityScore`: `planet`, `longitude`, `house`, `zone`, `fraction_through_house`, `intensity`.

```python
from moira.huber import house_zones, age_point, chart_intensity_profile
from moira.facade import Moira, HouseSystem
from datetime import datetime, timezone

m = Moira()
dt_birth = datetime(1988, 4, 4, 14, 30, tzinfo=timezone.utc)
dt_now   = datetime(2026, 4, 7, tzinfo=timezone.utc)

# Koch houses (Huber doctrine)
houses = m.houses(dt_birth, latitude=51.5, longitude=-0.1, system=HouseSystem.KOCH)
chart  = m.chart(dt_birth)

zones   = house_zones(houses)
ap      = age_point(houses, chart.jd_ut, m.jd(2026, 4, 7))
profile = chart_intensity_profile(houses, chart.longitudes())
print(f"Age Point: House {ap.house} ({ap.zone.value}), intensity {ap.intensity:.2f}")
print(f"Dominant planet: {profile.dominant_planet}")
```

---

## 12. Relational Techniques

### Synastry

```python
from moira.facade import (
    synastry_aspects, synastry_contacts,
    house_overlay, mutual_house_overlays,
    synastry_contact_relations, mutual_overlay_relations,
    synastry_condition_profiles, synastry_chart_condition_profile,
    synastry_condition_network_profile,
    SynastryHouseOverlay, MutualHouseOverlay,
    SynastryAspectTruth, SynastryAspectContact,
    SynastryOverlayTruth, SynastryRelation,
    SynastryConditionState, SynastryConditionProfile,
    SynastryChartConditionProfile,
    SynastryConditionNetworkProfile,
    SynastryAspectPolicy, SynastryOverlayPolicy,
    SynastryComputationPolicy,
)
```

| Function | Returns | Description |
|---|---|---|
| `synastry_aspects(chart_a, chart_b, tier=2, orbs=None, orb_factor=1.0, include_nodes=True)` | `list[AspectData]` | Inter-chart aspects |
| `synastry_contacts(chart_a, chart_b, ...)` | `list[SynastryAspectContact]` | Contacts with classification |
| `house_overlay(chart_source, target_houses, ...)` | `SynastryHouseOverlay` | chart_source planets in target_houses |
| `mutual_house_overlays(chart_a, houses_a, chart_b, houses_b, ...)` | `MutualHouseOverlay` | Both overlay directions |

### Composite Charts

```python
from moira.facade import (
    composite_chart, composite_chart_reference_place,
    CompositeChart,
)

comp = composite_chart(chart_a, chart_b, houses_a, houses_b)
# CompositeChart(planets: dict[str, PlanetData], houses: HouseCusps | None)
```

### Davison Relationship Charts

```python
from moira.facade import (
    davison_chart, davison_chart_uncorrected,
    davison_chart_reference_place, davison_chart_spherical_midpoint,
    davison_chart_corrected,
    DavisonChart, DavisonInfo,
)
```

Four variants differing in how the geographic and temporal midpoints are computed:

| Variant | Function | Midpoint time | Midpoint location |
|---|---|---|---|
| Standard | `davison_chart` | JD arithmetic mean | Spherical midpoint |
| Uncorrected | `davison_chart_uncorrected` | Arithmetic mean | Arithmetic mean |
| Reference Place | `davison_chart_reference_place` | Arithmetic mean | Supplied explicitly |
| Spherical | `davison_chart_spherical_midpoint` | Arithmetic mean | Great-circle midpoint |
| Corrected | `davison_chart_corrected` | Corrected for JD midpoint | Spherical midpoint |

`DavisonChart`: `chart` (Chart), `info` (DavisonInfo — midpoint JD, lat, lon).

---

## 13. Geography

### Astro*Carto*Graphy

```python
from moira.facade import acg_lines, acg_from_chart, ACGLine
```

| Function | Returns | Description |
|---|---|---|
| `acg_lines(planet_ra_dec, gmst_deg, lat_step=2.0)` | `list[ACGLine]` | ACG lines given a pre-built RA/Dec dict and GMST |
| `acg_from_chart(chart, bodies=None, lat_step=2.0)` | `list[ACGLine]` | ACG lines directly from a `Chart` |

`acg_lines` is the low-level engine. `acg_from_chart` is a convenience wrapper that
handles GAST extraction and calls `sky_position_at` for each body.

#### `ACGLine` fields

| Field | Type | Description |
|---|---|---|
| `planet` | `str` | Body name |
| `line_type` | `str` | `"MC"` / `"IC"` / `"ASC"` / `"DSC"` |
| `longitude` | `float \| None` | Geographic longitude for MC/IC meridians |
| `points` | `list[tuple[float, float]]` | `(lat, lon)` curve points for ASC/DSC |

MC/IC lines are meridians: `longitude` is set, `points` is empty.
ASC/DSC lines are curves: `points` is set, `longitude` is `None`.

```python
from moira.facade import Moira, Body
from datetime import datetime, timezone

m = Moira()
dt = datetime(1988, 4, 4, 14, 30, tzinfo=timezone.utc)
chart = m.chart(dt)

lines = m.astrocartography(chart, observer_lat=51.5, observer_lon=-0.1)
for line in lines:
    if line.line_type == "MC":
        print(f"{line.planet} MC meridian: {line.longitude:.2f}°E")
    else:
        print(f"{line.planet} {line.line_type}: {len(line.points)} points")
```

### Local Space

```python
from moira.facade import local_space_positions, local_space_from_chart, LocalSpacePosition
```

| Function | Returns | Description |
|---|---|---|
| `local_space_positions(planet_ra_dec, latitude, lst_deg)` | `list[LocalSpacePosition]` | Azimuth/altitude from RA/Dec and LST |
| `local_space_from_chart(chart, observer_lat, observer_lon, bodies=None)` | `list[LocalSpacePosition]` | Convenience wrapper for a `Chart` |

#### `LocalSpacePosition` fields

| Field | Type | Description |
|---|---|---|
| `body` | `str` | Body name |
| `azimuth` | `float` | Compass bearing 0-360 degrees (North = 0, East = 90) |
| `altitude` | `float` | Elevation above (+) or below (-) horizon |
| `is_above` | `bool` | True when `altitude >= 0` |

**Method:** `compass_direction() -> str` - returns an 8-point compass label (N/NE/E/SE/S/SW/W/NW).

```python
ls = m.local_space(chart, latitude=51.5, longitude=-0.1)
for pos in ls:
    arrow = "↑" if pos.is_above else "↓"
    print(f"{pos.body:10s}  Az {pos.azimuth:.1f}° {pos.compass_direction():2s}  "
          f"Alt {pos.altitude:+.1f}° {arrow}")
```

### Parans

Parans identify simultaneous horizon and meridian crossings shared by two stars
or planets — a complementary layer to ACG.

```python
from moira.facade import (
    find_parans, natal_parans,
    evaluate_paran_site, sample_paran_field, analyze_paran_field,
    evaluate_paran_stability, extract_paran_field_contours,
    consolidate_paran_contours, analyze_paran_field_structure,
    Paran, ParanCrossing, ParanSignature, ParanStrength,
    ParanSiteResult, ParanFieldSample, ParanFieldAnalysis,
    ParanContourPathSet, ParanFieldStructure,
    DEFAULT_PARAN_POLICY, CIRCLE_TYPES,
)
```

| Function | Returns | Description |
|---|---|---|
| `find_parans(bodies, jd_day, lat, lon, orb_minutes=4.0, policy=None)` | `list[Paran]` | Paran crossings for a supplied body-name list at a location |
| `natal_parans(bodies, natal_jd, lat, lon, orb_minutes=4.0)` | `list[Paran]` | Natal paran crossings for a supplied body-name list |
| `evaluate_paran_site(lat, lon, parans)` | `ParanSiteResult` | Score a relocation site by paran activity |
| `sample_paran_field(jd_ut, lat_range, lon_range, ...)` | `list[ParanFieldSample]` | Grid of paran scores over a geographic region |
| `analyze_paran_field(samples)` | `ParanFieldAnalysis` | Identify peaks, regions, crossings in field |
| `evaluate_paran_stability(lat, lon, jd_start, jd_end, ...)` | `ParanStability` | Paran activity stability over time |
| `extract_paran_field_contours(samples, threshold)` | `ParanContourExtraction` | Contour lines at a paran score threshold |
| `consolidate_paran_contours(contours)` | `ParanContourPathSet` | Merge and sort contour paths |
| `analyze_paran_field_structure(samples, ...)` | `ParanFieldStructure` | Full structural analysis: hierarchy + associations |

#### `Paran` fields

| Field | Type | Description |
|---|---|---|
| `body1` | `str` | First body |
| `body2` | `str` | Second body |
| `circle1` | `str` | Circle type for the first body |
| `circle2` | `str` | Circle type for the second body |
| `jd1` | `float` | Event JD for the first body crossing |
| `jd2` | `float` | Event JD for the second body crossing |
| `orb_min` | `float` | Difference between the crossings in arcminutes of time |
| `crossing1` | `ParanCrossing` | Crossing details for the first body |
| `crossing2` | `ParanCrossing` | Crossing details for the second body |
| `signature` | `ParanSignature` | Combined paran signature metadata |

---

## 14. Fixed Stars

### Unified fixed-star surface (`star_registry.csv` + metadata sidecars)

```python
from moira.facade import (
    star_at, all_stars_at,
    list_named_stars, find_named_stars, list_stars, find_stars, star_magnitude,
    load_catalog,
    heliacal_rising_event, heliacal_setting_event, heliacal_rising, heliacal_setting,
    heliacal_catalog_batch,
    star_chart_condition_profile, star_condition_network_profile,
    FixedStar, HeliacalEvent, HeliacalBatchResult,
    FixedStarLookupPolicy, HeliacalSearchPolicy, FixedStarComputationPolicy,
    FixedStarTruth, FixedStarClassification,
    UnifiedStarRelation, UnifiedStarMergePolicy, UnifiedStarComputationPolicy,
    StarConditionState, StarConditionProfile,
    StarChartConditionProfile, StarConditionNetworkProfile,
)
```

| Function | Returns | Description |
|---|---|---|
| `star_at(name, jd_tt, policy=None)` | `FixedStar` | Public fixed-star lookup, with sovereign registry data and Gaia-derived enrichment fields when available |
| `all_stars_at(jd_tt)` | `dict[str, FixedStar]` | All named stars at one epoch |
| `list_named_stars()` / `list_stars()` | `list[str]` | All named stars in the sovereign registry |
| `find_named_stars(query)` / `find_stars(query)` | `list[str]` | Fuzzy search across named stars and nomenclature aliases |
| `star_magnitude(name)` | `float` | Visual magnitude |
| `load_catalog()` | `None` | Reload the sovereign fixed-star registry and indexes |
| `heliacal_rising(name, jd_ut, latitude, longitude)` | `float \| None` | JD of heliacal rising |
| `heliacal_setting(name, jd_ut, latitude, longitude)` | `float \| None` | JD of heliacal setting |
| `heliacal_rising_event(name, jd_ut, lat, lon)` | `HeliacalEvent` | Heliacal rising with classification |
| `heliacal_setting_event(name, jd_ut, lat, lon)` | `HeliacalEvent` | Heliacal setting with classification |
| `heliacal_catalog_batch(event_kind, jd_start, latitude, longitude, *, max_magnitude=6.5, names=None, search_days=400, policy=None)` | `HeliacalBatchResult` | Batch heliacal search across the fixed-star registry |

There is no separate public `fixed_star_at` function in 1.0.3. The public
lookup surface is `star_at(...)`, which returns a `FixedStar` vessel.

Specialty module helper: `from moira.stars import star_light_time_split`
returns `(observed, true)` fixed-star positions separated by stellar light-time,
but it is not re-exported by `moira.facade` in 1.0.3.

#### Catalog convenience sets

`royal_stars.py` and `behenian_stars.py` are standalone sub-modules — not re-exported at the `moira` top-level. Import them directly:

```python
from moira.royal_stars import (
    list_royal_stars, available_royal_stars, royal_star_at,
    ALDEBARAN, REGULUS, ANTARES, FOMALHAUT,
)
from moira.behenian_stars import (
    list_behenian_stars, available_behenian_stars, behenian_star_at,
    ALGOL, ALCYONE, SIRIUS, SPICA, ARCTURUS, ALPHECCA, VEGA,  # + 8 more constants
)
```

### Search helpers and merged fields

| Function | Returns | Description |
|---|---|---|
| `star_at(name, jd_tt)` | `FixedStar` | Named star with Gaia enrichment when available |
| `stars_near(longitude, orb, jd_tt)` | `list[FixedStar]` | Stars within `orb`° of a longitude |
| `stars_by_magnitude(max_mag, jd_tt)` | `list[FixedStar]` | Stars brighter than `max_mag` |
| `list_named_stars()` | `list[str]` | All traditionally-named stars |
| `find_named_stars(query)` | `list[str]` | Fuzzy name search across named stars |

#### `FixedStar` fields

| Field | Type | Description |
|---|---|---|
| `name` | `str` | Traditional name |
| `nomenclature` | `str \| None` | Catalog designation or alternate nomenclature |
| `longitude` | `float` | Ecliptic longitude (°) |
| `latitude` | `float` | Ecliptic latitude (°) |
| `magnitude` | `float` | Visual magnitude |
| `bp_rp` | `float \| None` | Gaia BP−RP colour index |
| `teff_k` | `float \| None` | Effective temperature (K) from Gaia |
| `parallax_mas` | `float \| None` | Gaia parallax (mas) |
| `distance_ly` | `float \| None` | Distance in light-years |
| `quality` | `StellarQuality \| None` | Stellar classification from Gaia colours |
| `source` | `str` | Data source used for the merged record |
| `is_topocentric` | `bool` | Whether topocentric correction was applied |
| `computation_truth` | `FixedStarTruth` | Computation truth data |
| `classification` | `FixedStarClassification` | Classification metadata |
| `relation` | `UnifiedStarRelation` | Relation metadata |
| `condition_profile` | `StarConditionProfile` | Consolidated star condition profile |

### Gaia enrichment status

`FixedStar` records may expose Gaia-derived fields such as `bp_rp`,
`parallax_mas`, `distance_ly`, and `quality`, but Moira 1.0.3 does not export a
standalone public Gaia loader/query surface. Gaia enrichment is internal to the
merged fixed-star API rather than a separate public subsystem.

### General visibility engine

Moira also exposes a generalized observational visibility layer that is broader
than the fixed-star heliacal helpers. This is the public surface used for
criterion-based visibility judgments and event searches.

```python
from moira.facade import (
    HeliacalEventKind, VisibilityTargetKind,
    LightPollutionClass, LightPollutionDerivationMode,
    ObserverAid, ObserverVisibilityEnvironment,
    VisibilityCriterionFamily, VisibilityExtinctionModel, VisibilityTwilightModel,
    ExtinctionCoefficient, MoonlightPolicy,
    VisibilityPolicy, VisibilitySearchPolicy,
    LunarCrescentVisibilityClass, LunarCrescentDetails,
    VisibilityAssessment, GeneralVisibilityEvent,
    visibility_assessment, visual_limiting_magnitude, visibility_event,
)
```

| Function | Returns | Description |
|---|---|---|
| `visibility_assessment(body, jd_ut, lat, lon, *, policy=None)` | `VisibilityAssessment` | Criterion-based visibility judgment at one observing moment |
| `visual_limiting_magnitude(jd_ut, lat, lon, *, policy=None)` | `float` | Estimated naked-eye limiting magnitude at the site and time |
| `visibility_event(body, event_kind, jd_start, lat, lon, *, heliacal_policy=None, visibility_policy=None, search_policy=None)` | `GeneralVisibilityEvent \| None` | Search for the next generalized visibility event matching the requested kind |

Key policy and vessel types: `VisibilityPolicy`, `VisibilitySearchPolicy`,
`VisibilityAssessment`, `GeneralVisibilityEvent`, `ObserverVisibilityEnvironment`,
`LunarCrescentDetails`.

### Variable Stars

```python
from moira.facade import (
    variable_star, list_variable_stars, variable_stars_by_type,
    phase_at, magnitude_at, next_minimum, next_maximum,
    minima_in_range, maxima_in_range,
    malefic_intensity, benefic_strength, is_in_eclipse,
    algol_phase, algol_magnitude, algol_next_minimum, algol_is_eclipsed,
    star_phase_state, star_condition_profile, catalog_profile, star_state_pair,
    validate_variable_star_catalog,
    VariableStar, VarType, VarStarPolicy, DEFAULT_VAR_STAR_POLICY,
    StarPhaseState, StarConditionProfile, CatalogProfile, StarStatePair,
)
```

#### `VarType` — variable star classification

| Constant | Meaning |
|---|---|
| `VarType.ECLIPSING_ALGOL` | Algol-type (EA) — sharp minima |
| `VarType.ECLIPSING_BETA` | Beta Lyrae-type (EB) — continuous variation |
| `VarType.ECLIPSING_W_UMA` | W Ursae Maj.-type (EW) — contact binaries |
| `VarType.CEPHEID` | Delta Cephei-type pulsating |
| `VarType.RR_LYRAE` | RR Lyrae pulsating |
| `VarType.MIRA` | Mira-type long-period |
| `VarType.SEMI_REG_SG` | Semi-regular supergiant |
| `VarType.SEMI_REG` | Semi-regular |

#### `VariableStar` fields

| Field | Type | Description |
|---|---|---|
| `name` | `str` | Star name |
| `designation` | `str \| None` | Catalog designation |
| `var_type` | `VarType` | Variability classification |
| `period_days` | `float` | Period in days (0 if irregular) |
| `epoch_jd` | `float` | Reference epoch JD |
| `epoch_is_minimum` | `bool` | True when the epoch is a minimum, False when it is a maximum |
| `mag_max` | `float` | Magnitude at maximum brightness |
| `mag_min` | `float` | Magnitude at minimum brightness |
| `mag_min2` | `float \| None` | Secondary minimum magnitude when applicable |
| `eclipse_width` | `float` | Eclipse duration as fraction of period (EA only) |
| `classical_quality` | `str` | "malefic" / "benefic" / "neutral" / "mixed" |
| `note` | `str` | Short catalog note |

**Derived properties:** `amplitude`, `is_eclipsing`, `is_pulsating`, `is_long_period`,
`is_irregular`, `is_malefic`, `is_benefic`, `type_class`.

#### Core functions

| Function | Returns | Description |
|---|---|---|
| `variable_star(name)` | `VariableStar` | Look up a star by name |
| `list_variable_stars()` | `list[str]` | All catalog star names (20 stars) |
| `variable_stars_by_type(var_type)` | `list[VariableStar]` | Filter catalog by type |
| `phase_at(star, jd)` | `float` | Phase in [0, 1) at a given JD |
| `magnitude_at(star, jd)` | `float` | Interpolated visual magnitude |
| `malefic_intensity(star, jd, policy=None)` | `float` | Malefic score [0, 1] |
| `benefic_strength(star, jd, policy=None)` | `float` | Benefic score [0, 1] |
| `is_in_eclipse(star, jd, policy=None)` | `bool` | True when near minimum for eclipsing type |
| `next_minimum(star, jd)` | `float` | JD of next minimum |
| `next_maximum(star, jd)` | `float` | JD of next maximum |
| `minima_in_range(star, jd_start, jd_end)` | `list[float]` | All minima in range |
| `maxima_in_range(star, jd_start, jd_end)` | `list[float]` | All maxima in range |

#### Algol convenience functions

| Function | Returns | Description |
|---|---|---|
| `algol_phase(jd)` | `float` | Algol phase at JD |
| `algol_magnitude(jd)` | `float` | Algol magnitude at JD |
| `algol_next_minimum(jd)` | `float` | JD of next Algol minimum |
| `algol_is_eclipsed(jd, policy=None)` | `bool` | True when Algol is near minimum |

#### Condition profile API

```python
state   = star_phase_state(star, jd)
# StarPhaseState(star, jd, phase, magnitude, malefic_score, benefic_score, in_eclipse)

profile = star_condition_profile(star, jd)
# StarConditionProfile — catalog truth + dynamic state in one record

cat     = catalog_profile(jd)
# CatalogProfile — aggregate over all 20 catalog stars

pair    = star_state_pair(star_a, star_b, jd)
# StarStatePair(primary, secondary) with structural relationship properties
```

### Multiple Star Systems

```python
from moira.facade import (
    multiple_star, list_multiple_stars, multiple_stars_by_type,
    angular_separation_at, position_angle_at,
    is_resolvable, dominant_component, combined_magnitude, components_at,
    sirius_ab_separation_at, sirius_b_resolvable,
    castor_separation_at, alpha_cen_separation_at,
    MultipleStarSystem, StarComponent, OrbitalElements, MultiType,
)
```

| Function | Returns | Description |
|---|---|---|
| `multiple_star(name)` | `MultipleStarSystem` | Retrieve a multiple-star system by name |
| `list_multiple_stars()` | `list[str]` | All catalog system names |
| `multiple_stars_by_type(multi_type)` | `list[MultipleStarSystem]` | Filter by system type |
| `angular_separation_at(system, jd_tt)` | `float` | Current angular separation (arcsec) |
| `position_angle_at(system, jd_tt)` | `float` | Current position angle (°) |
| `is_resolvable(system, jd_tt, aperture_mm)` | `bool` | True if resolvable with aperture |
| `dominant_component(system)` | `StarComponent` | Brighter/primary component |
| `combined_magnitude(system)` | `float` | Combined visual magnitude |
| `components_at(system, jd_tt)` | `dict` | Full component/separation snapshot for the system |
| `sirius_ab_separation_at(jd_tt)` | `float` | Sirius A–B separation (arcsec) |
| `sirius_b_resolvable(jd_tt, aperture_mm=200)` | `bool` | True if Sirius B is resolvable |
| `castor_separation_at(jd_tt)` | `float` | Castor AB separation (arcsec) |
| `alpha_cen_separation_at(jd_tt)` | `float` | α Cen A–B separation (arcsec) |

`MultiType` constants: `VISUAL  WIDE  SPECTROSCOPIC  OPTICAL`

---

## 15. Eclipses & Phenomena

### Solar & Lunar Eclipses

```python
from moira.facade import (
    EclipseData, EclipseEvent, EclipseType, EclipseCalculator,
    SolarBodyCircumstances, SolarEclipseLocalCircumstances,
    LocalContactCircumstances, LunarEclipseAnalysis, LunarEclipseLocalCircumstances,
)

calc = EclipseCalculator(reader=get_reader())
data = calc.calculate(dt)           # EclipseData
```

#### `EclipseData` fields

| Field | Type | Description |
|---|---|---|
| `sun_longitude` | `float` | Sun longitude at the evaluated moment |
| `moon_longitude` | `float` | Moon longitude at the evaluated moment |
| `node_longitude` | `float` | Node longitude at the evaluated moment |
| `moon_latitude` | `float` | Moon latitude relative to the ecliptic |
| `eclipse_type` | `EclipseType` | TOTAL_SOLAR / ANNULAR / PARTIAL_SOLAR / PENUMBRAL / PARTIAL_LUNAR / TOTAL_LUNAR |
| `is_eclipse_season` | `bool` | Whether the Sun is close enough to the nodes for eclipse season |
| `is_solar_eclipse` | `bool` | Solar eclipse flag |
| `is_lunar_eclipse` | `bool` | Lunar eclipse flag |
| `eclipse_magnitude` | `float` | Computed eclipse magnitude |
| `saros_index` | `float` | Saros cycle position/index |
| `metonic_year` | `float` | Metonic cycle position |
| `moon_distance_km` | `float` | Geocentric Moon distance in kilometers |
| `galactic_center_longitude` | `float` | Galactic center longitude reference |
| `sun_apparent_radius` | `float` | Apparent solar radius |
| `moon_apparent_radius` | `float` | Apparent lunar radius |
| `earth_shadow_apparent_radius` | `float` | Apparent umbral radius |
| `earth_penumbra_apparent_radius` | `float` | Apparent penumbral radius |
| `sun_stone` | `int` | Aubrey-stone style solar index |
| `moon_stone` | `int` | Aubrey-stone style lunar index |
| `node_stone` | `int` | Aubrey-stone style node index |
| `south_node_stone` | `int` | Aubrey-stone style south-node index |
| `angular_separation_3d` | `float` | 3D Sun/Moon angular separation |
| `solar_topocentric_separation` | `float` | Topocentric Sun/Moon separation |
| `sun_node_distance` | `float` | Distance from Sun to node |
| `metonic_is_reset` | `bool` | Whether the Metonic cycle resets here |
| `moon_parallax` | `float` | Lunar parallax |
| `sun_side` | `int` | Stonehenge side index for the Sun |
| `sun_pos_in_side` | `int` | Position of the Sun within the side index |

#### NASA-compatible lunar eclipse API

```python
from moira.facade import (
    NasaLunarEclipseContacts, NasaLunarEclipseEvent,
    next_nasa_lunar_eclipse, previous_nasa_lunar_eclipse,
    translate_lunar_eclipse_event,
)

event = next_nasa_lunar_eclipse(jd_start, reader=reader)
prev  = previous_nasa_lunar_eclipse(jd_start, reader=reader)
```

### Planetary Phenomena

```python
from moira.facade import (
    greatest_elongation, perihelion, aphelion,
    next_moon_phase, moon_phases_in_range,
    PhenomenonEvent,
)
```

| Function | Returns | Description |
|---|---|---|
| `greatest_elongation(body, jd_start, direction="east", reader=None, max_days=600.0)` | `PhenomenonEvent \| None` | Next greatest elongation of Mercury or Venus in the requested direction |
| `perihelion(body, jd_start, reader=None, max_days=None)` | `PhenomenonEvent \| None` | Next perihelion passage |
| `aphelion(body, jd_start, reader=None, max_days=None)` | `PhenomenonEvent \| None` | Next aphelion passage |
| `next_moon_phase(phase_name, jd_start, reader=None)` | `PhenomenonEvent` | Next exact named moon phase (`"New Moon"`, `"First Quarter"`, `"Full Moon"`, etc.) |
| `moon_phases_in_range(jd_start, jd_end, reader=None)` | `list[PhenomenonEvent]` | All eight standard moon phases in a date range |

`PhenomenonEvent`: `body`, `phenomenon`, `jd_ut`, `value`.

### Occultations

```python
from moira.facade import (
    close_approaches, lunar_occultation, lunar_star_occultation, all_lunar_occultations,
    CloseApproach, LunarOccultation,
)
```

| Function | Returns | Description |
|---|---|---|
| `close_approaches(body_a, body_b, jd_start, jd_end, max_sep_deg=1.0, step_days=0.5, reader=None)` | `list[CloseApproach]` | Close conjunctions within the requested separation threshold |
| `lunar_occultation(body, jd_start, jd_end, reader=None)` | `list[LunarOccultation]` | Moon occultation events for a planet |
| `lunar_star_occultation(star_lon, star_lat, star_name, jd_start, jd_end, step_days=0.25, observer_lat=None, observer_lon=None, observer_elev_m=0.0, reader=None)` | `list[LunarOccultation]` | Moon occultation of a fixed star at a supplied ecliptic position |
| `all_lunar_occultations(jd_start, jd_end, planets=None, reader=None)` | `list[LunarOccultation]` | Lunar occultations for the default planet set or a supplied planet list |

### Sothic Cycle (Egyptian calendar)

```python
from moira.facade import (
    sothic_rising, sothic_epochs, sothic_drift_rate,
    egyptian_civil_date, days_from_1_thoth, predicted_sothic_epoch_year,
    sothic_chart_condition_profile, sothic_condition_network_profile,
    EgyptianDate, SothicEntry, SothicEpoch,
    EGYPTIAN_MONTHS, EGYPTIAN_SEASONS, EPAGOMENAL_BIRTHS,
    HISTORICAL_SOTHIC_EPOCHS,
    SothicComputationPolicy,
)
```

| Function | Returns | Description |
|---|---|---|
| `sothic_rising(latitude, longitude, year_start, year_end, epoch_jd=1772027.5, arcus_visionis=10.0, policy=None)` | `list[SothicEntry]` | Sirius heliacal rising entries across a year range |
| `sothic_epochs(latitude, longitude, year_start, year_end, epoch_jd=1772027.5, tolerance_days=1.0, arcus_visionis=10.0, policy=None)` | `list[SothicEpoch]` | New Year coincidences across a year range |
| `sothic_drift_rate(entries)` | `float` | Drift rate derived from a `list[SothicEntry]` |
| `egyptian_civil_date(jd, epoch_jd=1772027.5, policy=None)` | `EgyptianDate` | Wandering civil calendar date |
| `days_from_1_thoth(jd, epoch_jd=1772027.5)` | `float` | Days elapsed since the last 1 Thoth |
| `predicted_sothic_epoch_year(known_epoch_year, n_cycles, cycle_length_years=1460.0, policy=None)` | `float` | Predicted year after one or more Sothic cycles |

`HISTORICAL_SOTHIC_EPOCHS`: list of known historical epoch dates.
`EPAGOMENAL_BIRTHS`: five epagomenal days and their mythological births.

---

## 16. Harmograms — Spectral Harmonic Analysis

```python
from moira.harmograms import (
    # Core computation
    harmonic_vector, point_set_harmonic_vector,
    zero_aries_parts_harmonic_vector, parts_from_zero_aries,
    intensity_function_spectrum, project_harmogram_strength,
    harmogram_trace,
    # Vessels
    HarmonicDomain,
    HarmonicVectorComponent, PointSetHarmonicVector,
    ZeroAriesPart, ZeroAriesPartsSet, ZeroAriesPartsHarmonicVector,
    IntensitySpectrumComponent, IntensityFunctionSpectrum,
    HarmogramProjectionTerm, HarmogramProjection, HarmogramDominantTerm,
    HarmogramTraceSample, HarmogramTraceSeries, HarmogramTrace,
    IntensitySpectrumComparisonTerm, IntensitySpectrumComparison,
    HarmogramTraceSeriesComparisonSample, HarmogramTraceSeriesComparison,
    # Policies
    HarmogramPolicy, HarmogramIntensityPolicy, HarmogramSamplingPolicy,
    PointSetHarmonicVectorPolicy, ZeroAriesPartsPolicy,
    # Enums
    HarmonicVectorNormalizationMode, ZeroAriesPairConstructionMode, SelfPairMode,
    HarmogramIntensityFamily, HarmogramOrbMode, GaussianWidthParameterMode,
    HarmogramOrbScalingMode, HarmogramSymmetryMode,
    IntensityNormalizationMode, IntensitySpectrumRealizationMode,
    HarmogramProjectionRealizationMode, HarmogramSamplingMode,
    HarmogramOutputMode, HarmogramChartDomain, HarmogramTraceFamily,
    # Research tools
    dominant_harmonic_contributors, compare_intensity_spectra, compare_trace_series,
)
```

The Harmograms engine is a **research-facing** spectral harmonic analysis subsystem. It is deliberately distinct from `moira.harmonics` (which computes classical harmonic chart positions for individual bodies). This package deals with harmonic *spectra* — the Fourier-style decomposition of an entire point set's angular distribution, not single-body positions.

**This module does not generate astrological positions.** It analyzes collections of longitudes (already computed by the position engines) for their harmonic structure.

The central concepts:

- **Harmonic vector** — the resultant vector of a point set projected onto the unit circle at harmonic H. Amplitude near 1.0 means the points cluster at H-fold symmetry; near 0.0 means they are uniformly distributed.
- **Zero-Aries parts** — pairwise angular differences between all bodies, projected to [0°, 360°). These are the raw material for the harmogram spectrum.
- **Intensity function spectrum** — the spectral distribution of harmonic energy across a defined harmonic domain.
- **Harmogram trace** — a time-domain trace of harmonic strength as the sky moves.
- **Harmogram projection** — decomposes a total strength value back onto per-harmonic contributions.

---

### `HarmonicDomain` — harmonic range specifier

```python
domain = HarmonicDomain(harmonic_start=1, harmonic_stop=12)
# .harmonics → tuple of all integers in [start, stop]
```

| Field | Type | Default | Description |
|---|---|---|---|
| `harmonic_start` | `int` | 1 | First harmonic (must be ≥ 1) |
| `harmonic_stop` | `int` | 12 | Last harmonic (must be ≥ start) |

**Property:** `harmonics` → `tuple[int, ...]` of all harmonics in the range.

---

### Core Data Vessels

#### `HarmonicVectorComponent` — single harmonic result

| Field | Type | Description |
|---|---|---|
| `harmonic` | `int` | Harmonic number (≥ 1) |
| `amplitude` | `float` | Resultant amplitude (≥ 0); 1.0 = perfect clustering at this harmonic |
| `phase_deg` | `float` | Phase of the resultant vector (°), [0°, 360°) |

**Property:** `amplitude_squared`.

#### `PointSetHarmonicVector` — harmonic vector for a named point set

| Field | Type | Description |
|---|---|---|
| `policy` | `PointSetHarmonicVectorPolicy` | Normalization and domain policy used |
| `body_names` | `tuple[str, ...]` | Names of the contributing points |
| `point_count` | `int` | Number of points |
| `harmonic_zero_amplitude` | `float` | H=0 amplitude (reflects normalization) |
| `components` | `tuple[HarmonicVectorComponent, ...]` | One component per harmonic in the domain |

**Method:** `get_component(harmonic)` → `HarmonicVectorComponent`.

#### `ZeroAriesPart` — one pairwise angular difference

| Field | Type | Description |
|---|---|---|
| `source_name` | `str` | Source body |
| `target_name` | `str` | Target body |
| `longitude_deg` | `float` | Angular difference projected to [0°, 360°) |

#### `ZeroAriesPartsSet` — collection of pairwise parts

| Field | Type | Description |
|---|---|---|
| `policy` | `ZeroAriesPartsPolicy` | Construction policy |
| `source_body_names` | `tuple[str, ...]` | Source body names |
| `target_body_names` | `tuple[str, ...]` | Target body names |
| `parts` | `tuple[ZeroAriesPart, ...]` | All constructed parts |

**Properties:** `source_point_count`, `target_point_count`, `parts_count`.

#### `ZeroAriesPartsHarmonicVector` — harmonic vector for a parts set

| Field | Type | Description |
|---|---|---|
| `vector_policy` | `PointSetHarmonicVectorPolicy` | Normalization policy |
| `parts_policy` | `ZeroAriesPartsPolicy` | Parts construction policy |
| `source_body_names` | `tuple[str, ...]` | Source bodies |
| `target_body_names` | `tuple[str, ...]` | Target bodies |
| `parts_count` | `int` | Number of parts contributing |
| `harmonic_zero_amplitude` | `float` | H=0 amplitude |
| `components` | `tuple[HarmonicVectorComponent, ...]` | Per-harmonic components |

**Method:** `get_component(harmonic)` → `HarmonicVectorComponent`.

---

### Intensity Function Spectrum

The intensity function spectrum evaluates how strongly the point set concentrates at each harmonic. Unlike the harmonic vector (which uses raw resultants), the intensity function applies a bell-shaped orb around each aspect, making it sensitive to near-aspect clustering.

```python
spectrum = intensity_function_spectrum(longitudes, harmonic, policy=...)
# IntensityFunctionSpectrum
```

#### `IntensitySpectrumComponent` fields

| Field | Type | Description |
|---|---|---|
| `harmonic` | `int` | Harmonic number |
| `amplitude` | `float` | Intensity amplitude at this harmonic (≥ 0) |
| `phase_deg` | `float` | Phase (°), [0°, 360°) |

#### `IntensityFunctionSpectrum` fields

| Field | Type | Description |
|---|---|---|
| `policy` | `HarmogramIntensityPolicy` | Intensity policy used |
| `harmonic_number` | `int` | The primary harmonic being analyzed |
| `realization_mode` | `IntensitySpectrumRealizationMode` | Computation method |
| `harmonic_zero_amplitude` | `float` | H=0 reference amplitude |
| `components` | `tuple[IntensitySpectrumComponent, ...]` | Per-harmonic components |

**Method:** `get_component(harmonic)` → `IntensitySpectrumComponent`.

---

### Harmogram Projection

Projects a harmogram strength back onto per-harmonic contributions, showing which harmonics drive the total score.

```python
proj = project_harmogram_strength(source_vector, intensity_spectrum, policy=...)
# HarmogramProjection
```

#### `HarmogramProjectionTerm` fields (one per harmonic)

| Field | Type | Description |
|---|---|---|
| `harmonic` | `int` | Harmonic number |
| `source_amplitude` | `float` | Source vector amplitude at this harmonic |
| `source_phase_deg` | `float` | Source vector phase at this harmonic |
| `intensity_amplitude` | `float` | Intensity spectrum amplitude at this harmonic |
| `intensity_phase_deg` | `float` | Intensity spectrum phase at this harmonic |
| `signed_contribution` | `float` | Signed contribution to total strength (positive = reinforcing) |

#### `HarmogramProjection` fields

| Field | Type | Description |
|---|---|---|
| `source_vector` | `PointSetHarmonicVector \| ZeroAriesPartsHarmonicVector` | Source point set |
| `intensity_spectrum` | `IntensityFunctionSpectrum` | Intensity spectrum used |
| `normalization_mode` | `HarmonicVectorNormalizationMode` | Normalization applied |
| `realization_mode` | `HarmogramProjectionRealizationMode` | Computation method |
| `harmonic_zero_contribution` | `float` | H=0 contribution |
| `total_strength` | `float` | Total projected strength (sum of all term contributions) |
| `terms` | `tuple[HarmogramProjectionTerm, ...]` | One term per harmonic |

**Method:** `get_term(harmonic)` → `HarmogramProjectionTerm`.

---

### Harmogram Trace

A time-domain trace of projected harmonic strength across a sequence of sky epochs.

```python
trace = harmogram_trace(jd_sequence, natal_longitudes, harmonic, policy=...)
# HarmogramTrace
```

#### `HarmogramTraceSample` fields (one per epoch)

| Field | Type | Description |
|---|---|---|
| `sample_index` | `int` | Index into the epoch sequence (≥ 0) |
| `sample_time` | `float` | JD of this sample |
| `source_vector` | `ZeroAriesPartsHarmonicVector` | Parts vector for this epoch |
| `projection` | `HarmogramProjection` | Full projection at this epoch |
| `total_strength` | `float` | Total projected strength at this epoch |

#### `HarmogramTraceSeries` fields

| Field | Type | Description |
|---|---|---|
| `harmonic_number` | `int` | The harmonic being traced |
| `intensity_spectrum` | `IntensityFunctionSpectrum` | Shared intensity spectrum |
| `samples` | `tuple[HarmogramTraceSample, ...]` | All samples in epoch order |

**Property:** `strengths` → `tuple[float, ...]` of `total_strength` per sample.

#### `HarmogramTrace` fields

| Field | Type | Description |
|---|---|---|
| `policy` | `HarmogramPolicy` | Governing policy |
| `interval_start` | `float` | JD start of the trace interval |
| `interval_stop` | `float` | JD end of the trace interval |
| `sample_times` | `tuple[float, ...]` | All epoch JDs in order |
| `series` | `tuple[HarmogramTraceSeries, ...]` | One series per harmonic in the output |

---

### Research Tools

```python
dominant = dominant_harmonic_contributors(projection, top_n=5)
# list[HarmogramDominantTerm]  — harmonics ranked by |signed_contribution|
```

#### `HarmogramDominantTerm` fields

| Field | Type | Description |
|---|---|---|
| `harmonic` | `int` | Harmonic number |
| `absolute_contribution` | `float` | Absolute value of the contribution (≥ 0) |
| `signed_contribution` | `float` | Signed contribution (positive = reinforcing) |

```python
cmp = compare_intensity_spectra(spectrum_a, spectrum_b)
# IntensitySpectrumComparison
```

#### `IntensitySpectrumComparison` fields

| Field | Type | Description |
|---|---|---|
| `left` | `IntensityFunctionSpectrum` | First spectrum |
| `right` | `IntensityFunctionSpectrum` | Second spectrum |
| `max_absolute_delta` | `float` | Maximum per-harmonic amplitude difference |
| `terms` | `tuple[IntensitySpectrumComparisonTerm, ...]` | Per-harmonic delta terms |

`IntensitySpectrumComparisonTerm`: `harmonic`, `left_amplitude`, `right_amplitude`, `amplitude_delta`.

```python
trace_cmp = compare_trace_series(series_a, series_b)
# HarmogramTraceSeriesComparison
```

`HarmogramTraceSeriesComparison`: `left`, `right`, `max_absolute_delta`, `samples` (each: `sample_index`, `sample_time`, `left_strength`, `right_strength`, `delta`).

---

### Policy Objects

#### `HarmogramPolicy` — master policy

| Field | Type | Default | Description |
|---|---|---|---|
| `point_set_policy` | `PointSetHarmonicVectorPolicy` | default | Normalization and domain for point sets |
| `parts_policy` | `ZeroAriesPartsPolicy` | default | Zero-Aries parts construction |
| `intensity_policy` | `HarmogramIntensityPolicy` | default | Intensity function shape |
| `sampling_policy` | `HarmogramSamplingPolicy` | default | Trace sampling |
| `output_mode` | `HarmogramOutputMode` | `MULTI_HARMONIC_FAMILY` | Single vs multi-harmonic output |
| `chart_domain` | `HarmogramChartDomain` | `DYNAMIC_SKY_ONLY_TRACE` | What the trace represents |
| `trace_family` | `HarmogramTraceFamily` | `DYNAMIC_ZERO_ARIES_PARTS` | Parts construction family |

`chart_domain` and `trace_family` must be consistent (enforced by `__post_init__`).

#### `HarmogramIntensityPolicy` — intensity function shape

| Field | Type | Default | Description |
|---|---|---|---|
| `family` | `HarmogramIntensityFamily` | `COSINE_BELL_HARMONIC_ASPECTS` | Aspect weighting shape |
| `include_conjunction` | `bool` | `True` | Whether to include H-fold conjunctions |
| `orb_mode` | `HarmogramOrbMode` | `COSINE_BELL` | Orb weighting function (must match family) |
| `orb_scaling_mode` | `HarmogramOrbScalingMode` | `EQUATED_TO_HARMONIC_ONE` | How orb scales with harmonic |
| `symmetry_mode` | `HarmogramSymmetryMode` | `STAR_SYMMETRIC` | Star-symmetric or conjunction-excluded |
| `normalization_mode` | `IntensityNormalizationMode` | `PEAK_ONE` | Spectrum normalization |
| `harmonic_domain` | `HarmonicDomain` | H1–H12 | Harmonics evaluated |
| `orb_width_deg` | `float` | 24.0 | Orb width at H=1 (°) |
| `gaussian_width_parameter_mode` | `GaussianWidthParameterMode` | `FWHM` | Gaussian width interpretation |
| `gaussian_width_deg` | `float \| None` | `None` | Gaussian width (required for Gaussian family) |
| `sample_count` | `int` | 4096 | Quadrature sample count (≥ 256) |

`HarmogramIntensityFamily` values: `COSINE_BELL_HARMONIC_ASPECTS  TOP_HAT_HARMONIC_ASPECTS  TRIANGULAR_HARMONIC_ASPECTS  GAUSSIAN_HARMONIC_ASPECTS`

`HarmogramOrbMode` must match the family: `COSINE_BELL  TOP_HAT  TRIANGULAR  GAUSSIAN`

`HarmogramSymmetryMode` values: `STAR_SYMMETRIC` (includes conjunction)  `CONJUNCTION_EXCLUDED`

#### `PointSetHarmonicVectorPolicy`

| Field | Type | Default | Description |
|---|---|---|---|
| `normalization_mode` | `HarmonicVectorNormalizationMode` | `MEAN_RESULTANT` | `RAW_SUM` or `MEAN_RESULTANT` |
| `harmonic_domain` | `HarmonicDomain` | H1–H12 | Harmonics computed |

#### `ZeroAriesPartsPolicy`

| Field | Type | Default | Description |
|---|---|---|---|
| `pair_construction_mode` | `ZeroAriesPairConstructionMode` | `ORDERED` | `ORDERED` (A→B ≠ B→A) or `UNORDERED` |
| `self_pair_mode` | `SelfPairMode` | `INCLUDE` | Whether to include self-pairs (A→A = 0°) |

---

### `HarmogramChartDomain` and `HarmogramTraceFamily` constraints

| `chart_domain` | Compatible `trace_family` |
|---|---|
| `DYNAMIC_SKY_ONLY_TRACE` | `DYNAMIC_ZERO_ARIES_PARTS` |
| `TRANSIT_TO_NATAL_TRACE` | `TRANSIT_TO_NATAL_ZERO_ARIES_PARTS` |
| `DIRECTED_OR_PROGRESSED_TRACE` | `DIRECTED_TO_NATAL_ZERO_ARIES_PARTS` or `PROGRESSED_TO_NATAL_ZERO_ARIES_PARTS` |

---

### Example: natal chart H4 spectral analysis

```python
from moira.harmograms import (
    parts_from_zero_aries, zero_aries_parts_harmonic_vector,
    intensity_function_spectrum, project_harmogram_strength,
    dominant_harmonic_contributors,
    HarmonicDomain, HarmogramIntensityPolicy, PointSetHarmonicVectorPolicy,
)
from moira.facade import Moira
from datetime import datetime, timezone

m = Moira()
chart = m.chart(datetime(1988, 4, 4, 14, 30, tzinfo=timezone.utc))
lons = chart.longitudes(include_nodes=False)  # dict[str, float]

domain = HarmonicDomain(harmonic_start=1, harmonic_stop=16)

# Build Zero-Aries parts from the natal chart
parts = parts_from_zero_aries(lons)

# Harmonic vector for H4
vec_policy = PointSetHarmonicVectorPolicy(harmonic_domain=domain)
hvec = zero_aries_parts_harmonic_vector(parts, 4, policy=vec_policy)
print(f"H4 amplitude: {hvec.get_component(4).amplitude:.4f}")

# Intensity spectrum at H4
int_policy = HarmogramIntensityPolicy(harmonic_domain=domain, orb_width_deg=18.0)
spectrum = intensity_function_spectrum(lons, 4, policy=int_policy)

# Project — which harmonics contribute most?
proj = project_harmogram_strength(hvec, spectrum)
print(f"Total strength: {proj.total_strength:.4f}")

dominant = dominant_harmonic_contributors(proj, top_n=4)
for term in dominant:
    print(f"  H{term.harmonic}: {term.signed_contribution:+.4f}")
```

---

## 17. Constellation Oracle

```python
# Import directly from the sub-module for the constellation you need:
from moira.constellations.stars_orion import (
    RIGEL, BETELGEUSE, BELLATRIX, ALNILAM, ALNITAK, MINTAKA, SAIPH,
    stars_in_orion, orion_star_at,
    rigel_at, betelgeuse_at, bellatrix_at,  # etc.
)
```

The Constellation Oracle groups the fixed-star catalog by IAU constellation. Each of the 48 sub-modules provides:

- **Named string constants** for each catalogued star (e.g. `RIGEL = "Rigel"`)
- **A constellation-scoped dispatcher** (`orion_star_at(name, jd_tt)`) that validates names against the constellation and calls `moira.stars.star_at`
- **Per-star convenience functions** (`rigel_at(jd_tt)`, `betelgeuse_at(jd_tt)`)
- **List helpers** (`stars_in_orion()`, `available_in_orion()`)

No symbols are re-exported from `moira.constellations.__init__`; always import from the specific sub-module.

### Module naming convention

Sub-modules follow the pattern `moira.constellations.stars_<constellation>`, where `<constellation>` is the IAU abbreviation in lowercase:

```
stars_andromeda    stars_aquarius    stars_aquila      stars_aries
stars_bootes       stars_cancer      stars_canis_major stars_canis_minor
stars_capricorn    stars_carina      stars_cassiopeia  stars_centaurus
stars_corvus       stars_crater      stars_crux        stars_cygnus
stars_draco        stars_gemini      stars_hercules    stars_hydra
stars_leo          stars_libra       stars_lyra        stars_ophiuchus
stars_orion        stars_pegasus     stars_perseus     stars_pisces
stars_sagittarius  stars_scorpius    stars_taurus      stars_ursa_major
stars_ursa_minor   stars_virgo       ... (48 total)
```

### Per-module interface pattern

Every constellation module exposes the same interface pattern:

```python
from moira.constellations.stars_scorpius import (
    ANTARES, SHAULA, LESATH, DSCHUBBA, GRAFFIAS,
    # ... other star name constants

    stars_in_scorpius,       # list[str] — all catalogued star names
    available_in_scorpius,   # list[str] — names resolvable right now
    scorpius_star_at,        # (name, jd_tt) → FixedStar

    antares_at,              # (jd_tt) → FixedStar
    shaula_at,
    # ... one function per catalogued star
)
```

### Usage

```python
from moira.facade import jd_from_datetime
from moira.constellations.stars_taurus import (
    ALDEBARAN, ALCYONE, PLEIADES_CLUSTER,
    taurus_star_at, aldebaran_at, alcyone_at,
    stars_in_taurus,
)
from datetime import datetime, timezone

jd = jd_from_datetime(datetime(2026, 4, 7, tzinfo=timezone.utc))

# By name via dispatcher:
ald = taurus_star_at(ALDEBARAN, jd)
print(f"Aldebaran: {ald.longitude:.4f}°  mag {ald.magnitude}")

# Via convenience function:
alc = alcyone_at(jd)

# List all Taurus stars:
print(stars_in_taurus())
```

All position computation delegates to `moira.stars.star_at` — the constellation oracle adds no positional logic of its own.

---

## 18. Calendar & Time

```python
from moira.facade import (
    jd_from_datetime, datetime_from_jd, julian_day, calendar_from_jd,
    calendar_datetime_from_jd, format_jd_utc, safe_datetime_from_jd,
    greenwich_mean_sidereal_time, local_sidereal_time, delta_t,
    CalendarDateTime,
)
```

| Function | Signature | Description |
|---|---|---|
| `jd_from_datetime` | `(dt: datetime) → float` | datetime → JD UT; naïve treated as UTC |
| `datetime_from_jd` | `(jd: float) → datetime` | JD UT → UTC datetime |
| `julian_day` | `(year, month, day, hour=0.0) → float` | Calendar date → JD |
| `calendar_from_jd` | `(jd: float) → CalendarDateTime` | JD → BCE-safe calendar breakdown |
| `calendar_datetime_from_jd` | `(jd: float) → CalendarDateTime` | Alias for `calendar_from_jd` |
| `format_jd_utc` | `(jd: float) → str` | Human-readable UTC string |
| `safe_datetime_from_jd` | `(jd: float) → datetime \| None` | Returns None for out-of-range JDs |
| `greenwich_mean_sidereal_time` | `(jd_ut: float) → float` | GMST in degrees |
| `local_sidereal_time` | `(jd_ut, longitude, dpsi=None, obliq=None) → float` | LAST in degrees |
| `delta_t` | `(year: float) → float` | ΔT in seconds for a decimal year |

### `CalendarDateTime` fields

| Field | Type | Description |
|---|---|---|
| `year` | `int` | Proleptic Gregorian year (negative for BCE) |
| `month` | `int` | Month (1–12) |
| `day` | `int` | Day (1–31) |
| `hour` | `float` | Decimal UT hour |
| `is_bce` | `bool` | True when year < 1 (BCE convention) |

```python
from moira.facade import jd_from_datetime, calendar_from_jd
import datetime

jd = jd_from_datetime(datetime.datetime(1988, 4, 4, 14, 30,
                                        tzinfo=datetime.timezone.utc))
print(jd)           # 2447255.104166...

cal = calendar_from_jd(jd)
print(cal.year, cal.month, cal.day, cal.hour)

# For BCE dates (negative year numbers):
jd_cleopatra = 1705426.0   # approx 69 BCE
cal2 = calendar_from_jd(jd_cleopatra)
print(cal2.is_bce, cal2.year)   # True, -68 (astronomical year numbering)
```

### Obliquity & nutation

```python
from moira.facade import mean_obliquity, true_obliquity, nutation

# All take jd_tt (Terrestrial Time)
from moira.facade import jd_from_datetime
from moira.julian import ut_to_tt
jd_ut = jd_from_datetime(dt)
jd_tt = ut_to_tt(jd_ut)

obl_mean = mean_obliquity(jd_tt)         # degrees
obl_true = true_obliquity(jd_tt)         # degrees (mean + nutation correction)
dpsi, deps = nutation(jd_tt)             # nutation in longitude and obliquity (arcsec)
```

### Ayanamsa

```python
from moira.facade import ayanamsa, tropical_to_sidereal, sidereal_to_tropical, list_ayanamsa_systems, Ayanamsa

offset       = ayanamsa(jd_ut, Ayanamsa.LAHIRI)                       # degrees to subtract
sidereal_lon = tropical_to_sidereal(tropical_lon, jd_ut, Ayanamsa.LAHIRI)
tropical_lon = sidereal_to_tropical(sidereal_lon, jd_ut, Ayanamsa.LAHIRI)
all_systems  = list_ayanamsa_systems()                                 # list of all Ayanamsa.* constants
```

---

## 19. Policy Objects

Every computational pillar that has configurable behavior exposes a frozen
dataclass policy. Policies use sensible defaults and can be constructed with
keyword arguments for the parameters you want to override.

### Pattern

```python
# Using the default:
result = some_function(inputs)

# Customizing:
from moira.facade import AspectPolicy
policy = AspectPolicy(include_minor=False)
result = some_function(inputs, policy=policy)
```

### Pillar policies reference

| Policy class | Module | Key parameters |
|---|---|---|
| `AspectPolicy` | aspects | `orb_table`, `min_tier`, `include_minor`, `motion_threshold` |
| `HousePolicy` | houses | `polar_fallback`, `unknown_system` |
| `DignityComputationPolicy` | dignities | `doctrine`, `mercury_sect_model`, `solar_condition`, `accidental_dignity` |
| `LotsComputationPolicy` | lots | `reversal_kind`, `derived_reference`, `external_reference` |
| `ProgressionComputationPolicy` | progressions | `time_key`, `direction`, `house_frame` |
| `TransitComputationPolicy` | transits | `search`, `return_search`, `syzygy_search` |
| `TransitSearchPolicy` | transits | `step_days`, `max_iterations`, `exact_threshold` |
| `SynastryComputationPolicy` | synastry | `aspect_policy`, `overlay_policy`, `composite_policy`, `davison_policy` |
| `PatternComputationPolicy` | patterns | `selection`, `stellium`, `orb_factor` |
| `TimelordComputationPolicy` | timelords | `firdaria_year_policy`, `zr_year_policy` |
| `VimshottariComputationPolicy` | dasha | `year_policy`, `ayanamsa_policy` |
| `FixedStarComputationPolicy` | fixed_stars | `lookup_policy`, `heliacal_search_policy` |
| `VarStarPolicy` | variable_stars | `eclipse_threshold` |
| `UnifiedStarComputationPolicy` | stars | `merge_policy` |
| `SothicComputationPolicy` | sothic | `calendar_policy`, `heliacal_policy`, `epoch_policy` |

### Doctrine constants

```python
from moira.facade import CANONICAL_ASPECTS, DEFAULT_POLICY, ASPECT_TIERS
from moira.facade import FIRDARIA_DIURNAL, FIRDARIA_NOCTURNAL, FIRDARIA_NOCTURNAL_BONATTI
from moira.facade import CHALDEAN_ORDER, MINOR_YEARS
from moira.facade import VIMSHOTTARI_YEARS, VIMSHOTTARI_SEQUENCE, VIMSHOTTARI_TOTAL
from moira.facade import VIMSHOTTARI_YEAR_BASIS, VIMSHOTTARI_LEVEL_NAMES
from moira.facade import EGYPTIAN_MONTHS, EGYPTIAN_SEASONS, EPAGOMENAL_BIRTHS
from moira.facade import HISTORICAL_SOTHIC_EPOCHS
from moira.facade import CIRCLE_TYPES, DEFAULT_PARAN_POLICY
from moira.facade import HARMONIC_PRESETS, MANSIONS
```

---

## Appendix A — Stability Tiers

| Tier | Meaning | Examples |
|---|---|---|
| **Frozen** | Signature and semantics will not change without a major version bump | `Moira`, `Chart`, `Body`, `HouseSystem`, `AspectData`, `HouseCusps`, all `__all__` members |
| **Provisional** | None currently designated | — |

---

## Appendix B — Kernel & Reader

```python
from moira.spk_reader import get_reader, set_kernel_path, SpkReader

# Set path globally (persists for the process lifetime):
set_kernel_path("/data/de441.bsp")

# Get the shared singleton reader:
reader = get_reader()

# Or construct a private reader:
reader = get_reader("/data/de441.bsp")
```

The `reader` argument accepted by most low-level functions defaults to the
global singleton if `None`. Pass an explicit reader only when you need
isolation from the global state (e.g., in tests or multi-tenant contexts).

---

## Appendix C — Coverage & Accuracy

| Property | Value |
|---|---|
| Ephemeris | JPL DE441 |
| Date coverage | 13 200 BC → 17 191 AD |
| Coordinate frame | Geocentric ecliptic, tropical (J2000.0 mean equinox) |
| Sidereal option | Any ayanamsa via `ayanamsa()` / `tropical_to_sidereal()` |
| ΔT model | Hybrid IERS/Morrison-Stephenson/extrapolation |
| Nutation | IAU 2000A (1365 terms) |
| Obliquity | Laskar 1986 / IAU 2006 combined |
| Topocentric Moon | Parallax-corrected RA/Dec and altitude |
| Fixed stars | Sovereign registry (`star_registry.csv` + JSON sidecars) |
| Variable stars | 20-star classical catalog with period/epoch/magnitude data |


