# Moira 6.6.0 - Planet-first Stelliums and Selected-zodiac Houses

Release date: 2026-09-09. Upgrade path: 6.5.0 to 6.6.0.

This release adds an independent, evidence-first concentration product and
corrects selected-zodiac sign-defined houses. It does not rewrite existing
aspect-pattern compatibility surfaces or astronomical reductions.

## Stellium analysis

- Strict requires four planets; Broad three. The canonical ten run from Sun
  through Pluto. Nodes, Chiron, angles, lots and other admitted factors may
  annotate a qualifying group but cannot manufacture one.
- Sign, actual house and tight total circular span are independent criteria.
  Tight defaults to eight degrees total, not a centroid radius or a chained
  conjunction network. Core geometry is frozen before associations are added.
- Identical core membership merges labels; different tight subsets and
  overlapping maximal tight groups remain distinct.
- Typed Python results and `POST /v1/stelliums/analyze` preserve policy,
  full-precision arc evidence, source/frame identity, input fingerprints,
  requested/computed/excluded coverage and criterion-level unavailability.
  The endpoint consumes a supplied chart snapshot without rerunning astronomy.

## House-frame correction

When `ayanamsa_offset` is supplied, Whole Sign and Solar Sign now select the
appropriate sign in that zodiac, including policy-directed Whole Sign
fallbacks. Returned cusp labels remain exact sign boundaries. Physical
quadrant/equal-degree house geometry and equatorial ARMC are not rotated.
Tropical and zero-offset results remain unchanged. Consumers must pair
longitudes and cusps in the same frame and must not apply an offset twice.

## Verification scope

Focused unit/server contracts cover planet-vs-point counts, independent
criteria, wrap/coincident/exact boundaries, rotation, partial evidence,
malformed snapshots, deterministic IDs, public exports and HTTP/Python parity.
House-frame regressions exercise both sign-defined systems, actual membership,
unchanged physical boundaries, ARMC and polar Whole Sign fallback. Existing
pattern/aspect compatibility checks remain part of the release gate. Synthetic
geometry and DE441 integration fixtures do not imply a new external ephemeris
accuracy certification. No native C++ algorithm or external catalog changed.

## Migration

Read [STELLIUM_ANALYSIS_STANDARD.md](../02_standards/STELLIUM_ANALYSIS_STANDARD.md)
and [COMPATIBILITY_NOTES_6.6.0.md](COMPATIBILITY_NOTES_6.6.0.md). Install
`moira-astro==6.6.0`; server consumers use `moira-astro[server]==6.6.0`.
Workspace/website deployment is a separate staged consumer release and is not
implied merely by publication of this engine package.
