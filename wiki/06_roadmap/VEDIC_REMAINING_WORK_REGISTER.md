# Vedic remaining work register

**Status:** Active documentation register; implementation requires a separately authorized work package.
**Last reconciled:** 8 October 2026.
**Baseline:** engine `main`, `cdd83ecaff6daa75012080c50207fed6cdb4467d`, version 6.9.9; includes the VED-001/003 source-publication package below. VED-005 is now `LOCAL_COMPLETE` for the selected 30-route admission, reader and policy repair; see section 20. The user authorized its engine/wiki source-publication package on 8 October 2026.
**Scope:** Moira engine, curated Python surfaces, REST contracts, source evidence and validation. Website and Urania adoption are separate product work.

This is the current index of remaining Vedic work. It supersedes the Vedic backlog claims in the [original completion roadmap](vedic_jyotish_completion.md), [Phase 2 gap register](vedic_jyotish_phase2_gaps.md), [paused Tier 2 tracker](TIER2_VEDIC_WORK_TRACKER.md), the Vedic entries in the [frontiers register](ENGINE_FRONTIERS_AND_POLISH_REGISTER.md), and section 6.2 of the [August coverage audit](../07_audit/ASTROLOGY_COVERAGE_FRONTIER_AUDIT_2026-08.md). Those records remain historical evidence, including their source leads and earlier pauses.

The [6 October surface receipt](VEDIC_SURFACE_REST_COMPLETENESS_2026-10-06.md) records the completed export/Gochar REST package. It is a completion receipt, not the remaining-work list. Source presence, public export, REST exposure, source validation, release and deployment are distinct states.

**Current extensions:** VED-015 is committed and pushed in engine
`0b34f22841eb6b5f7dace9128b4d01cc11c480d3` and wiki
`4c12d88b9825d562be38f7d3b67c37a703449735`. Its
[source, policy, engine/REST and verification receipt](../02_standards/DAILY_PANCHANGA_STANDARD.md)
records the admitted daily contract. Source publication is not deployment.
The user subsequently selected lunar-month and festival rules; VED-023/024
below preserve their distinct admission and remaining-work boundaries.

## 1. Status and priority

| Status | Meaning |
| --- | --- |
| `OPEN_INTEGRATION` | A calculation or policy already exists, but a public, chart-composition or REST surface omits it. Admission still requires appropriate bounds and evidence. |
| `OPEN_ENGINE` | A concrete behavior or helper contract remains incomplete in current code. |
| `SOURCE_RESEARCH` | A recorded extension needs edition collation, named lineage, typed results and fixtures before implementation. An old source citation does not admit a rule. |
| `EVIDENCE_REVIEW` | Existing code/evidence must be reconciled before a broader completion claim is justified. |
| `CANDIDATE` | Optional expansion recorded for a scope decision; not a committed delivery obligation. |
| `BOUNDED_ADMISSION` | A finite contract is implemented, while named exceptional rules or authority reconciliation remain open. |
| `LOCAL_COMPLETE` | Authorized engine/public/REST package implemented and validated locally; publication, release and adoption remain distinct. |

`P1` closes gaps in existing products; `P2` deepens existing families or provides the next foundational composition; `P3` is a larger separately scoped programme. These are sequencing suggestions, not effort estimates, dates or an instruction to resume paused work. No item must mechanically pass twelve identical phases: use the constitutional gates that apply to its actual object.

There are **24 stable numbered work packages** below: **18 remain open,
including bounded VED-023 and the VED-017 window frontier. VED-005 is locally
complete for its selected admission repair; VED-001/003/004/006/015 are complete
and source-published for their bounded contracts**.
Several contain source-separated subquestions
rather than a promise to implement every tradition. Five optional candidates
follow in a separate table. Shared source/REST/validation requirements are not
counted as additional techniques.

## 2. Existing engine and REST closure

| ID | Work still required | Current evidence | Status / priority |
| --- | --- | --- | --- |
| VED-001 | Locally complete for strict one/two-cycle selection, exact seven-body/optional node-pair inputs and canonical execution receipts. Complete-cycle/co-lord source collation, alternative formulations and later cycles remain separate VED-013/021 research. | [Chara cycle standard](../02_standards/CHARA_DASHA_CYCLE_STANDARD.md), [approved plan](VEDIC_CHARA_D60_IMPLEMENTATION_PLAN_2026-10-07.md) and [validation receipt](../03_validation/VEDIC_CHARA_D60_VALIDATION_2026-10-07.md). Default period arithmetic retained; published second-cycle evidence is explicitly partial. | `LOCAL_COMPLETE`; included in this engine/wiki publication package; release/deployment separate |
| VED-002 | Complete Sayanadi admission: recheck the printed example and arithmetic against identified editions; define birth-ghati units/rounding and name-syllable inputs; validate bodies, required Moon, numeric ranges and missing inputs; then decide chart composition, root/facade/`vedic` curation and typed REST exposure. Preserve omitted/not-evaluable states and the source provenance of any historical effect text. | [sayanadi_avastha](../../moira/avasthas.py) and [one worked-example test](../../tests/unit/test_sayanadi.py) exist. `PlanetAvasthas` has an optional `sayanadi` field, but `evaluate_avasthas` does not accept the required inputs or populate it; root curation and [REST](../../moira_server/models/vedic_extended.py) omit it. The standalone helper falls back when Moon/body metadata is missing. The September claim of full chart wiring is incorrect. | `EVIDENCE_REVIEW` followed by `OPEN_INTEGRATION`, P1 |
| VED-003 | Locally complete for transport, four edition-owned names, Santhanam signs, modern composed full positions and the explicit `classical_derived_linear` full-degree policy through engine/facade/REST/strength. The wider library establishes classical/commentarial support at the reviewed scopes. Direct classical D60 degree prescription and exact primary-published planetary pairs are optional future research outside this closed implementation scope. | [D60 standard](../02_standards/D60_SOURCE_ADMISSION_STANDARD.md), [classical-derived admission](D60_CLASSICAL_DERIVED_ADMISSION_2026-10-07.md) and [execution receipt](../03_validation/D60_CLASSICAL_DERIVED_VALIDATION_2026-10-07.md). Modern and derived-classical provenance stay distinct; frozen witnesses and rational boundary checks validate both selected mappings. Harmonic defaults retained. | `LOCAL_COMPLETE`; included in this engine/wiki publication package; release/deployment separate |
| VED-004 | Locally complete: seven weights validated/exposed, actual selected/applied/reserved policy receipts, and personal-score frame precedence reconciled. | [Personalized Muhurta standard](../02_standards/MUHURTA_PERSONAL_SEARCH_STANDARD.md) and [validation receipt](../03_validation/MUHURTA_PERSONAL_SEARCH_VALIDATION_2026-10-06.md). Reserved classical-rule flag is fixed True; no alternate school is silently selected. | `LOCAL_COMPLETE`; engine/wiki source published, release/deployment separate |
| VED-005 | Locally complete for the selected 30 Vimshottari, alternate-dasha, Shadbala, dignity, Sade Sati and Vedic-profile routes: strict inputs/identities, admitted period trees, selected-policy preflight, serving-reader repair, consistent alternate chart frames and applied-policy receipts. Additional range/execution/response budgets require separately selected operational policy. | [Admission standard](../02_standards/VEDIC_REST_ADMISSION_STANDARD.md) and [audit/repair validation receipt](../03_validation/VEDIC_REST_ADMISSION_VALIDATION_2026-10-08.md): 175 distinct latest passing tests, real discovered/configured-kernel lifecycles and explicit compatibility changes. Earlier Panchanga/Muhurta hardening remains its original scope; neither package claims a whole-Vedic numerical certification. | `LOCAL_COMPLETE`; included in the authorized engine/wiki source-publication package, release/deployment separate |

VED-001 is locally complete. VED-003 admits transport, selected-edition names, source-owned signs, modern composed full positions and a usable classical-derived full-degree profile. Both full source profiles have completed computational validation, including independent software witnesses and sixteen real-reader date/frame chart batches. Classical support is established at the separately documented scopes; direct classical D60 degree prescription and exact published planetary pairs remain unclaimed source-evidence frontiers, not implementation gates. A single rounded arudha-point witness is conditional. VED-002 requires evidence and engine hardening before exposing the existing helper. Passing a direct numerical example does not settle its birth/name input doctrine.

## 3. Muhurta work recovered from the paused notes

| ID | Work still required | Current evidence and boundary | Status / priority |
| --- | --- | --- | --- |
| VED-006 | Locally complete for natal-aware sampled composition: actual personal evaluator, explicit true ayanamsa and serving-reader clocks, visible failures, threshold-qualified consecutive runs, ranked peak/bracket evidence and operational caps, with bounded REST search. Exact transitions and sunrise-owned search would require separately selected composition. | [Search engine](../../moira/muhurta_search.py), repaired legacy scorer/tuple adapters, eight shared root/facade/Vedic exports, two facade methods and `POST /v1/muhurta/search`; [owning standard](../02_standards/MUHURTA_PERSONAL_SEARCH_STANDARD.md) and [validation receipt](../03_validation/MUHURTA_PERSONAL_SEARCH_VALIDATION_2026-10-06.md). Existing rule profile retained; no Western doctrine or new classical rule admitted. | `LOCAL_COMPLETE`; bounded sampled/JD-weekday contract, engine/wiki source published, release/deployment separate |
| VED-007 | Admit typed named-Muhurta intervals and policies. Begin by evaluating the existing Abhijit/Brahma predicates and day/night ownership; research Godhuli, Vijaya, Amrita, Ravi Yoga and Sarvarthasiddhi separately before adding them. Define location/time inputs, interval endpoints and unavailable-sunrise behavior, then REST parity. | [is_abhijit_muhurta and is_brahma_muhurta](../../moira/muhurta.py) are standalone boolean helpers. The named list in activity guidance is not a computed window catalogue. The [paused tracker](TIER2_VEDIC_WORK_TRACKER.md) supplies historical source leads only. | `OPEN_INTEGRATION` for existing predicates; `SOURCE_RESEARCH` for additions, P2 |
| VED-008 | Deepen Panchanga Shuddhi with separately sourced Tara-cycle/paryaya variants, Panchaka Rahita and granular Yoga/Karana rules. Keep existing Tara/Chandra results intact; define exactly which extra inputs and cancellations a selected profile evaluates. | Basic [tara_bala, chandra_bala and personal_muhurta_score](../../moira/muhurta.py) already exist and are exposed through `/v1/muhurta/personal/score`. No current `panchaka_rahita` helper or full paryaya-neutralization contract was found. The old tracker is not proof of implementation. | `SOURCE_RESEARCH`, P2 |
| VED-009 | Build a finite source-owned Muhurta dosha/Parihara family: exact detection windows, independent witnesses and named neutralization rules. Resolve Vishanadi/Tyajya, Yamaghanta and finer Gandanta boundaries against editions; preserve detected, neutralized, unavailable and excluded states. | Current [Muhurta](../../moira/muhurta.py) contains Dagdha/Vishti rules and basic Gandanta classification. `detect_muhurta_doshas` is absent, and current `MuhurtaClassification` has no claimed rich dosha/neutralization fields. The paused tracker's "fully wired" description is historical drift. | `SOURCE_RESEARCH`, P2 |
| VED-010 | Admit Muhurta Lagna, planetary-strength and Navamsha-shuddhi composition with named purpose policies. Reuse existing Varga/Shadbala results without silently choosing relationship/aspect schools; disclose missing houses/strength and keep subcomponents inspectable. | `evaluate_muhurta_lagna_strength` is absent from current [Muhurta](../../moira/muhurta.py). [Varga](../../moira/varga.py), [Shadbala](../../moira/shadbala.py) and chart inputs are ingredients, not the complete technique. | `SOURCE_RESEARCH`, P2 |
| VED-011 | Turn selected activity guidance into finite, testable, source-owned purpose profiles: marriage variants, construction/Vastu, travel and business only after scope selection. Expose evaluated rules, exclusions and disagreements rather than letting prose or a generic score imply complete purpose coverage. | [ACTIVITY_MUHURTA_GUIDANCE](../../moira/muhurta.py) contains guidance data; it is not a comprehensive executable purpose-policy system. Existing REST provenance says activity guidance is not admitted. | `SOURCE_RESEARCH`, P2 |

The May tracker is retained as a research trail. Its claims that dosha detection, rich classification and Lagna-strength helpers had been wired are not the current implementation baseline. This register does not automatically resume that paused programme.

## 4. Other established-family depth and foundational additions

| ID | Work still required | Current evidence and admission gate | Status / priority |
| --- | --- | --- | --- |
| VED-012 | Source and implement selected extended yoga rules: BPHS 41.2–15 per-Lagna wealth cases, further royal-birth associations, and JP 7.14 Navamsha-based Neecha Bhanga. Resolve the exact Raman Part II citation, edition and accessibility before relying on it. Preserve per-rule evidence, lineage alternatives and cancellation conditions; add chart/Varga joins and REST inputs only when the selected rule needs them. | The [historical Phase 2 enrichment list](vedic_jyotish_phase2_gaps.md) records these leads. The existing [yoga engine](../../moira/yogas.py) is present and proof-bearing; its JP 7.14 source note explicitly says that Navamsha rule is not implemented. Do not equate all Raja/Dhana yogas or all BPHS chapter-39 references with these specific missing cases. | `SOURCE_RESEARCH`, P2 |
| VED-013 | Evaluate additional Chara Dasha lineages and source-owned Argala strength grading. Keep alternative period/direction/co-lord rules and count-based intervention separate; define how any Shadbala context affects a named grading product before calculating it. | [Jaimini extended](../../moira/jaimini_extended.py) already has sign aspects, Arudha, Argala, both Karakamsa readings and Rao cycles. Its Argala is count-based; additional Rath/RB-NS leads in the [old register](vedic_jyotish_phase2_gaps.md) need independent admission. Rao's second-cycle transport belongs only to VED-001. | `SOURCE_RESEARCH`, P2 |
| VED-014 | Research and admit one explicitly named Kalachakra Dasha profile before expanding variants: Savya/Apasavya traversal, Nakshatra/pada-to-sign mapping, cycle length, birth balance, year basis and nested periods. Create independent source fixtures and typed lineage-bearing vessels before bounded REST design. | [dasha_systems](../../moira/dasha_systems.py) provides Ashtottari and Yogini; [alternate-dasha standard](../02_standards/ALTERNATE_DASHAS_BACKEND_STANDARD.md) excludes Kalachakra. The [original roadmap](vedic_jyotish_completion.md) is a source lead, not an executable definition. | `SOURCE_RESEARCH`, P3 |
| VED-015 | Completed local daily contract: local date/zone/location, sunrise-owned Vara, retained sunrise/sunset crossings, solved angular limb endings, repeated/skipped sunrise evidence, half-open coverage, and unavailable solar states. | [Daily engine](../../moira/daily_panchanga.py), curated root/facade/Vedic exports and `POST /v1/panchanga/day`; [source/policy/validation standard](../02_standards/DAILY_PANCHANGA_STANDARD.md). Three named sunrise conventions and existing ayanamsa choices are explicit. Lunar months/festivals remain separate scope. | `LOCAL_COMPLETE`; engine/wiki source published, release/deployment separate |
| VED-016 | Source and admit special Lagnas as distinct products, beginning with selected Bhava/Hora/Ghati Lagna traditions. Define sunrise/elapsed-time ownership, units, sidereal frame and lineage differences; provide typed results and transport provenance. | No first-class Bhava/Hora/Ghati Lagna implementation was found in the inspected engine/server tree. Ordinary chart Lagna, vargas and Pancha Pakshi clock inputs do not supply these definitions. | `SOURCE_RESEARCH`, P3 |

## 5. Gochar enrichment beyond the admitted snapshot

| ID | Work still required | Current evidence and boundary | Status / priority |
| --- | --- | --- | --- |
| VED-017 | Reader-bound epoch/civil-date composition is locally complete. Remaining: admit bounded dated windows; solve subject and blocker ingresses, retrograde re-entries and intervals where observations/relations change, with boundary and coverage evidence. | The [date-derived standard](../02_standards/GOCHARA_DATE_DERIVED_STANDARD.md) and [validation receipt](../03_validation/GOCHARA_DATE_DERIVED_VALIDATION_2026-10-06.md) own complete seven-body input derivation, separate epoch clocks/ayanamsas, optional same-birth raw Raman-encoded BAV, facade exports and two strict REST routes. `forecast.dated_events` in the [catalogue](../../moira/gochara_policy.py) remains outside snapshot scope. Existing transit search is substrate, not a complete Gochar forecast product. | `COMPOSITION_LOCAL_COMPLETE`; `WINDOWS_OPEN_ENGINE`, P2 |
| VED-018 | Evaluate additional Gochar corpora, references and nodal participation independently. Collate complete source profiles, baseline/indication tables, subjects, blockers and exemptions; resolve known edition/table discrepancies before exposing an executable choice. | [Catalogue](../../moira/gochara_policy.py) records `profile.brihat_samhita_104`, `reference.alternatives`, the conflicting Phaladeepika/Prasna Marga nodal treatments, `nodes.blocker_participation` and disputed tables. Seven classical bodies and natal Moon remain the only admitted computation profile. | `SOURCE_RESEARCH`, P3 |
| VED-019 | Evaluate separately sourced Gochar modifier/extension products: Counter-Vedha, source-specific sign-part activation, dignity/aspect and dasha context, ingress-Moon Murthi, and Nakshatra/chakra/Latta systems. Preserve relation types and competing conventions; do not collapse them into one strength score or generic Vedha switch. | [Catalogue](../../moira/gochara_policy.py) records `vedha.counter_vedha`, the two distinct activation treatments, strength-context records, `murthi.ingress_moon` and `nakshatra.chakra_extensions`. Each carries a non-admission limitation. Sarvatobhadra and 27/28-star geometry need their own source object, not an inferred extension of sign-based Vedha. | `SOURCE_RESEARCH`, P3 |

VED-018 and VED-019 are evidence programmes. Source-attested, disputed, research-required and outside-snapshot records remain visibly distinct. A catalogue entry is not authorization to compute it, and this register supplies no repaired disputed table. Remedies and interpretive recommendations remain outside the computational package.

## 6. Source, validation and documentation follow-through

| ID | Work still required | Current evidence and boundary | Status / priority |
| --- | --- | --- | --- |
| VED-020 | Preserve the remaining Pancha Pakshi source-admission queue: alternate solar/Padu/Sookshma doctrines, Bharana/Adhikara identities, vinadi routing, unresolved outcome cells, cross-witness composition, condition/scoring and electional search. Resolve each blocked identity/edition layer independently before runtime or REST promotion. | The [current research standard, deferred products](../02_standards/PANCHA_PAKSHI_RESEARCH_STANDARD.md#10-deferred-products) is the owning detailed queue. Stage 2J and the later research pilots are not blanket public outcome admission. Existing schedules, clocks, natal/Padu/EAT identity and other admitted capabilities must not be reclassified as absent. | `SOURCE_RESEARCH`, P3; retain the owning stage boundaries |
| VED-021 | Strengthen independently traceable worked-case coverage for the specific extensions being admitted. Record source editions/pages, inputs, expected component results, boundary/missing-data cases and explicit tolerances. Use JHora/Kala differences to locate lineage disagreements rather than treating software agreement as classical authority or predictive accuracy. Audit the single Sayanadi example before relying on it for full-family admission. | Existing Vedic unit/server tests and standards already exist; the paused tracker saying validation is "None" is stale. The [surface receipt](VEDIC_SURFACE_REST_COMPLETENESS_2026-10-06.md) records 397 focused passes and separate 193/72 regression runs for their actual scope; [VED-005](../03_validation/VEDIC_REST_ADMISSION_VALIDATION_2026-10-08.md) adds 175 distinct admission/lifecycle/transport passes. These are not a validation study of every future rule. | `EVIDENCE_REVIEW`, P1 per selected package |
| VED-022 | Reconcile remaining source headers and technical contract prose, then publish generated documentation when source publication is authorized. Distinguish standalone Sayanadi from chart admission and require engine/public/REST closure receipts for future completion notices. | VED-001 already reconciled the [Jaimini](../../moira/jaimini_extended.py) header to one/two-cycle support and named source limits. Muhurta policy/helper/personal-score/search prose is reconciled by VED-004/006; the initial June design is explicitly historical. VED-005 reconciles the selected family's REST standards/reference and generated pages. Generated `moira.wiki` must only be updated through `scripts/sync_git_wiki.py`; source push and runtime release remain separate. | `OPEN_INTEGRATION`, P1 documentation work in each affected package |

### Authorized lunar-month and festival extensions, 6 October 2026

| ID | Work still required | Current evidence and admission gate | Status / priority |
| --- | --- | --- | --- |
| VED-023 | Source and implement exceptional Purnimanta month/fortnight mapping and Kshaya-year regional relabeling. Regional solar dates and era years require their own explicit profiles. | [Lunar-month engine](../../moira/lunar_month.py), `Moira.lunar_month_at`, curated exports and `POST /v1/panchanga/lunar-month` implement bounded Amanta/ordinary-Purnimanta context with solved conjunctions/ingresses, Adhika/Kshaya evidence, uncertainty brackets and explicit unsupported states. [Source/policy/validation record](../02_standards/LUNAR_MONTH_AND_FESTIVAL_POLICY.md). The PAC solar-ingress residual is [reconciled](../03_validation/SIDEREAL_GENERAL_PRECESSION_RECONCILIATION.md): corrected IAU 2006 general precession; all 13 published ingresses pass the original 60-second gate. | `BOUNDED_ADMISSION`, P2; exceptional source rules remain open |
| VED-024 | Admit finite festival/fasting rule catalogues by identified lineage: exact ritual windows, viddha, repeated/skipped tithi selection, intercalation eligibility, precedence and parana. Expose catalogue admission states and bounded typed evaluation through REST together. | [Research and policy surface](../02_standards/LUNAR_MONTH_AND_FESTIVAL_POLICY.md) records institutional calendars, local corpus limits, explicit policy axes and test requirements. PAC dates do not constitute a complete executable rule specification; no universal festival catalogue is admitted. | `SOURCE_RESEARCH`, P2; research packet decision `defer_for_source_completion` |

## 7. Optional expansion candidates

These are not promoted to required engine work by this reconciliation. Select a finite scope and evaluate sources before adding them to sections 2–6.

| Candidate | What a scoping decision must settle |
| --- | --- |
| C-01: Vedic matching | Named Kuta/Ashtakoota/Dashakoota lineage, component calculations, regional exceptions and visible cancellation rules; chart compatibility ingredients do not establish an admitted matching product. |
| C-02: Prashna | A particular Vedic Prashna text/profile and required inputs; existing Western Horary evidence is a different doctrine. |
| C-03: KP astrology | Star/sub/sub-sub partitions, cuspal sub-lords, significators, time policies and named source/lineage. A Krishnamurti ayanamsa is not a KP engine. |
| C-04: Tajika/Varshaphal long-tail review | Inventory the finite source-owned cases missing from the already substantial [Varshaphal engine](../../moira/varshaphal.py) before claiming any whole family absent. The May notes are a review lead, not a verified current defect list. |
| C-05: Research/corpus/filtering tools | Define licensed/provenance-bearing datasets, repeatable chart queries and component comparisons. This is infrastructure; it is not an additional Vedic calculation technique or evidence of predictive validity. |

The user authorized lunar-month and festival investigation after VED-015. VED-023/024 now own that work; unadmitted regional calendars and ritual branches remain visible, rather than being folded into a claim of daily Panchanga completeness.

## 8. Work already present: do not reopen as missing

| Existing product | Correct remaining boundary |
| --- | --- |
| Seventeen Varga divisions, Vedic dignities, Shadbala including Bhava Bala, BAV/SAV and reductions, Vimshottari/Ashtottari/Yogini | Existing families; do not reconstruct the pre-Phase-1 backlog. Deepening must name a specific rule or defect. |
| Yoga core, extended Jaimini, upagrahas, four chart-evaluated avastha systems | Existing engine and REST families. Selected yoga/Jaimini enrichment and Sayanadi admission remain above. |
| Tara/Chandra Bala, personal Muhurta, Vimshopaka/Vargottama, Kakshya/Shodhya Pinda, Sade Sati | Existing calculations and REST. Their old "missing" notices are superseded. |
| Rao Chara second cycle | VED-001 locally closes strict cycle selection and canonical engine/REST receipts; complete-cycle and co-lord authority remains bounded in the owning standard. |
| D60 named deities | VED-003 locally closes eight-route transport, four selected-edition names, source-only signs and modern/classical-derived full-degree profiles. Each profile has explicit provenance and completed engine/facade/REST/strength validation. Direct classical D60 degree prescription and exact printed planetary pairs remain separately unclaimed; the absence of a direct prescription does not block the derived policy. |
| Sayanadi | Standalone code exists; VED-002 owns evidence, hardening and chart/public/REST admission. |
| Gochar snapshot and doctrine catalogue | Original engine/public/REST package committed at the baseline. VED-017 epoch/date composition is now locally complete; dated windows and VED-018/019 remain independent admissions. |
| Daily sunrise-owned Panchanga | VED-015 engine/public/REST is locally complete; its named policy, source and bounded verification are in the linked receipt. No website adoption or deployment is implied. |
| Unified Vedic exports | The 6 October package added 84 curated `vedic` names and sixteen root Varga names. Their absence is closed; this is not blanket admission of every standalone module helper. |
| Existing Muhurta, Vedic, Pancha Pakshi and Varshaphal standards/tests | They exist. Additional worked-case coverage and scope corrections are specific follow-through, not "no documentation" or "no tests." |

## 9. Suggested package order and definition of done

1. **Close existing product omissions:** VED-001/003/005 are locally complete for their selected scopes. Evaluate the remaining VED-002 Sayanadi evidence and admission before exposing it; carry VED-021/022 with that package. Operational REST budgets remain a separate scope decision.
2. **Muhurta composition:** VED-004/006 are locally complete for the bounded sampled/JD-weekday profile. VED-007–011 remain individually source-owned admissions; exact transitions and sunrise-owned search require their own scope decision.
3. **Daily foundation:** VED-015 is locally complete. Selected special Lagnas and Kalachakra would be separate, newly authorized packages.
4. **Deepen source-specific families:** selected VED-012/013 and Gochar VED-017–019. Pancha Pakshi retains its owning stage-by-stage queue.

Every admitted package must state the governing object, edition/lineage and ambiguity policy; input and output ownership; evaluated/omitted/unavailable distinctions; public export identity; explicit bounded request and typed response contracts; reader/resource lifecycle; direct-engine/HTTP parity; hostile and boundary inputs; source-owned fixtures; documentation and completion receipt. New output fields must preserve canonical engine truth rather than rebuilding it in the server. Numerical authority, transport fidelity and predictive claims are different validation questions.

For research-only items, completion is an evidence packet plus an explicit admission/defer/exclude decision. For calculation work, evidence precedes runtime implementation. For a public/REST gap, completion requires both surfaces and their contracts. A push is not a release, deployed endpoint or website tool.

## 10. Initial reconciliation evidence and maintenance

This is a source/contract reconciliation, not a new source-book collation or whole-engine numerical certification. Current code, model fields, public curation, registered routes, standards and tests were inspected. A kernel-free project-runtime smoke additionally verified:

- 12 versus 24 Chara periods and repeated sign/year/lord spans;
- absent REST cycle selection;
- absent Sayanadi chart inputs and all chart Sayanadi slots remaining `None`;
- absent root Sayanadi curation and absent REST birth inputs;
- absent D60 response `deity` and absent natal Muhurta request weights;
- absent claimed Muhurta dosha/Lagna-strength helpers;
- an unused natal parameter in the scorer's syntax tree;
- accepted string/boolean Panchanga numeric coercion.

Runtime: project Python 3.14.3, Moira 6.9.9, with `MOIRA_NO_DOWNLOAD=1`. The witness ran through `.\.venv\Scripts\python.exe -` with a stdin assertion script; it used no chart resource or network. The preceding 397/193/72 test receipts were not rerun for these documentation edits and are cited only for their original package scope. A filename search of the local book corpus found Raman PDFs, including a volume-2 file; the old statement that "no accessible scan exists" was not carried forward as a verified fact. Exact book/edition/verse identity still needs collation for the intended yoga cases.

The eight canonical documentation paths changed in this pass are this register; the three historical Vedic roadmaps/trackers; the Vedic entries in the broad frontiers register; section 6.2 of the August audit; `wiki/Home.md`; and the unified Vedic paragraph in `wiki/02_standards/API_REFERENCE.md`. Engine, REST implementation, numerical fixtures, test policy, dependencies, version, generated wiki, website and other worktrees are untouched. The initial working tree was clean.

Verification commands for documentation:

```powershell
$env:MOIRA_NO_DOWNLOAD='1'
.\.venv\Scripts\python.exe scripts/check_doc_consistency.py
.\.venv\Scripts\python.exe scripts/sync_rest_api_reference.py --check
git diff --check
```

All three documentation commands passed. Direct project-runtime checks also passed for 22 unique ordered work IDs, five unique candidate IDs, 50 relative file/anchor links and five historical/superseded notices. An in-memory preview through the owning wiki generator passed with the new untracked register explicitly included; it verified flat-page and engine-source link rewriting without staging or writing generated files. Generated-wiki publication is a later authorized operation; this pass does not stage, commit, push or synchronize the mirror.

Keep the IDs stable. Close items with a linked source/engine/public/REST receipt, not a blanket "complete" label. Split a package only when its doctrinal object or independently reviewable delivery changes; avoid duplicating shared requirements or resurrecting a historical absence claim. Update the baseline and date whenever this register is reconciled again.

## 11. VED-015 local completion, 6 October 2026

The user selected VED-015 as the next implementation package. The
[daily standard](../02_standards/DAILY_PANCHANGA_STANDARD.md) owns the resulting
source review, selected and deferred conventions, strict input/output contracts,
actual commands and verification limits. Section 10 above is the earlier
documentation-only pass; its "untouched" statement applies to that pass.
Other numbered work packages and optional candidates retain their prior scope.

## 12. Personalized Muhurta completion and source publication, 6 October 2026

The user selected VED-004 plus VED-006 after the dated-Gochar snapshot push.
The [owning standard](../02_standards/MUHURTA_PERSONAL_SEARCH_STANDARD.md) and
[receipt](../03_validation/MUHURTA_PERSONAL_SEARCH_VALIDATION_2026-10-06.md) record
the repaired existing profile, bounded search, public/REST admission and actual
verification. Source collation for additional schools, Sunrise Vara search and
exact transitions are not implied by local composition correctness. VED-005's
remaining family audit and VED-007–011 retain separate boundaries. Earlier
section-10 evidence describes the initial reconciliation, not this later code.

After validation the user authorized commit and push of this package. The
containing engine/wiki source commits publish VED-004 and the bounded VED-006
repair, with the generated wiki published first. Release, deployment and
website/Urania adoption remain separate operations.

## 13. VED-001/003 research checkpoint, 7 October 2026

The user selected bounded Chara cycles and D60 deity transport, requesting deep
research first. The [owning source packet](VEDIC_CHARA_D60_SOURCE_RESEARCH_2026-10-07.md)
records online primary-author research, the local book/article corpus, visually
checked edition pages, fingerprints, source disagreements, current engine/HTTP
witnesses and a finite implementation proposal. It identifies an article/book
attribution error, partial second-cycle evidence, four D60 name discrepancies
and a separate D60 placement convention. No alternative Chara school or new
Varga arithmetic is admitted by a transport omission.

The baseline is 140 passing existing engine tests plus 10 selected Chara HTTP
tests, with separate kernel-free probes. These are scoped regression receipts,
not authority validation of every proposed rule. VED-001/003 remain open; the
21-open count is unchanged. Only this register and the new research packet are
edited in this checkpoint. Runtime, validation policy/evidence baselines,
generated wiki, source publication, release, deployment and website adoption
are unchanged.

## 14. VED-001/003 implementation, 7 October 2026

The user approved the [four-slice plan](VEDIC_CHARA_D60_IMPLEMENTATION_PLAN_2026-10-07.md).
Chara now validates bounded cycles and complete inputs and returns actual
execution metadata through REST. All eight Varga placement routes preserve
canonical nullable enrichment. Four deity names are corrected against the
identified Santhanam printed list with explicit migration values.

Further source adjudication admits `bphs_santhanam_sign` as a typed sign-only
product and selected Vimshopaka method. It does not supply continuous degrees;
full-position consumers reject that selection and preserve harmonic defaults.
The [D60 standard](../02_standards/D60_SOURCE_ADMISSION_STANDARD.md) records
the missing passage/fixtures needed to close that subitem. The
[Chara standard](../02_standards/CHARA_DASHA_CYCLE_STANDARD.md) distinguishes
partial published repetition evidence from the retained co-lord convention.

The [completion receipt](../03_validation/VEDIC_CHARA_D60_VALIDATION_2026-10-07.md)
records source boundaries, exact compatibility changes, focused tests, installed
DE441 chart integration and documentation checks. VED-001 is locally complete;
VED-003 remains bounded with full source placement open. Twenty numbered
packages remain open; historical checkpoint counts above retain their dates.
Commit/push, generated-wiki publication, release, deployment and website/Urania
adoption were not authorized by this implementation request.

## 15. D60 full-position extension, 7 October 2026

The user authorized widening source review and exceeding the full-position
acceptance checks. The [new source packet](D60_FULL_POSITION_SOURCE_RESEARCH_2026-10-07.md)
adjudicates the dated PVR textbook/linear composition, author revision notices,
the article's incorrect D9 arithmetic and unpaired published D60 coordinates.
The named modern full profile is implemented through engine, facade, all seven
named/chart request shapes and strength, with canonical positional source
receipts, strict new-profile inputs and exhaustive half-degree boundary checks.
The [execution receipt](../03_validation/D60_FULL_POSITION_VALIDATION_2026-10-07.md)
records this extension separately from the earlier checkpoint above.

VED-003 remains `BOUNDED_ADMISSION`: named modern computation is locally
complete; the classical passage and paired published full-D60 oracle are not
established. This does not reset other package states or change the 24 stable
IDs/20 open count. Source publication, release and product adoption remain
separate states.

## 16. D60 bounded evidence decision, 7 October 2026

The [completed adjudication](D60_EVIDENCE_ADJUDICATION_2026-10-07.md) reviews
two identified BPHS editions/commentaries, named local treatments and further
primary author publications. Retain the explicit dated Moira composition;
admit no classical full-degree method or current JHora equivalence. Sharma's
published sign example/table rows provide independent regression evidence.
The single published arudha D1/full-D60 pair is compatible under nearest-minute
rounding and incompatible under truncation; its rounding rule is unknown.

The finite research task is complete. The remaining classical/planetary-oracle
claims are not established in the reviewed sources, with concrete evidence
required to reopen them. This preserves VED-003's bounded admission and the
24 stable IDs/20 open count. No new runtime/API selection or source authority
is introduced by the validation witnesses.

## 17. D60 broader computational validation, 7 October 2026

The [completed broader receipt](../03_validation/D60_CROSS_ENGINE_VALIDATION_2026-10-07.md)
records 24,432 conditioned inputs compared with checksum-pinned PyJHora
full-point outputs and compiled Maitreya returned signs/instrumented
longitudes: all 720 segments, exact/adjacent boundaries, 20,000 seeded
samples and 112 planetary inputs across sixteen date/frame charts. No
disagreement exceeds the predeclared arithmetic budget; signs agree exactly.
Independent rational evaluation agrees throughout. The 4,552-case offline
fixture reproduces exactly; permanent engine/facade/REST/strength tests use
external expected values. The source fragments are private validation inputs,
not runtime dependencies or copied engine implementation.

**Modern implementation and broader computational validation are complete
locally.** VED-003's remaining bounded state concerns historical authority
claims, including an identified classical full-degree law and exact published
planetary pairs. Neither is concealed as an unfinished engineering gate.
Current PVR Jagannatha Hora equivalence and predictive effectiveness are not
claimed. The 24 stable IDs/20 open count, other package states and existing
source locators are preserved. Commit/push, release and website adoption are
separate from this local outcome.

## 18. Classical-derived D60 reconciliation, 7 October 2026

The [wider-library adjudication](D60_CLASSICAL_DERIVED_ADMISSION_2026-10-07.md)
supersedes sections 14-17 wherever they imply that no classical-derived
full-degree policy can be admitted. It establishes separately scoped BPHS
D60 sign authority, Saravali general subdivision arithmetic, Jataka Parijata
D12 fractional correspondence and Raman's explicit Navamsa degree notes.
The D60 degree extension is Moira's disclosed derivation.

`classical_derived_linear` is implemented through the full engine/facade,
all seven named/chart REST shapes, sign projection and D60-containing
Vimshopaka groups. Canonical source locators and `d60_degree_attribution`
make its derivation inspectable. Existing modern positional locators retain
their exact identity. The [completed validation receipt](../03_validation/D60_CLASSICAL_DERIVED_VALIDATION_2026-10-07.md)
covers exact rational boundaries, primary commentarial D9 examples, unchanged
frozen external witnesses, real DE441 charts and strict REST preflight.
Source-profile groups also normalize tiny negative wrap inputs before
composing the other divisions and D1 relationships.

The admitted classical-derived product and its engineering validation are
complete locally. A directly prescribed classical D60 degree algorithm and
exact source-published planetary pairs remain unclaimed historical frontiers.
At this checkpoint the register retained 24 stable IDs and 20 open-or-bounded
packages. The final closure below supersedes that count and VED-003's earlier
bounded status. Publication, release and product adoption remain separate.

## 19. VED-003 final closure and source-publication package, 7 October 2026

The user approved closing the admitted D60 scope and publishing the completed
engine/wiki package. **VED-003 is `LOCAL_COMPLETE`.** Its source sign policy,
modern composed full positions, classical-derived full degrees, edition-owned
deities, public/facade/REST transport and D60-containing strength consumers
are implemented and validated. The [execution receipt](../03_validation/D60_CLASSICAL_DERIVED_VALIDATION_2026-10-07.md)
records 1,552 distinct passing tests and 24,432 conditioned corpus checks
within the unchanged numerical budget. No engineering work remains for the
admitted profiles.

The register now contains **24 stable IDs, five closed scoped packages
(VED-001/003/004/006/015), and 19 open-or-bounded packages**, including VED-017's
independent window frontier. A directly prescribed classical D60 degree law
and exact source-published planetary pairs are optional future research;
neither is a closure gate or an additional promised work package. Historical
checkpoint counts and decisions above remain dated evidence.

VED-001's already completed bounded Chara cycle work is included in the same
coherent engine/wiki publication package. Generated wiki source is published
first; the parent engine package then records that wiki gitlink. Package
release, deployment and website/Urania adoption remain separate actions.

## 20. VED-005 local admission closure, 8 October 2026

The authorized audit and repair closes the selected 30 existing Vimshottari,
alternate-dasha, Shadbala, dignity, Sade Sati and Vedic-profile contracts.
**VED-005 is `LOCAL_COMPLETE` at that scope.** The
[admission standard](../02_standards/VEDIC_REST_ADMISSION_STANDARD.md) and
[validation receipt](../03_validation/VEDIC_REST_ADMISSION_VALIDATION_2026-10-08.md)
record the original failures, reader repair, strict policy/input admission,
alternate chart-frame correction, applied receipts, 175 distinct latest
passing tests and actual startup checks. Previously coerced inputs, unknown
classical keys/lords and unsupported house identities intentionally fail
validation. Valid partial dignity maps and selected mixed component frames
retain their existing meaning.

The register now contains **24 stable IDs, six closed scoped packages
(VED-001/003/004/005/006/015), and 18 open-or-bounded packages**. Section 9's
first package now leaves VED-002 Sayanadi evidence/admission as the remaining
technique, with per-package VED-021/022 follow-through. Jaimini's already
corrected header is reconciled here rather than reopened as a defect.

No new classical calculation or full-family authority claim is introduced.
Range, execution and response budgets for the existing Sade Sati/deep
Vimshottari services remain a separately scoped operational frontier. Local
closure does not imply source push, release, deployment or website/Urania
adoption. Historical counts above retain their dated checkpoint meaning.

The user authorized source publication on 8 October: commit/push the generated
wiki first, then the parent engine's scoped code, tests, canonical documents
and wiki gitlink. VED-002 research begins after that checkpoint; it does not
change the VED-005 validation or admit a new classical calculation.
