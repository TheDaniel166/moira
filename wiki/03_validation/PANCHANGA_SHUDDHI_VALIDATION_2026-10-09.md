# VED-008 implementation and validation receipt

**Date:** 9 October 2026. **Baseline:** engine `c647363`, generated wiki
`2e74b0b`, version 6.9.9. **State:** implemented and validated; included in the containing authorized
engine/wiki source-publication package. Release and deployment remain separate.

The user approved implementing the named profiles together while preserving
existing Tara/Chandra behavior. This receipt closes that selected VED-008
engine/public/REST scope. The [standard](../02_standards/PANCHANGA_SHUDDHI_STANDARD.md)
and [source packet](../06_roadmap/VEDIC_PANCHANGA_SHUDDHI_SOURCE_RESEARCH_2026-10-08.md)
own source choices, clock derivations, disagreements and explicit exclusions.

## Surfaces and evidence classes

| Surface | Implementation and proof |
| --- | --- |
| Pure Shuddhi owner | Panchaka, separately selectable MC/PS Tara, nine-Yoga timing, eleven-Karana activity evidence and independent Bhadra claims; frozen typed vessels and strict admission. Source-table and mathematical boundary tests. |
| Private dated composer | Sunrise-owned cells, full parent-event roots, current Lagna, Moon-quarter/sign transitions, derived interval boundaries, numerical uncertainty and partial polar/natal states. Analytic and DE441 numerical tests. |
| Public access | Sixteen identical root/vedic/facade exports, three facade methods; dated reader remains caller-owned. Export identity and lifecycle tests. |
| REST | Catalogue/direct/day routes; finite strict inputs, nested typed results, lossless serializers, serving-reader service, canonical errors. Exact engine/HTTP comparisons and adversarial requests. |
| Compatibility | Existing Tara/Chandra, five-limb classification, weighted personal scoring, generic search, named Muhurta and Daily Panchanga. Selected existing unit/server regression suites. |

No dependency, version, native/astronomical substrate, existing scoring
default, website or Urania implementation changed. No third-party astrology
engine supplied the implementation architecture or arithmetic.

## Executed verification

Runtime: `C:/dev/moira/.venv/Scripts/python.exe`, Python 3.14.3.
`MOIRA_NO_DOWNLOAD=1` and `MOIRA_STRICT_KNOWN_ISSUES=1`; installed DE441
resolved by the existing discovery layer at
`C:/Users/nilad/.moira/kernels/de441.bsp`. Harness network access was denied
except marked loopback. No test waiver, failure or resource skip was used.

The final non-overlapping acceptance slices total **622 passing tests**:

1. New unit/server tests plus existing Muhurta, sampled-search, named/special
   Muhurta and Daily Panchanga unit/server suites: **608 passed**, 120.30 s,
   **77 planetary resource uses**, all run.
2. `tests/integration/test_panchanga_shuddhi_ephemeris.py`: **12 passed**,
   **15 planetary resource uses**, all run, including both configured-kernel
   and discovered-kernel FastAPI startups.
3. Two final analytic solar-admission cases: exact zero-width solar roots
   remain available, and a next-sunrise bracket crossing civil midnight is
   rejected as uncertain ownership.

Combined: **92 successful DE441 resource uses**; zero failures/errors/skips.
The earlier targeted 73 unit and 30 server passes are included in the 608,
not additional tests. After tightening immutable-vessel validation, all 115
new unit/server/integration tests were rerun successfully. The subsequent
solar-admission change was verified by the expanded 32-test server slice
and the six real-cell cases; repeated tests are not added to the 622. The entire repository suite was not run or claimed.

```powershell
$env:MOIRA_NO_DOWNLOAD = "1"
$env:MOIRA_STRICT_KNOWN_ISSUES = "1"
.\.venv\Scripts\python.exe -m pytest tests/unit/test_panchanga_shuddhi.py tests/server/test_server_panchanga_shuddhi.py tests/unit/test_muhurta.py tests/unit/test_muhurta_search.py tests/unit/test_named_muhurta.py tests/unit/test_special_muhurta.py tests/unit/test_daily_panchanga.py tests/server/test_server_muhurta_routes.py tests/server/test_server_muhurta_search.py tests/server/test_server_named_muhurta.py tests/server/test_server_special_muhurta.py tests/server/test_server_daily_panchanga.py -q -o addopts=
.\.venv\Scripts\python.exe -m pytest tests/integration/test_panchanga_shuddhi_ephemeris.py -q --disable-warnings
```

Fourteen Python files parse with Python 3.10 grammar. Ruff adds zero findings
relative to HEAD; all 65 findings in the existing export modules predate this
package (line shifts normalized). New owner/transport/test files are clean.
The executable Python standard example, documentation consistency, generated
REST inventory (492 paths/operations), wiki synchronization and whitespace
checks pass. Eight generated wiki pages carry the canonical documentation.

The private JUnit/static receipts are under
`C:/dev/outputs/ved008-implementation-2026-10-09/`.

## What the tests establish

**Source arithmetic:** all 68,040 Panchaka number combinations agree with
the independently transcribed Kalaprakasika offset formulation; both published
worked-number examples agree. This is finite arithmetic corroboration, not
astronomical or predictive validation.

**Named rules:** both Tara profiles cover 27 natal stars × 27 transit stars ×
4 quarters, preserving base Tara count/polarity. All 27 Yogas are checked,
including every partial-period table entry, exact end ownership, clipping and
uncertainty. Every Bhadra table row is checked at tithi durations 0.8, 1.0 and
1.2 days with unequal actual Karana halves; raw/clipped endpoints agree with
independent rational formulae. All Moon residences, all 60 Karana positions
and both day/night values are exercised. Catalogue checks include Kimstughna.

**Numerical composition:** analytic sky tests exercise changing Lagna, root
wrap, adaptive fast motion, backward-phase rejection, merged uncertainty,
missing solar anchors and independent partial components. Real DE441 tests
cover Delhi 9/10 October 2026, New York 8 March/1 November DST transitions,
the equator 2 January 2000, latitude 65.99° on 22 September 2026, Tromso
solstices and its 20 March polar-Lagna partial result.

Six available real days each use 48 distributed probes plus a non-midpoint
probe in every cell. Fresh planet and full-house calculations agree with
the stored discrete values/findings outside uncertainty bands. Parent tithi,
Karana and Yoga endpoints bracket the theoretical phase boundary; solar
endpoints bracket the selected geometric altitude signal. Default numerical
brackets are at most 0.1 seconds. Sun/Moon and Lagna use true Lahiri, the
existing apparent-geocentric reduction and explicit UT1 event time.

**Transport:** invalid numbers/booleans/strings, unknown profiles/extras,
invalid/absent full spans, malformed/skipped dates and invalid coordinates
are rejected. Missing astronomy is typed partial/unavailable success; missing
resources and coverage use canonical error envelopes with request IDs. Both
startup reader paths preserve exact canonical serialization and do not close
or replace the serving reader. Explicit/active reader paths agree and restore
context ownership.

## Limits and ownership audit

The source fixtures validate the selected printed rules; real-day comparisons
validate numerical composition against independent calls to the existing
substrate. They do not constitute a published paired full-Shuddhi oracle,
observational accuracy guarantee or evidence of predictive efficacy. The
approved package does not require those unrelated claims for closure.

MC quarter interpretation, Sastri's alternative, fixed Yoga ghatis and
normalized Bhadra ghatis remain visibly different policies. No universal
precedence is invented when restrictions and exceptions coexist. Specific
unselected readings retain their documented research conditions. VED-009/010/
011 and generic score/search integration remain separate admissions.

The implementation's objects, helpers and branch structure follow the source
tables, bounded celestial events and affine interval arithmetic. Provenance
and all policy decisions remain engine-owned; serializers only project them.
This is local source-profile completion, not release or deployment.


## Authorized source publication

The user authorized committing and pushing the complete VED-008 package on
9 October 2026. Publish the generated wiki first, then the engine implementation,
canonical documentation and exact wiki gitlink. Source research is included
with its admitted runtime contract and validation evidence.

The 622 distinct passing tests remain the implementation acceptance evidence.
Publication updates status prose only; computational code, fixtures and
thresholds are unchanged. Publication gates are documentation consistency,
generated REST inventory (492 paths/operations), generated-wiki synchronization,
explicit staged manifests and whitespace checks. Exact local/remote SHAs and
the parent gitlink are verified after pushing and recorded in the handoff.

The next recommended package is VED-009, starting with edition-specific
research and a finite dosha/Parihara admission plan. It is not implemented by
this publication. VED-010 strength composition and VED-011 purpose elections
follow separately. No release, tag, deployment or website adoption is included.
