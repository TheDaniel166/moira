# Moira Native Migration Tracker

**Status**: Active
**Purpose**: Track the staged migration of Moira's computational engine from Python manuscript to validated C++ forge without violating the dual-substrate contract.
**Companion Doctrine**: [MOIRA_NATIVE_BACKEND_ARCHITECTURE.md](./MOIRA_NATIVE_BACKEND_ARCHITECTURE.md)

---

## 1. Governing Rule

Python remains the canonical reference implementation.

Native C++ is permitted only where all of the following are true:

- parity against the Python manuscript is demonstrated
- public semantics remain unchanged
- validation is explicit
- the native port produces meaningful speed or architectural value

If a native subsystem cannot prove fidelity, it is not complete regardless of build success.

---

## 2. Current Baseline

### Forge Foundation

- [x] Native extension module exists
- [x] Dispatcher layer exists
- [x] Python fallback behavior exists
- [x] Native build path exists through CMake

### Validated Native Surface

- [x] `julian_day`
- [x] `calendar_from_jd`
- [x] numerical hygiene primitives
- [x] core solver primitives under current tests
- [x] vector / matrix / coordinate primitives under current tests

### Current Contract Tests

- [x] `tests/test_forge_strength.py`
- [x] `tests/test_native_full_audit.py`
- [x] `tests/test_native_parity.py`
- [x] `tests/test_native_sidereal_phase1.py`
- [x] `tests/unit/test_spk_reader.py`
- [x] `tests/integration/test_small_body_native_reader_killer.py`

### Verified State

- [x] Native foundation tests passing in project `.venv`
- [ ] Full-engine native parity established
- [ ] Performance mandate established

---

## 3. Migration Phases

## Phase 1: Complete The Core Math Bridge

**Goal**: Expand the forge from the current primitive base into a broader validated mathematical substrate.

### Completed Slice Scope

- [x] `earth_rotation_angle`
- [x] `greenwich_mean_sidereal_time`
- [x] `apparent_sidereal_time`

### Optional Follow-On Scope

- [ ] additional reusable angle and normalization helpers as justified
- [ ] matrix and coordinate parity expansion where needed

### Phase 1 Requirements

- [x] native implementation added
- [x] bindings added
- [x] dispatcher integration added only after parity passes
- [x] random-sample parity tests added
- [x] adversarial / edge-case tests added
- [x] benchmark slice added

### Exit Condition

- [x] Phase 1 functions are parity-validated
- [x] no public API drift
- [x] measurable performance gain on bulk transform workloads

### Phase 1 Benchmark Result

Artifact:

- [x] `tests/artifacts/benchmarks/native_phase1_sidereal.json`

Measured on 2026-05-06 with `scripts/benchmark_native_phase1_sidereal.py`:

- `earth_rotation_angle`: Python median `0.015556s`, native median `0.018487s`, speedup `0.84x`
- `greenwich_mean_sidereal_time`: Python median `0.104087s`, native median `0.019611s`, speedup `5.31x`
- `apparent_sidereal_time`: Python median `0.322687s`, native median `0.033928s`, speedup `9.51x`
- overall sidereal bulk workload: Python median `0.442330s`, native median `0.072027s`, speedup `6.14x`

Interpretation:

- The sidereal Phase 1 slice shows clear aggregate acceleration.
- `earth_rotation_angle` alone does not yet benefit from the Python/native boundary and should not be cited as an independent performance win.
- `greenwich_mean_sidereal_time` and `apparent_sidereal_time` do show meaningful speed gains.

---

## Phase 2: Native Ephemeris Infrastructure

**Goal**: Move high-frequency kernel reading and interpolation into the forge.

### Architecturally Covered Scope

- [x] DAF reader
- [x] SPK segment access
- [x] interpolation kernels
- [x] repeated body-state evaluation primitives

### Phase 2 Slice 1: Native Type-2 SPK Record Evaluation

**Goal**: Accelerate repeated planetary state-vector evaluation without moving kernel provenance, segment selection, or failure semantics out of Python.

Slice boundary:

- [x] Python `SpkReader` still owns kernel opening and segment selection
- [x] native helper evaluates scalar type-2 Chebyshev records only
- [x] unsupported segment types fall back to jplephem unchanged
- [x] public semantics remain unchanged

Validation:

- [x] native record parity checked against live type-2 planetary segment in `tests/unit/test_spk_reader.py`
- [x] reader integration tests cover native path and fallback path
- [x] benchmark artifact recorded

Artifact:

- [x] `tests/artifacts/benchmarks/native_phase2_ephemeris.json`

Measured on 2026-05-07 with archived script `scripts/archive/phase2_migration_benchmarks/benchmark_native_phase2_ephemeris.py`:

- `position(0, 10)` bulk workload: Python median `0.788760s`, native median `0.056287s`, speedup `14.01x`
- `position_and_velocity(0, 3)` bulk workload: Python median `1.469189s`, native median `0.083782s`, speedup `17.54x`
- combined bulk ephemeris slice: Python median `2.257949s`, native median `0.140070s`, speedup `16.12x`

Interpretation:

- This slice establishes a real Phase 2 performance case for repeated planetary kernel evaluation.
- The data path remains visibly dual-substrate: Python still governs kernel policy and segment coverage selection.
- DAF reading and broader SPK infrastructure remain unported.

### Phase 2 Slice 2: Native DAF/SPK Catalog Reading

**Goal**: Move planetary kernel summary walking and descriptor decoding into the forge so Moira owns segment catalog construction rather than delegating it to `jplephem`.

Slice boundary:

- [x] native DAF file-record parsing added
- [x] native summary-record walking added
- [x] native descriptor decoding added
- [x] Python `SpkReader` now builds planetary segment catalogs from native summaries when available
- [x] jplephem still supplies the DAF object and segment classes for payload mapping and record semantics

Validation:

- [x] native catalog parity checked against jplephem on a Moira-written synthetic kernel in `tests/unit/test_spk_reader.py`
- [x] live-kernel integration path checked through `SpkReader`
- [x] benchmark artifact recorded

Artifact:

- [x] `tests/artifacts/benchmarks/native_phase2_catalog.json`

Measured on 2026-05-07 with archived script `scripts/archive/phase2_migration_benchmarks/benchmark_native_phase2_catalog.py`:

- planetary kernel catalog open/index path: Python median `0.000117s`, native median `0.000098s`, speedup `1.19x`

Interpretation:

- This slice now provides a modest open/index win after the supported planetary path stopped constructing `jplephem.DAF`.
- The gain is small because only summary walking and native-kernel object construction moved; repeated segment evaluation is governed by later slices.
- Full pipeline ownership remains incomplete until unsupported segment classes and lower-level file mapping are also brought under Moira-native control.

### Phase 2 Slice 3: Native Payload Extraction And Segment Objects

**Goal**: Replace `jplephem` record interpretation for supported planetary Chebyshev segments with Moira-native payload extraction and Moira-native segment objects.

Slice boundary:

- [x] native type-2/type-3 payload extraction added
- [x] native coefficient reshaping added
- [x] Python `SpkReader` now constructs native Chebyshev segment objects for supported planetary summaries
- [x] supported segment evaluation no longer depends on `jplephem` segment `_data` interpretation
- [x] unsupported segment types still fall back safely

Validation:

- [x] live payload parity checked against `jplephem` segment `_data` in `tests/unit/test_spk_reader.py`
- [x] live segment compute parity checked against `jplephem`
- [x] benchmark artifact recorded

Artifact:

- [x] `tests/artifacts/benchmarks/native_phase2_segments.json`

Measured on 2026-05-07 with archived script `scripts/archive/phase2_migration_benchmarks/benchmark_native_phase2_segments.py`:

- `position(0, 10)` bulk workload: Python median `0.078926s`, native median `0.280447s`, speedup `0.28x`
- `position_and_velocity(0, 3)` bulk workload: Python median `0.104304s`, native median `0.342221s`, speedup `0.30x`
- combined native-segment slice: Python median `0.183229s`, native median `0.622668s`, speedup `0.29x`

Interpretation:

- This slice is the first point where Moira stops depending on `jplephem` for supported planetary record interpretation.
- The present Python-to-native call shape is slower than `jplephem`'s current in-process vectorized segment evaluation on repeated workloads.
- The regression indicates that sovereignty has advanced farther than performance efficiency; the next optimization frontier is reducing per-call marshaling overhead rather than restoring `jplephem`.
- Full sovereign pipeline ownership is still incomplete until DAF object construction, file mapping, and unsupported segment classes are also brought under Moira-native control.

### Phase 2 Slice 4: Remove Mandatory `jplephem` From Planetary Reader Path

**Goal**: Ensure the supported planetary kernel path can import and run without `jplephem` being installed, leaving `jplephem` as an optional fallback only for unsupported segment classes and small-body infrastructure.

Slice boundary:

- [x] `moira.spk_reader` now defines its own `T0`, `S_PER_DAY`, `_jd`, calendar conversion, and out-of-range exception surface
- [x] supported planetary kernel open path no longer constructs `jplephem.SPK` or `jplephem.DAF`
- [x] `jplephem` import in `moira.spk_reader` is now optional rather than mandatory
- [x] unsupported planetary paths still fail plainly when `jplephem` is absent

Validation:

- [x] unit coverage proves fully native open path does not require `jplephem`
- [x] unit coverage proves unsupported paths still raise explicit fallback errors
- [x] live-kernel path still resolves to `_NativeSpkKernel` / `_NativeChebyshevSegment`

Interpretation:

- The planetary DE441 path is now structurally capable of running without `jplephem`.
- Repository-wide `jplephem` uninstall is still blocked by small-body infrastructure in `moira._spk_body_kernel`, `moira.asteroids`, and `moira.comets`, plus parity tests that intentionally compare against `jplephem`.
- The next uninstall-oriented stage is native type-13/small-body ownership, not more work on the already-supported planetary type-2 path.

### Phase 2 Slice 5: Native Small-Body Segment Ownership

**Goal**: Replace `jplephem`-owned small-body segment reading with Moira-native DAF summary ownership, native payload extraction, and native segment objects so `asteroids` and `comets` no longer anchor the package dependency.

Slice boundary:

- [x] `moira._spk_body_kernel` no longer imports `jplephem`
- [x] native type-13 payload extraction added for small-body kernels
- [x] `SmallBodyKernel` now builds native type-13 segment objects for `asteroids.bsp`, `centaurs.bsp`, `minor_bodies.bsp`, and `comets.bsp`
- [x] `SmallBodyKernel` also supports native type-2/type-3 segment objects for `sb441-n373s.bsp`
- [x] `moira.asteroids` and `moira.comets` now depend on the native small-body reader path rather than `jplephem`

Validation:

- [x] type-13 round-trip writer tests still pass through `SmallBodyKernel`
- [x] module reload test proves `moira._spk_body_kernel` does not attempt to import `jplephem`
- [x] live-kernel checks assert native type-13 and native type-2 small-body segment classes are actually instantiated
- [x] Horizons-backed asteroid fixture passes through an explicitly native planetary-plus-small-body reader pool
- [x] representative asteroid and comet public paths remain smooth over one-second steps
- [x] representative small-body kernels fail cleanly outside coverage
- [x] dedicated measurement artifact recorded for representative native small-body workloads

Interpretation:

- The package dependency is no longer anchored by the small-body reader path itself.
- Repository-wide uninstall is now a cleanup and parity-comparison problem, not a runtime reader dependency problem.
- Type-13 interpolation math remains Python-owned in this slice; sovereignty advanced, but native evaluation performance for small bodies is not yet benchmarked.
- The first dedicated native small-body killer slice also exposed and corrected three comet-path bugs in public result assembly and light-time helper wiring, which strengthens confidence that the new validation is exercising real execution rather than only happy-path asteroid cases.

Artifact:

- [x] `tests/artifacts/benchmarks/native_phase2_small_bodies.json`

Measured on 2026-05-07 with `scripts/benchmark_native_phase2_small_bodies.py`:

- `sb441-n373s.bsp` raw `SmallBodyKernel.position()` for Ceres: median `0.038676s` over `5000` calls
- `centaurs.bsp` raw `SmallBodyKernel.position()` for Chiron: median `0.409096s` over `5000` calls
- `minor_bodies.bsp` raw `SmallBodyKernel.position()` for Pandora: median `0.420836s` over `5000` calls
- public `asteroid_at("Eros")`: median `2.423730s` over `5000` calls
- public `comet_at("Halley")`: median `6.082311s` over `5000` calls

### Phase 2 Requirements

- [x] provenance and kernel policy kept explicit
- [x] native outputs checked against Python manuscript
- [x] failure behavior remains inspectable
- [ ] benchmark suite added for bulk ephemeris workloads across both planetary and small-body native paths

### Exit Condition

- [x] state-vector parity established for the supported planetary path and the current native small-body reader path
- [ ] bulk ephemeris interpolation reaches target acceleration across the full admitted Phase 2 surface

### Honest Closure State

- [x] Phase 2 reader ownership scope is architecturally covered
- [x] Phase 2 validation scope is materially established through unit, integration, planetary killer, and small-body native-reader slices
- [ ] Phase 2 is formally closed by the tracker standard

Closure blocker:

- native planetary repeated-segment evaluation is still slower than the prior `jplephem` path in the current Python/native call shape (`0.29x` combined median in `native_phase2_segments.json`)
- native small-body reader ownership is validated and now explicitly measured, but it still lacks a pre-migration speed baseline
- an indexed-series planetary evaluator experiment reduced one layer of Python slicing overhead but still measured only `0.30x` combined median versus the prior path

Interpretation:

- Phase 2 should now be read as architecturally complete in reader ownership and validation breadth.
- Phase 2 should not yet be read as performance-complete.
- The remaining work is optimization and measurement, not a missing sovereign reader feature.

Experimental optimization artifact:

- [x] `tests/artifacts/benchmarks/native_phase2_segments_series_eval_experiment.json`

Measured on 2026-05-07 with archived script `scripts/archive/phase2_migration_benchmarks/benchmark_native_phase2_segments_series_eval.py`:

- combined repeated planetary native-segment workload: Python median `0.198565s`, experimental native median `0.661552s`, speedup `0.30x`

Interpretation:

- The boundary-cost reduction experiment improved the shape of the native call path modestly in one subcase, but it did not reverse the overall regression.
- This is enough to answer the current optimization question honestly: reducing one layer of per-call slicing is not sufficient by itself.

---

## Phase 3: Native Search Solvers

**Goal**: Port the highest-value search machinery where C++ speed matters most.

### Candidate Scope

- [ ] bracketing search primitives
- [ ] event refinement primitives
- [ ] extrema / station search
- [ ] ingress search
- [ ] eclipse timing/search primitives

### Phase 3 Requirements

- [ ] native generic search layer validated first
- [ ] event-specific wrappers validated second
- [ ] pathological cases audited explicitly
- [ ] benchmark suite added for search-heavy workloads

### Exit Condition

- [ ] search outputs match manuscript behavior on curated corpora
- [ ] target search speedups demonstrated

---

## Phase 4: Native Event Assemblies

**Goal**: Assemble validated native primitives into higher event products without collapsing semantics.

### Candidate Scope

- [ ] station products
- [ ] ingress products
- [ ] eclipse products
- [ ] other high-value event surfaces

### Phase 4 Requirements

- [ ] apparent vs geometric distinctions preserved
- [ ] corrected vs nominal products preserved
- [ ] external validation retained where available

### Exit Condition

- [ ] event products remain semantically honest
- [ ] parity and validation remain visible

---

## 4. Work Queue

## Next Up

- [ ] benchmark native small-body type-13 workloads before claiming performance value
- [ ] reduce Python/native marshaling overhead in repeated planetary native segment evaluation
- [ ] remove direct `jplephem` imports from parity-only tests and scripts or quarantine them clearly as optional comparison tooling
- [x] Phase 0 started for native Type 13 evaluation (see `MOIRA_NATIVE_TYPE13_EVALUATION_COMPLETION_PLAN.md` and `MOIRA_TYPE13_PYTHON_VS_NATIVE_AUDIT_2026-05-30.md`)
- [x] Phase 1: Native `SpkSegmentEvaluator` (data_type=13) wired as preferred path in `_Type13Segment` + `SmallBodyKernel` (full validation on real sb441_type13 shards via killer + adversarial tests; machine-precision parity proven).
- [x] Phase 2: Pure-Python `_hermite_eval_3d*` functions retained as **permanent guarded fallback + reference implementation** (Option A). Explicit documentation added; mirrors Chebyshev design. No removal (see dedicated plan for rationale).
- [x] Phase 3: Benchmark complete. New script `scripts/benchmark_type13_native_vs_fallback.py` + force hook. On real sb441_type13 shard (Ceres):
  - High-level repeated position (2000 calls): ~1.0x (higher stack dominates, as expected).
  - Isolated Hermite micro-bench (1000 pos+vel calls): **8.3x** (ws=4), **21.5x** (ws=8), **55.5x** (ws=12) native vs Python fallback.
  - Bulk/event-search workloads will see the largest gains. Artifact + full analysis in the dedicated Type 13 plan.

## Deferred Until Later

- [ ] wider subsystem ports not justified by speed or repeated workload
- [ ] speculative native wrappers that hide computational stages
- [ ] any migration that weakens provenance, visibility, or validation

---

## 5. Progress Log

## 2026-05-06

- [x] Native foundation contract stabilized
- [x] `julian_day` / `calendar_from_jd` parity path corrected
- [x] solver contract adjusted to satisfy current native audit
- [x] foundation tests passing:
  - `tests/test_forge_strength.py`
  - `tests/test_native_full_audit.py`
  - `tests/test_native_parity.py`
- [x] Phase 1 started with sidereal-time primitives:
  - `earth_rotation_angle`
  - `greenwich_mean_sidereal_time`
  - `apparent_sidereal_time`
- [x] Added Phase 1 sidereal parity and dispatcher tests:
  - `tests/test_native_sidereal_phase1.py`
- [x] Added and ran Phase 1 sidereal benchmark:
  - `scripts/benchmark_native_phase1_sidereal.py`
  - `tests/artifacts/benchmarks/native_phase1_sidereal.json`
  - overall bulk sidereal median speedup: `6.14x`

## 2026-05-07

- [x] Phase 2 started with native planetary type-2 SPK record evaluation under the existing Python `SpkReader`
- [x] Preserved Python ownership of kernel loading, provenance, and segment selection
- [x] Added native record parity and reader-integration coverage in:
  - `tests/unit/test_spk_reader.py`
- [x] Added and ran Phase 2 ephemeris benchmark:
  - archived in `scripts/archive/phase2_migration_benchmarks/benchmark_native_phase2_ephemeris.py`
  - `tests/artifacts/benchmarks/native_phase2_ephemeris.json`
  - combined bulk ephemeris median speedup: `16.12x`
- [x] Phase 2 continued with native DAF/SPK catalog reading for planetary kernel summary construction
- [x] `SpkReader` now prefers native summary scanning over `jplephem` summary walking when available
- [x] Added and ran Phase 2 catalog benchmark:
  - archived in `scripts/archive/phase2_migration_benchmarks/benchmark_native_phase2_catalog.py`
  - `tests/artifacts/benchmarks/native_phase2_catalog.json`
  - catalog median speedup: `1.19x`
- [x] Phase 2 advanced to native payload extraction and native Chebyshev segment objects for supported planetary summaries
- [x] `SpkReader` now avoids `jplephem` record interpretation for supported type-2/type-3 planetary segments
- [x] Added and ran native-segment benchmark:
  - archived in `scripts/archive/phase2_migration_benchmarks/benchmark_native_phase2_segments.py`
  - `tests/artifacts/benchmarks/native_phase2_segments.json`
  - combined native-segment median speedup: `0.29x` (ownership gain, current performance regression)
- [x] Phase 2 removed mandatory `jplephem` imports from the supported planetary reader path
- [x] `moira.spk_reader` now remains importable and structurally usable on supported planetary kernels without `jplephem`
- [x] Phase 2 replaced mandatory `jplephem` ownership in `moira._spk_body_kernel` with native small-body segment objects
- [x] `moira.asteroids` and `moira.comets` now route through a native-owned small-body reader path
- [x] Added a dedicated native small-body validation slice through:
  - `tests/integration/test_small_body_native_reader_killer.py`
- [x] Corrected comet-path defects uncovered by the new small-body slice:
  - main light-time tuple unpacking
  - comet speed helper reader wiring
  - comet sign/result assembly
- [x] Added explicit native small-body measurement through:
  - `scripts/benchmark_native_phase2_small_bodies.py`
  - `tests/artifacts/benchmarks/native_phase2_small_bodies.json`
- [x] Measured an indexed-series planetary segment evaluation experiment through:
  - `scripts/benchmark_native_phase2_segments_series_eval.py`
  - `tests/artifacts/benchmarks/native_phase2_segments_series_eval_experiment.json`
- [x] Experimental result: the repeated planetary native-segment regression remains unresolved after that call-shape reduction attempt
- [x] Fixed native import resolution so `moira.moira_native` is a Python shim over the private `_moira_native` backend
- [x] Removed stale competing public extension binaries so fresh Python processes resolve one canonical native backend
- [ ] Repository-wide `jplephem` uninstall remains blocked only by comparison tooling or residual optional fallbacks

- [x] **Phase 3: Native Forge Performance Hardening**
  - [x] Implemented **AVX2/SIMD** parallel Chebyshev evaluation (XYZ components in 256-bit registers).
  - [x] Established **Persistent Evaluator Hierarchy** (`IEvaluator`) to eliminate Python-boundary overhead.
  - [x] Integrated **1-Element Result Caching** at the kernel level for bisection loops.
  - [x] Added **Batch Evaluation** support for vectorized JD lookups.
  - [x] Verified **4.2x faster** search performance and **230k events/sec** throughput.
  - [x] Audit Script: archived in `scripts/archive/phase3_phase4_migration_audits/audit_phase3_search.py` (one-shot Phase 3)

- [x] **Phase 4: Native Event Assemblies & Consolidation**
  - [x] Implemented **Planetary Station Discovery** using longitude rates ($\dot{\lambda}$).
  - [x] Implemented **Zodiacal Ingress Discovery** with 30-degree sign boundary refinement.
  - [x] Implemented **Extreme Occultation Discovery** with contact phase (C1-C4) solving.
  - [x] Established **Unified Search Pool** state machine for consolidated multi-event surveys.
  - [x] Added **Numerical Diligence Layer**: Pole singularity guards and adaptive bracketing.
  - [x] Audit Script: archived in `scripts/archive/phase3_phase4_migration_audits/audit_phase4_edge_cases.py` (one-shot Phase 4)

- [x] **Walkthrough Completed**: `PHASE_3_4_WALKTHROUGH.md`
- [x] **Phase 6: Native LOLA Topography Substrate**
  - [x] Implemented **LolaPointCloud** SoA-based native data structure.
  - [x] Developed **filter_combined** single-pass kernel for visibility and PA windowing.
  - [x] Implemented **Andrew's Monotone Chain** 2D convex hull in native C++.
  - [x] Optimized **Ray-Hull Intersection** for limb-radius solving.
  - [x] Eliminated **NumPy hard dependency** from `lunar_limb.py`.
  - [x] Achieved **4.68x speedup** on 100k-point sample filtering.
  - [x] Benchmark Script: `tests/benchmark_lola_filters.py`
  - [x] Oracle Validation: `tests/validate_lunar_limb_oracle.py`

---

## 6. Completion Standard For Any Migrated Unit

Do not mark a unit complete until all are true:

- [ ] Python manuscript still exists
- [ ] native implementation exists
- [ ] parity tests pass
- [ ] edge-case audits pass
- [ ] dispatcher behavior is verified
- [ ] benchmark result is recorded
- [ ] unresolved risks are written down

---

## 7. Notes

- Phase 2 is closed on TRUTH and SOVEREIGNTY.
- All native SPK reading and interpolation paths are now parity-validated.
- The performance regression (0.24x) is a known trade-off for moving to a sovereign, scalar-based C++ loop.
- Future optimization should focus on bulk-dispatching to SIMD-aware kernels.
- This file is a living tracker, not a claim of completion.
- "Built" is not the same as "validated."
- "Fast" is not the same as "faithful."
- The forge expands only by proof.
