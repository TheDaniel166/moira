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

## Release boundary

The generated current-status artifacts are source-tree truth until an exact release receipt binds them to a source commit and package. They must not be described as deployed or current-production evidence before that release boundary is crossed. The Website and Workspace remain separate consumers and are not edited by this engine program.

Exact evidence uses a two-commit boundary so that a receipt never claims to have tested the commit that merely stores that receipt:

1. The **source commit** contains the calculation source, contracts, gate, and documentation to be tested. Its parent worktree and nested wiki must be clean.
2. `scripts/replay_lightbox_receipts.py --require-exact-source` records that source commit only when `HEAD` and the clean worktree remain unchanged from the beginning through the end of the replay.
3. The assurance matrix and current status are regenerated from those receipts. Before commit, the only permitted parent-worktree changes are the five generated evidence files and, after wiki synchronization, the `moira.wiki` gitlink.
4. The generated assurance and current-status Markdown pages are committed in the nested wiki. That nested commit may change only those two pages.
5. A single-parent **attestation commit** records exactly the five generated evidence files plus the nested wiki gitlink. Its sole parent must be the receipt's source revision. It is an evidence envelope for that parent; it is not itself the tested source revision.
6. `scripts/check_lightbox_release_gate.py --exact-release` accepts either the bounded pre-attestation state or the clean committed attestation state. It rejects source drift, merge attestations, a wrong parent, extra or missing paths, dirty post-attestation worktrees, nested-wiki drift, local receipts, and failed replay contracts.

The attestation commit can be published only after the exact gate passes in both states. Any later source change requires a new source commit, replay, and attestation; an earlier receipt is never carried forward by assertion.
