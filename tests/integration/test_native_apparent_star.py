"""Native apparent fixed star against the Python stage 2.

``moira_native.ApparentStarEvaluator`` (src/native/include/evaluators.hpp)
applies the same parallax, light deflection (Sun, Jupiter, Saturn) and annual
aberration as ``moira.stars._earth_based_effects``, through the shared native
helpers in ``apparent_place.hpp``. Measured on 2026-10-30 over the stars and
epochs below: identical for straight-line stars; at most 0.0008 arcsec for
the binary components, whose native inputs are a two-day chord of the orbit.
"""

from __future__ import annotations

import math

import pytest

import moira.stars as stars
from moira import moira_native as mn

pytestmark = pytest.mark.requires_ephemeris

STARS = ["Sirius", "Spica", "Regulus", "Antares", "Aldebaran", "Barnard's Star", "Rigil Kentaurus", "Polaris"]
EPOCHS = [2378496.5, 2451545.0, 2460600.5, 2488069.5]
TOLERANCE_ARCSEC = 0.005


def _separation_arcsec(u, v) -> float:
    cross = (u[1] * v[2] - u[2] * v[1], u[2] * v[0] - u[0] * v[2], u[0] * v[1] - u[1] * v[0])
    dot = sum(a * b for a, b in zip(u, v))
    return math.degrees(math.atan2(math.sqrt(sum(c * c for c in cross)), dot)) * 3600.0


@pytest.mark.integration
@pytest.mark.parametrize("name", STARS)
def test_native_apparent_star_matches_python_stage_two(name, planetary_reader) -> None:
    record = {r.name: r for r in stars._load_registry_records()}[name]
    for jd in EPOCHS:
        def evaluator(target, center, jd=jd):
            return planetary_reader.evaluator(target, center, jd - 1.0, jd_end_tt=jd + 1.0)

        earth = mn.SumEvaluator(evaluator(399, 3), evaluator(3, 0))
        inputs = stars._native_star_inputs(record, jd - 1.0, jd + 1.0)
        star = mn.FixedStarEvaluator(*inputs[:6], ref_epoch_jd=inputs[6])
        native = mn.ApparentStarEvaluator(star, earth, evaluator(10, 0), evaluator(5, 0), evaluator(6, 0))
        python = stars._icrs_position(record, jd, "apparent", planetary_reader)
        assert _separation_arcsec(native.evaluate(jd)[:3], python) <= TOLERANCE_ARCSEC, (name, jd)


def test_heliacal_star_product_is_validated() -> None:
    assert stars.HeliacalSearchPolicy().star_product == "astrometric"
    with pytest.raises(ValueError, match="star_product"):
        stars.HeliacalSearchPolicy(star_product="geometric")
