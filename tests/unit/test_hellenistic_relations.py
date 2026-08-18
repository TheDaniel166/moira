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


def test_ray_is_fail_closed_until_geometry_is_admitted() -> None:
    condition = assemble_hellenistic_condition("Sun", TESTIMONY_CHART)

    assert condition.ray == HellenisticRayTruth(
        status=HellenisticAspectEvaluationStatus.NOT_EVALUABLE,
        subject="Sun",
        reason=RAY_NOT_ADMITTED_REASON,
    )
    with pytest.raises(ValueError, match="doctrine_not_admitted"):
        HellenisticRayTruth(
            status=HellenisticAspectEvaluationStatus.NOT_EVALUABLE,
            subject="Sun",
            reason="guessed_ray_geometry",
        )


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
    assert condition.ray.reason == RAY_NOT_ADMITTED_REASON


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
