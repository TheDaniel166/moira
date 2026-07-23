# Pancha Pakshi Free and Enhanced Product Plan

**Status:** Core product shipped; Enhanced workflow expansion and launch
observation remain in progress.

**Current production boundary (2026-07-22):** The website is pinned to
`moira-astro 5.1.2`, all 19 admitted REST operations are contract-accounted
for, and the public `/pancha-pakshi` product is live. The current production
website artifact is `a387a51ac8f3f5048f85c028e0fe028161fc9ff8`.

### Completion boundary

The package release, website adapter, and Free public beta in Phases 1–3 are
complete. The first Enhanced workflow is also live: entitled Enhanced,
Workspace, and administrator users may explore an exact caller-selected local
date and time through the protected `atInstant` path.

The shipped product includes both admitted identity methods, manual natal data
entry, birth-data import from an existing saved chart, explicit timing and
Sookshma policy selection, one frozen-instant composition path, the dial and
current-half timeline, interval inspection, relation and derivation evidence,
method and source receipts, honest non-selection states, responsive
presentation, and production entitlement enforcement.

Phase 4 is not complete. Its remaining Enhanced product work is:

1. a bounded 31-day planner;
2. side-by-side timing and Sookshma policy comparison;
3. multi-subject comparison for up to five subjects;
4. dedicated account-persistent Pancha Pakshi subjects and locations (saved
   chart birth-data import already exists, but is not this complete workflow);
5. bounded CSV, ICS, and PDF export; and
6. user-authored transition reminders.

Phase 5 is active rather than complete: production observation began with the
2026-07-22 public launch. Presentation and reliability may be tuned from that
evidence, but doctrine, source boundaries, and the prohibition on scoring
remain unchanged.

## Product constitution

1. The MIT package and its self-hosted REST server expose every admitted Pancha
   Pakshi computation. Commercial entitlements do not belong in the engine.
2. Website Free exposes a genuinely useful present-time product, including its
   method, policy, provenance, omissions, and failure state.
3. Website Enhanced sells workflow: arbitrary-time exploration, ranges, saved
   subjects, comparison, export, reminders, and higher operational scale.
4. The same frozen request must produce identical computational truth for Free,
   Enhanced, Workspace, and self-hosted callers.
5. Source-admission privacy is not a premium tier. Private Uromarisi research
   remains private for every user; only its admitted governance status is public.
6. No tier receives a numerical score, percentage, generic good/bad judgment,
   prognosis, medical interpretation, or automatic "best time" ranking.
7. Profile, timing, and Sookshma policies remain explicit. The website may
   remember a user's choice only after the user makes it; it must not invent a
   universal default.

The commercial principle is: **truth is not paywalled; convenience, planning,
automation, persistence, and presentation may be.**

## Tier matrix

| Capability | MIT package and self-hosted REST | Website Free | Website Enhanced |
|---|---|---|---|
| All 19 admitted REST operations | Complete | Used through curated workflows | Same engine operations |
| Profile catalog, sources, omissions, admission status | Complete | Public, no account | Same |
| Uromarisi constitutional status | Status only | Public transparency panel | Same; no extra research data |
| Aksara identity | Complete | One active, session-local subject | Saved and multiple subjects |
| Natal-Moon identity | Complete | One active, session-local subject | Saved and multiple subjects |
| Nakshatra mapping, Padu, first-EAT seed, directed relation | Complete | Visible in derivation | Same, plus comparisons |
| Present astronomical paksha and local-solar context | Complete | Yes | Yes |
| Fixed-clock and solar-proportional current cells | Complete | Yes | Yes |
| Timing and Sookshma policy selection | Caller explicit | User explicit | User explicit, plus side-by-side comparison |
| Present major and subordinate activity | Complete | Yes | Yes |
| Current solar-half timeline | Caller composes | Yes | Yes |
| Caller-selected date or time | Complete | Present time only | Yes |
| Range planner | Caller composes | No | Up to 31 days per request |
| Multi-subject comparison | Caller composes | No | Up to five subjects per view |
| Saved subjects and locations | Caller owns storage | Session-local | Account-persistent |
| CSV, ICS, and PDF export | Caller composes | No | Up to 31 days per export |
| Boundary reminders | Caller composes | No | User-selected categorical transitions |
| Scores, percentages, best-time ranking | Not admitted | No | No |
| Private research corpus | Not exposed | No | No |

Free interactive use should not gain a new daily quota. It should use the
website's existing public-compute concurrency and rate guard. Its scope is
structural: the server freezes one present instant and accepts no caller-supplied
instant. Enhanced accepts explicit instants and bounded ranges.

The feature joins the existing Moira Enhanced plan at the existing product
price. Workspace and administrator accounts inherit Enhanced through the
existing entitlement ladder.

## Website product

The public route should be `/pancha-pakshi` and should proceed in this order:

1. Explain and require an identity method: the 1879 name/query-initial product
   or the 2024 natal-Moon composition.
2. Resolve the subject bird and display the exact source-scoped derivation.
3. Require explicit timing and Sookshma policy choices.
4. Freeze one instant for the entire composed calculation.
5. Display the major activity, subordinate activity, exact interval, next
   transition, directed relation facts, and current-half timeline.
6. Keep a persistent **Method and sources** drawer containing profile IDs,
   policy IDs, source locators, omissions, modern-composition notices, exact
   fractions, and failure statuses.
7. Offer Enhanced actions using honest language: **Explore another date**,
   **Compare policies**, **Plan 31 days**, **Save subjects**, **Export**, and
   **Set a transition reminder**.

The interface must use neutral visual language. It must not use red/green
favorability colors, gauges, stars, scores, or auspicious/inauspicious badges.
When a fixed-clock policy has an unmaterialized tail, display the engine's
non-selection state; never silently switch to the proportional policy.

Enhanced reminders are user-authored predicates such as "notify me when my bird
enters Rule." They are not Moira-selected favorable windows.

## Transport and entitlement architecture

The open-source `moira_server` remains an unentitled transport over the complete
admitted engine. Hosted commercial enforcement belongs in the website server.

Create one website composition function, provisionally
`buildPanchaPakshiSnapshot`, used by every tier. It receives a frozen instant,
explicit profile IDs, subject bird, timing policy, and Sookshma policy, then
preserves the engine result losslessly.

Recommended tRPC surface:

- `panchaPakshi.catalog` — public metadata and admission status.
- `panchaPakshi.resolveAksara` — public compute.
- `panchaPakshi.resolveNatalIdentity` — public compute.
- `panchaPakshi.current` — public compute; the server supplies one frozen instant.
- `panchaPakshi.atInstant` — Enhanced; the caller supplies the instant.
- `panchaPakshi.planRange` — Enhanced; maximum 31 days per request.
- `panchaPakshi.compareSubjects` — Enhanced; maximum five subjects.
- `panchaPakshi.export` — Enhanced; maximum 31 days.
- `panchaPakshi.reminders` — Enhanced persistence and delivery.

Use the existing website mechanisms:

- `publicComputeProcedure` for anonymous/free computation;
- `protectedEnhancedProcedure` for arbitrary time, ranges, persistence, export,
  and reminders;
- `hasEnhanced()` so Workspace and administrators inherit access;
- `LockedFeature` for discoverable UI affordances, never as the security gate;
- `TRACKED_TOOLS` and privacy-safe usage receipts.

Required invariants:

- entitlement rejection occurs before input parsing and engine work;
- the browser is never the access authority;
- the production engine REST service remains internal;
- one frozen instant is reused across paksha, solar context, current-cell, and
  Sookshma composition;
- profile capabilities are discovered and checked, never assumed;
- policy IDs, profile IDs, provenance, omissions, fractions, and non-selection
  statuses survive serialization;
- current results are never cached beyond their next boundary;
- telemetry contains no name, birth data, raw coordinate, or source text.

## Implementation sequence

### 1. Package closure and release — Complete

- Finish and isolate the existing Pancha Pakshi work from unrelated changes.
- Correct the current changelog route-count drift (`17` must become `19`).
- Confirm all 19 public methods and routes are complete and documented.
- Bump `pyproject.toml` and `moira/facade.py` to `5.1.0`.
- Add `RELEASE_NOTES_5.1.0.md` and `COMPATIBILITY_NOTES_5.1.0.md`.
- Build and inspect the wheel and sdist, including all admitted manifest data.
- Tag and publish only after the release identity and public-surface gates pass.

Completed through the patched `moira-astro 5.1.2` release. The original
`5.1.0` target remains below as historical implementation intent; subsequent
patches are the production authority.

Likely package files:

- `pyproject.toml`
- `moira/facade.py`
- `CHANGELOG.md`
- `README.md`
- `wiki/03_release/RELEASE_NOTES_5.1.0.md`
- `wiki/03_release/COMPATIBILITY_NOTES_5.1.0.md`

No engine-semantic change is expected for tiering.

### 2. Website engine adapter — Complete

- Pin staging and production to `moira-astro 5.1.0`.
- Assert the exact Pancha Pakshi OpenAPI contract before enabling the feature.
- Add the lossless composition helper and typed shared contract.
- Register public and Enhanced tRPC procedures behind a feature kill switch.

Production uses exact engine-version and OpenAPI admission checks, a lossless
shared contract, one frozen-instant composition function, public catalog and
identity procedures, Free `current`, protected Enhanced `atInstant`, tier
inheritance, privacy-safe usage receipts, and a fail-closed feature switch.

Likely website files:

- `server/_core/panchaPakshi.ts`
- `server/routers/panchaPakshi.ts`
- `server/routers.ts`
- `shared/panchaPakshi.ts`
- `shared/tiers.ts`

### 3. Free public beta — Complete

- Ship identity selection, explicit policies, present snapshot, current-half
  timeline, relation facts, provenance, and boundary/failure handling.
- Add `/pancha-pakshi` routing, navigation, route metadata, prerendering,
  documentation, and accessibility coverage.
- Do not advertise Enhanced Pancha features until the entitlement path exists.

The public route, presentation, accessibility coverage, explicit evidence
boundaries, and entitlement-aware Enhanced entry point are live.

### 4. Enhanced workflow — In progress

- Add arbitrary-time exploration, 31-day planning, policy comparison,
  multi-subject comparison, saved subjects, exports, and reminders.
- Add a database table and migration only when persistence/reminders begin; do
  not mix this with unrelated schema work.
- Update Pricing and FAQ copy only after anonymous and Enhanced staging smokes.

Shipped: exact arbitrary-time exploration for Enhanced, Workspace, and
administrator users, plus reuse of existing saved-chart birth data.

Remaining: the 31-day planner, side-by-side policy comparison, multi-subject
comparison, dedicated Pancha Pakshi persistence, CSV/ICS/PDF export, and
transition reminders. Existing saved-chart import must not be reported as
completion of the dedicated persistence workflow.

### 5. Observe and harden — Active

- Observe for 30 days.
- Tune batching, caching, and presentation only; do not alter doctrine or add
  scoring in response to engagement metrics.

The observation window began with the 2026-07-22 public production launch.

## Verification gates

Package validation must include targeted Pancha tests first, the complete
non-network suite, documentation consistency, release identity, wheel/sdist
build, package-content inspection, and `twine check` using the project `.venv`.

Website tests must prove:

- Free and Enhanced return identical engine truth for the same frozen request.
- Missing explicit profile or policy is rejected.
- Anonymous/free callers cannot invoke arbitrary-date, range, save, export, or
  reminder procedures.
- Rejections happen before any engine call.
- Workspace and administrator accounts inherit Enhanced.
- All 19 engine operations are contract-accounted for.
- No score, generic favorability, private research, prognosis, or medical field
  leaks through any response or presentation.
- Sunrise/sunset boundaries, paksha boundaries, exact cell endpoints,
  fixed-clock tails, DST display, polar failure, 422 input errors, timeouts, and
  engine-unavailable states remain honest.
- Focused tests, the complete website test suite, type check, production build,
  strict prerender, anonymous/Enhanced staging smokes, and exact-artifact
  promotion all pass.

## Launch measures

Hard correctness and reliability targets:

- zero Free/Enhanced computational parity differences;
- zero private-data or scoring-contract leaks;
- at least 99.5% successful present-snapshot requests;
- present snapshot p95 below 2 seconds;
- 31-day planner p95 below 8 seconds, otherwise move it to an asynchronous job.

Privacy-safe product measures:

- identity-form completion;
- successful present snapshot;
- policy switches;
- planner, comparison, export, and reminder use;
- Enhanced CTA selection and conversion;
- seven-day return after a completed snapshot.

Engagement metrics may improve workflow and presentation. They must never be
used to justify invented doctrine, hidden defaults, scoring, or stronger claims.
