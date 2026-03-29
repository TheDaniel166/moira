# Nine Parts Backend Standard

**Subsystem:** `moira/nine_parts.py`
**Computational Domain:** Abu Ma'shar's Nine Hermetic Lots
**SCP Phase:** 11 — Architecture Freeze and Validation Codex
**Status:** Constitutional

---

## Part I — Architecture Standard

### §1. Computational Definition

#### §1.1 What the Nine Parts Are

The Nine Parts are Abu Ma'shar's expansion of the classical Hermetic Lots into a
system of nine: seven lots associated with the seven classical planets, plus two
nodal lots (the Part of the Sword and the Part of the Node). Each lot is computed
as a directed arc from one chart body to another, projected from the Ascendant.

**Doctrine basis:** Abu Ma'shar, *Kitāb taḥāwil sinī al-mawālīd*. Confirmed
formulas and reversal rule: Benjamin N. Dykes, *Introductions to Traditional
Astrology* (Cazimi Press, 2010) and *Persian Nativities Vol. II* (Cazimi Press,
2010).

This subsystem is **not** the Hellenistic nonomoiria (9-fold sign subdivision)
and is **not** the Vedic Navamsha (D9 chart). The Vedic Navamsha is handled by
`moira/varga.py`. The Hellenistic nonomoiria is not currently implemented.

#### §1.2 Formula Table

All nine parts use the formula: `Longitude = (Asc + Add − Sub) mod 360°`

| # | Part | Planet | Day Add | Day Sub |
|---|---|---|---|---|
| 1 | Fortune | Moon | Moon | Sun |
| 2 | Spirit | Sun | Sun | Moon |
| 3 | Love | Venus | Spirit | Fortune |
| 4 | Necessity | Mercury | Fortune | Spirit |
| 5 | Courage | Mars | Fortune | Mars |
| 6 | Victory | Jupiter | Jupiter | Spirit |
| 7 | Nemesis | Saturn | Fortune | Saturn |
| 8 | Sword | — | Mars | Saturn |
| 9 | Node | — | North Node | Moon |

Parts 3 (Love), 4 (Necessity), and 6 (Victory) are **derived**: their formula
ingredients include other computed lots (Fortune and/or Spirit), not only raw
planet longitudes. The engine computes Fortune and Spirit first; derived parts
are computed after.

#### §1.3 Night Reversal Rule

Abu Ma'shar applies **full reversal** for all nine parts for night charts. For
night charts, the Add and Sub operands are swapped:

`Night formula: Longitude = (Asc + Day_Sub − Day_Add) mod 360°`

**Night definition:** the chart is nocturnal when the Sun is in houses 1–6
(below the horizon). The caller supplies `is_night_chart: bool`; the engine
does not determine sect independently.

**No per-lot exceptions.** The full reversal applies to all nine parts
uniformly. This is the Abu Ma'shar standard confirmed by Dykes. Some medieval
editors stopped reversing the Part of Fortune following a misreading of Ptolemy;
this engine does not follow that error.

#### §1.4 Dependency Order

```
Step 1: Fortune (raw: Moon, Sun)
        Spirit  (raw: Sun, Moon)
Step 2: Love       (derived: Spirit, Fortune)
        Necessity  (derived: Fortune, Spirit)
        Courage    (raw: Fortune [computed], Mars)
        Victory    (derived: Spirit [computed], Jupiter)
        Nemesis    (raw: Fortune [computed], Saturn)
        Sword      (raw: Mars, Saturn)
        Node       (raw: North Node, Moon)
```

The engine enforces this order internally. Callers do not control computation
order.

---

### §2. Public API

#### §2.1 Primary Entry Point

```python
def nine_parts_abu_mashar(
    asc: float,
    planets: dict[str, float],
    is_night_chart: bool,
    policy: NinePartsPolicy = DEFAULT_NINE_PARTS_POLICY,
) -> NinePartsAggregate
```

**Parameters:**

| Parameter | Type | Description |
|---|---|---|
| `asc` | `float` | Ascendant longitude in degrees [0, 360) |
| `planets` | `dict[str, float]` | Planet name → longitude mapping |
| `is_night_chart` | `bool` | True when Sun is in houses 1–6 |
| `policy` | `NinePartsPolicy` | Doctrinal configuration |

**Required planet keys:** `Sun`, `Moon`, `Mars`, `Jupiter`, `Saturn`,
`North Node`.

**Returns:** `NinePartsAggregate` — complete result with all parts, dependency
relations, per-part condition profiles, and aggregate intelligence.

**Raises:** `KeyError` if a required planet key is missing; `ValueError` if
any longitude is non-finite.

#### §2.2 Validation Entry Point

```python
def validate_nine_parts_output(aggregate: NinePartsAggregate) -> list[str]
```

Returns a list of failure strings. An empty list confirms full consistency.
See §4 (Validation Codex) for the complete check list.

---

### §3. Type Surface

#### §3.1 Classification Namespaces

| Type | Values | Purpose |
|---|---|---|
| `NinePartName` | `FORTUNE` … `NODE` | Canonical Abu Ma'shar part names |
| `NinePartFormulaVariant` | `DAY`, `NIGHT` | Which formula column was applied |
| `NinePartDependencyKind` | `DIRECT`, `DERIVED` | Whether the formula uses other lots |
| `NinePartsReversalRule` | `FULL_REVERSAL` | Only admitted reversal doctrine |

#### §3.2 Policy Surface

```python
@dataclass(frozen=True)
class NinePartsPolicy:
    reversal_rule: NinePartsReversalRule = NinePartsReversalRule.FULL_REVERSAL
```

`DEFAULT_NINE_PARTS_POLICY` is the module-level default instance.

The only admitted reversal rule is `FULL_REVERSAL`. No other option is
historically supported for the Abu Ma'shar Nine Parts system.

#### §3.3 Truth-Preservation Vessel — NinePartComputationTruth

Preserved per part. Records every operand and decision made during formula
evaluation.

| Field | Type | Description |
|---|---|---|
| `asc_longitude` | `float` | Ascendant used for projection |
| `add_key` | `str` | Add operand key (after reversal) |
| `sub_key` | `str` | Sub operand key (after reversal) |
| `add_longitude` | `float` | Resolved longitude of add operand |
| `sub_longitude` | `float` | Resolved longitude of sub operand |
| `is_night_chart` | `bool` | Whether chart was nocturnal |
| `formula_reversed` | `bool` | Whether night reversal was applied |
| `formula_variant` | `NinePartFormulaVariant` | DAY or NIGHT |
| `formula` | `str` | Human-readable formula string |

**Invariant:** `formula_reversed` implies `is_night_chart`. `formula_variant`
is `NIGHT` iff `formula_reversed` is True. `formula` must equal
`f"Asc + {add_key} − {sub_key}"`.

#### §3.4 Primary Result Vessel — NinePart

| Field | Type | Description |
|---|---|---|
| `name` | `NinePartName` | Canonical name |
| `planet_association` | `str \| None` | Associated planet; `None` for Sword and Node |
| `meaning` | `str` | Brief interpretive domain |
| `longitude` | `float` | Computed longitude [0, 360) |
| `sign` | `str` | Sign name |
| `sign_degree` | `float` | Degree within sign [0, 30) |
| `sign_symbol` | `str` | Glyph character |
| `dependency_kind` | `NinePartDependencyKind` | DIRECT or DERIVED |
| `computation` | `NinePartComputationTruth` | Full computation audit trail |

**Invariants:** `longitude` in [0, 360); `sign_degree` in [0, 30);
`sign` matches `sign_of(longitude)`.

**Phase 3 properties:**

| Property | Returns | Description |
|---|---|---|
| `is_derived` | `bool` | True when `dependency_kind` is DERIVED |
| `is_nocturnal_formula` | `bool` | True when night formula was used |
| `has_planet_association` | `bool` | False only for Sword and Node |
| `degrees_in_sign` | `int` | Whole degrees in sign |
| `minutes_in_sign` | `int` | Arc minutes within whole degree |

#### §3.5 Relational Vessel — NinePartsDependencyRelation

| Field | Type | Description |
|---|---|---|
| `part` | `NinePartName` | The part whose dependency is described |
| `lot_dependencies` | `tuple[NinePartName, ...]` | Lots this formula depends on |

**Invariant:** `lot_dependencies` must match the canonical dependency list for
the named part. Empty for direct parts.

**Properties:** `is_direct` (no lot dependencies), `dependency_count`.

#### §3.6 Relational Group Vessel — NinePartsSet

| Field | Type | Description |
|---|---|---|
| `parts` | `list[NinePart]` | Nine parts in canonical order |
| `is_night_chart` | `bool` | Sect of the chart |
| `policy` | `NinePartsPolicy` | Policy used |
| `dependency_relations` | `list[NinePartsDependencyRelation]` | One per part |

**Invariants:** exactly 9 parts; exactly 9 dependency relations; all parts
share the same `is_night_chart`.

**Methods:** `get(name)`, `get_dependency_relation(name)`.

**Phase 6 properties:** `direct_parts`, `derived_parts`,
`nocturnal_formula_count`, `planetary_parts`, `nodal_parts`.

#### §3.7 Condition Vessel — NinePartConditionProfile

| Field | Type | Description |
|---|---|---|
| `part` | `NinePart` | The part |
| `dependency_relation` | `NinePartsDependencyRelation` | Dependency relation |
| `lord` | `str` | Traditional domicile ruler of the part's sign |
| `lord_is_part_planet` | `bool` | True when lord == part's planet association |

**Invariant:** `lord` must match `_SIGN_RULER[part.sign]`.

**Properties:** `is_in_own_sign`, `is_derived`.

#### §3.8 Aggregate Vessel — NinePartsAggregate

| Field | Type | Description |
|---|---|---|
| `parts_set` | `NinePartsSet` | Complete parts set |
| `condition_profiles` | `list[NinePartConditionProfile]` | 9 profiles |
| `policy` | `NinePartsPolicy` | Policy used |

**Invariant:** exactly 9 condition profiles.

**Properties:** `parts_in_own_sign`, `unique_lords`, `dominant_lord`.

**Methods:** `get_profile(name)`.

---

### §4. Validation Codex

`validate_nine_parts_output(aggregate)` checks:

| # | Check | Failure example |
|---|---|---|
| 1 | Exactly 9 parts | `"Expected 9 parts, found 8"` |
| 2 | Parts in canonical order | `"Part 2: expected LOVE, got COURAGE"` |
| 3 | Night consistency across parts | `"Fortune: is_night_chart mismatch"` |
| 4 | formula_reversed matches night flag | `"Fortune: formula_reversed=False but is_night_chart=True"` |
| 5 | Derived parts follow their dependencies | `"Love appears before its dependency Spirit"` |
| 6 | DERIVED classification on derived parts | `"Love: dependency_kind should be DERIVED"` |
| 7 | DIRECT classification on direct parts | `"Fortune: dependency_kind should be DIRECT"` |
| 8 | Longitudes finite and in [0, 360) | `"Fortune: longitude 361.0 not in [0, 360)"` |
| 9 | sign_degree in [0, 30) | `"Fortune: sign_degree 30.0 not in [0, 30)"` |
| 10 | Sign names match longitudes | `"Fortune: sign 'Aries' does not match sign_of(…)"` |
| 11 | Lord assignments match sign rulers | `"Fortune: lord 'Sun' does not match sign ruler for 'Cancer'"` |
| 12 | Exactly 9 condition profiles | `"Expected 9 condition profiles, found 8"` |
| 13 | Exactly 9 dependency relations | `"Expected 9 dependency relations, found 7"` |

---

### §5. Doctrine Boundaries

#### §5.1 What This Module Owns

- The Nine Parts formula catalogue for the Abu Ma'shar tradition
- Night reversal logic (FULL_REVERSAL)
- Dependency ordering enforcement (Fortune/Spirit before derived lots)
- Result vessels through all SCP layers
- Lord-of-the-part assignment (traditional domicile rulers only)

#### §5.2 What This Module Does Not Own

- Night determination (caller supplies `is_night_chart`)
- House calculation or Ascendant computation
- Solar return chart construction
- Al-Sijzi Transfer of Management mechanics (Phase 2, not yet implemented)
- Vedic Navamsha (handled by `moira/varga.py`)
- Hellenistic nonomoiria (not yet implemented)
- The Part of Fortune used elsewhere in Moira (e.g. in `lots.py` or
  `longevity.py`) is not governed by this module; each subsystem owns its
  own Fortune computation

#### §5.3 Admitted Doctrine

- Abu Ma'shar, full-reversal variant only
- Traditional (pre-modern) domicile rulers (no outer planets)
- Egyptian bounds and Dorothaean triplicity rulers are not used in this
  module; the lord-of-the-part assignment uses domicile only

#### §5.4 Deferred Doctrine (Not Yet Implemented)

- Al-Sijzi Transfer of Management: itissāl chain of the lot lord, tasyīr
  profection of the part through bounds (Phase 2)
- The intersection with `longevity.py` for the Part-based Hyleg refinement
  (Phase 2 interface design required before implementation)

---

## Part II — Implementation Notes

### §6. Module Location

`moira/nine_parts.py` — standalone module, not part of `lots.py`.

Rationale: the Nine Parts are a specific named doctrinal system (Abu Ma'shar),
not a generic lot catalogue entry. Keeping them separate prevents confusion
with the ~430-entry `PARTS_DEFINITIONS` catalogue and makes the doctrinal
scope explicit.

### §7. Relation to lots.py

The `nine_parts_abu_mashar()` engine does not call `lots.py` internally. It
reimplements the arc formula (`Asc + A − B mod 360°`) directly for the nine
parts, ensuring that the reversal rule, dependency order, and result vessels
are governed entirely by this module.

The formulas for Fortune and Spirit in `nine_parts.py` are mathematically
identical to the `"Fortune"` and `"Spirit"` entries in `lots.py`. They are not
the same objects; callers should not mix results from the two modules.

### §8. Relation to varga.py

The Vedic Navamsha (D9) is fully implemented in `moira/varga.py` via
`calculate_varga(longitude, 9)` and the `navamsa()` convenience function.
The `segment_idx % 12` formula in `varga.py` naturally encodes the Vedic
elemental starting-point rule and produces correct navamsha sign assignments.
No additional navamsha work is needed in `nine_parts.py`.

---

## Part III — Change Policy

### §9. Stability Guarantees

The following are **frozen** and require a doctrine review before changing:

- `_NINE_PARTS_CATALOGUE` — the nine formula definitions
- `NinePartName` enum values and their order
- `NinePartsReversalRule.FULL_REVERSAL` semantics
- The dependency order (Fortune/Spirit before derived lots)

The following are **internal** and may change without API notice:

- `_SIGN_RULER`, `_DERIVED_PARTS`, `_LOT_DEPENDENCIES`
- `_ALL_DEPENDENCY_RELATIONS`, `_DEPENDENCY_RELATION_BY_NAME`
- `_validate_inputs`, `_resolve_key`

### §10. Extension Points

To add Al-Sijzi Transfer of Management (Phase 2):

1. Define `LotManagement` vessel in this module
2. Add `lot_management(part, chart, date) -> LotManagement`
3. Design the `longevity.py` intersection interface in a separate doctrinal
   note before touching either module
4. Do not modify any existing Phase 1–8 vessels or the primary engine
