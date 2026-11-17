"""Scoped numeric-totality obligations for the admitted Stage 3 clock routes.

This supplies the missing finite-execution argument separately from value
enclosures. Concrete direct type-2 data, bounded interpolation/polynomials,
the source's finite guards and the compensated TT/TDB recovery are required.
Binary/source/resource identity and arithmetic premises belong to the caller;
the record is not an authenticated or physical-accuracy certificate.
"""
from dataclasses import dataclass
from fractions import Fraction as F

from . import julian
from ._eclipse_interval import RationalInterval as I
from ._eclipse_interval_roots import EnclosureUnavailable
from ._eclipse_clock_provider import bound_native_ut1_to_tt
from ._eclipse_canon_clock_bounds import bound_canon_catalog_ut1_to_tt
from ._eclipse_native_clock_bounds import _require_sources
from ._eclipse_refined_serving_clock import prove_reduced_split_clock_convergence
from ._eclipse_native_spk_bounds import _selected_descriptor
from ._eclipse_time_bounds import bound_serving_single_tdb
from .spk_reader import SpkReader


@dataclass(frozen=True, slots=True)
class Stage3ClockRouteObligations:
    """Separable route, guard, identity and finite-iteration obligations."""

    input_anchor_jd: float
    input_domain: I
    clock_policy: str
    clock_branch: str
    tt_domain: I
    kernel_identity_sha256: str
    identity_descriptor_count: int
    compensated_recovery_max_iterations: int
    forward_totality_under_declared_premises: bool
    direct_identity_routes_covered: bool
    historical_raw_identity_guard_covered: bool
    legacy_split_fallback_possible: bool
    unchanged_source_resources_required: bool = True
    ieee_and_libm_contract_required: bool = True
    physical_accuracy_certified: bool = False


def prove_stage3_clock_route_obligations(reader,anchor: float,domain: I, *, policy='native'):
    """Prove finite forward execution on supported branches, or fail closed.

    Historical and future branches contain finitely many calendar/table
    cases, all denominators and outputs bounded by the existing providers.
    Direct EOP has its independent totality checker. Historical kernel-
    identity checks cover both raw and retargeted TT: a one-day hull contains
    the maximal admitted raw/corrected separation on these selected domains.
    The ordinary single-JD solve takes at most eight iterations; if exhausted,
    its compensated recovery has the split proof's finite bound. Therefore
    numerical two-cycles cannot invalidate the historical identity guards.
    Resource exhaustion/interruption and changed code/environment are outside
    this numerical theorem, as for every other serving arithmetic bound.
    """
    if type(reader) is not SpkReader or reader._closed:
        raise EnclosureUnavailable('open direct reader required for scoped route proof')
    _require_sources()
    if policy=='canon_catalog':
        bounds = bound_canon_catalog_ut1_to_tt(anchor,domain,require_totality=True)
        branch = 'canon_catalog_monthly'
        proved = bounds.forward_totality_conditionally_proved
    elif policy=='native':
        receipt = bound_native_ut1_to_tt(reader,anchor,domain)
        branch,bounds = receipt.branch,receipt.bounds
        if branch=='direct_eop':
            proved = bound_native_ut1_to_tt(reader,anchor,domain,
                require_totality=True).bounds.forward_totality_conditionally_proved
        else:
            if branch not in ('historical_hpiers','future_scenario'):
                raise EnclosureUnavailable('numeric totality branch not yet proved: '+branch)
            proved = True
    else:
        raise ValueError('unknown Stage 3 forward clock policy')
    tt = I.point(bounds.anchor_jd)+bounds.output_offset_days-anchor
    # The identity-selection clock is single-part, so its raw and corrected
    # input epochs must stay in the strict converter domain before recovery.
    wide = I(tt.lo-1,tt.hi+1)
    if (I.point(anchor)+wide).lo<=-40_000_000 or (I.point(anchor)+wide).hi>=40_000_000:
        raise EnclosureUnavailable('identity clock reaches a time-domain guard')
    recovery = prove_reduced_split_clock_convergence(anchor,I.point(0),first_part_offsets=wide)
    if recovery.status!='proved':
        raise EnclosureUnavailable('identity clock compensated recovery unproved')
    if branch=='historical_hpiers':
        target = F.from_float(reader._kernel_identity.lunar_tidal_acceleration_arcsec_per_cy2)
        years = tuple(bounds.possible_years)
        t = max(abs(F(year)-F.from_float(julian._TIDAL_REF_EPOCH)) for year in years)+2
        correction = abs(F.from_float(julian._TIDAL_CONVERSION)
            *(target-F.from_float(julian._TIDAL_NDOT_HPIERS)))*(t/100)**2
        if correction>=F(86400,2):
            raise EnclosureUnavailable('historical raw identity outside one-day guard')
    single = bound_serving_single_tdb(anchor,wide)
    absolute = I.point(anchor)+single.tdb_offset_days
    descriptors = []
    for pair in ((0,3),(3,399),(3,301),(0,10)):
        # Check each day with the literal Python and C++ descriptor guards.
        for day in range(absolute.lo//1,absolute.hi//1+1):
            part = absolute.intersect(I(day,day+1-F(1,2**53)))
            if part is None:
                continue
            selected = _selected_descriptor(reader,*pair,float(day),part-day)
            if selected.frame!=1 or selected.data_type!=2:
                raise EnclosureUnavailable('identity routes require direct J2000 type-2 data')
            descriptors.append((pair,selected.start_i,selected.end_i))
    return Stage3ClockRouteObligations(float(anchor),domain,policy,branch,tt,
        reader._source_identity.sha256,len(set(descriptors)),recovery.max_iterations,
        bool(proved),True,True,False)
