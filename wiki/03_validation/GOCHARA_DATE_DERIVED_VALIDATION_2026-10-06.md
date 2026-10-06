# VED-017 date-derived Gochar validation receipt

Date: 6 October 2026. Scope: complete reader-bound epoch/civil-instant snapshots,
optional raw natal BAV provenance and strict REST transport. The
[owning standard](../02_standards/GOCHARA_DATE_DERIVED_STANDARD.md) defines
policy, derivation, source conventions and remaining forecast boundaries.

## Runtime and resources

- Canonical engine checkout: `C:\dev\moira`, `main`, starting at
  `34e3430bbf91a0c2fe57f059d72a11ce73cfb422`, initially clean.
- Sole execution runtime: `.venv\Scripts\python.exe`, Python 3.14.3.
- Required native extension: `moira/_moira_native.cp314-win_amd64.pyd`.
  Composition remains Python-governed and uses the existing strengthened
  planetary, precession, nutation and SPK substrate. No C++ port or rebuild.
- Installed `de441.bsp` discovered under the existing user kernel cache;
  integration content identity `DE-0441LE-0441`. No ephemeris download.
- ERFA 2.0.1.5 used only as a development oracle, never as runtime computation.
- Test environment: `MOIRA_TEST_MODE=1`, `MOIRA_STRICT_KNOWN_ISSUES=1`.
  `tests/KNOWN_ISSUES.yml` was empty. Default network denied; local TestClient
  tests explicitly marked loopback; no external network test selected.

## Authority and evidence

The existing independently collated
`tests/fixtures/gochara_phaladeepika_26.json` remains unchanged:
SHA-256 `81b2b7f95413685426f6221b07b0a4b94484d1ef22d902abedbca63fc6e88fd0`.
Its Sastri 1950 source witness governs seven favorable sets, 36 directed
ordinary-Vedha pairs, two directed exemptions and 84 indication themes.
The selected existing engine and HTTP tests exercise those witnesses.

BAV tests exercise the existing Raman-encoded tables and independent
sign-distance accumulation, including the same-birth eight-reference input
map and lookup at the absolute transit sign. No fresh primary-scan comparison
of Raman editions was performed; this product preserves the established
encoding and explicitly names its provenance.

Clock/frame authorities consulted online are linked in the standard: JPL
ephemeris export documentation, IERS time-scale definitions and pinned
SOFA/ERFA `gmst06`/`ee00` source. The local Gochar research receipt and existing
backend/source standards informed the bounded composition admission. No
additional disputed tradition was made executable.

## New behavior exercised

| Boundary | Evidence |
| --- | --- |
| Single-reader ownership | Explicit/contextual reader spies at both epochs; ambient context restored after success, natal failure and transit failure |
| Distinct clocks and ayanamsas | Deliberately shifted analytic TT; each epoch binds once and uses its own TT for every planet and offset |
| Date handling | Aware civil instants convert once through UTC-to-UT1; equivalent offsets agree; dates, naive times, booleans and numeric timestamps rejected |
| Raw natal BAV | Eight natal signs including Lagna, own unreduced tables and absolute-sign counts; clock/frame spies prevent using transit Lagna or mismatched TT |
| Policy surface | All twelve named ayanamsas exercised with installed resources; contradictory BAV choices and unused/missing birth location rejected |
| Resource truth | Missing reader/segment/anchor, invalid time identity and uncovered epochs have distinct failures; no partial success or anchor fallback |
| Immutable products | Frozen input copies and derived fields; incorrect clock receipts, incomplete position tuples and mismatched ayanamsa policy rejected |
| Transport | Actual compositor through analytic loopback; exact facade/serializer parity; real DE441 HTTP success and actual uncovered-epoch 422 |
| Discovery/curation | Eleven dated names share root/facade/vedic identity; explicit response models, twelve ayanamsa enum values, error envelopes and five Gochar routes |

Installed-kernel reconstruction covers modern natal/transit epochs,
historical natal JD 2316412.5 with nonzero reader tidal correction, and an
equal-epoch live Spica anchor. Each retained tropical longitude is compared
to a direct `planet_at` call at the same bound TT, and sidereal reduction to
the existing canonical TT ayanamsa. This proves composition over the substrate;
it is not a new external position or traditional ayanamsa certification.

## Private sidereal-time oracle

Five year-start epochs (1600, 1900, 2000, 2026, 2100) deliberately separate TT
from UT1 by one day to expose accidental reuse of UT1 in TT precession terms.
This synthetic separation is a clock-routing test, not a claimed physical
Delta-T. GMST is compared to ERFA `gmst06`; local apparent sidereal time to
ERFA `gst06a` plus longitude 77.209 degrees.

| Quantity | Maximum observed absolute residual | Test tolerance |
| --- | --- | --- |
| GMST | 0.0000236971 arcsec | 0.00072 arcsec (`2e-7` degrees) |
| Local apparent sidereal time | 0.0000295415 arcsec | 0.0036 arcsec (`1e-6` degrees) |

The complementary-term approximation is retained. Equal-epoch private GMST
also agrees with the existing public/native contract within `1e-10` degrees
on these cases. Existing public one-epoch behavior has not been retuned.
Detailed local measurements are saved at
`C:\dev\outputs\gochara-dated-2026-10-06\sidereal-time-oracle.json`.

## Executed commands

All commands run in `C:\dev\moira` with the test environment above.

The final new-feature slice:

```powershell
.venv\Scripts\python.exe -m pytest tests/unit/test_gochara_dated.py tests/server/test_server_gochara_dated.py tests/integration/test_gochara_dated_ephemeris.py -q -o addopts='' --junitxml=C:/dev/outputs/gochara-dated-2026-10-06/final-dated.xml
```

Result: **77 passed, zero failures/errors/skips**, 28.76 seconds. The harness
recorded 19 successful planetary resource receipts, one content probe and
DE441 identity. The integration test uses the session-shared engine fixture.

The broader compatibility slice:

```powershell
.venv\Scripts\python.exe -m pytest tests/unit/test_reader_bound_sidereal_time.py tests/unit/test_gochara_dated.py tests/unit/test_gochara.py tests/unit/test_gochara_constitutional.py tests/unit/test_vedic_surface_completeness.py tests/unit/test_vedic_facade.py tests/unit/test_ashtakavarga.py tests/unit/test_sidereal.py tests/unit/test_julian_delta_t.py tests/unit/test_facade_clock_boundaries.py tests/server/test_server_gochara.py tests/server/test_server_gochara_dated.py tests/server/test_server_time_scale_adapters.py tests/server/test_server_ashtakavarga_routes.py tests/server/test_server_sidereal_routes.py tests/integration/test_gochara_dated_ephemeris.py -q -o addopts='' --junitxml=C:/dev/outputs/gochara-dated-2026-10-06/targeted.xml
```

Result: **853 passed, zero failures/errors/skips**, 467.17 seconds. Existing
facade/Ashtakavarga transport tests repeatedly initialize an engine and account
for much of that duration. The final new-feature slice above ran after the last
resource-validation and compatibility edits and added five distinct cases; the two final JUnit
receipts contain **858 distinct passing cases** after deduplication by test
class/name. Repeated runs are not counted as additional coverage.

An initial combined collection attempt exposed duplicate unit/integration
module basenames; the integration file was renamed before successful execution.
One early analytic assertion differed in floating-point operation order;
the witness now performs tropical normalization before sidereal subtraction,
matching the specified coordinate stages. Neither failure was deferred or
added to known issues.

The final packaging pass replaced the new direct stdlib `StrEnum` import with
the existing `moira._strenum` Python 3.10 shim and made the test's ISO `Z`
parser compatible with Python 3.10. The affected 77-case slice was rerun
successfully. All six new Python files also parsed with
`ast.parse(..., feature_version=(3, 10))`. This is syntax/compatibility evidence,
not an executed Python 3.10 native-runtime test.

Documentation checks:

```powershell
.venv\Scripts\python.exe scripts/sync_rest_api_reference.py
.venv\Scripts\python.exe scripts/sync_rest_api_reference.py --check
git diff --check
.venv\Scripts\python.exe scripts/sync_git_wiki.py
.venv\Scripts\python.exe scripts/sync_git_wiki.py --check
```

REST inventory regenerated and checked: **480 paths/operations, 37 GET,
443 POST**, including five Gochar operations. Whitespace check passed.
Canonical documentation is synchronized to the Git wiki using its owning
generator; publication is a separate action.
At the initial validation checkpoint, the two new canonical documents were
staged so the generator's `git ls-files` discovery included them; the other
package changes were unstaged. Wiki synchronization wrote nine pages, retained
335 and removed none. Git publication was subsequently authorized as recorded
below.

## Change manifest and remaining boundaries

- `moira/gochara_dated.py`: typed composition policy, inputs/receipts,
  reader-bound factories, optional raw natal BAV, explicit resource/coverage errors.
- `moira/julian.py`: private UT1/TT sidereal-time helpers sharing the existing
  polynomial/complementary terms; public one-epoch results preserved.
- `moira/_facade_vedic.py`, `moira/__init__.py`, `moira/facade.py`,
  `moira/vedic.py`: reader-owning convenience methods and eleven shared exports.
- `moira/gochara_policy.py`: two cited composition records; original textual
  profile, snapshot defaults and scope choices preserved.
- `moira_server/models/gochara_dated.py`, model curation, Gochar service,
  serializer/router, error handlers and discovery metadata: two strict dated
  operations and lossless named-attribute views over canonical results.
- New dated unit/REST/integration and sidereal-time tests; existing Gochar
  discovery count and Vedic curation family updated.
- Canonical standards, API references, Home, constitutional history,
  remaining-work register and Unreleased changelog record this bounded admission.

No unrelated work was present initially. Native sources, dependencies,
installed resources, core Gochar judgments, BAV tables, source books,
website/Workspace, releases and deployment remain unchanged. The initial
verification checkpoint was local and uncommitted. Subsequent Git publication
does not change the version or create a release.
Only Python 3.14.3 was executed; other supported runtimes were not tested.

VED-017 forecast windows remain open: subject/blocker ingresses, retrograde
re-entry, interval ownership and resource coverage need their own admission.
VED-018/019 remain separate source/enrichment work. No predictive accuracy,
universal ayanamsa parity or new edition reconciliation is claimed.

## Git publication authorization and checks

The user authorized committing and pushing this exact package on 6 October
2026. Publication order is generated Git wiki `master` first, followed by
engine `main` with the updated wiki gitlink, canonical documentation, code and
tests. No forecast-window implementation is included.

Immediately before publication, both repositories were fetched and each
reported `0 0` against its owning remote branch. Current REST inventory, Git
wiki synchronization and whitespace checks passed. Python 3.14.3, engine
6.9.9, the required native extension and installed DE441 resource were
reconfirmed; both saved JUnit receipts were read and their 858 distinct
passing cases verified. Runtime code has not changed since those test runs.
The only publication-time content edit is this receipt update and its
generated wiki copy.

The publisher verifies both remote branch SHAs, parent wiki gitlink and clean
working trees after the two pushes. Git publication remains separate from
PyPI release, running-server rollout, website adoption and deployment.
