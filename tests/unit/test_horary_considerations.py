"""P3 production considerations checked against pre-existing source-derived fixtures."""
from dataclasses import FrozenInstanceError, asdict, replace
import json
import math
from pathlib import Path

import pytest

from moira.horary_reception import LillySnapshotContext, LillyPlanetPosition, lilly_condition_snapshot
from moira.horary_considerations import (
    LillyFigureKind, LillyQualitativeKind as Kind, LillyQualitativeEvidence, LillyQuestionBinding, LillyHourAssertion,
    lilly_early_ascendant, lilly_late_ascendant, lilly_late_moon, lilly_via_combusta,
    lilly_artist_warning, lilly_saturn_considerations, lilly_seventh_lord_warning,
    lilly_solar_proximity, lilly_first_ruler_combust, lilly_lunar_orientation,
    lilly_voc_qualification, lilly_testimony_balance, lilly_hour_agreement, adapt_horary_planetary_hour,
)
from moira.horary_moon import (
    LillyP3State as State, LillyTimeInterval as Interval, LillyMoonTrace, LillyMoonCoverage,
    LillyCoverageState as Coverage, LillyMoonProvenance, LillyVOCDefinition, LillyMoonContact,
    lilly_void_of_course,
)

DATA = json.loads((Path(__file__).parents[1] / "fixtures/horary/lilly_p3_moon_considerations_2026_10_23.json").read_text(encoding="utf-8"))
CASES = [c for c in DATA["fixtures"] if c["family"] != "voc"]
CONTEXT = LillySnapshotContext("synthetic-P3-considerations", None, 1000.)


def assessment(value, subjects, context=CONTEXT, kind=Kind.VERY_YOUNG):
    if value is None:
        return None
    return LillyQualitativeEvidence(context, kind, State.PRESENT if value else State.ABSENT,
        subjects, "fixture-independent-qualitative-premise", "Synthetic source-qualified premise; no numerical score", ("fixture-attestation",))


def snapshot(body, sign, degree=None, context=CONTEXT):
    return lilly_condition_snapshot(LillyPlanetPosition(body, sign, degree), context=context)


def raw_voc(state):
    study = Interval(999.,1001.)
    cov = LillyMoonCoverage(study, Coverage.COMPLETE, "synthetic-fixture")
    trace = LillyMoonTrace(CONTEXT, LillyMoonProvenance("fixture", "synthetic", "none", "synthetic_JD"),study,
        Interval(1000.1,1000.1), (LillyMoonContact("future", "Saturn", 120., Interval(1000.05,1000.05)),)
        if state == "absent" else (), (), (), cov,cov,cov,
        State.PRESENT if state != "not_evaluable" else State.NOT_EVALUABLE, ("fixture-prior-separation",))
    return lilly_void_of_course(trace, definition=LillyVOCDefinition.EXACT_BEFORE_INGRESS)


@pytest.mark.parametrize("case", CASES, ids=lambda c:c["id"])
def test_runtime_matches_independently_specified_p3_consideration_fixtures(case):
    x, expected, family = case["inputs"],case["expected"],case["family"]
    if family == "early_ascendant":
        result = lilly_early_ascendant(x["degree"], context=CONTEXT,
            very_young=assessment(x["very_young"],("querent",)), description_matches=assessment(x["description_matches"],("querent",),kind=Kind.DESCRIPTION_MATCHES))
        assert result.trigger.value == ("present" if expected["raw_trigger"] else "absent")
        assert result.qualification.value == expected["qualification"] and result.state.value == expected["caution"]
    elif family == "late_ascendant":
        result = lilly_late_ascendant(x["degree"], context=CONTEXT,
            figure_kind=None if x["figure_kind"] is None else LillyFigureKind(x["figure_kind"]),
            age_corresponds=assessment(x["age_corresponds"],("querent",),kind=Kind.AGE_CORRESPONDS), certain_event_time=assessment(x["certain_event_time"],("figure_event",),kind=Kind.CERTAIN_EVENT_TIME))
        assert result.trigger.value == ("present" if expected["raw_trigger"] else "absent")
        assert result.qualification.value == expected["qualification"] and result.state.value == expected["caution"]
    elif family == "via_combusta":
        from moira.horary_reception import lilly_position_from_longitude
        moon = lilly_condition_snapshot(lilly_position_from_longitude("Moon",x["longitude_deg"]),context=CONTEXT)
        result = lilly_via_combusta(moon,context=CONTEXT)
        assert (result.trigger is State.PRESENT) is expected["membership"]
        assert result.attribution == expected["attribution"]
    elif family == "voc_qualification":
        result = lilly_voc_qualification(raw_voc(x["raw_voc"]),snapshot("Moon",x["sign"]), principals=("Venus","Mars"),
            very_strong=assessment(x["principals_very_strong"],("principal_a:Venus","principal_b:Mars"),kind=Kind.PRINCIPALS_VERY_STRONG))
        assert result.voc.state.value == expected["raw_voc"] and result.state.value == expected["qualification"]
        assert result.predicted_outcome is expected["outcome"] is None
    elif family == "late_moon":
        result = lilly_late_moon(snapshot("Moon",x["sign"],x["degree"]),context=CONTEXT)
        assert result.state.value == expected["numeric_trigger"]
        assert dict(result.observed)["source_emphasis_sign"] is expected["emphasis_sign"]
    elif family == "artist_warning":
        result = lilly_artist_warning(context=CONTEXT,matter_concerns_seventh=x["matter_concerns_seventh"],
            cusp_afflicted=assessment(x["cusp_afflicted"],("seventh_cusp",),kind=Kind.SEVENTH_CUSP_AFFLICTED),
            lord_retrograde=assessment(x["lord_retrograde"],("seventh_lord",),kind=Kind.SEVENTH_LORD_RETROGRADE), lord_impeded=assessment(x["lord_impeded"],("seventh_lord",),kind=Kind.SEVENTH_LORD_IMPEDED))
        assert result.state.value == expected["caution"] and result.scope == expected["scope"]
    elif family == "saturn_warning":
        result = lilly_saturn_considerations(x["house"],context=CONTEXT)
        assert any(r.trigger is State.PRESENT for r in result) is expected["trigger"]
        assert all(dict(r.observed)["retrograde_enhancement"] == expected["retrograde_enhancement"] for r in result)
    elif family == "solar_geometry":
        result = lilly_solar_proximity("Jupiter",x["sun_longitude_arcseconds"]/3600,x["planet_longitude_arcseconds"]/3600,context=CONTEXT)
        assert result.band.value == expected["band"]
    elif family == "hour_source_example":
        binding=LillyQuestionBinding(LillySnapshotContext(case["id"]+":didactic_unspecified",None),case["id"],None,None)
        result=lilly_hour_agreement(x["ascendant_sign"],binding=binding,hour=LillyHourAssertion(binding,"Mars","p121-122_source_assertion"))
        assert getattr(result,expected["source_asserted_route"]) is State.PRESENT
        assert result.state is State.PRESENT and result.hour.origin == "source_asserted"
        assert result.binding.context.jd_ut is None
    elif family == "lunar_orientation":
        result=lilly_lunar_orientation(x["moon_minus_sun_deg"],0.,context=CONTEXT)
        assert result.state == expected["state"] and result.visibility_inferred is expected["visibility_inferred"]
    elif family == "role_attribution":
        assert expected["automatic_significator_assignment"] is False
        # Role assignment is deliberately absent from the runtime API; source
        # stance remains the fixture's documentary claim, not a new predicate.
        import moira.horary_moon as module
        assert not any("significator" in name for name in module.__all__)
    elif family == "testimony_balance":
        result=lilly_testimony_balance(context=CONTEXT)
        assert result.state.value == expected["deferral_trigger"]
    else:
        raise AssertionError(f"uncovered fixture family: {family}")


@pytest.mark.parametrize("other",[LillySnapshotContext("contact",None,1000.),LillySnapshotContext(CONTEXT.epoch,True,1000.),LillySnapshotContext(CONTEXT.epoch,None,1001.)])
def test_qualitative_evidence_cannot_be_transported_to_another_context(other):
    evidence=assessment(True,("querent",),other)
    with pytest.raises(ValueError,match="context/subjects"):
        lilly_early_ascendant(2,context=CONTEXT,very_young=evidence)
    with pytest.raises(ValueError,match="context/body"):
        lilly_via_combusta(snapshot("Moon","Libra",20,other),context=CONTEXT)


def test_numeric_scores_and_wrong_subjects_cannot_establish_qualitative_facts():
    with pytest.raises(TypeError,match="attributed"):
        lilly_early_ascendant(2,context=CONTEXT,very_young=True)
    with pytest.raises(ValueError,match="subjects"):
        lilly_early_ascendant(2,context=CONTEXT,very_young=assessment(True,("seventh_lord",)))
    with pytest.raises(ValueError,match="subjects"):
        lilly_voc_qualification(raw_voc("present"),snapshot("Moon","Aries"),principals=("Venus","Mars"),
            very_strong=assessment(True,("Venus",),kind=Kind.PRINCIPALS_VERY_STRONG))
    result=lilly_voc_qualification(raw_voc("present"),snapshot("Moon","Aries"),principals=("Venus","Venus"),
        very_strong=assessment(True,("principal_a:Venus","principal_b:Venus"),kind=Kind.PRINCIPALS_VERY_STRONG))
    assert result.state is State.PRESENT  # roles can collide; no replacement planet invented


def test_missing_inputs_preserve_unknown_and_known_negative_evidence():
    assert lilly_early_ascendant(None,context=CONTEXT).state is State.NOT_EVALUABLE
    assert lilly_early_ascendant(5,context=CONTEXT).state is State.ABSENT
    assert lilly_late_ascendant(20,context=CONTEXT,figure_kind=None).state is State.ABSENT
    assert lilly_via_combusta(snapshot("Moon","Aries"),context=CONTEXT).state is State.ABSENT
    assert lilly_via_combusta(snapshot("Moon","Libra"),context=CONTEXT).state is State.NOT_EVALUABLE
    assert lilly_late_moon(None,context=CONTEXT).state is State.NOT_EVALUABLE
    assert lilly_lunar_orientation(None,0,context=CONTEXT).state == "not_evaluable"
    assert lilly_solar_proximity("Mars",None,10,context=CONTEXT).combustion is State.NOT_EVALUABLE
    assert lilly_first_ruler_combust(None,context=CONTEXT,first_ruler="Sun").state is State.NOT_APPLICABLE
    assert all(r.state is State.NOT_EVALUABLE for r in lilly_saturn_considerations(None,context=CONTEXT))
    binding=LillyQuestionBinding(CONTEXT,"missing-hour",None,None)
    result=lilly_hour_agreement("Aries",binding=binding,hour=None)
    assert result.state is result.identity is result.nature is result.triplicity is State.NOT_EVALUABLE


def test_seventh_lord_clause_preserves_independent_fall_term_and_unknown_misfortune():
    fallen=lilly_seventh_lord_warning(snapshot("Saturn","Aries",10),context=CONTEXT)
    assert fallen.state is State.PRESENT and dict(fallen.observed)["fall"] == "present"
    malefic_term=lilly_seventh_lord_warning(snapshot("Sun","Aries",28),context=CONTEXT)
    assert malefic_term.state is State.PRESENT and dict(malefic_term.observed)["malefic_term"] == "present"
    missing=lilly_seventh_lord_warning(snapshot("Sun","Aries"),context=CONTEXT)
    assert missing.state is State.NOT_EVALUABLE
    clear=lilly_seventh_lord_warning(snapshot("Sun","Aries",1),context=CONTEXT,
        unfortunate=assessment(False,("seventh_lord",),kind=Kind.SEVENTH_LORD_UNFORTUNATE))
    assert clear.state is State.ABSENT


def test_first_ruler_solar_evidence_requires_correct_body_and_epoch():
    solar=lilly_solar_proximity("Mars",10.,15.,context=CONTEXT)
    assert lilly_first_ruler_combust(solar,context=CONTEXT,first_ruler="Mars").state is State.PRESENT
    with pytest.raises(ValueError,match="context/body"):
        lilly_first_ruler_combust(solar,context=CONTEXT,first_ruler="Venus")
    with pytest.raises(ValueError):
        lilly_first_ruler_combust(solar,context=LillySnapshotContext("other",None,1000),first_ruler="Mars")
    cazimi=lilly_solar_proximity("Mars",10.,10.05,context=CONTEXT)
    assert lilly_first_ruler_combust(cazimi,context=CONTEXT,first_ruler="Mars").state is State.ABSENT


def test_hour_binding_and_adapter_require_epoch_location_and_question_identity():
    from moira.horary import HoraryPlanetaryHourReceipt
    context=LillySnapshotContext("hour-question",True,1000.)
    binding=LillyQuestionBinding(context,"hour-question",51.5,-.1)
    receipt=HoraryPlanetaryHourReceipt(question_id="hour-question",jd_ut1=1000.,latitude_deg=51.5,longitude_deg=-.1,
        source_id="validated-solar-hour",hour_ruler="Mars",hour_number=7,hour_start_jd=1000.,hour_end_jd=1000.+.5/12,
        sunrise_jd=999.75,sunset_jd=1000.25,local_time_algorithm_id="synthetic_validated_solar_interval")
    assertion=adapt_horary_planetary_hour(receipt,binding=binding)
    assert assertion.origin == "supplied_bound_horary_receipt"
    assert lilly_hour_agreement("Aries",binding=binding,hour=assertion).state is State.PRESENT
    for bad in (replace(binding,question_id="other"),replace(binding,latitude_deg=52),replace(binding,context=LillySnapshotContext("other",True,1000.))):
        with pytest.raises(ValueError,match="binding"):
            lilly_hour_agreement("Aries",binding=bad,hour=assertion)
    with pytest.raises(ValueError,match="match"):
        adapt_horary_planetary_hour(receipt,binding=replace(binding,longitude_deg=1))
    with pytest.raises(ValueError,match="sect"):
        adapt_horary_planetary_hour(receipt,binding=replace(binding,context=LillySnapshotContext("hour-question",False,1000.)))
    unknown=replace(binding,context=LillySnapshotContext("hour-question",None,1000.))
    known_hour=adapt_horary_planetary_hour(receipt,binding=unknown)
    assert known_hour.hour_is_day_chart is True
    assert lilly_hour_agreement("Cancer",binding=unknown,hour=known_hour).triplicity is State.PRESENT


@pytest.mark.parametrize("cut,lower,edge,upper",[(17/60,"cazimi","cazimi_boundary","combust"),
    (8.5,"combust","combust_boundary","under_beams"),(17.,"under_beams","beams_boundary","clear")])
def test_solar_representation_envelope_is_separate_from_doctrinal_thresholds(cut,lower,edge,upper):
    for delta,expected in ((-1e-7,lower),(0,edge),(1e-7,upper)):
        result=lilly_solar_proximity("Jupiter",300.,300.+cut+delta,context=CONTEXT)
        assert result.band.value == expected
        assert result.roundoff_arcminutes is not None and result.roundoff_arcminutes < 1e-8
    adjacent=math.nextafter(300.+cut,math.inf)
    assert lilly_solar_proximity("Jupiter",300.,adjacent,context=CONTEXT).band.value == edge


def test_cross_sign_cazimi_boundary_does_not_erase_known_absence_of_combustion():
    result=lilly_solar_proximity("Jupiter",29.9,29.9+17/60,context=CONTEXT)
    assert result.band.value == "cazimi_boundary" and result.same_sign is False
    assert result.combustion is State.ABSENT


@pytest.mark.parametrize("value",[True,float("nan"),float("inf"),-float("inf")])
def test_nonfinite_or_boolean_geometry_is_rejected(value):
    for call in (lambda:lilly_early_ascendant(value,context=CONTEXT),lambda:lilly_solar_proximity("Mars",0,value,context=CONTEXT),
                 lambda:lilly_lunar_orientation(value,0,context=CONTEXT)):
        with pytest.raises((TypeError,ValueError)):
            call()


def test_immutable_outputs_serialize_unknown_inputs_without_scores_or_verdicts():
    result=lilly_early_ascendant(2,context=CONTEXT)
    with pytest.raises(FrozenInstanceError):
        result.state=State.ABSENT
    encoded=json.loads(json.dumps(asdict(result)))
    assert encoded["state"] == "not_evaluable" and encoded["qualification"] == "not_evaluable"
    assert encoded["evidence"] == []
    assert not {"confidence_score","predicted_outcome","chart_valid"} & encoded.keys()
    with pytest.raises(ValueError):
        LillyQualitativeEvidence(CONTEXT,Kind.VERY_YOUNG,State.PRESENT,("querent",),"source","reason",())
    with pytest.raises(ValueError):
        lilly_early_ascendant(30,context=CONTEXT)


def test_assessment_cannot_be_reused_for_a_different_proposition_at_same_epoch():
    age=assessment(True,("querent",),kind=Kind.AGE_CORRESPONDS)
    with pytest.raises(ValueError,match="proposition"):
        lilly_early_ascendant(2,context=CONTEXT,very_young=age)
