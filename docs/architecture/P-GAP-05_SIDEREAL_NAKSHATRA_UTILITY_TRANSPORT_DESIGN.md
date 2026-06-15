# P-GAP-05 Sidereal And Nakshatra Utility Transport Design

Version: 0.2
Date: 2026-06-14
Status: implemented and admitted
Scope: bounded REST admission plan for mechanical sidereal longitude,
ayanamsa, and Nakshatra lookup primitives

This design follows
`wiki/02_standards/SIDEREAL_NAKSHATRA_UTILITY_BACKEND_STANDARD.md`.

P-GAP-05 evaluates the root/facade surfaces:

- `list_ayanamsa_systems`
- `ayanamsa`
- `tropical_to_sidereal`
- `sidereal_to_tropical`
- `nakshatra_of`
- `all_nakshatras_at`

These routes are utility primitives. They must not duplicate Panchanga,
Muhurta, Dasha, Varga, Manazil, or chart-backed sidereal doctrine.

---

## 1. Route Family

Prefixes:

- `/v1/sidereal`
- `/v1/nakshatra`

Routes:

- `GET /v1/sidereal/ayanamsa-systems`
- `POST /v1/sidereal/ayanamsa`
- `POST /v1/sidereal/convert`
- `POST /v1/nakshatra/position`
- `POST /v1/nakshatra/bulk`

Route naming doctrine:

- `ayanamsa-systems` means registry discovery only.
- `ayanamsa` means one date-specific ayanamsa value.
- `convert` means one longitude converted between tropical and sidereal.
- `nakshatra/position` means one tropical longitude placed into the 27-fold
  Nakshatra taxonomy.
- `nakshatra/bulk` means the same mechanical lookup applied to a bounded map
  of named tropical longitudes.

---

## 2. Request Models

`SiderealAyanamsaRequest`:

- `jd_ut`: float
- `ayanamsa_system`: string, default `Lahiri`
- `mode`: string, default `true`

Validation:

- `jd_ut` must be finite
- `ayanamsa_system` must be one of `Ayanamsa.ALL`
- `mode` must be `true` or `mean`
- extra fields rejected

`SiderealConversionRequest`:

- `longitude_deg`: float
- `jd_ut`: float
- `direction`: `tropical_to_sidereal` or `sidereal_to_tropical`
- `ayanamsa_system`: string, default `Lahiri`
- `mode`: string, default `true`

Validation:

- all numeric values finite
- `direction` must be admitted
- `ayanamsa_system` must be one of `Ayanamsa.ALL`
- `mode` must be `true` or `mean`
- extra fields rejected

`NakshatraPositionRequest`:

- `tropical_longitude_deg`: float
- `jd_ut`: float
- `ayanamsa_system`: string, default `Lahiri`

Validation:

- all numeric values finite
- `ayanamsa_system` must be one of `Ayanamsa.ALL`
- extra fields rejected

`NakshatraBulkRequest`:

- `positions`: mapping of name string to tropical longitude float
- `jd_ut`: float
- `ayanamsa_system`: string, default `Lahiri`

Validation:

- `positions` must be non-empty
- `positions` must contain no more than `64` entries
- every name must be non-empty after trimming
- every longitude must be finite
- `jd_ut` must be finite
- `ayanamsa_system` must be one of `Ayanamsa.ALL`
- extra fields rejected

User-defined ayanamsa payloads are not admitted in Stage 1.

---

## 3. Response Models

`AyanamsaSystemResponse`:

- `system`
- `reference_value_j2000_deg`
- `is_star_anchored`
- `default_mode`
- `supported_modes`

`AyanamsaSystemsEnvelopeResponse`:

- `systems`
- `total`
- `provenance`

`SiderealAyanamsaResponse`:

- `jd_ut`
- `ayanamsa_system`
- `mode`
- `ayanamsa_deg`
- `value_range`: `[0, 360)`
- `provenance`

`SiderealConversionResponse`:

- `direction`
- `jd_ut`
- `ayanamsa_system`
- `mode`
- `input_longitude_deg`
- `output_longitude_deg`
- `ayanamsa_deg`
- `longitude_range`: `[0, 360)`
- `provenance`

`NakshatraPositionResponse`:

- `name`: optional
- `tropical_longitude_deg`
- `jd_ut`
- `ayanamsa_system`
- `nakshatra`
- `nakshatra_index`
- `nakshatra_number`
- `nakshatra_lord`
- `pada`
- `degrees_in`
- `degrees_remaining`
- `sidereal_longitude_deg`

`NakshatraPositionEnvelopeResponse`:

- `request`
- `position`
- `provenance`

`NakshatraBulkEnvelopeResponse`:

- `request`
- `positions`
- `total`
- `provenance`

---

## 4. Service Design

Expected service file:

- `moira_server/services/sidereal.py`

Service functions:

- `list_sidereal_ayanamsa_systems`
- `compute_sidereal_ayanamsa`
- `convert_sidereal_longitude`
- `compute_nakshatra_position`
- `compute_nakshatra_bulk`

Service responsibilities:

- call existing `moira.sidereal` functions
- serialize engine result vessels without altering their meaning
- compute `ayanamsa_deg` once for conversion responses and expose it
- compute `degrees_remaining = NAKSHATRA_SPAN - degrees_in`
- preserve 0-based and 1-based Nakshatra indexing
- attach explicit provenance and stage sequence

The service must not build charts or derive planetary positions. Callers
provide longitude truth directly.

---

## 5. Provenance

Shared provenance fields:

- `source_module`: `moira.sidereal`
- `engine_entrypoint`
- `time_scale`: `UT_JD`
- `product_kind`
- `stage_sequence`

Ayanamsa registry provenance:

- `registry_owner`: `moira.sidereal.Ayanamsa`
- `reference_epoch`: `J2000`
- `user_defined_ayanamsa`: `not_admitted`

Ayanamsa value provenance:

- `ayanamsa_system`
- `ayanamsa_mode`
- `jd_policy`: `caller_supplied_UT_JD`
- `mode_policy`: `true_or_mean_only`
- `star_anchor_policy`: `engine_owned_for_true_star_anchored_systems`

Conversion provenance:

- all ayanamsa value provenance fields
- `longitude_input_policy`: `finite_input_normalized_by_engine_modulo`
- `conversion_direction`

Nakshatra provenance:

- `ayanamsa_system`
- `ayanamsa_mode`: `true`
- `taxonomy`: `twenty_seven_equal_nakshatras`
- `span_deg`: `360 / 27`
- `pada_span_deg`: `(360 / 27) / 4`
- `interpretation`: `not_returned`
- `panchanga_judgement`: `not_returned`

---

## 6. Error Semantics

The routes must reject through the standard `422` validation envelope:

- non-finite JD values
- non-finite longitude values
- unknown ayanamsa names
- empty ayanamsa names
- invalid modes
- invalid conversion directions
- empty Nakshatra bulk maps
- oversized Nakshatra bulk maps
- empty bulk position names
- extra request fields

Star-anchored true ayanamsa fallback behavior remains owned by
`moira.sidereal.ayanamsa`. The REST layer must not repair missing catalog
truth by substituting another ayanamsa system.

---

## 7. Implementation Files

Implemented files:

- `moira_server/models/sidereal.py`
- `moira_server/services/sidereal.py`
- `moira_server/routers/sidereal.py`
- `tests/server/test_server_sidereal_routes.py`

Router registration:

- export router from `moira_server/routers/__init__.py`
- include router in `moira_server/app.py`
- export response/request models from `moira_server/models/__init__.py`

REST reference update:

- route group count increases by `2`
- `/v1` route count increases by `5`
- `sidereal` family row added with three routes
- `nakshatra` family row added with two routes
- route table rows added
- Sidereal And Nakshatra Utility REST Admission Boundary section added

Gap ledger update:

- P-GAP-05 marked `admitted`
- next candidate becomes `P-GAP-06` Harmograms

---

## 8. Verification Requirements

Focused server tests:

- successful ayanamsa systems route
- ayanamsa systems parity with `list_ayanamsa_systems`
- successful ayanamsa value route
- ayanamsa value parity with `ayanamsa`
- successful tropical-to-sidereal conversion route
- successful sidereal-to-tropical conversion route
- conversion route parity with engine functions
- conversion round-trip invariant
- successful Nakshatra position route
- Nakshatra position parity with `nakshatra_of`
- successful Nakshatra bulk route
- Nakshatra bulk parity with `all_nakshatras_at`
- Nakshatra boundary assignment around exact mansion boundary
- invalid ayanamsa rejection
- invalid mode rejection
- invalid direction rejection
- non-finite JD rejection
- non-finite longitude rejection
- empty bulk map rejection
- oversized bulk map rejection
- extra field rejection
- provenance truth for product kind, taxonomy, ayanamsa policy, and
  non-Panchanga boundary
- route registry audit confirming the admitted route set

Implementation verification:

- `python -m py_compile` for new and touched server files
- `python -m pytest tests/server/test_server_sidereal_routes.py -q`
- route registry audit confirming the five designed routes

No new sidereal external-reference validation is required for REST admission.
Existing integration tests remain the authority for the engine's ayanamsa
truth. The route tests prove adapter truth over existing engine functions.

---

## 9. Non-Goals

This design does not admit:

- `/v1/panchanga/*` replacements
- `/v1/muhurta/*` replacements
- Dasha balance or period routes
- chart-backed Moon derivation
- chart-backed sidereal house derivation
- Varga projection
- Manazil routes
- Abhijit Nakshatra
- user-defined ayanamsa REST payloads
- arbitrary fixed-star anchor payloads
- mutable global sidereal mode
- interpretation text or recommendation language
- dense tables or async sweeps
- kernel path mutation

---

## 10. Admission Result

P-GAP-05 is implemented and admitted.

Admitted implementation surface:

- `GET /v1/sidereal/ayanamsa-systems`
- `POST /v1/sidereal/ayanamsa`
- `POST /v1/sidereal/convert`
- `POST /v1/nakshatra/position`
- `POST /v1/nakshatra/bulk`

Verification performed:

- `.venv\Scripts\python.exe -m py_compile moira_server\models\sidereal.py moira_server\services\sidereal.py moira_server\routers\sidereal.py moira_server\app.py moira_server\models\__init__.py moira_server\routers\__init__.py`
- `.venv\Scripts\python.exe -m pytest tests/server/test_server_sidereal_routes.py -q`
- live route registry audit confirmed five P-GAP-05 routes, `337`
  versioned `/v1` routes, and `341` total non-documentation routes
