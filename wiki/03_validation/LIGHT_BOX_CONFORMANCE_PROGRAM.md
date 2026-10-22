# Light Box Conformance Program

This program implements GAP-007 without weakening the Light Box doctrine. Its governing object is conformance evidence, not a new claim that every calculation is correct. A source pointer proves ownership. A test-file mention is an evidence lead. Neither is an exact-release receipt.

## Seven stages

1. **Family register and priority boundary.** Generate the complete public calculation denominator from `moira.facade.__all__` and OpenAPI, resolve aliases, assign every canonical calculation to one primary family, and keep product priority separate from conformance.
2. **Strongest existing exemplars.** Admit bounded partial contracts for mature reduction vessels, alternative-frame receipts, Pancha Pakshi, western electional composition, Hellenistic profile, signed motion witness, progressions, and primary directions. Residual and exact-release fields remain unresolved until replayed.
3. **Production-user coverage.** Scan the Website and Workspace authoring repositories at exact Git revisions. Promote only exact REST path literals and explicit public-Python imports to P0. Dynamic or indirect use remains a named limitation rather than an inference.
4. **Phenomena and relationship review.** Review event searches, stations, rise/set, eclipses, occultations, heliacal work, aspects, relationship, composites, Davison, and patterns. Preserve the audit's major-gap or mixed disposition where transport evidence varies.
5. **Vedic, classical, specialist, and facade-only closure.** Give every remaining family a reviewed structural disposition and evidence leads. `Reviewed` means its gap is classified; it does not mean the family passed the doctrine.
6. **Runtime repair and release enforcement.** Add replayable evidence contracts, an assurance matrix, stale-artifact detection, and a changed-surface gate. Runtime mathematics changes only when a reproduced defect—not an absent receipt—requires one.
7. **Exact release and public conformance status.** Generate a machine-readable and human-readable status for the exact source/inventory identity. The engine artifact may be prepared locally; publication, website edits, package release, and deployment require their own authorization.

## Evidence vocabulary

- `conformant`: every required contract field is resolved and the exact release is verified by receipts.
- `partial`: a bounded subset of the contract is supported; the unresolved fields remain visible.
- `not_applicable`: a reviewed field or calculation class has no meaningful application, with a reason and evidence.
- `unresolved`: evidence is absent, stale, contradictory, or not yet reviewed deeply enough.

Family review uses `strong_exemplar`, `partial`, `mixed`, `major_gap`, and `unresolved`. Those labels guide work; they never replace the per-surface conformance status.

## Generated-artifact maintenance

Use the project interpreter with the optional development and server dependencies
installed. From the repository root on Windows:

```powershell
.\.venv\Scripts\python.exe scripts\maintain_generated.py --check
.\.venv\Scripts\python.exe scripts\maintain_generated.py --refresh
```

`--check` is read-only and stops at the first stale or failed stage. `--refresh`
writes mechanical generator outputs in the current checkout, stops at the first
review/replay blocker, and runs the complete check sequence after a successful
refresh. Earlier outputs can have changed when a later stage fails; review the
scoped Git diff before publishing. Both modes use the invoking interpreter,
resolve imports from this checkout, disable automatic downloads, and retain
strict known-issue checking.

The dependency order is:

1. Generated REST reference blocks and Hellenistic inventories, which are inputs
   to the documentation index.
2. Calculation inventory, conformance manifest, family register, and assessment.
3. Assurance matrix, public status, and the existing source gate.
4. Git wiki mirror, after all canonical Markdown outputs are ready.

The product-usage snapshot, reviewed release baseline, conformance admissions,
and execution receipts retain their existing review and replay processes. When
an inventory change blocks generation, the command identifies the affected
stage and the review or replay needed. Review the new surface membership and
bindings, preserve original consumer-audit provenance, and execute the admitted
contracts when fresh evidence is required. Resume `--refresh` after resolving
the blocker. Execution receipts retain their actual originating source identity;
exact-release verification remains a separate release gate.

The wiki refresh uses `--no-prune` and discovers Git-tracked canonical pages.
Stage newly authored canonical pages explicitly before mirroring them. Review
the generated diff, publish the nested wiki first, then commit its gitlink with
the scoped parent changes. Use an isolated checkout when unrelated source work
is in progress; the command performs no staging, commit, push, or evidence replay.

### Required pre-merge gate

The Release Hardening workflow runs the stable, unique **Generated Artifact
Gate** job for every pull request and every push to `main`, with no changed-path
filter. It checks the published wiki submodule, runs the read-only maintenance
command and its regression tests, and gates the larger release-hardening suites.

Repository branch protection for `main` requires a pull request, an up-to-date
branch, administrator enforcement, and these stable check names:

- **Engine Docstring Preflight**
- **Generated Artifact Gate**
- **Python 3.10 Server Compatibility Gate**
- **Release Hardening Gate**

Requiring the prerequisite checks also blocks a failed prerequisite from being
hidden by a skipped dependent job. The solo-maintainer configuration requires
zero approving reviews while retaining the pull-request and status-check
requirements. This server-side setting is separate from the workflow file:
publishing YAML alone does not make a check required. Preserve any additional
existing repository protections when configuring it.

## Release boundary

The generated current-status artifacts are source-tree truth until an exact release receipt binds them to a source commit and package. They must not be described as deployed or current-production evidence before that release boundary is crossed. The Website and Workspace remain separate consumers and are not edited by this engine program.

Exact evidence binds receipts to the inventory fingerprint and contract digest:

1. `scripts/replay_lightbox_receipts.py --require-exact-source` records the clean source revision when `HEAD` and the clean worktree remain unchanged from the beginning through the end of the replay, while `--reclassify-existing` refreshes version/inventory metadata when contracts are unchanged.
2. The assurance matrix and current status are regenerated from those receipts and synchronized to `moira.wiki` via `scripts/sync_git_wiki.py`.
3. `scripts/check_lightbox_release_gate.py --exact-release` accepts either the bounded pre-commit worktree (containing only the approved generated evidence paths and optional `moira.wiki` gitlink) or any clean committed worktree whose nested `moira.wiki` checkout is clean and matches the gitlink. It does not require a separate two-commit parent-SHA ceremony.
