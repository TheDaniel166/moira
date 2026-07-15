# Moira 4.3.0 — Source-Owned Western Electional Profiles

Moira 4.3.0 expands Western electional astrology from one bounded Moon
condition into three independent historical lineages, a shared Dorothean
root-and-matter context, the first source-complete matter profile, and a
bounded profile-status scanner. Every admitted object is public through the
engine, `Moira` facade, and typed REST API.

## Sahl and Dorotheus Moon conditions

The release adds two Moon-condition profiles beside the existing Ramesey
profile:

- `sahl_moon_condition_v1`, following Sahl bin Bishr's ten impediments in
  *On Elections* section 22;
- `dorotheus_moon_condition_v1`, following the eleven corruption clauses in
  Dorotheus, *Carmen Astrologicum* V.6.3-14 and preserving V.6.15 as a separate
  remedy instruction.

Public REST routes are:

- `POST /v1/electional/western/sahl-moon-condition`
- `POST /v1/electional/western/dorotheus-moon-condition`

Sahl's unstated burnt-path endpoints and conflicting Arabic/Latin eighth-rule
readings remain named policies. Dorotheus's underdetermined southern-descending
and longitude-or-latitude disengagement clauses remain measured but
`not_evaluable`; later orbs and modern proxies are not imported silently.

## Dorothean root, outcome, and matter context

`dorotheus_rooted_context_v1` makes the shared V.6/V.31 structure explicit:

- the Moon is the root of the work;
- the lord of the Moon's sign describes the outcome;
- the first exact traditional Moon connection is searched only until sign
  exit;
- six matter-significator families remain distinct;
- ephemeral elections reject natal inputs, while radical elections require a
  complete natal moment, location, and house-system bundle.

It is available through `Moira.dorotheus_rooted_context_at(...)` and
`POST /v1/electional/western/dorotheus-rooted-context`. Undefined V.31
"bad-place" and broader accidental-misfortune semantics remain visible
uncomputed requirements.

## First source-complete matter profile

`dorotheus_construction_v1` composes Dorotheus V.2-V.6, V.31, and every V.7
construction clause. It exposes sign tempo, convertible and twin-sign effects,
sect fit, Moon condition, root/outcome evidence, matter significators, lunar
light, and benefic/malefic strong-place witnesses.

Public access is available through:

- `dorotheus_construction_at(...)`
- `Moira.dorotheus_construction_at(...)`
- `POST /v1/electional/western/dorotheus-construction`

The result distinguishes completeness precisely:

- `source_complete: true`
- `complete_matter_profile: true`
- `numerically_complete: false`
- `complete_electional_judgement: false`

Increasing in calculation requires a lawful mean-lunar-position/equation
product, and "on the ecliptic, rising north" lacks a source-defined crossing
region or tolerance. Moira preserves both clauses without inventing answers.

## Bounded profile-status windows

The three Moon-condition profiles can now be scanned through:

- `scan_western_electional_profile(...)`
- `Moira.western_electional_profile_windows(...)`
- `POST /v1/electional/western/profile-windows`

Callers must explicitly select one or more qualifying statuses:

- `clear_of_profile_impediments`
- `one_or_more_profile_impediments`
- `indeterminate`

Every sampled instant reports its status, qualification truth, triggered rule
IDs, and not-evaluable rule IDs. Adjacent qualifying samples may be merged
under an explicit gap policy, but the result makes no claim that truth is
continuous between samples or that an exact transition boundary was solved.

REST scanning is limited to 256 points with a minimum one-hour cadence.
Ramesey and Sahl reuse range-level void-of-course windows rather than repeating
the same sign-level search at every point. A local DE441 performance smoke at
the 256-point cap completed in approximately 1.2 seconds for each of those two
profiles on the release workstation; this is operational performance evidence,
not scientific validation or a cross-platform guarantee.

## Compatibility

All electional engine, facade, and REST entry points are additive relative to
4.2.1. The profile-window surface was not present in a released version, so its
explicit `qualification_statuses` requirement does not break a published
contract.

No existing generic electional predicate, numeric-fit scorer, relationship
route, or response envelope is removed or renamed. Version 4.3.0 does not
introduce electional scores, rankings, recommendations, remedy-fulfillment
claims, or empirical claims for astrological doctrine.

## Validation

Release evidence uses the project `.venv` on Python 3.14 with downloads
disabled, strict known-issue expiry, and the discovered DE441 kernel. It
includes:

- source-order, threshold, boundary, variant, and indeterminacy tests for the
  Ramesey, Sahl, and Dorotheus Moon profiles;
- rooted-context, natal-contract, next-connection, and matter-significator
  tests;
- V.2-V.7 construction invariants and explicit unresolved-clause tests;
- exact public-export and facade-method governance;
- typed REST serialization and OpenAPI schema checks for every route;
- DE441 parity between optimized profile scans and independent single-moment
  evaluations;
- documentation consistency and release-version alignment.

These checks establish source fidelity, computational invariants, regression
protection, and transport visibility for the stated products. They do not
establish empirical validity for astrological claims.
