"""DE441 end-to-end checks for the explicitly selected candidate models."""
import pytest

from moira.julian import julian_day
from moira.lunar_shadow_events import inspect_lunar_shadow_candidate


pytestmark = [pytest.mark.requires_ephemeris, pytest.mark.slow]


@pytest.mark.parametrize("policy", ["danjon_angular", "static_finite_cone"])
@pytest.mark.parametrize("year,month,day,hour,kind", [
    (2020, 7, 5, 4.5, "penumbral"),
    (2022, 11, 8, 11., "total"),
    (2023, 10, 28, 20., "partial"),
])
def test_real_candidate_and_legacy_stability(eclipse_calculator, policy, year, month, day, hour, kind):
    center = julian_day(year, month, day, hour)
    legacy_before = eclipse_calculator.calculate_lunar_event_jd(center)
    result = inspect_lunar_shadow_candidate(eclipse_calculator, center, policy=policy)
    assert result.status == "detected" and not result.complete
    event = result.event
    assert event.candidate_type == kind
    assert event.geometry_at_greatest.policy == policy
    assert event.contacts.p1 <= event.greatest_jd_ut <= event.contacts.p4
    for first, last in ((event.contacts.u1, event.contacts.u4), (event.contacts.u2, event.contacts.u3)):
        if first is not None:
            assert event.contacts.p1 <= first <= last <= event.contacts.p4
    assert eclipse_calculator.calculate_lunar_event_jd(center) == legacy_before


def test_2020_opale_control_is_reported_with_distinct_epoch_semantics(eclipse_calculator):
    # OPALE INPOP19A reports 04:30:03 UTC (rounded seconds), not our
    # penumbral-overlap-maximum definition. Compare only as a broad control.
    opale = julian_day(2020, 7, 5, 4 + 30/60 + 3/3600)
    result = inspect_lunar_shadow_candidate(eclipse_calculator, opale, policy="danjon_angular")
    assert result.status == "detected"
    assert abs(result.event.greatest_jd_ut - opale) * 86400 < 120
    # Different numerical criteria, even on identical Sun/Moon vectors.
    event = result.event
    assert abs(event.axis_distance_minimum_jd_ut - event.angular_opposition_minimum_jd_ut) * 86400 > 1.0
    assert abs(event.greatest_jd_ut - event.axis_distance_minimum_jd_ut) * 86400 > 0.01
    assert not event.completeness_certified


@pytest.mark.parametrize("policy,scale", [("danjon_angular", 1.), ("static_finite_cone", 1.01)])
@pytest.mark.parametrize("center", [1124725.8731301976, 1605129.5464545744,
                                  1614490.4889631793, 2457117.0006844974,
                                  2459035.6878407523])
def test_candidate_contact_step_convergence(eclipse_calculator, policy, scale, center):
    runs = [inspect_lunar_shadow_candidate(eclipse_calculator, center, policy=policy,
                                           earth_radius_scale=scale, coarse_step_seconds=step)
            for step in (120., 60., 30., 10.)]
    assert all(run.status == "detected" for run in runs)
    reference = runs[-1].event.contacts
    for run in runs[:-1]:
        assert run.event.candidate_type == runs[-1].event.candidate_type
        for name in ("p1", "u1", "u2", "u3", "u4", "p4"):
            value, expected = getattr(run.event.contacts, name), getattr(reference, name)
            assert (value is None) == (expected is None)
            if expected is not None:
                assert abs(value - expected) * 86400 < 0.03
