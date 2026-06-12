# Galactic Backend Standard

Version: 0.1
Date: 2026-06-12
Status: Active backend admission packet for Phase 10 REST evaluation
Scope: `moira.galactic`

This standard records the backend truth that may be exposed by the REST server
for P10-04 Galactic Coordinates. It is a coordinate-frame standard, not a
galactic-houses standard and not a rendered sky-map or catalog-sweep standard.

It is downstream of:

- `wiki/00_foundations/ENGINE_VS_SERVICE_BOUNDARY.md`
- `docs/architecture/MOIRA_SERVER_ROUTE_ADMISSION_CHECKLIST.md`
- `docs/architecture/MOIRA_SERVER_PHASE10_LEDGER.md`
- `wiki/03_validation/VALIDATION_EXPERIMENTAL.md`

---

## 1. Governing Object

The governing object is the IAU galactic coordinate frame and its lawful
bridges to Moira's ecliptic and equatorial coordinate strata:

- direct equatorial J2000/ICRS to galactic longitude/latitude
- direct galactic longitude/latitude to equatorial J2000/ICRS
- true-of-date ecliptic longitude/latitude to galactic longitude/latitude
- galactic longitude/latitude to true-of-date ecliptic longitude/latitude
- named galactic reference points expressed in true-of-date ecliptic
  coordinates
- chart-body galactic positions derived from chart ecliptic coordinates

The galactic frame is not a zodiac, not a house system, and not an observer
horizon product. It is a celestial coordinate frame.

---

## 2. Public Engine Surface

Authoritative module:

- `moira/galactic.py`

Re-export module:

- `moira/sky/galactic.py`

REST authority:

- `moira.galactic`

`moira.sky.galactic` is a compatibility/re-export surface. It does not replace
the owning backend module for REST admission.

Public vessel:

- `GalacticPosition`

Public functions:

- `equatorial_to_galactic(ra, dec)`
- `galactic_to_equatorial(l, b)`
- `ecliptic_to_galactic(lon, lat, obliquity, jd_tt)`
- `galactic_to_ecliptic(l, b, obliquity, jd_tt)`
- `galactic_position_of(body, ecliptic_lon, ecliptic_lat, obliquity, jd_tt)`
- `all_galactic_positions(body_data, obliquity, jd_tt)`
- `galactic_reference_points(obliquity, jd_tt)`

---

## 3. Frame Doctrine

Direct equatorial inputs:

- `ra` is right ascension in degrees.
- `dec` is declination in degrees.
- The frame is J2000/ICRS.
- No epoch conversion is performed by `equatorial_to_galactic`.

Direct galactic inputs:

- `l` is galactic longitude in degrees.
- `b` is galactic latitude in degrees.
- The frame is IAU galactic, using the Liu, Zhu & Zhang (2011) J2000/ICRS
  rotation constants.

Ecliptic bridge inputs:

- ecliptic longitude and latitude are true-of-date coordinates.
- `obliquity` is the true obliquity for the epoch of date.
- `jd_tt` is the TT Julian Day needed for the precession/nutation bridge.
- The bridge converts true-of-date ecliptic coordinates through true-of-date
  equatorial coordinates, then into J2000/ICRS before applying the galactic
  rotation matrix.

Reference-point outputs:

- named galactic landmarks are stored from their J2000/ICRS equatorial
  definitions and returned as true-of-date ecliptic coordinates for the
  supplied `obliquity` and `jd_tt`.

---

## 4. Result Semantics

`GalacticPosition` preserves:

- `body`
- `lon`: galactic longitude in `[0, 360)`
- `lat`: galactic latitude in `[-90, 90]`
- `ecliptic_lon`: source true-of-date ecliptic longitude
- `ecliptic_lat`: source true-of-date ecliptic latitude

Derived proximity fields:

- `near_galactic_plane`
- `galactic_hemisphere`
- `angular_distance_to_gc`
- `angular_distance_to_anticenter`

These proximity fields are convenience properties on the vessel. They do not
change the governing coordinate-frame computation.

---

## 5. Bounded Output Policy

First REST admission may expose:

- raw equatorial to galactic transform
- raw galactic to equatorial transform
- raw ecliptic to galactic transform
- raw galactic to ecliptic transform
- galactic reference points for one epoch
- chart-backed galactic positions for a bounded body list

First REST admission must not expose:

- galactic houses
- rendered sky maps
- browser projection helpers
- catalog-wide star or body sweeps
- proper-motion star catalog products
- observer-local horizon products
- dense grid products

Galactic Houses must remain a separate P10-05 admission family because it
derives a house system from the galactic frame rather than merely exposing the
frame itself.

---

## 6. Validation And Evidence

Existing validation:

- `tests/unit/test_experimental_validation.py`
- `tests/unit/test_galactic.py`
- `tests/integration/test_galactic_oracle_reference.py`
- `wiki/03_validation/VALIDATION_EXPERIMENTAL.md`

Covered invariants include:

- Galactic Center maps near `(l=0, b=0)`.
- North Galactic Pole maps near `b=+90`.
- equatorial and galactic transforms round trip.
- ecliptic bridge round trips at J2000.
- reference points return the five named landmarks.
- direct transforms match Astropy/ERFA oracle comparisons within the recorded
  validation threshold.
- public entry points reject non-finite inputs and impossible latitude or
  declination values.

---

## 7. REST Admission Position

P10-04 Galactic Coordinates is eligible to move from evaluation to transport
design for a bounded synchronous route family.

REST design must preserve:

- explicit source and target frame labels
- `jd_tt` and obliquity provenance for ecliptic bridge products
- chart-backed datetime normalization provenance
- requested and returned body lists
- stage sequence truth

No `/v1/galactic/*` route should be admitted without preserving this frame
doctrine in request models, response models, service provenance, and route
tests.
