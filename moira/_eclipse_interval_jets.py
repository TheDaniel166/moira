"""Second-order interval chain rules for bounded eclipse reference functions.

A jet is (value, first derivative, second derivative) in one declared time
coordinate. Product, inverse and composition rules are applied with exact
rational intervals and outward 128-bit dyadic quantization. A jet never
asserts continuity across a source branch; its caller owns that obligation.
"""
from ._eclipse_interval import RationalInterval as I
from ._eclipse_interval_elementary import sin_cos_enclosure
from ._eclipse_interval_roots import EnclosureUnavailable


def q(value):
    """Round an interval outward to the working dyadic grid."""
    return value.quantize_outward(128)


def constant(value):
    """Give a time-independent scalar its zero derivatives."""
    return I.point(value), I.point(0), I.point(0)


def variable(value):
    """Give a scalar time interval unit rate and zero acceleration."""
    return value, I.point(1), I.point(0)


def add(a, b):
    return tuple(q(x+y) for x,y in zip(a,b))


def neg(a):
    return tuple(-x for x in a)


def sub(a, b):
    return add(a,neg(b))


def mul(a, b):
    return q(a[0]*b[0]), q(a[1]*b[0]+a[0]*b[1]), q(a[2]*b[0]+2*a[1]*b[1]+a[0]*b[2])


def scale(a, value):
    return mul(a,constant(value))


def inverse(a):
    if a[0].contains_zero:
        raise EnclosureUnavailable('jet inverse denominator contains zero')
    return q(1/a[0]), q(-a[1]/a[0].square()), q(2*a[1].square()/(a[0]**3)-a[2]/a[0].square())


def div(a, b):
    return mul(a,inverse(b))


def square(a):
    return q(a[0].square()), q(2*a[0]*a[1]), q(2*a[1].square()+2*a[0]*a[2])


def sqrt(a):
    if a[0].lo <= 0:
        raise EnclosureUnavailable('jet square-root differentiability not proved')
    root = a[0].sqrt(128)
    return q(root), q(a[1]/(2*root)), q(a[2]/(2*root)-a[1].square()/(4*root**3))


def sin_cos(a):
    trig = sin_cos_enclosure(a[0],precision_bits=128)
    s,c = trig.sine,trig.cosine
    return ((s,q(c*a[1]),q(c*a[2]-s*a[1].square())),
            (c,q(-s*a[1]),q(-s*a[2]-c*a[1].square())))


def polynomial(x, coefficients):
    """Evaluate an ascending-power polynomial by the chain/product rules."""
    result = constant(0)
    for coefficient in reversed(coefficients):
        result = add(mul(result,x),constant(coefficient))
    return result


def dot(a, b):
    result = constant(0)
    for x,y in zip(a,b):
        result = add(result,mul(x,y))
    return result


def norm(a):
    value = constant(0)
    for x in a:
        value = add(value,square(x))
    return sqrt(value)


def vector_add(a, b):
    return tuple(add(x,y) for x,y in zip(a,b))


def vector_sub(a, b):
    return tuple(sub(x,y) for x,y in zip(a,b))


def matrix_product(a, b):
    return tuple(tuple(dot(row,tuple(b[k][j] for k in range(3))) for j in range(3)) for row in a)


def matrix_vector(a, b):
    return tuple(dot(row,b) for row in a)


def rotation_x(angle):
    s,c = sin_cos(angle)
    z,o = constant(0),constant(1)
    return ((o,z,z),(z,c,s),(z,neg(s),c))


def rotation_z(angle):
    s,c = sin_cos(angle)
    z,o = constant(0),constant(1)
    return ((c,s,z),(neg(s),c,z),(z,z,o))
