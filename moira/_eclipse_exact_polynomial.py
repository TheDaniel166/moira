"""Exact polynomial queries for bounded eclipse topology.

Coefficients are ascending rationals. Root counts use the classical signed
Euclidean remainder (Sturm) theorem: variations ignore zero entries; V(a)-
V(b) counts (a,b], and subtracting a root at b gives (a,b). Repeated factors
are removed for isolation and retained through the gcd derivative chain for
multiplicity. Positive-content primitive remainders preserve Sturm signs.
No floating coefficient trim, numerical near-zero or sampled root scan is
used. Degree/coefficient/query/refinement limits fail explicitly.

The theorem is independently formalized in Manuel Eberl, Sturm's Theorem,
Archive of Formal Proofs (2014), https://isa-afp.org/entries/Sturm_Sequences.html.
The implementation below is derived from polynomial division and that sign
variation statement; it does not call an external algebra package.
"""
from dataclasses import dataclass,replace
from fractions import Fraction as F
from functools import reduce
from math import gcd,lcm

from ._eclipse_interval import RationalInterval as I
from ._eclipse_interval_roots import EnclosureUnavailable


class ExactPolynomialBudgetError(EnclosureUnavailable):
    """An exact algebra or root-query resource bound was exhausted."""


def trim(p):
    p = tuple(p)
    while p and not p[-1]:
        p = p[:-1]
    return p


def poly(p):
    # Algebraic pseudo-remainders legitimately exceed interval endpoint
    # sizes; their separate coefficient/degree budget is checked below.
    def exact(c):
        if isinstance(c,bool) or not isinstance(c,(int,float,F)):
            raise ValueError('finite real polynomial coefficients required')
        return F(c)
    return trim(exact(c) for c in p)


def add(a,b):
    return trim((a[k] if k<len(a) else 0)+(b[k] if k<len(b) else 0)
                for k in range(max(len(a),len(b))))


def scale(p,c):
    return trim(c*x for x in p)


def sub(a,b):
    return add(a,scale(b,-1))


def mul(a,b):
    if not a or not b:
        return ()
    result = [F(0)]*(len(a)+len(b)-1)
    for i,x in enumerate(a):
        for j,y in enumerate(b):
            result[i+j] += x*y
    return trim(result)


def derivative(p):
    return trim(k*p[k] for k in range(1,len(p)))


def evaluate(p,x):
    result = F(0)
    for c in reversed(p):
        result = result*x+c
    return result


def enclose(p,box, *, bits=256):
    result = I.point(0)
    for c in reversed(p):
        result = (result*box+c).quantize_outward(bits)
    return result


def primitive(p, *, positive_leading=False):
    p = poly(p)
    if len(p)>49 or any(max(c.numerator.bit_length(),c.denominator.bit_length())>131072 for c in p):
        raise ExactPolynomialBudgetError('polynomial degree/coefficient limit')
    denominator = lcm(*(c.denominator for c in p)) if p else 1
    if denominator.bit_length()>262144:
        raise ExactPolynomialBudgetError('polynomial common-denominator limit')
    integers = tuple(int(c*denominator) for c in p)
    content = reduce(gcd,(abs(c) for c in integers),0) or 1
    if positive_leading and integers and integers[-1]<0:
        content = -content
    return tuple(c//content for c in integers)


def remainder(a,b):
    """Return a positive multiple of rem(a,b), using primitive integers.

    Each elimination multiplies by ABS(lc(b)), then subtracts the signed
    multiple of b. Thus the remaining polynomial has the true remainder's
    sign even when lc(b)<0. Removing a positive gcd changes no sign.
    """
    a,b = primitive(a),primitive(b)
    if not b:
        raise ZeroDivisionError('zero polynomial divisor')
    r = a
    lead = b[-1]
    while r and len(r)>=len(b):
        shift = len(r)-len(b)
        value = r[-1]*(1 if lead>0 else -1)
        r = primitive(sub(scale(r,abs(lead)),(0,)*shift+scale(b,value)))
    return r


def quotient(a,b):
    """Perform exact rational division; reject a nonzero remainder."""
    a,b = poly(a),poly(b)
    if not b:
        raise ZeroDivisionError('zero polynomial divisor')
    result = [F(0)]*max(0,len(a)-len(b)+1)
    r = a
    while r and len(r)>=len(b):
        shift = len(r)-len(b)
        value = r[-1]/b[-1]
        result[shift] += value
        r = sub(r,(0,)*shift+scale(b,value))
    if r:
        raise ValueError('polynomial division is not exact')
    return trim(result)


def polynomial_gcd(a,b):
    a,b = primitive(a),primitive(b)
    while b:
        a,b = b,remainder(a,b)
    return primitive(a,positive_leading=True)


def squarefree(p):
    p = primitive(p,positive_leading=True)
    return primitive(quotient(p,polynomial_gcd(p,derivative(p))),positive_leading=True) if len(p)>1 else p


def _integer_sign_at(p,x):
    """Evaluate only the sign, homogenizing by the positive denominator."""
    if not p:
        return 0
    n,d = x.numerator,x.denominator
    value,power = p[-1],d
    for c in reversed(p[:-1]):
        value = value*n+c*power
        power *= d
    return (value>0)-(value<0)


@dataclass(frozen=True, slots=True)
class ExactRealRoot:
    """A unique closed real-root enclosure and its original multiplicity."""

    polynomial: tuple[int,...]
    interval: I
    multiplicity: int = 1


@dataclass(frozen=True, slots=True)
class ExactRootIsolation:
    """All distinct roots, or explicit unresolved portions of the domain."""

    domain: I
    polynomial: tuple[int,...]
    roots: tuple[ExactRealRoot,...]
    unresolved: tuple[I,...]
    complete: bool
    queries: int
    reason: str


class ExactPolynomialOracle:
    """Request-local signed remainder, gcd and algebraic sign queries.

    The query budget counts variation/sign/refinement queries. Polynomial
    degree and coefficient size have separate finite bounds. This oracle
    owns no ambient/global caches and no platform floating-point tests.

    RITE: Exact polynomial oracle.
    THEOREM: Signed primitive Sturm chains count real roots exactly.
    RITE OF PURPOSE: Preserve contacts and complementary root exclusions.
    LAW OF OPERATION: Own request caches; enforce explicit finite budgets.
    Canon: Eberl, Sturm's Theorem (AFP 2014); exact rational arithmetic.
    [MACHINE_CONTRACT v1]
    {"scope":"private exact eclipse algebra","id":"moira.eclipse.exact_polynomial",
     "risk":"high","api":["isolate","sign","count_closed","refine"],
     "state":{"mutable":true,"owners":["request caller"],"contents":"chains, gcds, squarefrees, query counter"},
     "effects":["request-local cache mutation"],
     "concurrency":{"thread":"request_local","cross_thread_calls":"forbidden","owner_thread_only_mutation":true},
     "failures":["explicit query, degree, coefficient and refinement budgets"],
     "succession":"no external algebra dependency","agent":"derived from rational division and Sturm variations"}
    [/MACHINE_CONTRACT]
    """

    def __init__(self, *, max_queries=100000,max_refinement_bits=1024):
        if any(type(v) is not int or v<0 for v in (max_queries,max_refinement_bits)):
            raise ValueError('nonnegative integer algebra budgets required')
        self.max_queries,self.max_refinement_bits = max_queries,max_refinement_bits
        self.queries = 0
        self._chains,self._gcds,self._squarefrees = {},{},{}

    def _tick(self):
        if self.queries>=self.max_queries:
            raise ExactPolynomialBudgetError('exact polynomial query budget')
        self.queries += 1

    def _sf(self,p):
        p = primitive(p,positive_leading=True)
        if p not in self._squarefrees:
            self._squarefrees[p] = squarefree(p)
        return self._squarefrees[p]

    def chain(self,p):
        p = self._sf(p)
        if not p:
            raise ValueError('the zero polynomial has no finite root count')
        if p not in self._chains:
            values = [p]
            if len(p)>1:
                values.append(primitive(derivative(p)))
                while values[-1]:
                    next_value = scale(remainder(values[-2],values[-1]),-1)
                    if not next_value:
                        break
                    values.append(next_value)
            self._chains[p] = tuple(values)
        return self._chains[p]

    def variations(self,p,x):
        self._tick()
        signs = tuple(s for q in self.chain(p) if (s:=_integer_sign_at(q,F(x))))
        return sum(a!=b for a,b in zip(signs,signs[1:]))

    def count_open(self,p,lo,hi):
        p = self._sf(p)
        if not p:
            raise ValueError('zero polynomial root count is infinite')
        if lo>=hi or len(p)<=1:
            return 0
        return self.variations(p,lo)-self.variations(p,hi)-int(_integer_sign_at(p,F(hi))==0)

    def count_closed(self,p,box):
        p = self._sf(p)
        if not p:
            raise ValueError('zero polynomial root count is infinite')
        if not box.width:
            return int(_integer_sign_at(p,box.lo)==0)
        return (self.count_open(p,box.lo,box.hi)+int(_integer_sign_at(p,box.lo)==0)
                +int(_integer_sign_at(p,box.hi)==0))

    def refine(self,root):
        self._tick()
        if not root.interval.width:
            return root
        box = root.interval
        if box.width<F(1,2**self.max_refinement_bits):
            raise ExactPolynomialBudgetError('algebraic refinement bit limit')
        middle = box.midpoint
        if not _integer_sign_at(root.polynomial,middle):
            return replace(root,interval=I.point(middle))
        left = self.count_open(root.polynomial,box.lo,middle)
        return replace(root,interval=I(box.lo,middle) if left else I(middle,box.hi))

    def sign(self,root,p):
        """Decide sign(p(alpha)); common roots are proved with exact gcds."""
        self._tick()
        p = primitive(p)
        if not p:
            return 0
        if not root.interval.width:
            return _integer_sign_at(p,root.interval.lo)
        if len(p)>=len(root.polynomial):
            # At alpha, a positive pseudo-division multiplier preserves sign.
            # Reducing here avoids high-degree radical comparison gcds.
            p = primitive(remainder(p,root.polynomial))
            if not p:
                return 0
        scale_value = max(map(abs,p))
        normalized = tuple(F(c,scale_value) for c in p)
        initial = enclose(normalized,root.interval,bits=160)
        if initial.lo>0:
            return 1
        if initial.hi<0:
            return -1
        key = root.polynomial,p
        if key not in self._gcds:
            self._gcds[key] = polynomial_gcd(*key)
        common = self._gcds[key]
        if len(common)>1 and self.count_closed(common,root.interval):
            return 0
        current = root
        while True:
            bits = max(160,current.interval.width.denominator.bit_length()+48)
            value = enclose(normalized,current.interval,bits=bits)
            if value.lo>0:
                return 1
            if value.hi<0:
                return -1
            current = self.refine(current)

    def isolate(self,p,domain=I(-1,1), *, tolerance=F(1,2**40)):
        """Isolate every distinct root, including endpoints and repeated roots."""
        original = primitive(p)
        if not original:
            return ExactRootIsolation(domain,original,(),(domain,),False,self.queries,'zero_polynomial')
        if len(original)==1:
            return ExactRootIsolation(domain,original,(),(),True,self.queries,'constant_polynomial')
        if not isinstance(domain,I) or tolerance<=0:
            raise ValueError('exact domain and positive tolerance required')
        q = squarefree(original)
        roots = []
        for x in {domain.lo,domain.hi}:
            if not _integer_sign_at(q,x):
                roots.append(ExactRealRoot(q,I.point(x)))
        stack,unknown = [domain],[]
        try:
            while stack:
                box = stack.pop()
                count = self.count_open(q,box.lo,box.hi)
                if not count:
                    continue
                if (count==1 and box.width<=tolerance and _integer_sign_at(q,box.lo)
                        and _integer_sign_at(q,box.hi)):
                    roots.append(ExactRealRoot(q,box))
                    continue
                if box.width<F(1,2**self.max_refinement_bits):
                    raise ExactPolynomialBudgetError('root isolation refinement bit limit')
                mid = box.midpoint
                if not _integer_sign_at(q,mid):
                    roots.append(ExactRealRoot(q,I.point(mid)))
                stack.extend((I(mid,box.hi),I(box.lo,mid)))
        except ExactPolynomialBudgetError as exc:
            unknown.extend((box,*stack))
            return ExactRootIsolation(domain,original,tuple(sorted(roots,key=lambda r:r.interval.lo)),
                tuple(unknown),False,self.queries,str(exc))
        # gcd(f,f') removes one multiplicity at each step. Isolating q
        # already proves that membership of a gcd is this SAME unique root.
        repeated = polynomial_gcd(original,derivative(original))
        chain = []
        while len(repeated)>1:
            chain.append(squarefree(repeated))
            repeated = polynomial_gcd(repeated,derivative(repeated))
        try:
            roots = [replace(r,multiplicity=1+sum(bool(self.count_closed(g,r.interval)) for g in chain))
                     for r in roots]
        except ExactPolynomialBudgetError as exc:
            return ExactRootIsolation(domain,original,tuple(roots),(domain,),False,self.queries,str(exc))
        return ExactRootIsolation(domain,original,tuple(sorted(roots,key=lambda r:r.interval.lo)),(),True,
                                  self.queries,'exact_sturm_partition')
