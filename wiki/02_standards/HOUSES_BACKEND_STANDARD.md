## Moira Houses Backend Standard

### Governing Principle

The Moira houses backend is a sovereign computational subsystem. Its definitions,
layer boundaries, invariants, failure doctrine, and determinism rules are stated
here and are frozen until explicitly superseded by a revision to this document.

This document reflects current implementation truth as of Phase 11 (1 189 passing tests
across 10 unit files and 1 integration file). It does not describe aspirational future
capabilities.

---

## Part I — Architecture Standard

### 1. Authoritative Computational Definitions

#### 1.1 House cusp

A **house cusp** in Moira is:

> An ecliptic longitude in degrees `[0, 360)` that marks the opening boundary of
> one of the twelve astrological houses for a given observer location, Julian date,
> and house system.

| Element | Definition |
|---|---|
| *ecliptic longitude* | Degrees along the ecliptic, normalised to `[0, 360)` by `normalize_degrees` |
| *observer location* | Geographic latitude `[-90, 90]` and longitude `[-180, 180]` in decimal degrees |
| *Julian date* | UT1-based Julian day number |
| *house system* | One of the 19 recognised `HouseSystem` codes |

Twelve cusps are always produced. No system produces fewer or more than 12.

#### 1.2 House

A **house** in Moira is:

> The half-open ecliptic arc `[cusps[n-1], cusps[n % 12])` for house number `n`
> (1–12), where arcs are measured as forward arcs on the circle.

| Rule | Definition |
|---|---|
| *interval* | House n owns `[cusps[n-1], cusps[n % 12])` — opening cusp included, next cusp excluded |
| *forward arc* | `(end - start) % 360°` — always non-negative, never assumes monotonic cusps |
| *membership test* | `(longitude - cusps[n-1]) % 360° < span_n` |
| *opening cusp ownership* | A longitude coinciding with a cusp belongs to the house that opens at that cusp |

#### 1.3 Ecliptic longitude placement

A **placement** is:

> The result of assigning one normalised ecliptic longitude to exactly one house
> under the interval rule using a specific set of 12 cusps.

| Guarantee | Description |
|---|---|
| *completeness* | Every longitude maps to exactly one house — no gaps, no overlaps |
| *determinism* | The same longitude and the same cusps always yield the same house |
| *normalisation* | Input is normalised to `[0, 360)` before membership evaluation |
| *exact-on-cusp* | When the distance to the opening cusp is `< 1e-9°`, `exact_on_cusp` is True; the point is still in that house |

#### 1.4 Angularity category

An **angularity category** is:

> A structural label derived from the assigned house number alone, independent
> of cusp positions, system family, or latitude.

| Category | Houses |
|---|---|
| `ANGULAR` | 1, 4, 7, 10 |
| `SUCCEDENT` | 2, 5, 8, 11 |
| `CADENT` | 3, 6, 9, 12 |

#### 1.5 Cusp proximity

**Cusp proximity** is:

> The forward-arc distance from a placed longitude to its nearest bracketing cusp,
> evaluated against an explicit caller-declared threshold.

| Distance | Formula |
|---|---|
| `dist_to_opening` | `(longitude - opening_cusp) % 360°` |
| `dist_to_closing` | `(closing_cusp - longitude) % 360°` |
| `house_span` | `dist_to_opening + dist_to_closing` (identity to `< 1e-9°`) |
| `nearest_cusp_distance` | `min(dist_to_opening, dist_to_closing)`; tie-break to opening cusp |
| `is_near_cusp` | `nearest_cusp_distance < near_cusp_threshold` |

#### 1.6 Signed cusp delta

A **signed cusp delta** between two systems is:

> `(right.cusps[i] - left.cusps[i]) % 360° - 360°` when `> 180°`, else
> `(right.cusps[i] - left.cusps[i]) % 360°`.

Result is always in the range `(-180°, 180°]`. Positive means the right cusp is
counter-clockwise ahead of the left; negative means behind.

---

### 2. Layer Structure

The backend is organised into ten phases. Each phase operates only on outputs
produced by phases below it. No phase reaches upward.

```
Phase  1 — Truth preservation           (HouseCusps: system / effective_system / fallback)
Phase  2 — Classification               (HouseSystemFamily, HouseSystemCuspBasis, HouseSystemClassification)
Phase  3 — Inspectability               (HouseCusps.__post_init__, _POLAR_SYSTEMS, _KNOWN_SYSTEMS)
Phase  4 — Policy                       (UnknownSystemPolicy, PolarFallbackPolicy, HousePolicy)
Phase  5 — Point-to-house membership    (HousePlacement, assign_house)
Phase  6 — Cusp proximity               (HouseBoundaryProfile, describe_boundary)
Phase  7 — Angularity                   (HouseAngularity, HouseAngularityProfile, describe_angularity)
Phase  8 — System comparison            (HouseSystemComparison, HousePlacementComparison, compare_systems, compare_placements)
Phase  9 — Chart-wide distribution      (HouseOccupancy, HouseDistributionProfile, distribute_points)
Phase 10 — Subsystem hardening         (invariant register, failure-behavior freeze, terminology alignment)
```

#### Layer boundary rules

A function in phase N:

- **may** consume any result vessel from phases 1 through N−1
- **may not** re-run cusp arithmetic
- **may not** re-perform house membership independently of `assign_house`
- **may not** mutate a vessel produced by an earlier phase
- **may not** introduce new doctrine inputs that are not explicit parameters

---

### 3. Supported Systems

19 house system codes are recognised. `_KNOWN_SYSTEMS` is the authoritative frozenset.

| Code | Name | Family | Cusp basis | Lat-sensitive | Polar-capable |
|---|---|---|---|---|---|
| `W` | Whole Sign | `WHOLE_SIGN` | `ECLIPTIC` | No | Yes |
| `E` | Equal | `EQUAL` | `ECLIPTIC` | No | Yes |
| `V` | Vehlow | `EQUAL` | `ECLIPTIC` | No | Yes |
| `M` | Morinus | `EQUAL` | `EQUATORIAL` | No | Yes |
| `X` | Meridian | `EQUAL` | `EQUATORIAL` | No | Yes |
| `O` | Porphyry | `QUADRANT` | `QUADRANT_TRISECTION` | Yes | Yes |
| `P` | Placidus | `QUADRANT` | `SEMI_ARC` | Yes | **No** |
| `B` | Alcabitius | `QUADRANT` | `SEMI_ARC` | Yes | Yes |
| `K` | Koch | `QUADRANT` | `OBLIQUE_ASCENSION` | Yes | **No** |
| `C` | Campanus | `QUADRANT` | `PRIME_VERTICAL` | Yes | Yes |
| `H` | Azimuthal | `QUADRANT` | `HORIZON` | Yes | Yes |
| `R` | Regiomontanus | `QUADRANT` | `POLAR_PROJECTION` | Yes | Yes |
| `T` | Topocentric | `QUADRANT` | `POLAR_PROJECTION` | Yes | Yes |
| `CT` | Carter | `QUADRANT` | `EQUATORIAL` | Yes | Yes |
| `PS` | Pullen SD | `QUADRANT` | `SINUSOIDAL` | Yes | **No** |
| `PR` | Pullen SR | `QUADRANT` | `SINUSOIDAL` | Yes | Yes |
| `U` | Krusinski | `QUADRANT` | `GREAT_CIRCLE` | Yes | Yes |
| `Y` | APC | `QUADRANT` | `APC_FORMULA` | Yes | Yes |
| `N` | Sunshine | `SOLAR` | `SOLAR_POSITION` | No | Yes |

**Polar-incapable systems** (`_POLAR_SYSTEMS`): `P`, `K`, `PS`.
These three produce geometrically disordered cusps above the critical latitude
`90° − obliquity` (≈ 66.56° at J2000) and fall back to Porphyry under the default
policy. Pullen SR (`PR`) uses a different sinusoidal formula and remains geometrically
valid to 90°; it is not in `_POLAR_SYSTEMS`.

#### QUADRANT H1 exception

For `QUADRANT` family systems with `cusp_basis == HORIZON` (Azimuthal, code `H`),
`cusps[0]` is a horizon-derived cusp and legitimately differs from the geographic
Ascendant. The `__post_init__` guard that asserts `cusps[0] == asc` is skipped for
this basis. All non-quadrant families also legitimately place H1 ≠ ASC.

---

### 4. Delegated Assumptions

The houses backend delegates to external modules without redefining them.

| Concern | Delegated to | Convention |
|---|---|---|
| Longitude normalisation | `moira.coordinates.normalize_degrees` | Returns `[0, 360)` |
| Time conversion (UT1 → TT) | `moira.julian.ut_to_tt` | Julian days |
| True obliquity | `moira.obliquity.true_obliquity` | Degrees |
| Nutation | `moira.obliquity.nutation` | `(dpsi, deps)` in degrees |
| Local sidereal time | `moira.julian.local_sidereal_time` | ARMC in degrees |
| Sign labelling | `moira.constants.sign_of` | `(name, symbol, degree_within_sign)` |
| Sun longitude (Sunshine only) | `moira.planets.sun_longitude` | Degrees; lazily imported |

The backend does not redefine any of these. Changes to those modules propagate
automatically to all cusp computations.

---

### 5. Public Surface

All public names are declared in the module `moira/houses.py`.

#### Enumerations

| Name | Members |
|---|---|
| `HouseSystemFamily` | `EQUAL`, `QUADRANT`, `WHOLE_SIGN`, `SOLAR` |
| `HouseSystemCuspBasis` | `ECLIPTIC`, `EQUATORIAL`, `SEMI_ARC`, `OBLIQUE_ASCENSION`, `QUADRANT_TRISECTION`, `PRIME_VERTICAL`, `HORIZON`, `POLAR_PROJECTION`, `SINUSOIDAL`, `GREAT_CIRCLE`, `APC_FORMULA`, `SOLAR_POSITION` |
| `HouseAngularity` | `ANGULAR`, `SUCCEDENT`, `CADENT` |
| `UnknownSystemPolicy` | `FALLBACK_TO_PLACIDUS`, `RAISE` |
| `PolarFallbackPolicy` | `FALLBACK_TO_PORPHYRY`, `RAISE`, `EXPERIMENTAL_SEARCH` |

#### Frozen dataclass vessels

| Vessel | Phase | Primary fields |
|---|---|---|
| `HouseSystemClassification` | 2 | `family`, `cusp_basis`, `latitude_sensitive`, `polar_capable` |
| `HousePolicy` | 4 | `unknown_system`, `polar_fallback` |
| `HouseCusps` | 1–4 | `system`, `cusps` (immutable tuple), `asc`, `mc`, `armc`, `vertex`, `anti_vertex`, `effective_system`, `fallback`, `fallback_reason`, `classification`, `policy` |
| `HousePlacement` | 5 | `house`, `longitude`, `house_cusps`, `exact_on_cusp`, `cusp_longitude` |
| `HouseBoundaryProfile` | 6 | `placement`, `opening_cusp`, `closing_cusp`, `dist_to_opening`, `dist_to_closing`, `house_span`, `nearest_cusp`, `nearest_cusp_distance`, `near_cusp_threshold`, `is_near_cusp` |
| `HouseAngularityProfile` | 7 | `placement`, `category`, `house` |
| `HouseSystemComparison` | 8 | `left`, `right`, `cusp_deltas`, `systems_agree`, `fallback_differs`, `families_differ` |
| `HousePlacementComparison` | 8 | `longitude`, `placements`, `houses`, `all_agree`, `angularity_agrees` |
| `HouseOccupancy` | 9 | `house`, `count`, `longitudes`, `placements`, `is_empty` |
| `HouseDistributionProfile` | 9 | `house_cusps`, `point_count`, `occupancies`, `counts`, `empty_houses`, `dominant_houses`, `angular_count`, `succedent_count`, `cadent_count` |

#### Computation functions

| Function | Signature | Phase |
|---|---|---|
| `classify_house_system` | `(code: str) -> HouseSystemClassification` | 2 |
| `calculate_houses` | `(jd_ut, latitude, longitude, system='P', *, policy=None) -> HouseCusps` | 1–4 |
| `assign_house` | `(longitude, house_cusps) -> HousePlacement` | 5 |
| `describe_boundary` | `(placement, *, near_cusp_threshold=3.0) -> HouseBoundaryProfile` | 6 |
| `describe_angularity` | `(placement) -> HouseAngularityProfile` | 7 |
| `compare_systems` | `(left, right) -> HouseSystemComparison` | 8 |
| `compare_placements` | `(longitude, *house_cusps_seq) -> HousePlacementComparison` | 8 |
| `distribute_points` | `(longitudes, house_cusps) -> HouseDistributionProfile` | 9 |

#### Module-level constants

| Name | Value | Meaning |
|---|---|---|
| `_MEMBERSHIP_CUSP_TOLERANCE` | `1e-9` | Degrees; threshold for `exact_on_cusp` detection |
| `_NEAR_CUSP_DEFAULT_THRESHOLD` | `3.0` | Degrees; default for `describe_boundary` |
| `_POLAR_SYSTEMS` | `frozenset{'P','K','PS'}` | Systems that produce invalid cusps above the critical latitude |
| `_KNOWN_SYSTEMS` | `frozenset` of 19 codes | All recognised `HouseSystem` values |
| `_ANGULARITY_MAP` | `dict[int, HouseAngularity]` | Static 12-entry lookup; never recomputed |

---

### 6. Fallback and Policy Doctrine

#### 6.1 Fallback triggers

Two conditions can redirect the computation away from the default polar fallback path. Both are evaluated before any cusp arithmetic.

| Trigger | Condition | Default behaviour | Strict behaviour |
|---|---|---|---|
| Critical latitude | `abs(latitude) >= 90° − obliquity` and `system in _POLAR_SYSTEMS` | Substitute Porphyry | Raise `ValueError` |
| Unknown system | `system not in _KNOWN_SYSTEMS` | Substitute Placidus | Raise `ValueError` |

The critical latitude is computed from the chart's actual obliquity at call time.
At J2000 obliquity (23.4377°) this is ≈ 66.56° — the geometric Arctic Circle,
above which some ecliptic degrees become circumpolar and the standard fixed-point
semi-arc iteration can produce geometrically invalid cusp orderings. The old fixed
75.0° threshold was incorrect: it silently returned invalid cusp sets from ≈66.6°
to 74.9°.

This does **not** mean Placidus is mathematically impossible above the critical
latitude. The 77°N branch-search experiment showed that valid, ordered Placidus
solutions can exist in narrow ARMC regimes. Moira therefore distinguishes between:

- globally supported behavior (default production path)
- conditionally solvable high-latitude cases (experimental search path)
- unsupported cases where the current production solver cannot recover a valid branch

Critical latitude takes precedence over unknown system when both conditions are true.

#### 6.2 Fallback truth preservation

When a fallback occurs:

| Field | Value |
|---|---|
| `HouseCusps.system` | The **requested** code — never modified |
| `HouseCusps.effective_system` | The **substituted** code actually used |
| `HouseCusps.fallback` | `True` |
| `HouseCusps.fallback_reason` | Human-readable string (see §6.3) |

When no fallback occurs: `fallback = False`, `fallback_reason = None`.

#### 6.3 Fallback reason strings (pattern)

| Trigger | Message pattern |
|---|---|
| Critical latitude + default policy | `"\|lat\| <value>° >= critical latitude <threshold>° (90° − obliquity); '<code>' produces invalid cusps above this threshold; fell back to Porphyry"` |
| Unknown + default policy | `"unknown system code '<code>'; fell back to Placidus"` |

#### 6.3a Experimental high-latitude search

`PolarFallbackPolicy.EXPERIMENTAL_SEARCH` is an explicit opt-in research mode.
It currently applies only to `HouseSystem.PLACIDUS`.

- The engine calls the separate `moira.experimental_placidus` module.
- The search solves the semi-arc equations directly and accepts the result only
  when exactly one ordered cusp cycle exists.
- If no ordered cycle exists, or more than one ordered cycle exists, the call
  raises `ValueError` rather than silently falling back.
- Successful experimental search returns `effective_system == system` and
  `fallback == False`; the experimental nature of the computation remains
  visible through `HouseCusps.policy`.

#### 6.4 Policy factory methods

| Method | `unknown_system` | `polar_fallback` |
|---|---|---|
| `HousePolicy.default()` | `FALLBACK_TO_PLACIDUS` | `FALLBACK_TO_PORPHYRY` |
| `HousePolicy.strict()` | `RAISE` | `RAISE` |
| `HousePolicy.experimental()` | `FALLBACK_TO_PLACIDUS` | `EXPERIMENTAL_SEARCH` |

`HousePolicy.default()` exactly replicates all pre-Phase-4 behaviour.

---

### 7. Invariant Register

#### 7.1 HouseCusps invariants (enforced by `__post_init__`)

| # | Invariant | Violation raises |
|---|---|---|
| C1 | `len(cusps) == 12` | `ValueError` |
| C2 | For QUADRANT family with `cusp_basis != HORIZON`: `abs(cusps[0] - asc) < 1e-9°` | `ValueError` |
| C3 | `fallback == (system != effective_system)` when `effective_system` is set | `ValueError` |
| C4 | `(fallback_reason is None) == (not fallback)` | `ValueError` |
| C5 | `classification is not None` when `effective_system` is non-empty | `ValueError` |
| C6 | `policy` is a `HousePolicy` | `TypeError` |

#### 7.2 HousePlacement invariants

| # | Invariant |
|---|---|
| P1 | `1 <= house <= 12` |
| P2 | `0.0 <= longitude < 360.0` |
| P3 | `0.0 <= cusp_longitude < 360.0` |
| P4 | `cusp_longitude == house_cusps.cusps[house - 1]` (within `1e-9°`) |

#### 7.3 HouseBoundaryProfile invariants

| # | Invariant |
|---|---|
| B1 | `dist_to_opening >= 0.0` |
| B2 | `dist_to_closing > 0.0` |
| B3 | `abs(dist_to_opening + dist_to_closing - house_span) < 1e-9` |
| B4 | `house_span > 0.0` |
| B5 | `near_cusp_threshold > 0.0` |
| B6 | `nearest_cusp_distance >= 0.0` |
| B7 | `is_near_cusp == (nearest_cusp_distance < near_cusp_threshold)` |

#### 7.4 HouseAngularityProfile invariants

| # | Invariant |
|---|---|
| A1 | `1 <= house <= 12` |
| A2 | `house == placement.house` |
| A3 | `category == _ANGULARITY_MAP[house]` |

#### 7.5 HouseSystemComparison invariants

| # | Invariant |
|---|---|
| SC1 | `len(cusp_deltas) == 12` |
| SC2 | All `d in cusp_deltas` satisfy `-180.0 < d <= 180.0` |
| SC3 | `systems_agree == (left.effective_system == right.effective_system)` |
| SC4 | `fallback_differs == (left.fallback != right.fallback)` |

#### 7.6 HousePlacementComparison invariants

| # | Invariant |
|---|---|
| PC1 | `0.0 <= longitude < 360.0` |
| PC2 | `len(placements) >= 2` |
| PC3 | `len(houses) == len(placements)` |
| PC4 | `houses[i] == placements[i].house` for all i |
| PC5 | `all_agree == (len(set(houses)) == 1)` |
| PC6 | `placements[i].longitude == longitude` for all i |

#### 7.7 HouseOccupancy invariants

| # | Invariant |
|---|---|
| O1 | `1 <= house <= 12` |
| O2 | `count == len(longitudes) == len(placements)` |
| O3 | `is_empty == (count == 0)` |
| O4 | `pl.house == house` for all `pl in placements` |

#### 7.8 HouseDistributionProfile invariants

| # | Invariant |
|---|---|
| D1 | `len(occupancies) == 12` |
| D2 | `len(counts) == 12` |
| D3 | `point_count == sum(counts)` |
| D4 | `angular_count + succedent_count + cadent_count == point_count` |
| D5 | `occupancies[i].house == i + 1` for all i |
| D6 | `counts[i] == occupancies[i].count` for all i |
| D7 | `dominant_houses == ()` when `point_count == 0` |
| D8 | `counts[h-1] == max(counts)` for all `h in dominant_houses` when `point_count > 0` |

---

### 8. Determinism and Ordering Rules

The following ordering guarantees are frozen.

| Context | Ordering rule |
|---|---|
| `HouseCusps.cusps` | House 1 at index 0, House 12 at index 11; indices never reordered |
| `HousePlacementComparison.placements` | Same order as systems passed to `compare_placements` |
| `HousePlacementComparison.houses` | Parallel to `placements` |
| `HouseDistributionProfile.occupancies` | House 1 at index 0, House 12 at index 11 |
| `HouseDistributionProfile.dominant_houses` | Ascending house number |
| `HouseOccupancy.longitudes` / `.placements` | Input order of `distribute_points` sequence |
| `assign_house` on equal input | Identical output — no state, no randomness |
| `distribute_points` on equal input | Identical output — deterministic via `assign_house` |
| `compare_placements` on equal input | Identical output |

---

### 9. Non-Goals and Excluded Concerns

The following are explicitly outside the scope of `moira/houses.py` and all
Phase 1–10 layers:

| Excluded concern | Notes |
|---|---|
| Planet position computation | Delegated to `moira.planets` |
| Aspect detection | Separate subsystem (`moira/aspects.py`) |
| Dignity scoring | Separate subsystem |
| Interpretation (weak/strong, benefic/malefic) | Never in the backend |
| Chart assembly | Higher-level orchestration |
| Hemisphere / quadrant totals | Deferred; doctrine not yet frozen |
| Harmonic house overlays | Deferred |
| Cross-system distribution comparison | Deferred |
| UI rendering or formatting | Excluded permanently from this file |
| Public API exposure (`__init__`) | Phase 12 |

---

## Part II — Validation Codex

### 10. Validation Environment

**Authoritative runtime:** project `.venv` (Python 3.14, Windows/cmd).

All validation commands must be run as:

```
.venv\Scripts\python.exe -m pytest <target>
```

No test may be marked passing unless it passes in `.venv` with no modifications
to the test file. Tests may not be silenced, skipped without a registered marker,
or monkey-patched to hide real failures.

---

### 11. Test File Register

| File | Phase(s) | Tests | Focus |
|---|---|---|---|
| `tests/unit/test_house_truth_preservation.py` | 1 | 85 | `system` / `effective_system` / `fallback` field integrity |
| `tests/unit/test_house_classification.py` | 2 | 126 | `HouseSystemFamily`, `HouseSystemCuspBasis`, `classify_house_system` |
| `tests/unit/test_house_inspectability.py` | 3 | 222 | `__post_init__` guard paths, `is_quadrant_system`, `is_latitude_sensitive` |
| `tests/unit/test_house_policy.py` | 4 | 51 | `HousePolicy`, `UnknownSystemPolicy`, `PolarFallbackPolicy`, strict raises |
| `tests/unit/test_house_membership.py` | 5 | 128 | `assign_house`, boundary interval, wraparound, exact-on-cusp |
| `tests/unit/test_house_boundary.py` | 6 | 154 | `describe_boundary`, distance doctrine, span-sum identity, threshold |
| `tests/unit/test_house_angularity.py` | 7 | 107 | `describe_angularity`, `_ANGULARITY_MAP`, all 12 houses |
| `tests/unit/test_house_comparison.py` | 8 | 69 | `compare_systems`, `compare_placements`, delta range, agreement flags |
| `tests/unit/test_house_distribution.py` | 9 | 110 | `distribute_points`, occupancy counts, empty/dominant, angularity totals |
| `tests/unit/test_house_hardening.py` | 10 | 133 | Cross-layer consistency, failure behavior, determinism, invariant preservation |
| `tests/unit/test_polar_houses.py` | 3–4 | 3 | Polar fallback at extreme latitudes |
| `tests/integration/test_houses_external_reference.py` | 1 | 1 | Placidus cusps vs external reference values |
| **Total** | | **1 189** | |

---

### 12. Validation Doctrine

#### 12.1 What must be validated per layer

| Layer | Must test |
|---|---|
| Truth preservation | `system` unchanged after fallback; `effective_system` matches what ran; `fallback` is `True` iff they differ; `fallback_reason` is None iff `fallback` is False |
| Classification | `classify_house_system` returns correct family and cusp_basis for all 19 recognised codes and raises on unknown codes |
| Inspectability | `__post_init__` raises concrete runtime exceptions (`ValueError` / `TypeError`) for violated invariants; properties are consistent with classification |
| Policy | Default policy produces no raise; strict policy raises `ValueError` on both polar and unknown triggers; error messages match §6.3 patterns |
| Membership | Every longitude in `[0, 360)` maps to exactly one house; opening cusp belongs to its house; `exact_on_cusp` fires within `1e-9°`; wraparound cusps are handled correctly |
| Boundary | `dist_to_opening + dist_to_closing == house_span` to `< 1e-9°`; `dist_to_closing > 0` always; `is_near_cusp` consistent with `nearest_cusp_distance`; zero/negative threshold raises `ValueError` |
| Angularity | `_ANGULARITY_MAP` covers all 12 houses; `category == _ANGULARITY_MAP[house]`; `house == placement.house` |
| Comparison | `cusp_deltas` all in `(-180, 180]`; `systems_agree` consistent with `effective_system`; `all placement.longitude == longitude` in `HousePlacementComparison` |
| Distribution | 12 occupancies always; `point_count == sum(counts)`; angularity sum == `point_count`; input order preserved; `dominant_houses` sorted ascending |
| Hardening | Cross-layer seam consistency; all failure paths; same input → same output across all public functions |

#### 12.2 Conftest fixture usage (Phase 10 onward)

New tests added from Phase 10 onward must use the session-scoped conftest fixtures
rather than constructing inline `HouseCusps`:

| Fixture | Provides | Scope |
|---|---|---|
| `natal_houses` | `HouseCusps` (Placidus, London 51.5°N / 0.1°W, 2000-01-01 12:00 UTC) | session |
| `moira_engine` | `Moira()` engine instance | session |
| `natal_chart` | Chart for the same reference moment | session |
| `jd_j2000` | `2451545.0` | session |

Tests that require a second system for comparison may construct it inline via
`calculate_houses` with the same reference coordinates.

#### 12.3 What tests must NOT do

- Modify `moira/houses.py` constants or vessel definitions to make a test pass
- Skip a failing test without a registered `KNOWN_ISSUES.yml` entry
- Assert on internal private names (`_circular_diff`, `_porphyry`, etc.) unless
  testing the specific private behaviour is the stated purpose of that test class
- Use `monkeypatch` to suppress a `ValueError` or `TypeError` that the
  implementation is meant to raise

---

### 13. Guaranteed Failure Conditions

The following inputs must always produce the stated error. This table is frozen.

| Function | Bad input | Error raised | Message contains |
|---|---|---|---|
| `calculate_houses` | `system not in _KNOWN_SYSTEMS` + `HousePolicy.strict()` | `ValueError` | `"unknown house system code"` |
| `calculate_houses` | `abs(latitude) >= 90° − obliquity` + `system in _POLAR_SYSTEMS` + `HousePolicy.strict()` | `ValueError` | `"critical latitude"` |
| `calculate_houses` / `houses_from_armc` | `policy` is not a `HousePolicy` | `TypeError` | `"policy must be a HousePolicy"` |
| `assign_house` | `len(house_cusps.cusps) != 12` | `ValueError` | `"exactly 12 cusps"` |
| `describe_boundary` | `near_cusp_threshold <= 0.0` | `ValueError` | `"near_cusp_threshold must be positive"` |
| `compare_placements` | fewer than 2 `HouseCusps` supplied | `ValueError` | `"at least 2"` |

The following inputs must always produce the stated runtime exception at
construction time:

| Vessel | Violated invariant | Raises |
|---|---|---|
| `HouseCusps` | `len(cusps) != 12` | `ValueError` |
| `HouseCusps` | `fallback != (system != effective_system)` | `ValueError` |
| `HouseCusps` | `fallback_reason` present when `fallback` is False | `ValueError` |
| `HouseCusps` | `policy` is not a `HousePolicy` | `TypeError` |
| `HousePlacement` | `house` outside `[1, 12]` | `ValueError` |
| `HousePlacement` | `cusp_longitude` does not match `house_cusps.cusps[house-1]` | `ValueError` |
| `HouseBoundaryProfile` | `dist_to_opening + dist_to_closing != house_span` | `ValueError` |
| `HouseBoundaryProfile` | `is_near_cusp` inconsistent with distances | `ValueError` |
| `HouseAngularityProfile` | `category != _ANGULARITY_MAP[house]` | `ValueError` |
| `HouseSystemComparison` | any delta outside `(-180, 180]` | `ValueError` |
| `HousePlacementComparison` | `len(placements) < 2` | `ValueError` |
| `HousePlacementComparison` | `placement.longitude != longitude` | `ValueError` |
| `HouseOccupancy` | `count != len(longitudes)` | `ValueError` |
| `HouseDistributionProfile` | `point_count != sum(counts)` | `ValueError` |
| `HouseDistributionProfile` | angularity sum != `point_count` | `ValueError` |

---

### 14. Cross-Layer Consistency Requirements

The following cross-layer relationships are required to hold at all times.

| Relationship | Requirement |
|---|---|
| `HousePlacement.cusp_longitude` | Must equal `placement.house_cusps.cusps[placement.house - 1]` |
| `HouseBoundaryProfile.opening_cusp` | Must equal `placement.cusp_longitude` |
| `HouseBoundaryProfile.closing_cusp` | Must equal `placement.house_cusps.cusps[placement.house % 12]` |
| `HouseAngularityProfile.house` | Must equal `placement.house` |
| `HouseAngularityProfile.category` | Must equal `_ANGULARITY_MAP[placement.house]` |
| `HousePlacementComparison.longitude` | Must equal `pl.longitude` for every `pl` in `placements` |
| `HouseOccupancy.placements[i].house` | Must equal `occupancy.house` for all i |
| `HouseDistributionProfile.counts[i]` | Must equal `occupancies[i].count` for all i |
| `HouseDistributionProfile.angular_count` | Must equal `sum(counts[h-1] for h in (1,4,7,10))` |
| `HouseCusps.classification` | Must equal `classify_house_system(effective_system)` |
| `HouseCusps.is_quadrant_system` | Must equal `classification.family == HouseSystemFamily.QUADRANT` |
| `HouseCusps.is_latitude_sensitive` | Must equal `classification.latitude_sensitive` |

---

### 15. Scope-Freeze Statement

The Moira houses backend is hereby frozen at Phase 10. The following changes
require an explicit revision to this document before implementation:

- Adding a new public vessel or computation function
- Adding a field to any existing vessel
- Changing the default value of any function parameter
- Changing the boundary condition of any interval rule or distance formula
- Adding a new house system code to `_KNOWN_SYSTEMS`
- Changing the critical-latitude formula (`90° − obliquity`)
- Changing the cusp tolerance (`1e-9°`)
- Changing the default near-cusp threshold (`3.0°`)
- Changing the angularity map (`_ANGULARITY_MAP`)
- Exposing any name through `__init__` (Phase 12)

The following changes do not require a revision:

- Adding new tests within an existing test class
- Adding docstring clarifications that do not change stated doctrine
- Performance improvements that produce identical outputs
- Fixing a defect where the implementation violates a stated invariant in this document

