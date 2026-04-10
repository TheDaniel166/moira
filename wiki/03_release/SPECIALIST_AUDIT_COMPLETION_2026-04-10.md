# Specialist Audit Completion

Date: 2026-04-10

Area closed
-----------
Roadmap section 4, `Remaining Specialist Audit`, is now closed.

Modules audited
---------------
All four modules were reviewed under the five audit lenses: public-surface
honesty, hidden defaults and fallback doctrine, vessel integrity, temporal
semantics, and validation sufficiency.

---

### electional.py (396 lines, 9 unit tests — all pass)

Public-surface honesty
    All four exported names (`ElectionalPolicy`, `ElectionalWindow`,
    `find_electional_windows`, `find_electional_moments`) match `__all__` and
    the boundary docstring exactly.

Hidden defaults and fallback doctrine
    `policy=None` resolves to `ElectionalPolicy()` (step_days=1/24,
    merge_gap_days=None→1.5×step, Placidus). Documented in the docstring.
    `reader=None` calls `get_reader()` singleton. Declared as a side effect in
    the docstring.

Vessel integrity
    `ElectionalPolicy` — `frozen=True, slots=True`.
    `ElectionalWindow` — `frozen=True, slots=True`.
    `ElectionalWindow.__post_init__` enforces boundary ordering, qualifying-JD
    anchoring, and duration consistency. Raises on violation.

Temporal semantics
    All computation inputs are Julian Days (float). `datetime_from_jd` is used
    only in the best-effort `__repr__` for display; it is not a computation path.
    No naïve `datetime` inputs accepted anywhere.

Validation sufficiency
    `jd_start >= jd_end` raises. Invalid cadence and merge-gap raise at policy
    construction. Latitude/longitude range validation explicitly delegated to
    `create_chart` — documented.

Findings
    No issues. Module is clean.

---

### dasha.py (1001 lines, 66 unit tests — all pass)

Public-surface honesty
    26-symbol `__all__` matches the BOUNDARY section exactly. Five vessel types,
    three policy surfaces, and all computational functions are exported by name.

Hidden defaults and fallback doctrine
    `policy=None` resolves through `_resolve_vimshottari_policy` →
    `DEFAULT_VIMSHOTTARI_POLICY` (Lahiri ayanamsa, Julian 365.25 year). Named
    constant, not buried. Per-call overrides (`ayanamsa_system`, `year_basis`)
    take precedence over policy when supplied — override logic is explicit and
    documented.

Vessel integrity
    Policy vessels (`VimshottariYearPolicy`, `VimshottariAyanamsaPolicy`,
    `VimshottariComputationPolicy`) — all `frozen=True, slots=True`.
    Result vessels (`DashaPeriod`, `DashaActiveLine`, `DashaConditionProfile`,
    `DashaSequenceProfile`, `DashaLordPair`) — `@dataclass(slots=True)` without
    `frozen=True`. `DashaPeriod` requires post-construction mutation to populate
    `.sub` during recursive build; this is intentional and documented. The
    remaining result vessels are immutable by convention (no caller mutates them
    after construction). This is an architectural design choice, not a defect.

Temporal semantics
    `vimshottari()` guards `math.isfinite` on both `moon_tropical_lon` and
    `natal_jd`. `current_dasha()` guards the same. `DashaPeriod.start_dt` /
    `end_dt` are computed properties delegating to `datetime_from_jd`; they are
    display surfaces, not computation inputs. No naïve `datetime` inputs.

Validation sufficiency
    `validate_vimshottari_output` enforces: level-1 chronological ordering,
    level-1 non-overlap, and recursive temporal containment of sub-periods at
    all depths. `DashaActiveLine.__post_init__` enforces level assignments and
    parent-child containment (with a 1e-6 day tolerance for float precision).
    `levels` range 1–5 guarded. Policy fields validated on every call through
    `_validate_vimshottari_policy`.

Findings
    One documentation observation: four result vessels (`DashaActiveLine`,
    `DashaConditionProfile`, `DashaSequenceProfile`, `DashaLordPair`) carry
    MACHINE_CONTRACT `"mutable": false` but are decorated `@dataclass(slots=True)`
    without `frozen=True`. The claim reflects intended post-construction
    immutability, not Python enforcement. No runtime safety gap. No change
    required; noted for audit continuity.

---

### timelords.py (2022 lines, 100 unit tests — all pass)

Public-surface honesty
    28-symbol `__all__` covering Firdaria and Zodiacal Releasing surfaces in
    full. Boundary docstring is unambiguous about scope. Delegations to
    `moira.profections` (domicile rulers) and `moira.julian` (calendar views)
    are declared.

Hidden defaults and fallback doctrine
    `policy=None` resolves to `DEFAULT_TIMELORD_POLICY` through
    `_resolve_timelord_policy`. The default policy carries 365.25 days for
    Firdaria and 360 days for Zodiacal Releasing — doctrinal distinction is
    explicit.
    `variant="standard"` in `firdaria()` and `current_firdaria()` — the
    alternative `"bonatti"` affects only nocturnal charts; documented.
    `use_loosing_of_bond=True` in `zodiacal_releasing` — doctrine default is
    declared in the docstring.
    `lot_name="Spirit"` in `zodiacal_releasing` / `current_releasing` —
    declared default; admits only `{"Spirit", "Fortune", "Eros", "Necessity"}`.

Vessel integrity
    `FirdarYearPolicy`, `ZRYearPolicy`, `TimelordComputationPolicy` — all
    `frozen=True, slots=True`.
    `FirdarPeriod` and `ReleasingPeriod` are result vessels with MACHINE_CONTRACTs.
    Both expose `start_dt` / `end_dt` as computed properties, not stored datetime
    fields — no stale UTC claims possible.

Temporal semantics
    `firdaria()` guards `math.isfinite(natal_jd)`.
    `current_firdaria()` guards both `natal_jd` and `current_jd`.
    `zodiacal_releasing()` guards `lot_longitude`, `natal_jd`, and
    `fortune_longitude` when provided.
    `current_releasing()` raises when `current_jd < natal_jd` and when
    `current_jd` exceeds the full releasing circuit cap.
    No naïve `datetime` inputs anywhere in the module.

Validation sufficiency
    `validate_firdaria_output` and `validate_releasing_output` are both
    exported public validators. `lot_name` validated against the four-element
    canonical set. `levels` range 1–4 enforced. Active-period lookup raises
    when no period found rather than silently returning None.

Findings
    No issues. Module is clean.

---

### cycles.py (1392 lines, 105 unit tests — all pass)

Public-surface honesty
    28-symbol `__all__` covering enums, vessels, and all computational surfaces.
    Doctrinal attributions are preserved in vessel docstrings (Abu Ma'shar for
    great conjunctions; Ptolemy for planetary ages; Rudhyar convention for
    synodic phases).

Hidden defaults and fallback doctrine
    `reader=None` resolves to `get_reader()` singleton — same pattern as
    `electional.py`, declared in docstrings.
    Doctrinal year-length (`_JULIAN_YEAR = 365.25`) is a module-level named
    constant used for returns, ages, and Firdaria surfaces in this module.
    Authority preference visible.

Vessel integrity
    All result vessels — `ReturnEvent`, `ReturnSeries`, `SynodicCyclePosition`,
    `GreatConjunction`, `GreatConjunctionSeries`, `MutationPeriod`,
    `PlanetaryAgePeriod`, `PlanetaryAgeProfile` — are `frozen=True, slots=True`.
    This module achieves full result-vessel immutability without exceptions.

Temporal semantics
    All computational inputs are Julian Days. Exact return solving is delegated
    to `moira.transits`; `cycles.py` passes only JDs to that layer. Synodic
    geometry delegation to astronomical Pillars is declared in the boundary
    docstring. No naïve `datetime` inputs.

Validation sufficiency
    `SynodicPhase.from_angle` normalizes input via `% 360.0` before
    classification — handles arbitrary float input gracefully. Return-series
    functions delegate input validation to the solver layer (`moira.transits`).
    Great-conjunction solver delegates search bounds to the transits solver.

Findings
    No issues. Module is clean.

---

Exit criteria — met
-------------------
- No known protected-zone contradictions remain open in these modules.
- One architectural observation deferred (dasha.py result vessel mutability):
  documented above with rationale; no change required.
- All four test suites green (280 combined cases).
- Audit run against project `.venv` on 2026-04-10.
