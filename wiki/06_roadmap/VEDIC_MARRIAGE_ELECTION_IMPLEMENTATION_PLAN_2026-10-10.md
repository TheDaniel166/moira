# VED-011 marriage elections: implementation plan

**Status:** Implemented and locally accepted, 10 October 2026.
The user subsequently authorized execution. The
[source standard](../02_standards/MARRIAGE_ELECTION_STANDARD.md) and
[validation receipt](../03_validation/MARRIAGE_ELECTION_VALIDATION_2026-10-10.md)
record implementation and completed acceptance gates. Publication, release
and deployment require their separate authorization.
**Baseline:** engine `e7107267942d1926da9bcf8ba3d1299b4205ccf9`, generated wiki
`0c79a578942db2d46e11f203bc6a9c57e730ba27`, version 6.9.9, project Python
3.14.3. The existing research packet and register edits remain local.
**Governing evidence:** [marriage-election source research](VEDIC_MARRIAGE_ELECTION_SOURCE_RESEARCH_2026-10-10.md),
including twelve fingerprinted PDFs, source loci, the legacy guidance defect
and the rule/variant inventory. The [remaining-work register](VEDIC_REMAINING_WORK_REGISTER.md)
tracks this marriage scope as locally complete and other VED-011 purposes as open.

## 1. Deliverable and scope

Deliver **MC Avasthi ordinary marriage astronomical timing**, with a separately
requested personal/context assessment and a separately named Godhuli
composition. Engine, curated Python, facade and REST must expose the same
rules, decisions, coverage and evidence. This is a complete implementation
of the selected, published profile manifest, not a claim to implement every
marriage tradition or every subject in MC's Vivaha chapter.

The package includes correcting and deprecating the contradictory legacy
marriage guidance, all required missing calculations listed below, the
SS-derived Jupiter/Venus availability adapter, source-scoped remedies,
reader-derived instant assessments and bounded transition-derived intervals.
It must remain possible to inspect the ordinary assessment when a Godhuli
exception is selected.

Construction/Vastu, travel, business, compatibility matching/Tara Kuta,
natal predictions about married life, family ritual scheduling, preparatory
ceremonies, social/kinship eligibility, extraordinary non-ephemeris omens,
website and Urania are explicit exclusions. Historical age/social prescriptions
and harmful-outcome prose are not numerical eligibility outputs. A separate
whole-ceremony-duration search is also outside the first contract: the result
elects a declared ritual **anchor instant**, not every moment of a booking.

The eight packages below are implementation dependencies with one final
admission gate. They are not eight independently complete public products.
Every package carries its engine result vessels, strict transport mapping
and relevant HTTP tests. Do not defer REST correctness until after engine
completion or expose unfinished profiles as supported production choices.

## 2. Decisions fixed by this plan

| Decision | Selected behavior and attribution |
| --- | --- |
| Ordinary authority | MC, Ramlal Avasthi commentary, 2004 edition. Distinguish verse, commentary and Moira composition decisions in each rule receipt. |
| Calendar precedence | The marriage-specific Vivaha 13 prescription governs where it conflicts with the general Samskara 26 restriction. This is an explicit interpretive composition decision. Lunar qualifications remain required; a six-solar-sign filter is insufficient. |
| Other books | KP, VV, BS, PVR and the Raman transcription remain visible in a comparison ledger. Except the separately selected VV Godhuli geometry, they do not silently contribute vetoes or remedies to the ordinary MC profile. Complete alternative profiles require their own admission; research-only choices are rejected as executable selectors. |
| Sidereal and node basis | Default Lahiri and the existing dated Lagna owner's true-node basis. Any additionally exposed ayanamsa must be consistently supported by all selected components. Record the actual coordinate/frame/time definitions; no independently mixed component defaults. |
| Star membership | Ordinary 27-star identity and unequal Abhijit-inclusive 28-star identity are separate types/fields selected per rule. Exact half-open partition ownership; no equal twenty-eighth division and no global star-grid switch. |
| Planet nature | A source-locked named nature convention with explicit Moon and Mercury prerequisites. Identify differences from shared BPHS-based nature components before reuse. |
| Weekday | Traditional day rules use their sunrise-owned weekday. Existing Shadbala evidence retains its owner's UTC/JD weekday. Each clock is labelled; neither substitutes for the other. |
| Availability | Modern Moira astronomical positions in a separately named SS-derived time-degree adapter. Do not claim a literal historical SS ephemeris or modern physical visibility model. Derivation and astronomical validation are required in package D. |
| Waiting-period clock | Initial MC Samskara 27 buffers use fixed **elapsed UT1 days**, shifted on the same UT1 timeline as their event brackets. This is a Moira boundary convention, not a claim that the text specifies modern clock arithmetic. Sunrise-counted or urgent alternatives are not automatic fallbacks. |
| Combustion versus asta | Marriage availability and an existing Lagna remedy's named longitude-orb combustion condition remain distinct predicates. Preserve each actual criterion in evidence; identical numbers do not make them equivalent. |
| Navamsa | Reuse the admitted MC four-Navamsa default; retain its already named optional-Pisces variant when requested. Validate the combination in the marriage catalogue. |
| Remedies | Finite source-owned target lists; raw detection persists. Unknown prerequisites never authorize cancellation. Qualitative strength language does not become an invented generic Shadbala threshold. |
| Personal scope | Exactly two identified participants when requested, explicit traditional role assignments where needed, and per-field missing-data evidence. Omission is not a personal pass. Birth context and election context have separate epochs. |
| Ceremony target | Required nonempty ritual-anchor label, treated as descriptive metadata. Calculations evaluate the requested instant or possible instants within a range. The engine does not infer the ritual from religion, names or a booking title. |
| Result ownership | One engine assessment and one serializer mapping. Server models validate transport and call engine admission; server code does not reconstruct doctrine or change aggregate decisions. |

Some source details need a finite derivation worksheet before their formula
is admitted: broader MC tithi/Karana coverage, the selected regional vedha
branch, Latta's grid/origin counting, precise history clearance, quantitative
conditions in MC 79–91, and the SS apparent-place/ascensional computation.
Package A assigns each to an identified source locus, formula, worked case
and exit criterion. These tasks are part of implementing this plan; a required
rule cannot disappear into an indefinite “future research” entry.

## 3. Finding-to-work coverage ledger

Create a machine-checkable manifest from this ledger. Each rule or tightly
coupled family must declare: stable ID; source/edition/locus; doctrinal versus
derived status; required/conditional/advisory applicability; inputs and
missing-input behavior; formula/table; clock and partition; transition
dependencies; permitted exception IDs; source fixtures and transport fields.
Classify positive preferences separately from prohibitions. If a condition's
applicability is unknown, it is not automatically `not_applicable`.

| ID | Research finding / source scope | Disposition and completion requirement | Packages |
| --- | --- | --- | --- |
| M01 | Legacy wedding stars/tithi contradictions | Correct the eleven stars and Mula treatment; one documented tithi basis; explicit guidance-only deprecation and migration tests. | A, B, F |
| M02 | MC 55 star, tithi and weekday eligibility | Required ordinary rules. Collate the wider MC restrictions and distinguish permission, preference and veto. Do not import PVR/Raman lists into MC. | A, B |
| M03 | Marriage Karana coverage | Required ordinary rule, source-locked beyond merely reusing Vishti. Resolve Kinstughna treatment from the selected authority; record PS/Drik differences without attributing their choice to MC. | A, B |
| M04 | Samskara 26 / Vivaha 13 calendar tension | Required solar and lunar qualifications under the chosen precedence, including Gemini/Ashadha and exceptional month evidence. | A, C |
| M05 | MC 56 five-line vedha | Required independent pair table and opposing-pada rule with its proper Abhijit treatment. | B |
| M06 | MC 57 seven-line vedha | Required fourteen reciprocal pairs, source planet-nature/pada qualifications; independently collated from M05. | B |
| M07 | MC 58 occupied/pierced/passed stars and clearance | Required astronomical history predicates; separate extraordinary omen clauses as excluded. Missing lookback evidence stays unavailable. | C |
| M08 | MC 59 Latta | Required planet-specific counts, direction, origin inclusion and source-selected grid. No unsourced retrograde reversal. | A, B |
| M09 | MC 60 Pata and quoted variants | Required selected MC prescription with yoga-ending evidence; alternative attributed prescriptions remain distinct, non-executable until admitted. | A, C |
| M10 | MC 61 Krantisamya | Required source sign-pair relation; do not replace with declination equality. | B |
| M11 | MC 62 Ekargala | Required named yoga set and expressly Abhijit-inclusive count. | B |
| M12 | MC 63–64 Upagraha/pada qualification | Required source table/qualification; no alias to another upagraha solely by name. | A, B |
| M13 | MC 64 adverse daylight eighth | Required full-parent daylight partition with weekday ownership. | C |
| M14 | MC 65 Kulika | Required day/night fifteenths and Saturday qualification; distinct from Gulika longitude. | C |
| M15 | MC 66 Dagdha | Required solar-sign/tithi mapping with explicit tithi numbering. | B |
| M16 | MC 67–68 Jamitra | Required Lagna- and Moon-based checks and 55th-Navamsa formulation, with separately targeted relief. | B, E |
| M17 | MC 69–71 regional treatment, star sums and relief | Required selected branch and source star-sum arithmetic; geography does not infer a tradition. Record regional alternatives and finite exception targets. | A, B, E |
| M18 | MC 72 southern Bana | Required named elapsed-tithi/Lagna formula with its source applicability, distinct from Panchaka. Do not turn a regional branch into a universal veto. | A, B |
| M19 | MC 73–74 solar-degree Bana | Required separate formula and weekday/day-night/purpose applicability; include Sun whole-degree transitions. | B, C |
| M20 | MC 75–78, 84–88, 92 existing Lagna components | Required reuse under their actual source/frame/variant contracts; their placement score is explanatory and cannot determine overall eligibility. | E |
| M21 | MC 79–83 additional ordinary Lagna restrictions | Required source derivation, fixtures and findings. Difficulty does not justify silently omitting them. | A, E |
| M22 | MC 88 Kartari; 89–91 broader remedies | Required Kartari detection and explicit source-remedy catalogue. Implement mathematically defined ordinary remedies. Resolve qualitative wording through finite source collation before admission; if an optional interpretation remains unestablished, name it as not admitted, leaving the raw restriction effective. Missing data for an admitted remedy is a different, unavailable state. | A, E |
| M23 | Samskara 27 / SS IX asta/balya/vriddha | Required directional Jupiter/Venus event definition, full neighboring-event context, buffers and typed witnesses. MC 28 alternatives stay separately identified. | D |
| M24 | MC 12 personal shuddhi | Required in the requested personal layer: bride Jupiter, groom Sun, both Moons, with independent findings. | E |
| M25 | MC 14 birth-period/first-born context | Required in the requested personal/context layer with explicit facts. MC/KP differences are preserved. Unknown facts do not disappear. Family ritual spacing in 15–16 remains excluded; catalogue any separate astronomical/month qualification retained from these verses. | A, E |
| M26 | Election Tara and Janma ambiguity | Admit a source-defined marriage election Tara policy in the requested personal layer; do not reuse Tara Kuta or label the shared unresolved Janma case a pass. | A, E |
| M27 | MC 93–95 context/special marriage form | Enumerate exact ordinary applicable predicates in the source worksheet; include them or name a precise contextual exclusion. No blanket exclusion of these verses as “context”. | A, E |
| M28 | MC 99–101 / VV / BS Godhuli | Required separate, explicitly derived Godhuli composition with declared temporal authority, MC exception targets, weekday/planetary qualifications and the ordinary result retained. BS provides comparison evidence, not a numeric window. | A, E, G |
| M29 | Missing complete-purpose engine/REST composition | Canonical catalogue, direct, reader-derived datetime and windows operations; strict evidence/state invariants and lossless public/HTTP parity. | F, G |
| M30 | Calendar-oracle limitations and source conflicts | Worked source/astronomy cases plus a comparison ledger; only compare external calendars on their stated common rule subset. No unsupported complete external-certification claim. | A, D, H |

The manifest must also enumerate the exclusions from section 1, including
matching passages from Vivaha 21 onward and preparatory acts in 96–98.
Conditional rules are still implemented: they return `not_applicable` only
when the prerequisite establishing non-applicability is known. A source
variant appearing in the research catalogue is not automatically an
executable profile option.

Also enumerate every reused foundation rule: Panchanga yoga/Karana/Tara
checks, selected Vishanadi/Tyajya and Yamaghanta rules, nakshatra/tithi/Lagna
Gandanta, Lagna placements and named-window eligibility. For each, explicitly
select the compatible component profile, applicability and remedy behavior.
Reusing a component's arithmetic does not authorize inheriting its defaults
or importing a rule from another book. The compatibility manifest must make
these shared dependencies as testable as M01–M30; a missing required foundation
cannot be hidden behind a completed new wedding rule.

## 4. Canonical result and input contracts

Use immutable engine-owned policy/input/result vessels. The ordinary profile
has a stable versioned ID, provisionally `mc_avasthi_2004_marriage_ordinary.v1`.
The personal layer and Godhuli composition have their own IDs and source
receipts. Freeze final IDs in package A and reuse them in Python, HTTP,
fixtures, documentation and generated discovery.

A finding carries `rule_id`, source references, applicability, evidence
availability, raw condition, measured/count values, exception assessments,
effective restriction, prerequisite IDs and unavailable reasons. Each
exception carries its target IDs and separately evaluated prerequisites.
Do not use a single optional boolean for all these states.

Return separate astronomical, personal and requested-composition decisions,
each with coverage completeness. An unrequested personal layer has
`not_requested` status and never contributes a personal pass. The aggregate
logic for a selected layer is:

| Evidence | Decision | Coverage |
| --- | --- | --- |
| At least one detected restriction has no demonstrated applicable cancellation | `restricted` | Complete or incomplete, independently reported |
| No effective restriction is established, but a required input/rule/applicability/boundary is unresolved | `indeterminate` | Incomplete |
| Every applicable required rule is evaluated, with no effective restriction | `passes_selected_profile` | Complete |

Unknown remedy prerequisites do not cancel a restriction. Their unavailability
remains visible alongside the conservative restriction decision. A favorable
advisory, named yoga or strength score never outranks a required finding.
Expose exclusions and their reasons without inflating the evaluated count.

Direct assessment accepts typed raw evidence, not caller-provided verdicts.
It may include canonical positions, calendar/solar parents and history/event
witnesses. Recompute derivable values and reject contradictions in epoch,
frame, body identity, interval containment, source selection or parent/child
relationships. Validate all admission conditions before opening a resource.
Missing evidence is allowed and produces partial/indeterminate findings;
malformed or mutually contradictory evidence is an input error.

Caller-supplied astronomical evidence is explicitly `caller_supplied`;
validation does not make it engine-verified. A direct pass is conditional on
that supplied evidence, and cannot claim reader-derived provenance. The
reader-derived path constructs the same input object and invokes the same
evaluator. Historical parents and natal epochs are distinct from the election
epoch; validate each in its own context rather than falsely requiring all
epochs to match.

Personal records have stable, distinct participant IDs and explicit role
assignments. Identical birth positions are valid; duplicate identities or
conflicting role assignments are not. Support canonical supplied natal
evidence first; do not add an implicit birth-chart calculation path with
different frame defaults. Record missing birth month/tithi/star/first-born
facts individually when a selected rule needs them.

## 5. Public operations, REST and ownership

The proposed public operations are:

| Engine / curated Python | REST operation | Resource boundary |
| --- | --- | --- |
| `marriage_election_catalogue()` | `GET /v1/muhurta/marriage/catalogue` | No ephemeris required; profiles, rules, variants, exclusions, supported limits. |
| `assess_marriage_election(evidence, *, policy, personal=None)` | `POST /v1/muhurta/marriage/direct` | Kernel-free evaluation of explicitly supplied evidence. |
| `marriage_election_for_datetime(dt, latitude, longitude, *, timezone, policy, personal=None, reader=None)` | `POST /v1/muhurta/marriage/datetime` | Serving-reader evidence for one aware instant; no duration guarantee. |
| `marriage_election_windows(start, end, latitude, longitude, *, timezone, policy, personal=None, limits=None, reader=None)` | `POST /v1/muhurta/marriage/windows` | Bounded half-open instant range; local IANA timezone owns civil/sunrise-day interpretation. |

`start` and `end` are aware instants with `start < end`; equivalent offset
representations refer to the same range. Convert to the declared local zone
through the canonical time owner. Do not silently accept a nonexistent
ZoneInfo local datetime or an inconsistent fold. A local-date UI can compute
its requested bounds; the API does not need a second ambiguous inclusive-date
range convention. Catalogue/direct requests must remain usable without
constructing a kernel-dependent `Moira` instance.

Add strict request/response models using existing `_StrictModel`, finite
numeric types and literal profile IDs. Validate unknown fields, booleans in
numeric slots, nonfinite values, malformed angles, duplicate body/participant
IDs, tuple sizes, unsupported combinations and contradictory receipts. Mirror
engine admission rather than inventing a more permissive HTTP default.
JSON round trips must preserve rule IDs, sources, numerical uncertainty,
coverage, exception witnesses and resource/frame provenance.

| Outcome | Engine / HTTP behavior |
| --- | --- |
| Invalid inputs or unsupported selector | Engine validation error / HTTP 422 validation envelope. |
| Missing serving kernel, clock or anchor resource | Existing Muhurta resource error / HTTP 503 `muhurta_resource_unavailable`. |
| Required epoch outside serving coverage | Existing coverage error / HTTP 422 `muhurta_date_outside_coverage`; explain requested versus parent/history epoch. |
| Valid but unavailable scientific context, such as polar geometry or unsupported month interpretation | Typed successful assessment with per-rule unavailable reasons; HTTP 200 preserves that result. |
| Bounded history was searched but a required witness was not established | Typed incomplete context, never “clear” by absence; disclose searched extent. |
| Deterministic work/output limit exceeded | New specific budget error, following the existing Sade Sati HTTP 422 search-budget convention, with limit kind/counts; no apparently complete partial result. |
| Complete evaluation with no eligible interval | HTTP 200, complete coverage and empty eligible list; distinguish from an empty list with indeterminate coverage. |

Use one request-scoped work meter across component calls and any supporting
search outside the requested interval. The facade passes its bound reader;
borrow it without closing it and restore any reader override on success,
failure or cancellation. Cache only with complete resource/frame/policy and
observer keys; prefer request-local caches. No hidden download or alternate
reader fallback. Detailed evidence must not be dropped to fit a response cap.

### Planned file ownership

New files below are proposed owners, not files already implemented:

- `moira/muhurta_marriage.py`: policies, typed input/result vessels,
  catalogue, pure assessment and aggregate invariants.
- `moira/_muhurta_marriage_sources.py` and
  `moira/_muhurta_marriage_rules.py`: immutable source-owned tables,
  rule manifest, discrete calculations and exception target definitions.
- `moira/muhurta_marriage_visibility.py`: SS-derived Jupiter/Venus adapter,
  directional events, waiting periods and provenance. Reuse protected
  astronomical primitives where their semantics match; do not replace the
  general physical-visibility model.
- `moira/muhurta_marriage_dated.py`: serving-reader evidence resolution,
  event dependency collection, bounded interval composition and budgets.
- Existing `moira/muhurta.py`: marriage-only legacy correction/deprecation.
  Reuse [Panchanga Shuddhi](../../moira/panchanga_shuddhi.py),
  [doshas](../../moira/muhurta_dosha.py), [Lagna](../../moira/muhurta_lagna.py),
  [dated Lagna](../../moira/muhurta_lagna_dated.py),
  [special windows](../../moira/special_muhurta.py),
  [lunar month](../../moira/lunar_month.py) and their admitted owners.
- `moira/__init__.py`, `moira/vedic.py`, `moira/facade.py`,
  `moira/_facade_vedic.py`: curated exports and matching facade delegation.
- `moira_server/models/muhurta_marriage.py`,
  `moira_server/services/muhurta_marriage.py`,
  `moira_server/serializers/muhurta_marriage.py`, their required export
  aggregators, [Muhurta router](../../moira_server/routers/muhurta.py) and
  [error mapping](../../moira_server/errors.py): strict, thin transport.
- New source/geometry fixtures and unit/integration/server tests named in
  section 7; `wiki/02_standards/MARRIAGE_ELECTION_STANDARD.md` and a dated
  `wiki/03_validation/VEDIC_MARRIAGE_ELECTION_VALIDATION_YYYY-MM-DD.md`
  receipt; route/public inventory and appropriate CI selections.

This work intersects protected public APIs, REST, astronomical event
computation, source tables and validation evidence under `AGENTS.md`.
Declare the exact affected anchors before each implementation edit. New
module names do not remove those obligations. No speculative native port,
new external ephemeris substrate or new base-runtime dependency is planned.

## 6. Eight implementation packages

### A. Lock source contracts, policies and migration

Complete the M01–M30 manifest and an explicit exclusion list. Recheck each
transcribed table against the named scan; lock MC-wide tithi/Karana coverage,
regional branch applicability, counting origins, nature changes, additional
Lagna predicates and source-scoped cancellation prerequisites. Derive missing
details in finite worksheets with page/verse, calculation and expected result.
Resolve ordinary clauses in 93–95 individually. A required unresolved formula
blocks profile admission rather than becoming an unnoticed optional rule.

For every required predicate **and every remedy prerequisite**, declare all
events that can change its truth. These dependencies become part of the
manifest and determine the dated evaluator in G. Define source-owned typed
vessels and matching strict transport models from the start; keep incomplete
profiles out of the production-supported catalogue.

Legacy migration: preserve the direct-module callable and dictionary/list
shape, correct the eleven stars, remove Mula from the contradictory avoid
list, and make marriage tithi lists explicitly **zero-based absolute lunar
indices 0–29**, generated from the selected paksha-aware rule table. Preserve
existing keys; document any added basis/source metadata. Do not invent a
preferred ranking: use an empty preferred list when the selected source
supplies no separate ranking. Mark the getter deprecated for marriage with a
warning and guidance-only note directing callers to the typed API. Direct
dictionary access remains documented legacy guidance, not a complete result.
Prevent legacy mutable data from becoming the typed manifest's authority.
Other activity dictionaries are outside this repair.

**Exit:** every research-inventory row is accounted for; all source worksheets
needed by subsequent rules have a concrete owner and gate; policy selectors,
coverage invariants and migration behavior are fixed. Catalogue and strict
model fixtures agree, without advertising unfinished production profiles.

### B. Implement discrete marriage rules

Implement M02/M03/M05/M06/M08/M10/M11/M12/M15/M17/M18/M19 and discrete parts
of M16 from the declared tables. Own the ordinary and Abhijit-inclusive grids
separately. Centralize exact partition ownership rather than repeating
float/floor approximations across rules. Derived count/identity receipts
must expose enough inputs to audit the formula.

Tests must establish the eleven-star set, fourteen seven-line pairs including
Dhanishtha–Vishakha and Chitra–Purva Bhadrapada, independent five-line pairs,
opposing padas, Latta directions and origin counts, Krantisamya sign pairs,
Upagraha/Ekargala sets and solar-sign/tithi mappings. Demonstrate different
answers where MC72, MC73 and generic Panchaka would be confused. Add exact
and neighboring-float tests for Sun whole degrees and unequal Abhijit edges.

**Exit:** source arithmetic, pure assessment, public result shape and HTTP
serialization/validation pass for every introduced finding. No unresolved
table is replaced with a familiar but differently named calculation.

### C. Complete calendar, solar partitions and history

Compose the lunar-month and solar-day owners for M04/M07/M09/M13/M14 and
the temporal applicability of Bana. Calculate complete lunations, tithis,
nakshatras and day/night parents before clipping. Preserve month ambiguity
and unsupported intercalation. Implement the chosen calendar precedence and
all lunar qualifications; do not merely whitelist six solar signs.

Define the history needed for occupied/pierced/passed-star and yoga-ending
conditions and for Moon clearance. Establish which event resets each state,
how to prove the relevant history was covered, and the bounded unavailable
outcome when it was not. A current longitude cannot certify a past event.
Validate supplied history against chronology, identity and parents; never
accept a freely supplied “history clear” flag.

**Exit:** Scorpio precedence, Gemini/Ashadha Dashami, solar ingress inside
a lunar date, daylight eighths, day/night fifteenths, Saturday qualification,
pre-sunrise ownership, DST, negative offsets, polar and exceptional-month
cases pass through direct, facade and HTTP contexts. Historical gaps remain
visible and cannot yield a complete pass.

### D. Derive and validate Jupiter/Venus availability

Write the SS IX.1–11 derivation before numerical implementation. State the
modern coordinate/frame inputs, the source apparent-place correction,
ascensional/time-degree quantity, sunrise/sunset geometry, branch selection,
equality ownership and admitted latitude domain. Keep tropical horizon
geometry separate from sidereal rule membership. If a modern substitution
changes the historical recipe, identify that substitution and its effect.

Implement the source Jupiter threshold and both Venus event branches with
event witnesses and uncertainty brackets. A root solver must implement the
declared event object; daily sampling, generic physical visibility and fixed
longitude combustion cannot silently stand in for it. Resolve preceding and
following relevant events even when outside the requested range. A simple
15-day request padding cannot establish every availability state.

Apply MC27 directional balya/vriddha buffers with the selected elapsed-UT1-day
convention, preserving the original event and shifted brackets. The invisible
interval, pre-disappearance interval and post-appearance interval are separate
findings. Do not auto-select the shorter MC28 or KP variant.

Use independent source-unit calculations, at least one fully exposed case
for each Jupiter/Venus event branch, both hemispheres, relevant seasonal
geometry, equality neighbors and a case differing from longitude-orb
combustion. Check derived geometry against an independent astronomical
construction under the same frame/timescale/horizon and predeclared tolerance.
Changing ayanamsa alone must not change tropical heliacal geometry.

**Exit:** source and astronomical validation both pass, with documented
derivation, event-order/buffer boundary tests and engine/HTTP witness parity.
Actual observed visibility is not claimed from this traditional model.

### E. Complete Lagna, personal assessment and remedies

Reuse the admitted Lagna/Navamsa components while adding complete selected
Jamitra, 55th Navamsa, MC79–83 and ordinary Kartari restrictions. Validate
canonical positions against any supplied context, preserving the prior
adversarial repairs. Additional Shadbala, if exposed as explanatory evidence,
retains its exact frame/UTC weekday and cannot become an invented veto or
global remedy threshold.

Implement personal M24–M27 with both participants and explicit birth/context
facts. Separate bride-Jupiter, groom-Sun, each Moon, election Tara and birth-
period findings. Resolve the selected marriage Janma treatment from its
source. Missing required context is not equivalent to a non-applicable rule.

Implement finite cancellation rules and targets. Distinguish missing data
for an admitted predicate from an unestablished interpretation of qualitative
wording. The first yields unavailable evidence; the second requires further
finite source collation, or a named not-admitted optional interpretation in
the catalogue. Neither cancels a detected restriction. Do not disguise an
unimplemented algorithm as a missing caller input or synthesize a strength
cutoff. Quantitative source-supported remedies required by the manifest must
be implemented and tested, not deferred wholesale.

Deliver a Godhuli composition explicitly naming **VV temporal geometry plus
selected MC99–101 exception rules**. It is a derived composition, not a claim
to implement MC's seasonal visual description numerically. Source-collate
its retained weekday, Moon/Mars and other qualifications. Keep the ordinary
assessment and raw restrictions alongside the exception outcome. The
literal MC seasonal timing description and BS's unquantified twilight rule
remain recorded alternatives, not mislabeled executable clocks.

**Exit:** role swaps, missing first-born/birth-period facts, identical valid
natal charts, invalid duplicate IDs, Janma cases, targeted versus unrelated
remedies, unknown strength prerequisites and Godhuli's retained prohibitions
pass across engine and HTTP. No remedy erases evidence.

### F. Complete instant public/facade/REST composition

Wire the four proposed operations through canonical public exports and
`_facade_vedic.py`. Build one reader-derived evidence context for a datetime
and call the pure evaluator. Source snapshots, policy and personal context
must remain immutable and internally consistent. Mirror strict engine
validation in request admission before resource access.

Complete catalogue/direct/datetime routes and their discovery/OpenAPI and
error envelopes. Add explicit supplied-versus-derived provenance tests.
Verify the catalogue's executable IDs exactly match accepted policy IDs in
engine and HTTP; unknown or research-only variants reject consistently.

**Exit:** all instant rules required by the selected profile are implemented
and fixture-backed; direct and dated assessment agree when given the same
canonical evidence; the public API and strict HTTP response preserve every
finding, exception, coverage state and receipt. Reader tests prove borrowing,
restoration, no ambient fallback and validation before resource access.

### G. Build bounded transition-derived intervals

Implement the windows operation as its own marriage product. The existing
[sampled Muhurta search](../../moira/muhurta_search.py) remains a separate
contract. Use the transition ledger to partition the requested range, evaluate
open interiors and handle endpoints under a single half-open convention.

Required transition families include Panchanga limbs; all relevant planetary
27/28-star and pada membership; Sun sign **and whole-degree** boundaries;
Lagna/D9/55th-Navamsa and source aspect boundaries; Moon-phase/planet-nature
switches; source remedy prerequisites; sunrise/sunset and source day/night
fractions; lunar-month boundaries; heliacal events/buffers; and history reset,
yoga-ending and Moon-clearance events. An optional selected remedy adds its
own transitions; it cannot be evaluated only at a cell midpoint.

Demonstrate event completeness for each family using its governing geometry:
unwrapped angle branches, station/extremum subdivision, appropriate bounded
root isolation and explicit singularity handling. Sign-change bracketing alone
misses tangencies or paired crossings. A dense sample grid is a supplementary
probe, never a completeness proof. If completeness cannot be established in
a region, expose that region as indeterminate rather than returning a
guaranteed eligible span across it.

Carry numerical brackets through derived offsets and intersections. Use the
existing 0.1-second default / 0.01–1-second requested tolerance convention
where the component can meet it; report any wider actual uncertainty rather
than claiming the requested value was achieved. Unresolved overlapping
brackets form an indeterminate band. Do not silently merge close events or
step over narrow prohibited intervals. Explicitly account for simultaneous
events and exact boundary points; a zero-duration point is not an eligible
duration window.

Return complete assessment cells, eligible interiors and indeterminate bands,
with source/event references. Coalesce presentation intervals only when no
uncertain/restricted gap is crossed; retain the underlying cells when evidence
changes but the aggregate decision does not. Build full supporting parents
and outside-range event context first, then clip once to `[start,end)`.

**Exit:** analytic tests for tangencies, double roots, retrograde recrossings,
wrap, simultaneous transitions, narrow restrictions, uncertain endpoints and
clipped parents pass. Real-reader examples exercise every selected event
family; direct evaluation agrees inside reported cells. HTTP returns exactly
the same coverage, boundaries and eligibility.

### H. Calibrate limits and close admission

Measure the implemented profile before fixing its public operational limits.
Maintain separate counters for requested duration, supporting-history extent,
position evaluations, root work, event count, returned cells/windows and
serialized response size. Set finite defaults and hard maxima from the
measured ordinary, dense-transition, high-latitude and long-history corpus;
publish the values in the catalogue and acceptance receipt before release.
The existing sampled search's 30 days / 4,096 samples / 128 results are not
automatically valid limits for this product.

Use provisional finite guards from the first implementation of each loop and
benchmark harness; calibration refines those guards rather than introducing
bounds only after an unbounded implementation has been exercised.

Prefer deterministic work counters. A wall-clock interruption is an operation
failure, not a reproducible scientific result. Check limits before expensive
expansion and after each bounded unit of work, including nested/history
calls. Return the named budget error on exhaustion or output overflow; do
not truncate into a successful-looking answer. Do not add pagination or
resumability without a demonstrated need and a separate stable contract.

Run the source, astronomical, boundary, resource and HTTP acceptance suites,
then a second adversarial composition pass. Resolve in-scope findings and
rerun affected cases before finalizing the source standard and validation
receipt. Keep source arithmetic, primary astronomical comparison, regression
parity, cross-engine corroboration and geometric invariants separately labelled.

**Exit:** all gates in section 7 pass; the final manifest has no unimplemented
required rule; operational limits are measured; engine/public/facade/REST
coverage is equal. Reconcile the remaining-work register with the exact
selected marriage scope. Other VED-011 purposes remain open.

## 7. Acceptance and verification

### New validation artifacts

Create independently transcribed source fixtures under
`tests/fixtures/marriage_election_sources.json` and worked geometry/event
fixtures under `tests/fixtures/marriage_visibility_cases.json`. Every case
records edition/hash/page, inputs, exact units/index basis, expected rule
outcome and interpretation. Do not generate source expectations by calling
the production rule under test. Keep private book PDFs outside the repository.

Proposed test ownership:

- `tests/unit/test_muhurta_marriage.py`: catalogue, source arithmetic,
  profiles, legacy migration, personal completeness and aggregate invariants.
- `tests/unit/test_muhurta_marriage_visibility.py`: independently derived
  time-degree geometry, event branches, buffer arithmetic and singularities.
- `tests/unit/test_muhurta_marriage_windows.py`: analytic transition cases,
  complete-parent/clipping semantics, uncertainty and deterministic budgets.
- `tests/integration/test_muhurta_marriage_ephemeris.py`: real serving-reader
  cases, independent astronomical witnesses and whole-profile worked cases.
- `tests/server/test_server_muhurta_marriage.py`: catalogue/direct/datetime/
  windows parity, strict hostile input, OpenAPI, typed errors and resources.

### Mandatory proof matrix

| Gate | Required result |
| --- | --- |
| Source coverage | M01–M30 and every research section-5 row map to an explicit manifest entry; no required implementation gap. Source disagreement fixtures remain policy-specific rather than forced into agreement. |
| Source arithmetic | Exact tables and independent rational/hand-worked expectations, including Abhijit `[276°40′,280°53′20″)`, opposing padas, Latta origin counts, both Bana formulae, Kulika/daylight eighths and Dagdha. |
| Source interpretation | Calendar precedence, Karana/tithi scope, regional applicability, nature, personal roles/Janma and each remedy prerequisite are named and fixture-backed; no ranking inferred from unspecific prose. |
| Astronomical authority | Source-defined SS quantity derived and checked against an independent geometry construction; modern positions/frame/clock checked using relevant primary authority fixtures under declared tolerances. No test calibrated solely to another wedding calendar. |
| Complete worked cases | Input positions, source decisions, exceptions and aggregate outcomes exposed for ordinary, personal, Godhuli, unavailable, known-restricted/incomplete and boundary cases. |
| Interval completeness | Every predicate and remedy dependency has a transition method and adversarial witness; uncertain or unsupported bands cannot become eligible windows. |
| Admission symmetry | Catalogue selectors, strict input domain, missing/contradictory distinctions, output invariants and all error classes agree across pure engine, facade and HTTP. |
| Resource truth | Required real-kernel/clock cases actually execute with serving-reader evidence; missing resources produce explicit errors. Resource skips do not count as closure of this gate. |
| Operational bounds | Measured counters, deterministic exhaustion, bounded history/root iterations, output caps, and complete-empty versus indeterminate-empty cases are tested. |
| Compatibility | Corrected legacy import/getter shape and deprecation tested; existing Muhurta sampled/scoring and component endpoints retain their independent contracts. Previous Vedic adversarial repairs stay green. |

The research did not establish a published full paired marriage-election
oracle. Do not label the completed implementation externally certified as a
whole on the basis of source arithmetic or calendar dates. This does not
excuse omitting validation: independently verify the source formulae,
astronomical primitives and complete worked decisions, and disclose the
precise scope of each comparison. If adding a Drik fixture, preserve its
location, timezone, access/version and explicitly shared subset; its omitted
tithi/weekday/Lagna checks cannot validate those Moira rules.

### Execution sequence and commands

All implementation verification uses the project `.venv`. Before kernel-bound
checks, resolve the resource through `_kernel_paths.py` with downloads disabled.
Start with the package's smallest unit/source/model slice, then its HTTP and
real-reader cases; broaden once the component passes.

```powershell
$env:PYTHONUTF8='1'
$env:MOIRA_NO_DOWNLOAD='1'
$env:MOIRA_TEST_MODE='1'
$env:MOIRA_STRICT_KNOWN_ISSUES='1'
.\.venv\Scripts\python.exe -m pytest tests/unit/test_muhurta_marriage.py tests/unit/test_muhurta_marriage_visibility.py tests/unit/test_muhurta_marriage_windows.py tests/server/test_server_muhurta_marriage.py -q -m "not external_network"
.\.venv\Scripts\python.exe -m pytest tests/integration/test_muhurta_marriage_ephemeris.py -q -m "not external_network"
```

At final acceptance include affected existing Panchanga, lunar-month,
Shuddhi, dosha, Lagna, special/named-window, sampled Muhurta and public API
slices. Retain `test_vedic_second_pass_repairs.py`,
`test_server_vedic_second_pass_repairs.py` and relevant serving-reader tests.
Run protected astronomical/native parity slices only for primitives actually
changed, then the current release-hardening selection. Add representative
new source/boundary/server tests and required integration coverage to the
owning CI workflows so the selected profile's dependencies cannot disappear
from release verification.

Report exact commands, distinct pass/failure/skip counts, real resource uses,
baseline versus new lint findings, source tolerances and remaining limitations.
Do not inherit the previous repair package's 6,342 passes as this package's
validation. Use scoped Ruff and supported Python grammar checks; perform
the repository's derivation/lineage audit after correctness review.

Update the owning standard and a protected validation receipt with those
results. At publication preparation run doc consistency, release identity,
Hellenistic inventory, REST-reference, generated-wiki and applicable website
publication-bundle checks through their owning scripts. Generate the wiki;
never hand-edit its files. Verify route counts from the actual admitted
router, not a guessed future total.

## 8. Completion and authorization boundary

Implementation is complete only when the finite manifest, source derivations,
all selected calculations, engine/public/REST contracts, bounded interval
evidence, operational limits and adversarial acceptance are complete together.
A pure calculator, HTTP wrapper, fixture-only implementation or sampled
window substitute does not close this package.

If a newly discovered source ambiguity affects a required rule, resolve it
within the owned source worksheet or propose a named interpretation with
supporting evidence. Do not quietly reduce the selected scope to declare
completion. If an optional remedy interpretation remains unestablished after
the source task, its not-admitted state and effect on the profile's scope must
stay visible. That is distinct from missing evidence for an implemented rule.

At the original planning checkpoint, the turn created only this plan file. It preserves the preceding
research/register edits and leaves runtime, tests, generated wiki, version
and other repositories unchanged. Commit/push, tag/release, deployment and
website/Urania adoption remain separate user-authorized actions. When source
publication is later requested, publish the generated wiki first and then
the engine with its exact wiki gitlink.

### Historical planning verification receipt

The plan was checked against the current component signatures, public/facade
and REST conventions, source research inventory, resource/error contracts,
nearest tests and CI gates. A read-only contract exploration and independent
design pass informed the required transition ledger and coverage invariants.
Verification passed for all 30 ordered coverage IDs, eight work packages,
11 local links, new-page whitespace and an in-memory preview through the
owning wiki generator. The preceding research/register file hashes are
unchanged. `scripts/check_doc_consistency.py` and `git diff --check` passed.
No runtime tests, generated-wiki synchronization or publication are claimed
for this planning turn.

### Implementation acceptance checkpoint

All eight work packages and the mandatory proof matrix are complete for the
selected marriage scope. The source standard records the named interpretations
and exclusions; the final validation receipt records source/geometry evidence,
227 focused passing tests, both full real-reader HTTP cases, repaired adversarial
findings, operational limits and generated-documentation checks. The catalogue
now reports `source_scoped_public`. The original six-hour request took about
28 minutes on this host. The subsequent
[first performance optimization](../03_validation/MARRIAGE_ELECTION_PERFORMANCE_2026-10-10.md)
reduces that measured HTTP calculation to 8.3 minutes with the complete
response preserved apart from its native-backend fingerprint. The subsequent
[exact-reuse pass](../03_validation/MARRIAGE_ELECTION_REUSE_2026-10-10.md)
records further optimization and reusable computation infrastructure.
No background-job or website service is implied.
Other VED-011 purpose profiles, publication and release remain separate.
