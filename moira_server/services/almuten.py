"""Service layer for the almuten routes. Doctrine stays in moira.dignities."""

from __future__ import annotations

from moira.dignities import (
    AlmutenDetermination,
    AlmutenDoctrine,
    almuten_figuris_determination,
    almuten_of_degree_determination,
)

from ..models.almuten import (
    AlmutenDegreeRequest,
    AlmutenFigurisRequest,
    AlmutenProvenanceResponse,
    AlmutenResponse,
    AlmutenScoredPointResponse,
    AlmutenTallyResponse,
)


_LILLY_TABLE = (
    "William Lilly, Christian Astrology (1647), Book I ch. XVIII, "
    "Table of the Essential Dignities of the Planets according to Ptolomy, p. 104"
)
_LILLY_DEGREE_SOURCE = (
    f"{_LILLY_TABLE}; almuten of a house, Book I ch. VI, p. 49"
)
_LILLY_FIGURIS_SOURCE = (
    f"{_LILLY_TABLE}; Lilly's own rule, Book I ch. VI p. 49 and Book III ch. CV "
    "pp. 531-532: most essential and accidental dignities in the whole figure, "
    "scored by the ready table of fortitudes and debilities, Book I ch. XIX, p. 115"
)
_LILLY_OTHERS_SOURCE = (
    f"{_LILLY_TABLE}; places counted as reported (not adopted) in Book III ch. CV, "
    "p. 531 (Ascendant, mid-heaven, Sun, Moon, Part of Fortune); Part of Fortune "
    "Asc + Moon - Sun by day and night, Book I p. 143"
)
_LILLY_NOT_COMPUTED = [
    "posited_best_and_elevated_most_lilly_book_iii_ch_cv_p_532",
]
_LILLY_OTHERS_NOT_COMPUTED = [
    "lilly_own_rule_accidental_dignities_over_the_whole_figure_p_532",
]
_LEGACY_SOURCE = "Moira pre-6.9.9 count (moira_legacy_v1); scale per Lilly 1647 p. 115"
_PARTICIPATING_AWARD = "participating_triplicity_ruler_awarded_1_point"
_ACCIDENTAL_WEIGHTS = (
    "house_points_1st_12_to_12th_1_and_day_ruler_7_hour_ruler_6"
)


def _provenance(
    determination: AlmutenDetermination,
    *,
    doctrine: AlmutenDoctrine,
    entrypoint: str,
    figuris: bool,
) -> AlmutenProvenanceResponse:
    if doctrine in (
        AlmutenDoctrine.WILLIAM_LILLY_1647,
        AlmutenDoctrine.WILLIAM_LILLY_1647_OTHERS_FIVE_PLACES,
    ):
        others = doctrine is AlmutenDoctrine.WILLIAM_LILLY_1647_OTHERS_FIVE_PLACES
        if not figuris:
            source, not_computed = _LILLY_DEGREE_SOURCE, []
        elif others:
            source, not_computed = _LILLY_OTHERS_SOURCE, list(_LILLY_OTHERS_NOT_COMPUTED)
        else:
            source, not_computed = _LILLY_FIGURIS_SOURCE, list(_LILLY_NOT_COMPUTED)
        return AlmutenProvenanceResponse(
            engine_entrypoint=entrypoint,
            doctrine_source=source,
            bounds_table="william_lilly_1647",
            triplicity_table="william_lilly_1647",
            unsourced_elements=[],
            not_computed=not_computed,
            tie_break=determination.tie_break,
        )
    return AlmutenProvenanceResponse(
        engine_entrypoint=entrypoint,
        doctrine_source=_LEGACY_SOURCE,
        bounds_table="egyptian",
        triplicity_table="dorothean_pingree_1976",
        unsourced_elements=(
            [_PARTICIPATING_AWARD, _ACCIDENTAL_WEIGHTS] if figuris else [_PARTICIPATING_AWARD]
        ),
        not_computed=[],
        tie_break=determination.tie_break,
    )


def _serialize(
    determination: AlmutenDetermination,
    provenance: AlmutenProvenanceResponse,
) -> AlmutenResponse:
    return AlmutenResponse(
        doctrine=determination.doctrine,
        almuten=determination.almuten,
        is_day_chart=determination.is_day_chart,
        tallies=[
            AlmutenTallyResponse(
                planet=tally.planet,
                essential_points=tally.essential_points,
                house_points=tally.house_points,
                ruler_points=tally.ruler_points,
                accidental_points=tally.accidental_points,
                total=tally.total,
            )
            for tally in determination.tallies
        ],
        scored_points=[
            AlmutenScoredPointResponse(name=point.name, longitude=point.longitude)
            for point in determination.scored_points
        ],
        tied_planets=list(determination.tied_planets),
        reason=determination.reason,
        provenance=provenance,
    )


def compute_almuten_of_degree(request: AlmutenDegreeRequest) -> AlmutenResponse:
    determination = almuten_of_degree_determination(
        request.longitude,
        request.is_day_chart,
        doctrine=request.doctrine,
    )
    return _serialize(
        determination,
        _provenance(
            determination,
            doctrine=request.doctrine,
            entrypoint="almuten_of_degree_determination",
            figuris=False,
        ),
    )


def compute_almuten_figuris(request: AlmutenFigurisRequest) -> AlmutenResponse:
    determination = almuten_figuris_determination(
        dict(request.positions),
        list(request.house_cusps),
        request.is_day_chart,
        prenatal_syzygy_lon=request.prenatal_syzygy_longitude,
        day_ruler=request.day_ruler,
        hour_ruler=request.hour_ruler,
        doctrine=request.doctrine,
        midheaven_longitude=request.midheaven_longitude,
        speeds=None if request.speeds is None else dict(request.speeds),
        north_node_longitude=request.north_node_longitude,
        node_doctrine=request.node_doctrine,
        fixed_star_longitudes=(
            None if request.fixed_star_longitudes is None else dict(request.fixed_star_longitudes)
        ),
    )
    return _serialize(
        determination,
        _provenance(
            determination,
            doctrine=request.doctrine,
            entrypoint="almuten_figuris_determination",
            figuris=True,
        ),
    )
