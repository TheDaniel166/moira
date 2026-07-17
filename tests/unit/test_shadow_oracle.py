from dataclasses import FrozenInstanceError, replace
import math
from types import SimpleNamespace

import pytest

from moira._ephemeris_time import _ephemeris_tt_to_ut1
from moira.constants import EARTH_RADIUS_KM, MOON_RADIUS_KM, SUN_RADIUS_KM
from moira.eclipse_geometry import (
    umbra_radius,
    penumbra_radius,
    lunar_umbral_magnitude,
    lunar_penumbral_magnitude,
    shadow_axis_offset_deg,
)


def test_solar_besselian_specialist_exports_preserve_type_identity() -> None:
    from moira.eclipse import SolarBesselianElements as EclipseElements
    from moira.eclipse_besselian import SolarBesselianElements as GoverningElements
    from moira.sky.eclipse import SolarBesselianElements as SkyElements

    assert EclipseElements is GoverningElements is SkyElements


def test_shadow_cone_geometry_invariants() -> None:
    """Prove that shadow cone geometry does not collapse or invert."""
    sun_dist_km = 149597870.7  # 1 AU
    moon_dist_km_perigee = 362600.0
    moon_dist_km_apogee = 405400.0
    
    # 1. Penumbra must always be strictly larger than Umbra
    u_peri = umbra_radius(sun_dist_km, moon_dist_km_perigee)
    p_peri = penumbra_radius(sun_dist_km, moon_dist_km_perigee)
    assert p_peri > u_peri > 0.0

    u_apo = umbra_radius(sun_dist_km, moon_dist_km_apogee)
    p_apo = penumbra_radius(sun_dist_km, moon_dist_km_apogee)
    assert p_apo > u_apo > 0.0
    
    # 2. Umbra size must strictly decrease as the Moon moves away
    # (The cone narrows to a point)
    assert u_peri > u_apo
    
    # 3. Penumbra size must strictly decrease as the Moon moves away
    # (The apparent angular size decreases due to 1/D perspective)
    assert p_peri > p_apo

def test_magnitude_monotonicity() -> None:
    """Prove that magnitude strictly increases as the axis offset decreases."""
    u_rad = 0.75  # degrees
    m_rad = 0.25  # degrees
    
    # Offset decreasing from 1.0 (edge) to 0.0 (exact center)
    offsets = [1.0, 0.75, 0.5, 0.25, 0.0]
    magnitudes = [
        lunar_umbral_magnitude(u_rad, m_rad, offset)
        for offset in offsets
    ]
    
    # Check strict monotonicity
    for i in range(len(magnitudes) - 1):
        assert magnitudes[i+1] > magnitudes[i]
        
    # At exact center (offset=0), mag = (0.75 + 0.25 - 0) / 0.5 = 2.0
    assert magnitudes[-1] == 2.0

def test_grazing_limits() -> None:
    """Test exactly when the Moon barely touches the umbra."""
    u_rad = 0.75
    m_rad = 0.25
    
    # Barely touching (exterior contact): offset = u_rad + m_rad = 1.0
    offset_exterior = 1.0
    mag_exterior = lunar_umbral_magnitude(u_rad, m_rad, offset_exterior)
    assert math.isclose(mag_exterior, 0.0, abs_tol=1e-9)
    
    # Just inside: offset slightly less than 1.0
    mag_just_inside = lunar_umbral_magnitude(u_rad, m_rad, 0.99)
    assert mag_just_inside > 0.0

def test_anti_solar_geometry() -> None:
    """Prove the shadow axis offset treats 180 degrees as zero offset."""
    # Exact opposition
    assert shadow_axis_offset_deg(180.0) == 0.0
    
    # Slightly off
    assert math.isclose(shadow_axis_offset_deg(179.5), 0.5, abs_tol=1e-9)
    assert math.isclose(shadow_axis_offset_deg(180.5), 0.5, abs_tol=1e-9)

def _solar_besselian_at_tt(eclipse_calculator, jd_tt: float):
    jd_ut1 = _ephemeris_tt_to_ut1(jd_tt, eclipse_calculator._reader)
    return eclipse_calculator.solar_besselian_elements(jd_ut1)


def test_runtime_besselian_projection_matches_native_shadow_axis(
    eclipse_calculator,
) -> None:
    elements = _solar_besselian_at_tt(eclipse_calculator, 2460409.25)

    projected_axis_distance_km = math.hypot(elements.x, elements.y) * EARTH_RADIUS_KM
    native_axis_distance_km = eclipse_calculator._native_solar_shadow_axis_distance_km(
        elements.jd_ut1
    )
    assert projected_axis_distance_km == pytest.approx(
        native_axis_distance_km,
        rel=2.0e-12,
        abs=1.0e-6,
    )


def test_runtime_besselian_orientation_ranges_and_cones_are_ordered(
    eclipse_calculator,
) -> None:
    elements = _solar_besselian_at_tt(eclipse_calculator, 2460409.25)

    # At the 2024-04-08 reference epoch the axis is west (negative x) and
    # north (positive y).  These robust signs guard the +east/+north basis.
    assert elements.x < 0.0
    assert elements.y > 0.0
    assert -90.0 <= elements.d <= 90.0
    assert 0.0 <= elements.mu < 360.0
    assert all(
        math.isfinite(value)
        for value in (
            elements.x,
            elements.y,
            elements.d,
            elements.mu,
            elements.l1,
            elements.l2,
            elements.tan_f1,
            elements.tan_f2,
        )
    )
    assert elements.l1 > 0.0
    assert elements.l1 > abs(elements.l2)
    assert elements.tan_f1 > elements.tan_f2 > 0.0


def test_runtime_besselian_cones_use_exact_common_tangent_geometry(
    eclipse_calculator,
) -> None:
    jd_tt = 2460409.25
    elements = _solar_besselian_at_tt(eclipse_calculator, jd_tt)
    state = eclipse_calculator._native_solar_shadow_axis_state_tt(jd_tt)

    sin_f1 = elements.tan_f1 / math.sqrt(1.0 + elements.tan_f1**2)
    sin_f2 = elements.tan_f2 / math.sqrt(1.0 + elements.tan_f2**2)
    assert sin_f1 == pytest.approx(
        (SUN_RADIUS_KM + MOON_RADIUS_KM) / state.sun_moon_distance_km,
        rel=2.0e-15,
    )
    assert sin_f2 == pytest.approx(
        (SUN_RADIUS_KM - MOON_RADIUS_KM) / state.sun_moon_distance_km,
        rel=2.0e-15,
    )

    cos_f1 = 1.0 / math.sqrt(1.0 + elements.tan_f1**2)
    cos_f2 = 1.0 / math.sqrt(1.0 + elements.tan_f2**2)
    distance_to_plane_km = -state.axis_projection_km
    assert elements.l1 * EARTH_RADIUS_KM == pytest.approx(
        MOON_RADIUS_KM / cos_f1 + distance_to_plane_km * elements.tan_f1,
        rel=2.0e-15,
    )
    assert elements.l2 * EARTH_RADIUS_KM == pytest.approx(
        distance_to_plane_km * elements.tan_f2 - MOON_RADIUS_KM / cos_f2,
        rel=2.0e-15,
    )


def test_runtime_besselian_l2_preserves_total_and_annular_sign(
    eclipse_calculator,
) -> None:
    total = _solar_besselian_at_tt(eclipse_calculator, 2460409.25)
    annular = _solar_besselian_at_tt(eclipse_calculator, 2463362.0416666665)

    assert total.l2 < 0.0
    assert annular.l2 > 0.0


def test_runtime_besselian_result_is_frozen(eclipse_calculator) -> None:
    elements = _solar_besselian_at_tt(eclipse_calculator, 2460409.25)

    with pytest.raises(FrozenInstanceError):
        elements.x = 0.0

    with pytest.raises(ValueError, match="magnitude of signed l2"):
        replace(elements, l2=-(elements.l1 + 1.0))


def test_runtime_besselian_fails_closed_for_non_de441_reader_identity(
    eclipse_calculator,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "moira.eclipse._reader_identity_at",
        lambda _reader, _jd_tt: SimpleNamespace(
            planetary_ephemeris="DE440",
            lunar_ephemeris="LE440",
            summary_label="DE-0440LE-0440",
        ),
    )

    with pytest.raises(RuntimeError, match="DE441/LE441"):
        eclipse_calculator.solar_besselian_elements(2460409.25)


def test_runtime_besselian_rejects_opposite_full_moon_geometry(
    eclipse_calculator,
) -> None:
    # The 2024-03-25 lunar-eclipse epoch places the Moon on the anti-solar
    # side of Earth, so it cannot define a solar shadow ray aimed at Earth.
    jd_ut1 = _ephemeris_tt_to_ut1(2460394.8, eclipse_calculator._reader)

    with pytest.raises(ValueError):
        eclipse_calculator.solar_besselian_elements(jd_ut1)
