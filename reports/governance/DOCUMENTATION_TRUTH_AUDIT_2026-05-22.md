# Documentation Truth Audit (2026-05-22)

## Scope

Repository-wide documentation audit across these strata:

- root repository markdown
- `docs/architecture`
- `wiki/` standards, doctrines, validation, research, release, roadmap
- `moira/docs`
- tracked markdown mirrors in `moira.wiki`
- code docstrings as executable documentation

This audit is truth-first. It distinguishes between:

- documentation that is machine-validated and currently truthful
- documentation that is structurally drifting from executable truth
- documentation that is reachable but not yet verified against a governing test

## Audit Method

Verification actually run:

- `python -m pytest tests/test_api_reference_validation.py tests/unit/test_public_api_drift.py -q`
- `python -m pytest tests/test_api_reference_validation.py tests/unit/test_docstring_governance.py tests/unit/test_public_api_drift.py -q`
- repository-wide tracked-markdown relative-link audit
- `wiki/` vs `moira.wiki/` overlap drift scan by content hash
- targeted post-remediation link audits for architecture, validation, and primary-directions files

Manual spot-audit focus:

- mirrored wiki surfaces
- standards/reference docs tied directly to public API
- roadmap/doctrine cross-links
- validation ledgers that cite live code paths

## Inventory

Approximate documentation counts by major directory:

- `docs`: 24 files
- `wiki`: 136 files
- `moira/docs`: 5 files
- `tests`: 5 markdown/yaml summary files
- `reports`: 13 files

Large/high-authority surfaces:

- `README.md`
- `wiki/02_standards/API_REFERENCE.md`
- `wiki/02_standards/ASPECT_BACKEND_STANDARD.md`
- `moira/docs/EXPORT_POLICY.md`

## Findings

### Critical

1. Tracked markdown link integrity is currently clean on the audited repository set.
   Evidence from final tracked-markdown link audit:
   - `0` missing local markdown targets
   - `0` stale absolute-path targets in tracked markdown
   Meaning:
   - The tracked documentation graph is currently navigable by local links.
   - Remaining link debt is now isolated to the `moira.wiki` mirror stratum rather than the main tracked repository markdown.

### Major

2. `wiki/` and `moira.wiki/` are not structurally isomorphic and should not be assumed to be strict mirrors by path.
   Evidence:
   - overlap scan found only 3 common relative paths, with most files mirrored by flattened or re-rooted names.
   Meaning:
   - “same content, different path conventions” may be true in many cases, but it is not safe to assume pathwise identity.

3. Overlap drift exists between `wiki/` and `moira.wiki/`, but the sampled cases are mostly context/path adaptations rather than semantic contradiction.
   Evidence:
   - `wiki/Home.md` vs `moira.wiki/Home.md`
   - `wiki/05_research/astrodynes/astrodynes_source_assessment_2026-04-09.md` vs mirror
   Interpretation:
   - current sampled drifts appear operational rather than doctrinal
   - this is a watch zone, not yet evidence of content dishonesty

4. Many validation and doctrine docs still reference code paths as plain text or stale absolute Windows paths rather than repository-stable relative links.
   Meaning:
   - even when the prose claim is true, the evidence trail is brittle
   - this weakens visibility doctrine

### Minor

5. Code docstring governance is now healthy on the audited enforcement surface.
   Evidence:
   - `tests/unit/test_docstring_governance.py` passes after remediation of the five previously failing modules
   Remediated files:
   - `moira/_spk_body_kernel.py`
   - `moira/spk_reader.py`
   - `moira/dispatch.py`
   - `moira/julian.py`
   - `moira/polar_motion.py`
   Meaning:
   - The repository's executable docstring-governance contract is currently truthful on the tested surface.

6. Some documentation claims are machine-enforced and currently healthy.
   Evidence:
   - `tests/test_api_reference_validation.py` passes
   - `tests/unit/test_public_api_drift.py` passes
   Meaning:
   - standards API reference and layered export-surface truth are currently in better condition than broader roadmap/research/architecture prose

7. Some mirror differences are expected due to sync transformation.
   Evidence:
   - `moira.wiki/Home.md` contains generated-banner and flattened links
   Meaning:
   - not every diff is a defect; mirror semantics must be judged in context

## Fixes Applied In This Audit Pass

Deterministic broken-link repairs made:

- `wiki/06_roadmap/lord_of_the_orb/lord_of_the_orb_roadmap.md`
- `wiki/06_roadmap/lord_of_the_turn/lord_of_the_turn_roadmap.md`
- `wiki/06_roadmap/nine_parts/nine_parts_roadmap.md`
- `wiki/03_validation/SIDEREAL_PHASE1_TRUTH_FINDINGS_2026-04-16.md`
- `wiki/03_validation/SIDEREAL_SOURCE_CITATION_LEDGER_2026-04-16.md`
- `docs/architecture/MOIRA_NATIVE_PLANETARY_PATH.md`
- `docs/architecture/MOIRA_NUMPY_SPICE_DEPENDENCY_MAP.md`
- `docs/architecture/MOIRA_NATIVE_PLANETARY_CLOSURE_TRACKER.md`
- `docs/architecture/MOIRA_NATIVE_PUBLIC_PLANETARY_EVALUATOR_SPEC.md`
- `wiki/01_doctrines/primary_directions/primary_directions_doctrine.md`
- `wiki/06_roadmap/primary_directions/primary_directions_roadmap.md`
- `wiki/03_validation/SWISS_EPHEMERIS_EXTENSIBILITY_ROADMAP.md`
- `wiki/05_research/primary_directions/primary_directions_fixed_star_family_matrix.md`
- `wiki/01_doctrines/primary_directions/primary_directions_truth_card_fixed_stars.md`
- `wiki/06_roadmap/primary_directions/primary_directions_phase10_audit.md`
- `wiki/02_standards/PRIMARY_DIRECTIONS_BACKEND_STANDARD.md`
- `wiki/05_research/primary_directions/remaining_primary_directions_frontiers.md`
- `wiki/01_doctrines/primary_directions/primary_directions_truth_card_parallels.md`
- `wiki/05_research/harmograms/harmograms_implementation_roadmap.md`

Docstring-governance remediation made:

- `moira/_spk_body_kernel.py`
- `moira/spk_reader.py`
- `moira/dispatch.py`
- `moira/julian.py`
- `moira/polar_motion.py`

These were limited to path-truth corrections where the intended target was unambiguous.

## What Was Intentionally Left Unchanged

- code semantics in protected computational modules
- `moira.wiki` submodule mirror content in this pass

These need controlled follow-up because they are numerous and, in the mirror case, live outside the main tracked wiki tree.

## Recommended Next Remediation Order

1. Add a repeatable markdown-link audit to test tooling so this drift stops reappearing silently.
2. Define the intended invariants between `wiki/` and `moira.wiki` so mirror drift can be judged mechanically instead of ad hoc.
3. Decide whether `moira.wiki` should be remediated in parallel or regenerated from `wiki/`.

## Honesty Receipt

This audit did not verify every prose claim against an external scientific authority.
It did verify:

- repository documentation topology
- machine-enforced reference/API/docstring governance surfaces
- tracked local link integrity
- overlap drift between the two main wiki strata

What remains unresolved:

- the full semantic truth of all roadmap/research/retrospective prose
- the broader `moira.wiki` mirror backlog, which still contains a larger absolute-path cluster outside the main tracked wiki tree
