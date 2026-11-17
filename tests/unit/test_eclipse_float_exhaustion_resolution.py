"""Exhaustion leaf size does not weaken adjacent-input contact resolution."""
from fractions import Fraction as F
import math

from moira._eclipse_solar_float_coverage import cover_native_solar_float_path
from tests.unit.test_eclipse_solar_float_coverage import _functions,ANCHOR,DOMAIN


def test_coarser_exhaustion_cells_keep_exactly_the_same_native_boundaries():
    bound,evaluate = _functions('H3')
    fine = cover_native_solar_float_path(ANCHOR,DOMAIN,bound,evaluate,
        tolerance=F(1,86400000),max_point_evaluations=100000)
    coarse = cover_native_solar_float_path(ANCHOR,DOMAIN,bound,evaluate,
        tolerance=F(1,864000),max_point_evaluations=100000)
    assert fine.all_represented_inputs_covered and coarse.all_represented_inputs_covered
    assert coarse.components==fine.components and coarse.sequence==fine.sequence
    assert coarse.subtype==fine.subtype=='H3'
    for entry,exit in coarse.components:
        for before,after in (entry,exit):
            assert math.nextafter(before,math.inf)==after
            assert (after-before)*86400<.001
