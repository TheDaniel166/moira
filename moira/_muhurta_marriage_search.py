"""Request-scoped bounded work and numerical event candidates for marriage.

Candidate discovery is explicitly separate from interval certification. No
sampled derivative or scan step is promoted to an analytic motion certificate.
"""
from dataclasses import dataclass
from contextlib import contextmanager
from math import ceil, floor, isfinite

from .panchanga_shuddhi import _number, _integer, ShuddhiBoundary


SEARCH_HARD_MAXIMA=(('max_evaluations',400000),('max_reader_calls',4000000),
    ('max_history_days',4096),('max_cells',4096),('max_transitions',16384),
    ('max_range_days',31),('max_output_bytes',32000000),
    ('max_root_iterations',200000),('max_historical_cells',4096))
MINIMUM_PARENT_HISTORY_DAYS=65


class MarriageSearchBudgetError(ValueError):
    """A deterministic work limit was reached; no complete partial result exists."""
    def __init__(self, kind, limit, count, stage):
        self.limit_kind, self.limit, self.count, self.stage = kind, limit, count, stage
        super().__init__(f'marriage {kind} budget exceeded at {stage}: {count} > {limit}')


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


class WorkMeter:
    """RITE: Request work ownership

    THEOREM: Count each bounded unit of evaluation, reader, root, transition, cell and output work.

    RITE OF PURPOSE:
        Count each bounded unit of evaluation, reader, root, transition, cell and output work.

    LAW OF OPERATION:
        Dependencies: immutable request limits.
        Mutable caches and counters belong to one request; computational calls
        remain on its owning thread. Only returned immutable evidence is shared.
        No resource ownership transfers and no missing evidence becomes success.

    Canon: MarriageSearchLimits and deterministic MarriageSearchBudgetError semantics.

    One meter shared by all subcalculations and borrowed reader operations.

    [MACHINE_CONTRACT v1]
    {
      "scope": "class",
      "id": "moira._muhurta_marriage_search.WorkMeter",
      "risk": "medium",
      "api": {
        "frozen": [],
        "internal": [
          "__init__",
          "tick"
        ]
      },
      "state": {
        "mutable": true,
        "owners": [
          "one computation request"
        ]
      },
      "effects": {
        "signals_emitted": [],
        "io": []
      },
      "concurrency": {
        "thread": "pure_computation",
        "cross_thread_calls": "safe_read_only",
        "owner_thread_only_mutation": true
      },
      "failures": {
        "policy": "raise typed input, resource, enclosure or budget failures; preserve scientific gaps"
      },
      "succession": {
        "stance": "terminal"
      },
      "agent": {
        "autofix": "allowed",
        "requires_human_for": [
          "public doctrine changes"
        ]
      }
    }
    [/MACHINE_CONTRACT]"""
    def __init__(self, limits):
        if not isinstance(limits,MarriageSearchLimits):
            raise ValueError('limits must be MarriageSearchLimits')
        self.limits = limits
        self.counts = {'evaluations':0,'reader_calls':0,'transitions':0,'cells':0,'output_bytes':0,
                       'root_iterations':0,'historical_cells':0}
        self.stage = 'preflight'

    def tick(self, kind, amount=1):
        self.counts[kind] += amount
        maximum = getattr(self.limits,'max_'+kind)
        if self.counts[kind] > maximum:
            raise MarriageSearchBudgetError(kind,maximum,self.counts[kind],self.stage)


class MeteredReader:
    """RITE: Borrowed-reader accounting

    THEOREM: Delegate computations to the serving reader while charging the request meter and rejecting closure.

    RITE OF PURPOSE:
        Delegate computations to the serving reader while charging the request meter and rejecting closure.

    LAW OF OPERATION:
        Dependencies: borrowed reader, request work meter.
        Mutable caches and counters belong to one request; computational calls
        remain on its owning thread. Only returned immutable evidence is shared.
        No resource ownership transfers and no missing evidence becomes success.

    Canon: Borrowed resource lifetime and serving-reader identity.

    Borrow a reader and meter its public computational entry points.

    Resource identity/coverage are delegated unchanged. This proxy owns no
    resource and cannot close or mutate the caller's reader. Evaluator closures
    are wrapped as well, preventing lower-level fast paths escaping the meter.

    [MACHINE_CONTRACT v1]
    {
      "scope": "class",
      "id": "moira._muhurta_marriage_search.MeteredReader",
      "risk": "medium",
      "api": {
        "frozen": [],
        "internal": [
          "__init__",
          "__getattr__",
          "close"
        ]
      },
      "state": {
        "mutable": true,
        "owners": [
          "one computation request"
        ]
      },
      "effects": {
        "signals_emitted": [],
        "io": [
          "borrowed reader and source-table access"
        ]
      },
      "concurrency": {
        "thread": "pure_computation",
        "cross_thread_calls": "safe_read_only",
        "owner_thread_only_mutation": true
      },
      "failures": {
        "policy": "raise typed input, resource, enclosure or budget failures; preserve scientific gaps"
      },
      "succession": {
        "stance": "terminal"
      },
      "agent": {
        "autofix": "allowed",
        "requires_human_for": [
          "public doctrine changes"
        ]
      }
    }
    [/MACHINE_CONTRACT]"""
    _CALLS = frozenset(('position','position_tdb','position_and_velocity',
        'position_and_velocity_tdb','position_and_velocity_tdb_with_receipt'))

    def __init__(self, reader, meter):
        self._reader, self._meter = reader,meter

    def __getattr__(self,name):
        if name=='_primary_planetary_reader':
            # Native bulk admission unwraps this accessor and would bypass
            # this request's meter and frozen route owner.
            raise AttributeError(name)
        value = getattr(self._reader,name)
        if name in self._CALLS:
            def call(*args,**kwargs):
                self._meter.tick('reader_calls')
                return value(*args,**kwargs)
            return call
        if name in ('evaluator','evaluator_tdb'):
            def evaluator(*args,**kwargs):
                original = value(*args,**kwargs)
                def call(*a,**k):
                    self._meter.tick('reader_calls')
                    return original(*a,**k)
                return call
            return evaluator
        return value

    def close(self):
        raise RuntimeError('marriage calculation borrows its reader and cannot close it')


@contextmanager
def borrow_marriage_reader(reader,meter):
    """Pin a pool's reader order while retaining the original lifetime lease.

    A lease alone protects close, but does not stop additions creating newer
    snapshots. The private pool below has its own frozen order and caches;
    it never closes any of its borrowed readers.
    """
    from .spk_reader import KernelPool
    if not isinstance(reader,KernelPool):
        yield MeteredReader(reader,meter)
        return
    class FrozenPool(KernelPool):
        """RITE: Pinned reader ordering

        THEOREM: Preserve the leased reader order while rejecting pool additions and resource closure.

        RITE OF PURPOSE:
            Preserve the leased reader order while rejecting pool additions and resource closure.

        LAW OF OPERATION:
            Dependencies: leased pool snapshot.
            Mutable caches and counters belong to one request; computational calls
            remain on its owning thread. Only returned immutable evidence is shared.
            No resource ownership transfers and no missing evidence becomes success.

        Canon: KernelPool snapshot lease; the original pool retains resource ownership.

        [MACHINE_CONTRACT v1]
        {
          "scope": "class",
          "id": "moira._muhurta_marriage_search.FrozenPool",
          "risk": "medium",
          "api": {
            "frozen": [],
            "internal": [
              "add",
              "close"
            ]
          },
          "state": {
            "mutable": true,
            "owners": [
              "one computation request"
            ]
          },
          "effects": {
            "signals_emitted": [],
            "io": [
              "borrowed reader and source-table access"
            ]
          },
          "concurrency": {
            "thread": "pure_computation",
            "cross_thread_calls": "safe_read_only",
            "owner_thread_only_mutation": true
          },
          "failures": {
            "policy": "raise typed input, resource, enclosure or budget failures; preserve scientific gaps"
          },
          "succession": {
            "stance": "terminal"
          },
          "agent": {
            "autofix": "allowed",
            "requires_human_for": [
              "public doctrine changes"
            ]
          }
        }
        [/MACHINE_CONTRACT]"""
        def add(self,reader):
            raise RuntimeError('marriage reader order is immutable')
        def close(self):
            raise RuntimeError('marriage pool does not own its readers')
    with reader._read_lease() as snapshot:
        pinned=FrozenPool(snapshot.readers)
        borrowed=MeteredReader(pinned,meter)
        borrowed.source_pool_generation=snapshot.generation
        yield borrowed


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
