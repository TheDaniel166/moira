from __future__ import annotations

from dataclasses import FrozenInstanceError
from types import SimpleNamespace

import pytest

import moira.lunar_orientation as lunar
from moira._lunar_apparent import LunarApparentContext


def _context(*, moon_to_sun=(0.0, 1.0, 0.0)) -> LunarApparentContext:
    return LunarApparentContext(
        jd_ut1_reception=2451545.0,
        jd_tt_reception=2451545.0007,
        jd_tdb_reception=2451545.0007,
        jd_tt_lunar_emission=2451545.00068,
        jd_tdb_lunar_emission=2451545.00068,
        jd_tt_solar_emission=2451544.9949,
        observer_distance_km=384400.0,
        observer_ssb_icrf=(0.0, 0.0, 0.0),
        observer_to_moon_icrf=(-1.0, 0.0, 0.0),
        moon_to_sun_icrf=moon_to_sun,
        sky_north_icrf=(0.0, 0.0, 1.0),
        sky_east_icrf=(0.0, 1.0, 0.0),
        icrf_to_true_of_date=((1.0, 0.0, 0.0), (0.0, 1.0, 0.0), (0.0, 0.0, 1.0)),
        translation_label="DE-0441LE-0441",
    )


def _resources():
    return SimpleNamespace(
        orientation_model="JPL DE440 lunar principal-axis orientation",
        target_frame_name="MOON_ME_DE440_ME421",
        pck_sha256="a" * 64,
        frame_kernel_sha256="b" * 64,
        coverage_start_jd_tdb=2287184.5,
        coverage_end_jd_tdb=2688976.5,
    )


def test_public_product_conventions_aliases_and_provenance(monkeypatch) -> None:
    monkeypatch.setattr(lunar, "lunar_apparent_context", lambda *_args, **_kwargs: _context())
    monkeypatch.setattr(lunar, "lunar_orientation_resources", _resources)
    monkeypatch.setattr(
        lunar,
        "lunar_me_rotation",
        lambda _jd: ((1.0, 0.0, 0.0), (0.0, 1.0, 0.0), (0.0, 0.0, 1.0)),
    )

    result = lunar.lunar_orientation_at(2451545.0, reader=object())

    assert result.observer is None
    assert result.sub_observer_longitude_east_deg == 0.0
    assert result.sub_observer_latitude_deg == 0.0
    assert result.sub_solar_longitude_east_deg == 90.0
    assert result.sub_solar_latitude_deg == 0.0
    assert result.axis_position_angle_deg == 0.0
    assert result.bright_limb_position_angle_deg == 90.0
    assert result.solar_colongitude_deg == 0.0
    assert result.libration_longitude_deg is result.sub_observer_longitude_east_deg
    assert result.libration_latitude_deg is result.sub_observer_latitude_deg
    assert result.source.body_fixed_frame == "MOON_ME_DE440_ME421"
    assert result.source.input_time_scale == "UT1"

    with pytest.raises(FrozenInstanceError):
        result.sub_observer_latitude_deg = 1.0


def test_bright_limb_position_angle_is_none_at_projection_singularity(monkeypatch) -> None:
    monkeypatch.setattr(
        lunar,
        "lunar_apparent_context",
        lambda *_args, **_kwargs: _context(moon_to_sun=(1.0, 0.0, 0.0)),
    )
    monkeypatch.setattr(lunar, "lunar_orientation_resources", _resources)
    monkeypatch.setattr(
        lunar,
        "lunar_me_rotation",
        lambda _jd: ((1.0, 0.0, 0.0), (0.0, 1.0, 0.0), (0.0, 0.0, 1.0)),
    )

    result = lunar.lunar_orientation_at(2451545.0, reader=object())
    assert result.bright_limb_position_angle_deg is None


@pytest.mark.parametrize(
    ("arguments", "error"),
    [
        ((91.0, 0.0, 0.0), ValueError),
        ((0.0, 181.0, 0.0), ValueError),
        ((0.0, 0.0, float("nan")), ValueError),
        ((True, 0.0, 0.0), TypeError),
    ],
)
def test_lunar_observer_rejects_ambiguous_or_nonfinite_coordinates(arguments, error) -> None:
    with pytest.raises(error):
        lunar.LunarObserver(*arguments)


def test_public_function_rejects_untyped_observer() -> None:
    with pytest.raises(TypeError, match="LunarObserver"):
        lunar.lunar_orientation_at(2451545.0, observer=(0.0, 0.0, 0.0), reader=object())
