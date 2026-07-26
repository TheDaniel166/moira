"""Adversarial parity guards for the Phase 4 Hellenistic contract gate."""

from __future__ import annotations

from datetime import datetime, timezone
from types import SimpleNamespace

import moira
import moira.aspects as aspects
import moira.classical as classical
import moira.dignities as dignities
import moira.facade as facade
import moira.hermetic_decans as hermetic_decans
import moira.lots as lots
import moira.profections as profections
import moira.timelords as timelords
import moira_server.models as server_models
import moira_server.models.decans as decan_models
import moira_server.models.dignities as dignity_models
import moira_server.models.hellenistic_aspects as aspect_models
import moira_server.models.lots as lot_models
import moira_server.models.timelords as timelord_models
import moira_server.routers.decans as decan_routers
import moira_server.serializers as server_serializers
import moira_server.serializers.decans as decan_serializers
import moira_server.serializers.lots as lot_serializers
import moira_server.services as server_services
import moira_server.services.decans as decan_services
import moira_server.services.lots as lot_services


_PHASE_3_EXPORTS = {
    aspects: (
        "AspectDirection",
        "HellenisticAspectEvaluationStatus",
        "HellenisticOvercomingRelation",
        "HellenisticDirectionTruth",
        "HellenisticOvercomingTruth",
        "HellenisticSuperiorityTruth",
        "find_whole_sign_aspects",
        "hellenistic_superiority_truth",
        "overcoming",
    ),
    dignities: (
        "TruthEvaluationStatus",
        "HorizonHemisphere",
        "HorizonComputationMethod",
        "SectComponentKind",
        "PlanetarySolarPhaseKind",
        "SolarProximityBand",
        "DignityHorizonFrame",
        "EssentialDignityComponentTruth",
        "PlanetarySolarPhaseTruth",
        "SolarProximityTruth",
        "BesiegingDependencyCompletenessTruth",
        "BesiegingTruth",
        "MercuryPhaseTruth",
        "HorizonTruth",
        "SectComponentTruth",
        "solar_proximity_truth",
        "planetary_solar_phase_truth",
        "besieging_truth",
    ),
    lots: (
        "LotArcPolicy",
        "LotEvaluationStatus",
        "LotDependencyCompletenessTruth",
        "LotAstrologicalConditionTruth",
        "LotNotEvaluable",
        "LotsEvaluation",
        "PartDefinition",
        "evaluate_lots",
    ),
    profections: (
        "ProfectionActivationStatus",
        "ProfectionActivationBodyTruth",
        "ProfectionActivationTruth",
        "profection_activation_truth",
    ),
    timelords: (
        "TimelordEvaluationStatus",
        "DecennialSequenceBodyTruth",
        "DecennialSequenceAssemblyTruth",
        "ZRFortuneAngularityTruth",
        "decennial_sequence_truth",
        "zr_fortune_angularity_truth",
    ),
}


def test_phase_3_exports_are_identical_across_curated_engine_surfaces() -> None:
    surfaces = (moira, classical, facade)

    for owner, names in _PHASE_3_EXPORTS.items():
        for name in names:
            direct = getattr(owner, name)
            assert all(getattr(surface, name) is direct for surface in surfaces)
            assert all(name in surface.__all__ for surface in surfaces)


def test_moira_aspects_forwards_the_complete_policy_surface(monkeypatch) -> None:
    seen: dict[str, object] = {}
    sentinel = object()
    policy = object()
    chart = SimpleNamespace(
        longitudes=lambda: {"Mars": 5.0, "Saturn": 95.0},
        speeds=lambda: {"Mars": 0.5, "Saturn": -0.1},
    )

    def fake_find_aspects(*args, **kwargs):
        seen["args"] = args
        seen["kwargs"] = kwargs
        return sentinel

    monkeypatch.setattr(facade, "find_aspects", fake_find_aspects)

    result = facade.Moira().aspects(
        chart,
        orbs={90.0: 3.0},
        include_minor=False,
        tier=2,
        orb_factor=0.75,
        policy=policy,
    )

    assert result is sentinel
    assert seen["args"] == ({"Mars": 5.0, "Saturn": 95.0},)
    assert seen["kwargs"] == {
        "orbs": {90.0: 3.0},
        "include_minor": False,
        "speeds": {"Mars": 0.5, "Saturn": -0.1},
        "tier": 2,
        "orb_factor": 0.75,
        "policy": policy,
    }


def test_moira_profection_forwards_activation_orb(monkeypatch) -> None:
    seen: dict[str, object] = {}
    sentinel = object()
    natal_dt = datetime(2000, 1, 1, tzinfo=timezone.utc)
    current_dt = datetime(2024, 1, 1, tzinfo=timezone.utc)
    positions = {"Sun": 0.4}

    def fake_schedule(*args, **kwargs):
        seen["args"] = args
        seen["kwargs"] = kwargs
        return sentinel

    monkeypatch.setattr(facade, "profection_schedule", fake_schedule)

    result = facade.Moira().profection(
        0.0,
        natal_dt,
        current_dt,
        positions,
        leap_day_policy=profections.LeapDayAnniversaryPolicy.FEBRUARY_28,
        activation_orb=0.25,
    )

    assert result is sentinel
    assert seen["args"] == (0.0, natal_dt, current_dt, positions)
    assert seen["kwargs"] == {
        "leap_day_policy": profections.LeapDayAnniversaryPolicy.FEBRUARY_28,
        "activation_orb": 0.25,
    }


def test_moira_evaluate_lots_preserves_full_policy_and_optional_inputs(
    monkeypatch,
) -> None:
    seen: dict[str, object] = {}
    sentinel = object()
    policy = object()
    chart = SimpleNamespace(
        longitudes=lambda *, include_nodes: {
            "Sun": 15.0,
            "Moon": 44.0,
            "North Node": 123.0,
        }
    )
    houses = SimpleNamespace(
        asc=100.0,
        mc=10.0,
        cusps=tuple(float(index * 30) for index in range(12)),
    )

    def fake_evaluate_lots(*args, **kwargs):
        seen["args"] = args
        seen["kwargs"] = kwargs
        return sentinel

    monkeypatch.setattr(facade, "evaluate_lots", fake_evaluate_lots)
    monkeypatch.setattr(facade, "is_day_chart", lambda sun, asc: True)

    result = facade.Moira().evaluate_lots(
        chart,
        houses,
        policy=policy,
        syzygy=22.0,
        prenatal_new_moon=33.0,
        prenatal_full_moon=44.0,
        lord_of_hour=55.0,
    )

    assert result is sentinel
    assert seen["args"] == (
        {"Sun": 15.0, "Moon": 44.0, "North Node": 123.0},
        {index + 1: float(index * 30) for index in range(12)},
        True,
    )
    assert seen["kwargs"] == {
        "policy": policy,
        "asc_longitude": 100.0,
        "mc_longitude": 10.0,
        "syzygy": 22.0,
        "prenatal_new_moon": 33.0,
        "prenatal_full_moon": 44.0,
        "lord_of_hour": 55.0,
    }


def test_moira_raw_truth_helpers_match_their_owning_modules() -> None:
    engine = facade.Moira()
    positions = {
        "Sun": 10.0,
        "Moon": 45.0,
        "Mercury": 80.0,
        "Venus": 120.0,
        "Mars": 160.0,
        "Jupiter": 220.0,
        "Saturn": 300.0,
    }

    assert engine.solar_proximity_truth(
        "Mars", 18.0, 10.0
    ) == dignities.solar_proximity_truth("Mars", 18.0, 10.0)
    assert engine.planetary_solar_phase_truth(
        "Mars", 160.0, 10.0
    ) == dignities.planetary_solar_phase_truth("Mars", 160.0, 10.0)
    assert engine.besieging_truth(
        160.0, positions, planet_name="Mars", orb=20.0
    ) == dignities.besieging_truth(
        160.0, positions, planet_name="Mars", orb=20.0
    )
    assert engine.profection_activation_truth(
        0.0, {"Sun": 0.25}, 0.5
    ) == profections.profection_activation_truth(
        0.0, {"Sun": 0.25}, 0.5
    )
    assert engine.decennial_sequence_truth(
        positions, True
    ) == timelords.decennial_sequence_truth(positions, True)
    assert engine.zr_fortune_angularity_truth(
        "Aries", None
    ) == timelords.zr_fortune_angularity_truth("Aries", None)
    assert engine.hellenistic_superiority_truth(
        5.0, 95.0, body1="Mars", body2="Saturn"
    ) == aspects.hellenistic_superiority_truth(
        5.0, 95.0, body1="Mars", body2="Saturn"
    )


def test_server_package_aggregators_preserve_typed_contract_identity() -> None:
    model_groups = {
        dignity_models: (
            "EssentialDignityTruthResponse",
            "PlanetarySolarPhaseTruthResponse",
            "SolarProximityTruthResponse",
            "BesiegingTruthResponse",
            "AccidentalDignityTruthResponse",
            "SectTruthResponse",
        ),
        aspect_models: (
            "HellenisticDirectionTruthResponse",
            "HellenisticOvercomingTruthResponse",
            "HellenisticSuperiorityTruthResponse",
            "WholeSignAspectResponse",
            "OvercomingResponse",
        ),
        lot_models: (
            "ArabicPartComputationTruthResponse",
            "LotDependencyCompletenessTruthResponse",
            "LotAstrologicalConditionTruthResponse",
            "LotNotEvaluableResponse",
            "LotsResultResponse",
        ),
        timelord_models: (
            "ProfectionActivationTruthResponse",
            "DecennialSequenceAssemblyTruthResponse",
            "ZRFortuneAngularityTruthResponse",
        ),
    }
    for owner, names in model_groups.items():
        for name in names:
            assert getattr(server_models, name) is getattr(owner, name)
            assert name in server_models.__all__

    serializer_names = (
        "serialize_arabic_part_computation_truth",
        "serialize_lot_dependency_completeness",
        "serialize_lot_astrological_condition_truth",
        "serialize_lot_not_evaluable",
        "serialize_lots_result",
    )
    for name in serializer_names:
        assert getattr(server_serializers, name) is getattr(lot_serializers, name)
        assert name in server_serializers.__all__

    assert (
        server_services.compute_lots_chart_evaluation
        is lot_services.compute_lots_chart_evaluation
    )
    assert "compute_lots_chart_evaluation" in server_services.__all__


def test_phase_4_keeps_unadmitted_hermetic_geometry_contained() -> None:
    quarantined = {
        "decan_at",
        "decan_for_longitude",
        "rising_decan",
    }
    for surface in (moira, classical, facade):
        assert quarantined.isdisjoint(surface.__all__)
        assert all(not hasattr(surface, name) for name in quarantined)


def test_unsupported_hermetic_transport_and_night_hours_are_removed() -> None:
    removed_by_owner = {
        hermetic_decans: ("DecanHour", "DecanHoursNight", "decan_hours"),
        decan_models: (
            "HermeticDecanCatalogResponse",
            "HermeticDecanEntryResponse",
            "HermeticDecanHourResponse",
            "HermeticDecanLookupResponse",
            "HermeticDecanNightHoursResponse",
            "HermeticLocationRequest",
            "HermeticLongitudeRequest",
        ),
        decan_services: (
            "compute_hermetic_decan_longitude",
            "compute_hermetic_decan_night_hours",
            "compute_hermetic_rising_decan",
            "list_hermetic_decan_catalog",
        ),
        decan_serializers: (
            "serialize_hermetic_decan_catalog",
            "serialize_hermetic_decan_lookup",
            "serialize_hermetic_decan_night_hours",
        ),
        decan_routers: (
            "hermetic_decans_router",
            "hermetic_decan_catalog_route",
            "hermetic_decan_longitude_route",
            "hermetic_rising_decan_route",
        ),
        server_models: (
            "HermeticDecanCatalogResponse",
            "HermeticDecanEntryResponse",
            "HermeticDecanHourResponse",
            "HermeticDecanLookupResponse",
            "HermeticDecanNightHoursResponse",
            "HermeticLocationRequest",
            "HermeticLongitudeRequest",
        ),
        server_services: (
            "compute_hermetic_decan_longitude",
            "compute_hermetic_decan_night_hours",
            "compute_hermetic_rising_decan",
            "list_hermetic_decan_catalog",
        ),
        server_serializers: (
            "serialize_hermetic_decan_catalog",
            "serialize_hermetic_decan_lookup",
            "serialize_hermetic_decan_night_hours",
        ),
    }
    for owner, names in removed_by_owner.items():
        assert all(not hasattr(owner, name) for name in names)
        exported = getattr(owner, "__all__", ())
        assert set(names).isdisjoint(exported)
