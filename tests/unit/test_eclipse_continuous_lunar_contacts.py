"""Independent analytic/decimal controls for exact-reference contact coverage."""
from dataclasses import replace
from decimal import Decimal, localcontext
from fractions import Fraction as F

import pytest

from moira._eclipse_continuous_lunar import ContinuousLunarVectorBounds
from moira._eclipse_continuous_lunar_contacts import (
    bound_continuous_lunar_contacts,
    isolate_lunar_reference_contacts,
)
from moira._eclipse_interval import RationalInterval as I
from moira._eclipse_interval_roots import EnclosureUnavailable


RADII = dict(effective_earth_radius_km=2, sun_radius_km=4, moon_radius_km=F(1, 2))


def _affine(box, *, speed=1, center=0, y=0, z=10, sun_rate=0, z_rate=0):
    sun = (I.point(0), I.point(0), I.point(-20) + sun_rate * box)
    moon = (speed * (box - center), I.point(y), I.point(z) + z_rate * box)
    return ContinuousLunarVectorBounds(
        box, sun, moon,
        (I.point(0), I.point(0), I.point(sun_rate)),
        (I.point(speed), I.point(0), I.point(z_rate)), (),
    )


def _cover(partition):
    assert partition.cells[0].interval.lo == partition.domain.lo
    assert partition.cells[-1].interval.hi == partition.domain.hi
    assert all(a.interval.hi == b.interval.lo for a, b in zip(partition.cells, partition.cells[1:]))


def _roots(partition):
    return [cell for cell in partition.cells if cell.status == "unique"]


def test_all_six_synthetic_contacts_and_complementary_exclusions():
    domain = I(-8, 8)
    result = isolate_lunar_reference_contacts(
        domain, _affine, tolerance=F(1, 1000), continuity_assumed=True,
        max_evaluations=2000, **RADII,
    )
    assert result.evaluations <= 2000
    assert result.vector_evaluations < result.evaluations
    assert not result.eclipse_absence_certified and not result.serving_evaluator_enclosed
    # Independently, contacts satisfy x^2=(E +/- z*sin(angle) +/- M)^2/cos(angle)^2.
    expected_squares = (F(55, 10)**2 / F(91, 100), F(3, 2)**2 / F(99, 100),
                        F(1, 2)**2 / F(99, 100))
    for partition, squared in zip((result.penumbral, result.umbral, result.total), expected_squares):
        _cover(partition)
        assert partition.complete and partition.resolution_reached
        roots = _roots(partition)
        assert len(roots) == 2
        assert roots[0].interval.hi < 0 < roots[1].interval.lo
        for root in roots:
            assert root.interval.square().contains(squared)
            assert not root.derivative.contains_zero


def test_short_positive_interval_between_fixed_cadence_samples_is_retained():
    center, speed = F(1, 3), 60_000_000

    def vectors(box):
        return _affine(box, speed=speed, center=center)

    result = isolate_lunar_reference_contacts(
        I(0, 1), vectors, tolerance=F(1, 10**10), continuity_assumed=True,
        max_evaluations=3000, **RADII,
    )
    roots = _roots(result.penumbral)
    assert result.penumbral.complete and len(roots) == 2
    assert 0 < (roots[1].interval.hi - roots[0].interval.lo) * 86400 < F(1, 10)
    assert roots[0].interval.hi < center < roots[1].interval.lo
    assert bound_continuous_lunar_contacts(vectors(I.point(center)), **RADII).penumbral_margin_km.lo > 0
    for time in (F(0), F(1, 4), F(1, 2), F(3, 4), F(1)):
        assert bound_continuous_lunar_contacts(vectors(I.point(time)), **RADII).penumbral_margin_km.hi < 0


def test_exact_tangent_remains_unresolved_and_near_miss_is_excluded():
    # E=1, S=2, distance=5 -> sin(p)=3/5, cos(p)=4/5.
    # At z=10, M=1, the penumbral contact radial distance is exactly 10.
    radii = dict(effective_earth_radius_km=1, sun_radius_km=2, moon_radius_km=1)

    def vectors(box, offset=0):
        return replace(_affine(box, y=10 + offset),
                       sun_geocentric_km=(I.point(0), I.point(0), I.point(-5)))

    tangent = isolate_lunar_reference_contacts(
        I(-1, 1), vectors, tolerance=F(1, 1000), continuity_assumed=True,
        max_evaluations=2000, **radii,
    )
    assert not tangent.penumbral.complete
    assert any(cell.status == "unresolved" and cell.interval.contains(0)
               for cell in tangent.penumbral.cells)
    miss = isolate_lunar_reference_contacts(
        I(-1, 1), lambda box: vectors(box, F(1, 1000)),
        tolerance=F(1, 1000), continuity_assumed=True, **radii,
    )
    assert miss.penumbral.complete
    assert all(cell.status == "excluded" for cell in miss.penumbral.cells)


@pytest.mark.parametrize("budget", [0, 1, 7])
def test_budget_is_shared_and_all_unprocessed_domains_are_retained(budget):
    result = isolate_lunar_reference_contacts(
        I(-8, 8), _affine, tolerance=F(1, 1000), continuity_assumed=True,
        max_evaluations=budget, **RADII,
    )
    assert result.evaluations <= budget
    assert result.vector_evaluations <= budget
    for partition in (result.penumbral, result.umbral, result.total):
        _cover(partition)
        assert not partition.complete
    assert result.total.cells[0].reason == "evaluation_budget_exhausted"


def test_missing_derivative_or_continuity_never_proves_unique_contacts():
    result = isolate_lunar_reference_contacts(
        I(-8, 8), lambda box: replace(_affine(box), differentiable_on_domain=False),
        tolerance=F(1, 10), continuity_assumed=True, **RADII,
    )
    assert not result.penumbral.complete
    assert not _roots(result.penumbral)
    unproved = isolate_lunar_reference_contacts(
        I(-8, 8), _affine, tolerance=F(1, 10), continuity_assumed=False, **RADII,
    )
    assert not unproved.penumbral.complete and not _roots(unproved.penumbral)


def test_unsupported_seam_retains_its_whole_domain_and_unexpected_errors_propagate():
    def missing(box):
        raise EnclosureUnavailable("unproved record seam")

    result = isolate_lunar_reference_contacts(
        I(-1, 1), missing, tolerance=F(1, 100), continuity_assumed=True, **RADII,
    )
    for partition in (result.penumbral, result.umbral, result.total):
        assert len(partition.cells) == 1
        assert partition.cells[0].status == "unresolved"
        assert "unproved record seam" in partition.cells[0].reason
        _cover(partition)

    def broken(box):
        raise RuntimeError("unexpected provider bug")

    with pytest.raises(RuntimeError, match="provider bug"):
        isolate_lunar_reference_contacts(
            I(-1, 1), broken, tolerance=F(1, 100), continuity_assumed=True, **RADII,
        )


def _decimal_margins(time, *, sun_rate, z, z_rate, y):
    # Independent closed-form evaluation for a straight Moon trajectory and
    # a collinear moving Sun; all input fractions denote exact reals.
    def d(value):
        value = F(value)
        return Decimal(value.numerator) / Decimal(value.denominator)

    distance = 20 - d(sun_rate) * time
    axial = d(z) + d(z_rate) * time
    radial = (time * time + d(y)**2).sqrt()
    p, u = Decimal(6) / distance, Decimal(2) / distance
    cp, cu = (1 - p*p).sqrt(), (1 - u*u).sqrt()
    pen = 2 + p*axial - cp*radial + Decimal('0.5')
    t = 2/u - axial
    umb = 2 - u*axial - cu*radial if t + u/cu*radial > 0 else -(t*t + radial*radial).sqrt()
    return pen, umb + Decimal('0.5'), umb - Decimal('0.5')


@pytest.mark.parametrize("z", [10, 19, 25, 30])
@pytest.mark.parametrize("time", [F(-3, 2), F(1, 4), F(3, 2)])
def test_values_and_rates_enclose_independent_high_precision_reference(z, time):
    params = dict(sun_rate=F(1, 100), z=z, z_rate=F(1, 5), y=F(1, 3))
    bounds = bound_continuous_lunar_contacts(_affine(I.point(time), **params), **RADII)
    with localcontext() as context:
        context.prec = 100
        t = Decimal(time.numerator) / Decimal(time.denominator)
        step = Decimal('1e-24')
        values = _decimal_margins(t, **params)
        before = _decimal_margins(t - step, **params)
        after = _decimal_margins(t + step, **params)
        for phase, expected, left, right in zip(("penumbral", "umbral", "total"), values, before, after):
            value = getattr(bounds, phase + "_margin_km")
            rate = getattr(bounds, phase + "_derivative_km_per_day")
            assert value.contains(F(expected))
            # The centred high-precision derivative is a sampled numerical
            # witness, not the source of the interval derivative guarantee.
            assert rate.contains(F((right - left) / (2 * step)))


def test_axis_and_apex_derivatives_are_not_invented():
    bounds = bound_continuous_lunar_contacts(_affine(I.point(0), z=20), **RADII)
    assert bounds.axis_distance_km.contains(0)
    assert bounds.umbral_margin_km.contains(F(1, 2))
    assert bounds.total_margin_km.contains(F(-1, 2))
    assert bounds.umbral_derivative_km_per_day is None


def test_nappe_switch_box_encloses_samples_on_both_branches():
    params = dict(sun_rate=0, z=F(201, 10), z_rate=0, y=F(1, 3))
    bounds = bound_continuous_lunar_contacts(_affine(I(-2, 2), **params), **RADII)
    with localcontext() as context:
        context.prec = 100
        for time in (Decimal('-2'), Decimal('0'), Decimal('2')):
            expected = _decimal_margins(time, **params)
            assert bounds.umbral_margin_km.contains(F(expected[1]))
            assert bounds.total_margin_km.contains(F(expected[2]))


@pytest.mark.parametrize("changed", [
    dict(effective_earth_radius_km=0), dict(sun_radius_km=2),
    dict(moon_radius_km=True), dict(moon_radius_km=float('nan')),
    dict(precision_bits=63), dict(precision_bits=True),
])
def test_invalid_radii_and_precision_are_rejected(changed):
    options = RADII | changed
    with pytest.raises(ValueError):
        bound_continuous_lunar_contacts(_affine(I.point(0)), **options)


def test_domain_and_provider_receipts_are_checked():
    with pytest.raises(EnclosureUnavailable, match="downstream"):
        bound_continuous_lunar_contacts(_affine(I.point(0), y=10, z=0), **RADII)
    with pytest.raises(TypeError, match="exactly the requested"):
        isolate_lunar_reference_contacts(
            I(-1, 1), lambda box: _affine(I.point(0)),
            tolerance=F(1, 10), continuity_assumed=True, **RADII,
        )
