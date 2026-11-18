"""Outward binary64 boxes used to evaluate the already certified source slabs."""

from dataclasses import dataclass

import numpy as np


def down(value):
    return np.nextafter(value, -np.inf)


def up(value):
    return np.nextafter(value, np.inf)


@dataclass(frozen=True, slots=True)
class Box:
    lo: object
    hi: object

    @staticmethod
    def point(value):
        return Box(value, value)

    @staticmethod
    def from_rational(bounds):
        return Box(*bounds.to_float_bounds())

    def __getitem__(self, index):
        return Box(self.lo[index], self.hi[index])

    def __add__(self, other):
        return Box(down(self.lo + other.lo), up(self.hi + other.hi))

    def __neg__(self):
        return Box(-self.hi, -self.lo)

    def __sub__(self, other):
        return self + (-other)

    def __mul__(self, other):
        a, b = self.lo * other.lo, self.lo * other.hi
        c, d = self.hi * other.lo, self.hi * other.hi
        return Box(down(np.minimum(np.minimum(a, b), np.minimum(c, d))),
                   up(np.maximum(np.maximum(a, b), np.maximum(c, d))))

    def positive_reciprocal(self):
        if np.any(self.lo <= 0):
            raise ArithmeticError("positive interval required for reciprocal")
        return Box(down(1 / self.hi), up(1 / self.lo))

    def square(self):
        a, b = self.lo * self.lo, self.hi * self.hi
        lo = np.where((self.lo <= 0) & (self.hi >= 0), 0, np.minimum(a, b))
        return Box(np.maximum(0, down(lo)), up(np.maximum(a, b)))

    def sqrt(self):
        if np.any(self.hi < 0):
            raise ArithmeticError("nonnegative interval required for square root")
        return Box(np.maximum(0, down(np.sqrt(np.maximum(self.lo, 0)))), up(np.sqrt(self.hi)))

    def intersect(self, other):
        lo, hi = np.maximum(self.lo, other.lo), np.minimum(self.hi, other.hi)
        if np.any(lo > hi):
            raise ArithmeticError("inconsistent independent interval bounds")
        return Box(lo, hi)


def stack(boxes, axis=-1):
    boxes = tuple(boxes)
    return Box(np.stack([box.lo for box in boxes], axis=axis),
               np.stack([box.hi for box in boxes], axis=axis))


def rational_matrix(matrix):
    return stack(tuple(stack(map(Box.from_rational, row)) for row in matrix), axis=0)


def dot(a, b):
    v = a * b
    return v[..., 0] + v[..., 1] + v[..., 2]


def norm_squared(v):
    terms = v.square()
    return terms[..., 0] + terms[..., 1] + terms[..., 2]


def cross(a, b):
    return stack(a[..., i] * b[..., k] - a[..., k] * b[..., i] for i, k in ((1, 2), (2, 0), (0, 1)))
