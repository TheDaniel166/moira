"""Uniform serving-versus-real error tubes for the selected lunar policies.

The derivation keeps record-evaluation error, clock error, finite light-time
updates, early stopping, record jumps and rounded geometry separate. It uses
the copied DE metadata and exact coefficient words, not fitted residuals.
The theorem requires the stated RN/gradual, FMA, sqrt, hypot/fsum and one-ulp
inverse-trig premises and stable source/data. It is not physical accuracy.
"""
from dataclasses import dataclass
from fractions import Fraction as F
from types import SimpleNamespace

from ._eclipse_interval import RationalInterval as I
from ._eclipse_interval_roots import EnclosureUnavailable
from ._eclipse_correlated_emb import native_record_position_error
from ._eclipse_piecewise_vectors import enclose_piecewise_eclipse_vectors
from ._eclipse_time_convergence import _ulp_upper
from .constants import EARTH_RADIUS_KM,MOON_RADIUS_KM,SUN_RADIUS_KM,C_KM_PER_DAY


def _up(value):
    return I.point(value).quantize_outward(128).hi


def _gamma(n):
    nu = F(n,2**52)
    return nu/(1-nu)


def _norm(vector):
    return sum((value.square() for value in vector),I.point(0)).sqrt(128)


@dataclass(frozen=True, slots=True)
class LunarServingErrorTube:
    """Derived absolute vector/geometry errors over a complete TT domain."""

    tt_anchor_jd: float
    domain: I
    sun_vector_l2_error_km: F
    moon_vector_l2_error_km: F
    danjon_margin_errors_rad: tuple[F,...]
    cone_margin_errors_km: tuple[F,...]
    earth_radius_scale: float
    source_record_count: int
    sun_record_jump_l1_km: F
    light_time_contraction_bound: F
    finite_split_route_under_premises: bool
    geometry_guards_under_premises: bool
    unchanged_resources_and_numeric_contract_required: bool = True
    physical_accuracy_certified: bool = False


def derive_lunar_serving_error_tube(scope, *, earth_radius_scale=1.01):
    """Derive a uniform bound rather than calibrating one from test samples.

    |T_n'|<=n² bounds each polynomial's speed on its record. The native
    Clenshaw error includes normalization and allowed scalar/FMA schedules.
    Every possible intervening record jump is added explicitly. The source
    clock's error converts to position error through that speed bound.

    A Sun delay map has q=V_sun/C<1 between its source joins. A finite-iterate
    comparison obeys E_next<=base+q*E+V*norm_round/C+J. The geometric-series
    bound encloses all ten updates. A possible early stop adds the bounded
    residual's remaining finite tail and at most ten further source jumps;
    no exact fixed point at a discontinuous record join is presumed.
    """
    if type(earth_radius_scale) is bool or not 0<float(earth_radius_scale)<100:
        raise ValueError('positive finite bounded Earth scale required')
    speed = F.from_float(C_KM_PER_DAY)
    errors,velocities,magnitudes,jumps = {},{},{},{}
    routes = {route.pair:route for route in scope.routes}
    for pair,route in routes.items():
        records = sorted((record for record in scope.model.records if record.pair==pair),key=lambda r:r.index)
        if not records:
            raise EnclosureUnavailable('missing copied tube route')
        error_rows,velocity_rows,magnitude_rows = [],[],[]
        for record in records:
            # For integral DE metadata the normalization ulp bound is <2^-40;
            # this slightly enlarged argument also covers endpoint overshoot.
            day = float((record.midpoint_seconds/86400+2451545)//1)
            state = SimpleNamespace(record_init=route.init,record_length=route.length,
                record_count=route.count,jd_tdb=day,normalized_time=I(-1-F(1,2**40),1+F(1,2**40)),
                record_snapshot=tuple(tuple(float(c) for c in axis) for axis in record.coefficients))
            error_rows.append(native_record_position_error(state))
            velocity_rows.append(tuple(sum((n*n*abs(c) for n,c in enumerate(axis)),F(0))*86400/record.radius_seconds
                                       for axis in record.coefficients))
            magnitude_rows.append(tuple(sum(map(abs,axis),F(0)) for axis in record.coefficients))
        jump = [F(0)]*3
        for before,after in zip(records,records[1:]):
            if after.index!=before.index+1:
                raise EnclosureUnavailable('tube record set has a gap')
            for axis in range(3):
                left = sum(before.coefficients[axis],F(0))
                right = sum((c*(-1)**n for n,c in enumerate(after.coefficients[axis])),F(0))
                jump[axis] += abs(left-right)
        velocities[pair] = tuple(_up(max(row[k] for row in velocity_rows)) for k in range(3))
        magnitudes[pair] = tuple(max(row[k] for row in magnitude_rows) for k in range(3))
        jumps[pair] = tuple(jump)
        errors[pair] = tuple(_up(max(row[k] for row in error_rows)
            +velocities[pair][k]*(scope.clock_error_seconds
                +2*max(record.radius_seconds for record in records)/2**40)/86400+jump[k]) for k in range(3))

    emb,earth_leg,moon_leg,solar = (0,3),(3,399),(3,301),(0,10)
    earth_errors = tuple(_up(errors[emb][k]+errors[earth_leg][k]
        +_ulp_upper(magnitudes[emb][k]+magnitudes[earth_leg][k])) for k in range(3))
    moon_errors = tuple(_up(errors[moon_leg][k]+errors[earth_leg][k]
        +_ulp_upper(magnitudes[moon_leg][k]+magnitudes[earth_leg][k])) for k in range(3))
    base = sum((errors[solar][k]+earth_errors[k]+_ulp_upper(
        magnitudes[solar][k]+magnitudes[emb][k]+magnitudes[earth_leg][k]) for k in range(3)),F(0))
    vectors = enclose_piecewise_eclipse_vectors(scope.model,scope.requested_domain)
    sun,moon = tuple(a[0] for a in vectors.sun),tuple(a[0] for a in vectors.moon)
    ds,dm = _norm(sun),_norm(moon)
    if ds.lo<=0 or dm.lo<=0:
        raise EnclosureUnavailable('positive reference source norms unproved')
    # dTDB/dTT lies within this source clock's globally derived contraction.
    from .julian import _NAIF_DELTET_K_SECONDS,_NAIF_DELTET_EB,_NAIF_DELTET_M1_RADIANS_PER_SECOND
    clock_q = abs(F.from_float(_NAIF_DELTET_K_SECONDS)*F.from_float(_NAIF_DELTET_M1_RADIANS_PER_SECOND))*(1+abs(F.from_float(_NAIF_DELTET_EB)))
    velocity = sum(velocities[solar],F(0))/(1-clock_q)
    q = velocity/speed
    if q>=F(1,100):
        raise EnclosureUnavailable('Sun delay contraction outside tube proof')
    jump = sum(jumps[solar],F(0))
    norm_upper = ds.hi+velocity*scope.model.horizon_days+jump+base
    if norm_upper/speed>=scope.model.horizon_days:
        raise EnclosureUnavailable('native Sun delays leave the frozen horizon')
    norm_round = _gamma(32)*norm_upper
    delay_round = norm_round/speed+_ulp_upper(norm_upper/speed)
    iterate_error = (base+jump+velocity*delay_round)/(1-q)
    residual = F.from_float(1e-14)+_ulp_upper(2*norm_upper/speed)
    sun_error = _up(iterate_error+velocity*(residual+2*iterate_error/speed+2*delay_round)/(1-q)
                    +10*jump/(1-q))
    moon_error = _up(sum(moon_errors,F(0)))
    # The finite-vector norm's relative rounding bound is <1/16. Then
    # norm >= peak/2 and norm <= sqrt(3)*peak*(1+gamma)<2*peak pointwise.
    if _gamma(32)>=F(1,16):
        raise EnclosureUnavailable('guarded norm arithmetic premise failed')
    re,rs,rm = map(F.from_float,(EARTH_RADIUS_KM,SUN_RADIUS_KM,MOON_RADIUS_KM))
    effective = F.from_float(EARTH_RADIUS_KM*float(earth_radius_scale))
    es = sun_error+_gamma(4)*(ds.hi+sun_error)
    em = moon_error+_gamma(4)*(dm.hi+moon_error)
    if ds.lo-es<=rs+max(re,effective) or dm.lo-em<=re+rm:
        raise EnclosureUnavailable('tube disjoint-source guards unproved')
    axis_error = (sun_error+es)/(ds.lo-es)+_gamma(8)
    coordinate_error = _up(moon_error*(1+axis_error)+dm.hi*axis_error
        +_gamma(128)*(dm.hi+moon_error)*(1+axis_error))
    if dm.lo<=2*coordinate_error:
        raise EnclosureUnavailable('angular perturbation tube reaches its singularity')
    angle_error = 4*coordinate_error/(dm.lo-2*coordinate_error)+F(4,2**52)
    z = -sum((s*m for s,m in zip(sun,moon)),I.point(0))/ds
    if z.lo-coordinate_error<=effective+rm:
        raise EnclosureUnavailable('whole-Moon downstream tube guard unproved')

    def ratio(radius,distance,dist_error):
        minimum = distance.lo-dist_error
        upper = radius/minimum
        error = radius*dist_error/(distance.lo*minimum)+_gamma(4)*upper
        return upper,_up(error)

    def angular(radius,distance,dist_error):
        upper,error = ratio(radius,distance,dist_error)
        if upper+error>=1:
            raise EnclosureUnavailable('inverse-trig tube domain unproved')
        cosine = I.point(1-(upper+error)**2).sqrt(128).lo
        angle_upper = upper/cosine
        return angle_upper,_up(error/cosine+_ulp_upper(angle_upper))

    pm,epm = angular(re,dm,em)
    ss,ess = angular(rs,ds,es)
    ps,eps = angular(re,ds,es)
    alpha,ealpha = angular(rm,dm,em)
    beta_hi = F.from_float(1.01)*pm+ss+ps
    beta_error = F.from_float(1.01)*epm+ess+eps+_gamma(8)*beta_hi
    # A lower umbra is needed by every Danjon source return, including cases
    # where all three overlap margins are strictly negative.
    umb_lower = F.from_float(1.01)*re/(dm.hi+em)-ss+re/(ds.hi+es)-beta_error
    if umb_lower<=0:
        raise EnclosureUnavailable('positive Danjon umbra tube guard unproved')
    angular_error = _up(beta_error+ealpha+angle_error+_gamma(8)*(beta_hi+alpha+2))
    if beta_hi+alpha+angular_error>=3:
        raise EnclosureUnavailable('Danjon combined angular guard unproved')

    def cone_error(sign):
        numerator = rs+effective if sign==1 else rs-effective
        low,high = numerator/ds.hi,numerator/ds.lo
        _,sine_error = ratio(numerator,ds,es)
        sine_error += _gamma(4)*numerator/(ds.lo-es)
        if low-sine_error<=0 or high+sine_error>=1:
            raise EnclosureUnavailable('cone tube opening guard unproved')
        cosine_lower = I.point(1-(high+sine_error)**2).sqrt(128).lo
        cosine_error = (high+sine_error)*sine_error/cosine_lower+_gamma(16)/cosine_lower
        t_upper = dm.hi+effective/low
        t_error = (coordinate_error+effective*sine_error/(low*(low-sine_error))
                   +_gamma(16)*(dm.hi+coordinate_error+effective/(low-sine_error)))
        if sign==-1 and effective/high-dm.hi-t_error<=0:
            raise EnclosureUnavailable('positive umbral nappe tube guard unproved')
        return _up((high+sine_error)*t_error+t_upper*sine_error
            +(1+cosine_error)*coordinate_error+dm.hi*cosine_error
            +_gamma(16)*((high+sine_error)*(t_upper+t_error)
                         +(1+cosine_error)*(dm.hi+coordinate_error)+rm))

    pen_error,umb_error = cone_error(1),cone_error(-1)
    return LunarServingErrorTube(scope.model.tt_anchor_jd,scope.requested_domain,sun_error,moon_error,
        (angular_error,)*3,(pen_error,umb_error,umb_error),float(earth_radius_scale),
        len(scope.model.records),jump,_up(q),True,True)
