# REST Reduction Visibility Audit

Status: active service-layer audit

Purpose:
- measure the current `moira_server` transport surface against the REST
  reduction-visibility contract
- identify where the network API already preserves engine truth
- identify where the API still collapses facade-visible reduction into
  final-only transport
- define the next implementation wave

Related governing documents:
- [ENGINE_VS_SERVICE_BOUNDARY.md](c:/Users/nilad/OneDrive/Desktop/Moira%20C++/wiki/00_foundations/ENGINE_VS_SERVICE_BOUNDARY.md)
- [SERVICE_LAYER_GUIDE.md](c:/Users/nilad/OneDrive/Desktop/Moira%20C++/wiki/02_services/SERVICE_LAYER_GUIDE.md)
- [REST_REDUCTION_VISIBILITY_IMPLEMENTATION_PLAN.md](c:/Users/nilad/OneDrive/Desktop/Moira%20C++/wiki/02_services/REST_REDUCTION_VISIBILITY_IMPLEMENTATION_PLAN.md)

---

## 1. Audit Standard

An endpoint family is considered:

- `Compliant` when it preserves reduction truth already present on the engine or
  facade surface, either directly or through an explicit transport shape.
- `Partial` when it preserves some major truth but still hides meaningful
  policy, reduction, or branch detail.
- `Non-compliant` when it effectively black-boxes a truth-bearing engine call
  and exposes no lawful path to inspect the omitted reduction.

This audit is about transport truth, not numerical correctness.

---

## 2. Current Family Status

| Route family | Status | Current truth preservation | Main gap |
|---|---|---|---|
| `chart` / `houses` | `Compliant` | `chart` now has a sibling reduction endpoint; `houses` preserves effective/fallback/classification truth | houses may later gain richer policy transport, but no foundational black-box gap remains |
| `positions` | `Compliant` | compact final routes plus sibling reduction endpoints for `planet` and `sky` | reduction truth is now present, but chart-level reuse and broader family consistency still remain |
| `transits` | `Compliant` | computation truth, classification, relation, condition profile serialized | lunar phase route remains thinner than transit/ingress truth model |
| `relationship` | `Compliant` | broad preservation of truth/classification/relation/condition across synastry, overlays, composites, Davison, patterns | payload economy may later need opt-in trimming, but truth path exists |
| `progressions` | `Compliant` | rich doctrine/relation/condition truth plus sibling reduction endpoints across secondary, declination, arc, time-key, house-frame, profile, and network surfaces | `house-frame/cusps` remains intentionally compact-first, but no major family-level reduction gap remains |
| `timelords` | `Partial` | sequence/profile surfaces preserve significant doctrinal structure | policy and reduction provenance are not framed as explicit transport options |
| `primary-directions` | `Compliant` | compact routes preserve meaningful results and search-derived routes now have sibling reduction endpoints for `arcs`, `profile`, and `network` | `speculum` remains compact-first, but the family now has a lawful route-uniform reduction path where search doctrine lives |
| `returns` / `varshaphal` | `Compliant` | embedded computation_truth (reusing transits structures for the underlying next_transit search derivation, with brackets/step/tolerance/PLANET_RETURN wrapper) + request controls for step_days/solver_tolerance_days (direction already present for planet); now provides direct reduction path | returns family now closed at direct level (embedded truth on ReturnEventResponse); varshaphal remains separate |
| `phenomena` | `Partial` | event truth exists at engine level | transport audit not yet widened enough to guarantee reduction exposure uniformly |
| `visibility` | `Partial` | domain-rich results exist | observer-environment and reduction path need explicit transport guarantees |
| `batch` | `Partial` | `charts` and `progressions` now have sibling batch reduction endpoints; `transits` and transit/ingress/return event payloads now preserve embedded wrapped-family truth (returns direct now Compliant) | `batch/returns` wrapper itself not yet widened to surface the now-available direct returns reduction; heterogeneous `events` remain mixed because some event subtypes (station/aspect/etc.) do not yet carry full reduction doctrine |

---

## 3. Concrete Findings

### 3.1 `chart` and `houses`

Files:
- [moira_server/routers/chart.py](c:/Users/nilad/OneDrive/Desktop/Moira%20C++/moira_server/routers/chart.py)
- [moira_server/serializers/chart.py](c:/Users/nilad/OneDrive/Desktop/Moira%20C++/moira_server/serializers/chart.py)
- [moira_server/models/chart.py](c:/Users/nilad/OneDrive/Desktop/Moira%20C++/moira_server/models/chart.py)

Current truth preserved:
- `houses` keeps:
  - requested system
  - effective system
  - fallback truth
  - classification truth
- `chart` now also keeps, through a sibling reduction route:
  - normalized UTC time and Julian-day reduction
  - observer context and local sidereal time when applicable
  - request versus returned body selection
  - per-planet reduction summaries
  - per-node source-surface summaries

Current gap:
- `houses` still does not expose a dedicated policy or reduction sibling route
- chart reduction is summary-grade rather than a full internal engine trace

Judgment:
- this foundational family now has a lawful reduction path

### 3.2 `positions`

Files:
- [moira_server/routers/positions.py](c:/Users/nilad/OneDrive/Desktop/Moira%20C++/moira_server/routers/positions.py)
- [moira_server/serializers/positions.py](c:/Users/nilad/OneDrive/Desktop/Moira%20C++/moira_server/serializers/positions.py)
- [moira_server/models/positions.py](c:/Users/nilad/OneDrive/Desktop/Moira%20C++/moira_server/models/positions.py)

Current truth preserved:
- final body position
- topocentric flag on `PlanetData`
- sibling reduction routes now preserve:
  - normalized UTC time and Julian-day reduction
  - observer context and local sidereal time
  - admitted correction-stage sequence
  - engine surface, vessel, and frame semantics

Current gap:
- the compact base routes remain final-only by design
- chart-level assembly still does not expose parallel reduction truth
- the reduction is transport-safe summary truth, not a full internal engine trace

Judgment:
- this family now satisfies the contract through sibling reduction endpoints

### 3.3 `primary-directions`

Files:
- [moira_server/models/primary_directions.py](c:/Users/nilad/OneDrive/Desktop/Moira%20C++/moira_server/models/primary_directions.py)
- [moira_server/routers/primary_directions.py](c:/Users/nilad/OneDrive/Desktop/Moira%20C++/moira_server/routers/primary_directions.py)
- [moira_server/serializers/primary_directions.py](c:/Users/nilad/OneDrive/Desktop/Moira%20C++/moira_server/serializers/primary_directions.py)

Current truth preserved:
- compact routes preserve:
  - doctrinal arc metadata
  - relation/profile/network enrichments where already admitted
- sibling reduction routes now preserve on the search-derived surfaces:
  - resolved policy truth
  - chosen key and key-source truth
  - house fallback/effective-system truth
  - search-mode truth (`engine_search` vs `submitted_arcs`)
  - request and observer context

Current gap:
- `speculum` remains compact-first
- the family does not yet expose a dedicated speculum reduction transport

Judgment:
- the search-derived route family is now reduction-uniform
- residual work, if pursued later, is about whether `speculum` should remain
  intentionally compact or gain its own sibling truth surface

### 3.4 `progressions`

Files:
- [moira_server/models/progressions.py](c:/Users/nilad/OneDrive/Desktop/Moira%20C++/moira_server/models/progressions.py)
- [moira_server/routers/progressions.py](c:/Users/nilad/OneDrive/Desktop/Moira%20C++/moira_server/routers/progressions.py)
- [moira_server/serializers/progressions.py](c:/Users/nilad/OneDrive/Desktop/Moira%20C++/moira_server/serializers/progressions.py)

Current truth preserved:
- compact routes preserve:
  - doctrine-family truth
  - relation truth
  - condition profile truth where the engine already carries it
- sibling reduction routes now preserve on the chart-producing and aggregate surfaces:
  - requested natal and target datetimes
  - requested bodies
  - computation truth
  - classification truth
  - admitted stage sequence
  - house-frame observer/system request context
  - aggregate input composition and per-item condition summaries

Live reduction routes:
- `/v1/progressions/secondary/reduction`
- `/v1/progressions/secondary-declination/reduction`
- `/v1/progressions/arc/reduction`
- `/v1/progressions/time-key/reduction`
- `/v1/progressions/house-frame/reduction`
- `/v1/progressions/profile/reduction`
- `/v1/progressions/network/reduction`

Current gap:
- `house-frame/cusps` remains intentionally compact-first

Judgment:
- the family is now reduction-visible in all of its major truth-bearing surfaces
- residual compact subroutes do not currently constitute a family-level contract failure

### 3.5 `transits`

Files:
- [moira_server/models/transits.py](c:/Users/nilad/OneDrive/Desktop/Moira%20C++/moira_server/models/transits.py)
- [moira_server/serializers/transits.py](c:/Users/nilad/OneDrive/Desktop/Moira%20C++/moira_server/serializers/transits.py)

Current truth preserved:
- computation truth
- search truth
- classification
- relation
- condition profile

Judgment:
- this is the strongest current example of the intended contract shape
- future route families should treat it as a model

### 3.6 `relationship`

Files:
- [moira_server/models/relationship.py](c:/Users/nilad/OneDrive/Desktop/Moira%20C++/moira_server/models/relationship.py)
- [moira_server/serializers/relationship.py](c:/Users/nilad/OneDrive/Desktop/Moira%20C++/moira_server/serializers/relationship.py)

Current truth preserved:
- classification
- computation truth
- relation
- condition profile
- fallback-bearing house truth in overlay/davison flows

Judgment:
- already broadly aligned with the reduction contract

### 3.7 `batch`

Files:
- [moira_server/models/batch.py](c:/Users/nilad/OneDrive/Desktop/Moira%20C++/moira_server/models/batch.py)
- [moira_server/routers/batch.py](c:/Users/nilad/OneDrive/Desktop/Moira%20C++/moira_server/routers/batch.py)
- [moira_server/serializers/batch.py](c:/Users/nilad/OneDrive/Desktop/Moira%20C++/moira_server/serializers/batch.py)
- [moira_server/services/batch.py](c:/Users/nilad/OneDrive/Desktop/Moira%20C++/moira_server/services/batch.py)

Current truth preserved:
- compact batch routes still preserve:
  - item-local success/failure isolation
  - compact result payloads for all admitted families
  - embedded transit/ingress truth where the wrapped event serializer already
    carries it
- sibling reduction routes now preserve:
  - `/v1/batch/charts/reduction`
    - per-item chart reduction truth
    - per-item failure isolation
  - `/v1/batch/progressions/reduction`
    - per-item progression computation truth
    - per-item classification truth
    - request-local batch technique context
    - per-item failure isolation

Current gap:
- `batch/returns` now can embed the direct returns family's reduction (embedded computation_truth from the transits-derived search + request controls); the wrapper itself has not yet been widened to surface it uniformly
- heterogeneous `batch/events` items remain only as strong as their underlying
  event subtype; station/aspect/equatorial items do not yet carry the same
  admitted reduction depth as transit/ingress/return items
- `batch` therefore does not yet preserve reduction uniformly across every
  embedded family (returns direct now compliant, but aggregate not yet updated)

Judgment:
- Wave 4 has started cleanly
- `batch` is improved but still `Partial`

---

## 4. Priority Remediation Order

### Priority 1

`timelords`, `varshaphal`, `visibility`, `phenomena`

Reason:
- mostly structurally healthy
- need consistency work more than first-principles redesign

(Note: returns direct family addressed in Wave 3/4 via embedded transits-derived reduction truth + controls; varshaphal remains separate.)

---

## 5. Recommended Contract Shape For Phase 1 Remediation

For the first implementation wave, prefer:

1. add explicit inclusion flags for reduction detail where the payload is still
   compact enough to remain ergonomic
2. add sibling `/reduction` endpoints for route families with heavy or deeply
   nested traces
3. reserve full dual-surface `result` / `reduction` responses for the route
   families where the reduction is core identity, especially `positions`

Live pilot targets:
- `/v1/positions/planet/reduction`
- `/v1/positions/sky/reduction`

Foundational targets now live:
- `/v1/chart/reduction`
- `/v1/positions/planet/reduction`
- `/v1/positions/sky/reduction`

---

## 6. Immediate Next Implementation Tasks

1. Sweep `timelords` for the same explicit reduction-path alignment now used by
   `progressions`.
2. Audit whether the `positions` reduction surface should eventually add
   optional deeper policy toggles beyond the current admitted defaults.
3. Update `batch/returns` now that the direct returns family has a lawful embedded
   reduction contract (computation_truth + controls).
4. Revisit heterogeneous `batch/events` only after the weaker event subtypes
   have stronger family-level truth surfaces.

---

## 7. Current Conclusion

The server is not uniformly non-compliant.

It already contains several route families that preserve real doctrinal and
reduction truth well, especially `transits`, `relationship`, and now `returns`
(direct family, via embedded transits-derived computation_truth on ReturnEventResponse
plus request policy controls).

However, the REST surface as a whole does not yet satisfy the newly frozen
contract uniformly because some remaining family surfaces (timelords, varshaphal,
visibility, phenomena) and some batch wrappers still expose reduction truth
inconsistently, even though the foundational surfaces, the primary-directions
search family, the progressions family, the direct returns family, and the
first Wave 4 batch reductions now have lawful truth paths.
