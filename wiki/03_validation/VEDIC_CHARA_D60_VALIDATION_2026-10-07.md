# Chara cycles and D60: implementation validation receipt

This records the earlier sign-only checkpoint. The subsequent
[full-profile extension](D60_FULL_POSITION_VALIDATION_2026-10-07.md) admits a
separately named modern profile; classical continuous-degree attribution is
still unestablished. Counts and decisions below remain this checkpoint's record.

Date: 7 October 2026. Decision: approved plan slices A/B/C complete locally;
slice D completes the **sign-only source admission branch**. Source-owned
continuous D60 placement remains explicitly open. VED-001 is locally complete;
VED-003 is a bounded admission with that remaining subitem.

The [approved plan](../06_roadmap/VEDIC_CHARA_D60_IMPLEMENTATION_PLAN_2026-10-07.md),
[Chara standard](../02_standards/CHARA_DASHA_CYCLE_STANDARD.md) and
[D60 source standard](../02_standards/D60_SOURCE_ADMISSION_STANDARD.md) govern
scope, source locators, compatibility and remaining evidence. The user
authorized implementation, not Git publication, release or deployment.

## Runtime and scope

- Checkout `C:\dev\moira`, branch `main`, starting commit
  `67b66de14cde0447730b0c9b57e5e14c1edd9935`; Moira 6.9.9.
- Project `.venv\Scripts\python.exe`, Python 3.14.3; required native extension
  `moira/_moira_native.cp314-win_amd64.pyd` loaded. These doctrine/transport
  changes have no admitted native counterpart and require no speculative port
  or native rebuild.
- `MOIRA_TEST_MODE=1`, `MOIRA_STRICT_KNOWN_ISSUES=1`,
  `MOIRA_NO_DOWNLOAD=1`; empty known-issues register, network deny by default,
  marked loopback only, external-network tests excluded.
- Resolver selected installed `C:\Users\nilad\.moira\kernels\de441.bsp`.
  Harness content probes confirmed DE441. Three new chart tests use the shared
  `moira_engine` serving reader and actual sidereal chart context; separate
  stubbed-context tests isolate transport/preflight. No kernel downloads.
- Initial modified work register and untracked research/plan documents were
  preserved. No unrelated engine family, website/Urania, kernel, harness,
  known-issue exemption, golden/snapshot artifact or tolerance was changed.

| File group | Result |
| --- | --- |
| `jaimini_extended`, Chara server models/route | Strict cycle/body/node/finite preflight, representable ordered intervals, frozen actual computation receipt; existing arithmetic retained |
| `varga`, Vedic facade | Four source-name corrections, explicit D60 enum/sign result/helper, canonical method receipt, sign-only strength selection and full-point rejection |
| Varga models/route/service/serializer | All eight placement shapes preserve nullable fields; new typed sign route; Vimshopaka receipt; truthful method applicability in OpenAPI |
| Root/facade/Vedic curation | Shared identities for `CharaDashaComputation`, `D60Method`, `D60SignResult`, `d60_sign`; new `Moira.d60_sign` admitted in method list and machine contract |
| Tests | New source/boundary/preflight/transport/strength/real-chart cases and explicit public API admission declarations |
| Standards/API/REST/Home/changelog/register | Current executable contract, migration values, source limits, generated REST inventory and dated completion links |

## Evidence and compatibility

Rao's published second-cycle Aries/Taurus durations are partial support for
Moira repetition. Synthetic fixtures isolate those durations and do not claim
to reconstruct the published chart/dates. Every retained Scorpio/Aquarius
co-lord branch is tested as implementation truth; complete source-chain
collation remains open. Fixed-year, selected lord mode, actual count,
direction and continuous ordered mahadasha/antardasha boundaries are checked.
Legacy five-field result construction retains unknown metadata instead of
inventing a historical convention. Invalid engine and HTTP inputs fail
explicitly before doctrine dispatch.

Santhanam BPHS I printed p.83/PDF p.82 was visually checked against its
fingerprinted local file. An additional primary-text transcription was
collated; its unknown printed base edition and Dandabhrt/Dandayudha variant
are recorded in the D60 standard. The commentary supports a sign law and the
Capricorn-to-Pisces example. Tests derive other signs from that law across all
twelve natal signs, both parities, exact half-degree boundaries and circular
limits. They supply no missing continuous-degree authority.

Literal odd/even ordinal fixtures cover the four corrected names: 6 Kinnara,
37 Sudha, 52 Dandayudha, 59 Bhramana. Repeated names remain legal. Shared
serializer tests cover all eight placement routes, including generic D60
`deity=null`; three actual DE441 chart requests confirm placement transport
and provenance. These are composition/transport checks, not an external
astronomical-accuracy or predictive-validity oracle.

An executable comparison against the trusted starting-commit Python modules
verified **720 D60 midpoints**, **48 Chara cases** (all Lagna signs, both cycle
counts, with/without nodes) and **28 default Vimshopaka cases** (seven planets,
four groups). Default numerical fields/periods/strength entries and totals
agree exactly. Exactly 48 deity occurrences change: four corrected ordinals
across twelve signs. Textual source claims and additive metadata/JSON fields
change intentionally. Legacy/manual full points and strength results may keep
unknown `d60_method=None`.

## Independently calculated strength consequence

Synthetic input: Sun 130, Moon 200, Mars 125, Mercury 315, Jupiter 105,
Venus Capricorn 13 degrees 25 minutes, Saturn 190 (sidereal degrees).
The existing D1 friendship convention makes Mercury Venus's great friend
and Jupiter its enemy: vargavishwa 18 versus 7. D60 sign/lord changes from
harmonic Gemini/Mercury to source Pisces/Jupiter. This is a convention-owned
arithmetic fixture, not a new independent validation of the friendship table.

| Group | D60 weight | Harmonic D60 points | Source D60 points | Harmonic total | Source total | Delta |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Dashavarga | 5.0 | 4.5 | 1.75 | 16.575 | 13.825 | -2.75 |
| Shodashvarga | 4.0 | 3.6 | 1.4 | 16.025 | 13.825 | -2.2 |

Every other division entry is unchanged; delta equals `(7-18)*weight/20`.
HTTP carries the same selected/applied method and contribution. Groups without
D60 return null applied metadata and reject a nondefault selection.

## Commands and results

All commands used the project runtime and the environment above. Private
machine-readable output resides in
`C:\dev\outputs\vedic-001-003-research-2026-10-07`; it is not a publication input.

| Selection | Result / receipt |
| --- | --- |
| Chara, deity, Varga, Shodashvarga, new admission, Vedic exports/facade, public audit, existing/new Varga HTTP (ten files) | Initial broad run: 366 passed, one failed, zero skipped; `implementation_core.xml`. Failure was the missing explicit admission of new `Moira.d60_sign` in the method-name declaration |
| New engine/HTTP admission files plus complete public audit after correction | 170 passed, zero failed/skipped; `implementation_final.xml`; covers every formerly failing node and final method/result/serializer code |
| Existing direct-input HTTP tests, `-k chara` | 10 passed, zero failed/skipped; `implementation_chara_http.xml` |
| Existing Phase-2 HTTP tests, `-k vimshopaka` | 3 passed, zero failed/skipped; `implementation_strength_http.xml` |
| Final Chara/D60 HTTP selection after fixed-year OpenAPI constant | 54 passed, zero failed/skipped; `implementation_final_http.xml` |
| Trusted-baseline executable compatibility probe | All 796 sampled cases pass exactly; `implementation_compatibility.json` |
| Scoped Ruff comparison | Zero introduced diagnostics in fifteen changed Python files. Existing 60 E402 root-import and five F811 facade-import diagnostics match starting commit; `lint_differential.json`. No broad lint cleanup or suppression |
| Documentation, generated REST and in-memory wiki preview | Owning doc guard, REST generator/check, new local links/code fences and in-memory page rendering pass; existing changelog file-URI links are preserved, not certified; generated Git wiki is not written |
| Git whitespace | `git diff --check` passes |

The focused pytest selections cover **380 distinct test nodes**, all passing
in their latest applicable run, zero skipped. Counts are deduplicated across
reruns; no claim of a single 380-test invocation or full repository suite.
The ordinary admission declarations are updated for explicitly added API;
protected snapshots/goldens and test policy remain unchanged. An initial
fixture-only failure (a manually allocated facade lacked its reader field)
was corrected in test setup before the broad selection. One attempted command
named a nonexistent standalone Vimshopaka unit file and collected no tests;
the actual owning Varga unit file and HTTP selections above supply coverage.

Reproduction uses `python -m pytest <listed owning files> -m 'not external_network'`,
`python scripts/check_doc_consistency.py`,
`python scripts/sync_rest_api_reference.py --check` and `git diff --check`,
with `.venv\Scripts\python.exe` substituted for `python`. No blanket full-engine
accuracy, full-suite, native-parity or all-Vedic-source claim follows.

## Remaining gate and publication state

Continuous source-owned D60 placement needs an identified edition/passage
defining within-sign degrees, endpoints, wrap and parity, plus source-owned
numerical fixtures. The admitted sign-only route and Vimshopaka selection do
not borrow harmonic degrees or close that gate. Full-cycle/co-lord Chara
source collation remains a separate research frontier.

Code/tests/canonical documents are locally changed. No commit, push, version
bump, release, generated-wiki publication, deployment or website/Urania adoption
is included in this request. The work register preserves these separate states.
