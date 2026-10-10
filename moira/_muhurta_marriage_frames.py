"""Finite-series interval extension of the admitted modern frame model.

Fukushima-Williams/P03 coefficients mirror the canonical frame owner. Nutation
uses the owner's actual loaded IERS rows. A native point anchor carries a
coefficient-derived arithmetic error and a global analytic series-rate bound;
no sampled slope establishes an interval exclusion. The executable fundamental argument definitions,
including their last planetary argument, are preserved exactly.
"""
from dataclasses import dataclass
from math import ulp
from ._bounded_memo import binary64_key, bounded_memo

from ._muhurta_marriage_enclosure import Interval as I, PI, polynomial, EnclosureUnavailable
from .nutation_2000a import _ensure_tables_loaded, _LS_J0_COUNT, _PL_J0_COUNT
from .sidereal import _AYANAMSA_AT_J2000
from ._muhurta_marriage_roundoff import nutation_errors,gamma

_AS=PI/648000
_CY=36525.
_EPS=(84381.406,-46.836769,-.0001831,.00200340,-.000000576,-.0000000434)
_FW=((-0.052928,10.556403,.4932044,-.00031238,-.000002788,.0000000260),
     (84381.412819,-46.811016,.0511268,.00053289,-.000000440,-.0000000176),
     (-.041775,5038.481484,1.5584175,-.00018522,-.000026452,-.0000000148),_EPS)
_PA=(0.,5028.796195,1.1054348,.00007964,-.000023857,-.0000000383)
_FA_SECONDS=((485868.249036,1717915923.2178,31.8792,.051635,-.00024470),
    (1287104.793048,129596581.0481,-.5532,.000136,-.00001149),
    (335779.526232,1739527262.8478,-12.7512,-.001037,.00000417),
    (1072260.703692,1602961601.2090,-6.3706,.006593,-.00003169),
    (450160.398036,-6962890.5431,7.4722,.007702,-.00005939))
_FA=tuple(tuple(I.point(c)*_AS for c in p) for p in _FA_SECONDS)+tuple(tuple(I.point(c) for c in p) for p in (
    (4.402608842,2608.7903141574),(3.176146697,1021.3285546211),(1.753470314,628.3075849991),
    (6.203480913,334.0612426700),(.599546497,52.9690962641),(.874016757,21.3299104960),
    (5.481293872,7.4781598567),(5.311886287,3.8133035638),(.02438175,.00000538691)))


def derivative(p):
    return tuple(k*c for k,c in enumerate(p) if k) or (I.point(0.),)


def _sum(values):
    return sum(values,I.point(0.))


@dataclass(frozen=True, slots=True)
class Differential:
    """An interval value and derivative with respect to the common TT variable."""
    value: I
    rate: I
    center: I | None = None
    radius: float = 0.
    centered: bool = True

    def __post_init__(self):
        if self.center is None:
            object.__setattr__(self,'center',self.value)
        if self.radius and self.centered:
            # Mean-value enclosure, centered on the SAME common TT variable.
            # This preserves cancellations such as barycentric Moon-Earth.
            centered=self.center+self.rate*I(-self.radius,self.radius)
            lo,hi=max(self.value.lo,centered.lo),min(self.value.hi,centered.hi)
            if lo>hi:
                raise EnclosureUnavailable('inconsistent_centered_differential')
            object.__setattr__(self,'value',I(lo,hi))

    @staticmethod
    def point(x):
        return x if isinstance(x,Differential) else Differential(I.point(x),I.point(0.))

    @staticmethod
    def rounded(value,rate,center,radius,centered,error=None):
        """Uniform error parameter, held constant in each surrogate branch.

        A full ulp safely covers one RN binary64 primitive (including gradual
        underflow). Transcendentals use the separately declared <=4ulp model.
        The same FULL-domain guard is retained at the common center.
        """
        guard=ulp(value.magnitude) if error is None else error
        return Differential(value.expand(guard),rate,center.expand(guard),radius,centered)

    def with_error(self,error):
        return self.rounded(self.value,self.rate,self.center,self.radius,self.centered,error)

    def __add__(self,other):
        b=self.point(other)
        return self.rounded(self.value+b.value,self.rate+b.rate,self.center+b.center,max(self.radius,b.radius),self.centered and b.centered)

    __radd__=__add__

    def __neg__(self):
        return Differential(-self.value,-self.rate,-self.center,self.radius,self.centered)

    def __sub__(self,other):
        return self+-self.point(other)

    def __rsub__(self,other):
        return self.point(other)+-self

    def __mul__(self,other):
        b=self.point(other)
        return self.rounded(self.value*b.value,self.rate*b.value+self.value*b.rate,self.center*b.center,max(self.radius,b.radius),self.centered and b.centered)

    __rmul__=__mul__

    def __truediv__(self,other):
        b=self.point(other)
        return self.rounded(self.value/b.value,(self.rate*b.value-self.value*b.rate)/b.value.square(),self.center/b.center,max(self.radius,b.radius),self.centered and b.centered)

    def __rtruediv__(self,other):
        return self.point(other)/self

    def square(self):
        return self.rounded(self.value.square(),2*self.value*self.rate,self.center.square(),self.radius,self.centered,
                            4*ulp(self.value.square().magnitude))

    def asin(self):
        return self.rounded(PI/2-self.value.acos(),self.rate/(1-self.value.square()).sqrt(),
                            PI/2-self.center.acos(),self.radius,self.centered,4*ulp(PI.hi))

    def sqrt(self):
        root=self.value.sqrt()
        return self.rounded(root,self.rate/(2*root),self.center.sqrt(),self.radius,self.centered)

    def sin(self):
        return self.rounded(self.value.sin(),self.value.cos()*self.rate,self.center.sin(),self.radius,self.centered,4*ulp(1.))

    def cos(self):
        return self.rounded(self.value.cos(),-self.value.sin()*self.rate,self.center.cos(),self.radius,self.centered,4*ulp(1.))

    def acos(self):
        return self.rounded(self.value.acos(),-self.rate/(1-self.value.square()).sqrt(),self.center.acos(),self.radius,self.centered,4*ulp(PI.hi))


def _jet_polynomial(p,x):
    result=Differential.point(0.)
    for c in reversed(p):
        result=result*x+c
    return result


def _differential_key(value):
    """All interval, derivative and common-center bits govern reuse."""
    return binary64_key(value.value.lo,value.value.hi,value.rate.lo,value.rate.hi,
                        value.center.lo,value.center.hi,value.radius)+bytes((value.centered,))


class FrameEnclosures:
    """RITE: Celestial-frame enclosure

    THEOREM: Carry nutation, precession and obliquity intervals from the frozen serving coefficient tables.

    RITE OF PURPOSE:
        Carry nutation, precession and obliquity intervals from the frozen serving coefficient tables.

    LAW OF OPERATION:
        Dependencies: frame coefficient tables.
        Mutable caches and counters belong to one request; computational calls
        remain on its owning thread. Only returned immutable evidence is shared.
        No resource ownership transfers and no missing evidence becomes success.

    Canon: Moira IAU frame reduction and admitted nutation tables.

    [MACHINE_CONTRACT v1]
    {
      "scope": "class",
      "id": "moira._muhurta_marriage_frames.FrameEnclosures",
      "risk": "high",
      "api": {
        "frozen": [],
        "internal": [
          "__init__",
          "_polynomials",
          "nutation",
          "angles"
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
    def __init__(self,meter):
        ls,pl=_ensure_tables_loaded()
        self.tables=(tuple(ls),tuple(pl))
        self.roundoff=nutation_errors(_FA,self.tables,(_LS_J0_COUNT,_PL_J0_COUNT))
        self.meter=meter
        rates=tuple((polynomial(derivative(p),I(-1.02,1.02))/_CY).magnitude for p in _FA)
        coarse=[]
        for terms,j0 in zip(self.tables,(_LS_J0_COUNT,_PL_J0_COUNT)):
            v,r=I.point(0.),I.point(0.)
            for index,(a,b,*multipliers) in enumerate(terms):
                amp=I.point(abs(a))+I.point(abs(b))
                omega=_sum(abs(n)*I.point(w) for n,w in zip(multipliers,rates) if n)
                multiplier=1.02 if index>=j0 else 1.
                v=v+amp*multiplier
                r=r+amp*(omega*multiplier+(I.point(1)/_CY if index>=j0 else 0.))
            coarse.append(((v*_AS/1000000).hi,(r*_AS/1000000).hi))
        self.coarse=tuple(coarse)
        # These owners freeze the source rows for this request. Coarse and
        # precise nutation share only the identical precession polynomials.
        self._polynomials=bounded_memo(self._polynomials,key=_differential_key,maxsize=4096)
        self.angles=bounded_memo(self.angles,
            key=lambda tt,coarse=False:_differential_key(tt)+bytes((coarse,)),maxsize=4096)
        self.sincos=bounded_memo(lambda angle:(angle.cos(),angle.sin()),
                                key=_differential_key,maxsize=4096)

    def nutation(self,tt,*,coarse=False):
        if tt.value.lo<2415020.5 or tt.value.hi>=2488434.5:
            raise EnclosureUnavailable('frame_certificate_outside_1900_2100')
        if coarse:
            return tuple(Differential(I(-v,v),I(-r,r)*tt.rate,I(-v,v),tt.radius,tt.centered).with_error(e)
                         for (v,r),e in zip(self.coarse,self.roundoff))
        from .nutation_2000a import nutation_2000a
        anchor=(tt.value.lo+tt.value.hi)/2
        native=nutation_2000a(anchor)
        result=[]
        for nominal,(_,bound),error in zip(native,self.coarse,self.roundoff):
            # A serving point is a permitted anchor because its error is
            # bounded from the loaded coefficients/operation graph above.
            # The slope is the GLOBAL analytic series bound, never a sampled
            # native slope. This avoids repeated Python trigonometric series.
            base=(I.point(nominal)*PI/180).expand(error)
            rate=I(-bound,bound)
            result.append(Differential(base+rate*(tt.value-anchor),rate*tt.rate,
                base+rate*(tt.center-anchor),tt.radius,tt.centered).with_error(error))
        return tuple(result)

    def _polynomials(self,tt):
        """Frame polynomials independent of the nutation enclosure mode."""
        t=(tt-2451545.)/_CY
        fw=tuple(_jet_polynomial(p,t)*_AS for p in _FW)
        return fw,_jet_polynomial(_PA,t)*_AS

    def angles(self,tt,*,coarse=False):
        fw,precession=self._polynomials(tt)
        psi,eps=self.nutation(tt,coarse=coarse)
        true_eps=fw[3]+eps
        ayanamsa=precession+psi+I.point(_AYANAMSA_AT_J2000['Lahiri'])*PI/180
        return fw,psi,eps,true_eps,ayanamsa


def rotate_x(vector,angle,*,sincos=None):
    x,y,z=vector
    c,s=(angle.cos(),angle.sin()) if sincos is None else sincos(angle)
    return x,c*y+s*z,-s*y+c*z


def rotate_z(vector,angle,*,sincos=None):
    x,y,z=vector
    c,s=(angle.cos(),angle.sin()) if sincos is None else sincos(angle)
    return c*x+s*y,-s*x+c*y,z


def true_equator(vector,angles,*,sincos=None):
    # Native forms matrix products while this owner applies rotations. There
    # are fewer than512 basic operations and eight orthogonal stages. The
    # induced1-norm amplification is <=sqrt(3)^8=81, so this guards either
    # admitted evaluation schedule, independently of cancellation.
    schedule_error=(gamma(512)*81*_sum(I.point(v.value.magnitude) for v in vector)).hi
    fw,psi,deps,_,_=angles
    gamb,phib,psib,epsa=fw
    vector=rotate_z(vector,gamb,sincos=sincos)
    vector=rotate_x(vector,phib,sincos=sincos)
    vector=rotate_z(vector,-psib,sincos=sincos)
    vector=rotate_x(vector,-epsa,sincos=sincos)
    # N = Rx(-(epsa+deps)) Rz(-dpsi) Rx(epsa), passive rotations.
    vector=rotate_x(vector,epsa,sincos=sincos)
    vector=rotate_z(vector,-psi,sincos=sincos)
    return tuple(v.with_error(schedule_error) for v in rotate_x(vector,-(epsa+deps),sincos=sincos))
