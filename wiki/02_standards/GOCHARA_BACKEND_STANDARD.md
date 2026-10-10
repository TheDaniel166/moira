# Gochara snapshot backend standard

Architecture, invariant freeze and final public curation: 6 October 2026. Domain: seven-classical-planet, natal-Moon snapshot evaluation under the collated Phaladeepika profile. All twelve constitutional gates are complete for this bounded domain; their receipt appears in the [constitutional ledger](../06_roadmap/GOCHARA_CONSTITUTIONAL_LEDGER.md).

## Governing object

The source-bound snapshot owns supplied sidereal positions, inclusive natal-Moon sign counting, source-specific indications, ordinary Vedha occupancy and independent raw own-BAV testimony. It preserves a favorable baseline alongside obstruction, exemption, missing observations and explicit layer omissions. Structural summaries and networks derive from those local results.

The engine does not decide which tradition is universally correct. `GocharaPolicy` records the selected executable profile and evaluation scope. `gochara_doctrine_options()` reports source alternatives and disputes with admission status and limitations. A catalogue record is not an executable preset.

This standard freezes the bounded snapshot domain. Nodes, counter-Vedha, sign-part timing, dasha or dignity overrides, nakshatra/chakra techniques, Murthi, dated forecasts and remedies remain independent admissions. Completion of the constitutional process for this core does not imply implementation of those extensions.

VED-017 adds a separately owned [date-derived compositor](GOCHARA_DATE_DERIVED_STANDARD.md).
It derives complete natal/transit inputs with explicit clock/frame evidence
and optional same-birth raw BAV, then calls this unchanged judgment core.
Ingress searches and dated forecast windows remain open.

## Authority and corpus

The executable profile is `phaladeepika_26_sastri_1950_seven_classical`: Mantreswara, *Phaladeepika*, V. Subrahmanya Sastri, second edition 1950. [Primary scan](https://www.wisdomlib.org/uploads/ocr/essays/phaladeepika/phaladeepika-2nd-ed-1950-by-v-subrahmanya-sastri-text.pdf), SHA-256 `f4b0b71735c788457a4fb4bf98524c058af89b095a72617bcf50546578018fd1`.

| Object | Authority | Corpus |
| --- | --- | --- |
| Natal Moon sign reference | 26.1 | Printed p.286 / PDF p.321 |
| Favorable membership | 26.2 | Seven sets, 36 favorable cells |
| Directed Vedha and exemptions | 26.3–8 | 36 directed pairs; Sun/Saturn and Moon/Mercury exceptions |
| Individual indications | 26.9–23 | 84 original paraphrases with verse/theme fixture anchors |
| Raw BAV context | 26.41, with explicitly limited engine scope | Own unreduced natal BAV, absolute transit sign, no threshold override |

The core source fixture is `tests/fixtures/gochara_phaladeepika_26.json`, independently collated from the printed pages, not generated from runtime tables. The original [core doctrine](../01_doctrines/GOCHARA_PHASE1_DOCTRINE.md) retains the complete numerical table and initial verification receipt.

The comparative research also inspected *Brihat Samhita* CIV, Sastri/Bhat 1946, in the local library; *Prasna Marga* XXII, [Raman 1992 scan](https://storage.yandexcloud.net/j108/library/j8jiaafw/Panangadu_Nambudhiri_-_Prasna_Marga_%28Part_II%29.pdf); Kapoor's *Phaladeepika* translation; Sastri's *Jataka Parijata* commentary; and Rao's [author-hosted modern text](https://www.vedicastrologer.org/articles/vedic_astro_textbook.pdf). The research report, inventory, scan hashes and inspected page ranges remain in `C:/dev/outputs/gochar-research-2026-10-06/`. Research copies are not distributed with the engine. Transcription leads are labelled as leads, not treated as printed-source admission.

## Policy axes and defaults

`GocharaPolicy` is frozen. Enum values are required; arbitrary strings or catalogue objects cannot select unadmitted rules. The source profile, reference and participant universe form one admitted domain. Engine scope controls describe what was evaluated; they do not imply a new textual school.

| Axis | Default | Admitted alternatives or boundary |
| --- | --- | --- |
| Source profile | `GocharaSourceProfile.PHALADEEPICA_26` | Only this complete profile is executable. Other source treatments remain separately catalogued. |
| Reference | `natal_moon_rasi` | Fixed by the profile. Lagna, Sun and nakshatra references need independent admission. |
| Subjects/blockers | Seven classical planets | Fixed conservative participation policy. Nodes and outer planets are rejected. The text's nodal baseline is not denied by this engine restriction. |
| Vedha scope | `GocharaVedhaMode.ORDINARY` | `BASELINE_ONLY` omits the layer and reports `omitted_by_policy` for favorable subjects. |
| Input completeness | `GocharaCompleteness.RETAIN_PARTIAL` | `REQUIRE_COMPLETE` requires all seven transit positions, including in baseline-only scope. |
| Raw BAV | `GocharaBavMode.RAW_IF_SUPPLIED` | `OMIT` rejects supplied tables; `REQUIRE_ALL_RAW` requires a table for every supplied subject. No mode interprets four or creates a strength override. |
| Activation | Whole-sign snapshot membership | Decanate/half-sign timing is not evaluated. Membership is not a claim about event fruition. |
| Astronomy | Caller-supplied sidereal positions | Caller owns epoch-specific ayanamsa and correction policy. The evaluator does not infer or certify them. |

The default policy exactly preserves the initial core's numerical rules, indications, ordinary Vedha and partial-input behavior. Each snapshot and local assessment retains its policy. `policy.selected_options` returns eight cited decisions in fixed axis order, including engine-scope and astronomy assumptions.

## Debate and admission surface

There are 30 catalogue entries across 16 topics: 12 admitted choices, nine source-attested but unadmitted alternatives, four disputes, three research questions and two products outside snapshot scope. These counts describe this catalogue, not an exhaustive census of Jyotish traditions.

| Status | Meaning |
| --- | --- |
| `admitted` | Executable choice or fixed decision within this standard. |
| `source_attested_not_admitted` | An inspected source attests the concept; complete operational semantics and fixtures are not yet admitted. |
| `disputed_not_admitted` | The inspected texts or editions conflict. No blended, repaired or alternate runtime rule is implied. |
| `research_required` | Source, geometry, participant or timing questions remain open. |
| `outside_snapshot_scope` | A separately scoped product or interpretation is required. |

Every `GocharaDoctrineOption` has a stable ID, topic, typed status, authority kind, source locators, statement and limitation. `textual`, `modern_author`, `research` and `engine_scope` distinguish where the decision comes from. In particular, completeness and omission controls are engineering decisions, not verses attributed to a classical author.

Important recorded distinctions:

| Topic | Evidence and boundary |
| --- | --- |
| Nodes | Phaladeepika 26.2 includes favorable position 10; Prasna Marga 22.51 uses 3, 6, 11 with blocking 12, 9, 5. Ketu narrative, blocker participation, exemptions and mean/true astronomy remain separate questions. |
| Counter-Vedha | Prasna Marga 22.34–35, 43 and 53 attest relief. It requires worked cases and overlap/exception policy; reversing all 36 pairs is not admitted. |
| Venus blockers | Phaladeepika 26.8 gives 11→3 and 12→6; Rao's Table 63 reverses the last two blockers. This remains a recorded discrepancy. |
| Mars tenth-position narrative | Phaladeepika 26.16, Brihat Samhita 104.17 and Prasna Marga 22.9 differ. The selected narrative retains its source; unlisted membership does not mean one universal adverse label. |
| Prasna Marga numerical sequences | The inspected 1992 edition contains conflicting lists in 22.36, 38, 40–41, 47, 49–50. Their cause is unresolved; no automatic repair is admitted. |
| Sign-part timing | Phaladeepika 26.25's decanates and Brihat Samhita 104.49–50's sign portions are different policies. |
| Four rekhas | Passage/commentary context differs. The engine retains raw 0–8 values and leaves existing BAV conventions unchanged. |
| Strength/context | Dasha, dignity, combustion and different aspect systems provide distinct testimony; no universal combined score is established. |
| Murthi | Rao's modern formulation uses the Moon at exact ingress. Earlier authority and retrograde re-entry ownership require admission. |
| Nakshatra/chakra objects | Phaladeepika 26.26 onward supplies distinct techniques; 27/28-position conventions require their own geometry and fixtures. |

Additional alternatives can be catalogued without making them executable. Runtime admission requires a named authority, a complete governing object, ambiguity policy, independent worked fixtures and a corresponding standard revision. A user cannot enable a disputed table by supplying a string, an arbitrary dictionary or a catalogue entry.

## Local result and relation semantics

`GocharaBaselineClass` has `FAVORABLE` and `OUTSIDE_FAVORABLE_SET`. The second is membership information, not a generic bad/neutral assessment. The individual indication and verse remain authoritative within the selected edition.

Ordinary Vedha states are `not_applicable`, `blocked`, `unobstructed`, `incomplete` and `omitted_by_policy`. A known non-exempt blocker proves `blocked` even if other eligible bodies are missing. `vedha_observation_complete` independently reports whether all eligible positions were observed; it returns `None` for omitted or inapplicable layers. Exempt bodies do not count as eligible missing blockers.

Every detected directed occupancy is a `GocharaVedhaWitness`. `relation_class` distinguishes non-exempt obstruction from exempt occupancy; `directed_pair` exposes the source pair. `active_vedha_witnesses`, `exempt_vedha_witnesses` and `eligible_blockers` are derived views. An exempt occupant alongside a real blocker cannot cancel that blocker. No witness means neither universal clearance nor counter-Vedha relief.

`GocharaBavAvailability` distinguishes raw supplied, not supplied and omitted by policy. Supplied values must be the subject's own unreduced natal BAV. Shape, integer bounds and subject identity are checked. Birth identity and reduction provenance cannot be certified because the existing BAV vessel lacks that metadata.

## Integration, aggregate and network semantics

`GocharaLocalProfile` combines the authoritative assessment into five descriptive conditions: favorable/unobstructed, favorable/blocked, favorable/incomplete, favorable/Vedha omitted, and outside the favorable set. Raw BAV remains independent. These are traceable testimony states, not outcome ratings.

`GocharaChartSummary` partitions observed local profiles, retains raw-BAV availability and missing subjects, and reports condition counts. `incomplete_verdict_planets` and `incomplete_observation_planets` differ: a confirmed blocker can give a complete obstruction verdict while other blocker observations remain incomplete. Absent bodies are never counted as observed unfavorable or unobstructed subjects.

`GocharaVedhaNetwork` projects known directed occupancy. An active edge points **blocker → subject**. Exempt edges are retained separately. Nodes represent observed bodies; degree counts cover known non-exempt edges only. Missing bodies are listed separately, not fabricated as zero-degree nodes. `observed_unconnected_planets` describes the observed active-edge projection, not a completed graph over missing bodies. An omitted Vedha layer supplies no assertion of unconnectedness.

Reciprocal edges retain both source relations. They do not create automatic relief. Graph degrees are not planetary importance, causal influence or astrological strength scores. `GocharaSubsystemProfile` derives local profiles, summary and network from one snapshot and policy, without independently supplied aggregate payloads.

## Invariant and failure register

- Longitudes are finite real degrees; booleans and non-real values are rejected. Modulo normalization preserves last-sign ownership if a tiny negative remainder rounds to exactly 360. Exact multiples of 30 belong to the next sign.
- Natal and transit sign indices are absolute 0–11; inclusive Moon-relative positions are 1–12. Own BAV lookup uses the absolute transit sign.
- Supplied positions are unique, nonempty, classical and canonically ordered. Unknown bodies and absent-subject BAV tables are rejected.
- Raw BAV counts are copied into integer tuples in 0–8. Duplicate, mismatched or policy-contradictory tables are rejected. Mutable inputs cannot change an existing snapshot.
- Derived result fields are not independent constructor inputs. Frozen vessels reject ordinary mutation; replacing a lawful input recomputes dependent fields.
- Every assessment in a snapshot carries the same policy and exact position collection. Strict completeness applies to direct vessels as well as the helper API.
- Detected witnesses partition into active and exempt occupancy. `blocked` requires an active witness; `unobstructed` requires complete eligible observations with no active witness.
- Local conditions derive solely from preserved baseline/ordinary-Vedha states; raw BAV never rewrites them.
- Condition counts sum to observed subjects. Favorable and outside-favorable groups partition observed subjects. Favorable conditions partition favorable membership.
- Network active/exempt edges are disjoint and retain source witnesses. Active-edge subjects match the aggregate blocked subjects. Incoming and outgoing degree sums each equal known active-edge count.
- Local, aggregate and network layers agree on policy, missing subjects, canonical order and observation completeness.
- Catalogue IDs are unique; selected choices are admitted and source-located. Unsupported profile, node, counter-Vedha and threshold values cannot execute.

Inputs with wrong types raise `TypeError`; invalid values or contradictory scope raise `ValueError`; lookups for an absent classical subject raise `KeyError`. No test waiver, oracle substitution, silent filtering, hidden remedy or score is part of this domain.

## Validation codex

Source conformance: all 84 baseline/indication cells under all twelve natal reference signs, and all 36 Vedha pairs against every other classical participant under all twelve reference signs. The initial core fixture verifies selected-edition rules, not astronomical positions or predictive performance.

Constitutional validation additionally exercises all 12 combinations of Vedha scope, input completeness and BAV mode; the five local conditions; partial blocked observations; exempt/active partitions; reciprocal edges; aggregate and graph reconciliation; mutation isolation; direct-vessel misuse; deterministic ordering; pickle round trips; catalogue status separation; and unsupported-option rejection.

Run from `C:/dev/moira`, using the project `.venv`:

```powershell
$env:MOIRA_TEST_MODE='1'
$env:MOIRA_STRICT_KNOWN_ISSUES='1'
.\.venv\Scripts\python.exe -m pytest tests/unit/test_gochara.py tests/unit/test_gochara_constitutional.py -m 'not external_network' -o addopts='--import-mode=importlib' -q
.\.venv\Scripts\ruff.exe check moira/gochara.py moira/gochara_policy.py tests/unit/test_gochara.py tests/unit/test_gochara_constitutional.py --no-fix --output-format concise
```

The three existing docstring-governance helpers are also scoped to both new engine modules. Executable examples are run, not merely syntax-checked. Public curation is verified by export identity tests and the existing explicit API-surface audit. Exact final outcomes, surrounding checks and remaining pre-existing failures are recorded in the constitutional ledger.

## Stable surface and examples

The frozen surface is 28 names through `moira.gochara`, package root, facade and Vedic convenience surface. The policy owner additionally curates its eleven policy/constants names through `moira.gochara_policy.__all__`. Internal source tables and assembly helpers remain excluded.

| Group | Public names |
| --- | --- |
| Constants/default | `GOCHARA_PROFILE`, `GOCHARA_PLANETS`, `DEFAULT_GOCHARA_POLICY` |
| Policy | `GocharaPolicy`, `GocharaSourceProfile`, `GocharaVedhaMode`, `GocharaCompleteness`, `GocharaBavMode` |
| Admission catalogue | `GocharaAdmissionStatus`, `GocharaDoctrineOption`, `gochara_doctrine_options` |
| Snapshot/relation | `GocharaPosition`, `GocharaVedhaWitness`, `GocharaPlanetResult`, `GocharaResult`, `GocharaVedhaStatus`, `gochara_from_positions` |
| Descriptive classes | `GocharaBaselineClass`, `GocharaBavAvailability`, `GocharaVedhaRelationClass`, `GocharaLocalCondition` |
| Derived vessels | `GocharaLocalProfile`, `GocharaChartSummary`, `GocharaNetworkNode`, `GocharaVedhaNetwork`, `GocharaSubsystemProfile` |
| Derived constructors | `gochara_local_profiles`, `gochara_subsystem_profile` |

```python
from moira import gochara_from_positions, gochara_subsystem_profile
from moira import (
    GocharaPolicy, GocharaVedhaMode, gochara_doctrine_options,
)

policy = GocharaPolicy(vedha_mode=GocharaVedhaMode.BASELINE_ONLY)
snapshot = gochara_from_positions(5.0, {"Sun": 65.0}, policy=policy)
profile = gochara_subsystem_profile(snapshot)
assert snapshot.for_planet("Sun").vedha_status.value == "omitted_by_policy"
assert profile.chart_summary.omitted_vedha_planets == ("Sun",)
assert not profile.vedha_network.vedha_evaluated
assert snapshot.policy.reference == "natal_moon_rasi"
assert all(o.status.value != "admitted" for o in gochara_doctrine_options("nodes"))
```

```python
from moira.gochara import gochara_from_positions, gochara_subsystem_profile

snapshot = gochara_from_positions(0.0, {"Mercury": 210.0, "Venus": 0.0})
profile = gochara_subsystem_profile(snapshot)
assert profile.chart_summary.blocked_planets == ("Mercury", "Venus")
assert profile.chart_summary.incomplete_observation_planets == ("Mercury", "Venus")
assert [(w.blocker.planet, w.subject.planet) for w in profile.vedha_network.active_edges] == [
    ("Venus", "Mercury"), ("Mercury", "Venus")
]
```

These examples use supplied illustrative positions. Astronomy, ingress searches, predictive accuracy, website delivery, deployment and release publication are outside this standard's validation claims.
