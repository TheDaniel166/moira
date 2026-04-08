# Jaimini Backend Standard

**Subsystem:** `moira/jaimini.py`
**Computational Domain:** Jaimini Chara Karakas
**Constitutional Phase:** 11 — Architecture Freeze and Validation Codex
**Status:** Constitutional

---

## Part I — Architecture Standard

### §1. Computational Definitions

#### §1.1 Chara Karaka

A Chara Karaka (Sanskrit: variable significator) is a Jaimini technique in which the
seven classical planets (and optionally Rahu) are ranked by the degree each planet
occupies within its sidereal sign. The planet holding the highest degree is assigned
the Atmakaraka role (soul significator). Successive planets take successive roles down
to the Darakaraka (spouse significator).

The authoritative engine is `jaimini_karakas(sidereal_longitudes, scheme)`. It accepts
a dict of planet name → sidereal longitude and an optional `JaiminiPolicy`, and returns
a `JaiminiKarakaResult` containing the full ranked assignment.

**The karaka pool:**

| Scheme | Planets |
|---|---|
| 7-karaka | Sun, Moon, Mars, Mercury, Jupiter, Venus, Saturn |
| 8-karaka | Sun, Moon, Mars, Mercury, Jupiter, Venus, Saturn, Rahu |

Ketu is never included in either scheme.

**Karaka roles — 7-karaka scheme (`KARAKA_NAMES_7`):**

| Rank | Role | Abbreviation | Signification |
|---|---|---|---|
| 1 | Atmakaraka | AK | Soul |
| 2 | Amatyakaraka | AmK | Career / minister |
| 3 | Bhratrikaraka | BK | Siblings |
| 4 | Matrikaraka | MaK | Mother |
| 5 | Pitrikaraka | PiK | Father |
| 6 | Gnatikaraka | GK | Community / disputes |
| 7 | Darakaraka | DK | Spouse |

**Karaka roles — 8-karaka scheme (`KARAKA_NAMES_8`):**

Ranks 1–5 are identical to the 7-karaka scheme. Then:

| Rank | Role | Abbreviation | Signification |
|---|---|---|---|
| 6 | Putrakaraka | PuK | Children |
| 7 | Gnatikaraka | GK | Community / disputes |
| 8 | Darakaraka | DK | Spouse |

**Effective degree:**

Each planet's sort key is its degree within its sidereal sign, computed as
`sidereal_longitude % 30`. Rahu is an exception: because Rahu moves retrograde, its
effective degree is inverted: `30 − (sidereal_longitude % 30)`. This inversion is
stored in `KarakaAssignment.is_rahu_inverted`.

**Tiebreaker:**

When two planets occupy exactly the same effective degree, the tie is flagged in
`JaiminiKarakaResult.tie_warnings` as a `(planet_A, planet_B)` pair. A deterministic
tiebreaker is applied (pool-index ordering) so the output is always a complete ranked
sequence. The result is indeterminate in the astronomical sense; the tie_warnings
flag preserves that fact.

**Planet types (`KarakaPlanetType`):**

| Value | Planets |
|---|---|
| `LUMINARY` | Sun, Moon |
| `INNER` | Mercury, Venus, Mars |
| `OUTER` | Jupiter, Saturn |
| `NODE` | Rahu (8-scheme only) |

Planet type is a structural classification based on astronomical category. It is not
a dignity or condition assessment.

---

### §2. Layer Structure

The Jaimini subsystem is organized into ten layers, each building on the prior
according to the constitutional dependency graph.

| Layer | Phase | Vessel / Function |
|---|---|---|
| 0 | Core | `jaimini_karakas()` |
| 1 | Truth Preservation | `KarakaAssignment`, `JaiminiKarakaResult` |
| 2 | Classification | `KarakaRole`, `KarakaPlanetType` |
| 3 | Inspectability | `by_planet()`, `by_karaka()`, `darakaraka`, `has_ties` |
| 4 | Policy | `JaiminiPolicy`, `scheme` parameter |
| 5–6 | (Relational) | Not applicable at this domain scale |
| 7 | Integrated Local Condition | `KarakaConditionProfile`, `karaka_condition_profile()` |
| 8 | Aggregate Intelligence | `JaiminiChartProfile`, `jaimini_chart_profile()` |
| 9 | Network Intelligence | `KarakaPair`, `karaka_pair()` |
| 10 | Hardening | `validate_jaimini_output()` |

Note: Phases 5–6 (Relational Formalization and Relational Hardening) do not apply to
the Jaimini domain at its current scale. The subsystem has no temporal structure or
containment relationship that requires relational vessels.

---

### §3. Delegated Assumptions

The Jaimini subsystem does not compute the following. Callers are responsible for
supplying correct values.

- **Sidereal conversion**: all input longitudes must already be sidereal. Ayanamsa
  application is the caller's responsibility (see `moira.sidereal`).
- **Nodal selection**: the caller is responsible for providing Rahu's longitude (not
  Ketu's) for 8-scheme computation. Ketu is ignored even if supplied.
- **Planet identification**: planet names must match the canonical pool strings
  exactly (`'Sun'`, `'Moon'`, `'Mars'`, `'Mercury'`, `'Jupiter'`, `'Venus'`,
  `'Saturn'`, `'Rahu'`).

---

### §4. Doctrine Surface

The doctrinal choices made by the Jaimini subsystem are explicit and located.

| Choice | Location | Default |
|---|---|---|
| Karaka pool — 7-scheme | `_POOL_7` module constant | Sun, Moon, Mars, Mercury, Jupiter, Venus, Saturn |
| Karaka pool — 8-scheme | `_POOL_8` module constant | `_POOL_7` + Rahu |
| Karaka role names | `KARAKA_NAMES_7`, `KARAKA_NAMES_8` module constants | Canonical per Jaimini Sutras |
| Rahu degree inversion | `_effective_degree()` internal function | `30 − (lon % 30)` |
| Tiebreaker | `jaimini_karakas()` sort key | Pool-index ordering (deterministic) |
| Scheme selection | `JaiminiPolicy.scheme` or `scheme` arg | 7 |
| Ayanamsa acknowledgement | `JaiminiPolicy.ayanamsa_system` field | `'Lahiri'` (informational only) |

---

### §5. Public Vessels

The following are the constitutional public vessels of the Jaimini subsystem.

**Classification constants:**
- `KarakaRole` — string constants for the eight karaka role names
- `KarakaPlanetType` — structural category constants: LUMINARY, INNER, OUTER, NODE

**Policy:**
- `JaiminiPolicy` — frozen dataclass encoding scheme and ayanamsa acknowledgement

**Name tables:**
- `KARAKA_NAMES_7` — ordered list of karaka role names for the 7-scheme
- `KARAKA_NAMES_8` — ordered list of karaka role names for the 8-scheme

**Truth-preservation vessels:**
- `KarakaAssignment` — immutable vessel for one planet's karaka role assignment
- `JaiminiKarakaResult` — immutable vessel for the complete ranked computation

**Condition vessels:**
- `KarakaConditionProfile` — integrated local condition for one `KarakaAssignment`

**Aggregate vessels:**
- `JaiminiChartProfile` — chart-wide aggregate over a full `JaiminiKarakaResult`

**Network vessels:**
- `KarakaPair` — structural edge connecting two karaka roles

**Computational functions:**
- `jaimini_karakas(sidereal_longitudes, scheme, policy)` — core Chara Karaka engine
- `atmakaraka(sidereal_longitudes, scheme)` — convenience accessor for the AK planet
- `karaka_condition_profile(assignment, scheme)` — build a condition profile
- `jaimini_chart_profile(result)` — build a chart-wide aggregate profile
- `karaka_pair(result, role_a, role_b)` — build a network pair from two named roles
- `validate_jaimini_output(result)` — invariant guard for a `JaiminiKarakaResult`

---

## Part II — Terminology Standard

### §6. Required Terms

The following terms carry specific meanings within this subsystem and must not be
used loosely.

| Term | Normative Meaning |
|---|---|
| **Chara Karaka** | One of the seven (or eight) variable significators computed by Jaimini's degree-rank method |
| **Atmakaraka** | The planet with the highest effective degree in its sign; the soul significator; `karaka_rank == 1` |
| **Darakaraka** | The planet with the lowest effective degree; the spouse significator; `karaka_rank == scheme` |
| **effective degree** | The sort key for a planet: `lon % 30` for most planets; `30 − (lon % 30)` for Rahu |
| **scheme** | The integer 7 or 8 selecting which planet pool and role table to use |
| **degree inversion** | Rahu's exclusive transformation — its effective degree is `30 − actual_degree` because it moves retrograde |
| **tie** | A pair of planets with exactly equal effective degrees; flagged in `tie_warnings` |
| **tiebreaker** | The deterministic pool-index ordering applied when two planets share an effective degree |
| **planet type** | The `KarakaPlanetType` structural category of a planet (LUMINARY / INNER / OUTER / NODE) |
| **karaka rank** | The 1-based integer position in the ranked sequence (1 = AK, scheme value = DK) |
| **karaka role** | The string role name assigned to a rank (e.g. `'Atmakaraka'`, `'Darakaraka'`) |
| **condition profile** | A flat doctrinal summary of one `KarakaAssignment`, integrating rank and type |
| **chart profile** | A chart-wide aggregate across all karaka assignments in a `JaiminiKarakaResult` |
| **karaka pair** | A `KarakaPair`; a structural edge between any two named karaka roles |

---

### §7. Forbidden Conflations

The following pairs must not be equated.

**`KarakaAssignment` and `KarakaConditionProfile`**
`KarakaAssignment` is the raw truth-preservation vessel from the engine. A
`KarakaConditionProfile` is a derived doctrinal summary augmenting it with typed
classification. One is the source; the other is a projection.

**`degree_in_sign` and zodiacal longitude**
`degree_in_sign` is the effective sort key (inverted for Rahu). The actual sidereal
longitude within the sign is `sidereal_longitude % 30`. These differ for Rahu.

**`karaka_rank` and `karaka_name`**
`karaka_rank` is an integer (1–8). `karaka_name` is a string role label. They are
correlated but must not be treated as interchangeable. Use `KarakaRole` constants
to reference a role by name; use `karaka_rank` for numeric comparisons.

**`sidereal_longitude` and `degree_in_sign`**
`sidereal_longitude` is the full sidereal position in [0, 360). `degree_in_sign` is
the effective degree within the sign used for sorting, in [0, 30] (30.0 possible for
Rahu at exactly 0° in sign).

**`tie_warnings` and indeterminism**
A non-empty `tie_warnings` signals an astronomically improbable but technically valid
degenerate case. It does not mean the output is invalid — a complete ranked sequence
is always returned.

**`scheme` and pool size**
`scheme` is the integer 7 or 8 and also the expected length of `assignments`. The
scheme value is the length of the pool and also controls which role names are used.
They are derived from the same integer but represent different things.

**`JaiminiChartProfile` and `JaiminiKarakaResult`**
`JaiminiKarakaResult` is the primary truth-preservation vessel from the engine.
`JaiminiChartProfile` is a derived aggregate summary. One is the source; the other
is a projection for downstream doctrinal use.

**`KarakaPair` and `JaiminiChartProfile`**
`KarakaPair` is a two-node network edge between two specific roles. `JaiminiChartProfile`
is a chart-wide summary across all seven or eight roles. One is local and relational;
the other is global.

---

## Part III — Invariant Register

### §8.1 Vessel Invariants

**`KarakaAssignment`:**
- `karaka_rank` ∈ [1, 8]
- `planet` is a non-empty string
- `degree_in_sign` ∈ [0.0, 30.0] (closed interval — 30.0 is permitted for Rahu at 0° in sign)
- `sidereal_longitude` ∈ [0.0, 360.0) (half-open — 360.0 is forbidden)

**`JaiminiKarakaResult`:**
- `scheme` ∈ {7, 8}
- `len(assignments) == scheme`
- `assignments[i].karaka_rank == i + 1` for all i (consecutive from 1)
- All planet names in `assignments` are distinct
- `atmakaraka == assignments[0].planet`

**`KarakaConditionProfile`:**
- `karaka_rank` ∈ [1, 8]
- `planet_type` is a valid `KarakaPlanetType` value
- `is_atmakaraka` is `True` if and only if `karaka_rank == 1`
- `is_darakaraka` is `True` if and only if `karaka_rank == scheme`

**`JaiminiChartProfile`:**
- `scheme` ∈ {7, 8}
- `len(profiles) == scheme`
- `has_ties == True` if and only if `tie_count >= 1`
- `has_ties == False` if and only if `tie_count == 0`

**`KarakaPair`:**
- `planet_a != planet_b`
- `involves_node` is `True` if and only if either `type_a` or `type_b` is `NODE`
- `both_are_nodes` is `True` if and only if both `type_a` and `type_b` are `NODE`
- `both_are_nodes` implies `involves_node`

---

### §8.2 Truth Invariants

- `KARAKA_NAMES_7` and `KARAKA_NAMES_8` are immutable. No function modifies or
  overrides them at runtime.
- `_POOL_7` and `_POOL_8` are immutable tuples. Pool membership defines which planets
  are valid in a given scheme.
- `KarakaAssignment.sidereal_longitude` always stores the original pre-inversion
  longitude normalised to [0, 360), even for Rahu.
- `KarakaAssignment.degree_in_sign` always stores the effective sort key (inverted
  for Rahu, un-inverted for all others).
- Ketu is never present in any assignment, even if supplied in the input dict.

---

### §8.3 Aggregate Invariants

**`JaiminiChartProfile`:**
- `atmakaraka_planet` equals `profiles[0].planet`
- `darakaraka_planet` equals `profiles[-1].planet`
- `has_node_atmakaraka` is `True` if and only if `profiles[0].planet_type == KarakaPlanetType.NODE`
- `has_node_darakaraka` is `True` if and only if `profiles[-1].planet_type == KarakaPlanetType.NODE`
- All planet names across `profiles` are distinct

---

### §8.4 Network Invariants

**`KarakaPair`:**
- `both_are_nodes` implies `involves_node`; `involves_node` does not imply `both_are_nodes`
- `karaka_pair()` raises `ValueError` if either role name is absent from the result
  (e.g. requesting `Putrakaraka` from a 7-scheme result)

---

## Part IV — Failure Doctrine

### §9.1 Invalid Inputs

- Passing `scheme` outside {7, 8} to `jaimini_karakas()` raises `ValueError`.
- Constructing `JaiminiPolicy` with `scheme` outside {7, 8} raises `ValueError`.
- Requesting an 8-scheme computation without `'Rahu'` in `sidereal_longitudes` raises
  `KeyError`.
- Requesting any scheme without all required pool planets raises `KeyError`.
- Constructing `KarakaAssignment` with `karaka_rank` outside [1, 8] raises `ValueError`.
- Constructing `KarakaAssignment` with an empty `planet` string raises `ValueError`.
- Constructing `KarakaAssignment` with `degree_in_sign` outside [0.0, 30.0] raises
  `ValueError`.
- Constructing `KarakaAssignment` with `sidereal_longitude` outside [0.0, 360.0)
  raises `ValueError`.
- Constructing `KarakaPair` with the same planet in both roles raises `ValueError`.
- Constructing `KarakaPair` with `involves_node` inconsistent with the supplied
  planet types raises `ValueError`.
- Calling `karaka_pair()` with a role name absent from the result raises `ValueError`.

---

### §9.2 Search Exhaustion

This subsystem does not perform iterative search. All computation is a single sort
over at most 8 values. There is no search exhaustion failure mode.

---

### §9.3 Invariant Failure

- `validate_jaimini_output()` raises `ValueError` with a descriptive message if:
  - `scheme` is not 7 or 8
  - `len(assignments)` does not equal `scheme`
  - Any `karaka_rank` is not in consecutive order beginning at 1
  - Any `karaka_name` does not match the canonical name list at its index
  - Any planet name is not in the pool for the scheme
  - Any planet name appears more than once
  - `atmakaraka` does not equal `assignments[0].planet`
  - Any `tie_warnings` entry references a self-pair or a planet outside the pool
- `JaiminiKarakaResult.__post_init__` raises `ValueError` on construction if scheme,
  assignment count, rank sequence, planet uniqueness, or atmakaraka-field consistency
  are violated.
- `JaiminiChartProfile.__post_init__` raises `ValueError` on construction if scheme,
  profile count, or has_ties/tie_count consistency are violated.

---

## Part V — Determinism Standard

### §10. Determinism Guarantees

- `jaimini_karakas()` is fully deterministic: given the same `sidereal_longitudes`
  dict and `scheme`, the output is identical in every call with no dependency on
  external state.
- When two planets share exactly the same effective degree (a tie), the tiebreaker is
  pool-index ordering. This is stable: the same pair of tied planets will always
  resolve in the same order.
- `karaka_condition_profile()`, `jaimini_chart_profile()`, `karaka_pair()`, and
  `validate_jaimini_output()` are pure functions with no side effects.
- Import-time side effects: none. The module initialises only module-level constants.
- No ephemeris access, database access, or external state is required at any point.
  The computation is a single in-memory sort over at most 8 values.

---

## Part VI — Validation Codex

### §11. Minimum Validation Commands

The following command must pass without error on any constitutionally correct
installation of this subsystem:

```
python -m pytest tests/unit/test_jaimini.py -v
```

All tests in `test_jaimini.py` must pass. The test suite validates:
- `KARAKA_NAMES_7` and `KARAKA_NAMES_8` structure and no-duplicate invariants
- `jaimini_karakas()` 7-scheme: rank order, atmakaraka, karaka name assignment,
  degree_in_sign computation, is_rahu_inverted, no spurious tie_warnings
- `jaimini_karakas()` 8-scheme: Rahu inclusion, 8-karaka names, Ketu exclusion
- Rahu degree inversion: effective degree and sidereal_longitude storage
- `atmakaraka()` convenience function correctness
- Tie detection: same-degree produces tie_warnings; distinct degrees do not
- Error handling: invalid scheme raises, missing planet raises, extra keys ignored
- `JaiminiKarakaResult` and `KarakaAssignment` frozen/slot constraints
- `KarakaRole` and `KarakaPlanetType` classification constants
- `JaiminiPolicy` construction, scheme validation, policy override in `jaimini_karakas()`
- `JaiminiKarakaResult` inspectability: `by_planet()`, `by_karaka()`, `darakaraka`,
  `has_ties`
- `KarakaAssignment.__post_init__` guard behavior for all guard conditions
- `JaiminiKarakaResult.__post_init__` guard behavior: bad scheme, wrong count,
  duplicate planet, atmakaraka mismatch, out-of-sequence rank
- `karaka_condition_profile()`: is_atmakaraka, is_darakaraka, planet_type,
  is_rahu_inverted flags
- `jaimini_chart_profile()`: scheme, atmakaraka_planet, darakaraka_planet, profile
  count, has_node_atmakaraka, has_ties, tie_count
- `JaiminiChartProfile.__post_init__` guard behavior: has_ties/tie_count consistency
- `karaka_pair()`: role correctness, planet correctness, involves_node, both_are_nodes
- `KarakaPair.__post_init__` guard behavior: same-planet, inconsistent involves_node
- `validate_jaimini_output()`: valid result accepted, wrong karaka_name detected,
  planet outside pool detected, self-pair tie_warning detected

---

### §12. Required Validation Themes

Any validation suite for this subsystem must demonstrate the following:

1. **Rank monotonicity** — for a set of distinct planetary degrees, the ranked
   sequence is in strictly descending order of effective degree.
2. **Rahu inversion correctness** — Rahu at a known longitude produces the expected
   inverted effective degree; `sidereal_longitude` stores the pre-inversion value.
3. **Rahu boundary case** — Rahu at exactly 0° in sign (degree_in_sign = 30.0) is
   accepted without error.
4. **Scheme isolation** — a 7-scheme computation never includes Rahu; an 8-scheme
   computation always includes Rahu; Ketu is never included in either.
5. **Tiebreaker determinism** — two calls with identical tied inputs produce identical
   ranked sequences.
6. **Policy override** — `JaiminiPolicy.scheme` overrides the `scheme` positional
   argument.
7. **Guard completeness** — every field-level invariant on `KarakaAssignment` and
   `JaiminiKarakaResult` is covered by at least one rejection test.
8. **Condition profile fidelity** — `karaka_condition_profile()` sets
   `is_atmakaraka` only for rank 1 and `is_darakaraka` only for the last rank of
   the scheme.
9. **Aggregate consistency** — `jaimini_chart_profile()` has_ties and tie_count
   are consistent with the source result's tie_warnings.
10. **Network integrity** — `karaka_pair()` raises for an absent role; `KarakaPair`
    raiseswhen `planet_a == planet_b` or when `involves_node` is inconsistent with
    the supplied planet types.
