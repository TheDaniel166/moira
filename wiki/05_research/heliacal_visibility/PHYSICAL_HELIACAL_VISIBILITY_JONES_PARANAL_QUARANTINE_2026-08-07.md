# Jones/Paranal Physical-Visibility Research Quarantine

Date: 2026-08-07
Status: quarantined; not an engine, API, data-pack, release, or roadmap dependency

## Decision

The site-specific Jones/Paranal scattered-moonlight experiment is removed from
the active Moira physical-visibility product path. It is not part of
`clear_sky_naked_eye_point_source_v1`, the public Python or REST contract, the
packaged compatibility resources, or the Phase 7 release gate.

This decision does not invalidate the source audit or the research questions.
It recognizes that the attempted Paranal composition was an optional
experimental branch, not a prerequisite for releasing the already admitted
general physical-visibility model.

## Active boundary after quarantine

- The engine continues to use the immutable external
  `moira-physical-heliacal-visibility` `1.2.0` pack.
- The opt-in single-epoch assessment and four-phase event contracts remain
  unchanged.
- Legacy visibility and heliacal defaults remain unchanged.
- General atmosphere, directional background, horizon, observer-factor,
  spectral-response, threshold, event-solver, and typed-receipt work remains
  active.
- No Jones component loader, Paranal scenario, `1.3` compatibility contract,
  environment variable, public type, public function, or response field is
  shipped.

## Removed from the active worktree

The quarantined scope includes the experimental moonlight runtime module,
Jones component-pack and Paranal scenario builders and validators, failed and
interrupted response-geometry artifacts, experiment-only tests, the draft
`1.3` compatibility contract, and the tentative public/facade/REST integration.

The pre-quarantine state is preserved outside the repository at:

`C:\Users\nilad\Documents\Codex\2026-07-25\m\recovery\moira-physical-visibility-pre-paranal-quarantine-2026-08-07.zip`

Archive SHA-256:
`b2d0debc26126618c68c94959a188ae304547c1c150c97edb590d239abea6182`.

The archive contains all 157 files that were modified or untracked before the
quarantine cleanup. It is recovery evidence, not a release artifact.

## Reopening rule

This work must not silently return as a Phase 7 prerequisite. Reopening it
requires a separately authorized research project with a new model identity,
a bounded scientific question, an explicit stop condition, source-owned
validation, and a release decision independent of the current physical model.
Until then, historical Jones/Paranal checkpoints are research history only and
must not be described as admitted product capability.

## Phase 7 restart point

Phase 7 returns to the core release boundary: regenerate the public capability
and API inventories from current runtime truth, validate the exact `1.2.0`
external pack, build and clean-install the wheel and sdist offline, rerun the
independent event oracles and regression gates, and record the resulting
release receipt. No site-specific moonlight scenario is required for closure.
