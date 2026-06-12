# Local Space Backend Standard

Version: 0.1
Date: 2026-06-11
Status: Active backend admission packet for Phase 10 REST evaluation
Scope: `moira.local_space`

This standard records the backend truth that may be exposed by the REST server
for P10-02 Local Space. It is not a map-rendering standard and does not admit
route products that project, draw, tile, or otherwise render a chart.

It is downstream of:

- `wiki/00_foundations/ENGINE_VS_SERVICE_BOUNDARY.md`
- `docs/architecture/MOIRA_SERVER_ROUTE_ADMISSION_CHECKLIST.md`
- `docs/architecture/MOIRA_SERVER_PHASE10_LEDGER.md`
- `wiki/03_validation/VALIDATION_EXPERIMENTAL.md`

---

## 1. Governing Object

The governing object is a body's apparent horizon position for one terrestrial
observer at one epoch:

- azimuth in the navigational convention, with North at `0` degrees and East at
  `90` degrees
- altitude above or below the local horizon
- above-horizon boolean
- 8-point compass label derived from azimuth

These are observer-local horizon products. They are not ecliptic positions,
house cusps, map projections, rendered compass charts, or relocation chart
synthesis.

---

## 2. Public Engine Surface

Authoritative module:

- `moira/local_space.py`

Public vessel:

- `LocalSpacePosition`

Public functions:

- `local_space_positions(planet_ra_dec, latitude, lst_deg)`
- `local_space_from_chart(chart, observer_lat, observer_lon, bodies=None)`

Facade exposure:

- `SpatialFacadeMixin.local_space(...)`

---

## 3. Frame And Input Truth

Direct low-level inputs:

- body name
- apparent right ascension in degrees
- apparent declination in degrees
- observer geographic latitude in degrees
- local apparent sidereal time in degrees

Chart-backed inputs:

- `ChartContext`
- observer latitude
- observer longitude
- optional selected bodies

Frame doctrine:

- RA/Dec are apparent equatorial coordinates matching the supplied local
  sidereal time unless a direct caller explicitly owns another source.
- `lst_deg` is local apparent sidereal time in degrees for the observer's
  longitude at the chart epoch.
- Longitude is not needed by `local_space_positions(...)` after LST has already
  been supplied.
- Chart-backed routes must derive apparent RA/Dec through the server's admitted
  topocentric sky-position path.
- Chart-backed routes must derive LST from `jd_ut`, nutation, true obliquity,
  and observer longitude.

---

## 4. Result Semantics

`LocalSpacePosition` preserves:

- `body`
- `azimuth`
- `altitude`
- `is_above`

Derived helper:

- `compass_direction()`

Result invariants:

- `azimuth` is normalized to `[0, 360)`.
- `altitude` is in `[-90, 90]`.
- `is_above` is true when `altitude >= 0`.
- results are sorted by azimuth.
- compass direction is an 8-point label: `N`, `NE`, `E`, `SE`, `S`, `SW`, `W`,
  or `NW`.

---

## 5. Bounded Output Policy

First REST admission may expose:

- direct Local Space positions from caller-supplied RA/Dec and LST
- chart-backed Local Space positions from datetime, observer, and bodies

First REST admission must not expose:

- rendered compass charts
- map products
- SVG or raster outputs
- projection products
- relocation chart synthesis
- unbounded body catalogs

REST transport should bound body count before admission.

---

## 6. Validation And Evidence

Existing validation:

- `tests/unit/test_local_space.py`
- `wiki/03_validation/VALIDATION_EXPERIMENTAL.md`

Covered invariants include:

- equatorial cardinal cases for zenith, nadir, east, and west horizon points
- north/south meridian cases at nonzero latitude
- sorting by azimuth
- 8-point compass labeling
- `LocalSpacePosition` repr and above/below-horizon semantics
- `local_space_from_chart(...)` wrapper plumbing for sidereal time and RA/Dec
  collection
- rejection of invalid direct latitude, LST, RA/Dec, declination, and body-name
  inputs

---

## 7. REST Admission Position

P10-02 Local Space is eligible to move from evaluation to transport design for
bounded direct and chart-backed horizon position products.

REST design must still decide:

- direct RA/Dec/LST route shape
- chart-backed route shape
- maximum body count
- observer latitude/longitude validation
- response provenance fields
- whether a compass label is serialized as a field or left to clients to derive

Do not admit map-rendering, compass-image, projection, or relocation synthesis
routes as part of first P10-02 transport.
