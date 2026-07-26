from __future__ import annotations

from dataclasses import replace

import pytest

from moira import Moira
from moira.dignities import (
    AccidentalConditionKind,
    AccidentalDignityCondition,
    AccidentalDignityPolicy,
    AccidentalDignityTruth,
    BesiegingDependencyCompletenessTruth,
    BesiegingTruth,
    ConditionPolarity,
    DignityComputationPolicy,
    DignityHorizonFrame,
    DispositorshipComputationPolicy,
    DispositorshipConditionState,
    DispositorshipOrderingPolicy,
    DispositorshipTerminationKind,
    UnsupportedSubjectHandling,
    DispositorshipUnsupportedSubjectPolicy,
    EssentialDignityKind,
    EssentialDignityDoctrine,
    EssentialDignityPolicy,
    HalbHayzDoctrine,
    MercurySectModel,
    HorizonComputationMethod,
    HorizonHemisphere,
    MODERN_DETRIMENT,
    MODERN_DOMICILE,
    PlanetaryConditionState,
    PlanetarySolarPhaseKind,
    PlanetarySolarPhaseTruth,
    calculate_condition_network_profile,
    PlanetaryReception,
    ReceptionBasis,
    MutualReceptionPolicy,
    ReceptionKind,
    ReceptionMode,
    SectHayzPolicy,
    SectComponentKind,
    SectStateKind,
    SolarConditionPolicy,
    SolarConditionKind,
    SolarProximityBand,
    SolarProximityTruth,
    TruthEvaluationStatus,
    calculate_chart_condition_profile,
    calculate_condition_profiles,
    calculate_dignities,
    calculate_dispositorship,
    calculate_dispositorship_condition_profiles,
    calculate_dispositorship_chart_condition_profile,
    calculate_dispositorship_network_profile,
    calculate_dispositorship_subsystem_profile,
    compare_dispositorship,
    calculate_receptions,
    besieging_truth,
    halb_required_hemisphere,
    is_in_halb,
    is_in_hayz,
    is_in_sect,
    is_besieged,
    mutual_receptions,
    oriental_occidental,
    planetary_solar_phase_truth,
    solar_proximity_truth,
    sect_light,
)
from moira.lots import (
    ArabicPart,
    ArabicPartClassification,
    ArabicPartComputationTruth,
    ArabicPartsService,
    PARTS_DEFINITIONS,
    LotChartConditionProfile,
    LotConditionProfile,
    LotConditionNetworkEdge,
    LotConditionNetworkEdgeMode,
    LotConditionNetworkProfile,
    LotConditionNetworkNode,
    LotDependency,
    LotDependencyCompletenessTruth,
    LotConditionState,
    LotDependencyRole,
    LotEvaluationStatus,
    LotsComputationPolicy,
    LotsDerivedReferencePolicy,
    LotsExternalReferencePolicy,
    LotsReferenceFailureMode,
    LotReferenceClassification,
    LotReferenceTruth,
    LotReferenceKind,
    LotReversalKind,
    LotArcPolicy,
    calculate_all_lot_dependencies,
    calculate_lot_chart_condition_profile,
    calculate_lot_condition_network_profile,
    calculate_lot_condition_profiles,
    calculate_lot_dependencies,
    calculate_lots,
    evaluate_lots,
    list_parts,
)


def _equal_houses(start: float = 0.0) -> list[dict]:
    return [{"number": i + 1, "degree": (start + i * 30.0) % 360.0} for i in range(12)]


def _complete_besieging_chart(**overrides: float) -> dict[str, float]:
    positions = {
        "Sun": 100.0,
        "Moon": 15.0,
        "Mercury": 150.0,
        "Venus": 200.0,
        "Mars": 10.0,
        "Jupiter": 250.0,
        "Saturn": 20.0,
    }
    positions.update(overrides)
    return positions


def _part_by_name(parts, name: str):
    for part in parts:
        if part.name == name:
            return part
    raise AssertionError(f"Part not found: {name}")


def test_essential_dignity_truth_preserves_all_atomic_components() -> None:
    by_name = {
        result.planet: result
        for result in calculate_dignities(
            [
                {"name": "Sun", "degree": 200.0},
                {"name": "Jupiter", "degree": 0.0},
                {"name": "Mars", "degree": 0.0},
            ],
            _equal_houses(0.0),
        )
    }

    jupiter = by_name["Jupiter"]
    assert jupiter.essential_dignity == "Bound"
    assert jupiter.essential_score == 2
    assert (
        jupiter.essential_truth.component(EssentialDignityKind.BOUND).ruler
        == "Jupiter"
    )
    assert (
        jupiter.essential_truth.component(EssentialDignityKind.BOUND).matched
        is True
    )
    assert (
        jupiter.essential_truth.component(EssentialDignityKind.PEREGRINE).matched
        is False
    )

    mars = by_name["Mars"]
    matched_kinds = {
        component.kind for component in mars.essential_truth.matched_components
    }
    assert EssentialDignityKind.DOMICILE in matched_kinds
    assert EssentialDignityKind.FACE in matched_kinds
    assert mars.essential_dignity == "Domicile"


def test_exact_horizon_truth_is_house_system_independent_and_fails_closed() -> None:
    frame = DignityHorizonFrame(asc_longitude=0.0, mc_longitude=270.0)
    planets = [
        {"name": "Sun", "degree": 240.0},
        {"name": "Venus", "degree": 210.0},
        {"name": "Mars", "degree": 0.0},
    ]

    first = {
        result.planet: result
        for result in calculate_dignities(
            planets,
            _equal_houses(0.0),
            horizon_frame=frame,
        )
    }
    second = {
        result.planet: result
        for result in calculate_dignities(
            planets,
            _equal_houses(180.0),
            horizon_frame=frame,
        )
    }

    for planet in ("Sun", "Venus", "Mars"):
        assert first[planet].sect_truth.is_day_chart is True
        assert second[planet].sect_truth.is_day_chart is True
        assert (
            first[planet].sect_truth.actual_hemisphere
            == second[planet].sect_truth.actual_hemisphere
        )
        assert (
            first[planet].sect_truth.horizon_truth.method
            is HorizonComputationMethod.ZODIACAL_ANGLES
        )

    assert first["Venus"].sect_truth.horizon_truth.hemisphere is HorizonHemisphere.ABOVE
    assert first["Mars"].sect_truth.horizon_truth.status is TruthEvaluationStatus.NOT_EVALUABLE
    assert first["Mars"].sect_truth.in_halb is None
    assert (
        first["Mars"].sect_truth.component(SectComponentKind.HALB).status
        is TruthEvaluationStatus.NOT_EVALUABLE
    )

    with pytest.raises(ValueError, match="Chart sect is not evaluable"):
        calculate_dignities(
            [{"name": "Sun", "degree": 0.0}],
            _equal_houses(0.0),
            horizon_frame=frame,
        )


def test_exact_mercury_conjunction_is_typed_not_evaluable() -> None:
    mercury = {
        result.planet: result
        for result in calculate_dignities(
            [
                {"name": "Sun", "degree": 240.0},
                {"name": "Mercury", "degree": 240.0},
            ],
            _equal_houses(0.0),
            horizon_frame=DignityHorizonFrame(
                asc_longitude=0.0,
                mc_longitude=270.0,
            ),
        )
    }["Mercury"]

    assert mercury.sect_truth.mercury_phase_truth.status is TruthEvaluationStatus.NOT_EVALUABLE
    assert mercury.sect_truth.mercury_phase_truth.reason == "mercury_conjunct_sun"
    assert mercury.sect_truth.in_sect is None
    assert mercury.sect_classification.state is SectStateKind.NOT_EVALUABLE
    assert "In Halb" not in mercury.accidental_dignities
    assert "In Hayz" not in mercury.accidental_dignities


def test_planetary_solar_phase_truth_fails_closed_at_both_boundaries() -> None:
    oriental = planetary_solar_phase_truth("Mars", 10.0, 130.0)
    assert oriental.status is TruthEvaluationStatus.EVALUATED
    assert oriental.phase is PlanetarySolarPhaseKind.ORIENTAL
    assert oriental.forward_distance_to_sun_deg == pytest.approx(120.0)
    assert oriental_occidental("Mars", 10.0, 130.0) == "oriental"

    conjunct = planetary_solar_phase_truth("Mars", 130.0, 130.0)
    assert conjunct.status is TruthEvaluationStatus.NOT_EVALUABLE
    assert conjunct.phase is None
    assert conjunct.reason == "planet_conjunct_sun"
    assert oriental_occidental("Mars", 130.0, 130.0) is None

    opposite = planetary_solar_phase_truth("Venus", 310.0, 130.0)
    assert opposite.status is TruthEvaluationStatus.NOT_EVALUABLE
    assert opposite.phase is None
    assert opposite.reason == "planet_opposite_sun"
    assert oriental_occidental("Venus", 310.0, 130.0) is None

    with pytest.raises(ValueError, match="evaluated results require"):
        PlanetarySolarPhaseTruth(
            status=TruthEvaluationStatus.EVALUATED,
            phase=None,
            forward_distance_to_sun_deg=120.0,
        )
    phase_condition = AccidentalDignityCondition(
        "phase",
        "oriental",
        "Oriental",
        2,
    )
    with pytest.raises(ValueError, match="not_evaluable phase truth"):
        AccidentalDignityTruth(
            conditions=[phase_condition],
            planetary_solar_phase_truth=conjunct,
            oriental_condition=phase_condition,
        )


def test_planetary_solar_phase_truth_is_preserved_when_policy_suppresses_condition() -> None:
    planets = [
        {"name": "Sun", "degree": 130.0},
        {"name": "Venus", "degree": 10.0},
    ]
    disabled_policy = DignityComputationPolicy(
        accidental=AccidentalDignityPolicy(
            include_oriental_occidental=False,
        )
    )
    venus = {
        result.planet: result
        for result in calculate_dignities(
            planets,
            _equal_houses(300.0),
            policy=disabled_policy,
        )
    }["Venus"]

    assert (
        venus.accidental_truth.planetary_solar_phase_truth.status
        is TruthEvaluationStatus.EVALUATED
    )
    assert (
        venus.accidental_truth.planetary_solar_phase_truth.phase
        is PlanetarySolarPhaseKind.ORIENTAL
    )
    assert venus.accidental_truth.oriental_condition is None
    assert "Oriental" not in venus.accidental_dignities


def test_planetary_solar_phase_boundary_never_assembles_a_label_or_score() -> None:
    mars = {
        result.planet: result
        for result in calculate_dignities(
            [
                {"name": "Sun", "degree": 130.0},
                {"name": "Mars", "degree": 130.0},
            ],
            _equal_houses(300.0),
        )
    }["Mars"]

    phase_truth = mars.accidental_truth.planetary_solar_phase_truth
    assert phase_truth.status is TruthEvaluationStatus.NOT_EVALUABLE
    assert phase_truth.reason == "planet_conjunct_sun"
    assert mars.accidental_truth.oriental_condition is None
    assert "Oriental" not in mars.accidental_dignities
    assert "Occidental" not in mars.accidental_dignities


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


def test_dignities_expose_source_corrected_halb_hayz_truth() -> None:
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

    legacy_policy = DignityComputationPolicy(
        accidental=AccidentalDignityPolicy(
            include_oriental_occidental=False,
            sect=SectHayzPolicy(include_halb=False),
        )
    )
    by_name = {
        d.planet: d
        for d in calculate_dignities(
            planet_positions,
            house_positions,
            policy=legacy_policy,
        )
    }

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
        ) == ("Bound", ["Cadent (H3)", "Direct", "Mutual Reception (Mars)"], 5)
    assert (
        by_name["Venus"].essential_truth.component(
            EssentialDignityKind.DETRIMENT
        ).matched
        is True
    )
    assert (
        by_name["Mars"].essential_dignity,
        by_name["Mars"].accidental_dignities,
        by_name["Mars"].accidental_score,
    ) == (
        "Detriment",
        ["Angular (H4)", "Direct", "Mutual Reception (Venus)", "In Hayz"],
        13,
    )

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
    assert venus.essential_classification.kind is EssentialDignityKind.BOUND
    assert venus.essential_classification.polarity is ConditionPolarity.STRENGTHENING
    assert venus.sect_classification is not None
    assert venus.sect_classification.state is SectStateKind.IN_HALB
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


@pytest.mark.parametrize(
    ("planet_lon", "expected_band"),
    [
        (100.0, SolarProximityBand.CAZIMI),
        (100.283, SolarProximityBand.CAZIMI),
        (100.284, SolarProximityBand.COMBUST),
        (108.0, SolarProximityBand.COMBUST),
        (108.001, SolarProximityBand.UNDER_SUNBEAMS),
        (117.0, SolarProximityBand.UNDER_SUNBEAMS),
        (117.001, SolarProximityBand.CLEAR),
    ],
)
def test_solar_proximity_truth_preserves_exclusive_raw_bands(
    planet_lon: float,
    expected_band: SolarProximityBand,
) -> None:
    truth = solar_proximity_truth("Mercury", planet_lon, 100.0)

    assert truth.status is TruthEvaluationStatus.EVALUATED
    assert truth.band is expected_band
    assert truth.distance_from_sun_deg == pytest.approx(
        abs(planet_lon - 100.0),
        abs=1e-12,
    )
    assert truth.reason is None


def test_solar_proximity_truth_separates_non_applicability_and_policy_suppression() -> None:
    sun_truth = solar_proximity_truth("Sun", 100.0, 100.0)
    assert sun_truth.status is TruthEvaluationStatus.NOT_EVALUABLE
    assert sun_truth.band is None
    assert sun_truth.distance_from_sun_deg == 0.0
    assert sun_truth.reason == "solar_proximity_not_applicable_to_sun"

    with pytest.raises(ValueError, match="evaluated results require"):
        SolarProximityTruth(
            status=TruthEvaluationStatus.EVALUATED,
            band=None,
            distance_from_sun_deg=5.0,
        )

    planets = [
        {"name": "Sun", "degree": 100.0},
        {"name": "Moon", "degree": 105.0},
        {"name": "Mercury", "degree": 105.0},
    ]
    policy = DignityComputationPolicy(
        accidental=AccidentalDignityPolicy(
            include_oriental_occidental=False,
            solar=SolarConditionPolicy(
                include_cazimi=False,
                include_combust=False,
                include_under_sunbeams=False,
            ),
        )
    )
    by_name = {
        result.planet: result
        for result in calculate_dignities(
            planets,
            _equal_houses(0.0),
            policy=policy,
        )
    }

    assert (
        by_name["Mercury"].accidental_truth.solar_proximity_truth.band
        is SolarProximityBand.COMBUST
    )
    assert by_name["Mercury"].solar_truth.present is False
    assert by_name["Mercury"].solar_truth.distance_from_sun == pytest.approx(5.0)
    assert (
        by_name["Moon"].accidental_truth.solar_proximity_truth.band
        is SolarProximityBand.COMBUST
    )
    assert by_name["Moon"].solar_truth.present is False
    assert by_name["Moon"].solar_truth.distance_from_sun is None
    assert (
        by_name["Sun"].accidental_truth.solar_proximity_truth.status
        is TruthEvaluationStatus.NOT_EVALUABLE
    )


def test_solar_proximity_policy_assembly_preserves_existing_band_fallthrough() -> None:
    planets = [
        {"name": "Sun", "degree": 100.0},
        {"name": "Moon", "degree": 220.0},
        {"name": "Mercury", "degree": 100.2},
    ]
    policy = DignityComputationPolicy(
        accidental=AccidentalDignityPolicy(
            include_oriental_occidental=False,
            solar=SolarConditionPolicy(
                include_cazimi=False,
                include_combust=True,
                include_under_sunbeams=True,
            ),
        )
    )
    mercury = {
        result.planet: result
        for result in calculate_dignities(
            planets,
            _equal_houses(0.0),
            policy=policy,
        )
    }["Mercury"]

    assert (
        mercury.accidental_truth.solar_proximity_truth.band
        is SolarProximityBand.CAZIMI
    )
    assert mercury.solar_truth.condition == "combust"
    assert mercury.solar_truth.label == "Combust"
    assert mercury.solar_truth.score == -5


def test_solar_proximity_luminary_policy_can_admit_moon_but_never_sun_itself() -> None:
    policy = DignityComputationPolicy(
        accidental=AccidentalDignityPolicy(
            include_oriental_occidental=False,
            solar=SolarConditionPolicy(include_for_luminaries=True),
        )
    )
    by_name = {
        result.planet: result
        for result in calculate_dignities(
            [
                {"name": "Sun", "degree": 100.0},
                {"name": "Moon", "degree": 105.0},
            ],
            _equal_houses(0.0),
            policy=policy,
        )
    }

    assert by_name["Moon"].solar_truth.condition == "combust"
    assert by_name["Sun"].solar_truth.present is False
    assert (
        by_name["Sun"].accidental_truth.solar_proximity_truth.status
        is TruthEvaluationStatus.NOT_EVALUABLE
    )


def test_besieging_truth_requires_complete_dependencies_and_preserves_neighbors() -> None:
    positions = _complete_besieging_chart()
    truth = besieging_truth(
        positions["Moon"],
        positions,
        planet_name="Moon",
    )

    assert truth.status is TruthEvaluationStatus.EVALUATED
    assert truth.dependency_truth.complete is True
    assert truth.dependency_truth.missing_bodies == ()
    assert truth.besieged is True
    assert truth.backward_neighbor == "Mars"
    assert truth.forward_neighbor == "Saturn"
    assert truth.backward_distance_deg == pytest.approx(5.0)
    assert truth.forward_distance_deg == pytest.approx(5.0)
    assert truth.pair == ("Mars", "Saturn")
    assert is_besieged(
        positions["Moon"],
        positions,
        planet_name="Moon",
    ) == ("Mars", "Saturn")
    assert is_besieged(positions["Moon"], positions) == ("Mars", "Saturn")


def test_besieging_truth_distinguishes_evaluated_absence_from_missing_bodies() -> None:
    outside_orb = _complete_besieging_chart(Saturn=40.0)
    evaluated = besieging_truth(
        outside_orb["Moon"],
        outside_orb,
        planet_name="Moon",
    )
    assert evaluated.status is TruthEvaluationStatus.EVALUATED
    assert evaluated.besieged is False
    assert evaluated.pair is None
    assert evaluated.forward_neighbor == "Saturn"
    assert evaluated.forward_distance_deg == pytest.approx(25.0)

    incomplete = {
        "Moon": 15.0,
        "Mars": 10.0,
        "Saturn": 20.0,
    }
    missing = besieging_truth(
        incomplete["Moon"],
        incomplete,
        planet_name="Moon",
    )
    assert missing.status is TruthEvaluationStatus.NOT_EVALUABLE
    assert missing.besieged is None
    assert missing.reason == "missing_required_chart_bodies"
    assert missing.dependency_truth.complete is False
    assert missing.dependency_truth.missing_bodies == (
        "Sun",
        "Mercury",
        "Venus",
        "Jupiter",
    )
    assert is_besieged(
        incomplete["Moon"],
        incomplete,
        planet_name="Moon",
    ) is None

    long_directed_arc = {
        "Sun": 10.0,
        "Moon": 0.0,
        "Mercury": 20.0,
        "Venus": 30.0,
        "Mars": 40.0,
        "Jupiter": 50.0,
        "Saturn": 170.0,
    }
    long_arc_truth = besieging_truth(
        long_directed_arc["Moon"],
        long_directed_arc,
        planet_name="Moon",
    )
    assert long_arc_truth.status is TruthEvaluationStatus.EVALUATED
    assert long_arc_truth.besieged is False
    assert long_arc_truth.backward_neighbor == "Saturn"
    assert long_arc_truth.backward_distance_deg == pytest.approx(190.0)


def test_besieging_truth_fails_closed_on_conjunctions_and_neighbor_ties() -> None:
    conjunct = _complete_besieging_chart(Venus=15.0)
    conjunct_truth = besieging_truth(
        conjunct["Moon"],
        conjunct,
        planet_name="Moon",
    )
    assert conjunct_truth.status is TruthEvaluationStatus.NOT_EVALUABLE
    assert conjunct_truth.reason == "one_or_more_bodies_conjunct_target"
    assert conjunct_truth.ambiguous_bodies == ("Venus",)

    tied = _complete_besieging_chart(
        Sun=20.0,
        Mars=10.0,
        Saturn=10.0,
    )
    tied_truth = besieging_truth(
        tied["Moon"],
        tied,
        planet_name="Moon",
    )
    assert tied_truth.status is TruthEvaluationStatus.NOT_EVALUABLE
    assert tied_truth.reason == "nearest_neighbor_tie"
    assert tied_truth.ambiguous_bodies == ("Mars", "Saturn")
    assert tied_truth.pair is None


def test_besieging_truth_rejects_malformed_dependency_and_condition_assembly() -> None:
    with pytest.raises(ValueError, match="status must be"):
        BesiegingDependencyCompletenessTruth(
            status="evaluated",  # type: ignore[arg-type]
            required_bodies=(),
            supplied_bodies=(),
            missing_bodies=(),
        )

    with pytest.raises(ValueError, match="missing_bodies must match"):
        BesiegingDependencyCompletenessTruth(
            status=TruthEvaluationStatus.NOT_EVALUABLE,
            required_bodies=("Sun", "Moon"),
            supplied_bodies=("Sun",),
            missing_bodies=(),
            reason="missing_required_chart_bodies",
        )

    incomplete = besieging_truth(
        15.0,
        {"Moon": 15.0, "Mars": 10.0, "Saturn": 20.0},
        planet_name="Moon",
    )
    condition = AccidentalDignityCondition(
        "besieging",
        "besieged",
        "Besieged (Mars/Saturn)",
        -5,
    )
    with pytest.raises(ValueError, match="not_evaluable besieging truth"):
        AccidentalDignityTruth(
            conditions=[condition],
            besieging_truth=incomplete,
            besieged_condition=condition,
        )
    complete_dependencies = BesiegingDependencyCompletenessTruth(
        status=TruthEvaluationStatus.EVALUATED,
        required_bodies=tuple(_complete_besieging_chart()),
        supplied_bodies=tuple(_complete_besieging_chart()),
        missing_bodies=(),
    )
    with pytest.raises(ValueError, match="besieged must match"):
        BesiegingTruth(
            status=TruthEvaluationStatus.EVALUATED,
            dependency_truth=complete_dependencies,
            target_planet="Moon",
            target_longitude=15.0,
            orb_deg=12.0,
            besieged=True,
            backward_neighbor="Venus",
            forward_neighbor="Saturn",
            backward_distance_deg=5.0,
            forward_distance_deg=5.0,
        )
    with pytest.raises(ValueError, match="besieged must match"):
        BesiegingTruth(
            status=TruthEvaluationStatus.EVALUATED,
            dependency_truth=complete_dependencies,
            target_planet="Moon",
            target_longitude=15.0,
            orb_deg=12.0,
            besieged=False,
            backward_neighbor="Mars",
            forward_neighbor="Saturn",
            backward_distance_deg=5.0,
            forward_distance_deg=5.0,
        )


def test_dignity_assembly_never_scores_incomplete_besieging_dependencies() -> None:
    incomplete_planets = [
        {"name": "Sun", "degree": 100.0},
        {"name": "Moon", "degree": 15.0},
        {"name": "Mars", "degree": 10.0},
        {"name": "Saturn", "degree": 20.0},
    ]
    moon = {
        result.planet: result
        for result in calculate_dignities(
            incomplete_planets,
            _equal_houses(0.0),
        )
    }["Moon"]
    assert (
        moon.accidental_truth.besieging_truth.status
        is TruthEvaluationStatus.NOT_EVALUABLE
    )
    assert moon.accidental_truth.besieged_condition is None
    assert not any(
        label.startswith("Besieged") for label in moon.accidental_dignities
    )

    complete_planets = [
        {"name": name, "degree": longitude}
        for name, longitude in _complete_besieging_chart().items()
    ]
    complete_moon = {
        result.planet: result
        for result in calculate_dignities(
            complete_planets,
            _equal_houses(0.0),
        )
    }["Moon"]
    assert complete_moon.accidental_truth.besieging_truth.besieged is True
    assert complete_moon.accidental_truth.besieged_condition is not None
    assert "Besieged (Mars/Saturn)" in complete_moon.accidental_dignities


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

    policy = DignityComputationPolicy(
        accidental=AccidentalDignityPolicy(
            include_oriental_occidental=False,
        )
    )
    mercury = {
        d.planet: d
        for d in calculate_dignities(
            planet_positions,
            house_positions,
            policy=policy,
        )
    }["Mercury"]

    assert mercury.accidental_dignities == ["Angular (H4)", "Direct", "Combust"]
    assert mercury.solar_truth.present is True
    assert mercury.solar_truth.condition == "combust"
    assert mercury.solar_truth.label == "Combust"
    assert mercury.solar_truth.score == -5
    assert mercury.solar_truth.distance_from_sun == pytest.approx(5.0, abs=1e-12)
    assert mercury.accidental_truth.solar_condition.label == "Combust"
    assert (
        mercury.accidental_truth.solar_proximity_truth.band
        is SolarProximityBand.COMBUST
    )
    assert mercury.sect_truth is not None
    assert mercury.sect_truth.in_sect is True
    assert mercury.sect_truth.in_halb is False
    assert mercury.sect_truth.in_hayz is None
    assert (
        mercury.sect_truth.component(SectComponentKind.HAYZ).status
        is TruthEvaluationStatus.NOT_EVALUABLE
    )
    assert mercury.sect_truth.hayz_evaluable is False
    assert [c.category for c in mercury.accidental_truth.conditions] == ["house", "motion", "solar"]
    assert mercury.solar_classification.kind is SolarConditionKind.COMBUST
    assert mercury.solar_classification.polarity is ConditionPolarity.WEAKENING
    assert mercury.sect_classification is not None
    assert mercury.sect_classification.state is SectStateKind.IN_SECT
    assert [c.kind for c in mercury.accidental_classification.conditions] == [
        AccidentalConditionKind.ANGULAR,
        AccidentalConditionKind.DIRECT,
        AccidentalConditionKind.COMBUST,
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
            include_oriental_occidental=False,
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
                include_halb=False,
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


def test_halb_policy_switch_controls_condition_and_score() -> None:
    house_positions = _equal_houses(300.0)
    planet_positions = [
        {"name": "Sun", "degree": 130.0, "is_retrograde": False},
        {"name": "Mercury", "degree": 132.0, "is_retrograde": False},
    ]
    enabled_policy = DignityComputationPolicy(
        accidental=AccidentalDignityPolicy(
            include_oriental_occidental=False,
            sect=SectHayzPolicy(include_hayz=False, include_halb=True),
        )
    )
    disabled_policy = DignityComputationPolicy(
        accidental=AccidentalDignityPolicy(
            include_oriental_occidental=False,
            sect=SectHayzPolicy(include_hayz=False, include_halb=False),
        )
    )

    enabled = {
        item.planet: item
        for item in calculate_dignities(
            planet_positions, house_positions, policy=enabled_policy
        )
    }["Sun"]
    disabled = {
        item.planet: item
        for item in calculate_dignities(
            planet_positions, house_positions, policy=disabled_policy
        )
    }["Sun"]

    assert "In Halb" in enabled.accidental_dignities
    assert enabled.accidental_truth.halb_condition is not None
    assert "In Halb" not in disabled.accidental_dignities
    assert disabled.accidental_truth.halb_condition is None
    assert enabled.accidental_score == (
        disabled.accidental_score + enabled.accidental_truth.halb_condition.score
    )


def test_halb_uses_sect_relative_hemisphere_in_day_and_night_charts() -> None:
    assert halb_required_hemisphere("Sun", is_day_chart=True) == "above"
    assert halb_required_hemisphere("Sun", is_day_chart=False) == "below"
    assert halb_required_hemisphere("Mars", is_day_chart=True) == "below"
    assert halb_required_hemisphere("Mars", is_day_chart=False) == "above"

    assert is_in_halb("Sun", "Aries", 9, is_day_chart=True)
    assert not is_in_halb("Sun", "Aries", 3, is_day_chart=True)
    assert is_in_halb("Sun", "Aries", 3, is_day_chart=False)
    assert not is_in_halb("Sun", "Aries", 9, is_day_chart=False)

    assert is_in_halb("Mars", "Cancer", 3, is_day_chart=True)
    assert not is_in_halb("Mars", "Cancer", 9, is_day_chart=True)
    assert is_in_halb("Mars", "Cancer", 9, is_day_chart=False)
    assert not is_in_halb("Mars", "Cancer", 3, is_day_chart=False)


def test_hayz_is_halb_plus_planetary_gender_and_mars_is_feminine() -> None:
    assert is_in_hayz("Mars", "Cancer", 9, is_day_chart=False)
    assert not is_in_hayz("Mars", "Leo", 9, is_day_chart=False)
    assert not is_in_hayz("Mars", "Cancer", 3, is_day_chart=False)


def test_mercury_sect_requires_phase_and_mercury_hayz_is_not_invented() -> None:
    with pytest.raises(ValueError, match="Mercury sect requires"):
        is_in_sect("Mercury", is_day_chart=True)

    assert halb_required_hemisphere(
        "Mercury",
        is_day_chart=True,
        mercury_rises_before_sun=True,
    ) == "above"
    assert is_in_halb(
        "Mercury",
        "Gemini",
        9,
        is_day_chart=True,
        mercury_rises_before_sun=True,
    )
    assert not is_in_hayz(
        "Mercury",
        "Gemini",
        9,
        is_day_chart=True,
        mercury_rises_before_sun=True,
    )


def test_dignity_chart_requires_sun_and_does_not_fabricate_mercury_phase() -> None:
    with pytest.raises(ValueError, match="Sun"):
        calculate_dignities(
            [{"name": "Mars", "degree": 15.0}],
            _equal_houses(0.0),
        )

    result = calculate_dignities(
        [
            {"name": "Sun", "degree": 200.0},
            {"name": "Mars", "degree": 15.0},
        ],
        _equal_houses(0.0),
    )
    mars = next(item for item in result if item.planet == "Mars")
    assert mars.sect_truth is not None
    assert mars.sect_truth.doctrine is HalbHayzDoctrine.AL_QABISI_BONATTI_DYKES_2007
    assert mars.sect_truth.mercury_rises_before_sun is None
    assert mars.sect_truth.in_halb is mars.sect_truth.hemisphere_matches


def test_oriental_occidental_policy_switch_controls_condition_and_score() -> None:
    house_positions = _equal_houses(300.0)
    planet_positions = [
        {"name": "Sun", "degree": 130.0, "is_retrograde": False},
        {"name": "Venus", "degree": 10.0, "is_retrograde": False},
    ]
    disabled_policy = DignityComputationPolicy(
        accidental=AccidentalDignityPolicy(
            include_oriental_occidental=False,
        )
    )

    enabled = {
        item.planet: item
        for item in calculate_dignities(planet_positions, house_positions)
    }["Venus"]
    disabled = {
        item.planet: item
        for item in calculate_dignities(
            planet_positions, house_positions, policy=disabled_policy
        )
    }["Venus"]

    assert "Oriental" in enabled.accidental_dignities
    assert enabled.accidental_truth.oriental_condition is not None
    assert "Oriental" not in disabled.accidental_dignities
    assert disabled.accidental_truth.oriental_condition is None
    assert enabled.accidental_score == (
        disabled.accidental_score
        + enabled.accidental_truth.oriental_condition.score
    )


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


def test_modern_co_ruler_policy_adds_outer_planet_essential_dignities() -> None:
    house_positions = _equal_houses(300.0)
    planet_positions = [
        {"name": "Sun", "degree": 130.0, "is_retrograde": False},
        {"name": "Moon", "degree": 100.0, "is_retrograde": False},
        {"name": "Mercury", "degree": 70.0, "is_retrograde": False},
        {"name": "Venus", "degree": 40.0, "is_retrograde": False},
        {"name": "Mars", "degree": 220.0, "is_retrograde": False},
        {"name": "Jupiter", "degree": 340.0, "is_retrograde": False},
        {"name": "Saturn", "degree": 310.0, "is_retrograde": False},
        {"name": "Uranus", "degree": 315.0, "is_retrograde": False},
        {"name": "Neptune", "degree": 345.0, "is_retrograde": False},
        {"name": "Pluto", "degree": 225.0, "is_retrograde": False},
    ]
    policy = DignityComputationPolicy(
        essential=EssentialDignityPolicy(
            doctrine=EssentialDignityDoctrine.MODERN_CO_RULERS,
        )
    )

    traditional = calculate_dignities(planet_positions, house_positions)
    modern = calculate_dignities(planet_positions, house_positions, policy=policy)
    by_name = {d.planet: d for d in modern}

    assert [d.planet for d in traditional] == ["Sun", "Moon", "Mercury", "Venus", "Mars", "Jupiter", "Saturn"]
    assert [d.planet for d in modern] == [
        "Sun", "Moon", "Mercury", "Venus", "Mars", "Jupiter", "Saturn", "Uranus", "Neptune", "Pluto"
    ]
    assert MODERN_DOMICILE["Uranus"] == ["Aquarius"]
    assert MODERN_DETRIMENT["Pluto"] == ["Taurus"]
    assert by_name["Uranus"].essential_dignity == "Domicile"
    assert by_name["Neptune"].essential_dignity == "Domicile"
    assert by_name["Pluto"].essential_dignity == "Domicile"
    assert by_name["Uranus"].essential_score == 5
    assert by_name["Uranus"].essential_truth.matching_signs == ("Aquarius",)
    assert by_name["Saturn"].essential_dignity == "Domicile"


def test_modern_co_ruler_policy_adds_outer_planet_detriments() -> None:
    house_positions = _equal_houses(300.0)
    planet_positions = [
        {"name": "Sun", "degree": 130.0, "is_retrograde": False},
        {"name": "Uranus", "degree": 125.0, "is_retrograde": False},
        {"name": "Neptune", "degree": 155.0, "is_retrograde": False},
        {"name": "Pluto", "degree": 35.0, "is_retrograde": False},
    ]
    policy = DignityComputationPolicy(
        essential=EssentialDignityPolicy(
            doctrine=EssentialDignityDoctrine.MODERN_CO_RULERS,
        )
    )

    by_name = {
        d.planet: d
        for d in calculate_dignities(planet_positions, house_positions, policy=policy)
    }

    assert by_name["Uranus"].essential_dignity == "Detriment"
    assert by_name["Neptune"].essential_dignity == "Detriment"
    assert by_name["Pluto"].essential_dignity == "Detriment"
    assert by_name["Pluto"].essential_score == -5
    assert by_name["Pluto"].essential_truth.matching_signs == ("Taurus",)


def test_modern_co_ruler_policy_extends_domicile_receptions() -> None:
    planet_positions = [
        {"name": "Mars", "degree": 310.0, "is_retrograde": False},
        {"name": "Uranus", "degree": 5.0, "is_retrograde": False},
    ]
    policy = DignityComputationPolicy(
        essential=EssentialDignityPolicy(
            doctrine=EssentialDignityDoctrine.MODERN_CO_RULERS,
        )
    )

    receptions = calculate_receptions(planet_positions, policy=policy)

    assert [
        (r.receiving_planet, r.host_planet, r.basis, r.mode)
        for r in receptions
    ] == [
        ("Mars", "Uranus", ReceptionBasis.DOMICILE, ReceptionMode.MUTUAL),
        ("Uranus", "Mars", ReceptionBasis.DOMICILE, ReceptionMode.MUTUAL),
    ]


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


def test_dispositorship_phase1_distinguishes_final_dispositors_terminal_cycles_and_unsupported_subjects() -> None:
    planet_positions = [
        {"name": "Sun", "degree": 130.0, "is_retrograde": False},      # Leo -> Sun
        {"name": "Moon", "degree": 100.0, "is_retrograde": False},     # Cancer -> Moon
        {"name": "Mercury", "degree": 250.0, "is_retrograde": False},  # Sagittarius -> Jupiter -> Moon
        {"name": "Venus", "degree": 10.0, "is_retrograde": False},     # Aries -> Mars
        {"name": "Mars", "degree": 35.0, "is_retrograde": False},      # Taurus -> Venus
        {"name": "Jupiter", "degree": 95.0, "is_retrograde": False},   # Cancer -> Moon
        {"name": "Saturn", "degree": 200.0, "is_retrograde": False},   # Libra -> Venus -> Mars cycle
        {"name": "Pluto", "degree": 305.0, "is_retrograde": False},    # unsupported in Phase 1
    ]

    profile = calculate_dispositorship(planet_positions)

    assert [chain.initial_subject for chain in profile.chains[:7]] == [
        "Sun", "Moon", "Mercury", "Venus", "Mars", "Jupiter", "Saturn",
    ]
    assert profile.final_dispositors == ("Sun", "Moon")
    assert profile.terminal_cycles == (("Venus", "Mars"),)
    assert profile.unsupported_subjects == ("Pluto",)

    mercury = profile.get_chain("Mercury")
    assert mercury.subject_in_scope is True
    assert mercury.subject_has_dispositor is True
    assert mercury.termination_kind is DispositorshipTerminationKind.FINAL_DISPOSITOR
    assert mercury.terminal_subjects == ("Moon",)
    assert mercury.cycle_members == ()
    assert [(link.subject, link.subject_sign, link.dispositor) for link in mercury.links] == [
        ("Mercury", "Sagittarius", "Jupiter"),
        ("Jupiter", "Cancer", "Moon"),
        ("Moon", "Cancer", "Moon"),
    ]

    venus = profile.get_chain("Venus")
    assert venus.termination_kind is DispositorshipTerminationKind.TERMINAL_CYCLE
    assert venus.terminal_subjects == ("Venus", "Mars")
    assert venus.cycle_members == ("Venus", "Mars")
    assert venus.is_terminal_cycle is True
    assert venus.is_final_dispositor is False

    pluto = profile.get_chain("Pluto")
    assert pluto.subject_in_scope is False
    assert pluto.subject_has_dispositor is False
    assert pluto.termination_kind is DispositorshipTerminationKind.UNRESOLVED
    assert pluto.links == []


def test_dispositorship_reject_policy_fails_on_unsupported_subjects() -> None:
    planet_positions = [
        {"name": "Sun", "degree": 130.0, "is_retrograde": False},
        {"name": "Moon", "degree": 100.0, "is_retrograde": False},
        {"name": "Pluto", "degree": 305.0, "is_retrograde": False},
    ]
    policy = DispositorshipComputationPolicy(
        unsupported_subjects=DispositorshipUnsupportedSubjectPolicy(
            handling=UnsupportedSubjectHandling.REJECT,
        )
    )

    with pytest.raises(ValueError, match="unsupported subjects"):
        calculate_dispositorship(planet_positions, policy=policy)


def test_dispositorship_segregate_policy_reports_unsupported_without_out_of_scope_chains() -> None:
    planet_positions = [
        {"name": "Sun", "degree": 130.0, "is_retrograde": False},
        {"name": "Moon", "degree": 100.0, "is_retrograde": False},
        {"name": "Pluto", "degree": 305.0, "is_retrograde": False},
    ]
    policy = DispositorshipComputationPolicy(
        unsupported_subjects=DispositorshipUnsupportedSubjectPolicy(
            handling=UnsupportedSubjectHandling.SEGREGATE,
        )
    )

    profile = calculate_dispositorship(planet_positions, policy=policy)

    assert [chain.initial_subject for chain in profile.chains] == ["Sun", "Moon"]
    assert profile.unsupported_subjects == ("Pluto",)
    with pytest.raises(KeyError):
        profile.get_chain("Pluto")


def test_dispositorship_reports_unresolved_when_the_next_dispositor_is_missing_from_chart() -> None:
    planet_positions = [
        {"name": "Mercury", "degree": 250.0, "is_retrograde": False},  # Sagittarius -> Jupiter (missing)
        {"name": "Venus", "degree": 40.0, "is_retrograde": False},
    ]

    profile = calculate_dispositorship(planet_positions)
    mercury = profile.get_chain("Mercury")

    assert mercury.subject_in_scope is True
    assert mercury.subject_has_dispositor is True
    assert mercury.termination_kind is DispositorshipTerminationKind.UNRESOLVED
    assert mercury.terminal_subjects == ()
    assert mercury.cycle_members == ()
    assert [(link.subject, link.subject_sign, link.dispositor) for link in mercury.links] == [
        ("Mercury", "Sagittarius", "Jupiter"),
    ]


def test_dispositorship_non_dignity_order_is_honored_by_profile_and_finals() -> None:
    planet_positions = [
        {"name": "Moon", "degree": 100.0, "is_retrograde": False},     # Cancer -> Moon
        {"name": "Sun", "degree": 130.0, "is_retrograde": False},      # Leo -> Sun
        {"name": "Mercury", "degree": 250.0, "is_retrograde": False},  # Sagittarius -> Jupiter -> Moon
        {"name": "Jupiter", "degree": 95.0, "is_retrograde": False},   # Cancer -> Moon
    ]
    policy = DispositorshipComputationPolicy(
        ordering=DispositorshipOrderingPolicy(use_dignity_order=False),
    )

    profile = calculate_dispositorship(planet_positions, policy=policy)

    assert [chain.initial_subject for chain in profile.chains] == ["Moon", "Sun", "Mercury", "Jupiter"]
    assert profile.final_dispositors == ("Moon", "Sun")


def test_dispositorship_condition_profiles_integrate_chain_truth_without_recomputing_doctrine() -> None:
    planet_positions = [
        {"name": "Sun", "degree": 130.0, "is_retrograde": False},      # Leo -> Sun
        {"name": "Moon", "degree": 100.0, "is_retrograde": False},     # Cancer -> Moon
        {"name": "Mercury", "degree": 250.0, "is_retrograde": False},  # Sagittarius -> Jupiter -> Moon
        {"name": "Venus", "degree": 10.0, "is_retrograde": False},     # Aries -> Mars
        {"name": "Mars", "degree": 35.0, "is_retrograde": False},      # Taurus -> Venus
        {"name": "Jupiter", "degree": 95.0, "is_retrograde": False},   # Cancer -> Moon
        {"name": "Pluto", "degree": 305.0, "is_retrograde": False},
    ]

    profiles = calculate_dispositorship_condition_profiles(planet_positions)
    by_name = {profile.initial_subject: profile for profile in profiles}

    assert by_name["Sun"].state is DispositorshipConditionState.SELF_DISPOSED
    assert by_name["Sun"].resolves_to_final is True
    assert by_name["Sun"].chain_length == 1

    assert by_name["Mercury"].state is DispositorshipConditionState.RESOLVED_TO_FINAL
    assert by_name["Mercury"].termination_kind is DispositorshipTerminationKind.FINAL_DISPOSITOR
    assert by_name["Mercury"].terminal_subjects == ("Moon",)
    assert by_name["Mercury"].chain_length == 3

    assert by_name["Venus"].state is DispositorshipConditionState.TERMINAL_CYCLE
    assert by_name["Venus"].cycle_members == ("Venus", "Mars")
    assert by_name["Venus"].is_terminal_cycle is True

    assert by_name["Pluto"].state is DispositorshipConditionState.OUT_OF_SCOPE
    assert by_name["Pluto"].is_out_of_scope is True


def test_dispositorship_condition_profiles_preserve_segregated_scope_behavior() -> None:
    planet_positions = [
        {"name": "Sun", "degree": 130.0, "is_retrograde": False},
        {"name": "Moon", "degree": 100.0, "is_retrograde": False},
        {"name": "Pluto", "degree": 305.0, "is_retrograde": False},
    ]
    policy = DispositorshipComputationPolicy(
        unsupported_subjects=DispositorshipUnsupportedSubjectPolicy(
            handling=UnsupportedSubjectHandling.SEGREGATE,
        )
    )

    profiles = calculate_dispositorship_condition_profiles(planet_positions, policy=policy)

    assert [profile.initial_subject for profile in profiles] == ["Sun", "Moon"]


def test_dispositorship_chart_condition_profile_aggregates_local_states_without_recomputing() -> None:
    planet_positions = [
        {"name": "Sun", "degree": 130.0, "is_retrograde": False},      # self-disposed
        {"name": "Moon", "degree": 100.0, "is_retrograde": False},     # self-disposed
        {"name": "Mercury", "degree": 250.0, "is_retrograde": False},  # resolves to Moon
        {"name": "Jupiter", "degree": 95.0, "is_retrograde": False},   # self/resolution anchor for Mercury
        {"name": "Venus", "degree": 10.0, "is_retrograde": False},     # cycle
        {"name": "Mars", "degree": 35.0, "is_retrograde": False},      # cycle
        {"name": "Pluto", "degree": 305.0, "is_retrograde": False},    # out of scope
    ]

    chart_profile = calculate_dispositorship_chart_condition_profile(planet_positions)

    assert chart_profile.profile_count == 7
    assert chart_profile.self_disposed_count == 2
    assert chart_profile.resolved_to_final_count == 2
    assert chart_profile.terminal_cycle_count == 2
    assert chart_profile.unresolved_count == 0
    assert chart_profile.out_of_scope_count == 1
    assert chart_profile.final_dispositor_count == 2
    assert chart_profile.cycle_count == 1
    assert chart_profile.has_mixed_terminals is True


def test_dispositorship_chart_condition_profile_detects_unresolved_mixed_chart_state() -> None:
    planet_positions = [
        {"name": "Sun", "degree": 130.0, "is_retrograde": False},      # self-disposed
        {"name": "Mercury", "degree": 250.0, "is_retrograde": False},  # unresolved -> Jupiter missing
    ]

    chart_profile = calculate_dispositorship_chart_condition_profile(planet_positions)

    assert chart_profile.self_disposed_count == 1
    assert chart_profile.unresolved_count == 1
    assert chart_profile.final_dispositor_count == 1
    assert chart_profile.cycle_count == 0
    assert chart_profile.has_mixed_terminals is True


def test_dispositorship_network_profile_projects_direct_relations_and_cycle_reciprocity() -> None:
    planet_positions = [
        {"name": "Sun", "degree": 130.0, "is_retrograde": False},      # self-disposed, isolated
        {"name": "Moon", "degree": 100.0, "is_retrograde": False},     # final endpoint
        {"name": "Mercury", "degree": 250.0, "is_retrograde": False},  # Mercury -> Jupiter
        {"name": "Jupiter", "degree": 95.0, "is_retrograde": False},   # Jupiter -> Moon
        {"name": "Venus", "degree": 10.0, "is_retrograde": False},     # Venus -> Mars
        {"name": "Mars", "degree": 35.0, "is_retrograde": False},      # Mars -> Venus
        {"name": "Pluto", "degree": 305.0, "is_retrograde": False},    # out of scope
    ]

    network = calculate_dispositorship_network_profile(planet_positions)

    assert network.node_count == 6
    assert network.edge_count == 4
    assert network.reciprocal_edge_count == 2
    assert network.unilateral_edge_count == 2
    assert network.isolated_subjects == ["Sun"]
    assert network.most_connected_subjects == ["Venus", "Mars", "Jupiter"]

    edge_tuples = {(edge.source_subject, edge.target_subject, edge.mode.value) for edge in network.edges}
    assert ("Mercury", "Jupiter", "unilateral") in edge_tuples
    assert ("Jupiter", "Moon", "unilateral") in edge_tuples
    assert ("Venus", "Mars", "reciprocal") in edge_tuples
    assert ("Mars", "Venus", "reciprocal") in edge_tuples

    node_map = {node.subject: node for node in network.nodes}
    assert node_map["Sun"].is_isolated is True
    assert node_map["Moon"].incoming_count == 1
    assert node_map["Moon"].outgoing_count == 0
    assert node_map["Venus"].reciprocal_count == 1
    assert node_map["Mars"].reciprocal_count == 1


def test_dispositorship_network_profile_respects_segregated_scope() -> None:
    planet_positions = [
        {"name": "Sun", "degree": 130.0, "is_retrograde": False},
        {"name": "Moon", "degree": 100.0, "is_retrograde": False},
        {"name": "Pluto", "degree": 305.0, "is_retrograde": False},
    ]
    policy = DispositorshipComputationPolicy(
        unsupported_subjects=DispositorshipUnsupportedSubjectPolicy(
            handling=UnsupportedSubjectHandling.SEGREGATE,
        )
    )

    network = calculate_dispositorship_network_profile(planet_positions, policy=policy)

    assert [node.subject for node in network.nodes] == ["Sun", "Moon"]
    assert network.edge_count == 0
    assert network.isolated_subjects == ["Sun", "Moon"]


def test_dispositorship_subsystem_profile_hardens_cross_layer_alignment() -> None:
    planet_positions = [
        {"name": "Sun", "degree": 130.0, "is_retrograde": False},
        {"name": "Moon", "degree": 100.0, "is_retrograde": False},
        {"name": "Mercury", "degree": 250.0, "is_retrograde": False},
        {"name": "Jupiter", "degree": 95.0, "is_retrograde": False},
        {"name": "Venus", "degree": 10.0, "is_retrograde": False},
        {"name": "Mars", "degree": 35.0, "is_retrograde": False},
        {"name": "Pluto", "degree": 305.0, "is_retrograde": False},
    ]

    subsystem = calculate_dispositorship_subsystem_profile(planet_positions)

    assert [chain.initial_subject for chain in subsystem.profile.chains] == [
        profile.initial_subject for profile in subsystem.condition_profiles
    ]
    assert subsystem.chart_condition_profile.profiles == subsystem.condition_profiles
    assert [node.subject for node in subsystem.network_profile.nodes] == ["Sun", "Moon", "Mercury", "Venus", "Mars", "Jupiter"]
    assert subsystem.chart_condition_profile.final_dispositor_count == len(subsystem.profile.final_dispositors)
    assert subsystem.network_profile.edge_count == 4


def test_dispositorship_subsystem_profile_preserves_segregated_scope_cross_layer() -> None:
    planet_positions = [
        {"name": "Sun", "degree": 130.0, "is_retrograde": False},
        {"name": "Moon", "degree": 100.0, "is_retrograde": False},
        {"name": "Pluto", "degree": 305.0, "is_retrograde": False},
    ]
    policy = DispositorshipComputationPolicy(
        unsupported_subjects=DispositorshipUnsupportedSubjectPolicy(
            handling=UnsupportedSubjectHandling.SEGREGATE,
        )
    )

    subsystem = calculate_dispositorship_subsystem_profile(planet_positions, policy=policy)

    assert [chain.initial_subject for chain in subsystem.profile.chains] == ["Sun", "Moon"]
    assert [profile.initial_subject for profile in subsystem.condition_profiles] == ["Sun", "Moon"]
    assert subsystem.chart_condition_profile.out_of_scope_count == 0
    assert [node.subject for node in subsystem.network_profile.nodes] == ["Sun", "Moon"]


def test_dispositorship_comparison_bundle_preserves_named_profiles_and_derived_finals() -> None:
    planet_positions = [
        {"name": "Sun", "degree": 130.0, "is_retrograde": False},
        {"name": "Moon", "degree": 100.0, "is_retrograde": False},
        {"name": "Mercury", "degree": 250.0, "is_retrograde": False},
        {"name": "Venus", "degree": 10.0, "is_retrograde": False},
        {"name": "Mars", "degree": 35.0, "is_retrograde": False},
        {"name": "Jupiter", "degree": 95.0, "is_retrograde": False},
        {"name": "Saturn", "degree": 200.0, "is_retrograde": False},
    ]

    default_policy = DispositorshipComputationPolicy()
    reject_policy = DispositorshipComputationPolicy(
        unsupported_subjects=DispositorshipUnsupportedSubjectPolicy(
            handling=UnsupportedSubjectHandling.REJECT,
        )
    )

    bundle = compare_dispositorship(
        planet_positions,
        [
            ("traditional_default", default_policy),
            ("traditional_strict", reject_policy),
        ],
    )

    assert bundle.doctrine_names == ("traditional_default", "traditional_strict")
    assert bundle.shared_final_dispositors == ("Sun", "Moon")
    assert bundle.all_final_dispositors == ("Sun", "Moon")
    assert bundle.get_item("traditional_default").profile.final_dispositors == ("Sun", "Moon")
    assert bundle.get_item("traditional_strict").profile.final_dispositors == ("Sun", "Moon")


def test_dispositorship_comparison_bundle_honors_profile_ordering_in_bundle_summaries() -> None:
    planet_positions = [
        {"name": "Moon", "degree": 100.0, "is_retrograde": False},
        {"name": "Sun", "degree": 130.0, "is_retrograde": False},
        {"name": "Mercury", "degree": 250.0, "is_retrograde": False},
        {"name": "Jupiter", "degree": 95.0, "is_retrograde": False},
    ]
    ordered_policy = DispositorshipComputationPolicy(
        ordering=DispositorshipOrderingPolicy(use_dignity_order=False),
    )

    bundle = compare_dispositorship(
        planet_positions,
        [
            ("input_order", ordered_policy),
            ("default_order", DispositorshipComputationPolicy()),
        ],
    )

    assert bundle.get_item("input_order").profile.final_dispositors == ("Moon", "Sun")
    assert bundle.get_item("default_order").profile.final_dispositors == ("Sun", "Moon")
    assert bundle.shared_final_dispositors == ("Moon", "Sun")
    assert bundle.all_final_dispositors == ("Moon", "Sun")


def test_dispositorship_comparison_bundle_rejects_duplicate_names() -> None:
    planet_positions = [
        {"name": "Sun", "degree": 130.0, "is_retrograde": False},
        {"name": "Moon", "degree": 100.0, "is_retrograde": False},
    ]

    with pytest.raises(ValueError, match="duplicate doctrine profile name"):
        compare_dispositorship(
            planet_positions,
            [
                ("traditional", DispositorshipComputationPolicy()),
                ("traditional", DispositorshipComputationPolicy()),
            ],
        )


def test_dispositorship_profile_lookup_uses_canonical_subject_normalization() -> None:
    planet_positions = [
        {"name": "sun", "degree": 130.0, "is_retrograde": False},
        {"name": "moon", "degree": 100.0, "is_retrograde": False},
    ]

    profile = calculate_dispositorship(planet_positions)

    assert profile.get_chain(" moon ").initial_subject == "Moon"
    with pytest.raises(KeyError, match="dispositorship chain not found"):
        profile.get_chain("pluto")


def test_dispositorship_comparison_bundle_lookup_sanitizes_missing_item_errors() -> None:
    planet_positions = [
        {"name": "Sun", "degree": 130.0, "is_retrograde": False},
        {"name": "Moon", "degree": 100.0, "is_retrograde": False},
    ]

    bundle = compare_dispositorship(
        planet_positions,
        [("traditional", DispositorshipComputationPolicy())],
    )

    with pytest.raises(KeyError, match="dispositorship comparison item not found"):
        bundle.get_item("internal-doctrine-name")


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


def test_lots_preserve_computation_truth_without_changing_formula_semantics() -> None:
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

    day_fortune = _part_by_name(calculate_lots(positions, house_cusps, True), "Fortune")
    night_fortune = _part_by_name(calculate_lots(positions, house_cusps, False), "Fortune")
    travel = _part_by_name(calculate_lots(positions, house_cusps, True), "Travel")

    assert day_fortune.formula == "Asc + Moon - Sun"
    assert day_fortune.computation_truth is not None
    assert day_fortune.computation_truth.requested_add_key == "Moon"
    assert day_fortune.computation_truth.requested_sub_key == "Sun"
    assert day_fortune.computation_truth.projector_key == "Asc"
    assert day_fortune.computation_truth.projector_reference.key == "Asc"
    assert day_fortune.computation_truth.arc_policy is LotArcPolicy.DIRECTED
    assert day_fortune.computation_truth.effective_add_key == "Moon"
    assert day_fortune.computation_truth.effective_sub_key == "Sun"
    assert day_fortune.computation_truth.reversed_at_night is True
    assert day_fortune.computation_truth.reversed_for_chart is False
    assert day_fortune.computation_truth.add_reference.source_kind == "planet"
    assert day_fortune.computation_truth.sub_reference.source_kind == "planet"
    assert day_fortune.computation_truth.formula == day_fortune.formula

    assert night_fortune.formula == "Asc + Sun - Moon"
    assert night_fortune.computation_truth is not None
    assert night_fortune.computation_truth.requested_add_key == "Moon"
    assert night_fortune.computation_truth.requested_sub_key == "Sun"
    assert night_fortune.computation_truth.effective_add_key == "Sun"
    assert night_fortune.computation_truth.effective_sub_key == "Moon"
    assert night_fortune.computation_truth.reversed_for_chart is True
    assert night_fortune.computation_truth.add_reference.key == "Sun"
    assert night_fortune.computation_truth.sub_reference.key == "Moon"

    assert travel.formula == "Asc + H9 - Ruler H9"
    assert travel.computation_truth is not None
    assert travel.computation_truth.add_reference.source_kind == "house_cusp"
    assert travel.computation_truth.add_reference.detail == "house_9"
    assert travel.computation_truth.sub_reference.source_kind == "house_ruler"
    assert travel.computation_truth.sub_reference.detail == "H9->Jupiter"
    assert travel.classification is not None
    assert travel.classification.primary_category == "hellenistic"
    assert travel.classification.category_tags == ("hellenistic", "medieval")
    assert travel.classification.reversal is LotReversalKind.DIRECT
    assert travel.classification.add_reference.kind is LotReferenceKind.HOUSE_CUSP
    assert travel.classification.sub_reference.kind is LotReferenceKind.HOUSE_RULER


def test_lots_classification_is_deterministic_and_aligned_with_preserved_truth() -> None:
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

    first = {
        part.name: part
        for part in calculate_lots(
            positions,
            house_cusps,
            False,
            prenatal_new_moon=25.0,
        )
    }
    second = {
        part.name: part
        for part in calculate_lots(
            positions,
            house_cusps,
            False,
            prenatal_new_moon=25.0,
        )
    }

    for name in ("Fortune", "Travel", "Rain (Ibn Ezra)", "Royal Lot (al-Tabari)"):
        left = first[name]
        right = second[name]

        assert left.longitude == pytest.approx(right.longitude, abs=1e-12)
        assert left.formula == right.formula
        assert left.classification == right.classification
        assert left.computation_truth is not None
        assert left.classification is not None
        assert left.classification.category_tags == tuple(
            tag.strip() for tag in left.category.split(",") if tag.strip()
        )
        assert left.classification.add_reference.kind.value == left.computation_truth.add_reference.source_kind
        assert left.classification.sub_reference.kind.value == left.computation_truth.sub_reference.source_kind

    fortune = first["Fortune"]
    assert fortune.classification is not None
    assert fortune.classification.reversal is LotReversalKind.NIGHT_REVERSED
    assert fortune.classification.add_reference.kind is LotReferenceKind.PLANET
    assert fortune.classification.sub_reference.kind is LotReferenceKind.PLANET

    rain = first["Rain (Ibn Ezra)"]
    assert rain.classification is not None
    assert rain.classification.category_tags == ("medieval", "weather")
    assert rain.classification.primary_category == "medieval"
    assert rain.classification.add_reference.kind is LotReferenceKind.EXTERNAL
    assert rain.classification.sub_reference.kind is LotReferenceKind.PLANET


def test_lots_expose_read_only_inspectability_properties() -> None:
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

    fortune = _part_by_name(calculate_lots(positions, house_cusps, False), "Fortune")
    travel = _part_by_name(calculate_lots(positions, house_cusps, True), "Travel")

    assert fortune.category_tags == ("hellenistic", "medieval")
    assert fortune.primary_category == "hellenistic"
    assert fortune.reversal_kind is LotReversalKind.NIGHT_REVERSED
    assert fortune.is_reversed is True
    assert fortune.add_reference_kind is LotReferenceKind.PLANET
    assert fortune.sub_reference_kind is LotReferenceKind.PLANET

    assert travel.reversal_kind is LotReversalKind.DIRECT
    assert travel.is_reversed is False
    assert travel.add_reference_kind is LotReferenceKind.HOUSE_CUSP
    assert travel.sub_reference_kind is LotReferenceKind.HOUSE_RULER
    assert travel.classification is not None
    assert travel.category_tags == travel.classification.category_tags
    assert travel.primary_category == travel.classification.primary_category

    with pytest.raises(AttributeError):
        fortune.category_tags = ("modern",)  # type: ignore[misc]


def test_lots_default_policy_preserves_current_behavior() -> None:
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

    left = calculate_lots(positions, house_cusps, False, prenatal_new_moon=25.0)
    right = calculate_lots(
        positions,
        house_cusps,
        False,
        policy=LotsComputationPolicy(),
        prenatal_new_moon=25.0,
    )

    assert [(part.name, part.longitude, part.formula) for part in left[:40]] == [
        (part.name, part.longitude, part.formula) for part in right[:40]
    ]
    assert all(part.classification is not None for part in right[:20])
    assert LotsComputationPolicy().is_default is True


@pytest.mark.parametrize("missing_luminary", ["Sun", "Moon"])
def test_lots_do_not_fabricate_luminary_derived_references(
    missing_luminary: str,
) -> None:
    positions = {
        "Sun": 100.0,
        "Moon": 220.0,
        "Mercury": 80.0,
        "Venus": 10.0,
        "Mars": 35.0,
        "Jupiter": 250.0,
        "Saturn": 310.0,
    }
    positions.pop(missing_luminary)
    house_cusps = {i + 1: i * 30.0 for i in range(12)}

    names = {
        part.name
        for part in calculate_lots(positions, house_cusps, True)
    }

    assert "Fortune" not in names
    assert "Spirit" not in names
    assert "Basis (Firmicus)" not in names
    assert "Basis (Valens)" not in names
    assert "Eros (Valens)" not in names
    assert "Necessity (Persian)" not in names
    assert "Siblings (Number)" in names


def test_source_verified_dorothean_lots_reverse_at_night() -> None:
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

    day = {
        part.name: part
        for part in calculate_lots(positions, house_cusps, True)
    }
    night = {
        part.name: part
        for part in calculate_lots(positions, house_cusps, False)
    }

    assert day["Siblings (Number)"].longitude == pytest.approx(170.0)
    assert night["Siblings (Number)"].longitude == pytest.approx(190.0)
    assert day["Time of Children"].longitude == pytest.approx(215.0)
    assert night["Time of Children"].longitude == pytest.approx(145.0)
    assert night["Siblings (Number)"].computation_truth is not None
    assert night["Siblings (Number)"].computation_truth.reversed_for_chart is True
    assert night["Time of Children"].computation_truth is not None
    assert night["Time of Children"].computation_truth.reversed_for_chart is True


def test_valens_theft_uses_saturn_as_projector_and_reverses_at_night() -> None:
    """Valens, Anthologies II.24 (Riley annotated PDF p. 176)."""

    positions = {
        "Sun": 100.0,
        "Moon": 0.0,
        "Mercury": 20.0,
        "Venus": 40.0,
        "Mars": 80.0,
        "Jupiter": 140.0,
        "Saturn": 250.0,
    }
    house_cusps = {i + 1: i * 30.0 for i in range(12)}

    day = _part_by_name(
        calculate_lots(positions, house_cusps, True),
        "Theft (Valens)",
    )
    night = _part_by_name(
        calculate_lots(positions, house_cusps, False),
        "Theft (Valens)",
    )

    assert day.longitude == pytest.approx(310.0)
    assert day.formula == "Saturn + Mars - Mercury"
    assert day.computation_truth is not None
    assert day.computation_truth.projector_key == "Saturn"
    assert day.computation_truth.projector_reference.longitude == pytest.approx(250.0)
    assert day.computation_truth.arc_policy is LotArcPolicy.DIRECTED

    assert night.longitude == pytest.approx(190.0)
    assert night.formula == "Saturn + Mercury - Mars"
    assert night.computation_truth is not None
    assert night.computation_truth.reversed_for_chart is True


def test_valens_theft_missing_saturn_projector_fails_closed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import moira.lots as lots_module

    theft = next(
        definition
        for definition in PARTS_DEFINITIONS
        if definition.name == "Theft (Valens)"
    )
    monkeypatch.setattr(lots_module, "PARTS_DEFINITIONS", [theft])

    positions = {
        "Sun": 100.0,
        "Moon": 0.0,
        "Mercury": 20.0,
        "Mars": 80.0,
    }
    house_cusps = {i + 1: i * 30.0 for i in range(12)}

    assert calculate_lots(positions, house_cusps, True) == []
    with pytest.raises(ValueError, match="Unresolved lot ingredient reference: Saturn"):
        calculate_lots(
            positions,
            house_cusps,
            True,
            policy=LotsComputationPolicy(
                unresolved_reference_mode=LotsReferenceFailureMode.RAISE,
            ),
        )


def test_valens_basis_projects_the_shorter_fortune_spirit_interval() -> None:
    """Valens, Anthologies II.22 (Riley annotated PDF p. 171)."""

    positions = {
        "Sun": 100.0,
        "Moon": 0.0,
        "Mercury": 20.0,
        "Venus": 40.0,
        "Mars": 80.0,
        "Jupiter": 140.0,
        "Saturn": 250.0,
    }
    house_cusps = {i + 1: i * 30.0 for i in range(12)}

    day = _part_by_name(
        calculate_lots(positions, house_cusps, True),
        "Basis (Valens)",
    )
    night = _part_by_name(
        calculate_lots(positions, house_cusps, False),
        "Basis (Valens)",
    )

    assert day.longitude == pytest.approx(160.0)
    assert night.longitude == pytest.approx(160.0)
    assert day.formula == "Asc + shortest_arc(Spirit, Fortune)"
    assert night.formula == "Asc + shortest_arc(Fortune, Spirit)"
    assert day.computation_truth is not None
    assert day.computation_truth.arc_policy is LotArcPolicy.SHORTEST
    assert night.computation_truth is not None
    assert night.computation_truth.reversed_for_chart is True


def test_source_specific_debt_and_knowledge_entries_do_not_collapse_traditions() -> None:
    """Valens II.23 and al-Biruni section 476, rows 12 and 61."""

    definitions = {definition.name: definition for definition in PARTS_DEFINITIONS}

    assert "Debt" not in definitions
    assert "Debtor" not in definitions
    assert "Knowledge" not in definitions

    valens_debt = definitions["Debt (Valens)"]
    abu_mashar_debt = definitions["Debt (Abu Mashar via al-Biruni)"]
    knowledge = definitions["Knowledge, True or False (Abu Mashar via al-Biruni)"]

    assert (valens_debt.day_add, valens_debt.day_sub) == ("Saturn", "Mercury")
    assert valens_debt.reverse_at_night is False
    assert valens_debt.category == "hellenistic"
    assert (abu_mashar_debt.day_add, abu_mashar_debt.day_sub) == ("Mercury", "Saturn")
    assert abu_mashar_debt.reverse_at_night is True
    assert abu_mashar_debt.category == "medieval"
    assert (knowledge.day_add, knowledge.day_sub) == ("Moon", "Jupiter")
    assert knowledge.reverse_at_night is False
    assert knowledge.category == "medieval"


def test_lots_narrow_policy_explicitly_disables_selected_reference_doctrine() -> None:
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

    derived_policy = LotsComputationPolicy(
        derived=LotsDerivedReferencePolicy(include_eros_valens=False),
    )
    external_policy = LotsComputationPolicy(
        external=LotsExternalReferencePolicy(include_prenatal_new_moon=False),
    )

    derived_parts = calculate_lots(positions, house_cusps, True, policy=derived_policy)
    external_parts = calculate_lots(
        positions,
        house_cusps,
        False,
        policy=external_policy,
        prenatal_new_moon=25.0,
    )

    assert "Necessity (Persian)" not in {part.name for part in derived_parts}
    assert "Rain (Ibn Ezra)" not in {part.name for part in external_parts}
    assert _part_by_name(derived_parts, "Fortune").longitude == pytest.approx(
        (0.0 + 220.0 - 100.0) % 360.0,
        abs=1e-12,
    )


def test_lots_policy_surface_is_deterministic_and_validated() -> None:
    default = LotsComputationPolicy()
    custom = LotsComputationPolicy(
        unresolved_reference_mode=LotsReferenceFailureMode.RAISE,
        derived=LotsDerivedReferencePolicy(include_eros_valens=False),
        external=LotsExternalReferencePolicy(include_prenatal_new_moon=False),
    )

    assert default == LotsComputationPolicy()
    assert default != custom
    assert custom.is_default is False

    with pytest.raises(ValueError, match="Unsupported lots unresolved-reference mode"):
        calculate_lots(
            {"Sun": 100.0, "Moon": 220.0},
            {i + 1: i * 30.0 for i in range(12)},
            True,
            policy=LotsComputationPolicy(
                unresolved_reference_mode="invalid",  # type: ignore[arg-type]
            ),
        )

    with pytest.raises(ValueError, match="Unresolved lot ingredient reference:"):
        calculate_lots(
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
            False,
            policy=LotsComputationPolicy(
                unresolved_reference_mode=LotsReferenceFailureMode.RAISE,
            ),
        )


def test_lot_evaluation_preserves_computed_and_not_evaluable_catalogue_truth() -> None:
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

    evaluation = evaluate_lots(positions, house_cusps, False)

    assert evaluation.status is LotEvaluationStatus.PARTIAL
    assert evaluation.evaluated_count == len(evaluation.parts)
    assert evaluation.not_evaluable_count == len(evaluation.not_evaluable)
    assert evaluation.not_evaluable
    assert all(item.missing_references for item in evaluation.not_evaluable)
    assert calculate_lots(positions, house_cusps, False) == evaluation.parts

    theft = _part_by_name(evaluation.parts, "Theft (Valens)")
    assert isinstance(
        theft.dependency_completeness,
        LotDependencyCompletenessTruth,
    )
    assert theft.dependency_completeness.complete is True
    assert theft.dependencies[0].role is LotDependencyRole.PROJECTOR
    assert theft.dependencies[0].effective_key == "Saturn"
    assert (
        theft.astrological_condition_truth.status
        is LotEvaluationStatus.NOT_EVALUABLE
    )
    assert (
        theft.astrological_condition_truth.reason
        == "no_admitted_lot_condition_doctrine"
    )


def test_lot_dependency_layer_is_deterministic_and_aligned_with_part_truth() -> None:
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

    parts = {part.name: part for part in calculate_lots(positions, house_cusps, False, prenatal_new_moon=25.0)}
    first = calculate_lot_dependencies(positions, house_cusps, False, prenatal_new_moon=25.0)
    second = calculate_lot_dependencies(positions, house_cusps, False, prenatal_new_moon=25.0)

    assert first == second
    assert [(dep.part_name, dep.role.value, dep.effective_key) for dep in first[:20]] == sorted(
        (dep.part_name, dep.role.value, dep.effective_key) for dep in first[:20]
    )

    fortune = parts["Fortune"]
    assert len(fortune.dependencies) == 3
    assert [dep.role for dep in fortune.dependencies] == [
        LotDependencyRole.PROJECTOR,
        LotDependencyRole.ADD_OPERAND,
        LotDependencyRole.SUB_OPERAND,
    ]
    assert fortune.dependencies[0].effective_key == fortune.computation_truth.projector_key
    assert fortune.dependencies[1].effective_key == fortune.computation_truth.effective_add_key
    assert fortune.dependencies[2].effective_key == fortune.computation_truth.effective_sub_key
    assert fortune.dependency_completeness.complete is True
    assert fortune.astrological_condition_truth.status is LotEvaluationStatus.NOT_EVALUABLE

    rain = parts["Rain (Ibn Ezra)"]
    assert rain.dependencies[1].reference_kind is LotReferenceKind.EXTERNAL
    assert rain.dependencies[2].reference_kind is LotReferenceKind.PLANET


def test_lot_dependencies_make_inter_lot_relations_explicit() -> None:
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

    dependencies = calculate_lot_dependencies(positions, house_cusps, False, prenatal_new_moon=25.0)
    by_part = {}
    for dep in dependencies:
        by_part.setdefault(dep.part_name, []).append(dep)

    basis = by_part["Basis (Firmicus)"]
    assert {(dep.role, dep.effective_key, dep.reference_kind) for dep in basis} == {
        (LotDependencyRole.PROJECTOR, "Asc", LotReferenceKind.ANGLE),
        (LotDependencyRole.ADD_OPERAND, "Spirit", LotReferenceKind.DERIVED_LOT),
        (LotDependencyRole.SUB_OPERAND, "Fortune", LotReferenceKind.DERIVED_LOT),
    }
    assert all(
        dep.is_inter_lot
        for dep in basis
        if dep.role is not LotDependencyRole.PROJECTOR
    )

    necessity = by_part["Necessity (Persian)"]
    assert any(
        dep.effective_key == "Eros (Valens)"
        and dep.reference_kind is LotReferenceKind.DERIVED_LOT
        and dep.is_inter_lot
        for dep in necessity
    )


def test_lot_dependency_policy_governs_admissibility_without_changing_default_semantics() -> None:
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

    default_dependencies = calculate_lot_dependencies(positions, house_cusps, False, prenatal_new_moon=25.0)
    narrow_dependencies = calculate_lot_dependencies(
        positions,
        house_cusps,
        False,
        policy=LotsComputationPolicy(
            derived=LotsDerivedReferencePolicy(include_eros_valens=False),
        ),
        prenatal_new_moon=25.0,
    )

    assert len(default_dependencies) >= len(narrow_dependencies)
    assert any(dep.effective_key == "Eros (Valens)" for dep in default_dependencies)
    assert not any(dep.effective_key == "Eros (Valens)" for dep in narrow_dependencies)


def test_lot_dependency_layer_exposes_all_vs_admitted_dependencies_and_helpers() -> None:
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

    default_parts = {
        part.name: part
        for part in calculate_lots(
            positions,
            house_cusps,
            False,
            prenatal_new_moon=25.0,
        )
    }
    narrow_parts = {
        part.name: part
        for part in calculate_lots(
            positions,
            house_cusps,
            False,
            policy=LotsComputationPolicy(
                derived=LotsDerivedReferencePolicy(include_eros_valens=False),
            ),
            prenatal_new_moon=25.0,
        )
    }

    fortune = default_parts["Fortune"]
    assert fortune.all_dependency_count == 3
    assert fortune.dependency_count == 3
    assert fortune.inter_lot_dependencies == []
    assert fortune.external_dependencies == []

    basis = default_parts["Basis (Firmicus)"]
    assert basis.dependency_count == 3
    assert basis.all_dependency_count == 3
    assert len(basis.inter_lot_dependencies) == 2
    assert all(dep.is_inter_lot for dep in basis.inter_lot_dependencies)

    rain = default_parts["Rain (Ibn Ezra)"]
    assert len(rain.external_dependencies) == 1
    assert rain.external_dependencies[0].effective_key == "New Moon"

    assert all(dep in part.all_dependencies for part in default_parts.values() for dep in part.dependencies)

    assert "Necessity (Persian)" not in narrow_parts
    all_default_dependencies = calculate_all_lot_dependencies(
        positions,
        house_cusps,
        False,
        prenatal_new_moon=25.0,
    )
    admitted_default_dependencies = calculate_lot_dependencies(
        positions,
        house_cusps,
        False,
        prenatal_new_moon=25.0,
    )
    assert all_default_dependencies == admitted_default_dependencies


def test_lot_condition_profiles_are_deterministic_and_align_with_part_truth() -> None:
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

    parts = {
        part.name: part
        for part in calculate_lots(
            positions,
            house_cusps,
            False,
            prenatal_new_moon=25.0,
        )
    }
    first = {
        profile.part_name: profile
        for profile in calculate_lot_condition_profiles(
            positions,
            house_cusps,
            False,
            prenatal_new_moon=25.0,
        )
    }
    second = {
        profile.part_name: profile
        for profile in calculate_lot_condition_profiles(
            positions,
            house_cusps,
            False,
            prenatal_new_moon=25.0,
        )
    }

    assert first == second

    fortune = parts["Fortune"]
    fortune_profile = first["Fortune"]
    assert fortune.condition_profile == fortune_profile
    assert fortune_profile.part_name == fortune.name
    assert fortune_profile.category_tags == fortune.category_tags
    assert fortune_profile.primary_category == fortune.primary_category
    assert fortune_profile.reversal is fortune.reversal_kind
    assert fortune_profile.dependencies == fortune.dependencies
    assert fortune_profile.all_dependencies == fortune.all_dependencies
    assert fortune_profile.direct_dependency_count == 3
    assert fortune_profile.indirect_dependency_count == 0
    assert fortune_profile.state is LotConditionState.DIRECT
    assert fortune.condition_state is LotConditionState.DIRECT

    basis_profile = first["Basis (Firmicus)"]
    assert basis_profile.direct_dependency_count == 1
    assert basis_profile.indirect_dependency_count == 2
    assert basis_profile.inter_lot_dependency_count == 2
    assert basis_profile.state is LotConditionState.MIXED

    rain_profile = first["Rain (Ibn Ezra)"]
    assert rain_profile.direct_dependency_count == 2
    assert rain_profile.indirect_dependency_count == 1
    assert rain_profile.external_dependency_count == 1
    assert rain_profile.state is LotConditionState.MIXED


def test_lot_chart_condition_profile_is_deterministic_and_aligns_with_part_profiles() -> None:
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

    first = calculate_lot_chart_condition_profile(
        positions,
        house_cusps,
        False,
        prenatal_new_moon=25.0,
    )
    second = calculate_lot_chart_condition_profile(
        positions,
        house_cusps,
        False,
        prenatal_new_moon=25.0,
    )
    profiles = calculate_lot_condition_profiles(
        positions,
        house_cusps,
        False,
        prenatal_new_moon=25.0,
    )

    assert first == second
    assert [profile.part_name for profile in first.profiles] == [profile.part_name for profile in profiles]
    assert first.profile_count == len(profiles)
    assert first.direct_count == sum(1 for profile in profiles if profile.state is LotConditionState.DIRECT)
    assert first.mixed_count == sum(1 for profile in profiles if profile.state is LotConditionState.MIXED)
    assert first.indirect_count == sum(1 for profile in profiles if profile.state is LotConditionState.INDIRECT)
    assert first.direct_dependency_total == sum(profile.direct_dependency_count for profile in profiles)
    assert first.indirect_dependency_total == sum(profile.indirect_dependency_count for profile in profiles)
    assert first.inter_lot_dependency_total == sum(profile.inter_lot_dependency_count for profile in profiles)
    assert first.external_dependency_total == sum(profile.external_dependency_count for profile in profiles)
    assert first.strongest_count == len(first.strongest_parts)
    assert first.weakest_count == len(first.weakest_parts)


def test_lot_chart_condition_profile_strongest_and_weakest_are_derived_only() -> None:
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

    chart_profile = calculate_lot_chart_condition_profile(
        positions,
        house_cusps,
        False,
        prenatal_new_moon=25.0,
    )
    profiles = {profile.part_name: profile for profile in chart_profile.profiles}

    def strongest_key(profile: LotConditionProfile) -> tuple[int, int, int, str]:
        return (
            {
                LotConditionState.DIRECT: 0,
                LotConditionState.MIXED: 1,
                LotConditionState.INDIRECT: 2,
            }[profile.state],
            -profile.direct_dependency_count,
            profile.indirect_dependency_count,
            profile.part_name,
        )

    def weakest_key(profile: LotConditionProfile) -> tuple[int, int, int, str]:
        return (
            {
                LotConditionState.INDIRECT: 0,
                LotConditionState.MIXED: 1,
                LotConditionState.DIRECT: 2,
            }[profile.state],
            -profile.indirect_dependency_count,
            profile.direct_dependency_count,
            profile.part_name,
        )

    strongest_rank = min(strongest_key(profile) for profile in chart_profile.profiles)
    weakest_rank = min(weakest_key(profile) for profile in chart_profile.profiles)
    weakest_profile = min(chart_profile.profiles, key=weakest_key)

    assert chart_profile.strongest_parts == sorted(
        [profile.part_name for profile in chart_profile.profiles if strongest_key(profile) == strongest_rank]
    )
    assert chart_profile.weakest_parts == sorted(
        [
            profile.part_name
            for profile in chart_profile.profiles
            if (
                profile.state is weakest_profile.state
                and profile.indirect_dependency_count == weakest_profile.indirect_dependency_count
                and profile.direct_dependency_count == weakest_profile.direct_dependency_count
            )
        ]
    )
    assert all(profiles[name].state is LotConditionState.DIRECT for name in chart_profile.strongest_parts)
    assert all(
        profiles[name].state is weakest_profile.state
        for name in chart_profile.weakest_parts
    )

    with pytest.raises(ValueError, match="state counts must match profile states"):
        replace(chart_profile, direct_count=chart_profile.direct_count + 1)

    with pytest.raises(ValueError, match="profiles must be in deterministic order"):
        replace(chart_profile, profiles=list(reversed(chart_profile.profiles)))

    with pytest.raises(ValueError, match="strongest_parts must match derived ranking"):
        replace(chart_profile, strongest_parts=["Fortune"])


def test_lot_condition_network_profile_is_deterministic_and_aligns_with_part_truth() -> None:
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

    first = calculate_lot_condition_network_profile(
        positions,
        house_cusps,
        False,
        prenatal_new_moon=25.0,
    )
    second = calculate_lot_condition_network_profile(
        positions,
        house_cusps,
        False,
        prenatal_new_moon=25.0,
    )
    profiles = calculate_lot_condition_profiles(
        positions,
        house_cusps,
        False,
        prenatal_new_moon=25.0,
    )

    expected_edge_count = sum(
        1 for profile in profiles for dependency in profile.dependencies if dependency.is_inter_lot
    )

    assert first == second
    assert first.node_count == len(profiles)
    assert first.edge_count == expected_edge_count
    assert [node.part_name for node in first.nodes] == sorted(profile.part_name for profile in profiles)
    assert [node.condition_state for node in first.nodes] == [
        {profile.part_name: profile.state for profile in profiles}[node.part_name]
        for node in first.nodes
    ]


def test_lot_condition_network_represents_unilateral_links_and_absence_of_reciprocals_correctly() -> None:
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

    network = calculate_lot_condition_network_profile(
        positions,
        house_cusps,
        False,
        prenatal_new_moon=25.0,
    )
    edge_tuples = {
        (edge.source_part, edge.target_part, edge.role, edge.mode)
        for edge in network.edges
    }

    assert (
        "Basis (Firmicus)",
        "Spirit",
        LotDependencyRole.ADD_OPERAND,
        LotConditionNetworkEdgeMode.UNILATERAL,
    ) in edge_tuples
    assert (
        "Basis (Valens)",
        "Spirit",
        LotDependencyRole.SUB_OPERAND,
        LotConditionNetworkEdgeMode.UNILATERAL,
    ) in edge_tuples
    assert (
        "Necessity (Persian)",
        "Eros (Valens)",
        LotDependencyRole.ADD_OPERAND,
        LotConditionNetworkEdgeMode.UNILATERAL,
    ) in edge_tuples
    assert all(
        edge.mode is LotConditionNetworkEdgeMode.UNILATERAL
        for edge in network.edges
    )
    assert not any(
        edge.mode is LotConditionNetworkEdgeMode.RECIPROCAL
        for edge in network.edges
    )
    assert network.reciprocal_edge_count == 0
    assert network.unilateral_edge_count == len(network.edges)


def test_lot_condition_network_identifies_isolated_and_connected_parts() -> None:
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

    network = calculate_lot_condition_network_profile(
        positions,
        house_cusps,
        False,
        prenatal_new_moon=25.0,
    )
    nodes = {node.part_name: node for node in network.nodes}

    assert nodes["Fortune"].is_isolated is False
    assert nodes["Spirit"].is_isolated is False
    assert nodes["Basis (Firmicus)"].outgoing_count == 2
    assert nodes["Basis (Firmicus)"].incoming_count == 0
    assert nodes["Basis (Firmicus)"].reciprocal_count == 0
    assert nodes["Basis (Valens)"].reciprocal_count == 0
    assert nodes["Fortune"].incoming_count > nodes["Spirit"].incoming_count
    assert "Fortune" not in network.isolated_parts
    assert "Basis (Firmicus)" not in network.isolated_parts
    assert "Accomplishment" in network.isolated_parts
    assert network.most_connected_parts == ["Fortune"]

    with pytest.raises(ValueError, match="nodes must be in deterministic order"):
        replace(network, nodes=list(reversed(network.nodes)))

    with pytest.raises(ValueError, match="edges must be in deterministic order"):
        replace(network, edges=list(reversed(network.edges)))

    if network.edges:
        edge = network.edges[0]
        reverse_edge = LotConditionNetworkEdge(
            source_part=edge.target_part,
            target_part=edge.source_part,
            role=edge.role,
            mode=LotConditionNetworkEdgeMode.UNILATERAL,
        )
        with pytest.raises(ValueError, match="unilateral edges must not have a reverse edge"):
            replace(
                network,
                edges=sorted(
                    network.edges + [reverse_edge],
                    key=lambda item: (item.source_part, item.target_part, item.role.value),
                ),
                unilateral_edge_count=network.unilateral_edge_count + 1,
            )


def test_lots_fail_clearly_on_duplicate_or_non_finite_inputs() -> None:
    house_cusps = {i + 1: i * 30.0 for i in range(12)}

    with pytest.raises(ValueError, match="Duplicate lot planet entry after normalization: Sun"):
        calculate_lots(
            {"sun": 100.0, "Sun": 101.0},
            house_cusps,
            True,
        )

    with pytest.raises(ValueError, match="Lot longitude for Sun must be finite"):
        calculate_lots(
            {"Sun": float("nan"), "Moon": 220.0},
            house_cusps,
            True,
        )

    with pytest.raises(ValueError, match="Lot planet name must not be empty"):
        calculate_lots(
            {"   ": 100.0},
            house_cusps,
            True,
        )


def test_lots_fail_clearly_on_invalid_house_inputs() -> None:
    positions = {
        "Sun": 100.0,
        "Moon": 220.0,
        "Mercury": 80.0,
    }

    with pytest.raises(ValueError, match="Lot house_cusps list must contain exactly 12 entries"):
        calculate_lots(positions, [float(i) for i in range(11)], True)

    with pytest.raises(ValueError, match=r"Lot house cusps missing \[12\]"):
        calculate_lots(positions, {i + 1: i * 30.0 for i in range(11)}, True)

    with pytest.raises(ValueError, match="Lot house cusp number must be in the range 1..12: 13"):
        calculate_lots(
            positions,
            {**{i + 1: i * 30.0 for i in range(11)}, 13: 330.0},
            True,
        )

    with pytest.raises(ValueError, match="Lot house cusp 1 must be finite"):
        calculate_lots(
            positions,
            {1: float("inf"), **{i + 1: i * 30.0 for i in range(1, 12)}},
            True,
        )


def test_lots_policy_validation_fails_deterministically_on_unsupported_values() -> None:
    positions = {"Sun": 100.0, "Moon": 220.0}
    house_cusps = {i + 1: i * 30.0 for i in range(12)}

    bad_mode_policy = replace(
        LotsComputationPolicy(),
        unresolved_reference_mode="invalid",  # type: ignore[arg-type]
    )
    with pytest.raises(ValueError, match="Unsupported lots unresolved-reference mode"):
        calculate_lots(positions, house_cusps, True, policy=bad_mode_policy)

    bad_derived_policy = replace(
        LotsComputationPolicy(),
        derived="invalid",  # type: ignore[arg-type]
    )
    with pytest.raises(ValueError, match="Unsupported lots derived-reference policy"):
        calculate_lots(positions, house_cusps, True, policy=bad_derived_policy)

    bad_external_policy = replace(
        LotsComputationPolicy(),
        external="invalid",  # type: ignore[arg-type]
    )
    with pytest.raises(ValueError, match="Unsupported lots external-reference policy"):
        calculate_lots(positions, house_cusps, True, policy=bad_external_policy)

    bad_flag_policy = replace(
        LotsComputationPolicy(),
        derived=replace(LotsDerivedReferencePolicy(), include_fortune="yes"),  # type: ignore[arg-type]
    )
    with pytest.raises(ValueError, match="Lots derived-reference policy field include_fortune must be a bool"):
        calculate_lots(positions, house_cusps, True, policy=bad_flag_policy)


def test_lot_vessel_invariants_fail_loudly_on_internal_drift() -> None:
    add_truth = LotReferenceTruth("Moon", 220.0, "planet", "Moon")
    sub_truth = LotReferenceTruth("Sun", 100.0, "planet", "Sun")
    projector_truth = LotReferenceTruth("Asc", 0.0, "angle", "house_cusp_1")
    computation_truth = ArabicPartComputationTruth(
        asc_longitude=0.0,
        projector_key="Asc",
        projector_reference=projector_truth,
        arc_policy=LotArcPolicy.DIRECTED,
        requested_add_key="Moon",
        requested_sub_key="Sun",
        effective_add_key="Moon",
        effective_sub_key="Sun",
        reversed_at_night=True,
        reversed_for_chart=False,
        add_reference=add_truth,
        sub_reference=sub_truth,
        formula="Asc + Moon - Sun",
    )
    classification = ArabicPartClassification(
        primary_category="hellenistic",
        category_tags=("hellenistic", "medieval"),
        reversal=LotReversalKind.NIGHT_REVERSIBLE,
        projector_reference=LotReferenceClassification(
            LotReferenceKind.ANGLE, "Asc", "house_cusp_1"
        ),
        add_reference=LotReferenceClassification(LotReferenceKind.PLANET, "Moon", "Moon"),
        sub_reference=LotReferenceClassification(LotReferenceKind.PLANET, "Sun", "Sun"),
    )

    with pytest.raises(ValueError, match="longitude must be in \\[0, 360\\)"):
        ArabicPart(
            name="Fortune",
            longitude=360.0,
            formula="Asc + Moon - Sun",
            category="hellenistic,medieval",
        )

    with pytest.raises(ValueError, match="formula must match projector, arc policy"):
        ArabicPartComputationTruth(
            asc_longitude=0.0,
            projector_key="Asc",
            projector_reference=projector_truth,
            arc_policy=LotArcPolicy.DIRECTED,
            requested_add_key="Moon",
            requested_sub_key="Sun",
            effective_add_key="Moon",
            effective_sub_key="Sun",
            reversed_at_night=False,
            reversed_for_chart=False,
            add_reference=add_truth,
            sub_reference=sub_truth,
            formula="Asc + Sun - Moon",
        )

    with pytest.raises(ValueError, match="primary_category must be included in category_tags"):
        ArabicPartClassification(
            primary_category="modern",
            category_tags=("hellenistic", "medieval"),
            reversal=LotReversalKind.DIRECT,
            projector_reference=LotReferenceClassification(
                LotReferenceKind.ANGLE, "Asc"
            ),
            add_reference=LotReferenceClassification(LotReferenceKind.PLANET, "Moon"),
            sub_reference=LotReferenceClassification(LotReferenceKind.PLANET, "Sun"),
        )

    with pytest.raises(ValueError, match="classification reversal must match computation truth"):
        ArabicPart(
            name="Fortune",
            longitude=120.0,
            formula="Asc + Moon - Sun",
            category="hellenistic,medieval",
            computation_truth=computation_truth,
            classification=replace(classification, reversal=LotReversalKind.DIRECT),
        )

    with pytest.raises(ValueError, match="add-reference classification must match computation truth"):
        ArabicPart(
            name="Fortune",
            longitude=120.0,
            formula="Asc + Moon - Sun",
            category="hellenistic,medieval",
            computation_truth=computation_truth,
            classification=replace(
                classification,
                add_reference=LotReferenceClassification(LotReferenceKind.EXTERNAL, "Moon"),
            ),
        )

    with pytest.raises(
        ValueError,
        match="dependencies must be empty or contain projector, add, and sub relations",
    ):
        ArabicPart(
            name="Fortune",
            longitude=120.0,
            formula="Asc + Moon - Sun",
            category="hellenistic,medieval",
            computation_truth=computation_truth,
            classification=classification,
            dependencies=[
                LotDependency(
                    part_name="Fortune",
                    role=LotDependencyRole.ADD_OPERAND,
                    requested_key="Moon",
                    effective_key="Moon",
                    reference_kind=LotReferenceKind.PLANET,
                    reference_longitude=220.0,
                ),
            ],
        )

    with pytest.raises(ValueError, match="dependencies must be a subset of all_dependencies"):
        ArabicPart(
            name="Fortune",
            longitude=120.0,
            formula="Asc + Moon - Sun",
            category="hellenistic,medieval",
            computation_truth=computation_truth,
            classification=classification,
            all_dependencies=[
                LotDependency(
                    part_name="Fortune",
                    role=LotDependencyRole.PROJECTOR,
                    requested_key="Asc",
                    effective_key="Asc",
                    reference_kind=LotReferenceKind.ANGLE,
                    reference_longitude=0.0,
                ),
                LotDependency(
                    part_name="Fortune",
                    role=LotDependencyRole.ADD_OPERAND,
                    requested_key="Moon",
                    effective_key="Moon",
                    reference_kind=LotReferenceKind.PLANET,
                    reference_longitude=220.0,
                ),
                LotDependency(
                    part_name="Fortune",
                    role=LotDependencyRole.SUB_OPERAND,
                    requested_key="Sun",
                    effective_key="Sun",
                    reference_kind=LotReferenceKind.EXTERNAL,
                    reference_longitude=100.0,
                ),
            ],
            dependencies=[
                LotDependency(
                    part_name="Fortune",
                    role=LotDependencyRole.PROJECTOR,
                    requested_key="Asc",
                    effective_key="Asc",
                    reference_kind=LotReferenceKind.ANGLE,
                    reference_longitude=0.0,
                ),
                LotDependency(
                    part_name="Fortune",
                    role=LotDependencyRole.ADD_OPERAND,
                    requested_key="Moon",
                    effective_key="Moon",
                    reference_kind=LotReferenceKind.PLANET,
                    reference_longitude=220.0,
                ),
                LotDependency(
                    part_name="Fortune",
                    role=LotDependencyRole.SUB_OPERAND,
                    requested_key="Sun",
                    effective_key="Sun",
                    reference_kind=LotReferenceKind.PLANET,
                    reference_longitude=100.0,
                ),
            ],
        )

    with pytest.raises(ValueError, match="condition_profile state must match|state must match derived dependency polarity"):
        bad_profile = replace(
            LotConditionProfile(
                part_name="Fortune",
                category_tags=("hellenistic", "medieval"),
                primary_category="hellenistic",
                reversal=LotReversalKind.NIGHT_REVERSIBLE,
                all_dependencies=[
                    LotDependency(
                        part_name="Fortune",
                        role=LotDependencyRole.PROJECTOR,
                        requested_key="Asc",
                        effective_key="Asc",
                        reference_kind=LotReferenceKind.ANGLE,
                        reference_longitude=0.0,
                    ),
                    LotDependency(
                        part_name="Fortune",
                        role=LotDependencyRole.ADD_OPERAND,
                        requested_key="Moon",
                        effective_key="Moon",
                        reference_kind=LotReferenceKind.PLANET,
                        reference_longitude=220.0,
                    ),
                    LotDependency(
                        part_name="Fortune",
                        role=LotDependencyRole.SUB_OPERAND,
                        requested_key="Sun",
                        effective_key="Sun",
                        reference_kind=LotReferenceKind.PLANET,
                        reference_longitude=100.0,
                    ),
                ],
                dependencies=[
                    LotDependency(
                        part_name="Fortune",
                        role=LotDependencyRole.PROJECTOR,
                        requested_key="Asc",
                        effective_key="Asc",
                        reference_kind=LotReferenceKind.ANGLE,
                        reference_longitude=0.0,
                    ),
                    LotDependency(
                        part_name="Fortune",
                        role=LotDependencyRole.ADD_OPERAND,
                        requested_key="Moon",
                        effective_key="Moon",
                        reference_kind=LotReferenceKind.PLANET,
                        reference_longitude=220.0,
                    ),
                    LotDependency(
                        part_name="Fortune",
                        role=LotDependencyRole.SUB_OPERAND,
                        requested_key="Sun",
                        effective_key="Sun",
                        reference_kind=LotReferenceKind.PLANET,
                        reference_longitude=100.0,
                    ),
                ],
                direct_dependency_count=3,
                indirect_dependency_count=0,
                inter_lot_dependency_count=0,
                external_dependency_count=0,
                state=LotConditionState.DIRECT,
            ),
            state=LotConditionState.MIXED,
        )
        ArabicPart(
            name="Fortune",
            longitude=120.0,
            formula="Asc + Moon - Sun",
            category="hellenistic,medieval",
            computation_truth=computation_truth,
            classification=classification,
            all_dependencies=bad_profile.all_dependencies,
            dependencies=bad_profile.dependencies,
            condition_profile=bad_profile,
        )


def test_lots_reference_builder_resolves_rulers_fixed_degrees_and_optional_inputs() -> None:
    service = ArabicPartsService()
    refs, ref_truths = service._build_refs(
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
        policy=LotsComputationPolicy(),
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
    assert ref_truths["Asc"].source_kind == "angle"
    assert ref_truths["H1"].source_kind == "house_cusp"
    assert ref_truths["18 Aries"].source_kind == "fixed_degree"
    assert ref_truths["Ruler H1"].source_kind == "house_ruler"
    assert ref_truths["Ruler H1"].detail == "H1->Mars"
    assert ref_truths["Ruler MC"].source_kind == "angle_ruler_alias"
    assert ref_truths["Ruler Sun"].source_kind == "planet_ruler"
    assert ref_truths["Ruler Syzygy"].source_kind == "syzygy_ruler"
    assert ref_truths["Fortune"].source_kind == "derived_lot"
    assert ref_truths["New Moon"].source_kind == "external"


@pytest.mark.requires_ephemeris
def test_moira_wrappers_for_dignities_and_lots_match_module_level_calculations(
    moira_engine: Moira,
    natal_chart,
    natal_houses,
) -> None:
    lons = natal_chart.longitudes(include_nodes=True)
    cusps_map = {i + 1: c for i, c in enumerate(natal_houses.cusps)}
    day = sect_light(lons["Sun"], natal_houses.asc) == "Sun"

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
