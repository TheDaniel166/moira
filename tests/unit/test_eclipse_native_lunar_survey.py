"""A known neighborhood cannot hide an additional possible event elsewhere."""
from fractions import Fraction as F
from types import SimpleNamespace

import moira._eclipse_native_lunar_survey as survey
from moira._eclipse_interval import RationalInterval as I


def test_second_overlap_outside_the_supplied_domain_stays_blocking(monkeypatch):
    monkeypatch.setattr(survey,'freeze_native_vector_scope',lambda *a:object())

    def rays(scope,box,**kwargs):
        y = box*(box-10)*100000
        return SimpleNamespace(sun_retarded_km=(I.point(1.5e8),I.point(0),I.point(0)),
            moon_retarded_km=(I.point(-400000),y,I.point(0)))

    monkeypatch.setattr(survey,'bound_frozen_native_vectors',rays)
    result = survey.survey_native_lunar_interval(object(),2451545.,I(-1,11),policy='danjon_angular',
        covered_event_domains=(I(F(-3,10),F(3,10)),),max_evaluations=128,max_native_points=0)
    assert not result.all_represented_inputs_resolved
    assert any(cell.status=='unresolved' and cell.domain.contains(F(10)) for cell in result.cells)
    assert survey.first_native_lunar_candidate(result,backward=True).status=='unresolved'
