# Migrating from Swiss Ephemeris to Moira

**Verified against:** `moira-astro` 6.4.0<br>
**Last verified:** 2026-08-15<br>
**Audience:** maintainers porting a Python, C/C++, JavaScript, or service-based
application from Swiss Ephemeris to Moira

Moira is not a drop-in reimplementation of the Swiss Ephemeris function and
flag surface. A safe migration translates the *meaning* of each calculation:
time scale, calendar, body identity, center, frame, apparent-place
corrections, observer, house policy, units, and failure behavior.

This guide gives that translation for the common chart-calculation path. It
marks each mapping as one of:

- **direct** — the same application intent has a normal Moira entry point;
- **policy translation** — the intent exists, but must be expressed explicitly;
- **separate product** — Swiss selected the result with a flag, while Moira
  exposes a distinct operation or vessel;
- **no direct equivalent** — do not invent parity in an adapter.

It does **not** claim numerical identity between two engines configured with
different ephemerides, time policies, frames, or reduction models. A shared
astrological *name* is not a promise of a shared *series*. See
[Why a Swiss number is not a Moira number](#why-a-swiss-number-is-not-a-moira-number).
It also
does not replace a legal review. The Swiss Ephemeris 2.10 programmer manual
describes a GPL v2-or-later/Professional dual license, while the `pyswisseph`
binding repository declares AGPL v3. Moira's source is MIT, while external
kernels and catalogs retain their own notices. Confirm the exact components
and versions your application distributes; see [`LICENSE`](../../LICENSE) and
[`PROVENANCE.md`](../../PROVENANCE.md).

## Why a Swiss number is not a Moira number

People will compare Moira to Swiss Ephemeris. That comparison is useful
only when both sides name the **same quantity**. Many Swiss flags and
Moira `Body` constants share an astrological label and **do not** share
an algorithm, an ephemeris, or a definition of “mean.”

Moira does not treat Swiss digits as a target. JPL, IERS, IAU, and
SOFA/ERFA outrank Swiss. When the two engines disagree and the strata
audit does not show Swiss holding the higher authority, the divergence
is **published and kept**. It is not “fixed” by moving Moira toward
Swiss.

Worked example — Black Moon Lilith, the comparison that shows up first:

| Label | Engine | What the number actually is | Typical residual vs the other engine |
| --- | --- | --- | --- |
| Mean Node | Moira `Body.MEAN_NODE` and Swiss `SE_MEAN_NODE` | Same IERS/ELP secular node | ~0.0000° on modern dates |
| Mean Lilith | Moira `Body.LILITH` | IERS 2003 **secular** mean apogee `F + Ω − l + 180°` | — |
| Mean Lilith | Swiss `SE_MEAN_APOG` | ELP **hybrid**: a mean plus selected periodic terms still labelled “mean” | **4–7′**, sign flips with date |
| True Lilith | Moira `Body.TRUE_LILITH` and Swiss `SE_OSCU_APOG` | Osculating DE apogee | ~1′ |

The 4–7′ Mean Lilith gap is therefore **expected**. It is not a frame
bug, not a nutation miss, and not a 6.2.x regression. 5.2.2 upgraded
the Mean Lilith *frame* (true equinox of date). 6.2.2 binds the
*series* to IERS. IERS versus the previous Meeus polynomial is
sub-arcsecond on 1955–2010 dates. Neither step can cancel Swiss’s
periodic terms, because those terms are not in Moira’s mean.

`SE_MEAN_APOG` → `Body.LILITH` is a **policy translation**: same
intent (mean apogee), different object. Adapters that assert
arcsecond or arcminute parity against `swe.MEAN_APOG` are testing
the wrong contract. Interpolated Swiss apogees (`INTP_APOG`,
`INTP_PERG`) have no public Moira equivalent; do not invent one to
close a Swiss table.

## 1. The shortest safe path

For a new Python integration, use the `Moira` facade, pass timezone-aware
datetimes, use semantic constants, and read typed results:

```python
from datetime import datetime, timezone

from moira import Body, HouseSystem, Moira
from moira.houses import HousePolicy

engine = Moira(kernel_path="/opt/moira/kernels/de441.bsp")
moment = datetime(2000, 1, 1, 12, 0, tzinfo=timezone.utc)

chart = engine.chart(
    moment,
    bodies=[Body.SUN, Body.MOON, Body.MERCURY],
    include_nodes=False,
)
houses = engine.houses(
    moment,
    latitude=51.5074,
    longitude=-0.1278,
    system=HouseSystem.PLACIDUS,
    policy=HousePolicy.strict(),
)

sun = chart.planets[Body.SUN]
print(sun.longitude)       # degrees, [0, 360)
print(sun.latitude)        # degrees
print(sun.distance)        # kilometres
print(sun.distance_au)     # astronomical units
print(sun.speed)           # longitude degrees/day
print(sun.retrograde)
print(houses.asc, houses.mc)
```

`Moira()` can be constructed without a kernel, but planetary operations will
then raise `MissingEphemerisKernelError`. Production code should configure the
kernel through `Moira(kernel_path=...)` or `MOIRA_KERNEL_PATH` and treat a
missing kernel as a readiness failure. Moira does not silently fall back to a
weaker ephemeris.

If the application is not written in Python, use the typed REST service in
section 12 rather than building a language-specific compatibility layer over
Python internals.

## 2. Translate a calculation contract, not a call signature

Before changing code, write down the contract currently implied by each Swiss
call:

| Question | Example answer |
|---|---|
| Input clock | aware UTC datetime, or UT1 Julian day |
| Civil calendar | proleptic Gregorian, or historical Julian |
| Ephemeris | named JPL DE-series kernel |
| Body | Sun, true node, Chiron, asteroid identity |
| Center | geocentric, heliocentric, or Solar System barycentric |
| Frame | ecliptic polar of date, equatorial sky, or Cartesian |
| Reduction | apparent, aberration, deflection, nutation |
| Observer | geocenter or explicit longitude/latitude/elevation |
| Units | degrees, kilometres/AU, degrees/day |
| House behavior | strict failure or declared high-latitude fallback |
| Sidereal policy | named ayanamsa, selected per call |
| Error behavior | fail closed; never accept an undeclared fallback |

Do not begin by replacing `swe.calc_ut()` with another function name. Begin by
making this contract explicit in the application. That step exposes hidden
global state and prevents a superficially successful but semantically wrong
port.

## 3. Architectural differences that affect the port

| Swiss-style pattern | Moira pattern |
|---|---|
| Process-global ephemeris path | Kernel supplied to `Moira(...)` or configured before engine construction |
| Process-global topocentric observer | Observer supplied on each applicable call |
| Process-global sidereal mode | Named ayanamsa supplied to a sidereal calculation |
| Integer body identifiers | Canonical body names and `Body` constants |
| Bitwise flags select several products | Explicit keyword policy or a distinct product method |
| Position tuple plus returned flags | Typed result vessel with named fields |
| Optional silent ephemeris fallback | Explicit configured kernel; missing coverage fails visibly |
| House code byte passed through | `HouseSystem` semantic constant plus `HousePolicy` |
| Library close/reset lifecycle | Long-lived facade/service ownership; no application-level `swe.close()` equivalent |

This is deliberate. In concurrent servers, one request must not be able to
change the observer, sidereal mode, Delta-T override, or ephemeris used by
another request.

## 4. A worked Python port

### 4.1 Typical PySwissEph code

```python
import swisseph as swe

swe.set_ephe_path("/opt/sweph/ephe")
jd_ut = swe.julday(2000, 1, 1, 12.0, swe.GREG_CAL)
flags = swe.FLG_SWIEPH | swe.FLG_SPEED

sun_values, returned_flags = swe.calc_ut(jd_ut, swe.SUN, flags)
cusps, angles = swe.houses_ex(jd_ut, 51.5074, -0.1278, b"P", 0)

sun_longitude = sun_values[0]
sun_latitude = sun_values[1]
sun_distance_au = sun_values[2]
sun_speed = sun_values[3]
```

### 4.2 Equivalent application intent in Moira

```python
from datetime import datetime, timezone

from moira import Body, HouseSystem, Moira
from moira.houses import HousePolicy

engine = Moira(kernel_path="/opt/moira/kernels/de441.bsp")
moment = datetime(2000, 1, 1, 12, 0, tzinfo=timezone.utc)

chart = engine.chart(moment, bodies=[Body.SUN], include_nodes=False)
houses = engine.houses(
    moment,
    latitude=51.5074,
    longitude=-0.1278,
    system=HouseSystem.PLACIDUS,
    policy=HousePolicy.strict(),
)

sun = chart.planets[Body.SUN]
sun_longitude = sun.longitude
sun_latitude = sun.latitude
sun_distance_au = sun.distance_au
sun_speed = sun.speed
```

The two snippets express comparable product intent, not guaranteed numerical
identity. The kernel, time conversion, reduction stages, and house behavior
must be aligned before comparing values.

### 4.3 Keep the rest of the application engine-neutral

Do not spread Moira vessels or Swiss tuples through business logic. Introduce
a small application-owned port:

```python
from dataclasses import dataclass
from datetime import datetime
from typing import Protocol


@dataclass(frozen=True)
class AppPosition:
    longitude_deg: float
    latitude_deg: float
    distance_au: float
    longitude_speed_deg_per_day: float


class EphemerisPort(Protocol):
    def position(self, body: str, moment: datetime) -> AppPosition: ...
```

Then implement a Moira adapter that performs unit and identity translation in
one inspectable place:

```python
from datetime import datetime

from moira import Moira


class MoiraEphemerisAdapter:
    def __init__(self, engine: Moira) -> None:
        self._engine = engine

    def position(self, body: str, moment: datetime) -> AppPosition:
        if moment.tzinfo is None or moment.utcoffset() is None:
            raise ValueError("moment must be timezone-aware")

        chart = self._engine.chart(
            moment,
            bodies=[body],
            include_nodes=False,
        )
        value = chart.planets[body]
        return AppPosition(
            longitude_deg=value.longitude,
            latitude_deg=value.latitude,
            distance_au=value.distance_au,
            longitude_speed_deg_per_day=value.speed,
        )
```

This adapter is intentionally small. A universal `swe` compatibility shim
would preserve Swiss's implicit global state and overloaded flags—the very
ambiguities the migration should remove.

It intentionally handles `chart.planets` only. Lunar nodes and Lilith points
live in `chart.nodes` and use different result vessels; give them an explicit
application DTO and adapter path instead of pretending every body is a
`PlanetData` record.

## 5. Time, calendars, and Delta-T

### 5.1 Prefer aware datetimes at the facade

`Moira.chart()`, `Moira.houses()`, `Moira.sky_position()`, and the other
facade workflows accept timezone-aware `datetime` values. They own the
UTC/UT1/TT conversion required by the product.

```python
from datetime import datetime, timezone

moment = datetime(2026, 8, 11, 12, 0, tzinfo=timezone.utc)
```

A naive datetime is not an acceptable substitute. Resolve local civil time,
including its IANA zone and daylight-saving ambiguity, before calling Moira.
That resolution belongs to the application; Python's `zoneinfo` is the normal
tool.

### 5.2 Low-level Julian days mean what their names say

At the low-level planetary surface, `jd_ut` means **UT1**, not an unspecified
"Julian date." `jd_tt` means TT. `jd_from_datetime()` returns the Julian-day
coordinate of an aware UTC civil datetime; it does not relabel UTC as UT1 or
TT.

Use low-level calls only when the application already owns the time-scale
contract:

```python
from moira.julian import DeltaTPolicy
from moira.planets import planet_at
from moira.spk_reader import SpkReader

fixed_clock = DeltaTPolicy(model="fixed", fixed_delta_t=69.0)
with SpkReader("/opt/moira/kernels/de441.bsp") as reader:
    sun = planet_at(
        "Sun",
        jd_ut,
        reader=reader,
        delta_t_policy=fixed_clock,
    )
```

`DeltaTPolicy` replaces a global `set_delta_t_userdef` pattern with immutable,
per-call policy. Admitted models are `hybrid`, `physical`, `nasa_canon`, and
`fixed`. The default hybrid path can use the bundled daily Earth-orientation
record when the epoch is covered. Do not set a fixed Delta-T merely to force
agreement with an old snapshot; use it only when it is part of the declared
calculation contract.

### 5.3 Historical calendar warning

Moira's `julian_day(year, month, day, hour)` and `calendar_from_jd()` use the
**proleptic Gregorian calendar**. Swiss's `swe.julday(..., swe.JUL_CAL)` can
interpret a historical Julian-calendar date. There is no flag-equivalent
calendar switch in the generic Moira helper.

If existing records are tagged as Julian calendar dates, convert them to an
unambiguous instant before entering Moira. Do not feed the same year/month/day
numbers to the proleptic-Gregorian helper and assume they denote the same day.
For BCE or astronomical year zero, use Moira's structured calendar vessels;
Python `datetime` itself cannot represent those years.

## 6. Bodies and catalog identities

Use `Body` constants at application boundaries:

| Swiss identity | Moira identity |
|---|---|
| `SE_SUN` | `Body.SUN` |
| `SE_MOON` | `Body.MOON` |
| `SE_MERCURY` … `SE_PLUTO` | matching `Body` constant |
| `SE_MEAN_NODE` | `Body.MEAN_NODE` |
| `SE_TRUE_NODE` | `Body.TRUE_NODE` |
| `SE_MEAN_APOG` | `Body.LILITH` (intent only — IERS secular mean, not Swiss ELP hybrid; expect 4–7′) |
| `SE_OSCU_APOG` | `Body.TRUE_LILITH` (osculating DE; the close numerical match) |
| `SE_CHIRON` | `Body.CHIRON` (included in the wheel catalog) |

`SE_MEAN_APOG` → `Body.LILITH` is the mean-apogee **intent**, not a
digit-for-digit identity. The 4–7′ residual is the documented series
difference in
[Why a Swiss number is not a Moira number](#why-a-swiss-number-is-not-a-moira-number).
Do not close it in an adapter.

`Body.ALL_PLANETS` is the ten-planet set and excludes Earth and the node
points. `Body.ALL_POINTS` includes the node/Lilith point set. Make the desired
body list explicit rather than assuming the two engines have identical
defaults.

Swiss asteroid arithmetic such as `SE_AST_OFFSET + 1` has no direct Moira
equivalent. Moira uses catalog identities and installed manifest coverage.
Supply a canonical name; when a name exists in both asteroid and comet
catalogs, qualify it as `asteroid:<name>` or `comet:<name>`. Canonical comet
designations such as `1P/Halley` are accepted by the relevant catalog surface.
Missing supplemental data is an operational error, not a reason to substitute
a different body.

## 7. Translating Swiss flags

The table below covers the common `swe_calc*` flags. "Closest" does not mean
bit-for-bit parity; it identifies the Moira product or policy that owns the
intent.

| Swiss flag | Classification | Moira translation |
|---|---|---|
| `SEFLG_JPLEPH` | policy translation | Configure the required JPL `.bsp` kernel; no per-call selector |
| `SEFLG_SWIEPH` | no direct equivalent | Moira does not run the Swiss ephemeris files |
| `SEFLG_MOSEPH` | no direct equivalent | No Moshier fallback; missing kernel coverage fails |
| `SEFLG_SPEED` | direct result field | `PlanetData.speed` is always longitude degrees/day |
| `SEFLG_SPEED3` | no direct equivalent | No three-position finite-difference mode switch |
| `SEFLG_HELCTR` | separate product | `Moira.heliocentric(...)` or the admitted heliocentric frame surface |
| `SEFLG_BARYCTR` | separate product | `Moira.ssb_chart(...)` or low-level `center="barycentric"`; choose the intended vessel explicitly |
| `SEFLG_TRUEPOS` | policy translation | Low-level `apparent=False` is the closest geometric intent |
| `SEFLG_NONUT` | direct policy | Low-level `nutation=False` |
| `SEFLG_NOGDEFL` | direct policy | Low-level `grav_deflection=False` |
| `SEFLG_NOABERR` | direct policy | Low-level `aberration=False` |
| `SEFLG_TOPOCTR` | direct policy | Supply `observer_lat`, `observer_lon`, and `observer_elev_m` per call |
| `SEFLG_SIDEREAL` | separate product | `Moira.sidereal_chart(...)` or explicit sidereal conversion with a named ayanamsa |
| `SEFLG_XYZ` | separate vessel | Low-level `frame="cartesian"`; coordinates are kilometres |
| `SEFLG_EQUATORIAL` | separate product | Use `sky_position()` for topocentric RA/declination, or an explicit Cartesian frame product |
| `SEFLG_RADIANS` | application conversion | Moira angle vessels use degrees; call `math.radians()` at the boundary |
| `SEFLG_J2000` | no one-line facade equivalent | Select a documented frame-specific product; do not relabel of-date coordinates |
| `SEFLG_ICRS` | no one-line facade equivalent | Select an admitted ICRF/J2000 Cartesian product only when that is the required contract |

For partial apparent-place control, use the low-level position function:

```python
from moira.planets import planet_at
from moira.spk_reader import SpkReader

with SpkReader("/opt/moira/kernels/de441.bsp") as reader:
    sun = planet_at(
        "Sun",
        jd_ut,
        reader=reader,
        apparent=True,
        aberration=True,
        grav_deflection=True,
        nutation=True,
        center="geocentric",
        frame="ecliptic",
        observer_lat=None,
        observer_lon=None,
    )
```

Moira's default result is apparent geocentric ecliptic position of date. A
request for Cartesian output returns `CartesianPosition`, not `PlanetData`.
Its `x`, `y`, and `z` values are kilometres and it does not include Swiss-style
velocity components.

## 8. Result fields and units

The most dangerous apparently successful port is a unit mismatch.

| Swiss position tuple | Moira `PlanetData` | Important difference |
|---|---|---|
| `xx[0]` longitude | `.longitude` | degrees |
| `xx[1]` latitude | `.latitude` | degrees |
| `xx[2]` distance | `.distance_au` for AU, `.distance` for km | **`.distance` is kilometres** |
| `xx[3]` longitude speed | `.speed` | degrees/day; always present |
| `xx[4]` latitude speed | no convenience-field equivalent | do not silently fill zero |
| `xx[5]` radial speed | no convenience-field equivalent | do not silently fill zero |

Additional Moira fields include `.retrograde`, `.is_topocentric`, `.sign`,
`.sign_symbol`, and `.sign_degree`. These are named result semantics, not
returned flag bits.

Topocentric `Moira.sky_position()` returns a different vessel:

```python
sky = engine.sky_position(
    moment,
    body=Body.MOON,
    latitude=51.5074,
    longitude=-0.1278,
    elevation_m=35.0,
)

print(sky.right_ascension)  # degrees
print(sky.declination)      # degrees
print(sky.azimuth)          # north=0, east=90
print(sky.altitude)         # degrees
print(sky.distance)         # kilometres
```

Do not use ecliptic longitude where the old application expected right
ascension, or geocentric ecliptic coordinates where it expected an observed
topocentric sky position.

## 9. Houses: translate names, not byte codes

Never pass an existing Swiss house-code literal through to Moira. Use semantic
constants:

```python
from moira import HouseSystem
from moira.houses import HousePolicy

houses = engine.houses(
    moment,
    latitude=64.1466,
    longitude=-21.9426,
    system=HouseSystem.PLACIDUS,
    policy=HousePolicy.strict(),
)
```

Common constants include `PLACIDUS`, `KOCH`, `PORPHYRY`, `REGIOMONTANUS`,
`CAMPANUS`, `ALCABITIUS`, `TOPOCENTRIC`, `VEHLOW`, `WHOLE_SIGN`, `EQUAL`,
`SUNSHINE`, `CARTER`, `EQUAL_MC`, `PULLEN_SD`, and `PULLEN_SR`.

Several literal identifiers are intentionally not Swiss's byte codes. For
example, Moira uses `HouseSystem.SUNSHINE`, not a copied `b"I"`; it uses
semantic constants for Carter, Equal MC, and the Pullen systems as well. The
constant is the compatibility boundary.

During migration, start with `HousePolicy.strict()`. This makes unsupported
polar geometry or an unknown system fail instead of concealing a difference.
If the product intentionally permits fallback, choose that policy explicitly
and persist the result receipts:

- `houses.system` — requested system;
- `houses.effective_system` — system actually used;
- `houses.fallback` — whether fallback occurred;
- `houses.fallback_reason` — why;
- `houses.policy` — governing policy.

Do not compare only cusp arrays while ignoring a change in effective system.

## 10. Sidereal charts and ayanamsa

Do not recreate `swe_set_sid_mode()` as a mutable global. Select a named
ayanamsa for each calculation:

```python
from moira.sidereal import Ayanamsa

sidereal = engine.sidereal_chart(
    moment,
    ayanamsa_system=Ayanamsa.LAHIRI,
    bodies=[Body.SUN, Body.MOON],
)
```

The default facade ayanamsa is Lahiri when none is supplied, but migration
code should name it. If the old application used a custom Swiss sidereal mode,
audit its epoch, offset, precession convention, and whether it expected true
or mean reference behavior. Do not substitute a similarly named preset
without a fixture that proves the intended convention.

## 11. Aspects, events, and searches

### 11.1 Aspects

Swiss position calculation and application-owned aspect detection are often
intermixed in legacy code. Moira makes aspect policy explicit:

```python
from moira.aspects import AspectPolicy

policy = AspectPolicy(
    tier=0,
    include_minor=False,
    orbs={0.0: 8.0, 60.0: 4.0, 90.0: 7.0, 120.0: 7.0, 180.0: 8.0},
    orb_factor=1.0,
    orb_mode="fixed",
)
aspects = engine.aspects(chart, policy=policy)
```

`AspectData` exposes the two bodies, named aspect, exact angle, actual
separation, orb, allowed orb, and applying/stationary truth. Preserve the old
application's orb doctrine in an `AspectPolicy`; do not treat a difference in
aspect lists as an ephemeris-position failure until the policies match.

### 11.2 Rise, set, and meridian events

The event surface is a distinct search product:

```python
from moira.sky.events import RiseSetPolicy, find_phenomena
from moira.spk_reader import SpkReader, use_reader_override

with SpkReader("/opt/moira/kernels/de441.bsp") as reader:
    with use_reader_override(reader):
        events = find_phenomena(
            Body.SUN,
            jd_start,
            lat=51.5074,
            lon=-0.1278,
            policy=RiseSetPolicy(),
        )

rise_jd = events.get("Rise")
set_jd = events.get("Set")
upper_transit_jd = events.get("Transit")
lower_transit_jd = events.get("AntiTransit")
```

An event that does not occur in the search interval is represented by an
absent dictionary key. Do not turn absence into a fabricated timestamp.
Horizon altitude, refraction, pressure, and temperature are calculation
policy; align them before comparing results with `swe_rise_trans*`.
Standalone low-level searches require an explicit active reader context, as
shown above. The REST service establishes that context for each request.

Eclipse, occultation, heliacal, station, retrograde, ingress, return, and
planetary-phenomena families have dedicated products. Use the
[`Python API Reference`](../02_standards/API_REFERENCE.md) and
[`REST API Reference`](REST_API_REFERENCE.md) for those families rather than
guessing a function name from Swiss.

## 12. REST migration for non-Python applications

Install and start the optional service:

```bash
pip install "moira-astro[server]"
uvicorn --factory moira_server:create_app --host 127.0.0.1 --port 8765
```

Set `MOIRA_KERNEL_PATH` in the service environment. Check readiness before
sending work:

```bash
curl --fail http://127.0.0.1:8765/ready
curl --fail http://127.0.0.1:8765/meta/version
curl --fail http://127.0.0.1:8765/meta/kernel
```

`/health` proves that the process responds. `/ready` is the deployment gate;
it returns HTTP 503 when required startup state or the kernel is unavailable.

Request a chart:

```bash
curl --fail-with-body \
  -H "Content-Type: application/json" \
  -d '{
    "dt": "2000-01-01T12:00:00Z",
    "bodies": ["Sun", "Moon", "Mercury"],
    "include_nodes": false,
    "observer_lat": 51.5074,
    "observer_lon": -0.1278,
    "observer_elev_m": 35.0
  }' \
  http://127.0.0.1:8765/v1/chart
```

For one position with explicit correction policy, use
`POST /v1/positions/planet`:

```json
{
  "dt": "2000-01-01T12:00:00Z",
  "body": "Sun",
  "apparent": true,
  "aberration": true,
  "grav_deflection": true,
  "nutation": true
}
```

Use the `/reduction` or `/pipeline` variants when the application needs a
receipt of intermediate reduction state. Do not parse human-readable error
text as an API. Preserve HTTP status, structured validation details, engine
version, and kernel metadata in diagnostics.

## 13. Dual-run verification without false parity

Run both engines behind the application-owned port before switching traffic.
Freeze each fixture's:

1. civil datetime, time zone, resolved UTC instant, and calendar;
2. body identity;
3. center, frame, apparent/geometric policy, and observer;
4. ephemeris/kernel identity and coverage;
5. house system and fallback policy;
6. sidereal/ayanamsa policy, if any;
7. expected units;
8. product-owned tolerance.

For circular angles, compare the shortest separation, not ordinary
subtraction:

```python
def circular_error_deg(left: float, right: float) -> float:
    return abs((left - right + 180.0) % 360.0 - 180.0)
```

An application-level comparison can then state its contract explicitly:

```python
def assert_position_close(
    expected: AppPosition,
    actual: AppPosition,
    *,
    angle_tolerance_deg: float,
    distance_tolerance_au: float,
) -> None:
    assert circular_error_deg(
        expected.longitude_deg,
        actual.longitude_deg,
    ) <= angle_tolerance_deg
    assert abs(expected.latitude_deg - actual.latitude_deg) <= angle_tolerance_deg
    assert abs(expected.distance_au - actual.distance_au) <= distance_tolerance_au
```

Choose tolerances from the consuming product's requirements and declared
numerical evidence. Do not choose them after looking at failures merely to make
the migration green. Swiss can be useful corroborating evidence, but it is not
the sole authority for JPL state vectors, IAU reductions, or product-specific
doctrine. Moira's validation documents name the authority appropriate to each
surface.

Recommended fixture families:

- ordinary modern date;
- leap-second-era boundary;
- pre-1972 date if the product supports it;
- zodiac wrap near 0/360 degrees;
- station/near-zero longitude speed;
- high-latitude observer;
- house geometry near a polar failure boundary;
- topocentric Moon, where parallax is visible;
- every sidereal preset the application actually offers;
- every supplemental body and catalog family the application actually uses;
- first and last admitted kernel-coverage dates.

Compare structured receipts as well as numbers. A numerically close result with
the wrong frame, body, effective house system, or fallback provenance is not a
passing migration.

## 14. Deployment sequence

1. **Inventory** every imported `swisseph` symbol, global setter, flag
   combination, body constant, and tuple index.
2. **Name the contract** for each call using section 2.
3. **Add an application port** and preserve current behavior behind a Swiss
   adapter.
4. **Implement the Moira adapter** with explicit units and policies.
5. **Dual-run offline** on immutable fixtures.
6. **Dual-run in shadow mode** if production data handling permits it; do not
   let the shadow result affect users.
7. **Gate deployment on `/ready`**, version, and kernel metadata.
8. **Canary** a bounded cohort and monitor errors by calculation family.
9. **Switch reads**, retaining rapid rollback to the old adapter.
10. **Remove Swiss global state and dependency** only after the accepted
    observation window.

Do not load or reconfigure the kernel per request. Construct long-lived engine
or service instances at startup. Do not mutate calculation policy while
requests are in flight.

## 15. Common migration failures

| Symptom | Likely cause | Repair |
|---|---|---|
| Distance is off by about 149.6 million | Moira kilometres compared with Swiss AU | use `.distance_au` or convert explicitly |
| Longitude differs slightly everywhere | different kernel or apparent-place policy | compare kernel metadata and correction flags |
| Moon differs much more than planets | observer or time-scale mismatch | align topocentric coordinates/elevation and UTC/UT1/TT |
| Sidereal values differ by a near-constant offset | ayanamsa mismatch | name and fixture the exact ayanamsa |
| Houses differ only at high latitude | hidden Swiss fallback or different polar policy | start with `HousePolicy.strict()`; inspect effective-system receipt |
| Historical date is many days off | Julian vs proleptic Gregorian input | convert the civil calendar before Moira |
| Body lookup returns missing/ambiguous | supplemental data absent or catalog name collision | install admitted data; use canonical/qualified identity |
| Server is alive but calculations fail | `/health` checked instead of `/ready`, or kernel missing | gate on `/ready` and `/meta/kernel` |
| Aspect lists differ while positions match | orb/tier/applying policy mismatch | encode the old doctrine in `AspectPolicy` |
| Adapter fills unavailable speed fields with zero | Swiss tuple shape was copied blindly | make unsupported fields optional or remove them |
| A flag combination has no clear mapping | it selected several semantic products at once | split the operation; do not invent a universal shim |

## 16. Migration checklist

### Inputs

- [ ] Every datetime is timezone-aware.
- [ ] Historical calendar convention is recorded and converted deliberately.
- [ ] UT1, UTC, and TT are not treated as synonyms.
- [ ] Longitude sign convention is confirmed (east positive in Moira APIs).
- [ ] Elevation units are metres.
- [ ] Body identities are semantic names, not inherited integer offsets.

### Calculation policy

- [ ] Kernel path and coverage are explicit.
- [ ] Apparent/geometric, aberration, deflection, and nutation choices are explicit.
- [ ] Center and coordinate frame are explicit.
- [ ] Observer state is per request, not global.
- [ ] Ayanamsa is named per sidereal calculation.
- [ ] House system uses `HouseSystem`; polar behavior uses `HousePolicy`.
- [ ] Aspect orbs and tiers use `AspectPolicy`.
- [ ] Delta-T override, if any, uses immutable `DeltaTPolicy` and is justified.

### Outputs

- [ ] Kilometres and AU are not conflated.
- [ ] Degrees and radians are not conflated.
- [ ] Missing latitude/radial speed is not represented as zero.
- [ ] Geocentric ecliptic and topocentric sky vessels are not interchanged.
- [ ] Requested and effective house systems are both retained.
- [ ] Version, kernel identity, and relevant policy receipts are logged.

### Verification and operations

- [ ] Circular-angle comparisons use wrap-safe distance.
- [ ] Tolerances are product-owned and written before acceptance.
- [ ] Fixture coverage includes wrap, station, topocentric, polar, and coverage edges.
- [ ] REST deployments gate on `/ready`, not only `/health`.
- [ ] Canary and rollback procedures are rehearsed.
- [ ] The Swiss dependency is removed only after the observation window.

## 17. Scope and authoritative references

This guide covers the common chart, position, observer, houses, sidereal,
aspect, and event migration path. It is not a promise that every Swiss symbol
has a Moira alias. For specialized work, use these current documents:

- [`Python API Reference`](../02_standards/API_REFERENCE.md)
- [`Service Layer Guide`](SERVICE_LAYER_GUIDE.md)
- [`REST API Reference`](REST_API_REFERENCE.md)
- [`Planetary Reduction Pipeline`](../02_standards/PLANETARY_REDUCTION_PIPELINE.md)
- [`Houses Backend Standard`](../02_standards/HOUSES_BACKEND_STANDARD.md)
- [`Validation — Astronomy`](../03_validation/VALIDATION_ASTRONOMY.md)
- [`Beyond Swiss Ephemeris`](../01_doctrines/BEYOND_SWISS_EPHEMERIS.md)
- [`Why Moira Does Not Compress DExx Files`](../01_doctrines/WHY_MOIRA_DOES_NOT_COMPRESS_DEXX.md)

Swiss behavior and flags should be checked against the official
[Swiss Ephemeris Programmer's Manual](https://www.astro.com/swisseph/swephprg.2.10.pdf)
for the exact version being migrated. The official
[`pyswisseph` repository](https://github.com/astrorigin/pyswisseph) documents
the Python binding shape. When either engine changes, re-run the application's
contract fixtures rather than assuming a previously accepted mapping still
holds.
