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
