# VED-013: Chara variants and Argala assessment implementation plan

**Date:** 12 October 2026. **Status:** All seven stages implemented and validated locally.
**Baseline:** `f8e9a615f04659c77a03713b302cb7189f4d890c`, Moira 6.9.9,
project Python 3.14.3. **Owner:** [VED-013](VEDIC_REMAINING_WORK_REGISTER.md).
**Evidence:** [source research packet](VEDIC_CHARA_ARGALA_SOURCE_RESEARCH_2026-10-12.md).
**Execution:** [validation receipt](../03_validation/VEDIC_CHARA_ARGALA_VALIDATION_2026-10-12.md)
and [public contract](../02_standards/JAIMINI_PROFILE_ASSESSMENT_STANDARD.md).

Deliver three additional Chara calculation recipes and three bounded Argala
assessment profiles, with the same discovery, admission, evidence and outcomes
in Python and REST. Preserve the existing Chara calculation and valid legacy
Argala calculations. Repair invalid-input discrepancies and inaccurate lineage
claims. Source arithmetic, calendar projection, count grade, character and
effective obstruction remain distinct contracts.

The user subsequently authorized implementation of all seven stages. Publication
remains a separate step. Website work,
new astronomical algorithms and an unrestricted strength-scoring framework are
outside this package. Completion applies to the named capabilities below; it
does not mean every Chara tradition or every Argala strength rule is resolved.

## 1. Selected profiles and admission boundaries

### 1.1 Chara

| Identity | Selected computation | Calendar and subperiod scope |
| --- | --- | --- |
| `moira_kn_rao_existing_v1` | Existing Lagna seed, ninth-sign footed sequence, sign-to-lord duration, current optional co-lord convention, no dignity adjustment | Existing one/two cycles, repeating duration cycle, 365.25-day clock and twelve antardashas remain unchanged on the legacy operation |
| `rangacharya_2007_method1_classical7_v1` | S08 printed 65-66: ordinary lords, Lagna seed, ninth-sign footed sequence, dasha-sign footed duration direction, count minus one and dignity adjustment | Exactly one cycle of twelve mahadasha arithmetic rows; optional explicitly identified Moira calendar projection; no antardashas |
| `rangacharya_2007_method2_male_classical7_v1` | S08 printed 66-68: Lagna seed, ordinary Lagna parity, modality sequences, lord-to-sign inclusive duration governed by lord-sign parity | Same bounded arithmetic/projection contract |
| `rangacharya_2007_female_prose_classical7_v1` | S08 printed 68-70: prakriti fourth seed, natal-Lagna parity, modality sequences, lord-to-sign count minus one governed by dasha-sign parity, prose-selected exceptions | Same bounded arithmetic/projection contract |

The manual identifies its first edition as 2007 despite the local filename's
2009 label. Its recipes are caller-selected profile identities. No demographic
inference selects the male/female branch. A source name is not a claim that every
older commentary in that lineage has been independently collated.

For the three new profiles, reject node/co-lord overrides, extra cycles,
antardasha requests, configurable dignity adjustments and alternate sequence
flags. Those switches would create combinations outside the selected recipes.

### 1.2 Argala

| Identity | Executable capabilities | Deliberate verdict limits |
| --- | --- | --- |
| `moira_argala_existing_v1` | Identity for the retained legacy seven-occupant, four-pair, count-only result, Ketu-occupied-reference reversal and two-malefic threshold | Existing boolean is a count convention; no new classical-strength claim |
| `bphs_santhanam_31_literal_assessment_v1` | Nine occupants; pairs 2/12, 4/10, 11/3, 5/9; count grades; three-malefic special third; node-reference reversal; directed quarter evidence; explicit count/qualification/strength composition | General planetary/group strength comparison and mixed quarter aggregation can be indeterminate |
| `pvr_2000_argala_count_first_v1` | W03 sections 10.6-10.7 and Exercise 16: nine occupants; four pairs; Ketu-occupied-reference reversal; greater/fewer counts decide, equal counts require strength | No invented strength tie-break or exact special-third threshold |
| `rath_argala_article_assessment_v1` | W04's nine-body subset: four ordinary pairs plus 8/6 and 7/1; Ketu-occupied-reference reversal; formation and observable sign-strength factors | No universal ordering of competing strength factors, exact special-third threshold, upagraha coverage or scalar strength score |

BPHS count grades belong to the BPHS profile. The other two return raw counts
and `count_grade.status=not_assessed`; they do not acquire BPHS grading by an
unannounced cross-source merge. All three expose the explicitly named character
component in section 3.4; its provenance is separate from the Argala author.
Rath's expanded positions and factors are a useful executable assessment even
when a final comparison is indeterminate.

Discovery must distinguish `legacy`, `admitted_bounded` and `research_required`,
with supported components, required inputs, source coordinates and limitations.
The evaluator accepts only its three new executable IDs; legacy entries point
to their existing operations. Research records are never accepted as selectors.

### 1.3 Named work that remains outside executable admission

| Candidate | Specific admission gate |
| --- | --- |
| Full BPHS Chara | Choose and source-lock co-lord/exaltation precedence, exact ties, node dignities, count interpretation and the contradictory example; separately admit subperiod seed/strength/sequence, clock and later cycles |
| PVR 2014 Chara | Reconcile Example 33 seed priority and Example 22 direction; specify every weakness cutoff/tie and implement the stated solar-year clock with independent astronomy validation |
| Rath Narayana | Separate family specification, Saturn/Ketu exceptions, subperiods and complementary second cycle with its own worked fixtures |
| Rangacharya Yogada/Argala potential | Admit aspecting-planet orders, the manual's D9/D3 conventions, contextual character, direction reading and competing merit/demerit aggregation |
| General Argala strength resolution | Source-owned comparator, participant pool, group aggregation, ties and missing-context semantics; no automatic Shadbala sum or borrowed dasa-lord hierarchy |

These are identified remaining capabilities, not claims that source material
does not exist. Catalogue limitations and the work register must retain them
after the bounded package is complete.

## 2. Source-conflict decisions

| Decision | Selected reading and consequence |
| --- | --- |
| C01: direction systems | Keep sequence direction and duration direction separate. Footed groups are not ordinary odd/even parity. No common boolean substitutes for both. |
| C02: method-1 precedence | Own-sign lord gives twelve before considering dignity. Otherwise subtract one from the inclusive count, then add one for exaltation or subtract one for debilitation. Use ordinary seven-body sign lords and sign-based dignity. |
| C03: zero years | Retain zero in the twelve-row arithmetic result. It consumes no time and produces no scheduled interval; never clamp to one/twelve or create artificial subperiods. |
| C04: female example | Select the explicit own-sign rule: Moon in Cancer gives Cancer twelve. Retain printed ten, computed twelve and the rule-based decision as separate fixture fields. The published table is not a twelve-of-twelve oracle. |
| C05: absent calendar doctrine | New source results contain years. Optional `moira_fixed_365_25_day_projection_v1` is a Moira engineering convention, not an attribution to the manual or a tropical solar year. No borrowed antardashas or second cycle. |
| C06: BPHS Chara table | Preserve the non-opposite node diagram and Scorpio duration disagreement as unresolved evidence. Do not alter positions, fabricate degrees or certify the complete table. |
| C07: Argala chart correction | Apply the volume's printed erratum adding Rahu in Gemini to the Argala chart. Preserve the uncorrected diagram and the erratum's identity. This resolves that omission only, not C06 in the other volume. |
| C08: count versus strength | BPHS greater-count OR stronger-causer logic and PVR count-first logic remain different. Equal counts do not prove equal strength; missing strength is never zero or false. |
| C09: directed quarters | Select only causer Q1/blocker Q4 and causer Q2/blocker Q3. Do not add Q3/Q2 or Q4/Q1. Use 7.5-degree sign quarters, not nakshatra padas. |
| C10: special third | BPHS requires at least three malefics. Preserve raw third-house blocker roles and independently report the special intervention; do not infer a global cancellation of the eleventh pair. Keep the legacy threshold of two under its legacy identity. |
| C11: reversal | BPHS reverses a reference explicitly identified as Rahu/Ketu. PVR/Rath reverse a reference whose sign contains Ketu. Occupancy, reference identity and direction must all be visible. |
| C12: source strength factors | Rath's Jupiter sign-aspect and own-sign examples establish factor witnesses, not a complete universal ranking. Under the admitted rasi geometry, its standard-nativity Jupiter in Pisces aspects both Gemini and Sagittarius. Preserve the source's selected winner separately; do not fabricate an asymmetric aspect or special-case the chart. |

**Additional evidence checked while planning:** S05, *BPHS*, Santhanam Vol. I,
one-based PDF 482 / printed 483, errata row for printed 313, explicitly adds
Rahu in Gemini to the chart. The page was visually inspected. This supersedes
the research packet's unresolved diagram/prose omission in section 4.1.
S05 PDF 26 / printed 27, chapter 3.11, was also visually checked for the
nine-body natural-character component. Both pages belong to the same witness
SHA-256 `13609f1af89541e070c798b8c70c6bfd74a8b9a71a71388913bf898e9f9ddf3f`.
Stage 1 reconciled these additions into the source packet and source ledger.
Implementation validation also corrected an unsourced negative Jupiter-aspect
fixture assertion under C12; the receipt records the independent geometry and
retained source judgment. It did not change the source to fit an output.

## 3. Executable semantics

### 3.1 Chara arithmetic and scheduling

Use zero-based signs internally and in transport; document source tables as
one-based/named signs. The footed-forward group is `{0,1,2,6,7,8}`. Method 1
uses the ninth sign for traversal and the dasha sign for duration direction.

For method 2, ordinary odd zodiacal signs traverse forward and even signs
backward. From the selected seed, movable sequences use offsets `0..11`,
fixed sequences successive five-step offsets, and dual sequences
`[0,4,8,1,5,9,2,6,10,3,7,11]`, multiplied by direction modulo twelve.
The female seed is Lagna plus three for odd Lagna, minus three for even Lagna.
Sequence modality is the seed's modality; direction remains natal-Lagna parity.

Male duration counts from lord sign to dasha sign by lord-sign parity,
inclusive, with no subtraction and own-sign twelve. Female duration counts
from lord sign to dasha sign by dasha-sign parity, subtracts one, with own-sign
twelve and opposite-sign ten taking precedence. Neither applies dignity changes.

Every row records ordinal, sign, lord/sign, count direction, inclusive count,
base years, selected exception, dignity adjustment, final integer years (0-12),
cumulative start/end years and rule IDs. Preserve all twelve distinct signs.
Invariant: nonnegative years, consistent derivation and cumulative sums; positive
durations must never be manufactured solely to satisfy calendar validation.

Calendar projection takes a strict finite caller-supplied epoch JD and the one
explicit projection ID. Compute endpoints from epoch plus cumulative years
times 365.25, not repeated cursor addition. Project positive rows to half-open
intervals `[start,end)`; link each interval to its arithmetic-row ordinal.
Zero rows carry `not_scheduled_zero_duration` and remain in arithmetic evidence.
Require finite, ordered, contiguous positive intervals and representable positive
spans. Reject huge finite epochs that collapse endpoints. Return no antardasha
arrays. With no projection request, calendar status is `not_requested`.

### 3.2 Argala formation and comparison

For each selected reference and pair, always return raw causers/blockers,
canonical body order, relative positions, direction, counts and formation.
BPHS grade maps count 0/1/2/3+ to none/limited/medium/excellent. This is an
ordinal count grade before obstruction, not an auspiciousness or strength score.

Keep `formation_state=absent|present` separate from
`effect_state=absent|unobstructed|obstructed|indeterminate`.
An indeterminate state requires reason codes, not a generic caveat string.
The initial bounded profiles have no admitted universal strength comparator;
`strength_comparison` is `not_required` or `indeterminate` with its reason.
`balanced` is reserved conceptually for an actually established equal-strength
comparison. The implemented enum excludes it because no selected profile can
establish it; counts/factors tying never emits that verdict.

| Condition | BPHS literal assessment | PVR count-first | Rath article assessment |
| --- | --- | --- | --- |
| No causers | Absent | Absent | Absent |
| Causers and no blockers | Unobstructed | Unobstructed | Unobstructed |
| More causers than blockers | Unobstructed by the selected greater-number rule | Unobstructed | Indeterminate; return counts/factors |
| More blockers than causers | Strength-dependent; apply quarter qualification below | Obstructed | Indeterminate; return counts/factors |
| Equal nonzero counts | Strength-dependent; apply quarter qualification below | Indeterminate: strength comparator not admitted | Indeterminate; no equal-strength inference |

For Rath, compute the observable factors illustrated by the source: own-sign
occupancy of the compared signs and Jupiter's Jaimini rasi aspect to each sign.
Reuse `moira.jaimini_extended.rasi_drishti_of` after checking its independent
geometry fixtures; use rasi drishti, not graha drishti. Do not
infer a winner by arbitrary factor weights or priority. Preserve the published
example's stated winner in the source fixture separately from the runtime's
bounded assessment. Formed intervention is not a predicted life outcome.

### 3.3 BPHS quarter evidence and composition

With longitude input, build the full directed causer-by-blocker matrix. Each
witness records body IDs, signs, relative positions, within-sign degrees,
quarter indices and whether it is one of the two admitted directed pairs.
Quarters own `[0,7.5)`, `[7.5,15)`, `[15,22.5)`, `[22.5,30)`.
Exact next-sign boundaries belong to the next sign; use no rounding epsilon.
With sign-only input, qualification is unavailable, never fabricated.

Composition is explicit and conservative:

1. Formation absence, no blockers, and BPHS's strict count victory resolve as
   above. Qualification restricts obstruction; it cannot reverse that selected
   count victory. Keep its independent evidence even when not needed to decide.
2. Otherwise, if degrees are absent, return `indeterminate/degrees_required`.
3. If no directed pair qualifies, obstruction fails: `unobstructed` under
   this literal qualification reading.
4. If the singleton pair qualifies, or all matrix entries qualify, retain the
   strength-dependent result: `indeterminate/strength_comparator_not_admitted`.
5. For a mixed matrix, return
   `indeterminate/multioccupant_quarter_composition_unestablished`. Preserve
   per-causer eligible-blocker lists, without a maximum-matching, filtered-count
   or all-causers-covered verdict presented as classical doctrine.

This selects a documented composition of the chapter's clauses. Fixture
expectations must distinguish the source's pair qualification, the count rule
and this combined assessment; matching one component does not certify another.

### 3.4 Character and special-third component

Select `bphs_santhanam_3_11_root_same_sign_v1`: Jupiter/Venus benefic;
Sun/Mars/Saturn/Rahu/Ketu malefic; Moon by increasing/decreasing phase;
Mercury malefic when sharing a sign with a classified malefic, otherwise benefic.
Evaluate Moon before Mercury; all nine bodies participate in Mercury association.
Use elongation `[0,180)` for the bright half and `[180,360)` for the dark half,
with exact conjunction/opposition ownership identified as an engineering choice.
The root-verse reading does not silently include the translator's additional
Moon benefic-aspect relief or Rangacharya's debilitated-Venus convention.

This is an explicitly sourced component composition for the new profiles.
Do not change the legacy yoga classifier's seven-body behavior. Reuse existing
owned classification primitives only if they express these exact semantics;
otherwise keep this small versioned component inside the new Argala owner.

For sign-only input, Moon's phase is `indeterminate/requires_longitude`.
Mercury is malefic if a known malefic shares its sign, indeterminate if its only
potential malefic associate is the unresolved Moon, otherwise benefic. Character
of a group is benefic, malefic or mixed only when established by its members;
otherwise it is indeterminate. Known benefic and malefic members already establish
mixed character despite an additional unknown member. Return every member's state.

For BPHS special third, compute minimum/maximum possible malefic counts:
minimum >=3 establishes presence, maximum <3 establishes absence, otherwise
presence is indeterminate. Report its source-described special effect separately
from ordinary intervention character and obstruction. PVR/Rath instead report
`not_assessed/special_third_threshold_not_admitted`; no threshold is guessed.

## 4. Engine and REST contract

### 4.1 Shared engine ownership

Add focused owners:

- `moira/jaimini_profile_policy.py`: immutable sources, rules, conflicts,
  profiles, capability/admission catalogue and `list_jaimini_profiles()`.
- `moira/_jaimini_profile_inputs.py`: strict admission and immutable snapshots
  for the new chart/reference/projection inputs; compatible legacy Argala helpers.
- `moira/chara_profiles.py`: `evaluate_chara_profile`, arithmetic vessels and
  separate projection. Keep existing `CharaDashaPeriod/Result` unchanged.
- `moira/argala_assessment.py`: `assess_argala`, pair/quarter/character/factor
  witnesses and canonical outcome composition.

Public input chart vessels have a discriminated `basis=signs|sidereal_longitudes`.
Chara requires exactly seven classical positions and Lagna; Argala requires all
nine and Lagna. Sign values are strict integers 0-11; new longitude values are
strict finite numbers in `[0,360)`. No bool/string coercion, extra bodies,
half-supplied node pairs or simultaneous representations. A sign chart carries
no invented degree precision. Its typed adapters are engine-owned and available
identically to direct and REST callers; the server implements no conversion rule.
In particular, 360 degrees is rejected by the new canonical input contract;
zodiac-wrap fixtures compare the last valid longitude with zero. The legacy
operations retain their existing circular-angle admission.

Argala references are explicit `lagna`, `house` (1-12) or `planet` (nine IDs).
Require one to twenty-two references, reject duplicate identities, and return
canonical order. Lagna, house 1 and a node in that sign remain distinct semantic
references where the selected source reverses only the node reference. Each
response records reference identity, actual sign and direction reason.

One profile per computation request keeps source ownership unambiguous. Multiple
profile comparisons use separate calls against the same chart. No implicit
profile default on new operations. Do not accept user strength scores, custom
rule lists, arbitrary callbacks or unsourced comparison overrides.

All new public results use frozen vessels and immutable tuple contents, validate
their invariants, and snapshot caller maps. Receipts include catalogue/profile
and component versions, source/rule IDs, input precision, participant pool,
reference/direction policy, supported/unsupported assessments and projection
identity when used. Missing context cannot become an empty participant list.

### 4.2 Legacy repair and compatibility

In `moira/jaimini_extended.py::argala`, validate the exact seven-body map,
finite non-boolean Lagna and every supplied node value before sign arithmetic.
Reject unknown node keys, malformed containers and ignored invalid Rahu values.
Preserve legacy finite circular-angle normalization and optional node maps:
`None`, empty, Rahu-only, Ketu-only and the complete pair remain valid.

Keep every valid numeric/body/boolean result, threshold and raw third-house role.
Correct the lineage/docstring to identify the retained Moira count convention
and explain coexistence of raw blocker and special-third roles. Add an optional
trailing computation receipt to the legacy result without breaking positional
construction; engine-produced results always supply it, manually constructed
legacy objects may report unknown metadata. Transport it additively through REST.
Document the deliberate textual correction and invalid-input tightening.
Do not relabel this computation as the newly admitted BPHS/PVR/Rath profiles.

Retain existing Chara request/response literals, epochs, co-lord tie-breaks,
cycles and antardasha behavior. A new zero-capable mahadasha type must not
weaken the existing positive-interval and mandatory-antardasha contract.

### 4.3 Public and HTTP surface

Export identical owning objects through `moira/__init__.py`, `moira/vedic.py`
and thin `Moira` facade methods. Add strict models in
`moira_server/models/jaimini_profiles.py`, thin service/serialization in
`moira_server/services/jaimini_profiles.py`, and routes on the existing Jaimini
router in `moira_server/routers/vedic_extended.py`:

| Method and path | Contract |
| --- | --- |
| `GET /v1/jaimini/extended/profiles` | Complete typed catalogue including executable, retained legacy and research-only entries |
| `POST /v1/jaimini/extended/chara-dasha/profile` | One new Chara profile, discriminated chart, optional explicit projection; twelve arithmetic rows and a separately typed schedule |
| `POST /v1/jaimini/extended/argala/assessment` | One new Argala profile, nine-body chart, bounded typed references; full formation, grade, character, comparison and qualification evidence |

Use `_StrictModel`, discriminated unions, bounded fields and enum identities.
OpenAPI must show required nodes, signs versus longitudes, projection choices,
uncertainty reason codes and executable-selector restrictions. Catalogue entry
IDs and evaluator selector enums have different scopes; do not type research
entries as though executable. Reject unknown/extra fields and cross-family IDs.

Services revalidate caller-constructed models before engine dispatch, then
serialize the owning typed result without reevaluating doctrine. Engine invalid
inputs raise explicit value/type errors; corresponding HTTP requests return 422.
Invariant failures are defects, not silently relabeled client errors. No response
filter in this first version hides absent or indeterminate evidence. Read-only
calculations must use the established application lifecycle without adding an
ephemeris requirement to their execution path.

## 5. Independent validation fixtures

Create `tests/fixtures/jaimini_profiles/` with a source manifest, README,
`chara_source_cases.json`, `argala_source_cases.json`, and
`source_conflicts.json`. Freeze expectations before evaluator implementation.
Record edition/author, source hash, printed and one-based PDF pages, transcription
method, input precision, expected fields and evidence class. Include small
numerical transcriptions and derivations, not redistributed books/scans.

| Corpus | Required discriminating evidence |
| --- | --- |
| Rangacharya sequences | All 24 printed male/female sequence rows, all 288 cells, independently transcribed; every Lagna, parity and modality; exact post-trine transitions |
| Rangacharya durations | Method-1 Scorpio/Libra/Virgo 7/8/4; seven printed method-2 durations; twelve female values with the Cancer ten/twelve conflict retained; independent own, adjacent, opposite, exalted, debilitated and zero cases |
| Calendar | Hand/rational cumulative years converted with the declared fixed clock; zero-row omission only from intervals; epoch, every endpoint and adjacent floats; collapsed/overflowed epoch rejection; source years unchanged by projection |
| BPHS Argala | Corrected printed 313 chart using the printed 483 erratum; node reference versus the same occupied house reference; 0/1/2/3+ grades; two versus three malefics; count victory, strength dependency and raw/special role coexistence |
| PVR Argala | Exercise 16's full twelve-reference/eight-position occupancy table, including Ketu's fourth and Rahu's tenth from Scorpio, and reversal at Aquarius; greater/fewer/equal counts |
| Rath Argala | 8/6 and 7/1 membership, node participation, Jupiter sign-aspect and own-sign factor witnesses; preserve source-stated judgments separately from the bounded runtime comparator |
| Degree quarters | Both directed positive pairs; negative reverse pairs; all sixteen quarter combinations; all twelve sign boundaries and 7.5/15/22.5 offsets with adjacent representable values; singleton, all-qualified, no-qualified and mixed matrices |
| Character | Nine-body classification, node-associated Mercury, waxing/waning boundaries, sign-only Moon/Mercury uncertainty, group character and minimum/maximum special-third counts |
| Source conflicts | Female Cancer; corrected BPHS Argala omission; unresolved BPHS Chara diagram/table; PVR 2014 contradictions; no discovery-only ID accepted for execution |

Maintain three distinct kinds of expected data: literal published values,
selected-profile values derived from the stated rule/decision, and synthetic
counterexamples. Never overwrite one with another. Sign-only witnesses test
sign precision directly; any additional representative degrees are synthetic
and cannot validate historical birth positions or unavailable source quarters.

Independent reference arithmetic must not import production evaluators, sequence
builders, sign/quarter helpers or policy-generated expected answers. Use printed
arrays for sequence oracles, hand-derived duration examples, and rational
partitions of the exact binary input for boundary expectations. Source hashes
establish identity, not correctness; regression parity and REST round trips
establish compatibility/transport, not independent doctrinal validation.

## 6. Seven implementation stages and exit gates

### Stage 1: source decisions, catalogue specification and fixture lock

Reconcile the two newly inspected BPHS pages, transcribe the complete fixture
tables, freeze the selected IDs/clauses and conflict ledger, and define all
capability and uncertainty states. Establish the source examples before any
evaluator can influence expected values. Leave research-only entries explicit.

**Exit:** every executable clause has source coordinates plus independent
positive/negative expectations; printed and selected values remain distinguishable.

### Stage 2: legacy admission repair and strict input contracts

Capture valid legacy snapshots, repair direct Argala admission, add its accurate
receipt/lineage transport, and implement the shared new chart/reference/projection
admission. Keep existing Chara vessels unchanged. Reject invalid inputs before
doctrine dispatch, including forged policy/request objects and ignored values.

**Exit:** all four observed direct/REST discrepancies become matched rejections;
empty/partial legacy node-map behavior and valid results retain parity.

### Stage 3: three Chara recipes and explicit calendar projection

Implement separate sequence, duration and projection steps with immutable
derivation witnesses. Cover all table rows, exceptions and zero-duration behavior.
Reject unsupported co-lords/cycles/antars rather than silently falling back.

**Exit:** 288 sequence cells, seven male durations, the female selected reading,
method-1 examples and independent calendar/boundary cases all pass. Default
Chara still produces its unchanged one/two-cycle output.

### Stage 4: Argala assessment and uncertainty composition

Implement typed reference resolution, nine-body occupancy, the character
component, three pair catalogues, BPHS grades/special-third/quarter matrix,
PVR count priority, Rath factor witnesses and the explicit composition tables.
Use known/possible counts only for uncertainty propagation, not strength scoring.

**Exit:** source occupancy tables and every state transition pass. No equal-count
tie becomes equal strength, no omitted node becomes absent, and mixed quarter
evidence cannot collapse into a fabricated boolean.

### Stage 5: public exports, facade and REST

Add discovery and both computation routes, typed response serialization,
schema examples and additive legacy receipt transport. Run every applicable
source fixture through owner, root, Vedic namespace, facade, service and actual
HTTP. Compare all evidence fields and reasons, not only final signs/booleans.

**Exit:** every admitted capability is discoverable and equally usable in Python
and REST; normal application startup and OpenAPI validation are exercised.

### Stage 6: adversarial, regression and bounded-cost validation

Test booleans/strings/nonfinite and huge numbers, missing/extra bodies, wrong
maps/unions/IDs, duplicate references, sign/longitude limits, invalid projection,
unknown context and result mutation. Test dict insertion-order invariance,
canonical ordering, all reference directions and isolation between profiles.
Do not add a general zodiac-rotation invariant to dignity or parity rules;
these deliberately depend on named signs.

Argala requests are bounded to nine bodies, twenty-two references and six pairs:
at most 132 pair summaries and a conservative maximum 10,692 degree-pair
witnesses. Actual disjoint occupancy produces fewer; implementation must never
build an unbounded caller-defined product. Chara always has twelve arithmetic
rows and at most twelve intervals. Verify no network, kernel, birth-chart or
resource-reader calls in direct evaluation. Avoid global caches and new deps.
Measure repeated engine/HTTP timings and response sizes on a fixed maximal
fixture; preserve all evidence and validation if optimizing.

Run targeted new tests, the legacy baseline and public-surface guards. Any
normal startup resource checks in integration tests must be recorded separately
from the kernel-free arithmetic claim. No tolerance relaxation, regenerated
expected answers or unexplained skipped required cases.

**Exit:** exact source, independent arithmetic, regression, transport and cost
results are separately reported; adversarial findings are repaired and retested.

### Stage 7: standards, generated references and closure receipt

Update the Chara standard, add an Argala assessment standard, document selectors,
precision/uncertainty states and migration behavior, and reconcile the source
packet/register. Record exact commands, source hashes, cases, results and remaining
research-only capabilities in a validation receipt under `wiki/03_validation/`.
Do not mark the whole VED-013 frontier universally complete.

Check docstrings, doc consistency, release identity, generated API inventory and
REST reference. Source edits may shift unrelated generated line references;
regenerate the owning inventory and inspect its diff instead of weakening its
guard. Canonical wiki is `wiki/`; use `scripts/sync_git_wiki.py` for its generated
mirror. Commit/push, nested wiki publication and release need their own requested
publication step; when authorized, publish the generated wiki before its parent
gitlink. Preserve unrelated light-box work throughout.

**Exit:** the selected package has a reproducible engine/REST validation receipt,
accurate claims and explicit remaining admission gates.

## 7. Verification entry points and completion criteria

Add focused tests such as `tests/unit/test_chara_profiles.py`,
`tests/unit/test_argala_assessment.py`,
`tests/unit/test_jaimini_profile_admission.py` and
`tests/server/test_server_jaimini_profiles.py`. Extend the existing direct-input
and curated-public-surface guards rather than creating parallel policy checks.

The research baseline previously passed **251 tests, zero failures/errors/skips**;
that receipt predates implementation and is not validation of this plan's profiles.
Start with:

```powershell
$env:MOIRA_NO_DOWNLOAD = '1'
$env:MOIRA_TEST_MODE = '1'
$env:MOIRA_STRICT_KNOWN_ISSUES = '1'
.\.venv\Scripts\python.exe -m pytest tests/unit/test_jaimini_extended.py tests/unit/test_vedic_chara_d60_admission.py tests/server/test_vedic_chara_d60_admission.py tests/server/test_vedic_direct_input_hardening.py -m 'not external_network' -q
```

Then run the new focused tests, relevant Jaimini/API facade regressions and
`tests/unit/test_api_surface_adversarial_audit.py`. Run the existing docstring
preflight and these release-facing checks after generated owners are updated:

```powershell
.\.venv\Scripts\python.exe tests/unit/test_docstring_governance.py
.\.venv\Scripts\python.exe scripts/check_doc_consistency.py
.\.venv\Scripts\python.exe scripts/check_release_identity.py
.\.venv\Scripts\python.exe scripts/generate_hellenistic_inventory.py --check
.\.venv\Scripts\python.exe scripts/sync_rest_api_reference.py --check
.\.venv\Scripts\python.exe scripts/sync_git_wiki.py --check
```

Public exports, canonical result semantics, server contracts and validation
evidence are protected zones. The implementation turn must make its pre-edit
declaration, inspect current dirty work and use the project `.venv`. No native
substrate change is needed for these bounded sign/degree computations.

- [x] Three new source-specific Chara recipes pass independent tables and durations.
- [x] Zero years, projection scope and absent subperiod doctrine remain explicit.
- [x] Three Argala assessment profiles expose their exact supported components.
- [x] Count grades, character, qualification and effective obstruction never conflate.
- [x] Source conflicts/errata and indeterminate outcomes survive every public surface.
- [x] Legacy valid outputs remain compatible; invalid direct/REST inputs agree.
- [x] Fixture expectations are independent of production evaluators.
- [x] Bounded cost, normal HTTP lifecycle, schema, docs and generated guards pass.
- [x] Closure names completed capabilities and preserves concrete remaining gates.
