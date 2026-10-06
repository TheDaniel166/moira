# Gochara Phala: Phase 1 engine doctrine

Status: historical initial-core checkpoint, implemented on 6 October 2026. “Phase 1” here named the first delivery slice, not constitutional Phase 1 closure. The current policy, subsystem architecture and stable surface are governed by the [backend standard](../02_standards/GOCHARA_BACKEND_STANDARD.md) and [constitutional ledger](../06_roadmap/GOCHARA_CONSTITUTIONAL_LEDGER.md). This checkpoint retains the initial default semantics and verification receipt; no release or website delivery is implied.

## Governing object and source

`moira.gochara.gochara_from_positions` evaluates the seven classical planets in supplied sidereal transit positions, counting whole signs inclusively from the natal Moon's sidereal sign. Its fixed profile is `phaladeepika_26_sastri_1950_seven_classical`.

Authority: Mantreswara, *Phaladeepika*, V. Subrahmanya Sastri, second edition (1950), [primary scan](https://www.wisdomlib.org/uploads/ocr/essays/phaladeepika/phaladeepika-2nd-ed-1950-by-v-subrahmanya-sastri-text.pdf). Chapter 26.1 governs the reference; 26.2 the favorable positions; 26.3–8 ordinary Vedha and exceptions; 26.9–23 the 84 planet/position indications; 26.41 the optional Ashtakavarga context. Printed pages 286–295 and 303 correspond to one-based PDF pages 321–330 and 338.

The inspected scan has SHA-256 `f4b0b71735c788457a4fb4bf98524c058af89b095a72617bcf50546578018fd1`. Numerical rules and narrative themes were visually collated against these printed pages. Runtime indications are original, concise paraphrases with individual verse locators. They describe the selected historical doctrine; they do not establish a predictive accuracy rate.

The source fixture is `tests/fixtures/gochara_phaladeepika_26.json`. It contains all 36 directed pairs, seven favorable sets, four directed exemptions, and verse/theme anchors for every one of the 84 indications. It was assembled from the source collation independently of runtime tables. The fixture's themes are regression anchors, not complete translated passages.

## Assembly and astronomy boundary

For a normalized longitude `L`, the absolute sign index is `floor(L / 30)` in 0–11. If the natal Moon sign is `M` and a transit sign is `T`, its inclusive position is `(T - M) % 12 + 1`. This is whole-sign counting; natal house cusps, aspect orbs and degrees within a sign do not determine ordinary Vedha.

The caller supplies finite real longitudes in degrees, converted to a consistent sidereal frame at each position's own epoch. The evaluator normalizes longitudes modulo 360. If floating-point remainder rounds an infinitesimal negative angle to exactly 360, the nearest representable value below 360 preserves its final-sign ownership. Booleans, non-real values and non-finite values are rejected. Natal reference and transit sign boundaries belong to the next sign at an exact multiple of 30 degrees.

This function calculates no ephemeris, ayanamsa, correction regime, time conversion or geographic house. `position_origin="caller_supplied_sidereal"` records that boundary. Callers using Moira charts must choose their astronomical policy explicitly and convert each chart at its own epoch using the existing sidereal APIs. These rule tests do not validate astronomical positions or ingress times. No native C++ calculation, external ephemeris or new runtime dependency is introduced by Phase 1.

The fixed subjects and blockers are Sun, Moon, Mars, Mercury, Jupiter, Venus and Saturn. Restricting blocker participation to these seven is an explicit conservative profile decision, not a universal claim about every school's use of nodes. Unknown keys, including Rahu and Ketu, are rejected rather than silently omitted.

## Admitted numerical rules

Both sides of every pair below are inclusive positions from the same natal Moon. A pair `3 → 9` means that another eligible planet occupying position 9 obstructs the subject's favorable position 3. It does not make position 9 a favorable position or imply the reverse rule.

| Subject | Favorable positions | Directed favorable → Vedha pairs | Exempt blocker | Source |
| --- | --- | --- | --- | --- |
| Sun | 3, 6, 10, 11 | 3→9, 6→12, 10→4, 11→5 | Saturn | 26.3 |
| Moon | 1, 3, 6, 7, 10, 11 | 1→5, 3→9, 6→12, 7→2, 10→4, 11→8 | Mercury | 26.4 |
| Mars | 3, 6, 11 | 3→12, 6→9, 11→5 | None | 26.5 |
| Mercury | 2, 4, 6, 8, 10, 11 | 2→5, 4→3, 6→9, 8→1, 10→8, 11→12 | Moon | 26.6 |
| Jupiter | 2, 5, 7, 9, 11 | 2→12, 5→4, 7→3, 9→10, 11→8 | None | 26.7 |
| Venus | 1, 2, 3, 4, 5, 8, 9, 11, 12 | 1→8, 2→7, 3→1, 4→10, 5→9, 8→5, 9→11, 11→3, 12→6 | None | 26.8 |
| Saturn | 3, 6, 11 | 3→12, 6→9, 11→5 | Sun | 26.5 |

Any other participant may obstruct; a blocker need not be a malefic. The subject cannot obstruct itself. All occupants of the directed Vedha sign are retained as witnesses, including exempt occupants. An exempt occupant alongside a real blocker does not cancel that blocker.

## Baseline, obstruction and missing data

Every supplied planet has a `GocharaPlanetResult`. Its `baseline_favorable` and cited `indication` preserve the unmodified baseline. Obstruction is reported separately; a blocked benefit is not rewritten into a newly invented adverse narrative.

| `vedha_status` | Meaning |
| --- | --- |
| `not_applicable` | The subject is outside this profile's favorable positions. Ordinary Vedha is not evaluated; no counter-Vedha relief is inferred. |
| `blocked` | At least one known, non-exempt occupant establishes obstruction. Missing other participants remain visible. |
| `incomplete` | No known non-exempt blocker is present, but at least one eligible blocker is absent from the snapshot. An unobstructed conclusion is unavailable. |
| `unobstructed` | Every eligible blocker has a supplied position and none occupies the directed Vedha sign. A missing exempt planet does not prevent this judgment. |

`missing_planets` describes the whole snapshot. Each planet's `missing_blockers` describes only its eligible missing participants. `vedha_witnesses` retains subject, blocker, both Moon-relative positions, exemption and verse citation. Input order does not affect canonical planet or witness order. Positions, judgments and copied BAV counts are immutable tuples in frozen vessels, detached from mutable input mappings and legacy BAV lists.

`evaluated_layers` identifies baseline, ordinary Vedha and historical indications, plus raw own-BAV context when supplied. Its inclusion of ordinary Vedha means the evaluator determined applicability and status; it does not imply an applicable or complete judgment. `outside_profile_layers` explicitly lists nodes, counter-Vedha, Tara, Kakshya, sign-part activation, dasha, strength overrides, dated forecasts, remedies and composite scores. These layers are not inferred from the baseline.

## Optional raw Ashtakavarga context

The `bhinna` argument accepts existing `BhinnashtakavargaResult` vessels keyed by the corresponding supplied subject. Each must be that subject's own **unreduced natal** BAV, with twelve integer counts in 0–8. Lookup delegates to `moira.ashtakavarga.transit_strength` at the transit's **absolute sidereal sign**, not its Moon-relative position. The count appears as `ashtakavarga_rekhas`; an absent table produces `None`. Neither four rekhas nor any other count changes baseline membership or Vedha status.

The existing BAV vessel has no birth identity or reduction provenance. The caller must bind it to the same natal chart and certify that it is unreduced. This function can verify table shape, count bounds, planet identity and snapshot participation; it cannot verify that external assertion. Phase 1 does not alter the existing BAV calculation or its separate strength conventions.

## Source discrepancies and exclusions

The selected edition's full sequences govern Mercury `8→1` and Venus `11→3`, `12→6`. The local Kapoor translation omits or truncates relevant sequences, and P. V. R. Narasimha Rao's Table 63 reverses the last two Venus blockers. Those alternative values are not merged into this profile.

Mars in position 10 follows the unsuccessful-efforts indication in Phaladeepika 26.16. Brihat Samhita 104.17 and Prasna Marga 22.9 offer different treatments. Nodes also require a separately admitted doctrine: Phaladeepika 26.2's Sun-like baseline includes position 10, while Prasna Marga 22.51 supplies a Saturn-like alternative. No nodal Vedha exemptions are inherited by analogy.

The research report and source inventory are retained outside the distributable engine in `C:/dev/outputs/gochar-research-2026-10-06/`. No scanned book or copied modern translation is packaged with the feature.

## Public API and executable example

The same eight names are exported by `moira.gochara`, the package root, `moira.facade` and `moira.vedic`: `GOCHARA_PROFILE`, `GOCHARA_PLANETS`, `GocharaVedhaStatus`, `GocharaPosition`, `GocharaVedhaWitness`, `GocharaPlanetResult`, `GocharaResult`, `gochara_from_positions`. This phase adds no `Moira` class method or REST endpoint.

```python
from moira import GocharaVedhaStatus, gochara_from_positions

report = gochara_from_positions(
    natal_moon_sidereal_longitude=5.0,
    transit_sidereal_longitudes={
        "Sun": 65.0, "Moon": 245.0, "Mars": 5.0,
        "Mercury": 5.0, "Jupiter": 5.0, "Venus": 5.0,
        "Saturn": 245.0,
    },
)
sun = report.for_planet("Sun")
assert sun.house_from_moon == 3
assert sun.baseline_favorable
assert sun.vedha_status is GocharaVedhaStatus.BLOCKED
assert [(w.blocker.planet, w.exempt) for w in sun.vedha_witnesses] == [
    ("Moon", False), ("Saturn", True)
]
assert report.missing_planets == ()
```

The example demonstrates a real Moon blocker alongside an exempt Saturn blocker. It uses illustrative supplied longitudes, not an astronomical chart for a stated date.

## Validation scope and receipt

Runtime: repository `.venv`, Python 3.14.3; engine version 6.9.9. Native/import smoke resolves `moira/_moira_native.cp314-win_amd64.pyd`. The feature itself uses the Python doctrinal path and stdlib, with existing BAV lookup delegation.

Source tests exercise all 84 planet/position baselines under all twelve reference signs (1,008 evaluations) and all 36 directed pairs against each of the six other classical participants under all twelve reference signs (2,592 evaluations). Additional tests cover partial snapshots, all four directed exemptions, multiple blockers, finite and exact-boundary inputs, mutable-input isolation, public-vessel contradictions, raw counts 0–8 without overrides, and shared export identity.

Changed files:

| File | Change |
| --- | --- |
| `moira/gochara.py` | Named profile, original indications, immutable vessels, ordinary Vedha evaluator, raw own-BAV context. |
| `moira/__init__.py` | Eight additive package-root exports. |
| `moira/facade.py` | The same eight exports; existing class methods unchanged. |
| `moira/vedic.py` | The same eight Vedic-surface exports. |
| `tests/fixtures/gochara_phaladeepika_26.json` | Independent source rules, themes and edition receipt. |
| `tests/unit/test_gochara.py` | 173 focused tests, including source scenarios and input/public contracts. |
| `tests/unit/test_api_surface_adversarial_audit.py` | Eight additions to the existing explicit root-surface expectation. |
| `wiki/01_doctrines/GOCHARA_PHASE1_DOCTRINE.md` | Governing doctrine, source choices, example and implementation receipt. |

Commands run from the engine root with its `.venv`:

```powershell
$env:MOIRA_TEST_MODE='1'
$env:MOIRA_STRICT_KNOWN_ISSUES='1'
.\.venv\Scripts\python.exe -m pytest tests/unit/test_gochara.py -m 'not external_network' -o addopts='--import-mode=importlib' -q
```

Final outcome: **173 passed**, no skips. The first development run had one test-harness expectation error: Python 3.14 raises `TypeError` for replacement of a dataclass `init=False` field. The test now verifies the fixed profile through the public constructor's stable `TypeError` contract. No runtime failure was hidden or waived.

```powershell
.\.venv\Scripts\python.exe -m pytest tests/unit/test_gochara.py tests/unit/test_api_surface_adversarial_audit.py tests/unit/test_vedic_facade.py tests/unit/test_ashtakavarga.py tests/unit/test_muhurta.py -m 'not external_network' -o addopts='--import-mode=importlib' -q
```

Broader outcome: **462 passed, one failed**, no skips. `test_vedic_facade_shadbala_chart_wrapper_delegates_to_engine` fails at its standalone direct `shadbala` call with `MissingKernelError` because no reader context is active. A fresh process loaded all three changed public modules from unchanged HEAD `edd305bcfe54879b6c49752e6c079223a626f6f2`, using an import loader over `git show HEAD:<path>` and the same unchanged remaining sources. Running that exact test reproduced the same failure. No Shadbala, reader, test-policy or known-issue changes were made. After this broader run, the final adjustment to retain last-sign ownership for tiny negative angles passed the full 173-test Gochar slice again; surrounding unchanged suites were not repeated.

```powershell
.\.venv\Scripts\ruff.exe check moira/gochara.py moira/vedic.py tests/unit/test_gochara.py tests/unit/test_api_surface_adversarial_audit.py --no-fix --output-format concise
git diff --check
```

Both pass. Checking all six changed Python files also identifies existing lint debt in the package root and facade. Ruff JSON diagnostics were compared on current contents and `git show HEAD:<path>` using the same `--stdin-filename` and UTF-8 bytes: **59 findings in `moira/__init__.py` before and after; five in `moira/facade.py` before and after; no introduced findings**. No global suppressions or unrelated lint edits were added.

The existing `tests/unit/test_docstring_governance.py` helpers `check_module_docstrings`, `check_class_docstrings` and `check_machine_contracts` each return zero violations for the new module. The single Python example in this document was extracted and executed successfully using the project runtime. A pre-edit import/native smoke and three selected public-root baseline checks also passed. All pytest runs used strict known-issue expiry checking and denied external networking.

The post-correctness lineage inspection checked helper structure, sign-boundary handling, result assembly and proof framing. Rules come from the declared primary text, counts use the explicit twelve-sign object, exceptions attach to named subjects, and assembly uses named vessels. No external-engine implementation, array layout, parity oracle, ephemeris fallback or runtime dependency was imported into this module. The floating-point endpoint policy follows sign ownership rather than an unexplained angle repair. This is a scoped inspection of the new technique, not a repository-wide sovereignty certification.

At this initial checkpoint, the working changes remained uncommitted on `main`; subsequent gate closure and source publication are tracked by the constitutional ledger. The pre-existing REST-fix branch and commits are preserved. Astronomy, existing Ashtakavarga/Muhurta/Sade Sati behavior, REST, website/Workspace, source books and generated `moira.wiki` were left untouched. Validation does not include a predictive accuracy study, a real-kernel astronomical authority comparison, ingress search, retrograde forecast segmentation, node doctrine, website delivery or publication. Caller-owned sidereal frame and BAV birth/reduction provenance remain the explicit assumptions.
