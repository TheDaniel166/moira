"""Shallow phases close with scalar Taylor transport, never widened budgets."""
from fractions import Fraction as F
import json
from pathlib import Path

import pytest

from moira._eclipse_interval import RationalInterval as I
from moira._eclipse_frozen_native_vectors import freeze_native_vector_scope
from moira._eclipse_refined_native_lunar import cover_refined_native_lunar


DATA = json.loads((Path(__file__).parents[1]/'fixtures/lunar_shadow_26_research_reference.json').read_text())


@pytest.mark.requires_ephemeris
@pytest.mark.parametrize('lunation,policy,scale',[(-34373,'static_finite_cone',1.01),
    (-28663,'danjon_angular',1.),(-28346,'static_finite_cone',1.01)])
def test_shallow_native_phase_complements_close_at_the_original_budget(planetary_reader,lunation,policy,scale):
    case = next(case for case in DATA['cases'] if case['lunation']==lunation)
    domain = I(F(-3,10),F(3,10))
    scope = freeze_native_vector_scope(planetary_reader,case['seed_tt'],domain)
    result = cover_refined_native_lunar(scope,planetary_reader,policy=policy,earth_radius_scale=scale)
    assert result.all_represented_inputs_covered
    assert all(phase.interval_evaluations<4096 for phase in result.phases)
    assert not any(cell.state=='unresolved' for phase in result.phases for cell in phase.cells)
    assert result.error_tube.finite_split_route_under_premises
