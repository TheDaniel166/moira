## Moira Sothic Backend Standard

### Governing Principle

The Moira Sothic backend is a sovereign computational subsystem. Its
definitions, layer boundaries, terminology, invariants, failure doctrine, and
determinism rules are stated here and are frozen until explicitly superseded by
a revision to this document.

This document reflects current implementation truth as of Sothic Phase 11. It
describes the subsystem that actually exists in `moira/sothic.py`; it does not
describe aspirational future capabilities.

---

## Part I - Architecture Standard

### 1. Authoritative Computational Definitions

#### 1.1 Core Sothic computation

A **Sothic result** in Moira is:

> The authoritative output of the Egyptian civil calendar conversion,
> Sirius heliacal-rising search, drift tracking, epoch detection, or cycle
> prediction logic embodied in `moira/sothic.py`.

The computational core remains the authority for:

- Egyptian civil calendar arithmetic
- modular 365-day wrap doctrine
- delegated heliacal-rising search for Sirius
- Sothic drift measurement
- epoch detection from drift tolerance
- cycle-length prediction arithmetic

Later layers may preserve, classify, inspect, aggregate, or network this truth.
They may not recompute Sothic doctrine independently.

#### 1.2 Egyptian civil date

An **EgyptianDate** in Moira is:

> The authoritative result of converting a Julian Day into the wandering
> 365-day Egyptian civil calendar anchored to the current epoch doctrine.

It preserves:

- civil month and day
- season
- day-of-year within the civil year
- epagomenal birth association where applicable
- modular-calendar computation truth

#### 1.3 Sothic rising entry

A **SothicEntry** in Moira is:

> The authoritative annual record of Sirius's heliacal rising for one
> astronomical year at one observer location, together with its Gregorian and
> Egyptian-calendar placement, drift, and cycle position.

It is produced by `sothic_rising(...)` and remains the canonical annual vessel.

#### 1.4 Sothic epoch

A **SothicEpoch** in Moira is:

> The authoritative record of a year whose Sirius heliacal rising falls within
> the currently admitted epoch tolerance of the New Year anchor.

It is produced by `sothic_epochs(...)` and remains a filtered, doctrine-bearing
subset of `SothicEntry`, not a second heliacal engine.

#### 1.5 Sothic relation

A **Sothic relation** in Moira is:

> The formal relation between a result vessel and the doctrinal anchor it
> depends on.

The current relation layer distinguishes:

| Term | Definition |
|---|---|
| `egyptian_calendar` | civil-calendar anchoring to the epoch |
| `sothic_rising` | Sirius heliacal-rising relation for an annual entry |
| `sothic_epoch` | Sirius heliacal-rising relation for an epoch-alignment result |

The current relation bases are:

- `civil_calendar_anchor`
- `sirius_heliacal_rising`

The current anchor is frozen as:

- `censorinus_139_epoch`

#### 1.6 Sothic condition profile

A **Sothic condition profile** in Moira is:

> A backend-only integrated structural summary derived from one
> `EgyptianDate`, `SothicEntry`, or `SothicEpoch`, combining preserved truth,
> classification, and relation state into a single per-result vessel.

It currently distinguishes only structural states already implied by result
truth:

- `calendar_anchor`
- `annual_rising`
- `epoch_alignment`

`SothicConditionProfile` is derived only from lower-layer truth. It is not a
second Sothic engine.

#### 1.7 Chart condition profile

A **Sothic chart condition profile** in Moira is:

> A deterministic aggregate of per-result Sothic condition profiles, reporting
> structural counts and strongest / weakest summaries under the currently
> embodied ranking.

It includes at least:

- ordered per-result condition profiles
- calendar-anchor / annual-rising / epoch-alignment counts
- strongest / weakest summaries under the current structural ranking

#### 1.8 Sothic condition network profile

A **Sothic condition network profile** in Moira is:

> A deterministic directed graph projection over preserved Sothic relations and
> integrated per-result condition profiles.

It includes at least:

- anchor nodes
- star nodes
- date / entry / epoch result nodes
- one directed edge per admitted relation
- incoming / outgoing / total degree counts
- isolated nodes
- direct-degree connectivity summaries

This graph is structural only. It is not an interpretive layer.

---

### 2. Layer Structure

The backend is organised into one computational core plus ten formalised
post-core layers. Each layer consumes outputs already produced below it. No
layer reaches upward.

```text
Core      - Authoritative Sothic computation (`egyptian_civil_date`,
            `sothic_rising`, `sothic_epochs`, `sothic_drift_rate`,
            `predicted_sothic_epoch_year`)
Phase  1  - Truth preservation
Phase  2  - Classification
Phase  3  - Inspectability and vessel hardening
Phase  4  - Doctrine / policy surface
Phase  5  - Relation formalisation
Phase  6  - Relation inspectability / hardening
Phase  7  - Integrated per-result condition
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
- may not recompute calendar, heliacal, drift, or epoch doctrine independently
- may not alter valid Sothic semantics by reclassification
- may not mutate an earlier-layer vessel in place
- may not introduce interpretation, recommendation, or UI concerns

---

### 3. Delegated Assumptions

The Sothic backend delegates to external modules without redefining them:

| Concern | Delegated to | Convention |
|---|---|---|
| Sirius heliacal rising | `moira.fixed_stars.heliacal_rising` | authoritative heliacal search source |
| Julian Day conversion | `moira.julian` | authoritative JD / calendar conversion layer |

Changes to those delegated sources propagate into the Sothic subsystem. This
document does not freeze their independent doctrine.

---

### 4. Doctrine Surface

#### 4.1 Calendar doctrine

Calendar doctrine is now explicit through:

- `SothicCalendarPolicy`

The current default doctrine embodies:

- the Censorinus 139 AD epoch anchor
- 1 Thoth as the start of the wandering 365-day civil year
- modular 365-day wrap arithmetic

#### 4.2 Heliacal doctrine

Heliacal doctrine is now explicit through:

- `SothicHeliacalPolicy`

The current default doctrine embodies:

- Sirius as the star of record
- delegated heliacal-rising detection
- `arcus_visionis = 10.0`
- `search_days = 400`

#### 4.3 Epoch doctrine

Epoch doctrine is now explicit through:

- `SothicEpochPolicy`

The current default doctrine embodies:

- `tolerance_days = 1.0`
- epoch admission by absolute residual drift after signed normalization

#### 4.4 Prediction doctrine

Prediction doctrine is now explicit through:

- `SothicPredictionPolicy`

The current default doctrine embodies:

- `cycle_length_years = 1460.0`

#### 4.5 Unified policy vessel

The authoritative doctrine surface is:

- `SothicComputationPolicy`
- `DEFAULT_SOTHIC_POLICY`

The default policy is normative and preserves current behavior.

---

### 5. Public Vessels

The following result vessels are part of the constitutional backend surface:

- `EgyptianDate`
- `SothicEntry`
- `SothicEpoch`
- `EgyptianCalendarTruth`
- `SothicComputationTruth`
- `EgyptianCalendarClassification`
- `SothicComputationClassification`
- `SothicRelation`
- `SothicConditionProfile`
- `SothicChartConditionProfile`
- `SothicConditionNetworkNode`
- `SothicConditionNetworkEdge`
- `SothicConditionNetworkProfile`

These vessels may reject inconsistent state at construction time. That
rejection is normative backend behavior.

---

## Part II - Terminology Standard

### 6. Required Terms

The following terms are normative and should be used consistently in code,
tests, and future docs:

| Term | Required meaning |
|---|---|
| Egyptian civil date | one modular-calendar date within the wandering 365-day civil year |
| Sothic entry | one annual Sirius heliacal-rising record |
| Sothic epoch | one admitted epoch-alignment result |
| anchor | the doctrinal epoch reference used by current calendar and relation logic |
| relation | first-class result-to-anchor or result-to-star truth |
| condition profile | derived per-result structural summary |
| chart condition profile | derived aggregate over condition profiles |
| network profile | directed graph projection over relations and condition profiles |

### 7. Forbidden Conflations

The following conflations are prohibited:

- treating delegated heliacal search as locally redefined astronomy
- treating epoch prediction as epoch detection
- treating the chart profile as a second annual-rising detector
- treating the network profile as an interpretive or symbolic layer

---

## Part III - Invariant Register

### 8. Core Vessel Invariants

The following invariants are constitutional:

#### 8.1 Result vessel invariants

- `EgyptianDate.day_of_year` must lie within the civil year
- `EgyptianDate.month_number`, `day`, `season`, and `epagomenal_birth` must be internally consistent
- `SothicEntry.jd_rising`, `drift_days`, and `cycle_position` must be finite and in-range
- `SothicEpoch.jd_rising` and `drift_days` must be finite and normalized
- when present, computation truth must agree with legacy vessel fields
- when present, classification must agree with computation truth
- when present, relation must agree with computation truth and classification
- when present, condition profile must agree with relation and classification

#### 8.2 Truth invariants

- calendar truth fields must be finite
- wrapped civil-day index must lie within `[0, 364]`
- Sothic computation truth must preserve `Sirius`
- coordinates, epoch JD, `arcus_visionis`, search days, and rising JD must be valid
- `cycle_position` and `tolerance_days` must be valid when present

#### 8.3 Chart aggregate invariants

- profile ordering must be deterministic
- count totals must match aggregated profiles
- strongest / weakest summaries must match derived ranking

#### 8.4 Network invariants

- node ids must be unique
- node ids must preserve the node-kind prefix
- nodes and edges must be deterministically ordered
- edges must reference existing nodes
- edge relation-kind, basis, and condition-state combinations must be doctrinally valid
- node degree counts must match edges
- isolated-node summaries must match derived node degrees
- most-connected summaries must match derived degree ranking

---

## Part IV - Failure Doctrine

### 9. Failure Rules

Failure behavior is normative.

#### 9.1 Invalid public inputs

Malformed public inputs must fail clearly with `ValueError`, including at least:

- non-finite `jd`
- non-finite `epoch_jd`
- invalid `latitude` or `longitude`
- reversed year ranges
- non-positive or non-finite `arcus_visionis`
- negative or non-finite `tolerance_days`
- invalid or malformed policy objects
- invalid cycle length or malformed epoch-prediction inputs

#### 9.2 Search exhaustion

Valid heliacal searches that do not find an event remain governed by current
semantics:

- `sothic_rising` omits that year
- `sothic_epochs` omits non-aligned years

#### 9.3 Invariant failure

Inconsistent internal vessels must fail immediately with `ValueError`. Silent
repair is not constitutional behavior.

---

## Part V - Determinism Standard

### 10. Determinism Guarantees

For fixed inputs, fixed delegated heliacal search behavior, and fixed policy,
the Sothic backend guarantees:

- deterministic calendar results
- deterministic preserved truth
- deterministic classification
- deterministic relation formation
- deterministic condition profiles
- deterministic chart aggregates
- deterministic network node and edge ordering

This determinism guarantee does not override independent changes in delegated
heliacal-search behavior or Julian Day conventions.

---

## Part VI - Validation Codex

### 11. Minimum Validation Commands

All future changes to the Sothic backend must, at minimum, pass:

```powershell
.\.venv\Scripts\python.exe -m py_compile moira\sothic.py tests\unit\test_sothic.py
.\.venv\Scripts\python.exe -m pytest tests\unit\test_sothic.py -q
```

If package exposure changes in a later phase, the relevant public API tests must
also be included in the required validation set.

### 12. Required Validation Themes

The validation corpus for this subsystem must continue to cover:

- Egyptian civil calendar semantics
- annual heliacal-rising semantics
- epoch-detection semantics
- drift-rate semantics
- truth / classification consistency
- relation consistency
- condition-profile consistency
- chart aggregate consistency
- network consistency
- malformed-input failure behavior
- deterministic ordering guarantees

---

## Part VII - Future Boundary

### 13. Explicit Non-Goals

The current constitutional Sothic backend does not yet include:

- interpretation
- symbolic historical commentary
- broader Egyptian calendrical systems beyond the current civil-year model
- autonomous heliacal-visibility doctrine beyond the delegated star engine

Those would require later explicit phases or a successor constitutional
document.
