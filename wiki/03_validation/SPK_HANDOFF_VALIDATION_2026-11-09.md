# Planetary SPK handoff validation, 2026-11-09

CSPICE N0067 via SpiceyPy 8.0.2 supplied the reference for geometric states
and Earth-centered reception light time at genuine DE441 and DE433 handoffs.
Skyfield 1.55 (using jplephem 2.24) and CALCEPH 5.0.0 provided cross-engine
comparisons. The residuals measure agreement on this corpus of JPL
coefficients and sampled epochs.
[NAIF data precedence][precedence] · [CSPICE light time][lt]

## Data and build

| Input | Size, bytes | SHA-256 |
| --- | ---: | --- |
| Installed DE441 | 3,307,878,400 | `9a824e6a8ce3d39f8a513b17278ff7b7ad226f964c76d2019b0a51d8808d6ff5` |
| JPL DE433 | 408,255,488 | `8dd1a8e17a44b3f4aca62def83867c7a7e2c7692c15cb9e34f19056037a888b3` |

Moira and Skyfield read the full DE441. Windows CSPICE returned
`SPICE(RECORDNOTFOUND)` on that file, and CALCEPH's full-file probe also
failed. They used a six-day excerpt centered on the 1969 handoff (SHA-256
`c3a7d212c1ef5c1e006ab8d714d68465db5f4a6885c507e404bcae3f68264591`).
The excerpt retains the original file order and handoff endpoints of all
28 descriptors. Each Type 2 record written with CSPICE `spkw02` was checked
against the source record, including midpoint, radius, and coefficients.
All four readers used the full DE433. [JPL planetary kernel archive][archive]
· [CSPICE Type 2 writer][writer]

The tested source is Moira 6.13.1 plus the SPK and light-time fixes and
regressions in this commit. Its base is
`2009c46ff9d85343f8686bd3ab7426d2b38bc694` and the code-and-test diff from
that base has SHA-256
`52abf62c9d475ed903b2ac143ef5aff4bd5ae109743fed769494bf96f7a26415`.
The run used CPython 3.14.8 and the rebuilt Windows x64 Release extension,
SHA-256 `6076146561144f400b8ff9b32f7705353a3dbe6851d1c39c86bfb468821d01cc`.

## Sample and method

| Kernel | Handoffs in TDB, with ET seconds past J2000 | Geometric states | Corrected positions | Crossings |
| --- | --- | ---: | ---: | ---: |
| DE441 | All 14 pairs at 1969-07-30 00:00:00, ET `-960120000` | 70 | 90 | 49 |
| DE433 | Earth-to-Moon at 2097-07-30 00:00:00, ET `3079252800`. Earth-to-Moon and SSB-to-Mercury at 2645-02-28 00:00:00, ET `20359252800` | 15 | 27 | 13 |

The DE441 raw pairs are `0 → 1…10`, `1 → 199`, `2 → 299`, `3 → 301` and
`3 → 399`. Corrected targets are the Sun (10), Moon (301), Mercury (199),
Venus (299) and the Mars through Pluto system barycenters (4–9). DE433 uses
`0 → 3 → 399 → 301` for the Moon and `0 → 199` for Mercury.

Geometric states use the same TDB Julian day and direct center/target pair
in J2000. Compare `SpkReader.position_and_velocity_tdb` with CSPICE `spkgeo`
after converting velocity to common units. Skyfield geometric samples
evaluate Moira's selected descriptor, so they corroborate interpolation.
Skyfield's corrected positions use its own `earth.at(t).observe(target)`
route. CALCEPH supplies geometric states to the harness's light-time solver.

Corrected positions use CSPICE `spkpos` with `CN`, observer `399`, and frame
`J2000`. The observer is at reception and the target is at emission.
The only correction is converged one-way Newtonian light time. Moira
retains the travel time as a separate offset from the reception TDB
Julian day and selects the last covering descriptor for each route leg.

For each handoff `b`, take geometric samples at `-10, -0.25, 0, +0.25, +10`
seconds relative to `b`. For each corrected target, find the reception ET
`r` of a photon emitted at `b`. Start with `r = b` and iterate
`r = b + |target(b) − earth(r)| / c` eight times in TDB seconds using
`c = 299792.458 km/s`. With `τ = r − b`, sample reception at
`b − max(2, τ/4)`, `b`, `b + τ/4`, `b + τ/2`, `r − 2`, `r − 0.125`,
`r + 0.125`, `r + 2` and `r + 250`. Convert `2451545 + ET / 86400` to TT
and back to TDB for the common binary64 reception coordinate. A crossing
means the CSPICE descriptor changes between reception ET and that ET
minus the returned light time.

## Results

These are maximum Euclidean differences from CSPICE.

| Measurement | Moira | Skyfield | CALCEPH |
| --- | ---: | ---: | ---: |
| DE441 geometric position, m | 0 | 0.0002384 | 0.001093 |
| DE441 geometric velocity, mm/s | 7.944e-9 | 1.005e-8 | 1.281e-8 |
| DE441 corrected position, m | 0.002835 | 0.006135 | 0.006135 |
| DE441 corrected position at crossings, m | 0.002835 | 0.006111 | 0.006134 |
| DE433 geometric position, m | 0 | 0.000007451 | 0.000003725 |
| DE433 geometric velocity, mm/s | 7.105e-9 | 7.944e-9 | 7.944e-9 |
| DE433 corrected position, m | 0.09779 | 0.20201 | 0.20201 |
| DE433 corrected position at crossings, m | 0.09779 | 0.20201 | 0.20201 |

Moira selected the CSPICE descriptor for each tested pair at the sampled
geometric and emission epochs. The DE441 run exercised `planet_at` and
`all_planets_at` with one target per call. The native planetary evaluator
served all 90 corrected samples, including 49 crossings. DE433 exercised
the reader and shared light-time solver with the DE433 center chains.

The controlled DE432s, DE440s and DE442s replay retained the same kernel
and fixture hashes as the precedence-only run. All 3,744 geometric
positions still agreed exactly. The maximum residual over 480 ordinary
light-time samples fell from 1.07068 m to 0.0192661 m. All 58 adjacent
crossings and 18 overlap crossings stayed native, with maximum residuals
of 0.00003072 m and 0 m respectively. Moira rejected 24 emissions before
kernel coverage and six emissions in the controlled gap. The controlled
comparison bands were 0.02 m for geometric position, 0.005 mm/s for
geometric velocity and 5 m for corrected position.

## Focused verification

With DE441 discoverable and the rebuilt extension loaded, the offline
suite passed 148 tests. Two optional `jplephem` parity checks were skipped.

```powershell
$env:MOIRA_NO_DOWNLOAD = '1'
$env:MOIRA_TEST_MODE = '1'
$env:MOIRA_STRICT_KNOWN_ISSUES = '1'
.\.venv\Scripts\python.exe -B -m pytest tests/unit/test_spk_reader.py tests/unit/test_planets_architecture_invariants.py tests/unit/test_de441_segment_boundaries.py tests/unit/test_planet_position_switches.py tests/unit/test_topocentric_multi_path_consistency.py tests/unit/test_kernel_pool_center_chaining.py tests/unit/test_native_import_resolution.py tests/unit/test_adversarial_native_daf_reader.py -m 'not external_network' -p no:cacheprovider
```

The local replay used `tmp/spk-reader-comparison/compare_precision.py`
for the controlled corpus and `tmp/spk-reader-comparison/real_handoffs.py`
for the genuine handoffs.

[archive]: https://ssd.jpl.nasa.gov/ftp/eph/planets/bsp/
[precedence]: https://naif.jpl.nasa.gov/pub/naif/toolkit_docs/C/req/spk.html#Data%20Precedence
[lt]: https://naif.jpl.nasa.gov/pub/naif/toolkit_docs/C/cspice/spkltc_c.html
[writer]: https://naif.jpl.nasa.gov/pub/naif/toolkit_docs/C/cspice/spkw02_c.html
