"""Independent exact-sphere controls for the real axis/cone construction."""
from decimal import Decimal, localcontext
from fractions import Fraction as F

import pytest

from moira._eclipse_interval import RationalInterval as I
from moira._eclipse_solar_axis_reference import bound_solar_axis_reference
from moira._eclipse_solar_coverage import cover_solar_central_path


def _geometry(box, x_rate=0):
    zero = I.point(0)
    return bound_solar_axis_reference(
        box, (I.point(-1000), zero, zero), (I.point(-40)+x_rate*box, 5*box, zero),
        sun_rate=(zero, zero, zero), moon_rate=(I.point(x_rate), I.point(5), zero),
        earth_major_km=10, earth_minor_km=10, sun_radius_km=57, moon_radius_km=2,
        continuous_model=True,
    )


def test_central_sphere_chord_and_radius_against_decimal_geometry():
    value = _geometry(I.point(0))
    assert value.axis_margin.contains(100)
    assert value.forward_margin.contains(28)
    assert value.daylight_interior_proved
    with localcontext() as context:
        context.prec = 100
        sine = Decimal(55)/960
        expected = (2-30*sine)/(1-sine*sine).sqrt()
        assert value.signed_radius.contains(F(expected))
    assert value.axis_derivative.contains(0)


@pytest.mark.parametrize('speed,subtype', [(0, 'H1'), (-5, 'H2'), (5, 'H3')])
def test_moving_sphere_geometry_proves_sequence_without_sample_grid(speed, subtype):
    result = cover_solar_central_path(
        I(-4, 4), lambda box: _geometry(box, speed), tolerance=F(1, 10000),
        continuity_assumed=True, max_evaluations=6000,
    )
    assert result.coverage_complete, [(c.kind, c.reason) for c in result.cells if c.kind == 'unresolved'][:5]
    assert result.subtype == subtype
