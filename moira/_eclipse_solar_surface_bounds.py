"""Uniform same-ray visibility bounds for supplied real geocentric boxes.

Closed caps are r.s>=cos(alpha), r.m>=cos(beta), r.n>=0, |r|=1.
For nonnegative multipliers, Cauchy-Schwarz gives the necessary condition
lambda*cos(alpha)+mu*cos(beta) <= |lambda*s+mu*m+nu*n|.
A strict reverse interval inequality excludes their COMMON intersection,
including lenses hidden although both discs individually reach the horizon.
Positive results instead require one independently enclosed ray strictly
inside both caps and the horizon. No float candidate is a proof.
"""
from dataclasses import dataclass
from fractions import Fraction as F

from ._eclipse_interval import RationalInterval as I
from ._eclipse_interval_roots import EnclosureUnavailable
from ._eclipse_surface_patches import _norm,_unit,bound_ellipsoid_patch
from .constants import SUN_RADIUS_KM,MOON_RADIUS_KM


def _dot(a,b):
    return sum((x*y for x,y in zip(a,b)),I.point(0)).quantize_outward(128)


@dataclass(frozen=True, slots=True)
class SolarSceneBox:
    """Supplied real ITRF position boxes; no source or time attestation."""

    sun_itrf_km: tuple[I,...]
    moon_itrf_km: tuple[I,...]
    sun_radius_km: F = F.from_float(SUN_RADIUS_KM)
    moon_radius_km: F = F.from_float(MOON_RADIUS_KM)

    def __post_init__(self):
        for name in ('sun_itrf_km','moon_itrf_km'):
            value = tuple(I.point(v) for v in getattr(self,name))
            if len(value)!=3:
                raise ValueError('three geocentric Cartesian components required')
            object.__setattr__(self,name,value)
        for name in ('sun_radius_km','moon_radius_km'):
            radius = I.point(getattr(self,name))
            if radius.width or radius.lo<=0:
                raise ValueError('positive point source radii required')
            object.__setattr__(self,name,radius.lo)


@dataclass(frozen=True, slots=True)
class CommonRayBounds:
    """Uniform cap data and a sufficient exclusion, never a sampled negative."""

    sun: tuple[I,...]
    moon: tuple[I,...]
    normal: tuple[I,...]
    sun_cosine: I
    moon_cosine: I
    excluded: bool
    reason: str
    exclusion_slack: I | None = None
    multipliers: tuple[F,...] | None = None


@dataclass(frozen=True, slots=True)
class CommonRayWitness:
    """A single real unit ray with strict, outward-enclosed clearances."""

    direction: tuple[I,...]
    sun_clearance: I
    moon_clearance: I
    horizon_sine: I


def bound_common_solar_rays(sun,moon,normal, *, sun_radius_km,moon_radius_km):
    """Bound common-cap feasibility, given a proved unit-normal function.

    Rays may be arbitrary vector boxes; normal must enclose an actual unit
    function, as the ellipsoid atlas supplies. Foreground depth separation
    is an admission condition inherited from solar_visibility_at_site;
    overlapping/reversed depth intervals remain unsupported, not absent.
    """
    sun,moon,normal = tuple(map(I.point,sun)),tuple(map(I.point,moon)),tuple(map(I.point,normal))
    if any(len(v)!=3 for v in (sun,moon,normal)):
        raise ValueError('three-component ray and normal boxes required')
    rs,rm = I.point(sun_radius_km),I.point(moon_radius_km)
    if rs.width or rm.width or min(rs.lo,rm.lo)<=0:
        raise ValueError('positive point radii required')
    ds,dm = _norm(sun),_norm(moon)
    if ds.lo<=rs.hi or dm.lo<=rm.hi:
        raise EnclosureUnavailable('observer outside both source spheres unproved')
    if dm.hi+rm.hi>=ds.lo-rs.hi:
        raise EnclosureUnavailable('strict foreground depth separation unproved')
    s,m = _unit(sun),_unit(moon)
    sa,sm = (rs/ds).quantize_outward(128),(rm/dm).quantize_outward(128)
    ca,cm = (1-sa.square()).sqrt(128),(1-sm.square()).sqrt(128)
    reason,slack,weights = 'common_ray_not_excluded',None,None
    candidates = [('disjoint_caps',ca*cm-sa*sm-_dot(s,m)),
        ('solar_cap_below_horizon',-(_dot(s,normal)+sa)),
        ('lunar_cap_below_horizon',-(_dot(m,normal)+sm))]
    for label,margin in candidates:
        if margin.lo>0:
            reason,slack = label,margin.quantize_outward(128)
            break
    else:
        for lam in (F(1,4),F(1,2),F(1),F(2),F(4)):
            w = tuple((lam*x+y).quantize_outward(128) for x,y in zip(s,m))
            nu = max(F(0),-_dot(w,normal).midpoint)
            combined = tuple((x+nu*n).quantize_outward(128) for x,n in zip(w,normal))
            margin = (lam*ca+cm-_norm(combined)).quantize_outward(128)
            if margin.lo>0:
                reason,slack,weights = 'joint_cap_horizon_separation',margin,(lam,F(1),nu)
                break
    return CommonRayBounds(s,m,normal,ca,cm,slack is not None,reason,slack,weights)


def bound_scene_on_patch(scene,patch):
    """Enclose all observers in a zero-elevation Cartesian ellipsoid patch."""
    if not isinstance(scene,SolarSceneBox):
        raise TypeError('SolarSceneBox required')
    observer = bound_ellipsoid_patch(patch)
    return bound_common_solar_rays(
        tuple(s-p for s,p in zip(scene.sun_itrf_km,observer.xyz_km)),
        tuple(m-p for m,p in zip(scene.moon_itrf_km,observer.xyz_km)),observer.normal,
        sun_radius_km=scene.sun_radius_km,moon_radius_km=scene.moon_radius_km)


def certify_common_solar_ray(bounds,direction):
    """Recheck a supplied candidate against all three strict constraints."""
    if len(direction)!=3:
        raise ValueError('three ray components required')
    ray = _unit(tuple(map(I.point,direction)))
    margins = (_dot(ray,bounds.sun)-bounds.sun_cosine,
               _dot(ray,bounds.moon)-bounds.moon_cosine,_dot(ray,bounds.normal))
    if all(m.lo>0 for m in margins):
        if bounds.excluded:
            raise ArithmeticError('strict witness contradicts a uniform exclusion')
        return CommonRayWitness(ray,*margins)
    return None
