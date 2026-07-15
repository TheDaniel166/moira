from __future__ import annotations

import pytest

import moira
from moira import facade
from moira.classical_perfection import (
    ClassicalBodyState,
    ClassicalPerfectionEvent,
    ClassicalPerfectionEventKind,
    ClassicalPerfectionState,
    LILLY_1647_PERFECTION_V1,
    LillyPerfectionKind,
    classify_lilly_perfection_events,
)
from moira.constants import Body


def _state(body: str, longitude: float, speed: float) -> ClassicalBodyState:
    signs = ("Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo",
             "Libra", "Scorpio", "Sagittarius", "Capricorn", "Aquarius", "Pisces")
    return ClassicalBodyState(body, longitude % 360.0, speed, signs[int(longitude % 360.0 // 30)])


def _states(**overrides) -> tuple[ClassicalBodyState, ...]:
    base = {
        Body.SUN: (120.0, 1.0), Body.MOON: (200.0, 13.0), Body.MERCURY: (0.0, 2.0),
        Body.VENUS: (80.0, 1.2), Body.MARS: (160.0, 0.5), Body.JUPITER: (5.0, 0.1),
        Body.SATURN: (280.0, 0.05),
    }
    base.update(overrides)
    return tuple(_state(body, *base[body]) for body in base)


def _aspect(event_id: str, jd: float, a: str, b: str, aspect="conjunction", angle=0.0):
    return ClassicalPerfectionEvent(event_id, jd, ClassicalPerfectionEventKind.ASPECT_EXACT,
                                    a, b, aspect, angle)


def _analysis(events=(), states=None, a=Body.MERCURY, b=Body.JUPITER, day=True):
    return classify_lilly_perfection_events(
        0.0, 10.0, a, b, is_day_chart=day,
        initial_states=states or _states(), events=tuple(events),
    )


def _witness(result, kind):
    return next(item for item in result.witnesses if item.kind is kind)


def test_lilly_policy_is_named_and_not_generic_traditional_mode() -> None:
    assert LILLY_1647_PERFECTION_V1.profile_id == "lilly_1647_perfection_v1"
    assert LILLY_1647_PERFECTION_V1.contact_scope == "summed_planetary_moieties"
    assert LILLY_1647_PERFECTION_V1.bounds_doctrine == "egyptian"
    assert LILLY_1647_PERFECTION_V1.triplicity_doctrine == "dorothean_sect_active"
    assert LILLY_1647_PERFECTION_V1.longitude_product == "apparent_geocentric_true_ecliptic_of_date"
    assert LILLY_1647_PERFECTION_V1.motion_product == "astrometric_geocentric_longitude_rate"


def test_moira_facade_binds_reader_and_fixed_policy(monkeypatch: pytest.MonkeyPatch) -> None:
    sentinel_reader = object()
    sentinel_result = object()
    captured = {}

    def fake_lilly(*args, **kwargs):
        captured["args"] = args
        captured["kwargs"] = kwargs
        return sentinel_result

    monkeypatch.setattr(facade, "lilly_perfection_at", fake_lilly)
    engine = moira.Moira()
    engine._reader_obj = sentinel_reader
    result = engine.lilly_perfection_at(
        0.0, 2.0, Body.MERCURY, Body.JUPITER, is_day_chart=True,
    )
    assert result is sentinel_result
    assert captured["args"] == (0.0, 2.0, Body.MERCURY, Body.JUPITER)
    assert captured["kwargs"] == {
        "is_day_chart": True,
        "reader": sentinel_reader,
        "policy": LILLY_1647_PERFECTION_V1,
    }


def test_direct_perfection_requires_in_moiety_application_and_exact_trace() -> None:
    result = _analysis((_aspect("pair", 2.0, Body.MERCURY, Body.JUPITER),))
    direct = _witness(result, LillyPerfectionKind.DIRECT)
    assert direct.state is ClassicalPerfectionState.PRESENT
    assert direct.event_ids == ("pair",)


def test_direct_perfection_uses_canonical_lilly_jupiter_saturn_moieties() -> None:
    states = _states(**{Body.JUPITER: (0.0, 0.1), Body.SATURN: (10.0, 0.05)})
    result = _analysis((_aspect("pair", 2.0, Body.JUPITER, Body.SATURN),),
                       states, Body.JUPITER, Body.SATURN)
    assert _witness(result, LillyPerfectionKind.DIRECT).state is ClassicalPerfectionState.PRESENT


def test_refranation_defeats_direct_perfection() -> None:
    station = ClassicalPerfectionEvent(
        "station", 1.0, ClassicalPerfectionEventKind.STATION_RETROGRADE, Body.MERCURY,
    )
    result = _analysis((station, _aspect("pair", 2.0, Body.MERCURY, Body.JUPITER)))
    assert _witness(result, LillyPerfectionKind.REFRANATION).state is ClassicalPerfectionState.PRESENT
    assert _witness(result, LillyPerfectionKind.DIRECT).state is ClassicalPerfectionState.ABSENT


def test_frustration_requires_the_heavier_significator_to_join_another_first() -> None:
    states = _states(**{Body.SUN: (4.0, 1.0)})
    result = _analysis((
        _aspect("frustrate", 1.0, Body.SUN, Body.JUPITER),
        _aspect("pair", 2.0, Body.MERCURY, Body.JUPITER),
    ), states)
    assert _witness(result, LillyPerfectionKind.FRUSTRATION).state is ClassicalPerfectionState.PRESENT
    assert _witness(result, LillyPerfectionKind.DIRECT).state is ClassicalPerfectionState.ABSENT


def test_prohibition_requires_one_swifter_planet_to_interpose_with_both_significators() -> None:
    states = _states(**{Body.MOON: (359.0, 13.0)})
    events = (
        _aspect("moon_mercury", 0.2, Body.MOON, Body.MERCURY),
        _aspect("moon_jupiter", 0.5, Body.MOON, Body.JUPITER),
        _aspect("pair", 2.0, Body.MERCURY, Body.JUPITER),
    )
    result = _analysis(events, states)
    prohibition = _witness(result, LillyPerfectionKind.PROHIBITION)
    assert prohibition.state is ClassicalPerfectionState.PRESENT
    assert prohibition.actors == (Body.MERCURY, Body.JUPITER, Body.MOON)
    assert prohibition.event_ids == ("moon_mercury", "moon_jupiter")
    assert _witness(result, LillyPerfectionKind.FRUSTRATION).state is ClassicalPerfectionState.ABSENT
    assert _witness(result, LillyPerfectionKind.DIRECT).state is ClassicalPerfectionState.ABSENT


def test_one_third_party_contact_alone_is_not_prohibition() -> None:
    states = _states(**{Body.MOON: (359.0, 13.0)})
    result = _analysis((
        _aspect("moon_mercury", 0.2, Body.MOON, Body.MERCURY),
        _aspect("pair", 2.0, Body.MERCURY, Body.JUPITER),
    ), states)
    assert _witness(result, LillyPerfectionKind.PROHIBITION).state is ClassicalPerfectionState.ABSENT


def test_prior_sign_ingress_preserves_indeterminacy_instead_of_inventing_break_law() -> None:
    ingress = ClassicalPerfectionEvent(
        "ingress", 1.0, ClassicalPerfectionEventKind.SIGN_INGRESS, Body.MERCURY,
        longitude_deg=30.0, sign_before="Aries", sign_after="Taurus",
    )
    result = _analysis((ingress, _aspect("pair", 2.0, Body.MERCURY, Body.JUPITER)))
    assert _witness(result, LillyPerfectionKind.DIRECT).state is ClassicalPerfectionState.INDETERMINATE


def test_received_translation_uses_house_triplicity_or_term_only() -> None:
    states = _states(**{
        Body.MARS: (10.0, 0.5), Body.SATURN: (15.0, 0.1), Body.MERCURY: (11.0, 2.0),
        Body.JUPITER: (100.0, 0.2),
    })
    result = _analysis((_aspect("translated", 2.0, Body.MERCURY, Body.SATURN),),
                       states, Body.MARS, Body.SATURN)
    translation = _witness(result, LillyPerfectionKind.TRANSLATION)
    assert translation.state is ClassicalPerfectionState.PRESENT
    assert translation.actors == (Body.MERCURY, Body.MARS, Body.SATURN)
    assert "house" in translation.reception_bases


def test_translation_fails_if_translator_meets_another_planet_first() -> None:
    states = _states(**{
        Body.MARS: (10.0, 0.5), Body.SATURN: (15.0, 0.1), Body.MERCURY: (11.0, 2.0),
        Body.JUPITER: (100.0, 0.2),
    })
    result = _analysis((
        _aspect("intervening", 1.0, Body.MERCURY, Body.VENUS, "square", 90.0),
        _aspect("translated", 2.0, Body.MERCURY, Body.SATURN),
    ), states, Body.MARS, Body.SATURN)
    assert _witness(result, LillyPerfectionKind.TRANSLATION).state is ClassicalPerfectionState.ABSENT


def test_collection_requires_two_averse_applications_and_double_reception() -> None:
    states = _states(**{
        Body.SUN: (350.0, 1.0), Body.JUPITER: (10.0, -0.2), Body.SATURN: (1.0, 0.05),
        Body.MERCURY: (100.0, 1.5),
    })
    events = (
        _aspect("sun_collects", 2.0, Body.SUN, Body.SATURN),
        _aspect("jupiter_collects", 3.0, Body.JUPITER, Body.SATURN),
    )
    result = _analysis(events, states, Body.SUN, Body.JUPITER)
    collection = _witness(result, LillyPerfectionKind.COLLECTION)
    assert collection.state is ClassicalPerfectionState.PRESENT
    assert collection.actors == (Body.SUN, Body.JUPITER, Body.SATURN)
    assert any(item.startswith("Sun:") for item in collection.reception_bases)
    assert any(item.startswith("Jupiter:") for item in collection.reception_bases)


def test_collection_requires_significators_not_to_behold_by_sign() -> None:
    states = _states(**{
        Body.SUN: (1.0, 1.0), Body.JUPITER: (10.0, -0.2), Body.SATURN: (5.0, 0.05),
        Body.MERCURY: (100.0, 1.5),
    })
    events = (
        _aspect("sun_collects", 2.0, Body.SUN, Body.SATURN),
        _aspect("jupiter_collects", 3.0, Body.JUPITER, Body.SATURN),
    )
    result = _analysis(events, states, Body.SUN, Body.JUPITER)
    assert _witness(result, LillyPerfectionKind.COLLECTION).state is ClassicalPerfectionState.ABSENT


def test_direct_perfection_uses_the_initially_applying_aspect_branch() -> None:
    result = _analysis((
        _aspect("wrong_branch", 1.0, Body.MERCURY, Body.JUPITER, "sextile", 60.0),
        _aspect("conjunction", 2.0, Body.MERCURY, Body.JUPITER),
    ))
    assert _witness(result, LillyPerfectionKind.DIRECT).event_ids == ("conjunction",)


def test_trace_is_deterministically_ordered_and_summary_is_derived() -> None:
    result = _analysis((
        _aspect("later", 2.0, Body.MERCURY, Body.JUPITER),
        _aspect("earlier", 1.0, Body.SUN, Body.MERCURY, "trine", 120.0),
    ))
    assert [item.event_id for item in result.events] == ["earlier", "later"]
    assert result.present_kinds == tuple(
        item.kind for item in result.witnesses if item.state is ClassicalPerfectionState.PRESENT
    )
    assert result.complete_electional_judgement is False
    assert result.policy is LILLY_1647_PERFECTION_V1
    assert result.scoring == "not_provided"
