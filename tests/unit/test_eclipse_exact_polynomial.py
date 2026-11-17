"""Factorized exact controls for Sturm isolation and algebraic sign queries."""
from fractions import Fraction as F
import random

import pytest

from moira._eclipse_interval import RationalInterval as I
from moira._eclipse_exact_polynomial import (ExactPolynomialOracle,ExactPolynomialBudgetError,
    add,mul,scale,poly,derivative,evaluate,polynomial_gcd,squarefree,remainder,primitive)


def from_roots(roots):
    p = (F(1),)
    for root in roots:
        p = mul(p,(-root,F(1)))
    return p


def test_zero_width_domain_retains_its_single_endpoint_once():
    oracle = ExactPolynomialOracle()
    result = oracle.isolate(poly((0,1)),I.point(0))
    assert result.complete and len(result.roots) == 1
    assert oracle.count_open(poly((0,1)),F(0),F(0)) == 0


@pytest.mark.parametrize('roots',[[],[F(0)],[F(-1),F(1)],[F(0)]*4,
    [F(-1)]*3+[F(1)]*2,[F(1,3),F(1,3),F(2,3)],
    [F(0),F(1,2**100),F(1,2**99)], [F(-1),F(-1)+F(1,2**70),F(1)]])
def test_all_known_roots_and_multiplicities_are_isolated(roots):
    p = from_roots(roots)
    oracle = ExactPolynomialOracle()
    result = oracle.isolate(p,tolerance=F(1,2**120))
    assert result.complete and not result.unresolved
    assert len(result.roots)==len(set(roots))
    for known,found in zip(sorted(set(roots)),result.roots):
        assert found.interval.contains(known) and found.multiplicity==roots.count(known)
        assert oracle.count_closed(found.polynomial,found.interval)==1


def test_no_real_roots_and_exact_sign_at_irrational_root():
    oracle = ExactPolynomialOracle()
    assert oracle.isolate((1,0,1)).complete
    assert not oracle.isolate((1,0,1)).roots
    roots = oracle.isolate((-F(1,2),0,1)).roots
    positive = roots[1]
    assert oracle.sign(positive,(-F(1,2),0,1))==0
    assert oracle.sign(positive,(-F(7,10),1))==1
    assert oracle.sign(positive,(-F(8,10),1))==-1
    assert oracle.sign(positive,(0,1))==1


def test_positive_pseudoremainder_preserves_true_rational_sign():
    rng = random.Random(20261118)
    for _ in range(50):
        a = poly(rng.randint(-10,10) for _ in range(7))
        b = poly([rng.randint(-10,10),rng.randint(-10,10),-rng.randint(1,10)])
        actual = remainder(a,b)
        # Independent ordinary rational long division.
        r = list(a)
        while r and len(r)>=len(b):
            value,shift = r[-1]/b[-1],len(r)-len(b)
            for j in range(len(b)):
                r[j+shift] -= value*b[j]
            while r and r[-1]==0:
                r.pop()
        if r:
            ratio = F(actual[-1])/r[-1]
            assert ratio>0 and tuple(c*ratio for c in r)==actual
        else:
            assert not actual


def test_endpoint_count_open_closed_and_gcds():
    p = from_roots([F(-1),F(0),F(0),F(1)])
    oracle = ExactPolynomialOracle()
    assert oracle.count_open(p,F(-1),F(1))==1
    assert oracle.count_closed(p,I(-1,1))==3
    assert squarefree(p)==primitive(from_roots([F(-1),F(0),F(1)]),positive_leading=True)
    assert polynomial_gcd(p,derivative(p))==(0,1)
    assert evaluate(add(p,scale(p,-1)),F(3))==0


def test_budget_and_identically_zero_polynomial_stay_unresolved():
    result = ExactPolynomialOracle(max_queries=0).isolate((-F(1,2),0,1))
    assert not result.complete and result.unresolved
    zero = ExactPolynomialOracle().isolate(())
    assert not zero.complete and zero.reason=='zero_polynomial'
    with pytest.raises(ExactPolynomialBudgetError):
        primitive([1]*50)
