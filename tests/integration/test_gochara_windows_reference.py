"""Independent ERFA/SOFA frame/anchor evidence for every admitted ayanamsa.

Thresholds are frozen in gochara_windows_validation_spec.json. Star propagation
models differ; these are angular comparisons, never a subsecond event oracle.
"""
import json
import math
from pathlib import Path
import pytest

from moira.sidereal import Ayanamsa,_STAR_ANCHORED,_AYANAMSA_AT_J2000,_ayanamsa_at_tt
from moira.stars import star_at
from tests.integration.test_stars_erfa_reference import _erfa_fixed_star_position,_registry_by_name

erfa=pytest.importorskip("erfa")
SPEC=json.loads((Path(__file__).parents[1]/"fixtures/gochara_windows_validation_spec.json").read_text())
pytestmark=pytest.mark.integration


@pytest.mark.parametrize("system",Ayanamsa.ALL)
@pytest.mark.parametrize("tt",SPEC["frames_and_anchors"]["epochs_tt"])
def test_named_offsets_against_independent_erfa_composition(system,tt):
    rules=SPEC["frames_and_anchors"]
    if system in _STAR_ANCHORED:
        anchor,target=_STAR_ANCHORED[system]
        lon,_=_erfa_fixed_star_position(_registry_by_name()[anchor],tt)
        expected=(lon-target)%360
        actual=(star_at(anchor,tt).longitude-target)%360
        tolerance=rules["anchor_threshold_degrees"]
    else:
        # p06e's general precession in longitude is returned in radians.
        precession=float(erfa.p06e(2451545.,tt-2451545.)[12])
        dpsi=float(erfa.nut06a(2451545.,tt-2451545.)[0])
        expected=_AYANAMSA_AT_J2000[system]+math.degrees(precession+dpsi)
        actual=_ayanamsa_at_tt(tt,system,"true")
        tolerance=rules["polynomial_threshold_degrees"]
    difference=abs((actual-expected+180)%360-180)
    assert difference<=tolerance,(system,tt,difference,tolerance)
