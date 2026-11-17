"""Independent synthetic contacts for the opt-in shadow-event product."""
import math
from types import SimpleNamespace

import pytest

from moira import eclipse
from moira.eclipse_geometry import EARTH_RADIUS_KM, MOON_RADIUS_KM, SUN_RADIUS_KM
from moira import lunar_shadow_events as events
from moira.lunar_shadow_events import LunarShadowWindowError, lunar_shadow_event_near


DAY = 2459000.0
D = 384400.0
S = 149597870.7
RATE = 0.15
ALPHA = math.asin(MOON_RADIUS_KM / D)
PM = math.asin(EARTH_RADIUS_KM / D)
SS = math.asin(SUN_RADIUS_KM / S)
PS = math.asin(EARTH_RADIUS_KM / S)
PEN = 1.01 * PM + SS + PS
UMB = 1.01 * PM - SS + PS


class FakeCalculator:
    _reader = None

    def _jd_tt_from_ut(self, jd, *, delta_t_mode):
        assert delta_t_mode == "native"
        return jd


@pytest.mark.parametrize("minimum,kind", [(0.001, "total"), (UMB, "partial"), (PEN, "penumbral")])
def test_danjon_contacts_match_independent_analytic_cone_tangencies(monkeypatch, minimum, kind):
    def bodies(jd, reader, *, sun_retarded, moon_retarded):
        assert sun_retarded and not moon_retarded
        theta = math.hypot(minimum, RATE * (jd - DAY))
        return (S, 0.0, 0.0), (-D * math.cos(theta), D * math.sin(theta), 0.0)

    monkeypatch.setattr(eclipse, "_eclipse_body_pair", bodies)
    event = lunar_shadow_event_near(FakeCalculator(), DAY, policy="danjon_angular")
    assert event.candidate_type == kind
    assert event.completeness_certified is False
    assert abs(event.greatest_jd_ut - DAY) * 86400 < 0.1
    for limit, first, last in (
        (PEN + ALPHA, event.contacts.p1, event.contacts.p4),
        (UMB + ALPHA, event.contacts.u1, event.contacts.u4),
        (UMB - ALPHA, event.contacts.u2, event.contacts.u3),
    ):
        if minimum >= limit:
            assert first is None and last is None
        else:
            offset = math.sqrt(limit**2 - minimum**2) / RATE
            assert abs(first - (DAY - offset)) * 86400 < 0.1
            assert abs(last - (DAY + offset)) * 86400 < 0.1


def test_truncated_window_is_not_reported_as_no_eclipse(monkeypatch):
    def bodies(jd, reader, *, sun_retarded, moon_retarded):
        theta = math.hypot(0.001, RATE * (jd - DAY))
        return (S, 0.0, 0.0), (-D * math.cos(theta), D * math.sin(theta), 0.0)

    monkeypatch.setattr(eclipse, "_eclipse_body_pair", bodies)
    with pytest.raises(LunarShadowWindowError):
        lunar_shadow_event_near(FakeCalculator(), DAY, policy="danjon_angular", window_days=0.05)


def test_unknown_policy_is_rejected():
    with pytest.raises(ValueError, match="policy"):
        lunar_shadow_event_near(FakeCalculator(), DAY, policy="legacy")


def test_undetected_narrow_event_is_unresolved_not_absent(monkeypatch):
    # A smooth ~8.6-second dip hidden between both the optimizer's nine
    # samples and the 120-second contact grid, with another broad minimum.
    def bodies(jd, reader, *, sun_retarded, moon_retarded):
        return (jd, 0., 0.), (1., 0., 0.)

    def model(sun, moon):
        x = sun[0] - DAY
        clearance = (x - 0.2)**2 + 0.01 - 0.2*math.exp(-((x + 0.12)/0.00005)**2)
        return SimpleNamespace(penumbral_margin=-clearance)

    monkeypatch.setattr(eclipse, "_eclipse_body_pair", bodies)
    monkeypatch.setattr(events, "danjon_angular_shadow", model)
    candidate = events.inspect_lunar_shadow_candidate(FakeCalculator(), DAY, policy="danjon_angular")
    assert candidate.status == "unresolved"
    assert candidate.event is None
    assert candidate.complete is False


def test_detected_candidate_retains_uncertified_status(monkeypatch):
    def bodies(jd, reader, *, sun_retarded, moon_retarded):
        theta = math.hypot(0.001, RATE * (jd - DAY))
        return (S, 0.0, 0.0), (-D * math.cos(theta), D * math.sin(theta), 0.0)
    monkeypatch.setattr(eclipse, "_eclipse_body_pair", bodies)
    candidate = events.inspect_lunar_shadow_candidate(FakeCalculator(), DAY, policy="danjon_angular")
    assert candidate.status == "detected"
    assert candidate.complete is False
    assert candidate.event.completeness_certified is False
