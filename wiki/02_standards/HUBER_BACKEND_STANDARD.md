# Huber Backend Standard

Version: 0.1
Date: 2026-06-13
Status: backend standard for Phase 12 evaluation

## Scope

This standard governs the Huber Astrological Psychology engine surface:

- `moira.huber`

It covers:

- golden-section house zones
- Age Point position
- Age Point contact scanning
- Dynamic Intensity Curve evaluation
- intensity at a longitude inside a house frame
- chart-wide intensity profile

It does not govern:

- house-cusp computation itself
- house-system fallback policy
- psychological interpretation text
- counseling claims
- chart rendering
- transits, progressions, or predictive timing outside Age Point mechanics

## Authority And Provenance

The engine documents the Huber method through:

- Bruno and Louise Huber, *Life Clock*
- Bruno Huber, *The Astrological Houses*
- Astrological Psychology Institute tradition

The module states that Huber doctrine prescribes Koch houses. The functions
accept any `HouseCusps` object, so doctrinal fidelity depends on caller-supplied
house-frame truth.

The Dynamic Intensity Curve is documented as a mathematical reconstruction:

- sinusoidal shape
- maximum at cusps
- minimum at the golden-section Low Point
- asymmetric because the Low Point is at phi rather than at 0.5

The module explicitly notes that the exact formula from the primary text has
not been independently verified against this reconstruction. Public transport
must preserve that limitation.

## Governing Objects

The admitted backend objects are:

- `HouseZone`
- `HouseZoneProfile`
- `AgePointPosition`
- `DynamicIntensity`
- `PlanetIntensityScore`
- `ChartIntensityProfile`

The admitted constants are:

- `PHI`
- `PHI_COMPLEMENT`
- `CYCLE_YEARS`
- `YEARS_PER_HOUSE`

The admitted computations are:

- `house_zones(house_cusps)`
- `age_point(age_years, house_cusps)`
- `age_point_contacts(house_cusps, planet_longitudes, orb=2.0, start_age=0.0, end_age=72.0, step_years=1.0 / 12.0)`
- `dynamic_intensity(house, fraction)`
- `intensity_at(longitude, house_cusps)`
- `chart_intensity_profile(points, house_cusps)`

## House-Frame Doctrine

Huber analysis is not independent of house truth.

REST transport must not accept an unqualified set of house cusps without
recording:

- requested house system
- effective house system
- fallback state
- fallback reason when present
- whether the effective house system is Koch
- source of the cusps: chart-backed server derivation or direct cusp input

If direct cusp input is ever admitted, it must be marked as caller-supplied
geometry and must not imply Moira derived the house frame.

## Required Transport Invariants

Any REST transport for Huber must preserve:

- `age_years`
- age-cycle number
- years per house
- house number
- fraction through the house
- Age Point longitude
- zone classification
- intensity value
- all house-zone boundary longitudes
- balance-point and low-point fractions
- house-size truth
- point names and source longitudes for chart profiles
- high/low intensity thresholds
- curve reconstruction note
- Koch-house doctrinal preference

Transport must reject:

- non-finite ages
- negative ages
- malformed house frames
- non-finite house cusps
- house frames without exactly 12 cusps
- non-finite point longitudes
- empty point names
- non-finite or negative contact orbs
- non-finite or non-positive contact scan step sizes
- reversed contact scan ranges

Transport must not:

- silently label non-Koch houses as doctrinally Huber-complete
- hide house fallback truth
- claim primary-text formula verification for the Dynamic Intensity Curve
- convert intensity scores into psychological diagnoses
- expose unbounded contact scans

## Validation Requirements

The minimum backend validation corpus is:

```powershell
.\.venv\Scripts\python.exe -m pytest tests\unit\test_huber.py -q
```

The validation corpus must continue to cover:

- golden-ratio constants
- 72-year cycle and 6-year house timing
- house-zone count and ordering
- balance-point and low-point fractions
- Age Point positions at ages 0, 18, 36, 54, and 72
- negative-age rejection
- dynamic-intensity curve bounds
- monotonic descent to the Low Point
- monotonic ascent from the Low Point
- zone classification
- chart-profile score invariants
- public `__all__` surface

Route admission must add transport tests for malformed house frames, non-Koch
provenance reporting, polar/fallback house behavior, non-finite numbers, and
bounded contact-scan policy.

## REST Admission Guidance

The first admissible route should be a direct or chart-backed Age Point route
with explicit house-frame provenance.

Recommended sequence:

1. `dynamic_intensity` primitive.
2. `house_zones` over an admitted house frame.
3. `age_point` over an admitted house frame.
4. `chart_intensity_profile` over admitted points and house frame.
5. bounded `age_point_contacts`.

Chart-backed routes must use the same house derivation and fallback truth as
the admitted houses REST surface. Huber must not introduce a second house
derivation path.

## Non-Goals

This standard does not admit:

- psychological interpretation text
- counseling claims
- health or clinical claims
- unbounded Age Point searches
- hidden house-system substitution
- independent house calculation inside Huber transport
- chart rendering
- `/v1/special/*` exposure
