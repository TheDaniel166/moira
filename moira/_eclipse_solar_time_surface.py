"""Bounded occurrence over closed time x full WGS84 surface domains.

The provider contract supplies real vector enclosures on WHOLE requested
intervals. No conjunction filter, midpoint failure or missing shadow means
absence. The continuous-current-policy DE provider is a separate adapter.
"""
from dataclasses import dataclass
from fractions import Fraction as F
from collections import deque
import time

from ._eclipse_interval import RationalInterval as I, IntervalBudgetError
from ._eclipse_interval_roots import EnclosureUnavailable
from ._eclipse_solar_surface_bounds import bound_scene_on_patch, certify_common_solar_ray
from ._eclipse_solar_surface_cover import _candidate_rays
from ._eclipse_surface_patches import full_ellipsoid_atlas, split_ellipsoid_patch
from .constants import EARTH_RADIUS_KM, SUN_RADIUS_KM, MOON_RADIUS_KM


def _norm(vector):
    return sum((v.square() for v in vector), I.point(0)).sqrt(160)


def _cap_chord(sine):
    if not 0 <= sine.lo <= sine.hi < 1:
        raise EnclosureUnavailable('angular bound outside admitted range')
    return (2-2*(1-sine.square()).sqrt(160)).sqrt(160)


def global_disc_separation(sun, moon, *, earth_radius=EARTH_RADIUS_KM,
                           sun_radius=SUN_RADIUS_KM, moon_radius=MOON_RADIUS_KM):
    """Whole-Earth exclusion from unit-ray chord distance and parallax.

    For |P|<=a<|V| the direction change is at most asin(a/|V|).
    Euclidean chord triangle inequalities include BOTH parallaxes and both
    apparent cap radii at their minimum observer distances. Positive slack
    therefore excludes every observer and horizon, independently of rotation.
    """
    sun, moon = tuple(map(I.point, sun)), tuple(map(I.point, moon))
    ds, dm = _norm(sun), _norm(moon)
    a, rs, rm = (I.point(v) for v in (earth_radius, sun_radius, moon_radius))
    if ds.lo <= a.hi+rs.hi or dm.lo <= a.hi+rm.hi:
        raise EnclosureUnavailable('external observer distances not bounded')
    separation = _norm(tuple(s/ds-m/dm for s,m in zip(sun,moon)))
    radius = (_cap_chord(a/ds)+_cap_chord(a/dm)+
              _cap_chord(rs/(ds-a))+_cap_chord(rm/(dm-a)))
    return (separation-radius).quantize_outward(128)


@dataclass(frozen=True, slots=True)
class TimeSurfaceCell:
    """A closed time cell and its entire surface chart, or all six charts."""

    time: I
    patch: object
    status: str
    reason: str
    slack: I | None = None


@dataclass(frozen=True, slots=True)
class TimeSurfaceWitness:
    """One exact time, exact ellipsoid point and strictly rechecked ray."""

    time: F
    patch: object
    ray: object


@dataclass(frozen=True, slots=True)
class SolarTimeSurfaceCover:
    """Full domain ledger; unresolved domains block any absence assertion."""

    domain: I
    cells: tuple
    witness: TimeSurfaceWitness | None
    evaluations: int
    elapsed_seconds: float
    max_evaluations: int
    max_seconds: float
    full_domain_retained: bool = True
    scope: str = 'conditional_whole_interval_vector_enclosures'
    physical_accuracy_certified: bool = False

    @property
    def presence_proved(self):
        return self.witness is not None

    @property
    def absence_proved(self):
        return bool(self.cells) and all(c.status == 'excluded' for c in self.cells)

    @property
    def time_interval_coverage_proved(self):
        return self.absence_proved

    @property
    def unresolved(self):
        return tuple(c for c in self.cells if c.status == 'unresolved')


def cover_solar_time_surface(domain, scene_provider, *, separation_provider=None,
                             witness_hints=(), max_evaluations=4096, max_seconds=120.,
                             min_time_width=F(1, 86400), max_surface_depth=18):
    """Prove an occurrence witness or exclude the complete time/surface box.

    Hints are (exact time, point patch, optional ray) and carry no authority.
    An early positive retains the rest of the domain explicitly. Time and
    surface splitting share closed endpoints. Budgets include hint checks.
    """
    if not isinstance(domain, I) or type(max_evaluations) is not int or max_evaluations < 0:
        raise ValueError('exact domain and nonnegative finite evaluation budget required')
    if not 0 < max_seconds < float('inf') or min_time_width <= 0 or max_surface_depth < 0:
        raise ValueError('positive finite duration, time width and depth required')
    start, calls, cells, witness = time.monotonic(), 0, [], None

    def available():
        return calls < max_evaluations and time.monotonic()-start < max_seconds

    for epoch, patch, ray in witness_hints:
        epoch = I.point(epoch).lo
        if not domain.lo <= epoch <= domain.hi:
            raise ValueError('witness hint outside requested domain')
        if patch.u.width or patch.v.width:
            raise ValueError('witness hint must specify an exact surface point')
        if not available():
            break
        calls += 1
        try:
            bound = bound_scene_on_patch(scene_provider(I.point(epoch)), patch)
            candidates = (ray,) if ray is not None else _candidate_rays(bound)
            for candidate in candidates:
                certified = certify_common_solar_ray(bound, candidate)
                if certified is not None:
                    witness = TimeSurfaceWitness(epoch, patch, certified)
                    break
        except (EnclosureUnavailable, IntervalBudgetError):
            pass
        if witness is not None:
            break
    # Breadth-first work prevents one hard face consuming the whole budget
    # before even trying the centre of another face.
    stack = deque([(domain, None, 0)])
    while stack:
        interval, patch, depth = stack.popleft()
        if witness is not None or not available():
            cells.append(TimeSurfaceCell(interval, patch, 'unresolved',
                'positive_witness_retained_complement' if witness else 'finite_resource_budget'))
            continue
        calls += 1
        reason = 'visibility_not_excluded'
        try:
            if patch is None and separation_provider is not None:
                slack = separation_provider(interval)
                if slack.lo > 0:
                    cells.append(TimeSurfaceCell(interval, None, 'excluded',
                                                  'whole_earth_disc_separation', slack))
                    continue
            if patch is None:
                # Broad source boxes may need time splitting before orientation
                # or space. The separation predicate has no cone admission gate.
                if interval.width > F(1, 48):
                    mid = interval.midpoint
                    stack.extend(((I(mid,interval.hi),None,0),(I(interval.lo,mid),None,0)))
                else:
                    stack.extend((interval,face,0) for face in full_ellipsoid_atlas())
                continue
            bound = bound_scene_on_patch(scene_provider(interval), patch)
            if bound.excluded:
                cells.append(TimeSurfaceCell(interval, patch, 'excluded', bound.reason,
                                              bound.exclusion_slack))
                continue
            if available():
                from ._eclipse_surface_patches import EllipsoidPatch
                calls += 1
                site = EllipsoidPatch(patch.axis,patch.sign,
                                      I.point(patch.u.midpoint),I.point(patch.v.midpoint))
                when = interval.midpoint
                point_bound = bound_scene_on_patch(scene_provider(I.point(when)),site)
                for candidate in _candidate_rays(point_bound):
                    certified = certify_common_solar_ray(point_bound,candidate)
                    if certified is not None:
                        witness = TimeSurfaceWitness(when,site,certified)
                        break
                if witness is not None:
                    cells.append(TimeSurfaceCell(interval,patch,'unresolved',
                                                  'positive_witness_retained_complement'))
                    continue
        except (EnclosureUnavailable, IntervalBudgetError) as exc:
            reason = str(exc)
        if interval.width > min_time_width and (patch is None or depth % 2 == 0):
            mid = interval.midpoint
            stack.extend(((I(mid,interval.hi),patch,depth+1),
                          (I(interval.lo,mid),patch,depth+1)))
        elif patch is not None and depth < max_surface_depth:
            stack.extend((interval,child,depth+1) for child in split_ellipsoid_patch(patch))
        else:
            cells.append(TimeSurfaceCell(interval,patch,'unresolved',reason))
    return SolarTimeSurfaceCover(domain,tuple(cells),witness,calls,time.monotonic()-start,
                                  max_evaluations,float(max_seconds))
