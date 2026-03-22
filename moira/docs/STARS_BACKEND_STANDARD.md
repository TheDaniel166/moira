## Moira Unified Stars Backend Standard

### Governing Principle

The Moira unified-star backend is a sovereign computational subsystem. Its
definitions, layer boundaries, terminology, invariants, failure doctrine, and
determinism rules are stated here and are frozen until explicitly superseded by
a revision to this document.

This document reflects current implementation truth as of Unified-Stars Phase
11. It describes the subsystem that actually exists in `moira/fixed_stars.py`
and `moira/stars.py`; it does not describe aspirational future capabilities.

---

## Part I - Architecture Standard

### 1. Authoritative Computational Definitions

#### 1.1 Unified-star subsystem boundary

The unified-star backend is a subsystem cluster with two authoritative files:

- `moira/fixed_stars.py`
- `moira/stars.py`

Their boundary is normative:

| File | Authority |
|---|---|
| `moira/fixed_stars.py` | fixed-star catalog lookup, proper-motion propagation, frame conversion, parallax handling, heliacal event search, and subsystem-level aggregate/network vessels |
| `moira/stars.py` | unified public star surface, Gaia enrichment, named lookup, proximity search, magnitude search, source precedence, and merge doctrine |

`moira/gaia.py` is a delegated dependency. It is not the constitutional center
of this subsystem.

#### 1.2 Core star computation

A **fixed-star position** in Moira is:

> The authoritative output of `fixed_star_at`, computed by catalog resolution,
> proper-motion propagation from catalog epoch, frame conversion to tropical
> ecliptic of date, and first-order annual stellar parallax where admitted.

`StarPosition` is the authoritative position vessel.

#### 1.3 Heliacal event

A **heliacal event** in Moira is:

> The authoritative event output of `heliacal_rising_event` or
> `heliacal_setting_event`, computed by daily search over elongation and
> visibility doctrine until a qualifying rising or last-visible setting is
> found.

Legacy `heliacal_rising` and `heliacal_setting` remain compatibility wrappers
that return only the event JD. `HeliacalEvent` is the authoritative explicit
event vessel.

#### 1.4 Unified star result

A **unified star** in Moira is:

> The authoritative public result of named lookup, proximity search, or
> magnitude search over the merged Hipparcos / Gaia surface.

`FixedStar` is the authoritative unified vessel. It preserves whether the
result is Hipparcos-only, Gaia-only, or merged.

#### 1.5 Relation

A **star relation** in Moira is:

> The first-class relational truth describing what kind of star result exists
> and on what basis it exists.

The current relation layer distinguishes:

| Vessel | Kind | Basis set |
|---|---|---|
| `StarPosition` | `catalog_lookup` | `named_star_lookup` |
| `HeliacalEvent` | `heliacal_event` | `heliacal_visibility` |
| `FixedStar` | `catalog_merge` | `named_lookup`, `proximity_search`, `magnitude_search` |

#### 1.6 Condition profile

A **star condition profile** in Moira is:

> A backend-only integrated structural summary derived from one star result
> vessel, consuming existing truth, classification, and relation state.

The current structural states are:

- `catalog_position`
- `heliacal_event`
- `unified_merge`

`StarConditionProfile` is derived only from lower-layer truth. It is not a
second star engine.

#### 1.7 Chart condition profile

A **star chart condition profile** in Moira is:

> A deterministic aggregate of per-result star condition profiles, reporting
> structural counts and strongest / weakest profile summaries under the
> currently embodied ranking.

It includes at least:

- ordered per-result condition profiles
- `catalog_position` / `heliacal_event` / `unified_merge` counts
- strongest / weakest profile summaries

#### 1.8 Condition network profile

A **star condition network profile** in Moira is:

> A deterministic directed graph projection over already-preserved star
> relations and condition profiles.

It includes at least:

- star nodes
- source nodes
- event nodes
- directed edges for catalog lookup, heliacal event, and unified catalog merge
- per-node incoming / outgoing / total degree
- isolated nodes
- direct-degree connectivity summaries

This graph is structural only. It is not interpretive or advisory.

---

### 2. Layer Structure

The backend is organised into one subsystem core plus ten formalised post-core
layers. Each layer consumes outputs already produced below it. No layer reaches
upward.

```
Core      - Authoritative unified-star computation (`fixed_star_at`,
            heliacal event search, `star_at`, `stars_near`,
            `stars_by_magnitude`)
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
- may not recompute star, heliacal, or merge doctrine independently
- may not alter valid astronomy, heliacal, or merge semantics by reclassification
- may not mutate an earlier-layer vessel in place
- may not introduce interpretation, recommendation, or UI concerns

---

### 3. Delegated Assumptions

The unified-star backend delegates to external modules without redefining them:

| Concern | Delegated to | Convention |
|---|---|---|
| Gaia catalog positions | `moira.gaia` | authoritative Gaia source and propagated Gaia positions |
| planetary longitude for solar parallax / elongation | `moira.planets` | authoritative solar longitude source |
| obliquity and coordinate transforms | `moira.obliquity`, `moira.coordinates` | authoritative frame-conversion layer |
| local sidereal time | `moira.rise_set` and star helpers | authoritative horizon-context support |
| Julian Day conversion | `moira.julian` | authoritative TT / UT conversion layer |

Changes to those delegated sources propagate into the unified-star subsystem.
This document does not freeze their independent doctrine.

---

### 4. Doctrine Surface

#### 4.1 Fixed-star doctrine

Fixed-star lookup and heliacal doctrine are explicit through:

- `FixedStarLookupPolicy`
- `HeliacalSearchPolicy`
- `FixedStarComputationPolicy`

These govern only doctrine already embodied by the engine:

- prefix lookup admission
- heliacal elongation threshold
- heliacal visibility tolerance
- heliacal setting visibility factor

Default policy is behavior-preserving.

#### 4.2 Unified-star doctrine

Unified merge and search doctrine are explicit through:

- `UnifiedStarMergePolicy`
- `UnifiedStarComputationPolicy`

These govern only doctrine already embodied by the subsystem:

- Gaia enrichment enablement
- Gaia search-result inclusion
- Gaia magnitude window
- Hipparcos ↔ Gaia sky-match radius
- dedup radius
- magnitude guard

Default policy is behavior-preserving.

---

### 5. Terminology Freeze

The following terms are now frozen:

| Term | Meaning |
|---|---|
| fixed-star position | the direct catalog-derived position result from `fixed_star_at` |
| heliacal event | the explicit rising/setting event vessel over the legacy JD wrappers |
| unified star | the merged public star result over Hipparcos / Gaia doctrine |
| catalog lookup | relation kind for direct fixed-star lookup |
| heliacal event | relation kind for heliacal visibility event truth |
| catalog merge | relation kind for unified-star result formation |
| source kind | `hipparcos`, `gaia`, or `both` |
| merge state | `unmatched`, `matched`, or `gaia_direct` |
| catalog position | structural condition state for `StarPosition` |
| unified merge | structural condition state for `FixedStar` |

`catalog lookup`, `catalog merge`, `source kind`, and `merge state` must be
used consistently in future code, docs, and tests.

---

## Part II - Invariants and Failure Doctrine

### 6. Vessel Invariants

The following invariants are normative.

#### 6.1 `StarPosition`

- `name` and `nomenclature` must be non-empty
- `longitude`, `latitude`, and `magnitude` must be finite
- if `computation_truth` is present, matched name and nomenclature must agree
- if `classification` is present, it must equal the derived classification
- if `relation` is present, it must equal the derived catalog-lookup relation
- if `condition_profile` is present, it must equal the derived catalog-position profile

#### 6.2 `HeliacalEvent`

- `jd_ut` must equal `truth.event_jd_ut`
- `event_kind` must be `rising` or `setting`
- `search_days` must be positive
- qualifying offsets and conjunction offsets must fall within `search_days`
- if `classification` is present, it must equal the derived classification
- if `relation` is present, it must equal the derived heliacal relation
- if `condition_profile` is present, it must equal the derived heliacal profile

#### 6.3 `FixedStar`

- `source` must be `hipparcos`, `gaia`, or `both`
- position and magnitude fields must be finite
- if `computation_truth` is present, `source_mode` and `is_topocentric` must agree
- Gaia-matched truth must preserve `gaia_source_index`
- Gaia-only truth must not preserve a Hipparcos name
- if `classification` is present, it must equal the derived classification
- if `relation` is present, it must equal the derived merge relation
- if `condition_profile` is present, it must equal the derived unified-merge profile

#### 6.4 `StarChartConditionProfile`

- `profiles` must be deterministically ordered
- count fields must equal the derived counts from `profiles`
- count fields must sum to the total profile count
- `strongest_profiles` and `weakest_profiles` must equal the derived ranking summaries

#### 6.5 `StarConditionNetworkProfile`

- nodes and edges must be deterministically ordered
- node ids must be unique
- edges must be unique
- edges must reference known nodes
- edge direction must match relation kind:
  - catalog lookup: `source:* -> star:*`
  - heliacal event: `event:* -> star:*`
  - catalog merge: `source:* -> star:*`
- node degree counts must match edges exactly
- `isolated_nodes` must equal the zero-degree set
- `most_connected_nodes` must equal the max-degree set

---

### 7. Failure Doctrine

Failure behavior is normative.

#### 7.1 Invalid caller input

Malformed public inputs must fail clearly and deterministically with
`ValueError`, including:

- empty names
- non-finite Julian Days
- invalid latitude / longitude ranges
- non-positive or non-finite search parameters
- incomplete observer coordinate pairs
- invalid orb or magnitude parameters
- invalid policy object types

#### 7.2 Lookup failure

Lookup failure remains semantic, not structural:

- unknown fixed-star names raise `KeyError`
- absence of the physical catalog file raises `FileNotFoundError`
- absence of an admissible Gaia match does not raise; it yields the non-enriched path

#### 7.3 Internal inconsistency

If a caller constructs a vessel with inconsistent truth, classification,
relation, condition, chart, or network state, construction must fail loudly
with `ValueError`.

Silent drift is prohibited.

---

## Part III - Validation Codex

### 8. Minimum Validation Commands

Changes to the unified-star subsystem must be validated in the project `.venv`.

Minimum commands:

```powershell
.\.venv\Scripts\python.exe -m py_compile moira\fixed_stars.py moira\stars.py tests\unit\test_fixed_stars_api.py
.\.venv\Scripts\python.exe -m pytest tests\unit\test_fixed_stars_api.py -q -k "Phase1TruthPreservation or Phase3InspectabilityAndHardening or Phase4PolicySurface or Phase5Relations or Phase6RelationInspectabilityAndHardening or Phase7ConditionProfiles or Phase8ChartConditionProfile or Phase9ConditionNetworkProfile or Phase10SubsystemHardening"
.\.venv\Scripts\python.exe -m pytest tests\unit\test_fixed_stars_api.py -q -k "heliacal_rising or heliacal_setting or star_at or fixed_star_at or stars_near or stars_by_magnitude"
```

If a future change touches the slower legacy star-group delegations, the full
`tests/unit/test_fixed_stars_api.py` file should also be run when time budget
permits.

### 9. Freeze Rule

This document freezes:

- the unified-star subsystem boundary
- star / heliacal / merge terminology
- current doctrine and policy surfaces
- current cross-layer invariants
- current failure doctrine
- current validation minimum

Future work may extend this subsystem, but may not silently repurpose or blur
the frozen terms and boundaries above.
