# Swiss Ephemeris to Moira Mapping

Status: verified draft, first audit pass.

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

- `mapped`: 29
- `partial`: 49
- `stdlib`: 5
- `missing`: 18
- `unsupported`: 3

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
| `sol_eclipse_*`, `lun_eclipse_*` | partial | `EclipseCalculator`, `m.eclipse(...)` | class-based instead of flat API |
| `rise_trans`, `rise_trans_true_hor` | partial | `find_phenomena(...)`, `get_transit(...)`, `twilight_times(...)` | split API, verified |
| `nod_aps_ut` | partial | `all_planetary_nodes(...)`, `m.planetary_nodes(...)` | lunar-node exact mapping still needs audit |
| `pheno_ut` | partial | `m.phenomena(...)`, `moon_phases_in_range(...)` | Swiss-style single-call vessel not audited |
| fixed-star heliacal functions | partial | `fixed_stars.heliacal_rising`, `fixed_stars.heliacal_setting`, `m.heliacal_rising`, `m.heliacal_setting` | star-only verified |
| `azalt`, `azalt_rev`, `cotrans` | mapped | `coordinates.py` transforms | exact per-symbol table still needs final pass |
| `refrac`, `refrac_extended` | missing | not yet verified in current repo surface | draft overclaimed these |
| `degnorm` | mapped | `coordinates.normalize_degrees(...)` | verified |
| `mooncross_ut`, `solcross_ut` | partial | transit/ingress helpers in `moira.transits` | exact Swiss parity needs audit |
| `gauquelin_sector` | mapped | `moira.gauquelin.gauquelin_sector(...)`, `all_gauquelin_sectors(...)`, `m.gauquelin_sectors(...)` | verified |
| `lun_occult_when_glob`, `lun_occult_when_loc` family | partial | `occultations.py`, `m.occultations(...)`, `lunar_star_occultation(...)` | draft incorrectly marked these missing |
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
- exact Moon-node crossing parity
- exact planetary-phenomena parity with Swiss `pheno_ut`
- whether atmospheric refraction helpers are public under the names assumed in the generated draft

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
| `set_delta_t_userdef` | missing | none audited | no verified global/user override surface |

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
| `time_equ` | missing | none audited | draft overclaimed an equivalent |
| `day_of_week` | partial | compute via converted datetime/calendar | no audited direct helper yet |
| `utc_time_zone` | stdlib | Python `datetime`/`zoneinfo` or Qt timezone handling | not a Moira concern |

### Planet and body positions

| Swiss symbol | Status | Current Moira equivalent | Notes |
| --- | --- | --- | --- |
| `calc_ut` | partial | `planet_at(...)`, `m.chart(...)`, `m.sky_position(...)` | split across low-level and facade |
| `calc` | partial | low-level planet pipeline, TT/UT handling internal | exact 1:1 row still needs signature audit |
| `calc_pctr` | missing | none audited | arbitrary-center body API not verified |
| `get_planet_name` | partial | body strings / constants already carry names | no audited exact helper |
| `get_orbital_elements` | missing | none audited | draft overclaimed `moira.orbits` |
| `orbit_max_min_true_distance` | missing | none audited | draft overclaimed `moira.orbits` |

### House systems

| Swiss symbol | Status | Current Moira equivalent | Notes |
| --- | --- | --- | --- |
| `houses` | mapped | `calculate_houses(...)`, `m.houses(...)` | verified |
| `houses_ex` | partial | `calculate_houses(...)` plus sidereal conversion separately | exact extended parity not finalized |
| `houses_ex2` | partial | core houses exist; cusp-speed parity not yet audited | do not claim full parity yet |
| `houses_armc` | missing | not yet audited as present | original draft claim not verified |
| `houses_armc_ex2` | missing | not yet audited as present | original draft claim not verified |
| `house_pos` | missing | not yet audited as present | original draft claim not verified |
| `house_name` | partial | `HOUSE_SYSTEM_NAMES`, `HouseSystem` constants | exact helper differs |

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
| `sol_eclipse_when_glob` | partial | `EclipseCalculator.next_solar_eclipse(...)` | class method, not flat function |
| `sol_eclipse_when_loc` | partial | `EclipseCalculator.solar_local_circumstances(...)` | not identical output shape |
| `sol_eclipse_where` | missing | no audited direct path/where helper | original draft overclaimed |
| `sol_eclipse_how` | partial | `solar_local_circumstances(...)` | closest current local-attribute surface |
| `lun_eclipse_when` | partial | `EclipseCalculator.next_lunar_eclipse(...)` | class method |
| `lun_eclipse_when_loc` | partial | `EclipseCalculator.lunar_local_circumstances(...)` | shape differs |
| `lun_eclipse_how` | partial | `lunar_local_circumstances(...)` / analysis bundle | shape differs |
| `lun_occult_when_glob` | partial | `all_lunar_occultations(...)`, `m.occultations(...)` | present, not Swiss-shaped |
| `lun_occult_when_loc` | partial | occultation search plus observer args in `occultations.py` | exact 1:1 helper not finalized |
| `lun_occult_where` | partial | occultation machinery present | exact path-style API not yet audited |

### Rise, set, transit

| Swiss symbol | Status | Current Moira equivalent | Notes |
| --- | --- | --- | --- |
| `rise_trans` | partial | `find_phenomena(...)`, `get_transit(...)` | split API |
| `rise_trans_true_hor` | partial | altitude parameter in `find_phenomena(...)` logic | no exact wrapper name |

### Nodes and apsides

| Swiss symbol | Status | Current Moira equivalent | Notes |
| --- | --- | --- | --- |
| `nod_aps_ut` | partial | `all_planetary_nodes(...)`, `m.planetary_nodes(...)` | planetary side verified |
| `mooncross_node_ut` | missing | no audited direct helper | original draft overclaimed |

### Planetary phenomena

| Swiss symbol | Status | Current Moira equivalent | Notes |
| --- | --- | --- | --- |
| `pheno_ut` | partial | `m.phenomena(...)` and moon-phase helpers | no audited single Swiss-style vessel |

### Heliacal phenomena

| Swiss symbol | Status | Current Moira equivalent | Notes |
| --- | --- | --- | --- |
| `heliacal_ut` | partial | `fixed_stars.heliacal_rising(...)`, `fixed_stars.heliacal_setting(...)`, facade star heliacal helpers | star-oriented verified |
| `heliacal_pheno_ut` | missing | no audited direct detailed heliacal phenomenon helper | draft overclaimed |
| `vis_limit_mag` | missing | no audited direct visual limiting magnitude helper | draft overclaimed |

### Coordinate transforms and corrections

| Swiss symbol | Status | Current Moira equivalent | Notes |
| --- | --- | --- | --- |
| `azalt` | partial | `equatorial_to_horizontal(...)` | no audited one-call Swiss-style wrapper |
| `azalt_rev` | missing | no audited reverse helper under claimed name | draft overclaimed |
| `cotrans` | mapped | `ecliptic_to_equatorial(...)`, `equatorial_to_ecliptic(...)` | verified |
| `cotrans_sp` | missing | no audited speed-aware public helper | draft overclaimed |
| `refrac` | missing | no audited public refraction helper under claimed name | draft overclaimed |
| `refrac_extended` | missing | no audited public helper under claimed name | draft overclaimed |
| `degnorm` | mapped | `normalize_degrees(...)` | verified |
| `radnorm` | stdlib | Python `math` modulo | no dedicated Moira helper needed |
| `difdeg2n` | partial | simple local math or future utility helper | no audited public helper |
| `deg_midp` | partial | simple local math or future utility helper | no audited public helper |

### Moon and Sun crossings

| Swiss symbol | Status | Current Moira equivalent | Notes |
| --- | --- | --- | --- |
| `mooncross_ut` | partial | transit/ingress search in `moira.transits` | exact target-longitude helper naming differs |
| `solcross_ut` | partial | transit/ingress search in `moira.transits` | exact target-longitude helper naming differs |
| `helio_cross_ut` | missing | no audited heliocentric crossing helper | draft overclaimed |

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
| `ISIS`, `NIBIRU`, `HARRINGTON`, etc. | partial | some named small bodies exist, fictional bodies not audited | generated draft conflated categories |

### High-confidence inclusion backlog

If Swiss parity is the goal, these are the clearest items still needing real
Moira surface rather than just mapping work:

- user-supplied Delta T override surface
- explicit ARMC house helpers if you want direct Swiss-style migration
- direct Moon-node crossing helper
- direct detailed heliacal-phenomena helper
- direct visual limiting magnitude helper
- reverse horizontal transform helper
- public atmospheric refraction helpers
- heliocentric longitude-crossing helper
- local-mean-time utility helpers
- tidal-acceleration override helpers
- library/file introspection helpers

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
