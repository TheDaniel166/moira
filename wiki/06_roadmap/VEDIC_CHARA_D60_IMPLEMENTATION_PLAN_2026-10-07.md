# VED-001/003 implementation plan: Chara cycles, D60 deities and placement

**Status:** Approved plan, executed at the [sign/cycle implementation checkpoint](../03_validation/VEDIC_CHARA_D60_VALIDATION_2026-10-07.md).
The subsequent [full-position extension](D60_FULL_POSITION_SOURCE_RESEARCH_2026-10-07.md)
records the separately named modern profile; the original plan below is retained.
**Date:** 7 October 2026.
**Baseline:** engine `main`, `67b66de14cde0447730b0c9b57e5e14c1edd9935`, version 6.9.9.
**Authority and evidence:** [source research packet](VEDIC_CHARA_D60_SOURCE_RESEARCH_2026-10-07.md); [remaining-work register](VEDIC_REMAINING_WORK_REGISTER.md), VED-001/003 with VED-021/022 validation/documentation follow-through.

## 1. Objective and delivery order

Resolve the three researched findings in Moira engine and REST:

1. Bound the existing Chara formulation and expose its actual calculation conventions.
2. Preserve D60 deity transport and correct four identified source-name discrepancies.
3. Adjudicate D60 placement, then admit only the calculation object the sources support, consistently across placement and strength consumers.

Use **four reviewable implementation slices**, followed by one combined acceptance receipt. Source adjudication for placement can begin alongside the first three slices; placement code follows its source gate. Tests, policy truth and documentation accompany each slice rather than waiting for a final generic hardening phase.

| Slice | Deliverable | Dependency / exit condition |
| --- | --- | --- |
| A | Bounded Chara engine/public/REST contract | Existing formulation identified honestly; strict inputs and complete calculation metadata verified. |
| B | Nullable D60 deity transport | All eight placement routes preserve engine values, including explicit `null`. No placement arithmetic change. |
| C | Four source-name corrections | Independent ordinal fixtures, source coordinates and old-to-new compatibility receipt; corrected strings survive transport. |
| D | Source-admitted D60 placement convention | Written source adjudication, explicit method selection and coherent dependent consumers. Sign-only evidence cannot authorize a full longitude. |

This is a finite package, not a twelve-phase programme. Website/Urania, other Varga variants, additional Chara schools and alternative year clocks are separate scope decisions. This plan does not authorize publication or deployment.

## 2. Slice A — bounded Chara contract

### Engine input and compatibility policy

Keep `chara_dasha` in its current owner, with the existing first-cycle default and positional argument order. Admit strict integer `cycles` values **1 and 2**. Reject boolean, string, float, zero, negative and greater values before allocating periods. Two is the admitted product bound, not a universal traditional maximum.

Enforce complete seven-classical-body input in the engine as well as REST: finite numeric longitudes/lagna/epoch, no booleans or numeric coercion, no missing or overwrite keys. Continue the current longitude normalization convention; do not silently change its numeric domain to a different frame.

`node_longitudes=None` selects classical Mars/Saturn. Exactly Rahu and Ketu with finite values selects the **existing Moira co-lord rule**. Reject an explicit empty, partial or extra-key map before calculation, with a useful error. Do not invent a node-opposition tolerance. Record that this tightens formerly accepted empty-map and invalid-cycle behavior; callers using `{}` should use `None` or omit the field.

Preserve current sign/year/lord arithmetic, co-lord tie behavior, twelve equal antardashas and full second-cycle repetition. Check that all period and subperiod endpoints are finite and strictly ordered, with adjacent periods continuous. Reject an extreme finite epoch if floating-point precision collapses the intervals. Do not alter Julian-day arithmetic to calendar anniversaries or true tropical returns.

### Canonical calculation receipt

Add a dedicated frozen Chara calculation metadata vessel to the canonical result. Do not extend `JaiminiExtendedPolicy`, whose current switches govern arudha. Recommended evidence:

| Field | Contract |
| --- | --- |
| `formulation_id` | Stable identifier for the existing Moira formulation, linked to its governing specification and evidence limits. |
| `cycle_count` | Accepted requested count, 1 or 2; successful computation contains exactly twelve periods per cycle. |
| `cycle_policy` | `repeat_first_cycle`. |
| `lord_mode` | Classical seven-body lords or the existing Moira co-lord convention; no claim that every Jaimini lineage uses its full tie-break chain. |
| `year_basis` / `year_days` | Existing fixed Julian-year convention, 365.25 days. |
| `epoch_basis` | Caller-supplied Julian-day epoch; no inferred timescale conversion. |

Derive `period_count` from the engine result, validate its agreement with `cycle_count`, and serialize canonical truth. Avoid separate mutable requested/computed counters for a calculation that either completes entirely or raises. A per-period cycle index is unnecessary initially; groups of twelve are ordered and unambiguous.

Preserve the old five-field result-constructor form with an appended optional metadata field for manual legacy construction. `None` means **unknown provenance**, not invented default metadata. Every engine-produced result must supply the validated receipt; HTTP success must preserve it. New metadata types must share object identity through the owning module, root, facade and `vedic` curation.

Correct the first-cycle-only header, article/book misattribution, blanket verification statement and overclaimed co-lord notes. State that Rao's published example supports two repeated second-cycle durations, while the full twelve-sign repetition and uncollated tie-break chain remain identified existing Moira conventions. Keep citations and limitations in the formulation specification; do not offer unimplemented schools as executable choices.

### REST and tests

Add strict bounded `cycles=1` to the Chara request. Validate complete node pairs at model preflight and mirror engine rejection in the normal field-specific 422 envelope. Copy calculation metadata from the engine; do not rebuild the method, clock or node mode in the server.

Test default first-cycle numeric parity, both sequence directions, own-sign duration, all co-lord branches including exact ties, complete second-cycle repetition, hostile inputs at both boundaries, metadata/count consistency and epoch precision failure. Keep the Rao published duration witness distinct from a synthetic full-chart test or an exact-date oracle.

**Minimum runtime scope:** [engine](../../moira/jaimini_extended.py), [REST models](../../moira_server/models/vedic_extended.py), [route](../../moira_server/routers/vedic_extended.py); curated exports only for the new admitted metadata type. Focused tests include [Chara unit tests](../../tests/unit/test_jaimini_extended.py), [direct-input HTTP tests](../../tests/server/test_vedic_direct_input_hardening.py) and [export identity tests](../../tests/unit/test_vedic_surface_completeness.py).

## 3. Slices B/C — D60 transport and source names

### B: preserve the canonical field

Add nullable `deity` to [VargaPointResponse](../../moira_server/models/varga.py) and copy `point.deity` in the [shared serializer](../../moira_server/serializers/varga.py). The engine already owns assignment; no server table or reconstruction from divisor/name is needed.

Verify actual JSON values at all eight placement routes:

- `/v1/varga/generic`
- `/v1/varga/named`
- `/v1/varga/shodashvarga`
- `/v1/varga/named/batch`
- `/v1/varga/shodashvarga/batch`
- `/v1/varga/chart/named`
- `/v1/varga/chart/shodashvarga`
- `/v1/varga/chart/shodashvarga/batch`

Generic divisor 60 and other unenriched points return explicit `null`; named D60 retains its engine string. Nested responses preserve batch/body keys and chart provenance. OpenAPI must express nullable deity on the shared vessel. Existing successful numeric fields retain their values.

### C: correct exactly four entries

In [the engine table](../../moira/varga.py), correct the identified one-based ordinals:

| Ordinal | Old output | Corrected output from the reviewed Santhanam edition |
| --- | --- | --- |
| 6 | `Kindar` | `Kinnara` |
| 37 | `Suddh` | `Sudha` |
| 52 | `Dhannayudh` | `Dandayudha` |
| 59 | `Brahman` | `Bhramana` |

Retain other spellings in this slice. Document changes as source corrections, with exact edition/page coordinates and an old-to-new migration table. Do not describe historically different names as supported input aliases: the engine returns names rather than accepting them for calculation. Preserve all sixty ordered positions and repeated names; ordinal identity belongs in fixtures and the correction receipt. An extra public deity-identity API is not needed for this package.

Add independent literal ordinal/name fixtures to [D60 tests](../../tests/unit/test_d60_deities.py), not expectations imported from `SHASHTIAMSHA_DEITIES`. Exercise affected odd/even positions, half-degree and sign boundaries, adjacent representable values and normalization. Transport tests must include corrected values in scalar, nested, batch and chart response families. Distinguish the 720-midpoint structural check from source verification of names.

**Compatibility receipt:** `deity` is an additive JSON field; corrected Python strings are an observable change even though REST previously omitted them. Strict client schemas, string comparisons and saved results may need updating. Source correction does not change D60 numeric placement in slices B/C.

## 4. Slice D — resolve the D60 placement disagreement

### Required source-adjudication deliverable

Complete a bounded admission record within this package, using the researched chapter-6 verse, Santhanam commentary and an independently identified translation or Sanskrit/commentarial witness where accessible. Distinguish commentary from verse and republication from independent evidence. Record disagreement openly if collation does not resolve it; do not turn a calculator output into authority.

The record must specify:

- Which computational object is governed: deity order, sign placement, continuous within-sign degree, or a combination.
- Start sign, progression/parity rules, normalization and exact interval endpoints.
- Independent reproduction of Capricorn 13°25′ giving Pisces in the commentary, versus Gemini in Moira's existing harmonic method.
- Whether continuous `sign_degree` and `varga_longitude` are actually specified. A sign result alone cannot establish those quantities.
- A precise source/profile identifier, evidence status and unresolved limits. No generic claim of a universally correct “Parashari D60.”

### Method and compatibility policy

Preserve the current default and keep `calculate_varga(..., 60)` as generic harmonic arithmetic. Admit the collated source method as an **explicit selection**, with engine-owned method identity preserved in its results. A future default migration would require its own compatibility decision.

Use one D60 method selection/resolver consistently across named placement, sign-only dispatch and strength. Thread it through the relevant [facade helpers](../../moira/_facade_vedic.py), [REST services](../../moira_server/services/varga.py), request models and canonical result provenance. Reject unsupported methods rather than silently substituting harmonic placement. Non-default selection for a named division/group where D60 does not participate must have an explicit applicability contract; it cannot be reported as applied.

Two source-gate outcomes are permitted:

1. **Full placement supported:** implement a source-selected named D60 returning a complete `VargaPoint`, with the source-established degree convention. Route it consistently through Shodashvarga, scalar/batch/chart products, `varga_sign_index`, `vimshopaka_bala` and `vimshopaka_all`. Keep generic harmonic calculation separate.
2. **Only sign placement supported:** admit a separate typed sign-only result and corresponding typed REST surface. The sign-only dispatcher and Vimshopaka can consume that admitted sign rule. Full-point routes must reject that source-only selection until degree semantics are admitted; they must not attach borrowed harmonic degrees to a source-labelled point. Keep the full-placement subitem open with the exact missing evidence, source locator and closure criterion. This completes a sign-level admission without mislabelling it as complete D60 placement.

A source-attested but incompletely specified method remains visibly unadmitted. If even the sign algorithm cannot be resolved beyond the single example, the deliverable is a specific defer/dispute decision with the missing rule identified, rather than output-tuned arithmetic.

### Consumer audit and numerical acceptance

Current [shashtiamsha](../../moira/varga.py) delegates placement to `calculate_varga`. The D60 fallback in `varga_sign_index` separately feeds Vimshopaka. Changing only the wrapper would split named-chart and strength conventions.

D60's current Vimshopaka weight is **5.0 in Dashavarga** and **4.0 in Shodashvarga**. An admitted placement change can therefore alter lord, dignity, points and total even when deity lookup is unchanged. Show independently expected D60 sign/lord/dignity/points and resulting totals; keep unrelated division entries and the group weights unchanged. Preserve old default results as compatibility witnesses, not source authority.

Add D60 to dispatcher/placement parity tests, but also use independent source fixtures. Test the Capricorn example, multiple source-derived signs/parities and boundaries, coherent method receipts, unknown/inapplicable methods, and both weighted groups. Include [Vimshopaka REST](../../tests/server/test_server_vedic_phase2_routes.py), whose result vessel differs from the eight placement routes. Vargottama's existing D1/D9 comparison and Jaimini's D9 use are outside the numeric correction.

## 5. Files and owning documentation

| Area | Expected implementation scope |
| --- | --- |
| Chara | `moira/jaimini_extended.py`; `moira_server/models/vedic_extended.py`; `moira_server/routers/vedic_extended.py`; new metadata exports in `moira/__init__.py`, `moira/facade.py`, `moira/vedic.py`. |
| D60 names/calculation | `moira/varga.py`; a small dedicated D60 policy/result owner only if slice D needs it; admitted public exports. |
| D60 placement consumers | `moira/_facade_vedic.py`; Varga REST models/services/serializers and [router](../../moira_server/routers/varga.py) if the source gate requires a sign-only endpoint. |
| Unit/public tests | Chara, D60 deity, [Varga](../../tests/unit/test_varga.py), [Shodashvarga](../../tests/unit/test_shodashvarga.py), [Vedic facade](../../tests/unit/test_vedic_facade.py), export identity and explicit [public-name admission](../../tests/unit/test_api_surface_adversarial_audit.py) for new curated types. |
| HTTP tests | [Varga route tests](../../tests/server/test_server_varga_routes.py), selected direct-input Chara tests, Vimshopaka tests and method/provenance coverage. |
| Standards | New dedicated Chara cycle standard; [Varga standard](../02_standards/VARGA_BACKEND_STANDARD.md); [API reference](../02_standards/API_REFERENCE.md); [REST reference](../02_services/REST_API_REFERENCE.md); linked source/admission/validation receipts and work-register status. |

The existing [Jaimini backend standard](../02_standards/JAIMINI_BACKEND_STANDARD.md) governs Chara Karakas, so do not expand it into a Chara Dasha policy by name association. No admitted native Chara/Varga counterpart was found in the inspected native/dispatch surfaces; a new native implementation is not a dependency of this plan.

Before runtime edits, declare the final manifest and protected canonical-result/default/REST/source/validation implications. Preserve unrelated work. Avoid changing test harness policy, known-issue exemptions, snapshots or tolerances to conceal a failure. Verify the project runtime and actual reader prerequisites first.

## 6. Verification and completion

Use only `C:\dev\moira\.venv` for execution. Start from the prior research receipt: 140 engine and 10 selected Chara HTTP passes. Those were run at the research checkpoint and are not rerun or upgraded to new admission proof by this plan.

Expected focused command set after implementation, adjusted only for genuinely affected/new tests:

```powershell
$env:MOIRA_TEST_MODE='1'
$env:MOIRA_STRICT_KNOWN_ISSUES='1'
.\.venv\Scripts\python.exe -m pytest tests\unit\test_jaimini_extended.py tests\unit\test_d60_deities.py tests\unit\test_varga.py tests\unit\test_shodashvarga.py tests\unit\test_vedic_surface_completeness.py -m 'not external_network' -q
.\.venv\Scripts\python.exe -m pytest tests\server\test_vedic_direct_input_hardening.py -k chara -m 'not external_network' -q
.\.venv\Scripts\python.exe -m pytest tests\server\test_server_varga_routes.py tests\unit\test_vedic_facade.py -m 'not external_network' -q
.\.venv\Scripts\python.exe -m pytest tests\server\test_server_vedic_phase2_routes.py -k vimshopaka -m 'not external_network' -q
.\.venv\Scripts\python.exe scripts\check_doc_consistency.py
.\.venv\Scripts\python.exe scripts\sync_rest_api_reference.py --check
git diff --check
```

Additional tests for new method/result types and public-name admission are required if those objects are added. Identify actual kernel resources before chart-backed tests; no downloads or borrowed ambient reader. Use stubbed context checks for transport and a separately recorded real reader/chart integration check. A missing resource is a reported verification gap, not a silently successful result.

The combined receipt must state source authority/limits, commands and pass/fail/skip counts, engine/REST default parity, constructor and JSON compatibility, exact corrected name values, selected/applied placement conventions, numerical impact on strength, public identity, resource lifecycle and the remaining source gates. Completion is per slice: A/B/C may close while a specifically bounded full-placement question remains open. Do not mark source-unresolved placement complete because transport tests pass.

Canonical documentation must describe actual executable behavior, then generated REST/OpenAPI and wiki output must follow their owning tools. Commit/push, wiki-first publication, a version bump, release, deployment and website adoption are later separately requested operations.

## 7. Planning checkpoint scope

Only this new plan file is created in this turn. The existing modified work register and untracked research packet remain preserved. Runtime code, tests, source tables, generated wiki and Git index are unchanged. Read-only code/consumer inspection is complete; checks passed for 26 local file links, whitespace/code fences and in-memory source/engine link rendering through the owning wiki generator. No preview files were written and no implementation tests were run during planning.

## Subsequent implementation receipt

The user subsequently approved this plan. The
[7 October implementation receipt](../03_validation/VEDIC_CHARA_D60_VALIDATION_2026-10-07.md)
records the resulting bounded engine/REST admission and source-only D60
adjudication. The research/planning checkpoint above remains historical;
current executable truth belongs to the linked standards and receipt.
