## Moira Dignities Backend Standard

### Governing Principle

The Moira dignities backend is a sovereign computational subsystem. Its
definitions, layer boundaries, terminology, invariants, failure doctrine, and
determinism rules are stated here and are frozen until explicitly superseded by
a revision to this document.

This document reflects current implementation truth as of Phase 11. It
describes the subsystem that actually exists in `moira/dignities.py`; it does
not describe aspirational future capabilities.

---

## Part I - Architecture Standard

### 1. Authoritative Computational Definitions

#### 1.1 Core dignity computation

A **planetary dignity result** in Moira is:

> The authoritative per-planet output of `DignitiesService.calculate_dignities`,
> computed for one of the Classic 7 planets from normalised sign state, house
> placement, sect context, solar proximity, and doctrine admitted under
> `DignityComputationPolicy`.

The computational core remains the authority for:

- essential dignity scoring
- accidental dignity scoring
- sect and hayz truth
- solar condition truth
- admitted mutual-reception scoring
- total score composition

Later layers may classify, preserve, aggregate, or inspect this truth. They may
not recompute the doctrine independently.

#### 1.2 Essential dignity

An **essential dignity** in Moira is:

> The first matching essential condition under the current essential doctrine
> tables, evaluated in this fixed priority order: domicile, exaltation,
> detriment, fall, peregrine.

| Element | Definition |
|---|---|
| doctrine tables | `DOMICILE`, `EXALTATION`, `DETRIMENT`, `FALL` |
| subject set | `CLASSIC_7` only |
| sign source | sign derived from planet longitude |
| priority | domicile > exaltation > detriment > fall > peregrine |
| score source | `SCORE_DOMICILE`, `SCORE_EXALTATION`, `SCORE_DETRIMENT`, `SCORE_FALL`, `SCORE_PEREGRINE` |

The returned `essential_dignity` string and `essential_score` integer remain the
legacy public surface. `essential_truth` and `essential_classification` are
descriptive preservation layers over that same result.

#### 1.3 Accidental dignity

An **accidental dignity** in Moira is:

> The sum of doctrine-admitted accidental conditions attached to one planet,
> where each admitted condition contributes a fixed signed score and explicit
> preserved truth.

The currently embodied accidental dimensions are:

- house strength
- motion state
- solar condition
- admitted mutual reception
- sect / hayz truth

Only house strength, motion, solar condition, and admitted mutual reception
contribute to `accidental_score` under the current engine behavior. Sect and
hayz are preserved and classified truth, not independent additive scoring
components.

#### 1.4 Reception

A **reception** in Moira is:

> A directed relational truth in which one planet occupies a sign belonging to
> another planet under an admitted reception basis.

Reception is formalised with three distinct layers of meaning:

| Term | Definition |
|---|---|
| `all_receptions` | all doctrine-detected directed receptions for the planet |
| `admitted_receptions` | the subset of `all_receptions` allowed by the current policy |
| `scored_receptions` | the subset of `admitted_receptions` that contributes to current accidental dignity scoring |

The current default doctrine admits domicile and exaltation reception bases.
The current default scoring semantics use only the admitted mutual subset.

#### 1.5 Planetary condition profile

A **planetary condition profile** in Moira is:

> A backend-only integrated structural summary derived from one
> `PlanetaryDignity`, combining preserved truth and classifications across the
> essential, accidental, sect, solar, and reception layers.

`PlanetaryConditionProfile` is a consumer of dignity truth, not a second dignity
engine.

#### 1.6 Chart condition profile

A **chart condition profile** in Moira is:

> A deterministic chart-wide aggregation of per-planet condition profiles,
> reporting structural counts and totals without adding interpretation.

It includes at least:

- ordered per-planet profiles
- reinforced / mixed / weakened counts
- strengthening / weakening / neutral totals
- strongest / weakest planets under existing structural criteria

#### 1.7 Condition network profile

A **condition network profile** in Moira is:

> A deterministic directed graph projection over admitted reception truth and
> integrated per-planet condition profiles.

It includes at least:

- one node per planet profile
- one directed edge per admitted reception relation
- unilateral vs mutual edge visibility
- incoming / outgoing / mutual counts per node
- isolated planets
- direct-degree connectivity summaries

This graph is a structural projection only. It is not an interpretive network
layer.

---

### 2. Layer Structure

The backend is organised into one computational core plus ten formalised
post-core layers. Each layer consumes outputs already produced below it. No
layer reaches upward.

```
Core      - Authoritative dignity computation (`calculate_dignities`)
Phase  1  - Truth preservation
Phase  2  - Classification
Phase  3  - Inspectability and vessel hardening
Phase  4  - Doctrine / policy surface
Phase  5  - Reception formalisation
Phase  6  - Reception inspectability / hardening
Phase  7  - Integrated planetary condition
Phase  8  - Chart-wide condition intelligence
Phase  9  - Reception / condition network intelligence
Phase 10  - Full-subsystem hardening
Phase 11  - Architecture freeze / validation codex
```

#### Layer boundary rules

A layer above the core:

- may consume preserved truth from lower layers
- may classify or aggregate earlier truth
- may add invariant checks that reject internally inconsistent vessels
- may not recompute dignity doctrine independently
- may not alter legacy scoring semantics by reclassification
- may not mutate an earlier-layer vessel in place
- may not introduce interpretation, recommendation, or UI concerns

---

### 3. Delegated Assumptions

The dignity backend delegates to external modules without redefining them:

| Concern | Delegated to | Convention |
|---|---|---|
| zodiac sign ordering | `moira.constants.SIGNS` | ordered list of 12 sign names |
| almuten support scoring | `moira.longevity.dignity_score_at` | imported lazily |
| phasis ephemeris lookup | `moira.planets.planet_at` | imported lazily |

Changes to those delegated sources propagate into the dignity subsystem. This
document does not freeze their independent doctrine.

---

### 4. Doctrine Surface

#### 4.1 Essential doctrine

The default essential doctrine is the classic fixed-table model encoded in:

- `DOMICILE`
- `EXALTATION`
- `DETRIMENT`
- `FALL`

`EssentialDignityPolicy` makes this doctrine explicit without changing the
default result.

#### 4.2 Accidental doctrine

The accidental doctrine surface is explicit through:

- `AccidentalDignityPolicy`
- `SolarConditionPolicy`
- `MutualReceptionPolicy`
- `SectHayzPolicy`

The default policy is normative:

> `DignityComputationPolicy()` must preserve the current historical subsystem
> behavior exactly.

#### 4.3 Sect and hayz doctrine

Sect and hayz doctrine is embodied by:

- `SECT`
- `PREFERRED_HEMISPHERE`
- `PREFERRED_GENDER`
- the current Mercury sect model

This truth is preserved and classified explicitly even where it does not affect
the current additive score.

#### 4.4 Solar-condition doctrine

Solar condition doctrine is embodied by the current distance bands:

| Condition | Current band | Score |
|---|---|---|
| Cazimi | within 17 arcminutes of the Sun | `SCORE_CAZIMI` |
| Combust | within 8 degrees of the Sun | `SCORE_COMBUST` |
| Under Sunbeams | greater than 8 and within 17 degrees | `SCORE_SUNBEAMS` |

The default policy governs whether each band is admitted. The band arithmetic
itself remains the authority of the computational core.

#### 4.5 Reception doctrine

The formal reception basis currently supported is limited to what the engine
already computes cleanly:

- domicile reception
- exaltation reception

No other reception basis is implied by this document.

---

### 5. Public Surface

The following public backend entry points are authoritative:

| Surface | Role |
|---|---|
| `PlanetaryDignity` | canonical per-planet dignity vessel |
| `PlanetaryReception` | canonical directed reception relation |
| `PlanetaryConditionProfile` | canonical integrated per-planet condition vessel |
| `ChartConditionProfile` | canonical chart-wide condition aggregation |
| `ConditionNetworkNode` | canonical node-level network summary |
| `ConditionNetworkEdge` | canonical directed network edge |
| `ConditionNetworkProfile` | canonical network aggregation |
| `DignityComputationPolicy` | canonical explicit doctrine/policy surface |
| `DignitiesService.calculate_dignities` | authoritative core computation |
| `DignitiesService.calculate_receptions` | authoritative formal reception projection |
| `DignitiesService.calculate_condition_profiles` | authoritative per-planet condition integration |
| `DignitiesService.calculate_chart_condition_profile` | authoritative chart-wide condition aggregation |
| `DignitiesService.calculate_condition_network_profile` | authoritative network aggregation |
| module-level wrappers of the above | convenience entry points mirroring the service |

No caller should reconstruct hidden doctrine from flattened labels when a
structured truth or classification field already exists.

---

### 6. Terminology Freeze

The following terminology is normative and must not drift casually:

| Term | Meaning |
|---|---|
| truth | structured preservation of already-computed doctrine |
| classification | typed description of preserved truth; never scoring logic |
| inspectability | derived convenience access that does not add doctrine |
| policy | explicit control over already-supported doctrine admission |
| all receptions | all detected directed reception relations |
| admitted receptions | policy-allowed subset of detected receptions |
| scored receptions | admitted mutual subset contributing to accidental score |
| reinforced / mixed / weakened | structural condition labels derived from existing polarity counts only |

In particular:

- classification must remain descriptive, not interpretive
- inspectability helpers must remain derived only
- condition profiles must remain integrative, not doctrinally independent
- network profiles must remain structural, not interpretive

---

### 7. Failure Doctrine

The dignity subsystem follows a strict split:

- bad external inputs fail with `ValueError`
- internally inconsistent result vessels fail with `ValueError` at construction
- invariant drift is treated as an implementation defect, not a recoverable state

The subsystem may not silently coerce malformed dignity inputs into a valid
chart representation.

---

### 8. Explicit Non-Goals

The dignity backend does not, in this frozen phase:

- perform interpretation
- provide recommendation logic
- build reception-network topology beyond direct structural graphing
- perform chart-wide interpretive synthesis
- redefine doctrine outside the explicit policy surface

---

## Part II - Validation Codex

### 9. Validation Environment

| Property | Value |
|---|---|
| authoritative runtime | project `.venv` |
| test runner | `.venv\Scripts\python.exe -m pytest` |
| primary test file | `tests/unit/test_dignities_and_lots.py` |
| dignity regression seam | `tests/unit/test_rule_engine_validation.py -k dignity` |
| focused baseline | 34 dignity/lots tests + 1 dignity rule-engine regression |
| acceptable result | 0 failures, 0 errors |

No dignity test may be modified to make the implementation pass. A failing test
is treated as an implementation defect unless the test itself is proven wrong.

---

### 10. Test Surface Register

| File | Scope | Focus |
|---|---|---|
| `tests/unit/test_dignities_and_lots.py` | subsystem-focused | legacy score preservation, truth/classification consistency, policy, reception, condition, chart-wide aggregation, network, malformed input, deterministic failure behavior |
| `tests/unit/test_rule_engine_validation.py -k dignity` | cross-subsystem regression seam | dignity result compatibility with the rule-engine validation surface |

---

### 11. Validation Doctrine

#### 11.1 What must be validated per layer

| Layer | Must test |
|---|---|
| core dignity computation | `total_score == essential_score + accidental_score`; legacy labels and scores remain unchanged under default policy |
| truth preservation | essential, accidental, sect, solar, and mutual-reception truth align with the legacy result fields they preserve |
| classification | every classification field aligns with its source truth and remains deterministic |
| inspectability | convenience properties are derived only and add no new doctrine or scoring |
| policy | default policy preserves historical behavior exactly; narrower policy changes only its explicit admission surface |
| reception | unilateral vs mutual are distinguished; basis is explicit; admitted subset is policy-governed; scored subset matches current accidental scoring doctrine |
| planetary condition | condition state is derived only from existing polarity counts; profile fields align with source dignity truth |
| chart-wide condition | counts, totals, strongest/weakest summaries, and ordering align with source profiles |
| network | node counts, edge counts, mutual/unilateral counts, isolated planets, and degree summaries align with admitted reception truth |
| hardening | malformed inputs fail clearly; vessel invariant drift fails clearly; same input yields same ordered output |

#### 11.2 What validation must not do

- treat a changed score as acceptable because the structured truth became richer
- bypass the policy surface to test an unsupported doctrine
- assert interpretive meaning from structural labels
- accept non-deterministic ordering in profiles, summaries, or network outputs
- weaken failure behavior to make malformed inputs appear tolerated

---

### 12. Invariant Register

This register is the normative source of truth for subsystem invariants.

#### INV-CORE - Core dignity invariants

| Code | Invariant |
|---|---|
| D-1 | `total_score == essential_score + accidental_score` for every `PlanetaryDignity` |
| D-2 | `essential_dignity` and `essential_score` are preserved unchanged by truth or classification layers |
| D-3 | `accidental_dignities` labels and `accidental_score` remain the authority for current accidental scoring semantics |
| D-4 | default-policy results are semantically identical to the historical subsystem behavior |

#### INV-TRUTH - Truth preservation invariants

| Code | Invariant |
|---|---|
| T-1 | `essential_truth.label == essential_dignity` when `essential_truth` is present |
| T-2 | `essential_truth.score == essential_score` when `essential_truth` is present |
| T-3 | accidental truth labels preserve the same condition labels exposed in `accidental_dignities` |
| T-4 | sect, hayz, solar, and mutual-reception truth preserve already-computed logic rather than reconstructing it later |

#### INV-CLASS - Classification invariants

| Code | Invariant |
|---|---|
| C-1 | each classification field is fully derivable from its paired truth field |
| C-2 | classification does not alter scoring, admission, or rule priority |
| C-3 | the same truth yields the same classification across calls |

#### INV-REC - Reception invariants

| Code | Invariant |
|---|---|
| R-1 | `PlanetaryReception.receiving_planet != PlanetaryReception.host_planet` |
| R-2 | `receiving_sign in host_matching_signs` |
| R-3 | `admitted_receptions` is a subset of `all_receptions` |
| R-4 | `scored_receptions` equals the admitted mutual subset exactly |
| R-5 | scored reception truth remains backward compatible with accidental dignity scoring |

#### INV-COND - Planetary condition invariants

| Code | Invariant |
|---|---|
| P-1 | `PlanetaryConditionProfile.state` matches the derived polarity state from strengthening and weakening counts |
| P-2 | condition profiles consume dignity truth; they do not recompute doctrine |
| P-3 | inspectability flags like `is_reinforced` are derived only from `state` |

#### INV-CHART - Chart-wide aggregation invariants

| Code | Invariant |
|---|---|
| A-1 | reinforced, mixed, and weakened counts match the states of contained profiles |
| A-2 | strengthening, weakening, and neutral totals equal the sum across contained profiles |
| A-3 | reception participation total equals the sum of admitted receptions across contained profiles |
| A-4 | profile order is deterministic by planet order |

#### INV-NET - Network invariants

| Code | Invariant |
|---|---|
| N-1 | each node planet matches its bound profile planet |
| N-2 | `total_degree == incoming_count + outgoing_count` for every node |
| N-3 | `mutual_count <= outgoing_count` for every node |
| N-4 | `mutual_edge_count` and `unilateral_edge_count` match the actual edge set |
| N-5 | isolated planets are exactly the nodes with degree zero |
| N-6 | node order is deterministic by planet order |

#### INV-POL - Policy invariants

| Code | Invariant |
|---|---|
| PO-1 | `DignityComputationPolicy()` is valid and semantically default |
| PO-2 | unsupported explicit doctrine choices raise `ValueError` |
| PO-3 | policy governs admissibility; it does not redefine the lower-level truth model ad hoc |

#### INV-IN - Input invariants

| Code | Invariant |
|---|---|
| I-1 | duplicate classic-planet entries are rejected |
| I-2 | non-finite longitude input is rejected |
| I-3 | non-boolean `is_retrograde` is rejected |
| I-4 | duplicate house cusp numbers are rejected |
| I-5 | house cusp numbers outside `1..12` are rejected |
| I-6 | incomplete cusp sets are rejected |

---

### 13. Determinism Register

The following ordering guarantees are normative:

| Surface | Guarantee |
|---|---|
| `calculate_dignities` | planets returned in deterministic traditional order |
| `calculate_receptions` | directed reception relations returned deterministically for the same input |
| `calculate_condition_profiles` | profiles returned in deterministic planet order |
| `calculate_chart_condition_profile` | strongest and weakest summaries are deterministic under ties |
| `calculate_condition_network_profile` | nodes and edges are deterministic for the same admitted reception truth |

Input permutation must not change the semantic output of the public dignity
surfaces.

---

### 14. Guaranteed Failure Conditions

The following inputs must always fail clearly and consistently.

| Function / vessel | Bad input or drift | Error |
|---|---|---|
| `calculate_dignities` | duplicate classic planet entry | `ValueError` |
| `calculate_dignities` | non-finite longitude | `ValueError` |
| `calculate_dignities` | non-boolean `is_retrograde` | `ValueError` |
| `calculate_dignities` | duplicate cusp number | `ValueError` |
| `calculate_dignities` | missing cusp numbers | `ValueError` |
| `calculate_dignities` | cusp number outside `1..12` | `ValueError` |
| policy validation | unsupported explicit essential doctrine | `ValueError` |
| `PlanetaryDignity` | legacy score / truth / classification inconsistency | `ValueError` |
| `PlanetaryReception` | self-reception or impossible host/sign relation | `ValueError` |
| `PlanetaryConditionProfile` | state or reception-subset drift | `ValueError` |
| `ChartConditionProfile` | aggregate counts or order drift | `ValueError` |
| `ConditionNetworkNode` | degree-count inconsistency | `ValueError` |
| `ConditionNetworkProfile` | isolated-planet, edge-count, or order drift | `ValueError` |

The exact message text may evolve for clarity, but the failure type and semantic
reason must remain stable.

---

### 15. Validation Commands

The minimum validation commands for this subsystem freeze are:

```powershell
.venv\Scripts\python.exe -m pytest tests\unit\test_dignities_and_lots.py -q
.venv\Scripts\python.exe -m pytest tests\unit\test_rule_engine_validation.py -q -k dignity
```

When implementation files change, syntax validation may also be run:

```powershell
python -m py_compile moira\dignities.py tests\unit\test_dignities_and_lots.py
```

---

### 16. Freeze Rule

After this phase, any change to the dignity backend that alters:

- default scores
- default admission behavior
- invariant meaning
- failure semantics
- ordering guarantees
- terminology frozen in Section 6

must be treated as an explicit architecture change and accompanied by a
documented revision to this standard.
