# Geodetic Backend Standard

Version: 0.1
Date: 2026-06-12
Status: Active backend admission packet for Phase 10 REST evaluation
Scope: `moira.geodetic`

This standard records the backend truth that may be exposed by the REST server
for P10-03 Geodetic. It is not a map-rendering standard and does not admit
geographic search, projection, or relocation synthesis products.

It is downstream of:

- `wiki/00_foundations/ENGINE_VS_SERVICE_BOUNDARY.md`
- `docs/architecture/MOIRA_SERVER_ROUTE_ADMISSION_CHECKLIST.md`
- `docs/architecture/MOIRA_SERVER_PHASE10_LEDGER.md`
- `wiki/03_validation/VALIDATION_EXPERIMENTAL.md`

---

## 1. Governing Object

The governing object is the geodetic zodiac mapping for a terrestrial
location:

- geographic longitude maps to native Geodetic MC
- geographic latitude plus obliquity derives the Geodetic Ascendant
- tropical and sidereal zodiac policies are explicit
- planet ecliptic longitudes may be inverted into geographic equivalent
  longitudes

These are geodetic astrology products. They are not map projections, rendered
maps, local-space horizon products, Astrocartography lines, or relocation chart
synthesis.

---

## 2. Public Engine Surface

Authoritative module:

- `moira/geodetic.py`

Public vessel:

- `GeodeticChart`

Public functions:

- `geodetic_mc(geo_longitude, ayanamsa_deg=0.0)`
- `geodetic_asc(geo_longitude, geo_latitude, obliquity, ayanamsa_deg=0.0)`
- `geodetic_chart(geo_longitude, geo_latitude, obliquity, ayanamsa_deg=0.0, zodiac="tropical")`
- `geodetic_chart_from_chart(chart, zodiac="tropical", ayanamsa_system=None)`
- `geodetic_equivalents(planet_longitudes, ayanamsa_deg=0.0)`
- `geodetic_equivalents_from_chart(chart, bodies=None, zodiac="tropical", ayanamsa_system=None)`

Facade exposure:

- `SpatialFacadeMixin.geodetic(...)`
- `SpatialFacadeMixin.geodetic_planet_equivalents(...)`

---

## 3. Frame And Input Truth

Direct chart inputs:

- geographic longitude
- geographic latitude
- true obliquity of the ecliptic
- zodiac policy: `tropical` or `sidereal`
- ayanamsa offset in degrees for sidereal policy

Chart-backed chart inputs:

- datetime
- geographic latitude
- geographic longitude
- zodiac policy
- ayanamsa system when zodiac is `sidereal`

Direct equivalent inputs:

- body name
- ecliptic longitude in degrees
- ayanamsa offset in degrees when direct input is sidereal

Chart-backed equivalent inputs:

- datetime
- geographic latitude and longitude for chart construction
- optional selected bodies
- zodiac policy
- ayanamsa system when zodiac is `sidereal`

Frame doctrine:

- tropical Geodetic MC is geographic longitude modulo 360.
- sidereal Geodetic MC is `(geographic longitude - ayanamsa) mod 360`.
- geodetic equivalents invert MC mapping and return geographic longitudes in
  `[-180, 180]`.
- chart-backed sidereal policy must resolve and serialize the ayanamsa system
  and ayanamsa offset.
- chart-backed obliquity must be derived from the chart epoch.

---

## 4. Result Semantics

`GeodeticChart` preserves:

- `geo_latitude`
- `geo_longitude`
- `mc`
- `asc`
- `obliquity`
- `zodiac`
- `ayanamsa_deg`

Result invariants:

- `mc` is in `[0, 360)`.
- `asc` is in `[0, 360)`.
- stored geographic longitude is wrapped to `[-180, 180]`.
- `zodiac` is either `tropical` or `sidereal`.
- `ayanamsa_deg` is `0.0` for tropical unless a caller deliberately supplies a
  direct nonzero offset.

---

## 5. Bounded Output Policy

First REST admission may expose:

- direct geodetic location charts
- chart-backed geodetic location charts
- direct geodetic equivalent longitudes
- chart-backed geodetic equivalent longitudes

First REST admission must not expose:

- primitive-only MC routes
- primitive-only ASC routes
- rendered maps
- projection products
- geographic search
- relocation synthesis
- unbounded body catalogs

REST transport should bound chart-backed body count before admission.

---

## 6. Validation And Evidence

Existing validation:

- `tests/unit/test_geodetic.py`

Covered invariants include:

- direct MC wrapping
- sidereal MC and ayanamsa round trip
- ASC range and equatorial cases
- GeodeticChart vessel integrity
- geodetic equivalent inversion
- sidereal equivalent wrapping
- rejection of non-finite coordinates, obliquity, ayanamsa, invalid zodiac,
  empty body names, and non-finite equivalent longitudes

---

## 7. REST Admission Position

P10-03 Geodetic is eligible to move from evaluation to transport design for
bounded location-chart and equivalent-longitude products.

REST design must still decide:

- direct and chart-backed route shapes
- zodiac policy schema
- ayanamsa policy serialization
- whether primitive MC/ASC helpers are public routes or internal only
- maximum chart-backed body count

Do not admit rendered map, projection, geographic search, relocation synthesis,
or primitive-helper-only routes as part of first P10-03 transport.
