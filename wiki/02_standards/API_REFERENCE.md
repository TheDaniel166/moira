# Moira API Reference

**Version:** 0.1.0
**Coverage:** 13 200 BC → 17 191 AD (JPL DE441)
**Import surface:** `import moira` — all stable symbols are re-exported from the top-level package.

---

## Table of Contents

1. [Quick Start](#1-quick-start)
2. [Core Types](#2-core-types)
3. [Moira Facade](#3-moira-facade)
4. [Ephemeris & Positions](#4-ephemeris--positions)
5. [Chart Structure](#5-chart-structure)
6. [Classical Techniques](#6-classical-techniques)
7. [Timing Techniques](#7-timing-techniques)
8. [Relational Techniques](#8-relational-techniques)
9. [Geography](#9-geography)
10. [Fixed Stars](#10-fixed-stars)
11. [Eclipses & Phenomena](#11-eclipses--phenomena)
12. [Calendar & Time](#12-calendar--time)
13. [Policy Objects](#13-policy-objects)

---

## Conventions

- Sections labeled `fields` are intended to be exhaustive for the documented vessel unless explicitly marked otherwise.
- Rows or examples that use `...` are abbreviated for width only; they are shorthand, not alternate signatures.
- When a section says `summary`, that label is intentional and means the section is highlighting the most important fields rather than restating every implementation detail inline.

---

## 1. Quick Start

### Installation & Kernel

Moira requires the JPL DE441 binary kernel (`de441.bsp`). Place it in a known
directory and supply the path once at construction. The package does not read a
`MOIRA_KERNEL_PATH` environment variable.

Small optional kernels for `centaurs.bsp` and `minor_bodies.bsp` are bundled
with the package. Large kernels such as `de441.bsp` still need to be provided
locally.

```python
from moira import Moira
from datetime import datetime, timezone

m = Moira()                       # looks for de441.bsp in default location
# or
m = Moira(kernel_path="/data/de441.bsp")
```

### First chart

```python
from moira import Moira, Body, HouseSystem
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
from moira import jd_from_datetime
from datetime import datetime, timezone

natal_sun = chart.planets["Sun"].longitude          # e.g. 14.7°
jd_start  = jd_from_datetime(datetime(2024, 1, 1, tzinfo=timezone.utc))
jd_end    = jd_from_datetime(datetime(2025, 1, 1, tzinfo=timezone.utc))

for event in m.transits(Body.JUPITER, natal_sun, jd_start, jd_end):
    print(event.jd_ut, event.relation.relation_kind)
```

---

## 2. Core Types

### `Body` — celestial body constants

```python
from moira import Body

Body.SUN       Body.MOON      Body.MERCURY   Body.VENUS
Body.MARS      Body.JUPITER   Body.SATURN    Body.URANUS
Body.NEPTUNE   Body.PLUTO

Body.TRUE_NODE   Body.MEAN_NODE   Body.LILITH

Body.EARTH       # for heliocentric computations
```

### `HouseSystem` — house system constants

```python
from moira import HouseSystem

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
from moira import Ayanamsa

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
from moira import AspectDefinition, ASPECT_TIERS

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

## 3. Moira Facade

`Moira(kernel_path=None)` is the primary entry point. All methods convert
`datetime` inputs to JD internally. Naïve datetimes are treated as UTC.

### Construction

```python
m = Moira()
m = Moira(kernel_path="/path/to/de441.bsp")
```

Raises `FileNotFoundError` if the kernel is not found.

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
| `midpoints(chart, orb=1.5)` | `list[Midpoint]` | All planetary midpoints |
| `midpoints_to_point(chart, longitude, orb=1.5)` | `list[Midpoint]` | Midpoints falling at a given longitude |
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
| `lunar_mansions(chart)` | `dict[str, MansionPosition]` | Arabic lunar mansion placement for chart bodies |
| `parans(natal_dt, latitude, longitude, bodies=None, orb_minutes=4.0)` | `list[Paran]` | Paran crossings for the chart date and location |

### Alternative frames & specialty coordinates

| Method | Returns | Description |
|---|---|---|
| `planetary_nodes(dt)` | `dict[str, OrbitalNode]` | Heliocentric orbital nodes and apsides for the planets |
| `galactic_chart(chart, bodies=None)` | `list[GalacticPosition]` | Galactic longitude/latitude for chart bodies |
| `galactic_angles(chart)` | `dict[str, tuple[float, float]]` | Ecliptic long/lat of major galactic reference points |
| `uranian(dt)` | `dict[str, UranianPosition]` | Positions of the eight Uranian/Hamburg School bodies |

### Phenomena & occultations

| Method | Returns | Description |
|---|---|---|
| `phenomena(body, jd_start, jd_end)` | `list[PhenomenonEvent]` | Greatest elongations, perihelion, and aphelion events in a range |
| `moon_phases(jd_start, jd_end)` | `list[PhenomenonEvent]` | All eight standard Moon phases in a date range |
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

## 4. Ephemeris & Positions

### Planetary positions — low-level functions

```python
from moira import planet_at, all_planets_at, sky_position_at
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

### Heliocentric positions

```python
from moira import heliocentric_planet_at, all_heliocentric_at, HeliocentricData
```

| Function | Returns | Description |
|---|---|---|
| `heliocentric_planet_at(body, jd_ut, reader=None)` | `HeliocentricData` | Heliocentric ecliptic longitude, latitude, distance |
| `all_heliocentric_at(jd_ut, bodies=None, reader=None)` | `dict[str, HeliocentricData]` | All planets heliocentrically |

### Asteroids

```python
from moira import asteroid_at, all_asteroids_at, list_asteroids
from moira import load_asteroid_kernel   # for non-DE441 bodies
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
from moira import uranian_at, all_uranian_at, list_uranian, UranianBody, UranianPosition
```

| Function | Returns | Description |
|---|---|---|
| `uranian_at(body, jd_ut)` | `UranianPosition` | Single Uranian body position |
| `all_uranian_at(jd_ut)` | `dict[str, UranianPosition]` | All eight Uranian bodies |
| `list_uranian()` | `list[str]` | Uranian body names (Cupido through Poseidon) |

`UranianBody` constants: `CUPIDO  HADES  ZEUS  KRONOS  APOLLON  ADMETOS  VULKANUS  POSEIDON`

### Galactic coordinates

```python
from moira import (
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
from moira import gauquelin_sector, all_gauquelin_sectors, GauquelinPosition
```

| Function | Returns | Description |
|---|---|---|
| `gauquelin_sector(ra_deg, ramc_deg, body="", ecliptic_longitude=None)` | `GauquelinPosition` | Gauquelin sector (1-36) for a single RA/RAMC position |
| `all_gauquelin_sectors(planet_ra_dec, lat, lst)` | `list[GauquelinPosition]` | Gauquelin sectors for a dict of body -> (ra, dec) |

`GauquelinPosition`: `body`, `sector` (1-36), `degree_in_sector`, `zone`, `is_plus_zone`, `ecliptic_longitude`.

### Coordinate utilities

```python
from moira import (
    icrf_to_ecliptic, icrf_to_equatorial, ecliptic_to_equatorial,
    equatorial_to_horizontal, angular_distance, normalize_degrees,
)
```

| Function | Signature | Description |
|---|---|---|
| `ecliptic_to_equatorial` | `(lon, lat, obliquity) -> (ra, dec)` | Ecliptic -> equatorial (degrees) |
| `equatorial_to_horizontal` | `(ha, dec, lat) -> (az, alt)` | Hour angle/Dec -> azimuth/altitude |
| `angular_distance` | `(lon1, lat1, lon2, lat2) -> float` | Great-circle distance (degrees) |
| `normalize_degrees` | `(d) -> float` | Map any angle to [0, 360) |

### Phase & apparent magnitude

```python
from moira import angular_diameter

ang_diam_arcsec = angular_diameter("Moon", jd)

# For full phase metrics use Moira.phase():
result = m.phase("Venus", dt)
# keys: phase_angle, illumination, angular_diameter_arcsec, apparent_magnitude
```

### Twilight

```python
from moira import twilight_times, TwilightTimes

t = twilight_times(jd, latitude=51.5, longitude=-0.1)
# TwilightTimes: civil_dawn, civil_dusk, nautical_dawn, nautical_dusk,
#                astro_dawn, astro_dusk, sunrise, sunset  (all JD UT)
```

---

## 5. Chart Structure

### Houses

```python
from moira import calculate_houses, HouseCusps, HouseSystem
from moira import (
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

**`UnknownSystemPolicy`**: controls behavior when an unrecognized house system is passed — `RAISE` (raises `ValueError`) or `FALLBACK` (silently returns Placidus). Set via `HousePolicy`.

**`PolarFallbackPolicy`**: controls behavior at polar latitudes where certain systems are undefined — `RAISE`, `PLACIDUS`, or `EQUAL`. Set via `HousePolicy`.

### Aspects

```python
from moira import (
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
from moira import (
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
from moira import classify_chart_shape, ChartShape, ChartShapeType

shape = classify_chart_shape(chart.longitudes(include_nodes=False))
# ChartShape(type, description, focal_point)
```

`ChartShapeType` constants: `BUNDLE  BOWL  BUCKET  LOCOMOTIVE  FAN  SEESAW  SPLASH  SPLAY`

### Midpoints

```python
from moira import calculate_midpoints, midpoints_to_point, Midpoint, MidpointsService

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
from moira import calculate_harmonic, HarmonicPosition, HARMONIC_PRESETS, HarmonicsService

h4 = calculate_harmonic(chart.longitudes(include_nodes=False), 4)
# list[HarmonicPosition(body, natal_lon, harmonic_lon)]

# Using the service class:
svc = HarmonicsService(chart.longitudes(include_nodes=False))
h5  = svc.harmonic(5)       # list[HarmonicPosition]
```

`HARMONIC_PRESETS`: dict of named harmonics, e.g. `{"4th": 4, "5th": 5, ...}`.

### Antiscia

```python
from moira import find_antiscia, antiscia_to_point, AntisciaAspect

antiscia = find_antiscia(chart.longitudes(), orb=1.0)
# AntisciaAspect(body1, body2, kind, orb)
# kind: "antiscion" (solstice axis) or "contra-antiscion" (equinox axis)
```

### Void of Course Moon

```python
from moira import (
    void_of_course_window, is_void_of_course,
    next_void_of_course, void_periods_in_range,
    LastAspect, VoidOfCourseWindow,
)

voc = void_of_course_window(jd_ut)
# VoidOfCourseWindow(start_jd, end_jd, last_aspect, ingress_sign)

voc_periods = void_periods_in_range(jd_start, jd_end)
```

---

## 6. Classical Techniques

### Dignities

```python
from moira import (
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
from moira import (
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
from moira import (
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
from moira import nakshatra_of, all_nakshatras_at, NakshatraPosition

pos = nakshatra_of(moon_longitude, jd_ut, ayanamsa_system=Ayanamsa.LAHIRI)
# NakshatraPosition(name, number, pada, lord, remaining_fraction)

all_naks = all_nakshatras_at(chart.longitudes(include_nodes=False), jd_ut)
# dict[str, NakshatraPosition]
```

### Arabic Lunar Mansions (Manazil)

```python
from moira import mansion_of, all_mansions_at, moon_mansion, MansionPosition, MANSIONS

pos = mansion_of(moon_longitude)
# MansionPosition(number, name, start_lon, end_lon, ruling_planet)

moon_man = moon_mansion(moon_longitude)   # same, convenience alias
all_m    = all_mansions_at(chart.longitudes())
```

`MANSIONS`: tuple of 28 `MansionInfo` entries.

### Longevity (Hyleg / Alcocoden)

```python
from moira import find_hyleg, calculate_longevity, HylegResult

hyleg = find_hyleg(chart_lons, cusps, is_day)
# HylegResult(hyleg, alcocoden, projected_years)

result = calculate_longevity(chart_lons, cusps, is_day)
print(result.projected_years)
```

### Gauquelin sectors

See Section 4 (Ephemeris & Positions).

### Planetary Hours

```python
from moira import planetary_hours, PlanetaryHoursDay, PlanetaryHour

day = planetary_hours(jd_ut, latitude, longitude, reader=None)
# PlanetaryHoursDay(date, day_hours: list[PlanetaryHour], night_hours: list[PlanetaryHour])
# PlanetaryHour(ruler, start_jd, end_jd)
```

### Varga (Vedic divisional charts)

```python
from moira import calculate_varga, navamsa, saptamsa, dashamansa, dwadashamsa, trimshamsa

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

## 7. Timing Techniques

### Transits

```python
from moira import (
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
from moira import find_stations, next_station, is_retrograde, retrograde_periods, StationEvent

stations = find_stations(Body.MARS, jd_start, jd_end, reader=reader)
# StationEvent(jd, body, kind)  kind: "retrograde" | "direct"

retro_intervals = retrograde_periods(Body.MERCURY, jd_start, jd_end, reader=reader)
# list[(jd_start, jd_end)]
```

### Progressions & Directions

All progression functions share the signature:
`(jd_natal, target_dt, bodies=None, reader=None) → ProgressedChart`

```python
from moira import (
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
from moira import speculum, find_primary_arcs, SpeculumEntry, PrimaryArc, DIRECT, CONVERSE

spec  = speculum(chart, houses, geo_lat=51.5)
arcs  = find_primary_arcs(chart, houses, geo_lat=51.5, max_arc=90.0, include_converse=True)
# list[PrimaryArc(significator, promissor, arc, direction)]
# arc.years()             → years by key "naibod" (default)
# arc.years("ptolemy")    → years by Ptolemy key
```

### Firdaria (Persian Time Lords)

```python
from moira import (
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
from moira import (
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
from moira import (
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

## 8. Relational Techniques

### Synastry

```python
from moira import (
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
from moira import (
    composite_chart, composite_chart_reference_place,
    CompositeChart,
)

comp = composite_chart(chart_a, chart_b, houses_a, houses_b)
# CompositeChart(planets: dict[str, PlanetData], houses: HouseCusps | None)
```

### Davison Relationship Charts

```python
from moira import (
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

## 9. Geography

### Astro*Carto*Graphy

```python
from moira import acg_lines, acg_from_chart, ACGLine
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
from moira import Moira, Body
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
from moira import local_space_positions, local_space_from_chart, LocalSpacePosition
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
from moira import (
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

## 10. Fixed Stars

### Sovereign fixed-star registry (`star_registry.csv` + JSON sidecars)

```python
from moira import (
    fixed_star_at, all_stars_at, list_stars, find_stars, star_magnitude,
    load_catalog,
    heliacal_rising_event, heliacal_setting_event, heliacal_rising, heliacal_setting,
    star_chart_condition_profile, star_condition_network_profile,
    StarPosition, HeliacalEvent,
    FixedStarLookupPolicy, HeliacalSearchPolicy, FixedStarComputationPolicy,
    StarPositionTruth, StarPositionClassification,
    StarRelation, StarConditionState, StarConditionProfile,
    StarChartConditionProfile, StarConditionNetworkProfile,
)
```

| Function | Returns | Description |
|---|---|---|
| `fixed_star_at(name, jd_tt)` | `StarPosition` | Ecliptic position with proper motion applied |
| `all_stars_at(jd_tt, names=None)` | `dict[str, StarPosition]` | Multiple named stars at one epoch |
| `list_stars()` | `list[str]` | All star names in the classical catalog |
| `find_stars(query)` | `list[str]` | Fuzzy name search |
| `star_magnitude(name)` | `float` | Visual magnitude |
| `load_catalog(path=None)` | — | Reload the fixed star catalog from a file |
| `heliacal_rising(name, jd_ut, latitude, longitude)` | `float \| None` | JD of heliacal rising |
| `heliacal_setting(name, jd_ut, latitude, longitude)` | `float \| None` | JD of heliacal setting |
| `heliacal_rising_event(name, jd_ut, lat, lon)` | `HeliacalEvent` | Heliacal rising with classification |
| `heliacal_setting_event(name, jd_ut, lat, lon)` | `HeliacalEvent` | Heliacal setting with classification |

`StarPosition`: `name`, `nomenclature`, `longitude`, `latitude`, `magnitude`, `computation_truth`, `classification`, `relation`, `condition_profile`.

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

### Unified Star API (merges catalog + Gaia)

```python
from moira import (
    star_at, stars_near, stars_by_magnitude,
    list_named_stars, find_named_stars,
    FixedStar, FixedStarTruth, FixedStarClassification,
    UnifiedStarRelation, UnifiedStarMergePolicy, UnifiedStarComputationPolicy,
)
```

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

### Gaia DR3 catalog

```python
from moira import (
    load_gaia_catalog, catalog_size, gaia_catalog_info,
    gaia_star_at, gaia_stars_near, gaia_stars_by_magnitude,
    GaiaStarPosition, StellarQuality, bp_rp_to_quality,
)
```

| Function | Returns | Description |
|---|---|---|
| `load_gaia_catalog(path)` | — | Load a Gaia DR3 CSV subset into memory |
| `catalog_size()` | `int` | Number of loaded Gaia entries |
| `gaia_catalog_info()` | `dict` | Summary stats of the loaded catalog |
| `gaia_star_at(source_id, jd_tt)` | `GaiaStarPosition` | Single Gaia source by DR3 ID |
| `gaia_stars_near(longitude, orb, jd_tt)` | `list[GaiaStarPosition]` | Gaia sources near a longitude |
| `gaia_stars_by_magnitude(max_mag, jd_tt)` | `list[GaiaStarPosition]` | Gaia sources brighter than max_mag |
| `bp_rp_to_quality(bp_rp)` | `StellarQuality` | Classify stellar type from BP−RP |

`StellarQuality` values: `O  B  A  F  G  K  M  GIANT  SUPERGIANT  UNKNOWN`

### Variable Stars

```python
from moira import (
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
from moira import (
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

## 11. Eclipses & Phenomena

### Solar & Lunar Eclipses

```python
from moira import (
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
from moira import (
    NasaLunarEclipseContacts, NasaLunarEclipseEvent,
    next_nasa_lunar_eclipse, previous_nasa_lunar_eclipse,
    translate_lunar_eclipse_event,
)

event = next_nasa_lunar_eclipse(jd_start, reader=reader)
prev  = previous_nasa_lunar_eclipse(jd_start, reader=reader)
```

### Planetary Phenomena

```python
from moira import (
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
from moira import (
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
from moira import (
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

## 12. Calendar & Time

```python
from moira import (
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
from moira import jd_from_datetime, calendar_from_jd
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
from moira import mean_obliquity, true_obliquity, nutation

# All take jd_tt (Terrestrial Time)
from moira import jd_from_datetime
from moira.julian import ut_to_tt
jd_ut = jd_from_datetime(dt)
jd_tt = ut_to_tt(jd_ut)

obl_mean = mean_obliquity(jd_tt)         # degrees
obl_true = true_obliquity(jd_tt)         # degrees (mean + nutation correction)
dpsi, deps = nutation(jd_tt)             # nutation in longitude and obliquity (arcsec)
```

### Ayanamsa

```python
from moira import ayanamsa, tropical_to_sidereal, sidereal_to_tropical, list_ayanamsa_systems, Ayanamsa

offset       = ayanamsa(jd_ut, Ayanamsa.LAHIRI)                       # degrees to subtract
sidereal_lon = tropical_to_sidereal(tropical_lon, jd_ut, Ayanamsa.LAHIRI)
tropical_lon = sidereal_to_tropical(sidereal_lon, jd_ut, Ayanamsa.LAHIRI)
all_systems  = list_ayanamsa_systems()                                 # list of all Ayanamsa.* constants
```

---

## 13. Policy Objects

Every computational pillar that has configurable behavior exposes a frozen
dataclass policy. Policies use sensible defaults and can be constructed with
keyword arguments for the parameters you want to override.

### Pattern

```python
# Using the default:
result = some_function(inputs)

# Customizing:
from moira import SomethingComputationPolicy
policy = SomethingComputationPolicy(parameter=value)
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
from moira import CANONICAL_ASPECTS, DEFAULT_POLICY, ASPECT_TIERS
from moira import FIRDARIA_DIURNAL, FIRDARIA_NOCTURNAL, FIRDARIA_NOCTURNAL_BONATTI
from moira import CHALDEAN_ORDER, MINOR_YEARS
from moira import VIMSHOTTARI_YEARS, VIMSHOTTARI_SEQUENCE, VIMSHOTTARI_TOTAL
from moira import VIMSHOTTARI_YEAR_BASIS, VIMSHOTTARI_LEVEL_NAMES
from moira import EGYPTIAN_MONTHS, EGYPTIAN_SEASONS, EPAGOMENAL_BIRTHS
from moira import HISTORICAL_SOTHIC_EPOCHS
from moira import CIRCLE_TYPES, DEFAULT_PARAN_POLICY
from moira import HARMONIC_PRESETS, MANSIONS
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

