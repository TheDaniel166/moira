from __future__ import annotations

from dataclasses import replace

import pytest

from moira import Moira
from moira.dignities import (
    AccidentalConditionKind,
    AccidentalDignityPolicy,
    ConditionPolarity,
    DignityComputationPolicy,
    EssentialDignityKind,
    MercurySectModel,
    PlanetaryConditionState,
    calculate_condition_network_profile,
    PlanetaryReception,
    ReceptionBasis,
    MutualReceptionPolicy,
    ReceptionKind,
    ReceptionMode,
    SectHayzPolicy,
    SectStateKind,
    SolarConditionPolicy,
    SolarConditionKind,
    calculate_chart_condition_profile,
    calculate_condition_profiles,
    calculate_dignities,
    calculate_receptions,
    is_in_hayz,
    is_in_sect,
    mutual_receptions,
    sect_light,
)
from moira.lots import ArabicPartsService, calculate_lots, list_parts


def _equal_houses(start: float = 0.0) -> list[dict]:
    return [{"number": i + 1, "degree": (start + i * 30.0) % 360.0} for i in range(12)]


def _part_by_name(parts, name: str):
    for part in parts:
        if part.name == name:
            return part
    raise AssertionError(f"Part not found: {name}")


def test_dignities_identify_essential_dignity_mutual_reception_and_hayz() -> None:
    house_positions = _equal_houses(300.0)
    planet_positions = [
        {"name": "Sun", "degree": 130.0, "is_retrograde": False},      # Leo, H7, day, hayz
        {"name": "Moon", "degree": 15.0, "is_retrograde": False},      # Aries
        {"name": "Mercury", "degree": 165.0, "is_retrograde": False},  # Virgo exaltation/domicile
        {"name": "Venus", "degree": 10.0, "is_retrograde": False},     # Aries
        {"name": "Mars", "degree": 35.0, "is_retrograde": False},      # Taurus
        {"name": "Jupiter", "degree": 95.0, "is_retrograde": False},   # Cancer exaltation
        {"name": "Saturn", "degree": 200.0, "is_retrograde": True},    # Libra exaltation, retrograde
    ]

    dignities = calculate_dignities(planet_positions, house_positions)
    by_name = {d.planet: d for d in dignities}

    assert [d.planet for d in dignities] == ["Sun", "Moon", "Mercury", "Venus", "Mars", "Jupiter", "Saturn"]

    assert by_name["Sun"].essential_dignity == "Domicile"
    assert "Angular (H7)" in by_name["Sun"].accidental_dignities
    assert "Direct" in by_name["Sun"].accidental_dignities
    assert "In Hayz" in by_name["Sun"].accidental_dignities

    assert by_name["Jupiter"].essential_dignity == "Exaltation"
    assert by_name["Saturn"].essential_dignity == "Exaltation"
    assert "Retrograde" in by_name["Saturn"].accidental_dignities

    assert "Mutual Reception (Mars)" in by_name["Venus"].accidental_dignities
    assert "Mutual Reception (Venus)" in by_name["Mars"].accidental_dignities


def test_dignities_preserve_legacy_semantics_while_exposing_structured_truth() -> None:
    house_positions = _equal_houses(300.0)
    planet_positions = [
        {"name": "Sun", "degree": 130.0, "is_retrograde": False},
        {"name": "Moon", "degree": 15.0, "is_retrograde": False},
        {"name": "Mercury", "degree": 165.0, "is_retrograde": False},
        {"name": "Venus", "degree": 10.0, "is_retrograde": False},
        {"name": "Mars", "degree": 35.0, "is_retrograde": False},
        {"name": "Jupiter", "degree": 95.0, "is_retrograde": False},
        {"name": "Saturn", "degree": 200.0, "is_retrograde": True},
    ]

    by_name = {d.planet: d for d in calculate_dignities(planet_positions, house_positions)}

    assert (
        by_name["Sun"].essential_dignity,
        by_name["Sun"].essential_score,
        by_name["Sun"].accidental_dignities,
        by_name["Sun"].accidental_score,
        by_name["Sun"].total_score,
    ) == ("Domicile", 5, ["Angular (H7)", "Direct", "In Hayz"], 8, 13)
    assert (
        by_name["Venus"].essential_dignity,
        by_name["Venus"].accidental_dignities,
        by_name["Venus"].accidental_score,
    ) == ("Detriment", ["Cadent (H3)", "Direct", "Mutual Reception (Mars)"], 5)
    assert (
        by_name["Mars"].essential_dignity,
        by_name["Mars"].accidental_dignities,
        by_name["Mars"].accidental_score,
    ) == ("Detriment", ["Angular (H4)", "Direct", "Mutual Reception (Venus)"], 11)

    sun = by_name["Sun"]
    assert sun.essential_truth is not None
    assert sun.essential_truth.label == sun.essential_dignity
    assert sun.essential_truth.score == sun.essential_score
    assert sun.essential_truth.sign == sun.sign
    assert sun.essential_truth.matching_signs == ("Leo",)
    assert sun.sect_truth is not None
    assert sun.sect_truth.is_day_chart is True
    assert sun.sect_truth.sect_light == "Sun"
    assert sun.sect_truth.in_sect is True
    assert sun.sect_truth.in_hayz is True
    assert sun.accidental_truth.house_condition is not None
    assert sun.accidental_truth.house_condition.label == "Angular (H7)"
    assert sun.accidental_truth.motion_condition is not None
    assert sun.accidental_truth.motion_condition.label == "Direct"
    assert sun.accidental_truth.hayz_condition is not None
    assert sun.accidental_truth.hayz_condition.label == "In Hayz"
    assert [c.label for c in sun.accidental_truth.conditions] == sun.accidental_dignities

    venus = by_name["Venus"]
    assert venus.solar_truth.present is False
    assert venus.sect_truth is not None
    assert venus.sect_truth.in_hayz is False
    assert [mr.other_planet for mr in venus.mutual_reception_truth] == ["Mars"]
    assert [mr.reception_type for mr in venus.mutual_reception_truth] == ["domicile"]
    assert [c.label for c in venus.accidental_truth.conditions] == venus.accidental_dignities
    assert venus.essential_classification is not None
    assert venus.essential_classification.kind is EssentialDignityKind.DETRIMENT
    assert venus.essential_classification.polarity is ConditionPolarity.WEAKENING
    assert venus.sect_classification is not None
    assert venus.sect_classification.state is SectStateKind.OUT_OF_SECT
    assert venus.solar_classification.kind is SolarConditionKind.NONE
    assert venus.solar_classification.present is False
    assert [r.kind for r in venus.reception_classification] == [ReceptionKind.DOMICILE]
    assert [r.polarity for r in venus.reception_classification] == [ConditionPolarity.STRENGTHENING]
    assert [c.kind for c in venus.accidental_classification.conditions] == [
        AccidentalConditionKind.CADENT,
        AccidentalConditionKind.DIRECT,
        AccidentalConditionKind.MUTUAL_RECEPTION,
    ]

    mars = by_name["Mars"]
    assert mars.accidental_truth.house_condition is not None
    assert mars.accidental_truth.house_condition.label == "Angular (H4)"
    assert mars.total_score == mars.essential_score + sum(c.score for c in mars.accidental_truth.conditions)


@pytest.mark.parametrize(
    ("mercury_lon", "expected_marker"),
    [
        (100.2, "Cazimi"),
        (105.0, "Combust"),
        (112.0, "Under Sunbeams"),
    ],
)
def test_dignities_solar_proximity_bands_are_classified_correctly(
    mercury_lon: float,
    expected_marker: str,
) -> None:
    house_positions = _equal_houses(0.0)
    planet_positions = [
        {"name": "Sun", "degree": 100.0, "is_retrograde": False},
        {"name": "Moon", "degree": 220.0, "is_retrograde": False},
        {"name": "Mercury", "degree": mercury_lon, "is_retrograde": False},
        {"name": "Venus", "degree": 40.0, "is_retrograde": False},
        {"name": "Mars", "degree": 150.0, "is_retrograde": False},
        {"name": "Jupiter", "degree": 250.0, "is_retrograde": False},
        {"name": "Saturn", "degree": 310.0, "is_retrograde": False},
    ]

    mercury = {d.planet: d for d in calculate_dignities(planet_positions, house_positions)}["Mercury"]
    assert expected_marker in mercury.accidental_dignities


def test_dignities_expose_structured_solar_condition_truth() -> None:
    house_positions = _equal_houses(0.0)
    planet_positions = [
        {"name": "Sun", "degree": 100.0, "is_retrograde": False},
        {"name": "Moon", "degree": 220.0, "is_retrograde": False},
        {"name": "Mercury", "degree": 105.0, "is_retrograde": False},
        {"name": "Venus", "degree": 40.0, "is_retrograde": False},
        {"name": "Mars", "degree": 150.0, "is_retrograde": False},
        {"name": "Jupiter", "degree": 250.0, "is_retrograde": False},
        {"name": "Saturn", "degree": 310.0, "is_retrograde": False},
    ]

    mercury = {d.planet: d for d in calculate_dignities(planet_positions, house_positions)}["Mercury"]

    assert mercury.accidental_dignities == ["Angular (H4)", "Direct", "Combust", "In Hayz"]
    assert mercury.solar_truth.present is True
    assert mercury.solar_truth.condition == "combust"
    assert mercury.solar_truth.label == "Combust"
    assert mercury.solar_truth.score == -5
    assert mercury.solar_truth.distance_from_sun == pytest.approx(5.0, abs=1e-12)
    assert mercury.accidental_truth.solar_condition.label == "Combust"
    assert mercury.sect_truth is not None
    assert mercury.sect_truth.in_hayz is True
    assert [c.category for c in mercury.accidental_truth.conditions] == ["house", "motion", "solar", "sect"]
    assert mercury.solar_classification.kind is SolarConditionKind.COMBUST
    assert mercury.solar_classification.polarity is ConditionPolarity.WEAKENING
    assert mercury.sect_classification is not None
    assert mercury.sect_classification.state is SectStateKind.IN_HAYZ
    assert [c.kind for c in mercury.accidental_classification.conditions] == [
        AccidentalConditionKind.ANGULAR,
        AccidentalConditionKind.DIRECT,
        AccidentalConditionKind.COMBUST,
        AccidentalConditionKind.HAYZ,
    ]


def test_dignities_classification_is_deterministic_and_aligned_with_truth() -> None:
    house_positions = _equal_houses(300.0)
    planet_positions = [
        {"name": "Sun", "degree": 130.0, "is_retrograde": False},
        {"name": "Moon", "degree": 15.0, "is_retrograde": False},
        {"name": "Mercury", "degree": 165.0, "is_retrograde": False},
        {"name": "Venus", "degree": 10.0, "is_retrograde": False},
        {"name": "Mars", "degree": 35.0, "is_retrograde": False},
        {"name": "Jupiter", "degree": 95.0, "is_retrograde": False},
        {"name": "Saturn", "degree": 200.0, "is_retrograde": True},
    ]

    first = {d.planet: d for d in calculate_dignities(planet_positions, house_positions)}
    second = {d.planet: d for d in calculate_dignities(planet_positions, house_positions)}

    for planet in ("Sun", "Venus", "Mercury", "Saturn"):
        left = first[planet]
        right = second[planet]

        assert left.essential_dignity == right.essential_dignity
        assert left.essential_score == right.essential_score
        assert left.accidental_dignities == right.accidental_dignities
        assert left.total_score == right.total_score

        assert left.essential_classification == right.essential_classification
        assert left.accidental_classification == right.accidental_classification
        assert left.sect_classification == right.sect_classification
        assert left.solar_classification == right.solar_classification
        assert left.reception_classification == right.reception_classification

        assert left.essential_classification is not None
        assert left.essential_classification.polarity.value == (
            "strengthening" if left.essential_truth.score > 0
            else "weakening" if left.essential_truth.score < 0
            else "neutral"
        )
        assert [c.label for c in left.accidental_classification.conditions] == left.accidental_dignities
        assert [c.score for c in left.accidental_classification.conditions] == [
            c.score for c in left.accidental_truth.conditions
        ]
        assert left.solar_classification.present == left.solar_truth.present
        assert left.sect_classification.in_sect == left.sect_truth.in_sect
        assert left.sect_classification.in_hayz == left.sect_truth.in_hayz
        assert [r.other_planet for r in left.reception_classification] == [
            r.other_planet for r in left.mutual_reception_truth
        ]


def test_dignities_expose_read_only_inspectability_properties() -> None:
    house_positions = _equal_houses(300.0)
    planet_positions = [
        {"name": "Sun", "degree": 130.0, "is_retrograde": False},
        {"name": "Moon", "degree": 15.0, "is_retrograde": False},
        {"name": "Mercury", "degree": 165.0, "is_retrograde": False},
        {"name": "Venus", "degree": 10.0, "is_retrograde": False},
        {"name": "Mars", "degree": 35.0, "is_retrograde": False},
        {"name": "Jupiter", "degree": 95.0, "is_retrograde": False},
        {"name": "Saturn", "degree": 200.0, "is_retrograde": True},
    ]

    by_name = {d.planet: d for d in calculate_dignities(planet_positions, house_positions)}

    sun = by_name["Sun"]
    venus = by_name["Venus"]

    assert sun.essential_kind is EssentialDignityKind.DOMICILE
    assert sun.essential_polarity is ConditionPolarity.STRENGTHENING
    assert sun.accidental_condition_kinds == (
        AccidentalConditionKind.ANGULAR,
        AccidentalConditionKind.DIRECT,
        AccidentalConditionKind.HAYZ,
    )
    assert sun.sect_state is SectStateKind.IN_HAYZ
    assert sun.solar_kind is SolarConditionKind.NONE
    assert sun.has_solar_condition is False
    assert sun.reception_kinds == ()
    assert sun.has_mutual_reception is False

    assert venus.essential_kind is venus.essential_classification.kind
    assert venus.essential_polarity is venus.essential_classification.polarity
    assert venus.accidental_condition_kinds == tuple(
        condition.kind for condition in venus.accidental_classification.conditions
    )
    assert venus.sect_state is venus.sect_classification.state
    assert venus.solar_kind is venus.solar_classification.kind
    assert venus.reception_kinds == tuple(
        reception.kind for reception in venus.reception_classification
    )
    assert venus.has_solar_condition is venus.solar_classification.present
    assert venus.has_mutual_reception is True

    with pytest.raises(AttributeError):
        setattr(sun, "essential_kind", EssentialDignityKind.PEREGRINE)


def test_planetary_dignity_invariants_fail_loudly_on_internal_drift() -> None:
    house_positions = _equal_houses(300.0)
    planet_positions = [
        {"name": "Sun", "degree": 130.0, "is_retrograde": False},
        {"name": "Moon", "degree": 15.0, "is_retrograde": False},
        {"name": "Mercury", "degree": 165.0, "is_retrograde": False},
        {"name": "Venus", "degree": 10.0, "is_retrograde": False},
        {"name": "Mars", "degree": 35.0, "is_retrograde": False},
        {"name": "Jupiter", "degree": 95.0, "is_retrograde": False},
        {"name": "Saturn", "degree": 200.0, "is_retrograde": True},
    ]
    venus = {d.planet: d for d in calculate_dignities(planet_positions, house_positions)}["Venus"]

    with pytest.raises(ValueError, match="total_score"):
        replace(venus, total_score=venus.total_score + 1)

    with pytest.raises(ValueError, match="accidental classification labels"):
        replace(
            venus,
            accidental_classification=replace(
                venus.accidental_classification,
                conditions=[],
            ),
        )

    with pytest.raises(ValueError, match="solar classification presence"):
        replace(
            venus,
            solar_classification=replace(venus.solar_classification, present=True),
        )


def test_dignities_default_policy_preserves_current_behavior() -> None:
    house_positions = _equal_houses(300.0)
    planet_positions = [
        {"name": "Sun", "degree": 130.0, "is_retrograde": False},
        {"name": "Moon", "degree": 15.0, "is_retrograde": False},
        {"name": "Mercury", "degree": 165.0, "is_retrograde": False},
        {"name": "Venus", "degree": 10.0, "is_retrograde": False},
        {"name": "Mars", "degree": 35.0, "is_retrograde": False},
        {"name": "Jupiter", "degree": 95.0, "is_retrograde": False},
        {"name": "Saturn", "degree": 200.0, "is_retrograde": True},
    ]

    without_policy = calculate_dignities(planet_positions, house_positions)
    with_default_policy = calculate_dignities(
        planet_positions,
        house_positions,
        policy=DignityComputationPolicy(),
    )

    assert [
        (d.planet, d.essential_dignity, d.essential_score, tuple(d.accidental_dignities), d.accidental_score, d.total_score)
        for d in without_policy
    ] == [
        (d.planet, d.essential_dignity, d.essential_score, tuple(d.accidental_dignities), d.accidental_score, d.total_score)
        for d in with_default_policy
    ]

    assert [
        (d.planet, tuple((r.host_planet, r.basis.value, r.mode.value) for r in d.receptions))
        for d in without_policy
    ] == [
        (d.planet, tuple((r.host_planet, r.basis.value, r.mode.value) for r in d.receptions))
        for d in with_default_policy
    ]


def test_dignities_narrow_policy_explicitly_disables_selected_conditions() -> None:
    house_positions = _equal_houses(300.0)
    planet_positions = [
        {"name": "Sun", "degree": 130.0, "is_retrograde": False},
        {"name": "Moon", "degree": 15.0, "is_retrograde": False},
        {"name": "Mercury", "degree": 132.0, "is_retrograde": False},
        {"name": "Venus", "degree": 10.0, "is_retrograde": False},
        {"name": "Mars", "degree": 35.0, "is_retrograde": False},
        {"name": "Jupiter", "degree": 95.0, "is_retrograde": False},
        {"name": "Saturn", "degree": 200.0, "is_retrograde": True},
    ]
    policy = DignityComputationPolicy(
        accidental=AccidentalDignityPolicy(
            solar=SolarConditionPolicy(
                include_cazimi=False,
                include_combust=False,
                include_under_sunbeams=False,
            ),
            mutual_reception=MutualReceptionPolicy(
                include_domicile=False,
                include_exaltation=False,
            ),
            sect=SectHayzPolicy(
                mercury_sect_model=MercurySectModel.LONGITUDE_HEURISTIC,
                include_hayz=False,
            ),
        )
    )

    by_name = {d.planet: d for d in calculate_dignities(planet_positions, house_positions, policy=policy)}

    assert policy.is_default is False
    assert policy.includes_any_solar_condition is False
    assert policy.includes_any_mutual_reception is False

    assert by_name["Sun"].accidental_dignities == ["Angular (H7)", "Direct"]
    assert by_name["Sun"].accidental_score == 6
    assert by_name["Mercury"].accidental_dignities == ["Angular (H7)", "Direct"]
    assert by_name["Venus"].accidental_dignities == ["Cadent (H3)", "Direct"]
    assert by_name["Mars"].accidental_dignities == ["Angular (H4)", "Direct"]
    assert by_name["Venus"].has_mutual_reception is False
    assert by_name["Venus"].reception_kinds == ()
    assert by_name["Sun"].sect_truth.in_hayz is True
    assert by_name["Sun"].accidental_truth.hayz_condition is None
    assert by_name["Mercury"].solar_truth.present is False
    assert by_name["Mercury"].solar_kind is SolarConditionKind.NONE
    assert by_name["Venus"].receptions == []
    assert by_name["Mars"].receptions == []


def test_dignity_policy_surface_is_deterministic_and_inspectable() -> None:
    left = DignityComputationPolicy()
    right = DignityComputationPolicy()
    custom = DignityComputationPolicy(
        accidental=AccidentalDignityPolicy(
            include_motion=False,
            solar=SolarConditionPolicy(include_cazimi=True, include_combust=False, include_under_sunbeams=False),
        )
    )

    assert left == right
    assert left.is_default is True
    assert left.includes_any_solar_condition is True
    assert left.includes_any_mutual_reception is True
    assert custom.is_default is False
    assert custom.includes_any_solar_condition is True
    assert custom.accidental.include_motion is False


def test_reception_layer_is_deterministic_and_distinguishes_mutual_and_unilateral() -> None:
    planet_positions = [
        {"name": "Sun", "degree": 130.0, "is_retrograde": False},
        {"name": "Moon", "degree": 100.0, "is_retrograde": False},
        {"name": "Mercury", "degree": 250.0, "is_retrograde": False},  # Sagittarius -> received by Jupiter
        {"name": "Venus", "degree": 10.0, "is_retrograde": False},     # Aries -> received by Mars
        {"name": "Mars", "degree": 35.0, "is_retrograde": False},      # Taurus -> received by Venus
        {"name": "Jupiter", "degree": 95.0, "is_retrograde": False},   # Cancer
        {"name": "Saturn", "degree": 200.0, "is_retrograde": True},
    ]

    first = calculate_receptions(planet_positions)
    second = calculate_receptions(planet_positions)

    assert first == second

    as_tuples = [
        (r.receiving_planet, r.host_planet, r.basis, r.mode, r.receiving_sign, r.host_sign)
        for r in first
    ]
    assert ("Venus", "Mars", ReceptionBasis.DOMICILE, ReceptionMode.MUTUAL, "Aries", "Taurus") in as_tuples
    assert ("Mars", "Venus", ReceptionBasis.DOMICILE, ReceptionMode.MUTUAL, "Taurus", "Aries") in as_tuples
    assert ("Mercury", "Jupiter", ReceptionBasis.DOMICILE, ReceptionMode.UNILATERAL, "Sagittarius", "Cancer") in as_tuples
    for reception in first:
        assert reception.receiving_planet != reception.host_planet
        assert reception.receiving_sign in reception.host_matching_signs
        assert reception.is_mutual is (reception.mode is ReceptionMode.MUTUAL)


def test_reception_layer_integrates_with_dignity_vessels_without_changing_default_scoring() -> None:
    house_positions = _equal_houses(300.0)
    planet_positions = [
        {"name": "Sun", "degree": 130.0, "is_retrograde": False},
        {"name": "Moon", "degree": 100.0, "is_retrograde": False},
        {"name": "Mercury", "degree": 250.0, "is_retrograde": False},
        {"name": "Venus", "degree": 10.0, "is_retrograde": False},
        {"name": "Mars", "degree": 35.0, "is_retrograde": False},
        {"name": "Jupiter", "degree": 95.0, "is_retrograde": False},
        {"name": "Saturn", "degree": 200.0, "is_retrograde": True},
    ]

    by_name = {d.planet: d for d in calculate_dignities(planet_positions, house_positions)}

    assert [(r.host_planet, r.basis, r.mode) for r in by_name["Venus"].all_receptions] == [
        ("Mars", ReceptionBasis.DOMICILE, ReceptionMode.MUTUAL),
        ("Sun", ReceptionBasis.EXALTATION, ReceptionMode.UNILATERAL),
    ]
    assert [(r.host_planet, r.basis, r.mode) for r in by_name["Venus"].receptions] == [
        ("Mars", ReceptionBasis.DOMICILE, ReceptionMode.MUTUAL),
        ("Sun", ReceptionBasis.EXALTATION, ReceptionMode.UNILATERAL),
    ]
    assert [(r.host_planet, r.basis, r.mode) for r in by_name["Mars"].receptions] == [
        ("Venus", ReceptionBasis.DOMICILE, ReceptionMode.MUTUAL),
        ("Moon", ReceptionBasis.EXALTATION, ReceptionMode.UNILATERAL),
    ]
    assert [(r.host_planet, r.basis, r.mode) for r in by_name["Mercury"].receptions] == [
        ("Jupiter", ReceptionBasis.DOMICILE, ReceptionMode.UNILATERAL),
    ]

    assert by_name["Mercury"].mutual_reception_truth == []
    assert by_name["Mercury"].reception_classification == []
    assert "Mutual Reception" not in " ".join(by_name["Mercury"].accidental_dignities)

    assert [r.other_planet for r in by_name["Venus"].mutual_reception_truth] == ["Mars"]
    assert [r.kind for r in by_name["Venus"].reception_classification] == [ReceptionKind.DOMICILE]
    assert tuple(by_name["Venus"].admitted_receptions) == tuple(by_name["Venus"].receptions)
    assert by_name["Venus"].scored_receptions == (
        by_name["Venus"].receptions[0],
    )
    assert by_name["Venus"].detected_reception_bases == (
        ReceptionBasis.DOMICILE,
        ReceptionBasis.EXALTATION,
    )
    assert by_name["Venus"].admitted_reception_bases == (
        ReceptionBasis.DOMICILE,
        ReceptionBasis.EXALTATION,
    )
    assert by_name["Venus"].has_detected_reception is True
    assert by_name["Venus"].has_unilateral_reception is True
    assert by_name["Mercury"].has_unilateral_reception is True
    assert by_name["Mercury"].has_detected_reception is True
    assert by_name["Mercury"].reception_modes == (ReceptionMode.UNILATERAL,)
    assert by_name["Mercury"].scored_receptions == ()


def test_reception_policy_governs_formal_reception_admissibility() -> None:
    planet_positions = [
        {"name": "Sun", "degree": 130.0, "is_retrograde": False},
        {"name": "Moon", "degree": 100.0, "is_retrograde": False},
        {"name": "Mercury", "degree": 250.0, "is_retrograde": False},
        {"name": "Venus", "degree": 10.0, "is_retrograde": False},
        {"name": "Mars", "degree": 35.0, "is_retrograde": False},
        {"name": "Jupiter", "degree": 95.0, "is_retrograde": False},
        {"name": "Saturn", "degree": 200.0, "is_retrograde": True},
    ]
    policy = DignityComputationPolicy(
        accidental=AccidentalDignityPolicy(
            mutual_reception=MutualReceptionPolicy(
                include_domicile=False,
                include_exaltation=False,
            )
        )
    )

    receptions = calculate_receptions(planet_positions, policy=policy)
    assert receptions == []

    house_positions = _equal_houses(300.0)
    by_name = {d.planet: d for d in calculate_dignities(planet_positions, house_positions, policy=policy)}
    assert by_name["Venus"].all_receptions != []
    assert by_name["Venus"].receptions == []
    assert by_name["Venus"].admitted_receptions == ()
    assert by_name["Venus"].scored_receptions == ()
    assert by_name["Venus"].has_detected_reception is True
    assert by_name["Mars"].all_receptions != []
    assert by_name["Mars"].receptions == []
    assert by_name["Mercury"].all_receptions != []
    assert by_name["Mercury"].receptions == []


def test_reception_inspectability_helpers_are_derived_only() -> None:
    house_positions = _equal_houses(300.0)
    planet_positions = [
        {"name": "Sun", "degree": 130.0, "is_retrograde": False},
        {"name": "Moon", "degree": 100.0, "is_retrograde": False},
        {"name": "Mercury", "degree": 250.0, "is_retrograde": False},
        {"name": "Venus", "degree": 10.0, "is_retrograde": False},
        {"name": "Mars", "degree": 35.0, "is_retrograde": False},
        {"name": "Jupiter", "degree": 95.0, "is_retrograde": False},
        {"name": "Saturn", "degree": 200.0, "is_retrograde": True},
    ]
    venus = {d.planet: d for d in calculate_dignities(planet_positions, house_positions)}["Venus"]

    assert venus.admitted_receptions == tuple(venus.receptions)
    assert venus.scored_receptions == tuple(r for r in venus.receptions if r.mode is ReceptionMode.MUTUAL)
    assert venus.detected_reception_bases == tuple(r.basis for r in venus.all_receptions)
    assert venus.admitted_reception_bases == tuple(r.basis for r in venus.receptions)

    with pytest.raises(AttributeError):
        setattr(venus, "scored_receptions", ())


def test_reception_invariants_fail_loudly_on_subset_drift() -> None:
    house_positions = _equal_houses(300.0)
    planet_positions = [
        {"name": "Sun", "degree": 130.0, "is_retrograde": False},
        {"name": "Moon", "degree": 100.0, "is_retrograde": False},
        {"name": "Mercury", "degree": 250.0, "is_retrograde": False},
        {"name": "Venus", "degree": 10.0, "is_retrograde": False},
        {"name": "Mars", "degree": 35.0, "is_retrograde": False},
        {"name": "Jupiter", "degree": 95.0, "is_retrograde": False},
        {"name": "Saturn", "degree": 200.0, "is_retrograde": True},
    ]
    venus = {d.planet: d for d in calculate_dignities(planet_positions, house_positions)}["Venus"]

    with pytest.raises(ValueError, match="admitted receptions must be a subset"):
        replace(venus, all_receptions=[])

    with pytest.raises(ValueError, match="mutual reception relation count mismatch"):
        replace(venus, receptions=venus.receptions[1:])


def test_condition_profiles_are_deterministic_and_align_with_dignity_truth() -> None:
    house_positions = _equal_houses(300.0)
    planet_positions = [
        {"name": "Sun", "degree": 130.0, "is_retrograde": False},
        {"name": "Moon", "degree": 100.0, "is_retrograde": False},
        {"name": "Mercury", "degree": 250.0, "is_retrograde": False},
        {"name": "Venus", "degree": 10.0, "is_retrograde": False},
        {"name": "Mars", "degree": 35.0, "is_retrograde": False},
        {"name": "Jupiter", "degree": 95.0, "is_retrograde": False},
        {"name": "Saturn", "degree": 200.0, "is_retrograde": True},
    ]

    first = calculate_condition_profiles(planet_positions, house_positions)
    second = calculate_condition_profiles(planet_positions, house_positions)
    dignities = {d.planet: d for d in calculate_dignities(planet_positions, house_positions)}
    profiles = {profile.planet: profile for profile in first}

    assert first == second
    assert [profile.planet for profile in first] == [d.planet for d in calculate_dignities(planet_positions, house_positions)]

    venus_profile = profiles["Venus"]
    venus_dignity = dignities["Venus"]
    assert venus_profile.essential_truth == venus_dignity.essential_truth
    assert venus_profile.essential_classification == venus_dignity.essential_classification
    assert venus_profile.accidental_truth == venus_dignity.accidental_truth
    assert venus_profile.accidental_classification == venus_dignity.accidental_classification
    assert venus_profile.sect_truth == venus_dignity.sect_truth
    assert venus_profile.sect_classification == venus_dignity.sect_classification
    assert venus_profile.solar_truth == venus_dignity.solar_truth
    assert venus_profile.solar_classification == venus_dignity.solar_classification
    assert venus_profile.all_receptions == venus_dignity.all_receptions
    assert venus_profile.admitted_receptions == venus_dignity.receptions
    assert venus_profile.scored_receptions == list(venus_dignity.scored_receptions)
    assert venus_profile.reception_classification == venus_dignity.reception_classification


def test_condition_profile_state_is_derived_only_from_condition_polarities() -> None:
    house_positions = _equal_houses(300.0)
    planet_positions = [
        {"name": "Sun", "degree": 130.0, "is_retrograde": False},
        {"name": "Moon", "degree": 100.0, "is_retrograde": False},
        {"name": "Mercury", "degree": 250.0, "is_retrograde": False},
        {"name": "Venus", "degree": 10.0, "is_retrograde": False},
        {"name": "Mars", "degree": 35.0, "is_retrograde": False},
        {"name": "Jupiter", "degree": 95.0, "is_retrograde": False},
        {"name": "Saturn", "degree": 200.0, "is_retrograde": True},
    ]
    by_name = {d.planet: d for d in calculate_dignities(planet_positions, house_positions)}

    sun_profile = by_name["Sun"].condition_profile
    venus_profile = by_name["Venus"].condition_profile
    saturn_profile = by_name["Saturn"].condition_profile

    assert sun_profile is not None
    assert sun_profile.state is PlanetaryConditionState.REINFORCED
    assert sun_profile.is_reinforced is True
    assert sun_profile.is_mixed is False
    assert sun_profile.is_weakened is False
    assert sun_profile.strengthening_count > 0
    assert sun_profile.weakening_count == 0

    assert venus_profile is not None
    assert venus_profile.state is PlanetaryConditionState.MIXED
    assert venus_profile.is_mixed is True
    assert venus_profile.strengthening_count > 0
    assert venus_profile.weakening_count > 0

    assert saturn_profile is not None
    assert saturn_profile.state is PlanetaryConditionState.MIXED
    assert by_name["Sun"].condition_state is sun_profile.state

    with pytest.raises(ValueError, match="state must match derived polarity counts"):
        replace(sun_profile, state=PlanetaryConditionState.WEAKENED)


def test_chart_condition_profile_is_deterministic_and_aligns_with_planet_profiles() -> None:
    house_positions = _equal_houses(300.0)
    planet_positions = [
        {"name": "Sun", "degree": 130.0, "is_retrograde": False},
        {"name": "Moon", "degree": 100.0, "is_retrograde": False},
        {"name": "Mercury", "degree": 250.0, "is_retrograde": False},
        {"name": "Venus", "degree": 10.0, "is_retrograde": False},
        {"name": "Mars", "degree": 35.0, "is_retrograde": False},
        {"name": "Jupiter", "degree": 95.0, "is_retrograde": False},
        {"name": "Saturn", "degree": 200.0, "is_retrograde": True},
    ]

    first = calculate_chart_condition_profile(planet_positions, house_positions)
    second = calculate_chart_condition_profile(planet_positions, house_positions)
    profiles = calculate_condition_profiles(planet_positions, house_positions)

    assert first == second
    assert [profile.planet for profile in first.profiles] == [profile.planet for profile in profiles]
    assert first.reinforced_count == sum(1 for profile in profiles if profile.state is PlanetaryConditionState.REINFORCED)
    assert first.mixed_count == sum(1 for profile in profiles if profile.state is PlanetaryConditionState.MIXED)
    assert first.weakened_count == sum(1 for profile in profiles if profile.state is PlanetaryConditionState.WEAKENED)
    assert first.strengthening_total == sum(profile.strengthening_count for profile in profiles)
    assert first.weakening_total == sum(profile.weakening_count for profile in profiles)
    assert first.neutral_total == sum(profile.neutral_count for profile in profiles)
    assert first.reception_participation_total == sum(len(profile.admitted_receptions) for profile in profiles)


def test_chart_condition_profile_strongest_and_weakest_are_derived_only() -> None:
    house_positions = _equal_houses(300.0)
    planet_positions = [
        {"name": "Sun", "degree": 130.0, "is_retrograde": False},
        {"name": "Moon", "degree": 100.0, "is_retrograde": False},
        {"name": "Mercury", "degree": 250.0, "is_retrograde": False},
        {"name": "Venus", "degree": 10.0, "is_retrograde": False},
        {"name": "Mars", "degree": 35.0, "is_retrograde": False},
        {"name": "Jupiter", "degree": 95.0, "is_retrograde": False},
        {"name": "Saturn", "degree": 200.0, "is_retrograde": True},
    ]
    chart_profile = calculate_chart_condition_profile(planet_positions, house_positions)

    ranking = {
        profile.planet: profile.strengthening_count - profile.weakening_count
        for profile in chart_profile.profiles
    }
    strongest_value = max(ranking.values())
    weakest_value = min(ranking.values())

    assert all(ranking[planet] == strongest_value for planet in chart_profile.strongest_planets)
    assert all(ranking[planet] == weakest_value for planet in chart_profile.weakest_planets)
    assert chart_profile.strongest_planets == sorted(
        chart_profile.strongest_planets,
        key=lambda planet: ["Sun", "Moon", "Mercury", "Venus", "Mars", "Jupiter", "Saturn"].index(planet),
    )
    assert chart_profile.weakest_planets == sorted(
        chart_profile.weakest_planets,
        key=lambda planet: ["Sun", "Moon", "Mercury", "Venus", "Mars", "Jupiter", "Saturn"].index(planet),
    )
    assert chart_profile.strongest_count == len(chart_profile.strongest_planets)
    assert chart_profile.weakest_count == len(chart_profile.weakest_planets)

    with pytest.raises(ValueError, match="state counts must match profile states"):
        replace(chart_profile, reinforced_count=chart_profile.reinforced_count + 1)


def test_condition_network_profile_is_deterministic_and_aligns_with_reception_truth() -> None:
    house_positions = _equal_houses(300.0)
    planet_positions = [
        {"name": "Sun", "degree": 130.0, "is_retrograde": False},
        {"name": "Moon", "degree": 100.0, "is_retrograde": False},
        {"name": "Mercury", "degree": 250.0, "is_retrograde": False},
        {"name": "Venus", "degree": 10.0, "is_retrograde": False},
        {"name": "Mars", "degree": 35.0, "is_retrograde": False},
        {"name": "Jupiter", "degree": 95.0, "is_retrograde": False},
        {"name": "Saturn", "degree": 200.0, "is_retrograde": True},
    ]

    first = calculate_condition_network_profile(planet_positions, house_positions)
    second = calculate_condition_network_profile(planet_positions, house_positions)
    dignities = calculate_dignities(planet_positions, house_positions)

    assert first == second
    assert first.node_count == len(dignities)
    assert first.edge_count == sum(len(d.receptions) for d in dignities)
    assert [node.planet for node in first.nodes] == [d.planet for d in dignities]


def test_condition_network_represents_unilateral_and_mutual_links_correctly() -> None:
    house_positions = _equal_houses(300.0)
    planet_positions = [
        {"name": "Sun", "degree": 130.0, "is_retrograde": False},
        {"name": "Moon", "degree": 100.0, "is_retrograde": False},
        {"name": "Mercury", "degree": 250.0, "is_retrograde": False},
        {"name": "Venus", "degree": 10.0, "is_retrograde": False},
        {"name": "Mars", "degree": 35.0, "is_retrograde": False},
        {"name": "Jupiter", "degree": 95.0, "is_retrograde": False},
        {"name": "Saturn", "degree": 200.0, "is_retrograde": True},
    ]
    profile = calculate_condition_network_profile(planet_positions, house_positions)

    edge_tuples = [
        (edge.source_planet, edge.target_planet, edge.basis, edge.mode)
        for edge in profile.edges
    ]
    assert ("Venus", "Mars", ReceptionBasis.DOMICILE, ReceptionMode.MUTUAL) in edge_tuples
    assert ("Mars", "Venus", ReceptionBasis.DOMICILE, ReceptionMode.MUTUAL) in edge_tuples
    assert ("Mercury", "Jupiter", ReceptionBasis.DOMICILE, ReceptionMode.UNILATERAL) in edge_tuples
    assert profile.mutual_edge_count == sum(1 for edge in profile.edges if edge.mode is ReceptionMode.MUTUAL)
    assert profile.unilateral_edge_count == sum(1 for edge in profile.edges if edge.mode is ReceptionMode.UNILATERAL)


def test_condition_network_identifies_isolated_and_support_rich_planets_on_controlled_case() -> None:
    house_positions = _equal_houses(300.0)
    planet_positions = [
        {"name": "Sun", "degree": 130.0, "is_retrograde": False},
        {"name": "Moon", "degree": 100.0, "is_retrograde": False},
        {"name": "Mercury", "degree": 250.0, "is_retrograde": False},
        {"name": "Venus", "degree": 10.0, "is_retrograde": False},
        {"name": "Mars", "degree": 35.0, "is_retrograde": False},
        {"name": "Jupiter", "degree": 95.0, "is_retrograde": False},
        {"name": "Saturn", "degree": 200.0, "is_retrograde": True},
    ]
    profile = calculate_condition_network_profile(planet_positions, house_positions)
    nodes = {node.planet: node for node in profile.nodes}

    assert nodes["Saturn"].is_isolated is False
    assert profile.isolated_planets == []
    assert nodes["Venus"].outgoing_count == 2
    assert nodes["Mars"].outgoing_count == 2
    assert nodes["Venus"].mutual_count == 1
    assert nodes["Mars"].mutual_count == 1
    assert profile.most_connected_planets == ["Venus"]


def test_dignities_fail_clearly_on_duplicate_classic_planet_entries() -> None:
    house_positions = _equal_houses(300.0)
    planet_positions = [
        {"name": "Sun", "degree": 130.0, "is_retrograde": False},
        {"name": "Sun", "degree": 131.0, "is_retrograde": False},
    ]

    with pytest.raises(ValueError, match="duplicate entry for classic planet"):
        calculate_dignities(planet_positions, house_positions)


def test_dignities_fail_clearly_on_non_finite_or_non_bool_planet_fields() -> None:
    house_positions = _equal_houses(300.0)

    with pytest.raises(ValueError, match=r"degree must be finite"):
        calculate_dignities(
            [{"name": "Sun", "degree": float("nan"), "is_retrograde": False}],
            house_positions,
        )

    with pytest.raises(ValueError, match=r"is_retrograde must be a bool"):
        calculate_dignities(
            [{"name": "Sun", "degree": 130.0, "is_retrograde": "no"}],
            house_positions,
        )


def test_dignities_fail_clearly_on_invalid_house_inputs() -> None:
    planet_positions = [{"name": "Sun", "degree": 130.0, "is_retrograde": False}]

    with pytest.raises(ValueError, match=r"duplicate cusp number 1"):
        calculate_dignities(
            planet_positions,
            [{"number": 1, "degree": 0.0}] + [{"number": i, "degree": float(i)} for i in range(1, 12)],
        )

    with pytest.raises(ValueError, match=r"missing \[12\]"):
        calculate_dignities(
            planet_positions,
            [{"number": i, "degree": float(i)} for i in range(1, 12)],
        )

    with pytest.raises(ValueError, match=r"number must be in the range 1..12"):
        calculate_dignities(
            planet_positions,
            _equal_houses(300.0)[:-1] + [{"number": 13, "degree": 0.0}],
        )


def test_policy_validation_fails_deterministically_on_unsupported_enum_values() -> None:
    house_positions = _equal_houses(300.0)
    planet_positions = [{"name": "Sun", "degree": 130.0, "is_retrograde": False}]
    bad_policy = replace(
        DignityComputationPolicy(),
        essential=replace(DignityComputationPolicy().essential, doctrine="invalid"),  # type: ignore[arg-type]
    )

    with pytest.raises(ValueError, match="Unsupported essential dignity doctrine"):
        calculate_dignities(planet_positions, house_positions, policy=bad_policy)


def test_chart_and_network_invariants_fail_loudly_on_cross_layer_drift() -> None:
    house_positions = _equal_houses(300.0)
    planet_positions = [
        {"name": "Sun", "degree": 130.0, "is_retrograde": False},
        {"name": "Moon", "degree": 100.0, "is_retrograde": False},
        {"name": "Mercury", "degree": 250.0, "is_retrograde": False},
        {"name": "Venus", "degree": 10.0, "is_retrograde": False},
        {"name": "Mars", "degree": 35.0, "is_retrograde": False},
        {"name": "Jupiter", "degree": 95.0, "is_retrograde": False},
        {"name": "Saturn", "degree": 200.0, "is_retrograde": True},
    ]
    chart_profile = calculate_chart_condition_profile(planet_positions, house_positions)
    network_profile = calculate_condition_network_profile(planet_positions, house_positions)

    with pytest.raises(ValueError, match="profiles must be in deterministic planet order"):
        replace(chart_profile, profiles=list(reversed(chart_profile.profiles)))

    with pytest.raises(ValueError, match="nodes must be in deterministic planet order"):
        replace(network_profile, nodes=list(reversed(network_profile.nodes)))


def test_dignity_helpers_cover_sect_and_mutual_reception_logic() -> None:
    assert sect_light(130.0, 300.0) == "Sun"
    assert sect_light(20.0, 300.0) == "Moon"

    assert is_in_sect("Jupiter", is_day_chart=True)
    assert not is_in_sect("Jupiter", is_day_chart=False)
    assert is_in_hayz("Sun", "Leo", 7, is_day_chart=True)
    assert not is_in_hayz("Moon", "Leo", 7, is_day_chart=True)

    receptions = mutual_receptions({"Venus": 10.0, "Mars": 35.0, "Sun": 130.0})
    assert ("Venus", "Mars", "Domicile") in receptions or ("Mars", "Venus", "Domicile") in receptions


def test_lots_day_and_night_formulas_resolve_core_references_correctly() -> None:
    positions = {
        "Sun": 100.0,
        "Moon": 220.0,
        "Mercury": 80.0,
        "Venus": 10.0,
        "Mars": 35.0,
        "Jupiter": 250.0,
        "Saturn": 310.0,
    }
    house_cusps = {i + 1: i * 30.0 for i in range(12)}

    day_parts = calculate_lots(positions, house_cusps, True)
    night_parts = calculate_lots(positions, house_cusps, False)

    day_fortune = _part_by_name(day_parts, "Fortune")
    night_fortune = _part_by_name(night_parts, "Fortune")
    day_spirit = _part_by_name(day_parts, "Spirit")
    night_spirit = _part_by_name(night_parts, "Spirit")
    day_eros = _part_by_name(day_parts, "Eros (Valens)")
    night_eros = _part_by_name(night_parts, "Eros (Valens)")

    assert day_fortune.longitude == pytest.approx((0.0 + 220.0 - 100.0) % 360.0, abs=1e-12)
    assert night_fortune.longitude == pytest.approx((0.0 + 100.0 - 220.0) % 360.0, abs=1e-12)
    assert day_spirit.longitude == pytest.approx((0.0 + 100.0 - 220.0) % 360.0, abs=1e-12)
    assert night_spirit.longitude == pytest.approx((0.0 + 220.0 - 100.0) % 360.0, abs=1e-12)
    assert day_eros.longitude == pytest.approx((0.0 + day_spirit.longitude - day_fortune.longitude) % 360.0, abs=1e-12)
    assert night_eros.longitude == pytest.approx((0.0 + night_fortune.longitude - night_spirit.longitude) % 360.0, abs=1e-12)


def test_lots_reference_builder_resolves_rulers_fixed_degrees_and_optional_inputs() -> None:
    service = ArabicPartsService()
    refs = service._build_refs(
        {
            "Sun": 100.0,
            "Moon": 220.0,
            "Mercury": 80.0,
            "Venus": 10.0,
            "Mars": 35.0,
            "Jupiter": 250.0,
            "Saturn": 310.0,
        },
        {i + 1: i * 30.0 for i in range(12)},
        True,
        syzygy=15.0,
        prenatal_nm=25.0,
        prenatal_fm=205.0,
        lord_of_hour=77.0,
    )

    assert refs["Asc"] == pytest.approx(0.0, abs=1e-12)
    assert refs["MC"] == pytest.approx(270.0, abs=1e-12)
    assert refs["Dsc"] == pytest.approx(180.0, abs=1e-12)
    assert refs["IC"] == pytest.approx(90.0, abs=1e-12)
    assert refs["18 Aries"] == pytest.approx(18.0, abs=1e-12)
    assert refs["Vindemiatrix"] == pytest.approx(193.0, abs=1e-12)
    assert refs["Ruler H1"] == pytest.approx(35.0, abs=1e-12)   # Aries -> Mars
    assert refs["Ruler MC"] == pytest.approx(310.0, abs=1e-12)
    assert refs["Ruler Sun"] == pytest.approx(220.0, abs=1e-12)  # Sun in Cancer -> Moon
    assert refs["Ruler Syzygy"] == pytest.approx(35.0, abs=1e-12)  # 15 Aries -> Mars
    assert refs["New Moon"] == pytest.approx(25.0, abs=1e-12)
    assert refs["Prenatal Full Moon"] == pytest.approx(205.0, abs=1e-12)
    assert refs["Lord of Hour"] == pytest.approx(77.0, abs=1e-12)


@pytest.mark.requires_ephemeris
def test_moira_wrappers_for_dignities_and_lots_match_module_level_calculations(
    moira_engine: Moira,
    natal_chart,
    natal_houses,
) -> None:
    lons = natal_chart.longitudes(include_nodes=False)
    cusps_map = {i + 1: c for i, c in enumerate(natal_houses.cusps)}
    day = sect_light(lons.get("Sun", 0.0), natal_houses.asc) == "Sun"

    expected_lots = calculate_lots(lons, cusps_map, day)
    actual_lots = moira_engine.lots(natal_chart, natal_houses)

    planet_dicts = [
        {
            "name": name,
            "degree": data.longitude,
            "is_retrograde": data.speed < 0,
        }
        for name, data in natal_chart.planets.items()
    ]
    house_dicts = [{"number": i + 1, "degree": cusp} for i, cusp in enumerate(natal_houses.cusps)]
    expected_dignities = calculate_dignities(planet_dicts, house_dicts)
    actual_dignities = moira_engine.dignities(natal_chart, natal_houses)

    assert [(p.name, round(p.longitude, 8)) for p in actual_lots[:20]] == [
        (p.name, round(p.longitude, 8)) for p in expected_lots[:20]
    ]
    assert [
        (d.planet, d.essential_dignity, d.total_score, tuple(d.accidental_dignities))
        for d in actual_dignities
    ] == [
        (d.planet, d.essential_dignity, d.total_score, tuple(d.accidental_dignities))
        for d in expected_dignities
    ]


def test_list_parts_is_sorted_and_contains_core_named_lots() -> None:
    names = list_parts()
    assert names == sorted(names)
    for required in ("Fortune", "Spirit", "Eros (Valens)", "Victory"):
        assert required in names
