from __future__ import annotations

from dataclasses import replace
from types import SimpleNamespace

import pytest

import moira
import moira.classical_perfection as perfection
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

_DIRECTED_ASPECTS = ((0., "conjunction"), (60., "sextile"), (90., "square"),
                     (120., "trine"), (180., "opposition"), (240., "trine"),
                     (270., "square"), (300., "sextile"))


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
    assert LILLY_1647_PERFECTION_V1.bounds_doctrine == "william_lilly_1647"
    assert LILLY_1647_PERFECTION_V1.triplicity_doctrine == "william_lilly_1647_sect_active"
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


@pytest.mark.parametrize("angle, aspect", _DIRECTED_ASPECTS)
@pytest.mark.parametrize("reverse_event", (False, True))
def test_direct_perfection_is_invariant_under_pair_and_event_orientation(angle, aspect, reverse_event):
    states = _states(**{Body.MERCURY: ((angle - 1) % 360, 2), Body.JUPITER: (0, .1)})
    event = _aspect("contact", 1, Body.MERCURY, Body.JUPITER, aspect, angle)
    if reverse_event:
        event = replace(event, actor=event.target, target=event.actor, directional_angle_deg=(-angle) % 360)
    for a, b in ((Body.MERCURY, Body.JUPITER), (Body.JUPITER, Body.MERCURY)):
        result = _analysis((event,), states, a, b)
        direct = _witness(result, LillyPerfectionKind.DIRECT)
        assert direct.state is ClassicalPerfectionState.PRESENT
        assert direct.actors == (a, b)
        assert direct.event_ids == ("contact",)
        assert result.events == (event,)
        assert result.events[0] is event  # lookup must not rewrite the neutral trace


def _synthetic_trace(monkeypatch, mercury, venus, start=0, end=.25):
    """Analytic longitude corpus; rates deliberately do not locate extrema."""
    fixed = {Body.SUN: 37, Body.MOON: 81, Body.MARS: 142, Body.JUPITER: 213, Body.SATURN: 282.345}

    def position(body, jd, *, reader):
        assert start <= jd <= end
        longitude = mercury(jd) if body == Body.MERCURY else venus(jd) if body == Body.VENUS else fixed[body]
        return SimpleNamespace(longitude=longitude % 360, speed=1.)

    monkeypatch.setattr(perfection, "planet_at", position)
    monkeypatch.setattr(perfection, "find_stations", lambda *args, **kwargs: ())
    return perfection._trace(start, end, object())


def _pair_contacts(events, angle=0):
    return tuple(e for e in events if e.kind is ClassicalPerfectionEventKind.ASPECT_EXACT
                 and (e.actor, e.target) == (Body.MERCURY, Body.VENUS)
                 and e.directional_angle_deg == angle)


@pytest.mark.parametrize("contact", (0., .25, 1.))
def test_trace_includes_both_endpoints_and_emits_shared_sample_once(monkeypatch, contact):
    events = _synthetic_trace(monkeypatch, lambda t: 10 + t, lambda t: 10 + contact, end=1.)
    hits = _pair_contacts(events)
    assert len(hits) == 1
    assert hits[0].jd_ut == pytest.approx(contact, abs=1 / 86400)
    if contact in (0., 1.):
        assert hits[0].jd_ut == contact


@pytest.mark.parametrize("turn", (.125, .073, .03, .22))
@pytest.mark.parametrize("curvature", (.1, -.1))
def test_trace_finds_two_contacts_inside_one_cell_with_no_individual_station(monkeypatch, turn, curvature):
    events = _synthetic_trace(monkeypatch,
        lambda t: 10 + t + curvature * ((t - turn) ** 2 - .0004), lambda t: 10 + t)
    hits = _pair_contacts(events)
    assert [e.jd_ut for e in hits] == pytest.approx([turn - .02, turn + .02], abs=1 / 86400)
    assert all(abs(curvature * ((e.jd_ut - turn) ** 2 - .0004)) <= 1e-7 for e in hits)
    assert not any(e.kind in (ClassicalPerfectionEventKind.STATION_DIRECT,
                             ClassicalPerfectionEventKind.STATION_RETROGRADE) for e in events)


@pytest.mark.parametrize("minimum, count", ((0., 1), (.000002, 0)))
@pytest.mark.parametrize("direction", (1, -1))
def test_trace_distinguishes_stationary_contact_from_near_miss(monkeypatch, minimum, count, direction):
    events = _synthetic_trace(monkeypatch,
        lambda t: 10 + t + direction * (.1 * (t - .073) ** 2 + minimum), lambda t: 10 + t)
    hits = _pair_contacts(events)
    assert len(hits) == count
    if hits:
        assert hits[0].jd_ut == pytest.approx(.073, abs=1 / 86400)


@pytest.mark.parametrize("angle, aspect", _DIRECTED_ASPECTS)
@pytest.mark.parametrize("direction", (1, -1))
def test_trace_finds_every_directed_branch_without_wrap_false_positive(monkeypatch, angle, aspect, direction):
    events = _synthetic_trace(monkeypatch, lambda t: 7.123 + angle + direction * (t - .1), lambda t: 7.123)
    hits = _pair_contacts(events, angle)
    assert len(hits) == 1
    assert hits[0].jd_ut == pytest.approx(.1, abs=1 / 86400)
    assert hits[0].aspect == aspect
    assert len(_pair_contacts(events, (angle + 180) % 360)) == 0


def test_trace_rejects_unresolved_continuous_contact_instead_of_partial_success(monkeypatch):
    with pytest.raises(RuntimeError, match="perfection.*incomplete.*near_continuous_contact"):
        _synthetic_trace(monkeypatch, lambda t: 10 + t, lambda t: 10 + t)


def test_trace_finds_exit_and_return_ingresses_inside_one_cell(monkeypatch):
    events = _synthetic_trace(monkeypatch,
        lambda t: 30 + .1 * (t - .073) ** 2 - .00004, lambda t: 11.)
    ingresses = [e for e in events if e.kind is ClassicalPerfectionEventKind.SIGN_INGRESS
                 and e.actor == Body.MERCURY]
    assert [e.jd_ut for e in ingresses] == pytest.approx([.053, .093], abs=1 / 86400)
    assert [(e.sign_before, e.sign_after) for e in ingresses] == [("Taurus", "Aries"), ("Aries", "Taurus")]


def test_trace_does_not_treat_a_tangent_sign_boundary_as_an_ingress(monkeypatch):
    events = _synthetic_trace(monkeypatch, lambda t: 30 + .1 * (t - .073) ** 2, lambda t: 11.)
    assert not any(e.kind is ClassicalPerfectionEventKind.SIGN_INGRESS
                   and e.actor == Body.MERCURY for e in events)


@pytest.mark.parametrize("contact", (0., .125, .25))
@pytest.mark.parametrize("direction", (1, -1))
def test_trace_records_forward_and_reverse_ingress_boundaries_once(monkeypatch, contact, direction):
    events = _synthetic_trace(monkeypatch, lambda t: 30 + direction * (t - contact), lambda t: 11.)
    ingresses = [e for e in events if e.kind is ClassicalPerfectionEventKind.SIGN_INGRESS
                 and e.actor == Body.MERCURY]
    assert len(ingresses) == 1
    assert ingresses[0].jd_ut == pytest.approx(contact, abs=1 / 86400)
    expected = ("Aries", "Taurus") if direction == 1 else ("Taurus", "Aries")
    assert (ingresses[0].sign_before, ingresses[0].sign_after) == expected


@pytest.mark.parametrize("kind", (LillyPerfectionKind.TRANSLATION, LillyPerfectionKind.COLLECTION,
                                 LillyPerfectionKind.PROHIBITION))
def test_compound_witnesses_keep_nonsymmetric_contacts_when_trace_orientation_reverses(kind):
    if kind is LillyPerfectionKind.TRANSLATION:
        states = _states(**{Body.MARS: (10, .5), Body.SATURN: (75, .1),
                            Body.MERCURY: (11, 2), Body.JUPITER: (100, .2)})
        a, b = Body.MARS, Body.SATURN
        events = (_aspect("translated", 2, Body.MERCURY, Body.SATURN, "sextile", 300),)
    elif kind is LillyPerfectionKind.COLLECTION:
        states = _states(**{Body.SUN: (55, 1), Body.JUPITER: (10, -.2),
                            Body.SATURN: (1, .05), Body.MERCURY: (100, 1.5)})
        a, b = Body.SUN, Body.JUPITER
        events = (_aspect("sun_collects", 2, Body.SUN, Body.SATURN, "sextile", 60),
                  _aspect("jupiter_collects", 3, Body.JUPITER, Body.SATURN))
    else:
        states = _states(**{Body.MOON: (49, 13), Body.MERCURY: (54, 2), Body.JUPITER: (115, .1)})
        a, b = Body.MERCURY, Body.JUPITER
        events = (_aspect("moon_mercury", .2, Body.MOON, Body.MERCURY),
                  _aspect("moon_jupiter", .5, Body.MOON, Body.JUPITER, "sextile", 300),
                  _aspect("pair", 2, a, b, "sextile", 300))
    original = _witness(_analysis(events, states, a, b), kind)
    assert original.state is ClassicalPerfectionState.PRESENT
    reversed_events = tuple(replace(e, actor=e.target, target=e.actor,
                                   directional_angle_deg=(-e.directional_angle_deg) % 360) for e in events)
    assert _witness(_analysis(reversed_events, states, a, b), kind) == original


def test_trace_refuses_exhausted_scan_budget(monkeypatch):
    monkeypatch.setattr(perfection, "_ROOT_POLICY", replace(perfection._ROOT_POLICY, max_evaluations=1))
    with pytest.raises(RuntimeError, match="perfection.*incomplete.*search_budget_exhausted"):
        _synthetic_trace(monkeypatch, lambda t: 10 + t, lambda t: 11.)
