# P9-10 Alternate Dashas Transport Design

Version: 0.1
Date: 2026-06-11
Status: P9-10 admitted; five direct-compute and four chart-backed alternate dasha routes live and tested
Scope: Phase 9 alternate dasha REST admission design

This document declares the REST route shapes admitted for alternate Vedic dasha
systems implemented in `moira.dasha_systems` and records the implemented
transport admission state.

It is downstream of:

- `docs/architecture/MOIRA_SERVER_BOUNDARY.md`
- `docs/architecture/MOIRA_SERVER_ROUTE_ADMISSION_CHECKLIST.md`
- `docs/architecture/MOIRA_SERVER_PHASE9_LEDGER.md`
- `wiki/02_standards/ALTERNATE_DASHAS_BACKEND_STANDARD.md`

The governing engine object is alternate Vedic time-lord sequence truth:

- Ashtottari Mahadasha and sub-period sequences
- Yogini Mahadasha and sub-period sequences
- explicit year-basis policy
- explicit ayanamsa policy for Moon nakshatra conversion
- period-level profile truth
- sequence-level aggregate profile truth

The authoritative engine functions are:

- `moira.dasha_systems.ashtottari(...)`
- `moira.dasha_systems.yogini_dasha(...)`
- `moira.dasha_systems.alternate_period_profile(...)`
- `moira.dasha_systems.alternate_sequence_profile(...)`
- `moira.dasha_systems.validate_alternate_dasha_output(...)`

---

## 1. Route Family

Router prefix:

- `/v1/dasha/alternate`

Route tag:

- `alternate-dashas`

Reason:

- Existing Vimshottari routes live under `/v1/dasha/vimshottari/*`.
- P9-10 should remain visibly part of the broader dasha timing surface without
  pretending that Ashtottari and Yogini are Vimshottari variants.
- A generic `/v1/vedic` route is not admitted.

---

## 2. Initial Transport Stance

The first admission is direct computation.

Required base inputs:

- `moon_tropical_lon`
- `natal_jd`
- `levels`
- explicit policy object

The server does not derive the natal Moon from datetime/location in this first
admission.

Allowed `levels`:

- Transport should accept `1` through `4`, matching the engine's effective
  clamp range for alternate dashas.

Longitude/JD validation:

- `moon_tropical_lon` must be finite.
- `natal_jd` must be finite.
- The engine may normalize the Moon longitude for nakshatra computation.

---

## 3. Policy Models

### 3.1 Shared Year Basis

Transport must accept only the year-basis labels admitted by the engine:

- `julian_365.25`
- `savana_360`
- `tropical_365.2422`
- `sidereal_365.2564`

### 3.2 Ashtottari Policy

Fields:

- `year_basis`, default `julian_365.25`
- `ayanamsa_system`, default `Lahiri`
- `bypass_eligibility`, default `true` for first REST admission
- `lagna_sign_index`, optional integer in `[0, 11]`

Transport doctrine:

- First admission should default `bypass_eligibility` to `true` because the
  engine does not yet implement full Rahu/Lagna eligibility checking.
- If a request sets `bypass_eligibility=false` with `lagna_sign_index`, the
  service should expose the current engine rejection honestly through the
  validation envelope.
- If a request sets `bypass_eligibility=false` without `lagna_sign_index`, the
  engine currently proceeds because no eligibility check can be evaluated.
  Transport may allow this but must not claim the eligibility doctrine was
  checked.

### 3.3 Yogini Policy

Fields:

- `year_basis`, default `julian_365.25`
- `ayanamsa_system`, default `Lahiri`

Yogini has no eligibility condition in the current engine.

---

## 4. Initial Route Shapes

### 4.1 Ashtottari Sequence

Route:

- `POST /v1/dasha/alternate/ashtottari/sequence`

Transport stance:

- `direct_compute`

Purpose:

- Resolve the full Ashtottari sequence from caller-supplied natal Moon tropical
  longitude, natal JD, levels, and Ashtottari policy.

Engine path:

1. Validate finite Moon longitude and natal JD.
2. Validate levels in `[1, 4]`.
3. Build `AshtottariPolicy`.
4. Call `ashtottari(moon_tropical_lon, natal_jd, levels, policy)`.
5. Call `validate_alternate_dasha_output(periods)` on the returned Mahadashas.
6. Serialize periods recursively.

Response:

- `system`
- `periods`
- `mahadasha_count`
- `levels_generated`
- resolved policy fields

### 4.2 Ashtottari Profile

Route:

- `POST /v1/dasha/alternate/ashtottari/profile`

Transport stance:

- `direct_compute`

Purpose:

- Resolve the Ashtottari sequence and aggregate profile in one call.

Engine path:

1. Compute the Ashtottari sequence using the same path as sequence route.
2. Call `alternate_sequence_profile(periods)`.
3. Serialize the source sequence and profile truth.

Response:

- source sequence response
- `system`
- `total_years`
- `mahadasha_count`
- period profiles

### 4.3 Yogini Sequence

Route:

- `POST /v1/dasha/alternate/yogini/sequence`

Transport stance:

- `direct_compute`

Purpose:

- Resolve the full Yogini sequence from caller-supplied natal Moon tropical
  longitude, natal JD, levels, and Yogini policy.

Engine path:

1. Validate finite Moon longitude and natal JD.
2. Validate levels in `[1, 4]`.
3. Build `YoginiPolicy`.
4. Call `yogini_dasha(moon_tropical_lon, natal_jd, levels, policy)`.
5. Call `validate_alternate_dasha_output(periods)` on the returned Mahadashas.
6. Serialize periods recursively.

Response:

- `system`
- `periods`
- `mahadasha_count`
- `levels_generated`
- resolved policy fields

### 4.4 Yogini Profile

Route:

- `POST /v1/dasha/alternate/yogini/profile`

Transport stance:

- `direct_compute`

Purpose:

- Resolve the Yogini sequence and aggregate profile in one call.

Engine path:

1. Compute the Yogini sequence using the same path as sequence route.
2. Call `alternate_sequence_profile(periods)`.
3. Serialize the source sequence and profile truth.

Response:

- source sequence response
- `system`
- `total_years`
- `mahadasha_count`
- period profiles

### 4.5 Period Profile

Route:

- `POST /v1/dasha/alternate/period-profile`

Transport stance:

- `projection`

Purpose:

- Build an `AlternatePeriodProfile` from a caller-supplied
  `AlternateDashaPeriod` transport vessel.

Reason for admitting this route:

- The engine exposes period-profile projection as a public surface independent
  of sequence computation.
- It lets API clients profile a period they already hold without recomputing a
  full sequence.

Required input:

- full alternate period vessel:
  - `system`
  - `level`
  - `lord`
  - `start_jd`
  - `end_jd`
  - optional recursive `sub`

Response:

- `system`
- `level`
- `lord`
- `planet`
- `years`
- `is_node_lord`
- `is_luminary_lord`

---

## 5. Response Semantics

`AlternateDashaPeriod` responses must preserve:

- `system`
- `level`
- `lord`
- `start_jd`
- `end_jd`
- `years`
- `is_terminal`
- recursive `sub`

`AlternatePeriodProfile` responses must preserve:

- `system`
- `level`
- `lord`
- `planet`
- `years`
- `is_node_lord`
- `is_luminary_lord`

`AlternateDashaSequenceProfile` responses must preserve:

- `system`
- `total_years`
- `mahadasha_count`
- `profiles`

Sequence/profile route responses must also preserve policy provenance:

- `year_basis`
- `ayanamsa_system`
- Ashtottari eligibility fields where applicable

---

## 6. Chart-Backed Surface

Chart-backed alternate-dasha routes are admitted after the post-Phase-9 shared
`SiderealChartContext` workflow.

Live shapes:

- `POST /v1/dasha/alternate/ashtottari/chart/sequence`
- `POST /v1/dasha/alternate/ashtottari/chart/profile`
- `POST /v1/dasha/alternate/yogini/chart/sequence`
- `POST /v1/dasha/alternate/yogini/chart/profile`

Reason:

- `moira.dasha_systems` consumes Moon tropical longitude and natal JD.
- Chart-backed routes use the server adapter to own birth chart derivation,
  Moon extraction, and policy provenance clearly.

Implementation:

- Responses expose the derived Moon tropical longitude and natal JD because
  those are the actual dasha engine inputs.
- Responses also embed compact sidereal chart provenance from the shared
  adapter.
- Direct-vs-chart parity is verified in
  `tests/server/test_server_alternate_dashas_routes.py`.

---

## 7. Explicit Non-Goals

The first P9-10 admission does not expose:

- Kalachakra Dasha
- Chara Dasha
- Vimshottari routes; those already exist under `/v1/dasha/vimshottari/*`
- full Ashtottari Rahu/Lagna eligibility implementation
- interpretive prediction text
- generic `/v1/vedic` umbrella routes

---

## 8. Verification Requirements For Admission

Implementation must verify:

- Ashtottari sequence route preserves system, lords, levels, timings, recursive
  sub-periods, and policy provenance.
- Yogini sequence route preserves system, lords, levels, timings, recursive
  sub-periods, and policy provenance.
- Profile routes preserve source sequence truth and aggregate profile truth.
- Period-profile route preserves derived planet, node flag, luminary flag, and
  duration.
- Non-finite Moon longitude is rejected.
- Non-finite natal JD is rejected.
- Invalid year basis is rejected.
- Empty ayanamsa label is rejected.
- Invalid levels are rejected by transport validation.
- Invalid period-profile vessels are rejected.
- Ashtottari `bypass_eligibility=false` with `lagna_sign_index` maps the
  engine rejection honestly.
- Route registration appears in startup route inventory.

Verification files to add:

- `tests/server/test_server_alternate_dashas_routes.py`

Existing engine verification slice:

- `tests/unit/test_dasha_systems.py`
- `tests/unit/test_public_doctrine_surfaces.py`
- `tests/unit/test_api_surface_adversarial_audit.py`

---

## 9. Admission State

P9-10 is admitted.

Implemented files:

- `moira_server/models/alternate_dashas.py`
- `moira_server/serializers/alternate_dashas.py`
- `moira_server/services/alternate_dashas.py`
- `moira_server/routers/alternate_dashas.py`
- route registration in `moira_server/app.py`
- package `__init__.py` exports for models, serializers, services, and routers
- `tests/server/test_server_alternate_dashas_routes.py`
- `wiki/02_services/REST_API_REFERENCE.md` route inventory updates
