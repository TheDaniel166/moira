from pathlib import Path
from datetime import datetime, timezone

import pytest

from moira._kernel_paths import find_planetary_kernel
from moira.classical_perfection import (
    ClassicalPerfectionEventKind, ClassicalPerfectionState, LillyPerfectionKind, lilly_perfection_at,
)
from moira.constants import Body
from moira.horary import (
    HoraryEvidenceState, HoraryHousePolicy, HoraryPerfectionState, HoraryQuestionReceipt,
    HoraryQuestionTimeBasis, HoraryQuestionTimeReceipt, HorarySourceCalendar, horary_evidence_at,
)
from moira.houses import HouseSystem
from moira.julian import jd_from_datetime, utc_to_ut1
from moira.planets import planet_at
from moira.spk_reader import SpkReader


@pytest.mark.requires_ephemeris
def test_j2000_lilly_trace_uses_de441_and_preserves_event_chronology() -> None:
    kernel = find_planetary_kernel()
    assert kernel is not None and kernel.name == "de441.bsp"
    with SpkReader(kernel) as reader:
        result = lilly_perfection_at(
            2451545.0, 2451547.0, Body.MERCURY, Body.JUPITER,
            is_day_chart=True, reader=reader,
        )
    assert Path(result.reader_provenance).name == "de441.bsp"
    assert result.profile_id == "lilly_1647_perfection_v1"
    assert len(result.initial_states) == 7
    assert result.events == tuple(sorted(result.events, key=lambda item: (item.jd_ut, item.event_id)))
    assert len({item.event_id for item in result.events}) == len(result.events)
    assert result.policy.planetary_moiety_table == "lilly_1647_traditional_moieties"
    assert any(item.kind is ClassicalPerfectionEventKind.ASPECT_EXACT for item in result.events)
    assert any(item.kind is ClassicalPerfectionEventKind.SIGN_INGRESS for item in result.events)
    assert len(result.witnesses) == 6
    assert result.complete_electional_judgement is False


def _direct(analysis):
    return next(w for w in analysis.witnesses if w.kind is LillyPerfectionKind.DIRECT)


@pytest.mark.requires_ephemeris
def test_de441_moon_jupiter_trine_survives_reversed_principal_roles() -> None:
    with SpkReader(find_planetary_kernel()) as reader:
        forward = lilly_perfection_at(2451548., 2451550., Body.MOON, Body.JUPITER,
                                     is_day_chart=True, reader=reader)
        reverse = lilly_perfection_at(2451548., 2451550., Body.JUPITER, Body.MOON,
                                     is_day_chart=True, reader=reader)
        assert forward.events == reverse.events
        assert _direct(forward).state is _direct(reverse).state is ClassicalPerfectionState.PRESENT
        assert _direct(forward).event_ids == _direct(reverse).event_ids
        event = next(e for e in forward.events if e.event_id in _direct(forward).event_ids)
        assert (event.actor, event.target, event.aspect, event.directional_angle_deg) == (
            Body.MOON, Body.JUPITER, "trine", 240.)
        a = planet_at(Body.MOON, event.jd_ut, reader=reader).longitude
        b = planet_at(Body.JUPITER, event.jd_ut, reader=reader).longitude
        assert abs((a - b - 240 + 180) % 360 - 180) <= 1e-7


@pytest.mark.requires_ephemeris
def test_public_horary_adapter_retains_the_de441_trine_for_jupiter_querent() -> None:
    instant = datetime(2000, 1, 4, 12, tzinfo=timezone.utc)
    jd = utc_to_ut1(jd_from_datetime(instant))
    question = HoraryQuestionReceipt(
        question_id="pair-orientation-regression", latitude_deg=51.5, longitude_deg=-25.,
        time=HoraryQuestionTimeReceipt(
            state=HoraryEvidenceState.EVALUATED,
            stated_basis=HoraryQuestionTimeBasis.QUESTION_PROPOSED_AND_FIGURE_ERECTED,
            stated_basis_source="Synthetic diagnostic metadata; no historical or outcome claim",
            source_calendar=HorarySourceCalendar.GREGORIAN,
            source_instant_label=instant.isoformat(), normalized_instant=instant,
            normalized_jd_ut1=jd, conversion_policy_id="moira.julian.jd_from_datetime+utc_to_ut1:v1",
            reason=None,
        ), perspective_path=(), terminal_topic_house=5,
    )
    with SpkReader(find_planetary_kernel()) as reader:
        profile = horary_evidence_at(question, house_policy=HoraryHousePolicy(HouseSystem.EQUAL),
                                    perfection_jd_end=jd + 2, reader=reader)
    assert profile.significators.principal_querent.body == Body.JUPITER
    assert profile.significators.principal_quesited.body == Body.MOON
    assert profile.perfection.state is HoraryPerfectionState.COMPOSED
    analysis = profile.perfection.analysis
    direct = _direct(analysis)
    assert direct.state is ClassicalPerfectionState.PRESENT
    assert direct.actors == (Body.JUPITER, Body.MOON)
    event = next(e for e in analysis.events if e.event_id in direct.event_ids)
    assert (event.actor, event.target, event.aspect, event.directional_angle_deg) == (
        Body.MOON, Body.JUPITER, "trine", 240.)
