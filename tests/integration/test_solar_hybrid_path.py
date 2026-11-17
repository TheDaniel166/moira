"""Native central-path hybrid regressions, not a catalog-parity claim.

The 20 seed epochs identify the previously investigated disagreements with
NASA's five-millennium catalog.  The seeds are native UT1 estimates of greatest
eclipse, not expected contact times or an independent astronomical oracle.
All witness positions and transitions must be recomputed against the active
ephemeris and time implementation, especially at the short ingress phases.
"""
from __future__ import annotations

import math

import pytest

import moira.solar_eclipse_hybrid as hybrid_module
from moira.eclipse import (
    EclipseEvent,
    _axis_surface_point_from_shadow,
    _earth_fixed_solar_shadow,
    _shadow_dot,
    _shadow_subtract,
    _solar_shadow_discs,
    _wgs84_surface_normal_unit,
)
from moira.solar_eclipse_hybrid import classify_solar_central_path
from moira.spk_reader import OutOfRangeError


pytestmark = pytest.mark.requires_ephemeris

# Lunation, approximate native greatest eclipse (UT1), and whether the earlier
# investigation established two opposite-sign daylight points. The final
# category is an observed witness, not NASA's subtype or a proof of absence.
CASES = (
    (-47625, 1045155.0252075894, True),
    (-45054, 1121079.0220085473, False),
    (-36192, 1382778.5574522745, False),
    (-36052, 1386913.0116933244, False),
    (-35107, 1414819.5999636794, False),
    (-34872, 1421759.5146040430, True),
    (-34866, 1421936.2171787173, False),
    (-29420, 1582760.5516342013, True),
    (-28610, 1606680.1270428728, True),
    (-25969, 1684669.8080241305, True),
    (-25934, 1685704.3261082352, True),
    (-13838, 2042905.6053827796, True),
    (-13369, 2056756.1447533281, True),
    (-5387, 2292468.4333965364, True),
    (-3673, 2343083.9751177207, True),
    (-2423, 2379997.9696220569, False),
    (-164, 2446707.2953674407, False),
    (2137, 2514657.1662552492, True),
    (4778, 2592647.0173241287, True),
    (10559, 2763363.8118256605, True),
)


def _event_at_native_seed(calc, seed):
    """Create an event at the native greatest seed without catalog labels."""
    return EclipseEvent(jd_ut=seed, data=calc.calculate_jd(seed))


def _independent_axis_witness(calc, witness):
    """Recompute angular-ratio and geometric-horizon evidence at a witness."""
    shadow = _earth_fixed_solar_shadow(calc, witness.jd_ut)
    assert shadow is not None
    point = _axis_surface_point_from_shadow(shadow)
    assert point is not None
    xyz = point.xyz_itrf_km
    sun_direction = _shadow_subtract(shadow.sun_xyz_from_earth_itrf_km, xyz)
    sun_distance = math.sqrt(_shadow_dot(sun_direction, sun_direction))
    sine_altitude = _shadow_dot(_wgs84_surface_normal_unit(xyz), sun_direction) / sun_distance
    altitude_deg = math.degrees(math.asin(max(-1.0, min(1.0, sine_altitude))))
    _, sun_radius, moon_radius = _solar_shadow_discs(shadow, xyz)
    ratio_minus_one = moon_radius / sun_radius - 1.0

    assert altitude_deg > 0.0
    assert witness.sun_altitude_deg == pytest.approx(altitude_deg, abs=1.0e-9)
    assert witness.angular_radius_ratio_minus_one == pytest.approx(ratio_minus_one, abs=1.0e-12)
    assert witness.latitude_deg == pytest.approx(point.latitude_deg, abs=1.0e-9)
    assert witness.longitude_deg == pytest.approx(point.longitude_deg, abs=1.0e-9)
    assert math.copysign(1.0, witness.signed_radius_km) == math.copysign(1.0, ratio_minus_one)


@pytest.mark.parametrize("lunation,seed,has_both_signs", CASES, ids=lambda x: str(x))
def test_twenty_disputed_cases_return_witnesses_or_explicit_uncertainty(
    eclipse_calculator, lunation, seed, has_both_signs,
):
    calc = eclipse_calculator
    event = _event_at_native_seed(calc, seed)
    assert event.data.saros_lunation_number == lunation
    result = classify_solar_central_path(calc, event)

    assert 0 <= result.evaluation_count <= 512
    assert result.reason
    # Sampled transitions cannot establish the completeness required for H2/H3.
    assert result.subtype is None
    if has_both_signs:
        assert result.status == "hybrid"
        assert result.axis_interval is not None
        assert result.annular_witness is not None
        assert result.total_witness is not None
        assert result.annular_witness.signed_radius_km < 0.0
        assert result.total_witness.signed_radius_km > 0.0
        for witness in (result.annular_witness, result.total_witness):
            assert result.axis_interval[0] < witness.jd_ut < result.axis_interval[1]
            _independent_axis_witness(calc, witness)
        assert result.transitions
        for transition in result.transitions:
            assert result.axis_interval[0] <= transition.start_jd_ut < transition.end_jd_ut <= result.axis_interval[1]
            assert transition.direction in {"annular_to_total", "total_to_annular"}
            assert 0.0 < transition.width_seconds <= 0.001
    else:
        # A same-sign sample or missing axis is not evidence of non-hybridness.
        assert result.status == "unresolved"


def test_sub_tenth_second_ingress_switch_is_isolated(eclipse_calculator):
    """The -0379 case switches near +0.08 s on the active native model."""
    result = classify_solar_central_path(
        eclipse_calculator,
        _event_at_native_seed(eclipse_calculator, 1582760.5516342013),
    )
    assert result.status == "hybrid"
    ingress = result.axis_interval[0]
    first = min(result.transitions, key=lambda t: t.start_jd_ut)
    assert first.direction == "annular_to_total"
    assert 0.0 < (first.start_jd_ut - ingress) * 86400.0 < 0.1
    assert (first.end_jd_ut - ingress) * 86400.0 < 0.1


@pytest.mark.parametrize(
    "seed,expected",
    ((2457987.267724502, "unresolved"),  # 2017 ordinary total
     (2460054.678318233, "hybrid"),      # 2023 hybrid control
     (2446707.2953674407, "unresolved")),  # 1986 unswitched case
)
def test_modern_controls_do_not_convert_single_sign_samples_to_proof(
    eclipse_calculator, seed, expected,
):
    calc = eclipse_calculator
    event = _event_at_native_seed(calc, seed)
    before = calc.calculate_jd(seed)
    result = classify_solar_central_path(calc, event)
    assert result.status == expected
    assert calc.calculate_jd(seed) == before == event.data


def test_evaluation_budget_exhaustion_remains_unresolved(eclipse_calculator):
    event = _event_at_native_seed(eclipse_calculator, 2457987.267724502)
    result = classify_solar_central_path(eclipse_calculator, event, max_evaluations=1)
    assert result.status == "unresolved"
    assert result.budget_exhausted
    assert result.evaluation_count == 1  # The seed shadow is included.


def test_budget_exhaustion_does_not_discard_two_existing_witnesses(eclipse_calculator):
    event = _event_at_native_seed(eclipse_calculator, 1582760.5516342013)
    result = classify_solar_central_path(eclipse_calculator, event, max_evaluations=10)
    assert result.status == "hybrid"
    assert result.budget_exhausted
    assert result.annular_witness is not None
    assert result.total_witness is not None
    assert not result.transitions  # Refinement was not attempted after exhaustion.


@pytest.mark.parametrize("stage", ("seed", "interval", "sample"))
@pytest.mark.parametrize("error_type", (OutOfRangeError, ValueError, ArithmeticError))
def test_unexpected_ephemeris_and_geometry_failures_propagate(
    eclipse_calculator, monkeypatch, stage, error_type,
):
    event = _event_at_native_seed(eclipse_calculator, 2457987.267724502)
    original = hybrid_module._earth_fixed_solar_shadow
    error = (
        OutOfRangeError("injected data failure", out_of_range_times=True)
        if error_type is OutOfRangeError else error_type("injected data failure")
    )

    if stage == "interval":
        def fail_interval(*_args, **_kwargs):
            raise error

        monkeypatch.setattr(hybrid_module, "_solve_solar_central_interval", fail_interval)
    else:
        calls = 0

        def fail_at_stage(*args, **kwargs):
            nonlocal calls
            calls += 1
            if calls == (1 if stage == "seed" else 2):
                raise error
            return original(*args, **kwargs)

        monkeypatch.setattr(hybrid_module, "_earth_fixed_solar_shadow", fail_at_stage)

    with pytest.raises(error_type, match="injected data failure"):
        classify_solar_central_path(eclipse_calculator, event)


def test_seed_with_no_axis_is_unresolved(eclipse_calculator, monkeypatch):
    event = _event_at_native_seed(eclipse_calculator, 2457987.267724502)
    monkeypatch.setattr(hybrid_module, "_earth_fixed_solar_shadow", lambda *_args, **_kwargs: None)
    result = classify_solar_central_path(eclipse_calculator, event)
    assert result.status == "unresolved"
    assert result.axis_interval is None
    assert result.annular_witness is None
    assert result.total_witness is None
    assert result.evaluation_count == 1


@pytest.mark.parametrize("field", ("radius", "altitude", "ratio"))
def test_nonfinite_observable_is_an_error(eclipse_calculator, monkeypatch, field):
    event = _event_at_native_seed(eclipse_calculator, 2457987.267724502)
    if field == "ratio":
        monkeypatch.setattr(hybrid_module, "_solar_shadow_discs", lambda *_args: (0.0, 1.0, math.nan))
    else:
        original = hybrid_module._shadow_dot
        calls = 0

        def corrupt_selected_observable(*args):
            nonlocal calls
            calls += 1
            # First diagnostic dot product is signed cone radius, third is
            # the geometric-horizon numerator. The first epoch is daylight.
            if calls == (1 if field == "radius" else 3):
                return math.nan
            return original(*args)

        monkeypatch.setattr(hybrid_module, "_shadow_dot", corrupt_selected_observable)
    with pytest.raises(ArithmeticError, match="not finite"):
        classify_solar_central_path(eclipse_calculator, event)
