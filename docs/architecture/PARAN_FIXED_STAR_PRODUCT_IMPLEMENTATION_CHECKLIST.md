# Paran Fixed-Star Product Implementation Checklist

**Status:** implementation and targeted verification complete
**Scope:** engine, facade, REST, validation, and Workspace-oriented composition
**Compatibility rule:** existing `find_parans()` and `natal_parans()` behavior
remains unchanged unless a caller explicitly selects a new surface or policy.

## 0. Governing decisions

- [x] Preserve the existing 24-hour paran search as the default doctrine.
- [x] Keep birth-moment angular contacts separate from two-body parans.
- [x] Reuse the sovereign star catalog and existing star groups; do not copy
  catalog coordinates or invent client-owned identities.
- [x] Keep the full star catalog distinct from the smaller paran working canon.
- [x] Treat crossing diagnostics as astronomical evidence, not UI prose.
- [x] Preserve kernel-free star-star computation.
- [x] Keep Workspace packet assembly in website transport rather than engine
  doctrine.

## 1. Engine-owned paran star canon

- [x] Add `moira/paran_stars.py`.
- [x] Define a Python 3.10-compatible `ParanStarTier` string enum.
- [x] Define immutable `ParanStarCanonEntry` vessels.
- [x] Build `PARAN_STAR_CANON` from the existing working fixed-star group.
- [x] Derive Royal, Behenian, and Ptolemaic membership from existing modules.
- [x] Add deterministic tier filtering and catalog-availability filtering.
- [x] Reject unknown tier identifiers explicitly.
- [x] Export the canon surface through `moira.facade`.
- [x] Add `GET /v1/parans/star-canon`.
- [x] Return stable order, membership tags, availability, counts, and tier ids.
- [x] Add unit, facade, OpenAPI, and REST parity tests.

## 2. Crossing inventory and absence reasons

- [x] Add an opt-in horizon-crossing availability helper to `moira.rise_set`.
- [x] Derive availability from the same geometric altitude signal and horizon
  threshold used by event search.
- [x] Distinguish `found`, `always_above_horizon`,
  `always_below_horizon`, and `solver_failure`.
- [x] Define immutable paran circle/body inventory vessels.
- [x] Preserve event JD, source method, and altitude policy when found.
- [x] Add `ParanSearchResult` without changing `find_parans()` return type.
- [x] Add `find_parans_with_inventory()`.
- [x] Add the equivalent detailed natal wrapper.
- [x] Add `include_crossing_inventory` to search and natal REST requests.
- [x] Serialize inventories without changing existing event serialization.
- [x] Test Regulus at 60 N as ordinary rising/setting.
- [x] Test Capella at 60 N as always above the horizon.
- [x] Test Acrux at 60 N as always below the horizon.
- [x] Test explicit solver-failure reporting.
- [x] Prove diagnostics do not change paran matches or event times.

## 3. Fixed-star field pipeline proof

- [x] Add a live Regulus-Capella target test for site evaluation.
- [x] Extend the live target through grid sampling and field analysis.
- [x] Require a grid that produces both active and inactive samples.
- [x] Prove non-empty contour extraction and path consolidation.
- [x] Prove higher-order field structure accepts the star target identity.
- [x] Add kernel-free REST parity for samples, analysis, contours, paths, and
  structure.
- [x] Prove no contour segment is silently discarded.

## 4. Named paran policy presets

- [x] Add `ParanPolicyPreset` with `permissive` and `star_planet_only`.
- [x] Add a strict preset resolver; unknown values must fail.
- [x] Keep `DEFAULT_PARAN_POLICY` behavior unchanged.
- [x] Add optional `policy_preset` to every paran REST request family.
- [x] Forward the effective policy through search, natal, site, stability,
  grid, analysis, contour, path, and structure computation.
- [x] Return the effective preset in REST metadata where applicable.
- [x] Test planet-star admission and star-star/planet-planet rejection under
  `star_planet_only`.
- [x] Defer any `classic_circles` preset until its event-pair doctrine has a
  named source and explicit allowed combinations.

## 5. Natal birth-moment angular contacts

- [x] Define `NatalAngularContact` as a distinct public vessel.
- [x] Add `natal_angular_contacts()` without altering `natal_parans()`.
- [x] Filter individual body crossings by declared time distance from the
  natal moment.
- [x] Preserve circle, crossing JD, natal JD, signed/absolute delta, body
  family, and crossing truth.
- [x] Support planets and catalog-resolved fixed stars.
- [x] Add `POST /v1/parans/natal-angular-contacts`.
- [x] Add engine and REST tests for inside-orb, boundary, outside-orb,
  deterministic ordering, and unknown identities.
- [x] Document the distinction between day parans and moment contacts.

## 6. Workspace paran/star packet

- [x] Add website-only packet models, service, and router.
- [x] Accept selected bodies/stars, canon tiers, policy preset, location, and
  natal JD.
- [x] Compose existing canon, paran, inventory, angular-contact, and heliacal
  truth without recomputing doctrine in transport.
- [x] Make heliacal inclusion explicit and bounded to selected stars.
- [x] Preserve provenance and warnings, including the planetary-kernel prerequisite.
- [x] Keep large geographic grids and contours on their existing endpoints.
- [x] Add `POST /v1/website/parans/packet`.
- [x] Add route discoverability, strict request validation, deterministic
  packet, and direct-engine parity tests.

## 7. Documentation and release gates

- [x] Update the Paran backend standard.
- [x] Update the Stars backend standard where the canon delegates to it.
- [x] Update the API reference and OpenAPI descriptions.
- [x] Run Python compilation checks for every changed module.
- [x] Run the complete paran unit suite in strict known-issue mode.
- [x] Run focused rise/set, star, facade, and server tests.
- [x] Run the offline external-reference paran regression.
- [x] Run documentation consistency validation.
- [x] Run `git diff --check`.
- [x] Perform a sovereignty/lineage smell audit.
- [x] Record exact verification scope, prerequisites, skips, and remaining
  external-validation gaps in the completion receipt.

## Intentionally out of scope

- Editing sovereign star catalog rows or provenance payloads.
- Adding a hidden client-only shortlist.
- Calling the working set a Brady canon without source authority.
- Changing the default permissive paran policy.
- Recasting birth-moment contacts as ordinary two-body parans.
- Reimplementing the existing heliacal astronomy in website transport.
- Publishing, tagging, or version-bumping the package in this implementation
  pass.
