"""Complete bounded coverage of represented binary64 native solar inputs.

The real reference and the serving program have different domains: the latter
receives finite binary64 Julian days. Whole-interval serving enclosures prove
uniform phases or exclusion. Every remaining represented input in a narrow
cell is evaluated exhaustively, never sampled. This closes numerical branch
and endpoint cells without asserting that a rounded program is continuous.
Source/build/environment stability is a separate caller obligation.
"""
from dataclasses import dataclass
from fractions import Fraction as F
import math
import struct

from ._eclipse_interval import RationalInterval as I
from ._eclipse_interval_roots import EnclosureUnavailable


@dataclass(frozen=True, slots=True)
class SolarFloatCoverageCell:
    """A closed real box and coverage of its represented input subset."""

    domain: I
    first_jd: float | None
    last_jd: float | None
    state: str
    method: str


@dataclass(frozen=True, slots=True)
class SolarFloatPathCoverage:
    """Native-input completeness, independent of real/physical certification."""

    ut1_anchor_jd: float
    domain: I
    cells: tuple[SolarFloatCoverageCell,...]
    status: str
    sequence: tuple[str,...]
    subtype: str | None
    components: tuple[tuple[tuple[float,float],tuple[float,float]],...]
    all_represented_inputs_covered: bool
    event_interval_enclosed: bool
    interval_evaluations: int
    point_evaluations: int
    max_interval_evaluations: int
    max_point_evaluations: int
    real_continuity_claimed: bool = False
    physical_accuracy_certified: bool = False


def _key(value):
    bits = struct.unpack('>Q',struct.pack('>d',value))[0]
    return (~bits & ((1<<64)-1)) if bits>>63 else bits^(1<<63)


def _value(key):
    bits = key^(1<<63) if key>>63 else ~key & ((1<<64)-1)
    return struct.unpack('>d',struct.pack('>Q',bits))[0]


def represented_solar_inputs(anchor: float, domain: I):
    """Return the first/last finite represented absolute JD in a real box."""
    absolute = I.point(anchor)+domain
    lower,upper = absolute.to_float_bounds()
    if F.from_float(lower)<absolute.lo:
        lower = math.nextafter(lower,math.inf)
    if F.from_float(upper)>absolute.hi:
        upper = math.nextafter(upper,-math.inf)
    if lower>upper:
        return None,None
    if not math.isfinite(lower) or not math.isfinite(upper):
        raise ValueError('finite native input domain required')
    return lower,upper


def cover_native_solar_float_path(anchor: float, domain: I, enclosure, evaluate, *,
                                   tolerance=F(1,86400000), max_interval_evaluations=4096,
                                   max_point_evaluations=4096, max_depth=80):
    """Cover every binary64 UT1 input, retaining budget failures explicitly.

    ``evaluate`` must execute the same stable serving source described by the
    enclosure and return none/annular/total/zero_radius. Missing resources or
    numeric exceptions propagate. The caller must establish source, tables,
    reader and arithmetic premises before accepting this result. A subtype
    requires complete complementary coverage and exactly one legal component.
    """
    if isinstance(anchor,bool) or not isinstance(anchor,(int,float)) or not math.isfinite(anchor):
        raise ValueError('finite represented anchor required')
    if not isinstance(domain,I):
        raise TypeError('exact UT1 offset domain required')
    tolerance = I.point(tolerance)
    if tolerance.lo!=tolerance.hi or tolerance.lo<=0:
        raise ValueError('positive exact tolerance required')
    if any(type(v) is not int or v<0 for v in (max_interval_evaluations,max_point_evaluations,max_depth)):
        raise ValueError('finite nonnegative integer budgets required')
    stack,cells,interval_calls,points = [(domain,0)],[],0,{}

    def state_at(jd):
        if jd not in points:
            if len(points)>=max_point_evaluations:
                raise EnclosureUnavailable('point_evaluation_budget_exhausted')
            state = evaluate(jd)
            if state not in ('none','annular','total','zero_radius'):
                raise TypeError('native solar evaluator returned an unsupported state')
            points[jd] = state
        return points[jd]

    while stack:
        box,depth = stack.pop()
        first,last = represented_solar_inputs(anchor,box)
        if first is None:
            cells.append(SolarFloatCoverageCell(box,None,None,'empty','no_represented_input'))
            continue
        reason = 'unresolved_native_predicate'
        try:
            if interval_calls>=max_interval_evaluations:
                raise EnclosureUnavailable('interval_evaluation_budget_exhausted')
            interval_calls += 1
            bounds = enclosure(box)
            if bounds.domain!=box:
                raise TypeError('source enclosure lost the exact UT1 domain')
            if bounds.axis_margin.hi<0 or (bounds.daylight_margin is not None and bounds.daylight_margin.hi<=0):
                state = 'none'
            elif (bounds.axis_margin.lo>=0 and bounds.forward_margin is not None and bounds.forward_margin.lo>0
                    and bounds.daylight_margin is not None and bounds.daylight_margin.lo>0
                    and bounds.signed_radius is not None and not bounds.signed_radius.contains_zero):
                state = 'total' if bounds.signed_radius.lo>0 else 'annular'
            else:
                state = None
            if state is not None:
                # Endpoints corroborate each accepted enclosure and detect a
                # mismatched source adapter immediately; they are not the proof
                # of the interior, which is the complete interval enclosure.
                if state_at(first)!=state or state_at(last)!=state:
                    raise ArithmeticError('serving endpoint disagrees with its interval inclusion')
                cells.append(SolarFloatCoverageCell(box,first,last,state,'whole_interval_serving_bound'))
                continue
        except EnclosureUnavailable as exc:
            reason = str(exc)
        if box.width<=tolerance.hi or depth>=max_depth or _key(last)-_key(first)<=4:
            count = _key(last)-_key(first)+1
            needed = sum(_value(key) not in points for key in range(_key(first),_key(last)+1)) if count<=max_point_evaluations else count
            if needed<=max_point_evaluations-len(points):
                for key in range(_key(first),_key(last)+1):
                    jd = _value(key)
                    state = state_at(jd)
                    offset = I.point(F.from_float(jd)-F.from_float(anchor))
                    cells.append(SolarFloatCoverageCell(offset,jd,jd,state,'exhaustive_represented_input'))
                continue
            cells.append(SolarFloatCoverageCell(box,first,last,'unresolved',reason+'; point_budget'))
            continue
        if interval_calls>=max_interval_evaluations:
            cells.append(SolarFloatCoverageCell(box,first,last,'unresolved',reason))
            continue
        middle = box.midpoint
        stack.extend(((I(middle,box.hi),depth+1),(I(box.lo,middle),depth+1)))

    cells.sort(key=lambda cell:(float('inf') if cell.first_jd is None else cell.first_jd,
                                float('inf') if cell.last_jd is None else cell.last_jd))
    represented = [cell for cell in cells if cell.first_jd is not None]
    if any(cell.state=='unresolved' for cell in represented):
        seen = {cell.state for cell in represented if cell.state in ('annular','total')}
        return SolarFloatPathCoverage(float(anchor),domain,tuple(cells),
            'hybrid' if len(seen)==2 else 'unresolved',(),None,(),False,False,
            interval_calls,len(points),max_interval_evaluations,max_point_evaluations)
    runs = []
    for cell in represented:
        if runs and _key(cell.first_jd)<=_key(runs[-1][2]):
            if cell.state!=runs[-1][0]:
                raise ArithmeticError('overlapping represented coverage states disagree')
            runs[-1] = (cell.state,runs[-1][1],max(runs[-1][2],cell.last_jd))
        elif runs and _key(cell.first_jd)==_key(runs[-1][2])+1 and cell.state==runs[-1][0]:
            runs[-1] = (cell.state,runs[-1][1],cell.last_jd)
        else:
            runs.append((cell.state,cell.first_jd,cell.last_jd))
    first,last = represented_solar_inputs(anchor,domain)
    complete = not any(cell.state=='unresolved' for cell in represented)
    if first is not None:
        complete = complete and bool(runs) and runs[0][1]==first and runs[-1][2]==last
        complete = complete and all(_key(a[2])+1==_key(b[1]) for a,b in zip(runs,runs[1:]))
    components,active,sequence = [],None,[]
    enclosed = complete and bool(runs) and runs[0][0]==runs[-1][0]=='none'
    for index,(state,start,end) in enumerate(runs):
        if state in ('annular','total','zero_radius'):
            if active is None:
                if index==0:
                    enclosed = False
                    active = (start,start)
                else:
                    active = (runs[index-1][2],start)
            if state!='zero_radius' and (not sequence or sequence[-1]!=state):
                sequence.append(state)
        elif active is not None:
            components.append((active,(runs[index-1][2],start)))
            active = None
    if active is not None:
        enclosed = False
    seen = {state for state,_,_ in runs if state in ('annular','total')}
    status = ('hybrid' if len(seen)==2 else next(iter(seen)) if len(seen)==1 and complete
              else 'zero_radius_axis' if complete and any(state=='zero_radius' for state,_,_ in runs)
              else 'no_legal_axis' if complete and not seen else 'unresolved')
    subtype = None
    if enclosed and len(components)==1:
        subtype = {('annular','total','annular'):'H1',('total','annular'):'H2',
                   ('annular','total'):'H3'}.get(tuple(sequence))
    return SolarFloatPathCoverage(float(anchor),domain,tuple(cells),status,tuple(sequence),subtype,
        tuple(components),bool(complete),bool(enclosed),interval_calls,len(points),
        max_interval_evaluations,max_point_evaluations)
