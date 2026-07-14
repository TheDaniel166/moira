# Gauquelin Backend Standard

Version: 0.2
Date: 2026-07-14
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

The default horizon altitude is `0°`: a geometric center crossing. The primary
sources below establish a wheel beginning at rise, but do not specify a
refraction, limb, or atmospheric convention. Nonzero thresholds are therefore
explicit caller policy, not a hidden historical default.

The primary plus zones are sectors 1-3 after rise and sectors 10-12 after upper
culmination. Gauquelin also reports weaker, echo-like tendencies after setting
and lower culmination, but those opposite regions are not classified as the
primary plus zones by this result contract.

---

## 2. Public Engine Surface

Authoritative module:

- `moira/gauquelin.py`

Public vessels:

- `GauquelinHorizonStatus`
- `GauquelinPosition`

Public functions:

- `gauquelin_sector(body_ra, body_dec, lat, lst, body="", horizon_altitude=0.0, sectors=36)`
- `all_gauquelin_sectors(planet_ra_dec, lat, lst, horizon_altitude=0.0, sectors=36)`

Facade exposure:

- `SpatialFacadeMixin.gauquelin_sectors(...)`

---

## 3. Input Truth

Direct engine inputs:

- apparent right ascension in degrees
- apparent declination in `[-90, 90]`
- geographic latitude in `[-90, 90]`
- local sidereal time in degrees
- explicit horizon altitude in `[-90, 90]` degrees
- positive integer sector count

Chart-backed transport inputs must derive apparent topocentric RA/Dec and local
sidereal time from explicit chart datetime and observer truth. The server must
not accept ecliptic longitude as a substitute for RA/Dec in chart-backed
Gauquelin routes.

---

## 4. Result Semantics

`GauquelinPosition` preserves:

- `body`: caller-supplied body label
- `sector`: one-based sector number for normal rise/set geometry; otherwise
  `None`
- `zone`: `"Plus Zone"` or `"Neutral Zone"` for normal canonical 36-sector
  output; `None` for undefined sectors or custom sector counts
- `diurnal_position`: normalized position in `[0, 360)` for normal rise/set
  geometry; otherwise `None`
- `sectors`: the sector resolution used
- `degree_in_sector`: offset in `[0, sector width)` inside the numbered sector;
  otherwise `None`
- `is_plus_zone`: true only for canonical plus-zone sectors
- `horizon_status`: `normal`, `circumpolar`, `never_rises`, or
  `horizon_coincident`

REST transport must preserve `horizon_status`. Circumpolar, never-rising, and
horizon-coincident states are valid degenerate astronomical states, not input
validation errors. They do not receive a fabricated sector, zone, diurnal
position, or degree-in-sector value.

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
- primary plus-zone sectors are exactly 1-3 and 10-12
- custom engine sector counts are unzoned
- exact boundaries belong to the following half-open sector and have a zero
  degree offset
- horizon altitude changes the diurnal semi-arc
- the default horizon is geometric and custom horizon altitude is bounded
- circumpolar, never-rising, and horizon-coincident states remain explicit and
  leave sector-derived quantities undefined
- exact-pole classification respects the requested horizon altitude
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

---

## 8. Primary Source Basis And Limits

The sector order and primary-zone classification are grounded in:

- Michel Gauquelin, *Cosmic Influences on Human Behavior* (1973), pp. 43-55:
  the 36-sector wheel begins at rise; sectors 1-3 follow rise and sectors 10-12
  follow upper culmination; setting and lower-culmination effects are described
  as weaker echoes.
- Michel Gauquelin, *Birth-Times: A Scientific Investigation of the Secrets of
  Astrology* (1983 English edition), pp. 22, 31-32, and 40: numbering begins at
  rise in the direction of diurnal motion, and the figures distinguish the two
  primary plus zones from the weaker opposite regions.
- Michel Gauquelin, *Le dossier des influences cosmiques* (1973), pp. 48-57:
  the French account independently describes the 36-sector wheel numbered from
  the body's rise and the concentrations after horizon and meridian passage.

These general works do not document the specialized numerical demarcation,
refraction convention, or a sector assignment for bodies without ordinary
rising and setting. Moira therefore uses explicit geometric doctrine and
invariant tests for those questions and does not attribute them to Gauquelin.

The broader primary-source map, C.U.R.A. licensing boundary, posthumous rights
uncertainty, and openly licensed corpus alternative are recorded in
`wiki/05_research/gauquelin_cura_source_inventory_2026-07-14.md`. No C.U.R.A.
version 6 or Open Gauquelin database rows are admitted by this standard.
