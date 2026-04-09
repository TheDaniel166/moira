# Production Readiness Roadmap

Status: active release-hardening roadmap

Purpose
-------
This document defines the remaining work required to move Moira from
production-capable engine state to a disciplined release candidate.

This is not a feature roadmap.
It is a release-integrity roadmap.

Moira has already undergone major hardening in:
- temporal semantics
- house-policy propagation
- canonical vessel immutability
- transit and occultation semantic honesty
- progression and sidereal solver correctness
- Hermetic and classical decan engine integrity
- API-reference and standards alignment

What remains is the final release layer:
- compatibility accounting
- documentation closure
- broader acceptance validation
- specialist-module review completion
- release-candidate gating

---

## 1. Release Contract

Goal: state clearly what changed and what callers must now expect.

Required outputs:
- release notes
- compatibility notes
- versioning decision

Behavior changes that must be recorded explicitly:
- naïve `datetime` inputs now raise instead of being treated as UTC
- several canonical result vessels are now frozen or tuple-backed
- invalid policy or invariant violations now raise concrete runtime errors
- `classify_house_system()` now raises on unknown codes
- Hermetic `decan_at()` no longer accepts `reader`
- Hermetic decan night-hour computation now rejects invalid night geometry

Decision points:
- patch release if treated as internal hardening only
- minor release if callers are expected to adapt in small ways
- major release if strict semantic-versioning honesty is desired

Exit criteria:
- release note drafted
- compatibility section reviewed
- version bump policy chosen

---

## 2. Documentation Closure

Goal: ensure that repository doctrine and user-facing docs tell the truth about the executable engine.

Priority sweep targets:
- `wiki/`
- `moira.wiki/`
- any mirrored API reference pages
- service-layer guides
- standards pages that still describe pre-hardening behavior

Focus areas:
- time semantics
- house-policy semantics
- vessel immutability
- public import paths
- removed or changed parameters

Known dangerous stale claims to grep for:
- `treated as UTC`
- `AssertionError`
- stale mutable vessel descriptions
- removed parameters such as `decan_at(..., reader=...)`

Recommended output:
- one short `API stability and behavioral changes` page linked from the release notes

Exit criteria:
- all known stale contract claims removed from primary docs
- root-public versus module-public paths are clearly distinguished

---

## 3. Acceptance Matrix

Goal: move from targeted confidence to release confidence.

Keep as required gate:
- current targeted unit matrix for hardened protected zones

Add release-level acceptance slices for:
- houses
- sidereal conversion
- progressions
- transits
- eclipse paths
- occultation paths
- Hermetic decans
- classical decanates

Acceptance corpus should include:
- fixed dates
- fixed latitudes/longitudes
- fixed doctrinal systems
- fixed expected tolerances

Authority preference:
- use external or institutional oracles where they exist
- where no full doctrinal oracle exists, validate substrate pieces and internal cross-consistency explicitly

Exit criteria:
- acceptance matrix codified
- results reproducible in `.venv`
- tolerances documented

---

## 4. Remaining Specialist Audit

Goal: finish adversarial review on the highest-risk modules not yet audited to the same depth.

Recommended order:
1. `electional.py`
2. `timelords.py`
3. `dasha.py`
4. `cycles.py`
5. doctrine-heavy specialist modules not yet reviewed at protected-zone depth
6. remaining public wrappers in `facade.py`

Audit lens:
- public-surface honesty
- hidden defaults and fallback doctrine
- vessel integrity
- temporal semantics
- validation sufficiency

Exit criteria:
- no known protected-zone contradictions remain open in these modules
- major findings either fixed or explicitly deferred with rationale

---

## 5. Operational Hardening

Goal: make future regressions harder.

Required work:
- add CI lane for the release acceptance matrix
- add doc-consistency grep checks for known dangerous phrases
- require targeted tests whenever protected-zone logic changes

Recommended doc-consistency checks:
- `treated as UTC`
- stale mutability claims
- stale removed parameters
- outdated house-vessel field descriptions

Exit criteria:
- CI gate exists
- doc-consistency checks exist
- protected-zone regression discipline is documented

---

## 6. Release Candidate Gate

Goal: define a real stop/go boundary for production release.

A release candidate should not be cut until all of the following are true:
- targeted unit matrix passes
- release acceptance matrix passes
- primary docs reflect current behavior
- compatibility notes are written
- versioning decision is recorded
- no unresolved protected-zone contradiction is known
- root public exports in `moira.__init__` have had final review

Exit criteria:
- release-candidate checklist signed off

---

## 7. Recommended Sequence

1. Draft release notes and compatibility notes.
2. Complete the remaining documentation sweep.
3. Formalize the acceptance matrix in CI.
4. Audit the remaining specialist modules.
5. Cut a release candidate.
6. Run one final regression and acceptance pass.
7. Release.

---

## 8. Current Assessment

Current state:
- engine integrity is substantially stronger than before the audit passes
- high-risk temporal and semantic defects have been removed from core subsystems
- public API truth is much better aligned with runtime behavior
- major doctrinal engines now have better boundary discipline

This supports the following practical assessment:

Moira is near release candidate quality at the engine level, but should still complete the final release-contract, documentation, and acceptance steps before being described without qualification as fully production ready.
