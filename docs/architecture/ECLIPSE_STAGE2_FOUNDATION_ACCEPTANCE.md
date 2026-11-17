# Eclipse Stage 2 foundation: acceptance record

**Status: supported-domain foundation checks passed; see limitations below.**
This record describes the bounded-state and root-isolation foundation in the current
isolated checkout. It does not accept Stage 3 or assert that Moira's live
eclipse searches, historical catalogs, event-wide paths, or widths are
complete. Existing uncommitted work is part of the candidate; this document
does not claim that it has been committed or released.

## Scope and supported evidence

| Component | Available result | Boundary of the claim |
|---|---|---|
| Interval arithmetic and roots | Exact rational intervals, outward conversion and elementary bounds; partition and opt-in interval Newton with budgets | Conclusions depend on the supplied function, continuity and derivative contracts. A tangent, exhausted budget or unavailable provider may remain unresolved. Neighboring closed cells can share a root. |
| DE441 type-2 states | Coefficient and derivative enclosures, descriptor/index checks and frozen-record evaluation | Unsupported types, readers, route or record seams fail closed. Source, native build and floating-point premises are explicit; copied-record evidence is not live mapped-kernel attestation or physical ephemeris error. |
| Time and light-time | Conditional forward clock bounds, split TT/TDB checks and per-iteration serving-delay residuals | Clock branches and source conditions have different support. An unknown branch remains unresolved. A residual at the delay used to evaluate a vector is not automatically the residual at the returned next delay, nor a fixed-point or physical error bound. |
| Lunar finite cone | `inspect_lunar_shadow_tt_interval` gives opt-in conditional bounds and an unresolved outcome with route, clock, norm and budget information | It describes represented binary64 TT inputs on a frozen type-2 snapshot, under declared numerical premises. It does not establish live-route or UT1 totality, continuous-time eclipse absence, physical accuracy, or a complete search. |
| Solar orientation | Conditional serving-axis, Earth-rotation, polar-motion, nutation, sidereal and selected Earth-fixed vector enclosures | Earth-fixed composition covers successful represented-input evaluations on the FW branch under stated assumptions. UT1/TT correspondence, live-route totality, event occurrence and event-wide paths are not certified. |

The API keeps its existing defaults: exhaustive clock-state checking is
opt-in and its shared budget is explicit. Exhausted budget, missing resources,
unsupported branches, unproved clock or geometry conditions, and an interval
touching the contact threshold must not become a negative-event finding.
Conditional results quantify the represented inputs and stated execution
policy only; they are not a claim about every real instant between floats.

## Gate controls

The following controls exercise the foundation; sampled DE441 agreement is
validation of those cases, not proof of an entire search domain.

| Gate area | Controls |
|---|---|
| Arithmetic, roots and extrema | `tests/unit/test_eclipse_interval.py`, `test_eclipse_interval_elementary.py`, `test_eclipse_interval_roots.py`, `test_eclipse_interval_newton.py` and `test_eclipse_extrema_controls.py`: constants, multiple and short roots, endpoint ownership, tangency, near miss, plateau, budgets and analytic derivative/extremum examples. |
| Type-2 records | `tests/unit/test_eclipse_spk_bounds.py`, `test_eclipse_native_spk_bounds.py`, `test_eclipse_spk_partition.py`, `test_eclipse_variable_spk_bounds.py` and `test_eclipse_spk_high_order_controls.py`: raw/independent recurrence, descriptor priority, exact endpoints and adjacent floats, including degree-48 Chebyshev controls. |
| Missing resources and emission seams | `tests/unit/test_eclipse_bounded_missing_and_emission_seam.py`: absent kernel and an actual DE441 retarded-Sun emission crossing a record; unsupported cases remain unresolved. |
| Clocks and model breakpoints | Clock, inverse, convergence and exhaustive-state tests under `tests/unit/test_eclipse_*clock*`, `test_eclipse_time_*` and `test_eclipse_canon_phase_window.py`, including the exact 2017 EOP/leap knot and NASA month and polynomial boundaries. |
| Lunar model and grazing control | `tests/integration/test_lunar_shadow_tt_interval.py` exercises conditional snapshot intervals. `tests/integration/test_eclipse_lunar_grazing_native_control.py` replays native lunation -40729 with a roughly 13.9-second contact pair at several scan steps. |
| Solar and Earth-fixed bounds | `tests/unit/test_eclipse_solar_serving.py`, `test_eclipse_wgs84_orientation.py`, `test_eclipse_polar_motion_bounds.py`, `test_eclipse_sidereal_bounds.py`, `test_eclipse_nutation_amplitudes.py` and `test_eclipse_earth_fixed_bounds.py`, subject to each test's stated inputs and premises. |

The -40729 native contact check is a **sampled convergence control**, not a
proof that the real event or its complete contacts were exhaustively found.
The static finite-cone model is a different policy from the native angular
model. A conditional outcome for one must not be described as an outcome for
the other or as a NASA-compatible determination.

## Verification and performance

An independent gate slice, run before the final exhaustive-budget integration,
passed **112 tests with 21 DE441 resource checks and no skips**. It covered the
high-order and extrema controls, missing kernel and emission seam, SPK
partition, NASA and EOP clock boundaries, and the native 13.9-second control.

After the budget/cache changes, the final broad run passed **1,355 tests with
513 DE441 resource checks, no failures, errors, or skips**, in 184.939 seconds.
It covered `tests/unit/test_eclipse_*.py` plus the lunar TT interval, native
grazing, global phase-ordering and coverage-edge integration tests. The JUnit
receipt is `work/phase2_complete_exact_tests.xml`, outside the repository.
The selected 504-file source fingerprint, covering `moira/**/*.py`, native
C/C++ sources and headers, and `CMakeLists.txt`, was
`c866a44d05f6974295faceeb6a27036a7c7098b0b08009ec79fe53daa4350c72`
after the run and matched the historical probe's before/after fingerprint.
This is not a full build-provenance, live-kernel, or runtime attestation.
Scoped Ruff, `git diff --check` and the docstring preflight for 73 changed
engine files also passed. These receipts describe the states and selection
actually tested; they do not attest later source edits.

Before the isolated-checkout commit, additional regression slices passed:
112 server, width-availability and ordering tests; 190 sampled solar
92-case tests; 69 lunar research and candidate tests; 109 hybrid, visibility,
swept-interior and IMCCE controls; and 44 catalog-runner tests. These slices
had no failures or skips. A separate 277-test native/SPK/catalog slice had
no failures and eight skips: two optional `jplephem` comparisons were
unavailable, and six type-3 cases were outside the selected native policy.
These checks preserve the model and sampling limits described above.

The broad test ran from the isolated checkout using its Python 3.14.8
environment, with `MOIRA_NO_DOWNLOAD=1`, `MOIRA_TEST_MODE=1`,
`MOIRA_STRICT_KNOWN_ISSUES=1`, `PYTHONDONTWRITEBYTECODE=1`, and `TEMP` and
`TMP` set to the workspace's `work/pip_build_tmp` directory. In the following
PowerShell form, replace `<work>` with the workspace's absolute `work` path:

```powershell
$files = @(Get-ChildItem tests\unit -Filter 'test_eclipse_*.py' | ForEach-Object { $_.FullName })
$extra = @('tests\integration\test_lunar_shadow_tt_interval.py',
           'tests\integration\test_eclipse_lunar_grazing_native_control.py',
           'tests\integration\test_eclipse_global_phase_ordering.py',
           'tests\integration\test_eclipse_de441_coverage_edge_contract.py')
.\.venv\Scripts\python.exe -B -m pytest @files @extra -q -ra -x -p no:cacheprovider --basetemp='<work>/phase2_complete_exact_tests' --junitxml='<work>/phase2_complete_exact_tests.xml'
```

An exploratory receipt at `work/stage2_tt_interval_benchmark_receipt.json`
records one Windows/Python 3.14.8 process using DE441 SHA-256
`9a824e6a8ce3d39f8a513b17278ff7b7ad226f964c76d2019b0a51d8808d6ff5`
and native binary SHA-256
`14312ce7e37fe89eea4947be9a0ba974b2cdea49abc9e74c78eb887c75f4f6dd`.
Its modern conditional negative/positive TT boxes took approximately
0.27–0.30 s warm per call; its historical control was unresolved with the
default exhaustive budget of zero. That receipt predates the final
budget/cache work, measures a small sample on one machine with a warm OS
cache, and is neither a catalog-throughput forecast nor a physical accuracy
claim. The receipt is outside the repository and is not automatically part of
a commit.

A subsequent exploratory run at TT `1248813.457560655`, using the static
finite-cone policy and Earth-radius scale 1.01, used a 3,000,000-state budget,
checked 1,883,904 normalized states with seven cache hits in 7.947 s, and
returned the conditional margin interval approximately [-0.6472013,
-0.6153957] km. The reproducible script is
`scripts/eclipse_catalog/stage2_historical_clock_probe.py`; the recorded
receipt `work/stage2_historical_clock_probe_receipt_20261117.json` is outside
the repository and is not automatically part of a commit. A further run of
the repository script reported the same bounds and counts in 12.096 s under
concurrent load. A separate
independent run with a 2,000,000-state budget reported the same state and
cache counts and bounds in 7.843 s. These results apply to the tested source
states and stated frozen-record, source and floating-point premises; they are
not the native angular 13.9-second result, a continuous-time exclusion, or
proof of a physical eclipse absence. The selected-source fingerprint matches
the fingerprint recorded after the final broad test run; the probe is still
conditional on its stated execution premises.

## Acceptance boundary

The Stage 2 implementation and tests above support the explicitly described
conditional domains. They do not establish unrestricted coverage, physical
accuracy or a universal runtime/build attestation. Any unavailable or
inconclusive domain remains unresolved. Stage 3 owns continuous/event-wide
phase coverage and solar hybrid classification; later stages own complete
topology, event-wide boundaries, geographic widths, API completion and fresh
catalog regeneration. This record does not promote those later claims.
