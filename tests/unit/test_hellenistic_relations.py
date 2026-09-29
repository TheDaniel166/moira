"""Score-free Hellenistic assemble-condition atoms."""

from __future__ import annotations

import pytest

from moira.aspects import (
    HellenisticAspectEvaluationStatus,
    find_whole_sign_aspects,
)
from moira.dignities import besieging_truth
from moira.dignities_types import TruthEvaluationStatus
from moira.hellenistic_relations import (
    DEFAULT_ADHERENCE_ORB_DEG,
    RAY_NOT_ADMITTED_REASON,
    HellenisticRayTruth,
    assemble_hellenistic_condition,
)


TESTIMONY_CHART = {
    "Sun": 10.0,
    "Moon": 45.0,
    "Mercury": 80.0,
    "Venus": 125.0,
    "Mars": 170.0,
    "Jupiter": 190.0,
    "Saturn": 300.0,
}

ENCLOSURE_CHART = {
    "Sun": 100.0,
    "Moon": 15.0,
    "Mercury": 150.0,
    "Venus": 200.0,
    "Mars": 10.0,
    "Jupiter": 250.0,
    "Saturn": 20.0,
}

OVERCOMING_CHART = {
    "Sun": 5.0,
    "Moon": 95.0,
    "Mercury": 200.0,
    "Venus": 230.0,
    "Mars": 275.0,
    "Jupiter": 140.0,
    "Saturn": 320.0,
}

ADHERENCE_CHART = {
    "Sun": 10.0,
    "Moon": 12.0,
    "Mercury": 80.0,
    "Venus": 125.0,
    "Mars": 170.0,
    "Jupiter": 210.0,
    "Saturn": 300.0,
}

APPLYING_SPEEDS = {
    "Sun": 2.0,
    "Moon": 1.0,
    "Mercury": 1.2,
    "Venus": 1.0,
    "Mars": 0.5,
    "Jupiter": -0.1,
    "Saturn": 0.05,
}


def _regard_map(subject: str, positions: dict[str, float]) -> dict[str, str]:
    regards: dict[str, str] = {}
    for aspect in find_whole_sign_aspects(positions):
        if subject not in {aspect.body1, aspect.body2}:
            continue
        other = aspect.body2 if aspect.body1 == subject else aspect.body1
        regards[other] = aspect.aspect
    return regards


def test_testimony_inverts_whole_sign_aspects() -> None:
    condition = assemble_hellenistic_condition("Sun", TESTIMONY_CHART)
    expected = _regard_map("Sun", TESTIMONY_CHART)
    witnesses = {item.body: item.aspect for item in condition.testimony.witnesses}

    assert condition.testimony.status is HellenisticAspectEvaluationStatus.EVALUATED
    assert witnesses == expected
    assert set(condition.testimony.averse_bodies) == (
        set(TESTIMONY_CHART) - {"Sun"} - set(expected)
    )
    assert "Moon" in condition.testimony.averse_bodies
    assert witnesses["Mercury"] == "Sextile"
    assert witnesses["Venus"] == "Trine"
    assert witnesses["Jupiter"] == "Opposition"
    assert witnesses["Saturn"] == "Sextile"


def test_overcoming_is_tenth_sign_from_the_subject() -> None:
    condition = assemble_hellenistic_condition("Sun", OVERCOMING_CHART)

    assert condition.overcoming.status is HellenisticAspectEvaluationStatus.EVALUATED
    assert condition.overcoming.overcame_by == ("Mars",)
    assert condition.overcoming.overcomes == ("Moon",)
    assert condition.overcoming.reason is None


def test_enclosure_reuses_besieging_truth() -> None:
    condition = assemble_hellenistic_condition("Moon", ENCLOSURE_CHART)
    direct = besieging_truth(
        ENCLOSURE_CHART["Moon"],
        ENCLOSURE_CHART,
        planet_name="Moon",
    )

    assert condition.enclosure == direct
    assert condition.enclosure.status is TruthEvaluationStatus.EVALUATED
    assert condition.enclosure.besieged is True
    assert condition.enclosure.backward_neighbor == "Mars"
    assert condition.enclosure.forward_neighbor == "Saturn"


def test_adherence_is_applying_or_exact_bodily_contact() -> None:
    applying = assemble_hellenistic_condition(
        "Sun",
        ADHERENCE_CHART,
        APPLYING_SPEEDS,
    )
    separating = assemble_hellenistic_condition(
        "Sun",
        ADHERENCE_CHART,
        {**APPLYING_SPEEDS, "Sun": 1.0, "Moon": 2.0},
    )
    empty = assemble_hellenistic_condition("Sun", TESTIMONY_CHART, APPLYING_SPEEDS)

    assert applying.adherence.status is HellenisticAspectEvaluationStatus.EVALUATED
    assert applying.adherence.adhered is True
    assert applying.adherence.partner == "Moon"
    assert applying.adherence.motion_state == "applying"
    assert applying.adherence.distance_deg == pytest.approx(2.0)
    assert applying.adherence.orb_deg == DEFAULT_ADHERENCE_ORB_DEG

    assert separating.adherence.adhered is False
    assert separating.adherence.partner == "Moon"
    assert separating.adherence.motion_state == "separating"

    assert empty.adherence.adhered is False
    assert empty.adherence.partner is None
    assert empty.adherence.distance_deg is None


def test_adherence_fails_closed_without_speeds_or_on_a_tie() -> None:
    no_speeds = assemble_hellenistic_condition("Sun", ADHERENCE_CHART)
    tied = assemble_hellenistic_condition(
        "Sun",
        {**ADHERENCE_CHART, "Mercury": 8.0},
        APPLYING_SPEEDS,
    )

    assert no_speeds.adherence.status is (
        HellenisticAspectEvaluationStatus.NOT_EVALUABLE
    )
    assert no_speeds.adherence.adhered is None
    assert no_speeds.adherence.partner == "Moon"
    assert no_speeds.adherence.reason == "speeds_not_supplied"

    assert tied.adherence.status is HellenisticAspectEvaluationStatus.NOT_EVALUABLE
    assert tied.adherence.adhered is None
    assert tied.adherence.reason == "ambiguous_nearest_partner"
    assert tied.adherence.distance_deg == pytest.approx(2.0)


def test_ray_aktinobolia_strict_3_geometry() -> None:
    # A planet at 15 Leo casts a dexter square to 15 Taurus.
    chart = {
        "Venus": 135.0,  # 15 Leo
        "Moon": 45.0,    # 15 Taurus (exact hit)
        "Sun": 48.0,     # 18 Taurus (just on the edge of 3 degree orb)
        "Mars": 41.9,    # 11.9 Taurus (outside 3 degree orb)
    }
    condition = assemble_hellenistic_condition(
        "Moon", chart, ray_orb_mode="strict_3"
    )
    assert condition.ray.status is HellenisticAspectEvaluationStatus.EVALUATED
    assert len(condition.ray.strikes) == 1
    strike = condition.ray.strikes[0]
    assert strike.origin_body == "Venus"
    assert strike.aspect_name == "Square"
    assert strike.focal_point_deg == 45.0
    assert strike.allowed_orb_deg == 3.0
    assert strike.distance_deg == 0.0

    sun_cond = assemble_hellenistic_condition("Sun", chart, ray_orb_mode="strict_3")
    assert len(sun_cond.ray.strikes) == 1
    assert sun_cond.ray.strikes[0].distance_deg == 3.0

    mars_cond = assemble_hellenistic_condition("Mars", chart, ray_orb_mode="strict_3")
    assert len(mars_cond.ray.strikes) == 0


def test_ray_aktinobolia_moiety_geometry() -> None:
    # Venus (moiety 3.5) casts dexter square to Moon (moiety 6.0) -> allowed orb 9.5
    # Venus at 15 Leo -> focal point 15 Taurus (45.0)
    chart = {
        "Venus": 135.0,
        "Moon": 36.0,  # 9.0 degrees away
        "Mars": 36.0,  # 9.0 degrees away, Mars moiety 3.5 -> allowed 7.0
    }
    moon_cond = assemble_hellenistic_condition("Moon", chart, ray_orb_mode="moiety")
    assert len(moon_cond.ray.strikes) == 1
    assert moon_cond.ray.strikes[0].allowed_orb_deg == 9.5
    assert moon_cond.ray.strikes[0].distance_deg == 9.0

    mars_cond = assemble_hellenistic_condition("Mars", chart, ray_orb_mode="moiety")
    assert len(mars_cond.ray.strikes) == 0


def test_ray_aktinobolia_retrograde_kinematics() -> None:
    chart = {
        "Venus": 135.0,  # 15 Leo
        "Moon": 44.0,    # 14 Taurus
    }
    speeds = {
        "Venus": -1.0,  # Retrograde, moving backward 1 deg/day
        "Moon": 12.0,   # Normal direct motion
    }
    # Focal point is currently 15 Taurus (45.0).
    # Venus is moving backward, so the focal point is moving backward.
    # It is at 45, moving to 44. The Moon is at 44 moving to 56.
    # Therefore, the ray is APPLYING to the Moon.
    condition = assemble_hellenistic_condition(
        "Moon", chart, speeds, ray_orb_mode="strict_3"
    )
    assert len(condition.ray.strikes) == 1
    strike = condition.ray.strikes[0]
    assert strike.motion_state == "applying"

    # If Venus were direct (e.g. +14.0 deg/day), the focal point would move from 45 to 59.
    # Moon moves from 44 to 56. The focal point is moving faster and pulling away.
    # This leads to SEPARATING.
    direct_speeds = {"Venus": 14.0, "Moon": 12.0}
    direct_cond = assemble_hellenistic_condition(
        "Moon", chart, direct_speeds, ray_orb_mode="strict_3"
    )
    assert direct_cond.ray.strikes[0].motion_state == "separating"

def test_assemble_is_score_free_and_subject_absent_fails_closed() -> None:
    missing_moon = {name: lon for name, lon in ENCLOSURE_CHART.items() if name != "Moon"}
    condition = assemble_hellenistic_condition("Moon", missing_moon)

    assert not hasattr(condition, "score")
    assert condition.testimony.status is (
        HellenisticAspectEvaluationStatus.NOT_EVALUABLE
    )
    assert condition.testimony.reason == "subject_longitude_not_supplied"
    assert condition.overcoming.status is (
        HellenisticAspectEvaluationStatus.NOT_EVALUABLE
    )
    assert condition.overcoming.reason == "subject_longitude_not_supplied"
    assert condition.adherence.status is (
        HellenisticAspectEvaluationStatus.NOT_EVALUABLE
    )
    assert condition.adherence.reason == "subject_longitude_not_supplied"
    assert condition.enclosure.status is TruthEvaluationStatus.NOT_EVALUABLE
    assert condition.enclosure.besieged is None
    assert condition.enclosure.reason == "missing_required_chart_bodies"
    assert "Moon" in condition.enclosure.dependency_truth.missing_bodies
    assert condition.ray.reason == "subject_longitude_not_supplied"


def test_assemble_rejects_empty_subject_and_empty_positions() -> None:
    with pytest.raises(ValueError, match="non-empty trimmed string"):
        assemble_hellenistic_condition("  ", TESTIMONY_CHART)
    with pytest.raises(ValueError, match="at least one classical planet"):
        assemble_hellenistic_condition("Sun", {"Fortune": 10.0})
    with pytest.raises(ValueError, match="adherence orb"):
        assemble_hellenistic_condition(
            "Sun",
            TESTIMONY_CHART,
            adherence_orb_deg=0.0,
        )
