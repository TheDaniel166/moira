"""Identity and delegation gates for the additive physical visibility API."""

from __future__ import annotations

import inspect

import pytest

import moira
import moira.facade as facade
import moira.heliacal as heliacal
import moira.sky.visibility as sky_visibility


_PHYSICAL_PUBLIC_NAMES = (
    "PhysicalVisibilityStatus",
    "PhysicalVisibilityEvidenceState",
    "PhysicalVisibilityPhase",
    "PhysicalVisibilityCrossingDirection",
    "PhysicalVisibilityBoundarySource",
    "PhysicalEventTimeSemantics",
    "PhysicalBackgroundScope",
    "PhysicalBackgroundComponentKind",
    "PhysicalAtmosphereInput",
    "PhysicalDirectionalBackground",
    "PhysicalModeledBackgroundComponent",
    "PhysicalSqmBackground",
    "PhysicalBortleBackground",
    "PhysicalHorizonSample",
    "PhysicalHorizonProfile",
    "PhysicalVisibilityPolicy",
    "VisibilityComponentReceipt",
    "PhysicalAtmosphereReceipt",
    "PhysicalValidityDomainReceipt",
    "PhysicalObserverProtocolReceipt",
    "PhysicalBackgroundReceipt",
    "PhysicalTargetReceipt",
    "PhysicalThresholdReceipt",
    "PhysicalVisibilityErrorBudgetReceipt",
    "PhysicalVisibilityAssessment",
    "PhysicalVisibilitySearchPolicy",
    "PhysicalObservationWindowReceipt",
    "PhysicalEventSolverReceipt",
    "PhysicalEventSensitivityReceipt",
    "PhysicalHorizonReceipt",
    "PhysicalEphemerisReceipt",
    "PhysicalVisibilityEventResult",
    "VisibilityDataPackConfig",
    "VisibilityDataPackReceipt",
    "physical_visibility_assessment",
    "physical_visibility_event",
)


@pytest.mark.parametrize("name", _PHYSICAL_PUBLIC_NAMES)
def test_physical_visibility_public_exports_preserve_identity(name: str) -> None:
    expected = getattr(heliacal, name)
    for surface in (moira, facade, sky_visibility):
        assert name in surface.__all__
        assert getattr(surface, name) is expected


def test_moira_physical_assessment_forwards_complete_objects(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    engine = object.__new__(facade.Moira)
    engine._reader_obj = None
    data_pack_config = object()
    policy = object()
    sentinel = object()
    calls: list[tuple[object, ...]] = []

    def physical_assessment(
        body,
        jd_ut,
        lat,
        lon,
        *,
        data_pack_config,
        policy,
    ):
        calls.append((body, jd_ut, lat, lon, data_pack_config, policy))
        return sentinel

    monkeypatch.setattr(
        facade,
        "physical_visibility_assessment",
        physical_assessment,
    )

    result = engine.physical_visibility_assessment(
        "Mars",
        2451545.0,
        12.5,
        -45.0,
        data_pack_config=data_pack_config,
        policy=policy,
    )

    assert result is sentinel
    assert calls == [
        ("Mars", 2451545.0, 12.5, -45.0, data_pack_config, policy)
    ]


def test_moira_physical_event_forwards_complete_objects(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    engine = object.__new__(facade.Moira)
    engine._reader_obj = None
    phase = object()
    data_pack_config = object()
    policy = object()
    search_policy = object()
    sentinel = object()
    calls: list[tuple[object, ...]] = []

    def physical_event(
        body,
        phase,
        jd_start,
        lat,
        lon,
        *,
        data_pack_config,
        policy,
        search_policy,
    ):
        calls.append(
            (
                body,
                phase,
                jd_start,
                lat,
                lon,
                data_pack_config,
                policy,
                search_policy,
            )
        )
        return sentinel

    monkeypatch.setattr(facade, "physical_visibility_event", physical_event)

    result = engine.physical_visibility_event(
        "Mars",
        phase,
        2451545.0,
        12.5,
        -45.0,
        data_pack_config=data_pack_config,
        policy=policy,
        search_policy=search_policy,
    )

    assert result is sentinel
    assert calls == [
        (
            "Mars",
            phase,
            2451545.0,
            12.5,
            -45.0,
            data_pack_config,
            policy,
            search_policy,
        )
    ]


def test_moira_physical_methods_keep_pack_and_policy_keyword_only() -> None:
    assessment = inspect.signature(
        facade.Moira.physical_visibility_assessment
    ).parameters
    event = inspect.signature(facade.Moira.physical_visibility_event).parameters

    for parameters in (assessment, event):
        assert parameters["data_pack_config"].kind is inspect.Parameter.KEYWORD_ONLY
        assert parameters["data_pack_config"].default is inspect.Parameter.empty
        assert parameters["policy"].kind is inspect.Parameter.KEYWORD_ONLY
    assert event["search_policy"].kind is inspect.Parameter.KEYWORD_ONLY
