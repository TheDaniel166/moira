from __future__ import annotations

from dataclasses import replace

import pytest

from moira.dignities import (
    AccidentalDignityPolicy,
    DignityComputationPolicy,
    DignityHorizonFrame,
    DignityScoringMode,
    DignityScoringPolicy,
    EgyptianBoundsDoctrine,
    EssentialDignityDoctrine,
    EssentialDignityKind,
    EssentialDignityPolicy,
    MutualReceptionPolicy,
    ParticipatingRulerPolicy,
    SectHayzPolicy,
    SolarConditionPolicy,
    calculate_dignities,
    is_in_hayz,
)


def _houses(start: float = 0.0) -> list[dict]:
    return [
        {"number": index + 1, "degree": (start + index * 30.0) % 360.0}
        for index in range(12)
    ]


def _quiet_accidental(*, include_motion: bool = False) -> AccidentalDignityPolicy:
    return AccidentalDignityPolicy(
        include_house_strength=False,
        include_motion=include_motion,
        include_speed=False,
        include_lunar_phase=False,
        include_oriental_occidental=False,
        include_planetary_aspects=False,
        include_node_contacts=False,
        include_fixed_star_contacts=False,
        include_besieging=False,
        include_joy=False,
        solar=SolarConditionPolicy(
            include_cazimi=False,
            include_combust=False,
            include_under_sunbeams=False,
            include_free_from_beams=False,
        ),
        sect=SectHayzPolicy(include_hayz=False, include_halb=False),
    )


def _result_for(
    planet: str,
    degree: float,
    *,
    policy: DignityComputationPolicy,
    **position: object,
):
    planets = [{"name": "Sun", "degree": 100.0}]
    if planet == "Sun":
        planets[0] = {"name": "Sun", "degree": degree, **position}
    else:
        planets.append({"name": planet, "degree": degree, **position})
    return {
        item.planet: item
        for item in calculate_dignities(planets, _houses(), policy=policy)
    }[planet]


def test_lilly_essential_score_is_cumulative_and_keeps_every_testimony() -> None:
    policy = DignityComputationPolicy(accidental=_quiet_accidental())
    mercury = _result_for("Mercury", 345.0, policy=policy)

    assert mercury.essential_dignity == "Bound"
    assert mercury.essential_score == 2 - 5 - 4
    assert mercury.essential_kinds == (
        EssentialDignityKind.BOUND,
        EssentialDignityKind.DETRIMENT,
        EssentialDignityKind.FALL,
    )
    assert [
        (component.kind, component.weight, component.score)
        for component in mercury.essential_truth.matched_components
    ] == [
        (EssentialDignityKind.BOUND, 2, 2),
        (EssentialDignityKind.DETRIMENT, -5, -5),
        (EssentialDignityKind.FALL, -4, -4),
    ]


def test_peregrine_is_a_minus_five_testimony_and_can_coexist_with_fall() -> None:
    policy = DignityComputationPolicy(accidental=_quiet_accidental())
    sun = _result_for("Sun", 190.0, policy=policy)

    assert sun.essential_score == -4 - 5
    assert sun.essential_kinds == (
        EssentialDignityKind.FALL,
        EssentialDignityKind.PEREGRINE,
    )


def test_direct_motion_scores_four_but_is_not_applied_to_luminaries() -> None:
    policy = DignityComputationPolicy(accidental=_quiet_accidental(include_motion=True))
    mercury = _result_for(
        "Mercury", 70.0, policy=policy, is_retrograde=False
    )
    sun = _result_for("Sun", 130.0, policy=policy, is_retrograde=False)

    assert mercury.accidental_score == 4
    assert mercury.accidental_truth.motion_condition.weight == 4
    assert sun.accidental_score == 0
    assert sun.accidental_truth.motion_condition is None
    assert any(
        receipt.reason == "not_applicable_to_luminary"
        for receipt in sun.accidental_truth.evaluations
    )


def test_stationary_planet_is_tracked_without_a_direct_or_retrograde_score() -> None:
    policy = DignityComputationPolicy(
        accidental=replace(
            _quiet_accidental(include_motion=True),
            include_speed=True,
        )
    )
    mercury = _result_for("Mercury", 90.0, policy=policy, speed=0.0)

    motion = mercury.accidental_truth.motion_condition
    assert motion is not None
    assert motion.code == "stationary"
    assert motion.weight == 0
    assert motion.score == 0
    assert motion.scored is False
    assert "Direct" not in mercury.accidental_dignities
    assert "Retrograde" not in mercury.accidental_dignities
    assert "Slow in Motion" in mercury.accidental_dignities


def test_bounds_and_participating_triplicity_are_independent_policy_axes() -> None:
    base = dict(
        accidental=_quiet_accidental(),
        scoring=DignityScoringPolicy(mode=DignityScoringMode.ESSENTIAL_ONLY),
    )
    ptolemaic = _result_for(
        "Mercury",
        345.0,
        policy=DignityComputationPolicy(
            **base,
            essential=EssentialDignityPolicy(
                bounds_doctrine=EgyptianBoundsDoctrine.PTOLEMAIC,
            ),
        ),
    )
    egyptian = _result_for(
        "Mercury",
        345.0,
        policy=DignityComputationPolicy(
            **base,
            essential=EssentialDignityPolicy(
                bounds_doctrine=EgyptianBoundsDoctrine.EGYPTIAN,
            ),
        ),
    )
    participating = _result_for(
        "Saturn",
        10.0,
        policy=DignityComputationPolicy(
            **base,
            essential=EssentialDignityPolicy(
                participating_ruler_policy=ParticipatingRulerPolicy.AWARD_REDUCED,
            ),
        ),
    )

    assert ptolemaic.essential_score == -7
    assert egyptian.essential_score == -14
    assert participating.essential_truth.component(
        EssentialDignityKind.TRIPLICITY
    ).score == 1


def test_full_essential_only_and_unscored_modes_preserve_truth_but_change_application() -> None:
    planets = [
        {"name": "Sun", "degree": 100.0, "speed": 0.99},
        {"name": "Mercury", "degree": 70.0, "speed": 1.2},
    ]
    full = calculate_dignities(planets, _houses())[1]
    essential_only = calculate_dignities(
        planets,
        _houses(),
        policy=DignityComputationPolicy(
            scoring=DignityScoringPolicy(mode=DignityScoringMode.ESSENTIAL_ONLY)
        ),
    )[1]
    unscored = calculate_dignities(
        planets,
        _houses(),
        policy=DignityComputationPolicy(
            scoring=DignityScoringPolicy(mode=DignityScoringMode.UNSCORED)
        ),
    )[1]

    assert full.essential_score == essential_only.essential_score
    assert full.accidental_score != 0
    assert essential_only.accidental_score == 0
    assert essential_only.accidental_truth.conditions
    assert all(not condition.scored for condition in essential_only.accidental_truth.conditions)
    assert unscored.total_score == 0
    assert unscored.essential_truth.matched_components
    assert all(component.score == 0 for component in unscored.essential_truth.components)
    assert unscored.essential_classification.polarity.value != "neutral"
    assert any(
        condition.polarity.value != "neutral"
        for condition in essential_only.accidental_classification.conditions
        if condition.kind.value not in {"hayz", "halb", "joy"}
    )


def test_mutual_reception_is_essential_and_not_duplicated_as_accidental() -> None:
    policy = DignityComputationPolicy(
        accidental=_quiet_accidental(),
        reception=MutualReceptionPolicy(include_domicile=True, include_exaltation=False),
    )
    by_name = {
        item.planet: item
        for item in calculate_dignities(
            [
                {"name": "Sun", "degree": 100.0},
                {"name": "Venus", "degree": 10.0},
                {"name": "Mars", "degree": 35.0},
            ],
            _houses(),
            policy=policy,
        )
    }

    assert by_name["Venus"].essential_truth.receptions[0].score == 5
    assert by_name["Venus"].mutual_reception_truth[0].score == 5
    assert "Mutual Reception (Mars)" not in by_name["Venus"].accidental_dignities


def test_mars_hayz_requires_a_masculine_sign_and_remains_unscored() -> None:
    assert is_in_hayz("Mars", "Leo", 9, is_day_chart=False)
    assert not is_in_hayz("Mars", "Cancer", 9, is_day_chart=False)

    mars = {
        item.planet: item
        for item in calculate_dignities(
            [{"name": "Sun", "degree": 10.0}, {"name": "Mars", "degree": 130.0}],
            _houses(),
            horizon_frame=DignityHorizonFrame(
                asc_longitude=50.0,
                mc_longitude=100.0,
            ),
        )
    }["Mars"]
    assert mars.accidental_truth.hayz_condition is not None
    assert mars.accidental_truth.hayz_condition.weight == 0
    assert mars.accidental_truth.hayz_condition.scored is False


def test_lilly_mode_rejects_modern_rulers_or_non_ptolemaic_bounds() -> None:
    with pytest.raises(ValueError, match="traditional_classic_7"):
        _result_for(
            "Uranus",
            310.0,
            policy=DignityComputationPolicy(
                essential=EssentialDignityPolicy(
                    doctrine=EssentialDignityDoctrine.MODERN_CO_RULERS
                )
            ),
        )
    with pytest.raises(ValueError, match="ptolemaic bounds"):
        _result_for(
            "Mercury",
            70.0,
            policy=DignityComputationPolicy(
                essential=EssentialDignityPolicy(
                    bounds_doctrine=EgyptianBoundsDoctrine.EGYPTIAN
                )
            ),
        )


@pytest.mark.parametrize(
    ("house", "expected"),
    [(1, 5), (10, 5), (7, 4), (11, 4), (2, 3), (5, 3), (9, 2), (3, 1), (6, -2), (8, -2), (12, -5)],
)
def test_lilly_house_weights_are_house_specific(house: int, expected: int) -> None:
    accidental = _quiet_accidental()
    accidental = AccidentalDignityPolicy(
        **{
            field: getattr(accidental, field)
            for field in accidental.__dataclass_fields__
            if field != "include_house_strength"
        },
        include_house_strength=True,
    )
    policy = DignityComputationPolicy(accidental=accidental)
    mercury = _result_for(
        "Mercury",
        (house - 1) * 30.0 + 1.0,
        policy=policy,
    )
    assert mercury.accidental_score == expected
    assert mercury.accidental_truth.house_condition.weight == expected


@pytest.mark.parametrize(
    ("longitude", "code", "expected"),
    [
        (100.1, "cazimi", 5),
        (105.0, "combust", -5),
        (110.0, "under_sunbeams", -4),
        (130.0, "free_from_beams", 5),
    ],
)
def test_lilly_solar_bands_are_exclusive_and_scored(
    longitude: float,
    code: str,
    expected: int,
) -> None:
    quiet = _quiet_accidental()
    policy = DignityComputationPolicy(
        accidental=AccidentalDignityPolicy(
            include_house_strength=False,
            include_motion=False,
            include_speed=False,
            include_lunar_phase=False,
            include_oriental_occidental=False,
            include_planetary_aspects=False,
            include_node_contacts=False,
            include_fixed_star_contacts=False,
            include_besieging=False,
            include_joy=False,
            solar=SolarConditionPolicy(),
            sect=quiet.sect,
        )
    )
    mercury = _result_for("Mercury", longitude, policy=policy)
    assert mercury.accidental_score == expected
    assert mercury.solar_truth.condition == code
    assert mercury.solar_truth.weight == expected


def test_lilly_speed_lunar_aspect_node_star_and_besieging_weights() -> None:
    quiet = _quiet_accidental()
    speed_policy = DignityComputationPolicy(
        accidental=AccidentalDignityPolicy(
            **{
                field: getattr(quiet, field)
                for field in quiet.__dataclass_fields__
                if field != "include_speed"
            },
            include_speed=True,
        )
    )
    assert _result_for("Mercury", 70.0, policy=speed_policy, speed=1.2).accidental_score == 2
    assert _result_for("Mercury", 70.0, policy=speed_policy, speed=0.5).accidental_score == -2

    lunar_policy = DignityComputationPolicy(
        accidental=AccidentalDignityPolicy(
            **{
                field: getattr(quiet, field)
                for field in quiet.__dataclass_fields__
                if field != "include_lunar_phase"
            },
            include_lunar_phase=True,
        )
    )
    assert _result_for("Moon", 130.0, policy=lunar_policy).accidental_score == 2
    assert _result_for("Moon", 70.0, policy=lunar_policy).accidental_score == -2

    aspect_policy = DignityComputationPolicy(
        accidental=AccidentalDignityPolicy(
            **{
                field: getattr(quiet, field)
                for field in quiet.__dataclass_fields__
                if field != "include_planetary_aspects"
            },
            include_planetary_aspects=True,
        )
    )
    by_name = {
        item.planet: item
        for item in calculate_dignities(
            [
                {"name": "Sun", "degree": 250.0},
                {"name": "Mercury", "degree": 10.0},
                {"name": "Jupiter", "degree": 10.0},
                {"name": "Venus", "degree": 130.0},
                {"name": "Saturn", "degree": 190.0},
                {"name": "Mars", "degree": 100.0},
            ],
            _houses(),
            policy=aspect_policy,
        )
    }
    assert by_name["Mercury"].accidental_score == 5 + 4 - 4 - 3

    contact_policy = DignityComputationPolicy(
        accidental=AccidentalDignityPolicy(
            **{
                field: getattr(quiet, field)
                for field in quiet.__dataclass_fields__
                if field not in {"include_node_contacts", "include_fixed_star_contacts"}
            },
            include_node_contacts=True,
            include_fixed_star_contacts=True,
        )
    )
    contact = calculate_dignities(
        [{"name": "Sun", "degree": 250.0}, {"name": "Mercury", "degree": 10.0}],
        _houses(),
        policy=contact_policy,
        node_positions={"Mean Node": 10.5},
        fixed_star_positions={"Regulus": 15.0, "Spica": 200.0, "Algol": 50.0},
    )[1]
    assert contact.accidental_score == 4 + 6

    besieging_policy = DignityComputationPolicy(
        accidental=AccidentalDignityPolicy(
            **{
                field: getattr(quiet, field)
                for field in quiet.__dataclass_fields__
                if field != "include_besieging"
            },
            include_besieging=True,
        )
    )
    besieged = {
        item.planet: item
        for item in calculate_dignities(
            [
                {"name": "Sun", "degree": 200.0},
                {"name": "Moon", "degree": 250.0},
                {"name": "Mercury", "degree": 10.0},
                {"name": "Venus", "degree": 100.0},
                {"name": "Mars", "degree": 0.0},
                {"name": "Jupiter", "degree": 150.0},
                {"name": "Saturn", "degree": 20.0},
            ],
            _houses(),
            policy=besieging_policy,
        )
    }["Mercury"]
    assert besieged.accidental_score == -5
    assert besieged.accidental_truth.besieged_condition.weight == -5
