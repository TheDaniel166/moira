# Moira Engine: Frontiers, Polish & Deferred Work Register (2026)

**Governing Authority**: Moira Canonical Instruction (`AGENTS.md`)  
**Audit Date**: September 21, 2026  
**Baseline Version**: Moira 6.8.2+ (Post-Tier 2 Houses & Nutation Caching)

---

## 1. Overview & Purpose

This register catalogs all source-level **stubs**, **placeholders**, **deferred doctrinal vessels**, and **active computational frontiers** identified during the repository-wide audit of Moira's core engine (`moira/`), native substrate (`src/native/`), and server transport layer (`moira_server/`).

In alignment with Moira's **Law of Policy Explicitness** and **Documentation Law**, every item is recorded with its precise file anchor, architectural rationale, and verified gate conditions.

---

## 2. Category A — Immediate Polish & Documentation Debt

These items represent discrepancies between live executable code and comments or documentation, or small harness-level stubs.

| Target | Location | Classification | Current State & Resolution |
| :--- | :--- | :--- | :--- |
| **`moira.sky` Subsystem Headers** | [`moira/sky/__init__.py`](file:///c:/dev/moira/moira/sky/__init__.py#L31-L56) | Stale Docstrings | **REMEDIATED (2026-09-21)**. Removed stale `[stub]` markers from all 6 fully-implemented astronomy submodules (`bodies`, `observation`, `galactic`, `events`, `eclipse`, `occultation`) and synchronized the design contract. |
| **Export Policy Subsystem** | `moira/_export_governance/` | Dead Subsystem | **REMEDIATED (2026-09-21)**. Excised unused `moira/_export_governance` package (11 modules), associated `tests/export_governance` (8 test suites / 162 tests), old audit reports (`reports/governance/`), and one-shot archived audit scripts. Port compliance verified across 282 engine files. |
| **Stars Bulk Serializer** | [`moira_server/serializers/stars.py`](file:///c:/dev/moira/moira_server/serializers/stars.py#L139) | Transport Placeholder | `dt=results.get("dt") if isinstance(results, dict) else None, # placeholder` in `serialize_stars_bulk`. |

---

## 3. Category B — Active Computational Frontiers

Three high-priority frontiers identified during the post-6.8.2 optimization survey:

### Frontier 1: Planetary Reduction Pipeline (`all_planets_at` Cash-In)
- **Status**: **COMPLETED & VERIFIED** (September 2026)
- **Anchors**: [`src/native/include/planetary_evaluator.hpp`](file:///c:/dev/moira/src/native/include/planetary_evaluator.hpp), [`src/native/bindings/moira_native.cpp`](file:///c:/dev/moira/src/native/bindings/moira_native.cpp), [`moira/planets.py`](file:///c:/dev/moira/moira/planets.py).
- **Accomplishments**:
  - Implemented `NativePlanetaryEvaluator::evaluate_all_planets_apparent_with_speed`, reducing the three sequential Python-native boundary crossings for central finite-difference speed into a single GIL-released pass.
  - Cached resolved SPK Chebyshev segment evaluators (`resolved_segments_`) across invocations, eliminating memory allocation and kernel mutex traffic.
  - Accelerated 10-planet apparent ecliptic reduction from 0.400 ms down to **0.319 ms** (3,131 charts/sec), reaching **0.227 ms** (>4,400 charts/sec) in raw C++.
  - Fixed `_prefill_npe_public_vector_cache` to iterate over all `_NPE_ADMITTED_BODIES` using canonical NAIF routes, eliminating the Mercury route lookup defect.

### Frontier 2: Aspect-Pattern Qualitative Scoring (`v1-draft`)
- **Status**: **COMPLETED & VERIFIED**
- **Anchor Documents**: [`docs/architecture/ASPECT_PATTERN_QUALITATIVE_SCORING_V1_DRAFT.md`](file:///c:/dev/moira/docs/architecture/ASPECT_PATTERN_QUALITATIVE_SCORING_V1_DRAFT.md), [`moira/pattern_coherence.py`](file:///c:/dev/moira/moira/pattern_coherence.py)
- **Scope & Delivery**:
  - Implemented policy `moira.pattern_coherence.qualitative.v1-draft` in [`moira/pattern_coherence.py`](file:///c:/dev/moira/moira/pattern_coherence.py), re-exported through [`moira/patterns.py`](file:///c:/dev/moira/moira/patterns.py) with `AspectPattern.evaluate_coherence()`.
  - Replaced arbitrary composite percentage scoring with two-part qualitative evaluation: **Coherence Band** (`Very strong`, `Strong`, `Moderate`, `Loose`, `Marginal`) and **Motion Qualifier** (`Motion unavailable`, `Partial motion`, `Station-sensitive`, `Exact`, `Applying`, `Separating`, `Mixed motion`).
  - Conservative weakest-link ratio aggregation $R = \max(\text{actual\_orb} / \text{reference\_orb})$ over frozen reference orbs (Opposition $8^\circ$, Square $7^\circ$, Trine $7^\circ$, Sextile $5^\circ$, Quincunx $3^\circ$).
  - Full template validation for all six canonical configurations: *T-Square*, *Grand Trine*, *Grand Cross*, *Yod*, *Mystic Rectangle*, and *Kite*. Non-admitted patterns cleanly return `NOT_ASSESSED`.
  - Validated by 52 automated tests in [`tests/unit/test_pattern_coherence_qualitative.py`](file:///c:/dev/moira/tests/unit/test_pattern_coherence_qualitative.py) satisfying all 8 acceptance requirements (IEEE-754 adjacent boundary cuts, motion qualifier precedence, speed reversal independence, degenerate/adversarial handling, and Section 7 synthetic configurations).
  - Exposed via dedicated REST endpoint `POST /v1/patterns/coherence` (`PatternCoherenceSearchResponse`) and enriched discovery endpoint `POST /v1/patterns/find` embedding `coherence: PatternCoherenceResponse | None` on `AspectPatternResponse`.
  - Comprehensive server contract suite in [`tests/server/test_server_pattern_coherence_routes.py`](file:///c:/dev/moira/tests/server/test_server_pattern_coherence_routes.py) (6/6 tests passing) verifying OpenAPI schema registration, engine-backed evaluation, filtering/dominance forwarding, and mock isolation.

### Frontier 3: Primary Directions Native Under-Pole Arcs
- **Status**: **COMPLETED**
- **Anchors**: `moira/primary_directions/`, [`src/native/include/primary_directions.hpp`](file:///c:/dev/moira/src/native/include/primary_directions.hpp), [`src/native/bindings/moira_native.cpp`](file:///c:/dev/moira/src/native/bindings/moira_native.cpp), [`moira/primary_directions/geometry.py`](file:///c:/dev/moira/moira/primary_directions/geometry.py)
- **Scope & Delivery**:
  - Implemented high-performance native C++ header [`src/native/include/primary_directions.hpp`](file:///c:/dev/moira/src/native/include/primary_directions.hpp) containing `NativeSpeculumPoint`, branch-independent continuous zenith distance invariant (`campanus_regio_sin_zenith_distance`), pole height solvers (`regiomontanus_pole_height`, `topocentric_pole_height`), oblique coordinate projector (`under_pole_w`), directed arc calculators (`regiomontanus_under_pole_arc`, `topocentric_under_pole_arc`), role-exchanged direct/converse arc pair solver (`compute_under_pole_pair_arcs`), and batched OpenMP matrix generator (`compute_under_pole_arcs_matrix`).
  - Formulated continuous vector/plane invariant $\sin ZD = |\text{transverse}| / \text{norm}$ where $\text{transverse} = \cos \delta \sin HA$ and $\text{meridional} = \cos \phi \cos \delta \cos HA + \sin \phi \sin \delta$, eliminating the classical meridian-quadrature ($MD = 90^\circ$) singularity without trigonometric discontinuities.
  - Formalized Jean-Baptiste Morin's True Converse Role-Exchange Law (*Astrologia Gallica* Book 22, Chapter 7 & Appendix 5): $\Delta_{\text{converse}} \neq -\Delta_{\text{direct}}$, proving strict reciprocity $\text{converse}(A \to B) = \text{direct}(B \to A)$ while retaining asymmetry against circular reflection.
  - Integrated seamless Python fallback and native dispatch in [`moira/primary_directions/geometry.py`](file:///c:/dev/moira/moira/primary_directions/geometry.py), achieving exact bit-level / sub-microarcsecond numerical parity ($|\Delta| < 10^{-12 \circ}$) with the pure-Python reference.
  - Achieved **9.3x speedup** on batched $12 \times 12$ chart-wide direction matrices (down from 0.503 ms to **0.054 ms** per 144 pairs) with OpenMP multi-threading and GIL-scoped release.
  - Verified across 284 passing unit tests including the dedicated parity suite in [`tests/unit/test_native_primary_directions_parity.py`](file:///c:/dev/moira/tests/unit/test_native_primary_directions_parity.py).

### Frontier 4: High-Latitude House Solvers Integration & Promotion
- **Status**: **COMPLETED**
- **Anchors**: [`moira/houses.py`](file:///c:/dev/moira/moira/houses.py), `moira/experimental_*.py`, [`src/native/include/houses.hpp`](file:///c:/dev/moira/src/native/include/houses.hpp), [`moira_server/routers/chart.py`](file:///c:/dev/moira/moira_server/routers/chart.py), [`moira_server/models/chart.py`](file:///c:/dev/moira/moira_server/models/chart.py)
- **Scope & Delivery**:
  - Re-founded pole projection onto the exact unitary cleared-denominator plane normal $\mathbf{n} = (-\sin \text{RA} \cos \phi_h, \cos \text{RA} \cos \phi_h, -\sin \phi_h)$, proving $\|\mathbf{n}\| = 1$ unconditionally for all pole heights $\phi_h \in [0^\circ, 90^\circ]$ and eliminating $\tan(\phi_h)$ division-by-zero singularities across both Python and native C++ (`houses.hpp`).
  - Promoted Campanus, Regiomontanus, and Topocentric from quarantined experimental isolation into the primary **Integrated Branch Doctrine** alongside Placidus and Alcabitius.
  - Re-classified `HouseSystem.CAMPANUS`, `HouseSystem.REGIOMONTANUS`, and `HouseSystem.TOPOCENTRIC` as `polar_capable=True`. `_POLAR_SYSTEMS` reduced to `{HouseSystem.KOCH}` due to intrinsic diurnal semi-arc circumpolar collapse ($|\tan \phi \tan \delta_{\text{MC}}| > 1$).
  - Under `HousePolicy.default()`, charts at polar latitudes ($|\phi| \ge 90^\circ - \varepsilon$) with admissible ARMC now automatically deliver real Campanus, Regiomontanus, or Topocentric cusps (`effective_system=system`, `fallback=False`), falling back cleanly to Porphyry with full provenance only when geometry degenerates or cusps fold.
  - Added REST endpoint `POST /v1/houses/polar-admissibility` returning contiguous valid ARMC windows, valid fractions, sample counts, practical windows, and stability metrics.
  - Verified across 141 tests in the core and server suites, plus 282 port compliance tests.

---

## 4. Category C — Formally Deferred Doctrinal & Astronomical Systems

These systems represent intentional boundaries where Moira refuses to invent speculative math without primary authority or oracle validation.

### 1. Cusp Dynamics & Instantaneous Speeds (`HouseCuspSpeed`, `HouseDynamics`)
- **Location**: [`moira/houses.py:5422–5560`](file:///c:/dev/moira/moira/houses.py#L5422-L5560)
- **Status**: Phase 3 Design Vessel (Deferred).
- **Doctrinal Challenge**: Cusp speed is observer-location dependent and requires calculating the instantaneous derivative of tropical ecliptic longitude with respect to Universal Time ($\text{deg}/\text{day}$) across polar and non-polar regimes without conflating ARMC-rate with MC-rate.
- **Gate Condition**: Requires validation against an independent oracle returning cusp speeds in extended output for $\ge 5$ house systems, $\ge 3$ latitudes, $\ge 3$ historical epochs, within a tolerance of $0.001^\circ/\text{day}$.

### 2. Aktinobolia Ray Geometry (`HellenisticRayTruth`)
- **Location**: [`moira/hellenistic_relations.py:146–164`](file:///c:/dev/moira/moira/hellenistic_relations.py#L146-L164)
- **Status**: Doctrine Not Admitted (Placeholder).
- **Detail**: In accordance with the Anti-Leakage Workflow, Moira does not invent speculative ray geometry. Returns `HellenisticAspectEvaluationStatus.NOT_EVALUABLE` with reason `doctrine_not_admitted` until primary source-backed ray optics are formalized.

### 3. Jaimini Chara Dasha: Second-Cycle Mahadashas
- **Location**: [`moira/jaimini_extended.py:529–534, 661`](file:///c:/dev/moira/moira/jaimini_extended.py#L529-L534)
- **Status**: Deferred.
- **Detail**: First-cycle Chara Dasha (12 mahadashas from lagna sign) is fully validated. K.N. Rao's second-cycle rule is explicitly recorded as unverified and deferred rather than guessed.

### 4. Sayanadi Avasthas
- **Location**: [`moira/avasthas.py:33, 794`](file:///c:/dev/moira/moira/avasthas.py#L33)
- **Status**: Deferred.
- **Detail**: BPHS 45.30–155 Sayanadi states (12 conditions from Sayana to Upaveshana) require birth ghatis and sub-division time reckoning distinct from standard planetary coordinate vectors. Intentionally deferred until a unified civil-birth time stratum is linked.

### 5. Solar Eclipse Atlas-Grade Terminator Closure
- **Location**: [`moira/eclipse.py:261–297`](file:///c:/dev/moira/moira/eclipse.py#L261-L297) (`SolarEclipsePath`)
- **Status**: Future Work.
- **Detail**: The central line, path width, duration, and WGS-84 tangency endpoints are rigorously validated against NASA GSFC Besselian elements. Full continuous terminator-limit closure envelopes are reserved for atlas-grade cartographic expansion.

---

## 5. Maintenance Protocol

1. **Pruning & Verification**: When an item in this register is implemented, remove its entry here and record the completion in `CHANGELOG.md` under `## [Unreleased]`.
2. **Zero False Assertions**: Stubs must continue raising explicit errors (`NotImplementedError` or typed unavailable receipts) rather than returning misleading zero or placeholder values.
