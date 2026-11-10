# Memory-mapped DE441 batch validation, 2026-11-10

A multi-epoch native SPK batch uses a shared read-only view of the open kernel
for isolated record loads. The same file supplies buffered reads for
contiguous record windows and fallback when a view is unavailable. Both paths
supply the existing evaluator with coefficient words in file order. [Record reader][reader]

The comparison used the full 3,307,878,400-byte DE441 kernel
(SHA-256 `9a824e6a8ce3d39f8a513b17278ff7b7ad226f964c76d2019b0a51d8808d6ff5`),
CPython 3.14.8, Moira 6.13.1, Skyfield 1.55 with jplephem 2.24, and
NumPy 2.4.3 on Windows 11 x64 and an AMD Ryzen 7 8700F.

| Source or artifact | Identity |
| --- | --- |
| Source base and buffered build's commit | `c97d32e4214e6480b0b016d61ca6a8e14298f026` |
| Code and test diff from that base, SHA-256 | `263f50c17397a0f0bc0dc71b18f30a0abe8b9facba9ae6bf4e3a625c17509f87` |
| Buffered native extension, SHA-256 | `053e33507ccfd0b6af79b6464180bede2ff446faa9cc31fc95e2fe040c13e9f0` |
| Mapped native Release extension, SHA-256 | `0280b4965aa90044487dca9c455507f3ddf291a8d93e35e553fa634b31e70abc` |

## Batch timings

The same [native batch workloads][batch] use 16,384 epochs and 12 targets for
states and 2,048 epochs and 10 targets for Earth-centered reception light
time. Skyfield uses vectorized `.at()` and `.observe()` on the same TDB
Julian days, split by Skyfield into a day and a fraction. The handoff grid
spans two days on either side of JD(TDB) 2440432.5. The full state grid spans
both kernel endpoints, JD(TDB) −3100015.5 to 8000016.5. Full-span light-time
receptions stay one day inside each edge to allow for emission coverage.

Each entry is the median of five warmed runs with alternating reader order.
The buffered column comes from a fresh run of the previous binary. The
Skyfield column comes from the paired run with mapped Moira. The
[run data][results] include all round timings, exact grid hashes, and the
repeat using the original J2000-plus-offset Skyfield time split.

| DE441 grid | Workload | Results | Buffered Moira, ms | Mapped Moira, ms | Skyfield, ms |
| --- | --- | ---: | ---: | ---: | ---: |
| Handoff | State | 196,608 | 16.520 | 17.701 | 94.353 |
| Handoff | Light time | 20,480 | 5.110 | 5.137 | 35.236 |
| Full span | State | 196,608 | 681.559 | 120.359 | 117.130 |
| Full span | Light time | 20,480 | 103.547 | 10.684 | 38.792 |

The state grids selected 28 distinct coefficient records near the handoff
and 196,612 across the full span. The mapped full-span state batch ran
5.66× as fast as buffered Moira and within 3% of Skyfield's time. The mapped
full-span light-time batch ran 9.69× as fast as buffered Moira and 3.63× as
fast as Skyfield.

## Accuracy

All four Moira result arrays have identical float64 hashes before and after
mapping. The full-span maximum differences between Moira and Skyfield with
standard time input were 1.349 mm for geometric positions and 1.908 mm for
light-time positions.

The separate accuracy replay uses CSPICE N0067 through SpiceyPy 8.0.2 at the
same epochs as the [original validation][batch]. For DE441, CSPICE reads the
[verified handoff excerpt][handoffs] with SHA-256
`c3a7d212c1ef5c1e006ab8d714d68465db5f4a6885c507e404bcae3f68264591`.
Moira and Skyfield read the full kernel. The replay uses the original
Skyfield time split.

| Genuine DE441 handoff measurement | Samples | Buffered Moira | Mapped Moira | Skyfield |
| --- | ---: | ---: | ---: | ---: |
| Maximum geometric position residual, mm | 70 | 0 | 0 | 0.23842 |
| Maximum corrected position residual, mm | 90 | 2.83549 | 2.83549 | 6.13548 |
| Maximum corrected position residual at a crossing, mm | 49 | 2.83549 | 2.83549 | 6.11068 |

Across the complete replay, the mapped build reproduced the archived CSPICE
residuals for 3,829 states and 757 valid light-time samples, including all
140 crossings. It reproduced the coverage decisions for all 46 probes,
including rejection of 30 uncovered emission samples.

## Local verification

The focused offline suite passed 174 tests with two optional jplephem
comparisons skipped. The synthetic adjacency, overlap, Type 3 units, and
sub-Julian-day-tick emission cases exercise both kernel byte orders. A
Windows runtime probe observed one lazily created read-only DE441 view
shared across 24 concurrent calls and released on reader close.

The local timing harness is `tmp/spk-reader-comparison/compare_skyfield_de441_span.py`
with `--standard-skyfield-time`. The CSPICE replay uses
`tmp/spk-reader-comparison/compare_skyfield_batches.py --native-multi-epoch --quick`
with the original saved handoff and controlled fixtures. The timing grids in
the quick replay are omitted from the archive.

[reader]: ../../src/native/include/daf.hpp
[results]: ../../tests/artifacts/benchmarks/spk_mapped_de441_batches_2026-11-10.json
[batch]: SPK_NATIVE_BATCH_VALIDATION_2026-11-10.md
[handoffs]: SPK_HANDOFF_VALIDATION_2026-11-09.md
