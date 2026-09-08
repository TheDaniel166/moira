# Galactic Backend Standard

Version: 0.2
Date: 2026-09-08
Status: Active backend and typed-reference admission standard
Scope: `moira.galactic`, `moira.cosmic_references`

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
- the legacy five-entry galactic reference-point table expressed in
  true-of-date ecliptic coordinates
- a typed cosmic-reference registry whose physical objects, coordinate-frame
  landmarks, and declared proxies remain semantically distinct
- chart-body galactic positions derived from chart ecliptic coordinates

The galactic frame is not a zodiac, not a house system, and not an observer
horizon product. It is a celestial coordinate frame.

---

## 2. Public Engine Surface

Authoritative module:

- `moira/galactic.py`
- `moira/cosmic_references.py`

Re-export module:

- `moira/sky/galactic.py`

REST authority:

- `moira.galactic`

`moira.sky.galactic` is a compatibility/re-export surface. It does not replace
the owning backend module for REST admission.

Public vessel:

- `GalacticPosition`
- `CosmicReferenceDefinition`
- `CosmicReferencePosition`

Public reference kind:

- `CosmicReferenceKind.PHYSICAL_OBJECT`
- `CosmicReferenceKind.COORDINATE_LANDMARK`
- `CosmicReferenceKind.PROXY_REFERENCE`

Public functions:

- `equatorial_to_galactic(ra, dec)`
- `galactic_to_equatorial(l, b)`
- `ecliptic_to_galactic(lon, lat, obliquity, jd_tt)`
- `galactic_to_ecliptic(l, b, obliquity, jd_tt)`
- `galactic_position_of(body, ecliptic_lon, ecliptic_lat, obliquity, jd_tt)`
- `all_galactic_positions(body_data, obliquity, jd_tt)`
- `galactic_reference_points(obliquity, jd_tt)`
- `cosmic_reference_definition(name)`
- `cosmic_reference_at(name, jd_tt)`
- `all_cosmic_references_at(jd_tt, kind=None)`
- `list_cosmic_references(kind=None)`

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

- `galactic_reference_points` is the frozen five-entry compatibility surface.
  Its historical `Super-Galactic Center` key means the astrological M87
  convention; it is not the formal supergalactic longitude origin or a unique
  Virgo/Local Supercluster barycenter.
- typed cosmic references are stored as ICRS/J2000 directions and projected by
  `icrf_to_true_ecliptic(jd_tt)` into the true ecliptic of date.
- every typed result retains its semantic kind, selected anchor, coordinate and
  semantic authorities, source version, citation URLs, and registry version.

### 3.1 Typed Reference Identity Doctrine

Registry version `2026.09.08.1` contains exactly 12 references:

- 2 physical objects: Sagittarius A* and M87 Galaxy
- 7 coordinate landmarks: galactic origin, anti-center, and two poles; formal
  supergalactic longitude origin and two poles
- 3 proxies: Virgo/M87 Astrological SGC, Great Attractor / Norma Cluster Proxy,
  and Shapley Concentration / ACO 3558 Proxy

The formal Galactic Center frame origin and Sagittarius A* are distinct
records. The formal supergalactic longitude origin, M87 Galaxy, and the
Virgo/M87 astrological SGC are also distinct records even where two selected
directions coincide.

Great Attractor and Shapley are extended, model-dependent regions. Their
entries therefore name the selected cluster catalog center and must not be
presented as a uniquely measured point center. A Local Group barycenter is not
admitted because no membership and mass model is declared.

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

`CosmicReferenceDefinition` preserves:

- stable reference identity, canonical name, and exact aliases
- semantic kind and anchor description
- source ICRS right ascension/declination and J2000 TT epoch
- position semantics, coordinate authority, and semantic authority
- source version, citation URLs, and registry version

`CosmicReferencePosition` adds the true-ecliptic-of-date longitude, latitude,
zodiac sign fields, and requested TT epoch without flattening the definition.

---

## 5. Bounded Output Policy

First REST admission may expose:

- raw equatorial to galactic transform
- raw galactic to equatorial transform
- raw ecliptic to galactic transform
- raw galactic to ecliptic transform
- galactic reference points for one epoch
- typed cosmic reference points for one epoch, optionally filtered by semantic
  kind
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
- the legacy five-point route and keys remain unchanged.
- the typed registry returns exactly 2 physical objects, 7 coordinate
  landmarks, and 3 declared proxies with non-null source and semantic receipts.
- formal supergalactic origin and pole directions match Astropy's
  `Supergalactic` frame within 0.1 arcsecond.
- galactic and supergalactic antipodes remain geometrically opposite.
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
- requested semantic kind, returned count, and typed-reference catalog version
- stage sequence truth

`POST /v1/galactic/cosmic-reference-points` accepts a finite `jd_tt` and an
optional `physical_object`, `coordinate_landmark`, or `proxy_reference` kind.
It is a bounded 12-record synchronous operation. It does not perform an
unbounded catalog search, invent structural barycenters, or reinterpret the
legacy five-point endpoint.

No `/v1/galactic/*` route should be admitted without preserving this frame
doctrine in request models, response models, service provenance, and route
tests.
