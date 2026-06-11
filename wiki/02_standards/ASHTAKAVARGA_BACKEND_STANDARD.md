# Moira Ashtakavarga Backend Standard

Version: 1.0
Date: 2026-06-11
Status: Current implementation truth; P9-09 REST admission prerequisite

## Governing Principle

The Moira Ashtakavarga backend is a Parashari rekha-distribution subsystem. It
preserves the encoded Raman 1981 rekha tables, per-planet
Bhinnashtakavarga, chart-level Sarvashtakavarga, optional shodhana reductions,
transit-strength lookup, sign-strength profiles, and aggregate chart profile
truth from caller-supplied sidereal longitudes or sign indices.

This document reflects current implementation truth. It is not a promise that
the module derives sidereal positions, ayanamsa, chart houses, or Lagna
internally.

---

## Part I - Architecture Standard

### 1. Authoritative Computational Definitions

#### 1.1 Rekha table

A **rekha table** in Moira is:

> A Raman 1981-encoded mapping from assessed planet and reference body to the
> 1-based sign distances that receive a benefic point.

The table covers:

- seven assessed classical planets
- eight references: the seven classical planets plus Lagna
- twelve possible 1-based sign distances

#### 1.2 Bhinnashtakavarga

A **Bhinnashtakavarga result** is:

> One assessed planet's 12-sign rekha vector, computed by counting benefic
> points from all eight reference positions.

| Field | Meaning |
|---|---|
| `planet` | Assessed classical planet |
| `rekhas` | 12-entry tuple, Aries through Pisces |
| `total_rekhas` | Sum of the 12 rekha counts |

Each rekha count is in `[0, 8]`.

#### 1.3 Sarvashtakavarga

A **Sarvashtakavarga result** is:

> The sign-by-sign sum of all seven Bhinnashtakavarga vectors.

The grand total is the sum of the seven Raman table totals currently verified
by tests: `337`.

#### 1.4 Shodhana

The backend implements two reductions:

- `trikona_shodhana(...)`: trine-group reduction
- `ekadhipatya_shodhana(...)`: same-ruler reduction after Trikona Shodhana

When enabled by policy, reduced Bhinnashtakavarga and Sarvashtakavarga truth is
preserved separately from the unreduced result. The unreduced result must not
be mutated by shodhana.

#### 1.5 Sign strength profile

A **sign strength profile** is:

> One planet/sign rekha count interpreted against the policy threshold.

The default strong threshold is `4`.

#### 1.6 Chart profile

An **Ashtakavarga chart profile** is:

> Aggregate intelligence over the Sarvashtakavarga and the per-planet
> Bhinnashtakavarga vectors.

It reports Sarva total, max/min sign indices, strong-sign counts by planet,
and the ayanamsa provenance label.

---

### 2. Layer Structure

The backend is organized around the constitutional phases declared in
`moira/ashtakavarga.py`:

```text
P1  - Truth preservation             (BhinnashtakavargaResult, AshtakavargaResult)
P2  - Classification constants       (RekhaTier)
P3  - Inspectability                 (for_sign, strong_signs, for_planet)
P4  - Policy surface                 (AshtakavargaPolicy)
P7  - Local condition profile        (SignStrengthProfile)
P8  - Aggregate chart profile        (AshtakavargaChartProfile)
P10 - Hardening                      (__post_init__ guards, validate_ashtakavarga_output)
P12 - Public API curation            (__all__, root/vedic/facade exports)
```

Layer boundary rules:

- `bhinnashtakavarga(...)` consumes sign indices and does not derive them from
  longitudes.
- `ashtakavarga(...)` consumes sidereal longitudes and reduces them to sign
  indices. It does not perform tropical-to-sidereal conversion.
- Shodhana products are separate result fields and must not mutate unreduced
  Bhinnashtakavarga truth.
- `sign_strength_profile(...)` consumes a `BhinnashtakavargaResult`; it does
  not recompute rekha vectors.
- `ashtakavarga_chart_profile(...)` consumes an `AshtakavargaResult`; it does
  not recompute the result from ad hoc fields.

---

### 3. Doctrine and Policy Surface

The current doctrine is the Parashari Ashtakavarga system encoded from B.V.
Raman, *Ashtakavarga System of Prediction* (1981). Raman is the committed table
authority for this implementation.

`AshtakavargaPolicy` currently exposes:

| Field | Default | Meaning |
|---|---|---|
| `ayanamsa_system` | `Lahiri` | Provenance label for upstream sidereal reduction |
| `strong_threshold` | `4` | Inclusive rekha threshold for strong sign classification |
| `apply_trikona_shodhana` | `False` | Enables Trikona Shodhana products |
| `apply_ekadhipatya_shodhana` | `False` | Enables Ekadhipatya after Trikona Shodhana |

`apply_ekadhipatya_shodhana=True` requires
`apply_trikona_shodhana=True`.

---

### 4. Public Surface

All public names are declared in `moira/ashtakavarga.py`.

#### Constants and registries

| Name | Meaning |
|---|---|
| `RekhaTier` | Strong/weak rekha tier constants |
| `REKHA_TABLES` | Raman 1981 rekha distance tables |

#### Frozen dataclass vessels

| Vessel | Primary fields |
|---|---|
| `AshtakavargaPolicy` | ayanamsa label, threshold, shodhana flags |
| `BhinnashtakavargaResult` | planet, rekhas, total rekhas |
| `AshtakavargaResult` | ayanamsa label, bhinna map, sarva vector, optional shodhana products |
| `SignStrengthProfile` | planet, sign index, rekha count, tier |
| `AshtakavargaChartProfile` | sarva total/max/min, strong counts, ayanamsa label |

#### Computation functions

| Function | Signature | Meaning |
|---|---|---|
| `bhinnashtakavarga` | `(planet, sign_indices) -> BhinnashtakavargaResult` | Compute one planet's BAV |
| `trikona_shodhana` | `(rekhas) -> tuple[int, ...]` | Apply trine reduction |
| `ekadhipatya_shodhana` | `(rekhas, sign_indices) -> tuple[int, ...]` | Apply same-ruler reduction |
| `ashtakavarga` | `(sidereal_longitudes, ayanamsa_system=None, policy=None) -> AshtakavargaResult` | Compute chart-level AV |
| `transit_strength` | `(planet, transit_sign_index, bhinna) -> int` | Read transit rekha count |
| `sign_strength_profile` | `(bhinna, sign_idx, policy=None) -> SignStrengthProfile` | Build local sign profile |
| `ashtakavarga_chart_profile` | `(result, policy=None) -> AshtakavargaChartProfile` | Build chart aggregate profile |
| `validate_ashtakavarga_output` | `(result) -> None` | Validate output invariants |

---

### 5. Determinism and Failure Doctrine

#### 5.1 Determinism

- Sign order is Aries through Pisces, index `0` through `11`.
- Reference order is `Sun`, `Moon`, `Mars`, `Mercury`, `Jupiter`, `Venus`,
  `Saturn`, `Lagna`.
- Planet order is the seven classical planets in the module order.
- Sidereal longitudes are reduced by modulo 360 and whole-sign division.
- Extra keys in `ashtakavarga(...)` inputs are ignored.
- Shodhana can only reduce rekha counts and leaves raw fields intact.

#### 5.2 Failure doctrine

The subsystem fails loudly on:

- unsupported assessed planet names
- missing required reference keys
- invalid sign indices
- malformed rekha vector lengths
- rekha values outside `[0, 8]`
- total rekha mismatches
- empty ayanamsa labels
- strong thresholds outside `[1, 8]`
- Ekadhipatya requested without Trikona
- inconsistent Sarvashtakavarga sums
- orphaned or inconsistent shodhana fields

---

## Part II - Validation Codex

### 6. Validation Scope

The Ashtakavarga backend is currently validated through:

- `tests/unit/test_ashtakavarga.py`
- public API surface checks in `tests/unit/test_api_surface_adversarial_audit.py`
- public doctrine surface checks in `tests/unit/test_public_doctrine_surfaces.py`

### 7. Validation Claims

The following claims are currently verified:

1. `REKHA_TABLES` structure and value ranges are valid.
2. Raman 1981 planet totals and row cardinalities are preserved.
3. Bhinnashtakavarga vectors have 12 entries and valid rekha ranges.
4. Known hand-calculated sign values match expected results.
5. Sarvashtakavarga is the signwise sum of all seven BAV vectors.
6. Longitude-to-sign conversion respects boundaries and modulo wrapping.
7. Transit strength reads the corresponding BAV sign count.
8. Policy rejects invalid thresholds and invalid shodhana flag combinations.
9. Trikona and Ekadhipatya Shodhana arithmetic and invariants are preserved.
10. Shodhana products are present only when policy requires them and validate
    structurally.
11. Sign and chart profile summaries preserve threshold and aggregate truth.
12. Public exports remain visible through `moira`, `moira.vedic`, and
    `moira.facade`.

### 8. Validation Commands

The minimum verification slice for this standard is:

```powershell
.\.venv\Scripts\python.exe -m py_compile moira\ashtakavarga.py tests\unit\test_ashtakavarga.py
.\.venv\Scripts\python.exe -m pytest tests\unit\test_ashtakavarga.py tests\unit\test_public_doctrine_surfaces.py -q
.\.venv\Scripts\python.exe -m pytest tests\unit\test_api_surface_adversarial_audit.py -q
```

---

## Part III - REST Admission Frontier

P9-09 may proceed to REST transport design after this standard.

First admitted REST shape should be direct-sync:

- caller-supplied sidereal longitudes or sign indices
- explicit ayanamsa provenance policy
- full Ashtakavarga result route
- Bhinnashtakavarga route
- transit-strength route
- sign-strength profile route
- chart-profile route

Chart-backed Ashtakavarga routes should be deferred until the server adapter
clearly owns tropical-to-sidereal reduction, Lagna derivation, and ayanamsa
policy truth.
