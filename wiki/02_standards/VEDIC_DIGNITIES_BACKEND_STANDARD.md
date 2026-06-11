# Moira Vedic Dignities Backend Standard

Version: 1.0
Date: 2026-06-11
Status: Current implementation truth; P9-08 REST admission prerequisite

## Governing Principle

The Moira Vedic dignities backend is a Parashari dignity and relationship
subsystem. It preserves dignity rank, planetary friendship, local condition,
and chart-level dignity profile truth from caller-supplied sidereal
longitudes.

This document reflects current implementation truth. It is not a promise that
the module derives sidereal positions, ayanamsa, or chart context internally.

---

## Part I - Architecture Standard

### 1. Authoritative Computational Definitions

#### 1.1 Vedic dignity result

A **Vedic dignity result** in Moira is:

> The dignity rank of one of the seven classical planets at a normalized
> sidereal longitude, using Parashari exaltation, debilitation, Mulatrikona,
> own-sign, and natural friendship tables.

| Field | Meaning |
|---|---|
| `planet` | One of `Sun`, `Moon`, `Mars`, `Mercury`, `Jupiter`, `Venus`, `Saturn` |
| `sidereal_longitude` | Normalized sidereal longitude in `[0, 360)` |
| `sign_index` | Zero-based sidereal sign index |
| `sign` | Sign name from `moira.constants.SIGNS` |
| `dignity_rank` | One of the seven Parashari dignity rank constants |
| `is_exalted` | True in the planet's exaltation sign |
| `is_debilitated` | True in the planet's debilitation sign |
| `is_mulatrikona` | True inside the planet's Mulatrikona sign range |
| `is_own_sign` | True in one of the planet's own signs |
| `exaltation_score` | Linear score from debility point to deepest exaltation point |

#### 1.2 Planetary relationship

A **planetary relationship** is:

> The directed Panchadha Maitri relationship from one participating planet to
> another, composed from natural friendship and temporary friendship.

Relationships are directional. The relation from planet A to planet B may
differ from the relation from B to A.

#### 1.3 Dignity condition profile

A **dignity condition profile** is:

> The local tier classification of one `VedicDignityResult`.

| Tier | Included ranks |
|---|---|
| `strong` | `exaltation`, `mulatrikona`, `own_sign` |
| `neutral` | `friend_sign`, `neutral_sign` |
| `weak` | `enemy_sign`, `debilitation` |

#### 1.4 Chart dignity profile

A **chart dignity profile** is:

> An aggregate profile over a caller-supplied mapping of planet names to
> `VedicDignityResult` vessels.

It reports strong/neutral/weak counts, planet tiers, exaltation scores, and
the strongest/weakest planet by exaltation score.

---

### 2. Layer Structure

The backend is organized around the current constitutional phases declared in
`moira/vedic_dignities.py`:

```text
P2  - Classification constants       (DignityTier)
P3  - Inspectability                 (is_strong, is_weak, is_friendly, is_hostile)
P4  - Policy vessel                  (VedicDignityPolicy)
P7  - Local condition profile        (DignityConditionProfile)
P8  - Aggregate chart profile        (ChartDignityProfile)
P10 - Hardening                      (__post_init__ guards, validate_dignity_output)
P12 - Public API curation            (__all__, root/vedic/facade exports)
```

Layer boundary rules:

- Dignity lookup consumes sidereal longitude; it does not compute sidereal
  reduction.
- Planetary relationship lookup consumes a mapping of sidereal longitudes; it
  does not derive chart positions.
- Profile builders consume existing dignity result vessels; they do not
  recompute dignity rank from ad hoc fields.
- Unknown non-classical planets are rejected by dignity lookup and relationship
  vessels.

---

### 3. Doctrine and Policy Surface

The current doctrine is the classical Parashari seven-planet dignity scheme.
Rahu and Ketu are explicitly outside this subsystem.

`VedicDignityPolicy` currently exposes:

| Field | Default | Meaning |
|---|---|---|
| `ayanamsa_system` | `Lahiri` | Provenance label for sidereal reduction policy used upstream |

The policy vessel does not perform ayanamsa conversion. It records the
sidereal-reduction context for callers and future adapters.

---

### 4. Public Surface

All public names are declared in `moira/vedic_dignities.py`.

#### Constants and registries

| Name | Meaning |
|---|---|
| `VedicDignityRank` | Seven dignity rank constants |
| `CompoundRelationship` | Five Panchadha Maitri compound relationship constants |
| `DignityTier` | Strong/neutral/weak condition tiers |
| `EXALTATION_SIGN` | Planet to exaltation sign index |
| `EXALTATION_DEGREE` | Planet to deepest exaltation degree |
| `DEBILITATION_SIGN` | Planet to debilitation sign index |
| `MULATRIKONA_SIGN` | Planet to Mulatrikona sign index |
| `MULATRIKONA_START` | Planet to Mulatrikona start degree |
| `MULATRIKONA_END` | Planet to Mulatrikona end degree |
| `OWN_SIGNS` | Planet to own-sign indices |
| `NATURAL_FRIENDS` | Natural friends by planet |
| `NATURAL_NEUTRALS` | Natural neutrals by planet |
| `NATURAL_ENEMIES` | Natural enemies by planet |

#### Frozen dataclass vessels

| Vessel | Primary fields |
|---|---|
| `VedicDignityResult` | planet, sidereal longitude, sign, rank, flags, exaltation score |
| `PlanetaryRelationship` | from planet, to planet, natural, temporary, compound |
| `VedicDignityPolicy` | ayanamsa system provenance label |
| `DignityConditionProfile` | planet, rank, tier, score, sign |
| `ChartDignityProfile` | tier counts, strongest/weakest planet, planet tiers, scores |

#### Computation functions

| Function | Signature | Meaning |
|---|---|---|
| `vedic_dignity` | `(planet, sidereal_longitude) -> VedicDignityResult` | Resolve dignity rank for one planet |
| `planetary_relationships` | `(sidereal_longitudes) -> list[PlanetaryRelationship]` | Compute directed relationships among present classical planets |
| `dignity_condition_profile` | `(result) -> DignityConditionProfile` | Build local dignity condition |
| `chart_dignity_profile` | `(dignity_results) -> ChartDignityProfile` | Build aggregate dignity profile |
| `validate_dignity_output` | `(dignity_results) -> None` | Validate output invariants |

---

### 5. Determinism and Failure Doctrine

#### 5.1 Determinism

- Sidereal longitudes are normalized mod 360 before dignity lookup.
- Dignity rank follows a fixed cascade:
  exaltation, debilitation, Mulatrikona, own sign, friend sign, enemy sign,
  neutral sign.
- Mercury's Virgo overlap is resolved by checking exaltation before
  Mulatrikona.
- Planetary relationships are emitted in the seven-planet order for planets
  present in the input mapping.

#### 5.2 Failure doctrine

The subsystem fails loudly on:

- unsupported dignity planets
- invalid result vessel planet names
- invalid result vessel longitude ranges
- invalid sign index or exaltation score ranges
- invalid relationship planet names
- invalid natural or temporary relationship labels
- empty chart profile input
- validation mismatch between result mapping keys and vessel planet names

Unknown keys in `planetary_relationships(...)` are ignored unless the
participating relationship vessel itself is constructed with an invalid planet.

---

## Part II - Validation Codex

### 6. Validation Scope

The Vedic dignities backend is currently validated through:

- `tests/unit/test_vedic_dignities.py`
- public API surface checks in `tests/unit/test_api_surface_adversarial_audit.py`
- public doctrine surface checks in `tests/unit/test_public_doctrine_surfaces.py`

### 7. Validation Claims

The following claims are currently verified:

1. Table constants preserve the expected seven classical planet dignity data.
2. Each dignity rank is reachable for concrete planet/longitude cases.
3. Exaltation score is bounded and reaches expected extrema.
4. Mercury's exaltation/Mulatrikona overlap resolves to exaltation.
5. Longitude wrapping preserves normalized result truth.
6. Rahu, Ketu, outer planets, and invalid planets are rejected where the
   subsystem owns planet validation.
7. Natural, temporary, and compound relationships are computed deterministically.
8. Local condition tiers classify strong, neutral, and weak dignity ranks.
9. Chart dignity profile counts and strongest/weakest summaries are coherent.
10. `validate_dignity_output(...)` catches key/vessel and sign-index mismatches.
11. Public exports remain visible through `moira`, `moira.vedic`, and
    `moira.facade`.

### 8. Validation Commands

The minimum verification slice for this standard is:

```powershell
.\.venv\Scripts\python.exe -m py_compile moira\vedic_dignities.py tests\unit\test_vedic_dignities.py
.\.venv\Scripts\python.exe -m pytest tests\unit\test_vedic_dignities.py tests\unit\test_public_doctrine_surfaces.py -q
.\.venv\Scripts\python.exe -m pytest tests\unit\test_api_surface_adversarial_audit.py -q
```

---

## Part III - REST Admission Frontier

P9-08 may proceed to REST transport design after this standard.

First admitted REST shape should be direct-sync:

- caller-supplied sidereal longitudes
- explicit ayanamsa provenance policy
- dignity result route
- relationship route
- local condition route
- aggregate chart profile route

Chart-backed Vedic dignity routes should be deferred until the server adapter
clearly owns tropical-to-sidereal reduction and records the ayanamsa policy used
to derive the sidereal longitudes.
