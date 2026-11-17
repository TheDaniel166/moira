"""Whole-TT native positive-overlap superset without a full-moon filter.

Necessary chord bounds apply to every defined positive result of each
selected lunar shadow policy. They do not turn an upstream model-domain
rejection into a successful geometry result. Unsupported rays remain bounded
unknowns. The ledger isolates candidate neighborhoods for the separate full
contact/extremum solver and never certifies a later event across unknown time.
"""
from dataclasses import dataclass
from fractions import Fraction as F

from ._eclipse_interval import RationalInterval as I
from ._eclipse_interval_roots import EnclosureUnavailable
from ._eclipse_frozen_native_vectors import freeze_native_vector_scope,bound_frozen_native_vectors
from ._eclipse_solar_float_coverage import represented_solar_inputs,_key,_value
from .constants import EARTH_RADIUS_KM,SUN_RADIUS_KM,MOON_RADIUS_KM
from .eclipse import _eclipse_body_pair


@dataclass(frozen=True, slots=True)
class NativeLunarSurveyCell:
    """A whole-box necessary-condition exclusion, candidate or uncertainty."""

    domain: I
    status: str
    reason: str
    chord_lower: F | None = None
    necessary_threshold_upper: F | None = None


@dataclass(frozen=True, slots=True)
class NativeLunarSurvey:
    """All requested TT inputs covered, with no inference across unknown time."""

    tt_anchor_jd: float
    domain: I
    policy: str
    cells: tuple[NativeLunarSurveyCell,...]
    vector_evaluations: int
    literal_native_points: int
    all_represented_inputs_resolved: bool
    complete_represented_input_ledger: bool = True
    defined_positive_overlap_superset_only: bool = True
    geometry_totality_outside_selected_domain_claimed: bool = False
    physical_accuracy_certified: bool = False


def _necessary_chord(sun,moon,policy,earth_radius_scale):
    def norm(vector):
        return sum((x.square() for x in vector),I.point(0)).sqrt(128)

    re,rs,rm = map(F.from_float,(EARTH_RADIUS_KM,SUN_RADIUS_KM,MOON_RADIUS_KM))
    ds,dm = norm(sun),norm(moon)
    effective = F.from_float(EARTH_RADIUS_KM*earth_radius_scale)
    if ds.lo<=rs+max(re,effective) or dm.lo<=re+rm:
        raise EnclosureUnavailable('positive disjoint native ray norms unproved')
    chord = norm(tuple((s/ds+m/dm).quantize_outward(128) for s,m in zip(sun,moon)))
    unit = F(512,2**52)
    gamma = unit/(1-unit)
    # Fewer than 128 elementary operations occur in either source geometry.
    # This 512-operation bound includes axis normalization, three-dimensional
    # hypot/fsum/cross rounding, one-ulp inverse trig and norm conditioning.
    angular_round = gamma*(1+dm.hi/dm.lo+ds.hi/ds.lo)
    dmin,smin = dm.lo*(1-gamma),ds.lo*(1-gamma)

    def asin_upper(radius,distance):
        denominator = I.point(distance*distance-radius*radius).sqrt(128).lo
        return radius/denominator

    if policy=='danjon_angular':
        threshold = (F.from_float(1.01)*asin_upper(re,dmin)+asin_upper(rm,dmin)
                     +asin_upper(rs,smin)+asin_upper(re,smin)+angular_round)
    else:
        opening = (rs+effective)*(1+gamma)/smin
        if opening>=F(1,2):
            raise EnclosureUnavailable('native cone opening unproved')
        cosine = I.point(1-opening*opening).sqrt(128).lo-gamma
        if cosine<=0:
            raise EnclosureUnavailable('native cone cosine unproved')
        # On every defined positive source result z-rm>=effective>0. Thus
        # chord<=sqrt(2)*sin(theta); the rounded cone clearance implies the
        # separate threshold below. No upstream cone distance is evaluated.
        numerator = (effective+rm+opening*dm.hi*(1+gamma)
                     +gamma*(effective+rm+2*dm.hi))
        threshold = I.point(2).sqrt(128).hi*numerator/(cosine*dmin)+angular_round
    return chord.lo,I.point(threshold).quantize_outward(128).hi


def survey_native_lunar_interval(reader,anchor: float,domain: I, *, policy,
                                 earth_radius_scale=1.,candidate_width=F(1,20),
                                 source_leaf_width=F(1,86400000),max_evaluations=8192,
                                 max_native_points=16384,max_depth=80,covered_event_domains=()):
    """Cover the caller's complete TT interval with conservative exclusions.

    Candidate cells are a superset, not detections. Every represented input
    remaining at a source seam can be evaluated exhaustively; a failed source
    call propagates, while exhausted proof budgets retain exact unknown time.
    Necessary tests do not require a full-moon neighborhood or continuity.
    The chord/threshold comparison never claims physical absence or geometry
    success on a policy's explicitly rejected upstream domain.
    """
    if policy not in ('danjon_angular','static_finite_cone'):
        raise ValueError('unknown selected lunar policy')
    if policy=='danjon_angular' and earth_radius_scale!=1.:
        raise ValueError('Danjon atmospheric convention is fixed')
    if not isinstance(domain,I) or candidate_width<=0 or source_leaf_width<=0:
        raise ValueError('exact domain and positive coverage resolutions required')
    if any(type(value) is not int or value<0 for value in (max_evaluations,max_native_points,max_depth)):
        raise ValueError('finite nonnegative budgets required')
    if any(not isinstance(part,I) or part.lo<domain.lo or part.hi>domain.hi for part in covered_event_domains):
        raise ValueError('covered contact domains must lie inside the full requested TT interval')
    try:
        scope = freeze_native_vector_scope(reader,anchor,domain)
    except EnclosureUnavailable as exc:
        cell = NativeLunarSurveyCell(domain,'unresolved',str(exc))
        return NativeLunarSurvey(anchor,domain,policy,(cell,),0,0,False)
    stack,cells,calls,points = [(domain,0)],[],0,0
    while stack:
        box,depth = stack.pop()
        reason = 'necessary_overlap_not_excluded'
        try:
            if calls>=max_evaluations:
                raise EnclosureUnavailable('native survey evaluation budget exhausted')
            calls += 1
            rays = bound_frozen_native_vectors(scope,box,moon_retarded=False)
            lower,upper = _necessary_chord(rays.sun_retarded_km,rays.moon_retarded_km,policy,earth_radius_scale)
            if lower>upper:
                cells.append(NativeLunarSurveyCell(box,'excluded','whole_interval_necessary_chord',lower,upper))
                continue
            covered = not covered_event_domains or any(part.lo<=box.lo<=box.hi<=part.hi for part in covered_event_domains)
            if box.width<=candidate_width and covered:
                cells.append(NativeLunarSurveyCell(box,'candidate','possible_defined_positive_overlap',lower,upper))
                continue
        except EnclosureUnavailable as exc:
            reason = str(exc)
        if calls>=max_evaluations or depth>=max_depth:
            cells.append(NativeLunarSurveyCell(box,'unresolved',reason))
            continue
        if box.width<=source_leaf_width:
            first,last = represented_solar_inputs(anchor,box)
            count = 0 if first is None else _key(last)-_key(first)+1
            if count>max_native_points-points:
                cells.append(NativeLunarSurveyCell(box,'unresolved',reason+'; native point budget'))
                continue
            for key in range(_key(first),_key(last)+1) if first is not None else ():
                jd = _value(key)
                sun,moon = _eclipse_body_pair(jd,reader,sun_retarded=True,moon_retarded=False)
                points += 1
                lower,upper = _necessary_chord(tuple(I.point(x) for x in sun),tuple(I.point(x) for x in moon),policy,earth_radius_scale)
                offset = I.point(F.from_float(jd)-F.from_float(anchor))
                covered = not covered_event_domains or any(part.contains(offset.lo) for part in covered_event_domains)
                status = 'excluded' if lower>upper else 'candidate' if covered else 'unresolved'
                cells.append(NativeLunarSurveyCell(offset,status,
                    'exhaustive_native_input_necessary_condition',lower,upper))
            continue
        middle = box.midpoint
        stack.extend(((I(middle,box.hi),depth+1),(I(box.lo,middle),depth+1)))
    cells.sort(key=lambda cell:cell.domain.lo)
    return NativeLunarSurvey(anchor,domain,policy,tuple(cells),calls,points,
                              all(cell.status!='unresolved' for cell in cells))


def first_native_lunar_candidate(coverage, *, backward=False):
    """Stop at the first candidate or unknown; never leap past uncertainty."""
    for cell in reversed(coverage.cells) if backward else coverage.cells:
        if cell.status!='excluded':
            return cell
    return None
