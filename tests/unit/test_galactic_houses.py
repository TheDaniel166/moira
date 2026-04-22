from __future__ import annotations

import pytest

from moira import galactic_houses


def test_calculate_galactic_houses_rejects_invalid_geographic_coordinates() -> None:
    with pytest.raises(ValueError, match="latitude must be in \\[-90, 90\\]"):
        galactic_houses.calculate_galactic_houses(2460000.5, 91.0, 0.0)

    with pytest.raises(ValueError, match="latitude must be in \\[-90, 90\\]"):
        galactic_houses.calculate_galactic_houses(2460000.5, -91.0, 0.0)

    with pytest.raises(ValueError, match="longitude must be in \\[-180, 180\\]"):
        galactic_houses.calculate_galactic_houses(2460000.5, 0.0, 181.0)


def test_find_galactic_angles_accepts_exact_zero_sweep_crossing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    step = 360.0 / galactic_houses._SWEEP_N

    def fake_altitude(l: float, armc: float, lat: float, jd_tt: float) -> float:
        index = round((l % 360.0) / step) % galactic_houses._SWEEP_N
        if index == 0:
            return 0.0
        if index < galactic_houses._SWEEP_N // 2:
            return 1.0
        return -1.0

    def fake_ternary_max(
        l_lo: float,
        l_hi: float,
        armc: float,
        lat: float,
        jd_tt: float,
    ) -> float:
        return 90.0

    def fake_bisect_horizon(
        l_lo: float,
        l_hi: float,
        armc: float,
        lat: float,
        jd_tt: float,
    ) -> float:
        if l_lo < 1.0:
            return 0.0
        return 180.0

    def fake_hour_angle(l: float, armc: float, jd_tt: float) -> float:
        return 270.0 if abs((l % 360.0) - 0.0) < 1e-9 else 90.0

    monkeypatch.setattr(galactic_houses, "_gal_altitude", fake_altitude)
    monkeypatch.setattr(galactic_houses, "_ternary_max", fake_ternary_max)
    monkeypatch.setattr(galactic_houses, "_bisect_horizon", fake_bisect_horizon)
    monkeypatch.setattr(galactic_houses, "_gal_hour_angle", fake_hour_angle)

    ga_l, gmc_l, gd_l, gic_l = galactic_houses._find_galactic_angles(
        armc=0.0,
        lat=0.0,
        jd_tt=2460000.5,
    )

    assert ga_l == pytest.approx(0.0)
    assert gmc_l == pytest.approx(90.0)
    assert gd_l == pytest.approx(180.0)
    assert gic_l == pytest.approx(270.0)


def _synthetic_galactic_cusps(start: float = 0.0) -> galactic_houses.GalacticHouseCusps:
    cusps_gal = tuple((start + i * 30.0) % 360.0 for i in range(12))
    cusps_ecl = cusps_gal
    angles = galactic_houses.GalacticAngles(
        ga_lon=cusps_gal[0],
        gmc_lon=cusps_gal[9],
        gd_lon=cusps_gal[6],
        gic_lon=cusps_gal[3],
        ga_ecl=cusps_ecl[0],
        gmc_ecl=cusps_ecl[9],
        gd_ecl=cusps_ecl[6],
        gic_ecl=cusps_ecl[3],
    )
    return galactic_houses.GalacticHouseCusps(
        cusps_ecl=cusps_ecl,
        cusps_gal=cusps_gal,
        angles=angles,
    )


def test_assign_galactic_house_places_midpoints_in_expected_house() -> None:
    house_cusps = _synthetic_galactic_cusps(0.0)

    for house_number in range(1, 13):
        midpoint = ((house_number - 1) * 30.0 + 15.0) % 360.0
        placement = galactic_houses.assign_galactic_house(midpoint, house_cusps)
        assert placement.house == house_number
        assert placement.exact_on_cusp is False
        assert placement.cusp_longitude == pytest.approx(house_cusps.cusps_gal[house_number - 1])


def test_assign_galactic_house_opening_cusp_belongs_to_opening_house() -> None:
    house_cusps = _synthetic_galactic_cusps(10.0)

    for house_number in range(1, 13):
        cusp = house_cusps.cusps_gal[house_number - 1]
        placement = galactic_houses.assign_galactic_house(cusp, house_cusps)
        assert placement.house == house_number
        assert placement.exact_on_cusp is True


def test_assign_galactic_house_normalizes_input() -> None:
    house_cusps = _synthetic_galactic_cusps(350.0)

    placement_a = galactic_houses.assign_galactic_house(5.0, house_cusps)
    placement_b = galactic_houses.assign_galactic_house(365.0, house_cusps)

    assert placement_a.house == 1
    assert placement_b.house == placement_a.house
    assert placement_b.galactic_longitude == pytest.approx(placement_a.galactic_longitude)


def test_body_galactic_house_position_matches_membership_and_midpoint_fraction() -> None:
    house_cusps = _synthetic_galactic_cusps(0.0)

    midpoint = 75.0
    position = galactic_houses.body_galactic_house_position(midpoint, house_cusps)
    placement = galactic_houses.assign_galactic_house(midpoint, house_cusps)

    assert position == pytest.approx(3.5)
    assert int(position) == placement.house


def test_describe_galactic_boundary_reports_forward_arc_distances() -> None:
    house_cusps = _synthetic_galactic_cusps(0.0)
    placement = galactic_houses.assign_galactic_house(75.0, house_cusps)

    profile = galactic_houses.describe_galactic_boundary(placement, near_cusp_threshold=20.0)

    assert profile.opening_cusp == pytest.approx(60.0)
    assert profile.closing_cusp == pytest.approx(90.0)
    assert profile.dist_to_opening == pytest.approx(15.0)
    assert profile.dist_to_closing == pytest.approx(15.0)
    assert profile.house_span == pytest.approx(30.0)
    assert profile.nearest_cusp == pytest.approx(60.0)
    assert profile.nearest_cusp_distance == pytest.approx(15.0)
    assert profile.is_near_cusp is True


def test_describe_galactic_boundary_rejects_non_positive_threshold() -> None:
    house_cusps = _synthetic_galactic_cusps(0.0)
    placement = galactic_houses.assign_galactic_house(75.0, house_cusps)

    with pytest.raises(ValueError, match="near_cusp_threshold must be positive"):
        galactic_houses.describe_galactic_boundary(placement, near_cusp_threshold=0.0)


def test_calculate_galactic_houses_returns_live_cusps_with_valid_ranges_and_membership() -> None:
    houses = galactic_houses.calculate_galactic_houses(2451545.0, 51.5, 0.0)

    assert len(houses.cusps_gal) == 12
    assert len(houses.cusps_ecl) == 12
    for cusp in houses.cusps_gal:
        assert 0.0 <= cusp < 360.0
    for cusp in houses.cusps_ecl:
        assert 0.0 <= cusp < 360.0

    for house_number in range(1, 13):
        opening = houses.cusps_gal[house_number - 1]
        closing = houses.cusps_gal[house_number % 12]
        span = (closing - opening) % 360.0
        midpoint = (opening + span / 2.0) % 360.0

        placement = galactic_houses.assign_galactic_house(midpoint, houses)
        position = galactic_houses.body_galactic_house_position(midpoint, houses)
        boundary = galactic_houses.describe_galactic_boundary(placement)

        assert placement.house == house_number
        assert int(position) == house_number
        assert house_number < position < house_number + 1.0
        assert boundary.house_span == pytest.approx(span)
        assert boundary.dist_to_opening + boundary.dist_to_closing == pytest.approx(span)
