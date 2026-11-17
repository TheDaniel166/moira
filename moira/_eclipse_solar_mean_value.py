"""Correlated mean-value forms for the same continuous solar predicates.

On one smooth clock/polar/source branch, f(X) is enclosed by
f(mid(X)) + f'(X)*(X-mid(X)). The point and derivative come from the
same explicitly frozen real curve. Intersecting two valid enclosures
reduces dependency without changing a model, root tolerance or budget.
Rounded native execution is never assigned this differentiability claim.
"""
from dataclasses import replace
from fractions import Fraction as F

from ._eclipse_interval import RationalInterval as I
from ._eclipse_solar_axis_refinement import refined_axis_solar_provider
from ._eclipse_solar_scalar_taylor import _smooth_clock_and_polar


def mean_value_solar_provider(scope, *, progress=None):
    """Tighten solar predicates by whole-box derivatives and an enclosed point."""
    base,stats = refined_axis_solar_provider(scope,progress=progress)
    stats['mean_value_contractions'] = 0

    def enclosure(domain):
        value = base(domain)
        if (not value.real_continuous_model or not 0<domain.width<F(10,86400)
                or not _smooth_clock_and_polar(scope,domain)):
            return value
        critical = (value.axis_margin.contains_zero or value.signed_radius is not None
                    and value.signed_radius.contains_zero)
        if not critical:
            return value
        point = base(I.point(domain.midpoint))
        if not point.real_continuous_model:
            return value
        h = domain-domain.midpoint
        updates = {}
        for name,rate_name in (('axis_margin','axis_derivative'),('signed_radius','radius_derivative')):
            box,target,rate = getattr(value,name),getattr(point,name),getattr(value,rate_name)
            if box is None or target is None or rate is None:
                continue
            meet = box.intersect((target+rate*h).quantize_outward(128))
            if meet is None:
                raise ArithmeticError('continuous solar mean-value enclosure disagrees with original bounds')
            if meet.width<box.width:
                stats['mean_value_contractions'] += 1
                updates[name] = meet
        return replace(value,**updates)

    return enclosure,stats
