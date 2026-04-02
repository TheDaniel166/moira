# Contributing to Moira

Thank you for your interest in contributing to Moira.

Moira is not a general-purpose astrology toy, a convenience wrapper around legacy assumptions, or a repository where plausible-looking output is treated as sufficient. It is an astronomy-first engine built around computational integrity, transparent derivation, doctrinal clarity, and long-term architectural coherence.

Contributions are welcome. But they are evaluated by the same standards that govern the engine itself.

Moira is now a stable public project. That matters. Changes are not judged only by whether they run. They are judged by whether they preserve truth, clarity, and structural integrity.

## What Moira Is

Moira is built on a few governing principles.

### Astronomy first

Astronomical computation is not subordinate to convenience, habit, or inherited software tradition. The engine begins with astronomical truth and works outward from there.

### Transparency second

A result should not merely exist. It should be interrogable. Its derivation, assumptions, and validation basis should be traceable wherever practical.

### Doctrine must remain explicit

Where Moira enters astrological territory, it must do so honestly. Different systems, traditions, and laws are not to be collapsed into vague composite behavior. Distinctions matter here.

### Architecture is part of correctness

In Moira, correct output achieved through ontological confusion, boundary collapse, or leaky layering is not considered a clean contribution. Structure matters because structure preserves truth over time.

### Stability matters

Moira is a stable engine. Public behavior, conceptual contracts, and validated logic are not to be altered casually.

## Before You Start

If your proposed contribution is substantial, open an issue before writing code.

This is especially important for:

- new features
- API changes
- doctrinal additions or revisions
- architectural refactors
- performance rewrites
- validation strategy changes
- anything that changes established numerical output

Small documentation fixes, typo corrections, and narrow test improvements usually do not require prior discussion.

Opening an issue first is not bureaucracy. It is how we prevent wasted effort when a proposal is misaligned with the engine’s law, scope, or architecture.

## What Counts as a Strong Contribution

A strong contribution to Moira does more than solve a local problem.

It usually does most or all of the following:

- solves a clearly defined problem
- fits the engine’s existing architecture
- preserves conceptual boundaries
- makes assumptions explicit
- provides a validation basis
- includes focused tests
- avoids silent behavioral drift
- improves the engine without diluting its identity

In this repository, “the code works” is only the beginning of the case, not the end of it.

## Accepted Contribution Types

### Bug fixes

Bug fixes are welcome, especially when they are narrow, reproducible, and accompanied by tests.

A good bug fix should clearly state:

- what is wrong
- how to reproduce it
- what behavior is expected
- what behavior actually occurs
- whether the issue is astronomical, doctrinal, API-level, validation-level, or infrastructural

If a fix changes numerical output, say so directly.

### Documentation improvements

Documentation contributions are welcome when they improve precision, clarity, validation traceability, conceptual orientation, or correct usage of the engine.

Moira benefits from documentation that explains law, not just mechanics.

### Tests and validation enhancements

This is one of the highest-value forms of contribution.

If you add or revise tests, especially in astronomy or doctrinal domains, make the authority, oracle, or rationale explicit. A test suite grows stronger when it makes clear not only what is being asserted, but why that assertion is justified.

### New features

New features are welcome only when they belong inside Moira.

That means they should be:

- clearly within the engine’s scope
- architecturally clean
- justifiable by real use
- supportable by validation
- coherent with the astronomy-first foundation

A feature is less likely to be accepted if it is speculative, difficult to validate, designed around convenience instead of truth, or better suited to a host application layered above the engine.

## Moira-Specific Standards of Acceptance

### 1. Astronomical changes must have a defensible basis

If your contribution affects any of the following:

- time systems
- coordinate systems
- precession, nutation, obliquity, or transforms
- ephemeris handling
- derived astronomical quantities
- planet, star, or house-related computation
- eclipse, direction, or event timing logic

then it must be grounded in something stronger than intuition or tradition.

That grounding may include:

- published standards
- primary references
- reproducible comparisons
- validated datasets
- authoritative computational models
- explicit derivational law

If the change affects numerical truth, the basis for that change must be stated plainly.

### 2. Astrological doctrine must remain doctrinally honest

Moira does not accept doctrinal blur.

If your contribution touches astrological logic, explain:

- which doctrine, school, or law is being implemented
- whether that doctrine is mainstream, disputed, or niche
- what assumptions are introduced
- what is being modeled exactly
- how the behavior should be validated

Do not merge distinct doctrinal families into a single softened abstraction just because they appear superficially similar.

If two systems differ, that difference should usually remain visible in the implementation.

### 3. Ontological structure matters

This is one of the places where Moira is intentionally strict.

A contribution may be rejected even if the output appears correct, if the internal model is ontologically unsound.

Examples of structural problems include:

- treating relation classes as target classes without justification
- collapsing distinct concepts into one implementation for convenience
- introducing mixed layers that confuse engine and consumer concerns
- hiding doctrinal distinctions behind generic naming
- weakening conceptual boundaries that the engine currently preserves

Moira is not merely trying to compute. It is trying to compute with clean law.

### 4. Architectural integrity is mandatory

Please respect existing boundaries.

Do not introduce:

- UI leakage into engine logic
- host-application concerns into core computation
- broad refactors without a concrete problem
- new abstractions that do not earn their complexity
- convenience shortcuts that erode future maintainability or clarity
- hidden coupling between unrelated subsystems

Architecture in Moira is not ornamental. It is part of how the engine protects truth from drift.

### 5. Validation is expected

Non-trivial changes should come with tests.

This is especially true for changes affecting:

- numerical results
- public API behavior
- doctrinal interpretation
- parsing or normalization
- edge-case handling
- validation logic
- result classification

If a change is difficult to test, that usually means the shape of the change should be reconsidered.

### 6. Stable behavior should not drift silently

Moira is stable. That means established behavior should not shift without explicit acknowledgment.

If your change does any of the following, say so clearly:

- changes public API behavior
- changes numerical output
- changes doctrine
- changes validation rules
- changes interpretation of existing inputs
- changes default assumptions

Silence around behavioral change is one of the fastest ways to weaken trust in a computational engine.

## Pull Request Expectations

Please keep pull requests focused.

Do not combine unrelated concerns in a single PR. For example, avoid bundling:

- bug fix + style cleanup
- doctrinal revision + refactor
- new feature + packaging rewrite
- validation change + unrelated documentation sweep

A pull request should explain, plainly:

- what problem it solves
- why this approach was chosen
- whether public behavior changes
- whether numerical output changes
- whether doctrine changes
- what tests were added or updated
- what sources, laws, or references justify the change
- what part of Moira is affected

For Moira, a small precise PR is far more valuable than a sweeping one.

## Coding Expectations

Follow the existing spirit of the codebase unless there is a strong reason not to.

In general:

- prefer clarity over cleverness
- prefer explicit law over hidden magic
- keep modules coherent in purpose
- keep names conceptually honest
- do not add abstraction merely to appear elegant
- do not rewrite stable code casually
- do not introduce dependencies without strong justification

Complexity must earn its place.

Moira is not trying to look sophisticated. It is trying to remain correct.

## Backward Compatibility

Moira is a stable engine, and backward compatibility matters.

Breaking public API changes should be rare, clearly justified, and discussed before implementation. The same applies to any change that may alter established computational behavior in a way downstream consumers would experience.

## Contributions Likely to Be Rejected

The following are less likely to be accepted:

- large refactors without a concrete and demonstrated problem
- speculative features without a validation strategy
- convenience abstractions that weaken conceptual law
- doctrine-by-implication instead of doctrine-by-definition
- silent changes to established numerical results
- generic APIs that erase meaningful distinctions
- host/UI concerns pushed into the engine
- stylistic rewrites of already stable code
- ontologically confused implementations that happen to produce plausible output

A contribution can be technically functional and still not belong in Moira.

## Reporting Issues

If you open an issue, please be precise.

Helpful issue reports include:

- Moira version
- Python version
- operating system
- reproduction steps
- expected behavior
- actual behavior
- minimal example if relevant
- comparison data if the issue is numerical
- doctrinal source if the issue concerns astrological interpretation

The clearer the issue, the easier it is to evaluate whether the problem is computational, doctrinal, architectural, or environmental.

## Review Philosophy

Moira is maintained with a strong emphasis on correctness, traceability, and long-term coherence. Final acceptance decisions remain with the maintainer for that reason.

This is not a rejection of contribution. It is the practical consequence of stewarding an engine whose value depends on trust.

Review may be exacting. That is intentional.

A contribution may be declined not because it lacks effort, but because it does not fit the engine’s standards, ontology, architecture, or validation law.

## Final Note

If you are here because you care about building something precise, honest, and durable, that is deeply appreciated.

Moira benefits most from contributors who understand that in a project like this, rigor is not hostility and standards are not gatekeeping. They are how the engine remains worthy of trust.
