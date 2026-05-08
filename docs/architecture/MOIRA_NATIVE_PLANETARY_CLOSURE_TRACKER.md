# Moira Native Planetary Closure Tracker

**Status**: Execution ledger
**Date**: 2026-05-08
**Companion documents**:
- [MOIRA_NATIVE_PLANETARY_PATH.md](./MOIRA_NATIVE_PLANETARY_PATH.md)
- [MOIRA_NATIVE_CLOSURE_PROGRAM.md](./MOIRA_NATIVE_CLOSURE_PROGRAM.md)
- [MOIRA_NATIVE_BACKEND_ARCHITECTURE.md](./MOIRA_NATIVE_BACKEND_ARCHITECTURE.md)
- [MOIRA_NATIVE_MIGRATION_TRACKER.md](./MOIRA_NATIVE_MIGRATION_TRACKER.md)

---

## 1. Purpose

This document turns the planetary path map into a closure ledger.

It is meant to answer, stage by stage:

- what currently owns the work
- what native capability already exists
- what is still missing
- what must be proven before the stage can be called closed
- what depends on what

This tracker is for the canonical planetary calculation pipeline.

It is not a generic native wish list.

---

## 2. Reading Rules

For each row:

- `current owner` means the code path that governs normal execution today
- `native target` means the smallest justified native closure target
- `parity gate` means the minimum correctness proof needed before routing
- `benchmark gate` means the measured surface that must have an artifact
- `production-route gate` means what must be true before the row counts as engine-routed

Status meanings:

- `Closed`: implemented, integrated, parity-backed, and acceptable for the claimed route
- `Partial`: some native capability exists, but one or more closure gates are still open
- `Open`: canonical path remains Python-owned and no admitted native route is yet closed
- `Intentional Python`: should remain Python-owned by doctrine or by low-value economics

---

## 3. Dependency Order

The planetary path should be closed in this order:

1. reader routing truth
2. reader performance truth
3. barycentric and geocentric orchestration
4. public planetary benchmark surfaces
5. apparent correction closure if justified
6. coordinate assembly closure if justified

The practical reason is simple:

- if the reader layer is not honestly closed, higher routing claims are weak
- if engine-level benchmark surfaces are not measured, local native wins can be misleading
- if the correction and coordinate layers remain Python by deliberate design, that should be stated rather than obscured

---

## 4. Closure Ledger

| ID | Pipeline stage | Canonical surface | Current owner | Native capability now | Current status | Main integration gap | Parity gate | Benchmark gate | Production-route gate | Depends on |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| PP-01 | Facade kernel context | [moira/_facade_kernel.py](/c:/Users/nilad/OneDrive/Desktop/Moira%20C++/moira/_facade_kernel.py:71) | Python | Native readers already sit behind `KernelPool` | Intentional Python | None at the orchestration layer; keep policy visible | Reader override tests prove the intended reader is selected | No standalone benchmark required | Public facade surfaces must continue to reach the same reader context without hidden switching | None |
| PP-02 | Public chart assembly | [moira/_facade_core.py](/c:/Users/nilad/OneDrive/Desktop/Moira%20C++/moira/_facade_core.py:70) | Python | Indirect only through deeper stages | Intentional Python | None unless benchmarking shows facade overhead dominates | Existing chart tests continue to pass unchanged | `Moira.chart(...)` end-to-end timing only after deeper rows are routed | Facade path must remain semantically unchanged while deeper native stages are admitted | PP-01 |
| PP-03 | Time conversion and sidereal helpers | `moira.julian`, `moira.dispatch` | Mixed Python and native | Native Julian/sidereal helpers are already routed in a narrow slice | Partial | Widening is not the goal; document admitted scope clearly | Current parity tests for routed Julian/sidereal helpers remain green | Keep existing sidereal artifact current if route changes | Normal planetary calls must reach the admitted helper route without alternate script setup | PP-01 |
| PP-04 | Reader selection and fallback dispatch | [moira/spk_reader.py](/c:/Users/nilad/OneDrive/Desktop/Moira%20C++/moira/spk_reader.py:166) | Python orchestration over native-capable reader | Native DAF path can replace `jplephem` for supported kernels | Partial | Fallback truth and support boundaries must remain explicit | Import-resolution and supported/unsupported reader tests | Supported-vs-fallback comparison at reader-entry level | Standard planetary calls must reach the native reader automatically when conditions are satisfied | PP-01 |
| PP-05 | Planetary kernel open and catalog scan | [moira/spk_reader.py](/c:/Users/nilad/OneDrive/Desktop/Moira%20C++/moira/spk_reader.py:149) | Native-backed through `SpkReader` | Native summary scan and segment construction exist | Partial | Performance is only modestly improved and must remain honestly framed | `tests/unit/test_spk_reader.py` plus supported-kernel parity coverage | `native_phase2_catalog.json` or successor artifact on the same surface | Normal `SpkReader` construction in `.venv` must take the native path on supported kernels | PP-04 |
| PP-06 | Segment payload extraction and Chebyshev evaluation | [moira/spk_reader.py](/c:/Users/nilad/OneDrive/Desktop/Moira%20C++/moira/spk_reader.py:122), [moira/spk_reader.py](/c:/Users/nilad/OneDrive/Desktop/Moira%20C++/moira/spk_reader.py:180) | Native-backed reader internals | Native record load and series evaluation exist for supported segments | Partial | Current checked artifacts show repeated-workload regression | Direct native-vs-Python state-vector parity on supported segment types | A replacement for `native_phase2_segments.json` showing the same surface and an honest baseline | Reader `position(...)` and `position_and_velocity(...)` must hit this path in normal planetary execution | PP-05 |
| PP-07 | Supplemental small-body reader path | [moira/_spk_body_kernel.py](/c:/Users/nilad/OneDrive/Desktop/Moira%20C++/moira/_spk_body_kernel.py:132) | Native-backed reader internals | Native ownership exists for supported supplemental kernels | Partial | Baseline and route claims need tighter benchmarking language | Integration and parity tests for supported small-body kernels | Small-body artifact with explicit pre-migration or fallback baseline | Supplemental kernels loaded through `KernelPool` must use the same normal route, not a script-only entry | PP-04 |
| PP-08 | Barycentric route chaining | [moira/planets.py](/c:/Users/nilad/OneDrive/Desktop/Moira%20C++/moira/planets.py:407) | Python | No canonical native wrapper yet; only reader-level acceleration below | Open | Repeated Python reader calls and route chaining overhead | Named parity tests for `_barycentric(...)` and `_barycentric_state(...)` against current Python truth if native wrapper is added | Microbenchmark on repeated body-state assembly, not just raw segment eval | `planet_at(...)`, `heliocentric_planet_at(...)`, and `planet_relative_to(...)` must all reach the same admitted wrapper | PP-06 |
| PP-09 | Earth barycentric state and geocentric subtraction | [moira/planets.py](/c:/Users/nilad/OneDrive/Desktop/Moira%20C++/moira/planets.py:457), [moira/planets.py](/c:/Users/nilad/OneDrive/Desktop/Moira%20C++/moira/planets.py:474) | Python | No canonical native wrapper yet | Open | High-value vector assembly still sits above the native reader boundary | Named parity tests for `_earth_barycentric*` and `_geocentric*` surfaces if routed | Benchmark repeated geocentric assembly for representative planetary calls | `planet_at(...)` must use the routed path in ordinary execution with explicit fallback behavior | PP-08 |
| PP-10 | Public `planet_at(...)` canonical product | [moira/planets.py](/c:/Users/nilad/OneDrive/Desktop/Moira%20C++/moira/planets.py:610) | Python | Indirect native participation only through lower reader stages | Open | No admitted native route above vector acquisition | Existing public parity semantics must remain exact if deeper routing changes | End-to-end `planet_at(...)` artifact on supported bodies and representative dates | Public call must use the admitted native-supported planetary substrate without caller patching | PP-09 |
| PP-11 | Public `all_planets_at(...)` chart workload | [moira/planets.py](/c:/Users/nilad/OneDrive/Desktop/Moira%20C++/moira/planets.py:1000) | Python | Indirect only through reader and narrow sidereal helpers | Open | This is the real engine benchmark surface and is not yet native-closed | Existing chart-level semantics and ordering must remain stable | End-to-end artifact for repeated chart-style workloads | Normal chart assembly must hit the same routed planetary substrate in `.venv` | PP-10 |
| PP-12 | Public `heliocentric_planet_at(...)` product | [moira/planets.py](/c:/Users/nilad/OneDrive/Desktop/Moira%20C++/moira/planets.py:1102) | Python | Indirect reader-level acceleration only | Open | No admitted native wrapper above barycentric fetches | Parity tests against current heliocentric Python truth if wrapper is added | End-to-end heliocentric benchmark only after PP-08 and PP-09 close | Public call must route through the same admitted barycentric substrate as other planetary products | PP-08 |
| PP-13 | Public `planet_relative_to(...)` product | [moira/planets.py](/c:/Users/nilad/OneDrive/Desktop/Moira%20C++/moira/planets.py:1261) | Python | Indirect reader-level acceleration only | Open | Relative-vector assembly still lives above the native boundary | Parity tests against current relative-position Python truth if wrapper is added | Benchmark relative-body workloads only after shared vector substrate is closed | Public call must use the same routed substrate, not a one-off native path | PP-08 |
| PP-14 | Apparent correction stack | [moira/corrections.py](/c:/Users/nilad/OneDrive/Desktop/Moira%20C++/moira/corrections.py:152) onward | Python | Some extension primitives may exist, but no canonical route is active | Intentional Python until a justified target is named | No closure target should be admitted without source-derived semantics and explicit policy preservation | Function-by-function parity against current Python manuscript if any routing is proposed | Benchmark only for a named public product, not isolated scalar helpers | A native route counts only if a public planetary surface reaches it with unchanged semantics | PP-10 |
| PP-15 | Rotation composition and frame transforms | [moira/planets.py](/c:/Users/nilad/OneDrive/Desktop/Moira%20C++/moira/planets.py:563), [moira/coordinates.py](/c:/Users/nilad/OneDrive/Desktop/Moira%20C++/moira/coordinates.py:173) | Python | Native primitives may exist, but canonical routing is absent | Intentional Python until benchmark pressure justifies change | No admitted closure case yet above the current Python truth path | Exact vector and angular parity against current Python transforms if routing is proposed | Benchmark only as part of `planet_at(...)`, `sky_position_at(...)`, or chart workloads | Any route must remain hidden behind unchanged public semantics and explicit fallback | PP-10 |
| PP-16 | Public `sky_position_at(...)` apparent topocentric product | [moira/planets.py](/c:/Users/nilad/OneDrive/Desktop/Moira%20C++/moira/planets.py:848) | Python | Native help exists only below the reader boundary | Open | Depends on unresolved apparent and horizontal-path closure | Current sky-position semantics must be preserved exactly if any native routing is attempted | End-to-end sky-position artifact on representative topocentric cases | Public sky-position calls must reach the admitted route without changing inputs, vessels, or defaults | PP-09, PP-14, PP-15 |
| PP-17 | Result-vessel packaging | `PlanetData`, `SkyPosition`, `HeliocentricData`, `Chart` | Python | No native target is justified | Intentional Python | None | Existing public API and vessel tests are sufficient | No standalone benchmark required | Vessels remain Python-facing even if deeper computation changes | PP-10, PP-11, PP-12, PP-13, PP-16 |

---

## 5. Stage Priorities

The highest-value closure rows are:

1. `PP-06` segment payload extraction and Chebyshev evaluation
2. `PP-08` barycentric route chaining
3. `PP-09` Earth barycentric and geocentric construction
4. `PP-10` public `planet_at(...)`
5. `PP-11` public `all_planets_at(...)`

These are the rows most likely to determine whether the native planetary effort becomes engine-real rather than reader-local.

---

## 6. Immediate Work Queue

The smallest correct execution queue is:

1. re-benchmark `PP-06` with a clean baseline and identify where boundary overhead dominates
2. decide whether `PP-08` and `PP-09` should be wrapped natively or deliberately left Python-owned
3. if they are admitted, add parity tests before widening any route
4. benchmark `PP-10` and `PP-11` as the first public closure surfaces
5. only then decide whether `PP-14` through `PP-16` deserve native closure effort

This keeps the program disciplined.

It prevents the repository from spending closure effort on late-stage coordinate or apparent products before the core planetary substrate is honestly measured.

---

## 7. Exit Standard

The planetary pipeline can be called native-closed only when:

1. the reader-level rows are either `Closed` or explicitly accepted as sovereignty-only
2. the vector-orchestration rows are either `Closed` or explicitly retained as Python by policy
3. at least `planet_at(...)` and `all_planets_at(...)` have end-to-end benchmark artifacts
4. production routing is proven through normal `.venv` execution, not script-only experiments
5. the documentation says plainly which rows are deliberately Python and which rows are truly native-routed

Until then, the honest reading remains:

- native planetary support is real
- reader-level integration is materially advanced
- full planetary closure is still in progress
