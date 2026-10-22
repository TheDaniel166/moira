# Geodetic Backend Standard

Version: 0.4
Date: 2026-10-22
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
- caller-supplied geographic latitude plus obliquity derives the Geodetic
  Ascendant; latitude is passed through unchanged with no inferred datum or
  geodetic/geocentric conversion
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
- `geodetic_chart(geo_longitude, geo_latitude, obliquity, ayanamsa_deg=None, zodiac="tropical")`
- `geodetic_chart_from_chart(chart, zodiac="tropical", ayanamsa_system=None)`
- `geodetic_equivalents(planet_longitudes, ayanamsa_deg=0.0)`
- `geodetic_equivalents_from_chart(chart, bodies=None, zodiac="tropical", ayanamsa_system=None)`

Facade exposure:

- `SpatialFacadeMixin.geodetic(...)`
- `SpatialFacadeMixin.geodetic_planet_equivalents(...)`

Both wrappers read `jd_ut`, `jd_tt`, `latitude`, `longitude` and `planets`, so
their argument is a `moira.chart.ChartContext` (as returned by
`Moira.relocated_chart(...)`). The lighter `moira.facade.Chart` returned by
`Moira.chart(...)` carries only `jd_ut` — which there denotes the civil UTC
input, not UT1 — and is not an accepted vessel for these wrappers.

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
- the ARMC for a location is derived from its tropical Geodetic MC; the
  sidereal Ascendant is the tropical rising Ascendant reduced by the same
  ayanamsa: `(tropical_asc - ayanamsa) mod 360`.
- the rising horizon root is selected by local hour angle, not by comparing
  ecliptic longitude with right ascension. With `H = ARMC - RA`, altitude's
  vertical rate under increasing local sidereal time has the sign of
  `-sin(H)` at non-polar latitudes; the Ascendant is the root with positive
  rate (`sin(H) < 0`).
- at exactly either geographic pole, the rising-rate branch is undefined; the
  shared low-level helper retains its principal-root tie for callers that need
  a deterministic algebraic result. Public geodetic chart functions refuse a
  margin of `1e-6` degrees around the poles.
- the tropical lane carries no ayanamsa: neither a direct offset nor a named
  system may accompany `zodiac = tropical`.
- the sidereal lane must name its displacement: `ayanamsa_deg` for direct
  requests (including an explicit `0.0` when intended), `ayanamsa_system` for
  chart-backed requests. An omitted direct offset is not treated as zero.
- an ayanamsa is resolved on the UT scale and obliquity on the TT scale. A
  vessel's TT must never be handed to `moira.sidereal.ayanamsa`, which performs
  its own UT→TT step; the duplicate shift grows with Delta-T and crosses the
  1e-6 degree longitude covenant at historical epochs.
- a geographic meridian is zodiac-independent, so every lane returns the same
  geographic anchor. `geodetic_equivalents` reads a nonzero ayanamsa as "these
  input longitudes are sidereal", so a chart vessel holding tropical positions
  must be converted into the sidereal lane before inversion, not inverted with
  the ayanamsa applied twice.
- geodetic equivalents invert MC mapping and return geographic longitudes in
  `[-180, 180]`.
- chart-backed sidereal policy must resolve and serialize the ayanamsa system
  and ayanamsa offset.
- chart-backed obliquity must be derived from the chart epoch.
- latitude is the caller-supplied geographic latitude, north-positive, passed
  unchanged into the Ascendant geometry. The engine does not infer a geodetic,
  geocentric, or astronomical source convention, datum, or conversion.
- Earth obliquity must be finite and in `[22, 25]` degrees, a guarded envelope
  around [NASA's reported 22.1–24.5° range](https://science.nasa.gov/science-research/earth-science/climate-science/milankovitch-orbital-cycles-and-their-role-in-earths-climate/)
  over the last million years; this is an input plausibility guard, not a claim
  about the epoch-validity span of the IAU 2006 P03 model. Chart-backed
  obliquity is produced by the engine's TT model.

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
- `provenance` (direct-input lane or chart epochs/model identities)

Result invariants:

- `mc` is in `[0, 360)`.
- `asc` is in `[0, 360)`.
- stored geographic longitude is wrapped to `[-180, 180]`.
- `zodiac` is either `tropical` or `sidereal`.
- `ayanamsa_deg` is `0.0` exactly when `zodiac` is `tropical`. A tropical
  request carrying an ayanamsa is refused, never silently honoured or dropped.
- transport has a true absent state, so presence is the declaration: supplying
  `ayanamsa_deg` or `ayanamsa_system` on a tropical request is refused even
  when the value is `0.0`.
- public vessel construction enforces finite coordinates and angles, the
  declared polar refusal margin, normalized stored longitude, zodiac policy,
  and chart-provenance consistency.
- chart-backed vessel provenance records the chart Julian Days, TT obliquity
  model identities, and sidereal ayanamsa system/UT lane when used. Direct
  calculations identify the caller-supplied input lane without implying an
  epoch or model.

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
- rising-root selection across the full non-polar latitude range, including
  near-polar cases
- sidereal ASC and MC use the same explicitly declared offset from the
  zodiac-independent tropical meridian
- direct sidereal chart requests reject an omitted offset while accepting an
  explicit zero
- GeodeticChart vessel integrity
- geodetic equivalent inversion
- sidereal equivalent wrapping
- rejection of non-finite coordinates, obliquity, ayanamsa, invalid zodiac,
  empty body names, and non-finite equivalent longitudes
- rejection of Earth obliquity outside the guarded `[22, 25]` degree envelope
- an independent horizon-equation root search agrees with the engine's
  Ascendant across hemispheres, longitude wrap, and near-polar samples
- direct `GeodeticChart` construction enforces its structural invariants
- chart-backed result provenance retains the exact chart Julian Days, obliquity
  model identities, and named sidereal ayanamsa lane
- rejection of latitudes within the declared polar margin of |90|, where the
  horizon no longer defines a rising ecliptic degree
- rejection of an ayanamsa offset or system carried on a tropical zodiac, at
  every engine entry point and at REST admission, plus the service-layer
  refusal when transport validation is bypassed
- chart-backed wrappers resolving ayanamsa on the UT scale while obliquity
  stays on the TT scale, with the Delta-T materiality bound recorded
- geographic-equivalent inversion returning one anchor for both zodiac lanes

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
