"""Full closed-domain contact coverage for one continuous DE441 reference."""
from decimal import Decimal, localcontext
from fractions import Fraction as F

import pytest

from moira._eclipse_continuous_lunar import build_continuous_lunar_reference
from moira._eclipse_continuous_lunar_contacts import isolate_continuous_lunar_contacts
from moira._eclipse_interval import RationalInterval as I
from moira.constants import EARTH_RADIUS_KM, MOON_RADIUS_KM, SUN_RADIUS_KM
from tests.unit.test_eclipse_continuous_lunar import _decimal_model


def _decimal_margins(model, offset):
    """Use the independent raw-coefficient Decimal evaluator as a witness.

    The radial distance here uses |Moon|^2-z^2; production bounds use a cross
    product. The finite-cone clearance is evaluated from apex coordinates,
    independently of the interval code's cancellation-free plane form.
    """
    with localcontext() as context:
        context.prec = 110
        time = (Decimal.from_float(model.tt_anchor_jd)
                + Decimal(offset.numerator) / Decimal(offset.denominator))
        sun, moon = _decimal_model(model, time)
        distance = sum(x*x for x in sun).sqrt()
        z = -sum(x*y for x, y in zip(sun, moon)) / distance
        radial = (sum(x*x for x in moon) - z*z).sqrt()
        re, rs, rm = (Decimal.from_float(value) for value in
                      (EARTH_RADIUS_KM, SUN_RADIUS_KM, MOON_RADIUS_KM))
        p, u = (rs + re) / distance, (rs - re) / distance
        cp, cu = (1 - p*p).sqrt(), (1 - u*u).sqrt()
        pen = p * (z + re/p) - cp * radial + rm
        t = re/u - z
        clearance = u*t - cu*radial if t + u/cu*radial > 0 else -(t*t + radial*radial).sqrt()
        return pen, clearance + rm, clearance - rm


@pytest.mark.requires_ephemeris
def test_2022_reference_covers_all_three_contact_predicates(planetary_reader, record_testsuite_property):
    anchor = 2459891.96
    domain = I(F(-1, 6), F(1, 6))
    model = build_continuous_lunar_reference(planetary_reader, anchor, domain)
    result = isolate_continuous_lunar_contacts(
        model, domain, tolerance=F(1, 864000), max_evaluations=2000,
    )
    assert result.evaluations <= 2000
    record_testsuite_property('reference_contact_callbacks', result.evaluations)
    record_testsuite_property('reference_contact_vector_evaluations', result.vector_evaluations)
    record_testsuite_property('reference_contact_tolerance_seconds', '0.1')
    assert not result.eclipse_absence_certified
    assert not result.serving_evaluator_enclosed and not result.physical_accuracy_certified
    contacts = []
    for partition in (result.penumbral, result.umbral, result.total):
        assert partition.complete, [(cell.status, cell.reason) for cell in partition.cells
                                    if cell.status not in ("excluded", "unique")]
        assert partition.resolution_reached
        assert partition.domain == domain and partition.time_scale == 'TT'
        assert partition.cells[0].interval.lo == domain.lo
        assert partition.cells[-1].interval.hi == domain.hi
        assert all(a.interval.hi == b.interval.lo for a, b in zip(partition.cells, partition.cells[1:]))
        unique = [cell.interval for cell in partition.cells if cell.status == "unique"]
        assert len(unique) == 2
        contacts.append(unique)
    pen, umb, total = contacts
    assert pen[0].hi < umb[0].lo < total[0].lo < total[1].lo < umb[1].lo < pen[1].lo
    for index, (ingress, egress) in enumerate(contacts):
        # This validates sampled endpoint signs using a separately implemented
        # 120-digit route, not a second physical ephemeris or completeness proof.
        assert _decimal_margins(model, ingress.lo)[index] < 0
        assert _decimal_margins(model, ingress.hi)[index] > 0
        assert _decimal_margins(model, egress.lo)[index] > 0
        assert _decimal_margins(model, egress.hi)[index] < 0


@pytest.mark.requires_ephemeris
def test_reference_contact_domain_cannot_escape_frozen_source(planetary_reader):
    model = build_continuous_lunar_reference(planetary_reader, 2459891.96, I(F(-1, 12), F(1, 12)))
    with pytest.raises(ValueError, match="outside the frozen"):
        isolate_continuous_lunar_contacts(model, I(-1, 1), tolerance=F(1, 86400))
