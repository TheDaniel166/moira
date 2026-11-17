"""Refresh exact orientation centres near solar endpoints and transitions.

Each refreshed provider encloses the same frozen continuous model. Only the
centre of its existing orientation Taylor bound changes; no tolerance, source
coefficient, derivative remainder or exclusion predicate is relaxed. This
prevents a distant orientation centre's remainder from obscuring a phase
transition very close to an axis endpoint.
"""
from dataclasses import replace
from fractions import Fraction as F

from ._eclipse_interval import RationalInterval as I
from ._eclipse_continuous_policy_clock import bound_continuous_policy_tt
from ._eclipse_continuous_solar_stage3 import continuous_solar_stage3_provider
from ._eclipse_orientation_reference import bound_celestial_orientation
from ._eclipse_solar_scalar_taylor import scalar_taylor_solar_provider


def refined_axis_solar_provider(scope, *, progress=None):
    """Intersect valid equivalent enclosures near an uncertain axis endpoint."""
    base,stats = scalar_taylor_solar_provider(scope,progress=progress)
    refreshed = {}
    stats['axis_orientation_refreshes'] = 0

    def enclosure(domain):
        value = base(domain)
        critical = (value.axis_margin.contains_zero or value.signed_radius is not None
                    and value.signed_radius.contains_zero)
        if not critical or domain.width>=F(1,86400):
            return value
        tt,_ = bound_continuous_policy_tt(scope.clock,domain)
        near = min(refreshed,key=lambda p:abs(p-tt[0].midpoint)) if refreshed else None
        # Wide candidate boxes can overlap the axis for several seconds
        # solely because of natural interval dependency. Recentring every
        # such box wastes a full 2414-term orientation evaluation. Keep its
        # valid remainder until a genuinely narrow undecided box needs a
        # closer centre; this changes cost, never the inclusion or tolerance.
        if (near is None or abs(near-tt[0].midpoint)>F(30,86400)
                or domain.width<F(1,8640000) and abs(near-tt[0].midpoint)>F(1,864000)):
            near = tt[0].midpoint
            point = bound_celestial_orientation(scope.orientation_series,scope.ut1_anchor_jd,I.point(near))
            local = replace(scope,orientation_midpoint=near,orientation_point=point)
            refreshed[near] = continuous_solar_stage3_provider(local)[0]
            stats['axis_orientation_refreshes'] += 1
        fine = refreshed[near](domain)
        # Both providers describe the identical curve on the identical box.
        # Preserve whichever proof flags/guards were already available while
        # intersecting only quantities for which both give an inclusion.
        updates = {}
        for name in ('axis_margin','signed_radius','forward_margin','daylight_margin',
                     'axis_derivative','radius_derivative'):
            left,right = getattr(value,name),getattr(fine,name)
            if left is None or right is None:
                continue
            meet = left.intersect(right)
            if meet is None:
                raise ArithmeticError('equivalent orientation-centred solar enclosures disagree')
            updates[name] = meet
        return replace(value,**updates)

    return enclosure,stats
