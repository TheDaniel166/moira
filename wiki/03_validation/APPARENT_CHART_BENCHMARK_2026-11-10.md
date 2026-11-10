# Swiss Ephemeris comparison and apparent-chart optimization, 2026-11-10

The apparent-chart path now searches the ordered Delta-T tables directly
and shares each epoch's SPK selections between public and per-body routes. The
native nutation evaluator computes sine and cosine once for each distinct
argument tuple and adds the terms in their original order. Individual SPK
record misses use the same read-only mapping and buffered fallback as sparse
batches. The longitude-rate calculation uses the center epoch and the same
two samples at ±0.002 days. [IERS tables][iers] · [SPK mapping validation][mapped]

The tests used CPython 3.14.8, Moira 6.13.1, Swiss Ephemeris 2.10.03
(Python binding version 20230604), and NumPy 2.4.3 on Windows 11 x64 with an
AMD Ryzen 7 8700F. The [run archive][results] includes both sets of timing
rounds, stage profiles, kernel and binary hashes, and accuracy evidence.

| Source or artifact | Identity |
| --- | --- |
| Source base and previous build's commit | `306329bcd02f667b208c2290cbcee47def67baf2` |
| Code and test diff from that base, SHA-256 | `9ffd4644f25514829809f37a4f4bb57237894d2157061d288945c21b3f4f6f3b` |
| Previous native extension, SHA-256 | `0280b4965aa90044487dca9c455507f3ddf291a8d93e35e553fa634b31e70abc` |
| Optimized native Release extension, SHA-256 | `560a61cb09a9bf34204fdd73ece73a5513edde078446497cf056c5d96f9cfa99` |

## Timings

Both runs cover the Sun, Moon, and eight planets from 1900 to 2100. Each entry
is the median of five warmed runs with alternating engine order. Geometric
state and light-time workloads compare Moira's native multi-epoch reader
with the Swiss Python binding. The state arrays include velocities. The
apparent workloads use `all_planets_at` and `swe.calc_ut` at the same UT
inputs and include ecliptic longitude, latitude, distance, and longitude
speed.

In the shared DE440 comparison, Moira reads the JPL SPK and Swiss reads the
original JPL binary. The DE441 comparison uses the full DE441 SPK in Moira
and Astrodienst's standard `sepl_18.se1` and `semo_18.se1` files in Swiss.
Both Swiss files report DE441 provenance. The harness verifies the returned
Swiss backend flags on every accuracy and warmup call. [JPL ephemerides][jpl]
· [Swiss flags][swiss] · [Swiss data][swiss-data]

| Workload | Planet results | Moira before, ms | Moira after, ms | Swiss first run, ms | Swiss second run, ms |
| --- | ---: | ---: | ---: | ---: | ---: |
| Shared DE440 geometric states | 163,840 | 23.170 | 24.267 | 165.579 | 169.158 |
| Shared DE440 light-time positions | 20,480 | 11.206 | 11.729 | 54.102 | 59.509 |
| DE441 vs Swiss standard files, geometric states | 163,840 | 22.953 | 23.347 | 157.422 | 163.647 |
| DE441 vs Swiss standard files, light-time positions | 20,480 | 10.829 | 10.991 | 46.582 | 49.171 |
| 24 apparent charts | 240 | 6.661 | 4.230 | 1.948 | 1.931 |
| 1,024 apparent charts | 10,240 | 478.681 | 289.139 | 41.926 | 41.389 |

The 1,024-chart workload used 39.6% less time in the optimized build. The
separate instrumented passes show the largest reductions in clock
conversion and nutation.

## Accuracy

The independent physical comparison uses CSPICE N0067 via SpiceyPy 8.0.2
at 200 epochs with ten targets at each epoch. The reference is Earth-centered
J2000 geometry from `spkgeo` and converged reception light time from `spkpos`
with `CN`. For DE441, CSPICE uses a 1900–2100 excerpt whose 73,069 records
across 28 descriptors were verified against the full kernel. The excerpt
SHA-256 is `b72c8205c390403b4a9248b97c747329643cc73c0ad637d96526cec64f4de45d`.
[CSPICE corrections][cspice]

| Comparison | Maximum position residual, both Moira builds | Maximum position residual, Swiss |
| --- | ---: | ---: |
| Shared DE440 geometric | 0.026 mm | 1.970 mm |
| Shared DE440 reception light time | 1.357 cm | 4.581 m |
| DE441 vs Swiss standard files, geometric | 0.028 mm | 22.284 km |
| DE441 vs Swiss standard files, reception light time | 1.358 cm | 22.283 km |

Pluto had the largest geometric residual with the Swiss standard files.
The maximum geometric sky-angle residual across all ten bodies in that
comparison was 0.00774 arcseconds. For apparent charts, the two engines'
maximum pairwise sky separation was 0.00733 arcseconds with shared TT and
4.813 arcseconds with their respective UT conversions. Those conversions
produced TT values up to 8.185 seconds apart.

All 10,240 planetary results in the 1,024-chart grid matched before and
after, bit for bit in longitude, latitude, distance, and longitude speed.
The exact replay also matched 7,169 nutation evaluations, 5,121 clock
outputs with their source metadata, and 352 Delta-T table knots.

The separate [SPK handoff corpus][handoff] reproduced the published CSPICE
residuals on 3,829 states and 757 valid light-time samples, including 140
emission crossings. All 46 coverage decisions matched, including rejection
of 30 uncovered samples. The maximum DE441 crossing residual was 2.83549 mm
against the verified six-day handoff excerpt.

## Local verification

The focused suite passed 561 tests, including the ERFA frame checks, and
skipped two optional jplephem tests. The comparison harnesses and required
data were run from `tmp/swiss-benchmark`. Timings came from
`compare_swiss.py`, the stage profiles from `diagnose_apparent_speed.py`,
and the exact output comparisons from `apparent_accuracy_fingerprint.py`.

[results]: ../../tests/artifacts/benchmarks/swiss_apparent_chart_optimization_2026-11-10.json
[mapped]: SPK_MAPPED_BATCH_VALIDATION_2026-11-10.md
[handoff]: SPK_NATIVE_BATCH_VALIDATION_2026-11-10.md
[iers]: https://iers-conventions.obspm.fr/chapter5.php
[jpl]: https://ssd.jpl.nasa.gov/planets/eph_export.html
[swiss]: https://www.astro.com/ftp/swisseph/doc/swephprg.2.10.htm
[swiss-data]: https://www.astro.com/ftp/swisseph/ephe/
[cspice]: https://naif.jpl.nasa.gov/pub/naif/toolkit_docs/C/cspice/spkpos_c.html
