# VED-011: purpose elections implementation plan

**Status:** P0–P6 locally complete and validated, 11 October 2026.
The user authorized following this plan through its end, beginning with
housing/Vastu. Commit, push, release and deployment remain separate actions.
The subsequent source-publication authorization packages the implementation
and all four focused-review repairs together; see the
[publication record](../03_validation/PURPOSE_ELECTION_VALIDATION_2026-10-11.md#7-source-publication-package).
Release and deployment remain separate actions.
**Basis:** [four-area source research](VEDIC_PURPOSE_ELECTION_SOURCE_RESEARCH_2026-10-11.md),
including complete MC48 scans, edition-separated variants, printed conflicts
and a finite admission-decision register.
**Baseline:** engine `c0c1d739c9cdf52910ff2f64aea6ac0ad88e347f`, wiki
`7ad434a903555679a2393afd7487138bb9d3634c`, version 6.9.9.
The existing MC marriage implementation and both published performance passes
are the compatibility baseline.

## 1. Intended outcome and sequence

Deliver source-defined election assessments for all four researched areas,
with equally strict engine, curated Python, facade and REST contracts.
Every supported profile must include a catalogue, direct evidence assessment,
reader-derived instant assessment and bounded certified windows. A component
may be exposed as a component, but must not masquerade as a complete profile.

Recommended delivery order:

1. MC48 housing: foundation commencement and residential entry, with separate
   ordinary first-entry, return and explicitly qualified exceptional scopes.
2. MC04 commerce: purchase, sale and first opening for trade under a declared
   `vipani` anchor composition.
3. MC48 ordinary travel: explicit departure anchor and direction; separately
   admitted KP directional/time components where their source contracts close.
4. VV ordinary marriage, followed by a separately source-closed KP ordinary
   marriage profile. Existing MC defaults and named Godhuli remain available.

The seven work packages below are dependency groups, not a requirement to
repeat twelve phases. Each vertical package includes its engine and REST
work, relevant source fixtures, hostile-input tests and real-resource checks.
No unfinished choice appears in the supported-profile catalogue.

Full Vastu site/design calculations, structural safety, lending/borrowing,
commodity-specific trades, incorporation and contract-specific elections,
military travel, compatibility matching, family ritual scheduling and whole-
ceremony duration searches remain explicitly separate extensions. Raman
profile admission additionally needs a verified printed edition. These
exclusions define this plan's deliverable rather than an unnamed future backlog.

## 2. Decisions fixed by the plan

### 2.1 Authority belongs to the selected action and edition

Each immutable profile manifest identifies:

- profile ID/version, source edition, scan hash and page/verse loci;
- purpose, actor roles and elected anchor, including any modern composition;
- every required rule and imported dependency, plus explicit exclusions;
- star partition, calendar, weekday clock, frames, units and index conventions;
- severity/preference classification, combination precedence and result states;
- exact remedy prerequisites, target rule IDs and non-cancellable restrictions;
- transition dependencies, missing-evidence behavior and validation fixture IDs.

The initial naming examples `mc_maniprabha_1948_house_entry.v1` and
`vv_vasantalakshmi_ordinary.v1` were planning placeholders, not API values.
Final runtime identities and their source/version distinctions are listed in
the [execution receipt](../03_validation/PURPOSE_ELECTION_VALIDATION_2026-10-11.md#1-delivered-source-and-public-contracts).

MC04 retains its own identity for existing marriage and the new commerce
loci. MC48 owns new housing/travel. The complete undated MC-F scan is a
collation witness, not an invisible replacement for MC04. Conflicts in KP
affect the corresponding KP rule; they do not invalidate independent MC
prescriptions or authorize a guessed correction.

### 2.2 Complete assessment has several independent meanings

A result reports separately:

- **source coverage:** which selected rules were evaluated, excluded by the
  declared scope, or unresolved;
- **astronomical evidence:** derived versus supplied evidence, frame/resource
  binding and any unavailable prerequisite;
- **doctrinal assessment:** original restrictions, preferences and explicitly
  applied exceptions, retaining their evidence;
- **personal/context coverage:** which actor and contextual facts were supplied;
- **numerical certification:** what was proved for the instant or interval.

Unknown prerequisites do not pass a restriction and cannot enable a remedy.
An inapplicable rule is not an unavailable rule. A passed astronomical-only
assessment is not a complete personal assessment. An uncertified time band
is not a certified favorable window. Favorable factors do not erase adverse
findings unless a selected source rule names that cancellation.

### 2.3 Required context is explicit

| Family | Context that needs typed ownership |
| --- | --- |
| Housing | Foundation versus entry; first/return/qualified exceptional entry; residential scope; declared door/building facing; ritual versus occupancy anchor; relevant resident's natal evidence; required event facts. |
| Travel | Traveller, departure act, declared direction and convention, outbound/return scope, relevant journey/exception facts, optional earlier actual departure; historical distance units only under a named conversion. |
| Business | Buyer versus seller versus trading operator; action/anchor; actor-specific natal evidence when selected; a counterparty is a distinct role, not a second anonymous birth chart. |
| Marriage | Selected tradition, existing explicit ritual/regional settings, source-required partner roles and natal evidence, first-born/context facts where applicable, named remedy selection. |

Do not infer tradition from coordinates, caste or names. Do not infer a
house-facing direction from geographic longitude, or a journey bearing from
an unverified place label. An exceptional context can waive only the source-
specified findings. Historical outcome prose must not become a claim of
engineering safety, travel safety, financial return or personal character.

## 3. P0 — close the selected source manifests

**Deliverable:** a reviewable rule/variant ledger and independently transcribed
fixtures for each first-admission profile, before changing its runtime rules.

1. Close research decisions D01–D04 and D06–D09 at their affected profiles.
   Collate MC48 12–13 and the ordinary portions of 11, including cross-referenced
   general and marriage restrictions. Reconcile specific permissions with
   general prohibitions explicitly; do not union every list.
2. Bind C01's 28-position chakra to a named astronomical partition. Use an
   already admitted 28-star partition only after verifying its semantics;
   where the verse supplies ordinal rules but not longitude boundaries,
   identify the astronomical adapter as a documented computational composition.
   Keep H05 and C05 on their distinct 27-position bases.
3. Resolve MC commerce placement quantifiers and the general restrictions
   imported by “good tithi”. Record the modern first-opening anchor separately
   from the literal `vipani` source rule.
4. Finish VV's selected timing cross-references, including chapter 17, and
   distinguish concluded doctrine from opinions quoted for refutation. Freeze
   the protected full-Jamitra rule and its exact ordinal/degree definition.
   Its practical solar-rate/rising-time arithmetic is historical evidence;
   bind the timing predicates to Moira's admitted astronomical substrate and
   disclose that computational composition instead of replacing precise
   positions with the book's practical approximation.
5. For KP marriage, close its own general timing references, qualitative
   strength interpretation and waiting-period definitions. Do not import MC's
   solution just because the events or doshas have similar names.
6. Resolve D05 only for KP tables selected for implementation. Preserve a
   disputed reading as unavailable if collation cannot settle it; do not expose
   a supposedly complete profile that requires that unresolved rule. Record a
   precise follow-up source request and an independently supported alternative.

**Gate:** every required rule has an executable definition, source locus,
inputs, transition set, missing-data behavior and fixture. Every omission has
a scope reason visible in the catalogue. A modern interpretive composition
can be admitted when explicitly named and validated; it must not be falsely
labelled a verbatim classical prescription. These decisions are normal work
within the approved implementation package, not repeated approval prompts.

## 4. P1 — share evidence computation without sharing doctrine

Current owners include `moira/muhurta_marriage.py`,
`moira/muhurta_marriage_dated.py`, the `_muhurta_marriage_*` source, context,
frame, history, enclosure, search and certification modules, and
`moira/_bounded_memo.py`. Inspect actual dependencies before extracting code.

Introduce a private request context and dependency specification only for
operations genuinely needed by a second family: exact positions/frames,
solar events, phase parents, month classification, ingress/history events,
visibility and root certificates. Keep each source's rule evaluators, remedy
graph, qualification logic and catalogue under its own family/profile owner.

The first consumer migration should be small: one housing request plus the
existing marriage request. Avoid a wholesale rename or a universal plugin
framework. Keep public marriage vessels and call signatures stable. Add new
private modules only where the extraction has two real consumers; leave
marriage-specific computations in their present owner.

Required invariants:

- Request only the dependency closure of the selected rules. A simple
  transaction must not automatically pay for marriage visibility/history.
- Reuse exact immutable results through `_bounded_memo.py`; bind source,
  reader, frame, policy, epoch and all numerical arguments in dependency-safe
  keys. Approximate epoch bins and cross-request ambient caches are excluded.
- Keep source admission, reader lifetime and work accounting outside cache
  hits. Borrowed readers are not closed or mutated. Exceptions and unresolved
  evidence are not promoted to successful cache entries.
- Keep limits on range, events, root iterations, ephemeris work, historical
  lookback, output size and retained state. A cache must not bypass a limit.
- Preserve the admitted interval-Chebyshev primitive, exact reference,
  tolerances and floating-point assumptions. No native expansion is needed
  unless a new calculation demonstrates that need under the existing doctrine.
- Share a historical/visibility result only when its event definition and
  complete semantic key match, not merely its planet and approximate date.

**Gate:** existing marriage direct, instant and window responses retain their
meaning and numerical evidence. Compare complete payloads with no broad
normalization; any changed implementation/source fingerprint must be named
and reviewed separately. Rerun the two actual real-resource marriage HTTP
acceptance cases after the extraction, alongside targeted memo and budget
isolation checks. Source-only test doubles do not prove this migration.

## 5. P2 — housing vertical implementation

**Implemented owners:** `moira/muhurta_vastu.py` and narrowly necessary private
modules; matching strict REST model/service/serializer modules under
`moira_server/`. These owners now exist in the authorized implementation.

Implement C01–C04 and H01–H06 from the research ledger at the selected scope:
foundation timing and first/return/qualified exceptional residential entry.
Implement the 28-star Vrisha and 27-star Kalasha arithmetic independently.
Derive solar/lunar calendar, star/phase, facing/tithi, Lagna/placement and
natal-relative predicates from the profile manifest. Ritual-performance
facts are declared or explicitly outside astronomical coverage.

Retain ordinary findings when an old-house or extraordinary-entry exception
is applied. Do not extend that relief to first entry without its explicit
source qualification. Do not call the symbolic excavation-sector calculation
a physical Rahu azimuth. Door installation C05 may be added as a later purpose
with its own manifest; its 27-part arithmetic fixture belongs in the source
ledger now to prevent accidental conflation.

**Acceptance:** exhaustive cyclic-count tables, 27/28 and Abhijit boundary
cases, north-facing house-number wraparound, paksha-specific Purna/Amavasya
conflict, month/solar-sign precedence, natal-eighth and missing-facing cases,
ordinary versus qualified exception pairs, real instant and transition-window
HTTP cases, and unavailability at the relevant polar/horizon limits.

## 6. P3 — business vertical implementation

**Proposed owner:** `moira/muhurta_business.py`, with its strict transport
counterparts. Implement B01–B03 as separate actions under MC04. Required
planet and temporal evidence follows each action's manifest; do not compute
or apply every sale placement clause to a purchaser automatically.

Expose each actor's findings in a multi-party comparison. Detect that buyer
and seller preferred-star sets are disjoint without converting this into a
software error or an averaged favorable result. Preferences and mandatory
restrictions must retain their source-defined priority. Moon **and** Venus
in Lagna is a conjunction of conditions in the selected `vipani` prescription.

**Acceptance:** all six purchase, seven sale and eleven trading stars plus
all complement cases; same instant/different role; AND versus OR witnesses;
Aquarius, Rikta and weekday edges; placement quantifier cases; missing/extra
role rejection; bounded real instant/window HTTP parity. Lender/borrower and
contract/incorporation requests must be rejected as unsupported purposes,
not silently mapped to purchasing or opening a shop.

## 7. P4 — travel vertical implementation

**Proposed owner:** `moira/muhurta_travel.py`, with its strict transport
counterparts. Close and implement the MC48 ordinary astronomical travel
manifest, including its selected natal layer, directional rules and explicit
11.112 import set. Retain source-specific general-to-specific precedence.

Add KP components only under their own admitted names: for example, the
printed weekday-release clock and worked modular tests can have independent
contracts even if KP's disputed star-direction table is withheld. A caller
cannot label this composition “complete KP travel”. No automatic mixing
with MC occurs; a cross-source composition requires its own named manifest.

All direction transformations, sunrise offsets, strict release edges,
distance conversions, prior-departure validity and return contexts are typed
inputs or derived evidence with an explicit convention. Do not reuse generic
Panchaka, Varjyam, day eighths or marriage remedies without formula identity.

**Acceptance:** all weekday/direction combinations; tithi/star directional
edges; just before/at/after sunrise release; missing sunrise; the printed
Friday/Pushya/Panchami example; every shifted Panchakam residue; change of
departure anchor; return and prior-departure cases; exception prerequisites
and target isolation; real travel instant/windows with at least one directional
release and one astronomical transition. No sparse sampling may certify the
intervals between those events.

## 8. P5 — additional marriage profiles

Extend the existing marriage family through a finite profile registry or
equivalent explicit dispatch. Keep MC ordinary and existing Godhuli policy
values/defaults stable. New profile selection owns its own calendar, stars,
Navamsa, nature/house rules, history requirements and remedy graph.

Implement VV first using the closed M01–M07/M13 manifest; implement KP ordinary
using M08–M10 after its separate source gate. Reuse the canonical astronomy
only under matching semantics. Shared Godhuli geometry does not imply shared
permissions; the ordinary result remains visible when a named exception is
selected. Reject remedies that do not belong to the chosen profile.

**Acceptance:** source-owned fixtures where profiles intentionally disagree:
VV Phalguna/Pisces versus Chaitra; protected Jamitra despite otherwise favorable
placements; both partners' Moon evidence; profile-specific Navamsa boundaries;
KP best/middling versus prohibited dark-half dates; distinct visibility waiting
periods; eighth-house Mars testimony versus overall eligibility. Test profile
isolation and unchanged MC results with direct, dated and HTTP calls.

BS standalone full marriage and Raman/modern profiles are subsequent named
admissions, not empty aliases. Their research records remain discoverable
without appearing as supported production options.

## 9. Common public and REST contract

Use four operations per family, following the established marriage shape:

| Operation | Canonical engine responsibility | REST responsibility |
| --- | --- | --- |
| Catalogue | Supported profiles/actions, edition manifest, dependencies, scope and limits | Serialize the same catalogue; OpenAPI enums contain admitted values only. |
| Direct assessment | Strict typed supplied evidence; conditional result with provenance | Validate structure and map to engine-owned constructors; do not imply reader verification. |
| Datetime assessment | Derive evidence from admitted resources and explicit location/time/frame policy | Resolve validated request fields; invoke engine; preserve unavailable states. |
| Windows | Partition a bounded interval using every selected rule's transition dependencies and certificates | Enforce strict bounds and response contracts; return canonical cells and receipts. |

Proposed route families are `/v1/muhurta/vastu/{operation}`,
`/v1/muhurta/business/{operation}` and `/v1/muhurta/travel/{operation}`;
existing `/v1/muhurta/marriage/{operation}` gains admitted profile choices.
The actual operation spellings should remain `catalogue`, `direct`,
`datetime` and `windows`, as in marriage. Confirm router ownership before
adding paths; do not create a server-only parallel astrology implementation.

Strictness requirements apply equally to Python/facade and HTTP:

- Reject unknown fields, non-finite values, boolean-as-number coercion,
  malformed enums, duplicate bodies/roles and incompatible profile components.
- Require timezone-aware instants and explicit civil timezone semantics;
  distinguish civil dates from sunrise-owned dates, UTC/UT1/TT and sidereal
  frames. Cover DST gaps/folds and historical time assumptions.
- Validate direction conventions, source units, context combinations, birth
  evidence and allowed range/limit settings before expensive work.
- Bind supplied evidence to its epoch, location, source and policy; do not
  accept forged receipt fields as verification of reader-derived evidence.
- Use existing consistent HTTP validation/error mappings. Malformed requests
  fail validation; unavailable astronomy is a canonical result state; exhausted
  work budgets must not become partial results labelled complete or favorable.
- Bound catalogue/result cardinality and payload size. Error paths must
  preserve reader lifecycle and avoid leaking internal file/system details.
- Serialize immutable engine results, including findings, exceptions, coverage,
  manifests and search receipts; never recalculate a source rule in a serializer.

Curate new public names in `moira/vedic.py` and `moira/facade.py` according to
current export conventions. Add root exports only if the established surface
requires them. Regenerate API reference/OpenAPI-facing inventories and wiki
through their owning tools. Existing coarse activity guidance should gain
accurate scope/deprecation pointers to the new profiles; do not silently change
generic sampled-search behavior or claim it now certifies these elections.

## 10. P6 — integrated validation, performance and closure

### 10.1 Three independent evidence layers

1. **Source fixtures:** independently transcribed sets, ordinals, tables,
   variants and worked examples with edition/page/hash. Avoid deriving expected
   fixtures by importing the implementation tables being tested.
2. **Computational evidence:** exhaustive finite-domain arithmetic; exact
   rational boundary witnesses where applicable; event-bracketing and enclosure
   tests; independent reference calculations under the same declared frame.
3. **Transport and execution evidence:** direct/facade/HTTP result equivalence,
   OpenAPI contracts, actual serving-reader lifecycle, budget failures and real
   instant/window requests through each admitted family.

Numerical agreement with another program cannot establish source authority.
A printed source table cannot establish the correctness of an astronomical
event search. A successful serialization test cannot establish either.

### 10.2 Boundary and adversarial matrix

Every admitted profile needs rule-to-transition coverage: sunrise/weekday,
sunset where relevant, tithi/karana/yoga, 27/28-star and pada boundaries,
solar/lunar month edges, sign/Navamsa crossings, motion/nature/visibility or
history transitions actually used, and all derived clock/remedy edges.
Split at numerical uncertainty bands; retain unresolved bands visibly.
Use half-open ownership consistently except where the named source predicate
requires an explicit strict edge. A request-wide favourable sample is not a
proof of an interval without adverse subintervals.

Required hostile cases include cross-profile remedy injection, cross-request
memo pollution, mismatched natal/election frames, stale supplied evidence,
missing partner/resident/direction, impossible context combinations, inadequate
lookback, absent resources, polar events, boundary coincidence, root-budget
exhaustion, output overflow and failure during a borrowed-reader request.

### 10.3 Performance without weaker answers

Capture cold and warm timings, dependency counts, source reads, work counters,
memo hit/eviction counts and peak retained memory for representative supported
requests. Compare identical resources and semantic results. Establish measured
per-family operational limits before advertisement; no sub-second promise is
made. Existing marriage requests still take minutes on the accepted workload.

Demand-driven dependency selection and exact reuse are the first optimizations.
Any later acceleration must preserve source rules, numerical certificates,
tolerances, unavailable states and budget behavior. Reducing history or using
coarser time steps requires a separately justified contract change, not a
performance patch. Background-job/service orchestration is separate scope.

### 10.4 Final acceptance checklist

- P0 manifests close all required selected rules; any deferred tradition has
  a named scope/evidence gap and is absent from supported choices.
- P2–P5 each pass source, boundary, hostile-input, public export and real HTTP
  instant/window acceptance; a dry run is not a replacement for a completed
  expensive request.
- P1 preserves the accepted marriage behavior and both full real-resource
  acceptance cases. New failures are repaired rather than recorded as skips.
- Relevant public/native/oracle changes receive the repository's protected-zone
  declaration and targeted checks; do not broaden the native substrate by habit.
- Documentation, release identity, Hellenistic/REST inventories, website metadata
  checks and generated wiki are consistent; no stale generated inventory is
  dismissed as unrelated to publication.
- Admission standards, source manifests, execution receipts and the remaining-
  work register identify exactly which VED-011 profiles are complete and what
  remains. Counts change only when the corresponding selected feature closes.

Run the smallest relevant tests after each change, then the affected integration
slices. Use `.\.venv\Scripts\python.exe`, downloads disabled for engine tests,
strict known-issue expiry and existing resource discovery. Preserve source and
validation evidence outside the repository until the canonical fixture/receipt
package has been reviewed. The final publication sequence, if separately
requested, is generated wiki first and then the engine's exact wiki reference.

## 11. Execution checkpoint

The user authorized and the implementation followed the full sequence,
beginning with MC48 housing. The [execution receipt](../03_validation/PURPOSE_ELECTION_VALIDATION_2026-10-11.md)
owns actual commands, completed source/numerical/HTTP evidence, performance
measurements, compatibility hashes and remaining scope.

| Package | Execution state |
| --- | --- |
| P0 source manifests | Closed for every supported profile; D05 conflicting KP travel tables and D10 Raman remain explicitly outside admission. |
| P1 shared evidence | Implemented; exact three-response MC compatibility and bounded dependency/reuse checks pass. |
| P2 housing | Implemented across engine/facade/REST; real foundation and entry windows, polar and budget cases pass. |
| P3 commerce | Implemented across engine/facade/REST; actor-specific comparison and real purchase/opening windows pass. |
| P4 travel | Implemented across engine/facade/REST; KP components and the final ordinary-travel real instant/window pass. |
| P5 additional marriage | VV/KP implemented with distinct manifests, histories and remedies; final VV and KP real instant/direct/window HTTP acceptance passes. |
| P6 integrated acceptance | Complete; all real HTTP, regression, source/boundary, performance and documentation gates pass at the recorded scope. |

No commit, push, release or deployment is implied by this local implementation.
