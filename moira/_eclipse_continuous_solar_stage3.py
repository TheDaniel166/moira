"""Differentiated continuous solar paths for the frozen current-policy lift.

The raw DE polynomials, implicit TT/TDB clock, ten real reception-light-time
updates, current nutation/FW series, continuous source-clock interpolation,
true-circle Earth rotation and interpolated polar motion are explicit real
objects. Native rounding and modulo-period discrepancies are handled by the
separate represented-input cover, never by asserting native continuity.
Taylor translations use whole-panel curvature and preserve source joins.
"""
from dataclasses import dataclass
from fractions import Fraction as F
import bisect

from . import _eclipse_interval_jets as j
from ._eclipse_interval import RationalInterval as I
from ._eclipse_interval_roots import EnclosureUnavailable
from ._eclipse_inverse_trig import atan_enclosure
from ._eclipse_interval_elementary import sin_cos_enclosure
from ._eclipse_continuous_policy_clock import freeze_continuous_policy_clock,bound_continuous_policy_tt
from ._eclipse_clock_provider import bound_native_ut1_to_tt
from ._eclipse_piecewise_vectors import freeze_eclipse_records,enclose_piecewise_eclipse_vectors
from ._eclipse_orientation_reference import (freeze_orientation_series,bound_celestial_orientation,
                                            taylor_celestial_orientation)
from ._eclipse_polar_motion_bounds import _table_snapshot
from ._eclipse_solar_pole_reference import bound_solar_pole_reference
from ._eclipse_solar_coverage import cover_solar_central_path
from .constants import ARCSEC2RAD


@dataclass(frozen=True, slots=True)
class SolarReferencePanel:
    """A source-bounded TT panel and its one-sided vector jets."""

    domain: I
    whole: object
    midpoint: F
    point: object


@dataclass(frozen=True, slots=True)
class ContinuousSolarStage3Scope:
    """Frozen resources and explicit mathematical choices for one request."""

    ut1_anchor_jd: float
    domain: I
    tt_domain: I
    clock: object
    records: object
    panels: tuple[SolarReferencePanel,...]
    orientation_series: object
    orientation_whole: tuple
    orientation_midpoint: F
    orientation_point: tuple
    polar_rows: tuple
    polar_sha256: str
    pi: I
    exact_real_model_only: bool = True
    native_continuity_claimed: bool = False
    physical_accuracy_certified: bool = False


def prepare_continuous_solar_stage3(reader,anchor: float,domain: I, *, panel_count=16):
    """Freeze the explicit lift, including record and orientation derivatives."""
    if type(panel_count) is not int or not 1<=panel_count<=128:
        raise ValueError('finite panel count from 1 to 128 required')
    clock = freeze_continuous_policy_clock(reader,anchor,domain)
    tt,_ = bound_continuous_policy_tt(clock,domain)
    mapped = bound_native_ut1_to_tt(reader,anchor,domain)
    native_tt = I.point(mapped.bounds.anchor_jd)+mapped.bounds.output_offset_days-anchor
    if tt[0].lo<native_tt.lo or tt[0].hi>native_tt.hi:
        raise ArithmeticError('real policy clock escaped its native interval lift')
    padding = F(1,10**10)
    full = I(tt[0].lo-padding,tt[0].hi+padding)
    records = freeze_eclipse_records(reader,anchor,full)
    panels = []
    for index in range(panel_count):
        box = I(full.lo+full.width*index/panel_count,full.lo+full.width*(index+1)/panel_count)
        whole = enclose_piecewise_eclipse_vectors(records,box,retarded_moon=True)
        point = enclose_piecewise_eclipse_vectors(records,I.point(box.midpoint),retarded_moon=True)
        panels.append(SolarReferencePanel(box,whole,box.midpoint,point))
    series = freeze_orientation_series()
    whole = bound_celestial_orientation(series,anchor,full)
    middle = full.midpoint
    point = bound_celestial_orientation(series,anchor,I.point(middle))
    rows,_,polar_digest = _table_snapshot()
    return ContinuousSolarStage3Scope(float(anchor),domain,full,clock,records,tuple(panels),
        series,whole,middle,point,rows,polar_digest,4*atan_enclosure(I.point(1),precision_bits=160))


def _hull_jets(values):
    return tuple(I(min(v[k].lo for v in values),max(v[k].hi for v in values)) for k in range(3))


def _translate_jet(point,curvature,offset):
    return (j.q(point[0]+point[1]*offset+curvature*offset.square()/2),
            j.q(point[1]+curvature*offset),curvature)


def _chain(jet,clock):
    return jet[0],j.q(jet[1]*clock[1]),j.q(jet[2]*clock[1].square()+jet[1]*clock[2])


def _trig(a):
    """Use the global unit Lipschitz bound around a certified point value.

    This avoids repeated-doubling interval inflation at ancient unwrapped
    phases. Both trigonometric derivatives have magnitude at most one.
    """
    point = sin_cos_enclosure(I.point(a[0].midpoint),precision_bits=128)
    radius = a[0].width/2
    sine = j.q((point.sine+I(-radius,radius)).intersect(I(-1,1)))
    cosine = j.q((point.cosine+I(-radius,radius)).intersect(I(-1,1)))
    return ((sine,j.q(cosine*a[1]),j.q(-sine*a[1].square()+cosine*a[2])),
            (cosine,j.q(-sine*a[1]),j.q(-cosine*a[1].square()-sine*a[2])))


def _polar_jets(rows,anchor,domain):
    mjd = I.point(anchor)+domain-F(4800001,2)
    alternatives = []
    if not rows:
        return j.constant(0),j.constant(0)
    if mjd.lo<=F.from_float(rows[0][0]):
        alternatives.append((j.constant(rows[0][1]),j.constant(rows[0][2])))
    if mjd.hi>=F.from_float(rows[-1][0]):
        alternatives.append((j.constant(rows[-1][1]),j.constant(rows[-1][2])))
    mjds = tuple(row[0] for row in rows)
    first = max(0,bisect.bisect_left(mjds,mjd.lo)-1)
    last = min(len(rows)-1,bisect.bisect_right(mjds,mjd.hi))
    for left,right in zip(rows[first:last],rows[first+1:last+1]):
        if left[0]==right[0]:
            continue
        owned = mjd.intersect(I(left[0],right[0]))
        if owned is None:
            continue
        fraction = j.scale(j.sub(j.variable(owned),j.constant(left[0])),
                           1/(F.from_float(right[0])-F.from_float(left[0])))
        alternatives.append(tuple(j.add(j.constant(left[k]),j.scale(fraction,
            F.from_float(right[k])-F.from_float(left[k]))) for k in (1,2)))
    if not alternatives:
        raise EnclosureUnavailable('polar reference interpolation gap')
    return tuple(_hull_jets([item[k] for item in alternatives]) for k in range(2))


def _gast_reference(scope,domain,tt,dpsi,eps):
    ut = j.add(j.variable(domain),j.constant(scope.ut1_anchor_jd))
    t = j.scale(j.add(tt,j.constant(F.from_float(scope.ut1_anchor_jd)-2451545)),F(1,36525))
    # Whole integer turns are removed exactly from this continuous lift;
    # true 2*pi gives no artificial discontinuity at a represented tau seam.
    turns = j.add(j.sub(ut,j.constant(F.from_float(scope.ut1_anchor_jd)//1)),
        j.add(j.constant(.7790572732640),j.scale(j.sub(ut,j.constant(2451545)),.00273781191135448)))
    turns = j.sub(turns,j.constant(turns[0].midpoint//1))
    era = j.scale(turns,2*scope.pi)
    poly = j.polynomial(t,(.014506,4612.156534,1.3915817,-.00000044,-.000029956,-.0000000368))
    om = j.scale(j.polynomial(t,(450160.398036,-6962890.5431,7.4722,.007702)),ARCSEC2RAD)
    f = j.scale(j.polynomial(t,(335779.526232,1739527262.8478)),ARCSEC2RAD)
    d = j.scale(j.polynomial(t,(1072260.703692,1602961601.2090)),ARCSEC2RAD)
    base = j.scale(j.sub(f,d),2)
    arguments = (om,j.scale(om,2),j.add(base,j.scale(om,3)),j.add(base,om),
                 j.add(base,j.scale(om,2)),j.add(j.scale(f,2),j.scale(om,3)),
                 j.add(j.scale(f,2),om),j.scale(om,3))
    coefficients = (.00264096,.00006352,.00001175,.00001121,-.00000455,.00000202,.00000198,-.00000172)
    sine = tuple(_trig(argument)[0] for argument in arguments)
    complementary = j.constant(0)
    for coefficient,trig in zip(coefficients,sine):
        complementary = j.add(complementary,j.scale(trig,coefficient))
    complementary = j.add(complementary,j.scale(j.mul(t,sine[0]),-.00000087))
    equation = j.add(j.mul(dpsi,_trig(eps)[1]),j.scale(complementary,ARCSEC2RAD))
    return j.add(era,j.add(j.scale(poly,ARCSEC2RAD),equation))


def continuous_solar_stage3_provider(scope: ContinuousSolarStage3Scope, *, progress=None,jet_observer=None):
    """Return request-local value/derivative enclosures and evaluation counters."""
    vector_points = {index:{panel.midpoint:panel.point} for index,panel in enumerate(scope.panels)}
    orientation_points = {scope.orientation_midpoint:scope.orientation_point}
    stats = dict(calls=0,vector_points=len(scope.panels),orientation_points=1)

    def enclosure(domain):
        stats['calls'] += 1
        if progress is not None and stats['calls']%64==0:
            progress(dict(stats,current_width_seconds=float(domain.width*86400)))
        tt,clock_continuous = bound_continuous_policy_tt(scope.clock,domain)
        sun_parts,moon_parts = [],[]
        source_continuous = True
        for index,panel in enumerate(scope.panels):
            owned = tt[0].intersect(panel.domain)
            if owned is None:
                continue
            if not panel.whole.continuous_on_domain:
                vectors = enclose_piecewise_eclipse_vectors(scope.records,owned,retarded_moon=True)
                sun_parts.append(vectors.sun)
                moon_parts.append(vectors.moon)
                source_continuous &= vectors.continuous_on_domain
                continue
            cache = vector_points[index]
            near = min(cache,key=lambda point:abs(point-owned.midpoint))
            h = owned-near
            error = max(component[2].magnitude*h.magnitude**2/2
                        for ray in (panel.whole.sun,panel.whole.moon) for component in ray)
            if owned.width<F(2,86400) and error>F(1,10**6):
                near = owned.midpoint
                cache[near] = enclose_piecewise_eclipse_vectors(scope.records,I.point(near),retarded_moon=True)
                stats['vector_points'] += 1
                h = owned-near
            point = cache[near]
            sun_parts.append(tuple(_translate_jet(p,c[2],h) for p,c in zip(point.sun,panel.whole.sun)))
            moon_parts.append(tuple(_translate_jet(p,c[2],h) for p,c in zip(point.moon,panel.whole.moon)))
        sun = tuple(_chain(_hull_jets([part[k] for part in sun_parts]),tt) for k in range(3))
        moon = tuple(_chain(_hull_jets([part[k] for part in moon_parts]),tt) for k in range(3))
        near = min(orientation_points,key=lambda point:abs(point-tt[0].midpoint))
        if tt[0].width<F(1,86400) and abs(near-tt[0].midpoint)>F(30,86400):
            near = tt[0].midpoint
            orientation_points[near] = bound_celestial_orientation(scope.orientation_series,
                scope.ut1_anchor_jd,I.point(near))
            stats['orientation_points'] += 1
        point = orientation_points[near]
        matrix = taylor_celestial_orientation(point[0],near,tt[0],scope.orientation_whole[0])
        matrix = tuple(tuple(_chain(element,tt) for element in row) for row in matrix)
        dpsi = _chain(_translate_jet(point[1],scope.orientation_whole[1][2],tt[0]-near),tt)
        eps = _chain(_translate_jet(point[2],scope.orientation_whole[2][2],tt[0]-near),tt)
        gast = _gast_reference(scope,domain,tt,dpsi,eps)
        x,y = _polar_jets(scope.polar_rows,scope.ut1_anchor_jd,domain)
        sx,cx = j.sin_cos(j.scale(x,ARCSEC2RAD))
        sy,cy = j.sin_cos(j.scale(y,ARCSEC2RAD))
        zero = j.constant(0)
        polar = ((cx,zero,sx),(j.mul(sx,sy),cy,j.neg(j.mul(cx,sy))),
                 (j.neg(j.mul(sx,cy)),sy,j.mul(cx,cy)))
        transpose = tuple(tuple(polar[k][i] for k in range(3)) for i in range(3))
        gs,gc = _trig(gast)
        one = j.constant(1)
        spin = ((gc,gs,zero),(j.neg(gs),gc,zero),(zero,zero,one))
        rotation = j.matrix_product(transpose,j.matrix_product(spin,matrix))
        # Q in the ray frame needs only U^T*z, the third row of U. Common
        # rotation of both rays cancels exactly from its isotropic part.
        pole = rotation[2]
        return bound_solar_pole_reference(domain,sun,moon,pole,
            continuous_model=bool(clock_continuous and source_continuous),jet_observer=jet_observer)
    return enclosure,stats


def cover_continuous_solar_stage3(scope, *, tolerance=F(1,86400000),max_evaluations=8192,progress=None):
    """Prove roots/components and all complements for the declared real lift."""
    provider,stats = continuous_solar_stage3_provider(scope,progress=progress)
    result = cover_solar_central_path(scope.domain,provider,tolerance=tolerance,
        continuity_assumed=True,max_evaluations=max_evaluations)
    return result,stats
