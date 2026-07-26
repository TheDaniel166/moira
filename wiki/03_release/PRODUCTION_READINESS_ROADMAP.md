# Production Readiness Roadmap

Status: historical 2.0.0 release-hardening roadmap; completed and superseded
by the 5.0.0 release and compatibility notes

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

Status: complete as of 2026-04-10

Completed outputs:
- release notes: `wiki/03_release/RELEASE_NOTES_2.0.0.md`
- compatibility notes: `wiki/03_release/COMPATIBILITY_NOTES_2.0.0.md`
- versioning decision: major release — version bumped from 1.2.1 to 2.0.0 in `pyproject.toml`

Behavior changes recorded:
- naïve `datetime` inputs now raise instead of being treated as UTC
- several canonical result vessels are now frozen or tuple-backed
- invalid policy or invariant violations now raise concrete runtime errors
- `classify_house_system()` now raises on unknown codes
- Hermetic `decan_at()` no longer accepts `reader`
- Hermetic decan night-hour computation rejected invalid night geometry in
  2.0.0; the unsupported capability was subsequently removed from executable
  code on 2026-07-26

Exit criteria met:
- release note drafted
- compatibility notes written with per-change migration guidance
- version bump recorded as major (strict semantic versioning)

---

## 2. Documentation Closure

Goal: ensure that repository doctrine and user-facing docs tell the truth about the executable engine.

Status: complete as of 2026-04-10

Sweep completed:
- `wiki/02_standards/API_REFERENCE.md` — version corrected to 2.0.0; all datetime, house-policy, decan, and vessel docs verified against live behavior
- `wiki/02_services/SERVICE_LAYER_GUIDE.md` — three stale `moira.Chart`-is-mutable claims corrected; Chart schema illustration updated to `frozen=True, slots=True`
- `moira.wiki/` — regenerated from sources by `scripts/sync_git_wiki.py` (40 files written, 79 unchanged)
- `wiki/02_standards/HOUSES_BACKEND_STANDARD.md` — already current; `HouseCusps` fields, policy enums, and fallback doctrine are all correctly documented
- `wiki/03_standards/VALIDATION_CASE_STELLAR_HELIACAL_RISING.md` — already correctly documents the removal of the elongation magnitude guard

Known dangerous stale phrases confirmed absent:
- `treated as UTC` — not present in any primary doc
- stale mutable vessel descriptions — Chart mutability claims corrected in service layer guide
- removed parameters such as `decan_at(..., reader=...)` — not present in any doc; API reference already shows clean signature
- `AssertionError` — not present in primary docs

Doc-consistency check: passes clean.

Exit criteria met:
- all known stale contract claims removed from primary docs
- root-public versus module-public paths are clearly distinguished in API reference

---

## 3. Acceptance Matrix

Status: complete as of 2026-04-10

### CI lane

Added `.github/workflows/release-acceptance.yml`.

Kernel-free slices running in CI on every push and PR:

| Slice | File | Cases | Oracle | Note |
|---|---|---|---|---|
| Hermetic decans | `tests/unit/test_hermetic_decans.py` | 87 | internal cross-consistency | all pass |
| Classical decanates | `tests/unit/test_decanates.py` | 71 | internal cross-consistency | all pass |
| Sidereal unit | `tests/unit/test_sidereal.py` | 51 | internal cross-consistency | all pass |
| Houses external reference | `tests/integration/test_houses_external_reference.py` | 2 | offline Swiss Ephemeris fixture | all pass |
| Sidereal external reference | `tests/integration/test_sidereal_external_reference.py` | 77 | offline swetest fixture | excl. `1625_03_16_ut12` — see gap below |

### Local-only slices (require DE441 kernel)

`kernels/` is git-ignored; DE441 (3.1 GB) is not bundled. These slices are
validated locally before release and cannot run in stock CI.

| Slice | File | Local result |
|---|---|---|
| Eclipse external reference | `tests/integration/test_eclipse_external_reference.py` | pass |
| Eclipse NASA reference | `tests/integration/test_eclipse_nasa_reference.py` | pass |
| Occultations external reference | `tests/integration/test_occultations_external_reference.py` | pass |
| Progressions external reference | `tests/integration/test_progressions_external_reference.py` | skip (auto) |

### Known gap log

**Resolved for 5.0.0 — Sidereal 1625 epoch**: the current external-reference
fixture declares a `0.01`-degree (`36`-arcsecond) cross-engine corroboration
envelope. The complete fixture, including `1625_03_16_ut12`, passes and the CI
lane no longer deselects that epoch. This remains secondary-engine
corroboration, not primary-authority validation.

### Exit criteria — met

- acceptance matrix codified: ✓
- results reproducible in `.venv`: ✓
- tolerances documented: ✓
- CI lane live: ✓ (`.github/workflows/release-acceptance.yml`)

---

## 4. Remaining Specialist Audit

Status: complete as of 2026-04-10

Modules audited: `electional.py`, `dasha.py`, `timelords.py`, `cycles.py`

Audit lens applied to each: public-surface honesty, hidden defaults and
fallback doctrine, vessel integrity, temporal semantics, validation sufficiency.

Results summary:

| Module | Tests | Result | Notes |
|---|---|---|---|
| `electional.py` | 9 | clean | — |
| `dasha.py` | 66 | clean | one deferred observation — see receipt |
| `timelords.py` | 100 | clean | — |
| `cycles.py` | 105 | clean | — |

Deferred observation (dasha.py, non-blocking):
    Result vessels `DashaActiveLine`, `DashaConditionProfile`,
    `DashaSequenceProfile`, and `DashaLordPair` carry MACHINE_CONTRACT
    `"mutable": false` but are decorated `@dataclass(slots=True)` without
    `frozen=True`. `DashaPeriod` requires post-construction mutation for `.sub`
    accumulation; the others are immutable by convention. No runtime safety gap;
    no change required. Documented in the receipt for audit continuity.

Completion receipt: `wiki/03_release/SPECIALIST_AUDIT_COMPLETION_2026-04-10.md`

Exit criteria — met:
- no known protected-zone contradictions remain open: ✓
- major findings either fixed or explicitly deferred with rationale: ✓
- all 280 combined test cases green: ✓

---

## 5. Operational Hardening

Goal: make future regressions harder.

Status: complete as of 2026-04-10

Completed outputs:
- CI gate added in `.github/workflows/release-hardening.yml`
- doc-consistency checks added in `scripts/check_doc_consistency.py`
- protected-zone regression discipline recorded in `wiki/03_release/PROTECTED_ZONE_REGRESSION_DISCIPLINE.md`
- completion receipt recorded in `wiki/03_release/OPERATIONAL_HARDENING_COMPLETION_2026-04-10.md`

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

## 8. Completion And Supersession

This roadmap governed the 2.0.0 hardening campaign and its original exit
criteria were completed. The later 5.0.0 release is governed by its own release
and compatibility notes. Its tag, GitHub Actions workflow, and PyPI publication
records provide the exact release commit and artifact evidence once the release
is cut. This historical roadmap is retained for audit continuity and is no
longer a statement that Moira is waiting to enter its first release-candidate
phase.
