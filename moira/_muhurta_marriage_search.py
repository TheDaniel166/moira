"""Request-scoped bounded work and numerical event candidates for marriage.

Candidate discovery is explicitly separate from interval certification. No
sampled derivative or scan step is promoted to an analytic motion certificate.
"""
from dataclasses import dataclass
from math import ceil, floor, isfinite
from ._event_search.budgets import SearchBudgetError, WorkMeter as _SharedWorkMeter
from ._event_search.resources import MeteredReader, borrow_reader as borrow_marriage_reader  # noqa: F401 -- compatibility exports

from .panchanga_shuddhi import _number, _integer, ShuddhiBoundary


SEARCH_HARD_MAXIMA=(('max_evaluations',400000),('max_reader_calls',4000000),
    ('max_history_days',4096),('max_cells',4096),('max_transitions',16384),
    ('max_range_days',31),('max_output_bytes',32000000),
    ('max_root_iterations',200000),('max_historical_cells',4096))
MINIMUM_PARENT_HISTORY_DAYS=65




class MarriageSearchBudgetError(SearchBudgetError):
    """Marriage's stable deterministic-budget error contract."""
    label = 'marriage'


@dataclass(frozen=True, slots=True)
class MarriageSearchLimits:
    """Finite request limits including supporting searches outside requested time."""
    max_evaluations: int = 300000
    max_reader_calls: int = 2000000
    max_history_days: int = 2048
    max_cells: int = 2048
    max_transitions: int = 8192
    max_range_days: int = 7
    max_output_bytes: int = 8000000
    max_root_iterations: int = 100000
    max_historical_cells: int = 4096

    def __post_init__(self):
        for name, maximum in SEARCH_HARD_MAXIMA:
            _integer(name,getattr(self,name),1,maximum)


class WorkMeter(_SharedWorkMeter):
    """Marriage admission adapter around request-owned neutral accounting."""
    def __init__(self, limits, *, budget_error=MarriageSearchBudgetError):
        if not isinstance(limits, MarriageSearchLimits):
            raise ValueError('limits must be MarriageSearchLimits')
        if not isinstance(budget_error, type) or not issubclass(budget_error, MarriageSearchBudgetError):
            raise ValueError('budget_error must preserve the canonical budget error contract')
        super().__init__(limits, budget_error=budget_error, kinds=(
            'evaluations', 'reader_calls', 'transitions', 'cells', 'output_bytes',
            'root_iterations', 'historical_cells'))




def bisect_crossing(function, low, high, tolerance_seconds, meter, kind):
    """Refine one witnessed directional crossing, retaining the full bracket."""
    left,right = function(low),function(high)
    if not isfinite(left) or not isfinite(right) or left*right > 0:
        raise ValueError('bisection requires a finite sign bracket')
    increasing = right > left
    for _ in range(80):
        if (high-low)*86400 <= tolerance_seconds:
            break
        meter.tick('root_iterations')
        mid = (low+high)/2
        if mid in (low,high):
            raise ValueError('floating-point event resolution exhausted')
        value = function(mid)
        if not isfinite(value):
            raise ValueError('event became unavailable inside root bracket')
        if (value < 0) == increasing:
            low,left = mid,value
        else:
            high,right = mid,value
    if (high-low)*86400 > tolerance_seconds:
        raise ValueError('event tolerance not reached')
    meter.tick('transitions')
    return ShuddhiBoundary(kind,(low+high)/2,low,high)


@dataclass(frozen=True, slots=True)
class AngularCandidate:
    """Witnessed angular crossing bracket, target and direction; not a completeness proof."""
    boundary: ShuddhiBoundary
    target_degrees: float
    direction: int


def angular_candidates(function, start, end, targets, step, tolerance, meter, kind):
    """Bidirectional candidate discovery with midpoint and motion reversals.

    Each result is a real refined crossing. Equal endpoint sectors do not
    suppress midpoint crossings. This routine intentionally makes NO claim of
    complete zero isolation; the window owner must use an independent enclosure
    certificate before labeling the intervals between candidates as constant.
    """
    _number('start',start)
    _number('end',end)
    if not start < end or not 0 < step <= end-start:
        raise ValueError('candidate scan requires a positive range and step')
    targets = tuple(sorted(set(targets)))
    if not targets or any(not 0 <= x < 360 for x in targets):
        raise ValueError('angular targets must be in [0,360)')
    roots = []
    def segment(a,b,va,vb,depth=0):
        delta = (vb-va+180)%360-180
        mid = (a+b)/2
        vm = function(mid)
        first = (vm-va+180)%360-180
        second = (vb-vm+180)%360-180
        if abs(delta) > 90 or first*second < 0 or abs(first+second-delta) > 1e-8:
            if depth >= 20 or (b-a)*86400 <= tolerance:
                return  # Retained by the independent unverified-search receipt.
            segment(a,mid,va,vm,depth+1)
            segment(mid,b,vm,vb,depth+1)
            return
        if delta == 0:
            return
        low,high = sorted((va,va+delta))
        for target in targets:
            for turn in range(floor((low-target)/360),ceil((high-target)/360)+1):
                unwrapped = target+360*turn
                if not low <= unwrapped <= high:
                    continue
                # A 180-degree residual cut cannot lie inside this <90-degree arc.
                def signal(t):
                    return (function(t)-target+180)%360-180
                if signal(a)*signal(b)>0:
                    continue
                root = bisect_crossing(signal,a,b,tolerance,meter,kind)
                if not roots or abs(root.jd_ut1-roots[-1].boundary.jd_ut1)*86400 > tolerance:
                    roots.append(AngularCandidate(root,target,1 if delta>0 else -1))
    a,va = start,function(start)
    while a < end:
        b = min(a+step,end)
        vb = function(b)
        segment(a,b,va,vb)
        a,va = b,vb
    return tuple(sorted(roots,key=lambda r:r.boundary.jd_ut1))
