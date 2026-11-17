"""Conditional TT interval checks do not claim live or continuous completeness."""
from fractions import Fraction
import math
from types import SimpleNamespace

import pytest

from moira._eclipse_interval import RationalInterval
from moira.eclipse import _eclipse_body_pair
from moira.lunar_shadow_events import inspect_lunar_shadow_tt_interval
from moira.lunar_shadow_models import spherical_cone_shadow


@pytest.mark.requires_ephemeris
@pytest.mark.parametrize(
    "center,half_seconds,expected",
    [
        (2459892.26, 100, "conditionally_excluded"),
        (2459891.9582497696, 5, "conditionally_overlapping"),
    ],
)
def test_tt_interval_encloses_live_samples_without_claiming_live_proof(
    planetary_reader, center, half_seconds, expected,
):
    """The model's represented-TT bound covers samples from the live route."""
    start, end = center - half_seconds / 86400, center + half_seconds / 86400
    result = inspect_lunar_shadow_tt_interval(SimpleNamespace(_reader=planetary_reader), start, end)
    assert result.status == expected
    assert result.model == "static_finite_cone"
    assert result.execution_policy == "frozen_type2_snapshot"
    assert len(result.record_routes) == result.route_bounds_evaluated == 14
    assert result.max_route_calls == 32 and result.max_records == 256
    assert result.clock_obligations == result.norm_obligations == 11
    assert len(result.kernel_sha256_at_reader_open) == 64
    assert all(len(route[3]) == 64 for route in result.record_routes)
    assert result.numerical_assumptions
    assert not result.numerical_premises_attested and not result.live_route_attested
    assert not result.continuous_time_covered and not result.ut1_covered
    assert not result.eclipse_absence_certified and not result.search_complete
    for tt in (start, math.nextafter(start, math.inf), center, math.nextafter(end, -math.inf), end):
        sun, moon = _eclipse_body_pair(tt, planetary_reader, sun_retarded=True, moon_retarded=False)
        actual = spherical_cone_shadow(sun, moon).penumbral_margin
        assert result.penumbral_margin_lower_km <= actual <= result.penumbral_margin_upper_km
        if expected == "conditionally_excluded":
            assert actual < -result.contact_tolerance_km
        else:
            assert actual > result.contact_tolerance_km


@pytest.mark.requires_ephemeris
def test_short_native_grazing_control_is_unresolved_under_other_model(planetary_reader):
    """The 13.9-second native event is not a finite-cone classification oracle."""
    tt = 1248813.457560655
    result = inspect_lunar_shadow_tt_interval(
        SimpleNamespace(_reader=planetary_reader), tt, tt, earth_radius_scale=1.01,
    )
    assert result.status == "unresolved"
    assert "clock" in result.reason
    assert result.penumbral_margin_lower_km is result.penumbral_margin_upper_km is None
    assert not result.eclipse_absence_certified and not result.search_complete


def test_unavailable_reader_stays_unresolved():
    result = inspect_lunar_shadow_tt_interval(SimpleNamespace(_reader=None), 2459892.25, 2459892.26)
    assert result.status == "unresolved"
    assert result.kernel_sha256_at_reader_open is None
    assert result.record_routes == ()
    assert not result.eclipse_absence_certified


@pytest.mark.requires_ephemeris
def test_exhausted_route_budget_is_unresolved_not_excluded(planetary_reader):
    result = inspect_lunar_shadow_tt_interval(
        SimpleNamespace(_reader=planetary_reader), 2459892.26, 2459892.26,
        max_route_calls=1,
    )
    assert result.status == "unresolved"
    assert "budget" in result.reason
    assert result.max_route_calls == 1
    assert result.route_bounds_evaluated is None
    assert not result.eclipse_absence_certified


@pytest.mark.parametrize("low,high,expected", [
    (-2, -2, "conditionally_excluded"),
    (-1, -1, "unresolved"),
    (-2, 2, "unresolved"),
    (1, 1, "unresolved"),
    (2, 2, "conditionally_overlapping"),
])
def test_contact_threshold_is_inclusive_at_both_sides(monkeypatch, low, high, expected):
    """A bound equal to either coalescence limit is not classified."""
    import moira._eclipse_lunar_totality as totality
    from moira._eclipse_contact_solver import _CONTACT_COALESCENCE_TOLERANCE_KM

    tolerance = Fraction.from_float(_CONTACT_COALESCENCE_TOLERANCE_KM)
    fake = SimpleNamespace(
        frozen_snapshot_status="conditionally_proved",
        frozen_snapshot_cone=SimpleNamespace(penumbral_margin_km=RationalInterval(low * tolerance, high * tolerance)),
        vectors=None, reasons=(), clock_checks=(), norm_checks=(),
        max_exhaustive_clock_states=0, exhaustive_clock_states_checked=0,
        exhaustive_clock_cache_hits=0,
    )
    monkeypatch.setattr(totality, "assess_conditional_lunar_interval_totality", lambda *a, **k: fake)
    result = inspect_lunar_shadow_tt_interval(SimpleNamespace(_reader=None), 1.0, 1.0)
    assert result.status == expected
    assert not result.eclipse_absence_certified and not result.continuous_time_covered


@pytest.mark.parametrize("start,end,scale", [
    (2.0, 1.0, 1.0), (float("nan"), 1.0, 1.0),
    (1.0, float("inf"), 1.0), (1.0, 1.0, 0.0),
    (True, 1.0, 1.0), (1.0, 1.0, 10**400),
])
def test_invalid_interval_rejected(start, end, scale):
    with pytest.raises(ValueError):
        inspect_lunar_shadow_tt_interval(SimpleNamespace(_reader=None), start, end, earth_radius_scale=scale)


@pytest.mark.parametrize("budget", [-1, True, 1.5])
def test_invalid_exhaustive_clock_budget_rejected(budget):
    with pytest.raises(ValueError):
        inspect_lunar_shadow_tt_interval(
            SimpleNamespace(_reader=None), 1.0, 1.0, max_exhaustive_clock_states=budget,
        )
