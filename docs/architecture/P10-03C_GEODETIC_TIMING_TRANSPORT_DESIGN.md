# P10-03c Geodetic Timing Transport Design

Version: 0.1
Date: 2026-10-28
Status: Design record for the Geodetic timing admission
Scope: REST admission of `moira.geodetic_timing.find_geodetic_transits`

Downstream of:
- `docs/architecture/P10-03B_GEODETIC_ANALYSIS_TRANSPORT_DESIGN.md`
- `docs/architecture/MOIRA_SERVER_ROUTE_ADMISSION_CHECKLIST.md`
- `wiki/02_standards/GEODETIC_ANALYSIS_STANDARD.md` section 6

P10-03b deferred timing to its own record. Timing differs from every earlier Geodetic route in five ways:
- it searches time;
- its cost grows with span and mover speed;
- it can exhaust declared budgets;
- it depends on ephemeris coverage;
- it reports UT1 epochs that clients will display as civil time.

## 1. Pre-admission evaluation

| Question | Answer |
| --- | --- |
| Engine owner | `find_geodetic_transits`; facade `Moira.geodetic_transits` |
| Surface stable and public | Yes. Standard section 6. The facade equals the owner composition (`tests/unit/test_geodetic_facade.py`). |
| Read-only request flow | Yes. The reader and clock identity are rebound and checked at completion by the owner. |
| Engine correctness gate | **Passed after a repair.** Before admission, orb windows narrower than the scan step were lost: at step 0.5 over 60 days, 14 of 34 Moon windows were missing while the result reported complete. Fixed in `moira._fixed_aspect_search` (commit `fix(timing): find orb windows narrower than the scan step`). Windows are now step-invariant, from 0.125 to 2 days, within 6 ms. |
| Transport stance | Bounded synchronous, cached by validated request (section 3). |

## 2. Route

`POST /v1/geodetic/chart/transits`. It is chart-backed by necessity: the mover always needs the server engine's ephemeris.

The reference place's Geodetic angles are frozen at `reference_dt`, a `frozen_tropical_anchor` on the engine clock. The search then finds when one mover makes the requested aspects to those fixed angles between `start_dt` and `end_dt`.

**There is no direct variant.** A supplied reference would save nothing, because the mover still needs the ephemeris.

## 3. Bounds and cost

Measured on DE441, at one place, over 366 days, with three aspects to four angles:

| Mover | Step | Wall time | Evaluations |
| --- | --- | --- | --- |
| Moon | 0.25 d | about 11 s | 16,127 |
| Moon | 0.5 d | about 7 s | 10,521 |
| Mars | 1 d | about 2.4 s | 2,661 |
| Sun | 1 d | about 1.4 s | 2,815 |
| Pluto | 2 d | about 1.1 s | 1,203 |

| Limit | Value | Basis |
| --- | --- | --- |
| `end_dt - start_dt` | Greater than 0 and at most 366 days | One year bounds the worst case at the step floor to about 11 s |
| `step_days` | [0.25, 5], default 0.5 | The floor bounds cost. Correctness no longer depends on the step (section 1). The default is declared and echoed. |
| Aspects | 1 to 8 unique `{angle_deg ∈ [0,180], orb_deg ∈ [0,10]}` | The owner admits orbs below 90; 10 bounds window width |
| Angles | Nonempty unique subset of MC, IC, ASC, DSC | Owner set |
| `max_evaluations` | ≤ 50,000 (owner default) | The owner's default is the ceiling |
| `max_subdivisions` | ≤ 10,000 (owner default) | The owner's default is the ceiling |
| `max_depth` | ≤ 12 (owner default) | The owner's default is the ceiling |
| `maximum_light_time_days` | (0, 2], default 1 | Covers the TNO and comet distances in the catalogs |
| `coverage_policy` | `require_full` (default) or `allow_partial` | Owner policy |
| Mover | Major planets or qualified `asteroid:` / `comet:` names, 1–64 characters | The owner refuses numeric NAIF IDs and ambiguous names |

The cache uses the existing expensive-response LRU, keyed by the validated request under namespace `v1:geodetic:chart:transits`, as Sade Sati windows already do.

## 4. Response truth

These fields are serialized without loss:
- **The frozen reference:** chart, display and tropical targets, `reference_jd_ut1/tt`, angles, `target_policy` and `source_frame`.
- **The mover:** `requested_mover`, `body_id` and small-body identity.
- **The applied policy,** echoed.
- **Intervals:** requested, covered, gaps and scanned.
- **Coverage resources:** center/target, source label, SHA-256, catalog IDs and TDB intervals.
- **Events:** target, aspect, directed branch, JD UT1, motion, residual and window index.
- **Orb windows:** covered span, entry and exit (or null), entry and exit statuses, and pass indices.
- **Budget use:** `evaluations` and `subdivisions`.
- **Outcome:** `complete`, `status` and `reasons`.
- **The bound clock:** UT1, TT, TDB, ΔT and its source, and the ephemeris identity.
- **The semantics strings:** `timescale`, `longitude_frame`, `correction_regime`, `completeness` and `resource_semantics`.

**Epochs are JD UT1.** Every event and boundary also carries `datetime_utc`, the same UT1 epoch rendered as UTC through `datetime_from_jd(_ut1_to_utc(...))`, the existing serializer convention. A JD remains the authoritative value.

**Exhausted budgets are a valid incomplete answer, not an error.** They return HTTP 200 with `complete: false` and the reason, as the standard requires. A missing time never proves the absence of an event.

## 5. Verification required for admission

**Parity:**
- The route equals `Moira.geodetic_transits` through the same serializer.
- Both zodiac lanes, and both a major planet and the Moon.
- The contact built into the reference is found at the reference epoch.

**Adversarial:**
- Aware datetimes and ordering.
- The span cap.
- The step, aspect, orb, angle and budget ceilings.
- Lane law and extra fields.
- A numeric or ambiguous mover is refused.

**Behavioural:**
- A tiny evaluation budget returns 200 incomplete with `search_budget_exhausted`.
- Repeat requests are served from the cache.
- The route works with no global kernel.

**Structural:**
- OpenAPI registration, the pinned route set, and a regenerated REST reference.

## 6. Admission decision

`POST /v1/geodetic/chart/transits` is admitted once section 5 passes. The P10-03 prohibitions (maps, projections, search, scoring and relocation) are unchanged, as are the earlier P10-03b routes.
