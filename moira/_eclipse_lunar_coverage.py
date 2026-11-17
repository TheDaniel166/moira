"""Closed TT coverage for model-specific lunar exclusion and overlap bounds.

Every requested instant belongs to a covering cell, including seams and
exhausted work. Exclusion uses a bound for a whole interval, never the absence
of a sampled detection. These reference-vector conclusions are distinct from
live-route totality, an exhaustive serving search and physical accuracy.
"""
from dataclasses import dataclass
from fractions import Fraction
from typing import Callable, Literal

from ._eclipse_angular_contacts import bound_angular_lunar_contacts
from ._eclipse_continuous_lunar import ContinuousLunarVectorBounds
from ._eclipse_continuous_lunar_contacts import _radii, bound_continuous_lunar_contacts
from ._eclipse_interval import IntervalBudgetError, RationalInterval as I
from ._eclipse_interval_roots import EnclosureUnavailable
from ._eclipse_reference_astro import bound_lunar_reference_vectors
from .constants import EARTH_RADIUS_KM, MOON_RADIUS_KM, SUN_RADIUS_KM


@dataclass(frozen=True, slots=True)
class LunarCoverageCell:
    """One whole-interval model exclusion, overlap, or bounded uncertainty."""

    domain: I
    status: Literal['excluded', 'overlap', 'unresolved']
    reason: str
    penumbral_margin: I | None = None
    chord_lower: Fraction | None = None
    threshold_upper: Fraction | None = None


@dataclass(frozen=True, slots=True)
class LunarReferenceCoverage:
    """A complete domain cover, not a claim that all of its cells resolved.

    A reference exclusion is conditional on the callback's whole-interval
    vector inclusion, unchanged inputs and selected model. No result attests
    the serving evaluator, a live kernel or physical eclipse absence.
    """

    domain: I
    policy: str
    margin_unit: str
    cells: tuple[LunarCoverageCell, ...]
    evaluations: int
    max_evaluations: int
    domain_covered: bool = True
    serving_route_totality_proved: bool = False
    eclipse_absence_certified: bool = False
    physical_accuracy_certified: bool = False


def _norm(vector, bits):
    return sum((component.square() for component in vector), I.point(0)).sqrt(bits)


def bound_lunar_exclusion_chord(
    vectors: ContinuousLunarVectorBounds, *, policy: str,
    earth_radius_km=EARTH_RADIUS_KM, sun_radius_km=SUN_RADIUS_KM,
    moon_radius_km=MOON_RADIUS_KM, precision_bits: int = 128,
) -> tuple[Fraction, Fraction]:
    """Return a whole-domain chord lower bound and necessary-overlap bound.

    c=|M/|M|+S/|S||=2 sin(theta/2)<=theta. For the Danjon model,
    asin(R/d)<=R/sqrt(d*d-R*R) yields an upper angular threshold.
    For the separate cone model, on the proved downstream hemisphere,
    chord<=sqrt(2)*sin(theta) and cp*r<=E+sp*z+M give its own bound.
    Full vector boxes already enclose motion, so no midpoint or sampled
    speed estimate is substituted. A strict lower>upper proves exclusion
    for the stated reference model only. Unsupported domains raise.
    """
    if not isinstance(vectors, ContinuousLunarVectorBounds):
        raise TypeError('reference vector bounds required')
    if type(precision_bits) is not int or not 64 <= precision_bits <= 256:
        raise ValueError('invalid chord precision')
    re, rs, rm = _radii(earth_radius_km, sun_radius_km, moon_radius_km)
    sun, moon = vectors.sun_geocentric_km, vectors.moon_geocentric_km
    ds, dm = _norm(sun, precision_bits), _norm(moon, precision_bits)
    if ds.lo <= rs + re or dm.lo <= re + rm:
        raise EnclosureUnavailable('whole-domain source distance not proved')
    normalized_sum = tuple((m/dm + s/ds).quantize_outward(precision_bits)
                           for m, s in zip(moon, sun))
    chord = _norm(normalized_sum, precision_bits)
    if policy == 'danjon_angular':
        def upper(radius, lower_distance):
            denominator = (I.point(lower_distance).square() - radius*radius).sqrt(precision_bits)
            if denominator.lo <= 0:
                raise EnclosureUnavailable('angular threshold denominator not proved')
            return I.point(radius)/denominator

        threshold = (Fraction.from_float(1.01)*upper(re, dm.lo) + upper(rm, dm.lo)
                     + upper(rs, ds.lo) + upper(re, ds.lo))
    elif policy == 'static_finite_cone':
        z = -sum((m*s for m, s in zip(moon, sun)), I.point(0))/ds
        if z.lo - rm < re:
            raise EnclosureUnavailable('whole-Moon downstream cone domain not proved')
        sp = I.point(rs + re)/I.point(ds.lo)
        if sp.hi >= 1:
            raise EnclosureUnavailable('cone opening domain not proved')
        cp = (1-sp.square()).sqrt(precision_bits)
        if cp.lo <= 0:
            raise EnclosureUnavailable('cone threshold denominator not proved')
        threshold = I.point(2).sqrt(precision_bits)*(re + sp*dm.hi + rm)/(cp*dm.lo)
    else:
        raise ValueError('unknown lunar policy')
    return chord.lo, threshold.hi


def cover_lunar_reference_interval(
    domain: I, vector_enclosure: Callable[[I], ContinuousLunarVectorBounds], *,
    policy: str, tolerance, earth_radius_km=EARTH_RADIUS_KM,
    sun_radius_km=SUN_RADIUS_KM, moon_radius_km=MOON_RADIUS_KM,
    precision_bits: int = 128, max_evaluations: int = 4096, max_depth: int = 80,
) -> LunarReferenceCoverage:
    """Cover the complete requested TT interval without a full-moon filter.

    The provider must enclose all selected vector branches throughout each
    requested cell. Continuity is not needed to exclude a complete value
    box. Unavailable or singular boxes are subdivided, then retained with
    their reason if the resolution/depth/evaluation limit is reached. This
    ledger intentionally does not infer contact identities or extrema.
    """
    if not isinstance(domain, I):
        raise TypeError('rational TT offset domain required')
    tol = I.point(tolerance)
    if tol.lo != tol.hi or tol.lo <= 0:
        raise ValueError('positive exact tolerance required')
    if policy not in ('danjon_angular', 'static_finite_cone'):
        raise ValueError('unknown lunar policy')
    if (type(max_evaluations) is not int or max_evaluations < 0
            or type(max_depth) is not int or not 0 <= max_depth <= 256):
        raise ValueError('invalid lunar coverage budget')
    if type(precision_bits) is not int or not 64 <= precision_bits <= 256:
        raise ValueError('invalid coverage precision')
    _radii(earth_radius_km, sun_radius_km, moon_radius_km)
    stack, cells, evaluations = [(domain, 0)], [], 0
    while stack:
        box, depth = stack.pop()
        if evaluations >= max_evaluations:
            cells.append(LunarCoverageCell(box, 'unresolved', 'evaluation_budget_exhausted'))
            continue
        evaluations += 1
        reason, margin, chord, threshold = 'contact_or_sign_not_resolved', None, None, None
        try:
            vectors = vector_enclosure(box)
            if not isinstance(vectors, ContinuousLunarVectorBounds) or vectors.tt_offset_days != box:
                raise TypeError('provider must retain the exact requested TT domain')
            chord, threshold = bound_lunar_exclusion_chord(
                vectors, policy=policy, earth_radius_km=earth_radius_km,
                sun_radius_km=sun_radius_km, moon_radius_km=moon_radius_km,
                precision_bits=precision_bits,
            )
            if chord > threshold:
                cells.append(LunarCoverageCell(box, 'excluded', 'whole_interval_chord_exclusion',
                                               chord_lower=chord, threshold_upper=threshold))
                continue
            if policy == 'danjon_angular':
                value = bound_angular_lunar_contacts(
                    vectors, earth_radius_km=earth_radius_km, sun_radius_km=sun_radius_km,
                    moon_radius_km=moon_radius_km, precision_bits=precision_bits,
                )
                margin = value.margins[0]
            else:
                value = bound_continuous_lunar_contacts(
                    vectors, effective_earth_radius_km=earth_radius_km,
                    sun_radius_km=sun_radius_km, moon_radius_km=moon_radius_km,
                    precision_bits=precision_bits,
                )
                margin = value.penumbral_margin_km
            if margin.hi < 0 or margin.lo > 0:
                status = 'excluded' if margin.hi < 0 else 'overlap'
                cells.append(LunarCoverageCell(box, status, 'whole_interval_margin_sign',
                                               margin, chord, threshold))
                continue
        except (EnclosureUnavailable, IntervalBudgetError) as exc:
            reason = 'enclosure_unavailable: ' + str(exc)
        if box.width <= tol.hi or depth >= max_depth:
            cells.append(LunarCoverageCell(box, 'unresolved', reason, margin, chord, threshold))
        else:
            middle = box.midpoint
            stack.append((I(middle, box.hi), depth+1))
            stack.append((I(box.lo, middle), depth+1))
    return LunarReferenceCoverage(
        domain, policy, 'rad' if policy == 'danjon_angular' else 'km',
        tuple(sorted(cells, key=lambda cell: (cell.domain.lo, cell.domain.hi))),
        evaluations, max_evaluations,
    )


def cover_lunar_tt_reference(reader, tt_anchor_jd: float, domain: I, *,
                             policy: str, tolerance, max_evaluations: int = 4096,
                             earth_radius_km=EARTH_RADIUS_KM):
    """Use multi-record polynomial value boxes over an arbitrary TT interval.

    The amplitude-bounded reference includes every ideal Sun-delay iterate,
    geometric Moon and selected record. It does not assume records join
    continuously, enclose the live binary64 route or attest raw MID/RADIUS.
    It inherits the unchanged source/reader and uniform-record premises of
    ``bound_lunar_reference_vectors``. Unproved coverage remains in the ledger.
    """
    def enclosure(box):
        values = bound_lunar_reference_vectors(reader, tt_anchor_jd, box)
        zeros = I.point(0), I.point(0), I.point(0)
        return ContinuousLunarVectorBounds(
            box, values.sun_retarded_km, values.moon_geometric_km, zeros, zeros, (),
            continuous_on_domain=False, differentiable_on_domain=False,
        )

    # Whole-box signs do not need continuity. First derivatives remain
    # unavailable, rather than assigning false zero rates across SPK seams.
    return cover_lunar_reference_interval(
        domain, enclosure, policy=policy, tolerance=tolerance,
        earth_radius_km=earth_radius_km, max_evaluations=max_evaluations,
    )


def first_reference_overlap(coverage: LunarReferenceCoverage, *, direction: int = 1):
    """Return the first overlap cell, stopping at any preceding uncertainty.

    This is a component/coverage query, not a nearest eclipse maximum. It
    must never step across an unresolved interval to a later sampled event.
    """
    if direction not in (-1, 1) or type(direction) is not int:
        raise ValueError('direction must be -1 or 1')
    cells = coverage.cells if direction == 1 else reversed(coverage.cells)
    for cell in cells:
        if cell.status != 'excluded':
            return cell
    return None
