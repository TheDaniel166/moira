## Moira Progressions Backend Standard

### Governing Principle

The Moira progressions backend is a sovereign computational subsystem. Its
definitions, layer boundaries, terminology, invariants, doctrine surface,
failure behavior, and determinism rules are stated here and are frozen until
explicitly superseded by a revision to this document.

This document reflects current implementation truth as of Progressions Phase 11.
It describes the subsystem that actually exists in `moira/progressions.py`; it
does not describe aspirational future capabilities.

---

## Part I - Architecture Standard

### 1. Authoritative Computational Definitions

#### 1.1 Core progression computation

A **progression result** in Moira is:

> The authoritative output of a symbolic progression or directing technique
> implemented in `moira/progressions.py`, computed by applying a declared
> symbolic key to the natal chart or to a progressed house frame.

The computational core remains the authority for:

- time-key progression date calculation
- uniform-arc direction calculation
- right-ascension direction calculation
- converse forms of supported techniques
- progressed house-frame calculation

Later layers may preserve, classify, inspect, aggregate, or network this truth.
They may not recompute progression doctrine independently.

#### 1.2 Precision doctrine boundary

The progression subsystem is:

> A symbolic time-advancement and direction subsystem over delegated planetary
> and house computation.

It is not the origin of Moira's absolute astronomical accuracy claims.

The following distinction is normative:

| Concept | Meaning |
|---|---|
| progression doctrine | the symbolic rule that maps life time to ephemeris time, directing arc, or house frame |
| positional accuracy | the fidelity of delegated planetary and house calculations returned by `moira.planets` and `moira.houses` |

This subsystem may preserve and formalize progression doctrine and computation
path truth. It may not independently overclaim positional accuracy beyond what
delegated modules and validation documents establish.

#### 1.3 Three-family doctrine classification

The current progression backend constitutionally embodies exactly three
progression doctrine families:

| Doctrine family | Required meaning |
|---|---|
| `time_key` | life time is mapped to a progressed ephemeris date and planetary positions are read from that date |
| `uniform_arc` | one common directing arc is applied to all natal bodies |
| `house_frame` | the local house frame is progressed as its own structural result |

This three-family classification is frozen backend doctrine. Future techniques
must be classified into one of these families or must justify a successor
revision to this standard.

#### 1.4 Symbolic key doctrine

Each progression technique is constitutionally defined by an explicit symbolic
key preserving at least:

- what unit of life is being mapped
- what ephemeris or rate unit is being applied
- whether the rate is fixed, variable, or stepped
- whether application is uniform or differential
- what coordinate system is used

This doctrine is first-class backend truth through `ProgressionDoctrineTruth`
and may not be reconstructed later from arithmetic alone.

#### 1.5 Progression relation

A **progression relation** in Moira is:

> The formal directing basis embodied by a progression result.

The current relation layer distinguishes:

| Relation kind | Required meaning |
|---|---|
| `time_key` | a result derived by advancing or reversing ephemeris time |
| `directing_arc` | a result derived by applying one directing arc to natal positions |
| `house_frame_projection` | a result derived from a progressed local house frame |

The current basis surface distinguishes:

- `continuous_time_key`
- `stepped_time_key`
- `solar_arc_reference`
- `ascendant_arc_reference`
- `naibod_rate`
- `progressed_house_frame`

#### 1.6 Progression condition profile

A **progression condition profile** in Moira is:

> A backend-only integrated structural summary derived from one
> `ProgressedChart` or `ProgressedHouseFrame`, combining preserved doctrine,
> classification, and relation truth into a single per-result condition vessel.

It currently distinguishes only structural states already implied by the source
truth:

- `uniform`
- `differential`
- `hybrid`

`ProgressionConditionProfile` is derived only from lower-layer truth. It is not
a second progression engine.

#### 1.7 Chart condition profile

A **progression chart condition profile** in Moira is:

> A deterministic aggregate of per-result progression condition profiles,
> reporting structural counts and strongest / weakest techniques under the
> currently embodied backend ranking.

It includes at least:

- ordered per-result condition profiles
- uniform / differential / hybrid counts
- relation-kind totals
- strongest / weakest technique summaries

#### 1.8 Progression condition network profile

A **progression condition network profile** in Moira is:

> A deterministic directed graph projection over preserved progression
> relations and integrated per-result condition profiles.

It includes at least:

- technique nodes
- basis or reference nodes
- one directed edge per admitted progression relation
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
Core      - Authoritative progression computation (`secondary_progression`,
            `solar_arc`, Naibod, tertiary, minor, converse forms, house frame)
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
- may not recompute progression doctrine independently
- may not alter valid progression semantics by reclassification
- may not mutate an earlier-layer vessel in place
- may not introduce interpretation, recommendation, or UI concerns

---

### 3. Delegated Assumptions

The progression backend delegates to external modules without redefining them:

| Concern | Delegated to | Convention |
|---|---|---|
| planetary positions | `moira.planets` | authoritative planetary longitude, speed, and retrograde source |
| house frames | `moira.houses` | authoritative local house and angle computation |
| coordinate conversion | `moira.coordinates` | authoritative ecliptic/equatorial conversion |
| obliquity | `moira.obliquity` | authoritative obliquity source |
| Julian Day conversion | `moira.julian` | authoritative JD / datetime conversion layer |
| ephemeris reader lifecycle | `moira.spk_reader` | `get_reader()` and `SpkReader` authority |
| body and house constants | `moira.constants` | authoritative symbolic constants |

Changes to those delegated sources propagate into the progression subsystem.
This document does not freeze their independent doctrine.

---

### 4. Doctrine Surface

#### 4.1 Policy doctrine

Progression doctrine is now explicit through:

- `ProgressionTimeKeyPolicy`
- `ProgressionDirectionPolicy`
- `ProgressionHouseFramePolicy`
- `ProgressionComputationPolicy`

The default policy is normative and preserves current behavior.

#### 4.2 Time-key doctrine

The current default time-key doctrine governs:

- `tropical_year_days`
- `synodic_month_days`

It applies to:

- secondary progression
- tertiary progression
- tertiary II progression
- minor progression
- their converse forms
- any other technique that maps life time to a progressed ephemeris date

#### 4.3 Uniform-arc doctrine

The current uniform-arc doctrine governs:

- `naibod_rate_deg_per_year`
- solar-arc reference basis
- ascendant-arc reference basis
- coordinate system distinction between longitude and right ascension

It applies to:

- solar arc
- solar arc in right ascension
- Naibod in longitude
- Naibod in right ascension
- ascendant arc
- their converse forms

#### 4.4 House-frame doctrine

The current house-frame doctrine governs:

- `default_house_system`
- progressed house-frame calculation through the one-day-one-year key

It applies to:

- `daily_house_frame`
- `daily_houses`

#### 4.5 Technique-family doctrine

The following classification is constitutionally required:

| Technique family | Current techniques |
|---|---|
| `time_key` | secondary, converse secondary, tertiary, converse tertiary, tertiary II, converse tertiary II, minor, converse minor |
| `uniform_arc` | solar arc, converse solar arc, solar arc in RA, converse solar arc in RA, Naibod longitude, converse Naibod longitude, Naibod RA, converse Naibod RA, ascendant arc |
| `house_frame` | daily house frame, daily houses |

This family mapping is frozen unless explicitly revised.

---

### 5. Public Vessels

The following result vessels are part of the constitutional backend surface:

- `ProgressedPosition`
- `ProgressedChart`
- `ProgressedHouseFrame`
- `ProgressionDoctrineTruth`
- `ProgressionComputationTruth`
- `ProgressionDoctrineClassification`
- `ProgressionComputationClassification`
- `ProgressionRelation`
- `ProgressionConditionProfile`
- `ProgressionChartConditionProfile`
- `ProgressionConditionNetworkNode`
- `ProgressionConditionNetworkEdge`
- `ProgressionConditionNetworkProfile`

These vessels may reject inconsistent state at construction time. That
rejection is normative backend behavior.

---

## Part II - Terminology Standard

### 6. Required Terms

The following terms are normative and should be used consistently in code,
tests, and future docs:

| Term | Required meaning |
|---|---|
| progression doctrine | the explicit symbolic key embodied by one technique |
| doctrine family | one of `time_key`, `uniform_arc`, or `house_frame` |
| rate mode | fixed, variable, or stepped |
| application mode | uniform or differential |
| coordinate system | the coordinate domain the technique operates in |
| relation | first-class directing-basis truth |
| condition profile | derived per-result structural summary |
| chart condition profile | derived aggregate over condition profiles |
| network profile | directed graph projection over relations and condition profiles |

### 7. Forbidden Conflations

The following conflations are prohibited:

- treating symbolic progression doctrine as an astronomical accuracy claim
- treating doctrine family as interpretation
- treating the chart profile as a second progression engine
- treating the network profile as an interpretive or recommendation layer
- collapsing `time_key`, `uniform_arc`, and `house_frame` into one undifferentiated category

---

## Part III - Invariant Register

### 8. Core Vessel Invariants

The following invariants are constitutional:

#### 8.1 Progressed position invariants

- progressed position names must be non-empty
- longitudes and speeds must be finite
- `retrograde` must be boolean
- sign fields must agree with longitude

#### 8.2 Progressed result invariants

- `chart_type` must be non-empty
- natal and progressed Julian Days must be finite
- target dates must be valid datetimes
- `positions` keys must match stored progressed position names
- when present, computation truth must agree with legacy fields
- when present, classification must agree with computation truth
- when present, relation must agree with computation truth and classification
- when present, condition profile must agree with relation and classification

#### 8.3 House-frame invariants

- house-frame vessels require house-frame doctrine truth
- house-frame vessels require classification, relation, and condition profile
- latitude and longitude must be finite and within valid terrestrial bounds
- house-system codes must be supported

#### 8.4 Policy invariants

- `ProgressionComputationPolicy` nested policy objects must be of the expected types
- tropical year, synodic month, and Naibod constants must be positive
- default house-system codes must be supported

#### 8.5 Relation invariants

- relation kind must match doctrine family and directed-arc usage
- relation basis must match computation truth
- time-key and house-frame relations may not carry a reference name
- non-Naibod directing arcs require a reference name

#### 8.6 Condition profile invariants

- structural state must match classification truth
- `hybrid` is reserved for house-frame techniques
- `uniform` is reserved for directed arcs with uniform application
- `differential` is required otherwise

#### 8.7 Chart aggregate invariants

- profile ordering must be deterministic
- count totals must match aggregated profiles
- strongest / weakest summaries must match derived ranking

#### 8.8 Network invariants

- node ids must be unique
- nodes and edges must be deterministically ordered
- edges must reference existing nodes
- node degree counts must match edges
- technique nodes may not have incoming edges
- target nodes may not have outgoing edges
- isolated-node summaries must match derived node degrees
- most-connected summaries must match derived degree ranking
- technique names must currently be unique within one network profile

---

## Part IV - Failure Doctrine

### 9. Failure Rules

Failure behavior is normative.

#### 9.1 Invalid public inputs

Malformed public inputs must fail clearly with `ValueError`, including at least:

- non-finite Julian Days
- malformed body lists
- duplicate body identifiers in one request
- invalid latitude or longitude values
- unsupported house-system codes
- invalid policy objects or policy values

Type misuse for policy subobjects may fail with `TypeError`.

#### 9.2 Invariant failure

Inconsistent internal vessels must fail immediately with `ValueError`. Silent
repair is not constitutional behavior.

#### 9.3 No semantic repair by higher layers

Later layers may reject invalid state. They may not silently reinterpret
progression doctrine in order to make an invalid vessel appear valid.

---

## Part V - Determinism Standard

### 10. Determinism Guarantees

For fixed inputs, fixed delegated planetary and house sources, and fixed
policy, the progression backend guarantees:

- deterministic doctrine truth
- deterministic classification
- deterministic relation formation
- deterministic condition profiles
- deterministic chart aggregate ordering
- deterministic network node and edge ordering

This determinism guarantee does not override independent changes in delegated
planetary, coordinate, or house calculations.

---

## Part VI - Validation Codex

### 11. Minimum Validation Commands

All future changes to the progression backend must, at minimum, pass:

```powershell
.\.venv\Scripts\python.exe -m py_compile moira\progressions.py tests\unit\test_progressions.py
.\.venv\Scripts\python.exe -m pytest tests\unit\test_progressions.py -q
```

If package exposure changes in a later phase, the relevant public API tests must
also be included in the required validation set.

### 12. Required Validation Themes

The validation corpus for this subsystem must continue to cover:

- valid progression semantics for supported techniques
- three-family doctrine truth and classification
- policy default-preservation behavior
- explicit doctrine override behavior
- relation consistency
- condition-profile consistency
- chart aggregate consistency
- network consistency
- malformed-input failure behavior
- deterministic ordering guarantees

---

## Part VII - Future Boundary

### 13. Explicit Non-Goals

The current constitutional progression backend does not yet include:

- interpretation
- recommendation logic
- aspect-driven progressed-event synthesis
- predictive ranking claims
- independent astronomical accuracy claims beyond delegated validation

Those would require later explicit phases or a successor constitutional
document.

