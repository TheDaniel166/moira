# D60 broader computational validation

Date: 7 October 2026. Owner: Moira engine, VED-003. **Outcome: broader
computational validation of `pvr_textbook_linear` is complete for the declared
mapping and interfaces.** Classical continuous-degree attribution remains
unestablished. These are separate acceptance questions.

The [source standard](../02_standards/D60_SOURCE_ADMISSION_STANDARD.md) governs
the forward natal-sign sequence, proportional within-part degree, half-open
endpoints and separate selected-edition deity names. The [earlier receipt](D60_FULL_POSITION_VALIDATION_2026-10-07.md)
and [literature adjudication](../06_roadmap/D60_EVIDENCE_ADJUDICATION_2026-10-07.md)
retain their historical scope. This pass adds executed external software
corroboration, reproducible numerical evidence and direct interface comparisons.

## Independent implementation evidence

| Comparator | Pinned identity | Actual execution and limits |
| --- | --- | --- |
| [PyJHora D60 source](https://github.com/naturalstupid/PyJHora/blob/48e57d29b47a3143519910a24866758116467485/src/jhora/horoscope/chart/charts.py) | Commit `48e57d29b47a3143519910a24866758116467485`, 6 August 2026; commit identifies V4.9.3. `charts.py` SHA-256 `c36c214e59c6a095438e67dacc29c7622dc8917ec25c723389c42655035ca86b`. | Execute unchanged `shashtyamsa_chart` function AST and selected constant/enum AST, with **explicit method 1**, in an isolated Python child. It returns full sign/degree pairs. No Moira or Swiss import occurs in this oracle process. This is not P.V.R. Rao's closed-source Jagannatha Hora, nor its current recommendation. The software's method label does not establish classical attribution. |
| [Maitreya D60 source](https://github.com/martin-pe/maitreya8/blob/dc468ded92798638f36a318838fc34eaf8623640/src/jyotish/Varga.cpp) | Commit `dc468ded92798638f36a318838fc34eaf8623640`, 6 March 2026. `Varga.cpp` SHA-256 `f081e3321e8051ddaffe709c5e558151a71b29721b64e335b222de8cb328ee95`. | Compile its exact D60 switch branch, sign projection and circular helpers as C++, using installed MSVC 14.50.35717, `/fp:precise /Od`. The harness represents `Rasi` by its integer index. Record the original returned sign and instrument its reduced intermediate longitude. **The intermediate is not a public Maitreya full-position product.** This is source-fragment execution, not a complete application build. |

Neither computation was rewritten in Python to imitate outputs. No external
implementation enters Moira runtime. `scripts/d60_cross_engine_sources.json`
pins selected source URLs, file hashes and repository license files.
`scripts/validate_d60_cross_engine.py` acquires and executes them in an explicit
private workspace. The repository contains Moira-owned orchestration and
numerical outputs; external source and binaries remain private. PyJHora's
repository includes AGPLv3 licensing and Maitreya GPLv2-or-later licensing;
their implementation text is not vendored into Moira.

`tests/artifacts/oracle/d60_cross_engine_2026-10-07.json` is **secondary
cross-engine evidence**, not primary classical or astronomical authority.
Refresh is explicit: reproduce pinned sources, inspect every disagreement,
then review an intentional fixture change. Failed comparisons preserve
diagnostics and prevent refresh. A new pin, tolerance or interpretation needs
renewed evidence adjudication; fixtures are not adjusted to fit an implementation.

## Corpus, precision and results

| Cohort | Inputs | PyJHora disagreements | Maitreya disagreements |
| --- | ---: | ---: | ---: |
| Every half-degree segment, at offsets 0.125, 0.25 and 0.375 degrees | 2,160 | 0 | 0 |
| Every segment start, exact and adjacent representable floats on both sides, including zodiac wrap | 2,160 | 0 | 0 |
| Uniform binary64 longitudes, fixed random seed 600017 | 20,000 | 0 | 0 |
| Seven classical planets, eight UTC dates from 1800 through 2400, Lahiri and Raman frames | 112 | 0 | 0 |
| **Total** | **24,432** | **0** | **0** |

Every input also agrees with independent `Fraction` evaluation of the
conditioned binary64 input: **zero Moira/rational disagreements**. The sign
and segment use rational division; proportional degree is evaluated exactly
before binary64 conversion. Moira retains mapped-longitude containment at
excluded upper edges. Sign agreement is exact; there is no tolerated sign
error or epsilon snap region.

Before comparison, the external numeric budget was declared as
`8 * ulp(2160.0) = 3.637978807091713e-12` degrees, based on maximum
intermediate arithmetic scale. This is a new secondary-comparator budget,
not a widened runtime, source-minute, existing rational or golden tolerance.
Maximum observed degree residuals: `1.1368683772161603e-13` degrees for
PyJHora, `2.2737367544323206e-13` for Maitreya. All exactly representable
interior samples agree exactly. No boundary mismatch was discarded.
These are floating-point mapping residuals, not astronomical accuracy claims.

The planetary D1 values originate from **Moira's installed DE441 reader**.
Both comparators independently map those exact sidereal inputs. The sixteen
date/frame charts cover all twelve natal signs and both parities. This proves
conditioned D1-to-D60 computation and transport, not independent ephemeris,
ayanamsa, birth-time or predictive accuracy. Datetime, frame and body are
recorded without inferring a publication's hidden seconds or rounding rule.

The offline fixture retains **4,552 cases**: all 4,320 deterministic interior
and boundary inputs, the first 120 seeded samples (selected by order, not
residual), and every planetary input. The full 24,432-input capture, raw
outputs, build receipt and disagreement ledger remain under
`C:\dev\outputs\vedic-d60-cross-engine-2026-10-07`.

## Interface and regression verification

`tests/unit/test_d60_cross_engine.py` compares engine positions directly with
both frozen implementations, grouped by natal sign and cohort. It checks
named/Shodashvarga facade outputs and the D60 sign used by Vimshopaka in both
D60-bearing groups. This does not independently validate the entire strength
doctrine from position witnesses.

`tests/server/test_d60_cross_engine.py` compares all seven full-point request
shapes with external expected coordinates over twelve natal signs; tests
120-result named/Shodashvarga batches; reproduces all sixteen real-reader
chart batches against frozen planetary inputs/outputs; and checks both
strength groups' transported D60 signs. Expected D60 coordinates come from
external captures, not another call to Moira.

Environment: `C:\dev\moira`, `main`, starting HEAD
`67b66de14cde0447730b0c9b57e5e14c1edd9935`, version 6.9.9; project `.venv`,
Python 3.14.3. Planetary resource resolved through its owning path module to
`C:\Users\nilad\.moira\kernels\de441.bsp`; pytest content-probes DE441.
Varga has no admitted native counterpart. This follow-up changes validation
tooling/fixtures/tests and documentation. Existing Chara/D60 dirty work is
preserved. Runtime/API semantics, defaults, harness, known-issue exemptions,
native extension and generated `moira.wiki` are unchanged.

Documentation reconciliation: the source standard and two research records
now link this completed computational evidence; the earlier validation receipt
preserves its narrower checkpoint and links forward. The Vedic work register
distinguishes completed modern validation from historical source admission.
Home adds discovery, and the unreleased changelog records this added coverage.

Pytest uses `MOIRA_TEST_MODE=1`, `MOIRA_STRICT_KNOWN_ISSUES=1`,
`MOIRA_NO_DOWNLOAD=1`, and `-m 'not external_network'`. Server tests admit
loopback; frozen evidence tests use no external network. The first new-coverage
run passed **205 tests**, with 19 successful DE441 resource uses and no skips.

```powershell
.\.venv\Scripts\python.exe -m pytest tests/unit/test_d60_cross_engine.py tests/server/test_d60_cross_engine.py -q -m 'not external_network' --junitxml=C:/dev/outputs/vedic-d60-cross-engine-2026-10-07/new_tests.xml
.\.venv\Scripts\python.exe -m pytest tests/unit/test_d60_cross_engine.py tests/server/test_d60_cross_engine.py tests/unit/test_d60_full_position.py tests/unit/test_d60_published_evidence.py tests/unit/test_vedic_chara_d60_admission.py tests/server/test_d60_full_position.py tests/server/test_vedic_chara_d60_admission.py tests/unit/test_varga.py tests/unit/test_shodashvarga.py tests/unit/test_d60_deities.py tests/unit/test_vedic_facade.py tests/server/test_server_varga_routes.py -q -m 'not external_network' --junitxml=C:/dev/outputs/vedic-d60-cross-engine-2026-10-07/regression.xml
.\.venv\Scripts\python.exe -m pytest tests/server/test_server_vedic_phase2_routes.py -k vimshopaka -q -m 'not external_network' --junitxml=C:/dev/outputs/vedic-d60-cross-engine-2026-10-07/strength_regression.xml
.\.venv\Scripts\python.exe scripts/validate_d60_cross_engine.py --work-dir C:/dev/outputs/vedic-d60-cross-engine-2026-10-07 --check-fixture tests/artifacts/oracle/d60_cross_engine_2026-10-07.json
```

The validator reproduced the frozen fixture exactly using checksum-verified
cached sources, without acquisition. A fresh private workspace requires
`--acquire` explicitly; kernel downloads remain disabled. Source-fragment
reproduction requires installed Windows MSVC. Ordinary offline tests need
neither comparator source nor a C++ compiler. Execution/document outcomes
are captured in private `verification.json`. This is focused acceptance,
not the whole repository suite or full-application software parity.

Final affected acceptance/regression runs: **1,399 + 3 = 1,402 distinct tests
passed**, zero failures/errors/skips. They re-execute the earlier 1,197-node
checkpoint and the 205 new nodes; the initial 205-test run is not added again.
The final runs recorded **25 + 6 successful DE441 resource uses**, with no
skips or failures and content-probed identity. New script/test Ruff, documentation
consistency, generated REST inventory, whitespace and eight-document in-memory
owning wiki render/link checks pass. The checked-in fixture reproduces exactly.
The lineage audit confirms no external implementation was copied into runtime
and no Moira output was used as an external expected D60 coordinate.
Link checks found no new missing targets; older changelog `file://` links
remain pre-existing formatting debt recorded in the private receipt.

## Acceptance decision

| Question | State |
| --- | --- |
| Modern mapping, partition semantics, broad external corroboration and engine/facade/REST/strength projection | **Complete under the declared policy**, within the corpus and arithmetic budget. No remaining engineering validation blocker identified. |
| Classical continuous-degree attribution | **Unestablished in reviewed sources.** Admit no additional classical full-point method without an identified passage and explicit semantics. |
| Exact source-published planetary D1/full-D60 pairs | **Not established by the literature review.** Separate from newly captured software outputs: an additional source-evidence frontier, not unfinished conditioned-computation validation. |
| Current PVR Jagannatha Hora equivalence/recommendation | **Not claimed.** PyJHora is another project; Maitreya intermediate evidence is expressly scoped. |
| Predictive effectiveness | **Not tested.** Arithmetic validation does not adjudicate interpretation. |

VED-003 retains bounded **historical source admission**, while its modern
implementation and broader computational validation are locally complete.
Secondary software outputs are not relabeled as primary classical evidence.
The package remains uncommitted/unpushed; release/deployment are separate.
