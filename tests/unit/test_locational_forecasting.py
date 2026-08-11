from __future__ import annotations

from dataclasses import replace
from types import SimpleNamespace

import pytest

import moira.locational_forecasting as locational
from moira.chart import ChartContext
from moira.constants import Body, HouseSystem
from moira.houses import HouseCusps, classify_house_system
from moira.transits import ReturnSearchPolicy, TransitComputationPolicy


def _houses(system: str = HouseSystem.EQUAL) -> HouseCusps:
    return HouseCusps(
        system=system,
        cusps=tuple(float(index * 30) for index in range(12)),
        asc=0.0,
        mc=270.0,
        armc=270.0,
        effective_system=system,
        classification=classify_house_system(system),
    )


def _chart(
    jd_ut: float,
    latitude: float,
    longitude: float,
    *,
    planets=None,
    nodes=None,
    system: str = HouseSystem.EQUAL,
) -> ChartContext:
    if planets is None:
        planets = {
            Body.SUN: SimpleNamespace(longitude=10.0, speed=1.0),
            Body.MOON: SimpleNamespace(longitude=20.0, speed=13.0),
        }
    if nodes is None:
        nodes = {Body.TRUE_NODE: SimpleNamespace(longitude=30.0)}
    return ChartContext(
        jd_ut=jd_ut,
        jd_tt=jd_ut + 0.0008,
        latitude=latitude,
        longitude=longitude,
        planets=planets,
        nodes=nodes,
        houses=_houses(system),
    )


def _patch_chart_composition(monkeypatch: pytest.MonkeyPatch, jd_return: float) -> None:
    def fake_create_chart(
        jd_ut,
        latitude,
        longitude,
        *,
        house_system,
        bodies,
        reader,
        policy,
    ):
        assert jd_ut == jd_return
        return _chart(jd_ut, latitude, longitude, system=house_system)

    def fake_relocated_chart(
        chart,
        latitude,
        longitude,
        *,
        house_system,
        policy,
    ):
        return _chart(
            chart.jd_ut,
            latitude,
            longitude,
            planets=dict(chart.planets),
            nodes=dict(chart.nodes),
            system=chart.houses.system if house_system is None else house_system,
        )

    monkeypatch.setattr(locational, "create_chart", fake_create_chart)
    monkeypatch.setattr(locational, "relocated_chart", fake_relocated_chart)


def test_relocated_solar_return_preserves_exact_epoch_and_celestial_snapshot(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    jd_return = 2_460_123.456
    monkeypatch.setattr(locational, "solar_return", lambda *args, **kwargs: jd_return)
    _patch_chart_composition(monkeypatch, jd_return)

    result = locational.relocated_solar_return(
        280.0,
        2027,
        40.0,
        -75.0,
        51.5,
        -0.1,
        source_house_system=HouseSystem.EQUAL,
        return_policy=TransitComputationPolicy(
            returns=ReturnSearchPolicy(
                step_days_override=0.5,
                default_max_days=400.0,
                per_body_max_days=((Body.SUN, 370.0),),
                solver_tolerance_days=2e-7,
            )
        ),
    )

    assert result.return_truth.return_kind == "solar_return"
    assert result.return_truth.body == Body.SUN
    assert result.return_truth.year == 2027
    assert result.return_truth.timing_source == "moira.transits.solar_return"
    assert result.return_truth.search_policy.policy_source == "caller_supplied"
    assert result.return_truth.search_policy.step_days_override == 0.5
    assert result.return_truth.search_policy.default_max_days == 400.0
    assert result.return_truth.search_policy.per_body_max_days == ((Body.SUN, 370.0),)
    assert result.return_truth.search_policy.solver_tolerance_days == pytest.approx(2e-7)
    assert result.source_chart.jd_ut == result.relocated_chart.jd_ut == jd_return
    assert dict(result.source_chart.planets) == dict(result.relocated_chart.planets)
    assert result.relocation_truth.same_epoch is True
    assert result.relocation_truth.same_celestial_snapshot is True
    assert result.relocation_truth.interpretation == "none_geometry_only"


@pytest.mark.parametrize(
    ("wrapper", "timing_name", "expected_kind", "expected_body"),
    [
        ("lunar", "lunar_return", "lunar_return", Body.MOON),
        ("planetary", "planet_return", "planetary_return", Body.VENUS),
    ],
)
def test_relocated_non_solar_return_truth_is_explicit(
    monkeypatch: pytest.MonkeyPatch,
    wrapper: str,
    timing_name: str,
    expected_kind: str,
    expected_body: str,
) -> None:
    jd_return = 2_460_200.25
    monkeypatch.setattr(locational, timing_name, lambda *args, **kwargs: jd_return)
    _patch_chart_composition(monkeypatch, jd_return)

    common = dict(
        source_latitude=10.0,
        source_longitude=20.0,
        relocated_latitude=-30.0,
        relocated_longitude=120.0,
        source_house_system=HouseSystem.EQUAL,
    )
    if wrapper == "lunar":
        result = locational.relocated_lunar_return(45.0, 2_460_150.0, **common)
    else:
        result = locational.relocated_planetary_return(
            Body.VENUS,
            75.0,
            2_460_150.0,
            direction="either",
            **common,
        )

    assert result.return_truth.return_kind == expected_kind
    assert result.return_truth.body == expected_body
    assert result.return_truth.search_start_jd_ut == 2_460_150.0
    assert result.return_truth.timing_source == f"moira.transits.{timing_name}"
    assert result.return_truth.search_policy.policy_source == "default"


def test_transiting_astrocartography_builds_explicit_snapshots_and_line_shifts(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(locational, "_ut1_to_ephemeris_tt", lambda jd, reader: jd + 0.0008)
    monkeypatch.setattr(locational, "nutation", lambda jd_tt: (0.1, 0.0))
    monkeypatch.setattr(locational, "true_obliquity", lambda jd_tt: 23.4)
    monkeypatch.setattr(
        locational,
        "apparent_sidereal_time",
        lambda jd_ut, dpsi, obliquity: jd_ut % 360.0,
    )

    def fake_sky_position_at(body, jd_ut, **kwargs):
        assert body == Body.SUN
        return SimpleNamespace(
            right_ascension=(2.0 * jd_ut) % 360.0,
            declination=15.0,
        )

    monkeypatch.setattr(locational, "sky_position_at", fake_sky_position_at)
    result = locational.transiting_astrocartography(
        (100.0, 101.0),
        (Body.SUN,),
        observer_latitude=0.0,
        observer_longitude=0.0,
        lat_step=10.0,
        reader=object(),
    )

    assert result.computation_truth.mode == "transit"
    assert result.computation_truth.epochs_jd_ut == (100.0, 101.0)
    assert result.computation_truth.progressed_mode == "not_admitted"
    assert result.computation_truth.directed_mode == "not_admitted"
    assert len(result.snapshots) == 2
    assert all(len(snapshot.lines) == 4 for snapshot in result.snapshots)
    assert len(result.transitions) == 4
    mc_shift = next(item for item in result.transitions if item.line_type == "MC")
    # RA advances 2 degrees while sidereal time advances 1 degree.
    assert mc_shift.meridian_signed_delta_deg == pytest.approx(1.0)
    assert mc_shift.source_meridian_longitude is not None
    assert mc_shift.target_meridian_longitude is not None
    asc_shift = next(item for item in result.transitions if item.line_type == "ASC")
    assert asc_shift.meridian_signed_delta_deg is None
    assert asc_shift.curve_point_shifts

    with pytest.raises(ValueError, match="exactly one MC/IC/ASC/DSC"):
        replace(
            result.snapshots[0],
            lines=(result.snapshots[0].lines[0],) * 4,
        )
    with pytest.raises(ValueError, match="exactly cover adjacent"):
        replace(
            result,
            transitions=(result.transitions[1], result.transitions[0], *result.transitions[2:]),
        )


def test_dynamic_astrocartography_rejects_implicit_policy_expansion() -> None:
    with pytest.raises(ValueError, match="strictly increasing"):
        locational.transiting_astrocartography(
            (101.0, 100.0),
            (Body.SUN,),
            observer_latitude=0.0,
            observer_longitude=0.0,
            reader=object(),
        )
    with pytest.raises(ValueError, match="admitted planets"):
        locational.transiting_astrocartography(
            (100.0,),
            ("Ceres",),
            observer_latitude=0.0,
            observer_longitude=0.0,
            reader=object(),
        )
    with pytest.raises(ValueError, match="must be unique"):
        locational.transiting_astrocartography(
            (100.0,),
            (Body.SUN, Body.SUN),
            observer_latitude=0.0,
            observer_longitude=0.0,
            reader=object(),
        )
    with pytest.raises(ValueError, match="epochs must be finite"):
        locational.transiting_astrocartography(
            (True,),
            (Body.SUN,),
            observer_latitude=0.0,
            observer_longitude=0.0,
            reader=object(),
        )
    with pytest.raises(ValueError, match="bodies must be a sequence"):
        locational.transiting_astrocartography(
            (100.0,),
            "Sun",
            observer_latitude=0.0,
            observer_longitude=0.0,
            reader=object(),
        )
