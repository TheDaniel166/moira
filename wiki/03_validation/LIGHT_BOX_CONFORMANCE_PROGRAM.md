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

### Separate fingerprint and execution identities

The v2 inventory records two hashes:

| Identity | Includes | Excludes | Used by |
|---|---|---|---|
| `surface_fingerprint_sha256` | The complete inventory payload, including its structural hash, engine label, discovery links, counts, and source locations | Its own hash field | Report identity and generated-artifact freshness |
| `structural_fingerprint_sha256` | Public export/route membership, aliases, ownership paths/names, classifications, direct Python declarations, and each REST operation's reachable schema constraints | Source line numbers, Markdown/test mention paths, owner-resolution diagnostics, classification prose, REST tags/prose, engine label, discovery counts | Reviewed baseline, product-use snapshot, manifest, family reports, and receipt binding |

Structural projection is versioned as
`moira.lightbox-structural-fingerprint/v1`. All consuming artifact schemas move
to v2; their existing `inventory_fingerprint_sha256` field now explicitly means
the structural hash. The v1 whole-report hash is never silently reinterpreted.
JSON hashing uses sorted object keys, compact separators, and UTF-8; surface
collections are sorted by stable surface ID for structural hashing. Python
declarations serialize explicit AST node fields, including empty and optional
fields; they do not depend on interpreter-specific `ast.dump()` presentation.

Python declaration hashes include parameter kinds, annotations, direct default
expressions, decorators, class bases, and directly declared result fields and
method signatures. They omit comments, docstrings, source positions, and function
bodies. REST hashes include request/response constraints and transitively
referenced schemas, including recursive schemas. Descriptions, examples, and
titles are annotations; fields actually named `description` or `title` and
their constraints remain part of the contract.

This is API identity, not proof that implementations are equivalent. Transitive
Python dependencies, evaluated defaults referenced through other constants,
native code, resource contents, and function bodies still require their own
source/resource review and appropriate execution. A stable structural hash does
not refresh a receipt's source revision, engine version, timestamp, output,
contract digest, or release status. Exact-source replay and release checks retain
their existing boundary. Selective dependency-based replay is a separate task.

After a documentation edit or a source-line shift, run `--refresh` normally.
Discovery artifacts and the wiki must still be regenerated when stale;
`--check` compares their complete rendered content. Untracked local Markdown can
still change discovery links, so an isolated checkout remains useful for
preserving drafts. Such metadata drift no longer requires rebinding the reviewed
baseline, consumer audit, or execution receipts. Actual API changes still block
those bindings and require deliberate review and the appropriate replay.

#### One-time migration of retained local receipts

Retain the matching v1 inventory before generating v2, then migrate explicitly:

```powershell
.\.venv\Scripts\python.exe scripts\replay_lightbox_receipts.py --migrate-legacy-inventory C:\path\to\retained-v1-inventory.json
```

The command verifies the old inventory digest, its receipt binding, unchanged
contracts, and matching legacy membership/classification/ownership. It preserves
each original receipt byte-for-byte as a JSON value, including receipt IDs and
execution history. The v2 envelope records the old header and full receipt-set
digest so the old artifact can be reconstructed and checked. This reviewed
current API binding does not establish declaration/schema shapes at the time of
the old execution: v1 did not record them. Only local unreleased receipts may
use this migration; exact-source v1 evidence requires a fresh v2 replay.

Migration does not run tests. Maintenance never invokes it automatically.
Baseline and product-use snapshot schema migration is a separate reviewed edit
that preserves coverage thresholds, audit dates, consumer revisions, and
callsites. `--reclassify-existing` cannot migrate schemas or rebind a changed
structural hash; migrated execution records remain immutable. The assurance
matrix verifies receipt digests and migration history and cannot promote a
migration to exact-source evidence.

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

1. `scripts/replay_lightbox_receipts.py --require-exact-source` records the clean source revision when `HEAD` and the clean worktree remain unchanged from the beginning through the end of the replay. `--reclassify-existing` only re-evaluates retained results under the same structural binding; it cannot update their execution identity or supply fresh release evidence.
2. The assurance matrix and current status are regenerated from those receipts and synchronized to `moira.wiki` via `scripts/sync_git_wiki.py`.
3. `scripts/check_lightbox_release_gate.py --exact-release` accepts either the bounded pre-commit worktree (containing only the approved generated evidence paths and optional `moira.wiki` gitlink) or any clean committed worktree whose nested `moira.wiki` checkout is clean and matches the gitlink. It does not require a separate two-commit parent-SHA ceremony.
