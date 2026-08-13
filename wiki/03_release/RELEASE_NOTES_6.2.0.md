# Moira 6.2.0 - Admitted Capability Baseline

**Release date:** 2026-08-13

**Public upgrade path:** 6.1.1 to 6.2.0. Callers still on 6.1.0 inherit the
6.1.1 asteroid identity catalog as part of this upgrade.

Moira 6.2.0 is the clean engine baseline after 6.1.1. It publishes only
work that is admitted, bounded, and already on `main`. It is a minor
release: new typed capability, unchanged existing request shapes, and no
reinterpretation of legacy visibility or chart results.

## In this release

- **Asteroid catalog `2026.08.12.1`** — 10,025 canonical names, 401 Type-13
  shards. Same identity product as published 6.1.1.
- **Planetary reduction repair** — reader/TT/mode provenance, per-thread
  cache ownership, narrowed native fallbacks, and one asteroid-owned
  apparent-vector adapter. REST schemas unchanged.
- **Track A** — exact transits to composite and Davison charts; fixed-star
  astrocartography; relocated returns; explicit-epoch dynamic ACG
  displacements. Calculation only. No scores, rankings, or travel advice.
- **Track B** — Lilly 1647 Horary evidence profile and a neutral Mundane
  event-chart profile. Calculation only. No answers, outcomes, or advice.
- **Physical visibility Phase 7** — opt-in `clear_sky_naked_eye_point_source_v1`
  assessment and four-phase event search. Legacy visibility/heliacal APIs
  keep their defaults. Numerical pack `1.2.0` stays outside the wheel.
- **Horizons comparator correction** — the retired kilometer-scale planet
  residuals were wrong targets/epochs, not DE441 error.

## Not in 6.2.0

These exist nearby and are **not** this release:

- Track C rectification
- Remaining planetary public-signature cleanup (P-05/P-06). Five legacy
  underscored workspace hooks stay, with deprecation warnings
- Jones/Paranal moonlight as runtime, API, or release-gate evidence
- Website or Urania Workspace product surfaces for Track A, Track B, or
  physical visibility
- Any claim that the full repository test suite was run for this tag

## Track A contracts

```text
POST /v1/composite/transits
POST /v1/davison/transits
POST /v1/astrocartography/fixed-stars
POST /v1/astrocartography/dynamic/transits
POST /v1/returns/relocated
```

Progressed/directed relationship charts and cyclocartography remain
excluded.

## Track B contracts

Horary composes Lilly 1647 question, house, significator, hour, and
perfection evidence from caller-supplied geometry. Mundane composes
ingress, syzygy, eclipse-epoch, and Jupiter-Saturn receipts. Incomplete
work is `not_evaluable`, never guessed.

## Physical visibility

```text
POST /v1/visibility/physical-assessment
POST /v1/visibility/physical-event
```

Callers must supply an explicit pack config. Operators set
`MOIRA_SERVER_PHYSICAL_VISIBILITY_DATA_PACK_DIRECTORY`. Missing or corrupt
packs fail closed. Mercury/Venus event search is not admitted.

Pack: `moira-physical-heliacal-visibility` `1.2.0`, CC BY-SA 4.0, manifest
`cf93433a9f66a5ea92832271ce3c4b023fcc8693164803539a9f1be85b17468c`.

## Planetary compatibility cycle

`planet_at(...)` still accepts the five underscored workspace hooks for
this cycle and warns. New code should not use them. P-05 removal is
later, independently.

## Install

```text
moira-astro==6.2.0
moira-astro[server]==6.2.0
```

Hosted asteroid trees should remain on `2026.08.12.1`. Read
`COMPATIBILITY_NOTES_6.2.0.md` before regenerating clients.
