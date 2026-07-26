# Hellenistic Engine Gate Roadmap

Date: 2026-07-25
Scope: `moira/` engine truth first; transport, product composition, and website
work only at their named later gates.

This is the current six-gate Hellenistic roadmap. It supersedes the phase
numbering in the older additive completion roadmap for current work. In
particular, “Phase 2” here means doctrine decisions, not the historical
“Bounds Expansion and Halb” phase.

## Gate Status

| Phase | Gate | Status | Boundary |
|---|---|---|---|
| 1 | False-output containment | Complete | Incorrect or unadmitted Hellenistic outputs fail closed; Decennial L3/L4 and Hermetic public surfaces remain quarantined. |
| 2 | Doctrine decisions | Complete | The disputed profection, Decennial, Halb/Hayz, ZR, lot, and Hermetic-catalog rules have explicit source or policy decisions. |
| 3 | Typed truth composition | Complete | Every admitted atomic family in the Phase 3 inventory now has a governing raw receipt or remains explicitly quarantined; compatibility labels and booleans are projections, not the source of truth. |
| 4 | Contract parity | Pending | Audit effective policy and provenance parity across exports, facade, serializers, REST models, and OpenAPI. Existing partial transport is not a parity receipt. |
| 5 | Unified Hellenistic profile | Pending | Compose a non-interpretive chart profile only from atomic admitted receipts. |
| 6 | Validation and documentation regeneration | Pending | Add independent source-owned goldens, regenerate inventories/matrices, archive stale completion claims, and only then update website documentation. |

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
named deep-subdivision candidates remain quarantined.

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

Engine receipt: `tests/fixtures/hellenistic_zr_valens_iv4.json`.

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
fixed-star assignments, so those accessors fail closed. Modern lookup, rising,
and night-hour geometry remain research-quarantined pending later gates.

Engine receipt: `moira/hermetic_decans.py`.
Standard: `wiki/02_standards/DECANS_BACKEND_STANDARD.md`.

## Phase 2 Exit Criteria

Phase 2 is closed only because:

1. every named doctrine conflict above has an explicit source or policy
   decision;
2. the engine no longer fabricates the disputed result;
3. focused tests and the ZR source-locked fixture cover the corrected behavior;
4. quarantined material remains unavailable through curated public surfaces;
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
| Hermetic decans and Decennial L3/L4 | These surfaces are quarantined rather than composition-ready. | Keep quarantined; Phase 3 does not reopen source admission. |

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
evaluated receipt. The L3/L4 quarantine is unchanged.

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
5. Hermetic decan geometry and Decennial L3/L4 remain quarantined;
6. the 18-file atomic gate passed all 907 collected tests under strict
   known-issues mode; Python compilation, documentation consistency, and
   `git diff --check` also passed.

This closure is engine truth composition only. The new Phase 3 names are
currently direct module surfaces; it does not claim root/classical/facade,
serializer, REST-model, OpenAPI, or website parity.

### Resting point for the next work session

Phase 4, Contract parity, is next:

1. inventory each effective Phase 3 policy and receipt across module exports,
   root exports, `moira.classical`, facade functions, `Moira` methods, and
   serializers;
2. align REST models and OpenAPI transport only after the engine-to-facade
   contract is explicit;
3. prove parity with adversarial round-trip tests rather than inferring it from
   existing partial transport;
4. keep the unified Hellenistic profile, validation/documentation
   regeneration, and website work at Phases 5 and 6.
