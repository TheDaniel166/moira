"""Correlated Earth-barycentre differences for bounded solar light time.

The retarded Moon contains EMB(emission)-EMB(reception). Independent boxes
lose this cancellation. On the same verified record the mean-value theorem
bounds that difference by a signed Chebyshev-velocity box times the bounded
clock displacement, plus independently derived native evaluation errors.
Actual barycentric additions/subtractions keep their own rounding errors.
This does not cross a record join or assert an arbitrary SPK normalization.
"""
from fractions import Fraction as F

from . import _eclipse_interval_jets as j
from ._eclipse_interval import RationalInterval as I
from ._eclipse_interval_roots import EnclosureUnavailable
from ._eclipse_time_convergence import _ulp_upper
from ._eclipse_native_spk_bounds import _rounded as r
from .julian import _NAIF_DELTET_K_SECONDS,_NAIF_DELTET_M1_RADIANS_PER_SECOND,_NAIF_DELTET_EB


def native_record_position_error(state):
    """Uniform native position error for integral-day DE type-2 arguments.

    Integral INIT/INTLEN, even length >= one day and <2**52 integer
    intermediates make the whole-day normalization exact. Remaining seconds
    and normalization errors are bounded by their ulps. For Clenshaw,
    |U_m(x)| <= (m+1)*rho**m, rho=1+e+sqrt(2e+e**2), on |x|<=1+e.
    The inhomogeneous rounding recurrence then gives E<=K*g*M/(1-K*g*b).
    This includes scalar/FMA expression schedules and the final assembly.
    The polynomial's derivative bounds the separate normalization error.
    RN/gradual arithmetic, correctly rounded FMA, matching source/record
    words and no unsafe reassociation remain required premises.
    """
    init,length,jd = map(F.from_float,(state.record_init,state.record_length,state.jd_tdb))
    if (init.denominator!=1 or length.denominator!=1 or jd.denominator!=1
            or length<86400 or int(length)%2 or abs(init)+state.record_count*length>=2**52
            or abs((jd-2451545)*86400-init)+4*length>=2**52):
        raise EnclosureUnavailable('correlated normalization proof requires integral DE metadata')
    radius = length/2
    seconds_error = _ulp_upper(F(86400))+4*_ulp_upper(4*length)
    x_error = seconds_error/radius+_ulp_upper(F(4))
    epsilon = max(x_error,state.normalized_time.magnitude-1,F(0))
    if epsilon>F(1,1000000):
        raise EnclosureUnavailable('normalized argument outside correlated-error domain')
    rho = (I.point(1+epsilon)+I.point(2*epsilon+epsilon*epsilon).sqrt(128)).quantize_outward(128).hi
    unit = F(1,2**52)
    gamma = 6*unit/(1-6*unit)
    errors = []
    for raw in state.record_snapshot:
        coefficients = tuple(F.from_float(value) for value in raw)
        degree = len(coefficients)-1
        if not 0<=degree<=256:
            raise EnclosureUnavailable('correlated coefficient budget exceeded')
        ub = tuple(I.point((m+1)*rho**m).quantize_outward(128).hi for m in range(degree+1))
        internal = max((sum((abs(coefficients[k])*ub[k-index]
                            for k in range(index,degree+1)),F(0))
                        for index in range(1,degree+1)),default=F(0))
        maximum_coefficient = max((abs(value) for value in coefficients[1:]),default=F(0))
        kernel = sum(ub,F(0))
        beta = 2*(1+epsilon)+1
        denominator = 1-kernel*gamma*beta
        if denominator<=0:
            raise EnclosureUnavailable('rounding recurrence contraction not proved')
        internal_error = kernel*gamma*(maximum_coefficient+beta*internal)/denominator
        final_error = ((2+epsilon)*internal_error
            +gamma*(abs(coefficients[0])+(2+epsilon)*(internal+internal_error)))
        derivative = sum((n*n*abs(value)*rho**max(0,n-1)
                          for n,value in enumerate(coefficients)),F(0))
        errors.append(I.point(final_error+derivative*x_error+F(1,2**1000)).quantize_outward(128).hi)
    return tuple(errors)


def _signed_record_velocity(state, seconds):
    length = F.from_float(state.record_length)
    start = F.from_float(state.record_init)+state.record_index*length
    x = ((seconds-start-length/2)/(length/2),I.point(86400/(length/2)),I.point(0))
    result = []
    for raw in state.record_snapshot:
        first,second = j.constant(0),j.constant(0)
        for coefficient in reversed(raw[1:]):
            first,second = j.add(j.sub(j.scale(j.mul(x,first),2),second),j.constant(coefficient)),first
        result.append(j.add(j.sub(j.mul(x,first),second),j.constant(raw[0]))[1])
    return tuple(result)


def correlated_emb_difference(reception,emission,delay_days: I,clock_error_seconds: F):
    """Enclose the native EMB difference, preserving the shared TT input."""
    if (reception.record_index!=emission.record_index
            or reception.record_init!=emission.record_init
            or reception.record_length!=emission.record_length
            or reception.record_snapshot!=emission.record_snapshot
            or reception.source.descriptor_start_second!=emission.source.descriptor_start_second
            or reception.source.descriptor_end_second!=emission.source.descriptor_end_second):
        raise EnclosureUnavailable('correlated EMB difference crosses a record/descriptor')
    before,after = reception.source.interval_seconds_tdb,emission.source.interval_seconds_tdb
    hull = I(min(before.lo,after.lo),max(before.hi,after.hi))
    velocity = _signed_record_velocity(reception,hull)
    k,m1,eb = map(lambda v:abs(F.from_float(v)),
                  (_NAIF_DELTET_K_SECONDS,_NAIF_DELTET_M1_RADIANS_PER_SECOND,_NAIF_DELTET_EB))
    contraction = k*m1*(1+eb)
    rate = I(1/(1+contraction),1/(1-contraction))
    clock_difference = -delay_days*rate+I(-2*clock_error_seconds/86400,2*clock_error_seconds/86400)
    error_before,error_after = native_record_position_error(reception),native_record_position_error(emission)
    return tuple((value*clock_difference+I(-left-right,left+right)).quantize_outward(128)
                 for value,left,right in zip(velocity,error_before,error_after))


def correlated_moon_initial(emb,moon_leg,earth_leg):
    """Cancel repeated native EMB values while retaining both addition errors."""
    result = []
    for e,m,leg in zip(emb,moon_leg,earth_leg):
        addition_error = _ulp_upper(e.magnitude+m.magnitude)+_ulp_upper(e.magnitude+leg.magnitude)
        result.append(r(m-leg+I(-addition_error,addition_error)))
    return tuple(result)


def correlated_moon_geocentric(reception,emission,moon_leg,earth_leg,delay_days,clock_error_seconds):
    """Bound the actual two barycentric sums and final subtraction."""
    emb_difference = correlated_emb_difference(reception,emission,delay_days,clock_error_seconds)
    result = []
    for delta,e0,e1,moon,earth in zip(emb_difference,reception.position_km,emission.position_km,moon_leg,earth_leg):
        addition_error = _ulp_upper(e1.magnitude+moon.magnitude)+_ulp_upper(e0.magnitude+earth.magnitude)
        result.append(r(delta+moon-earth+I(-addition_error,addition_error)))
    return tuple(result)
