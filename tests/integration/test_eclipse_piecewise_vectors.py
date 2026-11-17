"""Independent raw-word Decimal checks across mixed emission records."""
from decimal import Decimal as D, localcontext
from fractions import Fraction as F

import pytest

from moira._eclipse_interval import RationalInterval as I
from moira._eclipse_piecewise_vectors import freeze_eclipse_records, enclose_piecewise_eclipse_vectors
from moira.constants import C_KM_PER_DAY
from moira import julian


def decimal_piecewise_vectors(model, offset, retarded_moon=False):
    """Independent forward Chebyshev recurrence and 120-digit iterations."""
    with localcontext() as context:
        context.prec = 120
        pi = D('3.141592653589793238462643383279502884197169399375105820974944592307816406286208998628034825342117068')

        def dec(value):
            return D(value.numerator)/D(value.denominator)

        def sin(x):
            x %= 2*pi
            if x>pi:
                x -= 2*pi
            if x < -pi:
                x += 2*pi
            total = term = x
            for n in range(1,120):
                term *= -x*x/D((2*n)*(2*n+1))
                total += term
            return total

        def seconds(tt):
            k,m0,m1,eb = map(D.from_float,(julian._NAIF_DELTET_K_SECONDS,
                julian._NAIF_DELTET_M0_RADIANS,julian._NAIF_DELTET_M1_RADIANS_PER_SECOND,
                julian._NAIF_DELTET_EB))
            correction = D(0)
            for _ in range(12):
                mean = m0+m1*86400*(tt+correction-2451545)
                correction = k/86400*sin(mean+eb*sin(mean))
            return (tt+correction-2451545)*86400

        def route(pair,tt):
            et = seconds(tt)
            selected = [r for r in model.records if r.pair==pair and
                        dec(r.midpoint_seconds-r.radius_seconds)<=et<=dec(r.midpoint_seconds+r.radius_seconds)]
            record = max(selected,key=lambda r:r.index)
            x = (et-dec(record.midpoint_seconds))/dec(record.radius_seconds)
            axes = []
            for coefficients in record.coefficients:
                p0,p1 = D(1),x
                total = dec(coefficients[0])
                if len(coefficients)>1:
                    total += dec(coefficients[1])*p1
                for coefficient in coefficients[2:]:
                    p0,p1 = p1,2*x*p1-p0
                    total += dec(coefficient)*p1
                axes.append(total)
            return tuple(axes)

        def add(a,b):
            return tuple(x+y for x,y in zip(a,b))

        def sub(a,b):
            return tuple(x-y for x,y in zip(a,b))

        t = D.from_float(model.tt_anchor_jd)+dec(offset)
        emb,leg,ml = (route(pair,t) for pair in ((0,3),(3,399),(3,301)))
        earth = add(emb,leg)
        speed = D.from_float(C_KM_PER_DAY)

        def retard(initial,body):
            vector = sub(initial,earth)
            for _ in range(10):
                delay = sum(x*x for x in vector).sqrt()/speed
                emitted = (route((0,10),t-delay) if body=='sun' else
                    add(route((0,3),t-delay),route((3,301),t-delay)))
                vector = sub(emitted,earth)
            return vector

        return (retard(route((0,10),t),'sun'),
                retard(add(emb,ml),'moon') if retarded_moon else sub(ml,leg))


@pytest.mark.requires_ephemeris
@pytest.mark.parametrize('anchor', [1248813.457560655,2459891.96,2001312.505])
@pytest.mark.parametrize('retarded_moon', [False,True])
def test_value_rate_curvature_with_independent_decimal(planetary_reader,anchor,retarded_moon):
    domain = I(F(-2,86400),F(2,86400))
    model = freeze_eclipse_records(planetary_reader,anchor,domain)
    point = enclose_piecewise_eclipse_vectors(model,I.point(0),retarded_moon=retarded_moon)
    assert point.continuous_on_domain and model.raw_record_words_verified
    with localcontext() as context:
        context.prec = 100
        h = F(1,10**10)
        center = decimal_piecewise_vectors(model,F(0),retarded_moon)
        left = decimal_piecewise_vectors(model,-h,retarded_moon)
        right = decimal_piecewise_vectors(model,h,retarded_moon)
        step = D(h.numerator)/D(h.denominator)
        for jets,values,before,after in zip((point.sun,point.moon),center,left,right):
            for jet,x,prior,later in zip(jets,values,before,after):
                assert jet[0].contains(F(x))
                assert jet[1].contains(F((later-prior)/(2*step)))
                assert jet[2].contains(F((later-2*x+prior)/(step*step)))


@pytest.mark.requires_ephemeris
def test_actual_record_crossing_retains_branch_residuals(planetary_reader):
    domain = I(F(-1,86400),F(1,86400))
    model = freeze_eclipse_records(planetary_reader,2001312.5,domain)
    point = enclose_piecewise_eclipse_vectors(model,domain)
    assert not point.continuous_on_domain and point.switches
    assert all(s.residual_seconds.contains_zero for s in point.switches)
    assert any(s.label=='sun_reception' for s in point.switches)
