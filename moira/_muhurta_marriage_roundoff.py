"""Coefficient-derived guards under an explicit binary64 arithmetic model.

These bounds are conditional on RN arithmetic, gradual underflow, no overflow,
and transcendental/remainder errors <=4 ulps. This is an arithmetic assumption,
not a claim that every platform's C library has been formally verified.
Guards are constant parameters on each full search cell, not sampled errors.
"""
from math import ceil,ulp,tau

from ._muhurta_marriage_enclosure import Interval as I,PI,TAU

ARITHMETIC_MODEL='binary64_RN_gradual_underflow_libm_4ulp.v1'


def gamma(n):
    u=I.point(2.**-53)
    return n*u/(1-n*u)


def norm_polynomial(coefficients,radius):
    return sum((I.point(c.magnitude if isinstance(c,I) else abs(c))*I.point(radius)**i
                for i,c in enumerate(coefficients)),I.point(0.))


def nutation_errors(arguments,tables,j0_counts):
    """Horner, phase, row, sequential-sum and angular-unit guards.

    32 bounds every fundamental-argument Horner/unit conversion schedule;
    phase construction has <=28 multiply/add operations for fourteen terms.
    The row and final-sum counts are derived from the actual loaded tables.
    """
    sizes=tuple(norm_polynomial(p,1.02) for p in arguments)
    argument_errors=[]
    for j,size in enumerate(sizes):
        error=gamma(32)*size
        if j>=5:
            turns=ceil(size.hi/tau)+1
            error=error+turns*(I.point(tau)-TAU).magnitude+8*ulp(tau)
        argument_errors.append(error)
    result=[]
    scale=PI/648000/1000000
    for rows,j0 in zip(tables,j0_counts):
        error=amplitude_sum=I.point(0.)
        for index,(a,b,*multipliers) in enumerate(rows):
            amplitude=I.point(abs(a))+abs(b)
            phase_size=sum((abs(n)*size for n,size in zip(multipliers,sizes)),I.point(0.))
            phase_error=sum((abs(n)*e for n,e in zip(multipliers,argument_errors)),I.point(0.))+gamma(28)*phase_size
            multiplier=1.02 if index>=j0 else 1.
            error=error+amplitude*(phase_error+8*ulp(1.)+gamma(8))*multiplier
            amplitude_sum=amplitude_sum+amplitude*multiplier
        error=error+gamma(len(rows)*2+16)*amplitude_sum
        result.append((error*scale).hi)
    return tuple(result)


def tdb_serving_error(tt,k,m0,m1,eb):
    """Implicit reference versus every successful (at least two step) call."""
    phase_size=I.point(abs(m0))+abs(m1)*(tt-2451545.).magnitude*86400
    turns=ceil(phase_size.hi/tau)+1
    phase_error=gamma(16)*phase_size+turns*(I.point(tau)-TAU).magnitude+8*ulp(tau)
    periodic_error=abs(k)*((1+abs(eb))*phase_error+8*ulp(1.)+gamma(16))
    # A full ulp also covers allowed fsum double-rounding; it is twice the
    # correctly rounded single-add bound 2^-32 day in this modern domain.
    epsilon=I.point(ulp(tt.magnitude))+periodic_error/86400
    q=I.point(abs(k*m1))*(1+abs(eb))
    return (q.square()*abs(k)/86400+epsilon/(1-q)).hi
