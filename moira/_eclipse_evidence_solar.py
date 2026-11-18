"""Public solar evidence adapters; every product retains its own scope."""
from fractions import Fraction as F

from .eclipse_evidence import (RationalBound as B,EclipseEvidence,EclipseProductEvidence,
    EvidenceBudget,EvidenceCell,EvidenceWitness,EvidenceTopology,EvidenceVertex,EvidenceArc,EvidenceLimit)
from ._eclipse_evidence_common import domain,quantity,source,surface,unavailable,failed
from ._eclipse_interval import RationalInterval as I
from ._eclipse_interval_roots import EnclosureUnavailable
from ._eclipse_continuous_solar_stage3 import (prepare_continuous_solar_stage3,
    continuous_solar_stage3_provider,cover_continuous_solar_stage3)
from ._eclipse_geographic_width import axis_normal_section,geographic_width_from_frame
from ._eclipse_swept_region import enclose_swept_region,seeded_surface_partition
from ._eclipse_solar_time_source import prepare_solar_time_source
from ._eclipse_solar_time_surface import cover_solar_time_surface
from ._eclipse_surface_patches import patch_through_cartesian_ray
from ._eclipse_cone_algebra import FixedConeFamily
from ._eclipse_cone_topology import solve_cone_topology
from ._eclipse_constraint_circles import complete_constraint_circles
from ._eclipse_solar_pole_reference import bound_solar_pole_reference
from .eclipse import EclipseCalculator,_earth_fixed_solar_shadow,_axis_surface_point_from_shadow,_WGS84_POLAR_RADIUS_KM
from .constants import EARTH_RADIUS_KM,MOON_RADIUS_KM,SUN_RADIUS_KM

PRODUCTS = ('occurrence','central_path','surface_topology','swept_region','geographic_width')
POINT_PRODUCTS = ('surface_topology','geographic_width')


def _central_quantities(bounds,daylight_unit):
    return tuple(quantity(name,getattr(bounds,name),unit) for name,unit in (
        ('containment','km^2'),('daylight',daylight_unit),('foreground','km'),
        ('acute','km^2'),('phase_order','dimensionless')))


def compute_solar_evidence(reader,epoch,box,selected,limit,tolerance,width_tolerance):
    requested_time = domain('UT1',epoch,box)
    src = source(reader,'continuous_real_current_policy_retarded_sun_moon')
    result = {p:unavailable(p,domain('UT1',epoch,I.point(0) if p in POINT_PRODUCTS else box),
        source(reader,'frozen_native_coefficients_exact_real_cone') if p=='surface_topology' else src,
        limit,'predicate_calls','not_computed','product_not_requested') for p in PRODUCTS}
    preparation = []
    scopes = {}

    def prepare(scope_box):
        if scope_box not in scopes:
            scope = prepare_continuous_solar_stage3(reader,epoch,scope_box,
                panel_count=1 if not scope_box.width else 4,local_point_rates=not scope_box.width)
            frames,stats = continuous_solar_stage3_provider(scope,frame_only=True)
            cache = {}

            def frame(part):
                if part not in cache:
                    cache[part] = frames(part)
                return cache[part]
            scopes[scope_box] = scope,frame,stats
            preparation.extend((('vector_panel_enclosures',2*len(scope.panels)),('orientation_enclosures',2),
                                ('copied_records',len(scope.records.records))))
        return scopes[scope_box]

    for product in PRODUCTS:
        if product not in selected:
            continue
        time = result[product].domain
        if limit == 0:
            result[product] = unavailable(product,time,result[product].source,limit,'predicate_calls',
                                          'unresolved','evaluation_budget_exhausted')
            continue
        current_source = result[product].source
        try:
            if reader is None or getattr(reader,'_closed',False):
                raise EnclosureUnavailable('open direct planetary reader required')
            if product == 'surface_topology':
                current_source = source(reader,'frozen_native_coefficients_exact_real_cone')
                calc = EclipseCalculator(reader=reader)
                snapshot_tt = calc._jd_tt_from_ut(epoch)
                current_source = source(reader,'frozen_native_coefficients_exact_real_cone',
                    clock='native_UT1_to_TT_snapshot',source_domain=time,
                    tt_domain=I.point(F(snapshot_tt)-F(epoch)))
                shadow = _earth_fixed_solar_shadow(calc,epoch,jd_tt=snapshot_tt)
                preparation.append(('native_snapshot_evaluations',1))
                if shadow is None:
                    raise EnclosureUnavailable('native_cone_state_unavailable; no absence inference')
                family = FixedConeFamily.from_shadow(shadow)
                cone = solve_cone_topology(family,max_queries=limit)
                circles = complete_constraint_circles(cone,max_queries=max(0,limit-cone.queries))
                vertices = [EvidenceVertex(repr(v.key),v.forward,v.horizon,v.nappe,v.tags,
                    tuple(map(str,v.point.root.polynomial)),B.from_interval(v.point.root.interval),
                    v.key[1] if v.key[0]=='root' else 1) for v in cone.vertices]
                known = {v.key for v in cone.vertices}
                vertices.extend(EvidenceVertex(repr(key),None,None,None,('clipping_circle',))
                                for key,_ in circles.points if key not in known)
                arcs = [EvidenceArc('cone',a.chart,repr(a.start),repr(a.end),B.from_interval(a.parameter),
                    (('branch',str(a.branch)),('forward',str(a.forward)),('horizon',str(a.horizon)),
                     ('nappe',str(a.nappe)),('collapsed_to_apex',str(a.collapsed_to_apex)))) for a in cone.arcs]
                arcs.extend(EvidenceArc(a.plane,a.chart,repr(a.start),repr(a.end),None,
                    (('cone_sign',str(a.cone_sign)),('other_plane_sign',str(a.other_plane_sign)))) for a in circles.arcs)
                complete = cone.complete and circles.complete
                topology = EvidenceTopology(tuple(vertices),tuple(arcs),len(cone.components),complete)
                values = [quantity('clipped_cone_components',len(cone.components),'count'),
                          quantity('native_snapshot_jd_tt',snapshot_tt,'TT Julian day')]
                for name in ('radius','slope','forward_start','equatorial_km','polar_km'):
                    values.append(quantity('frozen_'+name,getattr(family,name),
                                           'dimensionless' if name=='slope' else 'km'))
                for name in ('origin','axis','east','north','sun'):
                    values.extend(quantity('frozen_'+name+'_'+str(i),v,
                        'km' if name in ('origin','sun') else 'dimensionless')
                        for i,v in enumerate(getattr(family,name)))
                result[product] = EclipseProductEvidence(product,'proved' if complete else 'unresolved',
                    cone.reason+'; '+circles.reason,time,current_source,
                    EvidenceBudget(limit,cone.queries+circles.queries,'Sturm_queries',
                                   not complete and cone.queries+circles.queries>=limit),
                    coverage_complete=complete,values=tuple(values),topology=topology,
                    horizon_policy='sun_centre_geometric_WGS84_no_refraction_or_terrain',
                    notes=('Component count is of clipped cone intersections, not filled surface regions.',
                           'Circle cut-set queries share the remaining finite query allocation.',))
            elif product == 'occurrence':
                model = prepare_solar_time_source(reader,epoch,box)
                current_source = source(reader,src.model_id,model.records,model.clock.source_digests,
                    clock=model.clock.branch,source_domain=time,tt_domain=model.records.domain)
                hints = ()
                shadow = _earth_fixed_solar_shadow(EclipseCalculator(reader=reader),epoch)
                preparation.append(('native_hint_evaluations',1))
                if shadow is not None:
                    point = _axis_surface_point_from_shadow(shadow)
                    if point is not None:
                        hints = ((F(0),patch_through_cartesian_ray(point.xyz_itrf_km),None),)
                cover = cover_solar_time_surface(box,model.scene,separation_provider=model.separation,
                    witness_hints=hints,max_evaluations=limit,max_seconds=None)
                state = 'proved' if cover.presence_proved else 'evaluated_zero' if cover.absence_proved else 'unresolved'
                witnesses = ()
                if cover.witness is not None:
                    w = cover.witness
                    witnesses = (EvidenceWitness(B.from_interval(I.point(w.time)),surface(w.patch),
                        tuple(quantity(n,getattr(w.ray,n)) for n in
                              ('sun_clearance','moon_clearance','horizon_sine'))),)
                cells = tuple(EvidenceCell(B.from_interval(c.time),c.status,c.reason,surface(c.patch),
                    () if c.slack is None else (quantity('exclusion_slack',c.slack),)) for c in cover.cells)
                result[product] = EclipseProductEvidence(product,state,'whole_time_surface_common_ray_cover',time,current_source,
                    EvidenceBudget(limit,cover.evaluations,'predicate_calls',bool(cover.unresolved) and cover.evaluations>=limit),
                    coverage_complete=cover.absence_proved,cells=cells,witnesses=witnesses,
                    full_surface_domain_retained=cover.full_domain_retained,
                    horizon_policy='same_ray_geometric_WGS84_no_refraction_or_terrain')
                preparation.extend((('copied_records',len(model.records.records)),
                                    ('rotation_scopes',len(model.rotation_scopes))))
                for prepared,_ in model.rotation_scopes:
                    preparation.extend((('occurrence_vector_panel_enclosures',2*len(prepared.panels)),
                                        ('occurrence_orientation_enclosures',2)))
            else:
                scope_box = box if product in ('central_path','swept_region') else I.point(0)
                # The width uses a point scope for tighter differentiated rates
                # even when a wider path scope was requested in the same call.
                scope,frame,stats = prepare(scope_box)
                current_source = source(reader,src.model_id,scope.records,
                    (*scope.clock.source_digests,scope.orientation_series.sha256,scope.polar_sha256),
                    clock=scope.clock.branch,source_domain=domain('UT1',epoch,scope.domain),tt_domain=scope.tt_domain)
                if product == 'central_path':
                    cover,counts = cover_continuous_solar_stage3(scope,tolerance=tolerance,max_evaluations=limit)
                    preparation.extend((('path_additional_vector_points',max(0,counts['vector_points']-len(scope.panels))),
                                        ('path_additional_orientation_points',max(0,counts['orientation_points']-1))))
                    result[product] = EclipseProductEvidence(product,
                        ('proved' if cover.event_interval_enclosed else 'bounded') if cover.coverage_complete else 'unresolved',
                        cover.reason,time,current_source,
                        EvidenceBudget(limit,cover.evaluations,'predicate_calls',not cover.coverage_complete and cover.evaluations>=limit),
                        coverage_complete=cover.coverage_complete,
                        cells=tuple(EvidenceCell(B.from_interval(c.domain),c.kind,c.reason,partition=c.phase) for c in cover.cells),
                        sequence=cover.sequence,subtype=cover.subtype,
                        horizon_policy='sun_centre_geometric_WGS84_no_refraction_or_terrain',
                        components=tuple((B.from_interval(a),B.from_interval(b)) for a,b in cover.central_intervals),
                        event_interval_enclosed=cover.event_interval_enclosed,
                        notes=('Complete sequence/subtype requires an enclosed event interval: '+str(cover.event_interval_enclosed),))
                elif product == 'geographic_width':
                    observed = frame(I.point(0))
                    axis = bound_solar_pole_reference(I.point(0),observed.sun,observed.moon,observed.rotation[2],
                                                      continuous_model=observed.continuous)
                    preparation.append(('axis_reference_checks',1))
                    if axis.axis_margin.hi < 0 or (axis.forward_margin is not None and axis.forward_margin.hi < 0):
                        result[product] = unavailable(product,time,current_source,limit,'section_predicates',
                            'not_applicable','no_legal_near_axis_reference_proved; no event-absence inference')
                        continue
                    width = geographic_width_from_frame(observed,epoch_ut1=epoch,
                        tolerance_km=width_tolerance,max_evaluations=limit)
                    cells = tuple(EvidenceCell(B.from_interval(part),state,
                        bound if isinstance(bound,str) else 'whole_section_sign',
                        quantities=() if isinstance(bound,str) else _central_quantities(bound,'dimensionless'),
                        coordinate='section_parameter') for part,state,bound in width.cells)
                    values,limits = [],[]
                    if width.width_km is not None:
                        values.append(quantity('geographic_width',width.width_km,'km'))
                        values.append(quantity('track_speed',width.section.track_speed_km_per_day,'km/UT1 day'))
                        values.append(quantity('axis_half_chord_squared',width.section.axis_half_chord_sq_km2,'km^2'))
                        for i,v in enumerate(width.section.reference_itrf_km):
                            values.append(quantity('reference_itrf_'+str(i),v,'km'))
                        limits = [EvidenceLimit(edge.side,B.from_interval(edge.parameter),
                            tuple(B.from_interval(v) for v in edge.xyz_itrf_km),edge.unique_root_proved) for edge in width.limits]
                    result[product] = EclipseProductEvidence(product,'bounded' if width.width_km is not None else 'unresolved',
                        width.reason,time,current_source,
                        EvidenceBudget(limit,width.evaluations,'section_predicates',
                                       width.status != 'bounded_width' and width.evaluations >= limit),
                        coverage_complete=width.width_km is not None,values=tuple(values),cells=cells,metric=width.metric,
                        precision_met=None if width.width_km is None else width.width_km.width<=width_tolerance,
                        horizon_policy='sun_centre_geometric_WGS84_no_refraction_or_terrain',limits=tuple(limits),
                        notes=(width.track_policy,'Instantaneous section width; no swept-union or NASA width claim.'))
                else:
                    def footprint(part,patch):
                        from ._eclipse_central_region_bounds import central_frame_patch_bounds
                        return central_frame_patch_bounds(frame(part),patch)
                    patches = None
                    hints = ()
                    try:
                        section = axis_normal_section(frame(I.point(0)))
                        point = patch_through_cartesian_ray(tuple(v.midpoint for v in section.reference_itrf_km))
                        night = patch_through_cartesian_ray(tuple(-s.midpoint*r*r for s,r in zip(section.sun,section.radii)))
                        patches = sorted(seeded_surface_partition(point,extra_hints=((night,F(1,16)),)),
                                         key=lambda p:p.u.width*p.v.width)
                        hints = (F(0),)
                    except EnclosureUnavailable:
                        pass
                    cover = enclose_swept_region(box,footprint,patches=patches,common_time_hints=hints,
                        max_evaluations=limit,max_seconds=None,max_surface_depth=3,max_time_evaluations_per_patch=16)
                    cells = []
                    for c in cover.cells:
                        ledger = tuple(EvidenceCell(B.from_interval(t),state,
                            bounds if isinstance(bounds,str) else 'whole_time_surface_sign',
                            quantities=() if isinstance(bounds,str) else _central_quantities(bounds,'km'))
                            for t,state,bounds in c.time_ledger)
                        cells.append(EvidenceCell(B.from_interval(box),c.status,c.reason,surface(c.patch),
                            common_time=None if c.common_time is None else B.from_interval(I.point(c.common_time)),
                            time_evidence=ledger))
                    complete = not cover.unresolved
                    empty = complete and not cover.inner
                    state = 'evaluated_zero' if empty else 'bounded' if cover.inner or any(c.status=='outside' for c in cover.cells) else 'unresolved'
                    result[product] = EclipseProductEvidence(product,state,'certified_inner_outer_mesh_with_retained_unknowns',time,current_source,
                        EvidenceBudget(limit,cover.evaluations,'predicate_calls',bool(cover.unresolved) and cover.evaluations>=limit),
                        coverage_complete=complete,cells=tuple(cells),
                        full_surface_domain_retained=cover.full_atlas_domain_retained,
                        values=(quantity('inner_cells',len(cover.inner),'count'),quantity('outer_cells',len(cover.outer),'count'),
                                quantity('unresolved_cells',len(cover.unresolved),'count')),
                        horizon_policy='sun_centre_geometric_WGS84_no_refraction_or_terrain',
                        notes=('No exact boundary curve or Hausdorff error is claimed.',))
        except Exception as exc:
            result[product] = failed(product,time,current_source,limit,'predicate_calls',exc)
    for scope,frame,stats in scopes.values():
        preparation.extend((('frame_provider_calls',stats['calls']),
            ('additional_vector_points',max(0,stats['vector_points']-len(scope.panels))),
            ('additional_orientation_points',max(0,stats['orientation_points']-1))))
    # Counter order and product order are stable; no elapsed time enters evidence.
    counters = {}
    for name,value in preparation:
        counters[name] = counters.get(name,0)+value
    configuration = (*tuple(quantity(n,v,'km') for n,v in (
        ('earth_equatorial_radius',EARTH_RADIUS_KM),('earth_polar_radius',_WGS84_POLAR_RADIUS_KM),
        ('solar_radius',SUN_RADIUS_KM),('lunar_radius',MOON_RADIUS_KM))),
        quantity('requested_time_tolerance',tolerance*86400,'seconds'),
        quantity('requested_width_interval_span',width_tolerance,'km'))
    return EclipseEvidence('solar',requested_time,tuple(result[p] for p in PRODUCTS),
        tuple(sorted(counters.items())),configuration=configuration)
