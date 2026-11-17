"""Complete fixed-state cone/ellipsoid generator stratification.

Every real critical parameter on both closed half-angle charts is isolated
by exact Sturm arithmetic. Open complementary cells have constant branch,
forward, horizon and signed-nappe labels. This is an arrangement of the
cone intersection, not a certificate for time uncertainty or the common-ray
visibility product. The Sun-centre horizon convention is explicit.
"""
from dataclasses import dataclass, replace
from fractions import Fraction as F

from . import _eclipse_exact_polynomial as p
from ._eclipse_cone_algebra import (
    FixedConeFamily, compare_roots, cone_chart, generator_point, quadratic_sign,
)
from ._eclipse_interval import RationalInterval as I, IntervalBudgetError
from ._eclipse_interval_roots import EnclosureUnavailable


@dataclass(frozen=True, slots=True)
class ConeVertex:
    """One algebraic Cartesian point, possibly a shared seam or apex."""

    key: tuple
    point: object
    forward: int
    horizon: int
    nappe: int
    tags: tuple
    multiplicities: tuple


@dataclass(frozen=True, slots=True)
class ConeArc:
    """An open cell between two algebraic roots; parameter is its outer hull.

    The roots, not their rational isolator endpoints, define the actual
    stratum. Labels apply to that open stratum, not the isolator halos.
    """

    chart: int
    parameter: I
    left_root: object
    right_root: object
    branch: int
    start: tuple
    end: tuple
    forward: int
    horizon: int
    nappe: int
    collapsed_to_apex: bool

    @property
    def legal(self):
        return self.forward >= 0 and self.horizon >= 0


@dataclass(frozen=True, slots=True)
class ConeTopology:
    """All generator cells and vertices, or an explicit bounded unknown."""

    family: FixedConeFamily
    vertices: tuple
    arcs: tuple
    unresolved: tuple
    complete: bool
    queries: int
    reason: str
    horizon_policy: str = 'sun_centre_ellipsoid_tangent_plane'
    scope: str = 'exact_real_affine_family_of_frozen_coefficients'
    time_interval_coverage_proved: bool = False
    physical_accuracy_certified: bool = False

    @property
    def legal_vertices(self):
        return tuple(v for v in self.vertices if v.forward >= 0 and v.horizon >= 0)

    @property
    def legal_arcs(self):
        return tuple(a for a in self.arcs if a.legal and not a.collapsed_to_apex)

    @property
    def components(self):
        """Connected components of the closed, clipped cone intersection."""
        parent = {v.key: v.key for v in self.legal_vertices}

        def find(key):
            while parent[key] != key:
                parent[key] = parent[parent[key]]
                key = parent[key]
            return key

        for arc in self.legal_arcs:
            parent[find(arc.end)] = find(arc.start)
        groups = {}
        for key in parent:
            groups.setdefault(find(key), []).append(key)
        return tuple(tuple(sorted(keys, key=repr)) for keys in groups.values())


def _labels(oracle, chart, root, branch, family):
    delta = oracle.sign(root, chart.delta)
    if delta < 0:
        return None
    # A is positive: the independent cone basis makes every direction nonzero.
    forward = quadratic_sign(oracle, root,
        p.sub(p.scale(chart.b, -1), p.scale(chart.a, family.forward_start)),
        p.poly((branch,)), chart.delta)
    horizon = quadratic_sign(oracle, root,
        p.sub(p.mul(chart.a, chart.horizon_origin),
              p.mul(chart.b, chart.horizon_direction)),
        p.scale(chart.horizon_direction, branch), chart.delta)
    nappe = quadratic_sign(oracle, root,
        p.sub(p.scale(chart.a, family.radius), p.scale(chart.b, family.slope)),
        p.poly((branch * family.slope,)), chart.delta)
    return forward, horizon, nappe


def _critical_nodes(oracle, chart):
    nodes = []
    for value, tag in ((F(-1), 'seam'), (F(1), 'seam')):
        nodes.append([p.ExactRealRoot(p.primitive((-value, 1), positive_leading=True), I.point(value)),
                      {tag}, {}])
    for name, polynomial in chart.critical:
        if not polynomial:
            # Identically active constraints are labelled on every stratum.
            continue
        isolated = oracle.isolate(polynomial, I(-1, 1))
        if not isolated.complete:
            raise EnclosureUnavailable(f'{name}: {isolated.reason}')
        for root in isolated.roots:
            inserted = False
            for index, node in enumerate(nodes):
                order, root, existing = compare_roots(oracle, root, node[0])
                node[0] = existing
                if not order:
                    node[0] = root
                    node[1].add(name)
                    node[2][name] = root.multiplicity
                    inserted = True
                    break
                if order < 0:
                    nodes.insert(index, [root, {name}, {name: root.multiplicity}])
                    inserted = True
                    break
            if not inserted:
                nodes.append([root, {name}, {name: root.multiplicity}])
    return nodes


def _sample_between(oracle, left, right):
    while left.interval.hi > right.interval.lo:
        if left.interval.width >= right.interval.width:
            left = oracle.refine(left)
        else:
            right = oracle.refine(right)
    value = (left.interval.hi + right.interval.lo) / 2
    # An equal cut is allowed only when it is not either algebraic root.
    if p.evaluate(left.polynomial, value) == 0 or p.evaluate(right.polynomial, value) == 0:
        if left.interval.width:
            left = oracle.refine(left)
        if right.interval.width:
            right = oracle.refine(right)
        return _sample_between(oracle, left, right)
    return value, left, right


def solve_cone_topology(family, *, max_queries=100000, max_refinement_bits=1024):
    """Classify every cone generator and both ellipsoid roots on the circle.

    Resource exhaustion retains both bounded charts as unknown. No numerical
    coefficient trimming, phase lattice, periodic sample or epsilon is used.
    """
    if not isinstance(family, FixedConeFamily):
        raise TypeError('an explicitly frozen FixedConeFamily is required')
    oracle = p.ExactPolynomialOracle(max_queries=max_queries,
                                     max_refinement_bits=max_refinement_bits)
    vertices, arcs = {}, []
    axis_only = not family.radius and not family.slope

    def key_for(chart, node_index, node, branch, labels):
        if axis_only:
            return ('axis', branch)
        if not labels[2] and family.slope:
            return ('apex',)
        if node[0].interval.width == 0 and abs(node[0].interval.lo) == 1:
            return ('seam', chart.sign * int(node[0].interval.lo), branch)
        return ('root', chart.sign, node_index, branch)

    try:
        for sign in (1, -1):
            chart = cone_chart(family, sign)
            nodes = _critical_nodes(oracle, chart)
            node_keys = {}
            for index, node in enumerate(nodes):
                root = node[0]
                delta = oracle.sign(root, chart.delta)
                for branch in (() if delta < 0 else ((0,) if not delta else (-1, 1))):
                    labels = _labels(oracle, chart, root, branch, family)
                    key = key_for(chart, index, node, branch, labels)
                    vertex = ConeVertex(key, generator_point(chart, root, branch), *labels,
                                        tuple(sorted(node[1])), tuple(sorted(node[2].items())))
                    if key in vertices:
                        old = vertices[key]
                        if (old.forward, old.horizon, old.nappe) != labels:
                            raise ArithmeticError('inconsistent shared cone junction labels')
                        vertex = replace(old, tags=tuple(sorted(set(old.tags) | set(vertex.tags))),
                                         multiplicities=tuple(sorted(set(old.multiplicities) |
                                                                     set(vertex.multiplicities))))
                    vertices[key] = vertex
                    for lookup in ((-1, 1) if not delta else (branch,)):
                        node_keys[index, lookup] = key
                    if not delta:
                        node_keys[index, 0] = key
            for index, (left, right) in enumerate(zip(nodes, nodes[1:])):
                sample, a, b = _sample_between(oracle, left[0], right[0])
                root = p.ExactRealRoot(p.primitive((-sample, 1), positive_leading=True), I.point(sample))
                delta = oracle.sign(root, chart.delta)
                for branch in (() if delta < 0 else ((0,) if not delta else (-1, 1))):
                    labels = _labels(oracle, chart, root, branch, family)
                    start, end = node_keys[index, branch], node_keys[index + 1, branch]
                    collapsed = axis_only or (not labels[2] and bool(family.slope))
                    arcs.append(ConeArc(sign, I(a.interval.lo, b.interval.hi), a, b,
                                        branch, start, end, *labels, collapsed))
        return ConeTopology(family, tuple(vertices.values()), tuple(arcs), (), True,
                            oracle.queries, 'all exact critical roots and complementary cells covered')
    except (EnclosureUnavailable, IntervalBudgetError, ValueError, OverflowError) as exc:
        return ConeTopology(family, tuple(vertices.values()), tuple(arcs),
                            ((1, I(-1, 1)), (-1, I(-1, 1))), False, oracle.queries, str(exc))
