# VED-002 implementation plan: source-owned Sayanadi admission

**Status:** Approved plan executed locally; see the [standard](../02_standards/SAYANADI_ADMISSION_STANDARD.md) and [validation receipt](../03_validation/SAYANADI_VALIDATION_2026-10-08.md). The original proposed slices below are retained as the governing plan.
**Date:** 8 October 2026.
**Baseline:** engine `77d34158cef7c936fdf6613f9be18ba5e8fad5aa`, Moira 6.9.9.
**Authority:** [collated source research and admission decision](VEDIC_SAYANADI_SOURCE_RESEARCH_2026-10-08.md); [remaining-work register](VEDIC_REMAINING_WORK_REGISTER.md), VED-002 with VED-021/022.

## 1. Objective and scope

Repair the existing Sayanadi helper and admit a usable BPHS Navamsa-ordinal result consistently through standalone calculation, chart evaluation, curated Python/facade surfaces and typed REST. Preserve the existing four avastha families and their doctrine. Support the nine source-defined Sayanadi bodies without assigning other avastha families to nodes. Provide both caller-supplied ghati inputs and a source-visible birth/sunrise composition, with explicit unavailable states.

Use four finite slices, each with its own relevant tests and one final package receipt. The competing degree-based method remains a named research frontier; historical effect text remains conditional attributed material. Website/Urania, release and deployment remain outside this engine package. Source publication is a separate action.

| Slice | Deliverable | Exit gate |
| --- | --- | --- |
| A | Correct and strictly admit the standalone calculation | Printed intermediate witnesses and exact rational boundary classification pass. |
| B | Typed policy, inputs, trace and chart composition | Supplied/derived clocks, names, bodies and omitted/unavailable states remain inspectable. |
| C | Curated Python/facade and typed REST parity | Canonical engine objects and receipts survive direct and birth-chart transports. |
| D | Integrated validation, compatibility and documentation | Source fixtures, hostile inputs, real-reader composition and lifecycle gates pass without weakening baselines. |

## 2. Slice A: source fixtures and arithmetic repair

Keep the owning helper in [avasthas](../../moira/avasthas.py), retaining its existing positional argument order for valid callers. Require a recognized subject, its finite longitude, a finite supplied Moon longitude and finite Lagna. Reject boolean/string numeric coercion, missing Moon/subject, invalid name values and non-integer/non-positive supplied ghati ordinals before calculation. Preserve and document the longitude normalization domain, with exact wrap and boundary behavior; do not introduce an epsilon that moves a valid input across a classical cell boundary.

Establish a correct integer partition for the actual supplied float. An exact rational decomposition is an available standard-library reference/implementation approach; choose an efficient implementation only after it agrees with the independent audit at adjacent representable inputs. Partition ownership must be common to planet and Moon star classification and within-sign Navamsa classification. Do not change shared nakshatra or varga helpers beyond this technique without separately verifying their consumers.

Replace the mislabeled Santhanam fixture with Sun 7 degrees 12 minutes Taurus, name Sa=4, ghati ordinal 31, source-specified Moon star and Lagna sign. Assert main sum 51, index 3, first remainder 1 and second remainder 0. Any chosen exact Moon/Lagna longitudes are synthetic representatives, visibly labeled. Retain the old 38-degree/name-1 example only as a synthetic compatibility case with first remainder 10, not a classical witness.

Freeze Hora Ratnam's Navamsa-commentary Mars **state-only** example separately: main sum 57, index 9. Do not invent a source-owned name/substate for it. Keep Bala Bhadra's degree-based Sun witness in the research record, outside the selected calculation fixture. Add Rao's Mercury within-sign seventh Navamsa and 42.5 elapsed-ghati -> ordinal 43 examples for their actual component scopes.

The original 14,580-case independent classification sweep must produce zero state/substate disagreements after repair. Also assert the integer components, complete star/sign/ordinal coverage, state remainder-zero -> 12, negative/tiny wrap behavior, periodic normalization within the declared numeric domain, and every body's correct constants. Tests must contain independent literal expectations or rational evaluation, not expected values imported from the implementation's table.

## 3. Slice B: policy, name/time inputs and canonical result

### Selected source and names

Introduce a dedicated frozen Sayanadi policy/context rather than adding unrelated switches to the four-family dignity policy. Initially execute only the collated BPHS within-sign Navamsa-ordinal method. Record stable formulation/source identifiers, source locations, partition convention and actual time/name input bases. Supported names/spellings belong to a selected edition, not a universal alias table.

Admit either strict numeric initial value 1-5 or one of the 35 canonical Devanagari sounds in the collated table. Use mutually exclusive inputs, or require agreement when both are explicitly provided; the public contract must choose one clear rule. Prefer mutual exclusion for the first contract. Apply Unicode normalization only if its exact accepted forms are declared and tested. Reject unknown sounds, empty strings, ambiguous English transliterations and full names; caller chooses the initial and personal-name convention. Preserve the selected sound, resolved value and source mapping in the receipt.

### Birth ghati and sunrise composition

The direct path accepts a strict positive integer **ghati ordinal**, with receipt `caller_supplied_ordinal`. A separate elapsed-time adapter uses exact ghati/vighati or declared elapsed-second inputs and the source's ceiling convention, rather than coercing a decimal into the integer helper. One ghati is 1,440 seconds and one vighati 24 seconds. Declare zero elapsed -> ordinal 1 as Moira's exact-sunrise boundary choice. Reject negative, nonfinite, boolean and incompatible forms.

For a birth datetime/location path, reuse the admitted [daily Panchanga](../../moira/daily_panchanga.py), [rise/set](../../moira/rise_set.py), [time conversion](../../moira/julian.py) and serving-reader conventions. Inspect their actual API before choosing the minimum composition. Do not alter astronomical substrate arithmetic to obtain a desired ghati. Require an aware civil instant and explicit valid location; convert to the existing admitted time basis once. Find the actual previous sunrise and retain its instant, uncertainty/bracket if available, horizon policy, elapsed seconds/ghatis, selected ordinal and reader/frame receipt.

Pre-sunrise births belong to the preceding sunrise, not the civil date's later sunrise. Validate ordering against the next sunrise where available. Missing/polar sunrise yields typed `unavailable` with a reason and no fabricated ghati. Boundary uncertainty that could alter the integer must remain visible or prevent claiming a single resolved result. Do not clamp an actual interval to 60 ghatis. If an operational request bound is needed, name it as an operational choice and validate it independently of classical authority.

### Chart/result composition

Preserve existing result construction by appending optional fields where necessary; manually constructed legacy results carry unknown provenance rather than an invented source receipt. Engine-produced admitted results must supply canonical metadata and trace: normalized positions, planet/star/Navamsa ordinals, Moon star, Lagna sign, ghati/name values, multiplier/addend, total, state remainder/index, both substate remainders, selected source and context status.

Append optional Sayanadi context to `evaluate_avasthas`. Omission leaves the family explicitly `omitted`; partial/invalid direct context is an admission error, not omission. An attempted astronomical composition may be `unavailable` for a named astronomical reason. Complete valid context populates the seven existing per-planet slots. Put optional Rahu/Ketu Sayanadi results in a separate typed collection rather than inventing node Baladi/dignity results. Keep Lajjitadi's existing node inputs and Sayanadi's node evaluation controls distinct, with applied receipts.

Require both nodes for a chart node-pair input when node evaluation is selected; standalone selection of one source-defined body may remain valid. Reject extras/partial maps at engine and HTTP boundaries. Record true/mean node and ayanamsa/frame choices in birth-chart composition; do not invent an opposition tolerance or silently convert supplied-position frames.

Historical effect strings require source-located catalogue review. Keep their traditional conditions and attribution separate from computed state/substate. Do not treat an untested prose lookup as a house/dignity/phase evaluator. Numeric state/substate admission must not depend on a claim that every conditional prediction is evaluated.

## 4. Slice C: public and REST contracts

Curate the admitted helper, policy/context, trace/status and result vessels through [root](../../moira/__init__.py), [vedic](../../moira/vedic.py) and owning [facade](../../moira/_facade_vedic.py), preserving object identity. Facade methods for supplied positions and birth composition must call canonical engine functions and use the facade's own reader for astronomical work.

Extend existing `POST /v1/avasthas/evaluate` with optional typed Sayanadi context and nullable/status-bearing Sayanadi response fields. Add a finite standalone Sayanadi route for all nine admitted subjects and a distinct birth-chart composition route. Settle exact route names in the implementation before generating OpenAPI/reference docs; this plan does not claim they exist already.

Use existing strict REST scalar and error-envelope conventions. Reject unsupported profile identities, coercions, incomplete contexts, duplicate/extra body identities and invalid node maps before computation/resource allocation. Declare mutually exclusive direct ordinal/elapsed/time-derived request shapes. Return typed omitted/unavailable/evaluated states and canonical applied receipts. Copy engine values in serializers; never reconstruct state arithmetic, source provenance or clock selection in route code.

Minimum current owners are [REST models](../../moira_server/models/vedic_extended.py) and [router](../../moira_server/routers/vedic_extended.py). The current route serializes inline; introduce scoped service/serializer modules only if composition warrants them. Reuse existing reader/resource lifecycle rather than adding another implicit global engine. Check OpenAPI shapes, nullable metadata, response validation and real HTTP JSON values, including failures.

## 5. Slice D: package acceptance and compatibility

| Gate | Required evidence |
| --- | --- |
| Primary/source components | Corrected Santhanam full intermediate Sun case; Sharma edition/table collation; commentary-only Mars state scope; Rao ordinal/time cases; no borrowed degree-lineage fixture. |
| Boundary arithmetic | Zero disagreements in the frozen 14,580-case exact rational sweep, plus independently asserted component/wrap/remainder coverage; no changed tolerance or golden baseline. |
| Names and bodies | All 35 canonical tokens, all five values, all nine constants, sibilant distinctions, unsupported/ambiguous tokens, Moon requirement, node chart/standalone distinction. |
| Hostile admission | Engine and HTTP: booleans, numeric strings, NaN/infinity, wrong types, missing subject/Moon, unknown bodies, bad ghati/name ranges, partial contexts, conflicting clocks/names, unknown policies and node maps. |
| Composition | Optional-input omission; complete evaluation; named unavailability; sunrise boundary, pre-sunrise and night births, timezone/DST handling, missing/polar sunrise; source-visible rounding and uncertainty. |
| Public/transport | Root/vedic/facade object identity; standalone/chart/direct/date-derived parity; canonical trace, source/status and conditional-text provenance survive JSON without recomputation. |
| Reader/lifecycle | Real discovered and explicit configured-kernel birth charts use the serving reader; borrowed readers remain open; owned lifetimes close correctly; unavailable/resource failures are visible. |
| Existing behavior | The other four avastha families retain valid-call results; affected Vedic export/direct-input/route regressions pass; corrected invalid-input behavior is documented. |
| Documentation | Reconciled module/test claims, owning standard, REST reference/OpenAPI, migration examples, updated register and generated wiki through its generator; final scoped validation receipt. |

Run project `.venv` tests with downloads disabled, strict known-issue expiry and the repository's default external-network deny policy. Start with the two existing avastha test modules, then the new finite unit/server/integration slice. Broaden only for changed consumers or unresolved failures. Use source fixtures and exact independent arithmetic for classical computation; use real-kernel cases for astronomical composition and lifecycle, without presenting synthetic charts as published classical oracles.

**Observable compatibility changes:** invalid/coerced/missing-input calls formerly accepted by the standalone helper will fail deliberately; boundary state/substate outputs affected by the demonstrated partition bug will change; additive optional engine/JSON fields expose previously omitted truth. Preserve legacy result construction with unknown metadata and existing no-Sayanadi evaluation behavior. Do not silently change other avastha doctrine or promise existing clients a universal alternative-lineage method.

**Completion:** VED-002 closes only after all selected calculation, engine/public/facade, time composition and typed REST gates pass and the actual commands/results are recorded. VED-021/022 close only for this package's evidence/documentation. A broader degree-based tradition or predictive validation study is a separately scoped programme, not an unnamed gate preventing completion of the selected BPHS contract.
