# P13-U1 Western Electional Issues 01-16 — Definitive Implementation Plan

**Status:** active implementation; Phases 1 and 3-6 are complete at their
named source boundaries, Phase 2A is complete, and Phase 2B geometry remains
explicitly doctrine-source-gated
**Scope:** the first sixteen unresolved Western electional issues identified
after the P1-P3 work  
**Public-surface rule:** an issue is not closed until its admitted product is
available through the engine, curated root exports, `Moira` facade, FastAPI
request/response models, a registered REST route, OpenAPI, and tests  
**Compatibility posture:** there are no known downstream consumers of these
electional contracts. We may correct or replace provisional electional
contracts instead of carrying compatibility shims, but every admitted doctrine
profile remains explicitly versioned.

## 1. Objective

Resolve the following issues without inventing historical doctrine, hiding
computational policy, or collapsing distinct sources into one generic
"traditional" system:

1. Dorotheus V.9 lunar separation-and-connection flow.
2. Dorotheus V.6 southern descent.
3. Dorotheus V.6 solar disengagement.
4. Dorotheus V.7 northward ecliptic crossing.
5. Dorotheus V.31 "made unfortunate" testimony.
6. Dorotheus V.6.29 supplementary inception/outcome indicators.
7. Sahl burnt-path endpoints.
8. Sahl fourth-house matter profiles.
9. Ramesey remedy fulfillment.
10. Ptolemaic bounds data.
11. General signed applying/separating analysis.
12. Perfection doctrines: direct perfection, translation, collection,
    prohibition, refranation, and source-required related forms.
13. Remaining matter profiles.
14. Complete electional judgement.
15. Transparent scoring/ranking and any separately admitted advice product.
16. Broader electional scanning.

The plan deliberately distinguishes four layers:

- **astronomical/geometry witness:** measurable sky state and event sequence;
- **source-owned doctrine:** a named author's interpretation of that witness;
- **judgement assembly:** an explicit composition of admitted doctrine
  products;
- **transport:** faithful REST serialization of the same engine result.

Transport code must not invent doctrine, and a library-only implementation is
not considered public or complete.

## 2. Confirmed Starting Truth

### 2.1 Reuse rather than rebuild

- `moira/aspects.py` already computes signed applying/separating state from the
  shortest directed arc and body speeds. Issue 11 is therefore an integration,
  authority-validation, and public-witness task—not a new aspect engine.
- `moira/void_of_course.py` already finds the next sign-bounded exact lunar
  connection. It does not yet expose the complete prior-separation/next-
  connection flow required by Dorotheus V.9.
- `moira/dignities.py`, `moira/lots.py`, and `moira/planetary_hours.py` already
  provide much of the measurable substrate needed by issues 5, 6, 9, and 12.
- The current Western electional scanner is a bounded discrete sampler for
  three Moon-condition profiles. It explicitly does not establish exact
  transition times or scan the later doctrine products.

### 2.2 Bounds correctness dependency — resolved 2026-07-15

`moira/egyptian_bounds.py::PTOLEMAIC_BOUNDS` formerly duplicated
`EGYPTIAN_BOUNDS`, and the former singular Chaldaean table concealed a
source-required sect distinction. Issue 10 corrected the Ptolemaic table and
introduced explicit Chaldaean day/night variants. Later fortification,
reception, almuten, or scoring work may now consume those named doctrines.

### 2.3 Documentation drift to correct before admission

The doctrine packet and research dossier contain superseded statements about
resolved lunar-number semantics and about the absence of acquisition gaps.
The existing Dorotheus and Sahl inventories are complete as inventories, but
several computational ambiguities still need primary parallels or an explicit
policy decision. Before implementation, the packet must distinguish:

- source inventory complete;
- computational semantics resolved;
- engine implementation admitted;
- public REST product admitted.

## 3. Architecture Rules for All Sixteen Issues

1. **Version doctrine, not astronomy.** Geometry vessels receive stable
   physical names. Source interpretations receive identifiers such as
   `dorotheus_v5_9_flow_v1` or `sahl_building_v1`.
2. **Preserve indeterminacy.** If a source does not settle a threshold,
   interval, ruler choice, or reception rule, return a typed indeterminate
   state or require the caller to select a named policy. Never silently choose
   a popular modern convention.
3. **Separate evidence from verdict.** Every doctrine clause records its input
   witness, source citation, selected policy, state, and any unresolved
   requirement.
4. **No universal traditional score.** A numeric ranking is a Moira-owned
   decision model unless a specific historical author supplies the complete
   aggregation rule. It must be labeled accordingly.
5. **No route-only computation.** FastAPI models validate and serialize;
   engine functions and the facade own computation.
6. **Public means the full ladder.** Every admitted product ships in one batch
   through module API → `moira/__init__.py` → `Moira` facade → server service →
   Pydantic models → router → OpenAPI/tests.
7. **No exact-window claim from samples.** Exact transitions require event
   bracketing and refinement around every truth-changing boundary.
8. **Source citations are data.** Profile metadata carries edition, work,
   book/chapter/section, printed page where available, and the interpretation
   decision derived from it.

## 4. Dependency Graph and Required Order

```text
Phase 0  Governance and source freeze
   |
   +--> Phase 1  Ptolemaic bounds correction (#10)
   |
   +--> Phase 2  Directed aspect and lunar-flow substrate (#11, #1)
   |        |
   |        +--> Phase 6  Perfection doctrines (#12)
   |
   +--> Phase 3  Lunar crossing/disengagement/burnt-path policy (#2, #3, #4, #7)
   |
   +--> Phase 4  Fortification, supplementary indicators, remedies (#5, #6, #9)
   |
   +--> Phase 5  Sahl fourth-house profiles (#8)
   |
   +--> Phase 7  Remaining matter profiles (#13)
                |
                +--> Phase 8  Complete judgement (#14)
                         |
                         +--> Phase 9  Ranking/advice decision (#15)
                         |
                         +--> Phase 10 Event-aware broader scanning (#16)
```

Phases 1-5 may be developed in separate commits once their source gates are
closed. Phases 6-10 depend on the shared substrate and must not be pulled
forward merely because a transport shape is easy to create.

## 5. Phase-by-Phase Implementation Plan

### Phase 0 — Governance and source freeze

**Purpose:** prevent another implementation from being built on a stale or
ambiguous doctrine statement.

**Work**

1. Update the doctrine packet and dossier so their issue states agree with
   executable truth.
2. Add a resolution ledger row for every issue with:
   - governing computational object;
   - primary passage and edition;
   - ambiguity question;
   - adopted policy or `source_pending`;
   - engine/profile identifier;
   - public route;
   - validation evidence.
3. For every newly acquired source, capture the title page, edition metadata,
   relevant page image, a short transcription, and enough surrounding text to
   avoid extracting a rule from context.
4. Freeze public naming before code. Because there are no consumers, replace
   awkward provisional names now rather than preserving them indefinitely.

**Likely files**

- `docs/architecture/P13-U1_WESTERN_ELECTIONAL_DOCTRINE_PACKET.md`
- `docs/architecture/P13-U1_WESTERN_ELECTIONAL_DOCTRINE_RESEARCH_DOSSIER.md`
- the Dorotheus and Sahl rule inventories
- a new validation/source-decision ledger under `wiki/03_validation/`

**Exit gate:** all sixteen issues have either a cited computational policy or
an explicit acquisition blocker. A secondary blog or another astrology engine
cannot close a primary-doctrine ambiguity.

---

### Phase 1 — Correct Ptolemaic bounds (#10) — COMPLETE 2026-07-15

**Governing object:** a complete zodiacal partition into five contiguous term
segments per sign under the named Ptolemaic scheme.

**Implementation**

1. Reconstruct the table from Ptolemy's stated arrangement and the relevant
   Hephaistion textual/table witness. Record textual variants rather than
   averaging or guessing between them.
2. If the authorities preserve more than one lawful reconstruction, expose a
   doctrine enum and separate immutable tables. Do not call either table simply
   "Ptolemaic" without variant metadata.
3. Validate each sign for exact `[0, 30)` coverage, five positive-width
   segments, no overlap/gap, lawful ruler identity, and deterministic boundary
   ownership.
4. Add an adversarial test proving that the Ptolemaic table is not identical
   to the Egyptian table.
5. Audit every consumer of term data. Consumers explicitly requesting
   Egyptian terms remain unchanged; consumers exposing a doctrine selector
   must receive the corrected variant.
6. Promote table/variant metadata through the existing public bounds API and
   REST response wherever the doctrine is selectable.

**Likely code/tests**

- `moira/egyptian_bounds.py` (or rename/split to a neutral bounds module if the
  public correction warrants it)
- `tests/unit/test_egyptian_bounds.py`
- `tests/unit/test_egyptian_bounds_public_api.py`
- affected dignity/longevity/server tests

**Closure:** all 60 Ptolemaic segments are source-traceable; the transmitted
planetary totals are tested; Chaldaean day/night variants replace the former
unsupported singular table; boundary, module, REST, and OpenAPI tests identify
the actual variant and source citation. Egyptian consumers remain unchanged.

---

### Phase 2 — Directed aspects and Dorotheus lunar flow (#11, #1)

#### 2A. General signed applying/separating witness (#11) — COMPLETE 2026-07-15

1. Preserve the existing signed shortest-arc algorithm in `moira/aspects.py`.
2. Define a first-class immutable witness containing bodies, aspect, current
   directed error, relative speed, applying/separating/exact/indeterminate
   state, orb policy, and frame/timescale provenance.
3. Explicitly define singularities:
   - exact at tolerance;
   - zero or unavailable relative speed;
   - stations within the evaluated interval;
   - wrap at 0/360 degrees;
   - multiple possible aspect branches.
4. Add invariant tests for longitude wrap, reversed body ordering, exactness,
   stations, and a numerical check immediately before/after perfection.
5. Promote the witness through root, facade, and a dedicated REST endpoint or
   as a typed component of the existing aspect route. The OpenAPI schema must
   expose motion semantics rather than flattening them to a boolean.

**Closure:** `AspectMotionWitness` preserves the selected signed aspect branch,
directed separation and error, relative speed, orb rate, exact/rate tolerances,
canonical scaled-orb policy, body-specific station thresholds, visible station
reasons, caller-declared frame/timescale, and an explicit instantaneous-only
scope. `aspect_motion_witness(...)`, `Moira.aspect_motion_witness(...)`, and
`POST /v1/aspects/motion-witness` expose the same object. Exactness, missing or
partial speeds, body stations, relative standstill, 0/360 wrap, positive and
negative branches, and the equidistant non-conjunction branch singularity are
covered by engine, facade, REST, OpenAPI, and public-surface tests.

#### 2B. Dorotheus V.9 lunar flow (#1) — GEOMETRY COMPLETE, DOCTRINE SOURCE-GATED 2026-07-15

1. Add a neutral `MoonConnectionFlow` vessel rather than embedding the search
   inside a leasing rule. It should contain:
   - previous exact lunar separation;
   - current motion state relative to that body/aspect;
   - next exact lunar connection;
   - exact event times and signed distances;
   - search/window policy and sign-ingress/egress bounds;
   - any station or no-event reason.
2. Reuse the current exact-perfection search from `void_of_course.py`, but do
   not expose its private helpers as the new architecture. Extract shared
   event-search logic into a neutral module if necessary.
3. Do not assume that the *previous* separation is sign-bounded. Resolve from
   Dorotheus/Theophilus/Hephaistion whether the root testimony means the most
   recent perfection, the last perfection since sign ingress, or another
   interval. Make this a named policy if the textual tradition contains more
   than one reading.
4. Define stake mapping independently: previous body/aspect describes the
   root; next body/aspect describes the outcome. Do not infer fortune/infortune
   merely from an aspect name.
5. Replace the V.9 `NOT_EVALUABLE` clause only after both event window and
   stake mapping are source-owned.
6. Expose the generic flow witness publicly and include it in the Dorotheus
   leasing REST response.

**Likely code/tests**

- `moira/aspects.py`
- `moira/void_of_course.py`
- a new neutral module such as `moira/aspect_events.py`
- `moira/_western_electional_matter.py`
- root/facade and `moira_server/models|routers|services`
- aspect-event, leasing-profile, facade, REST, and OpenAPI tests

**Exit gate:** a fixed epoch can be traced from longitudes/speeds to previous
and next exact events, then to the Dorothean clause; tests prove the selected
window policy and REST preserves every witness field.

**Closure and remaining source gate:** `MoonConnectionFlow` now preserves the
caller-selected prior-event window (`current_sign` or bounded
`fixed_lookback`), exact previous and next directional perfections, signed
query and exact residuals, current motion state, sign bounds, considered body
set, and explicit no-event reasons. It is public through
`moon_connection_flow_at(...)`, `Moira.moon_connection_flow_at(...)`, and
`POST /v1/aspects/moon-connection-flow`. A V.9 leasing request must supply the
previous-window policy, and its REST response embeds the complete flow.

The source audit confirmed that *Carmen* V.9.8 requires both what the Moon
flows away from and what it connects to. V.6.27-31 supplies the general
root/outcome sequence, while V.10 and V.29 demonstrate that matter-specific
chapters can assign separation and connection differently. The surviving V.9
text does not assign the two events to its four leasing stakes. Therefore the
geometry is complete but `moon_separation_and_connection_flow` lawfully
remains `NOT_EVALUABLE`; replacing that state still requires the fuller
Theophilus/Hephaistion parallel identified in the source-acquisition list.

---

### Phase 3 — Lunar direction, solar disengagement, and burnt path (#2, #3, #4, #7) — COMPLETE AT SOURCE BOUNDARY 2026-07-15

These issues share lunar geometry but do not necessarily share doctrine.

#### 3A. Southern descent and northward ecliptic crossing (#2, #4)

1. Define a source-neutral `LunarEclipticDirectionWitness` from geocentric
   ecliptic latitude, latitude rate, nearest node crossing, and exact crossing
   time.
2. Distinguish three possible source objects before coding:
   - being north/south of the ecliptic;
   - moving northward/southward;
   - having just crossed or being about to cross within a defined interval.
3. Prefer exact sign-change/event semantics over an invented degree tolerance.
   If the source requires a region around the crossing, expose its interval as
   named policy data.
4. Make the V.6 and V.7 clauses consume the neutral witness under separate
   Dorothean policies; do not use one rule's interpretation to fill the other.

#### 3B. Solar disengagement (#3)

1. Determine whether the passage governs longitudinal separation from
   conjunction, emergence from beams, latitude separation, or a compound
   condition.
2. Reuse existing solar elongation/combustion witnesses if the source selects
   longitudinal visibility zones. Add a new geometry vessel only if latitude
   is independently material.
3. If the primary line remains underdetermined, retain `NOT_EVALUABLE` in the
   canonical profile and allow only explicitly named research variants. Do not
   convert a conjecture into `dorotheus_moon_condition_v1`.

#### 3C. Sahl burnt-path endpoints (#7)

1. Search the fuller Sahl tradition and translator notes for explicit
   endpoints or a referenced inherited table.
2. If Sahl truly supplies no endpoints, remove
   `UNRESOLVED_SOURCE_WORDING` as a computational default. Require callers to
   select a named historical/glossary variant, while a source-faithful Sahl
   profile reports the clause as indeterminate.
3. Each variant must carry inclusive/exclusive boundary law and a citation.
4. Add exact endpoint and 0/360 wrap tests.

**Likely code/tests**

- a new lunar-direction witness module or a narrowly shared helper
- `moira/_western_electional_dorotheus.py`
- `moira/_western_electional_construction.py`
- `moira/western_electional.py`
- existing unit, facade, REST, and OpenAPI suites

**Exit gate:** every clause says precisely which measurable object it tests;
all thresholds/intervals are cited or caller-selected; unresolved textual
meaning remains visibly unresolved.

**Implementation result:** `LunarEclipticDirectionWitness` now exposes the
Moon's apparent geocentric ecliptic latitude and latitude rate, independent
north/south position and motion classifications, adjacent exact sign-changing
node crossings, crossing direction, exact UT1 event times, and the nearest
crossing relation. It is public through the package root,
`Moira.lunar_ecliptic_direction_at(...)`, and
`POST /v1/electional/western/lunar-ecliptic-direction`. The numerical root
tolerances are algorithm policy, explicitly not a doctrinal node orb.

Dorotheus V.6 and V.7 consume that neutral witness under distinct clause
policies. The V.6 solar-disengagement clause additionally exposes canonical
instantaneous Sun-Moon conjunction motion and the independent lunar-latitude
witness. Dorotheus and the Hephaistion III.7 parallel establish latitude
direction but supply no before/after crossing interval; V.6 likewise supplies
no rule for combining longitudinal and latitudinal disengagement. These clauses
therefore remain `NOT_EVALUABLE` with materially complete geometry.

Sahl section 22d still supplies only “the end of Libra and the beginning of
Scorpio.” The public moment and scan requests now require an explicit
`SahlBurntPathVariant`: source-faithful indeterminacy, Dykes's glossary/fall
degrees `[199, 213)`, or the later fifteen-degree convention `[195, 225)`.
Every computational variant records its citation and half-open boundary law;
there is no ambient computational default at the public call boundary.

---

### Phase 4 — Fortification, supplementary indicators, and Ramesey remedy (#5, #6, #9)

**Status (2026-07-15): complete at the primary-source boundary.** The primary
pages required one correction to the original plan: V.6.29 does not define a
set of interchangeable outcome rulers. V.6.22 keeps the Moon-sign lord as the
primary outcome indicator; V.6.29 adds the editorial ninth-part lord and Lot
of Fortune's lord for inception, and the Moon's next connection for outcome.
Moira therefore exposes distinct supplementary witnesses rather than a ruler
selector.

#### 4A. Dorotheus V.31 "made unfortunate" (#5)

Implemented as four source-ordered testimonies on each matter significator:
under the rays, “made unfortunate,” not looking at the Ascendant, and bad
place. The first, third, and fourth are evaluated under the existing explicit
V.31 policy. “Made unfortunate” remains a named `not_evaluable` source gate:
the primary passage and edition glossary do not close it to an exclusive list.
Observed whole-sign Mars/Saturn configurations remain evidence only. The
combination law is visible: any triggered testimony establishes an impediment;
otherwise an unresolved testimony makes the result indeterminate. No generic
dignity score is used.

#### 4B. Supplementary inception and outcome indicators (#6)

Implemented as three side-by-side `DorotheusSupplementaryIndicator`
witnesses with fixed roles and no fallback:

1. `editorial_ninth_part_lord` — `not_evaluable`; edition note 31 identifies
   a Persian editorial insertion but gives no division, boundary, or ruler
   scheme, so Moira does not assume modern navamsa doctrine;
2. `lot_of_fortune_lord` — evaluated through Moira's current sect-aware Lots
   engine and labelled `inception_supplement`;
3. `next_moon_connection` — the existing first exact traditional aspect
   before sign exit, labelled `outcome_supplement`.

The Moon-sign lord remains the primary V.6.22 outcome indicator.

#### 4C. Ramesey remedy fulfillment (#9)

Implemented as five typed clauses: the combined Moon cadence/no-Ascendant-
relation condition; Jupiter/Venus in the first or whole-sign sextile/trine to
the Ascendant; Ascendant-cusp fortification; Ascendant-lord fortification; and
hour-lord fortification. The high-level path resolves the planetary-hour lord.
The last three clauses remain individually `indeterminate` because pp. 127-128
command fortification but do not provide a closed predicate. They are not
replaced with a generic dignity total. Aggregate fulfillment is
`fulfilled`, `not_fulfilled`, or `indeterminate`; urgent applicability remains
separate, and neither can erase a triggered Moon impediment.

**Likely code/tests**

- `moira/_western_electional_context.py`
- `moira/western_electional.py`
- possibly a new shared `moira/classical_fortification.py`
- root/facade/server model, service, router, serialization, and OpenAPI tests

**Exit gate: passed.** Every formerly free-text requirement is now a typed
evaluated clause or named unresolved source gate, engine/root/facade and REST
expose the same evidence, and no point score stands in for a source rule.

---

### Phase 5 — Sahl fourth-house matter profiles (#8) — COMPLETE AT SOURCE BOUNDARY 2026-07-15

Do not create one broad "fourth-house election." Admit separate profiles in
source order:

1. `sahl_building_v1` (§§43-46)
2. `sahl_demolition_v1` (§47)
3. `sahl_land_v1` (§§48-49)
4. `sahl_wells_and_rivers_v1` (§50)
5. `sahl_planting_v1` (§§51-53)
6. `sahl_sowing_v1` (§§54-55)

**Implementation**

1. Build a clause matrix for Moon, Ascendant, significator lords, Fortune,
   Mercury, benefics/malefics, house placement, motion, light/number, and
   aspects.
2. Resolve source terms before admission: increasing/defective in number,
   eastern/ascending, ascending in apogee circle, separation/cleansing, and
   stakes.
3. Reuse shared geometry and fortification witnesses; keep profile-specific
   combination law in Sahl doctrine code.
4. Every result preserves source order, clause evidence, triggered clauses,
   and not-evaluable clauses. No aggregate score.
5. Expose a typed matter-profile selector through engine, root, facade, and
   `POST /v1/electional/western/sahl-matter-profile`.

**Exit gate:** all six profiles have fixed source citations, per-clause tests,
cross-profile discrimination tests, REST round trips, and OpenAPI enums that
name every admitted profile.

**Implementation result:** all six profiles are admitted as distinct,
source-ordered objects through `evaluate_sahl_matter_profile(...)`,
`sahl_matter_profile_at(...)`, `Moira.sahl_matter_profile_at(...)`, and
`POST /v1/electional/western/sahl-matter-profile`. Each result embeds the
general section 22 Moon-condition layer and preserves its own full clause set,
triggered gates, unresolved clauses, authority, policy, and measurements.

Closed source objects compute directly: sign quadruplicities/elements,
whole-sign configurations, Sahl moiety joins, explicit houses, Lot of Fortune,
Egyptian bounds, Dorothean triplicity, lunar light increase, and named
malefic/benefic placements. The held edition does not close "in number,"
eastern/ascending, circle motion, cleansing, several separation windows, or
the generic command to adapt a significator. Those phrases are not guessed:
they are typed `not_evaluable` clauses carrying the relevant observed
alternatives and Dykes's notes. A false explicit conjunct can still clear a
compound gate; an unresolved conjunct can never fabricate a trigger.

The public profile enum names exactly `sahl_building_v1`,
`sahl_demolition_v1`, `sahl_land_v1`, `sahl_wells_and_rivers_v1`,
`sahl_planting_v1`, and `sahl_sowing_v1`. No aggregate score, advice,
recommendation, generic fourth-house profile, or complete-election claim is
provided.

---

### Phase 6 — Classical perfection doctrines (#12) — LILLY V1 COMPLETE 2026-07-15

**Status:** complete for the named `lilly_1647_perfection_v1` profile. The
full 1647 Lilly facsimile supplied as Wellcome scan `b30338724` closes direct
perfection, translation, collection, prohibition, refranation, and
frustration at printed pp. 110-113 and 125-126. Sahl, Bonatti, abscission, and
reflection remain separate unadmitted profiles or forms; none is blended into
the Lilly result.

**Governing object:** a time-ordered sequence of aspectual attempts and exact
events among named significators, with reception and station/sign changes
evaluated under a named authorial policy.

**Implementation**

1. Create a neutral event sequence engine, likely in
   `moira/classical_perfection.py`, that can find the next relevant exact
   aspect, station, sign ingress, and competing perfection for each actor.
2. Admit doctrine objects separately:
   - direct perfection;
   - translation of light;
   - collection of light;
   - prohibition;
   - refranation;
   - frustration, abscission, or reflection only if the chosen primary profile
     defines them sufficiently.
3. Define before code:
   - which planets are significators and which may translate/collect;
   - zodiacal versus mundane aspect scope;
   - orb/contact and exactness law;
   - speed/order requirements;
   - whether sign ingress or station breaks an application;
   - reception types and whether domicile/exaltation alone or triplicity/term
     also count;
   - precedence when multiple events compete.
4. Return the complete event trace. A label such as `prohibited` without the
   intervening planet, aspect, and event times is insufficient.
5. Add source-specific policy identifiers rather than one universal
   `traditional` mode (for example, Sahl and Lilly profiles if both are
   admitted).
6. Expose a standalone public analysis route before using perfection inside a
   complete electional judgement.

**Implemented public product**

- neutral, time-ordered exact-aspect, station, and sign-ingress trace in
  `moira/classical_perfection.py`;
- source-owned six-witness Lilly classifier using the canonical Lilly 1647
  moiety table and explicit reception policy;
- package-root and `moira.western_electional` exports;
- `Moira.lilly_perfection_at(...)` with bound kernel reader;
- `POST /v1/electional/western/classical-perfection` with a typed 31-day
  maximum interval and seven traditional-planet enum;
- no score, advice, recommendation, generic traditional mode, or complete
  electional judgement.

**Tests**

- synthetic ephemeris/event cases isolating every doctrine;
- exact ties, stations, sign ingresses, wrap, and no-perfection cases;
- DE441 regression cases with recorded provenance;
- root/facade/REST/OpenAPI parity.

**Exit gate:** each classification is reproducible from the returned event
trace and selected source policy; secondary-engine agreement is corroboration
only, not the governing proof.

---

### Phase 7 — Remaining matter profiles (#13)

Admit profiles in dependency and source-completeness order:

1. commerce, buying, and selling;
2. journeys, sea travel, and ships;
3. marriage and partnership;
4. debt, lawsuits, and wills;
5. medical and surgical elections after a source-specific melothesia table is
   acquired and separately provenance-validated;
6. any historically sensitive or partially horary chapters only after an
   explicit product decision establishes that they are genuinely electional.

**For every profile**

1. Define the matter, source range, significators, required chart/natal input,
   general rules inherited, matter-specific clauses, ambiguity policy, and
   exclusions.
2. Do not fold Dorotheus and Sahl into a single profile. A comparison product
   may contain both independent evaluations later.
3. Implement one vertical slice at a time through engine, root, facade, REST,
   OpenAPI, fixtures, and docs.
4. Use a registry only for selection/dispatch. The registry must not erase
   distinct result types or source-specific input requirements.
5. Exclude horary diagnosis, medical treatment claims, or other products not
   authorized by the electional scope.

**Exit gate:** each inventory row is marked admitted, explicitly deferred, or
excluded with a reason. "Remaining profiles complete" never means every
historical chapter was forced into software.

---

### Phase 8 — Complete electional judgement (#14)

**Governing object:** an inspectable composition of previously admitted
doctrine results for one proposed moment and one declared matter—not a new
black-box algorithm.

**Proposed result structure**

- request/chart and kernel provenance;
- doctrine profile and matter profile;
- general Moon condition;
- rooted context and root/outcome witness;
- matter-specific evaluation;
- perfection path;
- natal/radical context when supplied and required;
- fortification and remedy witnesses;
- explicit unresolved/excluded requirements;
- overall assembly state such as `complete_under_profile`, `impeded`,
  `indeterminate`, or `insufficient_input`.

**Implementation**

1. Define `WesternElectionalJudgementPolicy` with immutable, serialized
   component choices and combination/precedence law.
2. Require a matter profile; do not offer a source-less "best time for
   anything" judgement.
3. Propagate indeterminacy. A missing required natal chart, unresolved source
   clause, or unavailable event witness cannot become a favorable result.
4. Preserve every component result in the response. The overall state is a
   summary index, not a replacement for evidence.
5. Add `Moira.western_electional_judgement_at(...)` and a dedicated REST route.

**Exit gate:** a caller can reconstruct the overall state solely from returned
components and the serialized combination policy; no hidden weights or
transport-only rules exist.

---

### Phase 9 — Ranking, scoring, and advice decision (#15)

This issue is resolved by admitting only semantics Moira can honestly own.

#### 9A. Ranking/scoring

1. Create a separate `ElectionalRankingPolicy`; never add a `score` field to a
   historical source result as though the author supplied it.
2. Support either caller-supplied weights or immutable named Moira profiles.
   Return every contribution, normalization, exclusion, tie-break, and final
   value.
3. Rank only moments evaluated under the same doctrine, matter, input, and
   ranking policy.
4. An indeterminate required doctrine clause is not zero and cannot be hidden
   by positive points. Ranking policies must reject or separately partition
   incomplete candidates.
5. Document the result as decision support, not empirical proof of astrological
   efficacy.

#### 9B. Advice/recommendation

1. Keep advice outside the engine unless a concrete product is authorized.
2. If admitted later, it must be a deterministic rendering of the complete
   judgement and ranking evidence, not an LLM-generated or mystical assertion.
3. "No advice product admitted" is an acceptable closure decision; it should
   be explicit in docs and API rather than remaining an implied TODO.

**Exit gate:** ranking is transparent and policy-owned; historical doctrine
results remain non-scored; the project records an explicit admit/defer decision
for advice.

---

### Phase 10 — Event-aware broader scanning (#16)

**Purpose:** scan complete profiles and judgements without misrepresenting a
uniform sample grid as exact continuous truth.

**Implementation**

1. First add adapters for rooted context, construction, Sahl matter profiles,
   Dorotheus matter profiles, perfection, and complete judgement.
2. Preserve the current bounded discrete scanner as an explicit fallback and
   comparison mode.
3. Add an event-aware mode that partitions the interval at every boundary that
   can change the selected doctrine:
   - sign and house ingress;
   - aspect perfection and orb entry/exit when doctrinally relevant;
   - Moon node/ecliptic crossing;
   - stations and direction changes;
   - sunrise and planetary-hour boundaries;
   - bound/face/dignity boundaries;
   - source-defined threshold crossings.
4. Refine brackets with a stated time tolerance and return the cause of each
   transition.
5. Exact windows may be claimed only when the chosen profile declares a
   complete boundary inventory. Otherwise label output `sampled` or
   `partially_event_refined`.
6. Enforce span, event-count, refinement-iteration, and response-size bounds in
   both engine and REST validation.
7. Add a public judgement-window route and keep ranking as an optional separate
   request policy.

**Tests**

- synthetic single-boundary and coincident-boundary cases;
- coarse/fine sampling agreement away from transitions;
- transition-time tolerance checks;
- deterministic merge/tie behavior;
- resource-limit rejection;
- facade, REST, and OpenAPI parity.

**Exit gate:** every returned window states whether it is sampled or exact,
which events define its boundaries, which doctrine was evaluated, and whether
any unresolved clause remains.

## 6. Issue Closure Matrix

| # | Issue | Depends on | Closure evidence |
|---:|---|---|---|
| 1 | Dorotheus V.9 lunar flow | 11 + source window/stake policy | prior/next exact-event trace; leasing clause and REST round trip |
| 2 | V.6 southern descent | lunar-direction witness + parallel | exact measurable object; boundary cases; V.6 profile no longer conjectural |
| 3 | V.6 solar disengagement | primary interpretation | explicit longitude/latitude/visibility policy and tests |
| 4 | V.7 northward crossing | lunar-direction witness + parallel | exact crossing policy; construction result and REST |
| 5 | V.31 made unfortunate | source-owned fortification policy | clause-level testimony; no generic-score substitution |
| 6 | V.6.29 supplementary indicators | distinct ninth-part/Fortune/connection roles | primary Moon-sign lord preserved; no selector or fallback |
| 7 | Sahl burnt path | source endpoints or explicit variant requirement | cited endpoints and edge tests, or canonical indeterminacy preserved |
| 8 | Sahl fourth-house profiles | **COMPLETE AT SOURCE BOUNDARY 2026-07-15** | six separate public profiles with source-order witnesses and typed unresolved terms |
| 9 | Ramesey remedy | fortification + hour lord + aspects | tri-state fulfillment; remedy remains non-erasing |
| 10 | Ptolemaic bounds | **COMPLETE 2026-07-15** | source-traced 12×5 table; Chaldaean day/night split; public source metadata |
| 11 | signed application/separation | **COMPLETE 2026-07-15** | first-class instantaneous witness, invariants, facade/REST/OpenAPI |
| 12 | perfection doctrines | **LILLY V1 COMPLETE 2026-07-15** | six source-owned classifications, complete event trace, facade, REST, and OpenAPI; Sahl/Bonatti/reflection remain unadmitted |
| 13 | remaining matters | shared substrate + per-matter sources | each inventory row admitted/deferred/excluded explicitly |
| 14 | complete judgement | 1-13 as applicable | reconstructible component assembly; typed indeterminacy |
| 15 | ranking/advice | 14 | transparent Moira-owned ranker; explicit advice admission decision |
| 16 | broader scanning | 14, optional 15 | bounded event-aware windows with honest exactness labels |

## 7. Source Material to Acquire

The existing full Dorotheus Book V and Sahl *On Elections* holdings do not need
to be reacquired. The Bonatti `146 Considerations` PDF and translator's
introduction are **not** substitutes for the full *Book of Astronomy*.

### Acquire next — closes remaining source gates and future named variants

1. **ACQUIRED AND APPLIED 2026-07-15:** Ptolemy, *Tetrabiblos*, Book I,
   chapter 20/21, F. E. Robbins Loeb edition. The complete term discussion,
   tables, and stated planetary totals closed issue 10.
2. **Hephaistion of Thebes, *Apotelesmatics*, Book I term material and full
   Book III electional material**, in the Dykes/Gramaglia translation if
   available. The existing Book III sample is useful but not enough. Needed
   for issues 1-4; issue 10 is independently closed from Ptolemy.
3. **The full astrological works of Theophilus of Edessa**, especially the
   labor/election chapters cited as parallels to Dorotheus V.9. Needed for
   issue 1.
4. **William Ramesey, *Astrologia Restaurata*, full Books II and III**, as a
   locally searchable scan or transcription alongside the original facsimile.
   Needed for issue 9.
5. **Benjamin Dykes, *The Works of Sahl & Masha'allah*** (complete volume), for
   application/separation, reception, translation, collection, prohibition,
   and the wider Sahl terminology. Needed only before a distinct Sahl
   perfection profile is admitted; it does not block the completed Lilly v1
   profile.
6. **ACQUIRED AND APPLIED 2026-07-15:** William Lilly, *Christian Astrology*,
   Books I-II, Wellcome Collection 1647 facsimile `b30338724`. Printed
   pp. 110-113 and 125-126 govern the admitted Lilly v1 perfection profile.
   The scan is a private research input and is not embedded in the repository.
7. **Guido Bonatti, *Book of Astronomy* / *Liber Astronomiae*, complete
   Benjamin Dykes translation**, not the *146 Considerations* extract and not
   the translator's introduction. Needed for issue 12 and for any later
   Bonatti-owned judgement or weighting profile.

### Acquire to close remaining Phase 5 gates or when Phase 7 begins

8. The alternate Sahl translation and source parallels cited in the existing
   Sahl inventory notes for §§43-55. We should extract the exact bibliography
   from those notes before purchase; the purpose is to resolve "in number,"
   eastern/ascending, apogee-circle, cleansing, and stakes—not to accumulate
   redundant editions. Phase 5 is source-complete without this acquisition,
   but the affected clauses remain numerically `not_evaluable` until stronger
   source evidence closes them.
9. The primary source for each medical melothesia scheme before medical or
   surgical profiles are admitted. The existing inventory records multiple
   incompatible schemes; no generic body-sign table should be selected first
   and sourced afterward.

### What to deliver when a source is found

For each item, the most useful package is:

- the complete searchable PDF, not isolated screenshots;
- title/copyright/edition pages;
- printed page number and PDF page number for each target passage;
- any translator footnotes and referenced parallel passages;
- confirmation of whether project distribution rights permit excerpts or only
  private research use.

We should not embed copyrighted books or long extracts in the repository.
Repository evidence should contain bibliographic metadata, bounded quotations
where lawful, paraphrased computational decisions, and page-level citations.

## 8. Commit and Release Strategy

Use small vertical batches rather than one sixteen-issue branch:

1. governance/source ledger;
2. Ptolemaic bounds correction;
3. directed aspects and lunar flow;
4. lunar crossing/disengagement/burnt path;
5. fortification, ruler variants, Ramesey remedy;
6. Sahl fourth-house profiles;
7. perfection doctrines;
8. matter-profile families, one family per commit;
9. complete judgement;
10. ranking decision/product;
11. event-aware scanning.

Each batch must include engine, root, facade, REST, OpenAPI, tests, and minimum
truthful documentation before merge. Do not accumulate library-only work for a
later transport batch.

Because the electional surface currently has no consumers, profile IDs and
request/response shapes may be deliberately revised. Such changes must still
be recorded in the changelog/release notes and covered by schema tests.

## 9. Verification Gates

Every implementation batch begins with its smallest unit test and then expands
only to affected public surfaces. Use the project `.venv`, downloads disabled,
and strict known-issue expiry.

```powershell
$env:MOIRA_NO_DOWNLOAD = "1"
$env:MOIRA_TEST_MODE = "1"
$env:MOIRA_STRICT_KNOWN_ISSUES = "1"

# Representative targeted engine slices; add the new phase-specific files.
.\.venv\Scripts\python.exe -m pytest `
  tests\unit\test_western_electional.py `
  tests\unit\test_sahl_electional.py `
  tests\unit\test_dorotheus_electional.py `
  tests\unit\test_dorotheus_rooted_context.py `
  tests\unit\test_dorotheus_construction.py `
  tests\unit\test_dorotheus_matter_profiles.py `
  tests\unit\test_aspect_motion_witness.py `
  tests\unit\test_aspects.py `
  tests\unit\test_void_of_course.py -q

# Existing and new transport/OpenAPI slices.
.\.venv\Scripts\python.exe -m pytest `
  tests\server\test_server_western_electional_routes.py `
  tests\server\test_server_sahl_electional_routes.py `
  tests\server\test_server_dorotheus_electional_routes.py `
  tests\server\test_server_dorotheus_rooted_context_routes.py `
  tests\server\test_server_dorotheus_construction_routes.py `
  tests\server\test_server_dorotheus_matter_profile_routes.py `
  tests\server\test_server_aspect_motion_witness.py `
  tests\server\test_server_western_electional_profile_scan_routes.py -q

# Curated public-export governance and documentation consistency.
.\.venv\Scripts\python.exe -m pytest `
  tests\unit\test_api_surface_adversarial_audit.py `
  tests\unit\test_egyptian_bounds_public_api.py -q
.\.venv\Scripts\python.exe scripts\check_doc_consistency.py
```

For kernel-bound cases, first resolve the actual planetary kernel through
`moira/_kernel_paths.py` with downloads disabled. Numerical fixtures must name
kernel identity, epoch, frame, timescale, observer/origin, correction regime,
and tolerance. Synthetic event tests prove branch logic; DE441 cases provide
regression and invariant evidence; primary texts govern doctrine meaning.

## 10. Definition of Done for the Sixteen-Issue Program

The program is complete only when:

- all sixteen ledger rows are closed as implemented, explicitly deferred for
  named missing evidence, or intentionally excluded with a product reason;
- no default profile contains an undocumented conjectural threshold;
- the false Ptolemaic bounds table is corrected or removed from public use;
- aspect and perfection conclusions expose their event geometry;
- every admitted matter profile is source-specific and non-scored by default;
- complete judgement preserves component evidence and indeterminacy;
- any ranking is visibly Moira-owned and fully decomposable;
- scanning labels sampled, refined, and exact products honestly;
- every admitted feature reaches root exports, facade, REST, OpenAPI, and
  tests in the same batch;
- the doctrine packet, research dossier, validation ledger, changelog, and
  release notes describe the code that actually ships.

This definition allows a historically underdetermined rule to remain
indeterminate. Closure means Moira handles the uncertainty explicitly; it does
not mean inventing a number merely to eliminate every `NOT_EVALUABLE` state.
