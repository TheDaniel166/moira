# The Moira Service Layer: Absolute Architectural Manifesto

## 1. The Sovereignty of the Facade (Orchestration Pattern)

The **Moira Service Layer** is not merely a collection of helper functions; it is a **Sovereign Orchestration Layer**. The `Moira` class serves as the **High Priestess and Dependency Injection (DI) Container**, binding a persistent `SpkReader` (JPL DE441) to a vast pantheon of computational sub-engines.

The facade enforces a single, inviolable contract: **no sub-engine may be invoked without flowing through the Moira instance**. This guarantees I/O consistency (every call shares the same memory-mapped kernel), temporal consistency (all JD conversions use the same ΔT tables), and doctrinal consistency (policies propagate from the facade to every leaf computation).

### 1.1 The Lifecycle of a Service Call

When a service method (e.g., `m.conjunctions()`) is invoked, the facade executes the following **Liturgy of Transformation**:

1. **Temporal Reconciliation**: Datetime objects are instantly converted to Julian Days (JD UT) via the `julian.py` substrate. The Meeus algorithm handles all proleptic Gregorian dates, including BCE dates via astronomical year numbering (0 = 1 BC, −1 = 2 BC).
2. **UT → TT Bridge**: The JD UT is translated to Terrestrial Time (JD TT) by adding ΔT/86400, where ΔT is interpolated from multi-era historical tables spanning 1600 CE to 2500 CE.
3. **Subsystem Delegation**: The call is routed to its sovereign module (e.g., `phenomena.py`, `dasha.py`) while passing the `Moira` instance's own `_reader` to ensure I/O consistency.
4. **Truth Extraction**: The subsystem derives truth from the raw SPK state vectors, applying the full apparent-position pipeline where required.
5. **Vessel Manifestation**: The result is decanted into a typed `slots`-optimized vessel and returned to the caller. Most result records are immutable, but the root `moira.Chart` vessel remains mutable by design in the current package surface.

### 1.2 The Full Method Inventory

The `Moira` facade exposes **70+ public methods** organized into ten sovereign domains:

| Domain | Representative Methods | Governance Module |
|--------|----------------------|-------------------|
| **Chart Construction** | `chart()`, `houses()`, `sky_position()` | `planets.py`, `houses.py` |
| **Aspects** | `aspects()`, `antiscia()` | `aspects.py` |
| **Phenomena** | `conjunctions_in_range()`, `moon_phases_in_range()`, `greatest_elongation()`, `resonance()` | `phenomena.py` |
| **Eclipses** | `eclipse()` | `eclipse.py` |
| **Stations & Retrogrades** | `stations()`, `retrograde_periods()`, `is_retrograde()` | `stations.py` |
| **Synastry** | `synastry_aspects()`, `house_overlay()`, `composite_chart()`, `davison_chart()` | `synastry.py` |
| **Time Lords** | `vimshottari_dasha()`, `firdaria()`, `zodiacal_releasing()` | `dasha.py`, `timelords.py` |
| **Progressions** | `progression()`, `solar_arc_directions()`, `tertiary_progression()`, `converse_progression()` | `progressions.py` |
| **Transits & Returns** | `transits()`, `ingresses()`, `solar_return()`, `lunar_return()` | `transits.py` |
| **Techniques** | `lots()`, `dignities()`, `midpoints()`, `harmonic()`, `profection()`, `planetary_hours()`, `astrocartography()`, `local_space()` | various |
| **Sidereal** | `sidereal_chart()`, `nakshatras()` | `sidereal.py` |
| **Fixed Stars** | `fixed_star()`, `heliacal_rising()` | `stars.py` |

---

## 2. The Ephemeris Substrate (SPK Reader & DE441)

### 2.1 The Kernel Gateway

All positional truth in Moira originates from a single source: the **JPL DE441 Binary SPK Kernel** (`de441.bsp`). The `SpkReader` class in `spkreader.py` provides memory-mapped access to this 3.1 GB file, which encodes Chebyshev polynomial coefficients for every major solar system body from **13,200 BCE to 17,191 CE**.

```
SpkReader
├── __init__(kernel_path)     → opens DAF/BSP via jplephem
├── position(center, target, jd) → Vec3 (x, y, z) in km, ICRF
└── position_and_velocity(center, target, jd) → (Vec3, Vec3) in km, km/day
```

The kernel uses a **two-epoch structure**: one segment covers −13200 to 1969, and another covers 1969 to 17191. The `SpkReader` automatically selects the correct segment for any query.

### 2.2 Body Routing Chains (NAIF Protocol)

DE441 stores positions relative to various barycenters. To obtain a body's position relative to a desired center, the engine chains multiple SPK segments using **NAIF ID routes**:

| Body | Route | Meaning |
|------|-------|---------|
| Sun | `(0→10)` | SSB → Sun |
| Moon | `(3→301)` | Earth-Moon Barycenter → Moon |
| Mercury | `(0→1), (1→199)` | SSB → Mercury Barycenter → Mercury |
| Venus | `(0→2), (2→299)` | SSB → Venus Barycenter → Venus |
| Mars | `(0→4)` | SSB → Mars Barycenter |
| Jupiter–Pluto | `(0→N)` | SSB → Planet Barycenter |
| Earth | `(0→3), (3→399)` | SSB → EMB → Earth |

The geocentric position of any body is computed by:
1. Summing the body's chain to get its SSB-relative position.
2. Summing the Earth chain `[(0,3), (3,399)]` to get Earth's SSB-relative position.
3. Subtracting Earth from body: `xyz_geo = xyz_body_ssb − xyz_earth_ssb`.

### 2.3 Module-Level Singleton

The `SpkReader` is managed as a **thread-safe module-level singleton** via `get_reader()` and an `RLock`:

- `get_reader(kernel_path)` — returns the cached instance, creating it on first call.
- `set_kernel_path(path)` — configures the kernel path before first access.
- The singleton pattern ensures that even high-cadence searches (scanning decades of conjunctions) share a single memory-mapped file handle, consuming minimal RAM.

---

## 3. The Seven-Step Apparent Position Pipeline

The crown jewel of the Moira engine is the **Seven-Step Apparent Position Pipeline**, implemented across `corrections.py` and `coordinates.py`. This transforms raw ICRF barycentric state vectors into the true apparent ecliptic position an observer would see.

### Step 1: Light-Time Correction
**Module**: `corrections.apply_light_time()`

The photon from a distant planet takes time to reach Earth. The planet's position must be evaluated at `t − τ`, where `τ = d/c`.

- **Algorithm**: Single Newton-Raphson iteration. Compute the planet's position at time `t`, calculate distance `d₀` and initial light-time `τ₀ = d₀/c`. Then re-evaluate the planet at `t − τ₀` and compute the final corrected `τ₁`.
- **Constant**: `C_KM_PER_DAY = 299,792.458 × 86,400 = 25,902,068,371.2 km/day`
- **Effect**: ~8.3 minutes for Sun, ~4–24 minutes for planets, ~1.3 seconds for Moon.

### Step 2: Annual Aberration (Relativistic)
**Module**: `corrections.apply_aberration()`

Earth's orbital velocity (~29.8 km/s) causes an apparent displacement of all celestial objects in the direction of motion.

- **Algorithm**: Full IAU SOFA relativistic formula:
  ```
  β = v_earth / c
  γ = 1 / √(1 − β²)
  u' = [u + (1 + (u·β)/(1+γ))·β] / [γ(1 + u·β)]
  ```
  where `u` is the unit vector toward the body and `β` is Earth's velocity vector in units of c.
- **Effect**: ~20.5″ maximum at 90° from the apex of Earth's motion.

### Step 3: Gravitational Deflection
**Module**: `corrections.apply_deflection()`

The Sun's gravitational field bends light passing near it, displacing apparent positions.

- **Algorithm**: IAU SOFA point-mass Sun model (LDSUN):
  ```
  deflection = (2 * r_s / d_sun) * [(u·q_sun)·p_sun − (p_sun·q_sun)·u]
  ```
  where `r_s = 2.95325008 km` (solar Schwarzschild radius), `q_sun` is the Sun's unit vector, and `p_sun` is the body's unit vector.
- **Singularity guard**: Skipped when `cos(ψ) < −0.9999999` (anti-solar point).
- **Effect**: ~1.75″ at the solar limb, ~0.004″ at 90° elongation.

### Step 4: Frame Bias (ICRF → J2000.0 Dynamical)
**Module**: `corrections.apply_frame_bias()`

The ICRF (International Celestial Reference Frame) is not exactly aligned with the J2000.0 dynamical frame used by precession/nutation theories.

- **Constants** (IAU 2006):
  - `dα₀ = −14.6 mas` (right ascension origin offset)
  - `ξ₀ = −16.6170 mas` (x-axis tilt)
  - `dε₀ = −6.8192 mas` (y-axis tilt)
- **Algorithm**: Small-angle antisymmetric rotation matrix (fixed, not time-dependent).
- **Effect**: ~17 mas, constant.

### Step 5: Precession (J2000.0 → Mean Equator of Date)
**Module**: `coordinates.precession_matrix_equatorial()` → delegates to `precession.py`

The Earth's spin axis slowly traces a cone with a ~25,772-year period. Precession rotates the J2000.0 mean equator/equinox to the mean equator/equinox of the observation date.

- **Model**: IAU 2006 (P03) Fukushima-Williams 4-angle formulation.
- **Effect**: ~50.3″/year in ecliptic longitude.

### Step 6: Nutation (Mean → True Equinox of Date)
**Module**: `coordinates.nutation_matrix_equatorial()` → delegates to `nutation_2000a.py`

Short-period oscillations of the Earth's axis caused by the Moon's orbital plane and solar gravitational torques.

- **Model**: IAU 2000A truncated series.
- **Term count**: **2,414 total** — 1,358 luni-solar terms + 1,056 planetary terms.
- **Fundamental arguments**: 14 parameters:
  - 5 Delaunay luni-solar: mean anomaly of Moon (`l`), mean anomaly of Sun (`l'`), mean argument of latitude (`F`), mean elongation of Moon (`D`), longitude of ascending node (`Ω`).
  - 8 planetary mean longitudes: Mercury through Neptune.
  - 1 general precession in longitude (`pₐ`).
- **Returns**: `(Δψ, Δε)` in degrees.
- **Matrix**: `N = R₁(−ε) · R₃(−Δψ) · R₁(ε₀)` where ε₀ is mean obliquity.
- **Accuracy**: ~0.1 μas for 1995–2050.

### Step 7: Topocentric Parallax (Geocenter → Observer)
**Module**: `corrections.topocentric_correction()`

Converts geocentric positions to the observer's actual location on Earth's surface.

- **Geodetic model**: WGS-84 (flattening `f = 1/298.257223563`).
- **Algorithm**: Compute observer's geocentric rectangular coordinates from (latitude, longitude, elevation), then subtract from the geocentric body position vector.
- **Effect**: ~1° for the Moon, ~0.01″ for planets, negligible for stars.

### Pipeline Summary

```
Raw SPK (ICRF, Barycentric, at time t)
  │
  ├─[1] Light-Time  ──→  ICRF, Geocentric, at time t−τ
  ├─[2] Aberration   ──→  ICRF, Geocentric, apparent direction
  ├─[3] Deflection   ──→  ICRF, Geocentric, gravity-corrected
  ├─[4] Frame Bias   ──→  J2000 Dynamical, Geocentric
  ├─[5] Precession   ──→  Mean Equator of Date
  ├─[6] Nutation     ──→  True Equator of Date
  └─[7] Parallax     ──→  Topocentric, True Equinox of Date
                            │
                            └── icrf_to_true_ecliptic() → (λ, β, Δ)
```

When `apparent=False` is passed to `planet_at()`, only the light-time correction and basic geocentric transformation are applied (geometric position).

---

## 4. The Time Substrate (julian.py)

### 4.1 Julian Day Conversion

All internal timestamps are expressed in **Julian Days** (JD), a continuous count of days since January 1, 4713 BCE at noon UT.

- `julian_day(year, month, day, hour)` → JD via the Meeus algorithm, valid for any proleptic Gregorian date.
- `jd_from_datetime(dt)` → JD from a Python `datetime` (naïve datetimes treated as UTC).
- `calendar_from_jd(jd)` → `(year, month, day, decimal_hour)`.
- `datetime_from_jd(jd)` → Python `datetime` (limited to 1 AD–9999 AD).
- `calendar_datetime_from_jd(jd)` → `CalendarDateTime` dataclass (BCE-safe via astronomical year numbering).

### 4.2 The CalendarDateTime Vessel

```python
@dataclass(frozen=True, slots=True)
class CalendarDateTime:
    year: int          # astronomical: 0 = 1 BC, −1 = 2 BC
    month: int
    day: int
    hour: int
    minute: int
    second: int
    microsecond: int = 0
    tzname: str = "UTC"
```

This vessel exists because Python's `datetime` cannot represent dates before 1 AD. All BCE-era calculations (e.g., ancient eclipse searches) use this type.

### 4.3 ΔT (TT − UT1) — The Temporal Bridge

The difference between Terrestrial Time (uniform, atomic) and Universal Time (tied to Earth's irregular rotation) is denoted **ΔT**. Moira interpolates ΔT from five historical tables:

| Era | Source | Method |
|-----|--------|--------|
| 1600–1900 | Historical reconstructions | 5-year interpolation |
| 1900–1955 | Pre-modern observations | 5-year interpolation |
| 1955–2015 | IERS observed values | 5-year interpolation |
| 2015–2026 | IERS annual values | Annual interpolation |
| 2026+ / ancient | HPIERS 2016 long-range model | Polynomial extrapolation |

- `delta_t(decimal_year)` → seconds.
- `ut_to_tt(jd_ut)` → `jd_ut + delta_t / 86400`.
- `tt_to_ut(jd_tt)` → JD UT via iterative inversion (since ΔT depends on the unknown UT).

### 4.4 Sidereal Time

- `greenwich_mean_sidereal_time(jd_ut)` → GMST in degrees.
- `apparent_sidereal_time(jd_ut, Δψ, ε)` → GAST = GMST + Δψ·cos(ε) (nutation-corrected).
- `local_sidereal_time(jd_ut, longitude, Δψ, ε)` → LST = GAST + λ_observer.

---

## 5. The Service Pylons (Deep Implementation)

### 5.1 The Phenomena Pylon: Search & Refinement
*Governance: `moira/phenomena.py`*

The Phenomena services identify discrete celestial milestones using a **Two-Phase Discovery Archetype**.

#### Phase I: Localization (Geometric Walk)

The service performs a coarse-grained scan using **geometric positions** (raw SPK, no apparent pipeline). Step sizes are body-dependent and event-dependent:
- **Conjunctions**: 3-day steps.
- **Moon phases**: 1-day steps.
- **Elongations/Apsides**: body-dependent daily steps.

The scan detects **sign changes** in a discriminant function (for zero-crossings like conjunctions and phases) or **slope reversals** (for extrema like elongations and apsides).

#### Phase II: Refinement (Apparent Bisection / Golden-Section)

Once a crossing or extremum is localized to a coarse interval, the service activates the **full Apparent Pipeline** and applies:

- **Bisection** for zero-crossings (conjunctions, phases, ingresses): converges to ~1-second precision by halving the interval until the discriminant magnitude is below threshold.
- **Golden-Section Search** for extrema (elongations, perihelion, aphelion): narrows the bracketed interval using the golden ratio φ = (√5−1)/2 to find the maximum/minimum without requiring derivatives.

#### Data Vessels

```python
@dataclass(slots=True)
class PhenomenonEvent:
    body: str              # e.g., "Venus"
    phenomenon: str        # e.g., "greatest_eastern_elongation"
    jd_ut: float           # precise Julian Day of event
    value: float           # e.g., elongation angle in degrees

@dataclass(slots=True)
class OrbitalResonance:
    ratio: float           # raw period ratio (e.g., 1.6255)
    synodic_period: float  # days
    harmonic_ratio: str    # "13:8"
    near_integer: tuple    # (13, 8)
    error: float           # fractional deviation
```

#### Public Functions

| Function | Description |
|----------|-------------|
| `greatest_elongation(body, jd_start, direction, max_days)` | Mercury/Venus max angular distance from Sun |
| `perihelion(body, jd_start, max_days)` | Closest approach to Sun |
| `aphelion(body, jd_start, max_days)` | Furthest distance from Sun |
| `next_moon_phase(phase_name, jd_start)` | Exact moment of named Moon phase |
| `moon_phases_in_range(jd_start, jd_end)` | All 8 phases chronologically |
| `next_conjunction(body1, body2, jd_start)` | Zero longitudinal separation |
| `conjunctions_in_range(body1, body2, jd_start, jd_end)` | All conjunctions in window |
| `resonance(body1, body2)` | Orbital resonance via continued fractions |

#### The Continued Fraction Solver

The `resonance()` service derives harmonic ratios from raw orbital periods using a **Continued Fraction Approximation**:

```
Input: ratio = T_earth / T_venus = 1.6255...
Algorithm:
  x = 1.6255
  a₀ = 1,  remainder = 1/(1.6255 − 1) = 1.5988...
  a₁ = 1,  remainder = 1/(1.5988 − 1) = 1.6686...
  a₂ = 1,  remainder = 1/(1.6686 − 1) = 1.4957...
  ...convergents: 1/1, 2/1, 3/2, 5/3, 8/5, 13/8 ←── Venus Rose!

Output: OrbitalResonance(ratio=1.6255, harmonic_ratio="13:8", error=0.0005)
```

The algorithm halts when the denominator exceeds `max_denominator=50`, producing the best rational approximation. This mathematically identifies the "Heartbeat of the Sphere" from raw orbital periods rather than relying on look-up tables.

---

### 5.2 The Eclipse Pylon: Shadow Geometry Engine
*Governance: `moira/eclipse.py`*

The Eclipse service is the most computationally intensive single-event calculator in Moira. It combines lunisolar geometry, Besselian elements, and shadow cone projection to fully characterize solar and lunar eclipses.

#### The EclipseCalculator Class

- `calculate(dt)` → `EclipseData` — full eclipse analysis for the nearest eclipse to the given datetime.

#### Eclipse Classification

| Solar | Lunar |
|-------|-------|
| Total | Total |
| Partial | Partial |
| Annular | Penumbral |
| Hybrid (Annular-Total) | — |

#### Data Vessels

```python
@dataclass(slots=True)
class EclipseData:
    # Type classification
    eclipse_type: str          # "solar_total", "lunar_penumbral", etc.
    # Timing
    events: list[EclipseEvent] # C1, C2, max, C3, C4 contact times
    # Saros/Metonic identification
    saros_series: int          # Saros series number
    saros_position: int        # Position within series
    # Geometry (solar eclipses)
    besselian_elements: dict   # Shadow cone parameters
    # Geometry (lunar eclipses)
    penumbral_magnitude: float
    umbral_magnitude: float

@dataclass(slots=True)
class SolarEclipseLocalCircumstances:
    # Observer-specific eclipse visibility
    ...

@dataclass(slots=True)
class LunarEclipseAnalysis:
    # Penumbral/umbral geometry
    ...
```

#### Saros & Metonic Cycles

Every eclipse is identified within its **Saros series** — a family of eclipses recurring every 6,585.3 days (≈18 years 11 days) with nearly identical geometry. The engine computes the series number and position from the eclipse's lunation number and nodal parameters.

---

### 5.3 The Station Pylon: Retrograde Detection Engine
*Governance: `moira/stations.py`*

Stations (the apparent standstills of planets as they switch between direct and retrograde motion) are detected via zero-crossing analysis of the planet's daily speed.

#### Algorithm

1. **Coarse scan**: Step forward in body-dependent daily intervals, evaluating `planet_at(body, jd).speed` at each step.
2. **Sign-change detection**: When `speed[i] > 0` and `speed[i+1] < 0` (or vice versa), a station is bracketed.
3. **Bisection refinement**: Narrow the bracket until precision reaches ~1 second, yielding the exact JD of station.

#### Data Vessel

```python
@dataclass(slots=True)
class StationEvent:
    body: str            # e.g., "Mars"
    station_type: str    # "retrograde" (SR) or "direct" (SD)
    jd_ut: float         # precise Julian Day
    longitude: float     # ecliptic longitude at station
```

#### Public Functions

| Function | Description |
|----------|-------------|
| `find_stations(body, jd_start, jd_end)` | All SR/SD stations in range |
| `next_station(body, jd_start, max_days)` | First upcoming station |
| `is_retrograde(body, jd)` | Boolean test at any instant |
| `retrograde_periods(body, jd_start, jd_end)` | List of `(SR_jd, SD_jd)` tuples |

---

### 5.4 The Temporal Pylon: Hierarchical Time Lord Solvers
*Governance: `moira/dasha.py`, `moira/timelords.py`*

Unlike the searcher-based Phenomena services, the Temporal services are **Recursive Solvers** that divide life into nested hierarchical periods.

#### 5.4.1 Vimshottari Dasha (Vedic Time Lords)

The 120-year **Vimshottari Cycle** is governed by nine planetary lords, each ruling a fixed number of years:

| Lord | Years | Lord | Years |
|------|-------|------|-------|
| Ketu | 7 | Rahu | 18 |
| Venus | 20 | Jupiter | 16 |
| Sun | 6 | Saturn | 19 |
| Moon | 10 | Mercury | 17 |
| Mars | 7 | **Total** | **120** |

**Sequence**: Ketu → Venus → Sun → Moon → Mars → Rahu → Jupiter → Saturn → Mercury → (repeat)

**Algorithm**:

1. **Nakshatra Determination**: Convert the natal Moon's tropical longitude to sidereal using the selected ayanamsa (default: Lahiri). Divide by 13°20′ to find the birth nakshatra (1–27).
2. **Starting Lord**: Each nakshatra is governed by a Vimshottari lord. The fraction of the nakshatra already traversed determines the **balance of dasha** remaining at birth.
3. **Recursive Sub-Period Generation**: The service generates up to **five levels** of nested sub-periods:

| Level | Name | Division |
|-------|------|----------|
| 1 | Mahadasha | 120-year cycle ÷ 9 lords |
| 2 | Antardasha | Each Mahadasha ÷ 9 lords |
| 3 | Pratyantardasha | Each Antardasha ÷ 9 lords |
| 4 | Sookshma | Each Pratyantardasha ÷ 9 lords |
| 5 | Prana | Each Sookshma ÷ 9 lords |

Each level is calculated as a fraction of its parent's span, maintained with **sub-microsecond precision** in the Julian Day substrate.

**Doctrinal Policies**: Users inject a `VimshottariComputationPolicy` to customize:

```python
@dataclass(frozen=True, slots=True)
class VimshottariComputationPolicy:
    year: VimshottariYearPolicy       # "julian_365.25" or "savana_360"
    ayanamsa: VimshottariAyanamsaPolicy  # Lahiri, Raman, Krishnamurti, etc.
```

The year basis choice affects every period boundary: Julian (365.25 days/year) produces longer absolute durations than Vedic Savana (360 days/year).

**Data Vessels**:

```python
@dataclass(slots=True)
class DashaPeriod:
    level: int              # 1–5
    planet: str             # ruling lord
    start_jd: float         # period start
    end_jd: float           # period end
    year_days: float        # year length used (365.25 or 360)
    sub: list[DashaPeriod]  # nested children
    year_basis: str         # doctrinal provenance
    birth_nakshatra: str    # computed nakshatra
    nakshatra_fraction: float  # fraction elapsed at birth
    lord_type: str          # LUMINARY, INNER, OUTER, NODE

@dataclass(slots=True)
class DashaActiveLine:
    mahadasha: str
    antardasha: str
    pratyantardasha: str
    sookshma: str
    prana: str
```

**Analytical Functions**:

| Function | Returns |
|----------|---------|
| `vimshottari(moon_lon, natal_jd, levels, ...)` | Full 120-year period tree |
| `current_dasha(moon_lon, natal_jd, current_jd, levels)` | Active periods at query moment |
| `dasha_balance(moon_lon, natal_jd)` | `(lord, remaining_years)` at birth |
| `dasha_active_line(periods)` | Named relational chain |
| `dasha_condition_profile(period)` | Integrated local condition |
| `dasha_sequence_profile(periods)` | Chart-wide aggregate stats |
| `dasha_lord_pair(line)` | Network node for lord pairing |
| `validate_vimshottari_output(periods)` | Structural invariant checker |

#### 5.4.2 Firdaria (Hellenistic Time Lords)

The Firdaria system assigns planetary rulerships based on **sect** (day vs. night chart):

- **Diurnal sequence**: Sun(10) → Venus(8) → Mercury(13) → Moon(9) → Saturn(11) → Jupiter(12) → Mars(7) → North Node(3) → South Node(2) = **75 years**
- **Nocturnal sequence**: Moon(9) → Saturn(11) → Mercury(13) → ... (different order)

Each major period is subdivided into sub-periods ruled by the other planets. The `firdaria()` function generates the complete sequence as a list of `FirdarPeriod` vessels.

#### 5.4.3 Zodiacal Releasing (Hellenistic Chronocrator)

Zodiacal Releasing projects a **Lot** (e.g., Lot of Fortune, Lot of Spirit) through the signs of the zodiac, with each sign's duration determined by its planetary ruler's "minor years":

```python
@dataclass(slots=True)
class ReleasingPeriod:
    sign: str           # zodiac sign
    lord: str           # sign ruler
    start_jd: float
    end_jd: float
    level: int          # 1 (major), 2 (sub), etc.
    peak: bool          # angular to Fortune = "peak period"
```

The service generates nested periods (major → sub → sub-sub) allowing for detailed life-phase analysis.

---

### 5.5 The Relational Pylon: Cross-Chart Mapping
*Governance: `moira/synastry.py`*

The Relational services orchestrate truth between two or more discrete state snapshots. Four distinct techniques are supported:

#### 5.5.1 Synastry Aspects (Bi-Wheel Mapping)

`synastry_aspects(chart_a, chart_b, tier, orbs, orb_factor)` computes every admitted aspect between the planets of two charts:

- Uses the same orb/tier/family system as natal aspects.
- Returns `list[AspectData]` with cross-chart body references.
- Applying/separating determined by comparing the speeds of planets in their respective charts.

#### 5.5.2 House Overlay

`house_overlay(chart_source, target_houses)` projects the planetary positions of one chart into the house framework of another:

- For each planet in `chart_source`, determines which house of `target_houses` it falls in.
- Returns `SynastryHouseOverlay` with a list of `HousePlacement` vessels.
- `mutual_house_overlays()` performs both directions simultaneously.

#### 5.5.3 Composite Chart (Midpoint Method)

`composite_chart(chart_a, chart_b)` generates a virtual synthetic chart by computing the **spatial midpoints** of corresponding planetary positions:

- For each shared body, the composite longitude = midpoint of the two natal longitudes (using the shorter arc).
- Houses computed for the midpoint time or a reference location.
- Returns `CompositeChart` with synthesized `planets`, `nodes`, and `houses`.

#### 5.5.4 Davison Chart (Time-Space Midpoint)

Unlike the abstract Composite, the Davison produces a **real chart** cast for the temporal and geographic midpoint of two births:

```python
@dataclass(slots=True)
class DavisonInfo:
    jd_a: float            # natal JD person A
    jd_b: float            # natal JD person B
    lat_a, lon_a: float    # birth coordinates A
    lat_b, lon_b: float    # birth coordinates B
    midpoint_jd: float     # (jd_a + jd_b) / 2
    midpoint_lat: float    # (lat_a + lat_b) / 2
    midpoint_lon: float    # (lon_a + lon_b) / 2
    method: str            # "arithmetic" | "spherical" | "corrected"
```

Multiple Davison variants exist:
- `davison_chart()` — arithmetic midpoint (default).
- `davison_chart_spherical_midpoint()` — great-circle midpoint on the sphere.
- `davison_chart_corrected()` — corrected for geographic curvature.
- `davison_chart_reference_place()` — midpoint time, user-specified location.

#### Policies

All synastry operations accept granular policy injection:

```python
@dataclass(frozen=True, slots=True)
class SynastryComputationPolicy:
    aspect: SynastryAspectPolicy
    overlay: SynastryOverlayPolicy
    composite: SynastryCompositePolicy
    davison: SynastryDavisonPolicy
```

---

## 6. The Aspect Engine (Classification & Graph Theory)

*Governance: `moira/aspects.py`*

### 6.1 Aspect Taxonomy

The aspect engine classifies **24 distinct aspects** across three tiers and two domains:

#### Zodiacal Domain

| Tier | Aspects | Count |
|------|---------|-------|
| **Major** | Conjunction (0°), Sextile (60°), Square (90°), Trine (120°), Opposition (180°) | 5 |
| **Common Minor** | Semisextile (30°), Semisquare (45°), Quintile (72°), Sesquiquadrate (135°), Biquintile (144°), Quincunx (150°) | 6 |
| **Extended Minor** | Septile (51.43°), Novile (40°), Decile (36°), Tridecile (108°), and others | 11 |

#### Declination Domain

| Aspect | Condition |
|--------|-----------|
| **Parallel** | Same declination (within orb) |
| **Contra-Parallel** | Equal but opposite declination (within orb) |

### 6.2 Classification Layer

Every detected aspect carries a full **classification descriptor**:

```python
@dataclass(frozen=True, slots=True)
class AspectClassification:
    domain: AspectDomain      # ZODIACAL or DECLINATION
    tier: AspectTier          # MAJOR, COMMON_MINOR, EXTENDED_MINOR
    family: AspectFamily      # CONJUNCTION, OPPOSITION, SQUARE, TRINE, SEXTILE,
                              # QUINTILE, SEPTILE, NOVILE, ...
```

### 6.3 Orb Handling

Orbs are stored in a `DEFAULT_ORBS` dictionary keyed by aspect angle. An `orb_factor` multiplier allows global tightening or widening:

- Factor `1.0` = default orbs (e.g., 8° for conjunction, 6° for trine).
- Factor `0.5` = tight orbs (e.g., 4° conjunction, 3° trine).
- Factor `1.5` = wide orbs (e.g., 12° conjunction, 9° trine).

### 6.4 Applying vs. Separating

When longitudinal speeds are available, the engine determines **motion state**:
- **Applying**: the faster body is closing the gap toward exact aspect.
- **Separating**: the faster body is moving away from exact aspect.
- **Stationary**: one body has near-zero speed (within threshold), aspect is "held."

### 6.5 Aspect Data Vessel

```python
@dataclass(slots=True)
class AspectData:
    body1: str               # e.g., "Sun"
    body2: str               # e.g., "Saturn"
    aspect: str              # e.g., "Square"
    angle: float             # exact aspect angle (90.0)
    separation: float        # actual angular distance
    orb: float               # |separation − angle|
    allowed_orb: float       # maximum admitted orb
    applying: bool | None    # True, False, or None (no speed data)
    stationary: bool         # body near standstill
    classification: AspectClassification

@dataclass(slots=True)
class AspectStrength:
    orb: float
    allowed_orb: float
    surplus: float           # allowed_orb − orb (positive = admitted)
    exactness: float         # 1.0 − (orb / allowed_orb), range [0, 1]
```

### 6.6 Pattern Detection

The engine identifies multi-body geometric configurations from aspect lists:

| Pattern | Definition |
|---------|------------|
| **T-Square** | Two planets in opposition, both square a third |
| **Grand Trine** | Three mutual trines forming an equilateral triangle |
| **Grand Cross** | Four planets in two oppositions and four squares |
| **Yod** | Two planets sextile each other, both quincunx a third (Finger of God) |
| **Stellium** | Three or more conjunctions in tight cluster |
| **Kite** | Grand trine with one planet opposed to one corner |
| **Mystic Rectangle** | Two oppositions connected by sextiles and trines |

```python
@dataclass(slots=True)
class AspectPattern:
    kind: str                # "T-Square", "Grand Trine", etc.
    bodies: list[str]        # participating planets
    aspects: list[AspectData]  # constituent aspects
```

### 6.7 Aspect Graph (Network Analysis)

`build_aspect_graph(aspects, bodies)` converts the flat aspect list into a relational network:

```python
@dataclass(slots=True)
class AspectGraph:
    nodes: list[AspectGraphNode]
    edges: list[AspectData]
    components: list[list[str]]   # connected subgraphs

@dataclass(slots=True)
class AspectGraphNode:
    name: str                     # planet name
    degree: int                   # number of aspects
    edges: list[AspectData]       # incident aspects
    family_counts: dict           # {TRINE: 2, SQUARE: 1, ...}
```

This enables structural queries like "which planet is the most aspected?" or "are there isolated planets with no major aspects?"

---

## 7. The House Systems (21 Implementations)

*Governance: `moira/houses.py`*

### 7.1 Supported Systems

Moira implements **21 house systems** spanning every major tradition:

#### Equal-Based Systems
| System | Method |
|--------|--------|
| **Equal** | 30° from Ascendant |
| **Whole Sign** | Sign boundaries from Ascendant's sign |
| **Vehlow** | Equal houses offset by 15° (cusps at mid-sign) |
| **Morinus** | Equal divisions of the celestial equator |
| **Meridian** | Equal divisions from the MC |

#### Quadrant Systems
| System | Method |
|--------|--------|
| **Placidus** | Trisection of diurnal/nocturnal semi-arcs (iterative) |
| **Koch** | Ascendant's birth-place semi-arc projected onto ecliptic |
| **Porphyry** | Trisection of quadrant arcs (direct) |
| **Campanus** | Prime vertical great circles projected onto ecliptic |
| **Regiomontanus** | Celestial equator divisions projected onto ecliptic |
| **Alcabitius** | Diurnal semi-arc trisection (similar to Placidus variant) |
| **Topocentric** | Polich-Page: observer-centered conic sections |
| **Azimuthal / Horizontal** | Horizon-based divisions |
| **Carter (Poli-Equatorial)** | Equal ARMC divisions |
| **Pullen (Sinusoidal Δ)** | Sinusoidal interpolation of quadrant boundaries |
| **Pullen (Sinusoidal Ratio)** | Sinusoidal ratio variant |
| **Krusinski** | Great circles through N/S horizon points |
| **APC** | Ascendant-Parallel-Circle |

#### Solar System
| System | Method |
|--------|--------|
| **Sunshine (Makransky)** | Divisions based on Sun's position relative to horizon |

### 7.2 The HouseCusps Vessel

```python
@dataclass(slots=True)
class HouseCusps:
    cusps: list[float]        # 12 ecliptic longitudes
    asc: float                # Ascendant
    mc: float                 # Midheaven (MC)
    vertex: float             # Vertex
    armc: float               # ARMC (sidereal time in degrees)
    obliquity: float          # True obliquity of ecliptic
    system: str               # Requested system
    effective_system: str     # Actually used (may differ due to fallback)
    fallback: bool            # True if polar fallback was triggered
    fallback_reason: str | None
    classification: HouseSystemClassification | None
    policy: HousePolicy | None
```

### 7.3 Polar Fallback Protocol

Quadrant systems like Placidus and Koch become mathematically undefined at extreme latitudes (|latitude| ≥ 90° − obliquity ≈ 66.56°). The engine handles this via **Policy-Driven Fallback**:

```python
class PolarFallbackPolicy(Enum):
    FALLBACK_TO_PORPHYRY = "porphyry"  # Graceful degradation
    RAISE = "raise"                      # Strict mode: error

class UnknownSystemPolicy(Enum):
    FALLBACK_TO_PLACIDUS = "placidus"
    RAISE = "raise"
```

When fallback occurs, the `HouseCusps` vessel preserves **doctrinal truth**: `system` records what was requested, `effective_system` records what was actually computed, and `fallback_reason` explains why.

### 7.4 House Assignment

```python
@dataclass(frozen=True, slots=True)
class HousePlacement:
    house: int             # 1–12
    longitude: float       # planet's longitude
    house_cusps: HouseCusps
    exact_on_cusp: bool    # within threshold of a cusp
    opening_cusp: float    # longitude of the cusp that opens this house
```

`assign_house(longitude, house_cusps)` uses the **interval rule**: house *n* owns the arc `[cusps[n−1], cusps[n mod 12])`, with correct handling of the 360°→0° wraparound.

---

## 8. The Vessels of Truth (Schema Rigidness)

Every service output is governed by the **Law of the Record**. Results must be decanted into strictly-typed vessels. Most doctrinal and policy records are immutable; the root `moira.Chart` vessel is a mutable snapshot that callers are expected to treat as read-only after construction.

### 8.1 Core Positional Vessels

```python
@dataclass(slots=True)
class PlanetData:
    name: str              # "Venus"
    longitude: float       # [0, 360) — ecliptic
    latitude: float        # ecliptic latitude
    distance: float        # km from Earth
    speed: float           # deg/day
    retrograde: bool       # speed < 0
    is_topocentric: bool   # False = geocentric
    sign: str              # computed: "Taurus"
    sign_symbol: str       # computed: "♉"
    sign_degree: float     # computed: longitude mod 30

@dataclass(slots=True)
class SkyPosition:
    name: str
    right_ascension: float  # degrees
    declination: float      # degrees
    azimuth: float          # degrees, N=0 E=90
    altitude: float         # degrees above horizon
    distance: float         # km

@dataclass(slots=True)
class Chart:
    jd_ut: float
    planets: dict[str, PlanetData]
    nodes: dict[str, NodeData]
    obliquity: float
    delta_t: float
```

### 8.2 Chart Construction Pipeline

`Moira.chart(dt, bodies, include_nodes, observer_lat, observer_lon, observer_elev_m)`:

1. Convert the datetime to JD UT.
2. For each body in `bodies`: call `all_planets_at()` with the bound reader.
3. Optionally compute nodes: True Node, Mean Node, Lilith.
4. Compute true obliquity and ΔT for the chart moment.
5. Bundle everything into `Chart`.

### 8.3 Architectural Invariants

All data vessels obey these laws:

| Invariant | Enforcement |
|-----------|-------------|
| **Immutability** | Default for doctrinal/policy/result records where mutation would change meaning. The root `Chart` vessel is the main exception and is mutable by implementation. |
| **Truth Preservation** | Vessels record the computational path (e.g., `year_basis`, `effective_system`) |
| **No Interpretation** | Vessels carry raw truth; interpretation is the caller's responsibility |
| **Self-Describing** | Classification enums and profiles are attached, never implied |

---

## 9. Operation & Performance Liturgy

### 9.1 Memory & I/O

The Moira service layer utilizes **Memory-Mapped DAF/BSP file handling** via the `SpkReader`. The `jplephem` library memory-maps the DE441 kernel, meaning:

- The 3.1 GB kernel is **not** loaded into RAM. Only the specific Chebyshev coefficient blocks needed for the current time and body are paged in by the OS.
- High-cadence searches (scanning decades of conjunctions) consume minimal RAM — typically < 50 MB for the entire process.
- Repeated queries for nearby dates hit the OS page cache, achieving near-zero disk I/O.

### 9.2 Computational Cost Profile

| Operation | Dominant Cost | Typical Latency |
|-----------|--------------|-----------------|
| Single `planet_at()` | 7-step pipeline + SPK read | ~0.1 ms |
| Full `chart()` (10 bodies + houses) | 10× planet_at + house calc | ~2 ms |
| `conjunctions_in_range()` (1 year) | ~120 coarse steps + ~12 refinements | ~50 ms |
| `moon_phases_in_range()` (1 year) | ~365 coarse steps + ~48 refinements | ~100 ms |
| `vimshottari_dasha()` (5 levels) | Pure arithmetic (no SPK) | ~1 ms |
| `eclipse()` | Besselian elements + contacts | ~20 ms |

### 9.3 No External Dependencies (Pure Python)

All vector/matrix operations in `coordinates.py` are implemented in **pure Python tuples** — no NumPy, no SciPy. This eliminates import overhead, simplifies deployment, and ensures the engine runs on any Python 3.10+ environment. The only external dependency for ephemeris I/O is `jplephem`.

### 9.4 Thread Safety and Shared Reader State

The computational methods are designed to be deterministic transformations of inputs into results, but the facade is not literally stateless. `Moira` binds a `SpkReader` on construction, and `spk_reader.py` also exposes a module-level singleton guarded by an `RLock`. In practice the package operates with shared reader state and pure read-only kernel access. This allows concurrent use so long as callers treat returned vessels as read-only and do not attempt to reconfigure the kernel path after the shared reader has been acquired.

### 9.5 Import-Time Side Effects

All modules declare zero import-time side effects, with two controlled exceptions:
- `julian.py` loads the ΔT interpolation tables once at import (a few KB of floats).
- `nutation_2000a.py` loads the IAU 2000A coefficient tables lazily on first use and then caches them in memory.

---

## 10. Architectural Patterns (Design Philosophy)

### 10.1 Pillar Isolation
Each technique module (dasha, timelords, eclipse, aspects, phenomena, stations, synastry) is **self-contained** with clear boundaries. There are no circular dependencies. Cross-cutting concerns are delegated:
- Time conversion → `julian.py`
- Coordinate transforms → `coordinates.py`
- Astrometric corrections → `corrections.py`
- Constants → `constants.py`

### 10.2 Policy Injection
Frozen policy dataclasses allow customization without breaking existing APIs. The default policy is always "the most common tradition," but users can override any doctrinal choice:

```python
# Default: Lahiri ayanamsa, Julian years
m.vimshottari_dasha(chart, natal_dt, levels=3)

# Custom: Raman ayanamsa, Savana years
policy = VimshottariComputationPolicy(
    year=VimshottariYearPolicy(year_basis="savana_360"),
    ayanamsa=VimshottariAyanamsaPolicy(ayanamsa_system=Ayanamsa.RAMAN)
)
m.vimshottari_dasha(chart, natal_dt, levels=3, policy=policy)
```

### 10.3 Classification Without Interpretation
Enums and frozen dataclasses classify results without adding subjective interpretation:
- `AspectClassification` tells you the tier and family — it doesn't tell you if it's "good" or "bad."
- `DashaLordType` tells you LUMINARY/INNER/OUTER/NODE — it doesn't assign benefic/malefic.
- `HouseSystemClassification` tells you EQUAL/QUADRANT/SOLAR — it doesn't favor one over another.

### 10.4 Relational Intelligence
Network vessels expose structural relationships between computation results:
- `AspectGraph` — planet-to-planet relational network with degree centrality.
- `DashaLordPair` — Mahadasha/Antardasha network node.
- `FirdarActivePair`, `ZRLevelPair` — time-lord relationship pairs.

### 10.5 Condition Profiles
Integrated "local condition" dataclasses bundle all doctrinal and computational truth for a single entity:
- `DashaConditionProfile` — planet, level, years, is_node_dasha, lord_type, etc.
- `DashaSequenceProfile` — chart-wide aggregate (mahadasha count, luminary/inner/outer/node counts).
- `FirdarConditionProfile`, `ZRConditionProfile` — Hellenistic equivalents.

### 10.6 Delegate, Don't Own
Each module owns **one conceptual domain** and delegates everything else. The `dasha.py` module never touches SPK data — it receives a pre-computed Moon longitude. The `phenomena.py` module never computes houses — it only works with planetary longitudes. This ensures that a change in the apparent-position pipeline propagates automatically to all consumers.

---

## 11. The Extensibility Ritual

To manifest a new service within the Moira sanctuary, the practitioner must follow the **Canon of Extension**:

### Step 1: Define the Vessel
Create a typed result vessel in the new module, preferably `dataclass(frozen=True, slots=True)` when the output is a doctrinal record. If mutability is intentional, document that explicitly and keep the mutation boundary narrow.

### Step 2: Define the Policy (if applicable)
If the technique has doctrinal variants (different traditions, optional corrections), create a frozen policy dataclass with sensible defaults.

### Step 3: Implement the Solver
Utilize the `Moira` facade's positional primitives (`m.chart()`, `m.planet_at()`, `m.houses()`). Never access the SPK reader directly from a service module.

### Step 4: Handle the Boundary
Ensure that all low-level math (nutation, aberration, coordinate transforms) is delegated to the engine modules (`corrections.py`, `coordinates.py`), while the service focuses purely on **Orchestration and Result Assembly**.

### Step 5: Add Classification
If the technique produces categorizable results, add an enum or frozen classification dataclass. Never embed interpretive text in the classification — let the consumer decide meaning.

### Step 6: Wire Into the Facade
Add a public method to the `Moira` class that delegates to your new module, following the existing naming conventions and parameter patterns.

---

*Liturgy Version: 2.0 (Absolute Deep Architecture Revision)*
*Custodian: Sophia, High Architect of the Moira Engine*

