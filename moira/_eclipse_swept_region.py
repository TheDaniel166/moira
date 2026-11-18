"""Certified inner/outer mesh enclosure of a finite time union on WGS84.

Inside requires one common time for the WHOLE surface cell. Outside requires
every time subinterval to exclude the WHOLE cell. All other cells remain in
the outer enclosure. An unresolved cell is never a boundary curve or width.
"""
from collections import deque
from dataclasses import dataclass
from fractions import Fraction as F
import time

from ._eclipse_interval import RationalInterval as I, IntervalBudgetError
from ._eclipse_interval_roots import EnclosureUnavailable
from ._eclipse_surface_patches import full_ellipsoid_atlas,split_ellipsoid_patch


def seeded_surface_partition(point_patch, *, half_width=F(1,10**8),extra_hints=()):
    """Partition all six faces with an exact small rectangle around a hint.

    The hint carries no inclusion authority. Grid cuts retain every spatial
    complement and every shared edge. It enables useful inner cells without
    refining the whole globe to the size of a short near-horizon footprint.
    """
    from ._eclipse_surface_patches import EllipsoidPatch
    if point_patch.u.width or point_patch.v.width or half_width <= 0:
        raise ValueError('exact point hint and positive half width required')
    result = []
    for face in full_ellipsoid_atlas():
        owned = [(p,w) for p,w in ((point_patch,half_width),*extra_hints)
                 if (face.axis,face.sign) == (p.axis,p.sign)]
        if not owned:
            result.append(face)
            continue
        cuts = []
        for coordinate in ('u','v'):
            values = {F(-1),F(1)}
            for p,w in owned:
                x = getattr(p,coordinate)
                if x.width or w <= 0:
                    raise ValueError('exact extra point and positive width required')
                values.update((max(F(-1),x.lo-w),min(F(1),x.lo+w)))
            cuts.append(sorted(values))
        result.extend(EllipsoidPatch(face.axis,face.sign,I(a,b),I(c,d))
                      for a,b in zip(cuts[0],cuts[0][1:])
                      for c,d in zip(cuts[1],cuts[1][1:]))
    return tuple(result)


def full_surface_partition_proved(patches):
    """Check exact area and disjoint interiors on each closed atlas face."""
    for axis in range(3):
        for sign in (-1,1):
            owned = [p for p in patches if (p.axis,p.sign) == (axis,sign)]
            if sum(p.u.width*p.v.width for p in owned) != 4:
                return False
            for index,a in enumerate(owned):
                for b in owned[index+1:]:
                    u,v = a.u.intersect(b.u),a.v.intersect(b.v)
                    if u is not None and v is not None and u.width*v.width > 0:
                        return False
    return True


@dataclass(frozen=True, slots=True)
class SweptCell:
    """One entire closed surface rectangle and its explicit time evidence."""

    patch: object
    status: str
    common_time: F | None
    time_ledger: tuple
    reason: str


@dataclass(frozen=True, slots=True)
class SweptRegionEnclosure:
    """Inner cells and an outer cover with every unresolved cell retained."""

    domain: I
    cells: tuple
    evaluations: int
    elapsed_seconds: float
    max_evaluations: int
    max_seconds: float | None
    scope: str = 'finite_interval_visible_central_footprint_union'
    horizon_policy: str = 'geometric_Sun_centre_no_refraction_or_terrain'
    full_atlas_domain_retained: bool = True
    exact_boundary_curve_claimed: bool = False

    @property
    def inner(self):
        return tuple(c for c in self.cells if c.status == 'inside')

    @property
    def outer(self):
        return tuple(c for c in self.cells if c.status != 'outside')

    @property
    def unresolved(self):
        return tuple(c for c in self.cells if c.status == 'unresolved')


def enclose_swept_region(domain,provider, *, patches=None, common_time_hints=(),
                         max_evaluations=4096,max_seconds=120.,max_surface_depth=12,
                         min_time_width=F(1,86400),max_time_depth=20,
                         max_time_evaluations_per_patch=32):
    """Cover the requested surface region; no missed sample implies exclusion.

    provider(time_interval, surface_patch) must enclose the entire product
    and return margins with inside/outside predicates. Finite budgets are
    cooperative and shared across time hints, subdivisions and all patches.
    """
    if not isinstance(domain,I) or type(max_evaluations) is not int or max_evaluations < 0:
        raise ValueError('exact domain and finite nonnegative budget required')
    if (max_seconds is not None and not 0 < max_seconds < float('inf')) or min_time_width <= 0:
        raise ValueError('finite positive duration and time resolution required')
    hints = tuple(I.point(t).lo for t in common_time_hints)
    if any(not domain.contains(t) for t in hints):
        raise ValueError('common-time hint outside event interval')
    start,calls,cells = time.monotonic(),0,[]
    surface = tuple(full_ellipsoid_atlas() if patches is None else patches)
    full_atlas = full_surface_partition_proved(surface)
    spatial = deque((p,0) for p in surface)

    def available():
        return calls < max_evaluations and (max_seconds is None or time.monotonic()-start < max_seconds)

    while spatial:
        patch,depth = spatial.popleft()
        ledger,inside = [],None
        for epoch in hints:
            if not available():
                break
            calls += 1
            try:
                bounds = provider(I.point(epoch),patch)
                if bounds.inside:
                    inside = epoch
                    ledger.append((I.point(epoch),'strict_common_time_inclusion',bounds))
                    break
            except (EnclosureUnavailable,IntervalBudgetError):
                pass
        pending = deque([(domain,0)]) if inside is None else deque()
        time_calls = 0
        while pending and available() and time_calls < max_time_evaluations_per_patch:
            interval,time_depth = pending.popleft()
            calls += 1
            time_calls += 1
            try:
                bounds = provider(interval,patch)
                if bounds.inside:
                    inside = interval.midpoint
                    ledger.append((interval,'strict_common_time_inclusion',bounds))
                    break
                if bounds.outside:
                    ledger.append((interval,'uniform_exclusion',bounds))
                    continue
                reason = 'boundary_or_unseparated_constraint'
            except (EnclosureUnavailable,IntervalBudgetError) as exc:
                reason = str(exc)
            if interval.width > min_time_width and time_depth < max_time_depth:
                mid = interval.midpoint
                pending.extend(((I(interval.lo,mid),time_depth+1),(I(mid,interval.hi),time_depth+1)))
            else:
                ledger.append((interval,'unresolved',reason))
        if inside is not None:
            cells.append(SweptCell(patch,'inside',inside,tuple(ledger),'uniform strict inclusion at a common time'))
        elif not pending and ledger and all(row[1] == 'uniform_exclusion' for row in ledger):
            cells.append(SweptCell(patch,'outside',None,tuple(ledger),'whole event interval excluded'))
        elif depth < max_surface_depth and available() and (patch.u.width or patch.v.width):
            spatial.extend((child,depth+1) for child in split_ellipsoid_patch(patch))
        else:
            ledger.extend((interval,'unresolved','finite_resource_budget') for interval,_ in pending)
            cells.append(SweptCell(patch,'unresolved',None,tuple(ledger),'retained in outer enclosure'))
    return SweptRegionEnclosure(domain,tuple(cells),calls,time.monotonic()-start,
                                max_evaluations,None if max_seconds is None else float(max_seconds),
                                full_atlas_domain_retained=full_atlas)
