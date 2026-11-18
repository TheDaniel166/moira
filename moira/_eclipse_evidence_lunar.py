"""Public lunar evidence from the accepted geometric-Moon reference profile."""
from dataclasses import replace

from .eclipse_evidence import (RationalBound as B,EclipseEvidence,EclipseProductEvidence,
    EvidenceBudget,EvidenceCell)
from ._eclipse_evidence_common import domain,quantity,source,unavailable,failed
from ._eclipse_interval_roots import EnclosureUnavailable
from ._eclipse_piecewise_vectors import freeze_eclipse_records,enclose_piecewise_eclipse_vectors
from ._eclipse_continuous_lunar import ContinuousLunarVectorBounds
from ._eclipse_lunar_coverage import cover_lunar_reference_interval
from ._eclipse_continuous_lunar_contacts import (LunarMarginTriplet,isolate_lunar_margin_triplet,
    bound_continuous_lunar_contacts)
from ._eclipse_angular_contacts import bound_angular_lunar_contacts
from ._eclipse_lunar_piecewise_extrema import cover_lunar_source_extrema
from .constants import EARTH_RADIUS_KM,MOON_RADIUS_KM,SUN_RADIUS_KM

PRODUCTS = ('occurrence','contacts','extrema')


def compute_lunar_evidence(reader,epoch,box,policy,scale,selected,limit,tolerance):
    time = domain('TT',epoch,box)
    src = source(reader,'continuous_geometric_moon_'+policy)
    result = {p:unavailable(p,time,src,limit,'vector_enclosures','not_computed','product_not_requested')
              for p in PRODUCTS}
    configuration = (quantity('earth_radius_scale',scale),quantity('earth_radius',EARTH_RADIUS_KM*scale,'km'),
                     quantity('solar_radius',SUN_RADIUS_KM,'km'),quantity('lunar_radius',MOON_RADIUS_KM,'km'),
                     quantity('requested_time_tolerance',tolerance*86400,'seconds'))
    if limit == 0:
        for p in selected:
            result[p] = unavailable(p,time,src,limit,'vector_enclosures','unresolved','evaluation_budget_exhausted')
        return EclipseEvidence('lunar',time,tuple(result[p] for p in PRODUCTS),configuration=configuration)
    try:
        if reader is None or getattr(reader,'_closed',False):
            raise EnclosureUnavailable('open direct planetary reader required')
        records = freeze_eclipse_records(reader,epoch,box,max_records=256)
        src = source(reader,'continuous_geometric_moon_'+policy,records,
            clock='implicit_reference_TT_to_TDB',source_domain=time,tt_domain=box)
    except Exception as exc:
        for p in selected:
            result[p] = failed(p,time,src,limit,'vector_enclosures',exc)
        return EclipseEvidence('lunar',time,tuple(result[p] for p in PRODUCTS),configuration=configuration)
    earth = EARTH_RADIUS_KM*scale
    preparation = []

    def vectors(part):
        return enclose_piecewise_eclipse_vectors(records,part,retarded_moon=False)

    def reference_vectors(part):
        v = vectors(part)
        return ContinuousLunarVectorBounds(part,tuple(a[0] for a in v.sun),
            tuple(a[0] for a in v.moon),tuple(a[1] for a in v.sun),
            tuple(a[1] for a in v.moon),(),continuous_on_domain=v.continuous_on_domain,
            differentiable_on_domain=v.continuous_on_domain)

    for product in PRODUCTS:
        if product not in selected:
            continue
        try:
            if product == 'occurrence':
                cover = cover_lunar_reference_interval(box,reference_vectors,policy=policy,
                    tolerance=tolerance,earth_radius_km=earth,max_evaluations=limit)
                complete = all(c.status != 'unresolved' for c in cover.cells)
                present = any(c.status == 'overlap' for c in cover.cells)
                state = 'proved' if present else 'evaluated_zero' if complete else 'unresolved'
                cells = tuple(EvidenceCell(B.from_interval(c.domain),c.status,c.reason,
                    quantities=() if c.penumbral_margin is None else
                    (quantity('penumbral_overlap',c.penumbral_margin,cover.margin_unit),)) for c in cover.cells)
                result[product] = EclipseProductEvidence(product,state,'selected_model_whole_domain_coverage',time,src,
                    EvidenceBudget(limit,cover.evaluations,'vector_enclosures',not complete and cover.evaluations>=limit),
                    coverage_complete=complete,cells=cells,
                    values=(quantity('positive_overlap_witnessed',int(present)),),
                    notes=('No live serving-route totality or physical absence attestation.',))
            elif product == 'contacts':
                def margin_provider(part):
                    v = reference_vectors(part)
                    if not v.continuous_on_domain:
                        raise EnclosureUnavailable('source_record_join_continuity_unproved')
                    # Contact isolation needs value and first-rate bounds. The
                    # curvature evaluator requires a norm bounded away from
                    # zero even on broad boxes that the root solver must split.
                    if policy=='danjon_angular':
                        return bound_angular_lunar_contacts(v,earth_radius_km=earth)
                    margins = bound_continuous_lunar_contacts(v,effective_earth_radius_km=earth)
                    return LunarMarginTriplet(part,
                        (margins.penumbral_margin_km,margins.umbral_margin_km,margins.total_margin_km),
                        (margins.penumbral_derivative_km_per_day,margins.umbral_derivative_km_per_day,
                         margins.total_derivative_km_per_day))
                cover = isolate_lunar_margin_triplet(box,margin_provider,tolerance=tolerance,
                    continuity_assumed=True,margin_unit='rad' if policy=='danjon_angular' else 'km',
                    model_policy=policy,max_evaluations=limit)
                parts = (('penumbral',cover.penumbral),('umbral',cover.umbral),('total',cover.total))
                preparation.append(('contact_vector_enclosures',cover.vector_evaluations))
                complete = all(p.complete for _,p in parts)
                count = sum(c.status in ('unique','present') for _,p in parts for c in p.cells)
                state = ('proved' if count else 'evaluated_zero') if complete else 'unresolved'
                cells = tuple(EvidenceCell(B.from_interval(c.interval),c.status,c.reason,
                    quantities=() if c.value is None else (quantity('overlap_margin',c.value,cover.margin_unit),),
                    partition=name) for name,part in parts for c in part.cells)
                result[product] = EclipseProductEvidence(product,state,'three_independent_contact_partitions',time,src,
                    EvidenceBudget(limit,cover.evaluations,'root_callbacks',not complete and cover.evaluations>=limit),
                    coverage_complete=complete,values=(quantity('root_cells',count,'count'),),cells=cells,
                    precision_met=all(p.resolution_reached for _,p in parts),
                    notes=('Shared-endpoint root cells are not deduplicated contact identities.',))
            else:
                cover = cover_lunar_source_extrema(records,box,policy=policy,earth_radius_km=earth,
                    tolerance=tolerance,max_evaluations=limit)
                complete = cover.critical_set_covered
                cells = tuple(EvidenceCell(B.from_interval(c.domain),c.kind,c.reason,
                    quantities=tuple(quantity('objective_'+str(i),v,
                        'rad' if i==1 or (i>=2 and policy=='danjon_angular') else 'km')
                        for i,v in enumerate(c.values))) for c in cover.cells)
                result[product] = EclipseProductEvidence(product,'bounded' if complete else 'unresolved',
                    'source_critical_sets_retained',time,src,
                    EvidenceBudget(limit,cover.evaluations,'vector_enclosures',not complete and cover.evaluations>=limit),
                    coverage_complete=complete,cells=cells,
                    notes=('Source jumps excluded from global extrema: '+str(cover.source_region_excluded_from_global_extrema),))
        except Exception as exc:
            result[product] = failed(product,time,src,limit,'vector_enclosures',exc)
    for p in PRODUCTS:
        result[p] = replace(result[p],horizon_policy='geocentric_shadow_no_surface_horizon',
                            **({'source':src} if p not in selected else {}))
    return EclipseEvidence('lunar',time,tuple(result[p] for p in PRODUCTS),
                           preparation=(('copied_records',len(records.records)),*preparation),configuration=configuration)
