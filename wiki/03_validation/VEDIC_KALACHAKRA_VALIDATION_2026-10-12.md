# VED-014 Kalachakra validation receipt

**Date:** 12 October 2026. **Version:** 6.9.9.
**Status:** Selected Santhanam/BPHS profile implemented and validated locally.
**Inspected parent:** `8852052f317d7f3841e1e390578e303f438140a8`.
**Runtime:** `C:\dev\moira\.venv\Scripts\python.exe`, Python 3.14.3.
**Scope:** [seven-stage plan](../06_roadmap/VEDIC_KALACHAKRA_IMPLEMENTATION_PLAN_2026-10-12.md),
[backend standard](../02_standards/KALACHAKRA_DASHA_STANDARD.md) and
[Python/REST API](../02_services/KALACHAKRA_DASHA_API.md).
Source publication, release and deployment have not occurred in this package.

## Delivered contract

`bphs_santhanam_longitude_row_cycle_v1` implements BPHS 46.93 longitude balance,
the reviewed Santhanam examples' natal-row repetition, and chapter 64 natal-row
AD rotation with its unchanged denominator. It returns exactly nine MD
occurrences and optional nine full ADs per MD, using exact rational source
arithmetic before birth clipping. Repeated signs retain unique paths and cycles.

Named fixed-day projection, bounded active lookup, natal-row Deha/Jeeva, gati
evidence, eligibility status and fourteen source-conflict decisions are shared
by module, root, facade, Vedic and five REST operations. Source-only supplied
sidereal calculation, projection and lookup require no reader. Date composition
uses one Moon derivation and one ayanamsa reduction at a reader-bound TT, with
separate UTC schedule and UT1/TT/TDB astronomy provenance.

Both constructors and public consumers protect aggregate result integrity.
Serializers revalidate sequence/current objects, so a forged sign, path,
partition, lineage or active status cannot become a successful response.
Unsupported requests fail before astronomy. Source projection precision errors,
resource failures and internal defects retain distinct HTTP contracts.

## Independent authority and evidence classes

The [research packet](../06_roadmap/VEDIC_KALACHAKRA_SOURCE_RESEARCH_2026-10-12.md)
records the inspected BPHS/Santhanam, JP/Sastri, Rao and Kapoor witnesses,
their SHA-256 fingerprints, PDF/printed coordinates and source conflicts.
The runtime is derived from those rules, not an external engine implementation.

`tests/fixtures/kalachakra/source_cases.json` was frozen and independently
checked before calculator implementation. Its SHA-256 remains
`f646f4ab82907988da8cdff128785a62e0c9502a66019c15c70885505952f823`.
The independent standard-library oracle imports no Moira implementation.
It checks all 27 memberships, 16 rows / 144 entries, row totals, 108 rational
pada starts, natal-row AD rotations, exact published/derived balances and checked
AD cells. The separate 24-position rings corroborate the table transcription;
they do not replace Santhanam's continuation rule.

Authority cases include BPHS 34°50′, first Aries/Aries and Taurus/Taurus ADs,
JP's paired 284°29′39″ example, and shared seed/balance portions of Rao's
Examples 95/96 and Exercise 34. Competing continuations, denominators, AD starts,
time-fraction methods and the complete ten-entry exercise remain discriminators.
They are not incorrectly treated as this profile's universal output oracle.

Exact source examples are distinguished from binary64 public inputs. The latter
are compared against exact ratios of their admitted values; deviation from a
sexagesimal witness is bounded by input conversion times the source slope.
No angular epsilon changes a pada or period occurrence. Calendar endpoints are
exact-ratio common-origin projections rounded once to binary64; no generic
tolerance determines interval ownership. A bounded ULP tolerance is used only
to validate TT/UT1/TDB receipt algebra after subtracting large Julian dates.

Source-year ratio denominators are bounded by the binary64 denominator and the
small admitted divisors (10 and a row total at most 100); endpoints have magnitude
at most 100 source years. A conservative 400-decimal-digit limit exceeds this
worst-case bound. The smallest positive binary64 input is exercised explicitly.
JSON preserves numerator/denominator as strings rather than unsafe numeric integers.

These checks establish source-rule implementation and structural correctness.
Real-kernel composition establishes agreement of the public paths with the same
Moira astronomical owner. It is not independent JPL-position accuracy validation
or external-software corroboration; the existing astronomy substrate owns those
separate evidence layers. No predictive efficacy claim is made.

## Commands and outcomes

All commands run from `C:\dev\moira` with `MOIRA_NO_DOWNLOAD=1` and
`MOIRA_STRICT_KNOWN_ISSUES=1`. `tests/KNOWN_ISSUES.yml` was empty.
Default network denial remained active; HTTP tests used the loopback marker.
Resource discovery through `moira._kernel_paths.find_planetary_kernel()` resolved
`C:\Users\nilad\.moira\kernels\de441.bsp`. The test harness independently
content-probed DE441. Required real-kernel tests ran without skips.

```powershell
.\.venv\Scripts\python.exe -m pytest tests/unit/test_kalachakra_sources.py tests/unit/test_kalachakra.py tests/unit/test_kalachakra_admission.py tests/unit/test_kalachakra_projection.py tests/unit/test_kalachakra_astronomy.py tests/unit/test_kalachakra_public_api.py tests/server/test_server_kalachakra.py tests/server/test_server_kalachakra_openapi.py -o addopts=-ra -q
```

**249 passed in 43.26 seconds**, no skips/failures. This includes all 108 padas
and floating neighbours, every row's source cutovers, repeated-sign occurrences,
full/visible conservation, both clocks, every projected active cutover, birth/final
coverage, subnormal and unrepresentable projections, forged results, resource
failures, strict Python/JSON admission, source/HTTP parity, all named ayanamsa
composition branches, route discovery and OpenAPI bounds. The two explicitly
ephemeris-marked cases cover real-kernel module/facade/direct/timezone and actual
chart/direct HTTP agreement; five harness resource receipts all succeeded.

```powershell
.\.venv\Scripts\python.exe -m pytest tests/unit/test_dasha.py tests/unit/test_dasha_systems.py tests/unit/test_dasha_full_intervals.py tests/unit/test_chara_profiles.py tests/server/test_server_alternate_dashas_routes.py tests/server/test_server_jaimini_profiles.py tests/server/test_vedic_direct_input_hardening.py tests/unit/test_public_api_drift.py tests/unit/test_public_api_contract.py tests/unit/test_api_surface_adversarial_audit.py tests/server/test_server_route_discoverability.py tests/server/test_server_error_mapping.py tests/server/test_error_mapping.py -o addopts=-ra -q
```

**545 passed in 231.67 seconds**, no skips/failures. Combined with the feature
slice, **794 distinct selected tests passed**. The preliminary source/baseline
run and intermediate repair runs overlap these selections and are not added
again. The full repository suite was not run.

After adding the explicit supported-ayanamsa catalogue and OpenAPI enum, the
affected public-export and schema/discovery slice was rerun: **3 passed in
9.59 seconds**, with no skips or failures. These overlap the 794-test selection.

Additional checks:

- `python tests/unit/test_docstring_governance.py`: all 375 engine Python files passed.
- Scoped Ruff on the four new engine owners, four transport modules and eight
  feature test files: passed, with no broad autofix.
- Both Python examples from the API document were executed in order and passed.
- The fixture fingerprint was rechecked after implementation and is unchanged.
- All eight new runtime modules parse with Python 3.10 grammar. The existing
  minimum-version lane's import/schema smoke, extended with Kalachakra admission,
  passed under the project Python 3.14.3. Actual Python 3.10 execution remains the
  wired CI lane; it was not run locally and no remote CI result is claimed.
- `scripts/check_doc_consistency.py`: passed.
- `scripts/check_release_identity.py`: passed for 6.9.9.
- `scripts/generate_hellenistic_inventory.py` and `--check`: generated/current.
- `scripts/sync_rest_api_reference.py` and `--check`: generated/current.
- `scripts/sync_git_wiki.py --no-prune` and `--check`: generated/current.
  An isolated copy of the resolved Git index included the new canonical pages
  for generation. The actual index fingerprint remained unchanged; no files
  were staged in the working checkout and no unrelated mirror pages were pruned.
- `scripts/build_website_docs_bundle.py --candidate` and `--check`: current
  local candidate, containing 26 documentation pages and 25 release records at
  `C:\dev\outputs\ved014-implementation-2026-10-12\publication.json`.
  This is a generated artifact, not a website publication.
- `git diff --check`: passed; existing LF/CRLF advisory messages are not failures.

The workflow now runs the kernel-free Kalachakra slice and tests its strict
requests in the minimum-Python smoke. Real-kernel acceptance remains explicit
local evidence, rather than being concealed by a kernel-free CI exclusion.

## Review findings repaired during implementation

The correctness review checked result construction as well as normal calculations.
Birth/period constructors validate local structure; aggregate sequence/current
validation independently rematerializes bounded expectations and compares types,
paths, partitions and metadata. Expected structure bounds traversal even for a
forged recursive tree. Current-response serialization performs the same validation.

The review also found that generated astronomical corruption could otherwise
escape as an input ValueError. After admission, malformed Moon/epoch receipts now
raise `KalachakraInvariantError`; the HTTP regression verifies sanitized 500
classification. Source projection failures retain their typed 422, including
bounded path/reason details, and missing identities/anchors remain 503.

The lineage review found source-owned row and occurrence objects, exact source
axes, and directly derived proportional partitions. Existing Moira astronomical
primitives provide time binding, lunar positions and ayanamsa. No external
engine code, new dependencies, native rewrite, opaque scoring, post-hoc row repair
or software-shaped traversal was introduced. The shared alternate-dasha runtime
remains unchanged; its obsolete Kalachakra-reservation docstring was corrected.

## Scope, remaining capabilities and publication boundary

Selected scope is locally complete. Explicit remaining capabilities are the
named competing traditions, deeper periods, full gati taxonomy, source-specific
eligibility evaluation and version/settings-pinned external-software comparison.
Both Cancer/Leo directions remain unresolved KC-10; this does not alter the
implemented period order. No arbitrary hybrid or unsupported strength gate is
available through either Python or REST.

Authored runtime paths are the four Kalachakra engine files, public export/mixin
additions and the four Kalachakra transport files plus scoped router/app/OpenAPI
and error registration. The package adds source fixtures, eight test modules,
CI wiring, canonical standard/API/research/plan/register updates and this receipt.
Generated REST/inventory/wiki artifacts derive from current canonical source.

Concurrent natal-discovery/light-box and small-body runtime/data/docs changes
were preserved. Shared app/OpenAPI diffs include their independent hunks; this
package owns only Kalachakra registration. No protected baseline, tolerance,
kernel, catalogue, native implementation or release version was changed for
Kalachakra. No commit, push, tag, release or website deployment was performed.

## Rao 2000 extension - 26 October 2026

This additive checkpoint follows the authorized review repair and expansion.
The preceding sections retain the original 12 October scope and results.
The working tree is engine `main` at `caec99b`, package/native version 6.10.1,
using project Python 3.14.8 on Windows. Unrelated staged and unstaged work was
preserved. No version, native numerical implementation or tolerance changed.

### Delivered scope and source decisions

`rao_2000_longitude_continuous_v1` / `ved014.rao2000.1` is admitted alongside
the unchanged Santhanam calculation identity. Catalogue `ved014.2` adds explicit
per-profile sources, rules, decisions, namespace, continuation and Deha/Jeeva
reference. All public export surfaces, Moira methods and existing calculation
routes select either profile; selection remains mandatory.

The private immutable recipe owner separates doctrine from exact interval
materialization. Rao advances through the eight same-family rows, uses each
parent's nine forward AD weights and denominator, and derives Deha/Jeeva from
the emitted nine-MD window. `R2000/` rows cannot be substituted for Santhanam
rows. Rao's directed gati includes markati and continuous seams; Santhanam's
unresolved KC-10 and unclassified row seams remain unchanged. Nine MDs, levels
1-2, full-parent construction before birth clipping, common-origin projection
and half-open bounded lookup retain their existing product limits.

The [author's textbook](https://www.vedicastrologer.org/articles/vedic_astro_textbook.pdf)
and local `Good books/vedic_astro_textbook.pdf` were rechecked, including printed
pages 294, 295 and 297 visually. Local source SHA-256 remains
`2971851a3cda30929cf5b1ec56b88902bd4a141c8d5479599573ddf1c5f78242`.
The existing research ledger supplies chapter/table coordinates. Discoverable
`R2000-01` through `R2000-09` explicitly preserve the reconciled KC-03 membership,
weight-derived totals, continuous family progression, recomputed AD denominator,
Deha/Jeeva/gati ownership, nine-MD product limit, author's savana preference and
unevaluated eligibility. The ten-entry exercise witness is preserved outside
the nine-entry output bound. A 365.25-day projection is a Moira option, not a
claim to reproduce the author's calendar dates or later Rao formulations.

### Independent evidence and compatibility

`tests/fixtures/kalachakra/rao_2000_source_cases.json` passed four independent
source tests before runtime implementation. It freezes printed Examples 95-97
and Exercise 34, with derived coverage/AD fractions and the BPHS-input
discriminator separately labelled. Its SHA-256 is
`99075505715be0a25da0bdd2116e327474d19eee66b0c9918308885951e461bb`.
The oracle imports no Moira code and traverses separately transcribed 24-position
Table 43 rings. The runtime instead advances through source rows. Tests cover
all 108 padas and binary64 edge neighbours, all 144 within-row occurrence
starts, exact full/visible partitions, denominator conservation, directed
gati, both clocks and active-boundary ownership. Sexagesimal source values and
binary64 public inputs retain an explicit mathematical conversion bound.

The original source fixture remains unchanged at
`f646f4ab82907988da8cdff128785a62e0c9502a66019c15c70885505952f823`.
The separately frozen pre-extension Santhanam transport fixture has SHA-256
`e7d22d56e104cc180aa344bb7886d45e7271b6f29ba37c1b35177082cf95d7ba`.
Its 648 cases span all pada midpoints, levels 1/2 and source-only/both clocks;
projected cases also freeze current results at birth and the final endpoint.
All payload hashes match. This fixture is regression evidence generated from
the previous engine, not independent doctrinal authority.

### Final validation

The combined run passed **1,115 tests in 110.69 seconds**, with zero failures,
errors or skips: **1,072 Kalachakra tests plus 43 public API/discovery checks**.
Harness receipts report seven DE441 uses, all successful, with one content
probe. Direct, tropical and date-derived composition, facade and actual HTTP
responses agree. These comparisons validate composition using the same
astronomy owner; they are not an independent planetary-position oracle.

```powershell
$env:MOIRA_NO_DOWNLOAD='1'
$env:MOIRA_TEST_MODE='1'
$env:MOIRA_STRICT_KNOWN_ISSUES='1'
$env:HYPOTHESIS_PROFILE='moira-ci'
.\.venv\Scripts\python.exe -m pytest `
  tests/unit/test_kalachakra.py tests/unit/test_kalachakra_sources.py `
  tests/unit/test_kalachakra_admission.py tests/unit/test_kalachakra_projection.py `
  tests/unit/test_kalachakra_astronomy.py tests/unit/test_kalachakra_public_api.py `
  tests/unit/test_kalachakra_rao_sources.py tests/unit/test_kalachakra_rao.py `
  tests/unit/test_kalachakra_compatibility.py `
  tests/server/test_server_kalachakra.py tests/server/test_server_kalachakra_openapi.py `
  tests/server/test_server_kalachakra_rao.py `
  tests/unit/test_public_api_contract.py tests/unit/test_public_api_drift.py `
  tests/server/test_server_route_discoverability.py `
  -o addopts=-ra -q --tb=short `
  --junitxml=C:/dev/outputs/ved014-rao-2026-10-26/validation.xml
```

Focused Ruff checks and five-file engine docstring preflight passed. All three
Python API examples executed, including the real-reader example. The workflow
YAML parses and its Kalachakra/minimum-version gates cover both profiles.
Python 3.10 grammar checks passed for six runtime/transport files; no local
Python 3.10 runtime or remote CI execution is claimed. Release-facing doc
consistency also passed.

Malformed profile/row metadata, invalid denominators and unsupported hybrids
are rejected. Forged sequence/current engine results return sanitized,
request-correlated 500 responses; unrepresentable projections remain explicit
422s. The preceding astronomy repair limits missing-anchor KeyError handling
to the resource lookup, so internal lookup failures remain invariant 500s.

### Remaining limits and publication

No version/settings-pinned JHora export was available. The registered-application
check found no JHora/Jagannatha Hora entry; that is not an exhaustive portable
installation search. No external-software parity or predictive validation is
claimed. Other traditions, deeper periods, eligibility and further gati policies
remain separately scoped. This package makes no change to alternate-dasha
arithmetic or other Vedic doctrine.

The review repair and extension are locally complete and uncommitted. No push,
release, tag, website or service deployment occurred. Canonical API/standard,
fixture documentation and the remaining-work register are reconciled; generated
publication inventories and wiki mirroring remain publication-stage work.

## Markati context repair - 26 October 2026

The preceding extension was committed locally as
`affd8fd6478e3c827c46392e3eea1bd394322634`, then reviewed adversarially. One P1
was reproduced: the pair-only Rao classifier marked ordinary Savya Cancer-to-Leo
and Apasavya Leo-to-Cancer movement as Markati. Section 24.3.3(2) requires a
temporary reversal. The original fixture's pair list and its consuming gati
test shared that incomplete reading. No period arithmetic defect was identified.

The user authorized this repair. Source Table 43 and section 24.3.3(2) were
rechecked in the author's online textbook; the local PDF retains its recorded
SHA-256. The new `rao_2000_markati_contexts.json` supplement distinguishes the
two reversing contexts from their two ordinary counterparts. Its frozen hash is
`9bded4c5fc07341c350dc5d5967fc657f9cce8b0d1ae104b2104cee6dc1e5450`.
The independently derived test-input ordinals were checked against exact source
arithmetic before freezing; an initial candidate's 54-degree ordinal was
corrected to 5 (elapsed row 86/5 years, birth at row position 2).
All three pre-existing JSON fixtures and their fingerprints remain unchanged.

The runtime receives the source row position and reads its predecessor and
successor using the admitted continuous-row owner. Only the central edge of
`Vi Cn Le Ge` / `Ge Le Cn Vi` is Markati, for Savya / Apasavya respectively.
Context is available across row boundaries and outside returned/clipped
windows without emitting more periods. The independent oracle instead locates
the occurrence in Table 43's 24-position ring. Its source-only check separately
verifies the direction reversal and all four derived input/path mappings.

Before changing runtime, the 27 targeted tests produced **13 failures and 14
passes**: all ordinary-path negatives and the forged false-label HTTP check
failed, while the positive reversals and independent supplement checks passed.
After repair, the focused context/gati slice passed **29 tests**. Its exhaustive
check covers all 144 source-row positions and 11,520 MD/AD transitions, including
contexts across seams and outside the visible window. Module/facade and actual
direct/chart-derived HTTP paths are tested at levels 1 and 2. A forged ordinary
Markati result is rejected as a request-correlated invariant 500.

The final twelve-module Kalachakra run passed **1,099 tests in 116.30 seconds**,
with no failures/errors/skips, seven successful DE441 resource uses and one
content probe. All 648 frozen Santhanam sequence/current cases still match.
It used the same feature modules and strict environment settings in the command
above, excluding the three general public-surface modules, with JUnit at
`C:/dev/outputs/ved014-markati-repair-2026-10-26/feature.xml`.
The original external review probes separately passed **16/16 in 14.38 seconds**;
the three originally failing probes now pass without changing their expectations.

```powershell
# Original review probes, using the project harness and the same strict environment.
$env:PYTHONPATH='C:\dev\moira;C:\dev\moira\tests'
.\.venv\Scripts\python.exe -m pytest -c pyproject.toml -p tests.conftest `
  C:/dev/outputs/ved014-adversarial-2026-10-26/test_review_probes.py `
  --confcutdir=C:/dev/outputs/ved014-adversarial-2026-10-26 `
  -o addopts=-ra -q --tb=short `
  --junitxml=C:/dev/outputs/ved014-markati-repair-2026-10-26/adversarial.xml
```

Scoped Ruff and three-file engine docstring preflight passed. The API, backend
standard, fixture documentation and remaining-work register now state the
context requirement. Existing route/schema shapes and the unreleased Rao profile
identity are retained; the discovery rule/decision descriptions are clarified.
The P1 is closed locally. This repair is uncommitted/unpushed, with no version
release, external-software comparison or deployment. Unrelated work is preserved.

### Source-publication validation

The user subsequently authorized commit and push. Upstream had already
reconciled the extension into `main` at `146d495` with package version 6.10.2.
The local editable/native build was refreshed and stale repository egg-info
regenerated; package and distribution metadata now agree on 6.10.2.
The same twelve-module feature command passed **1,099 tests in 136.78 seconds**
on this reconciled source, with no failures/errors/skips, seven successful
DE441 resource uses and all 648 Santhanam compatibility cases unchanged.
JUnit is retained at
`C:/dev/outputs/ved014-markati-publish-2026-10-26/feature.xml`.
Scoped Ruff/docstring checks passed. The earlier uncommitted/unpushed statements
are historical checkpoints. This authorized thirteen-path source-publication
package does not release a version or deploy a service/site; exact commit and
remote verification are recorded in the adjacent publication receipt.
