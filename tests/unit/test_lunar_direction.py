"""Neutral lunar latitude-direction and exact crossing tests."""

from __future__ import annotations

import math
from types import SimpleNamespace

import pytest

import moira
import moira.facade as facade
import moira.lunar_direction as lunar
import moira.western_electional as western


class _Reader:
    pass


def _periodic_moon(_body, jd_ut: float, *, reader):
    assert isinstance(reader, _Reader)
    phase = math.pi * jd_ut / 10.0
    return SimpleNamespace(
        latitude=5.0 * math.sin(phase),
        longitude=(13.0 * jd_ut) % 360.0,
    )


def test_direction_witness_finds_adjacent_sign_changing_roots(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(lunar, "planet_at", _periodic_moon)
    result = lunar.lunar_ecliptic_direction_at(3.0, reader=_Reader())

    assert result.hemisphere is lunar.LunarEclipticHemisphere.NORTH
    assert result.motion is lunar.LunarLatitudeMotion.NORTHWARD
    assert result.previous_crossing.jd_ut == pytest.approx(0.0, abs=1e-12)
    assert result.previous_crossing.direction is lunar.LunarNodeCrossingDirection.ASCENDING
    assert result.next_crossing.jd_ut == pytest.approx(10.0, abs=1e-12)
    assert result.next_crossing.direction is lunar.LunarNodeCrossingDirection.DESCENDING
    assert result.nearest_crossing is result.previous_crossing
    assert result.nearest_crossing_relation is lunar.LunarNodeCrossingRelation.PREVIOUS
    assert result.interpretation_scope == "astronomical_witness_only_no_doctrinal_region"


def test_exact_root_is_current_without_creating_a_doctrinal_orb(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(lunar, "planet_at", _periodic_moon)
    result = lunar.lunar_ecliptic_direction_at(10.0, reader=_Reader())

    assert result.hemisphere is lunar.LunarEclipticHemisphere.ON_ECLIPTIC
    assert result.motion is lunar.LunarLatitudeMotion.SOUTHWARD
    assert result.previous_crossing.jd_ut == 10.0
    assert result.next_crossing.jd_ut == 10.0
    assert result.nearest_crossing_relation is lunar.LunarNodeCrossingRelation.CURRENT
    assert result.policy.latitude_zero_tolerance_deg == 1e-10


def test_policy_and_input_validation_are_explicit() -> None:
    with pytest.raises(ValueError, match="scan_step_days"):
        lunar.LunarEclipticDirectionPolicy(scan_step_days=21.0)
    with pytest.raises(ValueError, match="jd_ut"):
        lunar.lunar_ecliptic_direction_at(float("nan"), reader=_Reader())
    with pytest.raises(TypeError, match="policy"):
        lunar.lunar_ecliptic_direction_at(3.0, reader=_Reader(), policy="orb")


def test_neutral_surface_is_public_through_engine_facade_and_root() -> None:
    names = {
        "LunarEclipticHemisphere",
        "LunarLatitudeMotion",
        "LunarNodeCrossingDirection",
        "LunarNodeCrossingRelation",
        "LunarEclipticDirectionPolicy",
        "LunarNodeCrossingWitness",
        "LunarEclipticDirectionWitness",
        "LUNAR_ECLIPTIC_DIRECTION_V1",
        "lunar_ecliptic_direction_at",
    }
    assert names <= set(western.__all__)
    assert names <= set(moira.__all__)
    assert names <= set(facade.__all__)
    assert hasattr(moira.Moira, "lunar_ecliptic_direction_at")


def test_facade_binds_reader_and_neutral_policy(monkeypatch: pytest.MonkeyPatch) -> None:
    captured = {}
    sentinel = object()

    def fake_direction(*args, **kwargs):
        captured["args"] = args
        captured["kwargs"] = kwargs
        return sentinel

    monkeypatch.setattr(facade, "lunar_ecliptic_direction_at", fake_direction)
    engine = moira.Moira()
    reader = object()
    engine._reader_obj = reader

    assert engine.lunar_ecliptic_direction_at(2451545.0) is sentinel
    assert captured["kwargs"]["reader"] is reader
    assert captured["kwargs"]["policy"] is lunar.LUNAR_ECLIPTIC_DIRECTION_V1
