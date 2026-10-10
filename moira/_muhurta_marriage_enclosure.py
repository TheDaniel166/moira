"""Outward-rounded polynomial enclosures for marriage event validation.

These private primitives certify the selected finite mathematical model, not
the accuracy of an ephemeris relative to nature. No sampled speed establishes
an enclosure. SPK coefficients are inspected from the exact serving native
evaluator, in bounded record batches, without reopening a kernel.
"""
from dataclasses import dataclass
from functools import lru_cache
from math import ceil, floor, inf, isfinite, nextafter, pi, sqrt, sin, cos, atan, acos, ulp


def _down(x):
    return nextafter(x, -inf)


def _up(x):
    return nextafter(x, inf)


@dataclass(frozen=True, slots=True)
class Interval:
    """Ordered closed binary64 enclosure with outward-rounded arithmetic operations."""
    lo: float
    hi: float

    def __post_init__(self):
        if not isfinite(self.lo) or not isfinite(self.hi) or self.lo > self.hi:
            raise ValueError('finite ordered interval required')

    @staticmethod
    def point(x):
        if isinstance(x, Interval):
            return x
        rounded=float(x)
        if type(x) is int and int(rounded)!=x:
            return Interval(_down(rounded),_up(rounded))
        return Interval(rounded,rounded)

    def __add__(self, other):
        y = self.point(other)
        return Interval(_down(self.lo + y.lo), _up(self.hi + y.hi))

    __radd__ = __add__

    def __neg__(self):
        return Interval(-self.hi, -self.lo)

    def __sub__(self, other):
        return self + -self.point(other)

    def __rsub__(self, other):
        return self.point(other) + -self

    def __mul__(self, other):
        y = self.point(other)
        products = (self.lo*y.lo, self.lo*y.hi, self.hi*y.lo, self.hi*y.hi)
        return Interval(_down(min(products)), _up(max(products)))

    __rmul__ = __mul__

    def __truediv__(self, other):
        y = self.point(other)
        if y.lo <= 0 <= y.hi:
            raise ValueError('interval denominator contains zero')
        return self * Interval(_down(1/y.hi), _up(1/y.lo))

    def __rtruediv__(self, other):
        return self.point(other) / self

    @property
    def magnitude(self):
        return max(abs(self.lo), abs(self.hi))

    def square(self):
        values = (self.lo*self.lo, self.hi*self.hi)
        return Interval(0. if self.lo <= 0 <= self.hi else max(0., _down(min(values))), _up(max(values)))

    def sqrt(self):
        if self.lo < 0:
            raise ValueError('square-root interval contains negative values')
        return Interval(max(0., _down(sqrt(self.lo))), _up(sqrt(self.hi)))

    def expand(self, radius):
        if not isfinite(radius) or radius < 0:
            raise ValueError('finite nonnegative radius required')
        return Interval(_down(self.lo-radius), _up(self.hi+radius))

    def sin(self):
        return _trig(self,False)

    def cos(self):
        return _trig(self,True)

    def atan(self):
        return Interval(_libm_point(atan,self.lo).lo,_libm_point(atan,self.hi).hi)

    def acos(self):
        if self.lo < -1 or self.hi > 1:
            raise ValueError('inverse cosine interval is outside [-1,1]')
        return Interval(_libm_point(acos,self.hi).lo,_libm_point(acos,self.lo).hi)


PI = Interval(_down(pi),_up(pi))
TAU = 2*PI
def _libm_point(function,x):
    """Conditional enclosure under the receipt's <=4-ulp libm model.

    Eight output ulps also cover an adjacent-binade change of ulp size.
    This uses the same declared premise as the serving-position guards;
    it does not assert a stronger platform-independent library contract.
    """
    value=function(x)
    return Interval.point(value).expand(8*ulp(value))


def _trig(x,cosine):
    """Endpoint enclosures plus EVERY possible internal extremum.

    Extremum indices use interval pi, including uncertain endpoint ownership.
    No range-reduced sampled slope establishes monotonicity or exclusion.
    """
    if x.hi-x.lo >= TAU.lo:
        return Interval(-1.,1.)
    indices=(x-(0. if cosine else PI/2))/PI
    if indices.hi-indices.lo>=4:
        return Interval(-1.,1.)
    a,b=(_libm_point(cos if cosine else sin,t) for t in (x.lo,x.hi))
    lo,hi=min(a.lo,b.lo),max(a.hi,b.hi)
    for k in range(ceil(indices.lo),floor(indices.hi)+1):
        if k%2:
            lo=-1.
        else:
            hi=1.
    return Interval(max(-1.,lo),min(1.,hi))


def _power(self,n):
    if type(n) is not int or n<0:
        raise ValueError('nonnegative integer interval exponent required')
    value=Interval.point(1.)
    base=self
    while n:
        if n%2:
            value=value*base
        base=base*base
        n//=2
    return value


Interval.__pow__ = _power


def atan2_interval(y,x):
    """Principal-angle rectangle enclosure; a branch cut remains explicit."""
    if x.lo>0:
        return (y/x).atan()
    if x.hi<0:
        if y.lo>=0:
            return (y/x).atan()+PI
        if y.hi<0:
            return (y/x).atan()-PI
        return Interval(-PI.hi,PI.hi)
    if y.lo>0:
        return PI/2-(x/y).atan()
    if y.hi<0:
        return -PI/2-(x/y).atan()
    return Interval(-PI.hi,PI.hi)


def polynomial(coefficients, x):
    """Horner enclosure, coefficients in ascending power order."""
    result = Interval.point(0.)
    for coefficient in reversed(coefficients):
        result = result*x + coefficient
    return result


def chebyshev(coefficients, s):
    """Clenshaw enclosure for ascending Chebyshev coefficients on [-1,1]."""
    if not coefficients or s.lo < -1 or s.hi > 1:
        raise ValueError('Chebyshev record and normalized domain required')
    first = second = Interval.point(0.)
    for c in reversed(coefficients[1:]):
        first, second = 2*s*first-second+c, first
    return s*first-second+coefficients[0]


def derivative_coefficients(coefficients):
    """Exact polynomial identity with outward-rounded coefficient arithmetic."""
    n = len(coefficients)-1
    if n <= 0:
        return (Interval.point(0.),)
    result = [Interval.point(0.) for _ in range(n+2)]
    for k in range(n-1, -1, -1):
        result[k] = result[k+2] + 2*(k+1)*Interval.point(coefficients[k+1])
    result[0] = result[0]/2
    return tuple(result[:n])


def derivative_bound(coefficients, scale, order=1):
    """sup |d^order p/dt^order| from |T_k|<=1, never sampled extrema."""
    series = tuple(Interval.point(x) for x in coefficients)
    for _ in range(order):
        series = derivative_coefficients(series)
    total = sum((Interval.point(x.magnitude) for x in series), Interval.point(0.))
    for _ in range(order):
        total = total*scale
    return total.hi


class EnclosureUnavailable(ValueError):
    """The exact selected reader/model interval lacks a proved enclosure."""


@dataclass(frozen=True, slots=True)
class RecordBounds:
    """Serving-record position, velocity and acceleration bounds with source identities."""
    position: tuple[Interval, Interval, Interval]
    velocity: float
    acceleration: float
    record_indices: tuple[int, ...]
    source_sha256: str
    center: int
    target: int


class ServingRecordEnclosures:
    """RITE: Serving Chebyshev records

    THEOREM: Bound the exact native serving records and their evaluation schedule without reopening kernels.

    RITE OF PURPOSE:
        Bound the exact native serving records and their evaluation schedule without reopening kernels.

    LAW OF OPERATION:
        Dependencies: borrowed reader, native bounded record accessor.
        Mutable caches and counters belong to one request; computational calls
        remain on its owning thread. Only returned immutable evidence is shared.
        No resource ownership transfers and no missing evidence becomes success.

    Canon: NAIF SPK type 2 record definition and the active Moira evaluator.

    Finite request-owned cache of source-bound type-2 record enclosures.

    The caller retains its reader lease. Selection uses the reader's actual
    descriptor priority; a descriptor seam is returned as unavailable for the
    caller to split, never filled by another kernel or interpolated across.

    [MACHINE_CONTRACT v1]
    {
      "scope": "class",
      "id": "moira._muhurta_marriage_enclosure.ServingRecordEnclosures",
      "risk": "high",
      "api": {
        "frozen": [],
        "internal": [
          "__init__",
          "_record",
          "direct"
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
    def __init__(self, reader, meter):
        self.reader, self.meter = reader, meter
        self.sources = set()
        self._record=lru_cache(maxsize=8192)(self._record)

    def _record(self, evaluator, index):
        self.meter.tick('evaluations')
        return evaluator.chebyshev_records(index, 1)[0]

    def direct(self, reader, center, target, a, b):
        if not isfinite(a) or not isfinite(b) or a > b:
            raise ValueError('finite ordered TDB record interval required')
        selector = getattr(reader, '_segment_for_tdb', None)
        if selector is None:
            raise EnclosureUnavailable('reader_has_no_source_bound_record_selector')
        segment = selector(center, target, a)
        if segment is not selector(center, target, b):
            raise EnclosureUnavailable('serving_descriptor_seam_requires_split')
        # A short higher-priority descriptor may lie entirely inside the range.
        for candidate in reader._segments_for_pair(center, target):
            if candidate is segment:
                break
            if candidate.start_jd <= b and candidate.end_jd >= a:
                raise EnclosureUnavailable('serving_descriptor_preemption_requires_split')
        if segment.data_type != 2:
            raise EnclosureUnavailable('record_enclosure_requires_type2')
        evaluator = segment._load_native_evaluator()
        if evaluator is None or not hasattr(evaluator, 'chebyshev_records'):
            raise EnclosureUnavailable('native_bounded_record_accessor_unavailable')
        init, length, count, components, _ = evaluator.chebyshev_metadata()
        if components != 3 or length <= 0:
            raise EnclosureUnavailable('unsupported_record_layout')
        # Outward-rounded epochs retain BOTH adjacent records at a join.
        seconds = (Interval(a, b)-2451545.)*86400-init
        indices = seconds/length
        first, last = max(0, floor(indices.lo)), min(count-1, floor(indices.hi))
        if first > last or last-first >= 256:
            raise EnclosureUnavailable('record_batch_requires_temporal_subdivision')
        boxes = []
        vmax = amax = 0.
        used = []
        scale = (Interval.point(172800.)/length).hi
        for index in range(first, last+1):
            record = self._record(evaluator, index)
            normalized = 2*(seconds-index*length)/length-1
            s = Interval(max(-1., normalized.lo), min(1., normalized.hi))
            boxes.append(tuple(chebyshev(c,s) for c in record))
            v = sum((Interval.point(derivative_bound(c,scale)).square() for c in record),Interval.point(0.)).sqrt().hi
            acceleration = sum((Interval.point(derivative_bound(c,scale,2)).square() for c in record),Interval.point(0.)).sqrt().hi
            vmax, amax = max(vmax,v), max(amax,acceleration)
            used.append(index)
        receipt = reader._receipt_for_segment(segment)
        self.sources.add(receipt.source.sha256)
        return RecordBounds(tuple(Interval(min(x[i].lo for x in boxes), max(x[i].hi for x in boxes)) for i in range(3)),
                            vmax, amax, tuple(used), receipt.source.sha256, center, target)
