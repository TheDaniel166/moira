"""Exact cut sets and complete open arcs of the horizon/forward circles.

Scale X=D*z to the unit sphere. Each clipping plane n.z=c cuts a circle,
a point, or nothing. All cone intersections come from the complete cone
arrangement; the two planes' shared intersections are solved independently.
Between these cuts the remaining constraint signs cannot change. Interval
arithmetic proves their sample signs; samples never establish the cut set.
"""
from dataclasses import dataclass, replace
from fractions import Fraction as F

from ._eclipse_cone_algebra import dot, cross, constant_radical_point
from ._eclipse_exact_polynomial import ExactPolynomialOracle
from ._eclipse_interval import RationalInterval as I, IntervalBudgetError
from ._eclipse_interval_roots import EnclosureUnavailable


@dataclass(frozen=True, slots=True)
class CircleArc:
    """Open projective-circle arc between two shared algebraic point IDs."""

    plane: str
    chart: int
    start: tuple
    end: tuple
    sample_parameter: F
    cone_sign: int
    other_plane_sign: int

    @property
    def legal(self):
        return self.cone_sign <= 0 and self.other_plane_sign >= 0


@dataclass(frozen=True, slots=True)
class ConstraintCircleArrangement:
    """All plane/sphere strata, separate from two-dimensional region counts."""

    cone_topology: object
    points: tuple
    arcs: tuple
    complete: bool
    unresolved: tuple
    reason: str


def _planes(family):
    horizon = tuple(s/r for s,r in zip(family.sun,family.radii)),F(1)
    row = family.inverse[0]
    forward = tuple(x*r for x,r in zip(row,family.radii)),family.forward_start+dot(row,family.origin)
    return (('horizon',*horizon),('forward',*forward))


def _box_sign(value):
    return 1 if value.lo > 0 else -1 if value.hi < 0 else None


def _cone_box(family,point):
    coords = [sum((c*(v-o) for c,v,o in zip(row,point,family.origin)),I.point(0))
              for row in family.inverse]
    return coords[1].square()+coords[2].square()-(family.radius+family.slope*coords[0]).square()


def _coincident_conic(family,n,c):
    """Exact proportionality after eliminating one rational plane coordinate."""
    axis = next(i for i,v in enumerate(n) if v)
    others = [i for i in range(3) if i != axis]
    centre = [F(0)]*3
    centre[axis] = c/n[axis]
    directions = []
    for i in others:
        v = [F(0)]*3
        v[i],v[axis] = F(1),-n[i]/n[axis]
        directions.append(v)

    def square(line):
        a,b,d = line
        return (a*a,2*a*b,2*a*d,b*b,2*b*d,d*d)

    sphere = [F(-1),F(0),F(0),F(0),F(0),F(0)]
    for i in range(3):
        sphere = [a+b for a,b in zip(sphere,square((centre[i],directions[0][i],directions[1][i])))]
    coords = []
    for row in family.inverse:
        scaled = tuple(v*r for v,r in zip(row,family.radii))
        coords.append((dot(scaled,centre)-dot(row,family.origin),
                       dot(scaled,directions[0]),dot(scaled,directions[1])))
    radius = (family.radius+family.slope*coords[0][0],
              family.slope*coords[0][1],family.slope*coords[0][2])
    cone = tuple(a+b-d for a,b,d in zip(square(coords[1]),square(coords[2]),square(radius)))
    index = next(i for i,v in enumerate(sphere) if v)
    ratio = cone[index]/sphere[index]
    return all(a == ratio*b for a,b in zip(cone,sphere))


def _plane_intersections(family,planes):
    _,n,c = planes[0]
    _,m,d = planes[1]
    nn,mm,nm = dot(n,n),dot(m,m),dot(n,m)
    det = nn*mm-nm*nm
    if not det:
        return ()
    centre = tuple(((c*mm-d*nm)*a+(d*nn-c*nm)*b)/det for a,b in zip(n,m))
    direction = cross(n,m)
    radicand = (1-dot(centre,centre))/dot(direction,direction)
    if radicand < 0:
        return ()
    return tuple((sign,constant_radical_point(
        tuple(r*v for r,v in zip(family.radii,centre)),
        tuple(sign*r*v for r,v in zip(family.radii,direction)),radicand))
        for sign in ((0,) if not radicand else (-1,1)))


def complete_constraint_circles(topology, *, max_queries=100000, max_refinements=512):
    """Enumerate every horizon/forward arc with shared cone-junction objects.

    The output is a constraint arrangement, including coincident/contact
    strata. It does not infer numbers of filled surface regions from loops.
    Unseparated algebraic cuts or finite-budget exhaustion remain bounded.
    """
    family = topology.family
    oracle = ExactPolynomialOracle(max_queries=max_queries)
    points = {v.key:v.point for v in topology.vertices}
    arcs = []
    if not topology.complete:
        return ConstraintCircleArrangement(topology,tuple(points.items()),(),False,
                                            ('horizon','forward'),'cone cut set incomplete')
    planes = _planes(family)
    try:
        shared = []
        for sign,point in _plane_intersections(family,planes):
            key = ('planes',sign)
            line = cross(planes[0][1],planes[1][1])
            coefficients = tuple(v/r for v,r in zip(line,family.radii))
            for vertex in topology.vertices:
                if not vertex.horizon and not vertex.forward and (
                        vertex.point.sign_linear(oracle,coefficients) == sign):
                    key,point = vertex.key,vertex.point
                    break
            points[key] = point
            shared.append(key)
        for index,(name,n,c) in enumerate(planes):
            _,other,other_c = planes[1-index]
            norm2 = dot(n,n)
            radius2 = 1-c*c/norm2
            if radius2 < 0:
                continue
            centre = tuple(c*v/norm2 for v in n)
            if not radius2:
                key = ('plane_tangent',name)
                # A tangent plane has exactly one sphere point. Reuse its
                # cone/plane junction identity when already present.
                candidates = [v.key for v in topology.vertices
                              if (v.horizon if name=='horizon' else v.forward) == 0]
                candidates.extend(shared)
                if candidates:
                    key = candidates[0]
                else:
                    points[key] = constant_radical_point(
                        tuple(v*r for v,r in zip(centre,family.radii)),(0,0,0),0)
                continue
            basis = next(tuple(F(int(i==axis)) for i in range(3)) for axis in range(3)
                         if any(cross(n,tuple(F(int(i==axis)) for i in range(3)))))
            east = cross(n,basis)
            north = cross(n,east)
            ae,an = radius2/dot(east,east),radius2/dot(north,north)
            ecoef = tuple(v/r for v,r in zip(east,family.radii))
            ncoef = tuple(v/r for v,r in zip(north,family.radii))
            nodes = set(shared)
            for v in topology.vertices:
                if (v.horizon if name=='horizon' else v.forward) == 0:
                    nodes.add(v.key)
            for sign in (-1,1):
                key = ('circle_seam',name,sign)
                for candidate in sorted(nodes,key=repr):
                    point = points[candidate]
                    if (point.sign_linear(oracle,ecoef) == 0 and
                            point.sign_linear(oracle,ncoef) == sign):
                        key = candidate
                        break
                else:
                    points[key] = constant_radical_point(tuple(v*r for v,r in zip(centre,family.radii)),
                        tuple(sign*v*r for v,r in zip(north,family.radii)),an)
                nodes.add(key)
            circle_coincident = _coincident_conic(family,n,c)
            other_coincident = all(a*c == b*other_c for a,b in zip(other,n)) and (
                not any(cross(n,other)))

            def parameter(key,chart,bits):
                point = points[key]
                es,ns = point.sign_linear(oracle,ecoef),point.sign_linear(oracle,ncoef)
                if not es:
                    return I.point(chart*ns)
                box = point.enclose(oracle,bits=bits)
                ec = sum((v*a for v,a in zip(box,ecoef)),I.point(0))
                nc = sum((v*a for v,a in zip(box,ncoef)),I.point(0))
                cosine = ec/I.point(radius2*dot(east,east)).sqrt(bits)
                sine = nc/I.point(radius2*dot(north,north)).sqrt(bits)
                return (chart*sine/(1+chart*cosine)).quantize_outward(bits)

            for chart in (1,-1):
                owned = [key for key in sorted(nodes,key=repr)
                         if points[key].sign_linear(oracle,ecoef) in (0,chart)]
                for refinement in range(max_refinements):
                    bits = 160+refinement*2
                    params = {key:parameter(key,chart,bits) for key in owned}
                    ordered = sorted(owned,key=lambda k:params[k].midpoint)
                    if all(params[a].hi < params[b].lo for a,b in zip(ordered,ordered[1:])):
                        break
                    for key in owned:
                        point = points[key]
                        if point.root.interval.width:
                            points[key] = replace(point,root=oracle.refine(point.root))
                else:
                    raise EnclosureUnavailable('circle critical points not separated within budget')
                for left,right in zip(ordered,ordered[1:]):
                    x = (params[left].hi+params[right].lo)/2
                    co,si = chart*(1-x*x)/(1+x*x),chart*2*x/(1+x*x)
                    for bits in (160,256,512,1024):
                        ea,na = I.point(ae).sqrt(bits),I.point(an).sqrt(bits)
                        point = tuple(r*(cc+co*e*ea+si*v*na)
                                      for r,cc,e,v in zip(family.radii,centre,east,north))
                        cone_sign = 0 if circle_coincident else _box_sign(_cone_box(family,point))
                        other_sign = 0 if other_coincident else _box_sign(sum(
                            (a*v/r for a,v,r in zip(other,point,family.radii)),I.point(0))-other_c)
                        if cone_sign is not None and other_sign is not None:
                            break
                    else:
                        raise EnclosureUnavailable('circle complementary arc sign not separated')
                    arcs.append(CircleArc(name,chart,left,right,x,cone_sign,other_sign))
        return ConstraintCircleArrangement(topology,tuple(points.items()),tuple(arcs),True,(),
                                            'complete cone, plane and complementary circle cut sets')
    except (EnclosureUnavailable,IntervalBudgetError,ZeroDivisionError) as exc:
        return ConstraintCircleArrangement(topology,tuple(points.items()),tuple(arcs),False,
                                            ('horizon','forward'),str(exc))
