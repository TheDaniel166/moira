# P10-03b Geodetic Analysis Transport Design

Version: 0.1
Date: 2026-10-28
Status: Design record for the second Geodetic admission (analysis products)
Scope: REST admission of Geodetic overlay, location comparison, inverse angle
loci and chart-backed house figures

Downstream of:
- `docs/architecture/P10-03_GEODETIC_TRANSPORT_DESIGN.md` (first admission)
- `docs/architecture/MOIRA_SERVER_ROUTE_ADMISSION_CHECKLIST.md`
- `wiki/02_standards/GEODETIC_ANALYSIS_STANDARD.md`
- `wiki/02_standards/GEODETIC_BACKEND_STANDARD.md`

P10-03 deferred several products to "their own Phase 10 design records". This record admits three of them as bounded synchronous analysis routes:
- static natal overlay;
- comparison of caller-supplied places;
- inverse angle loci.

It also admits the chart-backed twin of the kernel-free `/houses` route. Timing (`find_geodetic_transits`) is not admitted here; it needs its own record (P10-03c).

## 1. Pre-admission evaluation

| Question | Answer |
| --- | --- |
| Engine owner | `moira.geodetic_inputs`, `moira.geodetic_analysis`, `moira.geodetic_curves`; facade methods `Moira.geodetic_houses/_overlay/_compare/_loci` |
| Surface stable and public | Yes. Public modules with immutable result vessels, governed by `GEODETIC_ANALYSIS_STANDARD.md`. The facade methods equal the owning compositions exactly (`tests/unit/test_geodetic_facade.py`). |
| Read-only request flow | Yes. No caches, no module-level state, no downloads. Chart-backed routes read positions through the server engine's reader. |
| Transport stance | Synchronous and bounded. Compare is a batch route with per-place failure isolation. |

## 2. Scope boundary: what this does and does not admit

This record admits analytic products only. P10-03's remaining prohibitions stay in force:

| Still not admitted | Why the admitted product is different |
| --- | --- |
| Rendered maps, projections, GeoJSON variants, dense geographic grids | Loci are analytic polylines on geographic longitude and latitude. Every vertex carries a forward-angle residual witness and every gap an exclusion reason. Nothing is rendered, projected or gridded, and interpolation between vertices is declared, not implied. |
| Geographic search, place scoring | Compare evaluates only caller-supplied places. The engine never proposes places. `minimum_contact_orb` ordering is declared geometric, not a suitability score. |
| Relocated natal chart synthesis | The overlay never recomputes the natal chart for a new place. Natal positions are taken once, unchanged, and placed in the place's Geodetic figure, which derives from geographic longitude, not birth-location houses. |
| Primitive MC-only or ASC-only routes | Not added. |
| Catalog-wide body sweeps | Bodies are explicit and bounded. |

## 3. Routes

**Chart-backed** routes compute natal positions with the server engine's reader. They need a kernel, and they always serialize the snapshot provenance: frame, corrections, UT1/TT, zodiac and ayanamsa.

| Route | Facade call |
| --- | --- |
| `POST /v1/geodetic/chart/houses` | `Moira.geodetic_houses` |
| `POST /v1/geodetic/chart/overlay` | `Moira.geodetic_overlay` |
| `POST /v1/geodetic/chart/compare` | `Moira.geodetic_compare` |
| `POST /v1/geodetic/chart/loci` | `Moira.geodetic_loci` |

**Direct** routes are kernel-free. The caller supplies **tropical** longitudes and declares their frame; the positions never acquire an ephemeris.

| Route | Composition |
| --- | --- |
| `POST /v1/geodetic/overlay` | `geodetic_snapshot_from_positions`, then `geodetic_house_chart`, then `geodetic_natal_overlay` |
| `POST /v1/geodetic/compare` | `geodetic_snapshot_from_positions`, then `compare_geodetic_locations` |
| `POST /v1/geodetic/loci` | `geodetic_snapshot_from_positions`, then `geodetic_angular_loci` |

In the direct overlay, the house figure is built on the request's declared frame and epochs, which overlay matching requires.

## 4. Request policy

**Shared rules:**
- **Zodiac lanes** follow P10-03.
  - Direct routes: `zodiac` plus `ayanamsa_deg`.
  - Chart-backed routes: `zodiac` plus `ayanamsa_system`.
  - Tropical refuses an offset or system; sidereal requires one.
- **Locations.** Overlay and houses take `geo_longitude` in [-180, 180] and `geo_latitude` strictly inside the P10-03 polar limit.
  - Compare places are `{location_id, geo_latitude, geo_longitude, display_name?}`.
  - `location_id` is 1–64 characters of `[A-Za-z0-9_.:-]` and must be unique.
- **House system.** `system` is explicit. An absent `house_policy` means `HousePolicy.strict()`, the owner's default.
- **Sun for solar house systems.** Each owner's rule is kept exactly.
  - Overlay and houses need an explicit tropical `sun_longitude`.
  - Compare reuses an explicitly included Sun from the snapshot, as `compare_geodetic_locations` does.
- **Aspect policy.** `aspect_policy` is required, with the same shape as `AspectsFromLongitudesRequest`: `tier` 0–2 (default 1), `orb_factor` greater than 0 and at most 10 (default 1), and `optional_sets` (at most 4).

**Bounds:**

| Limit | Value | Basis |
| --- | --- | --- |
| Bodies per request | ≤ 12 (`GEODETIC_MAX_BODIES`) | P10-03 bound |
| Places per compare | 1 to 24 | Synchronous batch; one shared snapshot |
| Loci angles | Nonempty unique subset of MC, IC, ASC, DSC | Owner's angle set |
| Loci `latitude_step_deg` | [0.5, 10], default 2 | At most about 360 samples per locus |
| Loci `max_evaluations` | 1 to 20,000, default 20,000 | The owner's default is the ceiling |
| Loci `round_trip_tolerance_deg` | (0, 1e-3], default 1e-7 | Positive, and too small to admit a false vertex |

**Failure policy:**
- `body_error_policy` (`raise` by default, or `collect`) governs bodies the snapshot cannot resolve.
  - Collected failures are serialized, and the snapshot and result report `complete: false`.
- Compare isolates each place, as the checklist requires of batch routes.
  - `place_error_policy` defaults to `collect`, so one failing place, such as a polar strict-house refusal, never masks the others.
  - `raise` is still available.

## 5. Response truth

These fields are serialized without loss:
- **Snapshot:** `positions` (with small-body identity), `failures`, `source_kind`, `source_frame`, `correction_regime`, `zodiac`, `ayanamsa_deg`, `ayanamsa_system`, `jd_ut1`, `jd_tt`, `resource_receipt_status` and `complete`.
- **Overlay:** placements (house, longitude, `exact_on_cusp`, `cusp_longitude`), contacts (`AspectDataResponse`, with `applying` always null because contacts are static), `target_longitudes`, `coincident_targets`, `placement_semantics`, the applied aspect policy and `complete`.
- **Compare:** each place's overlay or failure (`failure_type`, `reason`) and its difference from the baseline (angle deltas, house changes, added and removed contacts), plus `order_by`, `baseline_id` and `complete`. The shared snapshot appears once.
- **Loci:** segments as ordered vertices (`latitude_deg`, `longitude_deg`, `residual_deg`, `rising_rate`, `boundary`), exclusions with reasons, `analytic_definition`, per-locus `complete`, and the result's `evaluations`, `semantics` ("ecliptic latitude zero, not a physical horizon track") and `interpolation`.

## 6. Verification required for admission

**Parity:**
- Every route equals its owner (direct) or facade method (chart-backed) exactly, field for field.
- Both lanes are covered, and at least three house systems for overlay and houses.

**Adversarial:**
- Lane law, extra fields, every bound above, duplicate place IDs and unknown angles.
- Polar places: a strict refusal is isolated per place in compare.
- Body failures under `collect`.

**Structural:**
- Direct routes never touch the engine.
- Chart-backed routes work with no global kernel.
- OpenAPI registration, the pinned geodetic route set, and a regenerated REST reference.

## 7. Admission decision

These seven routes are admitted once section 6 passes. `GEODETIC_BACKEND_STANDARD.md` section 7 and the Phase 10 ledger then point here.

Timing remains deferred to P10-03c. The P10-03 prohibitions listed in section 2 remain.
