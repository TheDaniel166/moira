# Paran Performance Validation

Date: 2026-07-12

Status: Python fast path admitted; native heliacal acceleration remains gated
by separate parity repair

## 1. Governing Object

The optimized product is unchanged: exact rise, set, upper transit, and lower
transit events within one 24-hour window, combined into paran pairs under the
existing time-orb doctrine. Analytic geometry and Newton iteration provide
brackets or estimates; the exact altitude/hour-angle signals remain the event
authority.

## 2. Baseline

Measured in the project `.venv` on the local Windows reference checkout after
kernel/catalog warm-up where applicable:

| Operation | Before |
|---|---:|
| `_lst` | 0.076 ms |
| stellar transit | 14.4 ms |
| stellar `find_phenomena` | 100.9 ms |
| stellar `_crossing_times` | 160.0 ms |
| Mars `_crossing_times` | 298.5 ms |
| 67-latitude field column | approximately 45 s in the supplied audit |

The focused pre-edit truth slice passed 95 tests.

## 3. Admitted Changes

1. Reuse the one nutation evaluation when constructing apparent sidereal time.
2. Seed meridian transit from the forward hour-angle displacement, perform at
   most eight Newton refinements, verify the exact residual and 24-hour window,
   then fall back to the original scan.
3. For fixed stars, derive daily altitude extrema and hour-angle brackets from
   center-window RA/Dec, then refine the exact altitude signal.
4. For planets, use center-window RA/Dec only to estimate brackets; exact
   topocentric altitude remains authoritative and failed estimates fall back to
   scanning.
5. Split paran horizon and meridian collection so latitude-independent stellar
   MC/IC events can be reused in a field column.
6. Add explicit request/field-scoped crossing reuse. There is no global cache;
   planetary keys retain the active reader identity.
7. Remove the prior duplicate MC/IC computation inside `_crossing_times`.

## 4. Parity Evidence

- Newton-first transits are compared with scan/bisection truth for all ten
  planets plus Regulus and Acrux, upper and lower transits, at five latitudes
  from -66 to +66 degrees; tolerance is 0.5 seconds.
- Fixed-star horizon events are compared with scan/bisection truth for five
  stars over the full -66 to +66 degree sweep in two-degree increments;
  event-set equality is exact and timing tolerance is 0.5 seconds.
- Planet horizon estimates are pinned against scan truth for all ten planets at
  -66, 0, and +66 degrees in the normal suite. A full two-degree sweep is part
  of the implementation acceptance receipt.
- The existing offline Horizons rise/set and paran fixtures remain required.
- Circumpolar diagnostic states are compared against the prior sampled states,
  including a grazing fixed-star geometry case.

## 5. Performance Receipt

Run:

```powershell
$env:MOIRA_NO_DOWNLOAD = "1"
$env:MOIRA_PERF_ASSERT = "1"
.\.venv\Scripts\python.exe tests\benchmark_paran_performance.py
```

Observed after implementation:

| Operation | After |
|---|---:|
| `_lst` | 0.043 ms |
| stellar transit | 0.53 ms |
| stellar `_crossing_times` | 11.1 ms |
| warmed Mars `_crossing_times` | 22.2 ms |
| 67-latitude field column | 1.09 s |
| field sample average | 16.3 ms |
| 53-available-star packet core | 0.51 s |

These are local performance evidence, not astronomical validation. The script's
absolute gates are opt-in because timing varies by host.

## 6. Native Heliacal Boundary

Native heliacal functions are not enabled by default by this performance work.
The pre-existing catalog-batch path remains available only through explicit
`use_native_heliacal=True`, and only for its fixed default heliacal policy.
Custom policy necessarily stays on Python truth. The C++ path still requires
independent Python/native parity for visibility policy, setting semantics,
Delta-T handling, frame/correction choices, observable roots, event ordering,
and metadata. Performance cannot authorize a divergent second doctrine.

A controlled Sirius probe with `setting_elongation_threshold=179` demonstrated
the gate's necessity: native returned a setting while the Python doctrine
correctly returned none. The former circular dispatch test has therefore been
renamed and now proves explicit native dispatch only; it is not parity evidence.
