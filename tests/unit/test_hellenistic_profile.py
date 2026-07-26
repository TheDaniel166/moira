"""Phase 5 unified Hellenistic profile contract and hardening tests."""

from __future__ import annotations

from dataclasses import asdict
from datetime import datetime, timezone
from types import SimpleNamespace

import pytest

import moira
import moira.classical as classical
import moira.facade as facade
from moira.constants import HouseSystem
from moira.dignities import (
    DignityComputationPolicy,
    EssentialDignityDoctrine,
    EssentialDignityPolicy,
)
from moira.hellenistic import (
    HELLENISTIC_CLASSICAL_PLANETS,
    HELLENISTIC_PROFILE_LOTS,
    HellenisticProfileExclusion,
    HellenisticProfilePolicy,
    HellenisticProfileStatus,
    hellenistic_chart_profile,
)
from moira.lots import (
    LotsComputationPolicy,
    LotsReferenceFailureMode,
    evaluate_lots,
)
from moira.profections import profection_schedule
from moira.timelords import DecennialPolicy, ZRYearPolicy


NATAL_DT = datetime(2000, 1, 1, tzinfo=timezone.utc)
CURRENT_DT = datetime(2024, 6, 1, tzinfo=timezone.utc)
POSITIONS = {
    "Sun": 10.0,
    "Moon": 45.0,
    "Mercury": 80.0,
    "Venus": 125.0,
    "Mars": 170.0,
    "Jupiter": 230.0,
    "Saturn": 300.0,
}
SPEEDS = {
    "Sun": 1.0,
    "Moon": 13.0,
    "Mercury": 1.2,
    "Venus": 1.0,
    "Mars": 0.5,
    "Jupiter": -0.1,
    "Saturn": 0.05,
}
WHOLE_SIGN_CUSPS = {
    number: (number - 1) * 30.0
    for number in range(1, 13)
}


def _profile(**overrides):
    inputs = {
        "natal_positions": POSITIONS,
        "natal_speeds": SPEEDS,
        "house_cusps": WHOLE_SIGN_CUSPS,
        "asc_longitude": 15.0,
        "mc_longitude": 280.0,
        "natal_dt": NATAL_DT,
        "current_dt": CURRENT_DT,
    }
    inputs.update(overrides)
    return hellenistic_chart_profile(**inputs)


def _score_paths(value, path: str = "") -> list[str]:
    found: list[str] = []
    if isinstance(value, dict):
        for key, item in value.items():
            child = f"{path}.{key}" if path else key
            if "score" in key.lower():
                found.append(child)
            found.extend(_score_paths(item, child))
    elif isinstance(value, (list, tuple)):
        for index, item in enumerate(value):
            found.extend(_score_paths(item, f"{path}[{index}]"))
    return found


def test_profile_is_score_free_and_identity_exported_across_public_surfaces() -> None:
    profile = _profile()
    names = set(moira.hellenistic.__all__)

    assert not _score_paths(asdict(profile))
    assert profile.included_components
    assert set(profile.excluded_components) == set(HellenisticProfileExclusion)
    assert {
        "HellenisticChartProfile",
        "HellenisticProfilePolicy",
        "hellenistic_chart_profile",
    } <= names
    for name in names:
        assert name in moira.__all__
        assert name in classical.__all__
        assert name in facade.__all__
        direct = getattr(moira.hellenistic, name)
        assert getattr(moira, name) is direct
        assert getattr(classical, name) is direct
        assert getattr(facade, name) is direct


def test_profile_preserves_atomic_receipts_and_exact_angle_lots() -> None:
    profile = _profile()
    lots = {lot.name: lot for lot in profile.lots}

    assert tuple(lots) == HELLENISTIC_PROFILE_LOTS
    assert lots["Fortune"].longitude == pytest.approx(50.0)
    assert lots["Spirit"].longitude == pytest.approx(340.0)
    assert lots["Eros (Valens)"].longitude == pytest.approx(305.0)
    assert lots["Necessity (Valens)"].longitude == pytest.approx(85.0)
    assert (
        lots["Fortune"].computation_truth.projector_reference.longitude
        == pytest.approx(15.0)
    )
    assert (
        lots["Fortune"].computation_truth.projector_reference.detail
        == "explicit_ascendant"
    )
    assert profile.profection == profection_schedule(
        15.0,
        NATAL_DT,
        CURRENT_DT,
        POSITIONS,
        activation_orb=5.0,
    )
    assert tuple(planet.planet for planet in profile.planets) == (
        HELLENISTIC_CLASSICAL_PLANETS
    )
    assert all(
        planet.sect_truth.is_day_chart == profile.is_day_chart
        for planet in profile.planets
    )
    assert profile.decennials.status is HellenisticProfileStatus.EVALUATED
    assert len(profile.decennials.active_periods) == 2
    assert (
        profile.zodiacal_releasing.status
        is HellenisticProfileStatus.EVALUATED
    )
    assert len(profile.zodiacal_releasing.active_periods) == 2

    evaluation = evaluate_lots(
        POSITIONS,
        WHOLE_SIGN_CUSPS,
        profile.is_day_chart,
        asc_longitude=15.0,
        mc_longitude=280.0,
    )
    parts = {part.name: part for part in evaluation.parts}
    assert (
        parts["Death of Brothers"].computation_truth.add_reference.longitude
        == pytest.approx(280.0)
    )
    assert (
        parts["Office"].computation_truth.add_reference.longitude
        == pytest.approx(270.0)
    )


def test_profile_uses_exact_horizon_sect_for_every_dependent_component() -> None:
    positions = {
        **POSITIONS,
        "Sun": 100.0,
    }
    profile = _profile(
        natal_positions=positions,
        asc_longitude=0.0,
        mc_longitude=90.0,
    )

    # The old Asc-only compatibility rule calls this night; exact MC-oriented
    # horizon geometry correctly places the Sun above the horizon.
    assert profile.is_day_chart is True
    assert profile.sect_light == "Sun"
    assert all(
        planet.sect_truth.is_day_chart is True
        for planet in profile.planets
    )
    assert profile.lots[0].longitude == pytest.approx(
        (positions["Moon"] - positions["Sun"]) % 360.0
    )


def test_profile_preserves_decennial_failure_as_typed_not_evaluable() -> None:
    tied_positions = {
        **POSITIONS,
        "Mercury": 80.0,
        "Venus": 80.0,
    }
    profile = _profile(natal_positions=tied_positions)

    assert (
        profile.decennials.status
        is HellenisticProfileStatus.NOT_EVALUABLE
    )
    assert profile.decennials.active_periods == ()
    assert profile.decennials.sequence_truth.ambiguous_groups
    assert any(
        issue.component == "decennials"
        for issue in profile.provenance.not_evaluable
    )


def test_profile_does_not_reuse_expired_zr_periods() -> None:
    profile = _profile(
        current_dt=datetime(2300, 1, 1, tzinfo=timezone.utc),
    )

    assert (
        profile.zodiacal_releasing.status
        is HellenisticProfileStatus.NOT_EVALUABLE
    )
    assert profile.zodiacal_releasing.active_periods == ()
    assert profile.zodiacal_releasing.reason == (
        "no active Zodiacal Releasing period found at level 1"
    )
    assert any(
        issue.component == "zodiacal_releasing"
        for issue in profile.provenance.not_evaluable
    )


def test_raw_profile_marks_unspecified_position_frame() -> None:
    profile = _profile()

    assert profile.provenance.position_frame == (
        "caller_supplied_position_frame_unspecified"
    )
    assert "position_frame_unverified" in profile.provenance.warnings


def test_profile_rejects_non_admitted_policy_and_geometry() -> None:
    modern = DignityComputationPolicy(
        essential=EssentialDignityPolicy(
            doctrine=EssentialDignityDoctrine.MODERN_CO_RULERS
        )
    )
    with pytest.raises(ValueError, match="traditional Classic 7"):
        HellenisticProfilePolicy(dignity=modern)

    with pytest.raises(ValueError, match="L3/L4"):
        HellenisticProfilePolicy(
            decennials=DecennialPolicy(
                deep_subdivision_method="valens"
            )
        )

    with pytest.raises(ValueError, match="fixed Decennial L1/L2"):
        HellenisticProfilePolicy(
            decennials=DecennialPolicy(start_lord_basis="ascendant")
        )

    with pytest.raises(ValueError, match="finite and positive"):
        HellenisticProfilePolicy(zr_year=ZRYearPolicy(year_days=float("nan")))

    with pytest.raises(ValueError, match="typed skipped-lot"):
        HellenisticProfilePolicy(
            lots=LotsComputationPolicy(
                unresolved_reference_mode=LotsReferenceFailureMode.RAISE
            )
        )

    equal_house_cusps = {
        number: (15.0 + (number - 1) * 30.0) % 360.0
        for number in range(1, 13)
    }
    with pytest.raises(ValueError, match="zodiac-sign boundary"):
        _profile(house_cusps=equal_house_cusps)

    with pytest.raises(ValueError, match="timezone-aware"):
        _profile(natal_dt=NATAL_DT.replace(tzinfo=None))

    with pytest.raises(ValueError, match="earlier"):
        _profile(current_dt=datetime(1999, 1, 1, tzinfo=timezone.utc))


def test_moira_profile_wrapper_forwards_exact_geometry_and_provenance(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    sentinel = object()
    seen: dict[str, object] = {}
    policy = HellenisticProfilePolicy()
    chart = SimpleNamespace(
        longitudes=lambda *, include_nodes: dict(POSITIONS),
        speeds=lambda: dict(SPEEDS),
    )
    houses = SimpleNamespace(
        system=HouseSystem.WHOLE_SIGN,
        effective_system=HouseSystem.WHOLE_SIGN,
        fallback=False,
        cusps=tuple(WHOLE_SIGN_CUSPS.values()),
        asc=15.0,
        mc=280.0,
    )

    def fake_profile(*args, **kwargs):
        seen["args"] = args
        seen["kwargs"] = kwargs
        return sentinel

    monkeypatch.setattr(facade, "hellenistic_chart_profile", fake_profile)
    result = facade.Moira().hellenistic_chart_profile(
        chart,
        houses,
        NATAL_DT,
        CURRENT_DT,
        policy=policy,
        syzygy=1.0,
        prenatal_new_moon=2.0,
        prenatal_full_moon=3.0,
        lord_of_hour=4.0,
        observer_latitude=40.0,
        observer_longitude=-74.0,
        observer_elevation_m=10.0,
        position_frame="test_position_frame",
        kernel_id="TEST-KERNEL",
        kernel_coverage="TEST-COVERAGE",
    )

    assert result is sentinel
    assert seen["args"] == (
        POSITIONS,
        SPEEDS,
        WHOLE_SIGN_CUSPS,
        15.0,
        280.0,
        NATAL_DT,
        CURRENT_DT,
    )
    assert seen["kwargs"] == {
        "policy": policy,
        "syzygy": 1.0,
        "prenatal_new_moon": 2.0,
        "prenatal_full_moon": 3.0,
        "lord_of_hour": 4.0,
        "observer_latitude": 40.0,
        "observer_longitude": -74.0,
        "observer_elevation_m": 10.0,
        "position_frame": "test_position_frame",
        "engine_version": facade.__version__,
        "kernel_id": "TEST-KERNEL",
        "kernel_coverage": "TEST-COVERAGE",
    }

    bad_houses = SimpleNamespace(
        **{
            **houses.__dict__,
            "system": HouseSystem.PLACIDUS,
            "effective_system": HouseSystem.PLACIDUS,
        }
    )
    with pytest.raises(ValueError, match="Whole Sign"):
        facade.Moira().hellenistic_chart_profile(
            chart,
            bad_houses,
            NATAL_DT,
            CURRENT_DT,
            kernel_id="TEST-KERNEL",
            kernel_coverage="TEST-COVERAGE",
        )
