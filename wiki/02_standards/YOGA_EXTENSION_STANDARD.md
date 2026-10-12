# Source-defined yoga extensions — VED-012

Status: selected package implemented and validated, 12 October 2026; source
publication authorized in the validation receipt. Catalogue version:
`ved012.1`. Package release and deployment remain separate.

Owners: `moira/yoga_extension_policy.py` and `moira/yoga_extensions.py`.
The [research packet](../06_roadmap/VEDIC_YOGA_EXTENSION_SOURCE_RESEARCH_2026-10-12.md)
records the inspected editions, scan hashes, pages, classical verses,
translator commentary and selected interpretations. The
[validation receipt](../03_validation/YOGA_EXTENSION_VALIDATION_2026-10-12.md)
distinguishes source witnesses, geometric tests, regression and transport.

## Admitted profiles

| Required profile ID | Entries | Exact selected reading |
| --- | ---: | --- |
| `jp_sastri_7_14_v1` | 1 | Any D1-debilitated body whose D9 sign lord occupies a D1 Lagna kendra/trikona, AND either movable D1 Lagna or movable D9 sign of the D1 Lagna lord |
| `raman_300_252_all_debilitated_v1` | 1 | A nonempty set of D1-debilitated bodies, ALL exalted in D9; the selected plural reading |
| `bphs_santhanam_41_2_15_v1` | 14 | 41.2–8: own-sign H5 resident and ALL named H11 occupants. 41.9–15: own-sign H1 resident and ALL named supporters, each conjunct OR directing its full aspect at that resident |
| `bphs_santhanam_39_selected_v1` | 5 | Separate 39.33–34, 36, 37, 38, 39 entries with all prescribed branches and lordship roles |

The catalogue contains 22 records: 21 admitted rules and BPHS 39.35 with
`admission=research_required`. The latter cannot execute. Its aspect targets
and type require resolution; demanding that each supporter fully aspect
both opposite H4/H10 occupants is impossible under the selected aspect
model. Other BPHS chapter-39 domains and the old unidentified “Raman Part II”
citation remain separate source leads. These limits do not block the
21 admitted rules.

There is no silent rule merging or precedence between profiles. Legacy
Kendra/Trikona overlap appears as a cross-reference. New results do not alter
legacy yoga defaults, erase D1 dignity, predict wealth/status, or invent
strength/dasha thresholds or cancellation rules.

## Engine admission and numerical ownership

`evaluate_yoga_extensions(sidereal_longitudes, lagna_sidereal_lon, *, profile_ids)`
requires exactly Sun, Moon, Mars, Mercury, Jupiter, Venus and Saturn, each a
finite numeric longitude in `[0,360)`, and a Lagna in the same range. Bools,
numeric strings, missing/extra bodies, unknown/duplicate profiles and empty
selections fail with `ValueError`. Select one to four profiles explicitly
using a list or tuple; output order is catalogue order.

Inputs are already sidereal D1 degrees. Ayanamsa, epoch and upstream
astronomical frame conversion belong to the caller. No D9 map, birth-time,
motion, strength or ancestry input is accepted by this extension.

The immutable call-local context uses natal whole-sign houses, the existing
classical lord/dignity tables, and directed full graha aspects from the yoga
owner. Conjunction/opposition/aspect require different physical bodies;
one body may hold several placement roles or be its own D9 dispositor.
Ordinary full aspects are seventh; Mars adds fourth/eighth, Jupiter
fifth/ninth and Saturn third/tenth. No sign-aspect or exchange shortcut is
substituted for these relations.

`moira.varga.navamsa` owns D9 computation, including exact rational partition
semantics for binary input values. All seven body D9 positions are computed
once when required; D9 Lagna is unused. Wealth/Raja-only selections perform
zero D9 calls. There is no ephemeris access, resource lookup or global cache
in direct evaluation. Relations are bounded sign-table operations rather
than a second chart calculation.

## Evidence contract

Frozen result tuples retain source identity, passage/pages/hash, rule and
profile ID, selected interpretation, typed clauses and AND branches. A rule
combines those branches with ANY. Each clause identifies the observed body,
lordship role, D1/D9 frame, sign, house/reference where relevant, and directed
related body. Clause state must agree with its predicate and observations.
Branch/rule summaries and counts are derived, not caller-written booleans.

| Object | State semantics |
| --- | --- |
| Formation | `formed`, `not_formed`, `not_applicable` |
| Evaluated clause | `satisfied`, `not_satisfied` |
| Qualification | `assessment=not_evaluated`, with source/passage/context |
| Cancellation assessment | `not_specified_by_selected_passage` |

`not_applicable` is used only by the Navamsa profiles when there are no
D1-debilitated bodies. Missing required chart inputs are errors. The ALL
rule never passes on an empty set. Non-evaluated strength/dasha/ancestry
context is a separate qualification rather than a false formation clause.
BPHS 41.16/17 dasha/strength context and 39.34 royal-lineage context retain
their attribution. Historical outcome claims are not evaluated.

Counts identify evaluated, formed, not formed and not applicable rules.
HTTP adds returned count after filtering. Counts refer to rules, not branch
witnesses or numbers of predictions. Serializers validate typed observations
and chart consistency, then transport the engine evidence without deriving
new doctrine. Transport accepts chart inputs only, never client proof trees.

## Public access and example

The catalogue, evaluator and eleven policy/source/result types are identical
objects at their defining modules, `moira`, `moira.facade` and `moira.vedic`.
`Moira.yoga_extensions_from_longitudes` delegates to the same evaluator.
The module function is sufficient for resource-free supplied-input use.

```python
from moira import evaluate_yoga_extensions

# Synthetic degrees representing the published Chart 122 sign table.
result = evaluate_yoga_extensions(
    {"Sun": 201, "Moon": 171, "Mars": 111, "Mercury": 181,
     "Jupiter": 328, "Venus": 214, "Saturn": 84},
    271,
    profile_ids=["raman_300_252_all_debilitated_v1"],
)
assert result.evaluated_count == 1
assert result.results[0].formation_state == "formed"
```

## REST contract

`GET /v1/yogas/extended/catalogue` returns typed profiles, source rules,
deferred records, required inputs, range and fixed computation assumptions.

`POST /v1/yogas/extended/evaluate` accepts the same input field names as the
engine plus strict boolean `include_absent`, default **true**. Schema enums
bound the four profiles. Numeric bounds, body identities, required inputs
and extra-field rejection appear in OpenAPI, with a synthetic Chart 122
example. Invalid input produces the normal structured 422
`validation_error` envelope before engine dispatch.

The response contains applied policy, chart positions, complete typed rule
proofs and all counts. `include_absent=false` returns only formed rules with
their qualifications; evaluated counts remain unchanged. It can validly
return zero rules. Default legacy `POST /v1/yogas/evaluate` behavior remains
a separate contract.

## Legacy migration notes

All public legacy yoga family functions and the classifier now share strict
seven-body/finite-number/policy validation. Legacy finite-angle modulo
normalization remains supported. Supplied speed maps may be partial but
contain only known bodies and finite numbers. Doctrine booleans and REST
`include_absent` reject strings and integers instead of coercing them.

`YogaCondition.evaluation_state` distinguishes omitted motion from observed
direct motion. `YogaResult.formation_state` is `indeterminate` when no
Neecha Bhanga OR branch passes and its speed branch is unevaluated; any
satisfied branch still establishes formation. Existing boolean values are
retained for compatibility. REST returns these additive states and the
applied legacy policy, and preserves indeterminate rows even when absent
results are filtered. Clients assuming only formed rows must now inspect
`formation_state` explicitly. The JP citation now points to its separate
extension profile. No new profile runs implicitly in the legacy evaluator.
