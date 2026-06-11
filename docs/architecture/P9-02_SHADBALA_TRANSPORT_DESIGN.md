# P9-02 Shadbala Transport Design

Version: 1.0
Date: 2026-06-11
Status: P9-02 admitted; four chart-backed Shadbala routes live and tested
Scope: Phase 9 Shadbala REST admission design

This document declares the REST route shapes admitted for Shadbala and records
the implemented model, serializer, service, router, and verification state.

It is downstream of:

- `docs/architecture/MOIRA_SERVER_BOUNDARY.md`
- `docs/architecture/MOIRA_SERVER_ROUTE_ADMISSION_CHECKLIST.md`
- `docs/architecture/MOIRA_SERVER_PHASE9_LEDGER.md`
- `wiki/02_standards/SHADBALA_BACKEND_STANDARD.md`

The governing engine object is sixfold Vedic planetary strength:

- Sthana Bala
- Dig Bala
- Kala Bala
- Chesta Bala
- Naisargika Bala
- Drig Bala

The authoritative engine function is `moira.shadbala.shadbala(...)`.

---

## 1. Route Family

Router prefix:

- `/v1/shadbala`

Route tag:

- `shadbala`

This family is live. The admitted paths are recorded in
`wiki/02_services/REST_API_REFERENCE.md`.

---

## 2. Initial Route Shapes

### 2.1 Chart-Backed Shadbala Result

Route:

- `POST /v1/shadbala/chart`

Transport stance:

- `bounded_sync`

Purpose:

- Compute full Shadbala from a timezone-aware chart request, deriving the
  required astronomical and Panchanga inputs through Moira instead of trusting a
  caller-supplied bundle of cross-dependent values.

Required input doctrine:

- timezone-aware datetime
- observer latitude
- observer longitude
- optional observer elevation
- house system
- ayanamsa or explicit Shadbala policy
- optional hora policy

Engine path:

1. Build a planet `Chart` through the stable injected `Moira` instance for the
   seven classical planets.
2. Build houses through the same injected `Moira` instance.
3. Convert chart tropical longitudes to sidereal longitudes with
   `tropical_to_sidereal(..., system=ayanamsa_system)`.
4. Extract signed daily speeds from the planet vessels.
5. Extract geocentric latitudes where available for Graha Yuddha resolution.
6. Call `panchanga_at(...)` from the same chart Sun/Moon tropical longitudes
   and `chart.jd_ut` to obtain `tithi_number` and `vara_lord`.
7. Derive day/night state with `is_day_chart(sun_tropical_lon, houses.asc)`.
8. Resolve `hora_lord` only when the request explicitly supplies it. No hidden
   sunrise lookup is performed.
9. Call `shadbala(...)`.
10. Call `validate_shadbala_output(...)` before serialization.

Truth boundary:

- The server owns the chart derivation path for longitudes, speeds, houses,
  day/night state, Panchanga support values, and yuddha latitude data.
- The route must not silently accept caller-supplied sidereal longitudes or
  speeds; that belongs to a later direct expert route if admitted.
- Hora strength must remain visibly policy-bound because `hora_lord_at(...)`
  requires sunrise JD and is not derivable from datetime alone.

Response:

- Full `ShadbalaResult`.
- Component strengths must remain visible; the response must not collapse the
  result into only `total_rupas`, sufficiency, or rankings.

### 2.2 Chart-Backed Shadbala Chart Profile

Route:

- `POST /v1/shadbala/chart/profile`

Transport stance:

- `bounded_sync`

Purpose:

- Compute the aggregate chart-level Shadbala profile from server-derived chart
  truth.

Engine path:

1. Follow the same chart-backed derivation path as `/v1/shadbala/chart`.
2. Call `shadbala_chart_profile(result)`.

Response:

- `ShadbalaChartProfile` only.
- The full component result is not silently bundled into the profile response.

### 2.3 Chart-Backed Shadbala Network Profile

Route:

- `POST /v1/shadbala/chart/network`

Transport stance:

- `bounded_sync`

Purpose:

- Compute the strength ranking and Graha Yuddha network profile from
  server-derived chart truth.

Engine path:

1. Follow the same chart-backed derivation path as `/v1/shadbala/chart`.
2. Call `graha_yuddha_pairs(sidereal_longitudes, planet_latitudes)`.
3. Call `shadbala_network_profile(result, wars)`.

Response:

- `ShadbalaNetworkProfile` only.
- Active wars, victors, and losers must be preserved as structured data.

### 2.4 Chart-Backed Shadbala Condition Profile

Route:

- `POST /v1/shadbala/chart/condition`

Transport stance:

- `bounded_sync`

Purpose:

- Compute the local Shadbala condition profile for one classical planet from a
  server-derived chart result.

Required additional input:

- `planet`: one of Sun, Moon, Mars, Mercury, Jupiter, Venus, Saturn

Engine path:

1. Follow the same chart-backed derivation path as `/v1/shadbala/chart`.
2. Select the requested planet from `result.planets`.
3. Call `shadbala_condition_profile(planet_result)`.

Response:

- `ShadbalaConditionProfile` only.

---

## 3. Deferred Direct Expert Surface

The following route is intentionally not part of first admission:

- `POST /v1/shadbala/direct`

Reason:

- `shadbala(...)` requires a coherent bundle of sidereal longitudes, signed
  planetary speeds, house cusps, JD, Tithi, Vara lord, day/night state,
  ayanamsa policy, optional hora lord, and optional planet latitudes.
- Allowing clients to supply that bundle before a strict consistency contract
  exists would expose a surface where individually valid fields can still form
  an astronomically incoherent chart.

Direct admission can be reconsidered after the chart-backed route is live and
the request contract can prove at least:

- all seven classical planets are present in both longitudes and speeds
- JD is finite and matches the stated support values
- house cusps are structurally complete
- tithi and vara fields are either recomputed by the service or explicitly
  marked as caller-owned support truth
- day/night state is explicitly caller-owned and not recomputed silently
- ayanamsa and sidereal input provenance are visible

---

## 4. Required Response Semantics

The Shadbala result response must preserve:

- `jd`
- `ayanamsa_system`
- `planets`

Each planet result must preserve:

- `planet`
- `sthana_bala`
- `dig_bala`
- `kala_bala`
- `chesta_bala`
- `naisargika_bala`
- `drig_bala`
- `total_shashtiamsas`
- `total_rupas`
- `required_rupas`
- `strength_ratio`
- `is_sufficient`

`sthana_bala` must preserve:

- `uchcha`
- `saptavargaja`
- `ojayugma`
- `kendradi`
- `drekkana`
- `total`

`kala_bala` must preserve:

- `nathonnatha`
- `paksha`
- `tribhaga`
- `abda_masa_vara_hora`
- `ayana`
- `yuddha`
- `total`

The chart profile response must preserve:

- `sufficient_count`
- `insufficient_count`
- `strongest_planet`
- `weakest_planet`
- `planet_tiers`
- `strength_ratios`
- `ayanamsa_system`

The network profile response must preserve:

- `ayanamsa_system`
- `strength_ranking`
- `dominant_planet`
- `recessive_planet`
- `active_wars`
- `war_victors`
- `war_losers`

Each Graha Yuddha record must preserve:

- `victor`
- `loser`
- `separation_deg`

The condition profile response must preserve:

- `planet`
- `tier`
- `total_rupas`
- `required_rupas`
- `strength_ratio`
- `is_sufficient`

---

## 5. Explicit Non-Goals For First Admission

Do not include in the first Shadbala REST increment:

- generic `/v1/vedic` catch-all transport
- direct caller-supplied Shadbala input bundles
- textual chart interpretation
- hidden sunrise lookup for hora lord
- sunrise-corrected local calendrical day rollover unless admitted as explicit
  policy
- route-triggered kernel, ayanamsa, or global state mutation
- flattened score-only output

If a later route computes sunrise-derived hora lord, it must expose that policy
plainly because it changes Kala Bala.

---

## 6. Transport Models

Model file:

- `moira_server/models/shadbala.py`

Declared request models:

- `ShadbalaPolicyRequest`
- `ShadbalaChartRequest`
- `ShadbalaConditionChartRequest`

Declared response models:

- `SthanaBalaResponse`
- `KalaBalaResponse`
- `GrahaYuddhaResponse`
- `PlanetShadbalaResponse`
- `ShadbalaResultResponse`
- `ShadbalaConditionProfileResponse`
- `ShadbalaChartProfileResponse`
- `ShadbalaNetworkProfileResponse`

Model validation must reject:

- naive datetimes
- non-finite observer inputs
- out-of-range observer latitude or longitude
- missing observer latitude or longitude
- empty ayanamsa fields
- unsupported planet names on `/chart/condition`
- ambiguous hora policy values

The chart request should require observer latitude and longitude. Shadbala
depends on house and horizon truth; unlike the instantaneous Panchanga route,
there is no location-free chart-backed Shadbala.

---

## 7. Verification Requirements For Admission

Before these routes can be marked live:

- chart route parity against `engine.chart(...)`, `panchanga_at(...)`,
  `tropical_to_sidereal(...)`, and `shadbala(...)`
- profile route parity against `shadbala_chart_profile(...)`
- network route parity against `graha_yuddha_pairs(...)` plus
  `shadbala_network_profile(...)`
- condition route parity against `shadbala_condition_profile(...)`
- serializer proof that Sthana Bala and Kala Bala components are not flattened
- serializer proof that Graha Yuddha records preserve victor/loser truth
- validator proof that `validate_shadbala_output(...)` is called on the base
  result path
- adversarial rejection for naive datetimes
- adversarial rejection for non-finite observer inputs
- adversarial rejection for missing observer latitude or longitude
- adversarial rejection for invalid ayanamsa or policy values
- adversarial rejection for invalid condition-profile planets
- boundary test proving no request path calls kernel lifecycle mutators
- route registration check proving all admitted paths are present

These checks are implemented in:

- `tests/server/test_server_shadbala_service.py`
- `tests/server/test_server_shadbala_routes.py`

The live REST reference has been updated only after those checks were added.

---

## 8. Serializer And Service Adapter Status

Serializer file:

- `moira_server/serializers/shadbala.py`

Service file:

- `moira_server/services/shadbala.py`

Declared serializer helpers:

- `serialize_sthana_bala`
- `serialize_kala_bala`
- `serialize_graha_yuddha`
- `serialize_planet_shadbala`
- `serialize_shadbala_result`
- `serialize_shadbala_condition_profile`
- `serialize_shadbala_chart_profile`
- `serialize_shadbala_network_profile`

Declared service helpers:

- `compute_shadbala_chart`
- `compute_shadbala_chart_profile`
- `compute_shadbala_chart_network`
- `compute_shadbala_chart_condition`

The service adapter must keep the derivation scaffold explicit. In particular,
it should materialize intermediate support truth in named local variables:

- chart
- tropical longitudes
- sidereal longitudes
- speeds
- latitudes
- Panchanga support result
- tithi number
- vara lord
- day/night state
- optional hora lord
- yuddha pairs

This is a protected doctrine surface. Do not collapse those stages into an
opaque helper that hides how Shadbala support truth is assembled.
