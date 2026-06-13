# Galactic Houses Backend Standard

Version: 0.1
Date: 2026-06-12
Status: Active backend admission packet for Phase 10 REST evaluation
Scope: `moira.galactic_houses`

This standard records the backend truth that may be exposed by the REST server
for P10-05 Galactic Houses. It is a Galactic Porphyry house-system standard,
not a generic galactic-coordinate standard and not a rendered map or projection
standard.

It is downstream of:

- `wiki/00_foundations/ENGINE_VS_SERVICE_BOUNDARY.md`
- `docs/architecture/MOIRA_SERVER_ROUTE_ADMISSION_CHECKLIST.md`
- `docs/architecture/MOIRA_SERVER_PHASE10_LEDGER.md`
- `docs/architecture/P10-04_GALACTIC_COORDINATES_TRANSPORT_DESIGN.md`
- `wiki/02_standards/GALACTIC_BACKEND_STANDARD.md`

---

## 1. Governing Object

The governing object is the Galactic Porphyry house system:

- Galactic Ascendant, Midheaven, Descendant, and IC
- twelve Galactic Porphyry cusps in native galactic longitude
- the same twelve cusps projected into true-of-date ecliptic longitude
- body membership by native galactic longitude
- fractional body progress through a galactic house
- cusp boundary context for a placement

The trisection is performed in the galactic frame. Ecliptic cusps are an
interoperability projection, not the governing trisection frame.

---

## 2. Public Engine Surface

Authoritative module:

- `moira/galactic_houses.py`

Public vessels:

- `GalacticAngles`
- `GalacticHouseCusps`
- `GalacticHousePlacement`
- `GalacticHouseBoundaryProfile`

Public functions:

- `calculate_galactic_houses(jd_ut, latitude, longitude)`
- `assign_galactic_house(galactic_longitude, house_cusps)`
- `body_galactic_house_position(galactic_longitude, house_cusps)`
- `describe_galactic_boundary(placement, near_cusp_threshold=3.0)`

Facade exposure:

- `SpatialFacadeMixin.galactic_houses(...)`

---

## 3. Frame And Input Truth

Chart-backed cusp inputs:

- timezone-aware datetime
- geographic latitude in `[-90, 90]`
- geographic longitude in `[-180, 180]`

Direct placement inputs:

- galactic longitude in degrees
- a complete twelve-cusp galactic-house vessel
- optional near-cusp threshold for boundary profile

Chart-backed placement inputs:

- timezone-aware datetime
- geographic latitude and longitude
- bounded selected bodies
- optional near-cusp threshold

Frame doctrine:

- `cusps_gal` is the native house frame.
- `cusps_ecl` is the ecliptic projection of those same cusps.
- `GalacticAngles` must preserve both galactic and ecliptic angle truth.
- body placement must use galactic longitude against `cusps_gal`.
- chart-backed body placement must derive body galactic longitude through the
  P10-04 galactic coordinate path, not through ad hoc frame conversion.

---

## 4. Result Semantics

`GalacticHouseCusps` preserves:

- twelve ecliptic cusp longitudes
- twelve galactic cusp longitudes
- four angles in both frames
- trisection direction

`GalacticHousePlacement` preserves:

- house number
- normalized galactic longitude
- exact-on-cusp status
- opening cusp longitude

`GalacticHouseBoundaryProfile` preserves:

- opening and closing cusp
- distance to opening cusp
- distance to closing cusp
- house span
- nearest cusp
- nearest cusp distance
- threshold used
- near-cusp flag

---

## 5. Bounded Output Policy

First REST admission may expose:

- chart-backed Galactic Porphyry cusp calculation
- direct placement for one supplied galactic longitude and supplied cusps
- chart-backed body placement for a bounded body list

First REST admission must not expose:

- rendered galactic house charts
- projection-specific drawing helpers
- catalog-wide body or star sweeps
- map products
- alternate galactic house systems
- mutable/global sidereal or coordinate state

Recommended first REST bound:

- maximum chart-backed bodies: `12`

---

## 6. Validation And Evidence

Existing validation:

- `tests/unit/test_galactic_houses.py`
- `tests/unit/test_galactic_houses_public_api.py`

Covered invariants include:

- invalid geographic coordinates are rejected
- non-finite public inputs are rejected
- exact sampled horizon crossings are accepted
- live cusps have twelve galactic and ecliptic longitudes
- house assignment honors midpoint membership
- opening cusps belong to the opening house
- input galactic longitude is normalized
- fractional house position matches membership
- boundary profile reports forward-arc distances
- public facade and package-root names resolve

---

## 7. REST Admission Position

P10-05 Galactic Houses is eligible to move from evaluation to transport design
for bounded synchronous routes.

REST design must preserve:

- native galactic cusp truth
- ecliptic cusp projection truth
- trisection direction
- chart datetime, `jd_ut`, `jd_tt`, latitude, longitude, obliquity, and ARMC
  provenance
- requested and returned body lists for chart-backed placement
- explicit deferred scope for rendered charts, projections, maps, and catalog
  sweeps
