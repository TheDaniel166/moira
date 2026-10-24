# Typed Fortune and predominator composition

Admission date: 2026-10-23. Engine-only, pending the combined release.

## Sources and boundaries

[Ptolemy, Tetrabiblos III.10, Robbins translation, pp. 275-279](https://penelope.uchicago.edu/Thayer/E/Roman/Texts/Ptolemy/Tetrabiblos/3B%2A.html)
defines the unreversed Fortune and the final Ascendant/Fortune alternatives
in the predominator procedure. The existing owner is
`moira/hellenistic_offices.py`; this extension consumes its determination,
without selecting the office again or extending it to longevity judgments.

The alternative sect-reversed Fortune follows the existing `Fortune` definition
and arithmetic in `moira/lots.py`. Its source review is recorded in
`wiki/05_research/lots/LOTS_SOURCE_VERIFICATION.md`. Selecting this convention
does not claim it is Ptolemy's formula or establish another historical school's
complete directional practice.

## Typed configuration

`moira.primary_directions` exports `PrimaryDirectionFortuneDoctrine`,
`PrimaryDirectionFortuneTarget`, `PrimaryDirectionPredominatorTarget`,
`PrimaryDirectionLotTarget`, their
union `PrimaryDirectionDerivedPointTarget`, and
`resolve_primary_direction_derived_point`.

All configuration is opt-in through the appended, empty-by-default
`derived_point_targets` policy field and preset keyword. Existing positional
arguments, defaults, `PrimaryArc` and timeline result shapes, facade exports,
and REST contracts are unchanged. No arbitrary named coordinates are admitted.

```python
from moira.primary_directions import (
    PrimaryDirectionFortuneTarget,
    PrimaryDirectionPredominatorTarget,
    PrimaryDirectionsPreset,
    find_primary_arcs,
    primary_directions_policy_preset,
)

fortune = PrimaryDirectionFortuneTarget()  # explicit Ptolemaic doctrine field
policy = primary_directions_policy_preset(
    PrimaryDirectionsPreset.PTOLEMY_MUNDANE,
    derived_point_targets=(fortune,),
)
arcs = find_primary_arcs(
    chart, houses, geo_lat, policy=policy,
    significators=[fortune.name], promissors=["Mars"],
)

# `determination` is an existing PtolemyPredominatorDetermination, for example
# hunt.predominator_determination from hunt_hellenistic_offices.
selected = PrimaryDirectionPredominatorTarget(determination)
selected_policy = primary_directions_policy_preset(
    PrimaryDirectionsPreset.PTOLEMY_MUNDANE,
    derived_point_targets=(selected,),
)
selected_arcs = find_primary_arcs(
    chart, houses, geo_lat, policy=selected_policy,
    significators=[selected.name], promissors=["Mars"],
)
```

## Computational contract

| Target | Longitude | Ecliptic latitude | Identity |
| --- | --- | --- | --- |
| Ptolemaic Fortune | `(ASC + Moon - Sun) mod 360`, day and night | zero | `Fortune`, class `derived_point` |
| Sect-reversed Fortune | day as above; night `(ASC + Sun - Moon) mod 360` | zero | `Fortune`, class `derived_point` |
| Selected planet | current natal planet longitude | current native planet latitude | original planet name and class |
| Selected Ascendant | current Ascendant | zero | `ASC`, class `angle` |
| Selected Lot of Fortune | Ptolemaic Fortune, regardless of sect | zero | `Fortune`, class `derived_point` |

The sect-reversed target requires an explicit Boolean `is_day_chart`, as the
lots owner does. No sect is inferred from names or a browser clock.
`PrimaryDirectionPredominatorTarget` rejects `not_evaluable` with the original
reason. It does not silently select ASC. Selected planet/ASC identities are
retained rather than duplicating them under a synthetic `Predominator` name.

At resolution, all seven stored planetary longitudes and Ascendant-relative
offsets, Fortune, and the selected longitude must match the supplied figure.
The `1e-9` degree comparison allowance covers floating point normalization of
the stored natal coordinates, not rounded or approximate input. Missing,
nonfinite, stale, or inconsistent source coordinates fail explicitly. Only
requested significators activate this dependency check. Longitude dependencies
do not require projecting the source planets into rise/set semi-arcs.

The determination contains no epoch or complete prenatal input record. This
adapter proves coordinate consistency; it cannot authenticate caller-supplied
sect, epoch, prenatal context, or the origin of a manually constructed office.
Those remain the existing office owner's and caller's contract.

## Admitted geometry and composition

Typed significators are admitted across all eight existing methods and 28
presets. Existing projection, latitude, relation and motion policies govern
each branch; this introduces no geometry law or new office-selection doctrine.
Direct/converse and explicit neo-converse retain their existing meanings.
Method, polar-domain and signed-timeline boundaries are detailed in
`primary_directions_derived_method_admission.md`.

Fortune has its own target class and requires its typed configuration; a bare
string does not create coordinates. It is not admitted as a promissor, aspect
source, midpoint source, or parallel/reflection source. Fixed-star conjunctions
admit native planet/angle significators and explicitly configured typed derived
significators, preserving node/cusp and relation restrictions. Two definitions of
the same canonical target in one policy are rejected, including two conflicting
Fortune conventions. A selected native planet retains its ordinary capabilities.

Timeline construction carries the typed configuration into its separate bound
search and uses the resolved natal longitude. Event filters preserve the
complete direct/converse distributor partition. All six existing time keys use
the engine's existing projection functions, including exact dynamic solar-key
inversion. No display approximations or website benchmark values are involved.

## Validation and limits

`tests/unit/test_primary_directions_derived_points.py` exercises both Fortune
formulas against explicit arithmetic and the existing lots owner; office
composition for Sun, Moon, a ruler, ASC and Fortune; original unresolved
reasons; stale sources; latitude preservation; policy and source-family gates;
all Ptolemy presets; iterable consumption; ordinary-pair preservation; and
all-six-key timeline partitions under event filters. An independent
equatorial-limit calculation checks direct/converse arcs from trigonometric
right ascension, without using the engine's speculum or geometry oracle.

These are construction, composition, and regression proofs, not a new published
historical worked-example corpus. Existing primary-direction geometry, native
parity, office, and transport suites remain required. DE441 supplies natal and
dynamic-key astronomical positions; it does not validate historical doctrine.

Catalogue lots, including Spirit, are now admitted through the same typed
system; their contract is in `primary_directions_catalogue_lots.md`.
Arbitrary custom points, new directional methods, wider Fortune/lot promissor
families, and full office-driven longevity judgments remain outside admission.
