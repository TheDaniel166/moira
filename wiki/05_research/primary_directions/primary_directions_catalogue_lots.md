# Catalogue lots as typed primary-direction targets

Admission date: 2026-10-23. Engine-only, staged for the combined release.

## Governing object and scope

`PrimaryDirectionLotTarget` composes the existing `moira/lots.py` catalogue
with the typed primary-direction target system. The catalogue, its named
variants, projector, directed/shortest arc, reversal rule and dependency
policies remain the formula authority. No formula was added or corrected by
this extension. Historical source verification remains in
`wiki/05_research/lots/LOTS_SOURCE_VERIFICATION.md`.

This is an explicit mathematical composition across all eight existing methods
and 28 presets. It does not assert that every catalogue lot was historically
directed in each school or that every source school's complete practice is
implemented. Lots remain significators with assigned zero ecliptic latitude.
No new promissor or derived-promissor source roles are admitted.

## Typed interface

The only new public Python symbol is `PrimaryDirectionLotTarget`, exported
from `moira.primary_directions`. It joins the existing
`PrimaryDirectionDerivedPointTarget` union and uses the already optional
`derived_point_targets` policy field/preset keyword. No public signature,
default, root/facade export, REST contract or result shape changes.

```python
from moira.primary_directions import (
    PrimaryDirectionLotTarget,
    PrimaryDirectionsPreset,
    find_primary_arcs,
    primary_directions_policy_preset,
)

spirit = PrimaryDirectionLotTarget("Spirit", is_day_chart=True)
basis = PrimaryDirectionLotTarget("Basis (Valens)", is_day_chart=True)
policy = primary_directions_policy_preset(
    PrimaryDirectionsPreset.PTOLEMY_MUNDANE,
    derived_point_targets=(spirit, basis),
)
arcs = find_primary_arcs(
    chart, houses, geo_lat, policy=policy,
    significators=[spirit.name, basis.name], promissors=["Mars"],
)
```

`lot_name` must be an exact, unique catalogue name. `is_day_chart` is a required
Boolean. Optional fields mirror the existing lots context:
`policy: LotsComputationPolicy`, `syzygy`, `prenatal_new_moon`,
`prenatal_full_moon`, and `lord_of_hour`. The four external values are finite
ecliptic longitudes, normalized modulo 360. Sect, syzygies and hour rulers are
not inferred or searched for by the adapter. Their epoch, frame and relevance
to the natal figure remain the caller's responsibility.

Names are `Lot: Spirit`, `Lot: Basis (Valens)`, and so on. Catalogue Fortune
retains the existing canonical `Fortune` identity and the catalogue's sect-
reversed formula. `Lot: Fortune` is not a second identity. Multiple definitions
of one canonical target are rejected, including catalogue Fortune together with
an explicit Ptolemaic Fortune or a Fortune-selected predominator.

The frozen vessel contains recipe identity and explicit context, never a cached
longitude, a mutable `ArabicPart`, or user-supplied arbitrary point coordinates.
Each resolution uses the current chart and houses. Named lots have the existing
`derived_point` target class. A known string classifies identity but cannot
construct coordinates without typed configuration.

## Calculation and source binding

The lots owner now has a module-private `_evaluate_lot_definitions` operation shared by
the unchanged full-catalogue `evaluate_parts` operation and the directional
adapter. Reference resolution, formula arithmetic and typed computation truth
are unchanged. Selected evaluation neither mutates the global catalogue nor
copies its arithmetic into primary directions.

Requested targets are grouped by their complete explicit context and evaluated
in one owner call per group. Groups, reference dictionaries and coordinates
are request-local; there is no persistent or cross-chart result cache. A point
excluded by the significator filter never activates lot evaluation.

The adapter supplies finite natal longitudes from the engine's body registry
and node aliases, the actual Ascendant and Midheaven, and all 12 finite house
cusps. Ordered cusp sequences and complete one-indexed cusp maps are accepted
by the resolver. Native planetary latitude is not an ingredient or a reason to
project source bodies into rise/set semi-arcs. A lot may resolve without the
luminaries when its recipe does not depend on them.

Fortune, Spirit and other synthetic entries injected into a chart's body maps
cannot replace owner-derived references or bypass dependency policy. Likewise,
a synthetic natal `Fortune` or `Lot: ...` entry cannot replace a typed point's
computed coordinates. The natal-speculum search excludes derived identities
and admits their coordinates only through typed resolution.

All catalogue semantics survive this composition: inter-lot dependencies,
house/planet/syzygy rulers, fixed-degree references, night reversal,
`Basis (Valens)` shortest arc, and the Saturn projector of `Theft (Valens)`.
A fixed-degree catalogue ingredient retains its owner's meaning and precision;
it is not silently replaced by an exact star reduction or another doctrine.

## Missing references and policy

The adapter preserves the existing derived/external admission policies. Missing
or policy-excluded ingredients do not acquire fabricated zero-degree values.
Only selected recipes are evaluated, so unrelated unresolved catalogue entries
cannot block construction, including when the supplied lots policy uses RAISE.

A requested directional point needs a coordinate under either SKIP or RAISE.
Selected evaluation therefore obtains the owner's typed not-evaluable receipt
using its receipt-producing mode and raises `ValueError` containing the target
name, original reason and missing-reference names. SKIP does not silently
remove a requested significator from a directional search. Public lots
SKIP/RAISE behavior is unchanged.

## Directional integration and validation

Every admitted preset retains typed lot configuration. Ordinary native
targets and all existing geometry, motion, latitude and relation laws retain
their prior meaning. Namespaced lot identities cannot enter the aspect,
midpoint, reflection or parallel source paths. Fixed-star conjunctions admit
explicitly configured typed significators alongside native planets/angles,
without admitting node/cusp significators or wider stellar relations.

Timeline construction retains the typed configuration in its independent bound
search and uses resolved natal longitudes. All six existing keys continue to
use the engine's projection functions, including exact dynamic solar-key
inversion. Event promissor filters preserve the complete bound partition.

`tests/unit/test_primary_directions_lots.py` compares every current catalogue
definition against the lots owner by day and night with complete context:
512 definitions across eight methods, 8,192 coordinate comparisons. This is owner-composition
regression evidence, not an independent historical oracle. Separate explicit
arithmetic checks cover reversible, non-reversible, dependent, shortest-arc and
non-Ascendant-projector formulas. An independent trigonometric equatorial-limit
oracle checks direct and converse arcs without using the production speculum.
Missing/policy-excluded references, source substitution, immutable/context
validation, batch separation, current-chart resolution, preset retention,
default preservation and all-six-key mundane/zodiacal timelines are covered.

Existing lots, primary-direction, predominator, native-parity and transport
regressions remain required. No native law was changed and no numerical port
is implied. New methods, lot promissors, derived-promissor source roles and
arbitrary custom formulas remain outside this admission.

The complete cross-method contract, existing domain/motion restrictions and
additional validation are in `primary_directions_derived_method_admission.md`.
