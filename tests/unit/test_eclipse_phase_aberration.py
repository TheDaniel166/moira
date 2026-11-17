"""Conditional enclosure of the native apparent-phase aberration expression."""
from fractions import Fraction

import pytest

from moira import corrections, planets
from moira._eclipse_interval import RationalInterval as I
from moira._eclipse_interval_roots import EnclosureUnavailable
from moira._eclipse_phase_aberration import bound_phase_aberration
from moira._eclipse_phase_astro import bound_phase_planetary_vectors
from moira.constants import Body, C_KM_PER_DAY


@pytest.mark.requires_ephemeris
@pytest.mark.parametrize("tt", [1026285.7107341307, 2459891.9582497696, 2688456.25])
def test_de441_phase_aberration_is_contained(planetary_reader, tt):
    bounds = bound_phase_planetary_vectors(planetary_reader, tt, I(Fraction(-5, 86400), Fraction(5, 86400)))
    sun = bound_phase_aberration(bounds.sun_retarded_km, bounds.earth_velocity_km_per_day)
    moon = bound_phase_aberration(bounds.moon_retarded_km, bounds.earth_velocity_km_per_day)
    assert not sun.native_build_attested
    assert not sun.arithmetic_environment_attested
    assert not sun.phase_enclosed
    for seconds in (-2, 0, 2):
        epoch = tt + seconds / 86400
        earth, velocity = planets._earth_barycentric_state(epoch, planetary_reader)
        for body, box in ((Body.SUN, sun), (Body.MOON, moon)):
            initial = planets._apply_planetary_light_time(body, epoch, planetary_reader, earth, planets._barycentric)[0]
            actual = corrections.apply_aberration(initial, velocity)
            assert all(bound.contains(value) for bound, value in zip(box.position_km, actual))


def test_aberration_rejects_ambiguous_zero_distance_and_superluminal_boxes():
    zero = I.point(0)
    with pytest.raises(EnclosureUnavailable):
        bound_phase_aberration((zero, zero, zero), (zero, zero, zero))
    with pytest.raises(EnclosureUnavailable):
        bound_phase_aberration((I.point(1), zero, zero), (I.point(C_KM_PER_DAY), zero, zero))


def test_aberration_distance_wrapper_branch_and_cancellation():
    zero = I.point(0)
    with pytest.raises(EnclosureUnavailable, match="distance"):
        bound_phase_aberration((I.point(0.9e-10), zero, zero), (zero, zero, zero))
    for vector, velocity in (
        ((1.1e-10, 0.0, 0.0), (0.0, 0.0, 0.0)),
        ((1e8, -1e8, 1.0), (10000.0, 10000.0, -1e-5)),
        ((-1e7, 1e7, -1e7), (20000.0, -20000.0, 20000.0)),
    ):
        box = bound_phase_aberration(tuple(I.point(x) for x in vector), tuple(I.point(x) for x in velocity))
        actual = corrections.apply_aberration(vector, velocity)
        assert all(bound.contains(value) for bound, value in zip(box.position_km, actual))
