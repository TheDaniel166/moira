"""Fresh frozen-record/selected-policy checks for all 26 disputed epochs.

These are local real-reference sign checks, not complete event classifications
or an instruction to adopt any external catalog label.
"""
from dataclasses import replace
from fractions import Fraction as F
import json
from pathlib import Path

import pytest

from moira._eclipse_angular_contacts import bound_angular_lunar_contacts
from moira._eclipse_continuous_lunar import (build_continuous_lunar_reference,
    enclose_continuous_lunar_reference, verify_continuous_lunar_record_words)
from moira._eclipse_continuous_lunar_contacts import bound_continuous_lunar_contacts
from moira._eclipse_interval import RationalInterval as I
from moira._eclipse_interval_roots import EnclosureUnavailable
from moira.constants import EARTH_RADIUS_KM


DATA = json.loads((Path(__file__).parents[1]/'fixtures/lunar_shadow_26_research_reference.json').read_text())


@pytest.mark.requires_ephemeris
@pytest.mark.parametrize('case', DATA['cases'], ids=lambda case: str(case['lunation']))
def test_selected_record_words_and_both_reference_policies(planetary_reader, case):
    model = build_continuous_lunar_reference(planetary_reader, case['seed_tt'], I.point(0))
    verified = verify_continuous_lunar_record_words(planetary_reader, model)
    assert not model.raw_record_mid_radius_verified
    assert verified.raw_record_mid_radius_verified and len(verified.raw_record_word_sha256) == 4
    vectors = enclose_continuous_lunar_reference(verified, I.point(0))
    assert vectors.raw_record_mid_radius_verified
    angular = bound_angular_lunar_contacts(vectors).margins[0]
    cone = bound_continuous_lunar_contacts(vectors,
        effective_earth_radius_km=EARTH_RADIUS_KM*1.01).penumbral_margin_km
    for value, key in ((angular, 'angular_maximum_margins_km'), (cone, 'cone_maximum_margins_km')):
        prior = case[key]['penumbral']
        if abs(prior) > 0.1:
            assert value.lo > 0 if prior > 0 else value.hi < 0
    assert not vectors.source_and_kernel_attested and not vectors.legacy_evaluator_enclosed


@pytest.mark.requires_ephemeris
def test_word_verification_rejects_changed_model_and_missing_routes(planetary_reader):
    model = build_continuous_lunar_reference(planetary_reader, 2459891.96, I.point(0))
    record = model.records[0]
    axes = [list(axis) for axis in record.coefficients]
    axes[0][0] += F(1, 1000)
    changed = replace(record, coefficients=tuple(tuple(axis) for axis in axes))
    with pytest.raises(EnclosureUnavailable, match='coefficient'):
        verify_continuous_lunar_record_words(planetary_reader,
            replace(model, records=(changed, *model.records[1:])))
    with pytest.raises(EnclosureUnavailable, match='four distinct'):
        verify_continuous_lunar_record_words(planetary_reader, replace(model, records=()))
