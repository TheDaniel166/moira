"""Differentiated real reference for Moira's FW/series orientation policy.

The FW polynomials and rotation objects follow IERS TN36 chapter 5. The
nutation terms and fundamental-argument coefficients are frozen from Moira's
current policy; in particular its linear p_A expression is retained here.
IERS equation 5.44 gives a different p_A polynomial. This module does not
silently repair that policy discrepancy or claim exact IAU conformance.
Unwrapped arguments define continuous reference trigonometric functions;
the rounded/modulo serving schedule needs its separate error enclosure.
"""
from dataclasses import dataclass, field
from fractions import Fraction as F
import hashlib
import struct

from . import _eclipse_interval_jets as j
from . import nutation_2000a as nutation_source
from ._eclipse_interval import RationalInterval as I
from ._eclipse_interval_roots import EnclosureUnavailable
from .constants import ARCSEC2RAD, DEG2RAD
from ._eclipse_inverse_trig import atan_enclosure
from ._eclipse_time_convergence import _ulp_upper


_EPS = (84381.406,-46.836769,-0.0001831,0.00200340,-0.000000576,-0.0000000434)
_DELAUNAY = (
    (485868.249036,1717915923.2178,31.8792,0.051635,-0.00024470),
    (1287104.793048,129596581.0481,-0.5532,0.000136,-0.00001149),
    (335779.526232,1739527262.8478,-12.7512,-0.001037,0.00000417),
    (1072260.703692,1602961601.2090,-6.3706,0.006593,-0.00003169),
    (450160.398036,-6962890.5431,7.4722,0.007702,-0.00005939),
)
_PLANETARY = ((4.402608842,2608.7903141574),(3.176146697,1021.3285546211),
    (1.753470314,628.3075849991),(6.203480913,334.0612426700),
    (0.599546497,52.9690962641),(0.874016757,21.3299104960),
    (5.481293872,7.4781598567),(5.311886287,3.8133035638),
    (0.02438175,0.00000538691))


@dataclass(frozen=True, slots=True)
class FrozenOrientationSeries:
    """Frozen current-policy nutation tables, independent of later caches."""

    longitude: tuple[tuple,...] = field(repr=False)
    obliquity: tuple[tuple,...] = field(repr=False)
    longitude_j0: int
    obliquity_j0: int
    sha256: str
    policy: str = 'current_moira_fundamental_arguments_unwrapped_real_reference'


def freeze_orientation_series():
    """Copy and hash every coefficient and integral argument multiplier."""
    ls,pl = nutation_source._ensure_tables_loaded()
    tables = tuple(tuple(tuple(row) for row in table) for table in (ls,pl))
    digest = hashlib.sha256(b'moira-stage3-frozen-orientation-series-v1\0')
    for table in tables:
        for row in table:
            if len(row)!=16 or any(type(x) is not int for x in row[2:]):
                raise EnclosureUnavailable('fourteen integral nutation arguments required')
            digest.update(struct.pack('<2d14i',*row))
    return FrozenOrientationSeries(*tables,nutation_source._LS_J0_COUNT,
                                    nutation_source._PL_J0_COUNT,digest.hexdigest())


def fundamental_argument_jets(t):
    """Lift the current policy's fourteen unwrapped polynomials to jets."""
    return tuple(j.scale(j.polynomial(t,coefficients),nutation_source._ARCSEC)
                 for coefficients in _DELAUNAY)+tuple(j.polynomial(t,row) for row in _PLANETARY)


def bound_nutation_reference(series: FrozenOrientationSeries, t):
    """Enclose radians and both derivatives by differentiating every term."""
    arguments = fundamental_argument_jets(t)
    result = []
    # This is the current source's microarcsecond-to-degree conversion,
    # followed by its degree-to-radian constant, interpreted as exact values.
    factor = F.from_float(1e-6/3600.0)*F.from_float(DEG2RAD)
    for table,split in ((series.longitude,series.longitude_j0),
                         (series.obliquity,series.obliquity_j0)):
        total = j.constant(0)
        for index,row in enumerate(table):
            argument = j.constant(0)
            for multiplier,base in zip(row[2:],arguments):
                if multiplier:
                    argument = j.add(argument,j.scale(base,multiplier))
            sine,cosine = j.sin_cos(argument)
            term = j.add(j.scale(sine,row[0]),j.scale(cosine,row[1]))
            total = j.add(total,j.mul(t,term) if index>=split else term)
        result.append(j.scale(total,factor))
    return tuple(result)


def bound_celestial_orientation(series: FrozenOrientationSeries, anchor: float, domain: I):
    """Return the current-policy real N*P matrix jets on the FW branch."""
    t = j.scale(j.add(j.variable(domain),j.constant(F.from_float(anchor)-2451545)),F(1,36525))
    if t[0].lo < -50 or t[0].hi>50:
        raise EnclosureUnavailable('FW reference requires |T|<=50 centuries')
    eps = j.scale(j.polynomial(t,_EPS),ARCSEC2RAD)
    gamma = j.scale(j.polynomial(t,(-.052928,10.556378,.4932044,-.00031238,-.000002788,.0000000260)),ARCSEC2RAD)
    phi = j.scale(j.polynomial(t,(84381.412819,-46.811016,.0511268,.00053289,-.000000440,-.0000000176)),ARCSEC2RAD)
    psi = j.scale(j.polynomial(t,(-.041775,5038.481484,1.5584175,-.00018522,-.000026452,-.0000000148)),ARCSEC2RAD)
    precession = j.matrix_product(j.rotation_x(j.neg(eps)),j.matrix_product(j.rotation_z(j.neg(psi)),
        j.matrix_product(j.rotation_x(phi),j.rotation_z(gamma))))
    dpsi,deps = bound_nutation_reference(series,t)
    nutation = j.matrix_product(j.rotation_x(j.neg(j.add(eps,deps))),
        j.matrix_product(j.rotation_z(j.neg(dpsi)),j.rotation_x(eps)))
    return j.matrix_product(nutation,precession),dpsi,eps


def taylor_celestial_orientation(point_matrix, point_offset, domain, curvature_matrix):
    """Enclose a smooth matrix from a point jet and whole-domain curvature."""
    h = domain-point_offset
    return tuple(tuple((j.q(value[0]+h*value[1]+h.square()*bound[2]/2),
                        j.q(value[1]+h*bound[2]),bound[2])
                       for value,bound in zip(row,bounds))
                 for row,bounds in zip(point_matrix,curvature_matrix))


def serving_nutation_error_radians(series: FrozenOrientationSeries, anchor: float, domain: I):
    """Bound current Python/native series rounding relative to the real lift.

    With u=2**-52, gamma_n=n*u/(1-n*u) bounds a sequence of n normal
    rounded operations. 64 operations cover each fundamental polynomial,
    conversion and wrap; 64 more cover a fourteen-argument phase sum.
    Sine/cosine are assumed finite, unit-range and within one ulp. FMA and
    alternative accumulation groupings are covered by the absolute sums.
    The represented tau's period error is included for every planetary wrap.
    Tables, source, powers, RN/gradual arithmetic and libm remain premises.
    """
    t = ((I.point(anchor)+domain-2451545)/36525)
    if t.lo < -50 or t.hi>50:
        raise EnclosureUnavailable('nutation error bound outside FW policy domain')
    unit = F(1,2**52)

    def gamma(n):
        product = n*unit
        if product>=1:
            raise EnclosureUnavailable('rounding-operation budget invalid')
        return product/(1-product)

    terr = I.point(gamma(2)*t.magnitude+F(1,2**1020)).quantize_outward(128).hi
    radius = I.point(t.magnitude+terr).quantize_outward(128).hi
    tau = F.from_float(nutation_source.math.tau)
    true_tau = 8*atan_enclosure(I.point(1),precision_bits=160)
    tau_error = (I.point(tau)-true_tau).magnitude
    magnitudes,errors = [],[]
    for index,coefficients in enumerate((*_DELAUNAY,*_PLANETARY)):
        coefficients = tuple(F.from_float(value) for value in coefficients)
        absolute = sum((abs(c)*radius**power for power,c in enumerate(coefficients)),F(0))
        derivative = sum((power*abs(c)*radius**(power-1)
                          for power,c in enumerate(coefficients) if power),F(0))
        error = gamma(64)*absolute+derivative*terr+F(1,2**1020)
        if index<5:
            factor = F.from_float(nutation_source._ARCSEC)
            absolute *= abs(factor)
            error = error*abs(factor)+gamma(2)*absolute
        else:
            error += (absolute/tau+2)*tau_error+4*_ulp_upper(tau)
        magnitudes.append(I.point(absolute).quantize_outward(128).hi)
        errors.append(I.point(error).quantize_outward(128).hi)
    factor = abs(F.from_float(1e-6/3600.0)*F.from_float(DEG2RAD))
    result = []
    for table,split in ((series.longitude,series.longitude_j0),(series.obliquity,series.obliquity_j0)):
        total_error = absolute_sum = F(0)
        for index,row in enumerate(table):
            amplitude = abs(F.from_float(row[0]))+abs(F.from_float(row[1]))
            phase_error = sum((abs(n)*e for n,e in zip(row[2:],errors)),F(0))
            phase_size = sum((abs(n)*m for n,m in zip(row[2:],magnitudes)),F(0))
            phase_error += gamma(64)*phase_size
            weight = F(1) if index<split else radius
            total_error += weight*amplitude*(phase_error+unit)
            if index>=split:
                total_error += terr*amplitude
            absolute_sum += weight*amplitude
        total_error += gamma(6*len(table)+32)*absolute_sum+F(1,2**1020)
        result.append(I.point((total_error+gamma(2)*absolute_sum)*factor).quantize_outward(128).hi)
    return tuple(result)


def taylor_nutation_bounds(series, anchor, domain, point_offset, point, whole, *, error_radians=None):
    """Translate reference nutation jets and add the derived serving error."""
    from ._eclipse_nutation_amplitudes import ConditionalNutationAmplitudeBounds
    h = domain-point_offset
    errors = serving_nutation_error_radians(series,anchor,domain) if error_radians is None else error_radians
    if len(errors)!=2 or any(error<0 for error in errors):
        raise ValueError('two nonnegative whole-domain nutation error bounds required')
    values = tuple((value[0]+h*value[1]+h.square()*bound[2]/2+I(-error,error))
                   /F.from_float(DEG2RAD) for value,bound,error in zip(point,whole,errors))
    return ConditionalNutationAmplitudeBounds(anchor,domain,values[0],values[1],
        len(series.longitude),len(series.obliquity),series.sha256)
