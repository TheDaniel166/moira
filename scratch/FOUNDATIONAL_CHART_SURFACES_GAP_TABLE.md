# Foundational Chart Surfaces — Exposed vs Engine-Available Gap Analysis

**Scope**: The three endpoints under the `chart` tag:
- `POST /v1/chart`
- `POST /v1/chart/reduction`
- `POST /v1/houses`

**Objective**: Identify additive opportunities to make the foundational chart surface as robust as the underlying Moira engine vessels and facade, without altering existing request/response contracts.

**Sources**:
- REST: `moira_server/routers/chart.py`, `moira_server/models/chart.py`, `moira_server/services/chart.py`, `moira_server/services/_shared.py`, `moira_server/serializers/chart.py`
- Engine: `moira/facade.py` (public `Chart`), `moira/houses.py` (HouseCusps + calculate_houses + HousePolicy), `moira/chart.py` (internal ChartContext)
- Governance: `wiki/02_services/REST_REDUCTION_VISIBILITY_AUDIT.md` (explicit gaps noted for this family)

---

## 1. Chart Compact Result (POST /v1/chart → ChartResponse)

| Feature / Field | Currently Exposed in REST | Engine / Facade Availability | Gap / Opportunity for Robustness |
|-----------------|-----------------------------|------------------------------|----------------------------------|
| `jd_ut` | Yes (ChartResponse) | Yes (Chart.jd_ut) | Fully aligned |
| `datetime_utc` | Yes (as ISO string) | Yes (property → datetime) | Aligned (string form) |
| `calendar_utc` (BCE-safe structured) | No | Yes (property → CalendarDateTime with astronomical year numbering) | Missing structured BCE-safe calendar breakdown. Engine computes it; REST only gives ISO string. |
| `obliquity` | Yes | Yes | Fully aligned |
| `delta_t` | Yes (seconds) | Yes | Fully aligned |
| `planets` (dict of PlanetPositionResponse) | Yes | Yes (dict[str, PlanetData]) | Aligned via serializer |
| `nodes` (dict of NodePositionResponse, controlled by include_nodes) | Yes | Yes (dict[str, NodeData]) | Aligned |
| `longitudes(include_nodes=...)` helper | No (must derive from planets/nodes) | Yes (method on Chart) | Additive convenience method exposure or flat longitudes enrichment |
| `speeds()` helper | No (must derive) | Yes (method on Chart) | Additive convenience |
| Bodies selection (`bodies` list, including small bodies when allowed) | Yes (request + response reflects returned) | Yes | Aligned |
| Topocentric observer for Moon | Implicit via `is_topocentric` flag on Moon planet | Yes (when observer_* supplied) | Observer context only appears in reduction, not compact result |
| Small-body support in chart | Supported in validation & request (allow_small_bodies) | Supported if manifest loaded | Good, but no explicit provenance in response about which kernel supplied small bodies |

---

## 2. Chart Reduction Surface (POST /v1/chart/reduction → ChartReductionResponse)

| Feature / Field | Currently Exposed in REST | Engine / Facade Availability | Gap / Opportunity for Robustness |
|-----------------|-----------------------------|------------------------------|----------------------------------|
| `result` (full ChartResponse) | Yes | N/A (REST construct) | Good pattern |
| `requested_datetime` / `normalized_datetime_utc` | Yes | Computed in service from request + engine | Aligned |
| `jd_ut`, `jd_ut1`, `jd_tt`, `delta_t_seconds`, `obliquity_deg` | Yes (detailed breakdown) | Engine provides jd_ut + delta_t + obliquity; UT1/TT conversions via julian | Strong — reduction adds the full temporal bridge |
| `requested_bodies` vs `returned_bodies` | Yes | Derived in service from request + chart result | Excellent for selection transparency |
| `include_nodes_requested/returned` | Yes | Derived | Good |
| `topocentric_requested` + observer context (lat/lon/elev + LST) | Yes (in reduction only) | Computed when observer supplied | Good |
| `stage_sequence` (high-level chart assembly stages) | Yes (`_CHART_STAGE_SEQUENCE`) | Internal stages exist; this is curated summary | Per audit: intentionally "summary-grade rather than full internal engine trace" |
| Per-planet reduction summaries (source_vessel, selection_surface, apparent/aberration/grav_deflection/nutation flags, frame, center, topocentric_applied, stage_sequence) | Yes (hard-coded full pipeline for all planets in current impl) | Actual pipeline in positions/planets layer (light-time, deflection, aberration, frame bias, precession, nutation, parallax, ecliptic) | Summary is robust for doctrine; actual per-planet variation or "apparent" toggles not exposed because chart() always runs full pipeline |
| Per-node reduction summaries (differentiated TRUE_NODE / MEAN_NODE / LILITH / TRUE_LILITH stage sequences) | Yes (custom _node_reduction_summary) | Engine has distinct true_node, mean_node, mean_lilith, true_lilith paths | Very good differentiation |
| Full internal vectors / intermediate states | No (by design) | Available deeper in corrections/coordinates/native | Per plan: do not expose unstable internals. Current summary-grade is correct. |
| Engine/kernel provenance (kernel name, version, manifest for small bodies) | Partial (via meta endpoints only) | Available on engine state | Could be enriched in reduction for complete auditability of the chart snapshot |

---

## 3. Houses (POST /v1/houses → HousesResponse)

| Feature / Field | Currently Exposed in REST | Engine / Facade Availability | Gap / Opportunity for Robustness |
|-----------------|-----------------------------|------------------------------|----------------------------------|
| `system` (requested) | Yes | Yes (HouseCusps.system) | Fully aligned |
| `effective_system` | Yes | Yes | Fully aligned |
| `fallback` + `fallback_reason` | Yes | Yes | Fully aligned |
| Classification (family, cusp_basis, latitude_sensitive, polar_capable) | Yes (flattened) | Yes (HouseSystemClassification on HouseCusps.classification) | Aligned |
| `asc`, `mc`, `armc`, `dsc`, `ic` | Yes (dsc/ic derived in serializer) | Yes (fields + properties) | Aligned |
| `east_point`, `vertex`, `anti_vertex` | Yes | Yes (optional fields on HouseCusps) | Aligned |
| `cusps` (12 values) | Yes | Yes | Aligned |
| `policy` (the exact HousePolicy that governed the result: unknown_system + polar_fallback) | No | Yes (HouseCusps.policy; HousePolicy dataclass with .default(), .strict(), .experimental()) | Major gap. Engine now stores the governing doctrine. REST only shows effects. |
| Input policy control (pass HousePolicy / enums on request) | No (HousesRequest has only dt/lat/lon/system) | Yes (Moira.houses(..., policy=...) and calculate_houses) | Explicitly noted as gap in REST_REDUCTION_VISIBILITY_AUDIT.md. Clients cannot request strict or experimental polar behavior. |
| `sun_longitude` (for Sunshine / solar-anchored systems) | No | Yes (optional kwarg to calculate_houses) | Missing for full support of certain house systems |
| `ayanamsa_offset` (for sidereal-anchored house calculations) | No | Yes (optional kwarg) | Missing for Vedic/sidereal house work |
| Dedicated houses reduction / provenance sibling | No | N/A (would be REST addition) | Explicit gap in audit: "houses still does not expose a dedicated policy or reduction sibling route" |
| Elevation / topocentric houses | Not supported in request (correct for standard calc) | Houses calculation uses lat/lon; height has limited effect in most systems | No gap |
| Caching | No (unlike chart) | N/A | Houses is cheap; not a robustness issue for truth but could be for perf |

---

## 4. Cross-Cutting / Combined Surfaces

| Feature | Currently Exposed | Engine Availability | Gap / Opportunity |
|---------|-------------------|---------------------|-------------------|
| Combined chart + houses in one call (common for natal) | No (separate endpoints) | Internal helper `build_chart_with_houses_context` exists in `_shared.py`; engine supports both | Additive combined endpoint (e.g. /natal or /chart-with-houses) would be highly useful for website/consumer use without breaking existing contracts |
| Observer context on compact chart result | Only `is_topocentric` flag on affected planet(s) | Full context available when supplied | Observer details (lat/lon/elev/LST) are reduction-only. Could add optional or lightweight observer block to main ChartResponse additively |
| HousePolicy echoed even on compact houses | No | Yes on the vessel | See houses table |

---

## Summary of Audit-Aligned Gaps (from REST_REDUCTION_VISIBILITY_AUDIT.md)

- Houses: no policy transport (input or output of governing policy)
- Houses: no reduction sibling route
- Chart reduction: intentionally summary-grade (this is accepted design, not a gap to close by dumping more internals)

**Additional robustness opportunities** surfaced by direct engine comparison (additive only):
- Structured `calendar_utc`
- Governing `policy` on houses response + input policy support
- `sun_longitude` / `ayanamsa_offset` for houses
- `longitudes()` / `speeds()` conveniences or enrichments
- Combined chart+housess response
- Optional observer context on compact chart
- Stronger provenance (kernel/manifest) inside chart reduction

All of the above can be introduced without mutating the shape or behavior of the three existing endpoints.

**Next recommended step for robustness**: Prioritize the two items the project's own audit already flags for this family (houses policy + houses reduction), plus the low-cost additive `calendar_utc` and policy echo on the existing houses response. These directly increase doctrinal visibility and parity with the engine's public contract.