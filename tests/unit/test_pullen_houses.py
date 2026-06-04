from __future__ import annotations

import pytest

from moira.constants import HouseSystem
from moira.houses import (
    _assemble_pullen_cusps,
    _compressed_expanded_quadrants,
    _pullen_sd,
    _pullen_sd_widths,
    _pullen_sr,
    _pullen_sr_widths,
    houses_from_armc,
)


def _house_spans(cusps: list[float]) -> list[float]:
    return [
        (cusps[(index + 1) % 12] - cusps[index]) % 360.0
        for index in range(12)
    ]


def _wrap_delta(left: float, right: float) -> float:
    return ((left - right + 180.0) % 360.0) - 180.0


def test_pullen_sd_and_sr_anchor_cardinal_cusps() -> None:
    armc = 20.0
    obliquity = 23.4392911
    lat = 35.0

    sd = houses_from_armc(armc, obliquity, lat, HouseSystem.PULLEN_SD)
    sr = houses_from_armc(armc, obliquity, lat, HouseSystem.PULLEN_SR)

    for houses in (sd, sr):
        assert houses.cusps[0] == pytest.approx(houses.asc)
        assert houses.cusps[9] == pytest.approx(houses.mc)
        assert _wrap_delta(houses.cusps[6], houses.asc + 180.0) == pytest.approx(0.0)
        assert _wrap_delta(houses.cusps[3], houses.mc + 180.0) == pytest.approx(0.0)


def test_pullen_sd_closed_form_width_law_for_regular_quadrant() -> None:
    q = 80.0
    widths = _pullen_sd_widths(q)
    small_flank, small_middle, _, big_flank, big_middle, _ = widths

    assert small_flank == pytest.approx(27.5)
    assert small_middle == pytest.approx(25.0)
    assert big_flank == pytest.approx(32.5)
    assert big_middle == pytest.approx(35.0)
    assert small_flank - small_middle == pytest.approx(2.5)
    assert big_flank - small_middle == pytest.approx(7.5)
    assert big_middle - small_middle == pytest.approx(10.0)


def test_pullen_sd_narrow_quadrant_branch_keeps_middle_house_zero() -> None:
    q = 20.0
    widths = _pullen_sd_widths(q)
    assert widths == pytest.approx((10.0, 0.0, 10.0, 40.0, 80.0, 40.0))

    cusps = _pullen_sd(asc=100.0, mc=80.0)
    spans = _house_spans(cusps)
    assert spans[10] == pytest.approx(0.0)  # H11


def test_pullen_sr_ratio_law_for_regular_quadrant() -> None:
    q = 80.0
    widths = _pullen_sr_widths(q)
    small_flank, small_middle, _, big_flank, big_middle, _ = widths

    ratio = small_flank / small_middle
    assert ratio > 1.0
    assert small_flank / small_middle == pytest.approx(ratio)
    assert big_flank / small_middle == pytest.approx(ratio ** 3)
    assert big_middle / small_middle == pytest.approx(ratio ** 4)
    assert sum(widths[:3]) == pytest.approx(q)
    assert sum(widths[3:]) == pytest.approx(180.0 - q)


def test_pullen_sr_extreme_narrow_quadrant_remains_ordered() -> None:
    cusps = _pullen_sr(asc=100.0, mc=99.999)
    spans = _house_spans(cusps)

    assert all(span >= 0.0 for span in spans)
    assert sum(spans) == pytest.approx(360.0)
    assert max(spans) > 170.0


def test_compressed_quadrant_orientation_is_explicit() -> None:
    q, expanded, compressed_is_mc_to_asc = _compressed_expanded_quadrants(asc=100.0, mc=20.0)
    assert q == pytest.approx(80.0)
    assert expanded == pytest.approx(100.0)
    assert compressed_is_mc_to_asc is True

    q, expanded, compressed_is_mc_to_asc = _compressed_expanded_quadrants(asc=100.0, mc=80.0)
    assert q == pytest.approx(20.0)
    assert expanded == pytest.approx(160.0)
    assert compressed_is_mc_to_asc is True

    q, expanded, compressed_is_mc_to_asc = _compressed_expanded_quadrants(asc=100.0, mc=350.0)
    assert q == pytest.approx(70.0)
    assert expanded == pytest.approx(110.0)
    assert compressed_is_mc_to_asc is False


def test_pullen_cusp_assembly_preserves_all_cardinal_anchors() -> None:
    widths = _pullen_sd_widths(80.0)
    cusps = _assemble_pullen_cusps(
        asc=100.0,
        mc=20.0,
        widths=widths,
        compressed_is_mc_to_asc=True,
    )

    assert cusps[0] == pytest.approx(100.0)
    assert cusps[3] == pytest.approx(200.0)
    assert cusps[6] == pytest.approx(280.0)
    assert cusps[9] == pytest.approx(20.0)
