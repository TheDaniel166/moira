"""Exact rational charts for a fixed affine cone and ellipsoid.

The declared generator is X=P+R*r(theta)+t*(u+K*r(theta)), with
r=e*cos(theta)+n*sin(theta). The independent basis (u,e,n) need not be
silently re-orthogonalized. Two projective charts use exact circle values
cos=sign*(1-x*x)/(1+x*x), sin=sign*2*x/(1+x*x), x in [-1,1].

Substituting in X.Q.X=1 gives A*t*t+2*B*t+C=0. Critical parameters are
B*B-A*C=0, A*f*f+2*B*f+C=0 and A*h0*h0-2*B*h0*h1+C*h1*h1=0.
They respectively cover ellipsoid tangencies, the forward plane and the
Sun-centre horizon h0+h1*t=0. Positive circle-denominator factors carry no
real roots and are removed EXACTLY, never by coefficient thresholds.
"""
from dataclasses import dataclass,replace
from fractions import Fraction as F

from ._eclipse_interval import RationalInterval as I
from ._eclipse_interval_roots import EnclosureUnavailable
from . import _eclipse_exact_polynomial as p
from .constants import EARTH_RADIUS_KM,MOON_RADIUS_KM
from .eclipse import _WGS84_POLAR_RADIUS_KM


def dot(a,b):
    return sum((x*y for x,y in zip(a,b)),F(0))


def cross(a,b):
    return tuple(a[i]*b[j]-a[j]*b[i] for i,j in ((1,2),(2,0),(0,1)))


def inverse_basis(u,e,n):
    rows = cross(e,n),cross(n,u),cross(u,e)
    determinant = dot(u,rows[0])
    if not determinant:
        raise EnclosureUnavailable('cone generator basis is singular')
    return tuple(tuple(v/determinant for v in row) for row in rows)


@dataclass(frozen=True, slots=True)
class FixedConeFamily:
    """Exact represented-state affine family, radii in km, dimensionless basis.

    The forward threshold is a parameter plane, not an implicit norm test.
    Both signed-radius nappes are retained. Sun-centre horizon and visible
    common-ray occurrence remain separately named products.
    """

    origin: tuple[F,...]
    axis: tuple[F,...]
    east: tuple[F,...]
    north: tuple[F,...]
    radius: F
    slope: F
    forward_start: F
    sun: tuple[F,...]
    equatorial_km: F = F.from_float(EARTH_RADIUS_KM)
    polar_km: F = F.from_float(_WGS84_POLAR_RADIUS_KM)
    kind: str = 'central'

    def __post_init__(self):
        for name in ('origin','axis','east','north','sun'):
            values = tuple(I.point(v) for v in getattr(self,name))
            if len(values)!=3 or any(v.width for v in values):
                raise ValueError('three finite point coordinates required')
            object.__setattr__(self,name,tuple(v.lo for v in values))
        for name in ('radius','slope','forward_start','equatorial_km','polar_km'):
            value = I.point(getattr(self,name))
            if value.width:
                raise ValueError('fixed cone coefficients must be points')
            object.__setattr__(self,name,value.lo)
        if not 0<self.polar_km<=self.equatorial_km:
            raise ValueError('positive ordered ellipsoid axes required')
        inverse_basis(self.axis,self.east,self.north)
        if sum((v/r)**2 for v,r in zip(self.sun,self.radii))<=1:
            raise EnclosureUnavailable('Sun outside ellipsoid must be proved')

    @property
    def radii(self):
        return self.equatorial_km,self.equatorial_km,self.polar_km

    @property
    def inverse(self):
        return inverse_basis(self.axis,self.east,self.north)

    @classmethod
    def from_shadow(cls,shadow, *, kind='central'):
        """Freeze an admitted native state; do not interpret None as empty.

        The real forward plane is beyond the Moon by its stored radius.
        The snapshot theorem is about these exact coefficients and true
        circle charts, not every rounded generator or a time interval.
        """
        if shadow is None:
            raise EnclosureUnavailable('no admitted shadow state to freeze')
        if kind=='central':
            radius,slope = shadow.central_radius_km,-shadow.central_cone_slope
        elif kind=='penumbral':
            radius,slope = shadow.penumbral_radius_km,shadow.penumbral_cone_slope
        else:
            raise ValueError('unknown cone family')
        return cls(shadow.fundamental_plane_point_xyz_km,shadow.axis_unit_away_from_sun,
            shadow.fundamental_east_unit_itrf,shadow.fundamental_north_unit_itrf,
            radius,slope,F.from_float(shadow.axis_projection_km)+F.from_float(MOON_RADIUS_KM),
            shadow.sun_xyz_from_earth_itrf_km,kind=kind)


def strip_circle_factors(value):
    value = p.poly(value)
    circle = (F(1),F(0),F(1))
    while len(value)>=3 and not p.remainder(value,circle):
        value = p.quotient(value,circle)
    return value


@dataclass(frozen=True, slots=True)
class ConeChart:
    """Quadratic line coefficients and all critical polynomials on one chart."""

    sign: int
    denominator: tuple
    origin: tuple
    direction: tuple
    a: tuple
    b: tuple
    c: tuple
    delta: tuple
    horizon_origin: tuple
    horizon_direction: tuple
    critical: tuple


def cone_chart(family,sign):
    """Derive the rational line/ellipsoid and horizon resultants."""
    if sign not in (-1,1):
        raise ValueError('circle chart sign must be +/-1')
    d = p.poly((1,0,1))
    radial = tuple(p.poly((sign*e,2*sign*n,-sign*e)) for e,n in zip(family.east,family.north))
    origin = tuple(p.add(p.scale(d,x),p.scale(r,family.radius)) for x,r in zip(family.origin,radial))
    direction = tuple(p.add(p.scale(d,u),p.scale(r,family.slope)) for u,r in zip(family.axis,radial))

    def metric(x,y):
        result = ()
        for a,b,r in zip(x,y,family.radii):
            result = p.add(result,p.scale(p.mul(a,b),1/(r*r)))
        return result

    a,b = metric(direction,direction),metric(origin,direction)
    c = p.sub(metric(origin,origin),p.mul(d,d))
    delta = p.sub(p.mul(b,b),p.mul(a,c))
    ho,hd = (),()
    for o,u,s,r in zip(origin,direction,family.sun,family.radii):
        ho = p.add(ho,p.scale(o,s/(r*r)))
        hd = p.add(hd,p.scale(u,s/(r*r)))
    ho = p.sub(ho,d)
    forward = p.add(p.add(p.scale(a,family.forward_start**2),p.scale(b,2*family.forward_start)),c)
    horizon = p.add(p.sub(p.mul(a,p.mul(ho,ho)),p.scale(p.mul(b,p.mul(ho,hd)),2)),p.mul(c,p.mul(hd,hd)))
    critical = tuple((name,strip_circle_factors(value)) for name,value in
                     (('ellipsoid',delta),('forward',forward),('horizon',horizon)))
    return ConeChart(sign,d,origin,direction,a,b,c,delta,ho,hd,critical)


def quadratic_sign(oracle,root,left,right,radicand):
    """Decide sign(L(alpha)+E(alpha)*sqrt(D(alpha))) without numerical zeros."""
    ds = oracle.sign(root,radicand)
    if ds<0:
        raise ValueError('negative algebraic radicand')
    ls = oracle.sign(root,left)
    if not ds:
        return ls
    rs = oracle.sign(root,right)
    if not ls:
        return rs
    if not rs or ls==rs:
        return ls
    difference = p.sub(p.mul(left,left),p.mul(p.mul(right,right),radicand))
    return ls*oracle.sign(root,difference)


@dataclass(frozen=True, slots=True)
class AlgebraicPoint:
    """Cartesian point (L+E*sqrt(D))/den at one isolated real root; den>0."""

    root: p.ExactRealRoot
    left: tuple
    right: tuple
    radicand: tuple
    denominator: tuple

    def linear_pair(self,coefficients,constant=F(0)):
        left,right = p.scale(self.denominator,constant),()
        for c,lp,rp in zip(coefficients,self.left,self.right):
            left,right = p.add(left,p.scale(lp,c)),p.add(right,p.scale(rp,c))
        return left,right

    def sign_linear(self,oracle,coefficients,constant=F(0)):
        lp,rp = self.linear_pair(coefficients,constant)
        return quadratic_sign(oracle,self.root,lp,rp,self.radicand)

    def sign_cone(self,oracle,family):
        coords = [self.linear_pair(row,-dot(row,family.origin)) for row in family.inverse]
        radius = (p.add(p.scale(self.denominator,family.radius),p.scale(coords[0][0],family.slope)),
                  p.scale(coords[0][1],family.slope))
        left,right = (),()
        for sign,(lp,rp) in ((1,coords[1]),(1,coords[2]),(-1,radius)):
            left = p.add(left,p.scale(p.add(p.mul(lp,lp),p.mul(p.mul(rp,rp),self.radicand)),sign))
            right = p.add(right,p.scale(p.mul(lp,rp),2*sign))
        return quadratic_sign(oracle,self.root,left,right,self.radicand)

    def enclose(self,oracle, *, bits=256):
        point = self
        sign = oracle.sign(point.root,point.radicand)
        if sign<0:
            raise ValueError('negative point radicand')
        while True:
            box = point.root.interval
            radicand = p.enclose(point.radicand,box,bits=bits) if sign else I.point(0)
            den = p.enclose(point.denominator,box,bits=bits)
            if radicand.lo>=0 and den.lo>0:
                square_root = radicand.sqrt(bits)
                return tuple(((p.enclose(lp,box,bits=bits)+p.enclose(rp,box,bits=bits)*square_root)/den)
                             .quantize_outward(bits) for lp,rp in zip(point.left,point.right))
            point = replace(point,root=oracle.refine(point.root))


def generator_point(chart,root,branch):
    """Create the exact near(-1), far(+1), or tangent(0) surface root."""
    left = tuple(p.sub(p.mul(chart.a,o),p.mul(chart.b,u)) for o,u in zip(chart.origin,chart.direction))
    right = tuple(p.scale(u,branch) for u in chart.direction)
    return AlgebraicPoint(root,left,right,chart.delta,p.mul(chart.denominator,chart.a))


def constant_radical_point(left,right,radicand):
    root = p.ExactRealRoot((0,1),I.point(0))
    return AlgebraicPoint(root,tuple((F(v),) for v in left),tuple((F(v),) for v in right),
                          (F(radicand),),(F(1),))


def point_at_rational_parameter(chart,value,branch):
    value = F(value)
    root = p.ExactRealRoot(p.primitive((-value,1),positive_leading=True),I.point(value))
    return generator_point(chart,root,branch)


def compare_roots(oracle,a,b):
    """Order two isolated roots, merging only a proved common algebraic root."""
    while True:
        if a.interval.hi<b.interval.lo:
            return -1,a,b
        if b.interval.hi<a.interval.lo:
            return 1,a,b
        overlap = a.interval.intersect(b.interval)
        common = p.polynomial_gcd(a.polynomial,b.polynomial)
        if overlap is not None and len(common)>1 and oracle.count_closed(common,overlap):
            return 0,replace(a,interval=overlap),b
        if not a.interval.width and not b.interval.width:
            raise ArithmeticError('distinct point roots have the same value')
        if a.interval.width>=b.interval.width:
            a = oracle.refine(a)
        else:
            b = oracle.refine(b)
