"""Bounded full-ellipsoid visibility partition for supplied snapshot boxes.

Each discarded surface rectangle has a uniform same-ray exclusion. A
positive result needs a rationally rechecked common-ray witness. Every
unvisited or unsupported rectangle remains in the ledger as unresolved.
This first Stage 4 foundation does not map UT1/TT, attest source boxes,
enumerate cone generators or prove event-wide/time-interval coverage.
"""
from dataclasses import dataclass
from fractions import Fraction as F
import math

from ._eclipse_interval import IntervalBudgetError,RationalInterval as I
from ._eclipse_interval_roots import EnclosureUnavailable
from ._eclipse_surface_patches import EllipsoidPatch,full_ellipsoid_atlas,split_ellipsoid_patch
from ._eclipse_solar_surface_bounds import (SolarSceneBox,CommonRayWitness,
    bound_scene_on_patch,certify_common_solar_ray)
from .solar_disc_visibility import solar_disc_visibility
from .constants import EARTH_RADIUS_KM
from .eclipse import _WGS84_POLAR_RADIUS_KM


@dataclass(frozen=True, slots=True)
class SurfaceRayWitness:
    """A strictly visible ray at one exact ellipsoid point patch."""

    point_patch: EllipsoidPatch
    ray: CommonRayWitness


@dataclass(frozen=True, slots=True)
class SurfaceVisibilityCell:
    """One uniformly resolved or explicitly unresolved surface rectangle."""

    patch: EllipsoidPatch
    status: str
    reason: str
    uniform_ray: CommonRayWitness | None = None
    exclusion_slack: I | None = None
    multipliers: tuple[F,...] | None = None


@dataclass(frozen=True, slots=True)
class SolarSurfaceSnapshotCover:
    """Full parameter ledger, with resolution and occurrence kept distinct."""

    scene: SolarSceneBox
    cells: tuple[SurfaceVisibilityCell,...]
    witness: SurfaceRayWitness | None
    patch_evaluations: int
    witness_site_evaluations: int
    max_patch_evaluations: int
    max_witness_site_evaluations: int
    full_spatial_partition_resolved: bool
    absence_proved: bool
    presence_proved: bool
    equatorial_radius_km: F = F.from_float(EARTH_RADIUS_KM)
    polar_radius_km: F = F.from_float(_WGS84_POLAR_RADIUS_KM)
    horizon_policy: str = 'strict common ray above ellipsoid tangent; no refraction or terrain'
    full_atlas_domain_retained: bool = True
    source_route_attested: bool = False
    time_interval_coverage_proved: bool = False
    full_cone_topology_proved: bool = False
    physical_accuracy_certified: bool = False


def _candidate_rays(bounds):
    """Reuse the ordinary cap solver solely to propose untrusted ray hints."""
    s,m,n = (tuple(float(c.midpoint) for c in vector)
             for vector in (bounds.sun,bounds.moon,bounds.normal))
    candidates = [s,m,n,tuple(x+y for x,y in zip(s,m))]
    sr,mr = (math.acos(max(-1.,min(1.,float(c.midpoint))))
             for c in (bounds.sun_cosine,bounds.moon_cosine))
    if 0<min(sr,mr)<=max(sr,mr)<=math.pi/2:
        result = solar_disc_visibility(s,m,n,sr,mr)
        if result.witness_direction is not None:
            candidates.append(result.witness_direction)
    return tuple(c for c in candidates if any(c))


def cover_solar_surface_snapshot(scene, *, max_patch_evaluations=256,
                                 max_witness_site_evaluations=64,max_depth=24,
                                 min_parameter_width=F(1,1024),stop_after_witness=True):
    """Cover all six charts, proving only strict exclusions or witnesses.

    Budgets count whole-patch predicates and point-site witness attempts
    separately. At most five candidate rays are rechecked per attempted
    site. Closed child rectangles share their split boundary. A stopped
    search retains every pending rectangle and cannot certify absence.
    """
    if not isinstance(scene,SolarSceneBox):
        raise TypeError('SolarSceneBox required')
    if any(type(v) is not int or v<0 for v in
           (max_patch_evaluations,max_witness_site_evaluations,max_depth)):
        raise ValueError('finite nonnegative integer budgets required')
    if type(stop_after_witness) is not bool:
        raise TypeError('stop_after_witness must be bool')
    width = I.point(min_parameter_width)
    if width.width or width.lo<=0:
        raise ValueError('positive exact minimum parameter width required')
    stack = [(p,0) for p in reversed(full_ellipsoid_atlas())]
    cells,witness,calls,sites = [],None,0,0
    while stack:
        patch,depth = stack.pop()
        if calls>=max_patch_evaluations:
            cells.append(SurfaceVisibilityCell(patch,'unresolved','patch_evaluation_budget'))
            continue
        calls += 1
        bounds = None
        reason = 'common_ray_not_excluded'
        try:
            bounds = bound_scene_on_patch(scene,patch)
            if bounds.excluded:
                cells.append(SurfaceVisibilityCell(patch,'excluded',bounds.reason,
                    exclusion_slack=bounds.exclusion_slack,multipliers=bounds.multipliers))
                continue
        except (EnclosureUnavailable,IntervalBudgetError) as exc:
            reason = str(exc)
        uniform = None
        if sites<max_witness_site_evaluations:
            sites += 1
            point = EllipsoidPatch(patch.axis,patch.sign,I.point(patch.u.midpoint),I.point(patch.v.midpoint))
            try:
                at = bound_scene_on_patch(scene,point)
                if not at.excluded:
                    for candidate in _candidate_rays(at):
                        ray = certify_common_solar_ray(at,candidate)
                        if ray is not None:
                            witness = witness or SurfaceRayWitness(point,ray)
                            if bounds is not None:
                                uniform = certify_common_solar_ray(bounds,candidate)
                            break
            except (EnclosureUnavailable,IntervalBudgetError):
                # Only the optional point search failed; its entire parent
                # domain is still retained and may be subdivided below.
                pass
        if uniform is not None:
            cells.append(SurfaceVisibilityCell(patch,'visible','uniform_strict_common_ray',uniform))
        elif witness is not None and stop_after_witness:
            cells.append(SurfaceVisibilityCell(patch,'unresolved','point_witness_only'))
        elif depth>=max_depth or max(patch.u.width,patch.v.width)<=width.lo:
            cells.append(SurfaceVisibilityCell(patch,'unresolved',reason))
        else:
            left,right = split_ellipsoid_patch(patch)
            stack.extend(((right,depth+1),(left,depth+1)))
        if witness is not None and stop_after_witness:
            cells.extend(SurfaceVisibilityCell(p,'unresolved','search_stopped_after_witness') for p,_ in stack)
            stack.clear()
    complete = all(c.status!='unresolved' for c in cells)
    absence = complete and all(c.status=='excluded' for c in cells)
    return SolarSurfaceSnapshotCover(scene,tuple(cells),witness,calls,sites,
        max_patch_evaluations,max_witness_site_evaluations,complete,absence,witness is not None)
