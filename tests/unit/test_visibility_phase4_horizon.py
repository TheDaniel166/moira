"""Phase 4 directional-horizon contract and fail-closed validation."""

from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path
from types import SimpleNamespace

import pytest

import moira.heliacal as heliacal
from moira._visibility_lut import (
    VisibilityDataPackConfig,
    VisibilityDataPackDomain,
)
from moira.constants import Body
from moira.heliacal import (
    PhysicalBackgroundScope,
    PhysicalDirectionalBackground,
    PhysicalHorizonProfile,
    PhysicalHorizonSample,
    PhysicalVisibilityEvidenceState,
    PhysicalVisibilityPolicy,
    PhysicalVisibilityStatus,
    physical_visibility_assessment,
)


_SHA = "a" * 64
_CERTIFICATE_PATH = (
    Path(__file__).resolve().parents[2]
    / "scripts"
    / "visibility_reference_lab"
    / "phase4_directional_horizon_certificate.json"
)


def _flat_profile(
    altitude_deg: float = 5.0,
) -> PhysicalHorizonProfile:
    return PhysicalHorizonProfile(
        samples=tuple(
            PhysicalHorizonSample(float(azimuth), altitude_deg)
            for azimuth in range(0, 360, 10)
        ),
        profile_id="test-terrain-horizon-v1",
        source_id="test-survey",
        source_receipt_sha256=_SHA,
    )


def _background() -> PhysicalDirectionalBackground:
    return PhysicalDirectionalBackground(
        photopic_luminance_cd_m2=1.0e-4,
        scotopic_luminance_cd_m2=1.5e-4,
        scope=PhysicalBackgroundScope.TOTAL_BACKGROUND,
        component_ids=("measured_total_night_sky",),
        source_id="test-background",
        source_receipt_sha256=_SHA,
        method_id="test-directional-luminance",
    )


def test_horizon_sample_normalizes_modulo_rounding_to_zero() -> None:
    assert PhysicalHorizonSample(360.0, 0.0).azimuth_deg == 0.0
    assert PhysicalHorizonSample(-1.0e-20, 0.0).azimuth_deg == 0.0
    with pytest.raises(ValueError, match=r"\[-5, 90\)"):
        PhysicalHorizonSample(0.0, 90.0)


def test_directional_horizon_certificate_is_immutable_and_source_bound(
) -> None:
    payload = _CERTIFICATE_PATH.read_bytes()
    certificate = json.loads(payload)

    assert hashlib.sha256(payload).hexdigest() == (
        heliacal._PHYSICAL_DIRECTIONAL_HORIZON_CERTIFICATE_SHA256
    )
    assert certificate["certificate_id"] == (
        "physical-heliacal-event-directional-horizon-lipschitz-v1"
    )
    assert certificate["profile_contract"][
        "interpolation_method_id"
    ] == "circular_linear_azimuth_v1"
    assert certificate["rate_derivation"][
        "directional_signal"
    ] == "g = z - r*tan(H(theta))"
    assert certificate["rate_derivation"][
        "combined_signal_rate_ceiling_per_day"
    ] == "radians(1024)*(1+K)"
    assert certificate["rate_derivation"][
        "zenith_law"
    ] == "at r=0, g=z and is independent of undefined azimuth"


def test_horizon_profile_interpolates_across_north_wrap() -> None:
    samples = [
        PhysicalHorizonSample(float(azimuth), 0.0)
        for azimuth in range(0, 360, 10)
    ]
    samples[-1] = PhysicalHorizonSample(350.0, 10.0)
    profile = PhysicalHorizonProfile(
        samples=tuple(samples),
        profile_id="north-wrap-v1",
        source_id="test-survey",
        source_receipt_sha256=_SHA,
    )

    assert profile.apparent_altitude_at(355.0) == pytest.approx(5.0)
    assert profile.apparent_altitude_at(-5.0) == pytest.approx(5.0)
    assert profile.actual_maximum_gap_deg == 10.0
    assert profile.maximum_absolute_slope_deg_per_deg == 1.0
    assert math.isfinite(profile.cone_signal_lipschitz_factor)


@pytest.mark.parametrize(
    ("apparent_altitude_deg", "horizon_altitude_deg"),
    (
        (-2.0, 0.0),
        (0.0, 0.0),
        (5.0, 2.0),
        (45.0, 30.0),
        (89.0, 80.0),
    ),
)
def test_cone_signal_preserves_altitude_minus_horizon_sign(
    apparent_altitude_deg: float,
    horizon_altitude_deg: float,
) -> None:
    signal = heliacal._physical_directional_horizon_signal(
        apparent_altitude_deg,
        horizon_altitude_deg,
    )
    expected_difference = (
        apparent_altitude_deg - horizon_altitude_deg
    )
    assert (signal > 0.0) == (expected_difference > 0.0)
    assert (signal < 0.0) == (expected_difference < 0.0)


def test_cone_signal_is_azimuth_independent_at_zenith() -> None:
    signals = tuple(
        heliacal._physical_directional_horizon_signal(90.0, horizon)
        for horizon in (-5.0, 0.0, 45.0, 89.0)
    )
    assert signals == pytest.approx((1.0, 1.0, 1.0, 1.0))


def test_horizon_profile_rejects_duplicate_normalized_azimuths() -> None:
    samples = tuple(
        PhysicalHorizonSample(float(azimuth), 0.0)
        for azimuth in range(0, 361, 10)
    )
    with pytest.raises(
        ValueError,
        match="duplicate normalized azimuths",
    ):
        PhysicalHorizonProfile(
            samples=samples,
            profile_id="duplicate-v1",
            source_id="test-survey",
            source_receipt_sha256=_SHA,
        )


def test_horizon_profile_rejects_missing_circular_coverage() -> None:
    samples = tuple(
        PhysicalHorizonSample(float(azimuth), 0.0)
        for azimuth in range(0, 350, 10)
    )
    with pytest.raises(
        ValueError,
        match="gap larger than 10 degrees",
    ):
        PhysicalHorizonProfile(
            samples=samples,
            profile_id="missing-sector-v1",
            source_id="test-survey",
            source_receipt_sha256=_SHA,
        )


def test_policy_rejects_competing_scalar_and_directional_horizons() -> None:
    with pytest.raises(
        ValueError,
        match="cannot be combined",
    ):
        PhysicalVisibilityPolicy(
            local_horizon_altitude_deg=1.0,
            directional_horizon=_flat_profile(),
        )


def test_single_epoch_assessment_uses_profile_at_target_azimuth(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    domain = VisibilityDataPackDomain(
        atmosphere_profile="us_standard",
        aerosol_profile="rural_summer",
        observer_altitude_m=0.0,
        surface_pressure_hpa=1013.25,
        aod550=0.1,
        angstrom_exponent=1.3,
        ozone_du=300.0,
        ground_albedo=0.2,
        solar_center_altitude_deg=(-18.0, 0.0),
        target_true_altitude_deg=(0.25, 45.0),
        relative_solar_azimuth_deg=(0.0, 180.0),
        refraction="bennett_extended_v1",
        outside_domain="fail_closed",
        no_extrapolation=True,
    )
    receipt = SimpleNamespace(
        pack_id="moira-physical-heliacal-visibility",
        version="1.2.0",
        composite_model_id="clear_sky_naked_eye_point_source_v1",
        manifest_sha256="b" * 64,
        source_dataset_ids=("test-pack-source",),
    )
    pack = SimpleNamespace(receipt=receipt, domain=domain)
    monkeypatch.setattr(
        heliacal,
        "load_visibility_data_pack",
        lambda _config: pack,
    )

    def horizontal(
        target: str,
        _jd_ut: float,
        _lat: float,
        _lon: float,
    ) -> tuple[float, float]:
        if target == Body.SUN:
            return 185.0, -8.0
        return 5.0, 2.0

    monkeypatch.setattr(heliacal, "_true_horizontal", horizontal)
    result = physical_visibility_assessment(
        Body.MARS,
        2451545.0,
        0.0,
        0.0,
        data_pack_config=VisibilityDataPackConfig("unused"),
        policy=PhysicalVisibilityPolicy(
            background=_background(),
            directional_horizon=_flat_profile(),
        ),
    )

    assert result.status is PhysicalVisibilityStatus.NOT_EVALUABLE
    assert (
        result.evidence_state
        is PhysicalVisibilityEvidenceState.NOT_APPLICABLE
    )
    assert result.reason == "target_below_local_horizon"
    assert result.horizon_receipt is not None
    assert result.horizon_receipt.directional_profile_applied
    assert result.horizon_receipt.queried_target_azimuth_deg == 5.0
    assert (
        result.horizon_receipt.target_local_horizon_altitude_deg
        == 5.0
    )
    assert (
        result.horizon_receipt.directional_profile_source_receipt_sha256
        == _SHA
    )
    assert result.observer_protocol_receipt.directional_profile_applied
