# Gauquelin Backend Standard

Version: 0.1
Date: 2026-06-12
Status: Active backend admission packet for Phase 10 REST evaluation
Scope: `moira.gauquelin`

This standard records the backend truth that may be exposed by the REST server
for P10-06 Gauquelin Sectors. It is a diurnal-sector and horizon-status
standard, not a rendered chart, statistical research, or map-product standard.

It is downstream of:

- `wiki/00_foundations/ENGINE_VS_SERVICE_BOUNDARY.md`
- `docs/architecture/MOIRA_SERVER_ROUTE_ADMISSION_CHECKLIST.md`
- `docs/architecture/MOIRA_SERVER_PHASE10_LEDGER.md`

---

## 1. Governing Object

The governing object is the Gauquelin diurnal sector position:

- apparent right ascension and declination of a body
- observer geographic latitude
- local sidereal time
- effective horizon altitude
- normalized diurnal position
- sector number
- canonical plus-zone classification
- explicit horizon status

The canonical Gauquelin system is the 36-sector form. Moira's engine also
supports caller-selected sector counts, but canonical plus-zone doctrine exists
only when `sectors == 36`.

---

## 2. Public Engine Surface

Authoritative module:

- `moira/gauquelin.py`

Public vessels:

- `GauquelinHorizonStatus`
- `GauquelinPosition`

Public functions:

- `gauquelin_sector(body_ra, body_dec, lat, lst, body="", horizon_altitude=-0.5667, sectors=36)`
- `all_gauquelin_sectors(planet_ra_dec, lat, lst, horizon_altitude=-0.5667, sectors=36)`

Facade exposure:

- `SpatialFacadeMixin.gauquelin_sectors(...)`

---

## 3. Input Truth

Direct engine inputs:

- apparent right ascension in degrees
- apparent declination in `[-90, 90]`
- geographic latitude in `[-90, 90]`
- local sidereal time in degrees
- effective horizon altitude in degrees
- positive integer sector count

Chart-backed transport inputs must derive apparent topocentric RA/Dec and local
sidereal time from explicit chart datetime and observer truth. The server must
not accept ecliptic longitude as a substitute for RA/Dec in chart-backed
Gauquelin routes.

---

## 4. Result Semantics

`GauquelinPosition` preserves:

- `body`: caller-supplied body label
- `sector`: one-based sector number
- `zone`: `"Plus Zone"` or `"Neutral Zone"` for canonical 36-sector output;
  `None` for custom sector counts
- `diurnal_position`: normalized position in `[0, 360)`
- `sectors`: the sector resolution used
- `degree_in_sector`: offset inside the numbered sector
- `is_plus_zone`: true only for canonical plus-zone sectors
- `horizon_status`: `normal`, `circumpolar`, or `never_rises`

REST transport must preserve `horizon_status`. Circumpolar and never-rising
states are valid degenerate astronomical states, not validation errors.

---

## 5. Bounded Output Policy

First REST admission may expose:

- one direct canonical 36-sector placement for supplied RA/Dec/LST
- bounded direct canonical 36-sector placements for supplied body RA/Dec map
- bounded chart-backed canonical 36-sector placements for selected chart bodies

First REST admission must not expose:

- custom sector counts as public REST policy
- rendered Gauquelin wheels or charts
- map products
- statistical research workflows
- catalog-wide body, asteroid, or fixed-star sweeps
- mutable/global observer or sidereal state

Recommended first REST bound:

- maximum direct bodies: `24`
- maximum chart bodies: `12`

---

## 6. Validation And Evidence

Existing validation:

- `tests/unit/test_experimental_validation.py`
- `tests/unit/test_session_fixes.py`
- `tests/unit/test_gauquelin.py`
- `tests/integration/test_gauquelin_external_reference.py`

Covered invariants include:

- sector is in the valid one-based range
- canonical plus-zone sectors are exactly 1-3, 10-12, 19-21, and 28-30
- custom engine sector counts are unzoned
- horizon altitude changes the diurnal semi-arc
- circumpolar and never-rising states remain explicit
- near-polar and extreme-declination cases do not produce NaN output
- non-finite and out-of-range public inputs are rejected
- cached external-reference rows corroborate the apparent topocentric
  RA/Dec/LST route to Gauquelin sector placement

---

## 7. REST Admission Position

P10-06 Gauquelin Sectors is eligible to move from evaluation to transport
design for bounded synchronous routes.

REST design must preserve:

- apparent RA/Dec/LST truth
- observer latitude
- effective horizon altitude
- canonical 36-sector plus-zone semantics
- explicit horizon status
- requested and returned body lists for bounded multi-body products
- chart datetime, normalized UTC datetime, `jd_ut`, `jd_tt`, and local
  sidereal time provenance for chart-backed products

Custom sector counts remain an engine capability, but should wait for a later
REST design because public plus-zone semantics are canonical 36-sector
semantics.
