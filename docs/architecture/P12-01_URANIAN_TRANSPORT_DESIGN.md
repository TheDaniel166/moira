# P12-01 Uranian Transport Design

Version: 0.3
Date: 2026-09-27
Status: admitted and repaired
Scope: Uranian / Hamburg School hypothetical-body REST contract

## 1. Route Boundary

P12-01 exposes:

- `GET /v1/uranian/catalog`
- `POST /v1/uranian/position`
- `POST /v1/uranian/bulk`

The routes expose nine conventional hypothetical orbits: the Hamburg eight
and the separately sourced Transpluto model. They do not expose physical
planet ephemerides, discovered TNOs, fixed stars, asteroids, midpoint trees,
dial interpretation, or cosmobiology networks.

## 2. Governing Object

One position record contains:

- canonical, case-sensitive name
- apparent geocentric true-ecliptic-of-date longitude and latitude
- geocentric distance in AU
- signed longitude speed and derived retrograde state
- zodiac sign fields
- source family, body group, model, and frame identifiers

The computation advances source orbital elements through Kepler's equation,
materializes a heliocentric ICRF vector, and passes it through Moira's
kernel-bound Earth/Sun and apparent-place reduction. The bound DE kernel is
used only for real observer geometry; it does not contain the hypothetical
body.

## 3. Requests

`GET /v1/uranian/catalog` has no body.

`POST /v1/uranian/position` requires:

- `name`: one canonical body name
- `jd_ut`: finite Julian Day UT1

`POST /v1/uranian/bulk` requires `jd_ut` and accepts an optional unique list
of one through nine canonical `names`. Omission requests all nine in engine
order.

## 4. Responses

Catalog responses contain `names`, `count`, `model`, `frame`, `epoch`, and
`provenance`.

Single and bulk position records contain:

- `name`, `longitude`, `latitude`, and `distance_au`
- `sign`, `sign_symbol`, and `sign_degree`
- `speed` and `retrograde`
- `body_group` and `source_family`
- `model`, `frame`, and `body_kind = "hypothetical_body"`

## 5. Validation Rules

The route family rejects non-finite dates, empty or unknown names, duplicates,
oversized name lists, and non-list bulk names. It preserves canonical casing
and never substitutes a physical body or arbitrary small body.

The catalog route is kernel-free. Position and bulk routes inject the
startup-created `Moira` engine and pass its reader explicitly, so request
handling cannot silently depend on ambient global kernel state.

## 6. Provenance

Every response preserves:

- `source_module = "moira.uranian"`
- the actual engine entry point
- `body_kind = "hypothetical_body"`
- `school = "Hamburg_Uranian_plus_Transpluto"`
- `model = "fixed_keplerian_orbit_apparent_geocentric"`
- `frame = "apparent_geocentric_true_ecliptic_of_date"`
- `epoch = "per_body_source_epoch"`
- `physical_ephemeris = "DE_kernel_for_Earth_and_Sun_observer_geometry_only"`
- an explicit stage sequence

`spk_kernel_used` is `false` for catalog metadata and `true` for computed
positions. The note explicitly rejects physical-body and discovered-TNO
interpretations.

## 7. Verification Contract

The focused acceptance slice is:

```powershell
$env:MOIRA_TEST_MODE = "1"
$env:MOIRA_STRICT_KNOWN_ISSUES = "1"
$env:MOIRA_NO_DOWNLOAD = "1"
.\.venv\Scripts\python.exe -m pytest tests\unit\test_uranian.py tests\oracle\test_uranian_oracle.py tests\server\test_server_uranian_routes.py tests\unit\test_facade_clock_boundaries.py -q
```

The protected oracle artifact covers all nine bodies at five dates from 1900
through 2026 and compares longitude, latitude, distance, signed speed, and
retrograde state with official Astrodienst `swetest` output. It is labelled
cross-engine corroboration, not physical authority.

## 8. Completion Boundary

P12-01 remains bounded to catalog, single-position, and bulk-position
transport. It does not admit topocentric or sidereal variants, midpoint or
dial structures, interpretive text, physical-body substitution, or any claim
that the hypothetical orbits are JPL/NAIF states.
