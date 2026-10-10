"""Bounded marriage partition, shared evidence registry and boundary ownership.

All decisions still come from the canonical instant evaluator. Numerical
admission is separate from candidate discovery: an uncertified cell cannot
advertise constant findings or an eligible interval.
"""
from dataclasses import dataclass, replace
from datetime import datetime
from math import ceil, floor

from ._muhurta_marriage_search import MarriageSearchBudgetError, WorkMeter, borrow_marriage_reader
from .muhurta_marriage import (MarriageElectionEvidence, MarriageElectionPolicy, MarriagePersonalContext,
    MarriageFinding, MarriageDecision, MarriageElectionAssessment, _number, _tuple, _decision)
from .muhurta_marriage_dated import (_Context, _admit, _retain_numerical_gap, _check_output, MarriageSearchReceipt)
from .panchanga_shuddhi import ShuddhiBoundary, ShuddhiInterval, _point
from .muhurta_marriage_visibility import _BUFFERS
from ._muhurta_marriage_sources import NINE, SEVEN, INGRESS_TOTAL_GHATIS
from .muhurta_marriage import assess_marriage_election
from .muhurta_dosha import _shift
from .spk_reader import get_reader, use_reader_override, MissingKernelError, OutOfRangeError
from ._ephemeris_time import _EphemerisTimeBasisError
from .muhurta_search import MuhurtaResourceError, MuhurtaCoverageError
from .julian import utc_to_ut1, jd_from_datetime
from .avasthas import _COMBUSTION_ORB_DEG


# The reference order is fixed and transported verbatim. Each value retains its
# exact engine type. Position and epoch values stay attached to their own sample.
_PART_NAMES = ('solar','phase_spans','yoga_span','karana_span','lunar_month','ingress_history',
               'star_history','yoga_endings','jupiter_apparition','venus_apparition')


@dataclass(frozen=True, slots=True)
class MarriageEvidencePart:
    """Typed immutable parent evidence interned once in a window result."""
    kind: str
    value: object

    def __post_init__(self):
        if self.kind not in _PART_NAMES or self.value is None:
            raise ValueError('evidence part requires a named non-null component')
        # Canonical evidence admission owns component types and immutability.
        # It deliberately cannot validate cross-component chronology until the
        # cell resolves all of its references together.
        from .muhurta_marriage import (MarriageSolarContext,MarriageIngressHistory,MarriageStarHistory,MarriageYogaEnding)
        from .muhurta_dosha import DoshaPhaseSpan
        from .lunar_month import LunarMonthResult
        from .muhurta_marriage_visibility import MarriageApparitionContext
        types={'solar':MarriageSolarContext,'yoga_span':ShuddhiInterval,
               'karana_span':ShuddhiInterval,'lunar_month':LunarMonthResult,
               'ingress_history':MarriageIngressHistory,'star_history':MarriageStarHistory,
               'jupiter_apparition':MarriageApparitionContext,'venus_apparition':MarriageApparitionContext}
        if self.kind in ('phase_spans','yoga_endings'):
            _tuple(self.kind,self.value,DoshaPhaseSpan if self.kind=='phase_spans' else MarriageYogaEnding,64)
        elif not isinstance(self.value,types[self.kind]):
            raise ValueError('evidence part has the wrong canonical component type')


@dataclass(frozen=True, slots=True)
class MarriageWindowWitness:
    """Raw election coordinates and references to immutable shared parents."""
    jd_ut1: float
    planets: tuple
    lagna_sidereal_longitude: float | None
    part_references: tuple[int | None, ...]

    def __post_init__(self):
        _number('jd_ut1',self.jd_ut1)
        if type(self.part_references) is not tuple or len(self.part_references)!=len(_PART_NAMES):
            raise ValueError('witness requires every named component reference slot')
        if any(x is not None and (type(x) is not int or x<0) for x in self.part_references):
            raise ValueError('evidence references must be nonnegative integers or None')
        MarriageElectionEvidence(self.jd_ut1,self.planets,self.lagna_sidereal_longitude)

    def resolve(self,parts,policy):
        values={}
        for kind,index in zip(_PART_NAMES,self.part_references):
            if index is None:
                continue
            if index>=len(parts) or parts[index].kind!=kind:
                raise ValueError('dangling or mismatched evidence reference')
            values[kind]=parts[index].value
        return MarriageElectionEvidence(self.jd_ut1,self.planets,self.lagna_sidereal_longitude,
                                         ayanamsa_system=policy.ayanamsa_system,**values)


@dataclass(frozen=True, slots=True)
class MarriageElectionCell:
    """Half-open interval, raw witness, finding references and explicit constancy admission."""
    interval: ShuddhiInterval
    witness: MarriageWindowWitness
    astronomical_finding_refs: tuple[int,...]
    personal_finding_refs: tuple[int,...]
    composition_finding_refs: tuple[int,...]
    astronomical: MarriageDecision
    personal_decision: MarriageDecision
    requested_composition: MarriageDecision
    constancy_certified: bool

    def __post_init__(self):
        if not isinstance(self.interval,ShuddhiInterval) or not isinstance(self.witness,MarriageWindowWitness):
            raise ValueError('cell requires typed interval and raw witness')
        if self.interval.contains(self.witness.jd_ut1) is not True:
            raise ValueError('cell witness must be strictly outside transition bands')
        if type(self.constancy_certified) is not bool:
            raise ValueError('cell constancy must be boolean')
        for name in ('astronomical_finding_refs','personal_finding_refs','composition_finding_refs'):
            refs=getattr(self,name)
            if type(refs) is not tuple or any(type(x) is not int or x<0 for x in refs) or len(refs)!=len(set(refs)):
                raise ValueError('finding references must be unique nonnegative integers')
        if not self.constancy_certified and self.requested_composition.status=='passes_selected_profile':
            raise ValueError('uncertified cell cannot be an eligible interval')


@dataclass(frozen=True, slots=True)
class MarriageElectionWindows:
    """Lossless interval partition with shared evidence, uncertainty bands and work receipt."""
    start: datetime
    end: datetime
    start_jd_ut1: float
    end_jd_ut1: float
    latitude: float
    longitude: float
    timezone: str
    policy: MarriageElectionPolicy
    personal: MarriagePersonalContext | None
    evidence_parts: tuple[MarriageEvidencePart,...]
    findings: tuple[MarriageFinding,...]
    cells: tuple[MarriageElectionCell,...]
    transition_bands: tuple[ShuddhiBoundary,...]
    kernel_label: str
    reader_binding: str
    search_receipt: MarriageSearchReceipt
    boundary_ownership: str = 'half_open_UT1; all_nonzero_root_bands_unresolved'

    def __post_init__(self):
        if not self.start_jd_ut1<self.end_jd_ut1:
            raise ValueError('window range must be positive')
        _tuple('evidence_parts',self.evidence_parts,MarriageEvidencePart,32768)
        _tuple('findings',self.findings,MarriageFinding,65536)
        _tuple('cells',self.cells,MarriageElectionCell,4096)
        _tuple('transition_bands',self.transition_bands,ShuddhiBoundary,16386)
        if not self.transition_bands or self.transition_bands[0].lower_jd_ut1!=self.start_jd_ut1 or self.transition_bands[-1].upper_jd_ut1!=self.end_jd_ut1:
            raise ValueError('partition must retain both requested range edges')
        if any(a.upper_jd_ut1>=b.lower_jd_ut1 for a,b in zip(self.transition_bands,self.transition_bands[1:])):
            raise ValueError('transition bands must be ordered, disjoint and maximally merged')
        if (any(c.constancy_certified for c in self.cells) and
                self.search_receipt.crossing_completeness!='complete_under_declared_arithmetic_model'):
            raise ValueError('certified cells require a complete numerical receipt')
        expected=tuple((a,b) for a,b in zip(self.transition_bands,self.transition_bands[1:]) if a.upper_jd_ut1<b.lower_jd_ut1)
        if tuple((c.interval.start,c.interval.end) for c in self.cells)!=expected:
            raise ValueError('cells and uncertainty bands must cover the requested range without gaps or overlap')
        for cell in self.cells:
            cell.witness.resolve(self.evidence_parts,self.policy)
            groups=[]
            for refs in (cell.astronomical_finding_refs,cell.personal_finding_refs,cell.composition_finding_refs):
                if any(x>=len(self.findings) for x in refs):
                    raise ValueError('dangling finding reference')
                groups.append(tuple(self.findings[x] for x in refs))
            if (cell.astronomical!=_decision(groups[0]) or cell.personal_decision!=_decision(groups[1],self.personal is not None)
                    or cell.requested_composition!=_decision(groups[2]+groups[1])):
                raise ValueError('cell decisions disagree with retained findings')
        referenced_parts={r for c in self.cells for r in c.witness.part_references if r is not None}
        referenced_findings={r for c in self.cells for group in (c.astronomical_finding_refs,c.personal_finding_refs,c.composition_finding_refs) for r in group}
        if referenced_parts!=set(range(len(self.evidence_parts))) or referenced_findings!=set(range(len(self.findings))):
            raise ValueError('shared registries cannot contain orphaned evidence or findings')

    def assessment(self,index):
        """Reconstruct the lossless canonical assessment at one cell witness."""
        if type(index) is not int or not 0<=index<len(self.cells):
            raise ValueError('invalid cell index')
        cell=self.cells[index]
        groups=tuple(tuple(self.findings[i] for i in refs) for refs in
            (cell.astronomical_finding_refs,cell.personal_finding_refs,cell.composition_finding_refs))
        return MarriageElectionAssessment(self.policy,cell.witness.resolve(self.evidence_parts,self.policy),self.personal,
            *groups,cell.astronomical,cell.personal_decision,cell.requested_composition,
            input_basis='serving_reader_derived; interval_witness')

    @property
    def eligible_intervals(self):
        """Qualified interiors; the retained endpoint bands remain uncertain."""
        return tuple(c.interval for c in self.cells if c.constancy_certified and
                     c.requested_composition.status=='passes_selected_profile')

    @property
    def indeterminate_cell_indices(self):
        return tuple(i for i,c in enumerate(self.cells) if not c.constancy_certified or
                     c.requested_composition.status=='indeterminate')

    def at(self,jd_ut1):
        """Certified rule states only; root bands and uncertified cells return None."""
        jd=_number('jd_ut1',jd_ut1)
        for index,cell in enumerate(self.cells):
            if cell.constancy_certified and cell.interval.contains(jd) is True:
                return self.assessment(index)
        return None


def admit_window(start,end,latitude,longitude,timezone,policy,personal,limits):
    admitted=_admit(start,latitude,longitude,timezone,policy,personal,limits)
    _admit(end,latitude,longitude,timezone,policy,personal,admitted[3])
    # Offset-aware datetime comparison is normalized by the canonical JD path,
    # avoiding Python's same-zone fold comparison shortcut.
    lo,hi=(utc_to_ut1(jd_from_datetime(x)) for x in (start,end))
    if lo>=hi:
        raise ValueError('marriage window requires start before end')
    if hi-lo>admitted[3].max_range_days:
        raise MarriageSearchBudgetError('range_days',admitted[3].max_range_days,hi-lo,'preflight')
    return (*admitted,lo,hi)


def _candidate_boundaries(context,lo,hi):
    meter=context.meter
    boundaries=[_point('range_start',lo),_point('range_end',hi)]
    # 108 ordinary physical padas/navamsas and the unequal Abhijit quartiles.
    targets=tuple(sorted(set([i*360/108 for i in range(108)]+[830/3+i*(2528/9-830/3)/4 for i in range(5)])))
    meter.stage='window_discrete_transitions'
    for planet in NINE:
        selected=tuple(sorted(set(targets+tuple(float(i) for i in range(360))))) if planet=='Sun' else targets
        roots=context.angular(((planet,1),),lo,hi,selected,min(1.,hi-lo),planet+'_discrete')
        boundaries.extend(r.boundary for r in roots)
    if context.lagna((lo+hi)/2) is not None:
        boundaries.extend(r.boundary for r in context.angular((('Lagna',1),),lo,hi,targets,
            min(1/24,hi-lo),'lagna_discrete'))
    else:
        # Point unavailability is not a full-domain constancy certificate;
        # seasonal obliquity can move the admitted subpolar boundary.
        context.reasons.append('lagna_domain_not_certified_for_window')
    for planet in SEVEN:
        if planet=='Sun':
            continue
        orb=_COMBUSTION_ORB_DEG.get(planet,10.)
        extra=(0.,180.) if planet=='Moon' else ()
        boundaries.extend(r.boundary for r in context.angular(((planet,1),('Sun',-1)),lo,hi,(orb,360-orb,*extra),
            min(1.,hi-lo),'combustion_'+planet))
    for planet in NINE:
        scan=context.certifier.scalar(lambda a,b,c,p=planet:context.certifier.station(p,a,b,c),lo,hi,min(1.,hi-lo),'motion_'+planet)
        context.reasons.extend('motion_'+planet+':'+reason for _,_,reason in scan.unresolved)
        for root in scan.roots:
            meter.tick('transitions')
            boundaries.append(ShuddhiBoundary('motion_station_'+planet,(root.lower+root.upper)/2,root.lower,root.upper))
    # Full phase parents, including their rational fixed/relative exclusions,
    # are resolved before clipping to the requested range.
    for day in range(floor(lo),ceil(hi)):
        roots,parents,_=context.phase_roots(day)
        boundaries.extend(b for values in roots.values() for b in values)
        boundaries.extend(b for spans in parents.values() for s in spans for b in (s.interval.start,s.interval.end))
    evidence=context.evidence((lo+hi)/2)
    # Calendar-owner and Panchanga solvers can enclose the same physical root
    # with different brackets. Retain both; their union owns the uncertainty.
    for _,_,phases,ingresses in context.months:
        boundaries.extend(ShuddhiBoundary('calendar_'+b.kind,b.jd_ut1,b.lower_jd_ut1,b.upper_jd_ut1)
                          for b in (*phases,*ingresses))
    history=evidence.ingress_history
    widths=dict(INGRESS_TOTAL_GHATIS)
    for event in history.events:
        pad=widths[event.planet]/120
        boundaries.extend((_shift(event.boundary,-pad,'ingress_buffer_start'),_shift(event.boundary,pad,'ingress_buffer_end')))
        if event.planet=='Sun':
            if event.cardinal_solar_days is not None:
                boundaries.extend((event.cardinal_solar_days.start,event.cardinal_solar_days.end))
            elif event.entered_sign not in (0,3,6,9):
                boundaries.extend((_shift(event.boundary,-16/60,'solar_buffer_start'),_shift(event.boundary,16/60,'solar_buffer_end')))
    for planet,events in context.apparition_events.items():
        for event in events:
            boundaries.append(event.boundary)
            post,pre=_BUFFERS[(planet,event.side)]
            shift=post if event.role=='appearance' else -pre
            boundaries.append(_shift(event.boundary,shift,'availability_waiting_period'))
    for passage in evidence.star_history.passages:
        boundaries.extend((passage.entry,passage.exit))
    for passage in evidence.star_history.moon28_passages:
        boundaries.extend((passage.entry,passage.exit))
    boundaries.extend(b.boundary for b in evidence.star_history.transition_bands)
    for day in range(floor(lo)-1,ceil(hi)+1):
        solar=context.solar_context(day+.5)
        if solar is not None:
            boundaries.extend((solar.day.start,solar.sunset,solar.day.end))
            if solar.half_set is not None:
                boundaries.extend((_shift(solar.half_set,-.5/60,'godhuli_start'),_shift(solar.half_set,.5/60,'godhuli_end')))
            if solar.upper_limb_set is not None:
                boundaries.append(solar.upper_limb_set)
    return boundaries


def _clipped_bands(boundaries,lo,hi):
    result=[]
    for b in boundaries:
        a,z=max(lo,b.lower_jd_ut1),min(hi,b.upper_jd_ut1)
        if a<=z:
            result.append(ShuddhiBoundary(b.kind,min(z,max(a,b.jd_ut1)),a,z))
    merged=[]
    for item in sorted(result,key=lambda b:b.lower_jd_ut1):
        if merged and item.lower_jd_ut1<=merged[-1].upper_jd_ut1:
            previous=merged.pop()
            a,z=previous.lower_jd_ut1,max(previous.upper_jd_ut1,item.upper_jd_ut1)
            kinds=tuple(dict.fromkeys((*previous.kind.split('+'),*item.kind.split('+'))))
            merged.append(ShuddhiBoundary('+'.join(kinds),(a+z)/2,a,z))
        else:
            merged.append(item)
    return tuple(merged)


def _derived_boundaries(assessment):
    """Read solved parent-derived rule edges; values never substitute a verdict."""
    for f in assessment.astronomical_findings:
        by_name={m.name:m.value for m in f.measures if m.unit=='JD_UT1'}
        for name,a in by_name.items():
            if not name.endswith('_lower'):
                continue
            z=by_name.get(name[:-6]+'_upper')
            if z is not None and a<=z:
                yield ShuddhiBoundary(f.rule_id+':'+name[:-6],(a+z)/2,a,z)


def _compose(context,start,end,lo,hi,personal,binding):
    context.range_anchor=(lo+hi)/2
    context.range_radius=(hi-lo)/2
    boundaries=_candidate_boundaries(context,lo,hi)
    initial=_clipped_bands(boundaries,lo,hi)
    # One representative per original parent cell is sufficient to enumerate
    # its algebraically derived edges. These are then partitioned again.
    for a,b in zip(initial,initial[1:]):
        if a.upper_jd_ut1>=b.lower_jd_ut1:
            continue
        sample=(a.upper_jd_ut1+b.lower_jd_ut1)/2
        assessment=assess_marriage_election(context.evidence(sample),policy=context.policy,personal=personal)
        boundaries.extend(_derived_boundaries(assessment))
    bands=_clipped_bands(boundaries,lo,hi)
    context.certifier.maximum_boundary_width_seconds=max(context.certifier.maximum_boundary_width_seconds,
        max((b.upper_jd_ut1-b.lower_jd_ut1)*86400 for b in bands))
    parts,part_index,findings,finding_index,cells=[],{},[],{},[]
    pending=[]
    def intern_part(kind,value):
        if value is None or value==():
            return None
        key=MarriageEvidencePart(kind,value)
        if key not in part_index:
            _check_output(key,context.meter,additional=True)
            part_index[key]=len(parts)
            parts.append(key)
        return part_index[key]
    def intern_findings(rows):
        refs=[]
        for f in rows:
            if f not in finding_index:
                _check_output(f,context.meter,additional=True)
                finding_index[f]=len(findings)
                findings.append(f)
            refs.append(finding_index[f])
        return tuple(refs)
    for a,b in zip(bands,bands[1:]):
        if a.upper_jd_ut1>=b.lower_jd_ut1:
            continue
        context.meter.tick('cells')
        jd=(a.upper_jd_ut1+b.lower_jd_ut1)/2
        evidence=context.evidence(jd)
        assessment=assess_marriage_election(evidence,policy=context.policy,personal=personal)
        witness=MarriageWindowWitness(jd,evidence.planets,evidence.lagna_sidereal_longitude,
            tuple(intern_part(name,getattr(evidence,name)) for name in _PART_NAMES))
        pending.append((a,b,witness,assessment))
        # Check retained evidence and cells while constructing the response,
        # before accumulating an unbounded serialization workload.
        _check_output((a,b,witness,assessment.astronomical,assessment.personal_decision,
                       assessment.requested_composition),context.meter,additional=True)
    receipt=context.receipt()
    certified=receipt.crossing_completeness=='complete_under_declared_arithmetic_model'
    for a,b,witness,assessment in pending:
        assessment=_retain_numerical_gap(assessment,receipt)
        refs=tuple(intern_findings(getattr(assessment,name)) for name in
                   ('astronomical_findings','personal_findings','composition_findings'))
        cells.append(MarriageElectionCell(ShuddhiInterval(a,b),witness,*refs,assessment.astronomical,
            assessment.personal_decision,assessment.requested_composition,certified))
    epoch=context.epoch((lo+hi)/2)
    return MarriageElectionWindows(start,end,lo,hi,context.latitude,context.longitude,context.timezone,
        context.policy,personal,tuple(parts),tuple(findings),tuple(cells),bands,epoch.identity.summary_label,
        binding,context.receipt())


def marriage_election_windows(start,end,latitude,longitude,*,timezone,policy,personal=None,limits=None,reader=None):
    """Partition a bounded half-open range with original boundary uncertainty."""
    lat,lon,zone,active,lo,hi=admit_window(start,end,latitude,longitude,timezone,policy,personal,limits)
    meter=WorkMeter(active)
    try:
        serving=get_reader() if reader is None else reader
        with borrow_marriage_reader(serving,meter) as borrowed, use_reader_override(borrowed):
            context=_Context(borrowed,meter,lat,lon,zone,timezone,policy)
            result=_compose(context,start,end,lo,hi,personal,'discovered_reader' if reader is None else 'caller_owned_reader')
            _check_output(result,meter)
            return replace(result,search_receipt=context.receipt())
    except OutOfRangeError as exc:
        raise MuhurtaCoverageError('marriage range or supporting parent/history exceeds serving coverage') from exc
    except (MissingKernelError,_EphemerisTimeBasisError,FileNotFoundError) as exc:
        raise MuhurtaResourceError('marriage requires the serving planetary and clock resources') from exc
