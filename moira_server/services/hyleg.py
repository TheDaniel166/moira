"""Service layer for the hyleg route. Doctrine stays in moira.longevity."""

from __future__ import annotations

from moira.longevity import (
    HylegDetermination,
    HylegiacalPlaceTruth,
    find_alcocoden_lilly_1647,
    find_hyleg_lilly_1647,
)

from ..models.hyleg import (
    AlcocodenCandidateResponse,
    AlcocodenLilly1647Request,
    AlcocodenLilly1647Response,
    HylegDominionCountResponse,
    HylegLilly1647Request,
    HylegLilly1647Response,
    HylegiacalPlaceResponse,
)


def compute_hyleg_lilly_1647(request: HylegLilly1647Request) -> HylegLilly1647Response:
    determination = find_hyleg_lilly_1647(
        request.sun_longitude,
        request.moon_longitude,
        list(request.house_cusps),
        request.is_day_chart,
        armc=request.armc,
        obliquity=request.obliquity,
        geographic_latitude=request.geographic_latitude,
        planet_positions=None if request.planets is None else dict(request.planets),
        prenatal_new_moon_longitude=request.prenatal_new_moon_longitude,
        prenatal_full_moon_longitude=request.prenatal_full_moon_longitude,
        latest_prenatal_syzygy=request.latest_prenatal_syzygy,
    )
    return _hyleg_response(determination)


def compute_alcocoden_lilly_1647(request: AlcocodenLilly1647Request) -> AlcocodenLilly1647Response:
    determination = find_alcocoden_lilly_1647(
        dict(request.positions),
        list(request.house_cusps),
        request.is_day_chart,
        armc=request.armc,
        obliquity=request.obliquity,
        geographic_latitude=request.geographic_latitude,
        prenatal_new_moon_longitude=request.prenatal_new_moon_longitude,
        prenatal_full_moon_longitude=request.prenatal_full_moon_longitude,
        latest_prenatal_syzygy=request.latest_prenatal_syzygy,
    )
    return AlcocodenLilly1647Response(
        doctrine=determination.doctrine,
        status=determination.status,
        hyleg=_hyleg_response(determination.hyleg),
        hyleg_longitude=determination.hyleg_longitude,
        alcocoden=determination.alcocoden,
        selection_basis=determination.selection_basis,
        candidates=[
            AlcocodenCandidateResponse(
                planet=candidate.planet,
                longitude=candidate.longitude,
                essential_points=candidate.essential_points,
                dignities=list(candidate.dignities),
                aspect_to_hyleg=candidate.aspect_to_hyleg,
                aspect_distance_deg=candidate.aspect_distance_deg,
                orb_deg=candidate.orb_deg,
                beholds_hyleg=candidate.beholds_hyleg,
                eastern=candidate.eastern,
            )
            for candidate in determination.candidates
        ],
        sign_ruler_of_hyleg=determination.sign_ruler_of_hyleg,
        alcocoden_house=determination.alcocoden_house,
        years_least=determination.years_least,
        years_mean=determination.years_mean,
        years_greater=determination.years_greater,
        angular_in_first_or_tenth=determination.angular_in_first_or_tenth,
        reason=determination.reason,
    )


def _place_response(candidate: HylegiacalPlaceTruth) -> HylegiacalPlaceResponse:
    return HylegiacalPlaceResponse(
        body=candidate.body,
        longitude=candidate.longitude,
        strict_house=candidate.strict_house,
        orb_house=candidate.orb_house,
        above_horizon=candidate.above_horizon,
        oblique_ascension_below_ascendant_deg=(
            candidate.oblique_ascension_below_ascendant_deg
        ),
        is_hylegiacal=candidate.is_hylegiacal,
        reason=candidate.reason,
    )


def _hyleg_response(determination: HylegDetermination) -> HylegLilly1647Response:
    return HylegLilly1647Response(
        doctrine=determination.doctrine,
        status=determination.status,
        hyleg=determination.hyleg,
        is_day_chart=determination.is_day_chart,
        candidates=[_place_response(candidate) for candidate in determination.candidates],
        both_luminaries_hylegiacal=determination.both_luminaries_hylegiacal,
        reason=determination.reason,
        selection_step=determination.selection_step,
        hyleg_longitude=determination.hyleg_longitude,
        dominion_places=dict(determination.dominion_places),
        dominion_counts=[
            HylegDominionCountResponse(
                planet=count.planet,
                dignities_by_place={name: list(kinds) for name, kinds in count.dignities_by_place},
                dignity_count=count.dignity_count,
                points=count.points,
                qualifies=count.qualifies,
            )
            for count in determination.dominion_counts
        ],
        dominion_planet=determination.dominion_planet,
        dominion_planet_place=(
            None
            if determination.dominion_planet_place is None
            else _place_response(determination.dominion_planet_place)
        ),
        part_of_fortune_place=(
            None
            if determination.part_of_fortune_place is None
            else _place_response(determination.part_of_fortune_place)
        ),
    )
