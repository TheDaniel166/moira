# Vedic remaining work register

**Status:** Active documentation register; implementation requires a separately authorized work package.
**Last reconciled:** 10 October 2026.
**Baseline:** engine `main`, version 6.9.9; VED-010 was published at engine `b578ec8`, generated wiki `9d35913`, with hosted Release Hardening and Acceptance Matrix green. Sections 27–35 retain earlier feature and review checkpoints. Sections 36–37 close all eleven first-pass and five second-pass adversarial findings; section 38 records the authorized publication package. Eleven of 24 stable feature packages have been delivered for their selected scopes; thirteen remain open/bounded. Repair findings are tracked separately from those feature counts. VED-011 is next. Release/deployment remain separate.
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

There are **24 stable numbered work packages** below: **13 remain open/bounded,
including bounded VED-023 and the VED-017 window frontier**.
**VED-001/002/003/004/005/006/007/008/009/010/015 reached their selected feature-delivery checkpoints**;
VED-001/002/003/004/005/006/007/008/009/010/015 are in the engine/wiki source-publication history. The separate repair acceptance in sections 36–37 closes all sixteen adversarial findings, including VED-010's optional Shadbala composition failure; it does not change these feature-delivery counts.
Several contain source-separated subquestions
rather than a promise to implement every tradition. Five optional candidates
follow in a separate table. Shared source/REST/validation requirements are not
counted as additional techniques.

## 2. Existing engine and REST closure

| ID | Work still required | Current evidence | Status / priority |
| --- | --- | --- | --- |
| VED-001 | Locally complete for strict one/two-cycle selection, exact seven-body/optional node-pair inputs and canonical execution receipts. Complete-cycle/co-lord source collation, alternative formulations and later cycles remain separate VED-013/021 research. | [Chara cycle standard](../02_standards/CHARA_DASHA_CYCLE_STANDARD.md), [approved plan](VEDIC_CHARA_D60_IMPLEMENTATION_PLAN_2026-10-07.md) and [validation receipt](../03_validation/VEDIC_CHARA_D60_VALIDATION_2026-10-07.md). Default period arithmetic retained; published second-cycle evidence is explicitly partial. | `LOCAL_COMPLETE`; engine/wiki source-published; release/deployment separate |
| VED-002 | Locally complete for the collated BPHS within-sign Navamsa-ordinal profile: exact partition ownership, strict body/Moon/name/ghati inputs, canonical trace, optional chart/node and sunrise-owned birth composition, curated Python/facade and typed REST parity. Degree-based traditions and full legacy-effect prose certification remain separately sourced scopes. | [Source audit](VEDIC_SAYANADI_SOURCE_RESEARCH_2026-10-08.md), [executed plan](VEDIC_SAYANADI_IMPLEMENTATION_PLAN_2026-10-08.md), [admission standard](../02_standards/SAYANADI_ADMISSION_STANDARD.md) and [validation receipt](../03_validation/SAYANADI_VALIDATION_2026-10-08.md): 278 distinct latest passes, zero disagreements in 14,580 independent rational cases, corrected Sa=4 source fixture, real reader/startup and direct/HTTP parity. Legacy effects explicitly retain uncertified, unevaluated provenance. | `LOCAL_COMPLETE`; engine/wiki source-published at the section 25 baseline; release/deployment separate |
| VED-003 | Locally complete for transport, four edition-owned names, Santhanam signs, modern composed full positions and the explicit `classical_derived_linear` full-degree policy through engine/facade/REST/strength. The wider library establishes classical/commentarial support at the reviewed scopes. Direct classical D60 degree prescription and exact primary-published planetary pairs are optional future research outside this closed implementation scope. | [D60 standard](../02_standards/D60_SOURCE_ADMISSION_STANDARD.md), [classical-derived admission](D60_CLASSICAL_DERIVED_ADMISSION_2026-10-07.md) and [execution receipt](../03_validation/D60_CLASSICAL_DERIVED_VALIDATION_2026-10-07.md). Modern and derived-classical provenance stay distinct; frozen witnesses and rational boundary checks validate both selected mappings. Harmonic defaults retained. | `LOCAL_COMPLETE`; engine/wiki source-published; release/deployment separate |
| VED-004 | Locally complete: seven weights validated/exposed, actual selected/applied/reserved policy receipts, and personal-score frame precedence reconciled. | [Personalized Muhurta standard](../02_standards/MUHURTA_PERSONAL_SEARCH_STANDARD.md) and [validation receipt](../03_validation/MUHURTA_PERSONAL_SEARCH_VALIDATION_2026-10-06.md). Reserved classical-rule flag is fixed True; no alternate school is silently selected. | `LOCAL_COMPLETE`; engine/wiki source published, release/deployment separate |
| VED-005 | Locally complete for the selected 30 Vimshottari, alternate-dasha, Shadbala, dignity, Sade Sati and Vedic-profile routes: strict inputs/identities, admitted period trees, selected-policy preflight, serving-reader repair, consistent alternate chart frames and applied-policy receipts. Additional range/execution/response budgets require separately selected operational policy. | [Admission standard](../02_standards/VEDIC_REST_ADMISSION_STANDARD.md) and [audit/repair validation receipt](../03_validation/VEDIC_REST_ADMISSION_VALIDATION_2026-10-08.md): 175 distinct latest passing tests, real discovered/configured-kernel lifecycles and explicit compatibility changes. Earlier Panchanga/Muhurta hardening remains its original scope; neither package claims a whole-Vedic numerical certification. | `LOCAL_COMPLETE`; engine/wiki source published, exact SHAs in section 21; release/deployment separate |

VED-001 is locally complete. VED-003 admits transport, selected-edition names, source-owned signs, modern composed full positions and a usable classical-derived full-degree profile. Both full source profiles have completed computational validation, including independent software witnesses and sixteen real-reader date/frame chart batches. Classical support is established at the separately documented scopes; direct classical D60 degree prescription and exact published planetary pairs remain unclaimed source-evidence frontiers, not implementation gates. A single rounded arudha-point witness is conditional. VED-002 now closes the selected BPHS numeric/state, name/clock, birth composition and public/REST contract. Its receipt separates source formula and transport validation from legacy conditional-effect prose certification and predictive claims.

## 3. Muhurta work recovered from the paused notes

| ID | Work still required | Current evidence and boundary | Status / priority |
| --- | --- | --- | --- |
| VED-006 | Locally complete for natal-aware sampled composition: actual personal evaluator, explicit true ayanamsa and serving-reader clocks, visible failures, threshold-qualified consecutive runs, ranked peak/bracket evidence and operational caps, with bounded REST search. Exact transitions and sunrise-owned search would require separately selected composition. | [Search engine](../../moira/muhurta_search.py), repaired legacy scorer/tuple adapters, eight shared root/facade/Vedic exports, two facade methods and `POST /v1/muhurta/search`; [owning standard](../02_standards/MUHURTA_PERSONAL_SEARCH_STANDARD.md) and [validation receipt](../03_validation/MUHURTA_PERSONAL_SEARCH_VALIDATION_2026-10-06.md). Existing rule profile retained; no Western doctrine or new classical rule admitted. | `LOCAL_COMPLETE`; bounded sampled/JD-weekday contract, engine/wiki source published, release/deployment separate |
| VED-007 | Complete locally: Abhijit, Brahma, Godhuli, Vijaya, selected Amrita, Ravi Yoga and Sarvarthasiddhi; named source policies, precise solar/phase boundaries, source exceptions, uncertainty and partial states, public/facade and five total REST routes. Amrita Siddhi and Kalaprakasika Amirtha are separate selectable identities. | [Five-name source decision](VEDIC_NAMED_MUHURTA_FIVE_SOURCE_AND_PLAN_2026-10-08.md), [standard](../02_standards/NAMED_MUHURTA_STANDARD.md), [383-test completion receipt](../03_validation/SPECIAL_MUHURTA_VALIDATION_2026-10-08.md). All five formerly outstanding names implemented and validated, including both startup reader paths and real DE441. Generic scoring/search and activity suitability remain separate products. | `LOCAL_COMPLETE`; all-seven-family implementation validated and included in this engine/wiki source-publication package; release/deployment separate |
| VED-008 | Locally complete for named Panchaka, alternative MC/PS Tara-cycle, nine-Yoga timing and eleven-Karana/Bhadra assessments, including solved sunrise-day cells. Existing Tara/Chandra, scoring and search remain compatible. Specific excluded readings, polar discontinuous Lagna timing and general score integration are separately bounded. | [Source research](VEDIC_PANCHANGA_SHUDDHI_SOURCE_RESEARCH_2026-10-08.md), [standard](../02_standards/PANCHANGA_SHUDDHI_STANDARD.md) and [622-test validation receipt](../03_validation/PANCHANGA_SHUDDHI_VALIDATION_2026-10-09.md). Sixteen curated exports, three facade methods, three typed REST routes; source conflicts and derived clocks remain explicit. | `LOCAL_COMPLETE`; included in this authorized engine/wiki source-publication package; release/deployment separate |
| VED-009 | Locally complete finite six-detector/three-exception package: source-specific stellar Vishanadi, both Yamaghantas and temporal nakshatra/tithi/Lagna Gandanta; raw evidence retained after opt-in neutralization. Other Tyajya types, angular/Abhukta variants and the complete twenty-one-dosha catalogue remain explicitly excluded extensions. | [Source packet](VEDIC_DOSHA_PARIHARA_SOURCE_AND_PLAN_2026-10-09.md), [standard](../02_standards/MUHURTA_DOSHA_STANDARD.md) and [validation receipt](../03_validation/MUHURTA_DOSHA_VALIDATION_2026-10-09.md). Fifteen owning exports, three facade methods and three strict REST routes; full-parent events, numerical bands, carryover and source-scoped cancellation evidence. Strength-dependent exceptions belong to VED-010. | `LOCAL_COMPLETE` and published at engine `571788a` / wiki `ed68937`; broader listed extensions remain unadmitted |
| VED-010 | Source-selected general/marriage Lagna components, both Navamsa readings, quarter-aspect support, MC placement score, raw restrictions and optional MC88 exceptions. Canonical Shadbala remains inspectable context; its dated multi-war failure and subsequent context/clock admission defects are repaired. | [Source record](VEDIC_LAGNA_SOURCE_AND_PLAN_2026-10-09.md), [standard](../02_standards/MUHURTA_LAGNA_STANDARD.md), [feature validation](../03_validation/MUHURTA_LAGNA_VALIDATION_2026-10-09.md), [combined repair validation](../03_validation/VEDIC_ADVERSARIAL_REPAIR_VALIDATION_2026-10-09.md). Eleven curated exports, three facade methods and three REST routes; source-backed D9 and Venus/Moon table corrections in shared owners. | `LOCAL_COMPLETE`; feature source-published and all identified repairs included in the section 38 publication package; broader listed remedies remain excluded |
| VED-011 | Turn selected activity guidance into finite, testable, source-owned purpose profiles: marriage variants, construction/Vastu, travel and business only after scope selection. Expose evaluated rules, exclusions and disagreements rather than letting prose or a generic score imply complete purpose coverage. | [ACTIVITY_MUHURTA_GUIDANCE](../../moira/muhurta.py) contains guidance data; it is not a comprehensive executable purpose-policy system. Existing REST provenance says activity guidance is not admitted. | `SOURCE_RESEARCH`, P2 |

The May tracker is retained as a research trail. Its historical "fully wired"
claim did not establish the current contract. VED-009 now has its own validated
dosha/Parihara owner; the legacy classification has not acquired that richer
contract. VED-010 Lagna-strength composition is locally complete for its named policies and instantaneous contract.

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
| VED-021 | Strengthen independently traceable worked-case coverage for the specific extensions being admitted. Record source editions/pages, inputs, expected component results, boundary/missing-data cases and explicit tolerances. Use JHora/Kala differences to locate lineage disagreements rather than treating software agreement as classical authority or predictive accuracy. | Existing Vedic unit/server tests and standards already exist; the paused tracker saying validation is "None" is stale. The [surface receipt](VEDIC_SURFACE_REST_COMPLETENESS_2026-10-06.md) records 397 focused passes and separate 193/72 regression runs for their actual scope; [VED-005](../03_validation/VEDIC_REST_ADMISSION_VALIDATION_2026-10-08.md) adds 175 distinct admission/lifecycle/transport passes. [VED-002](../03_validation/SAYANADI_VALIDATION_2026-10-08.md) closes its selected source example, component/name/body/boundary and real-reader/HTTP coverage. These are not a validation study of every future rule. | `EVIDENCE_REVIEW`, P1 per selected package; VED-002 and all-seven-family VED-007 follow-through locally complete |
| VED-022 | Reconcile remaining source headers and technical contract prose, then publish generated documentation when source publication is authorized. Require engine/public/REST closure receipts for future completion notices. | VED-001 already reconciled the [Jaimini](../../moira/jaimini_extended.py) header to one/two-cycle support and named source limits. Muhurta policy/helper/personal-score/search prose is reconciled by VED-004/006; the initial June design is explicitly historical. VED-005 reconciles the selected family's REST standards/reference and generated pages. VED-002 reconciles Sayanadi calculation, chart/birth admission, legacy prose provenance and standards/reference/receipt. Generated `moira.wiki` is updated only through `scripts/sync_git_wiki.py`; source push and runtime release remain separate. | `OPEN_INTEGRATION`, P1 documentation work in each affected package; VED-002 and all-seven-family VED-007 follow-through locally complete |

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
| Yoga core, extended Jaimini, upagrahas, four chart-evaluated avastha systems plus optional Sayanadi | Existing engine and REST families. Selected yoga/Jaimini enrichment remains above; Sayanadi's bounded admission is closed locally. |
| Tara/Chandra Bala, personal Muhurta, Vimshopaka/Vargottama, Kakshya/Shodhya Pinda, Sade Sati | Existing calculations and REST. Their old "missing" notices are superseded. |
| Rao Chara second cycle | VED-001 locally closes strict cycle selection and canonical engine/REST receipts; complete-cycle and co-lord authority remains bounded in the owning standard. |
| D60 named deities | VED-003 locally closes eight-route transport, four selected-edition names, source-only signs and modern/classical-derived full-degree profiles. Each profile has explicit provenance and completed engine/facade/REST/strength validation. Direct classical D60 degree prescription and exact printed planetary pairs remain separately unclaimed; the absence of a direct prescription does not block the derived policy. |
| Sayanadi | VED-002 locally closes the selected BPHS source recipe, strict standalone/chart/node/birth inputs, inspectable results and curated Python/facade/REST surfaces. Legacy effect prose is explicitly uncertified and unevaluated. |
| Gochar snapshot and doctrine catalogue | Original engine/public/REST package committed at the baseline. VED-017 epoch/date composition is now locally complete; dated windows and VED-018/019 remain independent admissions. |
| Daily sunrise-owned Panchanga | VED-015 engine/public/REST is locally complete; its named policy, source and bounded verification are in the linked receipt. No website adoption or deployment is implied. |
| Unified Vedic exports | The 6 October package added 84 curated `vedic` names and sixteen root Varga names. Their absence is closed; this is not blanket admission of every standalone module helper. |
| Existing Muhurta, Vedic, Pancha Pakshi and Varshaphal standards/tests | They exist. Additional worked-case coverage and scope corrections are specific follow-through, not "no documentation" or "no tests." |

## 9. Suggested package order and definition of done

**Next package: VED-011 — selected complete purpose elections.** All eleven findings in the [Vedic adversarial repair plan](VEDIC_ADVERSARIAL_REPAIR_PLAN_2026-10-09.md) and all five second-pass findings have completed [combined repair acceptance](../03_validation/VEDIC_ADVERSARIAL_REPAIR_VALIDATION_2026-10-09.md). The user authorized publishing those repairs on 10 October. VED-011 starts with source research and selection of finite activity/lineage profiles; it has not started and remains separately authorized work.

1. **Close existing product omissions:** VED-001/002/003/005 and their scoped VED-021/022 follow-through are complete and source-published. This first item's selected implementation scope is closed. Operational REST budgets remain a separate scope decision.
2. **Muhurta composition:** VED-004/006 are complete for the bounded sampled/JD-weekday profile. VED-007 is locally complete for all seven named families, including exact Sun/Moon transitions and sunrise-owned named-day composition. VED-008 is locally complete for the named source assessments and bounded day cells. VED-009 is locally complete for its six detectors and three source-scoped exceptions. VED-010 is source-published for its selected Lagna/Navamsa components; its optional Shadbala composition and subsequent admission defects have passed combined repair acceptance. **VED-011 is next**; integrating these products into generic scoring/search remains a separate scope decision.
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

## 21. VED-005 source publication, 8 October 2026

The authorized publication completed in the requested order:

- Generated wiki `293979c942b4083f59569f58a0e7b0d697bdbe39` was committed and pushed to `origin/master` first.
- Parent engine `77d34158cef7c936fdf6613f9be18ba5e8fad5aa` was committed and pushed to `origin/main` second, including the matching wiki gitlink.
- Both checkouts were clean and at zero divergence after publication; exact remote branch SHAs and generated-wiki synchronization were verified.

The 175 distinct latest passing tests remain the original selected VED-005
validation scope. This publication pass reconciled status prose and performed
documentation/whitespace checks; it did not alter the validated calculations,
test policy, version 6.9.9, release or deployment state. The subsequent Sayanadi
research documents are a new local package, not part of those published SHAs.

## 22. VED-002 source review and execution plan, 8 October 2026

The user selected Sayanadi after VED-005 publication. The
[source research](VEDIC_SAYANADI_SOURCE_RESEARCH_2026-10-08.md) collates local
Santhanam BPHS, an identified Sharma edition, Rao's textbook and a competing
Sanketanidhi/Hora Ratnam degree reading. Visual page review establishes the
selected BPHS within-sign Navamsa-ordinal profile, sunrise-owned ghati
ordinal, five-group name table and all nine body constants. The printed Sun
arithmetic is consistent; the existing fixture's Sa=1 is incorrect and masks
a different first substate remainder.

The unmodified engine's 34 selected tests pass, while an independent exact
rational classification audit demonstrates 1,015 disagreements in 14,580
boundary cases. Missing Moon/body fallbacks, hostile input admission and
absent chart/public/REST composition also require repair. The
[implementation plan](VEDIC_SAYANADI_IMPLEMENTATION_PLAN_2026-10-08.md) defines
four finite slices and their source, boundary, strict-input, time, reader,
public/REST and documentation gates. Historical effect prose and competing
degree-based variants retain their own source boundaries.

**VED-002 remains open for engine and integration work.** Research completion
does not close its implementation or VED-021/022 follow-through. The register
retains 24 stable IDs, six closed scoped packages and 18 open-or-bounded
packages. No VED-002 runtime, native substrate, dependency, golden baseline,
website or deployed endpoint changed in this source-audit checkpoint.

## 23. VED-002 local implementation closure, 8 October 2026

The user approved execution of the four-slice Sayanadi plan. The
[admission standard](../02_standards/SAYANADI_ADMISSION_STANDARD.md) and
[validation receipt](../03_validation/SAYANADI_VALIDATION_2026-10-08.md)
close the selected BPHS within-sign Navamsa-ordinal calculation, strict
name/ghati/body contracts, optional chart/node evaluation, reader-bound
sunrise/birth composition and owning Python/facade/REST surfaces. The
corrected source example, all source constants/tokens, 14,580 independent
rational boundary cases with zero disagreements, analytical uncertainties,
four real date/frame cases, polar absence and both startup-reader paths are
verified. The distinct latest test total is 278, with no failures/errors/skips.

VED-002 is `LOCAL_COMPLETE`; its scoped VED-021/022 validation/documentation
follow-through is complete. The current register has **24 stable IDs, seven
closed scoped packages (VED-001/002/003/004/005/006/015), and 17 open-or-bounded
packages**. Section 9's first item has no remaining selected implementation
work. Historical sections 20-22 retain their earlier checkpoint counts and
are superseded by this execution receipt.

The supplied-input and birth-clock contracts preserve omitted, evaluated and
unavailable distinctions. Legacy effect summaries carry explicit uncertified,
unevaluated provenance. Competing degree-lineage admission and a full textual
catalogue audit are independent source scopes, not hidden incomplete work in
this admitted numeric profile. Astronomical/native substrate, version,
dependencies, test policy and unrelated work are unchanged. Canonical and
generated documentation are reconciled locally; this package is uncommitted
and unpushed. Release, deployed REST and website/Urania adoption are separate.

## 24. VED-002 authorized source publication, 8 October 2026

The user authorized committing and pushing the completed Sayanadi package
before proceeding with VED-007. The containing source commits publish the
generated wiki first, then the parent engine's code, tests, canonical
documentation and matching wiki gitlink. Section 23's uncommitted statement
describes its earlier local-completion checkpoint. The 278-test receipt and
14,580-case rational audit retain their recorded verification scope.

This is source publication at version 6.9.9, with no release or deployment.
VED-007 begins after this checkpoint as a separate named-Muhurta package.

## 25. VED-007 two-window admission, 8 October 2026

The preceding Sayanadi publication is verified at engine
`acf5851c3b2369a9dd5630921437dc31c7064b4d` and generated wiki
`447768124157bc8df4d8be9347506da2d831b98d`, with matching remote SHAs and
clean checkouts at that publication checkpoint.

The authorized VED-007 package then admitted Abhijit and Brahma intervals
after reviewing the Avasthi Chintamani scan, Arunadatta/Hemadri commentary,
Raman transcription and local-library witnesses. Its canonical engine
owns source and compatibility policies, supplied/solved solar anchors,
root/endpoint bounds, per-window availability, civil sunrise-date ownership
and separate weekday eligibility. Seven exports, two facade methods and
two strict REST routes preserve that same result.

The [224-test receipt](../03_validation/NAMED_MUHURTA_VALIDATION_2026-10-08.md)
records independent rational formulas, source discrepancy handling,
boundary/hostile/partial cases, real DE441 polar/DST events, unchanged PAC
sunrise component tolerance and both serving-reader startup paths.
Source-formula, component-astronomy and HTTP evidence are stated separately.
VED-021/022 follow-through is complete at this scope.

The two-window integration is complete locally; VED-007 remains a bounded
package because its individually named additions still require admission.
There remain seven closed packages and seventeen open-or-bounded packages.
The new code and documentation are uncommitted/unpushed. Source publication,
release, deployed REST and website/Urania adoption remain separate.

## 26. VED-007 authorized source publication, 8 October 2026

The user authorized committing and pushing the completed Abhijit/Brahma
package. The containing source commits publish the five generated wiki
pages first, then the parent engine's implementation, tests, canonical
documentation and matching wiki gitlink. Section 25's uncommitted statement
records the earlier local-completion checkpoint. The 224-test receipt retains
its actual source, numerical, real-resource and transport verification scope.
Publication changes status and clarifies remaining scope; it does not alter
the validated arithmetic or acceptance thresholds.

Godhuli, Vijaya, Amrita, Ravi Yoga and Sarvarthasiddhi are still outstanding
parts of VED-007. Their rules have not yet completed source review,
implementation and validation. `SOURCE_RESEARCH` is not evidence that
classical sources are unavailable. VED-007 remains partially complete as a
whole, with its two-window engine/public/REST contract complete. Version
remains 6.9.9; source publication is separate from release and deployment.

## 27. VED-007 five-name local completion, 8 October 2026

The user authorized finishing the five outstanding names. The earlier
sections 25–26 describe the historical two-window checkpoint; their research
status is superseded for Godhuli, Vijaya, Amrita, Ravi Yoga and Sarvarthasiddhi.

- Primary source collation now supplies explicit Godhuli width/visibility
  restrictions, Vijaya's eleventh daylight part, both separately named Amrita
  tables, Ravi's inclusive Sun/Moon count and Sarvarthasiddhi's weekday table.
  The source packet records editions/pages/hashes, disagreements and the
  unidentified print edition of the digital Muhurta Sadhana witness.
- `moira.special_muhurta` supplies all five additions and a dated seven-name
  composition retaining the existing Abhijit/Brahma object. Eleven owning
  exports, three facade methods and three typed REST routes complete access.
- Numerical root bands, source eligibility, empty matches, missing astronomy
  and unevaluated activity suitability remain distinct. Sun and Moon star
  transitions both bound Ravi; weekdays belong to the requested sunrise day.
- Final combined acceptance: **383 passed, no failures/errors/skips**; **33
  DE441 resource uses**, all run. Complete source-table/pair coverage,
  independent rational and analytic cases, real DST/polar/reader/HTTP cases,
  and existing-family regression are documented in the linked receipt.
- Fourteen Python files pass 3.10 grammar checks with no new Ruff findings.
  REST inventory is 489 paths/operations. Canonical and generated docs are
  reconciled; no new runtime dependency or substrate change was introduced.

VED-007 is `LOCAL_COMPLETE` for its seven source-selected timing/presence
families. The alternative Amrita readings are supported, not conflated.
Universal activity elections, other Godhuli seasonal/optical readings and
other names called Amrita are not silently claimed; VED-008–011 retain their
own rule/purpose scope. Eight of the 24 packages are complete, sixteen remain
open/bounded. This paragraph records the local checkpoint; section 28 records
the subsequent source-publication authorization. No deployment is implied.

Owning evidence: [source packet](VEDIC_NAMED_MUHURTA_FIVE_SOURCE_AND_PLAN_2026-10-08.md),
[standard](../02_standards/NAMED_MUHURTA_STANDARD.md), and
[execution receipt](../03_validation/SPECIAL_MUHURTA_VALIDATION_2026-10-08.md).

## 28. VED-007 authorized complete source publication, 8 October 2026

The user authorized committing and pushing the completed five-name extension.
The containing engine/wiki package publishes all seven named families across
engine, curated Python/facade and REST surfaces. The generated wiki is
published first; the parent then records its exact gitlink. The implementation
acceptance remains **383 passed, zero failures/errors/skips**, with **33 DE441
resource uses**, all run. Publication changes status prose, not computation.

The source-selected completion boundary remains explicit: Amrita Siddhi and
Kalaprakasika Amirtha are different profiles; Godhuli's selected timing and
weekday exceptions are inspectable; numerical uncertainty is retained. Eight
of 24 stable packages are complete and sixteen remain open/bounded. Source
publication does not imply a package release, deployed endpoint or website.

**Recommended next: VED-008 — Panchanga Shuddhi.** Establish named source
rules for Tara-cycle/paryaya distinctions, Panchaka Rahita and finer
Yoga/Karana eligibility, then provide canonical engine results and equally
strict REST transport. Existing Tara/Chandra Bala must remain intact. This
recommendation does not start that separate implementation package.

## 29. VED-008 research and proposed admission, 8 October 2026

The user authorized research following the completed VED-007 publication.
The [source research packet](VEDIC_PANCHANGA_SHUDDHI_SOURCE_RESEARCH_2026-10-08.md)
collates online primary witnesses and local corpus scans, including the 1946
Sastri/Bhat Brihat Samhita, image-only chapter 100, and P. S. Sastri's textbook
filed under the Raman author folder. Printed pages and scan hashes control
attribution; OCR absence is not source absence.

The proposed finite package covers Panchaka Rahita, separately selected MC/PS
Tara-cycle rules, the nine adverse Nitya Yogas with partial periods, and an
eleven-Karana catalogue plus Bhadra components. It states clock derivations,
exception conflicts, strict engine/REST contracts and concrete acceptance
cases. The private arithmetic check proves the KP offset formula and direct
remainder table agree in all 68,040 bounded inputs and checks two printed
examples; it is not astronomical or predictive validation.

Research is complete for these admission decisions. The inconsistent MC Hindi
thirds interpretation and Raman initial-ghati example have specific recorded
deferral conditions; they do not prevent the recommended named profiles.
Universal Bhadra exception precedence is unclaimed. Runtime implementation,
REST additions, scoring/search integration and publication have not started.
Eight stable packages remain complete and sixteen open/bounded.

## 30. VED-008 local implementation closure, 9 October 2026

The user approved implementing the named profiles together while preserving
existing Tara/Chandra behavior. The complete selected package now includes
Panchaka arithmetic/current Lagna, separate MC and PS Tara-cycle readings,
nine-Yoga timed restrictions, eleven Karana activity entries, and independent
Bhadra residence/day-night/mouth/tail claims. Derived clocks and simultaneous
restrictions/exceptions are visible; no universal favorable verdict is added.

Sixteen owning exports, three facade methods and catalogue/direct/day REST
routes preserve the engine result. Sunrise-owned cells use full solved parent
events, changing Lagna, coherent true ayanamsa, explicit root bands, bounded
work and typed polar/missing-component states. The existing score/search and
Tara/Chandra contracts are unchanged.

Acceptance totals **622 passed, zero failures/errors/skips**, with **92 DE441
resource uses**, all run: 608 new/compatibility unit/server cases and 12 new
real-kernel integration cases, plus two final analytic solar-admission cases. Source tables, all 68,040 Panchaka arithmetic
inputs, both Tara variants, rational temporal windows, strict REST, DST/polar
and configured/discovered reader paths are covered in the
[receipt](../03_validation/PANCHANGA_SHUDDHI_VALIDATION_2026-10-09.md).

Nine of 24 stable packages are complete; fifteen remain open/bounded.
Implementation, source research and canonical/generated documentation are
local and uncommitted/unpushed. Version 6.9.9 is unchanged; no release,
deployment or website/Urania work is included. VED-009 cancellation rules,
VED-010 strength overlays and VED-011 complete purpose elections retain their
own scope. Particular source disagreements remain named exclusions rather
than silently merged rules.

## 31. VED-008 authorized source publication and next package, 9 October 2026

The user authorized committing and pushing the complete VED-008 package,
including the source research, engine/public/facade implementation, three
strict REST routes, independent fixtures, tests and canonical/generated docs.
Publish the generated wiki first and commit its exact gitlink with the engine.
The [validation receipt](../03_validation/PANCHANGA_SHUDDHI_VALIDATION_2026-10-09.md)
retains the 622-test acceptance and source/clock/coverage boundaries. Nine
stable packages are complete; fifteen remain open/bounded. Source publication
does not imply a version release, deployment or website/Urania adoption.

**Recommended next: VED-009 — Muhurta dosha and Parihara.** First collate the
source-specific Vishanadi/Tyajya, Yamaghanta and finer Gandanta detection
rules, clocks, exceptions and boundary ownership. Then select a finite initial
profile set and separately named cancellation rules. Every neutralization must
retain the detected condition, the source rule and the evidence that its
prerequisites are met; missing evidence must remain unknown. Existing Shuddhi
restrictions/exception overlaps must not silently acquire universal precedence.

The subsequent implementation should reuse the bounded dated composition,
carry source-separated detected/neutralized/unavailable/excluded states, and
arrive with canonical public/facade and equally strict REST support. Independent
source fixtures, exact boundary cases and real-reader/HTTP parity are its
acceptance gates. VED-010 then adds selected Lagna/strength/Navamsha composition;
VED-011 builds complete purpose profiles on those evaluated components.
This sequence is a recommendation, not authorization to start those packages.

## 32. VED-009 source-selected local completion, 9 October 2026

The user selected the VED-009 package after the published release-hardening
repair. The [source packet](VEDIC_DOSHA_PARIHARA_SOURCE_AND_PLAN_2026-10-09.md)
collates inspected MC Avasthi, Kalaprakasika and local Santhanam BPHS scans,
records the Rohini worked clock example and preserves differing Mula,
Purva Bhadrapada and tithi-Gandanta readings as named policies.

The canonical [dosha/Parihara owner](../../moira/muhurta_dosha.py) implements
stellar Vishanadi, weekday/star and daytime Yamaghanta, and temporal
nakshatra/tithi/Lagna Gandanta. Three opt-in exceptions retain raw witnesses
and nullable prerequisite evidence. Cross-source exceptions are excluded;
missing evidence cannot manufacture an affirmative cancellation. Dated
composition solves full parents, retains fixed-width carryover and merges
all overlapping numerical bands, including edges whose estimates fall just
outside the sunrise day.

Fifteen owning exports, three facade methods and catalogue/direct/day REST
routes provide strict, lossless access. **153 new tests pass**, including
independent source/rational and analytic cases, six real-date component
comparisons, polar/DST/reader cases and both configured/discovered HTTP
startups. Existing named/Shuddhi regression tests also pass. The
[validation receipt](../03_validation/MUHURTA_DOSHA_VALIDATION_2026-10-09.md)
records the separate release-gate and documentation checks without treating
internal numerical agreement as an external astrological oracle.

Final local acceptance totals **1,999 passed, one existing unrelated
void-of-course skip, zero failures/errors**. All 55 Release Hardening test
files and all six generated/release documentation checks pass; DE441 records
231 successful resource uses across the feature and release runs. The REST
inventory has 495 operations. Exact public snapshots and class-docstring
governance include this package, without weakening their assertions.

VED-009 is `LOCAL_COMPLETE` for this finite six-detector/three-exception
package. Ten of 24 stable packages are complete; fourteen remain open/bounded.
Scoped VED-021/022 follow-through is complete. The full twenty-one-dosha
catalogue, other Tyajya types and angular/Abhukta variants remain explicitly
listed source extensions. These exclusions do not imply unavailable sources.

**Recommended next: VED-010**, selected Lagna/strength/Navamsa composition
and its dependent exception prerequisites, followed by VED-011 purpose
profiles. Neither package is started here. Current VED-009 work is local,
uncommitted/unpushed at version 6.9.9; release, deployment and website/Urania
adoption remain separate.

## 33. VED-009 authorized source publication, 9 October 2026

The user authorized committing and pushing the completed VED-009 package,
then proceeding with VED-010. Publish the generated wiki first, followed by
the engine source, tests, canonical documentation, publication manifest and
exact wiki gitlink. Section 32's uncommitted statement records its earlier
local checkpoint. The acceptance remains 1,999 passed, one existing unrelated
void-of-course skip and zero failures/errors; publication does not change
arithmetic or validation thresholds. Version 6.9.9 remains unchanged.

VED-010 is now authorized as the next engine/REST package. Begin with source
collation for Lagna, planetary-strength and Navamsa-shuddhi composition and
its named purpose/exception prerequisites; reuse existing Varga/Shadbala
owners without hiding school choices or missing inputs. VED-011 complete
purpose elections remain separate. Source publication does not imply a
package release, deployment or website/Urania adoption.


## 34. VED-009 publication and VED-010 selected composition

VED-009 was committed and pushed wiki-first: generated wiki
`ed68937510e6ce162da82420b4f42415c0480161`, then engine
`571788a1fe705b096d5a69911f30be583c7c45d7`. Remote branch tips and the parent
gitlink were verified. Hosted [Release Hardening](https://github.com/TheDaniel166/moira/actions/runs/37933596179)
and [Acceptance Matrix](https://github.com/TheDaniel166/moira/actions/runs/37933596186)
completed successfully for that engine SHA.

The user then authorized VED-010. Source inspection established finite general
and marriage Lagna profiles, named Navamsa variants, fractional-aspect support,
MC87/92's placement score and scoped MC88 exceptions. Shadbala is separate
context, not a blanket override. Source availability is established; broader
remedies and VED-011 complete purpose elections remain explicit extensions.

The shared Varga D9 partition and Venus-to-Moon natural relation were corrected
against BPHS6.12 and3.55. Their dependent regression evidence is part of this
package. See the linked source record, standard and validation receipt for
final acceptance status. VED-010 is included in the authorized wiki-first
source-publication package.


VED-010 acceptance is complete locally: **363 new feature tests**, **881
affected existing Vedic regressions**, and all four release-hardening groups.
The deduplicated final outcome is **2,856 passed, one existing no-aspect
void-of-course skip, zero unresolved failures/errors**. All 18 changed Python
files pass Python3.10 grammar; full scoped Ruff, exact API/docstring guards,
all six release-facing artifact checks and whitespace checks pass. The REST
inventory now has 498 operations; the new unit/REST files are added to CI.

Eleven of 24 stable packages are locally complete; thirteen remain open/bounded.
**Next at this checkpoint: VED-011**, selected complete purpose elections;
section 35 subsequently puts the identified repairs first. This next package is
not started by VED-010 closure. The user subsequently authorized VED-010
commit/push, followed by a deep adversarial review of the current Vedic
system. This publication includes the generated wiki first, then the engine
source, tests, canonical documents, publication manifest and exact gitlink.
The review is a separate assessment of the resulting snapshot.

## 35. VED-010 publication and adversarial repair priority

VED-010 was published wiki-first at `9d3591367af6311bbec5f47afeab7918939b5724`,
then engine `b578ec89b90f709c8e64d5d9405ca06d29fcc69c`. Hosted
[Release Hardening](https://github.com/TheDaniel166/moira/actions/runs/37995452783)
and [Acceptance Matrix](https://github.com/TheDaniel166/moira/actions/runs/37995452792)
succeeded. The separate adversarial review identified **eleven findings:
four P1 and seven P2**, comprising ten runtime/contract defects and one stale
validation fixture. Their root causes predate VED-010.

The completed broader regression run was **4,387 passed, one failed, zero
errors/skips**, across 112 files, with all 406 DE441 resource receipts run.
The failure reproduces alone and is attributable to the Einstein alternate-
Dasha fixture retaining balances derived with the superseded precession
scalar. Independent source/boundary/HTTP probes establish the other findings,
including a valid dated Lagna request failing only when Shadbala is included.
The broader run is not green; the narrower release gates do not override it.

The user requested a [plan covering all eleven repairs](VEDIC_ADVERSARIAL_REPAIR_PLAN_2026-10-09.md).
It groups full-parent Dasha timing and fixture reconciliation, Varga boundaries,
source-defined Shadbala components, war allocation/evidence, and reader/scan
robustness into five packages with individual and combined acceptance.
VA-01 through VA-11 remain open. This is a planning checkpoint, with no
corrective implementation or new publication. VED-011 follows their closure.


## 36. All eleven adversarial repairs closed locally — 9 October 2026

The user approved the five-package plan and implementation. VA-01 through
VA-11 are now closed across engine, curated/facade and REST surfaces. Dasha
subperiods use full parents before clipping; Varga boundaries use one exact
partition; source-selected strength components use explicit geometry; one
canonical ledger governs all war adjustments; borrowed readers and Sade Sati
work limits are enforced. The shared temporary-friendship correction and the
geocentric REST strength frame are documented dependent repairs.

The [completion/source receipt](../03_validation/VEDIC_ADVERSARIAL_REPAIR_VALIDATION_2026-10-09.md)
records **6,276 distinct passing tests, one existing unrelated VOC skip,
zero unresolved failures/errors**, across 173 files. Every original 112-file
adversarial selection was rerun, plus new/affected consumers and all 62 current
release-hardening files. Five initial migration failures were resolved with
exact comparisons retained; the 23-file reconciliation passed 1,215 tests.
All 835 DE441 resource uses ran. Independent 65,880-case Varga and 4,320-case
D60 consistency corpora remain green. Source disagreements, retained
conventions and sampling limits remain visible in the policy receipts.

This closes the repair checkpoint, not the remaining Vedic roadmap. Eleven
of 24 VED packages remain complete and thirteen open/bounded; VA identifiers
are repairs, not new VED packages. **Next: VED-011**, selected complete purpose
elections. It is not started here. All changes remain local, uncommitted and
unpushed at 6.9.9. Publication, release and deployment remain separate actions.

## 37. Second adversarial pass: five repairs closed locally — 9 October 2026

The second review identified five additional composition/admission defects.
The approved repair now unifies dated Shadbala's UTC weekday evidence,
canonicalizes Lagna/Bhava positions against their accepted strength context,
recomputes house-independent strength components during receipt validation,
checks Dasha full-parent/child and year provenance across engine/REST, and
uses one half-open Sade Sati longitude normalization. Existing partial-child
REST requests remain admitted through an explicit validator mode; generated
trees continue to require complete coverage. Declared contradictory evidence
rejects in both modes.

The updated [validation receipt](../03_validation/VEDIC_ADVERSARIAL_REPAIR_VALIDATION_2026-10-09.md)
records **6,342 distinct passing tests, one existing unrelated VOC skip and
zero unresolved failures/errors**, across 175 files. The 121-file Vedic run
and all 64 release-hardening files completed; a final 17-file reconciliation
passed 1,104 tests, including all three compatibility regressions identified
by those runs. All 814 DE441 resource receipts in the three runs executed.
The 66 new regression cases are wired into CI. Original adversarial probes,
250 generated Dasha trees / 166,118 nodes, all six documentation checks,
grammar, scoped Ruff and whitespace checks also pass.

This closes VA2-01 through VA2-05. The VED package count and remaining policy
boundaries are unchanged; VED-011 remains the next separately authorized
package. The complete repair work remains local and uncommitted/unpushed.

## 38. Combined repair publication package — 10 October 2026

The user authorized committing and pushing all accumulated repairs: VA-01
through VA-11 and VA2-01 through VA2-05, with their regression tests, CI
selection, owning standards and validation receipt. Publication order is the
generated wiki first, then the engine and its exact wiki gitlink. Sections
35–37 preserve the review and local-completion states at their earlier
checkpoints; their uncommitted/unpushed statements are historical.

The combined acceptance remains **6,342 distinct passing tests, one existing
unrelated VOC skip and zero unresolved failures/errors**, with the resource
execution and source-policy limits recorded in the validation receipt. The
roadmap now consistently identifies **VED-011** as the next package: select
finite purpose profiles, collate their sources and disagreements, then admit
engine and REST rules with explicit evaluated/excluded/unavailable evidence.
Marriage variants, construction/Vastu, travel and business are candidate
scopes, not a promise of universal activity coverage. Research and
implementation of VED-011 have not begun in this publication package.

Version remains 6.9.9. Source publication, release and deployment remain
distinct; no tag, package release, runtime deployment or website/Urania
adoption is included.
