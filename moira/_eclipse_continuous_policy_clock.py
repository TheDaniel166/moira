"""Continuous real lifts of the three native clock branches used in Stage 3.

Stored tables and constants are interpreted as exact represented values.
Historical linear HPIERS interpolation includes the reader's explicit tidal
translation; direct EOP uses its UT1 segments; future time uses the declared
boundary-conditioned quadratic scenario. Calendar/table joins are kept as
piecewise branches. This is distinct from rounded execution and physical
Delta-T uncertainty. Unsupported handoffs remain unavailable.
"""
from dataclasses import dataclass
from fractions import Fraction as F

from . import _eclipse_interval_jets as j
from . import julian
from . import delta_t_physical
from ._eclipse_interval import RationalInterval as I
from ._eclipse_interval_roots import EnclosureUnavailable
from ._eclipse_clock_provider import bound_native_ut1_to_tt
from ._eclipse_native_clock_bounds import _snapshot_sources


@dataclass(frozen=True, slots=True)
class ContinuousPolicyClock:
    """Frozen clock policy and exact interpolation rows on a UT1 domain."""

    anchor_jd: float
    domain: I
    branch: str
    hpiers_rows: tuple
    eop_segments: tuple
    tidal_target: float
    future_reference_year: float
    future_reference_seconds: float
    source_digests: tuple[str,...]


def freeze_continuous_policy_clock(reader,anchor: float,domain: I):
    """Admit only a whole-domain branch already enclosed by the native clock."""
    native = bound_native_ut1_to_tt(reader,anchor,domain)
    table,tdigest,edigest,_ = _snapshot_sources()
    if native.branch not in ('historical_hpiers','direct_eop','future_scenario'):
        raise EnclosureUnavailable('continuous policy clock branch unsupported: '+native.branch)
    data = julian.EOPRegistry._ensure_loaded()
    absolute = I.point(anchor)+domain
    segments = []
    if native.branch=='direct_eop':
        for mjd in native.bounds.possible_mjds:
            segment = julian.EOPRegistry._segment_bounds(mjd,data)
            if segment is not None and I(segment[0],segment[2]).intersect(absolute) is not None:
                segments.append(tuple(segment))
    boundary = julian._delta_t_observation_boundary()
    return ContinuousPolicyClock(float(anchor),domain,native.branch,table,tuple(segments),
        reader._kernel_identity.lunar_tidal_acceleration_arcsec_per_cy2,
        boundary.year,boundary.total,(tdigest,edigest))


def bound_continuous_policy_tt(scope: ContinuousPolicyClock,domain: I):
    """Enclose TT offset, first and second derivatives per UT1 day.

    The true continuity flag is proved algebraically from the shared endpoint
    table values. One-sided derivative hulls also bound secant slopes through
    a continuous table knot; differentiability at that knot is not asserted.
    """
    if domain.lo<scope.domain.lo or domain.hi>scope.domain.hi:
        raise ValueError('continuous clock request outside frozen domain')
    absolute = I.point(scope.anchor_jd)+domain
    pieces = []
    continuous = True
    if scope.branch=='direct_eop':
        intervals = []
        for start,dt0,end,dt1 in scope.eop_segments:
            part = absolute.intersect(I(start,end))
            if part is None:
                continue
            ut = j.variable(part)
            fraction = j.scale(j.sub(ut,j.constant(start)),1/(F.from_float(end)-F.from_float(start)))
            seconds = j.add(j.constant(dt0),j.scale(fraction,F.from_float(dt1)-F.from_float(dt0)))
            pieces.append(j.sub(j.add(ut,j.scale(seconds,F(1,86400))),j.constant(scope.anchor_jd)))
            intervals.append((start,dt0,end,dt1))
        cursor = absolute.lo
        for start,_,end,_ in sorted(intervals):
            if F.from_float(start)>cursor:
                raise EnclosureUnavailable('continuous EOP clock gap')
            cursor = max(cursor,F.from_float(end))
        if cursor<absolute.hi:
            raise EnclosureUnavailable('continuous EOP clock upper gap')
        intervals.sort()
        continuous = all(a[2]==b[0] and a[3]==b[1] for a,b in zip(intervals,intervals[1:]))
    else:
        lower,upper = absolute.to_float_bounds()
        first_year = julian.calendar_from_jd(lower)[0]
        last_year = julian.calendar_from_jd(upper)[0]
        for year in range(first_year,last_year+1):
            start,end = map(lambda y:F.from_float(julian.julian_day(y,1,1)),(year,year+1))
            part = absolute.intersect(I(start,end))
            if part is None:
                continue
            ut = j.variable(part)
            y = j.add(j.constant(year),j.scale(j.sub(ut,j.constant(start)),1/(end-start)))
            if scope.branch=='historical_hpiers':
                for (x0,v0),(x1,v1) in zip(scope.hpiers_rows,scope.hpiers_rows[1:]):
                    owned = y[0].intersect(I(x0,x1))
                    if owned is None:
                        continue
                    local = owned,y[1],y[2]
                    f = j.scale(j.sub(local,j.constant(x0)),1/(F.from_float(x1)-F.from_float(x0)))
                    seconds = j.add(j.constant(v0),j.scale(f,F.from_float(v1)-F.from_float(v0)))
                    centuries = j.scale(j.sub(local,j.constant(julian._TIDAL_REF_EPOCH)),F(1,100))
                    coefficient = (-F.from_float(julian._TIDAL_CONVERSION)
                        *(F.from_float(scope.tidal_target)-F.from_float(julian._TIDAL_NDOT_HPIERS)))
                    seconds = j.add(seconds,j.scale(j.square(centuries),coefficient))
                    # Restrict the input variable along with its year branch.
                    owned_ut = I.point(start)+(owned-year)*(end-start)
                    local_ut = owned_ut,I.point(1),I.point(0)
                    pieces.append(j.sub(j.add(local_ut,j.scale(seconds,F(1,86400))),j.constant(scope.anchor_jd)))
            else:
                centuries = j.scale(j.sub(y,j.constant(scope.future_reference_year)),F(1,100))
                coefficient = F.from_float(delta_t_physical.TIDAL_COEFF)+F.from_float(delta_t_physical.GIA_COEFF)
                seconds = j.add(j.constant(scope.future_reference_seconds),j.scale(j.square(centuries),coefficient))
                pieces.append(j.sub(j.add(ut,j.scale(seconds,F(1,86400))),j.constant(scope.anchor_jd)))
    if not pieces:
        raise EnclosureUnavailable('continuous clock has no owned branch')
    return tuple(I(min(piece[k].lo for piece in pieces),max(piece[k].hi for piece in pieces))
                 for k in range(3)),continuous
