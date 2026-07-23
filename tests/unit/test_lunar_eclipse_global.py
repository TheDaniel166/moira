from __future__ import annotations

import pytest

from moira.constants import Body
from moira.eclipse_global import EclipseEpoch, EclipseGeocentricBodyState
from moira.lunar_eclipse_global import LunarEclipseShadowState


def _body_state(body: str) -> EclipseGeocentricBodyState:
    return EclipseGeocentricBodyState(
        body=body,
        right_ascension_deg=10.0,
        declination_deg=-5.0,
        distance_km=400_000.0,
        semidiameter_deg=0.25,
        horizontal_parallax_deg=0.9,
        origin="earth_center",
        frame="true_equator_and_equinox_of_date",
        correction_policy="declared test policy",
    )


def test_epoch_requires_scale_consistent_delta_t() -> None:
    epoch = EclipseEpoch(
        jd_tt=2_460_000.5 + 70.0 / 86400.0,
        jd_ut1=2_460_000.5,
        delta_t_seconds=70.0,
        time_policy="test",
    )
    assert epoch.delta_t_seconds == 70.0

    with pytest.raises(ValueError, match="delta_t_seconds"):
        EclipseEpoch(
            jd_tt=2_460_000.5 + 70.0 / 86400.0,
            jd_ut1=2_460_000.5,
            delta_t_seconds=71.0,
            time_policy="test",
        )


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("right_ascension_deg", 360.0),
        ("declination_deg", 90.1),
        ("distance_km", 0.0),
        ("semidiameter_deg", 0.0),
        ("horizontal_parallax_deg", 90.0),
    ],
)
def test_body_state_rejects_invalid_physical_ranges(
    field: str,
    value: float,
) -> None:
    values = {
        "body": Body.MOON,
        "right_ascension_deg": 10.0,
        "declination_deg": -5.0,
        "distance_km": 400_000.0,
        "semidiameter_deg": 0.25,
        "horizontal_parallax_deg": 0.9,
        "origin": "earth_center",
        "frame": "true_equator_and_equinox_of_date",
        "correction_policy": "declared test policy",
    }
    values[field] = value
    with pytest.raises(ValueError):
        EclipseGeocentricBodyState(**values)


def test_shadow_state_requires_gamma_axis_and_radius_consistency() -> None:
    shadow = LunarEclipseShadowState(
        gamma_earth_radii=0.5,
        axis_distance_km=6378.137 * 0.5,
        moon_radius_earth_radii=0.27,
        umbra_radius_earth_radii=0.73,
        penumbra_radius_earth_radii=1.25,
        umbral_magnitude=0.92,
        penumbral_magnitude=1.96,
        shadow_model="test",
    )
    assert shadow.penumbral_magnitude > shadow.umbral_magnitude

    with pytest.raises(ValueError, match="gamma"):
        LunarEclipseShadowState(
            gamma_earth_radii=0.6,
            axis_distance_km=6378.137 * 0.5,
            moon_radius_earth_radii=0.27,
            umbra_radius_earth_radii=0.73,
            penumbra_radius_earth_radii=1.25,
            umbral_magnitude=0.92,
            penumbral_magnitude=1.96,
            shadow_model="test",
        )


def test_body_state_retains_canonical_body_identity() -> None:
    assert _body_state(Body.SUN).body == Body.SUN
    assert _body_state(Body.MOON).body == Body.MOON
