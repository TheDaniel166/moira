# Hellenistic Engine Gate Roadmap

Date: 2026-07-27
Scope: `moira/` engine truth first; transport, product composition, and website
work only at their named later gates.

This is the current six-gate Hellenistic roadmap. It supersedes the phase
numbering in the older additive completion roadmap for current work. In
particular, “Phase 2” here means doctrine decisions, not the historical
“Bounds Expansion and Halb” phase.

## Reading Rule: Closed Exclusions Are Not Backlog

All six engine gates are complete. Hermetic star attribution/geometry,
Decennial L3/L4, and Valens distribution interpretation are closed exclusions
from that completed contract. They must not be copied into a gap list, version
plan, or release blocker. The Hermetic catalog may remain available by direct
research import, but no Hermetic product transport is admitted.

The only post-6.0 engine delta recorded here is the dated monthly-profection
contract below. Any future proposal to expand a closed exclusion is a new
research-and-admission project, not unfinished Hellenistic completion work.

## Gate Status

| Phase | Gate | Status | Boundary |
|---|---|---|---|
| 1 | False-output containment | Complete | Incorrect or unadmitted Hellenistic outputs fail closed; Decennial L3/L4 and Hermetic public surfaces are closed exclusions. |
| 2 | Doctrine decisions | Complete | The disputed profection, Decennial, Halb/Hayz, ZR, lot, and Hermetic-catalog rules have explicit source or policy decisions. |
| 3 | Typed truth composition | Complete | Every admitted atomic family has a governing raw receipt; excluded families are structurally absent. Compatibility labels and booleans are projections, not the source of truth. |
| 4 | Contract parity | Complete | Phase 3 policy and raw receipts now have identity-preserving engine exports, full facade forwarding, explicit serializers, typed REST models, and OpenAPI schemas. |
| 5 | Unified Hellenistic profile | Complete | `HellenisticChartProfile` composes a score-free chart profile from exact admitted atomic receipts and names every excluded branch. |
| 6 | Validation and documentation regeneration | Complete | Independent source-owned goldens, generated capability/API inventories, canonical validation docs, and archived historical claims now form the engine gate. Website implementation remains separate. |

## Phase 2 Closure Receipt

### Profection anniversary semantics

Annual profection schedules use completed civil anniversaries in the natal
timezone. February 29 births require an explicit February 28 or March 1 policy.
Elapsed fractional Julian years are not used as civil age.

### Decennial projection semantics

Decennials preserves two coordinates instead of collapsing them:

- a 30-day-month / 360-day-year distribution coordinate
- an elapsed-Julian-day projection from `sequence_origin_jd`

Projected JDs are not represented as civil-month anniversaries. L3/L4 and both
named deep-subdivision candidates are outside the closed admitted contract.

### Halb and Hayz

Halb uses the admitted al-Qabisi/Bonatti sect-relative hemisphere rule. Hayz
adds the planet's own sign gender. Mars is feminine; Mercury is neutral and
requires explicit sect-phase truth rather than a fabricated default.

### Zodiacal Releasing

Valens, *Anthologies* IV.4 governs two source fixtures:

- when Spirit and Fortune are in the same sign, Spirit's activity sequence
  begins in the following sign
- a long-sign subordinate sequence transfers to the opposite sign at the exact
  211-month circuit boundary

The Gemini fixture reaches Sagittarius after 211 months, remains there for 12
months, and uses the final 17 months in Capricorn. The source prose and
explanatory note govern; the inconsistent intervening numerical table does not.

Engine receipt: `tests/golden/hellenistic_zr_valens_iv4.json`.

### Conflicted lots

`PartDefinition` now carries an explicit projector and directed-versus-shortest
arc policy. Computation truth preserves both.

- `Theft (Valens)` projects Mercury→Mars from Saturn by day and reverses the
  operands at night.
- `Basis (Valens)` projects the shorter Fortune/Spirit interval from the
  Ascendant.
- `Debt (Valens)` and `Debt (Abu Mashar via al-Biruni)` remain distinct
  source-named formulas.
- The al-Bīrūnī glyph/continuation-mark conflicts for Illness and the two
  Valens marriage lots are resolved without inventing reversals.
- `Knowledge, True or False (Abu Mashar via al-Biruni)` is the source-specific
  Jupiter→Moon formula without night reversal.

Research receipt:
`wiki/05_research/lots/LOTS_SOURCE_VERIFICATION.md`.

### Hermetic catalog reconstruction

The 36-name catalog has been reconstructed from Wilhelm Gundel,
*Dekane und Dekansternbilder* (1936), pp. 379-383, “Die lateinische
Dekanliste des Hermes Trismegistos,” transcribing British Library Harley
MS 3731, ff. 1r-50r.

The engine preserves each entry's sign, ordinal, name, planetary face, edition
page, and source identifier. The identified edition does not supply the former
fixed-star assignments, so those accessors fail closed. The full text supports
Aries-starting 10-degree segmentation. The tropical-frame and rising
projections remain direct-import research only and are closed product
exclusions. The unsupported night-hour experiment has been removed from
executable code.

Engine receipt: `moira/hermetic_decans.py`.
Standard: `wiki/02_standards/DECANS_BACKEND_STANDARD.md`.

## Phase 2 Exit Criteria

Phase 2 is closed only because:

1. every named doctrine conflict above has an explicit source or policy
   decision;
2. the engine no longer fabricates the disputed result;
3. focused tests and the ZR source-locked fixture cover the corrected behavior;
4. closed-exclusion material remains unavailable through curated public
   surfaces;
5. no Phase 3 composition, Phase 4 parity claim, Phase 5 profile, or website
   admission is implied.

## Phase 3 Start Receipt

The first Phase 3 slice establishes the composition contract without claiming
the gate complete:

- essential dignity truth preserves independent domicile, exaltation,
  triplicity, Egyptian-bound, Chaldean-face, detriment, fall, and peregrine
  components; the scalar label is only a compatibility projection;
- `DignityHorizonFrame` makes chart sect and body hemisphere independent of
  selected house-system cusp numbering;
- exact Ascendant/Descendant placement and exact Mercury/Sun conjunction no
  longer become fabricated booleans;
- lot dependencies now include the projector alongside both operands and carry
  an explicit completeness receipt;
- `evaluate_lots` returns typed receipts for unresolved catalogue entries
  instead of silently erasing them;
- lot dependency composition is explicitly separated from astrological
  condition, which remains `not_evaluable` without admitted doctrine.

At this start checkpoint, Phase 3 remained open for the collapsed/default-
bearing Hellenistic families and a final atomic-truth gate audit. Phase 4
parity, Phase 5 profile composition, and website work were not implied by this
start receipt.

### Phase 3 atomic-vessel inventory

The 2026-07-26 engine pass found the following remaining composition work.
This is an implementation inventory, not a capability or correctness claim:

| Atomic family | Current collapse or default | Phase 3 disposition |
|---|---|---|
| Oriental/Occidental phase | The compatibility helper returned `str | None`, exact conjunction and opposition were forced into `oriental`, and policy suppression erased the available geometry. | Closed in the second Phase 3 slice with `PlanetarySolarPhaseTruth`; boundaries are typed `not_evaluable`, and only evaluated truth may assemble a condition or score. |
| Solar proximity | `SolarConditionTruth.present=False` conflated an evaluated clear band, a non-applicable Sun, a default-suppressed Moon, and policy-suppressed conditions. | Closed in the third Phase 3 slice with exclusive `SolarProximityTruth`; raw geometry is preserved separately from policy assembly, and the Sun fails closed as non-applicable. |
| Besieging | `tuple | None` conflated evaluated absence, incomplete chart dependencies, same-degree neighbour ambiguity, and missing chart context. | Closed in the third Phase 3 slice with `BesiegingDependencyCompletenessTruth` and `BesiegingTruth`; incomplete or ambiguous geometry cannot score. |
| Profection activation | `activated_planets=[]` means either no conjunctions or no natal positions were supplied. | Closed in the fourth Phase 3 slice with `ProfectionActivationTruth`; absent dependencies are typed `not_evaluable`, while an explicit empty mapping and evaluated absence remain evaluated results. |
| Decennial sequence | The final ordered tuple carries no atomic starting/ordering receipt, and equal non-sect-light longitudes fall through to private planet order. | Closed in the fourth Phase 3 slice with `DecennialSequenceAssemblyTruth`; every Classic 7 arc is preserved and non-sect-light longitude ties fail closed instead of using private order. |
| ZR Fortune angularity | Missing Fortune leaves `angularity_class=None` but projects `is_peak_period=False`, collapsing “not evaluable” into “not peak.” | Closed in the fourth Phase 3 slice with `ZRFortuneAngularityTruth`; raw missing-Fortune peak truth is `None`, while the legacy field remains a compatibility `False`. |
| Aspect direction and overcoming | Direction uses enum-or-`None` applicability and overcoming uses a scalar boolean without a shared typed Hellenistic superiority receipt. | Closed in the fourth Phase 3 slice with `HellenisticSuperiorityTruth`; typed direction applicability and winner-or-neither overcoming share one ordered-pair receipt and introduce no score. |
| Hermetic decans and Decennial L3/L4 | These surfaces are closed exclusions rather than composition-ready. | Keep excluded; Phase 3 does not reopen source admission. |

Triplicity assignment, admitted bounds, ordinary decanate position, essential
dignity components, horizon/sect/Mercury phase, and lot dependency evaluation
already expose sufficient atomic witnesses for this gate's current inventory.
Their legacy scalar helpers remain compatibility projections and must not
become the source of later composition.

### Phase 3 second-slice receipt

`planetary_solar_phase_truth()` now governs the five admitted non-luminary
planetary phase classifications. Its assembly doctrine is:

1. preserve the forward longitude arc from the planet to the Sun;
2. return typed `not_evaluable` at exact conjunction, exact opposition, or for
   a body outside the admitted set;
3. preserve evaluated phase truth even when policy suppresses the condition;
4. assemble an Oriental/Occidental label and score only from evaluated truth.

`oriental_occidental()` remains a compatibility projection. It returns
`None` for non-evaluable truth rather than fabricating one side of a boundary.
At that checkpoint, Phase 3 remained in progress.

### Phase 3 third-slice receipt

`solar_proximity_truth()` now preserves one exclusive Cazimi, Combust, Under
Sunbeams, or Clear band before accidental policy assembly. The Sun is typed
`not_evaluable`; Moon geometry remains available even when the default
luminary policy suppresses its condition. Policy fall-through remains a
compatibility behavior and cannot rewrite the raw band.

`besieging_truth()` now requires complete classical chart dependencies and
preserves the target, nearest backward and forward neighbours, directed
distances, and configured orb. Missing bodies, unresolved target identity,
same-degree neighbours, directional ties, and side-boundary ambiguity fail
closed. Only an evaluated Mars/Saturn enclosure within orb can assemble the
legacy condition and score. `is_besieged()` remains a flattened compatibility
projection.

The engine vessels, public dignity exports, chart assembly, compatibility
helpers, and existing REST serialization path are regression-covered for this
slice. That serialization evidence is not the Phase 4 parity receipt. Phase 3
remained in progress at that checkpoint.

### Phase 3 fourth-slice receipt

`profection_activation_truth()` now preserves each supplied body's normalized
longitude, minimum distance from the profected Ascendant, activation orb, and
activation boolean. Missing natal positions are typed `not_evaluable`;
explicitly supplied empty dependencies and evaluated charts with no activated
bodies remain distinct evaluated receipts. `activated_planets` is a
compatibility projection.

`decennial_sequence_truth()` preserves the Classic 7 dependency geometry from
the sect light and makes the final ordering inspectable. The sect light remains
the starting lord; equal non-sect-light longitudes are typed
`not_evaluable`, and generation fails closed instead of falling through to a
private planet order. Every generated L1/L2 period preserves the same
evaluated receipt. The closed L1/L2 depth boundary is unchanged.

`zr_fortune_angularity_truth()` preserves Fortune dependency completeness,
inclusive place, angularity class, and raw peak truth. Missing Fortune carries
raw `is_peak_period=None`; the legacy period field remains `False` only as a
compatibility projection.

`hellenistic_superiority_truth()` composes two independent components for one
ordered body pair. Direction preserves sinister/dexter applicability and typed
boundary reasons. Overcoming preserves both inclusive sign places and an
evaluated `body1`, `body2`, or `neither` relation. No additive dignity or
superiority score was introduced.

## Phase 3 Closure Receipt

Phase 3 is complete because:

1. every admitted atomic family in the recorded inventory now exposes a
   governing component receipt;
2. missing dependencies and boundary ambiguity are typed `not_evaluable`
   rather than collapsed into false, empty, or a private ordering default;
3. compatibility strings, lists, and booleans are derived from raw truth and
   cannot contradict it in admitted engine output;
4. synthetic scoring remains outside the Hellenistic product contract;
5. Hermetic decan geometry and Decennial L3/L4 remain closed exclusions;
6. the 18-file atomic gate passed all 907 collected tests under strict
   known-issues mode; Python compilation, documentation consistency, and
   `git diff --check` also passed.

At the Phase 3 checkpoint this closure covered engine truth composition only:
the new names were direct module surfaces and did not yet claim
root/classical/facade, serializer, REST-model, OpenAPI, or website parity.
Phase 4 below closes the first five of those contract gaps; website parity
remains outside this engine roadmap gate.

## Phase 4 Closure Receipt

Phase 4 closes the contract gap without composing a chart-wide Hellenistic
profile:

1. the 44 newly curated Phase 3 symbols resolve to the same owning-module
   objects through `moira`, `moira.classical`, and `moira.facade`;
2. `Moira` exposes the admitted raw helpers, `evaluate_lots()`, and complete
   aspect/profection policy forwarding instead of narrowing caller policy;
3. REST dignity, lot, profection, Decennial, ZR, and whole-sign aspect
   responses use explicit typed receipt models rather than
   `dict[str, Any]`;
4. `/v1/lots/chart` transports the full `LotsEvaluation`, including
   `not_evaluable` entries and aggregate counts, instead of silently dropping
   unresolved catalogue entries;
5. profection activation orb, Decennial sequence assembly, ZR Fortune
   angularity, and Hellenistic superiority survive engine-to-JSON round trips;
6. OpenAPI points those fields at concrete receipt schemas, and adversarial
   tests freeze both compatibility projections and the raw source of truth;
7. Decennial L3/L4 and Hermetic tropical-frame/rising projections remain
   closed exclusions; the unsupported Hermetic night-hour experiment is absent.

This receipt does not admit Firdaria into a Hellenistic profile, reinterpret a
typed result, add a synthetic score, regenerate the Phase 6 capability matrix,
or authorize website work.

## Phase 5 Closure Receipt

Phase 5 is complete through the new `moira.hellenistic` composition boundary:

1. `hellenistic_chart_profile()` requires all seven classical planets, one
   finite speed per planet, exact zodiac-boundary Whole Sign cusps, the actual
   Ascendant and Midheaven, and timezone-aware natal/current datetimes;
2. exact Ascendant/Midheaven horizon truth is the single sect source used by
   planetary receipts, triplicity, lots, Decennials, and Zodiacal Releasing;
3. the profile includes score-free planetary component truth, Whole Sign
   aspects and superiority, Fortune/Spirit/Valens Eros/Valens Necessity,
   annual profection activation, current Decennial L1/L2 periods, and current
   Zodiacal Releasing periods;
4. atomic `not_evaluable` results remain visible in their owning receipt and
   in profile provenance; the composer does not replace them with false,
   empty, or inferred defaults;
5. `HellenisticProfilePolicy` freezes Classic-7 dignity doctrine, Dorothean
   triplicity, skip-and-report lot failure behavior, and the admitted
   Decennial L1/L2 policy while preserving admitted bounds, ZR, profection,
   and component selectors; Decennial L3/L4 remains unselectable;
6. `HellenisticProfileProvenance` records method, lineage, sources, input
   semantics, the chart position frame, calendar/timescale, engine and kernel
   identity/coverage when available, warnings, and non-evaluable receipts;
7. the exact engine objects are exported through `moira`,
   `moira.classical`, and `moira.facade`; `Moira.hellenistic_chart_profile()`
   derives a no-fallback Whole Sign chart profile without recomputing doctrine;
8. `POST /v1/hellenistic/chart-profile` uses explicit request, response,
   serializer, service, route, and OpenAPI types. Its reachable response graph
   contains no score field and exposes no selectable Decennial deep method.

The implementation pass also closed four composition hazards found during the
gate:

- Lots now accept explicit Ascendant and Midheaven longitudes. Whole Sign cusp
  1 and cusp 10 remain house-sign boundaries rather than silently replacing
  the actual angles. Legacy raw callers that omit the angles retain a labelled
  compatibility fallback.
- Whole Sign geometry validation requires cusp 1 to be the exact zodiac-sign
  boundary containing the Ascendant, so equal-house geometry cannot
  masquerade as a Hellenistic Whole Sign input.
- The chart-backed REST service uses the apparent-geocentric,
  true-ecliptic-of-date planetary position/rate product and applies observer
  coordinates independently to the Whole Sign angles. The composer no longer
  infers or mislabels a planetary frame from observer coordinates alone.
- Active Zodiacal Releasing lookup uses half-open period ownership and returns
  typed `not_evaluable` outside the generated circuit. It never reuses the
  final expired period as current truth.

The profile explicitly excludes Firdaria, medieval almutens, later electional
rules, unscoped primary directions, Decennial L3/L4, Hermetic-decan geometry,
and Valens distribution interpretation. It contains no chart-wide score,
ranking, recommendation, or interpretive narrative.

Validation on 2026-07-26 passed the 950-test Hellenistic dependency and
transport gate under strict known-issues mode, Python compilation, REST
inventory synchronization, documentation consistency, and `git diff --check`.
The literal configured repository suite exceeded a ten-minute local command
window without a terminal result. A bounded release/governance follow-up
passed 80 tests and reproduced only the pre-existing `_FamilyCatalog`
docstring violation in unchanged `moira/asteroid_families.py`; that unrelated
baseline issue is not part of the Phase 5 changeset.

## Phase 6 Closure Receipt

Phase 6 is complete at the engine and transport documentation boundary:

1. `tests/golden/hellenistic_source_tables.json` is a hand-authored,
   runtime-independent corpus for the full Dorothean triplicity table,
   planetary joys, all four admitted bounds doctrines, the ordinary 36-face
   cycle, the four unified-profile lots, and Decennial L1/L2 source arithmetic;
2. the Valens IV.4 same-sign start-shift and 211-month circuit fixture now
   lives under `tests/golden/`, records its source ownership explicitly, and is
   not generated from engine output;
3. `tests/unit/test_hellenistic_source_goldens.py` checks every source table,
   every bounds segment start and midpoint, all 36 faces, concrete day/night
   lot outputs, and Decennial L1/L2 arithmetic;
4. `scripts/generate_hellenistic_inventory.py` verifies runtime anchors,
   curated export identities, registered OpenAPI operations, request/response
   schemas, and prohibited public paths;
5. the generated capability matrix distinguishes admitted, qualified,
   supporting, research-only, closed-exclusion, non-Hellenistic, and
   out-of-contract surfaces;
6. the generated API inventory records 49 Hellenistic, supporting, or
   explicitly adjacent operations from the 435-operation application and
   confirms zero Hermetic-geometry, Triacontaeteris, or Decennial L3/L4 paths;
7. the former additive roadmap and session tracker are archived behind stable
   link stubs instead of being maintained as current capability claims;
8. the astrology validation report, backend standards, Python API reference,
   REST reference, bounds validation note, and wiki home now point readers to
   the source audit and generated runtime artifacts.

The source audit preserves the hard qualifications: ordinary faces currently
use a later Agrippa witness; joy houses use a modern synthesis with identified
ancient locations; civil profection projection and proximity/enclosure
thresholds are policies; Halb/Hayz is medieval; only four profile lots are
source-goldened; Hermetic geometry, Decennial L3/L4, Triacontaeteris, and
interpretation remain outside the completed contract.

Validation on 2026-07-26 passed:

- 1,060 focused Hellenistic engine, composition, export, serializer, REST, and
  OpenAPI tests under `MOIRA_TEST_MODE=1` and
  `MOIRA_STRICT_KNOWN_ISSUES=1`;
- fresh-versus-committed Hellenistic inventory generation;
- REST API reference synchronization;
- documentation consistency;
- Python compilation for the new generator and tests;
- `git diff --check`.

This closes the six engine gates. It does not update or publish website
documentation, deploy a server, or admit interpretive Hellenistic product
claims. Any website implementation is a separate release scope built from
these engine-owned artifacts.

## 6.0.0 Release Closeout

The post-gate release hardening pass on 2026-07-26:

1. removed the unsupported Hermetic night-hour implementation and all dormant
   Hermetic transport models, services, serializers, and router definitions;
2. retained the source catalog and qualified geometry only inside the
   explicitly research-only direct module;
3. added strict Hellenistic source-golden, generated-inventory,
   contract-parity, profile, server, and OpenAPI gates to release CI;
4. passed all 944 collected focused Hellenistic engine/transport tests;
5. passed all 11,703 collected deterministic non-network repository tests,
   with 13 declared optional-resource/oracle skips and no failures;
6. passed release identity, documentation consistency, inventory generation,
   REST-reference synchronization, wiki synchronization, workflow parsing,
   Python compilation, and `git diff --check`; and
7. froze the breaking curated-import removals and typed migration guidance in
   the 6.0.0 release and compatibility notes.

This closeout does not admit Hermetic star attribution or geometry, Decennial
L3/L4, Triacontaeteris, Valens distribution interpretation, synthetic scoring,
or website product composition. Those exclusions are not unfinished engine
work.

## Post-6.0 Source Checkpoint: Dated Monthly Profections

The website Phase 3 continuity audit exposed one contract gap after the 6.0.0
engine gates: Moira supplied the ordered twelve monthly lords but no
authoritative dated product intervals.

The source checkpoint now closes that implementation gap:

1. `profection_chronology()` resolves exact consecutive civil anniversaries in
   an explicit IANA timezone and emits twelve contiguous half-open intervals;
2. `MonthlyProfectionIntervalPolicy` freezes the sole admitted projection as
   `equal_twelfths_of_civil_anniversary_year`;
3. `ProfectionChronologyMethod` labels the result
   `computational_projection`, explicitly excluding any claim that it is
   Valens IV.28's separate day-Sun/night-Moon distance method;
4. explicit IANA resolution uses the standard-library `zoneinfo` interface,
   fails closed if the host lacks the requested entry, and records its source
   without claiming an unavailable database version;
5. invalid IANA keys and civil anniversaries falling in DST gaps fail closed,
   while repeated local times require an explicit earlier/later occurrence
   policy that is preserved in the receipt;
6. `ProfectionResult`, root/classical/facade exports, `Moira`, serializers,
   REST models, the unified Hellenistic profile, and OpenAPI preserve the same
   effective policy and exact boundaries; and
7. vessel, unit, parity, route, and OpenAPI tests cover sign-sequence
   continuity, equal-duration policy, UTC/Julian agreement, active-boundary
   ownership, leap policy, DST, timezone transport, and strict schemas.

Doctrine:
`wiki/01_doctrines/timelords/monthly_profection_chronology_doctrine.md`.

This is a source checkpoint, not a publication claim. The hosted Phase 3 gate
closes only after a new Moira release containing this contract is built,
published, installed in staging, promoted as the exact tested artifact, and
verified through the live website timeline. The immutable `v6.0.0`
documentation bundle must not be regenerated from this post-release source;
the chronology contract requires a new release identity.
