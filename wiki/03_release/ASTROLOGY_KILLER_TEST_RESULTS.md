# Astrology Killer Test Results

Status: verified in the project `.venv`

Purpose
-------
This report records the first dedicated adversarial astrology gauntlet for
Moira.

These are not interpretive demonstrations.
They are doctrine, boundary, policy, and public-path validation checks for:

- zodiac, house, aspect, and nakshatra boundary behavior
- antiscia, midpoint dial, and Arabic mansion seam behavior
- day/night lot reversal truth
- lot dependency-network determinism
- aspect semantic invariance under input permutation
- dignity sign-boundary discipline
- profection cycle, monthly lord, and activation behavior
- Vimshottari boundary and cycle-failure behavior
- Firdaria and Zodiacal Releasing containment and boundary behavior
- explicit sidereal electional evaluation support
- malformed doctrine-input failure behavior
- public chart vessel truth preservation across derived astrology layers

Proof files
-----------
- `tests/unit/test_astrology_adversarial_gauntlet.py`
- `tests/unit/test_electional.py`

Verification command
--------------------
- `python -m pytest tests/unit/test_astrology_adversarial_gauntlet.py -q`
- `python -m pytest tests/unit/test_electional.py -q`

All listed commands passed on 2026-04-24.

---

## 1. Boundary Assassins

Measured surfaces:

| Boundary | Assertion |
| --- | --- |
| Zodiac sign seam | `29.999999999` Aries, `30.0` Taurus, `359.999999999` Pisces, `360.0` Aries |
| House cusp seam | Point just before cusp remains in prior house; exact cusp belongs to opening house |
| Aspect orb seam | Exact allowed-orb sextile is admitted; `0.000001 deg` outside is rejected |
| Nakshatra seam | Final instant of first nakshatra remains index `0`; exact boundary advances to index `1`, pada `1` |
| Arabic mansion seam | Final instant of first mansion remains mansion `1`; exact boundary advances to mansion `2` |
| Zodiac wrap | `360.0 deg` returns to first sign and first mansion |

Interpretation:

- Core astrology arithmetic honors half-open interval doctrine at sign,
  house, aspect, and nakshatra boundaries.
- No off-by-one or wraparound bleed was observed in the tested seams.

---

## 2. Mirror And Dial Geometry

Measured surfaces:

| Attack | Assertion |
| --- | --- |
| Antiscion round-trip | `antiscion(antiscion(lon)) == lon mod 360` across seams |
| Contra-antiscion round-trip | `contra(contra(lon)) == lon mod 360` across seams |
| Near-wrap antiscion contact | `359.999999999 -> 180.000000001` detected inside `1e-6 deg` |
| Midpoint seam | `350/10` and `10/350` both midpoint to `0.0 deg` |
| 90-degree dial seam | `90.0 deg` folds to `0.0 deg`; just-before value remains just before the dial seam |

Interpretation:

- Hidden-point arithmetic is reversible where doctrine requires it.
- Dial folding and shorter-arc midpoint behavior remain coherent at the
  circular seam.

---

## 3. Lots Day/Night Reversal

Fixed synthetic chart:

| Input | Value |
| --- | ---: |
| Ascendant | `100.0 deg` |
| Sun | `20.0 deg` |
| Moon | `80.0 deg` |

Measured doctrine:

| Lot | Day formula result | Night formula result |
| --- | ---: | ---: |
| Fortune | `Asc + Moon - Sun = 160.0 deg` | `Asc + Sun - Moon = 40.0 deg` |
| Spirit | `Asc + Sun - Moon = 40.0 deg` | `Asc + Moon - Sun = 160.0 deg` |

Truth preservation:

- Day Fortune preserved `effective_add_key == "Moon"` and
  `effective_sub_key == "Sun"`.
- Night Fortune preserved `reversed_for_chart == True` with
  `effective_add_key == "Sun"` and `effective_sub_key == "Moon"`.

Interpretation:

- Fortune and Spirit reverse visibly by doctrine.
- The result vessel preserves the computational path rather than merely
  returning a longitude.

---

## 4. Lot Dependency-Network Determinism

Measured surface:

| Attack | Assertion |
| --- | --- |
| Reversed planet input order | Same lot-network nodes, edges, isolated set, and most-connected set |
| Network node accounting | Incoming, outgoing, and reciprocal counts remain identical |
| Network edge accounting | Source, target, dependency role, and reciprocal/unilateral mode remain identical |

Interpretation:

- Lot network truth is independent of caller mapping insertion order.
- Derived lot dependencies remain stable as a graph, not merely as isolated
  longitude results.

---

## 5. Aspect Permutation Attack

Measured surface:

| Attack | Assertion |
| --- | --- |
| Reversed input insertion order | Same unordered body pairs, aspect names, and orbs |
| Graph profile | Node and edge accounting remains internally consistent |
| Harmonic profile | Chart total equals admitted aspect count; per-body totals match graph degree |

Interpretation:

- Aspect semantics survive input permutation.
- The test intentionally does not require `body1/body2` orientation to change;
  Moira currently preserves caller-discovery orientation in the result vessel.

---

## 6. Dignity Sign-Boundary Discipline

Measured surface:

| Probe | Result |
| --- | --- |
| Sun at `149.999999999 deg` | Leo, domicile |
| Moon at `150.0 deg` | Virgo, not domicile |

Interpretation:

- Essential dignity does not bleed across the Leo/Virgo boundary.
- Structured essential-truth metadata agrees with the visible sign.

---

## 7. Profection Cycle Attack

Measured surface:

| Probe | Result |
| --- | --- |
| Age `0` and age `12` | Same profected house, sign, lord, and monthly-lord sequence |
| Age `13` | Advances to house `2`, Taurus, Venus |
| Month `0` at age `13` | Taurus / Venus |
| Month `11` at age `13` | Aries / Mars |
| Activation seam | Body within `1e-6 deg` of profected Asc is admitted; distant body is rejected |

Interpretation:

- Annual profection preserves its 12-year cycle.
- Monthly lord sequence wraps correctly and does not smear activation across
  a loose boundary.

---

## 8. Vimshottari Doctrine Boundary

Measured surface:

| Probe | Result |
| --- | --- |
| Moon just before nakshatra boundary | First Vimshottari lord |
| Moon exactly at boundary | Second Vimshottari lord |
| Exact-boundary first mahadasha | `nakshatra_fraction == 0.0` |
| Query before birth | Explicit `ValueError` |
| Unsupported year basis | Explicit `ValueError` |

Interpretation:

- Dasha entry is boundary-honest.
- Doctrine settings fail explicitly rather than falling back to an ambient
  default.

---

## 9. Timelord Containment And Boundary Attack

Measured surface:

| Probe | Result |
| --- | --- |
| Firdaria output | Public validator accepts generated hierarchy |
| Firdaria major sequence | Matches declared diurnal sequence |
| Firdaria total span | Major periods sum to `75.0` years |
| Exact first-major end | Active major advances to next major; half-open interval honored |
| End of 75-year cycle | Explicit `ValueError` |
| Zodiacal Releasing output | Public validator accepts level containment through level `3` |
| Invalid ZR level | Explicit `ValueError` |
| Invalid lot name | Explicit `ValueError` |

Interpretation:

- Time-lord hierarchies preserve containment and half-open boundary doctrine.
- Invalid symbolic doctrine requests fail explicitly.

---

## 10. Malformed Doctrine Inputs

Measured failures:

| Malformation | Result |
| --- | --- |
| Incomplete house-cusp map for lots | Explicit `ValueError` |
| Strict unresolved-reference policy | Explicit `ValueError` |
| Invalid aspect policy orb factor | Explicit `ValueError` |

Interpretation:

- Malformed doctrine inputs are rejected before silent substitution.
- Policy failure remains visible to callers.

---

## 11. Electional Sidereal Evaluation

Measured surface:

| Probe | Result |
| --- | --- |
| Default tropical policy | Predicate still receives the legacy chart payload |
| Explicit sidereal policy | Predicate receives `ElectionalEvaluation` |
| Sidereal planet longitudes | Tropical chart longitudes are converted through declared ayanamsa |
| Sidereal node longitudes | Node longitude view is converted through the same policy |
| Sidereal house cusps | House-cusp view is converted without mutating the chart |
| Policy failures | Invalid frame, mode, or empty sidereal ayanamsa fail explicitly |

Interpretation:

- Electional search is no longer tropical-only when the caller requests a
  sidereal evaluation frame.
- The underlying chart remains the astronomical truth carrier; sidereal
  electional work is exposed as an explicit evaluation view.

---

## 12. Public Chart Vessel Truth Preservation

Measured public path:

| Derived layer | Assertion |
| --- | --- |
| Lots | Fortune recomputes from chart-carried Asc, Sun, Moon, and sect |
| Aspects | Motion state classification remains in the declared finite enum set |
| Dignities | Every chart-carried planet receives a dignity result |
| Lot network | Node and edge counts match their materialized vessels |

Interpretation:

- Public chart assembly preserves lower-layer astrology truth.
- Derived layers consume the chart vessel without mutating or replacing its
  carried astronomical positions.

---

## Summary Table

| Challenge | Result | Evidence |
| --- | --- | --- |
| Boundary assassins | Pass | Sign, house, aspect, and nakshatra seams behave cleanly |
| Mirror and dial geometry | Pass | Antiscia, midpoint, dial, and mansion seams behave coherently |
| Lots reversal truth | Pass | Fortune/Spirit day-night reversal and operand truth preserved |
| Lot network determinism | Pass | Dependency graph survives reversed input order |
| Aspect permutation attack | Pass | Semantic aspect set survives reversed input order |
| Dignity boundary discipline | Pass | Domicile does not bleed across Leo/Virgo seam |
| Profection cycle attack | Pass | 12-year return, monthly wrap, and activation seam hold |
| Vimshottari boundary doctrine | Pass | Nakshatra lord transition and failure modes are explicit |
| Timelord containment attack | Pass | Firdaria and Zodiacal Releasing validate hierarchy and boundaries |
| Electional sidereal evaluation | Pass | Sidereal predicate view exists without mutating chart substrate |
| Malformed doctrine inputs | Pass | Bad policies and incomplete inputs fail visibly |
| Public chart truth preservation | Pass | Lots, aspects, dignities, and lot network stay coherent from chart vessel |

Bottom line

Moira now has a dedicated adversarial astrology killer-test layer. It does not
pretend interpretive doctrine is a physical oracle. It proves the appropriate
thing: explicit doctrine, clean boundaries, visible policy, deterministic
semantic behavior, and public-path truth preservation.
