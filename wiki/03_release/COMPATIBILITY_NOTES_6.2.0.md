# Compatibility Notes - Moira 6.2.0

## Upgrade Boundary

Moira 6.2.0 is backward-compatible from 6.1.1 and 6.1.0.

- Existing 6.1.x function signatures, REST paths, and response models remain.
- The 10,025-name asteroid registry from 6.1.1 is unchanged.
- Legacy visibility and heliacal defaults, requests, responses, and event
  meanings are unchanged.
- New surfaces are additive. Omission does not select the physical model,
  Horary, Mundane, or Track A.

## Asteroid catalog

Same contract as 6.1.1. Identity is not availability. A host still needs
external release `2026.08.12.1` for the new 51 bodies to be
position-capable.

## Planetary reduction

Valid planet and asteroid positions keep the same public astronomy. The
repair rejects mismatched injected reduction contexts and isolates
reader/thread caches. Unexpected native-optimization failures now
propagate instead of being swallowed.

The five underscored `planet_at` workspace hooks remain for this
compatibility cycle and emit `DeprecationWarning`. Remove them before
the next signature-cleanup release.

## Track A

New routes and Python exports only. Existing synastry, return, and ACG
callers are unchanged. Progressed/directed relationship and
cyclocartography requests stay out of contract.

Server transport bounds (body/target/epoch caps) apply only to
`moira_server`. Direct Python is not narrowed.

## Track B

Horary and Mundane are evidence profiles, not judgement engines. They
do not infer question topics, emit yes/no answers, choose capitals, or
score outcomes. Cached 6.1.x charts do not need rewrite; new callers
opt in.

Regenerate OpenAPI clients to see the new operations.

## Physical visibility

No migration for `visibility_assessment`, `visibility_tonight`,
`visibility_event`, or their REST twins. Physical functions require
keyword-only pack and policy arguments. REST cannot take a filesystem
path; configure the server environment.

Jones/Paranal moonlight remains outside runtime and public API.

## Recommended Migration Sequence

1. Install `moira-astro==6.2.0` in staging.
2. Keep the `2026.08.12.1` asteroid pointer used by 6.1.1.
3. Regenerate REST/OpenAPI clients if you consume new routes.
4. Stop using underscored `planet_at` hooks in new code.
5. Do not point legacy visibility caches at the physical model.
6. Promote the exact staged artifact.
7. Verify installed version, `/ready`, one retained asteroid (`Mani`),
   one 6.1.1 asteroid (`'Aylo'chaxnim`), and one unchanged planet call.

## Upgrade Pin

```text
moira-astro==6.2.0
moira-astro[server]==6.2.0
```

## Rollback

Pin back to `6.1.1` to keep the 10,025 catalog without Track A/B,
physical visibility, or the planetary repair. Pin `6.1.0` only if the
host asteroid tree is also returned to `2026.07.27.1`.
