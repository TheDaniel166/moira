# Moira 5.1.0 — Source-Scoped Pancha Pakshi and Explicit Dignity Policy

**Release date:** 2026-07-21

**Public upgrade path:** 5.0.0 to 5.1.0

Moira 5.1.0 adds a first-class, source-scoped Pancha Pakshi subsystem and makes
Halb and Oriental/Occidental dignity inclusion independently selectable. It
also strengthens bulk eclipse-range execution, adds public Gauquelin validation
evidence, and closes several release-validation gaps discovered while preparing
the package.

The release remains governed by explicit policy and provenance. Pancha Pakshi
does not select a universal canon, invent a numerical score, or turn research
conflicts into prognostic truth. Dignity switches control the inclusion of
already computed conditions; they do not alter the underlying astronomical or
sect geometry.

## Highlights

- Source-scoped Pancha Pakshi is available through immutable engine vessels,
  package-root exports, `Moira` facade methods, and typed `/v1/pancha-pakshi`
  REST routes.
- Fixed-clock and solar-proportional timing remain separate, explicitly named
  policies. No Pancha Pakshi profile is selected by default.
- Uromarisi constitutional evidence is inspectable across activity,
  classification, relation, condition, aggregate, network, and public-status
  layers without collapsing documented conflicts.
- Dignity callers can independently include or exclude Halb, Hayz, and
  Oriental/Occidental conditions through engine and REST policy vessels.
- Bulk solar and lunar eclipse ranges can use conservative native TT candidate
  discovery while Python retains time policy, physical refinement,
  classification, inclusive-range semantics, and result assembly.
- The g5 Gauquelin validation harness now carries explicit historical-dataset
  scope and validation evidence.

## Pancha Pakshi public boundary

The admitted public profile is
`agastya_madras_1879_akshara_fixed_clock`. Its authority is limited to the
source product and locators recorded in its manifest. The API exposes profile
discovery, aksara identity, schedules, source-scoped mappings, temporal
selection, materialization, current-cell selection, relations, conditions,
aggregates, networks, and constitution status.

The following boundaries are deliberate:

- profile selection is explicit and fails closed;
- fixed-clock and solar-proportional composition are different policies;
- exact rational nazhigai values remain fractions in Python and serialize as
  numerator/denominator pairs;
- research witnesses and conflicting cells retain their own admission status;
- no generic good/bad score, forecast, or empirical efficacy claim is added.

## Dignity policy controls

`DignityComputationPolicy` now reaches independent accidental-condition
controls:

- `SectHayzPolicy.include_hayz`;
- `SectHayzPolicy.include_halb`;
- `AccidentalDignityPolicy.include_oriental_occidental`.

All default to `True`, preserving 5.0.0 output. Setting one to `False` removes
that condition's label, structured truth vessel, and additive contribution.
It does not mutate planetary phase, sect, house placement, or longitude.

The same policy is accepted by all six dignity REST routes. The quarantined
Valens distribution option remains unavailable rather than being exposed as an
inert switch.

## Astronomical and validation hardening

`find_phenomena()` now treats a missing meridian crossing inside its exact
24-hour search window as an absent event key. This matters for the Moon, whose
successive meridian crossings can be separated by more than 24 hours.
`get_transit()` remains fail-closed when its requested window contains no
bracket, so direct callers retain explicit failure semantics.

Release preparation also aligned the physics-layer node reference with the
reader-owned ephemeris clock, removed a false repository-wide prohibition on
supported annotation syntax, made kernel-backed property tests independent of
cold-cache timing, restored the session kernel after a state-mutating manifest
test, and refreshed one deterministic DE441 regression fixture affected by the
admitted clock correction.

## Evidence boundaries

Pancha Pakshi source-table tests and constitutional invariants establish
source fidelity and structural coherence, not empirical astrological efficacy.
DE441-backed tests exercise astronomical routing and time conversion; they are
not historical Pancha Pakshi oracles. Gauquelin historical-dataset tests are
bounded to their named corpus. Snapshot and fixed-value tests remain regression
evidence rather than external authority validation.

## Publication

Pushing the `v5.1.0` tag triggers the repository's GitHub Actions publication
workflow. Its cibuildwheel matrix produces the supported platform and Python
wheels and publishes them to PyPI. Local wheel production is not part of the
release procedure.
