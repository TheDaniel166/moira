# VED-012: source-defined yoga extensions implementation plan

Date: 12 October 2026. Status: all seven stages executed; selected package locally complete.

Governing evidence: [source research and current-runtime receipt](VEDIC_YOGA_EXTENSION_SOURCE_RESEARCH_2026-10-12.md).
The user subsequently authorized implementation through all seven stages.
The [execution receipt](../03_validation/YOGA_EXTENSION_VALIDATION_2026-10-12.md)
records 573 passing selected tests, source/HTTP parity, regression and cost
evidence, and the separate concurrent repository-wide docstring findings.
Commit/push, release and deployment remain separate actions. The sections
below preserve the approved requirements; the receipt records their delivery.

## 1. Intended result and finite scope

Deliver 21 source rule entries through one Python owner and equally capable
REST transport. Preserve source alternatives, clause witnesses, chart-frame
derivations and non-evaluated context. Existing six-family yoga results do
not acquire extra Navamsa/wealth/Raja rules by default.

| Proposed profile identity | Executable entries | Governing reading |
| --- | ---: | --- |
| `jp_sastri_7_14_v1` | 1 | Debilitated planet's D9 lord in natal kendra/trikona, with the movable-Lagna or movable-D9-Lagna-lord condition |
| `raman_300_252_all_debilitated_v1` | 1 | At least one D1-debilitated classical planet; every such planet exalted in D9 |
| `bphs_santhanam_41_2_15_v1` | 14 | Every named supporter required; per-supporter conjunction OR directed full aspect in 41.9-15 |
| `bphs_santhanam_39_selected_v1` | 5 | Separate 39.33-34, 36, 37, 38 and 39 entries, with branch and lord-role evidence |

The counts are source rules, not the number of body/branch witnesses or
predictions. Catalogue BPHS 39.35 as `research_required` with the specific
aspect-target problem in the research document. It must never be an
always-false evaluator disguised as supported functionality. The other
chapter-39 domains and unidentified "Raman Part II" citations remain
separate source leads. Completing this package does not certify them.

Also repair the demonstrated legacy Python/REST admission mismatch,
strict-boolean discrepancy, missing-motion proof state and policy receipt.
These are bounded contract repairs, not a rewrite of legacy yoga doctrine.

## 2. Ownership and compatibility decisions

Expected implementation owners, subject to the usual pre-edit declaration:

- `moira/yoga_extensions.py`: immutable context, typed results and the 21
  evaluators. `moira/yoga_extension_policy.py`: finite profile/rule catalogue,
  source records and admission states. Keep ordinary Python functions and
  named clauses; no user-programmable expression language or plugin engine.
- `moira/yogas.py`: shared admission and limited legacy evidence metadata.
  Extract a small internal admission helper only if both modules need it;
  do not refactor every Vedic subsystem.
- Existing `moira/varga.py` owns exact D9 calculation; existing dignity and
  sign-lord data own those definitions. New code must not implement a second
  Navamsa floor formula or repair a boundary by epsilon snapping.
- `moira/__init__.py`, `moira/facade.py`, `moira/vedic.py`, and
  `moira/_facade_vedic.py`: curated exports and a thin direct-input facade
  method. Exports must be the identical engine objects.
- Yoga models, service and router in `moira_server/`: strict transport and
  serialization only. Existing router registration should remain the owner.
- Targeted unit/server tests, source-derived fixtures and owning standards,
  API reference, validation receipt and remaining-work register.

Public vessels/exports, server contracts and protected validation artifacts
require the repository's protected-zone declaration before implementation.
No new dependency, native port, date search, birth rectification, kernel
download or website/Urania work is needed for this longitude-based product.

For correctly typed existing inputs, retain legacy policy choices, rule
ordering, names, formed/cancelled/present booleans and suppression behavior.
Invalid input rejection and additive evidence fields are intentional
compatibility changes and need migration notes. The legacy false boolean
for an unevaluated condition remains a compatibility field; its new state
field conveys that no false observation was established.

## 3. Proposed public and REST contract

### Engine and facade

Expose `list_yoga_extension_rules()` and
`evaluate_yoga_extensions(sidereal_longitudes, lagna_sidereal_lon, *,
profile_ids)` with named immutable policy/source/result vessels.
Provide `Moira.yoga_extensions_from_longitudes` as a thin delegation.
The catalogue must include the selected rules, source locators, fixed
assumptions, required inputs, admission status and deferred 39.35 entry.

Require exactly seven classical body names, finite numeric longitudes and
a finite numeric Lagna. Reject bools, numeric strings, unknown/missing body
keys, invalid policy types and unknown/duplicate/empty profile selections.
The extension accepts canonical degrees in `[0, 360)`; conversion from a
date, tropical coordinates or another chart frame is the caller's explicit
responsibility. Existing legacy finite-angle normalization remains unchanged.
There is no caller-supplied D9 map that could contradict D1.

`profile_ids` is required, with one to four known profiles. Applied receipts
name the catalogue version, source IDs, selected profile IDs and fixed
whole-sign/full-graha/D9 assumptions. Unsupported profiles are rejected
before evaluation. This package needs no speed, Shadbala, dasha, birth-time
or ancestry input. Reject unsupported extra inputs instead of ignoring them.

Build one call-local context: normalized D1 signs, Lagna-relative houses,
lord-role map, D9 signs, directed aspect matrix and own/debilitated/exalted
sign flags. Compute each of the seven body D9 positions and the Lagna D9
position at most once when a selected profile needs them. Wealth/Raja-only
requests should not compute unused D9 data. Do not introduce a global cache.

### Canonical proof objects

Every rule result includes stable `rule_id`, `profile_id`, source reference,
formation state, source-defined effect kind, typed clause observations,
participants with their lordship roles, branch witnesses and qualifications.
Keep chart/source/profile identity separate from the human-readable label.

- Formation states: `formed`, `not_formed`, `not_applicable`. Missing required
  chart inputs are errors, not `not_formed` or silently skipped rules.
- Clause/context states: `satisfied`, `not_satisfied`, `not_applicable`,
  `not_evaluated`. Observations identify body, role, D1/D9 frame, reference,
  house/sign and directed relation where relevant; prose alone is insufficient.
- Empty candidate sets do not satisfy a universal rule. JP retains all
  eligible body branches; Raman retains all debilitated-body obligations.
- A self-dispositor may satisfy a placement condition; one body holding two
  lordship roles does not create a conjunction or aspect to itself. Preserve
  both roles when one physical participant fills them.
- Strength/dasha/royal-lineage qualifications are attributed and explicitly
  not evaluated. Do not convert them into guessed cancellation clauses,
  wealth scores or outcome predictions.
- The selected passages' lack of a cancellation clause is recorded as
  `not_specified_by_selected_passage`, distinct from evaluating a cancellation
  and finding it false. D1 debilitation remains visible after a relief match.
- Source overlaps are cross-references. No precedence suppression or score
  aggregation is invented between these independent sources.

Constructors and serializers must enforce the relation between states and
derived summaries, reject forged/inconsistent vessels, and preserve frozen
content without mutable nested maps. Summary counts must distinguish rules
evaluated, returned, formed, not formed and not applicable.

### REST

Add two routes under the existing yoga router:

| Route | Contract |
| --- | --- |
| `GET /v1/yogas/extended/catalogue` | Resource-free typed discovery of the four proposed profiles, 21 supported rules, their exact assumptions and separately non-admitted source records |
| `POST /v1/yogas/extended/evaluate` | Required seven-body D1 map, Lagna and profile IDs; optional strict `include_absent` boolean, default true; complete typed proofs and applied-policy receipt |

Reuse the canonical engine preflight in the service boundary as appropriate;
Pydantic constraints supplement rather than define a rival admission policy.
Unknown/extra fields and all wrong scalar types return the repository's
structured 422 validation error. Keep source/admission errors explicit;
do not catch arbitrary exceptions and return an empty successful result.

The new default returns the bounded full proof set. When `include_absent`
is false, filter only confirmed `not_formed`/`not_applicable` results;
never remove qualifications attached to formed entries. Full engine counts
remain visible. Serialization must transport frame/source/branch evidence
and policy without recalculation or lossy free-form dictionaries.

## 4. Seven implementation stages

### Stage 1: freeze source admission and independent fixtures

Create the standard, immutable source records and finite rule catalogue
using the identities/pages/hashes in the research packet. Preserve original
verse versus translator commentary. Fix the 21 IDs and all AND/OR,
quantifier, reference-frame and aspect-direction choices before coding.

Freeze Chart 122's printed D1/D9 sign table independently of the evaluator.
Record synthetic representative longitudes separately, clearly labelled.
Create independently hand-derived positive and counterexample fixtures for
JP's two movable branches, all fourteen wealth entries and all five Raja
entries. Use all twelve ascendants where the wealth tables imply them.
Expected truth must not be generated by the function under test.

For 39.35, preserve the primary-source lead and the 84-case full-aspect
impossibility proof. Admission beyond a catalogue record requires a cited
resolution of aspect targets/type and a positive witness. Do not make the
other 21 rules depend on solving that separate reading.

Exit: each executable ID has a source/interpretation record and an
independent test specification; the ambiguous record is visibly excluded.

### Stage 2: admission and evidence repairs

Introduce consistent preflight for the aggregate and public yoga family
entry points: complete seven-body maps, real finite numbers, no bools,
known identities, typed policy, finite supplied speeds and strict doctrine
booleans. Preserve documented finite-angle normalization in the legacy
surface. Ensure aggregate calls do not repeatedly rebuild full contexts.

For legacy `YogaCondition`, add an `evaluation_state` field, deriving
`satisfied`/`not_satisfied` for ordinary existing constructions and explicitly
marking omitted-speed conditions `not_evaluated`. Enforce that a satisfied
state agrees with the existing boolean and that non-evaluated is not true.
Add `formation_state` to legacy `YogaResult`: `formed`, `not_formed` or
`indeterminate`. A Neecha Bhanga OR rule is formed if any evaluated branch
passes; if none passes and the motion branch lacks input, it is indeterminate.
Do not use OR aggregation for families whose source requires AND.

Preserve legacy booleans and present names, expose the new states through
REST, and retain indeterminate results when the old `include_absent=false`
filter is used. Document this intentional increase in retained evidence.
Return the applied legacy policy in the REST chart result as well.
Strictly reject coercible booleans in both policy and transport options.

Exit: the research probes become passing adversarial tests; valid legacy
outputs retain their previous field values, with additive truthful metadata.
No new source profile affects the legacy detector defaults.

### Stage 3: shared context and the two Navamsa rules

Implement the new immutable vessels/context and JP/Raman evaluators using
the existing exact D9 owner. Test natal houses of the D9 lord versus houses
in D9, D1 Lagna lord versus D9 Lagna lord, self-dispositors and the two
movable branches. Include charts where only one of the two source profiles
forms, so they cannot accidentally collapse into one rule.

For Raman, test one/multiple debilitated planets, one failing D9 member and
no debilitated planets. Exercise exact binary inputs around every D9 sign
partition and zodiac wrap; derive expectations with rational arithmetic,
not the implementation's float multiplication. Never use a tolerance to
reassign a boundary to the neighboring cell.

Exit: published Chart 122 sign witnesses, rational boundaries and all
independent clause cases pass; input maps and results remain immutable.

### Stage 4: wealth and selected royal-birth rules

Implement the research tables directly as named clauses. For 41.2-8 test
each required H11 member independently. For 41.9-15 test mixed conjunction
and directed-aspect supporters, single missing supporters, reverse-only
aspects, exchange-only distractors and special Mars/Jupiter/Saturn aspects.

Implement the five Raja entries with all specified alternatives, role
aliasing, distinct-body relation checks and source-overlap references.
Test conjunction versus mutual aspect versus opposition as different
witnesses even when they establish the same source result.

Exit: every admitted row/branch has independent positives and negatives;
no broad sambandha shortcut, vacuous truth, self-conjunction or invented
strength/cancellation condition survives the adversarial cases.

### Stage 5: public exports, facade and REST parity

Add curated identical-object exports and the thin facade method. Add both
routes, strict request/response models, canonical serialization, schema
examples and the legacy additive-state/policy transport from Stage 2.

Run every source fixture through module, root, facade, Vedic namespace,
service and actual HTTP paths. Compare source/branch/state/policy and counts
exactly. Inspect OpenAPI for bounded selections, enum identities, finite
strict numerics, extra-field rejection and typed non-admitted discovery.
Use configured app lifecycle fixtures; an in-process mocked server test
does not by itself establish normal startup behavior.

Exit: a client can discover, select and inspect every admitted profile;
no doctrine is implemented solely in the server or hidden in Python.

### Stage 6: adversarial, regression and cost validation

Combine the preceding targeted tests with export/admission regression and
the existing yoga/varga/REST baseline. Include invalid input before dispatch,
wrong policy objects, duplicate/unknown profile IDs, strings/bools/non-finite
numbers, missing and extra planets, unsupported contexts, forged vessels,
mutation attempts and all filtered-response cases.

Exhaustively cover twelve Lagna signs, relevant directed aspect pairs and
all D9 partitions with adjacent representable values. Verify four profiles
selected individually and together; subset results must match their results
in the combined request. Check deterministic ordering, no duplicate rule
IDs, exact returned/evaluated counts and no mutation of source fixtures.

Cost gates: zero ephemeris/resource/network calls during direct evaluation;
no D9 work for non-D9 selections and no more than eight D9 calls for a full
request. Measure repeated all-profile engine/HTTP runs on a fixed corpus,
including cold/warm timing and payload size; establish an observed baseline
without substituting a hardware-specific latency guess for correctness.
No global cache, skipped clauses or smaller validation corpus for speed.

Distinguish primary sign/verse validation, independent geometric invariants,
regression parity and transport fidelity in the receipt. Reconstructing
Chart 122's historical birth positions is a separate astronomical exercise
unless its missing frame details are explicitly selected; the sign table
is sufficient for the published rule witness. No predictive-accuracy claim.

Exit: all admitted source rows and public paths are exercised; repairs are
verified, no tolerances loosened and no required case silently skipped.

### Stage 7: documentation and closure receipt

Update the yoga source header, standard, API reference, policy catalogue,
examples, migration note, validation receipt and VED-012 register entry.
Replace the stale JP "not implemented" reference with the exact extension
identity after it exists. Correct the Raman availability claim through the
current register/research record; historical notes remain historical.

Run the release-facing documentation consistency guard and applicable
generated-inventory checks. When publication is authorized, regenerate
`moira.wiki` only with `scripts/sync_git_wiki.py`, review the intended files,
publish the generated wiki first and then the parent engine/gitlink.
Implementation completion alone does not authorize commit/push or release.

Exit: exact commands, counts, source fixtures, tolerances, runtime/resource
scope and unresolved source records are in the receipt. Mark the selected
21-entry package complete only after engine and REST acceptance. Preserve
39.35 and other chapter-specific extensions as explicit remaining work.

## 5. Starting verification slice

The research baseline has already passed 195 tests with no failures/skips:

```powershell
$env:MOIRA_NO_DOWNLOAD = '1'
$env:MOIRA_TEST_MODE = '1'
$env:MOIRA_STRICT_KNOWN_ISSUES = '1'
.\.venv\Scripts\python.exe -m pytest tests\unit\test_yogas.py tests\unit\test_varga_exact_partition.py tests\server\test_vedic_direct_input_hardening.py -q
```

Implementation should add focused files such as
`tests/unit/test_yoga_extensions.py`,
`tests/unit/test_yoga_extension_admission.py` and
`tests/server/test_server_yoga_extensions.py`, plus a small provenance-owned
fixture directory. Add the relevant export guard tests once symbols change;
do not start with a full-repository test run or regenerate protected
baselines merely to accept changed output.

## 6. Acceptance checklist

- [x] Exactly 21 admitted source rules, four named profiles and a visibly
  non-admitted 39.35 record; no claim of complete BPHS chapter coverage.
- [x] Printed Chart 122 witness plus independent table/branch expectations.
- [x] Canonical D9 and rational boundary validation with no numerical shortcuts.
- [x] Equal engine/REST admission, strict booleans and accurate evidence states.
- [x] All source/role/frame/quantifier/aspect and qualification evidence survives HTTP.
- [x] Existing valid legacy field values retained; explicit migration notes for repairs.
- [x] Bounded context work, no ephemeris dependency and measured performance.
- [x] Public curation, normal application lifecycle, documentation and validation receipt.

All selected implementation criteria are satisfied locally. See the receipt
for exact validation boundaries and the repository-wide preflight findings
outside this package. BPHS 39.35 and broader source extensions remain
explicitly outside executable admission. Generated Git-wiki publication,
commit/push and release are not part of this implementation action.
