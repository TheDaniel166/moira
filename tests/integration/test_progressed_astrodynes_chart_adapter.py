"""Primary-source and invariant tests for chart-backed progressed Astrodynes."""

from __future__ import annotations

from datetime import datetime, timezone

import pytest

import moira
from moira.progressed_astrodynes_chart import (
    church_of_light_progressed_astrodynes_chart,
    church_of_light_progression_geometry,
)


_NATAL = datetime(1882, 12, 12, 12, 11, 26, tzinfo=timezone.utc)
_TARGET = datetime(1949, 8, 29, 12, 0, 0, tzinfo=timezone.utc)
_LAT = 41 + 37 / 60
_LON = -94.0


def _minutes(first: float, second: float) -> float:
    return abs((first - second + 180.0) % 360.0 - 180.0) * 60.0


def test_benjamine_geometry_matches_primary_manual_positions(moira_engine) -> None:
    geometry = church_of_light_progression_geometry(
        _NATAL,
        _TARGET,
        _LAT,
        _LON,
        reader=moira_engine._reader,
    )
    major = {item.body: item for item in geometry.major_terminals}
    minor = {item.body: item for item in geometry.minor_terminals}
    transit = {item.body: item for item in geometry.transit_terminals}
    truth = geometry.time_truth

    assert truth.limiting_date.year == 1882
    assert truth.limiting_date.month == 12
    assert truth.limiting_date.day == pytest.approx(9.1416666667)
    assert truth.major_completed_years == 67
    assert truth.major_egmt_interval_hours == pytest.approx(-6.6761111111)
    assert truth.major_ephemeris_datetime.date().isoformat() == "1883-02-17"
    assert truth.minor_ephemeris_datetime.date().isoformat() == "1887-12-09"

    assert _minutes(major["Sun"].longitude_deg, 328.25) < 1.0
    assert _minutes(minor["Moon"].longitude_deg, 178 + 42 / 60) < 0.2
    assert _minutes(minor["Mercury"].longitude_deg, 236 + 35 / 60) < 0.2
    assert _minutes(minor["Neptune"].longitude_deg, 58 + 10 / 60) < 0.6
    assert _minutes(transit["Neptune"].longitude_deg, 193 + 31 / 60) < 0.6


def test_chart_backed_result_is_complete_deterministic_and_kernel_derived(
    moira_engine,
) -> None:
    first = church_of_light_progressed_astrodynes_chart(
        _NATAL,
        _TARGET,
        _LAT,
        _LON,
        reader=moira_engine._reader,
    )
    second = church_of_light_progressed_astrodynes_chart(
        _NATAL,
        _TARGET,
        _LAT,
        _LON,
        reader=moira_engine._reader,
    )

    assert first == second
    assert first.normal.checksums_pass
    assert len(first.normal.signs) == 12
    assert len(first.normal.houses) == 12
    assert len(first.practical.signs) == 12
    assert len(first.practical.houses) == 12
    assert first.major_relations
    assert first.minor_relations
    assert first.transit_relations
    assert first.reenforcements
    assert len({item.relation_id for item in first.major_relations}) == len(
        first.major_relations
    )


def test_moira_facade_chart_adapter_uses_bound_reader(moira_engine) -> None:
    direct = church_of_light_progression_geometry(
        _NATAL,
        _TARGET,
        _LAT,
        _LON,
        reader=moira_engine._reader,
    )
    assert (
        moira_engine.progressed_astrodynes_geometry(
            _NATAL,
            _TARGET,
            _LAT,
            _LON,
        )
        == direct
    )


@pytest.mark.parametrize(
    "kwargs,fragment",
    [
        ({"natal_dt": datetime(2000, 1, 1)}, "timezone-aware"),
        ({"target_dt": datetime(1800, 1, 1, tzinfo=timezone.utc)}, "must not precede"),
        ({"observer_lat": 91.0}, "observer_lat"),
        ({"observer_lon": 181.0}, "observer_lon"),
    ],
)
def test_chart_adapter_rejects_invalid_boundaries(
    moira_engine,
    kwargs: dict,
    fragment: str,
) -> None:
    inputs = {
        "natal_dt": _NATAL,
        "target_dt": _TARGET,
        "observer_lat": _LAT,
        "observer_lon": _LON,
        "reader": moira_engine._reader,
    }
    inputs.update(kwargs)
    with pytest.raises((TypeError, ValueError), match=fragment):
        church_of_light_progression_geometry(**inputs)


def test_chart_adapter_public_exports_are_identity_preserving() -> None:
    import moira.facade as facade
    import moira.progressed_astrodynes_chart as adapter

    for name in adapter.__all__:
        assert getattr(moira, name) is getattr(adapter, name)
        assert getattr(facade, name) is getattr(adapter, name)
        assert name in moira.__all__
        assert name in facade.__all__
