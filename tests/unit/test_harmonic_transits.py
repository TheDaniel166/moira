"""Doctrine and invariant tests for sampled mixed-origin harmonic forecasts."""

from dataclasses import FrozenInstanceError
import math

import pytest

from moira.harmonic_transits import (
    HarmonicTransitMemberOrigin,
    HarmonicTransitSample,
    MixedOriginHarmonicTransitForecastPolicy,
    MixedOriginHarmonicTransitMode,
    mixed_origin_harmonic_transit_forecast,
)
from moira.harmonics import HarmonicOrbPolicy


ONE_TRANSIT = MixedOriginHarmonicTransitMode.ONE_TRANSIT_TWO_NATAL
TWO_TRANSITS = MixedOriginHarmonicTransitMode.TWO_TRANSITS_ONE_NATAL


def _policy(
    *,
    harmonics: tuple[int, ...] = (5,),
    reference_orb_deg: float = 1.0,
    modes: tuple[MixedOriginHarmonicTransitMode, ...] = (ONE_TRANSIT,),
    minimum_observed_duration_days: float = 0.0,
    maximum_sample_gap_days: float = 1.0,
) -> MixedOriginHarmonicTransitForecastPolicy:
    return MixedOriginHarmonicTransitForecastPolicy(
        harmonics=harmonics,
        modes=modes,
        orb_policy=HarmonicOrbPolicy(reference_orb_deg=reference_orb_deg),
        minimum_observed_duration_days=minimum_observed_duration_days,
        maximum_sample_gap_days=maximum_sample_gap_days,
    )


def _forecast(
    natal: dict[str, float],
    samples: list[HarmonicTransitSample],
    *,
    policy: MixedOriginHarmonicTransitForecastPolicy | None = None,
):
    return mixed_origin_harmonic_transit_forecast(
        natal,
        samples,
        policy or _policy(),
    )


def test_default_policy_admits_both_mixed_origin_modes() -> None:
    policy = MixedOriginHarmonicTransitForecastPolicy(harmonics=(5,))

    assert set(policy.modes) == {ONE_TRANSIT, TWO_TRANSITS}


def test_exact_h5_emits_both_modes_with_resolved_addey_limits() -> None:
    forecast = _forecast(
        {"Natal A": 0.0, "Natal B": 72.0},
        [HarmonicTransitSample(2_460_000.0, {"Transit A": 72.0, "Transit B": 144.0})],
        policy=_policy(modes=(ONE_TRANSIT, TWO_TRANSITS)),
    )

    assert {window.mode for window in forecast.windows} == {
        ONE_TRANSIT,
        TWO_TRANSITS,
    }
    for window in forecast.windows:
        sample = window.samples[0]
        assert sample.harmonic == 5
        assert sample.projected_spread_deg == pytest.approx(0.0)
        assert sample.source_residual_spread_deg == pytest.approx(0.0)
        assert sample.projected_orb_limit_deg == pytest.approx(1.0)
        assert sample.source_orb_limit_deg == pytest.approx(0.2)


def test_complete_arc_rejects_pairwise_chain() -> None:
    # Every adjacent pair is within one degree, but all three require 1.5
    # degrees.  Connected-component admission would be a false positive.
    forecast = _forecast(
        {"A": 0.0, "B": 0.75},
        [HarmonicTransitSample(1.0, {"T": 1.5})],
        policy=_policy(harmonics=(1,), reference_orb_deg=1.0),
    )

    assert forecast.windows == ()


def test_complete_arc_uses_the_short_wrap_boundary_span() -> None:
    forecast = _forecast(
        {"A": 359.9, "B": 0.1},
        [HarmonicTransitSample(1.0, {"T": 0.0})],
        policy=_policy(harmonics=(1,), reference_orb_deg=0.2),
    )

    assert forecast.window_count == 1
    assert forecast.windows[0].samples[0].projected_spread_deg == pytest.approx(
        0.2
    )


def test_same_body_name_is_lawful_across_natal_and_transit_origins() -> None:
    forecast = _forecast(
        {"Mars": 0.0, "Venus": 72.0},
        [HarmonicTransitSample(1.0, {"Mars": 144.0})],
    )

    identities = forecast.windows[0].member_identities
    assert (HarmonicTransitMemberOrigin.NATAL, "Mars") in identities
    assert (HarmonicTransitMemberOrigin.TRANSIT, "Mars") in identities
    assert len(identities) == 3


def test_windows_split_on_missing_sample_and_excessive_time_gap() -> None:
    forecast = _forecast(
        {"A": 0.0, "B": 72.0},
        [
            HarmonicTransitSample(0.0, {"T": 144.0}),
            HarmonicTransitSample(0.5, {"T": 144.0}),
            HarmonicTransitSample(1.0, {"T": 150.0}),
            HarmonicTransitSample(1.5, {"T": 144.0}),
            HarmonicTransitSample(3.0, {"T": 144.0}),
        ],
        policy=_policy(maximum_sample_gap_days=1.0),
    )

    assert [
        tuple(sample.sample_index for sample in window.samples)
        for window in forecast.windows
    ] == [(0, 1), (3,), (4,)]
    assert [window.observed_duration_days for window in forecast.windows] == [
        pytest.approx(0.5),
        pytest.approx(0.0),
        pytest.approx(0.0),
    ]


def test_minimum_duration_filter_is_conservative_over_sampled_bounds() -> None:
    samples = [
        HarmonicTransitSample(0.0, {"T": 144.0}),
        HarmonicTransitSample(0.5, {"T": 144.0}),
        HarmonicTransitSample(1.0, {"T": 144.0}),
    ]

    admitted = _forecast(
        {"A": 0.0, "B": 72.0},
        samples,
        policy=_policy(minimum_observed_duration_days=1.0),
    )
    rejected = _forecast(
        {"A": 0.0, "B": 72.0},
        samples,
        policy=_policy(minimum_observed_duration_days=1.000_001),
    )

    assert admitted.window_count == 1
    assert admitted.windows[0].observed_duration_days == pytest.approx(1.0)
    assert rejected.windows == ()


def test_peak_is_earliest_sample_with_minimum_complete_arc() -> None:
    forecast = _forecast(
        {"A": 0.0, "B": 0.2},
        [
            HarmonicTransitSample(10.0, {"T": 0.9}),
            HarmonicTransitSample(10.5, {"T": 0.4}),
            HarmonicTransitSample(11.0, {"T": 0.4}),
        ],
        policy=_policy(harmonics=(1,), reference_orb_deg=1.0),
    )

    window = forecast.windows[0]
    assert window.first_sampled_jd_ut == pytest.approx(10.0)
    assert window.peak_sampled_jd_ut == pytest.approx(10.5)
    assert window.last_sampled_jd_ut == pytest.approx(11.0)
    assert window.sample_count == 3


def test_input_maps_and_sequences_are_defensively_immutable() -> None:
    natal = {" A ": 0.0, "B": 72.0}
    transit_map = {" T ": 144.0}
    harmonics = [5]
    modes = [ONE_TRANSIT]
    sample = HarmonicTransitSample(1.0, transit_map)
    policy = MixedOriginHarmonicTransitForecastPolicy(
        harmonics=harmonics,  # type: ignore[arg-type]
        modes=modes,  # type: ignore[arg-type]
    )
    forecast = mixed_origin_harmonic_transit_forecast(natal, [sample], policy)

    natal["A"] = 9.0
    transit_map["T"] = 9.0
    harmonics.append(7)
    modes.append(TWO_TRANSITS)

    assert forecast.natal_longitudes == {"A": 0.0, "B": 72.0}
    assert forecast.transit_samples[0].longitudes == {"T": 144.0}
    assert forecast.policy.harmonics == (5,)
    assert forecast.policy.modes == (ONE_TRANSIT,)
    with pytest.raises(TypeError):
        forecast.natal_longitudes["A"] = 1.0  # type: ignore[index]
    with pytest.raises(TypeError):
        forecast.transit_samples[0].longitudes["T"] = 1.0  # type: ignore[index]
    with pytest.raises(FrozenInstanceError):
        forecast.window_count = 9  # type: ignore[misc]


@pytest.mark.parametrize(
    "harmonics",
    [(), (5, 5), (0,), (-1,), (True,), (5.0,), (5.5,), ("5",)],
)
def test_policy_rejects_nonunique_or_non_positive_integer_harmonics(
    harmonics: tuple[object, ...],
) -> None:
    with pytest.raises(ValueError):
        MixedOriginHarmonicTransitForecastPolicy(
            harmonics=harmonics,  # type: ignore[arg-type]
        )


@pytest.mark.parametrize("value", [math.nan, math.inf, -math.inf])
def test_sample_rejects_nonfinite_timestamp_or_longitude(value: float) -> None:
    with pytest.raises(ValueError):
        HarmonicTransitSample(value, {"Mars": 1.0})
    with pytest.raises(ValueError):
        HarmonicTransitSample(1.0, {"Mars": value})


def test_samples_trim_labels_and_reject_ambiguous_trimmed_identity() -> None:
    sample = HarmonicTransitSample(1.0, {" Mars ": -1.0})

    assert sample.longitudes == {"Mars": pytest.approx(359.0)}
    with pytest.raises(ValueError):
        HarmonicTransitSample(1.0, {"Mars": 1.0, " Mars ": 2.0})
    with pytest.raises(ValueError):
        HarmonicTransitSample(1.0, {" ": 1.0})


def test_forecast_rejects_non_advancing_timestamps() -> None:
    policy = _policy()
    samples = [
        HarmonicTransitSample(2.0, {"T": 144.0}),
        HarmonicTransitSample(2.0, {"T": 144.0}),
    ]

    with pytest.raises(ValueError, match="strictly increasing"):
        mixed_origin_harmonic_transit_forecast(
            {"A": 0.0, "B": 72.0}, samples, policy
        )


def test_forecast_rejects_finite_timestamps_with_nonfinite_total_span() -> None:
    samples = [
        HarmonicTransitSample(-1e308, {"T": 144.0}),
        HarmonicTransitSample(0.0, {"T": 144.0}),
        HarmonicTransitSample(1e308, {"T": 144.0}),
    ]

    with pytest.raises(ValueError, match="timestamp span must be finite"):
        _forecast(
            {"A": 0.0, "B": 72.0},
            samples,
            policy=_policy(maximum_sample_gap_days=1e308),
        )


def test_forecast_rejects_transit_body_identity_drift() -> None:
    samples = [
        HarmonicTransitSample(1.0, {"T": 144.0}),
        HarmonicTransitSample(2.0, {"Other": 144.0}),
    ]

    with pytest.raises(ValueError, match="body identity"):
        _forecast({"A": 0.0, "B": 72.0}, samples)


def test_forecast_rejects_invalid_samples_and_nonfinite_natal_input() -> None:
    with pytest.raises(ValueError, match="HarmonicTransitSample"):
        mixed_origin_harmonic_transit_forecast(
            {"A": 0.0, "B": 72.0},
            [object()],  # type: ignore[list-item]
            _policy(),
        )
    with pytest.raises(ValueError, match="finite"):
        _forecast(
            {"A": math.nan, "B": 72.0},
            [HarmonicTransitSample(1.0, {"T": 144.0})],
        )


def test_forecast_records_sampled_scope_sources_and_deterministic_body_order() -> None:
    forecast = _forecast(
        {" zeta ": 72.0, "Alpha": 0.0},
        [HarmonicTransitSample(1.0, {" Transit Z ": 144.0})],
    )

    assert forecast.natal_bodies == ("Alpha", "zeta")
    assert forecast.transit_bodies == ("Transit Z",)
    assert forecast.transit_sample_count == 1
    assert forecast.input_provenance == (
        "caller_supplied_natal_longitudes_and_timestamped_transit_samples"
    )
    assert forecast.evaluation_scope == (
        "sampled_complete_mixed_origin_triples_without_interpolation"
    )
    assert "no Sirius parity" in forecast.claim_boundary
    assert "no exact ingress or egress" in forecast.claim_boundary
    assert len(forecast.source_locators) == 2
    assert "astrosoftware.com" in forecast.source_locators[0]
    assert "Forecasting%20with%20Vibrational%20Astrology.pdf" in (
        forecast.source_locators[1]
    )
