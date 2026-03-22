## Moira Transits Backend Standard

### Governing Principle

The Moira transits backend is a sovereign computational subsystem. Its
definitions, layer boundaries, terminology, invariants, failure doctrine, and
determinism rules are stated here and are frozen until explicitly superseded by
a revision to this document.

This document reflects current implementation truth as of Transits Phase 11. It
describes the subsystem that actually exists in `moira/transits.py`; it does
not describe aspirational future capabilities.

---

## Part I - Architecture Standard

### 1. Authoritative Computational Definitions

#### 1.1 Core transit computation

A **transit event** in Moira is:

> The authoritative event output of `next_transit` or `find_transits`,
> computed by scanning for a sign change in the signed angular difference
> between a moving body and a resolved target longitude, then refining the
> crossing by bisection.

The computational core remains the authority for:

- target resolution
- crossing detection
- bracketing and bisection refinement
- direction-of-motion labeling
- sign ingress detection
- return search
- syzygy search

Later layers may preserve, classify, inspect, aggregate, or network this truth.
They may not recompute the transit doctrine independently.

#### 1.2 Accuracy doctrine boundary

The transit subsystem is:

> A timing and search subsystem over delegated longitude engines.

It is not the origin of Moira's astronomical accuracy claims.

The following distinction is normative:

| Concept | Meaning |
|---|---|
| solver precision | the local bracketing / bisection tolerance embodied in search truth and policy |
| model accuracy | the end-to-end astronomical fidelity of delegated longitude sources and validation corpus |

This subsystem may preserve and formalize solver precision. It may not
independently overclaim model accuracy beyond what delegated modules and
validation documents establish.

#### 1.3 Ingress

An **ingress event** in Moira is:

> The authoritative event output of `find_ingresses`, computed by scanning for
> a crossing of a zodiac sign boundary longitude and refining the crossing by
> bisection.

`IngressEvent` is the authoritative ingress vessel. It preserves the entered
sign, sign-boundary longitude, direction, and search truth.

#### 1.4 Transit relation

A **transit relation** in Moira is:

> The formal event-level relation between a moving body and the target or sign
> boundary it reaches.

The current relation layer distinguishes:

| Term | Definition |
|---|---|
| `target_crossing` | a body reaching a resolved transit target longitude |
| `sign_ingress` | a body crossing a sign boundary longitude |

`TransitRelationBasis` makes explicit whether the target came from:

- numeric longitude
- planet
- node
- lilith
- asteroid
- fixed star
- sign boundary

#### 1.5 Transit condition profile

A **transit condition profile** in Moira is:

> A backend-only integrated structural summary derived from one `TransitEvent`
> or `IngressEvent`, combining preserved event truth, classification, and
> relation state into a single per-event condition vessel.

It currently distinguishes only structural states already implied by event
truth:

- `static_target`
- `dynamic_target`
- `boundary_event`

`TransitConditionProfile` is derived only from lower-layer truth. It is not a
second transit engine.

#### 1.6 Chart condition profile

A **transit chart condition profile** in Moira is:

> A deterministic aggregate of per-event transit condition profiles, reporting
> structural counts and strongest / weakest source bodies under the currently
> embodied ranking.

It includes at least:

- ordered per-event condition profiles
- static / dynamic / boundary counts
- target-crossing vs sign-ingress counts
- dynamic-relation totals
- strongest / weakest source-body summaries

#### 1.7 Transit condition network profile

A **transit condition network profile** in Moira is:

> A deterministic directed graph projection over preserved transit relations and
> integrated per-event condition profiles.

It includes at least:

- body nodes
- target or sign nodes
- one directed edge per admitted event relation
- incoming / outgoing / total degree counts
- isolated nodes
- direct-degree connectivity summaries

This graph is structural only. It is not an interpretive or recommendation
layer.

---

### 2. Layer Structure

The backend is organised into one computational core plus ten formalised
post-core layers. Each layer consumes outputs already produced below it. No
layer reaches upward.

```
Core      - Authoritative transit computation (`next_transit`, `find_transits`,
            `find_ingresses`, return search, syzygy search)
Phase  1  - Truth preservation
Phase  2  - Classification
Phase  3  - Inspectability and vessel hardening
Phase  4  - Doctrine / policy surface
Phase  5  - Relation formalisation
Phase  6  - Relation inspectability / hardening
Phase  7  - Integrated per-event condition
Phase  8  - Chart-wide condition intelligence
Phase  9  - Relation / condition network intelligence
Phase 10  - Full-subsystem hardening
Phase 11  - Architecture freeze / validation codex
```

#### Layer boundary rules

A layer above the core:

- may consume preserved truth from lower layers
- may classify or aggregate earlier truth
- may add invariant checks that reject internally inconsistent vessels
- may not recompute crossing doctrine independently
- may not alter valid transit, ingress, return, or syzygy semantics by reclassification
- may not mutate an earlier-layer vessel in place
- may not introduce interpretation, recommendation, or UI concerns

---

### 3. Delegated Assumptions

The transit backend delegates to external modules without redefining them:

| Concern | Delegated to | Convention |
|---|---|---|
| planetary longitude | `moira.planets.planet_at` | authoritative body longitude source |
| nodes / lilith longitude | `moira.nodes` | authoritative node and lilith longitude source |
| asteroid longitude | `moira.asteroids.asteroid_at` | authoritative asteroid longitude source |
| fixed-star longitude | `moira.fixed_stars.fixed_star_at` | authoritative fixed-star longitude source |
| ephemeris reader lifecycle | `moira.spk_reader` | `get_reader()` and `SpkReader` authority |
| Julian Day conversion | `moira.julian` | authoritative JD / datetime conversion layer |
| body and sign constants | `moira.constants` | authoritative symbolic constants |

Changes to those delegated sources propagate into the transit subsystem. This
document does not freeze their independent doctrine.

---

### 4. Doctrine Surface

#### 4.1 Search doctrine

Transit search doctrine is now explicit through:

- `TransitSearchPolicy`
- `ReturnSearchPolicy`
- `SyzygySearchPolicy`
- `TransitComputationPolicy`

The default policy is normative and preserves current behavior.

#### 4.2 Transit search doctrine

The current default doctrine embodies:

- auto-selected scan cadence by body through `_auto_step`
- local bisection tolerance of `1e-6` days where not overridden
- sign-change gating through signed angular difference

This doctrine governs search cadence and local refinement only.

#### 4.3 Return doctrine

Return doctrine is embodied through:

- `_RETURN_SEARCH_DAYS`
- the current body-specific default search windows
- the existing direction filter semantics

`planet_return`, `solar_return`, and `lunar_return` remain consumers of the
same core crossing search rather than independent return engines.

#### 4.4 Syzygy doctrine

Syzygy doctrine is embodied through:

- scan-back cadence
- synodic search envelope multiplier
- bisection tolerance for phase crossing refinement

`last_new_moon`, `last_full_moon`, and `prenatal_syzygy` remain wrappers around
the current elongation-crossing search doctrine.

#### 4.5 Relation doctrine

No additional relational doctrine is implied beyond the current formalized
event relation layer. The subsystem does not currently define inter-planet
reception, aspectual support, or chart-wide interpretive transit intelligence.

---

### 5. Public Vessels

The following result vessels are part of the constitutional backend surface:

- `TransitEvent`
- `IngressEvent`
- `LongitudeResolutionTruth`
- `CrossingSearchTruth`
- `TransitComputationTruth`
- `IngressComputationTruth`
- `LongitudeResolutionClassification`
- `CrossingSearchClassification`
- `TransitComputationClassification`
- `IngressComputationClassification`
- `TransitRelation`
- `TransitConditionProfile`
- `TransitChartConditionProfile`
- `TransitConditionNetworkNode`
- `TransitConditionNetworkEdge`
- `TransitConditionNetworkProfile`

These vessels may reject inconsistent state at construction time. That
rejection is normative backend behavior.

---

## Part II - Terminology Standard

### 6. Required Terms

The following terms are normative and should be used consistently in code,
tests, and future docs:

| Term | Required meaning |
|---|---|
| transit event | one body reaching one resolved target longitude |
| ingress event | one body crossing one sign boundary |
| target resolution | how a requested target was turned into a longitude |
| search truth | preserved scan / bracket / tolerance truth |
| solver precision | local refinement tolerance only |
| model accuracy | delegated astronomical fidelity, not locally defined here |
| relation | first-class event-level body-to-target or body-to-sign truth |
| condition profile | derived per-event structural summary |
| chart condition profile | derived aggregate over condition profiles |
| network profile | directed graph projection over relations and condition profiles |

### 7. Forbidden Conflations

The following conflations are prohibited:

- treating solver tolerance as an end-to-end accuracy claim
- treating transit relation as an interpretive influence judgment
- treating the chart profile as a second event detector
- treating the network profile as a predictive or recommendation layer

---

## Part III - Invariant Register

### 8. Core Vessel Invariants

The following invariants are constitutional:

#### 8.1 Event invariants

- `TransitEvent.body` and `IngressEvent.body` must be non-empty
- event Julian Days must be finite
- event direction must be valid under current doctrine
- when present, computation truth must agree with legacy event fields
- when present, classification must agree with computation truth
- when present, relation must agree with computation truth and classification
- when present, condition profile must agree with relation and classification

#### 8.2 Search truth invariants

- all preserved search values must be finite
- `step_days` and `solver_tolerance_days` must be positive
- search and bracket intervals must be ordered
- `crossing_jd_ut` must lie inside the preserved bracket

#### 8.3 Relation invariants

- sign-ingress relations must use `sign_boundary` basis
- sign-ingress relations must not be dynamic
- `sign_boundary` basis is reserved for sign-ingress relations

#### 8.4 Condition profile invariants

- target-crossing profiles must carry a target kind
- sign-ingress profiles must not carry a target kind
- target-crossing state must match dynamic-target truth
- sign-ingress state must be `boundary_event`

#### 8.5 Chart aggregate invariants

- profile ordering must be deterministic
- count totals must match aggregated profiles
- strongest / weakest summaries must match derived ranking

#### 8.6 Network invariants

- node ids must be unique
- nodes and edges must be deterministically ordered
- edges must reference existing nodes
- node degree counts must match edges
- isolated-node summaries must match derived node degrees
- most-connected summaries must match derived degree ranking

---

## Part IV - Failure Doctrine

### 9. Failure Rules

Failure behavior is normative.

#### 9.1 Invalid public inputs

Malformed public inputs must fail clearly with `ValueError`, including at least:

- empty body identifiers
- non-finite Julian Days
- non-finite target or natal longitudes
- invalid direction filters
- non-positive search windows or step sizes
- unordered or zero-width date ranges where current API requires increasing ranges
- unresolved target specifications
- invalid policy objects or policy values

#### 9.2 Search exhaustion

Valid searches that do not find an event remain governed by current semantics:

- `next_transit` returns `None`
- return wrappers raise `RuntimeError`
- syzygy wrappers raise `RuntimeError`

#### 9.3 Invariant failure

Inconsistent internal vessels must fail immediately with `ValueError`. Silent
repair is not constitutional behavior.

---

## Part V - Determinism Standard

### 10. Determinism Guarantees

For fixed inputs, fixed delegated longitude sources, and fixed policy, the
transit backend guarantees:

- deterministic event ordering
- deterministic preserved truth
- deterministic classification
- deterministic relation formation
- deterministic condition profiles
- deterministic chart aggregates
- deterministic network node and edge ordering

This determinism guarantee does not override independent changes in delegated
longitude sources or ephemeris data.

---

## Part VI - Validation Codex

### 11. Minimum Validation Commands

All future changes to the transit backend must, at minimum, pass:

```powershell
.\.venv\Scripts\python.exe -m py_compile moira\transits.py tests\unit\test_transits.py
.\.venv\Scripts\python.exe -m pytest tests\unit\test_transits.py -q
```

If package exposure changes in a later phase, the relevant public API tests must
also be included in the required validation set.

### 12. Required Validation Themes

The validation corpus for this subsystem must continue to cover:

- valid transit detection semantics
- valid ingress detection semantics
- return and syzygy semantics
- truth/classification consistency
- relation consistency
- condition-profile consistency
- chart aggregate consistency
- network consistency
- malformed-input failure behavior
- deterministic ordering guarantees

---

## Part VII - Future Boundary

### 13. Explicit Non-Goals

The current constitutional transit backend does not yet include:

- interpretation
- recommendation logic
- chart-wide interpretive transit intelligence
- aspect-driven transit synthesis
- autonomous astronomical accuracy claims beyond delegated validation

Those would require later explicit phases or a successor constitutional
document.

