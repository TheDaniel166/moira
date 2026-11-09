# Compatibility Notes - Moira 6.13.0

Python 3.10 through 3.15 are supported. REST changes are additive, apart from the
result values described below.

## Behaviour changes

- **Zariel cusps change.** House 1 now starts at RAMC + 90 degrees in right
  ascension instead of the Ascendant's right ascension. Stored Zariel charts need
  recalculating.
- **Generated harmonic layout names change.** `pattern.name` and
  `geometry.template_name` report family names, such as `Novile Triangle 1-2-3`
  for `H9 Triangle 1-2-3`, and `Seminovile Rectangle 1-8` for `Rectangle 1/18`.
  The numbered forms remain in `GeometricPatternTemplate.aliases`. Code that
  compares the old strings must change.
- **A preset layout matching a registered pattern reports under that name.**
  `H4 Triangle 1-1-2` is now `T-Square`, with its apex, and deduplicates with the
  named detector.
- **More patterns receive a grade.** Patterns that returned `Not assessed` now
  return a band, unless they are Stelliums or caller-supplied templates. The six
  v1 templates keep their bands.
- **The coherence policy identifier is now**
  `moira.pattern_coherence.qualitative.v2-draft`. Code that compares it must
  change.

## Additions

- `find_all_patterns`, `find_geometric_patterns` and `PatternComputationPolicy`
  accept `orbs` and `pattern_orbs`. Each named detector accepts `orbs` and
  `pattern_orb`.
- Pattern REST requests accept `orbs` and `pattern_orbs`. Responses add
  `detection_truth.applied_orbs`, and `computation_truth.orbs` and
  `computation_truth.pattern_orbs`.
- `pattern_default_orbs()` and `GET /v1/patterns/default-orbs` publish the
  default limits, and pattern geometry on REST adds `aliases`.
- `evaluate_pattern_coherence`, its result types, `FROZEN_REFERENCE_ORBS` and
  `PATTERN_COHERENCE_POLICY_ID` are exported from `moira` and `moira.facade`.
- Five house system codes: `AT`, `MS`, `SP`, `SA` and `P5`.

## Unchanged

- With no orb settings, pattern detection finds the same patterns as 6.12.1.
- Coherence bands, aggregation and motion qualifiers.
- `orb_factor` behaves as before when no `orbs` are passed.
