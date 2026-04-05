# Swiss Ephemeris to Moira Mapping

Status: verified draft, first audit pass; Phase 1–4 row corrections applied 2026-04-04.

This document is a corrected first pass over an AI-generated Swiss Ephemeris
translation draft. It is intentionally narrower than the original text.
Only mappings verified against the current repository surface are stated as
facts here.

Use this as:
- a migration guide for the audited subset
- a correction log for the original draft
- a checklist for the remaining unaudited `pyswisseph` surface

Do not treat this file as a complete 420-symbol authoritative map yet.

## Status Legend

For inventory purposes, each Swiss symbol should eventually land in one of
these buckets:

- `mapped` — a clear Moira equivalent exists now
- `partial` — the intent exists, but the shape is split or not strictly 1:1
- `stdlib` — use Python or another non-Moira standard tool instead
- `missing` — no current Moira equivalent
- `unsupported` — intentionally outside Moira's design scope

## Audit Totals For This Pass

For the 104 symbol rows currently inventoried from the generated draft:

- `mapped`: 61
- `partial`: 35
- `stdlib`: 5
- `missing`: 3
- `unsupported`: 4

These totals are for the audited rows in this document, not yet for the full
published `pyswisseph` symbol surface.

## Core Corrections to the Original Draft

The original draft had several structural errors:

- The real constructor is `Moira(kernel_path=...)`, not `Moira(ephe_path=...)`.
- There is no `Moira.planet(...)` facade method in the current repo.
- There is no public `moira.models.Observer` layer in the current repo.
- Rise/set lives in `moira.rise_set`, not `moira.riseset`.
- Ayanamsa constants live in `moira.sidereal.Ayanamsa`, not `moira.constants`.
- Planet result vessels do not expose Swiss-shaped fields like
  `speed_longitude`; `PlanetData` uses `speed`.
- `PlanetData.distance` and `SkyPosition.distance` are stored in kilometers,
  not AU.

## Migration Principle

Swiss Ephemeris is a flag-driven C API with global mutable state. Moira is a
typed Python engine with:

- explicit arguments instead of global setters
- typed result vessels instead of tuples
- facade methods for common workflows
- lower-level engine functions for specialist access

Some migrations are therefore semantic rather than signature-identical.

## Verified Mappings

### 1. Configuration and initialization

Swiss global ephemeris path:

```python
import swisseph as swe
swe.set_ephe_path("/path/to/ephe")
swe.set_jpl_file("de441.eph")
```

Moira constructor or reader setup:

```python
from moira import Moira

m = Moira(kernel_path="/path/to/de441.bsp")
```

There is also a lower-level kernel path hook:

```python
from moira.spk_reader import set_kernel_path

set_kernel_path("/path/to/de441.bsp")
```

Swiss global topo observer:

```python
swe.set_topo(lon, lat, alt)
```

Moira does not keep global observer state. Pass observer coordinates per call:

```python
from moira.planets import sky_position_at

sky = sky_position_at(
    "Moon",
    jd_ut,
    observer_lat=lat,
    observer_lon=lon,
    observer_elev_m=alt,
)
```

There is no `swe.close()` equivalent.

### 2. Time and Julian day

Verified equivalents in `moira.julian`:

| Swiss | Moira |
| --- | --- |
| `swe.julday(...)` | `moira.julian.julian_day(...)` |
| `swe.revjul(...)` | `moira.julian.calendar_from_jd(...)` |
| UTC `datetime -> JD` | `moira.julian.jd_from_datetime(dt)` |
| `swe.deltat(...)` | `moira.julian.delta_t(year_decimal)` |
| `swe.sidtime(...)` | `moira.julian.greenwich_mean_sidereal_time(jd_ut)` |
| apparent sidereal time | `moira.julian.apparent_sidereal_time(...)` |
| local sidereal time | `moira.julian.local_sidereal_time(...)` |

Important difference:

- `delta_t()` currently takes a decimal year, not a JD.
- The original draft's `utc_to_jd()` and `jd_to_utc()` names do not match the
  current public surface I have verified in `moira.julian`.

### 3. Planet and body positions

The audited low-level engine entry points are in `moira.planets`:

```python
from moira.planets import planet_at, sky_position_at, all_planets_at
```

Low-level geocentric ecliptic position:

```python
pos = planet_at("Sun", jd_ut)
pos.longitude
pos.latitude
pos.distance   # kilometers
pos.speed      # degrees/day
```

Topocentric sky position:

```python
sky = sky_position_at(
    "Moon",
    jd_ut,
    observer_lat=lat,
    observer_lon=lon,
    observer_elev_m=alt,
)
sky.right_ascension
sky.declination
sky.azimuth
sky.altitude
sky.distance   # kilometers
```

Facade-level whole-chart workflow:

```python
from moira import Moira

m = Moira(kernel_path="/path/to/de441.bsp")
chart = m.chart(dt, observer_lat=lat, observer_lon=lon, observer_elev_m=alt)
sun = chart.planets["Sun"]
```

Important corrections to the original draft:

- There is no audited `m.planet(...)` facade method.
- The nearest stable facade equivalent is usually `m.chart(...)` or
  `m.sky_position(...)`.
- The low-level equivalent for Swiss `calc_ut()` is `planet_at(...)`.

### 4. Houses

Facade:

```python
from moira import Moira
from moira.constants import HouseSystem

m = Moira()
houses = m.houses(dt, latitude=lat, longitude=lon, system=HouseSystem.PLACIDUS)
```

Low-level:

```python
from moira.houses import calculate_houses

houses = calculate_houses(jd_ut, lat, lon, HouseSystem.PLACIDUS)
```

Verified current fact:

- `calculate_houses(...)` exists.
- The original draft's `houses_from_armc` and `body_house_position` claims are
  not yet audited in this pass and are intentionally omitted here.

### 5. Ayanamsa and sidereal mode

Verified surface is in `moira.sidereal`:

```python
from moira.sidereal import Ayanamsa, ayanamsa

offset = ayanamsa(jd_ut, Ayanamsa.LAHIRI)
```

Important correction:

- `Ayanamsa` does not live in `moira.constants`.
- The original draft's `ayanamsa_value(...)` name does not match the current
  audited function; the verified function is `ayanamsa(...)`.

### 6. Fixed stars

Low-level audited surface:

```python
from moira.fixed_stars import fixed_star_at, list_stars, find_stars, star_magnitude

spica = fixed_star_at("Spica", jd_tt)
mag = star_magnitude("Spica")
```

Facade:

```python
from moira import Moira

m = Moira()
spica = m.fixed_star("Spica", dt)
```

Important correction:

- The fixed-star low-level function expects `jd_tt`, not `jd_ut`.
- The facade accepts a `datetime` and handles conversion.

### 7. Eclipses

The current eclipse engine is class-based, not a flat top-level function set.

Verified surface:

```python
from moira.eclipse import EclipseCalculator

calc = EclipseCalculator()
solar = calc.next_solar_eclipse(jd_start)
lunar = calc.next_lunar_eclipse(jd_start)
```

Facade-level single-moment eclipse evaluation also exists:

```python
from moira import Moira

m = Moira()
data = m.eclipse(dt)
```

Important correction:

- The original draft's top-level imports like `from moira.eclipse import next_solar_eclipse`
  are not verified as current public functions in this repo.
- The audited current shape is `EclipseCalculator.next_solar_eclipse(...)` and
  `EclipseCalculator.next_lunar_eclipse(...)`.

### 8. Rise, set, and transit

Verified surface is in `moira.rise_set`:

```python
from moira.rise_set import find_phenomena, get_transit, twilight_times

events = find_phenomena("Sun", jd_start, lat, lon)
upper = get_transit("Sun", jd_start, lat, lon, upper=True)
lower = get_transit("Sun", jd_start, lat, lon, upper=False)
twilight = twilight_times(jd_day, lat, lon)
```

Important correction:

- The module is `rise_set`, not `riseset`.
- The current API is event-dictionary based, not `next_rise(...)` /
  `next_set(...)` wrappers.

### 9. Nodes and apsides

Verified facade:

```python
from moira import Moira

m = Moira()
nodes = m.planetary_nodes(dt)
```

Verified low-level:

```python
from moira.planetary_nodes import all_planetary_nodes

nodes = all_planetary_nodes(jd_ut)
```

The original draft's exact `lunar_nodes(...)` / `next_moon_node_crossing(...)`
mapping is not yet audited here.

### 10. Planetary phenomena

Verified facade:

```python
from moira import Moira

m = Moira()
events = m.phenomena("Venus", jd_start, jd_end)
phases = m.moon_phases(jd_start, jd_end)
```

Verified low-level:

```python
from moira.phenomena import moon_phases_in_range

phases = moon_phases_in_range(jd_start, jd_end)
```

Important correction:

- The original draft's `planetary_phenomena(...)` function name is not yet
  audited as a current public function in this repo.

## Pending Audit

The following original-draft areas still need explicit symbol-by-symbol review
before they can be treated as authoritative:

- exact Swiss flag-to-keyword mapping table
- body constant mapping table
- house-system code mapping table
- coordinate transform helper mapping
- heliacal mapping
- occultation mapping
- gauquelin mapping details
- asteroid and arbitrary-body migration examples
- "not yet implemented" completeness table

## Inventory Snapshot From This Audit Pass

This is not yet the full 420-symbol matrix, but it is now explicit about what
is already covered versus what still needs inclusion.

| Swiss symbol / family | Current Moira status | Current Moira surface | Notes |
| --- | --- | --- | --- |
| `set_ephe_path`, `set_jpl_file` | mapped | `Moira(kernel_path=...)`, `set_kernel_path(...)` | semantic equivalent |
| `set_topo` | partial | per-call `observer_lat`, `observer_lon`, `observer_elev_m` | no global observer state |
| `close` | unsupported | none | no C-handle lifecycle |
| `julday`, `revjul` | mapped | `julian_day`, `calendar_from_jd` | verified |
| UTC `datetime -> JD` | mapped | `jd_from_datetime` | verified |
| `deltat` | partial | `delta_t(year_decimal)` | same domain, different signature |
| `sidtime` | mapped | `greenwich_mean_sidereal_time` | verified |
| `calc_ut` | partial | `planet_at(...)`, `m.chart(...)`, `m.sky_position(...)` | split across low-level and facade |
| `calc` | partial | low-level TT/UT distinction not fully inventoried yet | needs exact signature audit |
| `houses`, `houses_ex` | mapped | `calculate_houses(...)`, `m.houses(...)` | verified |
| `set_sid_mode`, `get_ayanamsa_ut` | partial | `moira.sidereal.ayanamsa(...)` | per-call doctrine, no global mode |
| `fixstar_ut`, `fixstar_mag` | mapped | `fixed_star_at(...)`, `star_magnitude(...)`, `m.fixed_star(...)` | verified |
| `sol_eclipse_*`, `lun_eclipse_*` | mostly mapped | `EclipseCalculator`, `m.eclipse(...)` | global search, local circumstances, path geometry, analysis bundle all mapped; `sol_eclipse_when_loc` remains partial (location-anchored search not yet independent) |
| `rise_trans`, `rise_trans_true_hor` | mapped | `find_phenomena(...)`, `get_transit(...)` | `find_phenomena` returns Rise/Set/Transit/AntiTransit; `altitude` kwarg and `RiseSetPolicy(horizon_altitude=...)` cover true-horizon; Group G audit 2026-04-04 |
| `nod_aps_ut` | partial | `all_planetary_nodes(...)`, `m.planetary_nodes(...)` | lunar-node exact mapping still needs audit |
| `pheno_ut` | partial | `m.phenomena(...)`, `moon_phases_in_range(...)` | Swiss-style single-call vessel not audited |
| fixed-star heliacal functions | partial | `fixed_stars.heliacal_rising`, `fixed_stars.heliacal_setting`, `m.heliacal_rising`, `m.heliacal_setting` | star-only verified |
| `azalt`, `azalt_rev`, `cotrans` | mapped | `coordinates.py` transforms | exact per-symbol table still needs final pass |
| `refrac`, `refrac_extended` | mapped | `atmospheric_refraction(...)`, `atmospheric_refraction_extended(...)` in `moira.coordinates` | Phase 1 |
| `degnorm` | mapped | `coordinates.normalize_degrees(...)` | verified |
| `mooncross_ut`, `solcross_ut` | partial | transit/ingress helpers in `moira.transits` | exact Swiss parity needs audit |
| `gauquelin_sector` | mapped | `moira.gauquelin.gauquelin_sector(...)`, `all_gauquelin_sectors(...)`, `m.gauquelin_sectors(...)` | verified |
| `lun_occult_when_glob`, `lun_occult_when_loc` family | mapped | `lunar_occultation(target, jd_start, jd_end)`, `lunar_star_occultation(...)`, `lunar_occultation_path_at(...)`, `lunar_star_occultation_path_at(...)` | both accept `observer_lat`/`observer_lon` for local search; `OccultationPathGeometry` for path; IOTA-validated; Group F audit 2026-04-04 |
| station / retrograde search | mapped | `find_stations`, `retrograde_periods`, `m.stations`, `m.retrograde_periods` | verified |
| returns / syzygy / ingresses | mapped | `solar_return`, `lunar_return`, `planet_return`, `prenatal_syzygy`, `find_ingresses`, `next_ingress`, facade methods | verified |
| asteroid body access | mapped | `asteroid_at`, `main_belt_at`, `centaur_at`, `tno_at`, `available_in_kernel` | verified |
| Uranian bodies | mapped | `moira.uranian`, `m.uranian(...)` | draft incorrectly implied missing support |

## True Gap Ledger So Far

These are the items from the generated draft that still look genuinely absent
or not yet verified as present in the current repo.

### Likely genuinely missing

- `set_lapse_rate`
- `lat_to_lmt`
- `lmt_to_lat`
- `get_current_file_data`
- `get_library_path`
- `get_tid_acc`
- `set_tid_acc`

### Still needs exact audit before claiming support

- full Swiss flag table (`FLG_*`)
- full body constant table against current Moira naming
- full ayanamsa constant table against `moira.sidereal.Ayanamsa`
- exact house-system byte-code mapping table
- exact coordinate-transform helper parity
- exact planetary-phenomena parity with Swiss `pheno_ut`

### Draft was wrong to call these missing

- lunar occultations
- star occultation support
- Uranian bodies
- asteroid kernel introspection
- station and retrograde search
- returns and syzygy helpers

## What Still Needs To Be Included In Moira

Based on this pass alone, the honest "needs inclusion" list is much smaller
than the generated draft implied.

High confidence missing utility surface:

- explicit tidal-acceleration override getters/setters if Swiss parity matters
- Swiss-style local-mean-time helper utilities if you want migration parity
- any file-introspection helpers analogous to Swiss library/file-path queries

Everything else above should be treated as "needs exact mapping work" before it
is treated as missing.

## Detailed Inventory: Symbols Named In The Generated Draft

This section is the more literal inventory pass: one row per Swiss symbol
named in the generated draft, with the best current status from this audit.

### Configuration

| Swiss symbol | Status | Current Moira equivalent | Notes |
| --- | --- | --- | --- |
| `set_ephe_path` | mapped | `Moira(kernel_path=...)`, `set_kernel_path(...)` | semantic equivalent |
| `set_jpl_file` | mapped | `Moira(kernel_path=...)`, `set_kernel_path(...)` | kernel path instead of file-name switch |
| `set_topo` | partial | per-call `observer_lat`, `observer_lon`, `observer_elev_m` | no global observer state |
| `close` | unsupported | none | no C-library lifecycle |
| `set_delta_t_userdef` | mapped | `DeltaTPolicy` in `moira.julian` | Phase 1; covers ΔT model and user override |

### Time and Julian day

| Swiss symbol | Status | Current Moira equivalent | Notes |
| --- | --- | --- | --- |
| `julday` | mapped | `moira.julian.julian_day(...)` | verified |
| `revjul` | mapped | `moira.julian.calendar_from_jd(...)` | verified |
| `utc_to_jd` | partial | `jd_from_datetime(...)` | exact helper name from draft not audited |
| `jdet_to_utc` | partial | `datetime_from_jd(...)`, `calendar_datetime_from_jd(...)` | shape differs |
| `jdut1_to_utc` | partial | `datetime_from_jd(...)`, `calendar_datetime_from_jd(...)` | no exact UT1-specific helper audited |
| `deltat` | partial | `delta_t(year_decimal)` | signature differs |
| `deltat_ex` | partial | `delta_t(...)` | no exact flag variant audited |
| `sidtime` | mapped | `greenwich_mean_sidereal_time(...)` | verified |
| `sidtime0` | partial | `apparent_sidereal_time(...)`, `local_sidereal_time(...)` | exact helper parity not finalized |
| `time_equ` | mapped | `equation_of_time(jd_tt)` in `moira.coordinates` | Phase 1 |
| `day_of_week` | partial | compute via converted datetime/calendar | no audited direct helper yet |
| `utc_time_zone` | stdlib | Python `datetime`/`zoneinfo` or Qt timezone handling | not a Moira concern |

### Planet and body positions

| Swiss symbol | Status | Current Moira equivalent | Notes |
| --- | --- | --- | --- |
| `calc_ut` | partial | `planet_at(...)`, `m.chart(...)`, `m.sky_position(...)` | split across low-level and facade |
| `calc` | partial | low-level planet pipeline, TT/UT handling internal | exact 1:1 row still needs signature audit |
| `calc_pctr` | mapped | `planet_relative_to(...)` in `moira.planets` | Phase 2 |
| `get_planet_name` | partial | body strings / constants already carry names | no audited exact helper |
| `get_orbital_elements` | mapped | `orbital_elements_at(body, jd_ut) → KeplerianElements` in `moira.orbits` | Phase 4 |
| `orbit_max_min_true_distance` | mapped | `distance_extremes_at(body, jd_ut) → DistanceExtremes` in `moira.orbits` | Phase 4 |

### House systems

| Swiss symbol | Status | Current Moira equivalent | Notes |
| --- | --- | --- | --- |
| `houses` | mapped | `calculate_houses(...)`, `m.houses(...)` | verified |
| `houses_ex` | mapped | `calculate_houses(jd_ut, lat, lon, system, *, ayanamsa_offset=...)` in `moira.houses` | pass `ayanamsa_offset=ayanamsa(jd_ut, Ayanamsa.LAHIRI)` for sidereal; explicit idiom |
| `houses_ex2` | mapped | `cusp_speeds_at(jd_ut, lat, lon, system) → HouseDynamics` in `moira.houses` | Phase 3; finite-difference cusp speeds, same method Swiss uses internally; idiom differs |
| `houses_armc` | mapped | `houses_from_armc(...)` in `moira.houses` | Phase 2 |
| `houses_armc_ex2` | mapped | `house_dynamics_from_armc(armc, obliquity, lat, system, *, ayanamsa_offset=...)` — `houses_from_armc` now accepts `ayanamsa_offset`; `house_dynamics_from_armc` for speeds | ARMC sidereal + speeds covered by both |
| `house_pos` | mapped | `body_house_position(...)` in `moira.houses` | Phase 2 |
| `house_name` | mapped | `HOUSE_SYSTEM_NAMES[system]` in `moira.constants` | dict lookup; same data, explicit idiom |

### Sidereal and ayanamsa

| Swiss symbol | Status | Current Moira equivalent | Notes |
| --- | --- | --- | --- |
| `set_sid_mode` | partial | per-call `ayanamsa(...)`, sidereal helpers, `Ayanamsa` constants | no global mode |
| `get_ayanamsa_ut` | mapped | `moira.sidereal.ayanamsa(...)` | verified function, different name |
| `get_ayanamsa_ex_ut` | partial | `ayanamsa(...)` | no exact flag variant audited |
| `get_ayanamsa_name` | partial | `Ayanamsa` string constants | no audited exact label helper |

### Fixed stars

| Swiss symbol | Status | Current Moira equivalent | Notes |
| --- | --- | --- | --- |
| `fixstar_ut` | mapped | `fixed_star_at(...)`, `m.fixed_star(...)` | low-level TT, facade datetime |
| `fixstar2_ut` | mapped | `fixed_star_at(...)`, `m.fixed_star(...)` | same current star pipeline |
| `fixstar_mag` | mapped | `star_magnitude(...)` | verified |
| `fixstar2_mag` | mapped | `star_magnitude(...)` | verified |

### Eclipses

| Swiss symbol | Status | Current Moira equivalent | Notes |
| --- | --- | --- | --- |
| `sol_eclipse_when_glob` | mapped | `EclipseCalculator().next_solar_eclipse(jd_start) → EclipseEvent` | global search, no location argument; Group F audit 2026-04-04 |
| `sol_eclipse_when_loc` | partial | `EclipseCalculator().solar_local_circumstances(jd_start, lat, lon) → SolarEclipseLocalCircumstances` | anchors to global maximum event then computes local sky circumstances; does not independently search for next eclipse visible at the observer location |
| `sol_eclipse_where` | mapped | `EclipseCalculator().solar_eclipse_path(jd_start) → SolarEclipsePath` | `central_line_lats/lons`, `umbral_width_km`, `duration_at_max_s`, `max_eclipse_lat/lon`; validated against Swiss `where` fixture; Group F audit 2026-04-04 |
| `sol_eclipse_how` | mapped | `EclipseCalculator().solar_local_circumstances(...)` → `SolarEclipseLocalCircumstances` | `event.data.eclipse_magnitude`, `sun_apparent_radius`, `moon_apparent_radius`, `topocentric_separation_deg`, `topocentric_overlap`; Group F audit 2026-04-04 |
| `lun_eclipse_when` | mapped | `EclipseCalculator().next_lunar_eclipse(jd_start) → EclipseEvent` | global search; Group F audit 2026-04-04 |
| `lun_eclipse_when_loc` | mapped | `EclipseCalculator().lunar_local_circumstances(jd_start, lat, lon) → LunarEclipseLocalCircumstances` | per-contact `LocalContactCircumstances` (jd_ut, azimuth, altitude, visible) for P1/U1/U2/U3/U4/P4/greatest; Group F audit 2026-04-04 |
| `lun_eclipse_how` | mapped | `LunarEclipseLocalCircumstances.analysis → LunarEclipseAnalysis` | `eclipse_magnitude`, `eclipse_type`, `gamma_earth_radii`, shadow radii on `EclipseData`; Group F audit 2026-04-04 |
| `lun_occult_when_glob` | mapped | `lunar_occultation(target, jd_start, jd_end)`, `lunar_star_occultation(...)`, `all_lunar_occultations(...)` | omit `observer_lat`/`observer_lon` for geocentric global search; Group F audit 2026-04-04 |
| `lun_occult_when_loc` | mapped | `lunar_occultation(target, jd_start, jd_end, observer_lat=lat, observer_lon=lon)`, `lunar_star_occultation(..., observer_lat=lat, observer_lon=lon)` | topocentric search when observer coords supplied; Group F audit 2026-04-04 |
| `lun_occult_where` | mapped | `lunar_occultation_path_at(target, jd_mid) → OccultationPathGeometry`, `lunar_star_occultation_path_at(...)` | `central_line_lats/lons`, `path_width_km`, `duration_at_greatest_s`; IOTA-validated; Group F audit 2026-04-04 |

### Rise, set, transit

| Swiss symbol | Status | Current Moira equivalent | Notes |
| --- | --- | --- | --- |
| `rise_trans` | mapped | `find_phenomena(body, jd_start, lat, lon) → dict` | returns `'Rise'`, `'Set'`, `'Transit'`, `'AntiTransit'` keys; covers all Swiss `CALC_RISE`/`CALC_SET`/`CALC_MTRANSIT`/`CALC_ITRANSIT` use cases; Group G audit 2026-04-04 |
| `rise_trans_true_hor` | mapped | `find_phenomena(body, jd_start, lat, lon, altitude=<val>)` or `RiseSetPolicy(horizon_altitude=<val>)` | explicit altitude override drives the bisection threshold; `refraction=False` gives geometric (no-atmosphere) horizon; Group G audit 2026-04-04 |

### Nodes and apsides

| Swiss symbol | Status | Current Moira equivalent | Notes |
| --- | --- | --- | --- |
| `nod_aps_ut` | partial | `all_planetary_nodes(...)`, `m.planetary_nodes(...)` | planetary side verified |
| `mooncross_node_ut` | mapped | `next_moon_node_crossing(...)` in `moira.nodes` | Phase 2 |

### Planetary phenomena

| Swiss symbol | Status | Current Moira equivalent | Notes |
| --- | --- | --- | --- |
| `pheno_ut` | partial | `m.phenomena(...)` and moon-phase helpers | no audited single Swiss-style vessel |

### Heliacal phenomena

| Swiss symbol | Status | Current Moira equivalent | Notes |
| --- | --- | --- | --- |
| `heliacal_ut` | partial | `fixed_stars.heliacal_rising(...)`, `fixed_stars.heliacal_setting(...)`, facade star heliacal helpers | star-oriented verified |
| `heliacal_pheno_ut` | mapped | `visibility_assessment(body, jd_ut, lat, lon, *, policy) -> VisibilityAssessment` in `moira.heliacal` | `VisibilityAssessment.solar_elongation_deg` + altitude + limiting magnitude constitute the phenomena tuple; Phase 5 / V6 |
| `vis_limit_mag` | mapped | `visual_limiting_magnitude(jd_ut, lat, lon, *, policy)` in `moira.heliacal` | Phase 5 / V6; Bortle sky limit + K&S 1991 moonlight penalty |

### Coordinate transforms and corrections

| Swiss symbol | Status | Current Moira equivalent | Notes |
| --- | --- | --- | --- |
| `azalt` | partial | `equatorial_to_horizontal(...)` | no audited one-call Swiss-style wrapper |
| `azalt_rev` | mapped | `horizontal_to_equatorial(...)` in `moira.coordinates` | Phase 1 |
| `cotrans` | mapped | `ecliptic_to_equatorial(...)`, `equatorial_to_ecliptic(...)` | verified |
| `cotrans_sp` | mapped | `cotrans_sp(...)` in `moira.coordinates` | Phase 1 |
| `refrac` | mapped | `atmospheric_refraction(...)` in `moira.coordinates` | Phase 1 |
| `refrac_extended` | mapped | `atmospheric_refraction_extended(...)` in `moira.coordinates` | Phase 1 |
| `degnorm` | mapped | `normalize_degrees(...)` | verified |
| `radnorm` | stdlib | Python `math` modulo | no dedicated Moira helper needed |
| `difdeg2n` | partial | simple local math or future utility helper | no audited public helper |
| `deg_midp` | partial | simple local math or future utility helper | no audited public helper |

### Moon and Sun crossings

| Swiss symbol | Status | Current Moira equivalent | Notes |
| --- | --- | --- | --- |
| `mooncross_ut` | partial | transit/ingress search in `moira.transits` | exact target-longitude helper naming differs |
| `solcross_ut` | partial | transit/ingress search in `moira.transits` | exact target-longitude helper naming differs |
| `helio_cross_ut` | mapped | `next_heliocentric_transit(...)` in `moira.planets` | Phase 2 |

### Gauquelin sectors

| Swiss symbol | Status | Current Moira equivalent | Notes |
| --- | --- | --- | --- |
| `gauquelin_sector` | mapped | `moira.gauquelin.gauquelin_sector(...)`, `all_gauquelin_sectors(...)`, `m.gauquelin_sectors(...)` | verified |

### Utility surface

| Swiss symbol | Status | Current Moira equivalent | Notes |
| --- | --- | --- | --- |
| `split_deg` | stdlib | local arithmetic | no dedicated audited helper |
| `cs2degstr` | stdlib | formatting | no dedicated audited helper |
| `d2l` | stdlib | `int(...)` | no Moira helper needed |
| `csnorm` | unsupported | none | not meaningful for Moira API surface |

### Bodies and catalogs

| Swiss symbol / family | Status | Current Moira equivalent | Notes |
| --- | --- | --- | --- |
| `AST_OFFSET + n` asteroid access | mapped | `asteroid_at(...)`, `main_belt_at(...)`, `centaur_at(...)`, `tno_at(...)` | verified |
| Uranian bodies `CUPIDO`..`POSEIDON` | mapped | `moira.uranian`, `m.uranian(...)` | verified |
| `SE_ISIS` (asteroid 42 Isis) | mapped | `asteroid_at("Isis", jd_ut)` via NAIF ID 2000042 in asteroid catalog | real minor planet with valid SPK entry; Group H audit 2026-04-04 |
| `SE_NIBIRU` | unsupported | none | no accepted scientific ephemeris, no NAIF ID, no SPK kernel; fictional body; `unsupported.doctrine` |
| `SE_HARRINGTON` | unsupported | none | Harrington's never-confirmed Planet X hypothesis; no NAIF ID, no SPK kernel exists; `unsupported.doctrine` |

### High-confidence inclusion backlog

If Swiss parity is the goal, these are the clearest items still needing real
Moira surface rather than just mapping work:

Implemented (Phase 1–4):
- `DeltaTPolicy` closes `set_delta_t_userdef` (Phase 1)
- `horizontal_to_equatorial` closes `azalt_rev` (Phase 1)
- `atmospheric_refraction` / `atmospheric_refraction_extended` close `refrac` / `refrac_extended` (Phase 1)
- `equation_of_time` closes `time_equ` (Phase 1)
- `houses_from_armc` / `body_house_position` close `houses_armc` / `house_pos` (Phase 2)
- `planet_relative_to` closes `calc_pctr` (Phase 2)
- `next_moon_node_crossing` closes `mooncross_node_ut` (Phase 2)
- `next_heliocentric_transit` closes `helio_cross_ut` (Phase 2)
- `orbital_elements_at` / `distance_extremes_at` close `get_orbital_elements` / `orbit_max_min_true_distance` (Phase 4)
- `visual_limiting_magnitude` closes `vis_limit_mag` (Phase 5 / V6)
- `ayanamsa_offset` kwarg on `calculate_houses` and `houses_from_armc` closes `houses_ex` / `houses_armc_ex2` sidereal parity
- `VisibilityAssessment.solar_elongation_deg` closes `heliacal_pheno_ut` (Phase 5 / V6)

Still missing:
- local-mean-time utility helpers (`lat_to_lmt`, `lmt_to_lat`)
- tidal-acceleration override helpers (`get_tid_acc`, `set_tid_acc`)
- library/file introspection helpers (`get_library_path`, `get_current_file_data`)

## Recommended Current Usage

If you are migrating off `pyswisseph` today, prefer this Moira shape:

```python
from moira import Moira
from moira.constants import HouseSystem
from moira.planets import planet_at, sky_position_at
from moira.rise_set import find_phenomena, get_transit
from moira.sidereal import Ayanamsa, ayanamsa

m = Moira(kernel_path="/path/to/de441.bsp")
chart = m.chart(dt, observer_lat=lat, observer_lon=lon)
houses = m.houses(dt, lat, lon, HouseSystem.PLACIDUS)
sun = chart.planets["Sun"]
moon_sky = m.sky_position(dt, "Moon", lat, lon)
events = find_phenomena("Sun", jd_start, lat, lon)
lahiri = ayanamsa(jd_ut, Ayanamsa.LAHIRI)
```

This draft should be extended only by checking each claimed mapping against the
live repo surface first.

