"""Conservative second-TT-derivative bounds for the frozen lunar reference.

For Chebyshev degree n on [-1,1], |T_n'|<=n^2 and
|T_n''|<=n^2(n^2-1)/3. Time-chain and norm derivatives propagate those
absolute bounds through the same ten ideal Sun-delay updates. These bounds
do not concern the rounded serving evaluator or physical acceleration error.
"""
from dataclasses import dataclass
from fractions import Fraction as F

from . import _eclipse_reference_clock as clock_source
from ._eclipse_continuous_lunar import ContinuousLunarReference
from ._eclipse_interval import RationalInterval as I
from ._eclipse_interval_roots import EnclosureUnavailable
from ._eclipse_spk_bounds import _chebyshev, _raw_seconds
from .constants import C_KM_PER_DAY


@dataclass(frozen=True, slots=True)
class LunarReferenceAccelerationBounds:
    """Absolute component accelerations in km per TT day squared."""

    sun: tuple[F, F, F]
    moon: tuple[F, F, F]
    domain: I
    sun_distance_lower_km: F
    clock_second_derivative_abs_per_day: F
    exact_reference_model_only: bool = True
    serving_evaluator_enclosed: bool = False


def bound_lunar_reference_accelerations(model: ContinuousLunarReference):
    """Bound accelerations over the complete frozen reception/emission domain.

    With TDB u=t+delta(u), u''=delta''(u)*(u')^3. Writing
    a=86400*M1, the global bound on delta'' is
    |K|/86400*a^2*((1+|EB|)^2+|EB|). The norm identity yields
    |(|v|)''| <= |v'|^2/|v|+|v''|. The whole Sun-delay map must
    stay inside the frozen horizon; no stop branch or fixed-point assumption
    replaces the reference's explicitly finite ten iterations.
    """
    if not isinstance(model, ContinuousLunarReference):
        raise TypeError('continuous lunar reference required')
    bits = model.precision_bits

    def upper(value):
        return I.point(value).quantize_outward(bits).hi

    def norm_upper(vector):
        return I.point(sum((x*x for x in vector), F(0))).sqrt(bits).hi

    horizon = I(model.tt_offset_days.lo-model.max_light_delay_days, model.tt_offset_days.hi)
    clock = clock_source.bound_continuous_reference_tdb(model.tt_anchor_jd, horizon, precision_bits=bits)
    reception = clock_source.bound_continuous_reference_tdb(
        model.tt_anchor_jd, model.tt_offset_days, precision_bits=bits)
    g = clock.derivative_tdb_per_tt.magnitude
    k, eb, m1 = (abs(F.from_float(value)) for value in (
        clock_source._NAIF_DELTET_K_SECONDS, clock_source._NAIF_DELTET_EB,
        clock_source._NAIF_DELTET_M1_RADIANS_PER_SECOND))
    g2 = upper(k/86400*(86400*m1)**2*((1+eb)**2+eb)*g**3)
    records = {(record.center, record.target): record for record in model.records}

    def route(pair):
        if pair not in records:
            raise EnclosureUnavailable('acceleration route record unavailable')
        record = records[pair]
        conversion = clock if pair == (0, 10) else reception
        seconds = _raw_seconds(model.tt_anchor_jd, conversion.tdb_offset_days)
        length = record.record_length_seconds
        if length <= 0 or seconds.lo <= record.record_start_seconds or seconds.hi >= record.record_start_seconds+length:
            raise EnclosureUnavailable('acceleration horizon leaves frozen record')
        x = 2*(seconds-record.record_start_seconds)/length-1
        position = tuple(_chebyshev(axis, x) for axis in record.coefficients)
        scale = 2*86400/length
        velocity, acceleration = [], []
        for coefficients in record.coefficients:
            first = sum((n*n*abs(c) for n, c in enumerate(coefficients)), F(0))*scale
            second = sum((F(n*n*(n*n-1), 3)*abs(c) for n, c in enumerate(coefficients)), F(0))*scale**2
            velocity.append(upper(first*g))
            acceleration.append(upper(second*g*g+first*g2))
        return position, tuple(velocity), tuple(acceleration)

    sp, sv, sa = route((0, 10))
    ep, ev, ea = route((0, 3))
    lp, lv, la = route((3, 399))
    _, mv, ma = route((3, 301))
    earth = tuple(e+leg for e, leg in zip(ep, lp))
    relative = tuple(s-e for s, e in zip(sp, earth))
    distance = sum((x.square() for x in relative), I.point(0)).sqrt(bits)
    speed = F.from_float(C_KM_PER_DAY)
    if distance.lo <= 0 or distance.hi/speed > model.max_light_delay_days:
        raise EnclosureUnavailable('Sun-delay horizon closure not proved for accelerations')
    earth_v = tuple(upper(e+leg) for e, leg in zip(ev, lv))
    earth_a = tuple(upper(e+leg) for e, leg in zip(ea, la))
    velocity = tuple(upper(s+e) for s, e in zip(sv, earth_v))
    acceleration = tuple(upper(s+e) for s, e in zip(sa, earth_a))
    for _ in range(10):
        v, a = norm_upper(velocity), norm_upper(acceleration)
        delay_rate = upper(v/speed)
        delay_accel = upper((v*v/distance.lo+a)/speed)
        velocity = tuple(upper(s*(1+delay_rate)+e) for s, e in zip(sv, earth_v))
        acceleration = tuple(upper(s*(1+delay_rate)**2+v*delay_accel+e)
                             for s, v, e in zip(sa, sv, earth_a))
    moon_acceleration = tuple(upper(m+leg) for m, leg in zip(ma, la))
    return LunarReferenceAccelerationBounds(acceleration, moon_acceleration, model.tt_offset_days,
                                            distance.lo, g2)
