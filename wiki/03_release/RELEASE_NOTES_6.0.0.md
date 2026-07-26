# Moira 6.0.0 - Hellenistic Engine Completion

**Release date:** 2026-07-26
**Public upgrade path:** 5.2.3 to 6.0.0

Moira 6.0.0 completes the six-gate Hellenistic engine program. It replaces
collapsed labels and speculative defaults with source-visible, typed truth;
aligns the Python, facade, REST, serializer, and OpenAPI contracts; and adds a
single non-interpretive Hellenistic chart profile assembled from the exact
admitted components.

This is an engine and transport release. It does not claim that a dedicated
hosted Hellenistic website experience has shipped.

## Why This Is A Major Release

Version 6.0.0 removes formerly curated Hermetic decan symbols whose doctrine
was not supportable from the identified source. That public import removal is
a breaking API change under Semantic Versioning.

The release also changes several incorrect or ambiguous compatibility outputs
to fail closed. Callers that treated missing dependencies as `False`, empty, or
an inferred default must now consume the typed evaluation receipts.

## The Six Completed Gates

### 1. False-output containment

The engine no longer emits results for unsupported or incomplete doctrine:

- Dorothean water triplicity uses the corrected ordering.
- Required luminaries fail closed when absent.
- The two verified lot reversals are corrected.
- Zodiacal Releasing angularity and exact-boundary behavior are corrected.
- Decennial L3/L4 remain unavailable.
- Hermetic catalog projections and night-hour experiments remain outside the
  curated public surface.

### 2. Doctrine decisions

Previously ambiguous rules now have explicit source or policy ownership:

- annual profections use completed civil anniversaries in the natal timezone;
- February 29 births require an explicit February 28 or March 1 policy;
- Decennials preserve a 30-day-month/360-day-year distribution coordinate
  separately from elapsed-Julian-day projection;
- Halb uses the admitted sect-relative hemisphere rule and Hayz adds the
  planet's sign gender;
- the Valens IV.4 same-sign start shift and exact 211-month circuit boundary
  are source-fixtured;
- conflicted lots remain separately source-named instead of being silently
  harmonized; and
- the Hermetic name-and-planetary-face catalog is tied to Gundel's 1936
  transcription of Harley MS 3731, while unsupported fixed-star assignments
  fail closed.

### 3. Typed truth composition

The governing Hellenistic result is now a component receipt, not a single
label or synthetic score. Typed truth covers:

- essential dignity components;
- horizon, sect, Mercury phase, planetary solar phase, and solar proximity;
- besieging dependency completeness and geometry;
- lot computation, dependency completeness, condition status, and
  `not_evaluable` results;
- profection activation;
- Decennial sequence assembly;
- Zodiacal Releasing Fortune angularity; and
- whole-sign direction, overcoming, and superiority.

Compatibility strings, lists, booleans, and legacy score-bearing condition
surfaces remain projections. They do not replace the raw component truth.

### 4. Contract parity

The admitted objects and policies have the same effective meaning through:

- owning engine modules;
- `moira` root exports;
- `moira.classical`;
- `moira.facade` and `Moira` methods;
- explicit serializers;
- typed FastAPI request and response models; and
- OpenAPI schema references.

Lots transport now preserves unresolved entries and aggregate
`not_evaluable` counts rather than silently dropping them.

### 5. Unified Hellenistic profile

`HellenisticChartProfile` composes one score-free chart receipt from:

- Whole Sign geometry;
- the seven classical planets;
- typed planetary condition components;
- Whole Sign aspects and superiority;
- Fortune, Spirit, Eros (Valens), and Necessity (Valens);
- annual profection activation;
- current Decennial L1/L2 periods; and
- current Zodiacal Releasing periods.

The engine entry points are:

```python
from moira import Moira, hellenistic_chart_profile
```

The REST entry point is:

```text
POST /v1/hellenistic/chart-profile
```

The profile requires explicit, valid inputs: all seven classical planets,
finite speeds, valid Whole Sign geometry, actual Ascendant and Midheaven
angles, and timezone-aware natal/current datetimes. It does not silently
substitute missing dependencies.

### 6. Validation and documentation regeneration

The release adds independent, source-owned goldens for:

- the Dorothean triplicity table;
- planetary joys;
- admitted Egyptian, Ptolemaic, Valens, and Chaldean bounds;
- all 36 ordinary Chaldean faces;
- the four unified-profile lots;
- Decennial L1/L2 arithmetic; and
- the Valens IV.4 same-sign and 211-month Zodiacal Releasing cases.

Generated capability and API inventories are now checked against runtime and
OpenAPI truth. The website documentation publication bundle is version-pinned
and drift-detectable.

## Hermetic Boundary

The direct `moira.hermetic_decans` module retains a source-reconstructed
research catalog and explicitly qualified lookup geometry. It is not curated
through the root, classical, facade, or REST product surfaces.

The following were removed from curated exports:

- `DecanHour`
- `DecanHoursNight`
- `DECAN_NAMES`
- `DECAN_RULING_STARS`
- `list_decans`
- `available_decans`
- `decan_for_longitude`
- `decan_at`
- `decan_hours`

All dormant Hermetic FastAPI models, services, serializers, and routes were
also removed. The identified Gundel/Harley witness provides names and
planetary faces, not the former one-fixed-star-per-decan table or the removed
night-hour algorithm.

## Explicit Exclusions

Moira 6.0.0 does not admit or imply:

- Firdaria as Hellenistic doctrine;
- medieval almutens;
- later electional rules;
- unscoped primary-direction branches;
- Decennial L3/L4;
- Hermetic fixed-star attribution or public geometry;
- Valens distribution interpretation;
- Triacontaeteris;
- a chart-wide score, ranking, recommendation, or predictive narrative.

These are typed or documented exclusions, not unfinished pieces of the
six-gate engine contract.

## Release Validation

Release hardening enforces:

- strict known-issue expiry;
- Hellenistic source goldens;
- generated capability/API inventory drift checks;
- root/classical/facade/server contract parity;
- unified-profile and OpenAPI behavior;
- absence of all Hermetic REST paths and transport symbols;
- REST-reference and website-publication regeneration;
- documentation consistency;
- release identity; and
- Python compilation and packaging checks.

The final local release candidate passed:

- all 944 collected focused Hellenistic engine, facade, serializer, REST, and
  OpenAPI tests under strict known-issue mode; and
- all 11,703 collected deterministic non-network repository tests, with 13
  declared skips for unavailable optional resources/comparators or explicitly
  deferred oracle cases and no failures.

The authoritative gate receipt is
`wiki/06_roadmap/hellenistic_completion/HELLENISTIC_ENGINE_GATES_2026-07.md`.

## Installation

```text
moira-astro==6.0.0
```

Server users should install the server extra:

```text
moira-astro[server]==6.0.0
```
