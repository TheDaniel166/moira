"""Public-contract tests for the bounded Horary engine adapter."""

from __future__ import annotations

import inspect
from datetime import datetime, timezone
from types import SimpleNamespace

import pytest

import moira
import moira.facade as facade_module
import moira.horary as horary_module
from moira._facade_classical import ClassicalFacadeMixin
from moira.classical_perfection import (
    ClassicalBodyState,
    LILLY_1647_PERFECTION_V1,
    classify_lilly_perfection_events,
)
from moira.constants import Body, HouseSystem, sign_of
from moira.horary import (
    HoraryChartSect,
    HoraryEvidenceState,
    HoraryHousePolicy,
    HoraryPerfectionState,
    HoraryQuestionReceipt,
    HoraryQuestionTimeBasis,
    HoraryQuestionTimeReceipt,
    HorarySourceCalendar,
)
from moira.houses import HouseCusps, HousePolicy, classify_house_system


_JD_UT1 = 2451545.0
_LATITUDE = 51.5074
_LONGITUDE = -0.1278
_TRADITIONAL_SEVEN = (
    Body.SUN,
    Body.MOON,
    Body.MERCURY,
    Body.VENUS,
    Body.MARS,
    Body.JUPITER,
    Body.SATURN,
)
_LONGITUDES = {
    Body.SUN: 120.0,
    Body.MOON: 200.0,
    Body.MERCURY: 150.0,
    Body.VENUS: 40.0,
    Body.MARS: 160.0,
    Body.JUPITER: 5.0,
    Body.SATURN: 280.0,
}


def _question() -> HoraryQuestionReceipt:
    return HoraryQuestionReceipt(
        question_id="public-horary-question",
        latitude_deg=_LATITUDE,
        longitude_deg=_LONGITUDE,
        time=HoraryQuestionTimeReceipt(
            state=HoraryEvidenceState.EVALUATED,
            stated_basis=(
                HoraryQuestionTimeBasis.QUESTION_PROPOSED_AND_FIGURE_ERECTED
            ),
            stated_basis_source="Lilly 1647 CA p. 121 public adapter test",
            source_calendar=HorarySourceCalendar.GREGORIAN,
            source_instant_label="2000-01-01 12:00 UTC test event",
            normalized_instant=datetime(
                2000,
                1,
                1,
                12,
                0,
                tzinfo=timezone.utc,
            ),
            normalized_jd_ut1=_JD_UT1,
            conversion_policy_id="test_utc_to_ut1_receipt_v1",
            reason=None,
        ),
        perspective_path=(),
        terminal_topic_house=9,
    )


def _houses() -> HouseCusps:
    cusps = tuple((150.0 + 30.0 * index) % 360.0 for index in range(12))
    return HouseCusps(
        system=HouseSystem.REGIOMONTANUS,
        cusps=cusps,
        asc=cusps[0],
        mc=cusps[9],
        armc=0.0,
        effective_system=HouseSystem.REGIOMONTANUS,
        fallback=False,
        fallback_reason=None,
        classification=classify_house_system(HouseSystem.REGIOMONTANUS),
        policy=HousePolicy.strict(),
    )


def _install_computational_fakes(monkeypatch: pytest.MonkeyPatch):
    reader = object()
    calls: dict[str, object] = {"positions": []}
    houses = _houses()
    hour_length = 0.5 / 12.0
    selected_hour = SimpleNamespace(
        ruler=Body.MERCURY,
        hour_number=7,
        jd_start=_JD_UT1,
        jd_end=_JD_UT1 + hour_length,
        is_daytime=True,
    )
    hours_day = SimpleNamespace(
        latitude=_LATITUDE,
        longitude=_LONGITUDE,
        sunrise_jd=_JD_UT1 - 0.25,
        sunset_jd=_JD_UT1 + 0.25,
        hours=(selected_hour,),
        hour_at=lambda jd: selected_hour if jd == _JD_UT1 else None,
    )

    def fake_houses(jd, latitude, longitude, system, *, policy, sun_longitude):
        calls["houses"] = (
            jd,
            latitude,
            longitude,
            system,
            policy,
            sun_longitude,
        )
        return houses

    def fake_hours(jd, latitude, longitude, *, reader):
        calls["hours"] = (jd, latitude, longitude, reader)
        return hours_day

    def fake_planet_at(
        body,
        jd,
        *,
        reader,
        apparent,
        aberration,
        grav_deflection,
        nutation,
        center,
        frame,
    ):
        assert (apparent, aberration, grav_deflection, nutation) == (
            True,
            True,
            True,
            True,
        )
        assert (center, frame) == ("geocentric", "ecliptic")
        calls["positions"].append((body, jd, reader))
        return SimpleNamespace(name=body, longitude=_LONGITUDES[body])

    monkeypatch.setattr(horary_module, "calculate_houses", fake_houses)
    monkeypatch.setattr(horary_module, "planetary_hours", fake_hours)
    monkeypatch.setattr(horary_module, "planet_at", fake_planet_at)
    return reader, calls


def test_public_adapter_owns_strict_composition_and_one_reader(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    reader, calls = _install_computational_fakes(monkeypatch)
    monkeypatch.setattr(
        horary_module,
        "lilly_perfection_at",
        lambda *args, **kwargs: pytest.fail(
            "perfection search must not run without an explicit end"
        ),
    )

    profile = horary_module.horary_evidence_at(
        _question(),
        house_policy=HoraryHousePolicy(HouseSystem.REGIOMONTANUS),
        reader=reader,
    )

    house_call = calls["houses"]
    assert house_call[:4] == (
        _JD_UT1,
        _LATITUDE,
        _LONGITUDE,
        HouseSystem.REGIOMONTANUS,
    )
    assert house_call[4] == HousePolicy.strict()
    assert house_call[5] == _LONGITUDES[Body.SUN]
    assert calls["hours"] == (_JD_UT1, _LATITUDE, _LONGITUDE, reader)
    assert tuple(body for body, _, _ in calls["positions"]) == _TRADITIONAL_SEVEN
    assert all(bound_reader is reader for _, _, bound_reader in calls["positions"])
    assert profile.house_geometry.source_mode.value == "computed"
    assert profile.house_geometry.house_cusps == _houses()
    assert profile.chart_sect.sect is HoraryChartSect.DAY
    assert profile.consideration_inputs.moon_placement is not None
    assert profile.consideration_inputs.saturn_placement is not None
    assert profile.consideration_inputs.first_ruler_solar_proximity is not None
    assert profile.perfection.state is HoraryPerfectionState.NOT_EVALUABLE
    assert profile.perfection.reason == "classical_perfection_analysis_not_supplied"
    assert profile.provenance.outcome_language == "not_provided"
    assert profile.provenance.advice_language == "not_provided"


def test_public_adapter_runs_only_the_bounded_canonical_lilly_search(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    reader, calls = _install_computational_fakes(monkeypatch)
    captured: dict[str, object] = {}

    def fake_perfection(
        jd_start,
        jd_end,
        significator_a,
        significator_b,
        *,
        is_day_chart,
        reader,
        policy,
    ):
        captured.update(
            jd_start=jd_start,
            jd_end=jd_end,
            significator_a=significator_a,
            significator_b=significator_b,
            is_day_chart=is_day_chart,
            reader=reader,
            policy=policy,
        )
        states = tuple(
            ClassicalBodyState(
                body=body,
                longitude=_LONGITUDES[body],
                speed=1.0,
                sign=sign_of(_LONGITUDES[body])[0],
            )
            for body in _TRADITIONAL_SEVEN
        )
        return classify_lilly_perfection_events(
            jd_start,
            jd_end,
            significator_a,
            significator_b,
            is_day_chart=is_day_chart,
            initial_states=states,
            events=(),
            reader_provenance="test explicit reader",
            policy=LILLY_1647_PERFECTION_V1,
        )

    monkeypatch.setattr(horary_module, "lilly_perfection_at", fake_perfection)
    profile = horary_module.horary_evidence_at(
        _question(),
        house_policy=HoraryHousePolicy(HouseSystem.REGIOMONTANUS),
        perfection_jd_end=_JD_UT1 + 5.0,
        reader=reader,
    )

    assert captured == {
        "jd_start": _JD_UT1,
        "jd_end": _JD_UT1 + 5.0,
        "significator_a": Body.MERCURY,
        "significator_b": Body.VENUS,
        "is_day_chart": True,
        "reader": reader,
        "policy": LILLY_1647_PERFECTION_V1,
    }
    assert tuple(body for body, _, _ in calls["positions"]) == _TRADITIONAL_SEVEN
    assert profile.perfection.state is HoraryPerfectionState.COMPOSED
    assert profile.perfection.analysis is profile.perfection_analysis_input


@pytest.mark.parametrize(
    "end",
    (True, float("nan"), _JD_UT1, _JD_UT1 - 1.0, _JD_UT1 + 31.000001),
)
def test_public_adapter_rejects_invalid_perfection_bounds_before_computation(
    monkeypatch: pytest.MonkeyPatch,
    end: float,
) -> None:
    monkeypatch.setattr(
        horary_module,
        "calculate_houses",
        lambda *args, **kwargs: pytest.fail("invalid interval must fail first"),
    )

    with pytest.raises(ValueError, match="perfection"):
        horary_module.horary_evidence_at(
            _question(),
            house_policy=HoraryHousePolicy(HouseSystem.REGIOMONTANUS),
            perfection_jd_end=end,
            reader=object(),
        )


def test_curated_root_and_facade_exports_share_exact_identity() -> None:
    curated = (
        "HoraryQuestionTimeBasis",
        "HorarySourceCalendar",
        "HoraryEvidenceProfile",
        "LILLY_1647_HORARY_V1",
        "horary_evidence_at",
    )
    for name in curated:
        assert name in moira.__all__
        assert name in facade_module.__all__
        assert getattr(moira, name) is getattr(facade_module, name)
        assert getattr(moira, name) is getattr(horary_module, name)

    namespace: dict[str, object] = {}
    exec("from moira import *", {}, namespace)
    assert all(namespace[name] is getattr(horary_module, name) for name in curated)


def test_concrete_horary_receipts_remain_module_only() -> None:
    for name in (
        "HoraryQuestionReceipt",
        "HoraryHousePolicy",
        "HoraryHouseGeometryReceipt",
        "HoraryPlanetaryHourReceipt",
        "HoraryConsiderationInputs",
        "HoraryPerfectionEvidence",
    ):
        assert name in horary_module.__all__
        assert name not in moira.__all__
        assert name not in facade_module.__all__


def test_public_adapter_signature_has_no_hidden_reader_or_house_default() -> None:
    parameters = inspect.signature(horary_module.horary_evidence_at).parameters
    assert tuple(parameters) == (
        "question",
        "house_policy",
        "perfection_jd_end",
        "reader",
    )
    assert parameters["house_policy"].kind is inspect.Parameter.KEYWORD_ONLY
    assert parameters["house_policy"].default is inspect.Parameter.empty
    assert parameters["perfection_jd_end"].default is None
    assert parameters["reader"].kind is inspect.Parameter.KEYWORD_ONLY
    assert parameters["reader"].default is inspect.Parameter.empty


def test_moira_method_delegates_to_facade_function_with_instance_reader(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    reader = object()
    expected = object()
    captured: dict[str, object] = {}

    def fake_adapter(question, *, house_policy, perfection_jd_end, reader):
        captured.update(
            question=question,
            house_policy=house_policy,
            perfection_jd_end=perfection_jd_end,
            reader=reader,
        )
        return expected

    monkeypatch.setattr(facade_module, "horary_evidence_at", fake_adapter)
    question = _question()
    policy = HoraryHousePolicy(HouseSystem.REGIOMONTANUS)
    engine = SimpleNamespace(_reader=reader)

    result = ClassicalFacadeMixin.horary_evidence_at(
        engine,
        question,
        house_policy=policy,
        perfection_jd_end=_JD_UT1 + 3.0,
    )

    assert result is expected
    assert captured == {
        "question": question,
        "house_policy": policy,
        "perfection_jd_end": _JD_UT1 + 3.0,
        "reader": reader,
    }
    assert facade_module.Moira.horary_evidence_at is (
        ClassicalFacadeMixin.horary_evidence_at
    )
