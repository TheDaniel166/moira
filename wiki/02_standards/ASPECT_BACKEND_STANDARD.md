## Moira Aspect Backend Standard

### Governing Principle

The Moira aspect backend is a sovereign computational subsystem. Its definitions,
layer boundaries, invariants, failure doctrine, and determinism rules are stated
here and are frozen until explicitly superseded by a revision to this document.

This document reflects current implementation truth. Focused verification
counts belong in completion receipts rather than frozen doctrine.

The [Complete Aspect Catalog](ASPECT_CATALOG.md) lists all 46 standard and 28
optional longitude targets, both declination relationships, every registered
alias, exact turn fractions, default orbs, selection rules, and harmonic presets.

---

## Part I — Architecture Standard

### 1. Authoritative Computational Definitions

#### 1.1 Ecliptic aspect

An **ecliptic aspect** in Moira is:

> A detected angular relationship between two distinct celestial bodies whose
> angular separation along the ecliptic falls within a declared orb of a
> canonical aspect angle.

| Element | Definition |
|---|---|
| *two distinct bodies* | `body1 != body2`; no self-aspects |
| *angular separation* | `angular_distance(lon1, lon2)` → `[0, 180]` degrees, folded at 180° |
| *canonical aspect angle* | A standard angle from `moira.constants.Aspect.ALL`, or an explicitly enabled member of `moira.optional_aspects.OPTIONAL_ASPECT_SETS` |
| *orb* | `abs(separation - angle)` |
| *within declared orb* | `orb <= allowed_orb` |
| *allowed_orb* | `default_orb * orb_factor`, or the caller-supplied override for that angle |

The admission test is fully reconstructable from the stored vessel:
```
orb        == abs(separation - angle)
orb        <= allowed_orb
separation  = angular_distance(lon1, lon2)
```

#### 1.2 Declination aspect

A **declination aspect** in Moira is:

> A parallel or contra-parallel between two distinct celestial bodies whose
> signed declinations satisfy one of the two defined relationships within a
> declared orb.

| Type | Admission test | Orb formula |
|---|---|---|
| Parallel | Same nonzero hemisphere and `abs(dec1 - dec2) <= allowed_orb` | `orb = abs(dec1 - dec2)` |
| Contra-Parallel | Opposite nonzero hemispheres and `abs(dec1 + dec2) <= allowed_orb` | `orb = abs(dec1 + dec2)` |

Two points exactly on the equator form one exact Parallel. A single equatorial
point has no hemisphere and forms neither relation with a non-equatorial point.
Hemisphere qualification precedes the orb formula so both relations cannot be
emitted for one pair near 0°.

Detected `DeclinationAspect` vessels carry no motion data; consequently the
legacy generic `aspect_motion_state(DeclinationAspect)` remains `NONE`. The
separate `DeclinationAspectMotionWitness` is the first-class temporal product
when declination rates are supplied.

#### 1.2.1 Module ownership

`moira.declination_aspects` governs parallels, contra-parallels, their
hemisphere/equator doctrine, policy, result vessels, and signed motion witness.
`moira.aspects` governs ecliptic-longitude and whole-sign relationships and
retains compatibility re-exports for the historical declination imports.
Shared domain/tier/family classification types live in the private
`moira._aspect_types` taxonomy layer so both engines use identical enum and
classification objects without circular imports.

Declination is a second angular coordinate on the celestial sphere. It is not
full Cartesian 3D geometry because radial distance is not part of these
relationships.

#### 1.2.2 Whole-sign direction and overcoming

`moira.aspects` also owns Hellenistic aspect direction and whole-sign
overcoming. `hellenistic_superiority_truth()` is the governing atomic receipt
for one ordered body pair: `HellenisticDirectionTruth` preserves directed-arc
geometry and sinister/dexter applicability, while
`HellenisticOvercomingTruth` preserves both inclusive sign places and the
typed winner-or-neither relation.

Direction is `not_evaluable` when no aspect angle is supplied, for conjunction
or opposition, or at an exact directed conjunction/opposition boundary. The
reason is preserved and an evaluable direction cannot be suppressed.
Overcoming remains evaluated for finite pair geometry. Sign counting is
inclusive: the first body overcomes the second only when the first occupies
the tenth sign from the second, which is nine zero-based sign steps forward.
Reversing the operands reverses the question. A third-sign/fourth-sign
confusion must not be accepted merely because the bodies form an undirected
square.

`AspectData.direction` and `overcoming(lon1, lon2)` are compatibility
projections from that shared raw truth. Detector-produced `AspectData` also
carries the aggregate `hellenistic_superiority_truth` receipt. No additive
dignity or superiority score is admitted by this composition layer.

#### 1.3 Admitted aspect

An aspect is **admitted** when the admission test passes. Admission is binary:
the aspect either qualifies or it does not. There is no partial admission and
no confidence score at the detection layer.

---

### 2. Layer Structure

The backend is organized into twelve phases. Each phase operates only on
outputs produced by phases below it. No phase reaches upward.

```
Phase  1 — Core aspect detection
Phase  2 — Relational truth preservation
Phase  3 — Classification
Phase  4 — Inspectability
Phase  5 — Doctrine inputs
Phase  6 — Policy surface
Phase  7 — Geometric strength
Phase  8 — Temporal state
Phase  9 — Canonical configuration
Phase 10 — Multi-body pattern layer
Phase 11 — Relational graph / network layer
Phase 12 — Harmonic / family intelligence layer
```

#### Layer boundary rule

A function in phase N may consume results from phases 1 through N−1.
It may not:

- re-run position arithmetic
- re-compute aspect admission
- alter a vessel produced by an earlier phase in place
- introduce new doctrine inputs not present in that phase's entry point

---

### 3. Delegated Assumptions

The aspect engine delegates to external modules without redefining them:

| Concern | Delegated to | Convention |
|---|---|---|
| Angular distance arithmetic | `moira.coordinates.angular_distance` | Returns `[0, 180]`, fold at 180° |
| Canonical aspect definitions | `moira.constants.Aspect.ALL` | 46 zodiacal aspects |
| Optional exact-fraction definitions | `moira.optional_aspects.OPTIONAL_ASPECT_SETS` | 28 additional targets in four opt-in sets |
| Default orb table | `moira.constants.DEFAULT_ORBS` | `{angle: max_orb}` |
| Aspect tier lists | `moira.constants.ASPECT_TIERS` | Major / Common Minor / Extended Minor |

The aspect backend does not redefine any of these. Changes to these constants
propagate automatically.

---

### 4. Canonical Aspect Set

The standard aspect set is declared in `CANONICAL_ASPECTS` — a module-level
tuple of 48 names, frozen at import time. It preserves the standard 46 zodiacal
names and two declination names. Optional zodiacal additions are declared
separately in `OPTIONAL_ASPECT_SETS`; `ASPECT_DEFINITIONS` combines all 74
zodiacal definitions for identity resolution without enabling optional detection.

| Tier | Count | Names |
|---|---|---|
| Major | 5 | Conjunction, Sextile, Square, Trine, Opposition |
| Common Minor | 6 | Semisextile, Semisquare, Sesquiquadrate, Quincunx, Quintile, Biquintile |
| Extended Minor | 35 | Septile (3), Novile (3), Decile (2), Undecile (5), Quindecile (4), Vigintile (4), Untion including Tao (4), Hexadecile (4), Seminovile (3), and Semiseptile (3) series; members below |
| Declination | 2 | Parallel, Contra-Parallel |

Rules:

- The 46 zodiacal names correspond 1-to-1 with entries in `Aspect.ALL`.
- The 2 declination names are produced exclusively by `find_declination_aspects`.
- `CANONICAL_ASPECTS` carries no detection logic; it is a declaration only.
- Standard detection produces only names in `CANONICAL_ASPECTS`; optional
  detection additionally produces names from the explicitly selected sets.

#### Additional extended-minor geometry and naming

| Attribute | Name | Angle | Circle fraction | Default orb | Display abbreviation |
|---|---|---|---|---|---|
| `Aspect.TAO` | Tao | 165° | 11/24 | 1° | `Tao` |
| `Aspect.HEXADECILE` | Hexadecile | 22.5° | 1/16 | 1° | `Hx` |
| `Aspect.SEMINOVILE` | Seminovile | 20° | 1/18 | 1° | `sN` |
| `Aspect.UNTION` | Untion | 15° | 1/24 | 1° | `Un` |

Quindecile remains 24° (1/15 of the circle). The 165° convention sometimes
called Quindecile is named **Tao** here to keep both geometries unambiguous;
the bare name `Quindecile` always selects 24°, including motion-witness requests.
[Astrodienst's Tao entry](https://www.astro.com/astrowiki/en/Tao) records this
alternative name. Michel Suignard's 2017
[Unicode working document N4811, Table 1](https://www.unicode.org/wg2/docs/n4811-fdbk-extra-aspect-sym.pdf)
records Hexadecile, Seminovile, Untion, and Quindecile at their respective
fractions; it is naming evidence, not a source for orbs or dedicated glyphs.

The 1° default orbs are explicit Moira policy, following the nearby extended
minor definitions; they are configurable through the existing orb table and
`orb_factor`. The text abbreviations above are Moira display labels, not claims
of standardized Unicode symbols. All four belong exclusively to the extended
minor tier (`tier=2`); tiers 0/1, common-minor defaults, and whole-sign/moiety
doctrine retain their existing aspect sets. Calls that select all aspects,
including the default `aspects_between()`, include the additions. Tao and Untion
share the `UNTION` family because they are the 11/24 and 1/24 members of the
24th-harmonic series.

#### Completion of the admitted harmonic families

These twenty additional targets are irreducible circle fractions. Every angle
is computed as `360 * numerator / denominator`, without rounding the repeating
fractions printed by some references. They are all extended minor aspects with
configurable 1° default orbs. Existing definitions and their orbs are preserved.

| Family | Canonical names, in corresponding order | Fractions of a turn |
|---|---|---|
| Undecile | Biundecile, Triundecile, Quadriundecile, Quinqueundecile | 2/11, 3/11, 4/11, 5/11 |
| Quindecile | Biquindecile, Quadraquindecile, Septaquindecile | 2/15, 4/15, 7/15 |
| Hexadecile | Sesquioctile, Quinsemioctile, Septsemioctile | 3/16, 5/16, 7/16 |
| Seminovile | Quinseminovile, Septseminovile | 5/18, 7/18 |
| Vigintile | Trivigintile, Septvigintile, Nonavigintile | 3/20, 7/20, 9/20 |
| Untion | Squile, Squine | 5/24, 7/24 |
| Semiseptile | Semiseptile, Trisemiseptile, Quinsemiseptile | 1/14, 3/14, 5/14 |

Naming evidence: [Aureas's version-12 aspect catalog](https://www.aureas-astrology.com/contents/en-us/d1_News.html),
[Astrolog's author-maintained aspect table](https://www.astrolog.org/astrolog/astdist.htm),
and [Philip Graves's aspect table](https://www.astrolearn.com/astrology-articles/aspects2/).
These sources establish terminology and published usage; Moira owns the
explicit orb and display-abbreviation policy. Numerical verification derives
the target angles independently from the exact fractions.

The unsigned angular-distance primitive reduces `abs(a-b)` modulo 360 before
folding at 180°. This keeps argument reversal symmetric and avoids adding and
subtracting 360 for a negative remainder, which can move repeating-fraction
targets across an otherwise exact closed orb boundary. The orb ceiling itself
is unchanged. Exact-rational and closed-boundary tests cover this primitive.

#### Canonical identities and aliases

`moira.aspect_registry.ASPECT_ALIASES` is a read-only mapping from declared
alternative spellings to canonical longitude-aspect names. `resolve_aspect()`
returns the existing `AspectDefinition` object. Both are also exposed through
`moira.aspects`, `moira.classical`, `moira.predictive`, `moira.facade`, and `moira`.
Resolution ignores case and internal ASCII spaces, hyphens, and underscores;
leading/trailing whitespace and unknown names raise `ValueError`. Geometry,
classification, canonical counts, and graph edges never gain duplicate entries
because an aspect has multiple names.

Examples include Octile → Semisquare, Tridecile/Sesquiquintile → Tredecile,
Nonile → Novile, Semioctile/Sexdecile → Hexadecile, Semidecile → Vigintile,
Semiduodecile/Quartisextile → Untion, and published spelling variants of the
new multiples. `Quindecile` always means 24°. The explicitly qualified
`Quindecile (165°)`, `Quindecile (Tyl)`, `Contraquindecile`, and
`Undecaquartisextile` resolve to Tao at 165° under those named conventions.
`Tredecile` remains 108°; no 13th-harmonic meaning is inferred. Ambiguous or
unadmitted labels such as Sentagon and GoldenRatio are not aliases.

Motion witnesses and relationship-transit selection accept the registry's
aliases and emit canonical names. REST motion input schemas advertise both
canonical names and declared aliases; output schemas enumerate canonical
names only. Relationship REST requests can explicitly select up to all 74
zodiacal aspects when all four optional sets are enabled, reject duplicates
after alias resolution, and retain the existing
branch, scan, and search-work budgets. Alias resolution never widens a tier.

`HARMONIC_PRESETS` now covers the admitted primitive divisions with H6,
H10, H14, H15, H16, H18, H20, and H24 added. H24 is named Untion (1/24),
not Tao (11/24). Existing preset labels are retained; new descriptions state
geometry without adding interpretive doctrine. See the Harmonics Backend Standard.

#### Optional H13, H32, H36, and H40 sets

These four sets add 28 primitive, irreducible fractions below half a turn.
Reducible members already belong to lower harmonic families and are not
duplicated. Angles use `360 * numerator / denominator` without rounding source
tables; exact integer fractions remain available in immutable metadata.

| Set | Numerators (denominator equals harmonic) | Primitive angle | Default orb |
|---|---|---|---|
| H13 | 1, 2, 3, 4, 5, 6 | 360/13° | 12/13° |
| H32 | 1, 3, 5, 7, 9, 11, 13, 15 | 11.25° | 0.375° |
| H36 | 1, 5, 7, 11, 13, 17 | 10° | 1/3° |
| H40 | 1, 3, 7, 9, 11, 13, 17, 19 | 9° | 0.3° |

Canonical labels are `H13 1/13`, `H32 3/32`, etc. Every member has its exact
`p/q` alias. H32 additionally admits the published Quartisemisquare series;
H36 admits the Sextisextile series and Trigintasextile for 1/36; H40 admits
Semivigintile and Quadragintile for 1/40. All six H13 published names are
explicitly qualified, such as `Tredecile (13th harmonic)` and
`Bitredecile (13th harmonic)`. Bare Tredecile stays 108°, Quindecile stays
24°, and Tao stays 165°.

[Philip Graves's authored table](https://www.astrolearn.com/astrology-articles/aspects2/)
provides the H13, H32, and H36 series terminology (with rounded source angles).
[David Cochrane's *The First 32 Harmonics*](https://www.astrosoftware.com/cpnew/a_and_v/pdf/harmonicfirst32.pdf)
documents research use of higher harmonics. These are naming and practice
sources, not precision or interpretive validation. Moira's exact rational
construction and configurable `12/H` degree default orbs are explicit engine
policy. These optional longitude defaults do not change the independent
projected-orb defaults of the harmonic-chart API.

```python
from moira import OPTIONAL_ASPECT_FRACTIONS, aspects_from_longitudes, resolve_aspect

analysis = aspects_from_longitudes(
    {"Sun": 0.0, "Moon": 360 / 13}, tier=0, optional_sets=("H13",),
)
assert analysis.optional_sets == ("H13",)
assert OPTIONAL_ASPECT_FRACTIONS["H13 1/13"] == (1, 13)
assert resolve_aspect("1/13").name == "H13 1/13"
```

`optional_sets=()` preserves existing detection defaults. Set names are case
insensitive and normalized in catalog order; unknown, repeated, non-string,
or untrimmed selectors fail closed. `AspectPolicy` freezes the selection.
The selected sets extend the requested tier or legacy `include_minor` set;
they never populate `Aspect.ALL`, `ASPECT_TIERS`, or `CANONICAL_ASPECTS`.
The moiety policy remains restricted to the five traditional major aspects.

The selector is available on `find_aspects`, `aspects_between`,
`aspects_to_point`, `aspects_from_longitudes`, synastry aspect/contact calls,
and relationship transit searches, including their facade and REST entry
points. Chart-wheel config and asteroid-family resonance requests expose the
same selector and preserve it in policy/provenance receipts. Explicit
`AspectPolicy` still takes precedence over legacy keyword
arguments. Synastry explicit selectors override its policy selector. Forecast
name filtering requires a matching enabled optional set; naming one specific
motion witness is itself an explicit opt-in. Aliases do not widen detection.

Position-only, synastry, derived-chart, and relationship-forecast receipts
preserve the enabled sets. These members are `extended_minor`, with distinct
`harmonic_13`, `harmonic_32`, `harmonic_36`, and `harmonic_40` families; graph
and harmonic profiles consume that classification without another admission.
Orb overrides and `orb_factor` retain their existing meaning.

`OPTIONAL_ASPECT_SETS`, `OPTIONAL_ASPECT_FRACTIONS`, and `ASPECT_DEFINITIONS`
are re-exported through the same public namespaces as `ASPECT_ALIASES`.
`GET /v1/aspects/optional-sets` exposes canonical names, exact numerators and
denominators, angles, orbs, and declared aliases. REST selection uses e.g.
`"optional_sets": ["H13", "H40"]`. The harmonic preset catalog additionally
contains H13, H32, H36, and H40, named after their primitive canonical members.
Selecting or listing a harmonic preset alone does not enable longitude sets.

---

### 5. Classification

`AspectClassification` classifies every admitted aspect on three independent axes:

| Axis | Type | Rule |
|---|---|---|
| `domain` | `AspectDomain` | `ZODIACAL` for ecliptic; `DECLINATION` for parallels |
| `tier` | `AspectTier` | Derived from `AspectDefinition.is_major`, `Aspect.EXTENDED_MINOR`, and optional-set membership |
| `family` | `AspectFamily` | Derived from `_FAMILY_BY_NAME`; maps each aspect name to its harmonic family |

Classification is **descriptive only**. It describes what was detected, not
how it should be interpreted. Strength, dignity weighting, and reception scoring
are excluded from the classification layer.

#### Family grouping

Aspects in the same harmonic series share a family:

| Family | Members |
|---|---|
| `CONJUNCTION` | Conjunction |
| `OPPOSITION` | Opposition |
| `SQUARE` | Square |
| `TRINE` | Trine |
| `SEXTILE` | Sextile |
| `SEMISEXTILE` | Semisextile |
| `SEMISQUARE` | Semisquare |
| `SESQUIQUADRATE` | Sesquiquadrate |
| `QUINCUNX` | Quincunx |
| `QUINTILE` | Quintile, Biquintile |
| `SEPTILE` | Septile, Biseptile, Triseptile |
| `NOVILE` | Novile, Binovile, Quadnovile |
| `DECILE` | Decile, Tredecile |
| `UNDECILE` | Undecile, Biundecile, Triundecile, Quadriundecile, Quinqueundecile |
| `QUINDECILE` | Quindecile, Biquindecile, Quadraquindecile, Septaquindecile |
| `VIGINTILE` | Vigintile, Trivigintile, Septvigintile, Nonavigintile |
| `HEXADECILE` | Hexadecile, Sesquioctile, Quinsemioctile, Septsemioctile |
| `SEMINOVILE` | Seminovile, Quinseminovile, Septseminovile |
| `UNTION` | Untion, Tao, Squile, Squine |
| `SEMISEPTILE` | Semiseptile, Trisemiseptile, Quinsemiseptile |
| `DECLINATION` | Parallel, Contra-Parallel |

---

### 6. Policy Layer

`AspectPolicy` encapsulates longitude-aspect doctrine and retains
`declination_orb` as a compatibility adapter for historical callers.

| Field | Type | Default | Effect |
|---|---|---|---|
| `tier` | `int \| None` | `None` | 0=Major only, 1=Major+Common Minor, 2=All; `None` defers to `include_minor` |
| `include_minor` | `bool` | `True` | Include Common Minor when `tier` is `None` |
| `orbs` | `dict[float, float] \| None` | `None` | Custom orb table `{angle: max_orb}`; overrides `orb_factor` when set |
| `orb_factor` | `float` | `1.0` | Multiplier on all default orbs; ignored when `orbs` is set |
| `declination_orb` | `float` | `1.0` | Ceiling for Parallel and Contra-Parallel detection |

When a `policy` argument is passed to a detection function it takes full precedence
over any corresponding individual keyword arguments. Individual parameters remain
available for backward compatibility.

`DEFAULT_POLICY` reproduces the historical default behaviour of all four
detection functions.

`DeclinationAspectPolicy` is the governing declination policy:

| Field | Default | Effect |
|---|---|---|
| `orb` | `1.0` | Admission ceiling for both relationships |
| `exact_tolerance_deg` | `1e-9` | Exactness precedence threshold |
| `rate_tolerance_deg_per_day` | `1e-12` | Relative signed-error rate treated as stalled |
| `hemisphere_policy` | `STRICT_SIGNED` | Parallel uses the same nonzero hemisphere; Contra-Parallel uses opposite nonzero hemispheres |
| `equator_policy` | `PAIRED_EQUATORIAL_PARALLEL` | Two equatorial points form one Parallel; one equatorial point is unclassified |

#### Policy validation

`AspectPolicy` validates its fields at construction:

| Condition | Raises |
|---|---|
| `orb_factor <= 0` | `ValueError` |
| `declination_orb < 0` | `ValueError` |

---

### 7. Geometric Strength

`AspectStrength` is a **pure arithmetic exactness summary** derived from
`orb` and `allowed_orb` only.

```
surplus   = allowed_orb - orb
exactness = 1.0 - orb / allowed_orb
```

| Field | Definition |
|---|---|
| `orb` | Angular deviation from target angle; always non-negative |
| `allowed_orb` | Orb ceiling applied at admission |
| `surplus` | `allowed_orb - orb`; remaining headroom |
| `exactness` | `1.0 - orb / allowed_orb`; `1.0` = exact, `0.0` = at boundary |

`aspect_strength` does not interpret strength. It does not weight by aspect
family, body dignity, or orbital speed.

#### Strength validation

`aspect_strength` validates its input before computing:

| Condition | Raises |
|---|---|
| `orb` or `allowed_orb` is non-finite, or `orb < 0` | `ValueError` |
| `allowed_orb <= 0` | `ValueError` |
| `orb > allowed_orb` | `ValueError` |

Whole-sign aspects are categorical rather than orb-admitted. Their strength
identity is `orb = allowed_orb = surplus = 0` and `exactness = 1`.

---

### 8. Temporal-State Doctrine

`MotionState` formalises the motion-aware truth already stored in `applying`
and `stationary`. It maps the complete decision space without ambiguity:

| Vessel/domain | `orb` | `stationary` | `applying` | `→ MotionState` |
|---|---|---|---|---|
| `DeclinationAspect` | any | — | — | `NONE` |
| Whole-sign `AspectData` | any | — | — | `NONE` |
| Zodiacal `AspectData` | `<= 1e-9` | any | any | `EXACT` |
| Zodiacal `AspectData` | `> 1e-9` | `True` | any | `STATIONARY` |
| Zodiacal `AspectData` | `> 1e-9` | `False` | `True` | `APPLYING` |
| Zodiacal `AspectData` | `> 1e-9` | `False` | `False` | `SEPARATING` |
| Zodiacal `AspectData` | `> 1e-9` | `False` | `None` | `INDETERMINATE` |

Categorical/no-motion domains yield `NONE`. For zodiacal aspects, `EXACT`
takes precedence over stationary and applying/separating classification.

#### Temporal consistency rules

- `APPLYING` ↔ `is_applying is True` and `is_separating is False`
- `SEPARATING` ↔ `is_separating is True` and `is_applying is False`
- `is_applying` and `is_separating` are never simultaneously `True`
- Both are `False` when `applying is None`

#### First-class declination motion

`DeclinationAspectMotionWitness` classifies a selected relationship from
caller-supplied declinations and optional declination rates, all expressed in
the same declared frame, timescale, origin, and correction regime.

| Relationship | Signed error `E` | Relative rate `dE/dt` |
|---|---|---|
| Parallel | `dec1 - dec2` | `speed1 - speed2` |
| Contra-Parallel | `dec1 + dec2` | `speed1 + speed2` |

Away from exactness, `orb = abs(E)` and
`orb_rate = sign(E) * dE/dt`. A negative orb rate is `APPLYING`; a positive
orb rate is `SEPARATING`. Exactness takes precedence. A relative rate inside
the policy tolerance is `STATIONARY`, while missing or partial rates are
`INDETERMINATE`. An individual zero declination rate does not force
`STATIONARY` when the relationship's relative error is still changing.

The witness is instantaneous (`instantaneous_no_event_search`). It does not
prove that a relationship will perfect before either body reverses in
declination; that stronger claim requires an epoch-based exact-root search.

---

### 9. Multi-Body Pattern Doctrine

`find_patterns` operates over an already-admitted `list[AspectData]`. It does
not re-run position arithmetic.

Implemented patterns and their structural requirements:

| Kind | Bodies | Required edges |
|---|---|---|
| `STELLIUM` | ≥3, maximal clique | Mutual Conjunction between every pair |
| `T_SQUARE` | exactly 3 | One Opposition (A–B) + Square(A–C) + Square(B–C) |
| `GRAND_TRINE` | exactly 3 | Trine(A–B) + Trine(B–C) + Trine(A–C) |
| `GRAND_CROSS` | exactly 4 | Two Oppositions + four Squares (closed cross) |
| `YOD` | exactly 3 | Sextile(B–C) + Quincunx(A–B) + Quincunx(A–C) |

#### Pattern ordering rules

- Output order: Stellia, T-Squares, Grand Trines, Grand Crosses, Yods.
- Each pattern kind is emitted at most once per unique body set (`frozenset`).
- Stellium: smaller subsets contained within a larger Stellium are suppressed.
- All other kinds are independent. A Grand Cross may also contain T-Squares;
  both are reported.
- Within each kind, patterns are ordered by sorted body-name iteration
  (outer loops always iterate over `sorted(all_bodies)`).

#### Pattern contributing-aspects ordering

The `aspects` tuple inside each `AspectPattern` is sorted by
`(body1, body2, aspect)`. This ordering is stable and independent of the input
list ordering.

#### Structural aspect counts

| Kind | `len(aspects)` |
|---|---|
| STELLIUM (3-body) | 3 |
| STELLIUM (4-body) | 6 |
| T_SQUARE | 3 |
| GRAND_TRINE | 3 |
| GRAND_CROSS | 6 |
| YOD | 3 |

---

### 10. Relational Graph Doctrine

`build_aspect_graph` expresses the chart as a deterministic aspect network.
Bodies become nodes; each admitted `AspectData` becomes an edge.

#### Graph construction rules

- Every body that appears in at least one aspect gets a node.
- Bodies supplied via `bodies=` that have no aspects get degree-0 nodes.
- `nodes` is sorted by body name.
- `edges` is sorted by `(body1, body2, aspect)`.
- `components` is sorted by `(min(component), len(component))` ascending.

#### Node invariants

| Invariant | Expression |
|---|---|
| Degree consistency | `degree == len(edges)` |
| Family count consistency | `sum(family_counts.values()) == degree` |
| Incidence | Every edge in `node.edges` has `body1 == name` or `body2 == name` |
| Edge ordering | `edges` sorted by `(body1, body2, aspect)` |

`family_counts` keys are `AspectData.aspect` strings (e.g. `"Trine"`), not
`AspectFamily` enum values. This is intentional: it preserves per-name granularity
at the graph layer (Trine vs Biquintile both count as QUINTILE family at the harmonic
layer, but remain distinct at the graph layer).

#### Derived properties

| Property | Definition |
|---|---|
| `hubs` | Nodes with maximum degree; empty tuple when all nodes are isolated |
| `isolated` | Nodes with degree 0, sorted by name |

---

### 11. Harmonic Intelligence Doctrine

`aspect_harmonic_profile` derives the family distribution of admitted aspects
at both the chart level and per body.

#### Profile construction rules

- `chart` covers all aspects in the input list.
- `by_body` has one entry per body that appears in at least one aspect.
- `by_body` keys are in sorted body-name order.
- A body with no aspects has no entry in `by_body`.

#### Family resolution order (when `classification` is absent)

1. `a.classification.family` when `classification` is not `None` (normal case).
2. `_FAMILY_BY_NAME[a.aspect]` when `classification` is `None` and the name
   is a known zodiacal name.
3. `AspectFamily.DECLINATION` as the fallback for any unrecognised name
   (covers "Parallel", "Contra-Parallel", or custom names).

#### `AspectFamilyProfile` invariants

| Invariant | Expression |
|---|---|
| Total | `sum(counts.values()) == total` |
| Proportions count | `len(proportions) == len(counts)` |
| Proportions sum | `abs(sum(proportions.values()) - 1.0) < 1e-9` when `total > 0` |
| Dominant membership | Every member of `dominant` is a key in `counts` |
| Proportion range | All proportions in `[0.0, 1.0]` |
| Key ordering | `counts` and `proportions` keys follow `AspectFamily` declaration order |
| Dominant ordering | `dominant` sorted by `AspectFamily.value` (alphabetical) |

---

### 12. Non-Goals

The following concerns are **explicitly outside the scope** of the current
aspect backend:

| Excluded concern | Reason |
|---|---|
| Interpretation (e.g. "this aspect is challenging") | Doctrine-specific; belongs above the engine |
| Dignity weighting or reception scoring | Requires a separate dignity model |
| Body-specific orb weights | Not in current `AspectPolicy` |
| Antiscion contacts | A separate geometric computation |
| Cross-chart (synastry) relational policies | Multi-chart context not yet in scope |
| Kite, Mystic Rectangle, Grand Quintile | Require oriented topology or 5-body matching |
| UI rendering or serialization | Belongs above the engine |
| Harmonic chart generation | Separate from aspect detection |

---

## Part II — Validation Codex

### 1. Validation Environment

| Property | Value |
|---|---|
| Authoritative runtime | `.venv` in the project root |
| Python version | 3.14.x (as resolved by `.venv`) |
| Test runner | `pytest` via `.venv\Scripts\python.exe -m pytest` |
| Test file | `tests/unit/test_aspects.py` |
| Baseline | Focused aspect test file passes under strict known-issues mode |
| Acceptable result | 0 failures, 0 errors |

No test in `test_aspects.py` may be modified to make the implementation pass.
A failing test is always treated as an implementation defect, not a test defect,
unless the test itself is proven incorrect.

---

### 2. Invariant Register

This register is the normative source of truth for all subsystem invariants.
Each invariant is identified by a short code for traceable reference.

#### INV-TRUTH — Truth preservation

| Code | Invariant |
|---|---|
| T-1 | Zodiacal `orb == abs(separation - angle)` to floating-point precision |
| T-2 | Zodiacal `orb <= allowed_orb`; whole-sign `orb == allowed_orb == 0` |
| T-3 | `orb_surplus == allowed_orb - orb >= 0` |
| T-4 | `separation` is in `[0, 180]` degrees |
| T-5 | For a Parallel: `orb == abs(dec1 - dec2)` |
| T-6 | For a Contra-Parallel: `orb == abs(dec1 + dec2)` |
| T-7 | `dec1` and `dec2` are in `[-90, +90]` |
| T-8 | Parallel and Contra-Parallel hemisphere predicates are mutually exclusive |
| T-9 | `overcoming(lon1, lon2)` is true exactly when `(sign1 - sign2) mod 12 == 9` |
| T-10 | `HellenisticDirectionTruth` is evaluated only for a supplied non-conjunction/non-opposition angle away from directed 0°/180° boundaries |
| T-11 | `HellenisticOvercomingTruth.relation` exactly matches the two inclusive sign places and admits an evaluated `neither` result |
| T-12 | Detector-produced `AspectData.direction` is the compatibility projection of its `hellenistic_superiority_truth.direction_truth` |

#### INV-CLASS — Classification

| Code | Invariant |
|---|---|
| C-1 | `classification.domain` is `ZODIACAL` or `WHOLE_SIGN` for detector-produced `AspectData` |
| C-2 | `classification.domain == DECLINATION` for every `DeclinationAspect` |
| C-3 | `classification.family == _FAMILY_BY_NAME[aspect]` for every zodiacal aspect |
| C-4 | `classification.family == AspectFamily.DECLINATION` for every `DeclinationAspect` |
| C-5 | `classification.tier == MAJOR` for every aspect in `{"Conjunction","Sextile","Square","Trine","Opposition"}` |
| C-6 | Classification is identical for the same aspect name across all calls |

#### INV-STR — Geometric strength

| Code | Invariant |
|---|---|
| S-1 | `0.0 <= orb <= allowed_orb` for any orb-admitted vessel passed to `aspect_strength` |
| S-2 | `surplus == allowed_orb - orb` |
| S-3 | `0.0 <= exactness <= 1.0` |
| S-4 | `exactness == 1.0 - orb / allowed_orb` |
| S-5 | `aspect_strength` raises `ValueError` when `allowed_orb <= 0` |
| S-6 | `aspect_strength` raises `ValueError` when `orb > allowed_orb` |
| S-7 | Whole-sign strength is `(orb=0, allowed_orb=0, surplus=0, exactness=1)` |

#### INV-MOT — Temporal state

| Code | Invariant |
|---|---|
| M-1 | `APPLYING` ↔ `is_applying is True` and `is_separating is False` |
| M-2 | `SEPARATING` ↔ `is_separating is True` and `is_applying is False` |
| M-3 | Zodiacal exactness yields `EXACT` before stationary/applying classification |
| M-4 | Non-exact zodiacal data yields `STATIONARY` when `stationary is True` |
| M-5 | A detection-only `DeclinationAspect` and whole-sign data yield generic `MotionState.NONE` |
| M-6 | `is_applying` and `is_separating` are never simultaneously `True` |
| M-7 | Non-exact zodiacal data yields `INDETERMINATE` when motion is unavailable |
| M-8 | Parallel signed error/rate are `dec1 - dec2` and `speed1 - speed2` |
| M-9 | Contra-Parallel signed error/rate are `dec1 + dec2` and `speed1 + speed2` |
| M-10 | Non-exact declination `orb_rate < 0` yields `APPLYING`; `orb_rate > 0` yields `SEPARATING` |
| M-11 | Declination exactness precedes rate classification |
| M-12 | Missing declination rates yield `INDETERMINATE` unless exact |
| M-13 | Declination `STATIONARY` means the relative error rate is inside tolerance, not that either individual body has zero rate |

#### INV-PAT — Pattern layer

| Code | Invariant |
|---|---|
| P-1 | Every body in `pattern.bodies` appears in at least one aspect in `pattern.aspects` |
| P-2 | `pattern.aspects` is sorted by `(body1, body2, aspect)` |
| P-3 | No pattern body-set is emitted more than once per kind |
| P-4 | Stellium sub-cliques contained in a larger Stellium are suppressed |
| P-5 | T_SQUARE has exactly 3 contributing aspects |
| P-6 | GRAND_TRINE has exactly 3 contributing aspects |
| P-7 | GRAND_CROSS has exactly 6 contributing aspects |
| P-8 | YOD has exactly 3 contributing aspects |
| P-9 | STELLIUM (3-body) has exactly 3; (4-body) has exactly 6 contributing aspects |
| P-10 | Output order: Stellia, T-Squares, Grand Trines, Grand Crosses, Yods |
| P-11 | `find_patterns` does not mutate the input list |

#### INV-GRAPH — Relational graph

| Code | Invariant |
|---|---|
| G-1 | `degree == len(edges)` for every node |
| G-2 | `sum(family_counts.values()) == degree` for every node |
| G-3 | Every edge in `node.edges` involves that node as `body1` or `body2` |
| G-4 | `node.edges` sorted by `(body1, body2, aspect)` |
| G-5 | `graph.nodes` sorted by body name |
| G-6 | `graph.edges` sorted by `(body1, body2, aspect)` |
| G-7 | `graph.components` sorted by `(min(c), len(c))` ascending |
| G-8 | `build_aspect_graph` does not mutate the input list |

#### INV-HARM — Harmonic layer

| Code | Invariant |
|---|---|
| H-1 | `sum(counts.values()) == total` |
| H-2 | `len(proportions) == len(counts)` |
| H-3 | `abs(sum(proportions.values()) - 1.0) < 1e-9` when `total > 0` |
| H-4 | Every member of `dominant` is a key in `counts` |
| H-5 | All proportions are in `[0.0, 1.0]` |
| H-6 | `chart.total == len(aspects)` |
| H-7 | `by_body[name].total` equals the number of aspects in which `name` participates |
| H-8 | `by_body` keys are in sorted body-name order |
| H-9 | `aspect_harmonic_profile` does not mutate the input list |

#### INV-POL — Policy

| Code | Invariant |
|---|---|
| PO-1 | `AspectPolicy` raises `ValueError` when `orb_factor <= 0` |
| PO-2 | `AspectPolicy` raises `ValueError` when `declination_orb < 0` |
| PO-3 | `DEFAULT_POLICY` is a valid, constructable `AspectPolicy` |
| PO-4 | Invalid tiers, non-boolean flags, and non-finite policy values raise `ValueError` |
| PO-5 | Caller-supplied orb mappings are defensively copied and exposed read-only |

---

### 3. Determinism Register

The following ordering guarantees are normative. Any permutation of an input
list must produce identical output on all of these:

| Context | Determinism guarantee |
|---|---|
| `find_aspects` result order | Sorted by `orb` ascending |
| `find_declination_aspects` result order | Sorted by `orb` ascending |
| `find_patterns` — pattern order | Stellia, T-Squares, Grand Trines, Grand Crosses, Yods |
| `find_patterns` — body-set per pattern | `frozenset` (order-independent identity) |
| `find_patterns` — `aspects` tuple | Sorted by `(body1, body2, aspect)` |
| `build_aspect_graph` — `nodes` | Sorted by body name |
| `build_aspect_graph` — `edges` | Sorted by `(body1, body2, aspect)` |
| `build_aspect_graph` — `components` | Sorted by `(min(c), len(c))` |
| `build_aspect_graph` — `node.edges` | Sorted by `(body1, body2, aspect)` |
| `aspect_harmonic_profile` — `by_body` keys | Sorted body-name order |
| `aspect_harmonic_profile` — `counts` keys | `AspectFamily` declaration order |
| `aspect_harmonic_profile` — `dominant` | Sorted by `AspectFamily.value` (alphabetical) |

---

### 4. Failure Doctrine

The following table lists every condition that raises an exception, the
exception type, and the diagnostic guarantee:

| Function / constructor | Condition | Exception | Diagnostic guarantee |
|---|---|---|---|
| `aspect_strength` | `allowed_orb <= 0` | `ValueError` | Message includes `"allowed_orb"` and the offending value |
| `aspect_strength` | `orb > allowed_orb` | `ValueError` | Message includes `"orb"` and both values |
| `aspect_strength` | Non-finite or negative geometry | `ValueError` | Message identifies `orb` or `allowed_orb` |
| `AspectPolicy` | `orb_factor <= 0` | `ValueError` | Message includes `"orb_factor"` |
| `AspectPolicy` | `declination_orb < 0` | `ValueError` | Message includes `"declination_orb"` |
| `AspectPolicy` | Invalid tier, flag, mapping, or non-finite value | `ValueError` | Message identifies the policy field |
| Detection entry points | Non-finite longitude/declination/speed or out-of-range declination | `ValueError` | Message identifies the geometry field |

All functions remain pure computations over valid inputs. Collection-oriented
detectors return empty results for empty valid mappings; first-class analysis
surfaces require at least two included points.

#### Behaviour on empty input

| Function | Input | Returns |
|---|---|---|
| `find_aspects` | `{}` | `[]` |
| `find_declination_aspects` | `{}` | `[]` |
| `find_patterns` | `[]` | `[]` |
| `build_aspect_graph` | `[]` | `AspectGraph(nodes=(), edges=(), components=())` |
| `aspect_harmonic_profile` | `[]` | `AspectHarmonicProfile(chart=empty, by_body={})` |

---

### 5. No-Mutation Guarantee

Every public function beyond the detection layer accepts its inputs by value
and does not mutate them:

| Function | Guarantee |
|---|---|
| `find_patterns(aspects)` | Does not alter `aspects` or any element of it |
| `build_aspect_graph(aspects, ...)` | Does not alter `aspects` or any element of it |
| `aspect_harmonic_profile(aspects)` | Does not alter `aspects` or any element of it |
| `aspect_strength(aspect)` | Does not alter `aspect` |
| `aspect_motion_state(aspect)` | Does not alter `aspect` |

---

### 6. Cross-Layer Consistency Rules

These rules govern the logical relationship between layers. Each rule must
hold on any output produced by the detection layer.

| Rule | Expression |
|---|---|
| Classification–family | `a.classification.family == _FAMILY_BY_NAME[a.aspect]` for all zodiacal `AspectData` |
| Classification–domain | Detector-produced `AspectData` is explicitly `ZODIACAL` or `WHOLE_SIGN` |
| Strength–surplus | `a.orb_surplus == aspect_strength(a).surplus` |
| Graph–harmonic | `sum(node.family_counts.values()) == hp.by_body[node.name].total` for every node |
| Harmonic–total | `hp.chart.total == len(aspects)` |
| Motion–is_applying | `aspect_motion_state(a) == APPLYING` ↔ `a.is_applying is True` |
| Motion–is_separating | `aspect_motion_state(a) == SEPARATING` ↔ `a.is_separating is True` |
| is_major–is_minor | `a.is_major != a.is_minor` for any classified `AspectData` |

---

### 7. Public Surface Register

Complete public surface of `moira.aspects` as of Phase 12:

#### Enumerations

| Name | Values |
|---|---|
| `AspectDomain` | `ZODIACAL`, `DECLINATION`, `WHOLE_SIGN` |
| `AspectTier` | `MAJOR`, `COMMON_MINOR`, `EXTENDED_MINOR` |
| `AspectFamily` | 18 members, including explicit `DECLINATION` and `UNKNOWN` families |
| `MotionState` | `APPLYING`, `EXACT`, `SEPARATING`, `STATIONARY`, `INDETERMINATE`, `NONE` |
| `DeclinationMotionState` | `APPLYING`, `EXACT`, `SEPARATING`, `STATIONARY`, `INDETERMINATE` |
| `AspectPatternKind` | `STELLIUM`, `T_SQUARE`, `GRAND_TRINE`, `GRAND_CROSS`, `YOD` |
| `HellenisticAspectEvaluationStatus` | `EVALUATED`, `NOT_EVALUABLE` |
| `HellenisticOvercomingRelation` | `BODY1_OVERCOMES_BODY2`, `BODY2_OVERCOMES_BODY1`, `NEITHER` |

#### Frozen dataclasses

| Name | Fields |
|---|---|
| `AspectClassification` | `domain`, `tier`, `family` |
| `HellenisticDirectionTruth` | evaluation status, aspect angle, directed arc, direction, reason |
| `HellenisticOvercomingTruth` | evaluation status, sign indices, inclusive places, relation, reason |
| `HellenisticSuperiorityTruth` | ordered body names and longitudes plus direction and overcoming components |
| `AspectPolicy` | `tier`, `include_minor`, `orbs`, `orb_factor`, `declination_orb` |
| `AspectStrength` | `orb`, `allowed_orb`, `surplus`, `exactness` |
| `AspectPattern` | `kind`, `bodies`, `aspects` |
| `AspectGraphNode` | `name`, `degree`, `edges`, `family_counts` |
| `AspectGraph` | `nodes`, `edges`, `components`; properties `hubs`, `isolated` |
| `AspectFamilyProfile` | `counts`, `total`, `proportions`, `dominant` |
| `AspectHarmonicProfile` | `chart`, `by_body` |
| `DeclinationAspectAnalysis` | `positions`, `aspects`, `orb`, `reference_frame`, `timescale`, `provenance`; derived counts and normalized mapping |
| `DeclinationAspectPolicy` | `orb`, exact/rate tolerances, hemisphere policy, equator policy |
| `DeclinationAspectMotionWitness` | selected relationship, declinations/rates, signed error, relative rate, orb/orb rate, state, policy and coordinate provenance |

#### Immutable result vessels

| Name | Rationale |
|---|---|
| `AspectData` | Frozen after complete construction by a detector |
| `DeclinationAspect` | Frozen after complete construction by a detector |
| `OutOfBoundsBody` | Frozen after complete construction by its detector |

The vessels are **terminal** (not designed for subclassing) and document their
structural invariants explicitly in their class docstrings.

#### Module-level constants

| Name | Type | Content |
|---|---|---|
| `CANONICAL_ASPECTS` | `tuple[str, ...]` | 48 canonical aspect names |
| `ASPECT_ALIASES` | read-only `Mapping[str, str]` | Declared alternatives resolving to canonical longitude names |
| `DEFAULT_POLICY` | `AspectPolicy` | Policy matching historical detection defaults |

#### Detection functions

| Name | Signature | Returns |
|---|---|---|
| `find_aspects` | `(positions, *, include_minor, tier, orbs, orb_factor, policy)` | `list[AspectData]` |
| `aspects_between` | `(body1, lon1, speed1, body2, lon2, speed2, ...)` | `list[AspectData]` |
| `aspects_to_point` | `(positions, point_name, point_lon, ...)` | `list[AspectData]` |
| `hellenistic_superiority_truth` | `(lon1, lon2, aspect_angle=None, *, body1="body1", body2="body2")` | `HellenisticSuperiorityTruth` |
| `find_declination_aspects` | `(declinations, *, orb, policy)` | `list[DeclinationAspect]` |
| `declination_aspects_from_declinations` | `(declinations, *, reference_frame, timescale, orb, policy)` | `DeclinationAspectAnalysis` |
| `declination_aspect_motion_witness` | `(body1, dec1, body2, dec2, aspect, *, speeds, orb, tolerances, reference_frame, timescale, policy)` | `DeclinationAspectMotionWitness` |

#### Derived-layer functions

| Name | Input | Returns |
|---|---|---|
| `aspect_strength` | `AspectData \| DeclinationAspect` | `AspectStrength` |
| `aspect_motion_state` | `AspectData \| DeclinationAspect` | `MotionState` |
| `find_patterns` | `list[AspectData]` | `list[AspectPattern]` |
| `build_aspect_graph` | `list[AspectData], bodies=None` | `AspectGraph` |
| `aspect_harmonic_profile` | `list[AspectData]` | `AspectHarmonicProfile` |

---

### 8. Validation Baseline

Validation uses the authoritative project `.venv` and the focused aspect,
moiety, signed-motion, synastry, pattern, public-surface, external-reference,
and relationship REST slices. Test counts are not frozen doctrine; the
completion receipt for a change records the exact commands, outcomes, skips,
fixtures, and scope exercised. Tests may change only when an explicitly
admitted contract changes, with regression coverage for the replacement law.

