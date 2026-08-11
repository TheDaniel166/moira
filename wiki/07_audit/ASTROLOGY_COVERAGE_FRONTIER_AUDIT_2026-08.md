# Moira Astrology Coverage Frontier Gap Audit (2026-08)

**Document:** `wiki/07_audit/ASTROLOGY_COVERAGE_FRONTIER_AUDIT_2026-08.md`
**Audit date:** 2026-08-09
**Last amended:** 2026-08-11 — Track B bounded implementation checkpoint

**Original repository baseline:** `c868fd082ceabda16793e1c3d6c26218ad8d83b6` (`origin/main` at the original audit)

**Track A admission baseline:** `7090255e2d6cc41f7b4df15417512412f0ad5366`

**Track B checkpoint:** branch `codex/track-b-western-research-20260811`
from baseline `24e90f9fa4cdbe9692d6f70469df7863f4b15d36`; the admission commit
containing this amendment is unreleased and undeployed

**Scope:** Moira calculation engine, facade, registered server contracts, tests, standards, and doctrine records
**Change type:** Capability assessment amended to record an admitted implementation; this document does not authorize another implementation, release, website work, or Workspace adoption

---

## 1. Executive conclusion

Moira no longer has broad foundational astrology gaps. Its existing calculation
surface is unusually deep across Western natal and predictive astrology,
Hellenistic composition, Jyotish, relationship charts, spatial techniques,
fixed stars, eclipses, harmonics, Uranian methods, and several historical
specialties.

On the Track B checkpoint, the two previously largest Western gaps now have
bounded, calculation-only contracts. The remaining strategic frontier is
concentrated in:

1. **Birth-time rectification evidence** as a candidate-comparison instrument,
   not an automatic claim that one time is astrologically true.
2. **Western annual revolutions** as a source-locked medieval/Arabic tradition
   distinct from generic return calculation and Jyotish Tajika/Varshaphal.
3. **Separately sourced Horary follow-ons** beyond the admitted Lilly evidence
   contract, without turning evidence into an answer oracle.
4. **Separately sourced Mundane subjects or interpretations**, only where a
   finite doctrine and credible validation method can be established.

Track A has now admitted exact transits to composite and Davison charts,
fixed-star astrocartography, relocated-return composition, and explicit-epoch
transiting astrocartography. Progressed or directed relationship charts,
progressed or directed locational modes, cross-chart multi-body patterns, and
chart-backed comet MC/IC/ASC/DSC lines remain bounded follow-on gaps rather than
evidence that the admitted Track A contracts are incomplete.

Track B now admits one Lilly 1647 Horary evidence profile and one neutral
Mundane event-chart profile spanning cardinal ingresses, strictly preceding
primary syzygies, explicitly named eclipse epochs, and complete
Jupiter-Saturn ecliptic-longitude conjunction sequences. Both have curated
root/facade parity, reader-bound `Moira` methods, and one strict REST route.
Neither contract interprets, predicts, scores, advises, infers a topic or
capital, or creates a shared judgement layer. This is an engine admission
checkpoint, not a package release, website adoption, or deployment.

KP astrology, selected deferred Jyotish branches, Chinese and Tibetan systems,
and historical astrological magic remain possible longer-horizon programmes.
Medical, financial, meteorological, and agricultural prediction should not be
prioritized without a much stronger validation and product-safety basis.

This audit does **not** reopen completed Hellenistic work, closed experimental
heliacal branches, unsupported Hermetic geometry, Decennial L3/L4, or Valens
distribution interpretation.

---

## 2. Why a new audit was necessary

The earlier [Feature Audit 2026](FEATURE_AUDIT_2026.md) was taken at commit
`8fc17b8efb1fa38723458d4f851520183d93ecf9` on 2026-05-15. The
[Western V2 Update](WESTERN_V2_UPDATE_2026-06.md) was a useful corrective pass,
but later implementation closed several of its gaps. Neither document should be
used by itself as the current implementation backlog.

Examples of superseded claims include:

| Historical claim | Current repository truth |
|---|---|
| Western electional is only a generic predicate engine | `moira/western_electional.py` and its construction, context, Dorothean, Sahl, judgement, ranking, scanning, and window modules now form a doctrine-owned subsystem with server contracts and validation records. |
| Jaimini stops at karakas | `moira/jaimini_extended.py` now includes rasi drishti, arudhas, argala, karakamsa, and a named first-cycle Chara Dasha policy. |
| The Vedic natal yoga catalog is absent | `moira/yogas.py` exposes a proof-bearing multi-family yoga engine. |
| Kakshya transit and Shodhya Pinda are absent | Both are implemented in `moira/ashtakavarga.py`. |
| Tajika/Varshaphal is absent | `moira/varshaphal.py` is a deep annual-return doctrine subsystem with server exposure. |
| Composite and Davison charts cannot act as transit targets | Exact transit searches against immutable composite and Davison targets are admitted through `moira.relationship_forecasting`, facade and `Moira` parity, and registered REST routes. Progressed or directed relationship charts and cross-chart multi-body patterns remain outside that contract. |
| Fixed-star and time-dependent astrocartography are absent | Fixed-star MC/IC/ASC/DSC lines and zenith/nadir points, relocated returns, and explicit-epoch transiting astrocartography are admitted. Progressed or directed locational modes and chart-backed comet MC/IC/ASC/DSC lines remain outside the admitted contract. |
| Triacontaeteris, Valens distributions, and deeper Decennials are unfinished Hellenistic work | The current Hellenistic contract treats these as closed exclusions or unsupported claims, not implementation backlog. |

The correction rule is simple: current code, registered exports, tests,
standards, and doctrine receipts outrank older audit prose.

---

## 3. Audit method and vocabulary

### 3.1 Inspected surfaces

This pass inspected:

- `moira/` engine modules and facade mixins;
- `moira_server/` registered models, serializers, services, and routers;
- `tests/unit/`, `tests/integration/`, and `tests/server/`;
- `wiki/01_doctrines/`, `wiki/02_standards/`, `wiki/03_validation/`,
  `wiki/05_research/`, and `wiki/06_roadmap/`;
- current and historical feature audits;
- official contemporary software documentation only as evidence that a workflow
  is used in practice, never as authority for historical doctrine.

At the amended baseline the repository contains 275 Python files under
`moira/`, 353 unit-test files, 84 integration-test files, 114 server-test files,
and 55 named backend standards. These counts establish scale only; they are not
correctness scores.

### 3.2 Status classes

| Status | Meaning |
|---|---|
| **Mature** | A named engine surface exists with policy, typed results, tests, and documentation appropriate to its claims. |
| **Partial** | Meaningful substrate or a bounded technique exists, but the astrological family is not complete as a first-class contract. |
| **Absent** | No first-class engine family exists; isolated ingredients do not count as the technique. |
| **Deferred** | The repository explicitly records that source, lineage, input, or validation prerequisites are unresolved. |
| **Closed exclusion** | The project has deliberately decided not to productize the claim. This is not backlog. |
| **Product/transport gap** | Engine truth exists but a facade, server, or user-facing surface lags. This is not a missing astrological calculation. |

### 3.3 What qualifies as a real gap

A candidate is a real engine gap only when at least one of the following is
true:

- the technique requires calculations that do not exist;
- the technique requires a named doctrine or lineage policy that does not
  exist;
- existing ingredients cannot be composed without inventing hidden defaults;
- there is no typed result capable of preserving evaluated, not-evaluable,
  unresolved, and excluded states;
- the current calculation cannot be independently validated at the level of
  the proposed claim.

Missing interpretation prose, website cards, display formatting, or a dedicated
REST route does not by itself establish an astrological engine gap.

---

## 4. Current high-level coverage

### 4.1 Areas that are not current frontier gaps

The following areas already have substantial engine ownership and should be
deepened only in response to a specific defect or independently justified
extension:

- natal chart construction, house systems, angles, frames, and relocation;
- aspects, whole-sign relationships, declination contacts, midpoints,
  antiscia, patterns, and planetary condition;
- dignities, receptions, triplicity, bounds, faces, almutens, lots, and
  special points;
- transits, ingresses, stations, returns, progressions, solar arcs, primary
  directions, profections, Firdaria, Zodiacal Releasing, and admitted
  Decennials;
- the unified non-interpretive Hellenistic chart profile;
- Western electional profiles, judgement receipts, rankings, and bounded
  window scanning;
- synastry, overlays, midpoint composites, Davison variants, relationship
  condition networks, and exact transits to composite and Davison targets;
- astrocartography, local space, geodetic work, parans, relocated charts,
  fixed-star astrocartography, relocated-return composition, explicit-epoch
  transiting astrocartography, and subplanetary points;
- fixed stars, variable and multiple stars, Behenian and Royal stars,
  heliacal phenomena, eclipses, and occultations;
- harmonics, harmonic transits, Huber techniques, Uranian bodies and points,
  chart shapes, astrodynes, and progressed astrodynes;
- Jyotish sidereal and nakshatra utilities, vargas, dignities, Shadbala,
  Ashtakavarga, dashas, Jaimini core/first-cycle extensions, yogas, upagrahas,
  avasthas, Panchanga, Muhurta, Sade Sati, Tajika/Varshaphal, and Pancha
  Pakshi;
- Arabic lunar mansions, planetary hours, Babylonian cycle material, and
  Sothic calculations.

This list does not claim every branch is infinitely complete. It means these
are existing families, not blank spaces that should be rediscovered as new
projects.

### 4.2 Closed exclusions that must not reappear as gaps

- Hermetic decan ruling-star claims and unsupported projection/rising
  geometry;
- the removed `decan_hours()` experiment;
- Decennial L3/L4 schemes without an admitted source-owned definition;
- Valens distribution effect or quality interpretation;
- Triacontaeteris without an adequate edition and reproducible doctrine;
- quarantined Jones/Paranal site-specific heliacal experiments;
- synthetic Hellenistic scores or interpretive verdicts;
- interpretive prose, personal advice, or recommendation generation inside
  Moira's calculation contract.

Reconsidering a closed exclusion requires a new evidence packet and an explicit
decision to reopen it. It must never happen through roadmap wording alone.

---

## 5. Confirmed frontier gaps and bounded closures

### 5.1 Horary/interrogational astrology

**Status:** Bounded Track B evidence contract admitted at the branch checkpoint
**Strategic value:** Follow-on only under a separately sourced finite policy
**Likely scope:** Large and doctrine-heavy beyond the admitted Lilly profile

**Existing substrate**

- horary-tagged lots in `moira/lots.py`;
- houses and turned-house arithmetic;
- essential and accidental dignity, reception, sect, planetary condition,
  planetary hours, and void-of-course computation;
- applying/separating aspect truth, perfection-event machinery, stations, and
  sign ingress detection;
- a source-conscious Western electional architecture that demonstrates how a
  named traditional policy can be kept separate from generic search.

**Admitted Track B contract**

- `moira.horary` owns immutable question-time, house-policy, turned-house,
  significator, planetary-hour, consideration, sect, perfection, and provenance
  evidence;
- the high-level adapter computes strict no-fallback houses, the traditional
  seven positions, and planetary-hour truth on one explicit reader;
- same-planet, Lilly day/night triplicity, and same-nature hour-agreement paths
  are source-locked to the 1647 edition;
- the existing six-form Lilly perfection engine is composed and semantically
  revalidated instead of duplicated;
- missing or incompatible dependencies remain typed `not_evaluable`;
- five curated root/facade symbols, a reader-bound `Moira` method, and one
  strict Horary REST route preserve the same evidence policy.

**Still outside the contract**

- topic inference from free text, yes/no answers, outcome or timing prose,
  scores, confidence, advice, and recommendations;
- automatic rejection merely because one consideration or hour agreement does
  not support radicality;
- a universal cross-author Horary doctrine or generic shared judgement layer;
- unsourced horary-tagged lots, descriptive person matching, and unresolved
  historical clock/calendar reconstructions; and
- medical, legal, financial, or other professional advice.

**Follow-on gate**

Any additional Horary doctrine requires its own identified lineage, edition,
finite evidence contract, ambiguity ledger, and worked validation fixture. It
must compose the admitted atomic truth without turning the engine into an
answer oracle.

### 5.2 Mundane astrology

**Status:** Neutral Track B event-chart profile admitted at the branch checkpoint
**Strategic value:** Follow-on only for separately sourced subjects or doctrine
**Likely scope:** Large beyond neutral astronomical event/chart composition

**Existing substrate**

- Jupiter-Saturn great-conjunction cycles in `moira/cycles.py`;
- sign ingresses, lunar phases, syzygies, returns, stations, and aspect events;
- global solar/lunar eclipse geometry and cartography;
- chart construction, houses, geographic relocation, astrocartography,
  subplanetary points, and local-space geometry;
- eclipse-to-natal target matching that can be generalized only if the target
  identity remains explicit.

**Admitted Track B contract**

- four cardinal-ingress roots and the separately named Ramesey 4/2/1 cadence;
- both primary-syzygy candidates plus the nearest strictly preceding selector;
- solar/lunar eclipse receipts that keep greatest eclipse, conjunctions, and
  contacts separately named;
- complete Jupiter-Saturn ecliptic-longitude conjunction sequences with every
  root retained;
- content-derived active-reader identity, coverage, explicit event clocks, and
  fail-closed product/frame/search revalidation;
- explicit caller-owned location role, source, validity interval, coordinates,
  house system, and local projection state;
- seven curated root/facade symbols, four reader-bound `Moira` methods, and one
  strict four-way-discriminated Mundane REST route.

**Still outside the contract**

- automatic capital or geopolitical subject selection;
- polity, organization, office, national-nativity, country-sign, or mundane
  subject identity doctrine;
- political, economic, market, conflict, disaster, agricultural, fertility,
  or weather interpretation and prediction;
- conjunction cluster/mutation-cycle claims, automatic event ranking, and
  synthetic scores; and
- any shared Horary/Mundane judgement layer.

**Follow-on gate**

Any subject or interpretive branch requires a separately source-locked finite
contract and evidence appropriate to the claim. The admitted neutral global
event and local-chart receipts must remain independently visible.

### 5.3 Predictive relationship charts

**Status:** Bounded Track A contract admitted; deeper predictive modes remain partial

**Strategic value:** Bounded follow-on only

**Likely scope:** Small-to-medium per separately admitted mode

**Admitted Track A contract**

- synastry aspects and overlays;
- midpoint composite construction;
- multiple Davison constructions;
- exact moving-body aspect perfections to immutable composite and Davison
  planet, node, angle, and cusp targets;
- stable derived-chart identity and complete search-policy provenance;
- root, facade, reader-bound `Moira`, serializer, model, and registered REST
  parity for the admitted transit surface.

**What remains outside the admitted contract**

- progressed or directed relationship-chart contracts that preserve which chart
  was advanced and by which policy;
- cross-chart multi-body pattern detection;
- orb entry/exit windows and interpretive relationship forecasting.

**Follow-on admission gate**

Any progression, direction, or pattern follow-on must reuse canonical chart and
aspect truth, preserve the derived-chart identity and advancing policy, and
receive its own independent fixtures. It must not widen the exact-transit v1
contract by implication.

### 5.4 Dynamic locational astrology

**Status:** Bounded Track A contract admitted; deeper dynamic modes remain partial

**Strategic value:** Bounded follow-on only

**Likely scope:** Medium per separately admitted geometry family

**Admitted Track A contract**

- planetary MC/IC/ASC/DSC astrocartography;
- selected-asteroid MC/IC/ASC/DSC lines and asteroid/comet zenith/nadir
  subplanetary points;
- local-space, geodetic, paran, and relocated-chart calculations;
- source-resolved true-of-date fixed-star MC/IC/ASC/DSC lines and zenith/nadir
  points using equatorial geometry;
- solar, lunar, and planetary return charts recast into a relocated local house
  frame without changing the return moment or celestial snapshot;
- caller-supplied, explicit-epoch transiting astrocartography with adjacent line
  displacement receipts.

**What remains outside the admitted contract**

- progressed or directed angular geography over time;
- chart-backed comet MC/IC/ASC/DSC line generation;
- interpolation, city or travel ranking, and interpretive location scoring.

**Follow-on admission gate**

Every line or point must remain an engine geometry product. Interpretive city
rankings and travel recommendations belong downstream. Any new progressed,
directed, or comet line family must identify its chart/epoch policy, preserve
body and ephemeris provenance, and add independent geometry fixtures rather
than relying on incidental planet-compatible behavior.

### 5.5 Birth-time rectification evidence

**Status:** Absent as a subsystem; strong substrate
**Strategic value:** High practitioner utility, high epistemic risk
**Likely scope:** Medium for evidence tooling; unacceptable as an automatic
truth oracle

**Existing substrate**

- high-resolution chart construction across candidate times;
- transits, progressions, solar arcs, primary directions, returns, eclipses,
  profections, and time-lord systems;
- batch and event-search infrastructure;
- exact angle, house, midpoint, and aspect calculations.

**What is missing**

- an immutable life-event input model with uncertainty windows;
- generation of candidate birth-time intervals;
- per-technique evidence receipts linked to each event and candidate;
- sensitivity analysis showing which outputs materially change with time;
- contradiction and missing-data reporting;
- a neutral comparison matrix that does not fabricate a single correct time.

**Admission gate**

Moira may compute candidate-dependent evidence. It must not claim that an
astrological score proves a birth time. Any weighting policy must be named,
versioned, optional, and decomposable into its observed components.

### 5.6 Western annual revolutions

**Status:** Partial substrate; doctrine family absent
**Strategic value:** Medium-high traditional expansion
**Likely scope:** Medium-to-large

**Existing substrate**

- exact solar, lunar, and planetary return timing;
- return-chart construction;
- profections, directions, lots, dignities, house rulership, and time lords;
- a deep Tajika/Varshaphal system that must remain culturally and doctrinally
  distinct.

**What is missing**

- a named medieval/Arabic/Latin annual-revolution policy;
- explicit natal-versus-revolution chart joins;
- lord-of-the-year and revolution-specific testimony under an identified
  lineage;
- relocation and locality policy for the return chart;
- source-owned worked examples independent of Moira.

**Admission gate**

Do not rename Tajika output as Western revolution doctrine. Select and cite an
edition, preserve conflicting methods as named policies, and begin with typed
components rather than a synthesized annual prediction.

---

## 6. Longer-horizon candidate programmes

### 6.1 KP astrology

**Status:** Absent apart from the Krishnamurti ayanamsa option

A real KP implementation would require unequal star/sub/sub-sub divisions,
cuspal sub-lords, house significators, ruling planets, event timing, and KP
horary policies. These are not implied by having a KP ayanamsa. Source rights,
edition identity, and lineage differences must be settled first.

### 6.2 Explicitly deferred Jyotish depth

The following are known, recorded deferrals rather than accidental omissions:

- Kalachakra Dasha and its Savya/Apasavya lineage choices;
- Sayanadi Avasthas, which require birth ghatis and additional native-name
  inputs;
- further Chara Dasha lineages and later cycles;
- selected long-tail Muhurta rules, named windows, neutralizations, and
  source-owned purpose profiles;
- remaining lineage-specific yoga and avastha expansions.

These should be considered only after rechecking the current
[Vedic Phase 2 gap register](../06_roadmap/vedic_jyotish_phase2_gaps.md), because
much of its original prose is historical beneath later "closed" notices.

### 6.3 Chinese and Tibetan systems

**Status:** Absent

Potential scopes range from a contained Chinese 28-Xiu lunar-mansion engine to
full BaZi/Four Pillars, Zi Wei Dou Shu, or Tibetan calendrical astrology. These
are not parameter additions to Western or Jyotish code. They require their own
calendar, ontology, source, transliteration, lineage, and validation programme.

A 28-Xiu astronomical identity pilot would be a more bounded first research
question than beginning with a full interpretive Chinese system.

### 6.4 Historical astrological magic

**Status:** Partial ingredients; no admitted family

Moira already owns planetary hours, electional conditions, Behenian stars,
Arabic lunar mansions, and some historical talismanic correspondences. A
coherent astrological-magic profile would still require a named source lineage,
safe product boundaries, explicit exclusion of harmful instructions, and a
decision about whether historical correspondence data belongs in the engine at
all.

### 6.5 General research and corpus tooling

**Status:** Cross-cutting opportunity, not an astrology doctrine

A reusable research layer could evaluate large chart/event corpora, preserve
dataset licenses and subject provenance, create blinded candidate sets, and
compare astrological hypotheses without embedding interpretive conclusions.
This could strengthen every future admission gate, but it should not be counted
as a missing astrological technique.

---

## 7. Areas not recommended for near-term productization

| Area | Reason for caution |
|---|---|
| Medical astrology and decumbiture | Health claims are high stakes; historical rules are not clinical evidence. At most, support historical research objects with an explicit medical-use prohibition. |
| Financial or market prediction | High-stakes financial implications and weak independent validation make automated forecasts inappropriate for an engine correctness claim. |
| Astrometeorology | Moira can calculate sky events, but that does not establish predictive meteorological skill. Modern weather belongs to physical forecast data and models. |
| Agricultural/planting prediction | Calendar and lunar-phase utilities are defensible; claims about crop outcomes need agricultural evidence not presently owned by the project. |
| Psychological, vocational, evolutionary, or past-life interpretation | These are primarily interpretive schools. Their prose and counselling frameworks are not missing astronomical calculations. |
| Degree-symbol systems and proprietary modern products | Often content- or license-led rather than computational; require separate rights and product review. |

An area may be historically interesting without being appropriate as a public
prediction product.

---

## 8. Practitioner-workflow cross-check

Official contemporary software documentation demonstrates that several
frontier candidates are established workflows:

- Solar Fire documents [rectification and life-event
  comparison](https://astrologysoftware.co.uk/solar-fire/rectification/).
- Solar Fire documents [classical horary search
  criteria](https://astrologysoftware.co.uk/solar-fire/solar-fire-extra-functions/).
- TimePassages documents [transits to composite
  charts](https://www.astrograph.com/downloads/Manual6.pdf).
- Solar Maps documents [time-dependent mapping and
  cyclocartography](https://astrologysoftware.co.uk/solars-maps/).
- Solar Fire documents [return, progression, direction, and dynamic-hit
  workflows](https://astrologysoftware.co.uk/solar-fire/solar-fire-forecasting/).

These sources establish contemporary workflow relevance only. They do not own
Moira's doctrine, formulas, source policy, or validation standard. The admitted
Track A contracts cover only the exact composite/Davison transit, fixed-star
astrocartography, relocated-return, and explicit-epoch transiting
astrocartography calculations described above; practitioner software breadth
does not imply parity for progressed, directed, interpretive, or ranking
workflows.

---

## 9. Recommended ordering

### Track A — bounded closure work

**Status:** Admitted at `7090255e2d6cc41f7b4df15417512412f0ad5366`.

1. Exact predictive composite/Davison targets — admitted.
2. Fixed-star astrocartography parity — admitted.
3. Relocated-return and explicit-epoch transiting-locational composition —
   admitted.

Track A remains calculation-only. It does not admit progressed or directed
relationship charts, cross-chart multi-body patterns, progressed or directed
cartography, chart-backed comet MC/IC/ASC/DSC lines, interpretation, rankings,
website work, or Workspace adoption. Those boundaries require a separately
authorized and independently validated follow-on.

### Track B — flagship new Western research

1. Horary source and ambiguity dossier — admitted.
2. Horary significator/perfection evidence contract — admitted.
3. Mundane source and chart-selection dossier — admitted.
4. Neutral mundane event-chart profile — admitted.

Horary and mundane must not share a generic judgement layer merely because
they reuse houses and aspects. The Track B checkpoint preserves that boundary
through separate modules, policies, receipts, facade methods, serializers, and
REST routes.

### Track C — predictive research instruments

1. Birth-time rectification evidence model.
2. Candidate-time sensitivity and event matrix.
3. Western annual-revolution source dossier.
4. Named revolution component profile.

### Track D — strategic greenfield research

1. KP source and lineage feasibility.
2. Chinese 28-Xiu identity/geometry feasibility.
3. Reassessment of the explicit Jyotish deferrals.
4. Historical astrological-magic product-boundary review.

No unfinished track should be expanded into implementation phases until its
research gate has a finite proposed contract and a credible independent
validation method.

---

## 10. Admission checklist for any selected frontier

A candidate becomes implementation-ready only when all applicable boxes can be
checked:

- [ ] The tradition, lineage, edition, and translation are identified.
- [ ] The proposed engine contract is computational rather than interpretive.
- [ ] Existing Moira substrate has been mapped to avoid duplicate truth.
- [ ] Required inputs, coordinate frames, clocks, locations, and calendars are
      explicit.
- [ ] Conflicting doctrine is represented as named policy or remains deferred.
- [ ] `not_evaluable`, `unresolved`, and `excluded` states are typed.
- [ ] Synthetic scores are absent or fully decomposable and policy-versioned.
- [ ] At least one independent source-owned worked example or oracle is
      available.
- [ ] Boundary, ambiguity, missing-input, and adversarial cases are defined.
- [ ] Root exports, facade, serializers, server models, and OpenAPI parity are
      planned only after atomic engine truth is stable.
- [ ] Website and Workspace adoption remain separately authorized downstream
      work.
- [ ] Release notes state both capability and exclusions without implying
      interpretation or prediction accuracy.

---

## 11. Recommended next decision

Do not begin another broad multi-phase implementation from this document.
After Track B receives a separately authorized durable commit/release decision,
choose one of the following explicit objectives:

- **highest-value research instrument:** rectification evidence matrix;
- **largest remaining Western doctrine gap:** source-locked Western annual
  revolutions distinct from generic returns and Jyotish Varshaphal;
- **bounded advanced-forecasting follow-on:** one separately scoped progressed,
  directed, cross-chart-pattern, or chart-backed comet-line contract;
- **bounded Horary or Mundane follow-on:** one independently sourced evidence
  policy without judgement, prediction, or automatic subject inference;
- **largest greenfield tradition:** Chinese 28-Xiu feasibility before any full
  Chinese astrology programme.

The selected objective should receive its own bounded research dossier and stop
condition. This audit remains a map, not permission to implement every row.

---

## 12. Closure ledger

| Area | Admission receipt | Admitted scope | Still outside the contract |
|---|---|---|---|
| Track A relationship forecasting | `7090255e2d6cc41f7b4df15417512412f0ad5366` | Exact transits to immutable composite and Davison planet, node, angle, and cusp targets | Progressed/directed relationship charts, orb windows, cross-chart multi-body patterns, interpretation |
| Track A locational forecasting | `7090255e2d6cc41f7b4df15417512412f0ad5366` | Fixed-star lines and points, relocated returns, and explicit-epoch transiting astrocartography | Progressed/directed locational modes, chart-backed comet MC/IC/ASC/DSC lines, interpolation, rankings, interpretation |
| Track B Horary evidence | Admission commit containing this amendment on `codex/track-b-western-research-20260811` | Lilly 1647 question/house/significator/hour/consideration/sect/perfection evidence; curated Python parity; one strict REST route | Topic inference, answer/outcome/timing prose, scores, advice, cross-author judgement, professional advice |
| Track B neutral Mundane profile | Admission commit containing this amendment on `codex/track-b-western-research-20260811` | Cardinal ingress, preceding syzygy, named eclipse epoch, complete Jupiter-Saturn root, explicit-location local-chart evidence; curated Python parity; one strict REST route | Automatic capitals/subjects, country-sign doctrine, clustering, prediction, interpretation, scores, advice |

The admission receipt identifies the bounded engine contract. This ledger does
not claim a package publication, website or Workspace adoption, or deployment.

---

## 13. Maintenance rule

This is a point-in-time audit bound to the commit named at the top. When a gap
changes state:

1. verify engine, facade, registered server, tests, standards, and doctrine;
2. update the affected row and add the closing commit;
3. distinguish calculation closure from transport or website adoption;
4. preserve deliberate exclusions instead of relabeling them as unfinished;
5. regenerate a dated companion audit when several rows change materially.

Historical audit documents remain useful provenance, but the newest verified
current-state audit controls prioritization.
