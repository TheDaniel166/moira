"""Independent ERFA/SOFA frame/anchor evidence for every admitted ayanamsa.

Thresholds are frozen in gochara_windows_validation_spec.json. Star propagation
models differ; these are angular comparisons, never a subsecond event oracle.
"""
import json
import math
from pathlib import Path
import pytest

from moira.sidereal import Ayanamsa,_STAR_ANCHORED,_AYANAMSA_AT_J2000,_ayanamsa_at_tt,_anchor_product
from moira.stars import star_at
from moira import stars
from tests.integration.test_stars_erfa_reference import _erfa_fixed_star_position,_registry_by_name,_rot_x_passive
from tests.integration.test_stars_apparent_erfa import _erfa_apparent

erfa=pytest.importorskip("erfa")
SPEC=json.loads((Path(__file__).parents[1]/"fixtures/gochara_windows_validation_spec.json").read_text())
pytestmark=pytest.mark.integration


def _erfa_apparent_longitude(name,tt,reader):
    """ERFA apcg/atciq apparent place of a catalog star, true ecliptic of date."""
    record={r.name:r for r in stars._load_registry_records()}[name]
    p_icrs=_erfa_apparent(record,tt,reader)
    jd_a,jd_b=float(int(tt)),float(tt-int(tt))
    p_true_equ=tuple(float(v) for v in erfa.rxp(erfa.pnm06a(jd_a,jd_b),p_icrs))
    eps_true=erfa.obl06(jd_a,jd_b)+erfa.nut06a(jd_a,jd_b)[1]
    lon,_=erfa.c2s(_rot_x_passive(p_true_equ,eps_true))
    return math.degrees(lon)%360.0


@pytest.mark.parametrize("system",Ayanamsa.ALL)
@pytest.mark.parametrize("tt",SPEC["frames_and_anchors"]["epochs_tt"])
def test_named_offsets_against_independent_erfa_composition(system,tt,request):
    rules=SPEC["frames_and_anchors"]
    if system in _STAR_ANCHORED:
        anchor,target=_STAR_ANCHORED[system]
        product=_anchor_product(system)
        if product=="apparent":
            # The (apparent) systems anchor on the apparent star: ERFA apcg/atciq.
            reader=request.getfixturevalue("planetary_reader")
            lon=_erfa_apparent_longitude(anchor,tt,reader)
        else:
            reader=None
            lon,_=_erfa_fixed_star_position(_registry_by_name()[anchor],tt)
        expected=(lon-target)%360
        actual=(star_at(anchor,tt,product=product,reader=reader).longitude-target)%360
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
