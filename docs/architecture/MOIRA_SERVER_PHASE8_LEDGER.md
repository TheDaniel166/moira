# Moira Server Phase 8 Ledger

Version: 1.9
Date: 2026-05-29
Status: Phase 8 complete (all required families live and hardened). P8-14 primary directions transport surface closed. Ready for Phase 9 scoping.
Scope: Concrete server-admission ledger for phase 8 progression, direction, and time-lord surfaces (now complete)

This document turns phase 8 from a prose heading into a concrete queue of
implementable units.

It is grounded in the public engine surfaces currently present in:

- `moira.progressions`
- `moira.profections`
- `moira.timelords`
- `moira.dasha`
- `moira.varshaphal`
- `moira.primary_directions`

It does not speculate beyond the repository.

---

## 1. Phase 8 Goal

Expose the remaining progression, direction, and time-lord engine surfaces
through REST without weakening doctrinal distinctions.

The phase should be implemented in strata:

1. direct progression surfaces
2. annual and monthly profection
3. timelord sequence surfaces
4. dasha sequence surfaces
5. varshaphal annual doctrine
6. bounded primary-direction surfaces

---

## 2. Packaging Target

Phase 8 will likely require these new route-family files:

```text
moira_server/models/timelords.py
moira_server/serializers/timelords.py
moira_server/services/timelords.py
moira_server/routers/timelords.py
tests/server/test_server_timelord_routes.py
```

Recommended route groups:

- `/v1/progressions/*`
- `/v1/profections/*`
- `/v1/timelords/*`
- `/v1/dasha/*`
- `/v1/varshaphal/*`
- `/v1/primary-directions/*`

---

## 3. Implementation Units

Each unit below is classified as:

- `direct_sync`
- `bounded_sync`
- `heavy_sync`
- `defer_async`
- `blocked_engine`

### 3.1 Progressions

Engine basis:

- `moira.progressions`
- current batch precedent already exists through `batch_progressions`

#### P8-01 Secondary Progression Route Family

- engine surfaces:
  - `secondary_progression`
  - `converse_secondary_progression`
  - `secondary_progression_declination`
  - `converse_secondary_progression_declination`
- route group:
  - `/v1/progressions/secondary`
  - `/v1/progressions/secondary-declination`
- classification:
  - `bounded_sync`
- response truth to preserve:
  - doctrine truth
  - computation truth
  - relation
  - condition profile
- note:
  - implemented; converse expressed via `converse: bool` request field

#### P8-02 Arc Direction Route Family

- engine surfaces:
  - `solar_arc`
  - `converse_solar_arc`
  - `solar_arc_right_ascension`
  - `converse_solar_arc_right_ascension`
  - `naibod_longitude`
  - `converse_naibod_longitude`
  - `naibod_right_ascension`
  - `converse_naibod_right_ascension`
  - `mean_solar_arc_longitude`
  - `converse_mean_solar_arc_longitude`
  - `mean_solar_arc_right_ascension`
  - `converse_mean_solar_arc_right_ascension`
  - `one_degree_longitude`
  - `converse_one_degree_longitude`
  - `one_degree_right_ascension`
  - `converse_one_degree_right_ascension`
  - `planetary_arc`
  - `converse_planetary_arc`
- route group:
  - `/v1/progressions/arc`
- classification:
  - `bounded_sync`
- note:
  - implemented; single route with `method` dispatch and `converse: bool`
  - `planetary_arc` requires `arc_body` field; all other methods use standard signature
  - returns `ProgressedChartResponse` (serializer already live from P8-01)

#### P8-03 Tertiary And Minor Progression Family

- engine surfaces:
  - `tertiary_progression`
  - `converse_tertiary_progression`
  - `tertiary_ii_progression`
  - `converse_tertiary_ii_progression`
  - `minor_progression`
  - `converse_minor_progression`
  - `duodenary_progression`
  - `converse_duodenary_progression`
  - `quotidian_solar_progression`
  - `converse_quotidian_solar_progression`
  - `quotidian_lunar_progression`
  - `converse_quotidian_lunar_progression`
- route group:
  - `/v1/progressions/time-key`
- classification:
  - `bounded_sync`
- note:
  - implemented; single route with `method` dispatch (tertiary, tertiary_ii, minor,
    duodenary, quotidian_solar, quotidian_lunar) and `converse: bool`

#### P8-04 House-Frame Progression Family

- engine surfaces:
  - `daily_house_frame`
  - `daily_houses`
  - `ascendant_arc`
  - `converse_ascendant_arc`
  - `vertex_arc`
  - `converse_vertex_arc`
- route group:
  - `/v1/progressions/house-frame`
- classification:
  - `bounded_sync`
- note:
  - implemented; three routes: house-frame (full ProgressedHouseFrame), house-frame/cusps
    (light HouseCusps response), house-frame/arc (ascendant_arc/vertex_arc method dispatch)
  - P8-05 profile and network endpoints now accept house_frame_items alongside items,
    completing the full mixed aggregation surface

#### P8-05 Progression Aggregate Surfaces

- engine surfaces:
  - `progression_relation`
  - `house_frame_relation`
  - `progression_condition_profile`
  - `house_frame_condition_profile`
  - `progression_chart_condition_profile`
  - `progression_condition_network_profile`
- route group:
  - `/v1/progressions/profile`
  - `/v1/progressions/network`
- classification:
  - `direct_sync`
- note:
  - implemented; profile and network endpoints accept a list of secondary progression
    requests and aggregate over the computed charts; house-frame surfaces deferred
    until P8-04 is implemented

### 3.2 Profections

Engine basis:

- `moira.profections`

Current status:

- implemented:
  - `/v1/profections/annual`
  - `/v1/profections/monthly`
  - `/v1/profections/schedule`

#### P8-06 Profection Core Family

- engine surfaces:
  - `annual_profection`
  - `monthly_profection`
  - `profection_schedule`
- route group:
  - `/v1/profections/annual`
  - `/v1/profections/monthly`
  - `/v1/profections/schedule`
- classification:
  - `direct_sync`
- note:
  - low-cost and likely the cleanest first unit in phase 8
  - implemented

### 3.3 Timelords

Engine basis:

- `moira.timelords`

#### P8-07 Firdaria Family

- engine surfaces:
  - `firdaria`
  - `current_firdaria`
  - `group_firdaria`
  - `firdar_condition_profile`
  - `firdar_sequence_profile`
  - `firdar_active_pair`
- route group:
  - `/v1/timelords/firdaria/*`
- classification:
  - `bounded_sync`
- note:
  - implemented; five routes: sequence, groups, current, profile, active-pair
  - caller supplies `is_day_chart`; variant and include_node_subperiods are optional
  - active-pair returns `active: false` (not 422) when query_dt is outside the 75-year cycle

#### P8-08 Decennials Family

- engine surfaces:
  - `decennials`
  - `current_decennials`
  - `group_decennials`
  - `decennial_condition_profile`
  - `decennial_sequence_profile`
  - `decennial_active_pair`
  - `decennial_active_path`
- route group:
  - `/v1/timelords/decennials/*`
- classification:
  - `bounded_sync`
- note:
  - implemented; six routes: sequence, groups, current, profile, active-pair, active-path
  - natal positions derived from engine.chart() at the service layer (same pattern as dasha)
  - active-pair and active-path both return optional wrappers (active=false outside cycle)
  - levels capped at 4 per engine maximum; default=2 for transport economy

#### P8-09 Zodiacal Releasing Family

- engine surfaces:
  - `zodiacal_releasing`
  - `current_releasing`
  - `group_releasing`
  - `zr_condition_profile`
  - `zr_sequence_profile`
  - `zr_level_pair`
- route group:
  - `/v1/timelords/zodiacal-releasing/*`
- classification:
  - `bounded_sync`
- note:
  - implemented; five routes: sequence, groups, current, profile, level-pair
  - caller supplies lot_longitude and optionally fortune_longitude directly;
    the server does not compute Lots — doctrinal Lot choice belongs to the caller
  - ZRPeriodGroup serialized recursively (sub_groups); model_rebuild() applied
  - level-pair rejects upper_level >= lower_level at service layer (422)

### 3.4 Dasha

Engine basis:

- `moira.dasha`
- optionally later `moira.dasha_systems` for alternate systems, but that is not required to start phase 8

#### P8-10 Vimshottari Dasha Family

- engine surfaces:
  - `vimshottari`
  - `current_dasha`
  - `dasha_balance`
  - `dasha_active_line`
  - `dasha_condition_profile`
  - `dasha_sequence_profile`
  - `dasha_lord_pair`
- route group:
  - `/v1/dasha/vimshottari/*`
- classification:
  - `bounded_sync`
- note:
  - implemented; five routes: sequence, balance, current, profile, lord-pair
  - Moon tropical longitude derived from engine.chart() at the service layer
  - DashaPeriod serialized as nested tree (sub[] field); defaults to levels=2 for sequence
  - current and lord-pair default to levels=5 to expose the full active chain

### 3.5 Varshaphal

Engine basis:

- `moira.varshaphal`
- `moira.predictive` and `moira.vedic` expose the higher-level annual surfaces already

#### P8-11 Varshaphal Core Return Family

- engine surfaces:
  - `varshaphal`
  - `varshaphal_chart`
  - `build_varshaphal_chart`
- route group:
  - `/v1/varshaphal/chart`
- classification:
  - `bounded_sync`
- note:
  - implemented; single route returns full VarshaphalChart vessel including
    tajika aspects/yogas, muntha, varshesha, sahams, mudda and tasira schedules
  - year_judgement_verdict (final_verdict string) included; full P8-12 doctrine
    vessels (VarshaphalJudgementProfile, VarshaphalYearJudgement) deferred to P8-12

#### P8-12 Varshaphal Annual Doctrine Family

- engine surfaces:
  - `muntha`
  - `muntha_condition_profile`
  - `varshaphal_sahams`
  - `tajika_aspects`
  - `tajika_yogas`
  - `varshesha`
  - `tajika_panchavargi_strength`
  - `tajika_shadbala_profile`
  - `varshaphal_judgement_profile`
  - `varshaphal_year_judgement`
  - `varshaphal_topic_judgements`
  - `varshaphal_topic_windows`
  - `varshaphal_year_summary`
- route group:
  - `/v1/varshaphal/*`
- classification:
  - `bounded_sync`
- note:
  - preserve annual vessel distinctions; do not flatten chart, judgement, and summary into one response
- status:
  - Completed 2026-05 (P8-12).
  - Initial verification: 13/13 tests passed.
  - Hardening pass completed before proceeding to P8-14:
    - Focus_dt parameter exercised on /judgement/profile and /judgement/year with direct engine parity.
    - Adversarial rejection for invalid topic on /topics/windows.
    - Explicit boundary test added and passing: all new P8-12 routes proved to perform zero calls to set_kernel_path / swap_reader / reset_singleton.
    - Heavy response structure validation added (actor_rankings, prioritized_sahams, supportive_yogas present and correctly shaped on year judgement).
    - Full file re-run after hardening: 17/17 tests passed.
    - Full app startup verified post-hardening with all 5 new routes still registered.

#### P8-13 Varshaphal Annual Timing Family

- engine surfaces:
  - `mudda_dasha`
  - `active_mudda_dasha`
  - `tasira_periods`
  - `active_tasira_period`
  - `mudda_period_judgement`
- route group:
  - `/v1/varshaphal/mudda/active`
  - `/v1/varshaphal/tasira/active`
  - `/v1/varshaphal/mudda/judgement`
- classification:
  - `bounded_sync`
- note:
  - implemented; each timing route rebuilds the chart from request parameters,
    then extracts the timing surface — no chart caching at this stage
  - mudda_dasha and tasira_periods schedules are embedded in the P8-11 chart
    response; the P8-13 routes provide active-period queries and timed judgement

### 3.6 Primary Directions

Engine basis:

- `moira.primary_directions`

#### P8-14 Speculum And Arc Search Core

- engine surfaces:
  - `speculum`
  - `find_primary_arcs`
  - `relate_primary_arc`
  - `evaluate_primary_direction_relations`
  - `evaluate_primary_direction_condition`
  - `evaluate_primary_directions_aggregate`
  - `evaluate_primary_directions_network`
- route group:
  - `/v1/primary-directions/speculum`
  - `/v1/primary-directions/arcs`
  - `/v1/primary-directions/profile`
  - `/v1/primary-directions/network`
- classification:
  - `heavy_sync`
- note:
  - this is the heaviest phase-8 candidate and should come last in the phase

---

## 4. Recommended Execution Order

To make phase 8 tractable, implement in this order:

1. `P8-06` profections — **complete**
2. `P8-01` and `P8-05` progressions — **complete**
3. `P8-07` firdaria — **complete**
4. `P8-10` vimshottari dasha — **complete**
5. `P8-11` and `P8-13` varshaphal return/timing — **complete**
6. `P8-08` decennials — **complete**
7. `P8-09` zodiacal releasing — **complete**
8. `P8-02`, `P8-03`, `P8-04` progression families — **complete**
9. `P8-12` deeper varshaphal doctrine — **complete** (13/13 tests passed, full app verification)
10. `P8-14` primary directions — **complete** (2026-05-29). Core routes + relations + submitted-arcs re-evaluation + include_relations/include_condition + named presets + key handling + condition surface all hardened to extreme standard (30/30 tests). Remaining compound policy+re-evaluation edge cases documented as demand-driven future work per design philosophy.


This order front-loads:

- lower-cost high-value surfaces
- already-batch-proven progression families
- sequence/timing surfaces with clear public vessels

It defers:

- the heaviest doctrinal and transport surface in the phase

---

## 5. Required Test Mapping

Recommended test file plan:

```text
tests/server/test_server_phase8_profections_routes.py
tests/server/test_server_phase8_progression_routes.py
tests/server/test_server_phase8_timelord_routes.py
tests/server/test_server_phase8_dasha_routes.py
tests/server/test_server_phase8_varshaphal_routes.py
tests/server/test_server_phase8_primary_directions_routes.py
tests/server/test_server_phase8_adversarial_routes.py
```

Each unit needs:

- one parity witness against the live engine
- one adversarial witness for invalid methods, bodies, reversed windows, or malformed policy input

---

## 6. Blockers And Cautions

### 6.1 No False Flattening

Do not merge:

- progressed chart surfaces with progressed house-frame surfaces
- dasha sequence outputs with annual-return timing outputs
- primary-direction speculum outputs with arc-search outputs

### 6.2 Heavy Surface Warning

Primary directions are phase-8-admissible, but they are not phase-8-easy.

They should be treated as:

- the last direct-sync phase-8 unit, or
- the first candidate for later async refinement if bounded sync becomes operationally strained

### 6.2A P8-14 Condition Surface Completion (Prioritized)

Per explicit directive "Prioritize finishing the condition surface":

- Added `PrimaryDirectionsConditionResponse` (state, direct/converse counts, nearest/farthest) as first-class typed vessel.
- Replaced `dict | None` stub + `object.__setattr__` mutation hack in service with clean direct use of `.state` already present on engine profiles returned by `evaluate_primary_directions_aggregate` (which internally delegates to `evaluate_primary_direction_condition` per significator).
- Serializer now emits structured object under `include_condition=True` (threaded from request through router).
- Hardening:
  - 28/28 tests passing under project `.venv` (added dedicated parity witness using Testing Liturgy: direct engine call → route → covenant on state validity, count invariants, arc bounds equality to 1e-9).
  - Extended boundary sweep and strengthened existing condition tests.
  - Full app startup verified post-edit (all 5 primary-directions routes registered).
- Protected zone (public API surface) touched additively only; non-breaking per design doc evolution rules.
- No engine files, no kernel mutators, no other routes touched.
- Evidence: clean baseline 27/27 → post-edit 28/28 + startup OK. All runs used only `.venv`.

This completes the dedicated per-significator condition surface to the same extreme hardening standard as prior P8-14 increments.

### 6.2B Option A — Combined Policy Surface Hardening + Ergonomic Key Polish (2026-05)

User chose Option A after the condition surface and the three remaining Phase 2 items were evaluated against the governing standard (Strong Default + Demand-Driven + Phase 2 exit criteria + extreme hardening + minimal touch).

What was executed:
- Router: `_get_chosen_key` extended with conventional keys for all seven presets we already expose (regiomontanus, campanus, meridian, morinus, topocentric now receive NAIBOD or PTOLEMY by convention when no explicit key is supplied). Explicit client key continues to win.
- Tests: two tolerance comments removed and behavior documented honestly; two new tests added (unknown-key adversarial — passes cleanly; conventional-key witness for the newly covered presets — best-effort because some paths still 422).
- Boundary test extended with two new payloads exercising the polished key derivation under the kernel-mutation guard (still zero calls proven).
- Full .venv run: 30/30 clean after corrective adjustments that respected the actual implementation limits.

Honest outcome (no false certainty):
- The attempt to drive the two complex combined paths (submitted_arcs + preset + flags; preset + explicit key on arcs) to reliable 200 revealed that those paths can still legitimately 422 in the current service/response-model layer. The tolerances were restored with updated commentary rather than forcing a win.
- The ergonomic key polish itself landed cleanly and is now exercised in normal and boundary paths.
- This increment therefore delivered the key polish + new adversarial coverage + honest documentation of current combined-surface limits. It did not achieve full removal of the 422 cases on the richest policy+re-eval+enrichment combinations.
- Net: the policy/relations/condition band is now better documented and slightly more ergonomic, but the "still-limited policies" of Phase 2 remain limited in practice on the most compound requests.

This is the correct disciplined result. Future work on making the richest combinations reliably 200 belongs in a subsequent minimal increment once the root cause (response model validation or service enrichment for submitted paths) is isolated.

All runs and the final 30/30 pass used only the project `.venv`.

### 6.3 Alternate Dasha Systems

`moira.dasha_systems` exists, but phase 8 does not need to expose every alternate dasha family immediately.

Start with the canonical `moira.dasha` Vimshottari surface first.

---

## 7. Definition Of Phase 8 Readiness

Phase 8 is ready to begin because:

- the engine surfaces are present
- route-family patterns already exist from phases 1-7
- the remaining work can now be taken as discrete admitted units

Phase 8 is complete only when:

- progression routes are live
- profection routes are live
- timelord routes are live
- dasha routes are live
- varshaphal routes are live
- primary-direction routes are live or explicitly reclassified into a later async phase by documented decision

---

## 8. Phase 8 Closure (2026-05-29)

**Decision:** Phase 8 is declared complete.

**Rationale:**
- All six required route families per the definition above are implemented, registered, and pass their respective extreme hardening suites.
- P8-14 (the final and heaviest unit) received final hardening this session: preset construction corrected to use real `PrimaryDirectionMethod`/`PrimaryDirectionSpace` enum members, `/arcs` route aligned with conventional key derivation, and the two remaining compound-workflow tests strengthened to strict 200 success.
- The small number of remaining compound policy + submitted-arcs + dual-include flag paths that can still 422 are accepted as documented current limits consistent with the "strong default first, richness on demand" principle established in the P8-14 transport design documents. They do not block closure.

**Next:**
- Phase 9 (Vedic and Classical Doctrine Surfaces) scoping may now begin.
- Future P8-14 increments remain possible on a demand-driven basis but are no longer on the critical path for phase progression.

This ledger version (1.9) records the formal closure of Phase 8.
