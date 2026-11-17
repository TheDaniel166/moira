"""DE441 regression for strict maximum ordering across the lunar phase."""
import math

import pytest

from moira.eclipse import EclipseCalculator
from moira.julian import julian_day

pytestmark = pytest.mark.requires_ephemeris


@pytest.mark.parametrize("date", [(2024, 1, 1), (2024, 3, 1), (0, 1, 1), (0, 3, 1)])
@pytest.mark.parametrize(
    "next_method,previous_method",
    [
        ("next_solar_eclipse", "previous_solar_eclipse"),
        ("next_lunar_eclipse", "previous_lunar_eclipse"),
        ("next_lunar_eclipse_canon", "previous_lunar_eclipse_canon"),
    ],
)
def test_next_previous_identity_across_calendar_boundaries(
    eclipse_calculator, date, next_method, previous_method,
):
    """On sampled DE441 dates, crossing midnight preserves event identity.

    The proleptic-Gregorian dates include New Year and leap-day boundaries
    in a modern year and astronomical year zero. Each query differs from
    midnight by one represented UT1 float; this is same-model ordering
    evidence, not an external oracle or a proof over all dates.
    """
    boundary = julian_day(*date)
    before = math.nextafter(boundary, -math.inf)
    after = math.nextafter(boundary, math.inf)
    next_search = getattr(eclipse_calculator, next_method)
    previous_search = getattr(eclipse_calculator, previous_method)

    next_before = next_search(before).jd_ut
    next_after = next_search(after).jd_ut
    previous_before = previous_search(before).jd_ut
    previous_after = previous_search(after).jd_ut

    assert next_before == next_after
    assert previous_before == previous_after
    assert previous_before < before < boundary < after < next_after


@pytest.mark.parametrize(
    "method,seed,expected",
    [
        ("previous_solar_eclipse", 2460409.26325, 2460409.2620393815),
        ("previous_lunar_eclipse", 2459891.959038358, 2459891.9582497696),
        ("previous_lunar_eclipse_canon", 2459891.958781869, 2459891.9577367916),
        ("next_lunar_eclipse", 2460394.796503038, 2460394.801112594),
        ("next_lunar_eclipse_canon", 2460394.796223973, 2460394.8005544636),
    ],
)
def test_nearest_maximum_can_cross_phase_seed(eclipse_calculator, method, seed, expected):
    """Same DE441 model, numerical regression tolerance 0.05 seconds in UT1."""
    event = getattr(eclipse_calculator, method)(seed)
    assert event.jd_ut == pytest.approx(expected, abs=0.05 / 86400)
    assert event.jd_ut < seed if method.startswith("previous") else event.jd_ut > seed


@pytest.mark.parametrize(
    "previous,next_,seed",
    [
        ("previous_solar_eclipse", "next_solar_eclipse", 2460409.26325),
        ("previous_lunar_eclipse", "next_lunar_eclipse", 2459891.959038358),
        ("previous_lunar_eclipse_canon", "next_lunar_eclipse_canon", 2459891.958781869),
    ],
)
def test_event_maximum_and_adjacent_floats_are_strict_and_deterministic(
    eclipse_calculator, previous, next_, seed,
):
    """The identity at exact max is excluded; each adjacent float includes it."""
    event = getattr(eclipse_calculator, previous)(seed)
    epoch = event.jd_ut
    for calculator in (eclipse_calculator, EclipseCalculator(reader=eclipse_calculator._reader)):
        assert getattr(calculator, next_)(math.nextafter(epoch, -math.inf)).jd_ut == epoch
        assert getattr(calculator, previous)(math.nextafter(epoch, math.inf)).jd_ut == epoch
        assert getattr(calculator, next_)(epoch).jd_ut > epoch
        assert getattr(calculator, previous)(epoch).jd_ut < epoch


def test_python_and_native_lunar_range_include_the_same_boundary_event(eclipse_calculator):
    """Both paths use the same DE441 model; parity is not an external oracle."""
    start = 2460394.796503038
    python = eclipse_calculator._lunar_eclipses_in_range_python(start, start + 1)
    native = eclipse_calculator.lunar_eclipses_in_range(start, start + 1)
    assert len(python) == len(native) == 1
    assert python[0].jd_ut == pytest.approx(native[0].jd_ut, abs=0.05 / 86400)


@pytest.mark.parametrize(
    "family,seed",
    [("solar", 2460390.0), ("lunar", 2460380.0),
     ("solar", 991000.0), ("lunar", 991000.0)],
)
def test_native_range_matches_search_at_inclusive_maximum_boundaries(
    eclipse_calculator, family, seed,
):
    """DE441 represented event identity agrees, including singleton ranges."""
    calc = eclipse_calculator
    maximum = getattr(calc, f"next_{family}_eclipse")(seed).jd_ut
    range_fn = getattr(calc, f"{family}_eclipses_in_range")
    python_range_fn = getattr(calc, f"_{family}_eclipses_in_range_python")
    assert calc._native_eclipse_syzygy_candidates(family, maximum, maximum) is not None
    for start, end in (
        (maximum, maximum),
        (maximum - 1e-8, maximum + 1e-8),
        (maximum - 0.5, maximum),
        (maximum, maximum + 0.5),
        (math.nextafter(maximum, -math.inf), maximum),
        (maximum, math.nextafter(maximum, math.inf)),
    ):
        events = range_fn(start, end)
        assert [event.jd_ut for event in events] == [maximum]
        assert [event.jd_ut for event in python_range_fn(start, end)] == [maximum]
    before = math.nextafter(maximum, -math.inf)
    after = math.nextafter(maximum, math.inf)
    for start, end in ((maximum - 0.5, before), (after, maximum + 0.5)):
        assert range_fn(start, end) == []
        assert python_range_fn(start, end) == []


@pytest.mark.parametrize("kind", ["any", "total", "central"])
def test_solar_local_phase_straddle_respects_global_kind_filter(eclipse_calculator, kind):
    event = eclipse_calculator.previous_solar_eclipse(2460409.26325, kind=kind)
    assert event.jd_ut == pytest.approx(2460409.2620393815, abs=0.05 / 86400)


@pytest.mark.parametrize("kind", ["any", "total"])
def test_lunar_phase_straddle_respects_kind_filter(eclipse_calculator, kind):
    event = eclipse_calculator.previous_lunar_eclipse(2459891.959038358, kind=kind)
    assert event.jd_ut == pytest.approx(2459891.9582497696, abs=0.05 / 86400)
