# Precession and SPK precision repair — 2026-10-27

Both authorized numerical repairs are implemented and the native extension is
rebuilt. Scoped publication uses an isolated checkout based on origin/main
f747c9e680a4dd872f75de461c0979d33c2f6fd1 (Moira 6.10.2), preserving its independent
astrocartography repair. The canonical checkout remains at
ffa60057388b39a9aae4383a7a5ea0aea97667c7 with all pending work preserved. No release,
dependency change, kernel-default change, or generated nested-wiki publication is
part of this repair.

## Correct coefficient and governing definition

Moira's bias-inclusive Fukushima–Williams gamma_bar now uses **10.556378 arcsec
per Julian century** in Python precession, native precession, and interval event
frames. The constant remains -0.052928 arcsec. This matches IAU 2006/P03 as
implemented by [ERFA pfw06](https://raw.githubusercontent.com/liberfa/erfa/1a8044cde5b7763295d472a6443387239127c6c8/src/pfw06.c#L85).
The complete four-angle polynomials are checked against ERFA across the closed
modern branch, including +/-50 Julian centuries, and the existing independent
official SOFA C ECM06 fixture now agrees to floating point roundoff.

**10.556403 is not globally superseded.** It remains correct for the precession-only
gamma in [ERFA p06e](https://raw.githubusercontent.com/liberfa/erfa/1a8044cde5b7763295d472a6443387239127c6c8/src/p06e.c#L244).
The repaired defect mixed that definition's linear coefficient into gamma_bar.
The live ERFA master source was checked and pinned to 1a8044cde5b7763295d472a6443387239127c6c8; original
source copies and SHA256 receipts are in the scratch authority directory.

The [IAU resolution list](https://www.iau.org/Iau/Publications/List-of-Resolutions.aspx)
and [current 2026 IERS product metadata](https://datacenter.iers.org/versionMetadata.php?filename=mt%2Feopc04_14_IAU2000.26.txt)
retain IAU 2006/2000A. New IAU 2006J2/2000A_R25 work is described as proposed for
conventions revision in the [IAU working-group report](https://www.iau.org/common/Uploaded%20files/WG-Comm-A2_CIERT_Annual%20Report%202025.pdf).
This repair implements the correct adopted model rather than mixing proposed
model terms into the current frame contract.

## SPK repair

ET remains binary64 TDB seconds since J2000. A TwoDiff compensated subtraction
carries the low part of ET-INIT into record-local time instead of losing up to
about a microsecond in a long segment. Normalization is centered on the record
midpoint: s=(offset-radius)/radius. This is algebraically the
[NAIF Chebyshev normalization](https://naif.jpl.nasa.gov/pub/naif/toolkit_docs/C/cspice/chbval_c.html).

The native SPK type-2/type-3 owner, legacy native Chebyshev evaluator, planetary
Python fallback and small-body Python time fallback use the repaired reduction.
Record selection, split-JD handling, descriptor coverage, final endpoint ownership,
velocity conventions, and coefficient ordering retain their existing contracts.
The shared native PCK path is covered by the focused PCK tests.

## Controlled comparison

The original experiment remains frozen at C:\dev\outputs\xalen-moira-comparison-20261027-07d766c6.
New outputs are at C:\dev\outputs\moira-precession-spk-repair-20261027-0257985e\comparison-after. The identical inputs, kernel, compiled XALEN runner,
XALEN commit and every numeric XALEN output were verified; 31 original files retain
their SHA256 hashes.
The Rust runner's segment HashMap has randomized iteration order, so numeric
outputs are compared after sorting segments by target/center identity.
The same experiment was repeated from the isolated publication checkout, with
identical repaired maxima, at
C:\dev\outputs\moira-precession-spk-publish-20261027-860cf134\comparison-publish.

- DE440s SHA256: c1c7feeab882263fc493a9d5a5b2ddd71b54826cdf65d8d17a76126b260a49f2.
- XALEN commit: 420b819659ac081d99d07567129ac117e9f2baac.
- 528 TT epochs (16 anchors and 512 seeded random epochs), 1850–2150.
- 7,392 raw SPK target/center samples; 5,280 major-body samples.
- Raw comparison uses identical binary64 TDB and ICRF/J2000 coordinates.
- Apparent comparison is geocentric, common reception TDB and TT frame epoch,
  converged light time, pure Lorentz aberration, no solar-potential term,
  gravitational deflection, topocentric correction, or refraction; common
  IAU 2006 mean ecliptic/equinox of date. XALEN's native nutation is undone.
- Independent comparators: CSPICE N0067 (SpiceyPy 8.0.2) and ERFA 2.0.1.5.

| Maximum residual | Before | Repaired |
| --- | ---: | ---: |
| Raw Moira SPK vs CSPICE, metres | 0.0557495658825 | 0 |
| Frame matrix entry vs ERFA | 1.81678685984e-10 | 3.88578058619e-16 |
| Frame-axis angle vs ERFA, arcsec | 3.74989765716e-05 | 8.01512259138e-11 |

Zero raw residual means identical returned coordinates for these 7,392 samples,
not a claim of zero ephemeris uncertainty or universal bitwise parity.
Composed geocentric routes can still differ at subtraction roundoff.

| Apparent common-frame maximum, arcsec | Moira before | Moira repaired | XALEN unchanged |
| --- | ---: | ---: | ---: |
| Sun | 3.83244076e-05 | 1.81769612e-06 | 0.415563773 |
| Moon | 0.000350255178 | 0.000325854623 | 0.000578430033 |
| Mercury | 3.99132408e-05 | 4.44488576e-06 | 0.450932168 |
| Venus | 3.87272906e-05 | 3.33919162e-06 | 0.601626031 |
| Mars | 3.69776983e-05 | 1.33461865e-06 | 0.484802944 |
| Jupiter | 3.74120667e-05 | 5.20540102e-07 | 0.371686223 |
| Saturn | 3.75359066e-05 | 3.10108834e-07 | 0.365285433 |
| Uranus | 3.70169433e-05 | 2.04712045e-07 | 0.357702176 |
| Neptune | 3.69395013e-05 | 1.4833468e-07 | 0.35605161 |
| Pluto | 3.73289499e-05 | 1.48914613e-07 | 0.361688466 |

The lunar apparent residual remains about 0.326 milliarcseconds; these two repairs
do not claim to remove the remaining apparent/light-time pipeline residuals.

## Build and focused verification

Native build uses the project venv (CPython 3.14.8), CMake, pybind11, and MSVC
14.50.35717, Release x64. Build scratch paths are under the repair output directory.
The rebuilt extension is loaded from C:\dev\moira\moira\_moira_native.cp314-win_amd64.pyd.
The publication checkout uses the identical rebuilt binary; all native build
sources were checked for identical content after Git newline normalization.

- Native SHA256 before: b62628d5f38856e71c0c4c6e92fca80711f74e3f14171bcc1023eb2f002c9153.
- Native SHA256 after: 19c07caab59801a339143f3b023a86cb2cb83a9ba57fa054caafc96fad3299d4.
- Focused suite: **375 passed, 8 skipped, 0 failures, 0 errors** in 15 files.
- Six skipped parameter combinations explicitly exclude Python type-3 velocity
  policy; two existing optional jplephem parity checks skip because jplephem is
  not installed. Independent CSPICE/ERFA checks ran successfully.
- New regressions cover exact rational synthetic type-2/type-3 positions and
  rates, long segment timing, native handle/standalone/legacy paths, isolated
  Python time fallbacks, split JDs, interior boundary ownership, closed final
  endpoints, and rejection outside descriptor coverage.
- Frame regressions cover Python, interval polynomial enclosures, and rebuilt
  native ecliptic longitude with nutation held fixed against ERFA precession.
- Existing tests cover native parity/import resolution, ERFA validation, orbital
  and planetary frames, adversarial DAF/runtime/PCK, real lunar PCK, and serving
  event enclosures. Test-time network access was disabled.
- The existing same-matrix invariant uses an exact binary scale factor (eight)
  instead of seven, avoiding an invalid floating point distributivity assumption;
  its 2e-15 tolerance is unchanged. No scientific fixture or golden was updated.
- Touched tests pass Ruff; engine lint retains exactly three pre-existing findings
  (two E402, one E731), independently reproduced on preserved original sources.
- Engine docstring preflight passes for all four touched Python files; scoped
  whitespace checks pass.

The isolated small-body fallback timing test supplies the canonical decoded
coefficient tensor. It does not certify that wrapper's unrelated forced-fallback
payload loader: the pre-existing six-argument payload call is incompatible with
the current five-argument binding. That separate issue was left unchanged.

Unrelated tracked/untracked file bytes, both Git indexes, complete nested wiki
state, and both HEADs were verified against the pre-edit preservation snapshot.
The native binary before repair and all original owned source files are retained
in the scratch preservation directory. Full test logs, JUnit, build logs, exact
comparison rows, and machine-readable verification are available alongside it.

## Expanded validation and differential controls

The expanded run used the project venv, denied external networking for offline
tests, enabled strict known-issue handling, and fixed PYTHONHASHSEED=0 for xdist
collection consistency. Selection receipts assert that both Python and native
imports resolve inside the intended candidate or control checkout. It covered
831 files and 25,870 offline cases:

| Initial offline run | Passed | Failed | Setup errors | Skipped |
| --- | ---: | ---: | ---: | ---: |
| Parallel non-serial corpus | 25,675 | 107 | 20 | 65 |
| Isolated serial corpus | 3 | 0 | 0 | 0 |

All 127 failed/error nodes were replayed on the unrepaired f747c9e control.
That control reproduced 49 failures and 20 setup errors; 58 cases passed there
and required investigation. Rebuilding the control extension from its own
unrepaired sources, with the same venv/compiler, also passed all 58, ruling out
an old-binary build mismatch as their cause.

All **58 differential failures now pass**. Their resolutions were validation
corrections, with no additional production numerical changes:

| Cases | Cause and reviewed correction |
| ---: | --- |
| 24 star positions | Historical coordinates contain the mixed gamma definition. Preserve their literal values and transport them through an independent ERFA legacy-to-corrected frame rotation. Propagation, nutation and the original 1e-9 degree tolerance are held fixed. All 28 date/star anchors agree within 2.85e-14 degrees. |
| 32 D60 REST cases | The independent varga outputs were frozen for historical planetary parent longitudes. Transport each external anchor to the returned parent using the exact slope 60 within the same half-degree partition; assert partition identity and response/provenance agreement. The independent data and 3.637978807091713e-12 degree tolerance are unchanged. The 224 parent/body combinations agree within 1.14e-13 degrees. |
| 1 Fortune witness | Replace an old ephemeris-specific literal with the defining day-chart arc Ascendant + Moon - Sun at the same inception. Keep the 1e-10 degree tolerance, Aquarius sign and Saturn ruler assertions. |
| 1 shallow penumbral minimum | Two independently centred argmins differ by 45.9 ms. A 161-sample, +/-2 second quadratic study finds 3.07e-11 Earth radii of objective noise, corresponding to about 70 ms of minimum-time conditioning. Replace the unsupported 43.2 ms equality with same-contact-interval membership and strictly smaller gamma than both one-second shoulders at each minimum. Keep the event-at-its-own-epoch magnitude assertions at 1e-12. This does not claim a more accurate time solver. |

The three star/D60/Dorotheus files pass all **324 tests**. The eclipse helper and
limiting-regression files pass all **83 tests**. An exact-node receipt binds all
58 differential cases to those passing reruns. No oracle artifact, golden data,
catalogue entry, external observation, or numerical tolerance was refreshed.
The minimum-time equality was explicitly replaced for the conditioning reason
above; it is not counted as a retained timing tolerance.

The remaining **69 offline failures/errors reproduce before the repair**:
26 daily-Panchanga synthetic-input cases; 20 light-box schema/register setup
errors; 5 stale generated-inventory/fingerprint cases; 7 house tests without an
active reader; 4 harness-policy tests; 3 historical Vimshottari witnesses; and
one each in asteroid element admission, expensive-response caching, server time
adapters, and the unrelated astrocartography geodetic witness. These were not
suppressed or modified. The broad suite is therefore not described as green.

The two long Muhurta API cases passed in the full run. Fresh two-case controls
also passed: 1,080.63 seconds unrepaired and 979.85 seconds repaired. These are
diagnostic timings, not a benchmark or a performance claim.

The final 18-file native/frame/SPK and remote astrocartography regression slice
passes **438 tests**, with the same eight documented skips and no failures or
errors. All eight touched test files pass Ruff; the four touched Python engine
files pass the engine docstring preflight. No production source changed during
the expanded validation corrections.

## External comparisons and LOLA resource status

The external corpus selected 397 cases: 390 non-serial and seven serial. Its
initial non-serial result was 360 passed, 29 failed and one skipped. All 29
failures also reproduced on the unrepaired control. Nineteen exposed a stale
wide-vector oracle input: Moira's reader accepts TT and internally converts it
to TDB, while the test sent the unconverted numeric TT value to Horizons as
TDB. The test now sends the same converted TDB instant to Horizons. **All 80
wide-vector cases pass** the unchanged 10 metre and 0.001 arcsecond gates.

The other ten non-serial failures concern missing version-2 STAC mappings,
changed live JPL/SBDB reference data, and two existing occultation/graze
discrepancies. The single skipped external case requires a custom Toutatis BSP
that is absent in both checkouts.

The serial run has four passes and three failures. All three exact failing
nodes reproduce on the freshly rebuilt unrepaired baseline: both Dunham sites
fail a frozen profile position-angle characterization, and the query-width
oracle lacks the cached cell-center-v2 mapping for (-120, 45). For Dunham1,
the baseline start angle is 210.79449628166353 degrees, the repaired angle is
210.79449623898816 degrees, and the existing fixture is 210.79452290667612
degrees (1e-12 degree gate). Thus the frozen-model mismatch already exists
before these repairs. Neither model fixture nor observed timing data was
changed. These tests fail before their later contact-chronology comparisons;
they do not establish that the full IOTA contact model currently passes.
The serial passes cover frozen authority-document bytes, NOAA height checks,
and the two LSK/time-admission cases.

After the matched-time vector correction, **13 existing external failures and
one resource-dependent skip remain**. Every remaining failing case has an
unrepaired baseline failure receipt; none is described as a newly introduced
repair regression.

The LOLA resources were not deleted: the persistent cache contains 80 readable
LAZ files (12,218,773,011 bytes). All 16 assets pinned by the two-site IOTA model
match their exact fixture byte lengths and SHA256 hashes. Missing
cell-center-v2 STAC lookup entries are a separate metadata-coverage issue;
legacy corner-query mappings were not silently relabelled, and no LOLA files
were restored or replaced.

Expanded evidence is under
C:\dev\outputs\moira-precession-spk-publish-20261027-860cf134, including
broad-parallel-hash0-analysis.json, baseline-offline-partial-analysis.json,
baseline-rebuilt-differences-analysis.json, offline-resolution-receipt.json,
star-frame-anchor-study.json, d60-parent-input-study.json,
eclipse-conditioning-samples.json, matched-wide-vectors-junit.xml,
live-serial-analysis.json, baseline-live-serial-analysis.json,
publication-preflight.json, and lola-resource-audit.json. The publication checkout
is isolated so that committing these scoped repairs does not capture or alter
the canonical checkout's pending horary work, Git index, or dirty nested wiki.
