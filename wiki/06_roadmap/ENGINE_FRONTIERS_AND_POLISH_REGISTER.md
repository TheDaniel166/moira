# Moira Engine: Frontiers, Polish & Deferred Work Register (2026)

**Governing Authority**: Moira Canonical Instruction (`AGENTS.md`)

**Original Audit Date**: September 21, 2026

**Last Reconciled**: September 29, 2026

**Baseline**: current `main`; this is not a release-version manifest

---

## 1. Overview & Purpose

This register preserves the 2026-09-21 completion receipts and records the
remaining active validation and doctrinal frontiers identified in Moira's core
engine (`moira/`), native substrate (`src/native/`), and server transport layer
(`moira_server/`). Completed entries below are historical receipts, not active
backlog.

In alignment with Moira's **Law of Policy Explicitness** and **Documentation Law**, every item is recorded with its precise file anchor, architectural rationale, and verified gate conditions.

---

## 2. Category A — Immediate Polish & Documentation Debt

These items represent discrepancies between live executable code and comments or documentation, or small harness-level stubs.

| Target | Location | Classification | Current State & Resolution |
| :--- | :--- | :--- | :--- |
| **`moira.sky` Subsystem Headers** | [`moira/sky/__init__.py`](../../moira/sky/__init__.py#L31-L56) | Stale Docstrings | **REMEDIATED (2026-09-21)**. Removed stale `[stub]` markers from all 6 fully-implemented astronomy submodules (`bodies`, `observation`, `galactic`, `events`, `eclipse`, `occultation`) and synchronized the design contract. |
| **Export Policy Subsystem** | `moira/_export_governance/` | Dead Subsystem | **REMEDIATED (2026-09-21)**. Excised unused `moira/_export_governance` package (11 modules), associated `tests/export_governance` (8 test suites / 162 tests), old audit reports (`reports/governance/`), and one-shot archived audit scripts. Port compliance verified across 282 engine files. |
| **Stars Bulk Serializer** | [`moira_server/serializers/stars.py`](../../moira_server/serializers/stars.py) | Dead Transport Helper | **REMEDIATED (2026-09-28)**. Removed the unused placeholder serializer. The live bulk-stars service constructs `StarsBulkResponse` directly from the validated request datetime. |
| **House Dynamics and Polar-House Prose** | [`moira/houses.py`](../../moira/houses.py), [HOUSES_BACKEND_STANDARD.md](../02_standards/HOUSES_BACKEND_STANDARD.md) | Stale / overstated documentation | **REMEDIATED (2026-09-28)**. Reconciled the implemented dynamics surface, `_POLAR_SYSTEMS == {'K'}`, and internal analytical/invariant validation scope. |

---

## 3. Category B — Completed Computational Frontiers (Historical Receipts)

The following projects were active frontiers during the original survey and
are retained only as completion receipts. They are not current work items.

### Frontier 1: Planetary Reduction Pipeline (`all_planets_at` Cash-In)
- **Status**: **COMPLETED & VERIFIED** (September 2026)
- **Anchors**: [`src/native/include/planetary_evaluator.hpp`](../../src/native/include/planetary_evaluator.hpp), [`src/native/bindings/moira_native.cpp`](../../src/native/bindings/moira_native.cpp), [`moira/planets.py`](moira/planets.py).
- **Accomplishments**:
  - Implemented `NativePlanetaryEvaluator::evaluate_all_planets_apparent_with_speed`, reducing the three sequential Python-native boundary crossings for central finite-difference speed into a single GIL-released pass.
  - Cached resolved SPK Chebyshev segment evaluators (`resolved_segments_`) across invocations, eliminating memory allocation and kernel mutex traffic.
  - Accelerated 10-planet apparent ecliptic reduction from 0.400 ms down to **0.319 ms** (3,131 charts/sec), reaching **0.227 ms** (>4,400 charts/sec) in raw C++.
  - Fixed `_prefill_npe_public_vector_cache` to iterate over all `_NPE_ADMITTED_BODIES` using canonical NAIF routes, eliminating the Mercury route lookup defect.

### Frontier 2: Aspect-Pattern Qualitative Scoring (`v1-draft`)
- **Status**: **COMPLETED & VERIFIED**
- **Anchor Documents**: [`docs/architecture/ASPECT_PATTERN_QUALITATIVE_SCORING_V1_DRAFT.md`](../../docs/architecture/ASPECT_PATTERN_QUALITATIVE_SCORING_V1_DRAFT.md), [`moira/pattern_coherence.py`](moira/pattern_coherence.py)
- **Scope & Delivery**:
  - Implemented policy `moira.pattern_coherence.qualitative.v1-draft` in [`moira/pattern_coherence.py`](moira/pattern_coherence.py), re-exported through [`moira/patterns.py`](moira/patterns.py) with `AspectPattern.evaluate_coherence()`.
  - Replaced arbitrary composite percentage scoring with two-part qualitative evaluation: **Coherence Band** (`Very strong`, `Strong`, `Moderate`, `Loose`, `Marginal`) and **Motion Qualifier** (`Motion unavailable`, `Partial motion`, `Station-sensitive`, `Exact`, `Applying`, `Separating`, `Mixed motion`).
  - Conservative weakest-link ratio aggregation $R = \max(\text{actual\_orb} / \text{reference\_orb})$ over frozen reference orbs (Opposition $8^\circ$, Square $7^\circ$, Trine $7^\circ$, Sextile $5^\circ$, Quincunx $3^\circ$).
  - Full template validation for all six canonical configurations: *T-Square*, *Grand Trine*, *Grand Cross*, *Yod*, *Mystic Rectangle*, and *Kite*. Non-admitted patterns cleanly return `NOT_ASSESSED`.
  - Validated by 52 automated tests in [`tests/unit/test_pattern_coherence_qualitative.py`](tests/unit/test_pattern_coherence_qualitative.py) satisfying all 8 acceptance requirements (IEEE-754 adjacent boundary cuts, motion qualifier precedence, speed reversal independence, degenerate/adversarial handling, and Section 7 synthetic configurations).
  - Exposed via dedicated REST endpoint `POST /v1/patterns/coherence` (`PatternCoherenceSearchResponse`) and enriched discovery endpoint `POST /v1/patterns/find` embedding `coherence: PatternCoherenceResponse | None` on `AspectPatternResponse`.
  - Comprehensive server contract suite in [`tests/server/test_server_pattern_coherence_routes.py`](tests/server/test_server_pattern_coherence_routes.py) (6/6 tests passing) verifying OpenAPI schema registration, engine-backed evaluation, filtering/dominance forwarding, and mock isolation.

### Frontier 3: Primary Directions Native Under-Pole Arcs
- **Status**: **COMPLETED**
- **Anchors**: `moira/primary_directions/`, [`src/native/include/primary_directions.hpp`](../../src/native/include/primary_directions.hpp), [`src/native/bindings/moira_native.cpp`](../../src/native/bindings/moira_native.cpp), [`moira/primary_directions/geometry.py`](moira/primary_directions/geometry.py)
- **Scope & Delivery**:
  - Implemented high-performance native C++ header [`src/native/include/primary_directions.hpp`](../../src/native/include/primary_directions.hpp) containing `NativeSpeculumPoint`, branch-independent continuous zenith distance invariant (`campanus_regio_sin_zenith_distance`), pole height solvers (`regiomontanus_pole_height`, `topocentric_pole_height`), oblique coordinate projector (`under_pole_w`), directed arc calculators (`regiomontanus_under_pole_arc`, `topocentric_under_pole_arc`), role-exchanged direct/converse arc pair solver (`compute_under_pole_pair_arcs`), and batched OpenMP matrix generator (`compute_under_pole_arcs_matrix`).
  - Formulated continuous vector/plane invariant $\sin ZD = |\text{transverse}| / \text{norm}$ where $\text{transverse} = \cos \delta \sin HA$ and $\text{meridional} = \cos \phi \cos \delta \cos HA + \sin \phi \sin \delta$, eliminating the classical meridian-quadrature ($MD = 90^\circ$) singularity without trigonometric discontinuities.
  - Formalized Jean-Baptiste Morin's True Converse Role-Exchange Law (*Astrologia Gallica* Book 22, Chapter 7 & Appendix 5): $\Delta_{\text{converse}} \neq -\Delta_{\text{direct}}$, proving strict reciprocity $\text{converse}(A \to B) = \text{direct}(B \to A)$ while retaining asymmetry against circular reflection.
  - Integrated seamless Python fallback and native dispatch in [`moira/primary_directions/geometry.py`](moira/primary_directions/geometry.py), achieving exact bit-level / sub-microarcsecond numerical parity ($|\Delta| < 10^{-12 \circ}$) with the pure-Python reference.
  - Achieved **9.3x speedup** on batched $12 \times 12$ chart-wide direction matrices (down from 0.503 ms to **0.054 ms** per 144 pairs) with OpenMP multi-threading and GIL-scoped release.
  - Verified across 284 passing unit tests including the dedicated parity suite in [`tests/unit/test_native_primary_directions_parity.py`](tests/unit/test_native_primary_directions_parity.py).

### Frontier 4: High-Latitude House Solvers Integration & Promotion
- **Status**: **COMPLETED**
- **Anchors**: [`moira/houses.py`](moira/houses.py), `moira/experimental_*.py`, [`src/native/include/houses.hpp`](../../src/native/include/houses.hpp), [`moira_server/routers/chart.py`](../../moira_server/routers/chart.py), [`moira_server/models/chart.py`](../../moira_server/models/chart.py)
- **Scope & Delivery**:
  - Re-founded pole projection onto the exact unitary cleared-denominator plane normal $\mathbf{n} = (-\sin \text{RA} \cos \phi_h, \cos \text{RA} \cos \phi_h, -\sin \phi_h)$, proving $\|\mathbf{n}\| = 1$ unconditionally for all pole heights $\phi_h \in [0^\circ, 90^\circ]$ and eliminating $\tan(\phi_h)$ division-by-zero singularities across both Python and native C++ (`houses.hpp`).
  - Promoted Campanus, Regiomontanus, and Topocentric from quarantined experimental isolation into the primary **Integrated Branch Doctrine** alongside Placidus and Alcabitius.
  - Re-classified `HouseSystem.CAMPANUS`, `HouseSystem.REGIOMONTANUS`, and `HouseSystem.TOPOCENTRIC` as `polar_capable=True`. `_POLAR_SYSTEMS` reduced to `{HouseSystem.KOCH}` due to intrinsic diurnal semi-arc circumpolar collapse ($|\tan \phi \tan \delta_{\text{MC}}| > 1$).
  - Under `HousePolicy.default()`, charts at polar latitudes ($|\phi| \ge 90^\circ - \varepsilon$) with admissible ARMC now automatically deliver real Campanus, Regiomontanus, or Topocentric cusps (`effective_system=system`, `fallback=False`), falling back cleanly to Porphyry with full provenance only when geometry degenerates or cusps fold.
  - Added REST endpoint `POST /v1/houses/polar-admissibility` returning contiguous valid ARMC windows, valid fractions, sample counts, practical windows, and stability metrics.
  - Verified across 141 tests in the core and server suites, plus 282 port compliance tests.

### Frontier 5: Primary Directions Bound Distributions, Dynamic Ephemeris Inversion & Chronological Life Timeline
- **Status**: **COMPLETED & VERIFIED** (September 2026)
- **Anchors**: [`moira/primary_directions/timeline.py`](moira/primary_directions/timeline.py), [`moira/primary_directions/distributor.py`](moira/primary_directions/distributor.py), [`moira/primary_directions/keys.py`](moira/primary_directions/keys.py), [`moira_server/routers/primary_directions.py`](../../moira_server/routers/primary_directions.py), [`moira_server/models/primary_directions.py`](../../moira_server/models/primary_directions.py)
- **Scope & Delivery**:
  - **Part 1 (Terms/Bounds Boundaries & Distributor Engine)**: Integrated traditional distribution through the terms/bounds (*distributor* / *particeps* and *participator* / *socius*). Built `resolve_distributor_chronology` and `resolve_primary_direction_bound_targets` mapping direct and converse arc traversals through Egyptian and Ptolemaic bounds without missing segments or overlapping boundaries.
  - **Part 2 (Dynamic Ephemeris Inversion)**: Formulated dynamic True Solar Arc inversion in Right Ascension ($\text{RA}_{\odot}(t_0 + Y) - \text{RA}_{\odot}(t_0) = \Delta$) and Longitude ($\lambda_{\odot}(t_0 + Y) - \lambda_{\odot}(t_0) = \Delta$). Implemented monotonic bracket expansion and high-precision bisection (`tol_days=1e-6`) in `invert_solar_arc_ra` and `invert_solar_arc_lon`, resolving exact solar non-uniformity across perihelion/aphelion velocities within $<30$ ephemeris queries. Added keys `PrimaryDirectionKey.SOLAR_RA_DYNAMIC` and `PrimaryDirectionKey.SOLAR_LON_DYNAMIC`.
  - **Part 3 (Chronological Life Timeline Engine & REST Surface)**: Implemented `compute_primary_directions_timeline` and facade method `primary_directions_timeline`, unifying arc search, bound boundary crossings, active distributor determination, and participator aspectual tagging into a chronological life sequence. Added REST endpoint `POST /v1/primary-directions/timeline` with strict Pydantic v2 schemas (`PrimaryDirectionsTimelineRequest` and `PrimaryDirectionsTimelineResponse`).
  - Validated across dedicated unit test suites (`test_primary_directions_bounds.py`, `test_primary_directions_dynamic_keys.py`, `test_primary_directions_timeline.py`) and server test suite (`test_server_primary_directions_timeline_routes.py`), achieving 100% pass across all 280+ primary directions tests.

### Frontier 6: Primary Directions Neo-Converse Motion Doctrine, Placidian Mundane Aspects & Native Placidian Mundane Solver
- **Status**: **COMPLETED & VERIFIED** (September 2026)
- **Anchors**: [`moira/primary_directions/converse.py`](moira/primary_directions/converse.py), [`moira/primary_directions/relations.py`](moira/primary_directions/relations.py), [`moira/primary_directions/targets.py`](moira/primary_directions/targets.py), [`moira/primary_directions/placidus.py`](moira/primary_directions/placidus.py), [`moira/primary_directions/__init__.py`](moira/primary_directions/__init__.py), [`moira/primary_directions/geometry.py`](moira/primary_directions/geometry.py), [`src/native/include/primary_directions.hpp`](../../src/native/include/primary_directions.hpp), [`src/native/bindings/moira_native.cpp`](../../src/native/bindings/moira_native.cpp)
- **Scope & Delivery**:
  - **Part 1 (`neo_converse` Motion Doctrine)**: Implemented counter-diurnal West-to-East primary motion ($\Delta_{\text{neo}} = (360^\circ - \Delta_{\text{dir}}) \pmod{360^\circ}$) holding the Significator stationary while directing promissors against the diurnal rotation. Rigorously differentiated from Morin's Traditional Converse role-exchange doctrine ($\Delta_{\text{conv}}(S \to P) = \Delta_{\text{dir}}(P \to S)$) on asymmetric oblique semi-arc systems (Placidus, Campanus, Topocentric), while preserving exact circle-complement identity with traditional converse on symmetric equatorial/meridian systems. Added `PrimaryDirectionConverseDoctrine.NEO_CONVERSE` and preset option `converse_doctrine="neo_converse"`.
  - **Part 2 (Placidian Mundane Aspects *In Mundo*)**: Generalized Placidian proportional semi-arc directions from conjunctions/oppositions to all classical mundane aspects: semi-sextile ($\pm 1/3$), sextile ($\pm 2/3$), square ($\pm 1.0$), trine ($\pm 4/3$), quincunx ($\pm 5/3$), and opposition ($2.0$). Defined cyclic temporal fraction trisection $f \in [-2.0, 2.0]$ with `wrap_mundane_fraction()`, allowing promissor mundane aspect points to inherit the parent promissor's diurnal/nocturnal semi-arc and be directed directly, converse, or neo-converse to significators across all quadrants. Added `PrimaryDirectionsPreset.PLACIDUS_MUNDANE_ASPECT` and `resolve_primary_direction_mundane_aspect_targets()`.
  - **Part 3 (Native Placidian Mundane Solver `_moira_native`)**: Implemented C++ functions `placidian_required_ha`, `placidian_mundane_arc`, `compute_placidian_pair_arcs`, and batched OpenMP matrix generator `compute_placidian_arcs_matrix` in `primary_directions.hpp` and exposed via pybind11 in `moira_native.cpp`. Dispatched transparently in `moira/primary_directions/geometry.py` with zero-drift numerical parity ($|\Delta| < 10^{-12 \circ}$) against Python reference math.
  - Validated across dedicated unit test suites (`test_primary_directions_neo_converse.py`, `test_primary_directions_mundane_aspects.py`, `test_native_primary_directions_parity.py`) and server contract suite, achieving 100% pass across all 395 primary directions tests.

### Frontier 7: Primary Directions Frontier Triad (Placidian Mundane Parallels, Ptolemaic Mundane Aspects & Zodiacal Midpoints)
- **Status**: **COMPLETED & VERIFIED** (September 2026)
- **Anchors**: [`moira/primary_directions/relations.py`](moira/primary_directions/relations.py), [`moira/primary_directions/targets.py`](moira/primary_directions/targets.py), [`moira/primary_directions/placidus.py`](moira/primary_directions/placidus.py), [`moira/primary_directions/__init__.py`](moira/primary_directions/__init__.py), [`moira_server/models/primary_directions.py`](../../moira_server/models/primary_directions.py), [`moira_server/services/primary_directions.py`](../../moira_server/services/primary_directions.py)
- **Scope & Delivery**:
  - **Part 1 (Placidian Mundane Parallels & Contra-Parallels *In Mundo*)**: Implemented true mundane parallel reflections across the Meridian ($f_{\text{par}} = -f_S$) and contra-parallel reflections across the Horizon ($f_{\text{contra}} = \text{copysign}(2.0 - |f_S|, f_S)$) via `compute_placidian_mundane_parallel_arc`. Direct and converse arcs evaluated with native equatorial acceleration. Added `PrimaryDirectionsPreset.PLACIDIAN_MUNDANE_PARALLEL` and target generators.
  - **Part 2 (Ptolemaic Mundane Aspects *In Mundo*)**: Added proportional semi-arc trisections under Ptolemy's mundane projection model (`PrimaryDirectionMethod.PTOLEMY_SEMI_ARC`), expanding the existing Placidian semi-arc trisection to Ptolemaic semi-arcs with exact quadrant temporal hour fractions. Added `PrimaryDirectionsPreset.PTOLEMY_MUNDANE_ASPECT`.
  - **Part 3 (Zodiacal Midpoint Targets in Primary Directions)**: Implemented shortest-arc circular midpoint targets ($A/B$) with rigorous $0^\circ$ Aries boundary wrapping ($\Delta \lambda = (\lambda_B - \lambda_A + 540^\circ) \pmod{360^\circ} - 180^\circ$). Full multi-method direction across all 8 projection systems, direct/converse/neo-converse motion doctrines, dynamic true solar arc time keys, and life timeline integration.
  - **Part 4 (Server Transport & Verification)**: Added Pydantic v2 request/response schemas for mundane parallels and midpoints, registered in advanced search policy vessels.
  - Validated across dedicated test suites (`test_primary_directions_mundane_parallels.py`, `test_primary_directions_ptolemy_mundane_aspects.py`, `test_primary_directions_midpoints.py`) with 412/412 tests passing (100% green).

### Frontier 8: House Dynamics & Instantaneous Cusp Speeds
- **Status**: **COMPLETED & VERIFIED** (September 2026)
- **Anchors**: [`moira/houses.py`](moira/houses.py), [`moira/_facade_core.py`](moira/_facade_core.py), [`moira_server/routers/chart.py`](../../moira_server/routers/chart.py), [`moira_server/models/chart.py`](../../moira_server/models/chart.py)
- **Scope & Delivery**:
  - **Part 1 (Analytical Ground Truth Derivations)**: Derived exact closed forms from first principles for fundamental angle velocities under Earth's diurnal rotation:
    - Midheaven: $\dot{\lambda}_{\text{MC}} = \omega_{\text{sidereal}} \frac{\cos \varepsilon}{1 - \sin^2 \varepsilon \sin^2 \lambda_{\text{MC}}}$ via `analytical_mc_speed()`.
    - Ascendant: $\dot{\lambda}_{\text{ASC}} = \omega_{\text{sidereal}} \frac{\cos \varepsilon + \tan \phi \sin \varepsilon \sin \theta}{\cos^2 \theta + (\sin \theta \cos \varepsilon + \tan \phi \sin \varepsilon)^2}$ via `analytical_asc_speed()`.
    - Vertex: $\dot{\lambda}_{\text{VTX}} = \omega_{\text{sidereal}} \frac{\cos \varepsilon - \cot \phi \sin \varepsilon \sin \theta}{\cos^2 \theta + (\sin \theta \cos \varepsilon - \cot \phi \sin \varepsilon)^2}$ via `analytical_vertex_speed()`.
  - **Part 2 (Engine Core & Facade Integration)**: Re-exported analytical functions and `house_dynamics_from_armc` at package root; integrated `Moira.house_dynamics(dt, latitude, longitude, system=...)` into `CoreFacadeMixin` for seamless high-level execution.
  - **Part 3 (Server Transport Layer)**: Added Pydantic v2 schemas (`CuspSpeedResponse`, `HouseDynamicsRequest`, `HouseDynamicsResponse`) and registered endpoint `POST /v1/houses/dynamics` with timezone validation and custom step/policy forwarding.
  - **Part 4 (Analytical and Invariant Validation)**: Validated across 9 house systems (Placidus, Koch, Regiomontanus, Campanus, Topocentric, Alcabitius, Porphyry, Equal, Whole Sign), 4 latitude regimes (London $+51.5^\circ$, Equator $0.0^\circ$, Sydney $-33.86^\circ$, Reykjavik $+64.1^\circ$), and 3 epochs (J2000, J1900, Modern 2026). Proved sub-millidegree/day internal analytical agreement ($< 0.0001^\circ/\text{day}$), equatorial horizon symmetry ($\dot{\lambda}_{\text{ASC}}(\theta) = \dot{\lambda}_{\text{MC}}(\theta + 90^\circ)$), and $O(h^4)$ Richardson convergence. This is internal mathematical validation, not an external house-speed authority comparison.
  - Validated by 90 automated tests in [`tests/unit/test_house_dynamics_oracle.py`](tests/unit/test_house_dynamics_oracle.py), 28 tests in [`tests/unit/test_house_dynamics.py`](tests/unit/test_house_dynamics.py), and 4 server contract tests in [`tests/server/test_server_house_dynamics_routes.py`](tests/server/test_server_house_dynamics_routes.py).

### Frontier 9: Current Small-Body Orbital Catalog Admission
- **Status**: **COMPLETED & VERIFIED** (September 28, 2026)
- **Anchors**: [`tests/artifacts/oracle/small_body_orbital_catalog_admission_2026-09-28.json`](../../tests/artifacts/oracle/small_body_orbital_catalog_admission_2026-09-28.json), [`tests/integration/test_orbital_elements_full_catalog.py`](../../tests/integration/test_orbital_elements_full_catalog.py), [`tests/integration/test_geometric_nodes_full_catalog.py`](../../tests/integration/test_geometric_nodes_full_catalog.py)
- **Scope & Delivery**:
  - Rebound active engine guidance and exhaustive gates to `moira-asteroids@2026.09.18.1` (11,223 bodies / 449 shards) while retaining `moira-comets@2026.07.28.1` (497 bodies / 20 shards).
  - Refreshed the exact-JDTDB JPL Horizons catalog holdout without rewriting its historical predecessor; only Encke's upstream solution changed, from `JPL#K273/14` to `JPL#K273/17`.
  - Bound the six-case authority corpus, exact release manifest hashes, and pre-existing live osculating-element product gates in a path-free governed admission. Six direct element and six geometric-node comparisons run and pass with no authority skip; the isolated live-primary drift audit passes 17/17.
  - Exhaustive element and geometric-node sweeps pass all 11,720 sovereign bodies with coverage, finiteness, canonical identity, exact core mapping, and manifest/shard receipt assertions.
  - This receipt does not admit small-body apsidal-passage event timing; that remains separately visible below.

### Frontier 10: Jaimini Chara Dasha Second-Cycle Mahadashas
- **Status**: **COMPLETED & VERIFIED** (September 29, 2026)
- **Anchors**: [`moira/jaimini_extended.py`](../../moira/jaimini_extended.py), [`tests/unit/test_jaimini_extended.py`](../../tests/unit/test_jaimini_extended.py)
- **Scope & Delivery**:
  - Researched K.N. Rao's specific second-cycle rule using his book *Predicting Through Jaimini's Chara Dasa* (pages 13-14).
  - Verified the second cycle is a direct repetition of the first cycle's sign sequence and dasha span (years) without length deduction.
  - Admitted the `cycles` parameter in `chara_dasha` allowing generation of exact multi-cycle continuous sequences.
  - Added deterministic tests asserting identical sign, lord, and exact span repetition between cycles.

### Frontier 11: Synastry Architectural Debt (Category E)
- **Status**: **COMPLETED & VERIFIED** (September 29, 2026)
- **Anchors**: [moira/synastry.py](../../moira/synastry.py), [moira_server/models/relationship.py](../../moira_server/models/relationship.py), [moira_server/services/relationship.py](../../moira_server/services/relationship.py), [moira_server/services/_shared.py](../../moira_server/services/_shared.py)
- **Scope & Delivery**:
  - Excised all 5 internal bookkeeping routes (e.g. synastry_contact_relations, synastry_network) and arbitrary ranking mechanics from the server transport layer.
  - Formally deprecated the unstable midpoint method for composite charts, establishing 
eference_place as the required, geometrically rigorous default.
  - Stripped out meaningless applying/separating derivations from synastry inter-aspect logic.
  - Enforced strict point identity isolation by explicitly blocking Mean Node and Liliths from polluting synastry evaluation grids.
  - Implemented a 	ime_unknown doctrinal flag down the entire pipeline, actively aborting Ascendant, Midheaven, and House evaluation rather than allowing a noon-guess to pass. Moon geometries are silently withheld from chart instantiation when requested on unknown time.

---
### Frontier 13: Heliacal Corpus Breadth
- **Status**: **COMPLETED & VERIFIED**
- **Anchors**: [	ests/oracle/test_heliacal_rising_oracle.py](../../tests/oracle/test_heliacal_rising_oracle.py), [	ests/unit/test_stars_heliacal.py](../../tests/unit/test_stars_heliacal.py)
- **Scope & Delivery**:
  - Expanded the oracle matrix beyond Mercury, Venus, Mars, Jupiter, and Saturn to incorporate externally admitted non-Sirius stellar event cases.
  - Implemented and validated moonlight-enabled live-ephemeris event handling.

### Frontier 12: Arabic Mansion Catalogue Provenance
- **Status**: **COMPLETED & VERIFIED** (September 29, 2026)
- **Anchors**: [moira/manazil.py](../../moira/manazil.py), [	ests/unit/test_manazil.py](../../tests/unit/test_manazil.py)
- **Scope & Delivery**:
  - Source-locked the mansion traditions by fully separating AL_BIRUNI_MANSIONS (unequal, star-based, without Agrippa paraphrases) from AGRIPPA_MANSIONS (equal tropical).
  - Resolved ruling star inaccuracies (e.g., Gamma Geminorum for Mansion 6) and corrected Latin transliterations (Athoray, Albucca, etc.).
  - Realigned the Picatrix good/bad natures according to *Picatrix* I.4.
  - Eliminated the singular MANSIONS array that conflated disparate traditions into a single computational grid.

### Frontier 14: Solar Eclipse Atlas-Grade Terminator Closure
- **Status**: **COMPLETED & VERIFIED** (September 29, 2026)
- **Anchors**: [`moira/eclipse.py`](moira/eclipse.py) (`SolarEclipsePath`)
- **Scope & Delivery**:
  - Implemented full continuous terminator-limit closure envelopes (Northern and Southern umbral limits).
  - Extended `SolarEclipsePath` to return `northern_limit_lats`, `northern_limit_lons`, `southern_limit_lats`, and `southern_limit_lons`.
  - Added internal `_umbral_envelope_points` and helpers for rigorous intersection solving along the path.

### Frontier 15: Named D60 Shashtiamsha Lords
- **Status**: **COMPLETED & VERIFIED** (September 29, 2026)
- **Anchors**: [`moira/varga.py`](../../moira/varga.py), [`tests/unit/test_d60_deities.py`](../../tests/unit/test_d60_deities.py)
- **Scope & Delivery**:
  - Established BPHS Chapter 6 as the primary doctrinal authority for the 60 Shashtiamsha deity names.
  - Implemented exact mapping logic: sequential progression for odd-sign placements, and precise reversed assignment (59 down to 0) for even-sign placements.
  - Enriched `VargaPoint` with the `deity` attribute exposing the traditionally designated lord.


## 4. Category C — Active Validation Frontiers

### 1. Small-body apsidal-passage accuracy

- **Status**: Exhaustive asteroid repair scope and candidate comet policy
  validated; release rebuilds and admission remain active.
- **Detail**: The element and geometric-node catalog admission is complete.
  Six asteroid/comet apsidal-passage timing comparisons still lack a reviewed
  release-bound acceptance decision and therefore remain `NOT RUN`. Current
  gate language lives in
  [VALIDATION_ASTRONOMY.md](../03_validation/VALIDATION_ASTRONOMY.md).
  The September 28 authority probe traced the large Halley/Encke residuals to
  the comet catalog's uniform 30-day Type-13 sampling, not the event solver.
  The builder now aligns its base with the asteroid catalog's 10-day/7-node
  policy and uses NAIF Type-13's admitted unequal-time capability for daily
  nodes around both radial extrema, fetched in Horizons requests bounded to 32
  Julian years. A two-comet end-to-end candidate passes
  all three frozen events under the unchanged gates. No new immutable
  497-comet release has yet been built or admitted.
  The companion asteroid audit now partitions every one of the 11,223 admitted
  identities. Same-span 10-day/5-day Horizons comparisons at every detected
  radial extremum identify exactly 59 failing bodies in 40 release shards;
  all shared source nodes agree exactly. A worst-case elliptic sweep gives the
  remaining 11,097 bodies an 863.97x margin inside the distance gate. This
  closes discovery and sizing, not release admission: those 40 shards still
  require a new immutable build and release-bound rerun.

---

## 5. Category D — Formally Deferred Doctrinal & Astronomical Systems

These systems represent intentional boundaries where Moira refuses to invent speculative math without primary authority or oracle validation.

### 1. Aktinobolia Ray Geometry (`HellenisticRayTruth`)
- **Location**: [`moira/hellenistic_relations.py:146–164`](moira/hellenistic_relations.py#L146-L164)
- **Status**: Formalized and Admitted.
- **Detail**: In accordance with the Anti-Leakage Workflow, Moira formalized the Ray doctrine using pure kinematics. `HellenisticRayTruth` now computes the physical focal point and evaluates applying/separating states through precise relative velocity inheritance (inclusive of retrograde sweeps). Supported orb doctrines: `strict_3` and `moiety`.

### 2. Sayanadi Avasthas
- **Location**: [`moira/avasthas.py:33, 794`](moira/avasthas.py#L33)
- **Status**: Deferred.
- **Detail**: BPHS 45.30–155 Sayanadi states (12 conditions from Sayana to Upaveshana) require birth ghatis and sub-division time reckoning distinct from standard planetary coordinate vectors. Intentionally deferred until a unified civil-birth time stratum is linked.


### 4. Pluto, Asteroid, and Comet Photometry
- **Location**: [`moira/phase.py`](../../moira/phase.py)
- **Status**: Unsupported Model.
- **Detail**: Moira does not invent modern apparent-magnitude models for Pluto, nor does it attempt to model phase curves (H, G parameters) for asteroids or coma activity for comets.



### Parked: Further Sothic Historical Confirmation

The bounded engine and REST surface may remain in place. Additional historical
epoch claims, schematic-projection expansion, or release work stay parked
until explicitly reopened.

---

## 7. Maintenance Protocol

1. **Pruning & Verification**: When an item in this register is implemented,
   move it out of active-frontier language and record material completion in
   `CHANGELOG.md` and the relevant validation or release receipt.
2. **Zero False Assertions**: Stubs must continue raising explicit errors (`NotImplementedError` or typed unavailable receipts) rather than returning misleading zero or placeholder values.
