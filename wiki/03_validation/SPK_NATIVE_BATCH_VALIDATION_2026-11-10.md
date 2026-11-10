# Native SPK batch validation, 2026-11-10

`SpkReader.states_tdb_batch` and `SpkReader.received_light_tdb_batch` evaluate
explicit routes in a single J2000 Type 2 or 3 kernel. The state buffer contains
positions in km and velocities in km/day. The light-time buffer contains
observer-relative positions in km and reception delays in days. Both retain
the caller's route and epoch order. Each emission iteration selects the last
covering descriptor for each route leg, with the emission offset kept separate
from the reception TDB Julian day. [Reader API][reader] · [NAIF precedence][precedence]

The run used Moira 6.13.1 with the native batch patch, Skyfield 1.55 with
jplephem 2.24, and NumPy 2.4.3 on Windows 11 x64, CPython 3.14.8, and an AMD
Ryzen 7 8700F. The [raw run][results] contains kernel SHA-256 hashes, durations
for each round, accuracy residuals, and coverage outcomes.

| Source or artifact | Identity |
| --- | --- |
| Source base and previous Moira build's commit | `0726ecc157530c60ebc7fa9aa2c516c477da08e2` |
| Code and test diff from that base, SHA-256 | `4e20dda735c3c2079b2870d587c4638a67a25b19f2c532750390fd520b0fd47b` |
| Previous native extension, SHA-256 | `6076146561144f400b8ff9b32f7705353a3dbe6851d1c39c86bfb468821d01cc` |
| Native batch Release extension, SHA-256 | `053e33507ccfd0b6af79b6464180bede2ff446faa9cc31fc95e2fe040c13e9f0` |

## Batch timings

Each timing is the median of five warmed runs with alternating reader order.
Skyfield uses one shared vectorized TDB `Time` array with `.at()` for each
state target and `earth.at(t).observe(target)` for reception light time. Moira
passes the same epochs and targets to the native batch in one call. The previous
Moira run used native state evaluation once per epoch and the prior planetary
light-time solver. Timed results include construction of comparable output
arrays in km, km/s, and seconds. [Skyfield position API][skyfield]

State grids use 12 targets, including Earth and the Earth–Moon barycenter.
Light-time grids use the same 10 solar-system targets with Earth as observer.
DE433 light time uses Mercury and the Moon, whose routes contain the tested
handoffs. The dense grids use equally spaced epochs rounded to 1/8192 day.
DE432s spans JD(TDB) 2433266.5–2469806.5, and DE440s and DE442s span
2396754.5–2506350.5. DE441 and DE433 use two days on each side of each distinct
[genuine handoff][handoffs], with an equal number of epochs per window. The
96-epoch DE440s grid reuses the original geometric sample.

| Kernel | Workload | Epochs | Results | Previous Moira, ms | Native batch, ms | Skyfield, ms |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| DE432s | State | 16,384 | 196,608 | 838.452 | 23.641 | 81.446 |
| DE432s | Light time | 2,048 | 20,480 | 578.398 | 12.942 | 25.570 |
| DE440s | State | 96 | 1,152 | 7.868 | 4.803 | 1.368 |
| DE440s | State | 1,024 | 12,288 | 79.994 | 18.784 | 6.210 |
| DE440s | State | 16,384 | 196,608 | 1034.264 | 58.719 | 104.177 |
| DE440s | Light time | 2,048 | 20,480 | 608.347 | 34.526 | 35.231 |
| DE442s | State | 16,384 | 196,608 | 1013.078 | 45.318 | 91.517 |
| DE442s | Light time | 2,048 | 20,480 | 629.434 | 33.721 | 39.076 |
| DE441 | State | 16,384 | 196,608 | 818.496 | 14.740 | 82.082 |
| DE441 | Light time | 2,048 | 20,480 | 497.837 | 4.807 | 33.053 |
| DE433 | State | 16,384 | 196,608 | 587.499 | 15.533 | 88.111 |
| DE433 | Light time | 2,048 | 4,096 | 132.904 | 2.052 | 13.500 |

Skyfield led on the 96- and 1,024-epoch DE440s state grids. The DE440s
light-time medians differed by 0.705 ms on this machine.

## Accuracy at segment crossings

The untimed replay uses the original controlled and genuine handoff epochs.
CSPICE N0067 through SpiceyPy 8.0.2 supplies the J2000 state with `spkgeo` and
Earth-centered reception position and delay with `spkpos` using `CN`. A
crossing means the reference selected a different descriptor at reception and
emission. Moira and Skyfield use full DE441, while the Windows CSPICE build
uses the [verified six-day DE441 excerpt][handoffs] with SHA-256
`c3a7d212c1ef5c1e006ab8d714d68465db5f4a6885c507e404bcae3f68264591`.
All three readers use full DE433. [CSPICE position and correction definitions][spkpos]

| Case | Crossings | Moira max position error, mm | Skyfield max position error, mm |
| --- | ---: | ---: | ---: |
| DE441 genuine | 49 | 2.83549 | 6.11068 |
| DE433 genuine | 13 | 97.78919 | 202.00546 |
| DE440s controlled adjacent | 29 | 0.03072 | 1.01152 |
| DE442s controlled adjacent | 29 | 0.01666 | 1.07288 |
| Controlled overlap | 18 | 0 | 0.53312 |
| Covered emissions in the controlled gap fixture | 2 | 0 | 0.01666 |

Native results matched previous Moira positions and velocities on all
3,829 geometric states and matched both positions and delays on all 757
valid light-time samples, including the 140 crossings. Across that replay,
Moira's maximum geometric position residual against CSPICE was 0 m and its
maximum velocity residual was `1.468e-8 mm/s`. The largest Moira delay residual
was 0.158 ns, on DE433. These residuals describe agreement on the sampled JPL
kernel data.

Moira agreed with CSPICE on all 46 coverage probes. The 30 uncovered emission
samples included 24 before kernel coverage and six in a controlled descriptor
gap. A native batch containing an uncovered sample raised a coverage error.

## Local verification

The focused offline suite passed 171 tests and skipped two optional
jplephem comparisons. With the comparison libraries on the import path,
172 passed and one legacy coefficient-payload test failed on array shape.
The same failure reproduced with the previous native extension.

The local harness reads the saved controlled and genuine handoff datasets in
`tmp/spk-reader-comparison`. The full command produced the archived timings.
Adding `--quick` uses smaller timing grids and replays the full accuracy
corpus. That replay reproduced the archived residuals and coverage outcomes.

```powershell
$env:MOIRA_NO_DOWNLOAD = '1'
.\.venv\Scripts\python.exe -B tmp/spk-reader-comparison/compare_skyfield_batches.py --native-multi-epoch
```

[reader]: ../../moira/spk_reader.py
[results]: ../../tests/artifacts/benchmarks/spk_native_skyfield_batches_2026-11-10.json
[handoffs]: SPK_HANDOFF_VALIDATION_2026-11-09.md
[precedence]: https://naif.jpl.nasa.gov/pub/naif/toolkit_docs/C/req/spk.html#Data%20Precedence
[skyfield]: https://rhodesmill.org/skyfield/api-position.html
[spkpos]: https://naif.jpl.nasa.gov/pub/naif/toolkit_docs/C/cspice/spkpos_c.html
