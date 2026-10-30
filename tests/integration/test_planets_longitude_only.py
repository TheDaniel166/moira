"""The longitude-only route returns exactly planet_at's longitude.

``moira.planets._default_apparent_longitude`` skips the speed differentiation
for search loops (the Lilly P4 trace). Its value must be bit-identical to
``planet_at(...).longitude`` on the default apparent geocentric route, with or
without a caller-owned context memo, in any call order.
"""
import random

import pytest

from moira._kernel_paths import find_planetary_kernel
from moira.planets import _default_apparent_longitude, planet_at
from moira.spk_reader import SpkReader

pytestmark = pytest.mark.requires_ephemeris
BODIES = ("Saturn", "Jupiter", "Mars", "Sun", "Venus", "Mercury", "Moon")


@pytest.fixture(scope="module")
def reader():
    kernel = find_planetary_kernel()
    assert kernel is not None
    with SpkReader(kernel) as opened:
        yield opened


def test_longitude_only_is_bit_identical_to_planet_at(reader):
    rng = random.Random(20261030)
    memo = {}
    for _ in range(150):
        jd = 2451545. + rng.uniform(-40000., 40000.)
        for body in BODIES:
            assert _default_apparent_longitude(body, jd, reader, memo) == planet_at(body, jd, reader=reader).longitude
        later = jd + rng.uniform(.001, 1.)
        for body in reversed(BODIES):
            expected = planet_at(body, later, reader=reader).longitude
            assert _default_apparent_longitude(body, later, reader) == expected


def test_longitude_only_rejects_other_bodies_and_missing_reader(reader):
    with pytest.raises(ValueError):
        _default_apparent_longitude("Uranus", 2451545., reader)
    with pytest.raises(ValueError):
        _default_apparent_longitude("Mars", 2451545., None)
