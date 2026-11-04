"""Geometric witnesses from the Introduction to the Tetrabiblos, chs. 43 and 52."""

from fractions import Fraction
from itertools import accumulate

import pytest

from moira.constants import HouseSystem
from moira.houses import _porphyry_prespan, assign_house, houses_from_armc


def test_chapter_52_unequal_quadrants():
    # The source supplies quadrant spans. Set ASC to 3° to exercise wrap.
    # Accumulate the published thirds from the prescribed opening.
    widths = [Fraction(span, 3) for span in (84, 96, 84, 96) for _ in range(3)]
    expected = [opening % 360 for opening in accumulate(widths[:-1], initial=Fraction(-2))]
    actual = _porphyry_prespan(3, 267)
    assert actual == pytest.approx(expected, abs=1e-10, rel=0)
    assert [(closing - opening) % 360 for opening, closing in zip(
        actual, actual[1:] + actual[:1], strict=True,
    )] == pytest.approx(widths)


@pytest.mark.parametrize("latitude", (45, -45, 75, -75))
def test_angular_houses_open_five_degrees_before_their_angles(latitude):
    tropical = houses_from_armc(0, 23.44, latitude, HouseSystem.PORPHYRY_PRESPAN)
    sidereal = houses_from_armc(
        0, 23.44, latitude, HouseSystem.PORPHYRY_PRESPAN, ayanamsa_offset=24,
    )
    assert tropical.effective_system == HouseSystem.PORPHYRY_PRESPAN
    assert sidereal.cusps == pytest.approx(tuple((cusp - 24) % 360 for cusp in tropical.cusps))
    for figure in (tropical, sidereal):
        for house, angle in zip((1, 4, 7, 10), (figure.asc, figure.ic, figure.dsc, figure.mc), strict=True):
            assert (angle - figure.cusps[house - 1]) % 360 == pytest.approx(5)
            assert assign_house(angle, figure).house == house


@pytest.mark.parametrize("quadrant", (14.999, 15))
def test_narrow_quadrant_rejects_prespan_without_a_positive_remainder(quadrant):
    with pytest.raises(ValueError, match="exceed 15°"):
        _porphyry_prespan(100, 100 - quadrant)


def test_just_wider_than_the_limit_is_admitted():
    cusps = _porphyry_prespan(100, 84.999)
    assert cusps[0] == pytest.approx(95)
    assert (cusps[0] - cusps[-1]) % 360 > 5


def test_inverted_angular_anchors_are_rejected():
    with pytest.raises(ValueError, match="angular anchors ordered"):
        _porphyry_prespan(100, 140)


@pytest.mark.parametrize(("armc", "latitude", "reason"), (
    (269, 66.56, "exceed 15°"),
    (270, 66.56, "uniquely defined rising"),
    (90, -66.56, "uniquely defined rising"),
    (0, 90, "uniquely defined rising"),
    (0, -90, "uniquely defined rising"),
))
def test_rejects_out_of_domain_observer_frames(armc, latitude, reason):
    with pytest.raises(ValueError, match=reason):
        houses_from_armc(armc, 23.44, latitude, HouseSystem.PORPHYRY_PRESPAN)
