"""Branch-aware lunar critical components and global-extremum exclusions.

Frozen SPK records need not meet exactly. Ordinary stationary roots and all
possible record-transition critical points therefore form separate sets.
The latter are isolated to the requested width and retain their one-sided
value/rate bounds; continuity is never asserted across them. Comparing their
whole-box values with an attained reference point can rigorously exclude
them from every requested global minimum/maximum without denying possible
microscopic local extrema at a record jump.
"""
from dataclasses import dataclass
from fractions import Fraction as F

from . import _eclipse_interval_jets as j
from ._eclipse_interval import IntervalBudgetError, RationalInterval as I
from ._eclipse_interval_roots import EnclosureUnavailable, isolate_roots
from ._eclipse_inverse_trig import asin_enclosure,atan_enclosure
from ._eclipse_piecewise_vectors import enclose_piecewise_eclipse_vectors
from ._eclipse_lunar_extrema import LunarObservableJets
from ._eclipse_continuous_lunar_contacts import _radii
from .constants import EARTH_RADIUS_KM,MOON_RADIUS_KM,SUN_RADIUS_KM


def _asin(a):
    cosine = (1-a[0].square()).sqrt(128)
    if cosine.lo<=0:
        raise EnclosureUnavailable('angular-radius derivative domain not proved')
    return (asin_enclosure(a[0]),j.q(a[1]/cosine),
            j.q(a[2]/cosine+a[0]*a[1].square()/(cosine**3)))


def _atan(a):
    denominator = 1+a[0].square()
    return atan_enclosure(a[0]),j.q(a[1]/denominator),j.q(a[2]/denominator-2*a[0]*a[1].square()/denominator.square())


def bound_piecewise_lunar_observables(vectors, *, policy, earth_radius_km=EARTH_RADIUS_KM,
                                     sun_radius_km=SUN_RADIUS_KM,moon_radius_km=MOON_RADIUS_KM):
    """Enclose five objectives and branch derivatives, including record joins."""
    re,rs,rm = _radii(earth_radius_km,sun_radius_km,moon_radius_km)
    sun,moon = vectors.sun,vectors.moon
    ds,dm = j.norm(sun),j.norm(moon)
    z = j.neg(j.div(j.dot(sun,moon),ds))
    if z[0].lo<=0 or ds[0].lo<=rs+re or dm[0].lo<=re+rm:
        raise EnclosureUnavailable('lunar source/antisolar domains not proved')
    cross = tuple(j.sub(j.mul(moon[a],sun[b]),j.mul(moon[b],sun[a]))
                  for a,b in ((1,2),(2,0),(0,1)))
    radial = j.div(j.norm(cross),ds)
    angle = _atan(j.div(radial,z))
    if policy=='danjon_angular':
        parallax = _asin(j.div(j.constant(re),dm))
        alpha = _asin(j.div(j.constant(rm),dm))
        solar = _asin(j.div(j.constant(rs),ds))
        solar_parallax = _asin(j.div(j.constant(re),ds))
        base = j.add(j.scale(parallax,1.01),solar_parallax)
        pen,umbra = j.add(base,solar),j.sub(base,solar)
        if umbra[0].lo<=0:
            raise EnclosureUnavailable('angular umbral circle not proved')
        margins = (j.sub(j.add(pen,alpha),angle),j.sub(j.add(umbra,alpha),angle),
                   j.sub(j.sub(umbra,alpha),angle))
    elif policy=='static_finite_cone':
        if z[0].lo-rm<re:
            raise EnclosureUnavailable('downstream finite-cone domain not proved')
        p,u = j.div(j.constant(rs+re),ds),j.div(j.constant(rs-re),ds)
        cp,cu = j.sqrt(j.sub(j.constant(1),j.square(p))),j.sqrt(j.sub(j.constant(1),j.square(u)))
        pen = j.add(j.sub(j.add(j.constant(re),j.mul(p,z)),j.mul(cp,radial)),j.constant(rm))
        apex = j.sub(j.div(j.constant(re),u),z)
        branch = j.add(apex,j.mul(j.div(u,cu),radial))[0]
        if branch.lo>0:
            clearance = j.sub(j.sub(j.constant(re),j.mul(u,z)),j.mul(cu,radial))
        elif branch.hi<0:
            clearance = j.neg(j.norm((apex,radial)))
        else:
            raise EnclosureUnavailable('finite-cone nappe branch not proved')
        margins = pen,j.add(clearance,j.constant(rm)),j.sub(clearance,j.constant(rm))
    else:
        raise ValueError('unknown lunar reference policy')
    values = radial,angle,*margins
    return LunarObservableJets(vectors.domain,
        ('axis_distance','angular_opposition','penumbral_overlap','umbral_overlap','total_overlap'),
        tuple(a[0] for a in values),tuple(a[1] for a in values),tuple(a[2] for a in values))


@dataclass(frozen=True, slots=True)
class LunarSourceCriticalCell:
    """A smooth exclusion, stationary box, or isolated source-critical set."""

    domain: I
    kind: str
    values: tuple[I,...]
    rates: tuple[I,...]
    source_labels: tuple[str,...]
    dominated_by_attained_reference: tuple[bool,...]
    reason: str


@dataclass(frozen=True, slots=True)
class LunarSourceExtremaCoverage:
    """Complete critical-set coverage with separate global-extremum evidence."""

    domain: I
    policy: str
    cells: tuple[LunarSourceCriticalCell,...]
    attained_reference_offset: F
    attained_reference_values: tuple[I,...]
    critical_set_covered: bool
    source_region_excluded_from_global_extrema: bool
    evaluations: int
    max_evaluations: int
    local_extrema_at_record_jumps_may_remain_clustered: bool = True
    continuity_across_record_jumps_claimed: bool = False
    physical_accuracy_certified: bool = False


def cover_lunar_source_extrema(model, domain: I, *, policy, reference_offset=F(0),
                               earth_radius_km=EARTH_RADIUS_KM,tolerance=F(1,864000),
                               max_evaluations=3000,max_depth=100):
    """Isolate every possible critical component and prove global exclusion.

    Smooth interiors exclude a stationary point only by whole-box rates.
    Every possible routing discontinuity is retained in a narrow component.
    Such a component can contain multiple local extrema; its entire value
    enclosure, not a sampled value or presumed continuity, decides whether
    it can compete with an attained reference value for a global extremum.
    """
    if not isinstance(domain,I) or domain.lo<model.domain.lo or domain.hi>model.domain.hi:
        raise ValueError('source-extrema domain outside frozen record set')
    tol = I.point(tolerance)
    if tol.lo!=tol.hi or tol.lo<=0:
        raise ValueError('positive exact source-critical tolerance required')
    if any(type(n) is not int or n<0 for n in (max_evaluations,max_depth)):
        raise ValueError('finite integer source-critical budgets required')
    reference_offset = F(reference_offset)
    if not model.domain.contains(reference_offset):
        raise ValueError('attained reference point outside frozen model')
    cache,count = {},0

    def observe(box):
        nonlocal count
        key = box.lo,box.hi
        if key not in cache:
            if count>=max_evaluations:
                raise EnclosureUnavailable('source-critical evaluation budget exhausted')
            count += 1
            vector = enclose_piecewise_eclipse_vectors(model,box)
            cache[key] = vector,bound_piecewise_lunar_observables(vector,policy=policy,
                                                                  earth_radius_km=earth_radius_km)
        return cache[key]

    try:
        _,reference = observe(I.point(reference_offset))
    except (EnclosureUnavailable,IntervalBudgetError) as exc:
        cell = LunarSourceCriticalCell(domain,'unresolved',(),(),(),(),str(exc))
        return LunarSourceExtremaCoverage(domain,policy,(cell,),reference_offset,(),False,False,
                                          count,max_evaluations)

    def dominates(values):
        return tuple(value.lo>target.hi if index<2 else value.hi<target.lo
                     for index,(value,target) in enumerate(zip(values,reference.values)))

    stack,cells = [(domain,0)],[]
    while stack:
        box,depth = stack.pop()
        try:
            vector,jet = observe(box)
            dominance = dominates(jet.values)
            if vector.continuous_on_domain and all(not rate.contains_zero for rate in jet.rates):
                cells.append(LunarSourceCriticalCell(box,'smooth_excluded',jet.values,jet.rates,(),dominance,
                                                     'all five whole-interval rates exclude zero'))
                continue
            if box.width<=tol.hi or depth>=max_depth:
                if vector.switches:
                    cells.append(LunarSourceCriticalCell(box,'source_component',jet.values,jet.rates,
                        tuple(sorted({switch.label for switch in vector.switches})),dominance,
                        'all possible record-transition critical points retained; no join continuity assumed'))
                    continue
                proofs = [isolate_roots(box,lambda part,index=index:observe(part)[1].rates[index],
                    derivative=lambda part,index=index:observe(part)[1].curvatures[index],
                    continuous=True,tolerance=tol,unit='TT day offset',time_scale='TT',
                    max_depth=0,max_evaluations=8) for index in range(5)]
                kind = 'stationary_component' if all(proof.complete for proof in proofs) else 'unresolved'
                cells.append(LunarSourceCriticalCell(box,kind,jet.values,jet.rates,(),dominance,
                    'separate stationary root proofs' if kind!='unresolved' else 'stationary root proof incomplete'))
                continue
        except (EnclosureUnavailable,IntervalBudgetError) as exc:
            if box.width<=tol.hi or depth>=max_depth or count>=max_evaluations:
                cells.append(LunarSourceCriticalCell(box,'unresolved',(),(),(),(),str(exc)))
                continue
        mid = box.midpoint
        stack.extend(((I(mid,box.hi),depth+1),(I(box.lo,mid),depth+1)))
    cells.sort(key=lambda cell:cell.domain.lo)
    complete = all(cell.kind!='unresolved' and (cell.kind=='smooth_excluded' or cell.domain.width<=tol.hi)
                   for cell in cells)
    try:
        endpoints = (tuple(dominates(observe(I.point(value))[1].values) for value in (domain.lo,domain.hi))
                     if complete else ())
    except (EnclosureUnavailable,IntervalBudgetError):
        endpoints = ()
    excluded = complete and len(endpoints)==2 and all(all(values) for values in endpoints)
    excluded = excluded and all(all(cell.dominated_by_attained_reference)
                                 for cell in cells if cell.kind!='smooth_excluded')
    return LunarSourceExtremaCoverage(domain,policy,tuple(cells),reference_offset,reference.values,
                                      complete,bool(excluded),count,max_evaluations)
