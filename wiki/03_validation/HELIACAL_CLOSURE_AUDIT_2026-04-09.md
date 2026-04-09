# Heliacal Closure Audit (2026-04-09)

Purpose:
- isolate the heliacal and generalized visibility frontier into its own audit
- determine what is already covered by Moira's current heliacal subsystem
- distinguish remaining validation debt from true missing capability
- use the newly available Swiss HTML as a section-level checklist only

Primary inputs:
- `moira/heliacal.py`
- `wiki/05_research/heliacal_visibility/heliacal_visibility_implementation_roadmap.md`
- `wiki/03_validation/VALIDATION_ASTRONOMY.md`
- local Swiss HTML: `C:\Users\nilad\Downloads\swisseph documentation.html`

Non-goal:
- this document does not ask Moira to copy Swiss heliacal flags or formulas
- this document does not lower Moira's heliacal subsystem into Swiss API shape

## 1. Swiss Heliacal Section Inventory

The relevant Swiss HTML section is:

- `5.1. Heliacal Events of the Moon, Planets and Stars`
- `5.1.1. Introduction`
- `5.1.2. Aspect determining visibility`
- `5.1.3. Functions to determine the heliacal events`
- `5.1.4. Future developments`
- `5.1.5. References`

The adjacent Swiss section is also relevant:

- `5.2. Eclipses, occultations, risings, settings, and other planetary phenomena`

For Moira, the heliacal closure question is therefore not:
- "do we have Swiss flag parity?"

It is:
- "do we already cover the event taxonomy, visibility doctrine, and search surfaces implied by that family?"

## 2. Current Moira Reality

`moira.heliacal` is not a stub.

It is already a real subsystem with:
- typed heliacal event taxonomy
- generalized visibility target taxonomy
- observer environment policy
- typed visibility doctrine
- search policy
- planetary heliacal and acronychal helpers
- generalized visibility event search for planets, stars, and Moon
- Yallop lunar crescent validation
- admitted Krisciunas & Schaefer 1991 moonlight model

This means the heliacal family is not primarily blocked by missing API surface.

It is primarily blocked by:
- breadth of validation
- closure of a few remaining environment/criterion families
- honesty of public claims

## 3. What Swiss 5.1 Implies, Mapped to Moira

### 3.1 Moon, planets, and stars

Swiss family implication:
- the heliacal subsystem should not be planet-only

Moira status:
- covered

Current Moira surfaces:
- `VisibilityTargetKind.PLANET`
- `VisibilityTargetKind.STAR`
- `VisibilityTargetKind.MOON`
- `visibility_assessment(...)`
- `visibility_event(...)`

Conclusion:
- Moira already satisfies the broad target-family requirement.

### 3.2 Event taxonomy

Swiss family implication:
- heliacal event semantics must distinguish more than one kind of event

Moira status:
- covered

Current Moira surfaces:
- `HeliacalEventKind.HELIACAL_RISING`
- `HeliacalEventKind.HELIACAL_SETTING`
- `HeliacalEventKind.ACRONYCHAL_RISING`
- `HeliacalEventKind.ACRONYCHAL_SETTING`
- `HeliacalEventKind.COSMIC_RISING`
- `HeliacalEventKind.COSMIC_SETTING`

Conclusion:
- Moira already has a typed and exhaustive event-family vocabulary.
- This is materially stronger than Swiss integer constants.

### 3.3 Aspect determining visibility

Swiss family implication:
- visibility is not a pure event-name problem; it depends on an explicit criterion

Moira status:
- covered in core shape, partial in closure

Current Moira surfaces:
- `VisibilityCriterionFamily`
- `VisibilityPolicy`
- `ObserverVisibilityEnvironment`
- `visual_limiting_magnitude(...)`
- moonlight-aware visibility policy via `MoonlightPolicy`

Conclusion:
- Moira already has an explicit visibility-doctrine layer.
- The open problem is not absence of doctrine surfaces.
- The open problem is whether the admitted criterion families are sufficiently validated to justify stronger claims.

### 3.4 Functions to determine heliacal events

Swiss family implication:
- the engine should expose both direct event helpers and a generalized event search surface

Moira status:
- covered

Current Moira surfaces:
- `planet_heliacal_rising(...)`
- `planet_heliacal_setting(...)`
- `planet_acronychal_rising(...)`
- `planet_acronychal_setting(...)`
- `visibility_event(...)`

Conclusion:
- Moira already covers both narrow convenience helpers and generalized event search.

### 3.5 Future developments

Swiss family implication:
- this family naturally has deferred extensions and search-model choices

Moira status:
- active frontier

Current deferred areas already named in `moira/heliacal.py`:
- broader stellar heliacal event batch validation corpus
- real ephemeris integration corpus for moonlight-aware visibility
- summit-grade generalized visibility corpus across criterion families
- terrain and horizon-profile integration

Conclusion:
- this is the true closure frontier.
- It is mostly validation and environment realism, not basic subsystem invention.

## 4. Current Validation State

From `wiki/03_validation/VALIDATION_ASTRONOMY.md` and `moira/heliacal.py`:

Admitted validation already present:
- generalized heliacal / visibility surfaces are validated in an implemented slice
- published modern planetary apparition windows are cited as part of the validation basis
- Censorinus 139 AD Sirius slice is cited as a delegated stellar anchor
- Yallop 1997 lunar class law is enforced
- Yallop corpus result in `moira/heliacal.py`: `295/295` within `±0.05` q-value

This means the subsystem has real validation already.

But the current validation basis is still uneven across target families:

- Moon:
  strong for lunar crescent class law through Yallop
- Planets:
  some admitted validation basis exists, but the public validation story is not yet collected into one sharp heliacal corpus statement
- Stars:
  the Sirius/Sothic anchor exists, but broad stellar heliacal validation is still thin
- Moonlight-aware visibility:
  formula-unit validation exists, but live-ephemeris integration validation is still deferred

## 5. Real Gaps

### 5.1 Validation breadth gap

Status:
- real

What is missing:
- a clearer unified heliacal validation matrix covering Moon, planets, and stars as separate target classes
- a broader stellar corpus beyond the Sirius anchor
- explicit moonlight-on live-ephemeris validation cases

Why it matters:
- without this, the subsystem may be stronger than Swiss in design but weaker than it sounds in publicly stated breadth

### 5.2 Criterion-family closure gap

Status:
- moderate

What is missing:
- stronger evidence that the admitted `VisibilityCriterionFamily` choices are sufficient for the actual public claims Moira wants to make

Why it matters:
- if Moira claims "full generalized visibility" too broadly, the criterion-family closure is not yet proven across all use cases

### 5.3 Environment realism gap

Status:
- real but secondary

What is missing:
- terrain or horizon-profile integration

Why it matters:
- for actual first/last visibility, local horizon obstruction can dominate the event time
- this is not a core taxonomy gap, but it is a realism and product-semantics gap

### 5.4 Public-claim honesty gap

Status:
- immediate documentation discipline issue

What is missing:
- a compact, explicit statement of what the subsystem presently validates strongly, what it validates only in slice form, and what remains provisional

Why it matters:
- the subsystem is already substantial
- the main risk now is overstating closure rather than understating capability

## 6. False Gaps

These should not drive work:

- Swiss heliacal flag parity
- Swiss integer option matrices
- Swiss-shaped function count equivalence
- Swiss compatibility constants for optical or visibility modes

Moira already has the correct higher-order replacement:
- typed policy objects
- typed event taxonomy
- separated environment, doctrine, and search layers

## 7. Closure Judgment

Heliacal is best described as:
- implemented subsystem
- partially closed validation program

It is not best described as:
- missing feature family
- parity backlog
- early-stage design sketch

This matters because the next step should not be:
- "implement heliacal"

The next step should be:
- "close the validation and claim boundary for the heliacal subsystem already in hand"

## 8. Recommended Next Actions

### Action A: write a heliacal validation matrix

Scope:
- one source document

Contents:
- target classes: Moon, planets, stars
- criterion families
- current oracle or published basis for each
- tested corpus size
- enforced tolerances
- claim level: strong / slice / provisional

Reason:
- this is the cleanest way to separate strong evidence from aspirational breadth

### Action B: isolate the stellar heliacal corpus problem

Scope:
- one source audit or research note

Question:
- what authoritative modern or historical stellar heliacal corpora are actually suitable as an oracle?

Reason:
- this is the largest honest weakness in the current closure story

### Action C: define moonlight integration validation cases

Scope:
- one source audit note or test-plan document

Question:
- which real observer/body/date cases should be used to validate K&S moonlight under live ephemeris conditions?

Reason:
- the formula layer is admitted, but the end-to-end event effect still needs a better proof path

### Action D: defer terrain integration until after validation closure

Reason:
- terrain realism is valuable, but it is not the highest-leverage next move
- validation closure on the existing admitted surfaces comes first

## 9. Final Assessment

The Swiss HTML does not reveal that Moira lacks a heliacal subsystem.

It reveals that Moira already has one, and that the remaining work is mostly:
- stronger validation breadth
- sharper claim discipline
- a few realism extensions

That is a better position than the earlier broad Swiss-gap framing suggested.
