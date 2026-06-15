# Muhurta Backend Standard

Version: 0.1
Date: 2026-06-14
Status: implemented backend standard for P-GAP-02 REST admission
Scope: Vedic Muhurta moment classification and score over Panchanga truth

This standard governs the Vedic Muhurta classification and scoring surfaces
that are public through the Python engine and admitted P-GAP-02 REST routes:

- `moira.muhurta.MuhurtaPolicy`
- `moira.muhurta.MuhurtaClassification`
- `moira.muhurta.MuhurtaScore`
- `moira.muhurta.classify_muhurta`
- `moira.muhurta.score_muhurta`

This standard does not govern the generic Western-oriented electional search
transport admitted in Phase 13. Muhurta is a Vedic doctrine layer over
Panchanga truth; `/v1/electional/*` is bounded scan infrastructure over
server-defined predicate and scorer catalogues.

---

## 1. Governing Object

The governing object for P-GAP-02 is:

- one Panchanga moment
- one explicit Muhurta policy
- one Muhurta classification
- optionally one numeric Muhurta score

The route family must preserve that a Muhurta response is a judgement over the
five Panchanga limbs at an instant:

- Tithi
- Vara
- Nakshatra
- Yoga
- Karana

It must not present Muhurta as:

- Western electional judgement
- arbitrary search scoring
- a recommendation engine
- a best-time finder
- a guarantee of auspicious outcome
- an activity-specific advisory system

---

## 2. Current Engine Truth

The live engine currently provides:

- `classify_muhurta(panchanga, policy=None)`
- `score_muhurta(panchanga, policy=None)`
- `MuhurtaPolicy` with score weights for the five Panchanga limbs
- `MuhurtaClassification` with limb-level and overall labels
- `MuhurtaScore` with total score, breakdown, and classification

The module also contains additional helpers:

- `is_abhijit_muhurta`
- `is_brahma_muhurta`
- `get_muhurta_guidance_for_activity`
- `muhurta_scorer`
- `find_best_muhurta_windows`

Those helpers are not admitted by P-GAP-02 Stage 1.

---

## 3. Code-Truth Findings

P-GAP-02 found these engine-truth gaps during admission. The first was
hardened before route implementation; the remaining items are explicitly
bounded out of transport:

1. Nakshatra classification is not currently bound to the live Panchanga
   Nakshatra vessel.
   - `classify_muhurta` reads `panchanga.nakshatra.name`.
   - The live Nakshatra vessel exposes `nakshatra`.
   - Resolved for P-GAP-02: `classify_muhurta` now reads the live
     `nakshatra` field.

2. Tara Bala is not currently wired into `classify_muhurta`.
   - `_classify_nakshatra` accepts `janma_nakshatra`.
   - `classify_muhurta` does not pass one.
   - P-GAP-02 Stage 1 must not claim Tara Bala support.

3. `MuhurtaPolicy.use_classical_ashubha_yoga` exists but is not honored by
   the current classification path.
   - REST transport should not expose this flag until the engine enforces it.

4. Panchanga Vara is JD-based, not sunrise-bound local Vara.
   - This is already declared in `moira.panchanga`.
   - Muhurta REST must echo that limitation when chart-backed routes are
     admitted.

5. Activity guidance is broader than the current classification/score vessel.
   - The guidance table contains activity-specific statements and notes.
   - It needs a separate doctrine packet before public transport.

6. Muhurta search windows depend on the generic electional scanner.
   - Search-window routes need separate bounds and semantics.
   - P-GAP-02 Stage 1 should not admit `/v1/muhurta/windows`.

---

## 4. Admitted Stage 1 Shape

P-GAP-02 admits a bounded synchronous REST family under:

- `/v1/muhurta/*`

Stage 1 routes should be limited to:

- `POST /v1/muhurta/direct/classification`
- `POST /v1/muhurta/direct/score`
- `POST /v1/muhurta/chart/classification`
- `POST /v1/muhurta/chart/score`

Direct routes should derive Panchanga through the existing direct Panchanga
surface:

- caller supplies Sun tropical longitude
- caller supplies Moon tropical longitude
- caller supplies JD
- caller supplies ayanamsa policy

Chart-backed routes should derive Panchanga through the existing chart-backed
Panchanga service:

- caller supplies timezone-aware datetime
- optional observer context follows the Panchanga route boundary
- server derives Sun/Moon through `Moira.chart`
- server computes Panchanga through `moira.panchanga.panchanga_at`
- server classifies or scores through `moira.muhurta`

The Muhurta route must not build a parallel Panchanga pipeline.

---

## 5. Policy Boundary

Stage 1 may expose score weights only:

- `weight_tithi`
- `weight_vara`
- `weight_nakshatra`
- `weight_yoga`
- `weight_karana`

Weight values must be finite and non-negative.

Stage 1 must not expose:

- `use_classical_ashubha_yoga` until the engine honors it
- `janma_nakshatra` until Tara Bala is implemented and tested
- activity-specific selectors
- arbitrary scorer code
- arbitrary search predicates

---

## 6. Response Truth

Every Muhurta response must include:

- request echo
- Panchanga source
- Panchanga result summary
- Muhurta policy echo
- classification
- reasons
- provenance

Score responses must additionally include:

- `total`
- `breakdown`
- `score_scale`: `engine_raw_unbounded`
- `score_direction`: `higher_is_more_favorable_under_policy`

The score is an engine raw score. It is not normalized and must not be
described as a probability, guarantee, or recommendation rank.

---

## 7. Provenance Requirements

Every admitted response must state:

- `source_module`: `moira.muhurta`
- `engine_entrypoint`: `classify_muhurta` or `score_muhurta`
- `panchanga_source`: `direct_inputs` or `chart_backed`
- `panchanga_module`: `moira.panchanga`
- `chart_construction`: `not_used` or `Moira.chart`
- `reader_owner`: `not_used` for direct routes, `Moira engine instance` for
  chart-backed routes
- `western_electional_doctrine`: `not_admitted`
- `search_semantics`: `not_admitted`
- `activity_guidance`: `not_admitted`
- `stage_sequence`

Minimum stage sequence:

- `input_validation`
- `panchanga_derivation`
- `muhurta_policy_binding`
- `muhurta_classification`
- `muhurta_scoring` for score routes
- `response_serialization`

---

## 8. Required Hardening Before Implementation

Engine/tests prove:

- Nakshatra classification reads the live Nakshatra vessel correctly.
- A known Gandanta or Uttama Nakshatra affects classification as intended.
- Score breakdown reflects the corrected Nakshatra classification.
- Exposed policy fields are the fields actually honored by the engine.
- `use_classical_ashubha_yoga` is either implemented or deliberately absent
  from transport.

This hardening is small and local to Muhurta classification truth.

---

## 9. Verification Requirements

Before REST admission, tests must cover:

- direct classification route success
- direct score route success
- chart-backed classification route success
- chart-backed score route success
- parity with `classify_muhurta`
- parity with `score_muhurta`
- naive datetime rejection on chart-backed routes
- non-finite direct longitude/JD rejection
- non-finite or negative policy weight rejection
- invalid ayanamsa rejection through the Panchanga path
- response provenance separating Muhurta from Western electional
- score response preserving raw unbounded score semantics
- no route registration under `/v1/electional/*`
- no search-window, activity-guidance, or recommendation route

---

## 10. Non-Goals

P-GAP-02 does not admit:

- `/v1/muhurta/windows`
- `/v1/muhurta/best`
- `/v1/muhurta/recommend`
- activity-specific guidance routes
- Abhijit/Brahma Muhurta routes
- Tara Bala until engine support is implemented and tested
- Western electional doctrine
- arbitrary predicates or scorers
- asynchronous search jobs
- dense day calendars

---

## 11. Admission Decision

P-GAP-02 is admitted as:

- `admitted`

Reason:

- the root engine surfaces exist
- the route family is useful and bounded
- the transport boundary can be kept distinct from Western electional search
- the live Nakshatra classification bug was corrected before public
  scoring/classification admission
