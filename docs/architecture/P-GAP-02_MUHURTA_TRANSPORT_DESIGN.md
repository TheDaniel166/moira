# P-GAP-02 Muhurta Transport Design

Version: 0.1
Date: 2026-06-14
Status: implemented and admitted
Scope: bounded REST admission plan for Vedic Muhurta moment classification and score

This design follows `wiki/02_standards/MUHURTA_BACKEND_STANDARD.md`.

P-GAP-02 evaluates the root-exported Muhurta surfaces:

- `classify_muhurta`
- `score_muhurta`
- `MuhurtaPolicy`
- `MuhurtaClassification`
- `MuhurtaScore`

This is a Vedic Panchanga-derived doctrine surface. It is not part of the
Phase 13 `/v1/electional/*` search infrastructure and must not inherit Western
electional judgement, arbitrary predicate, or recommendation semantics.

---

## 1. Implementation Gate

Implementation completed after minor engine hardening:

- `classify_muhurta` reads the live Nakshatra vessel field
  `panchanga.nakshatra.nakshatra`, not only a nonexistent `.name` field.
- tests prove that Nakshatra classification can affect classification and
  score output.
- `use_classical_ashubha_yoga` is omitted from transport because the engine
  does not yet honor it.

---

## 2. Route Family

Prefix:

- `/v1/muhurta`

Routes:

- `POST /v1/muhurta/direct/classification`
- `POST /v1/muhurta/direct/score`
- `POST /v1/muhurta/chart/classification`
- `POST /v1/muhurta/chart/score`

Route naming doctrine:

- `direct` means the caller supplies Sun/Moon tropical longitude and JD, as in
  `/v1/panchanga/instant`.
- `chart` means the server derives Sun/Moon through `Moira.chart`, as in
  `/v1/panchanga/chart`.
- `classification` returns labels and reasons only.
- `score` returns raw engine score, breakdown, and classification.

---

## 3. Request Models

`MuhurtaPolicyRequest`:

- `weight_tithi`: float, default `1.0`
- `weight_vara`: float, default `1.0`
- `weight_nakshatra`: float, default `1.0`
- `weight_yoga`: float, default `1.5`
- `weight_karana`: float, default `0.8`

Validation:

- all weights must be finite
- all weights must be greater than or equal to `0.0`

Not admitted in Stage 1:

- `use_classical_ashubha_yoga`
- `janma_nakshatra`
- activity selectors

`MuhurtaDirectRequest`:

- `sun_tropical_lon`: float
- `moon_tropical_lon`: float
- `jd`: float
- `ayanamsa_system`: string, default `Lahiri`
- `panchanga_policy`: optional `PanchangaPolicyRequest`
- `muhurta_policy`: optional `MuhurtaPolicyRequest`

Validation:

- longitudes and JD must be finite
- ayanamsa must be non-empty and accepted by the Panchanga path

`MuhurtaChartRequest`:

- `dt`: timezone-aware datetime
- `observer_lat`: optional float in `[-90, 90]`
- `observer_lon`: optional float in `[-180, 180]`
- `observer_elev_m`: float, default `0.0`
- `ayanamsa_system`: string, default `Lahiri`
- `panchanga_policy`: optional `PanchangaPolicyRequest`
- `muhurta_policy`: optional `MuhurtaPolicyRequest`

Validation:

- reject naive datetime
- observer latitude and longitude must be supplied together
- observer fields must be finite
- ayanamsa must be non-empty and accepted by the Panchanga path

---

## 4. Response Models

`MuhurtaClassificationResponse`:

- `overall`
- `tithi`
- `vara`
- `nakshatra`
- `yoga`
- `karana`
- `reasons`

Each classification label is one of:

- `auspicious`
- `neutral`
- `inauspicious`

`MuhurtaScoreResponse`:

- `total`
- `breakdown`
- `classification`
- `score_scale`: `engine_raw_unbounded`
- `score_direction`: `higher_is_more_favorable_under_policy`

`MuhurtaEnvelopeResponse`:

- `request`
- `panchanga`
- `policy`
- `classification`
- `score`, only for score routes
- `provenance`

The `panchanga` block should reuse the existing `PanchangaResultResponse`
shape so clients can inspect the source limbs.

---

## 5. Service Design

Expected service file:

- `moira_server/services/muhurta.py`

Service functions:

- `compute_muhurta_direct_classification`
- `compute_muhurta_direct_score`
- `compute_muhurta_chart_classification`
- `compute_muhurta_chart_score`

Direct routes should reuse:

- `compute_panchanga_direct`

Chart-backed routes should reuse:

- `compute_panchanga_chart`

Then the service should call:

- `classify_muhurta`
- `score_muhurta`

No route should synthesize a `PanchangaResult` by ad hoc local structures.

---

## 6. Provenance

Every response includes:

- `source_module`: `moira.muhurta`
- `engine_entrypoint`: `classify_muhurta` or `score_muhurta`
- `panchanga_source`: `direct_inputs` or `chart_backed`
- `panchanga_module`: `moira.panchanga`
- `chart_construction`: `not_used` or `Moira.chart`
- `reader_owner`: `not_used` or `Moira engine instance`
- `western_electional_doctrine`: `not_admitted`
- `search_semantics`: `not_admitted`
- `activity_guidance`: `not_admitted`
- `score_scale`: `not_applicable` or `engine_raw_unbounded`
- `stage_sequence`

Stage sequences:

Classification:

- `input_validation`
- `panchanga_derivation`
- `muhurta_policy_binding`
- `muhurta_classification`
- `response_serialization`

Score:

- `input_validation`
- `panchanga_derivation`
- `muhurta_policy_binding`
- `muhurta_classification`
- `muhurta_scoring`
- `response_serialization`

---

## 7. Error Semantics

The routes must reject through the standard `422` validation envelope:

- naive datetimes
- non-finite direct inputs
- empty ayanamsa
- invalid ayanamsa propagated from the Panchanga path
- partial observer context
- non-finite observer values
- negative or non-finite policy weights
- extra request fields

Kernel absence for chart-backed routes should use the existing server error
envelope for missing ephemeris/kernel resources. The route must not repair
that by mutating kernel paths.

---

## 8. Implementation Files

Implemented files:

- `moira_server/models/muhurta.py`
- `moira_server/services/muhurta.py`
- `moira_server/routers/muhurta.py`
- `tests/server/test_server_muhurta_routes.py`

Router registration:

- router is exported from `moira_server/routers/__init__.py`
- router is included in `moira_server/app.py`

REST reference update:

- route family count increased by `4`
- `/v1` route count increased by `4`
- `muhurta` family row added
- four route table rows added
- Muhurta REST Admission Boundary section added

Gap ledger update:

- P-GAP-02 is marked `admitted` after engine hardening, implementation,
  tests, route registry audit, and REST reference update.

---

## 9. Verification Requirements

Engine hardening tests before route implementation:

- a Nakshatra vessel with an Uttama Nakshatra can classify as auspicious
- a Nakshatra vessel with a Gandanta Nakshatra can classify as inauspicious
- score breakdown changes when Nakshatra classification changes
- exposed policy fields match honored engine behavior

Focused server tests:

- direct classification route success
- direct score route success
- chart-backed classification route success
- chart-backed score route success
- direct response parity with `classify_muhurta`
- direct response parity with `score_muhurta`
- chart-backed response parity through the existing Panchanga service
- naive datetime rejection
- partial observer rejection
- non-finite direct input rejection
- invalid policy weight rejection
- invalid ayanamsa rejection
- provenance truth separating Muhurta from Western electional
- route registry audit confirming four new `/v1/muhurta/*` routes

---

## 10. Non-Goals

This design does not admit:

- `/v1/muhurta/windows`
- `/v1/muhurta/best`
- `/v1/muhurta/recommend`
- activity-specific guidance routes
- Abhijit Muhurta routes
- Brahma Muhurta routes
- Tara Bala / Janma Nakshatra inputs
- Western electional doctrine
- arbitrary predicates or scorers
- async search jobs
- dense Muhurta calendars

---

## 11. Admission Result

P-GAP-02 is admitted through:

- `POST /v1/muhurta/direct/classification`
- `POST /v1/muhurta/direct/score`
- `POST /v1/muhurta/chart/classification`
- `POST /v1/muhurta/chart/score`

Recommended status:

- `admitted`
