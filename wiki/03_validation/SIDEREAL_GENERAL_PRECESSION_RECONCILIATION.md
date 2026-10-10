# Sidereal general-precession reconciliation

**Date:** 6 October 2026. **Scope:** the PAC 1948 SE solar-ingress residual
identified during VED-023 admission and the shared scalar that caused it.

## Finding and correction

The initial lunar-month comparison found a solar ingress 64.4768 seconds
later than PAC's printed 15 June 2026, 12:53 IST. The event solver correctly
bracketed its own longitude boundary, but the shared ayanamsa precession
scalar was the wrong astronomical quantity.

`general_precession_in_longitude(jd_tt)` used the Fukushima-Williams
rotation angle `psib`, including its -0.041775 arcsecond frame-bias term.
The caller adds this scalar to a stored J2000 mean ayanamsa reference. That
operation requires accumulated **general precession in longitude, `p_A`**,
which is zero at J2000. The rotation matrix needs the distinct FW angles.

The authority is the P03/IAU 2006 formulation, independently evaluated with
[SOFA-derived ERFA `eraP06e`, output `pa`](https://github.com/liberfa/erfa/blob/v2.0.1/src/p06e.c).
It explicitly distinguishes general precession from FW rotation angles and
notes the published fifth-order sign misprint. In arcseconds, for TT Julian
centuries `T` from J2000:

```
p_A = 5028.796195 T + 1.1054348 T² + 0.00007964 T³
      - 0.000023857 T⁴ - 0.0000000383 T⁵
```

Moira now evaluates this scalar in degrees. At the published June instant,
the previous scalar exceeds `p_A` by **2.551926848 arcseconds**. Before the
correction, the sidereal Sun was **2.564347555 arcseconds** short of 60°.
The scalar error therefore accounts for the discrepancy to about 0.01242
arcseconds, consistent with the remaining fraction of a second in the
comparison to a rounded printed minute.

This is a correction of the implemented astronomical object. No ayanamsa
reference constant was fitted to an ingress. UT1-to-TT conversion, DE441
positions, apparent geocentric longitude, nutation, mean/true choices and
event boundary ownership retain their existing contracts. The named Lahiri
reference is still 23.857092317461543° at J2000 mean; the 1956 historical
origin does not constitute an independently imposed exact apparent epoch
constraint in this implementation.

## Sources and finite comparison corpus

The institutional source is
[IMD/PAC's English 2026–27 archive](https://packolkata.imd.gov.in/download/EnglishRP2627.zip),
retrieved 6 October 2026. PDF `RP 1948 SE Final.pdf` SHA256:

```
a8816abe4fae7fc0f0e4349a3d91eef00cfc0044a5f050b1b3bfe826847f9eaa
```

Printed 158 / PDF 178 contains 13 Sun ingress rows. Every row was
transcribed and checked against the rendered page, including the following
year's second Mesha ingress. Printed vi–vii distinguishes variable ayanamsa
nirayana ingresses from the fixed-23°15′ saura calendar; only the former is
the comparison object. Printed vi states the geocentric event times can be
converted from IST to UT by subtracting 5h30m. Tests use timezone-aware IST
instants and canonical UTC-to-UT1 conversion rather than passing TT to a
UT1 evaluator.

The [versioned transcription](../../tests/fixtures/pac_1948_solar_ingresses.json)
records the publisher, checksum, page, precision, time conversion, event
semantics and original **60-second acceptance limit**. No threshold was
relaxed after the failed comparison. The table is printed to minutes and
does not establish subsecond external accuracy.

Additional angular corroboration: at 00:00 UTC on 22 May and 22 June 2026,
corrected true Lahiri values are 24°13′39.063″ and 24°13′44.540″. These round
to PAC's month-header values 24°13′39″ and 24°13′45″, printed 18 and 26 /
PDF 38 and 46. Their headings specify a date rather than a precise epoch;
this corroboration is not a separate subsecond or subarcsecond oracle.

## Measured event results

The following reproducible measurements use installed DE441, apparent
geocentric ecliptic-of-date Sun, Lahiri true mode, UT1 event JDs, and the
default 0.1-second lunar-month bracket. Residuals are **Moira minus the
published instant**, in seconds. Sankranti is a separate existing public
event assembly with its own angular solver, sharing the corrected scalar.

| Published IST | Lunar month | Sankranti |
|---|---:|---:|
| 2026-04-14 09:33 | -21.176 | -21.259 |
| 2026-05-15 06:22 | +1.978 | +1.978 |
| 2026-06-15 12:53 | +0.330 | +0.330 |
| 2026-07-16 23:39 | +22.577 | +22.577 |
| 2026-08-17 07:59 | -14.420 | -14.502 |
| 2026-09-17 07:53 | -2.472 | -2.472 |
| 2026-10-17 19:52 | -18.210 | -18.292 |
| 2026-11-16 19:43 | +12.524 | +12.524 |
| 2026-12-16 10:25 | +2.307 | +2.307 |
| 2027-01-14 21:10 | +25.296 | +25.214 |
| 2027-02-13 10:09 | +4.697 | +4.614 |
| 2027-03-15 07:00 | +5.603 | +5.603 |
| 2027-04-14 15:28 | +22.824 | +22.742 |

All 13 pass the original one-minute institutional comparison. The maximum
absolute residual is **25.296 seconds**. The solvers differ by at most
0.0824 seconds, within their combined bracket/resolution allowance of
0.2 seconds; this latter check is internal consistency, not independent
astronomical authority. Entered-side endpoints from different scan brackets
can differ within the configured tolerance.

## Verification and consequences

[Independent scalar checks](../../tests/integration/test_erfa_validation.py)
compare against installed PyERFA 2.0.1.5 / ERFA 2.0.1 at 16 TT epochs,
including J2000, the 1956 origin, the June ingress, BCE/modern samples and
both ends of the ±50-century polynomial interval. All 16 failed before the
fix and pass after it at the existing **0.001-arcsecond** threshold. This
proves the quantity independently of PAC solar timing or a secondary
astrology engine. ERFA remains a development oracle; the runtime polynomial
requires no new dependency.

[Lunar-month integration checks](../../tests/integration/test_lunar_month.py)
exercise all 13 institutional rows through both existing event paths,
retaining exact month identities, conjunction comparisons, root-side
witnesses and explicit unavailable exceptional Purnimanta results.
[REST checks](../../tests/server/test_server_lunar_month.py) verify the
formerly failing June ingress through the typed HTTP response as well.

Reproduction, with installed resources and the project's Python 3.14.3
runtime (Moira 6.9.9):

```powershell
$env:MOIRA_NO_DOWNLOAD = "1"
$env:MOIRA_STRICT_KNOWN_ISSUES = "1"
.\.venv\Scripts\python.exe -m pytest tests/integration/test_erfa_validation.py -k general_precession -q
.\.venv\Scripts\python.exe scripts/reconcile_pac_solar_ingresses.py
```

The [offline measurement script](../../scripts/reconcile_pac_solar_ingresses.py)
emits the source receipt, resolved installed kernel, policy, UT1 instants,
complete event brackets and residuals as JSON; it exits unsuccessfully if
the authority or internal-consistency checks fail. The installed resource
for these measurements was `C:\Users\nilad\.moira\kernels\de441.bsp`,
read by the required native SPK backend.

The correction affects every polynomial ayanamsa path, including explicit
user-defined anchors and polynomial star fallbacks. Live true-star anchors
remain separately evaluated. Derived sidereal engine and REST values receive
the same correction through their existing calls. Historical changes can be
larger than the modern 2.55-arcsecond example; this is not a tolerance-preserving
refit of older outputs. The coordinate matrix and its admitted native
counterpart use their own FW angles and receive no numerical modification.

The scalar polynomial continues its existing extrapolation outside ±50
centuries, which is a disclosed model limitation. The wider Vondrak matrix
validity does not certify this scalar. This reconciliation closes the named
PAC solar-ingress discrepancy; exceptional Purnimanta/Kshaya regional
mapping and source-owned festival rules remain open in VED-023/024.

The selected broader command was:

```powershell
.\.venv\Scripts\python.exe -m pytest tests/integration/test_lunar_month.py tests/integration/test_erfa_validation.py tests/integration/test_sidereal_external_reference.py tests/unit/test_sidereal.py tests/unit/test_sidereal_nakshatra_boundaries.py tests/unit/test_physics_layer.py tests/unit/test_panchanga.py tests/unit/test_daily_panchanga.py tests/integration/test_daily_panchanga.py tests/unit/test_lunar_month.py tests/server/test_server_lunar_month.py tests/server/test_server_daily_panchanga.py tests/server/test_server_panchanga_routes.py tests/server/test_server_panchanga_service.py tests/server/test_server_sidereal_routes.py tests/server/test_server_sidereal_context.py tests/test_native_sidereal_phase1.py -q --tb=short
```

That first run covered **901 cases: 900 passed and one failed**. The failure
was `test_pbt_true_node_common_frame_intersection`, whose witness applied
`apply_frame_bias` before the already bias-inclusive precession matrix. An
isolated replay at UT1 JD 2400000 using the original HEAD precession source
also failed. Removing that extra bias application repairs the witness;
both strict `1e-12` normalized plane-intersection assertions remain. No
node runtime, coordinate matrix or native implementation was changed. The
original command was not retrospectively classified as a clean run.

The affected/new follow-up commands were:

```powershell
.\.venv\Scripts\python.exe -m pytest tests/unit/test_physics_layer.py::test_pbt_true_node_common_frame_intersection -q --tb=short --junitxml=tmp/pac-node-witness.xml
.\.venv\Scripts\python.exe -m pytest tests/server/test_server_lunar_month.py::test_http_mithuna_ingress_passes_original_pac_minute_gate tests/unit/test_vedic_facade.py tests/unit/test_vedic_surface_completeness.py -q --tb=short --junitxml=tmp/pac-reconciliation-followup.xml
```

These passed **1/1** and **22/22**, with zero failures or skips. Across the
broader run and corrected/new follow-ups, **923 distinct selected cases**
have passed their latest execution. The 16 scalar checks and an additional
86-case nakshatra-boundary rerun are already included in that coverage, not
added again to its count. The broader harness admitted 78 planetary-resource
receipts, all DE441, with zero skips or resource failures; the follow-ups
reported 3 and 4 receipts respectively. External network access remained
disabled; the server cases used explicitly marked loopback.

Scoped Ruff checks passed for the measurement script and lunar-month
integration/server files. A wider lint check also reported the pre-existing
`E741` single-letter variable at `test_erfa_validation.py:211`, outside the
changed lines; it was left untouched and is not reported as a clean lint
run. `git diff --check` passed. `tests/KNOWN_ISSUES.yml` stayed empty and
strict expiry checking remained enabled. No whole-suite, universal calendar,
or historical regional-rule certification is claimed.
