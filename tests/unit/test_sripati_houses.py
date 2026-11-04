"""Śrīpatipaddhati I.6–8, Sastri (1937), printed worked table p. 12."""

from fractions import Fraction

import pytest

from moira.constants import HouseSystem
from moira.houses import _sripati, assign_house, houses_from_armc


_PRINTED_CENTERS = (
    (14, 31, 46), (42, 15, 14), (69, 58, 43), (97, 42, 11),
    (129, 58, 43), (162, 15, 14), (194, 31, 46), (222, 15, 14),
    (249, 58, 43), (277, 42, 11), (309, 58, 43), (342, 15, 14),
)
_PRINTED_CLOSING = (
    (28, 23, 30), (56, 6, 58), (83, 50, 27), (113, 50, 27),
    (146, 6, 58), (173, 23, 30), (208, 23, 30), (236, 6, 58),
    (263, 50, 27), (293, 50, 27), (326, 6, 58), (358, 23, 30),
)


def _arcseconds(degrees: int, minutes: int, seconds: int) -> int:
    return 3600 * degrees + 60 * minutes + seconds


def test_sastri_worked_example():
    printed_centers = tuple(_arcseconds(*entry) for entry in _PRINTED_CENTERS)
    printed_sandhis = tuple(_arcseconds(*entry) for entry in _PRINTED_CLOSING)
    asc, ic, dsc, mc = printed_centers[::3]
    full_turn = 360 * 3600
    anchors = (asc, ic, dsc, mc, asc + full_turn)
    exact_centers = []
    for left, right in zip(anchors[:-1], anchors[1:], strict=True):
        exact_centers.extend((left, Fraction(2 * left + right, 3), Fraction(left + 2 * right, 3)))
    neighbors = exact_centers[1:] + [anchors[-1]]
    exact_sandhis = [
        Fraction(left + right, 2) % full_turn
        for left, right in zip(exact_centers, neighbors, strict=True)
    ]

    centers, opening = _sripati(asc / 3600, mc / 3600)
    assert [value * 3600 for value in centers] == pytest.approx(exact_centers, abs=1e-7, rel=0)
    closing = opening[1:] + opening[:1]
    assert [value * 3600 for value in closing] == pytest.approx(exact_sandhis, abs=1e-7, rel=0)
    assert all(abs(exact - printed) <= Fraction(1, 2)
               for exact, printed in zip(exact_centers, printed_centers, strict=True))
    errors = [exact - printed for exact, printed in zip(exact_sandhis, printed_sandhis, strict=True)]
    assert [index + 1 for index, error in enumerate(errors) if abs(error) > Fraction(1, 2)] == [6]
    assert errors[5] == 5 * 3600 + Fraction(1, 6)
    assert exact_sandhis[11] - exact_sandhis[5] == 180 * 3600


@pytest.mark.parametrize("latitude", (45.0, -35.0, 80.0, -80.0))
def test_sandhis_govern_placement_in_both_zodiac_frames(latitude):
    tropical = houses_from_armc(100.0, 23.44, latitude, HouseSystem.SRIPATI)
    sidereal = houses_from_armc(100.0, 23.44, latitude, HouseSystem.SRIPATI, ayanamsa_offset=24.0)
    for figure in (tropical, sidereal):
        assert figure.house_centers[::3] == pytest.approx((figure.asc, figure.ic, figure.dsc, figure.mc))
        assert figure.sandhis == figure.cusps[1:] + figure.cusps[:1]
        opening_to_asc = (figure.asc - figure.cusps[0]) % 360
        asc_to_closing = (figure.sandhis[0] - figure.asc) % 360
        assert opening_to_asc + asc_to_closing == pytest.approx(30)
        assert opening_to_asc != pytest.approx(asc_to_closing)
        for index, (center, edge) in enumerate(zip(figure.house_centers, figure.cusps, strict=True)):
            assert assign_house(center, figure).house == index + 1
            placement = assign_house(edge, figure)
            assert placement.house == index + 1
            assert placement.exact_on_cusp
            assert assign_house((edge - 1e-5) % 360, figure).house == (index or 12)
    for name in ("cusps", "house_centers", "sandhis"):
        assert getattr(sidereal, name) == pytest.approx(
            tuple((value - 24.0) % 360 for value in getattr(tropical, name)),
        )


@pytest.mark.parametrize(("asc", "mc"), ((100.0, 140.0), (100.0, 280.0)))
def test_requires_ordered_distinct_angular_centers(asc, mc):
    with pytest.raises(ValueError, match="distinct angular centres ordered"):
        _sripati(asc, mc)
