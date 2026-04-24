## Moira Triplicity Backend Standard

### Governing Principle

The Moira triplicity backend is a sovereign datum-provider subsystem. Its
definitions, layer boundaries, invariants, failure doctrine, and determinism
rules are stated here and are frozen until explicitly superseded by a
revision to this document.

This document reflects current implementation truth as of Phase 11 (75 passing
tests in `tests/unit/test_triplicity.py`). It does not describe aspirational
future capabilities.

---

## Part I — Architecture Standard

### 1. Authoritative Computational Definitions

#### 1.1 Triplicity

A **triplicity** in Moira is:

> A grouping of exactly three zodiac signs that share the same classical
> element (fire, earth, air, or water) and are governed by the same set of
> three planetary rulers under a given doctrinal authority.

| Element | Signs |
|---|---|
| Fire  | Aries, Leo, Sagittarius |
| Earth | Taurus, Virgo, Capricorn |
| Air   | Gemini, Libra, Aquarius |
| Water | Cancer, Scorpio, Pisces |

Each triplicity has exactly three rulers: a day ruler, a night ruler, and a
participating (mixed-sect) ruler.

#### 1.2 Doctrine

A **triplicity doctrine** in Moira is:

> A named authority that prescribes the precise ruler assignments for each
> triplicity group. Different editions or traditions may assign different
> day/night/participating rulers; each is a distinct doctrine.

Currently only one doctrine is implemented:

| Member | Authority |
|---|---|
| `DOROTHEAN_PINGREE_1976` | Dorotheus of Sidon, *Carmen Astrologicum*, ed. Pingree (Leipzig, 1976) |

#### 1.3 Active ruler

The **active ruler** for a sign in a given sect context is:

> `day_ruler` when `is_day_chart is True`; `night_ruler` otherwise.

The active ruler is the planet that holds full triplicity dignity for that
sign under that sect context.

#### 1.4 Participating ruler

The **participating ruler** is:

> The third ruler in the triplicity triple — neither the day ruler nor the
> night ruler. Its contribution to any scoring computation is governed
> explicitly by `ParticipatingRulerPolicy` at each call site.

The participating ruler's dignitary weight is contested across doctrinal
sources. Moira preserves the ambiguity explicitly rather than silently
embedding a choice.

#### 1.5 Triplicity score

A **triplicity score** in Moira is:

> The integer contribution awarded to one planet for occupying one sign,
> computed as:
>
> - `primary_score` (default 3) if the planet is the active ruler
> - `participating_score` (default 1) if the planet is the participating
>   ruler and `ParticipatingRulerPolicy.AWARD_REDUCED` is in effect
> - `0` otherwise, including when `ParticipatingRulerPolicy.IGNORE` is used

Score values are bounded to `{0, participating_score, primary_score}`.

#### 1.6 TriplicityAssignment

A **TriplicityAssignment** in Moira is:

> An immutable, fully resolved record of one sign's triplicity assignment
> under one doctrine and one sect context. It carries day_ruler,
> night_ruler, participating_ruler, active_ruler, and the canonical
> 3-element signs tuple.

---

### 2. Module Architecture

`moira/triplicity.py` is a **utility / datum-provider** module. It does
not orchestrate computations or call other Moira engines.

The internal structure follows the same phase model as the houses backend,
but because this is a utility module, only four phases are applicable. The
full phase table is:

```
Phase  1 — Truth preservation     (TriplicityDoctrine, doctrine enum; explicit table binding)
Phase  2 — Classification         (TriplicityElement, ParticipatingRulerPolicy)
Phase  3 — Inspectability         (TriplicityAssignment.__post_init__, @property helpers)
Phase  4 — Policy                 (ParticipatingRulerPolicy; explicit call-site declaration)
Phase  5 — (N/A: no position logic)
Phase  6 — (N/A: no proximity computation)
Phase  7 — (N/A: no angularity)
Phase  8 — (N/A: no system comparison)
Phase  9 — (N/A: no chart-wide distribution)
Phase 10 — Subsystem hardening    (invariant register, failure-behavior freeze)
Phase 11 — Architecture freeze    (this document)
Phase 12 — Public API exposure    (moira/__init__.py)
```

#### Layer boundary rules

`triplicity.py`:

- **may** read `moira.constants.SIGNS` for sign validation
- **may not** call any Moira planet, chart, or dignity engine
- **may not** emit astronomical computations (positions, angles, times)
- **may not** access chart context except through explicit `is_day_chart` parameter
- **may not** mutate a `TriplicityAssignment` after construction

---

### 3. Supported Doctrines

| Member | Table variable | Triplicity group coverage |
|---|---|---|
| `DOROTHEAN_PINGREE_1976` | `_TRIPLICITY_RULERS_DOROTHEAN_PINGREE_1976` | All 12 signs (4 triplicity groups) |

The `_TABLES` dict is the registry that maps `TriplicityDoctrine` members to
their ruler tables. A `KeyError` on `_TABLES` lookup is the authorised signal
for an unrecognised doctrine argument.

#### DOROTHEAN_PINGREE_1976 ruler assignments

| Group | Day ruler | Night ruler | Participating ruler |
|---|---|---|---|
| Fire (Aries, Leo, Sagittarius) | Sun | Jupiter | Saturn |
| Earth (Taurus, Virgo, Capricorn) | Venus | Moon | Mars |
| Air (Gemini, Libra, Aquarius) | Saturn | Mercury | Jupiter |
| Water (Cancer, Scorpio, Pisces) | Mars | Venus | Moon |

**Water triplicity scholarly commitment**: The assignment of Mars as the
water-triplicity day ruler follows Pingree's 1976 critical edition of
Dorotheus. Some later redactions assign Mars only to mixed-sect contexts;
Moira preserves Pingree's edition as the canonical source for
`DOROTHEAN_PINGREE_1976`. See module docstring for extended provenance note.

---

### 4. Delegated Assumptions

| Concern | Delegated to | Convention |
|---|---|---|
| Sign name list | `moira.constants.SIGNS` | Ordered list of 12 tropical sign name strings |

No other delegation. All other logic (tables, sign grouping, element lookup,
scoring) is self-contained within `moira/triplicity.py`.

---

### 5. Public Surface

All public names are declared in `moira/triplicity.py` and re-exported from
`moira/__init__.py`.

#### Enumerations

| Name | Members | Inherits |
|---|---|---|
| `TriplicityDoctrine` | `DOROTHEAN_PINGREE_1976` | `StrEnum` |
| `TriplicityElement` | `FIRE`, `EARTH`, `AIR`, `WATER` | `StrEnum` |
| `ParticipatingRulerPolicy` | `IGNORE`, `AWARD_REDUCED` | `StrEnum` |

#### Frozen dataclass vessels

| Vessel | Fields | Guards in `__post_init__` |
|---|---|---|
| `TriplicityAssignment` | `sign`, `doctrine`, `is_day_chart`, `day_ruler`, `night_ruler`, `participating_ruler`, `active_ruler`, `signs` | 5 (see §7) |

#### @property helpers on TriplicityAssignment

| Property | Returns | Derivation |
|---|---|---|
| `element` | `TriplicityElement` | `_SIGNS_TO_ELEMENT[frozenset(signs)]` |
| `inactive_ruler` | `str` | `night_ruler` if `is_day_chart` else `day_ruler` |
| `has_participating_overlap` | `bool` | `participating_ruler == active_ruler` |

#### Computation functions

| Function | Signature | Returns |
|---|---|---|
| `triplicity_assignment_for` | `(sign, *, is_day_chart, doctrine=…) -> TriplicityAssignment` | Fully resolved assignment record |
| `triplicity_score` | `(planet, sign, *, is_day_chart, doctrine=…, participating_policy=…, primary_score=3, participating_score=1) -> int` | Integer score ∈ {0, 1, 3} by default |

#### Module-level private constants

| Name | Purpose |
|---|---|
| `_TRIPLICITY_RULERS_DOROTHEAN_PINGREE_1976` | Ruler table for `DOROTHEAN_PINGREE_1976` doctrine |
| `_DOROTHEAN_PINGREE_SIGN_GROUPS` | Precomputed `triple → signs tuple` map |
| `_TABLES` | Registry: `TriplicityDoctrine → ruler table` |
| `_SIGN_GROUPS` | Registry: `TriplicityDoctrine → sign groups map` |
| `_SIGNS_TO_ELEMENT` | `frozenset(signs) → TriplicityElement` lookup |

---

### 6. Failure Doctrine

#### 6.1 triplicity_assignment_for failure contract

| Condition | Behaviour |
|---|---|
| `sign` not present in table for the given doctrine | `ValueError("Sign <sign> has no triplicity entry in doctrine <doctrine>")` |
| `doctrine` key not in `_TABLES` (raw string or unknown member) | `KeyError` |
| `is_day_chart` is not `bool` | `TypeError("is_day_chart must be bool, …")` via `__post_init__` |
| Any other `__post_init__` guard violation | `ValueError` or `TypeError` (see §7) |
| No partial output on failure | Guaranteed — construction is atomic |

#### 6.2 triplicity_score failure contract

| Condition | Behaviour |
|---|---|
| `sign` not present in table | Returns `0` silently — never raises |
| `planet` not in table for the given sign | Returns `0` silently — never raises |
| `doctrine` key not in `_TABLES` | `KeyError` |
| Invalid or empty string for `planet` | Returns `0` silently |
| Correct inputs | Returns exactly one of: `primary_score`, `participating_score`, or `0` |

The asymmetry between `triplicity_assignment_for` (raises on bad sign) and
`triplicity_score` (returns 0 on bad sign) is intentional. Assignment lookup
is an explicit resolution step where a missing sign is a programming error.
Score lookup is called from scoring loops where absence of rulership is the
expected answer for most planet/sign combinations.

#### 6.3 TriplicityAssignment direct-construction failure contract

Construction of `TriplicityAssignment` directly (outside `triplicity_assignment_for`)
is permitted for testing synthetic assignments. All five `__post_init__` guards
are always enforced:

| Guard | Violation raises |
|---|---|
| `sign not in SIGNS` | `ValueError` |
| `doctrine not isinstance TriplicityDoctrine` | `ValueError` |
| `not isinstance(is_day_chart, bool)` | `TypeError` |
| `active_ruler != (day_ruler if is_day_chart else night_ruler)` | `ValueError` |
| `len(signs) != 3` | `ValueError` |
| `sign not in signs` | `ValueError` |

---

### 7. Invariant Register

#### 7.1 TriplicityAssignment invariants (enforced by `__post_init__`)

| # | Invariant | Violation raises |
|---|---|---|
| T1 | `sign in SIGNS` | `ValueError` |
| T2 | `isinstance(doctrine, TriplicityDoctrine)` | `ValueError` |
| T3 | `isinstance(is_day_chart, bool)` | `TypeError` |
| T4 | `active_ruler == (day_ruler if is_day_chart else night_ruler)` | `ValueError` |
| T5 | `len(signs) == 3` | `ValueError` |
| T6 | `sign in signs` | `ValueError` |

#### 7.2 triplicity_assignment_for invariants

| # | Invariant |
|---|---|
| F1 | `result.sign == sign` |
| F2 | `result.doctrine == doctrine` |
| F3 | `result.is_day_chart == is_day_chart` |
| F4 | `result.active_ruler == result.day_ruler` when `is_day_chart is True` |
| F5 | `result.active_ruler == result.night_ruler` when `is_day_chart is False` |
| F6 | `len(result.signs) == 3` |
| F7 | `result.sign in result.signs` |
| F8 | All signs in `result.signs` share the same `day_ruler`, `night_ruler`, and `participating_ruler` |

#### 7.3 triplicity_score invariants

| # | Invariant |
|---|---|
| S1 | Return value ∈ {0, `participating_score`, `primary_score`} |
| S2 | Return value is non-negative |
| S3 | At most one planet in CLASSIC_7 scores `primary_score` for any given sign/sect combination |
| S4 | Return is deterministic: same inputs always yield same output |

#### 7.4 Cross-layer invariants

| # | Invariant |
|---|---|
| CL1 | `triplicity_score(a.active_ruler, sign, is_day_chart=is_day, participating_policy=IGNORE) == primary_score` for all signs and sects |
| CL2 | `triplicity_score(a.inactive_ruler, sign, is_day_chart=is_day, participating_policy=IGNORE) == 0` for all signs and sects |
| CL3 | `triplicity_score(a.participating_ruler, sign, is_day_chart=is_day, participating_policy=AWARD_REDUCED) == participating_score` when `not a.has_participating_overlap` |
| CL4 | `triplicity_score(a.participating_ruler, sign, is_day_chart=is_day, participating_policy=IGNORE) == 0` when `not a.has_participating_overlap` |

---

### 8. Determinism and Ordering Rules

| Context | Rule |
|---|---|
| `TriplicityAssignment.signs` tuple | Order is determined by insertion order of `_TRIPLICITY_RULERS_DOROTHEAN_PINGREE_1976` (Python dict, guaranteed insertion-ordered since Python 3.7) |
| `triplicity_assignment_for` on equal input | Identical output — no state, no randomness |
| `triplicity_score` on equal input | Identical output — no state, no randomness |
| `_SIGNS_TO_ELEMENT` lookup | Order-independent (keyed by `frozenset`) |

---

### 9. Non-Goals and Excluded Concerns

| Excluded concern | Notes |
|---|---|
| Planetary position computation | Belongs to `moira.planets` |
| Chart assembly and sect determination | Belongs to higher-level engines |
| Almuten figuris or dignity totalling | Belongs to `moira.dignities` |
| Relational intelligence between signs | Belongs to `moira.aspects` or `moira.dignities` |
| Multi-doctrine lookup or comparison | Deferred — single doctrine is the current scope |
| Topical house triplicity rulers | Outside scope of this module |
| Astrological interpretation | Never in this backend |

---

## Part II — Validation Codex

### 10. Validation Environment

**Authoritative runtime:** project `.venv` (Python 3.14, Windows).

All validation commands must be run as:

```
.venv\Scripts\python.exe -m pytest <target>
```

No test may be marked passing unless it passes in `.venv` with no
modifications to the test file.

---

### 11. Test File Register

| File | Phase(s) | Tests | Focus |
|---|---|---|---|
| `tests/unit/test_triplicity.py` | 1–4, 10 | 75 | Full public surface contract |

**Test class breakdown:**

| Class | Count | Coverage |
|---|---|---|
| `TestTriplicityDoctrine` | 3 | Enum is `StrEnum`; exactly one value; correct value string |
| `TestTriplicityElement` | 3 | Four members; correct value strings; `StrEnum` identity |
| `TestParticipatingRulerPolicy` | 3 | Two members; correct value strings; `StrEnum` identity |
| `TestTriplicityAssignmentFields` | 9 | Field preservation, `active_ruler` sect logic, `signs` tuple, frozen identity |
| `TestTriplicityAssignmentGuards` | 5 | All five `__post_init__` paths |
| `TestTriplicityAssignmentProperties` | 12 | `element`, `inactive_ruler`, `has_participating_overlap` across all signs/sects |
| `TestTriplicityAssignmentFor` | 8 | All 12 signs, all 4 element groups, sect switch, sibling-sign agreement |
| `TestTriplicityScore` | 14 | Primary/participating/zero paths, both policies, custom weights, exhaustive non-negativity |
| `TestHardening` | 18 | Determinism, cross-layer invariants CL1–CL4, failure contracts, misuse resistance |
| **Total** | **75** | |

---

### 12. Validation Doctrine

#### 12.1 Hand-verified spot checks (DOROTHEAN_PINGREE_1976)

These values are hand-checked against Pingree 1976 and must not change
without a doctrine revision.

| Sign | is_day_chart | active_ruler | inactive_ruler | participating_ruler | element |
|---|---|---|---|---|---|
| Aries | True | Sun | Jupiter | Saturn | fire |
| Leo | False | Jupiter | Sun | Saturn | fire |
| Sagittarius | True | Sun | Jupiter | Saturn | fire |
| Taurus | True | Venus | Moon | Mars | earth |
| Virgo | False | Moon | Venus | Mars | earth |
| Capricorn | True | Venus | Moon | Mars | earth |
| Gemini | True | Saturn | Mercury | Jupiter | air |
| Libra | False | Mercury | Saturn | Jupiter | air |
| Aquarius | True | Saturn | Mercury | Jupiter | air |
| Cancer | True | Mars | Venus | Moon | water |
| Scorpio | False | Venus | Mars | Moon | water |
| Pisces | True | Mars | Venus | Moon | water |

#### 12.2 Water triplicity Pingree commitment

The assignment `Cancer/Scorpio/Pisces → day: Mars, night: Venus, participating: Moon`
is the authoritative DOROTHEAN_PINGREE_1976 value. Any change to this triple
requires a new doctrine member and must not alter the existing table entry.

#### 12.3 Score spot checks

| Planet | Sign | is_day_chart | Policy | Expected score |
|---|---|---|---|---|
| Sun | Aries | True | IGNORE | 3 |
| Sun | Aries | False | IGNORE | 0 |
| Jupiter | Aries | False | IGNORE | 3 |
| Jupiter | Aries | True | IGNORE | 0 |
| Saturn | Aries | True | AWARD_REDUCED | 1 |
| Saturn | Aries | True | IGNORE | 0 |
| Moon | Aries | True | AWARD_REDUCED | 0 |
| Mars | Cancer | True | IGNORE | 3 |
| Venus | Cancer | False | IGNORE | 3 |
| Mars | Cancer | False | IGNORE | 0 |
| Moon | Cancer | True | AWARD_REDUCED | 1 |
| Sun | Ophiuchus | True | AWARD_REDUCED | 0 |
| Uranus | Aries | True | AWARD_REDUCED | 0 |

#### 12.4 Cross-layer invariant proof

Invariants CL1–CL4 are exercised exhaustively in `TestHardening` against
all 12 signs × 2 sect contexts (= 24 cases each). No pathological case
was found in the DOROTHEAN_PINGREE_1976 table: `has_participating_overlap`
is False for all 24 combinations.

---

### 13. Known Limitations

| Limitation | Notes |
|---|---|
| Single doctrine | Only `DOROTHEAN_PINGREE_1976` is implemented. The `_TABLES` registry is extensible. |
| No chart-position awareness | This module receives `is_day_chart` as a caller-declared parameter; it does not compute sect from planetary positions. |
| `signs` tuple order is insertion-order | The tuple order reflects `_TRIPLICITY_RULERS_DOROTHEAN_PINGREE_1976` insertion order, not any canonical doctrinal ordering of signs within a triplicity group. |
| Relational intelligence belongs in dignity layer | Whether a planet's triplicity rulership contributes to its total essential dignity score is governed by `moira.dignities`, not this module. |
| No validation against external oracle | No machine-readable external authority for Dorothean triplicity tables has been identified; spot checks in §12.1 are hand-verified against Pingree 1976 directly. |
