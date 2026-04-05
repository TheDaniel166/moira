from __future__ import annotations

from types import SimpleNamespace

import pytest

from moira.constants import Body
from moira.heliacal import (
    GeneralVisibilityEvent,
    HeliacalEventKind,
    HeliacalPolicy,
    LightPollutionClass,
    LightPollutionDerivationMode,
    LunarCrescentDetails,
    LunarCrescentVisibilityClass,
    MoonlightPolicy,
    ObserverAid,
    ObserverVisibilityEnvironment,
    VisibilityAssessment,
    VisibilityCriterionFamily,
    VisibilityExtinctionModel,
    VisibilityModel,
    VisibilityPolicy,
    VisibilitySearchPolicy,
    VisibilityTargetKind,
    VisibilityTwilightModel,
    _effective_limiting_magnitude,
    _effective_visibility_model,
    _ks1991_moon_magnitude,
    _ks1991_scattering_function,
    _ks1991_moonlight_nanolamberts,
    _ks1991_dark_sky_nanolamberts,
    planet_heliacal_rising,
    visibility_assessment,
    visibility_event,
)
import moira.heliacal as heliacal_module


def test_visibility_policy_defaults_to_limit_mag_threshold_family() -> None:
    policy = VisibilityPolicy()
    assert policy.criterion_family is VisibilityCriterionFamily.LIMITING_MAGNITUDE_THRESHOLD
    assert policy.extinction_model is VisibilityExtinctionModel.LEGACY_ARCUS_VISIONIS
    assert policy.twilight_model is VisibilityTwilightModel.ARCUS_VISIONIS_SOLAR_DEPRESSION
    assert policy.moonlight_policy is MoonlightPolicy.IGNORE


def test_yallop_policy_is_lunar_only_in_direct_assessment() -> None:
    with pytest.raises(ValueError, match="defined only for the Moon"):
        visibility_assessment(
            Body.VENUS,
            2451545.0,
            0.0,
            0.0,
            policy=VisibilityPolicy(
                criterion_family=VisibilityCriterionFamily.YALLOP_LUNAR_CRESCENT,
            ),
        )


def test_linear_bortle_mapping_is_explicit_and_monotonic() -> None:
    dark = VisibilityPolicy(
        environment=ObserverVisibilityEnvironment(light_pollution_class=LightPollutionClass.BORTLE_1),
        light_pollution_derivation_mode=LightPollutionDerivationMode.BORTLE_LINEAR,
    )
    bright = VisibilityPolicy(
        environment=ObserverVisibilityEnvironment(light_pollution_class=LightPollutionClass.BORTLE_9),
        light_pollution_derivation_mode=LightPollutionDerivationMode.BORTLE_LINEAR,
    )
    assert _effective_limiting_magnitude(dark) == pytest.approx(7.6)
    assert _effective_limiting_magnitude(bright) == pytest.approx(3.6)
    assert _effective_limiting_magnitude(dark) > _effective_limiting_magnitude(bright)


def test_table_bortle_mapping_matches_declared_policy_values() -> None:
    policy = VisibilityPolicy(
        environment=ObserverVisibilityEnvironment(light_pollution_class=LightPollutionClass.BORTLE_5),
        light_pollution_derivation_mode=LightPollutionDerivationMode.BORTLE_TABLE,
    )
    assert _effective_limiting_magnitude(policy) == pytest.approx(5.6)


def test_explicit_limiting_magnitude_overrides_light_pollution_derivation() -> None:
    policy = VisibilityPolicy(
        environment=ObserverVisibilityEnvironment(
            light_pollution_class=LightPollutionClass.BORTLE_9,
            limiting_magnitude=6.2,
        ),
    )
    assert _effective_limiting_magnitude(policy) == pytest.approx(6.2)


def test_visibility_model_can_adapt_into_observer_environment() -> None:
    model = VisibilityModel(
        limiting_magnitude=5.4,
        horizon_altitude_deg=2.5,
        pressure_mbar=900.0,
    )
    environment = model.to_observer_environment(
        light_pollution_class=LightPollutionClass.BORTLE_6,
        observing_aid=ObserverAid.BINOCULARS,
    )
    assert environment.limiting_magnitude == pytest.approx(5.4)
    assert environment.local_horizon_altitude_deg == pytest.approx(2.5)
    assert environment.observing_aid is ObserverAid.BINOCULARS


def test_heliacal_policy_default_builds_visibility_policy() -> None:
    policy = HeliacalPolicy.default()
    assert policy.visibility_policy is not None
    assert policy.visibility_policy.environment is not None
    assert policy.visibility_policy.environment.observing_aid is ObserverAid.NAKED_EYE


def test_effective_visibility_model_prefers_new_environment_horizon_and_threshold() -> None:
    policy = HeliacalPolicy(
        visibility_model=VisibilityModel(
            limiting_magnitude=6.5,
            horizon_altitude_deg=0.0,
            extinction_coefficient=0.3,
        ),
        visibility_policy=VisibilityPolicy(
            environment=ObserverVisibilityEnvironment(
                light_pollution_class=LightPollutionClass.BORTLE_8,
                limiting_magnitude=4.4,
                local_horizon_altitude_deg=3.0,
                pressure_mbar=880.0,
                temperature_c=5.0,
            )
        ),
    )
    effective = _effective_visibility_model(policy)
    assert effective.limiting_magnitude == pytest.approx(4.4)
    assert effective.horizon_altitude_deg == pytest.approx(3.0)
    assert effective.extinction_coefficient == pytest.approx(0.3)
    assert effective.pressure_mbar == pytest.approx(880.0)
    assert effective.temperature_c == pytest.approx(5.0)


def test_observer_environment_rejects_invalid_humidity() -> None:
    with pytest.raises(ValueError, match="relative_humidity"):
        ObserverVisibilityEnvironment(relative_humidity=1.5)


def test_visibility_search_policy_rejects_non_positive_window() -> None:
    with pytest.raises(ValueError, match="search_window_days"):
        VisibilitySearchPolicy(search_window_days=0)


def test_visibility_event_returns_generalized_lunar_event_with_yallop(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "moira.heliacal._lunar_crescent_details_for_evening",
        lambda *args, **kwargs: LunarCrescentDetails(
            best_time_jd_ut=2451545.25,
            sunset_jd_ut=2451545.15,
            moonset_jd_ut=2451545.35,
            lag_minutes=144.0,
            arcl_deg=12.0,
            arcv_deg=8.0,
            daz_deg=5.0,
            moon_altitude_deg=7.5,
            sun_altitude_deg=-4.0,
            lunar_parallax_arcmin=57.0,
            topocentric_crescent_width_arcmin=0.4,
            q=0.3,
            visibility_class=LunarCrescentVisibilityClass.A,
        ),
    )
    monkeypatch.setattr("moira.heliacal._target_signed_elongation", lambda *args, **kwargs: 12.0)

    event = visibility_event(
        Body.MOON,
        HeliacalEventKind.ACRONYCHAL_RISING,
        2451545.0,
        0.0,
        0.0,
        visibility_policy=VisibilityPolicy(
            criterion_family=VisibilityCriterionFamily.YALLOP_LUNAR_CRESCENT,
        ),
    )
    assert isinstance(event, GeneralVisibilityEvent)
    assert event is not None
    assert event.target_kind is VisibilityTargetKind.MOON
    assert event.kind is HeliacalEventKind.ACRONYCHAL_RISING
    assert event.lunar_crescent_details is not None
    assert event.lunar_crescent_details.visibility_class is LunarCrescentVisibilityClass.A
    assert event.assessment.criterion_family is VisibilityCriterionFamily.YALLOP_LUNAR_CRESCENT


def test_yallop_lunar_family_rejects_morning_event_kinds() -> None:
    with pytest.raises(NotImplementedError, match="evening first-sighting"):
        visibility_event(
            Body.MOON,
            HeliacalEventKind.HELIACAL_RISING,
            2451545.0,
            0.0,
            0.0,
            visibility_policy=VisibilityPolicy(
                criterion_family=VisibilityCriterionFamily.YALLOP_LUNAR_CRESCENT,
            ),
        )


def test_yallop_visibility_class_thresholds_follow_declared_boundaries() -> None:
    assert heliacal_module._yallop_visibility_class(0.300) is LunarCrescentVisibilityClass.A
    assert heliacal_module._yallop_visibility_class(0.216) is LunarCrescentVisibilityClass.B
    assert heliacal_module._yallop_visibility_class(-0.014) is LunarCrescentVisibilityClass.C
    assert heliacal_module._yallop_visibility_class(-0.160) is LunarCrescentVisibilityClass.D
    assert heliacal_module._yallop_visibility_class(-0.232) is LunarCrescentVisibilityClass.E
    assert heliacal_module._yallop_visibility_class(-0.293) is LunarCrescentVisibilityClass.F


def test_yallop_observability_depends_on_aid_and_class() -> None:
    assert heliacal_module._yallop_class_observable(
        LunarCrescentVisibilityClass.A,
        ObserverAid.NAKED_EYE,
    ) is True
    assert heliacal_module._yallop_class_observable(
        LunarCrescentVisibilityClass.C,
        ObserverAid.NAKED_EYE,
    ) is False
    assert heliacal_module._yallop_class_observable(
        LunarCrescentVisibilityClass.C,
        ObserverAid.BINOCULARS,
    ) is True
    assert heliacal_module._yallop_class_observable(
        LunarCrescentVisibilityClass.E,
        ObserverAid.TELESCOPE,
    ) is False


def test_visibility_event_returns_generalized_stellar_event(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "moira.stars.heliacal_rising_event",
        lambda *args, **kwargs: SimpleNamespace(
            is_found=True,
            jd_ut=2451545.25,
            computation_truth=SimpleNamespace(qualifying_sun_altitude=-10.0),
        ),
    )
    monkeypatch.setattr(
        "moira.heliacal.visibility_assessment",
        lambda *args, **kwargs: VisibilityAssessment(
            body="Sirius",
            jd_ut=2451545.25,
            criterion_family=VisibilityCriterionFamily.LIMITING_MAGNITUDE_THRESHOLD,
            effective_limiting_magnitude=6.5,
            apparent_magnitude=-1.46,
            true_altitude_deg=7.0,
            apparent_altitude_deg=7.5,
            local_horizon_altitude_deg=0.0,
            solar_elongation_deg=-14.0,
            is_geometrically_visible=True,
            is_bright_enough=True,
            observable=True,
        ),
    )
    monkeypatch.setattr("moira.heliacal._target_signed_elongation", lambda *args, **kwargs: -14.0)

    event = visibility_event(
        "Sirius",
        HeliacalEventKind.HELIACAL_RISING,
        2451545.0,
        31.2,
        29.9,
    )
    assert isinstance(event, GeneralVisibilityEvent)
    assert event is not None
    assert event.target_kind is VisibilityTargetKind.STAR
    assert event.kind is HeliacalEventKind.HELIACAL_RISING
    assert event.sun_altitude_deg == pytest.approx(-10.0)


def test_visibility_event_returns_generalized_cosmic_event(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "moira.heliacal._check_visibility_with_target_alt",
        lambda *args, **kwargs: (2451545.25, 5.0, -18.0, -4.0),
    )
    monkeypatch.setattr("moira.heliacal._signed_elongation", lambda *args, **kwargs: -15.0)
    monkeypatch.setattr(
        "moira.heliacal.visibility_assessment",
        lambda *args, **kwargs: VisibilityAssessment(
            body=Body.VENUS,
            jd_ut=2451545.25,
            criterion_family=VisibilityCriterionFamily.LIMITING_MAGNITUDE_THRESHOLD,
            effective_limiting_magnitude=6.5,
            apparent_magnitude=-4.0,
            true_altitude_deg=4.5,
            apparent_altitude_deg=5.0,
            local_horizon_altitude_deg=0.0,
            solar_elongation_deg=-15.0,
            is_geometrically_visible=True,
            is_bright_enough=True,
            observable=True,
        ),
    )

    event = visibility_event(
        Body.VENUS,
        HeliacalEventKind.COSMIC_RISING,
        2451545.0,
        0.0,
        0.0,
    )
    assert isinstance(event, GeneralVisibilityEvent)
    assert event is not None
    assert event.target_kind is VisibilityTargetKind.PLANET
    assert event.kind is HeliacalEventKind.COSMIC_RISING
    assert event.sun_altitude_deg == pytest.approx(-18.0)


@pytest.mark.requires_ephemeris
def test_visibility_assessment_returns_typed_result() -> None:
    result = visibility_assessment(
        Body.VENUS,
        2451545.0,
        0.0,
        0.0,
        policy=VisibilityPolicy(
            environment=ObserverVisibilityEnvironment(
                limiting_magnitude=-30.0,
                local_horizon_altitude_deg=-90.0,
            )
        ),
    )
    assert isinstance(result, VisibilityAssessment)
    assert result.criterion_family is VisibilityCriterionFamily.LIMITING_MAGNITUDE_THRESHOLD


@pytest.mark.requires_ephemeris
def test_visibility_assessment_uses_explicit_limiting_magnitude_override() -> None:
    result = visibility_assessment(
        Body.VENUS,
        2451545.0,
        0.0,
        0.0,
        policy=VisibilityPolicy(
            environment=ObserverVisibilityEnvironment(
                light_pollution_class=LightPollutionClass.BORTLE_9,
                limiting_magnitude=-30.0,
                local_horizon_altitude_deg=-90.0,
            )
        ),
    )
    assert result.effective_limiting_magnitude == pytest.approx(-30.0)


@pytest.mark.requires_ephemeris
def test_visibility_assessment_local_horizon_can_block_geometry() -> None:
    result = visibility_assessment(
        Body.VENUS,
        2451545.0,
        0.0,
        0.0,
        policy=VisibilityPolicy(
            environment=ObserverVisibilityEnvironment(
                limiting_magnitude=-30.0,
                local_horizon_altitude_deg=90.0,
            )
        ),
    )
    assert result.is_geometrically_visible is False
    assert result.observable is False


@pytest.mark.requires_ephemeris
def test_visibility_assessment_can_disable_refraction() -> None:
    with_refraction = visibility_assessment(
        Body.VENUS,
        2451545.0,
        0.0,
        0.0,
        policy=VisibilityPolicy(
            environment=ObserverVisibilityEnvironment(
                limiting_magnitude=-30.0,
                local_horizon_altitude_deg=-90.0,
            ),
            use_refraction=True,
        ),
    )
    without_refraction = visibility_assessment(
        Body.VENUS,
        2451545.0,
        0.0,
        0.0,
        policy=VisibilityPolicy(
            environment=ObserverVisibilityEnvironment(
                limiting_magnitude=-30.0,
                local_horizon_altitude_deg=-90.0,
            ),
            use_refraction=False,
        ),
    )
    assert with_refraction.apparent_altitude_deg != pytest.approx(without_refraction.apparent_altitude_deg)
    assert without_refraction.apparent_altitude_deg == pytest.approx(without_refraction.true_altitude_deg)


@pytest.mark.requires_ephemeris
def test_visibility_event_returns_generalized_planetary_event() -> None:
    event = visibility_event(
        Body.VENUS,
        HeliacalEventKind.HELIACAL_RISING,
        2458994.5,
        35.0,
        35.0,
    )
    assert isinstance(event, GeneralVisibilityEvent)
    assert event is not None
    assert event.target_kind is VisibilityTargetKind.PLANET
    assert event.kind is HeliacalEventKind.HELIACAL_RISING
    assert event.assessment.body == Body.VENUS
    assert event.assessment.observable is True


@pytest.mark.requires_ephemeris
def test_visibility_event_matches_legacy_planetary_wrapper() -> None:
    general = visibility_event(
        Body.VENUS,
        HeliacalEventKind.HELIACAL_RISING,
        2458994.5,
        35.0,
        35.0,
    )
    legacy = planet_heliacal_rising(
        Body.VENUS,
        2458994.5,
        35.0,
        35.0,
    )
    assert general is not None
    assert legacy is not None
    assert general.jd_ut == pytest.approx(legacy.jd_ut)
    assert general.elongation_deg == pytest.approx(legacy.elongation_deg)
    assert general.target_altitude_deg == pytest.approx(legacy.planet_altitude_deg)
    assert general.sun_altitude_deg == pytest.approx(legacy.sun_altitude_deg)
    assert general.apparent_magnitude == pytest.approx(legacy.apparent_magnitude)


# ---------------------------------------------------------------------------
# Krisciunas & Schaefer (1991) moonlight model — unit tests
# Authority: Krisciunas & Schaefer (1991), PASP 103, 1033-1039.
# ---------------------------------------------------------------------------

def test_ks1991_moon_magnitude_full_moon() -> None:
    # At phase angle 0 (full moon), Eq. 9 gives exactly -12.73
    result = _ks1991_moon_magnitude(0.0)
    assert result == pytest.approx(-12.73, abs=1e-9)


def test_ks1991_moon_magnitude_new_moon() -> None:
    # At phase angle 180 (new moon), magnitude is large positive
    result = _ks1991_moon_magnitude(180.0)
    # -12.73 + 0.026 * 180 + 4e-9 * 180^4
    # = -12.73 + 4.68 + 4e-9 * 1.0497e9 = -12.73 + 4.68 + 4.199 = -3.851
    assert result == pytest.approx(-12.73 + 0.026 * 180 + 4e-9 * 180**4, rel=1e-9)


def test_ks1991_moon_magnitude_is_symmetric_in_phase_angle() -> None:
    # K&S Eq.9 uses |alpha|, so +90 and -90 give same result
    assert _ks1991_moon_magnitude(90.0) == pytest.approx(_ks1991_moon_magnitude(-90.0))


def test_ks1991_moon_magnitude_monotone_full_to_new() -> None:
    # As phase angle increases from 0 to 180, the Moon gets fainter (larger magnitude)
    mags = [_ks1991_moon_magnitude(a) for a in range(0, 181, 10)]
    assert all(m1 <= m2 for m1, m2 in zip(mags, mags[1:]))


def test_ks1991_scattering_function_is_clamped_below_10_deg() -> None:
    # rho < 10 should be clamped to 10
    at_10 = _ks1991_scattering_function(10.0)
    at_5 = _ks1991_scattering_function(5.0)
    at_0 = _ks1991_scattering_function(0.0)
    assert at_5 == pytest.approx(at_10)
    assert at_0 == pytest.approx(at_10)


def test_ks1991_scattering_function_has_minimum_near_90_degrees() -> None:
    # The K&S 1991 scattering function f(rho) is NOT monotone.
    # It has a forward-scattering peak near rho=0 (from cos^2 and from the 10^(6.15-rho/40) term)
    # and a back-scattering peak near rho=180 (from cos^2(180)=1, same as cos^2(0)=1).
    # The function reaches a local minimum around rho=90 degrees.
    f_at_30 = _ks1991_scattering_function(30.0)
    f_at_90 = _ks1991_scattering_function(90.0)
    f_at_150 = _ks1991_scattering_function(150.0)
    # 90 degrees should be less than both 30 and 150
    assert f_at_90 < f_at_30
    assert f_at_90 < f_at_150


def test_ks1991_scattering_function_spot_check() -> None:
    # Spot-check at rho=90 against the formula directly:
    # f(90) = 10^5.36 * (1.06 + cos^2(90)) + 10^(6.15 - 90/40)
    #       = 10^5.36 * (1.06 + 0) + 10^(6.15 - 2.25)
    #       = 229087 * 1.06 + 10^3.9
    #       = 242832.2 + 7943.3 = 250775.5
    import math as _math
    expected = 10**5.36 * (1.06 + _math.cos(_math.radians(90.0))**2) + 10**(6.15 - 90.0/40.0)
    assert _ks1991_scattering_function(90.0) == pytest.approx(expected, rel=1e-9)


def test_ks1991_moonlight_zero_when_moon_below_horizon() -> None:
    result = _ks1991_moonlight_nanolamberts(
        rho_deg=45.0,
        alt_moon_deg=-5.0,   # below horizon
        phase_angle_deg=0.0,
        extinction_k=0.172,
        alt_target_deg=30.0,
    )
    assert result == 0.0


def test_ks1991_moonlight_zero_when_target_below_horizon() -> None:
    result = _ks1991_moonlight_nanolamberts(
        rho_deg=45.0,
        alt_moon_deg=30.0,
        phase_angle_deg=0.0,
        extinction_k=0.172,
        alt_target_deg=-2.0,  # below horizon
    )
    assert result == 0.0


def test_ks1991_moonlight_full_moon_brighter_than_quarter() -> None:
    # Full moon (phase_angle=0) should produce more sky glow than quarter moon (phase_angle=90)
    common = dict(rho_deg=45.0, alt_moon_deg=45.0, extinction_k=0.172, alt_target_deg=45.0)
    b_full = _ks1991_moonlight_nanolamberts(phase_angle_deg=0.0, **common)
    b_quarter = _ks1991_moonlight_nanolamberts(phase_angle_deg=90.0, **common)
    assert b_full > b_quarter > 0.0


def test_ks1991_moonlight_greater_near_moon_than_far() -> None:
    # Sky closer to the Moon (smaller rho) should be brighter
    common = dict(alt_moon_deg=45.0, phase_angle_deg=0.0, extinction_k=0.172, alt_target_deg=45.0)
    b_near = _ks1991_moonlight_nanolamberts(rho_deg=15.0, **common)
    b_far = _ks1991_moonlight_nanolamberts(rho_deg=90.0, **common)
    assert b_near > b_far


def test_ks1991_dark_sky_nanolamberts_bortle1_darker_than_bortle9() -> None:
    policy_dark = VisibilityPolicy(
        environment=ObserverVisibilityEnvironment(light_pollution_class=LightPollutionClass.BORTLE_1),
    )
    policy_bright = VisibilityPolicy(
        environment=ObserverVisibilityEnvironment(light_pollution_class=LightPollutionClass.BORTLE_9),
    )
    b_dark = _ks1991_dark_sky_nanolamberts(policy_dark)
    b_bright = _ks1991_dark_sky_nanolamberts(policy_bright)
    # Darker sky = lower nanolamberts
    assert b_dark < b_bright


def test_ks1991_dark_sky_nanolamberts_bortle3_reference() -> None:
    # Bortle 3: SQM = 21.25 mag/arcsec²
    # B_nL = 34.08 * 10^((21.572 - 21.25) / 2.5) = 34.08 * 10^0.1288
    import math as _math
    expected = 34.08 * 10.0**((21.572 - 21.25) / 2.5)
    policy = VisibilityPolicy(
        environment=ObserverVisibilityEnvironment(light_pollution_class=LightPollutionClass.BORTLE_3),
    )
    assert _ks1991_dark_sky_nanolamberts(policy) == pytest.approx(expected, rel=1e-9)


def test_moonlight_policy_enum_admits_ks1991() -> None:
    policy = VisibilityPolicy(moonlight_policy=MoonlightPolicy.KRISCIUNAS_SCHAEFER_1991)
    assert policy.moonlight_policy is MoonlightPolicy.KRISCIUNAS_SCHAEFER_1991


def test_visibility_assessment_ks1991_reduces_limiting_magnitude_under_bright_moon(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # When the Moon is full and overhead, KS1991 should reduce effective limiting magnitude.
    # We monkeypatch the horizontal-position helpers to place the Moon directly overhead
    # and the target 45 degrees away.
    import math as _math

    def _mock_true_horizontal(body: str, jd_ut: float, lat: float, lon: float):
        if body == "Moon":
            return (0.0, 80.0)    # Moon near zenith
        return (45.0, 40.0)       # target 45 deg in azimuth, 40 deg altitude

    def _mock_true_altitude(body: str, jd_ut: float, lat: float, lon: float):
        if body == "Moon":
            return 80.0
        return 40.0

    def _mock_phase_angle(body_name: str, jd_ut: float) -> float:
        return 0.0  # full moon

    monkeypatch.setattr("moira.heliacal._true_horizontal", _mock_true_horizontal)
    monkeypatch.setattr("moira.heliacal._true_altitude", _mock_true_altitude)
    monkeypatch.setattr("moira.heliacal._planet_alt", lambda *a, **kw: 40.0)
    monkeypatch.setattr("moira.heliacal._target_apparent_magnitude", lambda *a, **kw: 5.0)

    import moira.heliacal as _h
    original_penalty = _h._ks1991_limiting_magnitude_penalty
    def _mock_penalty(policy, jd_ut, lat, lon, body):
        # Call with the mocked horizontal helper so the calculation runs
        from moira.heliacal import (
            _ks1991_moonlight_nanolamberts, _ks1991_dark_sky_nanolamberts,
        )
        import math
        moon_az, moon_alt = _mock_true_horizontal("Moon", jd_ut, lat, lon)
        tgt_az, tgt_alt = _mock_true_horizontal(body, jd_ut, lat, lon)
        moon_phase = 0.0  # full moon
        cos_rho = (
            math.sin(math.radians(moon_alt)) * math.sin(math.radians(tgt_alt))
            + math.cos(math.radians(moon_alt)) * math.cos(math.radians(tgt_alt))
            * math.cos(math.radians(moon_az - tgt_az))
        )
        rho_deg = math.degrees(math.acos(max(-1.0, min(1.0, cos_rho))))
        b_moon = _ks1991_moonlight_nanolamberts(rho_deg, moon_alt, moon_phase, 0.172, tgt_alt)
        b_dark = _ks1991_dark_sky_nanolamberts(policy)
        if b_moon <= 0.0:
            return 0.0
        return -2.5 * math.log10(1.0 + b_moon / b_dark)
    monkeypatch.setattr("moira.heliacal._ks1991_limiting_magnitude_penalty", _mock_penalty)

    policy_ignore = VisibilityPolicy(
        moonlight_policy=MoonlightPolicy.IGNORE,
        environment=ObserverVisibilityEnvironment(light_pollution_class=LightPollutionClass.BORTLE_3),
    )
    policy_ks = VisibilityPolicy(
        moonlight_policy=MoonlightPolicy.KRISCIUNAS_SCHAEFER_1991,
        environment=ObserverVisibilityEnvironment(light_pollution_class=LightPollutionClass.BORTLE_3),
    )

    result_ignore = visibility_assessment(Body.VENUS, 2451545.0, 35.0, 35.0, policy=policy_ignore)
    result_ks = visibility_assessment(Body.VENUS, 2451545.0, 35.0, 35.0, policy=policy_ks)

    # KS1991 should give a LOWER effective limiting magnitude than IGNORE (moonlit sky is brighter)
    assert result_ks.effective_limiting_magnitude < result_ignore.effective_limiting_magnitude
    # And the moonlight field should be populated
    assert result_ks.moonlight_sky_nanolamberts is not None
    # IGNORE should leave the field None
    assert result_ignore.moonlight_sky_nanolamberts is None


def test_visibility_assessment_ks1991_no_penalty_when_moon_below_horizon(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # When the Moon is below the horizon, penalty must be zero and limiting magnitude unchanged.
    monkeypatch.setattr(
        "moira.heliacal._true_horizontal",
        lambda body, jd_ut, lat, lon: (0.0, -10.0),  # everything below horizon
    )
    monkeypatch.setattr(
        "moira.heliacal._true_altitude",
        lambda body, jd_ut, lat, lon: -10.0,
    )
    monkeypatch.setattr("moira.heliacal._planet_alt", lambda *a, **kw: -10.0)
    monkeypatch.setattr("moira.heliacal._target_apparent_magnitude", lambda *a, **kw: 5.0)

    policy_ignore = VisibilityPolicy(
        moonlight_policy=MoonlightPolicy.IGNORE,
        environment=ObserverVisibilityEnvironment(light_pollution_class=LightPollutionClass.BORTLE_3),
    )
    policy_ks = VisibilityPolicy(
        moonlight_policy=MoonlightPolicy.KRISCIUNAS_SCHAEFER_1991,
        environment=ObserverVisibilityEnvironment(light_pollution_class=LightPollutionClass.BORTLE_3),
    )

    result_ignore = visibility_assessment(Body.VENUS, 2451545.0, 35.0, 35.0, policy=policy_ignore)
    result_ks = visibility_assessment(Body.VENUS, 2451545.0, 35.0, 35.0, policy=policy_ks)

    assert result_ks.effective_limiting_magnitude == pytest.approx(result_ignore.effective_limiting_magnitude)
    assert result_ks.moonlight_sky_nanolamberts is None
