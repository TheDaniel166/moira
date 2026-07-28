from __future__ import annotations

import math

import pytest

from moira.constants import Body
from moira.heliacal import (
    LightPollutionDerivationMode,
    MoonlightPolicy,
    ObserverAid,
    ObserverVisibilityEnvironment,
    VisibilityCriterionFamily,
    VisibilityExtinctionModel,
    VisibilityPolicy,
    VisibilityTwilightModel,
    atmospheric_extinction,
    directional_twilight_sky_brightness,
    point_source_visibility_threshold,
    relative_optical_airmass,
    visibility_assessment,
    visibility_event,
    visual_limiting_magnitude,
)
from moira.heliacal import HeliacalEventKind


def _physical_policy(
    *,
    extinction_model: VisibilityExtinctionModel = (
        VisibilityExtinctionModel.KASTEN_YOUNG_1989_BROADBAND
    ),
    environment: ObserverVisibilityEnvironment | None = None,
    field_factor_includes_atmosphere: bool = True,
) -> VisibilityPolicy:
    return VisibilityPolicy(
        criterion_family=VisibilityCriterionFamily.CRUMEY_2014_POINT_SOURCE,
        extinction_model=extinction_model,
        twilight_model=VisibilityTwilightModel.SCHAEFER_1993_DIRECTIONAL,
        environment=environment,
        light_pollution_derivation_mode=(
            LightPollutionDerivationMode.BORTLE_TABLE
        ),
        crumey_field_factor_includes_atmosphere=(
            field_factor_includes_atmosphere
        ),
    )


@pytest.mark.parametrize(
    ("altitude_deg", "expected"),
    [
        (90.0, 0.9997119919),
        (30.0, 1.9942928525),
        (0.0, 37.9196083778),
    ],
)
def test_kasten_young_1989_relative_optical_airmass_reference_values(
    altitude_deg: float,
    expected: float,
) -> None:
    assert relative_optical_airmass(altitude_deg) == pytest.approx(
        expected,
        rel=2e-10,
    )


def test_airmass_rejects_below_horizon_instead_of_clamping() -> None:
    with pytest.raises(ValueError, match="apparent altitude"):
        relative_optical_airmass(-0.01)


def test_schaefer_component_airmasses_match_table_3_horizon_values() -> None:
    result = atmospheric_extinction(
        0.0,
        model=VisibilityExtinctionModel.SCHAEFER_1993_COMPONENTS,
        observer_altitude_m=0.0,
        relative_humidity=0.5,
        observer_latitude_deg=0.0,
        sun_right_ascension_deg=0.0,
    )

    assert result.rayleigh_airmass == pytest.approx(34.9, abs=0.1)
    assert result.aerosol_airmass == pytest.approx(81.6, abs=0.1)
    assert result.ozone_airmass == pytest.approx(12.7, abs=0.1)
    assert result.sky_brightness_extinction_coefficient == pytest.approx(
        0.1066
        + 0.031 * 2.6 / 3.0
        + 0.12
        * (1.0 - 0.32 / math.log(0.5)) ** (4.0 / 3.0)
    )
    assert (
        result.total_zenith_extinction_coefficient
        != result.sky_brightness_extinction_coefficient
    )
    assert 0.0 < result.transmission_fraction < 1.0


def test_schaefer_components_reproduce_extinction_angle_example() -> None:
    # Schaefer (1993), section 3.17: Medicine Mountain (2940 m,
    # latitude 44.8 N), summer Sun RA 90 degrees, and 50% humidity.
    result = atmospheric_extinction(
        90.0,
        model=VisibilityExtinctionModel.SCHAEFER_1993_COMPONENTS,
        observer_altitude_m=2940.0,
        relative_humidity=0.5,
        observer_latitude_deg=44.8,
        sun_right_ascension_deg=90.0,
    )

    assert result.rayleigh_coefficient_mag_per_airmass == pytest.approx(
        0.101,
        abs=0.001,
    )
    assert result.ozone_coefficient_mag_per_airmass == pytest.approx(
        0.010,
        abs=0.001,
    )
    assert result.aerosol_coefficient_mag_per_airmass == pytest.approx(
        0.041,
        abs=0.001,
    )


def test_measured_broadband_extinction_keeps_declared_coefficient_visible() -> None:
    result = atmospheric_extinction(
        30.0,
        model=VisibilityExtinctionModel.KASTEN_YOUNG_1989_BROADBAND,
        extinction_coefficient_k=0.2,
    )

    assert result.broadband_airmass == pytest.approx(1.9942928525)
    assert result.total_zenith_extinction_coefficient == pytest.approx(0.2)
    assert result.sky_brightness_extinction_coefficient == pytest.approx(0.2)
    assert result.extinction_magnitude == pytest.approx(0.3988585705)
    assert result.rayleigh_airmass is None


def test_schaefer_directional_twilight_reference_evaluation() -> None:
    result = directional_twilight_sky_brightness(
        90.0,
        -12.0,
        90.0,
        extinction_coefficient_k=0.2,
    )

    assert result.valid
    assert result.formula_applied
    assert result.sky_airmass == pytest.approx(0.9999995825)
    assert result.sky_nanolamberts == pytest.approx(751.4833448)


def test_directional_twilight_reports_night_and_day_regimes_explicitly() -> None:
    night = directional_twilight_sky_brightness(
        45.0,
        -19.0,
        90.0,
        extinction_coefficient_k=0.2,
    )
    day = directional_twilight_sky_brightness(
        45.0,
        1.0,
        90.0,
        extinction_coefficient_k=0.2,
    )

    assert night.valid
    assert not night.formula_applied
    assert night.sky_nanolamberts == 0.0
    assert night.reason == "sun_below_astronomical_twilight"
    assert not day.valid
    assert day.sky_nanolamberts is None
    assert day.reason == "sun_above_twilight_model_range"


def test_crumey_2014_eq53_reproduces_representative_example() -> None:
    background_cd_m2 = 2.0e-4
    background_nl = background_cd_m2 * math.pi / 1.0e-5
    result = point_source_visibility_threshold(
        background_nl,
        field_factor=2.0,
    )

    assert result.valid
    assert result.background_luminance_cd_m2 == pytest.approx(background_cd_m2)
    assert result.limiting_magnitude == pytest.approx(6.1818775043)


def test_crumey_threshold_refuses_extrapolation() -> None:
    result = point_source_visibility_threshold(1.0e7)
    assert not result.valid
    assert result.limiting_magnitude is None
    assert result.reason == "background_outside_crumey_2014_range"


def test_physical_policy_rejects_incoherent_or_hidden_inputs() -> None:
    with pytest.raises(ValueError, match="admitted physical extinction"):
        VisibilityPolicy(
            criterion_family=VisibilityCriterionFamily.CRUMEY_2014_POINT_SOURCE,
            twilight_model=VisibilityTwilightModel.SCHAEFER_1993_DIRECTIONAL,
        )
    with pytest.raises(ValueError, match="derives its own limiting magnitude"):
        _physical_policy(
            environment=ObserverVisibilityEnvironment(limiting_magnitude=6.0),
        )
    with pytest.raises(ValueError, match="naked-eye"):
        _physical_policy(
            environment=ObserverVisibilityEnvironment(
                observing_aid=ObserverAid.BINOCULARS,
            ),
        )
    with pytest.raises(ValueError, match="must be bool"):
        VisibilityPolicy(
            crumey_field_factor_includes_atmosphere="yes",  # type: ignore[arg-type]
        )
    with pytest.raises(ValueError, match="BORTLE_TABLE"):
        VisibilityPolicy(
            criterion_family=VisibilityCriterionFamily.CRUMEY_2014_POINT_SOURCE,
            extinction_model=(
                VisibilityExtinctionModel.KASTEN_YOUNG_1989_BROADBAND
            ),
            twilight_model=VisibilityTwilightModel.SCHAEFER_1993_DIRECTIONAL,
        )


@pytest.mark.parametrize(
    ("field_name", "value", "message"),
    [
        ("local_horizon_altitude_deg", math.nan, "local_horizon"),
        ("local_horizon_altitude_deg", 91.0, "local_horizon"),
        ("temperature_c", math.nan, "temperature_c"),
        ("pressure_mbar", math.nan, "pressure_mbar"),
        ("relative_humidity", math.nan, "relative_humidity"),
        ("observer_altitude_m", math.nan, "observer_altitude_m"),
    ],
)
def test_observer_environment_rejects_nonphysical_numeric_inputs(
    field_name: str,
    value: float,
    message: str,
) -> None:
    with pytest.raises(ValueError, match=message):
        ObserverVisibilityEnvironment(**{field_name: value})


def test_visual_limiting_magnitude_rejects_directional_physical_policy() -> None:
    with pytest.raises(ValueError, match="directional"):
        visual_limiting_magnitude(
            2451545.0,
            0.0,
            0.0,
            policy=_physical_policy(),
        )


def test_visual_limiting_magnitude_moonlight_is_zenith_referenced(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "moira.heliacal._ks1991_zenith_limiting_magnitude_penalty",
        lambda *args: -0.75,
    )
    policy = VisibilityPolicy(
        moonlight_policy=MoonlightPolicy.KRISCIUNAS_SCHAEFER_1991,
        environment=ObserverVisibilityEnvironment(limiting_magnitude=6.0),
    )

    assert visual_limiting_magnitude(
        2451545.0,
        0.0,
        0.0,
        policy=policy,
    ) == pytest.approx(5.25)


def test_physical_criterion_is_not_silently_used_by_legacy_event_search() -> None:
    with pytest.raises(ValueError, match="single-epoch"):
        visibility_event(
            Body.VENUS,
            HeliacalEventKind.HELIACAL_RISING,
            2451545.0,
            0.0,
            0.0,
            visibility_policy=_physical_policy(),
        )


def test_physical_visibility_assessment_exposes_complete_derivation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def horizontal(body: str, jd_ut: float, lat: float, lon: float):
        if body == Body.SUN:
            return (0.0, -15.0)
        if body == Body.MOON:
            return (90.0, -20.0)
        return (180.0, 45.0)

    monkeypatch.setattr("moira.heliacal._true_horizontal", horizontal)
    monkeypatch.setattr("moira.heliacal._true_altitude", lambda *args: 45.0)
    monkeypatch.setattr("moira.heliacal._planet_alt", lambda *args, **kwargs: 45.0)
    monkeypatch.setattr(
        "moira.heliacal._target_apparent_magnitude",
        lambda *args: 1.0,
    )
    monkeypatch.setattr(
        "moira.heliacal._target_signed_elongation",
        lambda *args: 30.0,
    )
    monkeypatch.setattr(
        "moira.heliacal.apply_refraction",
        lambda altitude, **kwargs: altitude,
    )
    monkeypatch.setattr(
        "moira.rise_set._body_ra_dec",
        lambda *args, **kwargs: (180.0, 0.0),
    )

    result = visibility_assessment(
        Body.VENUS,
        2451545.0,
        0.0,
        0.0,
        policy=_physical_policy(),
    )

    assert result.criterion_applicable
    assert result.atmospheric_extinction is not None
    assert result.twilight_sky_brightness is not None
    assert result.point_source_threshold is not None
    assert result.point_source_threshold.valid
    assert result.extinction_adjusted_magnitude is not None
    assert result.extinction_adjusted_magnitude > result.apparent_magnitude
    assert result.dark_sky_nanolamberts is not None
    assert result.total_sky_nanolamberts is not None
    assert result.total_sky_nanolamberts > result.dark_sky_nanolamberts
    assert result.visibility_margin_magnitude == pytest.approx(
        result.effective_limiting_magnitude
        - result.apparent_magnitude
    )
    assert result.criterion_target_magnitude == result.apparent_magnitude
    assert not result.target_extinction_applied_separately
    assert result.observable


def test_physical_assessment_can_apply_separately_calibrated_target_extinction(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def horizontal(body: str, jd_ut: float, lat: float, lon: float):
        return (0.0, -19.0) if body == Body.SUN else (180.0, 45.0)

    monkeypatch.setattr("moira.heliacal._true_horizontal", horizontal)
    monkeypatch.setattr("moira.heliacal._true_altitude", lambda *args: 45.0)
    monkeypatch.setattr("moira.heliacal._planet_alt", lambda *args, **kwargs: 45.0)
    monkeypatch.setattr(
        "moira.heliacal._target_apparent_magnitude",
        lambda *args: 1.0,
    )
    monkeypatch.setattr(
        "moira.heliacal._target_signed_elongation",
        lambda *args: 30.0,
    )
    monkeypatch.setattr(
        "moira.rise_set._body_ra_dec",
        lambda *args, **kwargs: (180.0, 0.0),
    )

    result = visibility_assessment(
        Body.VENUS,
        2451545.0,
        0.0,
        0.0,
        policy=_physical_policy(field_factor_includes_atmosphere=False),
    )

    assert result.extinction_adjusted_magnitude is not None
    assert result.criterion_target_magnitude == pytest.approx(
        result.extinction_adjusted_magnitude
    )
    assert result.target_extinction_applied_separately


def test_physical_visibility_assessment_marks_daylight_outside_model(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def horizontal(body: str, jd_ut: float, lat: float, lon: float):
        return (0.0, 10.0) if body == Body.SUN else (180.0, 45.0)

    monkeypatch.setattr("moira.heliacal._true_horizontal", horizontal)
    monkeypatch.setattr("moira.heliacal._true_altitude", lambda *args: 45.0)
    monkeypatch.setattr("moira.heliacal._planet_alt", lambda *args, **kwargs: 45.0)
    monkeypatch.setattr(
        "moira.heliacal._target_apparent_magnitude",
        lambda *args: 1.0,
    )
    monkeypatch.setattr(
        "moira.heliacal._target_signed_elongation",
        lambda *args: 30.0,
    )
    monkeypatch.setattr(
        "moira.heliacal.apply_refraction",
        lambda altitude, **kwargs: altitude,
    )
    monkeypatch.setattr(
        "moira.rise_set._body_ra_dec",
        lambda *args, **kwargs: (180.0, 0.0),
    )

    result = visibility_assessment(
        Body.VENUS,
        2451545.0,
        0.0,
        0.0,
        policy=_physical_policy(),
    )

    assert not result.criterion_applicable
    assert result.criterion_reason == "sun_above_twilight_model_range"
    assert result.effective_limiting_magnitude is None
    assert not result.observable
