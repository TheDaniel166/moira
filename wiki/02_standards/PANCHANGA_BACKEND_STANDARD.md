# Panchanga Backend Standard

**Subsystem:** `moira/panchanga.py`
**Computational Domain:** Vedic Panchanga (Five-Element Almanac)
**Constitutional Phase:** 11 — Architecture Freeze and Validation Codex
**Status:** Constitutional

---

## Part I — Architecture Standard

### §1. Computational Definitions

#### §1.1 Panchanga

The Panchanga (Sanskrit: five limbs) is the Vedic almanac. It specifies five
simultaneous qualities of any instant in time:

| Element | Sanskrit | Basis | Span |
|---|---|---|---|
| Tithi | लिर् | Moon–Sun sidereal elongation ÷ 12° | 12° |
| Vara | वार | Weekday (Julian Day ÷ 7) | time-based (sunrise→sunrise) |
| Nakshatra | नक्षत्र | Moon's sidereal longitude ÷ 13.33° | 13.33° |
| Yoga | योग | (Sun + Moon sidereal sum) ÷ (360°/27) | 13.33° |
| Karana | करण | Moon–Sun sidereal elongation ÷ 6° | 6° (half-Tithi) |

The authoritative engine is `panchanga_at(sun_tropical_lon, moon_tropical_lon, jd)`.
It returns a `PanchangaResult` containing all five elements at the requested instant.
Nakshatra computation is delegated to `moira.sidereal.nakshatra_of`.

**Tithi:** 30 Tithis per lunar month. Tithis 1–15 (indices 0–14) belong to Shukla
Paksha (waxing / bright fortnight); Tithis 16–30 (indices 15–29) to Krishna Paksha
(waning / dark fortnight). Tithi 15 (index 14) is Purnima (Full Moon); Tithi 30
(index 29) is Amavasya (New Moon).

**Vara:** Seven weekday lords in Sunday-origin order: Sun, Moon, Mars, Mercury,
Jupiter, Venus, Saturn. The Julian Day formula `int(jd + 1.5) % 7` gives the 0-based
index. Vara does not have a degree span; `degrees_elapsed` and `degrees_remaining`
are both 0.0 on its `PanchangaElement`.

**Nakshatra:** Delegated entirely to `moira.sidereal.nakshatra_of`. The returned
object is stored as `PanchangaResult.nakshatra` (typed as `object` to avoid circular
imports).

**Yoga:** 27 Yogas, each spanning 360°/27 ≈ 13.33°. Five are traditionally
inauspicious (Ashubha Yoga) per Parashari canon: Atiganda (index 5), Shula (index 8),
Ganda (index 9), Vyatipata (index 16), and Vaidhriti (index 26). These are recorded
in `_ASHUBHA_YOGA_INDICES`.

**Karana:** 60 Karanas per lunar month (two per Tithi). Positions 1–56 cycle through
7 movable Karanas (Bava, Balava, Kaulava, Taitila, Gara, Vanija, Vishti). Positions
0, 57, 58, 59 are fixed Karanas: Kimstughna, Shakuni, Chatushpada, Naga respectively.

**Planet type for Vara lords (`VaraLordType`):**

| Value | Planets |
|---|---|
| `LUMINARY` | Sun, Moon |
| `INNER` | Mercury, Venus, Mars |
| `OUTER` | Jupiter, Saturn |

Ketu is never a Vara lord.

---

### §2. Layer Structure

| Layer | Phase | Vessel / Function |
|---|---|---|
| 0 | Core | `panchanga_at()` |
| 1 | Truth Preservation | `PanchangaElement`, `PanchangaResult` |
| 2 | Classification | `TithiPaksha`, `YogaClass`, `KaranaType`, `VaraLordType` |
| 3 | Inspectability | `span`, `fraction_elapsed` on `PanchangaElement`; `is_dark_fortnight`, `is_purnima`, `is_amavasya`, `is_auspicious_yoga` on `PanchangaResult` |
| 4 | Policy | `PanchangaPolicy`, `policy` parameter on `panchanga_at()` |
| 5–6 | (Relational) | Not applicable — the five Panchanga elements are parallel, not hierarchical |
| 7 | Integrated Local Condition | `TithiConditionProfile`, `tithi_condition_profile()` |
| 8 | Aggregate Intelligence | `PanchangaProfile`, `panchanga_profile()` |
| 9 | (Network) | Not applicable at this domain scale |
| 10 | Hardening | `validate_panchanga_output()` |

Note: Phases 5–6 (Relational Formalization and Relational Hardening) do not apply
here. The five Panchanga elements are computed in parallel with no containment or
ordering relationship between them. Phase 9 (Network Intelligence) is similarly
inapplicable; no meaningful two-element network pair exists at the scale of a single
Panchanga instant.

---

### §3. Delegated Assumptions

The Panchanga subsystem does not compute the following. Callers are responsible for
supplying correct values.

- `sun_tropical_lon`: the tropical ecliptic longitude of the Sun, from an ephemeris
- `moon_tropical_lon`: the tropical ecliptic longitude of the Moon, from an ephemeris
- Ayanamsa application: the subsystem applies the configured ayanamsa internally via
  `moira.sidereal.tropical_to_sidereal`; the caller supplies tropical longitudes
- Sunrise correction for Vara: the implementation uses JD directly; Vara may differ
  from strict Vedic reckoning near midnight before local sunrise. This is a declared
  limitation.

---

### §4. Doctrine Surface

| Choice | Location | Default |
|---|---|---|
| Tithi span | Inline constant `12.0` | 12° per Tithi |
| Yoga span | `_YOGA_SPAN` module constant | 360°/27 ≈ 13.333° |
| Karana span | Inline constant `6.0` | 6° per Karana |
| Weekday origin | `_vedic_weekday()` | Sunday = 0 |
| Vara lord sequence | `VARA_LORDS` module constant | Sun, Moon, Mars, Mercury, Jupiter, Venus, Saturn |
| Ashubha Yoga indices | `_ASHUBHA_YOGA_INDICES` module constant | {5, 8, 9, 16, 26} (0-based) |
| Fixed Karana positions | `_karana_name()` / `panchanga_profile()` | 0, 57, 58, 59 |
| Ayanamsa | `PanchangaPolicy.ayanamsa_system` or `ayanamsa_system` arg | `'Lahiri'` |

---

### §5. Public Vessels

**Classification constants:**
- `TithiPaksha` — string constants SHUKLA / KRISHNA for the two fortnights
- `YogaClass` — string constants AUSPICIOUS / INAUSPICIOUS
- `KaranaType` — string constants MOVABLE / FIXED
- `VaraLordType` — string constants LUMINARY / INNER / OUTER

**Policy:**
- `PanchangaPolicy` — frozen dataclass with `ayanamsa_system`

**Name tables:**
- `TITHI_NAMES` — 30 Tithi names (Pratipada … Amavasya)
- `YOGA_NAMES` — 27 Yoga names (Vishkumbha … Vaidhriti)
- `KARANA_NAMES` — 11 Karana names (7 movable + 4 fixed)
- `VARA_LORDS` — 7 weekday planetary lords (Sunday-origin)
- `VARA_NAMES` — 7 Vedic weekday names (Sunday-origin)

**Truth-preservation vessels:**
- `PanchangaElement` — immutable vessel for one of the five elements
- `PanchangaResult` — immutable vessel for the complete five-element Panchanga

**Condition vessels:**
- `TithiConditionProfile` — integrated condition for the Tithi element (paksha, Purnima/Amavasya flags)

**Aggregate vessels:**
- `PanchangaProfile` — chart-wide aggregate: paksha, yoga_class, karana_type, vara_lord_type

**Computational functions:**
- `panchanga_at(sun_tropical_lon, moon_tropical_lon, jd, ayanamsa_system, policy)` — core engine
- `tithi_condition_profile(result)` — build a `TithiConditionProfile`
- `panchanga_profile(result)` — build a `PanchangaProfile`
- `validate_panchanga_output(result)` — invariant guard

---

## Part II — Terminology Standard

### §6. Required Terms

| Term | Normative Meaning |
|---|---|
| **Tithi** | Lunar day; one of 30 per month; spans 12° of Moon–Sun elongation |
| **Vara** | Vedic weekday; determined by Julian Day; associated with one of 7 planetary lords |
| **Nakshatra** | Lunar mansion; determined by Moon's sidereal longitude; delegated to `moira.sidereal` |
| **Yoga** | One of 27 spans of the combined Sun+Moon sidereal sum; each spans ≈ 13.33° |
| **Karana** | Half-Tithi; 60 per month; spans 6° of Moon–Sun elongation |
| **Shukla Paksha** | Waxing (bright) fortnight; Tithis 1–15, indices 0–14 |
| **Krishna Paksha** | Waning (dark) fortnight; Tithis 16–30, indices 15–29 |
| **Purnima** | Full Moon; Tithi index 14 |
| **Amavasya** | New Moon; Tithi index 29 |
| **Ashubha Yoga** | One of the five traditionally inauspicious Yogas; indices {5, 8, 9, 16, 26} |
| **index** | 0-based position in the element's cycle (stored in `PanchangaElement.index`) |
| **number** | 1-based position; always `index + 1` (stored in `PanchangaElement.number`) |
| **span** | The arc length of the element's division: 12° for Tithi, 6° for Karana, ≈13.33° for Yoga, 0 for Vara |
| **degrees_elapsed** | Arc elapsed within the current span at the queried instant |
| **degrees_remaining** | Arc remaining until the next span boundary |
| **vara lord type** | `VaraLordType` structural classification of the weekday's ruling planet |

---

### §7. Forbidden Conflations

**`PanchangaElement` and `PanchangaResult`**
`PanchangaElement` is the vessel for one of the five elements. `PanchangaResult`
is the aggregate result for all five. An element must not be treated as a result.

**`degrees_elapsed` and `fraction_elapsed`**
`degrees_elapsed` is a raw arc value. `fraction_elapsed` is a proportion in [0, 1].
They convey related but different quantities.

**`index` and `number`**
`index` is 0-based (used for array access). `number` is 1-based (used for traditional
Jyotish notation). `PanchangaElement.number == index + 1` always.

**`Vara` and a degree-based element**
Vara is time-based, not degree-based. Its `PanchangaElement` always has
`degrees_elapsed == degrees_remaining == span == 0.0`. It must not be used in
degree arithmetic.

**`PanchangaResult.is_purnima` and `tithi.index == 14`**
These are semantically equivalent. `is_purnima` is the preferred inspectability
accessor. Using raw index comparisons in downstream code is acceptable but `is_purnima`
conveys intent.

**`TithiConditionProfile.paksha` and `PanchangaResult.is_dark_fortnight`**
`is_dark_fortnight` returns a bool (Krishna = True). `paksha` returns a `TithiPaksha`
constant string. They test the same condition but serve different purposes.

**`YogaClass.INAUSPICIOUS` and "inauspicious Yoga"**
`YogaClass.INAUSPICIOUS` is a classification constant. Whether a Yoga is inauspicious
is determined by `_ASHUBHA_YOGA_INDICES`. The class constant is the label; the set is
the authoritative gate.

---

## Part III — Invariant Register

### §8.1 Vessel Invariants

**`PanchangaElement`:**
- `index >= 0`
- `number == index + 1`
- `degrees_elapsed >= 0.0`
- `degrees_remaining >= 0.0`

**`PanchangaResult`:**
- `jd` is finite (not NaN, not ±Inf)
- `ayanamsa_system` is non-empty
- `tithi.index` ∈ [0, 29]
- `yoga.index` ∈ [0, 26]
- `karana.index` ∈ [0, 59]
- `vara.index` ∈ [0, 6]
- `vara_lord` ∈ `VARA_LORDS`

---

### §8.2 Truth Invariants

- `TITHI_NAMES`, `YOGA_NAMES`, `KARANA_NAMES`, `VARA_LORDS`, `VARA_NAMES` are
  immutable module-level constants. No function modifies them at runtime.
- `_ASHUBHA_YOGA_INDICES` is a frozen set. No function modifies it at runtime.
- `_YOGA_SPAN` is computed once at module load from `360.0 / 27`.
- `PanchangaResult.vara.degrees_elapsed` and `.degrees_remaining` are always 0.0.
- Nakshatra is delegated: `PanchangaResult.nakshatra` is the object returned by
  `moira.sidereal.nakshatra_of`. Its internal structure is not validated by this
  subsystem.

---

### §8.3 Aggregate Invariants

**`PanchangaProfile`:**
- `paksha` ∈ {`TithiPaksha.SHUKLA`, `TithiPaksha.KRISHNA`}
- `yoga_class` ∈ {`YogaClass.AUSPICIOUS`, `YogaClass.INAUSPICIOUS`}
- `karana_type` ∈ {`KaranaType.MOVABLE`, `KaranaType.FIXED`}
- `vara_lord` ∈ `VARA_LORDS`
- `vara_lord_type` ∈ {`VaraLordType.LUMINARY`, `VaraLordType.INNER`, `VaraLordType.OUTER`}
- `ayanamsa_system` is non-empty

---

### §8.4 Network Invariants

Not applicable. No network vessels are defined in this subsystem.

---

## Part IV — Failure Doctrine

### §9.1 Invalid Inputs

- Constructing `PanchangaElement` with `index < 0` raises `ValueError`.
- Constructing `PanchangaElement` with `number != index + 1` raises `ValueError`.
- Constructing `PanchangaElement` with `degrees_elapsed < 0` or `degrees_remaining < 0`
  raises `ValueError`.
- Constructing `PanchangaResult` with a non-finite `jd` raises `ValueError`.
- Constructing `PanchangaResult` with an empty `ayanamsa_system` raises `ValueError`.
- Constructing `PanchangaResult` with `tithi.index` outside [0, 29] raises `ValueError`.
- Constructing `PanchangaResult` with `vara_lord` not in `VARA_LORDS` raises `ValueError`.
- Constructing `PanchangaPolicy` with an empty `ayanamsa_system` raises `ValueError`.

---

### §9.2 Search Exhaustion

This subsystem performs no iterative search. All computation is direct arithmetic
from planetary longitudes. There is no search exhaustion failure mode.

---

### §9.3 Invariant Failure

- `validate_panchanga_output()` raises `ValueError` with a descriptive message if:
  - `jd` is not finite
  - `ayanamsa_system` is empty
  - `tithi.index`, `yoga.index`, `karana.index`, or `vara.index` are out of range
  - `vara_lord` is not in `VARA_LORDS`
  - `tithi.name` does not match `TITHI_NAMES[tithi.index]`
  - `yoga.name` does not match `YOGA_NAMES[yoga.index]`
  - `vara.name` does not match `VARA_NAMES[vara.index]`
  - Any element's `number != index + 1`
- `PanchangaResult.__post_init__` raises `ValueError` at construction time for the
  same range and validity constraints (excluding name-matching, which is checked only
  by `validate_panchanga_output`).

---

## Part V — Determinism Standard

### §10. Determinism Guarantees

- `panchanga_at()` is fully deterministic: given the same `sun_tropical_lon`,
  `moon_tropical_lon`, `jd`, and `ayanamsa_system`, the output is identical in every
  call.
- `tithi_condition_profile()`, `panchanga_profile()`, and `validate_panchanga_output()`
  are pure functions with no side effects.
- Import-time side effects: none. The module initialises only module-level constants
  and the `_YOGA_SPAN` derived value.
- No ephemeris access or external state is required. All computation is arithmetic on
  the supplied tropical longitudes after ayanamsa conversion via `moira.sidereal`.

---

## Part VI — Validation Codex

### §11. Minimum Validation Commands

```
python -m pytest tests/unit/test_panchanga.py -v
```

All tests in `test_panchanga.py` must pass. The test suite validates:
- Name table structure: lengths, no duplicates, fixed positions
- `panchanga_at()` Tithi arithmetic against independent calculation
- `panchanga_at()` Vara weekday mapping
- `panchanga_at()` Yoga arithmetic
- `panchanga_at()` Karana arithmetic including fixed Karana boundaries
- `PanchangaElement.degrees_elapsed + degrees_remaining == span` across all elements
- Field types and vessel invariants on `PanchangaResult`
- `TithiPaksha`, `YogaClass`, `KaranaType`, `VaraLordType` classification constants
- `PanchangaPolicy` construction and policy override in `panchanga_at()`
- `PanchangaElement.span` and `fraction_elapsed` properties
- `PanchangaResult.is_dark_fortnight`, `is_purnima`, `is_amavasya`, `is_auspicious_yoga`
- `PanchangaElement.__post_init__` guard behavior
- `PanchangaResult.__post_init__` guard behavior
- `tithi_condition_profile()` field fidelity, paksha classification, flag consistency
- `panchanga_profile()` paksha, yoga_class, karana_type, vara_lord_type
- `validate_panchanga_output()` acceptance of valid results and rejection of wrong
  names

---

### §12. Required Validation Themes

Any validation suite for this subsystem must demonstrate:

1. **Tithi index continuity** — as Moon–Sun elongation increases from 0° to near 360°,
   the Tithi index transitions correctly from 0 to 29.
2. **Purnima and Amavasya detection** — `is_purnima` is True exactly when
   `tithi.index == 14`; `is_amavasya` exactly when `tithi.index == 29`.
3. **Paksha classification** — index < 15 gives SHUKLA; index ≥ 15 gives KRISHNA.
4. **Policy override** — `panchanga_at()` with a `policy` uses `policy.ayanamsa_system`
   regardless of the `ayanamsa_system` positional argument.
5. **Vara determinism** — the same JD always produces the same Vara and Vara lord.
6. **Guard completeness** — every field-level invariant on `PanchangaElement` and
   `PanchangaResult` is covered by at least one rejection test.
7. **Condition profile fidelity** — `tithi_condition_profile()` preserves all Tithi
   fields and correctly sets `is_purnima`, `is_amavasya`, and `paksha`.
8. **Aggregate consistency** — `panchanga_profile()` yoga_class is INAUSPICIOUS if
   and only if `yoga.index` is in `_ASHUBHA_YOGA_INDICES`; karana_type is FIXED if
   and only if `karana.index` ∈ {0, 57, 58, 59}.
9. **Name-index fidelity** — `validate_panchanga_output()` detects any mismatch
   between an element's `name` field and the canonical name list at that index.
