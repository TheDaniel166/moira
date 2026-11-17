"""Derived native solar-radius error around the continuous Stage 3 model.

The capsule separates native record/clock/light-time errors, UT1-to-TT
rounding, frame errors, line/ellipsoid conditioning and rounded cone algebra.
It is used only on the historical branch whose tables/calendar bounds are
checked here. No residual measured from a native sample sets an error bound.
Source/build/RN/libm and unchanged-resource premises remain explicit.
"""
from dataclasses import dataclass
from fractions import Fraction as F
from types import SimpleNamespace

from ._eclipse_interval import RationalInterval as I
from ._eclipse_interval_roots import EnclosureUnavailable
from ._eclipse_time_convergence import _ulp_upper
from ._eclipse_lunar_serving_error import _gamma,_up,_norm
from ._eclipse_orientation_reference import serving_nutation_error_radians
from ._eclipse_continuous_policy_clock import bound_continuous_policy_tt
from .constants import EARTH_RADIUS_KM,MOON_RADIUS_KM,SUN_RADIUS_KM,C_KM_PER_DAY,ARCSEC2RAD,DEG2RAD
from .eclipse import _WGS84_POLAR_RADIUS_KM
from . import julian


def sharp_native_record_error(state):
    """Bound each local Clenshaw residual with its own propagation weight.

    The exact b_k magnitude is sum_j |c_j| |U_(j-k)(x)|. Local rounding
    residuals delta_j propagate as U_(j-k)*delta_j. Backward evaluation uses
    already bounded E_(k+1),E_(k+2); it never multiplies the largest low-order
    coefficient by every higher-order propagation weight. Scalar/FMA orders,
    normalization error and slightly extended endpoint arguments are included.
    """
    from ._eclipse_correlated_emb import native_record_position_error
    coarse = native_record_position_error(state)  # validates DE metadata/domain
    length = F.from_float(state.record_length)
    xerror = (_ulp_upper(F(86400))+4*_ulp_upper(4*length))/(length/2)+_ulp_upper(F(4))
    epsilon = max(xerror,state.normalized_time.magnitude-1,F(0))
    rho = (I.point(1+epsilon)+I.point(2*epsilon+epsilon*epsilon).sqrt(128)).quantize_outward(128).hi
    results = []
    for raw,prior in zip(state.record_snapshot,coarse):
        c = tuple(F.from_float(value) for value in raw)
        n = len(c)-1
        u = tuple(_up((k+1)*rho**k) for k in range(n+1))
        magnitude = [F(0)]*(n+3)
        errors = [F(0)]*(n+3)
        residuals = [F(0)]*(n+3)
        for k in range(1,n+1):
            magnitude[k] = _up(sum((abs(c[j])*u[j-k] for j in range(k,n+1)),F(0)))
        for k in range(n,0,-1):
            residuals[k] = _up(_gamma(6)*(abs(c[k])+2*(1+epsilon)*(magnitude[k+1]+errors[k+1])
                                        +magnitude[k+2]+errors[k+2])+F(1,2**1000))
            errors[k] = _up(sum((u[j-k]*residuals[j] for j in range(k,n+1)),F(0)))
        assembly = ((1+epsilon)*errors[1]+errors[2]
            +_gamma(6)*(abs(c[0])+(1+epsilon)*(magnitude[1]+errors[1])+magnitude[2]+errors[2]))
        derivative = sum((k*k*abs(value)*rho**max(0,k-1) for k,value in enumerate(c)),F(0))
        results.append(min(prior,_up(assembly+derivative*xerror+F(1,2**1000))))
    return tuple(results)


@dataclass(frozen=True, slots=True)
class SolarRadiusErrorScope:
    """Uniform ray/frame errors and the bounds needed by the radius capsule."""

    domain: I
    sun_error_km: F
    moon_error_km: F
    moon_norm_upper_km: F
    source_distance_lower_km: F
    source_distance_upper_km: F
    frame_element_error: F
    ut1_to_tt_rounding_error_days: F
    comparison_ut1_halo_days: F
    comparison_pole_error: F
    direct_split_totality_under_premises: bool = True
    physical_accuracy_certified: bool = False


def derive_solar_radius_error_scope(reference,native_scope):
    """Derive finite ray/frame errors over the entire admitted request.

    This initial capsule admits the HPIERS branch away from calendar-year
    boundaries. Other clock branches retain the original native enclosures.
    The source's finite ten-update and early-stop comparison includes record
    jumps, as in the independently tested lunar error derivation.
    """
    if reference.clock.branch!='historical_hpiers':
        raise EnclosureUnavailable('solar radius capsule requires historical HPIERS clock')
    absolute = I.point(reference.ut1_anchor_jd)+reference.domain
    lo,hi = absolute.to_float_bounds()
    year = julian.calendar_from_jd(lo)[0]
    if year!=julian.calendar_from_jd(hi)[0] or not -15000<year<15000:
        raise EnclosureUnavailable('solar radius capsule crosses a calendar branch')
    start,end = map(lambda y:F.from_float(julian.julian_day(y,1,1)),(year,year+1))
    if absolute.lo<=start+2 or absolute.hi>=end-2:
        raise EnclosureUnavailable('solar radius capsule too close to year boundary')
    if reference.polar_rows:
        mjd = absolute-F(4800001,2)
        if not (mjd.hi<F.from_float(reference.polar_rows[0][0])
                or mjd.lo>F.from_float(reference.polar_rows[-1][0])):
            raise EnclosureUnavailable('solar radius capsule requires a clamped polar branch')
    rows = reference.clock.hpiers_rows
    slopes = [abs(F.from_float(v1)-F.from_float(v0))/(F.from_float(x1)-F.from_float(x0))
              for (x0,v0),(x1,v1) in zip(rows,rows[1:])]
    if min(F.from_float(b)-F.from_float(a) for (a,_),(b,_) in zip(rows,rows[1:]))<F(1,100):
        raise EnclosureUnavailable('historical table conditioning outside radius proof')
    century = (abs(F(year)-F.from_float(julian._TIDAL_REF_EPOCH))+2)/100
    coefficient = abs(F.from_float(julian._TIDAL_CONVERSION)
        *(F.from_float(reference.clock.tidal_target)-F.from_float(julian._TIDAL_NDOT_HPIERS)))
    year_error = _gamma(8)*(abs(year)+2)
    dt_magnitude = max(abs(F.from_float(v)) for _,v in rows)+coefficient*century*century
    seconds_error = year_error*(max(slopes)+2*coefficient*century/100)+_gamma(64)*(dt_magnitude+1)
    epoch_magnitude = (absolute+I(-1,1)).magnitude
    time_error = _up(seconds_error/86400+_ulp_upper(dt_magnitude/86400)+2*_ulp_upper(epoch_magnitude))

    errors,velocities,magnitudes,jumps = {},{},{},{}
    for route in native_scope.routes:
        records = sorted((r for r in native_scope.model.records if r.pair==route.pair),key=lambda r:r.index)
        er,vr,mr = [],[],[]
        for record in records:
            day = float((record.midpoint_seconds/86400+2451545)//1)
            state = SimpleNamespace(record_init=route.init,record_length=route.length,
                record_count=route.count,jd_tdb=day,normalized_time=I(-1-F(1,2**40),1+F(1,2**40)),
                record_snapshot=tuple(tuple(float(c) for c in axis) for axis in record.coefficients))
            er.append(sharp_native_record_error(state))
            vr.append(tuple(sum((n*n*abs(c) for n,c in enumerate(axis)),F(0))*86400/record.radius_seconds
                            for axis in record.coefficients))
            mr.append(tuple(sum(map(abs,axis),F(0)) for axis in record.coefficients))
        jump = [F(0)]*3
        for before,after in zip(records,records[1:]):
            if after.index!=before.index+1:
                raise EnclosureUnavailable('solar tube copied-record gap')
            for k in range(3):
                jump[k] += abs(sum(before.coefficients[k],F(0))
                    -sum((c*(-1)**n for n,c in enumerate(after.coefficients[k])),F(0)))
        pair = route.pair
        velocities[pair] = tuple(max(row[k] for row in vr) for k in range(3))
        magnitudes[pair] = tuple(max(row[k] for row in mr) for k in range(3))
        jumps[pair] = sum(jump,F(0))
        # A unique copied record over the padded complete horizon rules out
        # native index disagreement. Only actual multi-record routes need
        # the extra possible endpoint-selection displacement.
        selection_seconds = 2*max(r.radius_seconds for r in records)/2**40 if len(records)>1 else F(0)
        errors[pair] = tuple(_up(max(row[k] for row in er)+jump[k]
            +velocities[pair][k]*(native_scope.clock_error_seconds+selection_seconds)/86400) for k in range(3))
    emb,earth,moon,sun = (0,3),(3,399),(3,301),(0,10)
    observer = tuple(errors[emb][k]+errors[earth][k]
        +_ulp_upper(magnitudes[emb][k]+magnitudes[earth][k]) for k in range(3))
    sun_base = sum((errors[sun][k]+observer[k]+_ulp_upper(
        magnitudes[sun][k]+magnitudes[emb][k]+magnitudes[earth][k]) for k in range(3)),F(0))
    moon_base = sum((errors[emb][k]+errors[moon][k]+observer[k]
        +2*_ulp_upper(magnitudes[emb][k]+magnitudes[moon][k]+magnitudes[earth][k]) for k in range(3)),F(0))
    sun_norms = [_norm(tuple(a[0] for a in panel.whole.sun)) for panel in reference.panels]
    moon_norms = [_norm(tuple(a[0] for a in panel.whole.moon)) for panel in reference.panels]
    dsmin,dsmax = min(n.lo for n in sun_norms),max(n.hi for n in sun_norms)
    dmmax = max(n.hi for n in moon_norms)
    speed = F.from_float(C_KM_PER_DAY)
    clock_q = abs(F.from_float(julian._NAIF_DELTET_K_SECONDS)*F.from_float(julian._NAIF_DELTET_M1_RADIANS_PER_SECOND))*(1+abs(F.from_float(julian._NAIF_DELTET_EB)))

    def retard(base,velocity,jump,norm):
        velocity /= 1-clock_q
        q = velocity/speed
        upper = norm+velocity*native_scope.model.horizon_days+jump+base
        if q>=F(1,100) or upper/speed>=native_scope.model.horizon_days:
            raise EnclosureUnavailable('solar finite-delay capsule guard unproved')
        rounded_delay = _gamma(32)*upper/speed+_ulp_upper(upper/speed)
        error = (base+jump+velocity*rounded_delay)/(1-q)
        residual = F.from_float(1e-14)+_ulp_upper(2*upper/speed)
        return _up(error+velocity*(residual+2*error/speed+2*rounded_delay)/(1-q)+10*jump/(1-q))

    observer_speed = sum(velocities[emb],F(0))+sum(velocities[earth],F(0))
    es = retard(sun_base,sum(velocities[sun],F(0)),jumps[sun],
        dsmax+(observer_speed+sum(velocities[sun],F(0)))*time_error)
    em = retard(moon_base,sum(velocities[emb],F(0))+sum(velocities[moon],F(0)),jumps[emb]+jumps[moon],
        dmmax+(observer_speed+sum(velocities[emb],F(0))+sum(velocities[moon],F(0)))*time_error)
    # Match the represented native TT with the continuous clock at a nearby
    # UT1 coordinate tau. The monotone clock gives |tau-t|<=E_TT/min(TT').
    # Rays and TT-only orientation then share exactly the same TT. Shifting
    # UT1 alone is a common daily rotation; only the clamped polar tilt can
    # change an oblate ellipsoid's metric. The caller encloses the tau halo.
    clock_jet,_ = bound_continuous_policy_tt(reference.clock,reference.domain)
    if clock_jet[1].lo<=0:
        raise EnclosureUnavailable('monotone comparison clock unproved')
    comparison_halo = _up(time_error/clock_jet[1].lo)
    polar = reference.polar_rows
    if not polar:
        pole_error = F(0)
    else:
        row = polar[0] if (absolute-F(4800001,2)).hi<F.from_float(polar[0][0]) else polar[-1]
        pole_error = _up(7*(abs(F.from_float(row[1]))+abs(F.from_float(row[2])))
                         *F.from_float(ARCSEC2RAD)*comparison_halo)

    t = ((I.point(reference.ut1_anchor_jd)+reference.tt_domain-2451545)/36525).magnitude
    euler_coefficients = ((84381.406,-46.836769,-.0001831,.00200340,-.000000576,-.0000000434),
        (-.052928,10.556378,.4932044,-.00031238,-.000002788,.0000000260),
        (84381.412819,-46.811016,.0511268,.00053289,-.000000440,-.0000000176),
        (-.041775,5038.481484,1.5584175,-.00018522,-.000026452,-.0000000148))
    euler_absolute = sum((sum((abs(F.from_float(c))*t**n for n,c in enumerate(row)),F(0))
                          for row in euler_coefficients),F(0))*F.from_float(ARCSEC2RAD)
    dpsi_error,deps_error = serving_nutation_error_radians(reference.orientation_series,
        reference.ut1_anchor_jd,reference.tt_domain)
    excess = abs(F.from_float(.00273781191135448))
    baseline = (absolute-2451545).magnitude
    product_error = excess*_ulp_upper(baseline)+_ulp_upper(excess*(baseline+_ulp_upper(baseline)))
    phase_error = product_error+2*_ulp_upper(2+excess*(baseline+_ulp_upper(baseline)))
    radian_error = 2*reference.pi.hi*phase_error+_ulp_upper(F(360))*F.from_float(DEG2RAD)+_ulp_upper(F(7))
    radian_error += 360*(I.point(DEG2RAD)-reference.pi/180).magnitude
    np_rate = max(a[1].magnitude for row in reference.orientation_whole[0] for a in row)
    # TT-only frame rates are below one radian/day throughout this admitted
    # FW/table domain (the computed NP bound is checked). UT1 is unchanged.
    if np_rate>=F(1,10):
        raise EnclosureUnavailable('frame TT-rate conditioning outside radius proof')
    frame_error = _up(8*(radian_error+_gamma(64)*(1+euler_absolute)+dpsi_error+deps_error)
                      +_gamma(512))
    if frame_error>=F(1,10**8):
        raise EnclosureUnavailable('frame perturbation outside small-error proof')
    return SolarRadiusErrorScope(reference.domain,es,em,dmmax,dsmin-dmmax,dsmax+dmmax,
                                 frame_error,time_error,comparison_halo,pole_error)


def bound_solar_radius_serving_error(scope: SolarRadiusErrorScope,reference):
    """Bound the native radius error using the ellipsoid's conditioning.

    The nominal line's fundamental point is orthogonal to its unit axis.
    Q=I/a²+delta*kkᵀ therefore bounds B by delta*|P|. A discriminant lower
    bound gives a sharper |P| cover even in a mixed near-limb box. All native
    quadratic, root, normalization and cone-rounding errors are then included.
    """
    if reference.signed_radius is None:
        raise EnclosureUnavailable('no nominal radius on this source box')
    a,b,rs,rm = map(F.from_float,(EARTH_RADIUS_KM,_WGS84_POLAR_RADIUS_KM,SUN_RADIUS_KM,MOON_RADIUS_KM))
    amin,amax = 1/(a*a),1/(b*b)
    extra = amax-amin
    pmax = min(scope.moon_norm_upper_km,I.point((1+amax*max(F(0),-reference.axis_margin.lo))
                 /(amin-a*a*extra*extra)).sqrt(128).hi)
    dm = scope.moon_norm_upper_km
    edistance = scope.sun_error_km+scope.moon_error_km
    dmin,dmax = scope.source_distance_lower_km,scope.source_distance_upper_km
    if dmin<=edistance or dmin<=rs+rm:
        raise EnclosureUnavailable('source-direction radius conditioning unproved')
    body_axis_error = 2*edistance/(dmin-edistance)+_gamma(128)
    projection_error = scope.moon_error_km+(dm+scope.moon_error_km)*body_axis_error+_gamma(256)*dm
    plane_body_error = (scope.moon_error_km+dm*body_axis_error
        +projection_error*(1+body_axis_error)+_gamma(256)*(2*dm+projection_error))
    matrix = 3*scope.frame_element_error
    before_normalization = body_axis_error*(1+matrix)+matrix
    if before_normalization>=F(1,10):
        raise EnclosureUnavailable('native terrestrial axis normalization unproved')
    axis_error = 2*before_normalization/(1-before_normalization)+_gamma(256)
    plane_error = plane_body_error*(1+matrix)+matrix*pmax+_gamma(4096)*(pmax+plane_body_error)
    metric_error = extra*(2*scope.comparison_pole_error+scope.comparison_pole_error**2)
    ea = amax*(2*axis_error+axis_error*axis_error)+(_gamma(256)*amax+metric_error)*(1+axis_error)**2
    eb = amax*(plane_error*(1+axis_error)+pmax*axis_error)+(_gamma(256)*amax+metric_error)*(pmax+plane_error)*(1+axis_error)
    ec = (amax*(2*pmax*plane_error+plane_error*plane_error)
          +_gamma(256)*(amax*(pmax+plane_error)**2+1)+metric_error*(pmax+plane_error)**2)
    bmag,cmag = extra*pmax,max(F(1),amax*pmax*pmax-1)
    numerator_error = (2*bmag*eb+eb*eb+amax*ec+cmag*ea+ea*ec
        +_gamma(256)*((bmag+eb)**2+(amax+ea)*(cmag+ec)))
    denominator_error = 2*amax*ea+ea*ea+_gamma(128)*(amax+ea)**2
    if amin*amin<=denominator_error or amin<=ea:
        raise EnclosureUnavailable('native quadratic conditioning unproved')
    derror = (numerator_error+reference.axis_margin.magnitude*denominator_error)/(amin*amin-denominator_error)
    derror += _gamma(128)*(reference.axis_margin.magnitude+derror)
    center_error = (eb+bmag*ea/amin)/(amin-ea)+_gamma(128)*(bmag+eb)/(amin-ea)
    if reference.axis_margin.lo>derror:
        half_error = derror/(I.point(reference.axis_margin.lo).sqrt(128).lo
                            +I.point(reference.axis_margin.lo-derror).sqrt(128).lo)
    else:
        half_error = I.point(derror).sqrt(128).hi
    half_max = I.point(max(F(0),reference.axis_margin.hi)+derror).sqrt(128).hi
    parameter_error = center_error+half_error+_gamma(128)*(bmag/amin+half_max+center_error)
    leg_error = parameter_error+projection_error+_gamma(256)*(dm+2*a+projection_error)
    norm_error = edistance+_gamma(128)*(dmax+edistance)
    if dmin<=norm_error:
        raise EnclosureUnavailable('native source-distance normalization unproved')
    sine_hi = (rs-rm)/dmin
    sine_error = ((rs-rm)*norm_error/(dmin*(dmin-norm_error))
                  +_gamma(128)*(rs-rm)/(dmin-norm_error))
    if sine_hi+sine_error>=1:
        raise EnclosureUnavailable('native cone opening unproved')
    cosine_lo = I.point(1-(sine_hi+sine_error)**2).sqrt(128).lo
    cosine_error = (sine_hi+sine_error)*sine_error/cosine_lo+_gamma(256)/cosine_lo
    if cosine_error>=cosine_lo:
        raise EnclosureUnavailable('native cone cosine conditioning unproved')
    leg_hi = dm+2*a
    error = ((sine_hi*leg_error+leg_hi*sine_error+sine_error*leg_error)/(cosine_lo-cosine_error)
             +reference.signed_radius.magnitude*cosine_error/(cosine_lo-cosine_error))
    error += _gamma(8192)*(rm+(dm+2*a)*(sine_hi+sine_error)/(cosine_lo-cosine_error)
                           +reference.signed_radius.magnitude)
    return _up(error)
