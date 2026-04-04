from __future__ import annotations

import math

import pytest

from moira import harmograms as _harmograms_module
from moira.harmograms import (
    GaussianWidthParameterMode,
    HarmonicDomain,
    HarmogramChartDomain,
    HarmogramIntensityFamily,
    HarmogramIntensityPolicy,
    HarmogramOrbMode,
    HarmogramOutputMode,
    HarmogramPolicy,
    HarmogramProjectionRealizationMode,
    HarmogramSamplingPolicy,
    HarmogramSamplingMode,
    HarmogramSymmetryMode,
    HarmogramTraceFamily,
    HarmonicVectorNormalizationMode,
    IntensitySpectrumRealizationMode,
    PointSetHarmonicVectorPolicy,
    SelfPairMode,
    ZeroAriesPairConstructionMode,
    ZeroAriesPartsPolicy,
    compare_intensity_spectra,
    compare_trace_series,
    dominant_harmonic_contributors,
    harmonic_vector,
    harmogram_trace,
    intensity_function_spectrum,
    parts_from_zero_aries,
    point_set_harmonic_vector,
    project_harmogram_strength,
    zero_aries_parts_harmonic_vector,
)


def _direct_tally_strength(
    longitudes_deg: tuple[float, ...],
    *,
    harmonic_number: int,
    policy: HarmogramIntensityPolicy,
    normalization_mode: HarmonicVectorNormalizationMode,
) -> float:
    values = [
        _harmograms_module._intensity_at_angle_deg(longitude, harmonic_number, policy)
        for longitude in longitudes_deg
    ]
    if normalization_mode is HarmonicVectorNormalizationMode.RAW_SUM:
        return sum(values)
    return sum(values) / len(values)


def _reconstructed_tally_strength(
    longitudes_deg: tuple[float, ...],
    *,
    spectrum,
    normalization_mode: HarmonicVectorNormalizationMode,
) -> float:
    values = []
    for longitude in longitudes_deg:
        value = spectrum.harmonic_zero_amplitude
        for component in spectrum.components:
            phase = math.radians(component.phase_deg + component.harmonic * longitude)
            value += 2.0 * component.amplitude * math.cos(phase)
        values.append(value)
    if normalization_mode is HarmonicVectorNormalizationMode.RAW_SUM:
        return sum(values)
    return sum(values) / len(values)


def test_point_set_harmonic_vector_single_point_tracks_phase_across_domain() -> None:
    vector = point_set_harmonic_vector(
        [{"name": "Sun", "degree": 45.0}],
        policy=PointSetHarmonicVectorPolicy(harmonic_domain=HarmonicDomain(1, 4)),
    )

    assert vector.point_count == 1
    assert vector.policy.harmonic_domain.harmonics == (1, 2, 3, 4)
    assert vector.harmonic_zero_amplitude == pytest.approx(1.0)
    assert [component.amplitude for component in vector.components] == pytest.approx([1.0, 1.0, 1.0, 1.0])
    assert [component.phase_deg for component in vector.components] == pytest.approx([45.0, 90.0, 135.0, 180.0])


def test_zero_aries_parts_set_ordered_with_self_pairs_has_n_squared_parts() -> None:
    parts = parts_from_zero_aries(
        [
            {"name": "Sun", "degree": 0.0},
            {"name": "Moon", "degree": 90.0},
            {"name": "Mercury", "degree": 180.0},
        ]
    )

    assert parts.policy.pair_construction_mode is ZeroAriesPairConstructionMode.ORDERED
    assert parts.policy.self_pair_mode is SelfPairMode.INCLUDE
    assert parts.source_point_count == 3
    assert parts.target_point_count == 3
    assert parts.parts_count == 9


def test_zero_aries_parts_set_ordered_without_self_pairs_has_n_times_n_minus_1_parts() -> None:
    parts = parts_from_zero_aries(
        [
            {"name": "Sun", "degree": 0.0},
            {"name": "Moon", "degree": 90.0},
            {"name": "Mercury", "degree": 180.0},
        ],
        policy=ZeroAriesPartsPolicy(self_pair_mode=SelfPairMode.EXCLUDE),
    )

    assert parts.parts_count == 6
    assert all(part.source_name != part.target_name for part in parts.parts)


def test_zero_aries_parts_harmonic_vector_preserves_garcia_identity_with_self_pairs_mean_resultant() -> None:
    positions = [
        {"name": "Sun", "degree": 10.0},
        {"name": "Moon", "degree": 130.0},
        {"name": "Mercury", "degree": 250.0},
    ]
    domain = HarmonicDomain(1, 5)
    point_vector = point_set_harmonic_vector(
        positions,
        policy=PointSetHarmonicVectorPolicy(harmonic_domain=domain),
    )
    parts_vector = zero_aries_parts_harmonic_vector(
        positions,
        vector_policy=PointSetHarmonicVectorPolicy(harmonic_domain=domain),
    )

    assert parts_vector.parts_count == 9
    assert parts_vector.vector_policy.harmonic_domain == domain
    for harmonic in domain.harmonics:
        point_component = point_vector.get_component(harmonic)
        parts_component = parts_vector.get_component(harmonic)
        assert parts_component.amplitude == pytest.approx(point_component.amplitude_squared, abs=1.0e-12)
        assert parts_component.phase_deg == pytest.approx(0.0, abs=1.0e-12)


def test_zero_aries_parts_harmonic_vector_preserves_garcia_identity_with_self_pairs_raw_sum() -> None:
    positions = [
        {"name": "Sun", "degree": 0.0},
        {"name": "Moon", "degree": 180.0},
    ]
    domain = HarmonicDomain(1, 2)
    point_vector = point_set_harmonic_vector(
        positions,
        policy=PointSetHarmonicVectorPolicy(
            normalization_mode=HarmonicVectorNormalizationMode.RAW_SUM,
            harmonic_domain=domain,
        ),
    )
    parts_vector = zero_aries_parts_harmonic_vector(
        positions,
        vector_policy=PointSetHarmonicVectorPolicy(
            normalization_mode=HarmonicVectorNormalizationMode.RAW_SUM,
            harmonic_domain=domain,
        ),
    )

    assert parts_vector.harmonic_zero_amplitude == pytest.approx(4.0)
    assert parts_vector.get_component(1).amplitude == pytest.approx(point_vector.get_component(1).amplitude_squared, abs=1.0e-12)
    assert parts_vector.get_component(2).amplitude == pytest.approx(point_vector.get_component(2).amplitude_squared, abs=1.0e-12)


def test_zero_aries_parts_harmonic_vector_excluding_self_pairs_breaks_exact_garcia_identity() -> None:
    positions = [
        {"name": "Sun", "degree": 25.0},
        {"name": "Moon", "degree": 140.0},
        {"name": "Mercury", "degree": 260.0},
    ]
    domain = HarmonicDomain(1, 3)
    point_vector = point_set_harmonic_vector(
        positions,
        policy=PointSetHarmonicVectorPolicy(harmonic_domain=domain),
    )
    parts_vector = zero_aries_parts_harmonic_vector(
        positions,
        parts_policy=ZeroAriesPartsPolicy(self_pair_mode=SelfPairMode.EXCLUDE),
        vector_policy=PointSetHarmonicVectorPolicy(harmonic_domain=domain),
    )

    assert parts_vector.parts_count == 6
    differences = [
        abs(parts_vector.get_component(h).amplitude - point_vector.get_component(h).amplitude_squared)
        for h in domain.harmonics
    ]
    assert any(diff > 1.0e-6 for diff in differences)


def test_point_set_harmonic_vector_rejects_duplicate_names() -> None:
    with pytest.raises(ValueError, match="duplicate entry"):
        point_set_harmonic_vector(
            [
                {"name": "Sun", "degree": 0.0},
                {"name": "Sun", "degree": 120.0},
            ]
        )


def test_harmonic_domain_rejects_invalid_bounds() -> None:
    with pytest.raises(ValueError, match="harmonic_start must be positive"):
        HarmonicDomain(0, 3)
    with pytest.raises(ValueError, match="harmonic_stop must be >= harmonic_start"):
        HarmonicDomain(3, 2)


def test_harmonic_vector_alias_resolves_to_point_set_surface() -> None:
    alias_vector = harmonic_vector([{"name": "Sun", "degree": 15.0}])
    direct_vector = point_set_harmonic_vector([{"name": "Sun", "degree": 15.0}])

    assert alias_vector == direct_vector


def test_intensity_policy_rejects_invalid_symmetry_conjunction_pairings() -> None:
    with pytest.raises(ValueError, match="requires include_conjunction=True"):
        HarmogramIntensityPolicy(
            include_conjunction=False,
            symmetry_mode=HarmogramSymmetryMode.STAR_SYMMETRIC,
        )

    with pytest.raises(ValueError, match="requires include_conjunction=False"):
        HarmogramIntensityPolicy(
            include_conjunction=True,
            symmetry_mode=HarmogramSymmetryMode.CONJUNCTION_EXCLUDED,
        )


def test_intensity_policy_rejects_family_orb_mode_mismatch() -> None:
    with pytest.raises(ValueError, match="orb_mode must match"):
        HarmogramIntensityPolicy(
            family=HarmogramIntensityFamily.TRIANGULAR_HARMONIC_ASPECTS,
            orb_mode=HarmogramOrbMode.COSINE_BELL,
        )


def test_gaussian_intensity_policy_requires_positive_declared_width() -> None:
    with pytest.raises(ValueError, match="gaussian_width_deg"):
        HarmogramIntensityPolicy(
            family=HarmogramIntensityFamily.GAUSSIAN_HARMONIC_ASPECTS,
            orb_mode=HarmogramOrbMode.GAUSSIAN,
            gaussian_width_deg=None,
        )


def test_intensity_function_spectrum_preserves_exact_policy_and_domain() -> None:
    policy = HarmogramIntensityPolicy(
        harmonic_domain=HarmonicDomain(1, 8),
        sample_count=4096,
    )

    spectrum = intensity_function_spectrum(4, policy=policy)

    assert spectrum.policy is policy
    assert spectrum.realization_mode is IntensitySpectrumRealizationMode.NUMERICAL_TRUNCATED
    assert tuple(component.harmonic for component in spectrum.components) == policy.harmonic_domain.harmonics


def test_star_symmetric_intensity_spectrum_suppresses_non_multiple_harmonics() -> None:
    spectrum = intensity_function_spectrum(
        4,
        policy=HarmogramIntensityPolicy(
            harmonic_domain=HarmonicDomain(1, 8),
            include_conjunction=True,
            symmetry_mode=HarmogramSymmetryMode.STAR_SYMMETRIC,
            sample_count=4096,
        ),
    )

    for harmonic in (1, 2, 3, 5, 6, 7):
        assert spectrum.get_component(harmonic).amplitude < 1.0e-6

    assert spectrum.get_component(4).amplitude > 1.0e-3
    assert spectrum.get_component(8).amplitude > 1.0e-3


def test_conjunction_excluded_intensity_spectrum_breaks_star_symmetry() -> None:
    spectrum = intensity_function_spectrum(
        4,
        policy=HarmogramIntensityPolicy(
            harmonic_domain=HarmonicDomain(1, 8),
            include_conjunction=False,
            symmetry_mode=HarmogramSymmetryMode.CONJUNCTION_EXCLUDED,
            sample_count=4096,
        ),
    )

    non_multiples = [spectrum.get_component(harmonic).amplitude for harmonic in (1, 2, 3, 5, 6, 7)]
    assert any(amplitude > 1.0e-4 for amplitude in non_multiples)


def test_top_hat_and_triangular_intensity_families_are_admitted() -> None:
    domain = HarmonicDomain(1, 8)
    top_hat = intensity_function_spectrum(
        4,
        policy=HarmogramIntensityPolicy(
            family=HarmogramIntensityFamily.TOP_HAT_HARMONIC_ASPECTS,
            orb_mode=HarmogramOrbMode.TOP_HAT,
            harmonic_domain=domain,
            sample_count=4096,
        ),
    )
    triangular = intensity_function_spectrum(
        4,
        policy=HarmogramIntensityPolicy(
            family=HarmogramIntensityFamily.TRIANGULAR_HARMONIC_ASPECTS,
            orb_mode=HarmogramOrbMode.TRIANGULAR,
            harmonic_domain=domain,
            sample_count=4096,
        ),
    )

    assert top_hat.policy.family is HarmogramIntensityFamily.TOP_HAT_HARMONIC_ASPECTS
    assert triangular.policy.family is HarmogramIntensityFamily.TRIANGULAR_HARMONIC_ASPECTS
    assert top_hat.get_component(4).amplitude > 1.0e-3
    assert triangular.get_component(4).amplitude > 1.0e-3


def test_gaussian_intensity_family_is_admitted_for_sigma_and_fwhm_modes() -> None:
    domain = HarmonicDomain(1, 8)
    gaussian_sigma = intensity_function_spectrum(
        4,
        policy=HarmogramIntensityPolicy(
            family=HarmogramIntensityFamily.GAUSSIAN_HARMONIC_ASPECTS,
            orb_mode=HarmogramOrbMode.GAUSSIAN,
            harmonic_domain=domain,
            gaussian_width_parameter_mode=GaussianWidthParameterMode.SIGMA,
            gaussian_width_deg=3.0,
            sample_count=4096,
        ),
    )
    gaussian_fwhm = intensity_function_spectrum(
        4,
        policy=HarmogramIntensityPolicy(
            family=HarmogramIntensityFamily.GAUSSIAN_HARMONIC_ASPECTS,
            orb_mode=HarmogramOrbMode.GAUSSIAN,
            harmonic_domain=domain,
            gaussian_width_parameter_mode=GaussianWidthParameterMode.FWHM,
            gaussian_width_deg=3.0,
            sample_count=4096,
        ),
    )

    assert gaussian_sigma.policy.family is HarmogramIntensityFamily.GAUSSIAN_HARMONIC_ASPECTS
    assert gaussian_fwhm.policy.family is HarmogramIntensityFamily.GAUSSIAN_HARMONIC_ASPECTS
    assert gaussian_sigma.get_component(4).amplitude > 1.0e-3
    assert gaussian_fwhm.get_component(4).amplitude > 1.0e-3


def test_triangular_intensity_family_differs_from_cosine_bell_family() -> None:
    domain = HarmonicDomain(1, 12)
    cosine = intensity_function_spectrum(
        4,
        policy=HarmogramIntensityPolicy(
            family=HarmogramIntensityFamily.COSINE_BELL_HARMONIC_ASPECTS,
            orb_mode=HarmogramOrbMode.COSINE_BELL,
            harmonic_domain=domain,
            sample_count=4096,
        ),
    )
    triangular = intensity_function_spectrum(
        4,
        policy=HarmogramIntensityPolicy(
            family=HarmogramIntensityFamily.TRIANGULAR_HARMONIC_ASPECTS,
            orb_mode=HarmogramOrbMode.TRIANGULAR,
            harmonic_domain=domain,
            sample_count=4096,
        ),
    )

    comparison = compare_intensity_spectra(cosine, triangular)

    assert comparison.max_absolute_delta > 1.0e-4


def test_top_hat_intensity_family_differs_from_triangular_family() -> None:
    domain = HarmonicDomain(1, 12)
    top_hat = intensity_function_spectrum(
        4,
        policy=HarmogramIntensityPolicy(
            family=HarmogramIntensityFamily.TOP_HAT_HARMONIC_ASPECTS,
            orb_mode=HarmogramOrbMode.TOP_HAT,
            harmonic_domain=domain,
            sample_count=4096,
        ),
    )
    triangular = intensity_function_spectrum(
        4,
        policy=HarmogramIntensityPolicy(
            family=HarmogramIntensityFamily.TRIANGULAR_HARMONIC_ASPECTS,
            orb_mode=HarmogramOrbMode.TRIANGULAR,
            harmonic_domain=domain,
            sample_count=4096,
        ),
    )

    comparison = compare_intensity_spectra(top_hat, triangular)

    assert comparison.max_absolute_delta > 1.0e-4


def test_gaussian_sigma_and_fwhm_modes_differ_for_same_declared_width() -> None:
    domain = HarmonicDomain(1, 12)
    gaussian_sigma = intensity_function_spectrum(
        4,
        policy=HarmogramIntensityPolicy(
            family=HarmogramIntensityFamily.GAUSSIAN_HARMONIC_ASPECTS,
            orb_mode=HarmogramOrbMode.GAUSSIAN,
            harmonic_domain=domain,
            gaussian_width_parameter_mode=GaussianWidthParameterMode.SIGMA,
            gaussian_width_deg=4.0,
            sample_count=4096,
        ),
    )
    gaussian_fwhm = intensity_function_spectrum(
        4,
        policy=HarmogramIntensityPolicy(
            family=HarmogramIntensityFamily.GAUSSIAN_HARMONIC_ASPECTS,
            orb_mode=HarmogramOrbMode.GAUSSIAN,
            harmonic_domain=domain,
            gaussian_width_parameter_mode=GaussianWidthParameterMode.FWHM,
            gaussian_width_deg=4.0,
            sample_count=4096,
        ),
    )

    comparison = compare_intensity_spectra(gaussian_sigma, gaussian_fwhm)

    assert comparison.max_absolute_delta > 1.0e-4


def test_gaussian_intensity_family_differs_from_compact_support_families() -> None:
    domain = HarmonicDomain(1, 12)
    gaussian = intensity_function_spectrum(
        4,
        policy=HarmogramIntensityPolicy(
            family=HarmogramIntensityFamily.GAUSSIAN_HARMONIC_ASPECTS,
            orb_mode=HarmogramOrbMode.GAUSSIAN,
            harmonic_domain=domain,
            gaussian_width_parameter_mode=GaussianWidthParameterMode.FWHM,
            gaussian_width_deg=4.0,
            sample_count=4096,
        ),
    )
    triangular = intensity_function_spectrum(
        4,
        policy=HarmogramIntensityPolicy(
            family=HarmogramIntensityFamily.TRIANGULAR_HARMONIC_ASPECTS,
            orb_mode=HarmogramOrbMode.TRIANGULAR,
            harmonic_domain=domain,
            sample_count=4096,
        ),
    )

    comparison = compare_intensity_spectra(gaussian, triangular)

    assert comparison.max_absolute_delta > 1.0e-4


def test_projection_matches_truncated_reconstructed_tally_for_zero_aries_parts_mean_resultant() -> None:
    positions = [
        {"name": "Sun", "degree": 12.0},
        {"name": "Moon", "degree": 133.0},
        {"name": "Mercury", "degree": 248.0},
    ]
    domain = HarmonicDomain(1, 12)
    parts_vector = zero_aries_parts_harmonic_vector(
        positions,
        vector_policy=PointSetHarmonicVectorPolicy(harmonic_domain=domain),
    )
    parts_set = parts_from_zero_aries(positions)
    intensity_policy = HarmogramIntensityPolicy(harmonic_domain=domain, sample_count=4096)
    intensity = intensity_function_spectrum(4, policy=intensity_policy)

    projection = project_harmogram_strength(parts_vector, intensity)
    direct = _reconstructed_tally_strength(
        tuple(part.longitude_deg for part in parts_set.parts),
        spectrum=intensity,
        normalization_mode=HarmonicVectorNormalizationMode.MEAN_RESULTANT,
    )

    assert projection.realization_mode is HarmogramProjectionRealizationMode.NUMERICAL_TRUNCATED
    assert projection.normalization_mode is HarmonicVectorNormalizationMode.MEAN_RESULTANT
    assert projection.total_strength == pytest.approx(direct, abs=1.0e-10)
    assert projection.harmonic_zero_contribution + sum(term.signed_contribution for term in projection.terms) == pytest.approx(
        projection.total_strength,
        abs=1.0e-12,
    )


def test_projection_matches_truncated_reconstructed_tally_for_zero_aries_parts_raw_sum() -> None:
    positions = [
        {"name": "Sun", "degree": 0.0},
        {"name": "Moon", "degree": 90.0},
        {"name": "Mercury", "degree": 190.0},
    ]
    domain = HarmonicDomain(1, 12)
    parts_vector = zero_aries_parts_harmonic_vector(
        positions,
        vector_policy=PointSetHarmonicVectorPolicy(
            normalization_mode=HarmonicVectorNormalizationMode.RAW_SUM,
            harmonic_domain=domain,
        ),
    )
    parts_set = parts_from_zero_aries(positions)
    intensity_policy = HarmogramIntensityPolicy(harmonic_domain=domain, sample_count=4096)
    intensity = intensity_function_spectrum(3, policy=intensity_policy)

    projection = project_harmogram_strength(parts_vector, intensity)
    direct = _reconstructed_tally_strength(
        tuple(part.longitude_deg for part in parts_set.parts),
        spectrum=intensity,
        normalization_mode=HarmonicVectorNormalizationMode.RAW_SUM,
    )

    assert projection.normalization_mode is HarmonicVectorNormalizationMode.RAW_SUM
    assert projection.total_strength == pytest.approx(direct, abs=1.0e-10)


def test_projection_diverges_from_full_direct_tally_when_domain_is_truncated() -> None:
    positions = [
        {"name": "Sun", "degree": 12.0},
        {"name": "Moon", "degree": 133.0},
        {"name": "Mercury", "degree": 248.0},
    ]
    domain = HarmonicDomain(1, 12)
    parts_vector = zero_aries_parts_harmonic_vector(
        positions,
        vector_policy=PointSetHarmonicVectorPolicy(harmonic_domain=domain),
    )
    parts_set = parts_from_zero_aries(positions)
    intensity_policy = HarmogramIntensityPolicy(harmonic_domain=domain, sample_count=4096)
    intensity = intensity_function_spectrum(4, policy=intensity_policy)

    projection = project_harmogram_strength(parts_vector, intensity)
    direct_full = _direct_tally_strength(
        tuple(part.longitude_deg for part in parts_set.parts),
        harmonic_number=4,
        policy=intensity_policy,
        normalization_mode=HarmonicVectorNormalizationMode.MEAN_RESULTANT,
    )

    assert abs(projection.total_strength - direct_full) > 1.0e-3


def test_projection_rejects_harmonic_domain_mismatch() -> None:
    source_vector = point_set_harmonic_vector(
        [{"name": "Sun", "degree": 30.0}],
        policy=PointSetHarmonicVectorPolicy(harmonic_domain=HarmonicDomain(1, 6)),
    )
    intensity = intensity_function_spectrum(
        2,
        policy=HarmogramIntensityPolicy(harmonic_domain=HarmonicDomain(1, 8)),
    )

    with pytest.raises(ValueError, match="must share the same harmonic domain"):
        project_harmogram_strength(source_vector, intensity)


def test_projection_preserves_term_access_and_source_identity() -> None:
    source_vector = point_set_harmonic_vector(
        [{"name": "Sun", "degree": 45.0}],
        policy=PointSetHarmonicVectorPolicy(harmonic_domain=HarmonicDomain(1, 4)),
    )
    intensity = intensity_function_spectrum(
        1,
        policy=HarmogramIntensityPolicy(harmonic_domain=HarmonicDomain(1, 4), sample_count=4096),
    )

    projection = project_harmogram_strength(source_vector, intensity)

    assert projection.source_vector is source_vector
    assert projection.intensity_spectrum is intensity
    assert projection.get_term(1).harmonic == 1


def test_harmogram_policy_rejects_cross_domain_mismatch() -> None:
    with pytest.raises(ValueError, match="must share the same harmonic domain"):
        HarmogramPolicy(
            point_set_policy=PointSetHarmonicVectorPolicy(harmonic_domain=HarmonicDomain(1, 4)),
            intensity_policy=HarmogramIntensityPolicy(harmonic_domain=HarmonicDomain(1, 8)),
        )


def test_harmogram_policy_rejects_trace_family_chart_domain_mismatch() -> None:
    with pytest.raises(ValueError, match="transit_to_natal_trace"):
        HarmogramPolicy(
            chart_domain=HarmogramChartDomain.DYNAMIC_SKY_ONLY_TRACE,
            trace_family=HarmogramTraceFamily.TRANSIT_TO_NATAL_ZERO_ARIES_PARTS,
        )


def test_harmogram_trace_builds_multi_harmonic_series_over_supplied_samples() -> None:
    policy = HarmogramPolicy(
        point_set_policy=PointSetHarmonicVectorPolicy(harmonic_domain=HarmonicDomain(1, 8)),
        intensity_policy=HarmogramIntensityPolicy(harmonic_domain=HarmonicDomain(1, 8), sample_count=4096),
        sampling_policy=HarmogramSamplingPolicy(
            sampling_mode=HarmogramSamplingMode.EXPLICIT_FIXED_STEP,
            sample_count=3,
        ),
        output_mode=HarmogramOutputMode.MULTI_HARMONIC_FAMILY,
        chart_domain=HarmogramChartDomain.DYNAMIC_SKY_ONLY_TRACE,
        trace_family=HarmogramTraceFamily.DYNAMIC_ZERO_ARIES_PARTS,
    )
    samples = [
        {
            "time": 0.0,
            "positions": [
                {"name": "Sun", "degree": 0.0},
                {"name": "Moon", "degree": 90.0},
            ],
        },
        {
            "time": 1.0,
            "positions": [
                {"name": "Sun", "degree": 10.0},
                {"name": "Moon", "degree": 100.0},
            ],
        },
        {
            "time": 2.0,
            "positions": [
                {"name": "Sun", "degree": 20.0},
                {"name": "Moon", "degree": 110.0},
            ],
        },
    ]

    trace = harmogram_trace(samples, harmonic_numbers=(1, 2), policy=policy)

    assert trace.policy is policy
    assert trace.interval_start == pytest.approx(0.0)
    assert trace.interval_stop == pytest.approx(2.0)
    assert trace.sample_times == pytest.approx((0.0, 1.0, 2.0))
    assert len(trace.series) == 2
    assert trace.get_series(1).harmonic_number == 1
    assert trace.get_series(2).harmonic_number == 2
    assert len(trace.get_series(1).samples) == 3


def test_harmogram_trace_single_harmonic_mode_rejects_multiple_harmonics() -> None:
    policy = HarmogramPolicy(
        output_mode=HarmogramOutputMode.SINGLE_HARMONIC,
    )
    samples = [
        {
            "time": 0.0,
            "positions": [
                {"name": "Sun", "degree": 0.0},
                {"name": "Moon", "degree": 90.0},
            ],
        },
        {
            "time": 1.0,
            "positions": [
                {"name": "Sun", "degree": 10.0},
                {"name": "Moon", "degree": 100.0},
            ],
        },
    ]

    with pytest.raises(ValueError, match="exactly one harmonic number"):
        harmogram_trace(samples, harmonic_numbers=(1, 2), policy=policy)


def test_harmogram_trace_rejects_sampling_count_mismatch() -> None:
    policy = HarmogramPolicy(
        sampling_policy=HarmogramSamplingPolicy(sample_count=3),
    )
    samples = [
        {
            "time": 0.0,
            "positions": [
                {"name": "Sun", "degree": 0.0},
                {"name": "Moon", "degree": 90.0},
            ],
        },
        {
            "time": 1.0,
            "positions": [
                {"name": "Sun", "degree": 10.0},
                {"name": "Moon", "degree": 100.0},
            ],
        },
    ]

    with pytest.raises(ValueError, match="sample_count"):
        harmogram_trace(samples, harmonic_numbers=(1,), policy=policy)


def test_harmogram_trace_sample_projection_matches_standalone_projection() -> None:
    policy = HarmogramPolicy(
        point_set_policy=PointSetHarmonicVectorPolicy(harmonic_domain=HarmonicDomain(1, 6)),
        intensity_policy=HarmogramIntensityPolicy(harmonic_domain=HarmonicDomain(1, 6), sample_count=4096),
    )
    samples = [
        {
            "time": 5.0,
            "positions": [
                {"name": "Sun", "degree": 12.0},
                {"name": "Moon", "degree": 133.0},
                {"name": "Mercury", "degree": 248.0},
            ],
        },
        {
            "time": 6.0,
            "positions": [
                {"name": "Sun", "degree": 15.0},
                {"name": "Moon", "degree": 136.0},
                {"name": "Mercury", "degree": 251.0},
            ],
        },
    ]

    trace = harmogram_trace(samples, harmonic_numbers=(4,), policy=policy)
    first_series = trace.get_series(4)
    first_sample = first_series.samples[0]
    standalone = project_harmogram_strength(first_sample.source_vector, first_series.intensity_spectrum)

    assert first_sample.projection == standalone
    assert first_sample.total_strength == pytest.approx(standalone.total_strength)


def test_harmogram_trace_stationary_samples_produce_stationary_strengths() -> None:
    policy = HarmogramPolicy(
        point_set_policy=PointSetHarmonicVectorPolicy(harmonic_domain=HarmonicDomain(1, 6)),
        intensity_policy=HarmogramIntensityPolicy(harmonic_domain=HarmonicDomain(1, 6), sample_count=4096),
    )
    repeated_positions = [
        {"name": "Sun", "degree": 0.0},
        {"name": "Moon", "degree": 90.0},
    ]
    samples = [
        {"time": 0.0, "positions": repeated_positions},
        {"time": 1.0, "positions": repeated_positions},
        {"time": 2.0, "positions": repeated_positions},
    ]

    trace = harmogram_trace(samples, harmonic_numbers=(2,), policy=policy)
    strengths = trace.get_series(2).strengths

    assert strengths[0] == pytest.approx(strengths[1])
    assert strengths[1] == pytest.approx(strengths[2])


def test_transit_to_natal_zero_aries_parts_trace_builds_from_relational_samples() -> None:
    policy = HarmogramPolicy(
        point_set_policy=PointSetHarmonicVectorPolicy(harmonic_domain=HarmonicDomain(1, 6)),
        intensity_policy=HarmogramIntensityPolicy(harmonic_domain=HarmonicDomain(1, 6), sample_count=4096),
        chart_domain=HarmogramChartDomain.TRANSIT_TO_NATAL_TRACE,
        trace_family=HarmogramTraceFamily.TRANSIT_TO_NATAL_ZERO_ARIES_PARTS,
    )
    samples = [
        {
            "time": 0.0,
            "transit_positions": [
                {"name": "Sun", "degree": 10.0},
                {"name": "Moon", "degree": 120.0},
            ],
            "natal_positions": [
                {"name": "Sun", "degree": 0.0},
                {"name": "Moon", "degree": 90.0},
            ],
        },
        {
            "time": 1.0,
            "transit_positions": [
                {"name": "Sun", "degree": 20.0},
                {"name": "Moon", "degree": 130.0},
            ],
            "natal_positions": [
                {"name": "Sun", "degree": 0.0},
                {"name": "Moon", "degree": 90.0},
            ],
        },
    ]

    trace = harmogram_trace(samples, harmonic_numbers=(2,), policy=policy)

    assert trace.policy.trace_family is HarmogramTraceFamily.TRANSIT_TO_NATAL_ZERO_ARIES_PARTS
    first_sample = trace.get_series(2).samples[0]
    assert first_sample.source_vector.source_body_names == ("Sun", "Moon")
    assert first_sample.source_vector.target_body_names == ("Sun", "Moon")


def test_directed_to_natal_zero_aries_parts_trace_builds_from_relational_samples() -> None:
    policy = HarmogramPolicy(
        point_set_policy=PointSetHarmonicVectorPolicy(harmonic_domain=HarmonicDomain(1, 6)),
        intensity_policy=HarmogramIntensityPolicy(harmonic_domain=HarmonicDomain(1, 6), sample_count=4096),
        chart_domain=HarmogramChartDomain.DIRECTED_OR_PROGRESSED_TRACE,
        trace_family=HarmogramTraceFamily.DIRECTED_TO_NATAL_ZERO_ARIES_PARTS,
    )
    samples = [
        {
            "time": 0.0,
            "directed_positions": [
                {"name": "Sun", "degree": 15.0},
                {"name": "Moon", "degree": 100.0},
            ],
            "natal_positions": [
                {"name": "Sun", "degree": 5.0},
                {"name": "Moon", "degree": 80.0},
            ],
        },
        {
            "time": 1.0,
            "directed_positions": [
                {"name": "Sun", "degree": 18.0},
                {"name": "Moon", "degree": 104.0},
            ],
            "natal_positions": [
                {"name": "Sun", "degree": 5.0},
                {"name": "Moon", "degree": 80.0},
            ],
        },
    ]

    trace = harmogram_trace(samples, harmonic_numbers=(3,), policy=policy)

    assert trace.policy.trace_family is HarmogramTraceFamily.DIRECTED_TO_NATAL_ZERO_ARIES_PARTS
    assert len(trace.get_series(3).samples) == 2


def test_progressed_to_natal_zero_aries_parts_trace_builds_from_relational_samples() -> None:
    policy = HarmogramPolicy(
        point_set_policy=PointSetHarmonicVectorPolicy(harmonic_domain=HarmonicDomain(1, 6)),
        intensity_policy=HarmogramIntensityPolicy(harmonic_domain=HarmonicDomain(1, 6), sample_count=4096),
        chart_domain=HarmogramChartDomain.DIRECTED_OR_PROGRESSED_TRACE,
        trace_family=HarmogramTraceFamily.PROGRESSED_TO_NATAL_ZERO_ARIES_PARTS,
    )
    samples = [
        {
            "time": 0.0,
            "progressed_positions": [
                {"name": "Sun", "degree": 25.0},
                {"name": "Moon", "degree": 140.0},
            ],
            "natal_positions": [
                {"name": "Sun", "degree": 12.0},
                {"name": "Moon", "degree": 100.0},
            ],
        },
        {
            "time": 1.0,
            "progressed_positions": [
                {"name": "Sun", "degree": 27.0},
                {"name": "Moon", "degree": 142.0},
            ],
            "natal_positions": [
                {"name": "Sun", "degree": 12.0},
                {"name": "Moon", "degree": 100.0},
            ],
        },
    ]

    trace = harmogram_trace(samples, harmonic_numbers=(4,), policy=policy)

    assert trace.policy.trace_family is HarmogramTraceFamily.PROGRESSED_TO_NATAL_ZERO_ARIES_PARTS
    assert len(trace.get_series(4).samples) == 2


def test_relational_trace_rejects_missing_required_position_set() -> None:
    policy = HarmogramPolicy(
        chart_domain=HarmogramChartDomain.TRANSIT_TO_NATAL_TRACE,
        trace_family=HarmogramTraceFamily.TRANSIT_TO_NATAL_ZERO_ARIES_PARTS,
    )
    samples = [
        {
            "time": 0.0,
            "transit_positions": [{"name": "Sun", "degree": 10.0}],
        },
        {
            "time": 1.0,
            "transit_positions": [{"name": "Sun", "degree": 11.0}],
            "natal_positions": [{"name": "Sun", "degree": 0.0}],
        },
    ]

    with pytest.raises(ValueError, match="natal_positions"):
        harmogram_trace(samples, harmonic_numbers=(1,), policy=policy)


def test_dominant_harmonic_contributors_rank_projection_terms() -> None:
    source_vector = point_set_harmonic_vector(
        [
            {"name": "Sun", "degree": 0.0},
            {"name": "Moon", "degree": 90.0},
            {"name": "Mercury", "degree": 180.0},
        ],
        policy=PointSetHarmonicVectorPolicy(harmonic_domain=HarmonicDomain(1, 6)),
    )
    intensity = intensity_function_spectrum(
        2,
        policy=HarmogramIntensityPolicy(harmonic_domain=HarmonicDomain(1, 6), sample_count=4096),
    )
    projection = project_harmogram_strength(source_vector, intensity)

    dominant = dominant_harmonic_contributors(projection, limit=2)

    assert len(dominant) == 2
    assert dominant[0].absolute_contribution >= dominant[1].absolute_contribution
    assert dominant[0].absolute_contribution == pytest.approx(abs(dominant[0].signed_contribution))


def test_compare_intensity_spectra_detects_conjunction_policy_difference() -> None:
    domain = HarmonicDomain(1, 8)
    left = intensity_function_spectrum(
        4,
        policy=HarmogramIntensityPolicy(
            harmonic_domain=domain,
            include_conjunction=True,
            symmetry_mode=HarmogramSymmetryMode.STAR_SYMMETRIC,
            sample_count=4096,
        ),
    )
    right = intensity_function_spectrum(
        4,
        policy=HarmogramIntensityPolicy(
            harmonic_domain=domain,
            include_conjunction=False,
            symmetry_mode=HarmogramSymmetryMode.CONJUNCTION_EXCLUDED,
            sample_count=4096,
        ),
    )

    comparison = compare_intensity_spectra(left, right)

    assert comparison.left is left
    assert comparison.right is right
    assert comparison.max_absolute_delta > 1.0e-4
    assert any(abs(term.amplitude_delta) > 1.0e-4 for term in comparison.terms)


def test_compare_trace_series_detects_strength_differences() -> None:
    domain = HarmonicDomain(1, 6)
    samples = [
        {
            "time": 0.0,
            "positions": [
                {"name": "Sun", "degree": 0.0},
                {"name": "Moon", "degree": 90.0},
            ],
        },
        {
            "time": 1.0,
            "positions": [
                {"name": "Sun", "degree": 15.0},
                {"name": "Moon", "degree": 105.0},
            ],
        },
    ]
    left_trace = harmogram_trace(
        samples,
        harmonic_numbers=(2,),
        policy=HarmogramPolicy(
            point_set_policy=PointSetHarmonicVectorPolicy(harmonic_domain=domain),
            intensity_policy=HarmogramIntensityPolicy(
                harmonic_domain=domain,
                include_conjunction=True,
                symmetry_mode=HarmogramSymmetryMode.STAR_SYMMETRIC,
                sample_count=4096,
            ),
        ),
    )
    right_trace = harmogram_trace(
        samples,
        harmonic_numbers=(2,),
        policy=HarmogramPolicy(
            point_set_policy=PointSetHarmonicVectorPolicy(harmonic_domain=domain),
            intensity_policy=HarmogramIntensityPolicy(
                harmonic_domain=domain,
                include_conjunction=False,
                symmetry_mode=HarmogramSymmetryMode.CONJUNCTION_EXCLUDED,
                sample_count=4096,
            ),
        ),
    )

    comparison = compare_trace_series(left_trace.get_series(2), right_trace.get_series(2))

    assert comparison.max_absolute_delta > 1.0e-4
    assert len(comparison.samples) == 2
    assert comparison.samples[0].sample_time == pytest.approx(0.0)


def test_compare_trace_series_rejects_sample_time_mismatch() -> None:
    domain = HarmonicDomain(1, 6)
    left_trace = harmogram_trace(
        [
            {
                "time": 0.0,
                "positions": [
                    {"name": "Sun", "degree": 0.0},
                    {"name": "Moon", "degree": 90.0},
                ],
            },
            {
                "time": 1.0,
                "positions": [
                    {"name": "Sun", "degree": 10.0},
                    {"name": "Moon", "degree": 100.0},
                ],
            },
        ],
        harmonic_numbers=(2,),
        policy=HarmogramPolicy(
            point_set_policy=PointSetHarmonicVectorPolicy(harmonic_domain=domain),
            intensity_policy=HarmogramIntensityPolicy(harmonic_domain=domain, sample_count=4096),
        ),
    )
    right_trace = harmogram_trace(
        [
            {
                "time": 0.0,
                "positions": [
                    {"name": "Sun", "degree": 0.0},
                    {"name": "Moon", "degree": 90.0},
                ],
            },
            {
                "time": 2.0,
                "positions": [
                    {"name": "Sun", "degree": 10.0},
                    {"name": "Moon", "degree": 100.0},
                ],
            },
        ],
        harmonic_numbers=(2,),
        policy=HarmogramPolicy(
            point_set_policy=PointSetHarmonicVectorPolicy(harmonic_domain=domain),
            intensity_policy=HarmogramIntensityPolicy(harmonic_domain=domain, sample_count=4096),
        ),
    )

    with pytest.raises(ValueError, match="sample times"):
        compare_trace_series(left_trace.get_series(2), right_trace.get_series(2))
