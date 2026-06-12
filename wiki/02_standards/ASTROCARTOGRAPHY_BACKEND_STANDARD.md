# Astrocartography Backend Standard

Version: 0.1
Date: 2026-06-11
Status: Active backend admission packet for Phase 10 REST evaluation
Scope: `moira.astrocartography`

This standard records the backend truth that may be exposed by the REST server
for P10-01 Astrocartography. It is not a map-rendering standard and does not
admit dense grid, contour, or tiled map products.

It is downstream of:

- `wiki/00_foundations/ENGINE_VS_SERVICE_BOUNDARY.md`
- `docs/architecture/MOIRA_SERVER_ROUTE_ADMISSION_CHECKLIST.md`
- `docs/architecture/MOIRA_SERVER_PHASE10_LEDGER.md`
- `wiki/03_validation/VALIDATION_EXPERIMENTAL.md`

---

## 1. Governing Object

The governing object is the Astro*Carto*Graphy geographic line family for one
chart epoch:

- MC meridian
- IC meridian
- Ascendant sampled curve
- Descendant sampled curve
- subplanetary zenith point
- subplanetary nadir point

These are geographic products on Earth. They are not chart aspects, house
cusps, map projections, or rendered graphics.

---

## 2. Public Engine Surface

Authoritative module:

- `moira/astrocartography.py`

Public vessels:

- `ACGLine`
- `SubPlanetaryPoint`

Public functions:

- `acg_lines(planet_ra_dec, gmst_deg, lat_step=2.0, jd_ut=None, refraction=False)`
- `acg_from_chart(chart, bodies=None, lat_step=2.0, refraction=False)`
- `subplanetary_points(planet_ra_dec, gmst_deg)`
- `subplanetary_from_chart(chart, bodies=None)`

Facade exposure:

- `SpatialFacadeMixin.astrocartography(...)`
- `SpatialFacadeMixin.subplanetary_points(...)`

---

## 3. Frame And Input Truth

Direct low-level inputs:

- body name
- apparent geocentric right ascension in degrees
- apparent geocentric declination in degrees
- Greenwich apparent sidereal time in degrees
- optional Julian Day for lunar topocentric handling
- optional latitude sampling step
- optional refraction flag

Chart-backed inputs:

- `ChartContext`
- optional selected bodies
- optional latitude sampling step
- optional refraction flag

Frame doctrine:

- RA/Dec are apparent geocentric equatorial coordinates of date unless the
  caller explicitly owns another direct-input source.
- `gmst_deg` is Greenwich apparent sidereal time in degrees.
- MC/IC line longitudes are geographic longitudes.
- ASC/DSC points are sampled `(latitude, longitude)` geographic pairs.
- Subplanetary point latitude is WGS-84 geodetic latitude derived from the
  geocentric declination.
- Subplanetary point longitude is wrapped to `[-180, 180)`.

---

## 4. Result Semantics

`ACGLine` preserves:

- `planet`
- `line_type`
- `longitude`
- `points`

Line-type invariants:

- `MC` and `IC` lines use `longitude` and have no sampled `points`.
- `ASC` and `DSC` lines use sampled `points` and have no single `longitude`.
- One body yields four ACG lines.

`SubPlanetaryPoint` preserves:

- `planet`
- `point_type`
- `latitude`
- `longitude`

Point-type invariants:

- one body yields one `Zenith` point and one `Nadir` point
- nadir latitude is the negative of zenith latitude
- nadir longitude is antipodal to zenith longitude

---

## 5. Bounded Output Policy

First REST admission may expose:

- bounded ACG line products
- bounded subplanetary point products

First REST admission must not expose:

- dense map grids
- rendered maps
- tiled map products
- contour extraction
- unbounded body catalogs
- fixed-star all-catalog ACG sweeps

Sampling policy:

- `lat_step` must be finite and in `(0, 178]`.
- REST transport should use a stricter operational default and maximum body
  count before admission.
- ASC/DSC sampling is a line approximation, not a rendered cartographic path.

---

## 6. Validation And Evidence

Existing validation:

- `tests/unit/test_astrocartography.py`
- `tests/unit/test_session_fixes.py`
- `wiki/03_validation/VALIDATION_EXPERIMENTAL.md`

Covered invariants include:

- four line vessels per body
- MC/IC antipodal meridian behavior
- zero-declination ASC/DSC meridian behavior
- high-declination circumpolar latitude skipping
- ASC/DSC symmetry around the MC meridian
- WGS-84 geodetic latitude conversion for subplanetary points
- chart wrapper delegation to apparent sidereal time and sky-position truth
- small-body subplanetary points through the admitted `planet_at` surface
- rejection of invalid sampling and non-finite coordinate inputs

---

## 7. REST Admission Position

P10-01 Astrocartography is eligible to move from evaluation to transport design
for bounded line and subplanetary products.

REST design must still decide:

- direct RA/Dec route shape
- chart-backed route shape
- maximum body count
- REST `lat_step` bounds
- response provenance fields
- whether small bodies are admitted in first transport or constrained to
  chart-contained bodies only

Do not admit dense grid or map-rendering routes as part of first P10-01
transport.
