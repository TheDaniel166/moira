"""
Moira — Harmogram Computation Engine
Governs the mathematical computation of harmonic vectors, intensity spectra, and harmogram projections for astrological pattern analysis.

Boundary: owns harmonic analysis algorithms and mathematical transformations. Delegates data structure definitions to models and utility functions to helpers.

Import-time side effects: None

External dependencies:
    - math module for trigonometric and complex number operations
    - harmograms.helpers for normalization and utility functions
    - harmograms.models for data structure definitions

Public surface:
    point_set_harmonic_vector, parts_from_zero_aries, zero_aries_parts_harmonic_vector,
    harmonic_vector, intensity_function_spectrum, project_harmogram_strength, harmogram_trace
"""

import math

from .helpers import (
    _component_to_complex,
    _intensity_at_angle_deg,
    _normalize_angle_deg,
    _normalize_positions,
    _normalize_trace_samples,
    _source_harmonic_domain,
    _source_normalization_mode,
)
from .models import (
    HarmogramIntensityPolicy,
    HarmogramOutputMode,
    HarmogramPolicy,
    HarmogramProjection,
    HarmogramProjectionRealizationMode,
    HarmogramProjectionTerm,
    HarmogramTrace,
    HarmogramTraceFamily,
    HarmogramTraceSample,
    HarmogramTraceSeries,
    HarmonicDomain,
    HarmonicVectorComponent,
    HarmonicVectorNormalizationMode,
    IntensityFunctionSpectrum,
    IntensitySpectrumComponent,
    IntensitySpectrumRealizationMode,
    PointSetHarmonicVector,
    PointSetHarmonicVectorPolicy,
    SelfPairMode,
    ZeroAriesPairConstructionMode,
    ZeroAriesPart,
    ZeroAriesPartsHarmonicVector,
    ZeroAriesPartsPolicy,
    ZeroAriesPartsSet,
)


def _parts_from_position_sets(
    source_positions: list[dict],
    target_positions: list[dict],
    *,
    policy: ZeroAriesPartsPolicy,
) -> ZeroAriesPartsSet:
    normalized_source = _normalize_positions(source_positions)
    normalized_target = _normalize_positions(target_positions)
    items: list[ZeroAriesPart] = []
    if normalized_source == normalized_target and policy.pair_construction_mode is ZeroAriesPairConstructionMode.UNORDERED:
        count = len(normalized_source)
        for index_a in range(count):
            start_b = index_a if policy.self_pair_mode is SelfPairMode.INCLUDE else index_a + 1
            for index_b in range(start_b, count):
                source = normalized_source[index_a]
                target = normalized_target[index_b]
                items.append(
                    ZeroAriesPart(
                        source_name=str(source["name"]),
                        target_name=str(target["name"]),
                        longitude_deg=_normalize_angle_deg(float(source["degree"]) - float(target["degree"])),
                    )
                )
    else:
        for source in normalized_source:
            for target in normalized_target:
                if policy.self_pair_mode is SelfPairMode.EXCLUDE and str(source["name"]) == str(target["name"]):
                    continue
                items.append(
                    ZeroAriesPart(
                        source_name=str(source["name"]),
                        target_name=str(target["name"]),
                        longitude_deg=_normalize_angle_deg(float(source["degree"]) - float(target["degree"])),
                    )
                )
    return ZeroAriesPartsSet(
        policy=policy,
        source_body_names=tuple(str(item["name"]) for item in normalized_source),
        target_body_names=tuple(str(item["name"]) for item in normalized_target),
        parts=tuple(items),
    )


def _compute_components(
    longitudes_deg: tuple[float, ...],
    *,
    harmonic_domain: HarmonicDomain,
    normalization_mode: HarmonicVectorNormalizationMode,
) -> tuple[HarmonicVectorComponent, ...]:
    point_count = len(longitudes_deg)
    components: list[HarmonicVectorComponent] = []
    for harmonic in harmonic_domain.harmonics:
        total = complex(0.0, 0.0)
        for longitude in longitudes_deg:
            angle = math.radians(harmonic * longitude)
            total += complex(math.cos(angle), math.sin(angle))
        if normalization_mode is HarmonicVectorNormalizationMode.MEAN_RESULTANT:
            total /= point_count
        amplitude = abs(total)
        phase_deg = 0.0 if amplitude < 1.0e-12 else _normalize_angle_deg(math.degrees(math.atan2(total.imag, total.real)))
        components.append(HarmonicVectorComponent(harmonic=harmonic, amplitude=amplitude, phase_deg=phase_deg))
    return tuple(components)


def _compute_intensity_components(
    harmonic_number: int,
    *,
    policy: HarmogramIntensityPolicy,
) -> tuple[float, tuple[IntensitySpectrumComponent, ...]]:
    sample_count = policy.sample_count
    samples = tuple(
        _intensity_at_angle_deg((360.0 * index) / sample_count, harmonic_number, policy)
        for index in range(sample_count)
    )
    harmonic_zero_amplitude = sum(samples) / sample_count
    components: list[IntensitySpectrumComponent] = []
    for harmonic in policy.harmonic_domain.harmonics:
        total = complex(0.0, 0.0)
        for index, sample in enumerate(samples):
            angle = math.radians((360.0 * index) / sample_count)
            total += sample * complex(math.cos(-harmonic * angle), math.sin(-harmonic * angle))
        total /= sample_count
        amplitude = abs(total)
        phase_deg = 0.0 if amplitude < 1.0e-12 else _normalize_angle_deg(math.degrees(math.atan2(total.imag, total.real)))
        components.append(IntensitySpectrumComponent(harmonic=harmonic, amplitude=amplitude, phase_deg=phase_deg))
    return harmonic_zero_amplitude, tuple(components)


def point_set_harmonic_vector(
    positions: list[dict],
    *,
    policy: PointSetHarmonicVectorPolicy | None = None,
) -> PointSetHarmonicVector:
    resolved_policy = PointSetHarmonicVectorPolicy() if policy is None else policy
    normalized = _normalize_positions(positions)
    longitudes_deg = tuple(float(item["degree"]) for item in normalized)
    point_count = len(longitudes_deg)
    harmonic_zero_amplitude = float(point_count) if resolved_policy.normalization_mode is HarmonicVectorNormalizationMode.RAW_SUM else 1.0
    return PointSetHarmonicVector(
        policy=resolved_policy,
        body_names=tuple(str(item["name"]) for item in normalized),
        point_count=point_count,
        harmonic_zero_amplitude=harmonic_zero_amplitude,
        components=_compute_components(
            longitudes_deg,
            harmonic_domain=resolved_policy.harmonic_domain,
            normalization_mode=resolved_policy.normalization_mode,
        ),
    )


def parts_from_zero_aries(
    positions: list[dict],
    *,
    policy: ZeroAriesPartsPolicy | None = None,
) -> ZeroAriesPartsSet:
    resolved_policy = ZeroAriesPartsPolicy() if policy is None else policy
    return _parts_from_position_sets(positions, positions, policy=resolved_policy)


def zero_aries_parts_harmonic_vector(
    positions: list[dict] | None = None,
    *,
    source_positions: list[dict] | None = None,
    target_positions: list[dict] | None = None,
    parts_policy: ZeroAriesPartsPolicy | None = None,
    vector_policy: PointSetHarmonicVectorPolicy | None = None,
) -> ZeroAriesPartsHarmonicVector:
    resolved_parts_policy = ZeroAriesPartsPolicy() if parts_policy is None else parts_policy
    resolved_vector_policy = PointSetHarmonicVectorPolicy() if vector_policy is None else vector_policy
    if positions is not None:
        if source_positions is not None or target_positions is not None:
            raise ValueError("pass either positions or source_positions/target_positions, not both")
        parts_set = parts_from_zero_aries(positions, policy=resolved_parts_policy)
    else:
        if source_positions is None or target_positions is None:
            raise ValueError("source_positions and target_positions are required for relational zero-Aries parts vectors")
        parts_set = _parts_from_position_sets(source_positions, target_positions, policy=resolved_parts_policy)
    harmonic_zero_amplitude = (
        float(parts_set.parts_count)
        if resolved_vector_policy.normalization_mode is HarmonicVectorNormalizationMode.RAW_SUM
        else 1.0
    )
    return ZeroAriesPartsHarmonicVector(
        vector_policy=resolved_vector_policy,
        parts_policy=resolved_parts_policy,
        source_body_names=parts_set.source_body_names,
        target_body_names=parts_set.target_body_names,
        parts_count=parts_set.parts_count,
        harmonic_zero_amplitude=harmonic_zero_amplitude,
        components=_compute_components(
            tuple(part.longitude_deg for part in parts_set.parts),
            harmonic_domain=resolved_vector_policy.harmonic_domain,
            normalization_mode=resolved_vector_policy.normalization_mode,
        ),
    )


def harmonic_vector(
    positions: list[dict],
    *,
    policy: PointSetHarmonicVectorPolicy | None = None,
) -> PointSetHarmonicVector:
    return point_set_harmonic_vector(positions, policy=policy)


def intensity_function_spectrum(
    harmonic_number: int,
    *,
    policy: HarmogramIntensityPolicy | None = None,
) -> IntensityFunctionSpectrum:
    resolved_policy = HarmogramIntensityPolicy() if policy is None else policy
    if harmonic_number <= 0:
        raise ValueError("harmonic_number must be positive")
    harmonic_zero_amplitude, components = _compute_intensity_components(harmonic_number, policy=resolved_policy)
    return IntensityFunctionSpectrum(
        policy=resolved_policy,
        harmonic_number=harmonic_number,
        realization_mode=IntensitySpectrumRealizationMode.NUMERICAL_TRUNCATED,
        harmonic_zero_amplitude=harmonic_zero_amplitude,
        components=components,
    )


def project_harmogram_strength(
    source_vector: PointSetHarmonicVector | ZeroAriesPartsHarmonicVector,
    intensity_spectrum: IntensityFunctionSpectrum,
) -> HarmogramProjection:
    source_domain = _source_harmonic_domain(source_vector)
    if source_domain != intensity_spectrum.policy.harmonic_domain:
        raise ValueError("source_vector and intensity_spectrum must share the same harmonic domain")
    normalization_mode = _source_normalization_mode(source_vector)
    harmonic_zero_contribution = source_vector.harmonic_zero_amplitude * intensity_spectrum.harmonic_zero_amplitude
    terms: list[HarmogramProjectionTerm] = []
    total_strength = harmonic_zero_contribution
    for harmonic in source_domain.harmonics:
        source_component = source_vector.get_component(harmonic)
        intensity_component = intensity_spectrum.get_component(harmonic)
        term_value = 2.0 * (
            _component_to_complex(source_component.amplitude, source_component.phase_deg)
            * _component_to_complex(intensity_component.amplitude, intensity_component.phase_deg)
        ).real
        total_strength += term_value
        terms.append(
            HarmogramProjectionTerm(
                harmonic=harmonic,
                source_amplitude=source_component.amplitude,
                source_phase_deg=source_component.phase_deg,
                intensity_amplitude=intensity_component.amplitude,
                intensity_phase_deg=intensity_component.phase_deg,
                signed_contribution=term_value,
            )
        )
    realization_mode = (
        HarmogramProjectionRealizationMode.NUMERICAL_TRUNCATED
        if intensity_spectrum.realization_mode is IntensitySpectrumRealizationMode.NUMERICAL_TRUNCATED
        else HarmogramProjectionRealizationMode.FINITE_CLOSED_FORM
    )
    return HarmogramProjection(
        source_vector=source_vector,
        intensity_spectrum=intensity_spectrum,
        normalization_mode=normalization_mode,
        realization_mode=realization_mode,
        harmonic_zero_contribution=harmonic_zero_contribution,
        total_strength=total_strength,
        terms=tuple(terms),
    )


def harmogram_trace(
    samples: list[dict],
    *,
    harmonic_numbers: tuple[int, ...] | list[int] | None = None,
    policy: HarmogramPolicy | None = None,
) -> HarmogramTrace:
    resolved_policy = HarmogramPolicy() if policy is None else policy
    normalized_samples = _normalize_trace_samples(samples)
    resolved_harmonics = tuple(int(value) for value in (harmonic_numbers if harmonic_numbers is not None else (1,)))
    if not resolved_harmonics:
        raise ValueError("harmonic_numbers must be non-empty")
    if any(harmonic <= 0 for harmonic in resolved_harmonics):
        raise ValueError("harmonic_numbers must contain only positive integers")
    if len(set(resolved_harmonics)) != len(resolved_harmonics):
        raise ValueError("harmonic_numbers must be unique")
    if resolved_policy.output_mode is HarmogramOutputMode.SINGLE_HARMONIC and len(resolved_harmonics) != 1:
        raise ValueError("single-harmonic traces require exactly one harmonic number")
    if resolved_policy.sampling_policy.sample_count is not None and len(normalized_samples) != resolved_policy.sampling_policy.sample_count:
        raise ValueError("samples must match the declared sampling policy sample_count")
    sample_times = tuple(sample_time for sample_time, _ in normalized_samples)
    source_vectors: list[ZeroAriesPartsHarmonicVector] = []
    for _, sample_payload in normalized_samples:
        if resolved_policy.trace_family is HarmogramTraceFamily.DYNAMIC_ZERO_ARIES_PARTS:
            if not isinstance(sample_payload, list):
                raise ValueError("dynamic zero-Aries-parts samples require 'positions'")
            positions = sample_payload
            source_vectors.append(
                zero_aries_parts_harmonic_vector(
                    positions=positions,
                    parts_policy=resolved_policy.parts_policy,
                    vector_policy=resolved_policy.point_set_policy,
                )
            )
        elif resolved_policy.trace_family is HarmogramTraceFamily.TRANSIT_TO_NATAL_ZERO_ARIES_PARTS:
            if not isinstance(sample_payload, dict):
                raise ValueError("transit-to-natal zero-Aries-parts samples require relational position sets")
            if not isinstance(sample_payload.get("transit_positions"), list) or not sample_payload["transit_positions"]:
                raise ValueError("transit-to-natal zero-Aries-parts samples require non-empty transit_positions")
            if not isinstance(sample_payload.get("natal_positions"), list) or not sample_payload["natal_positions"]:
                raise ValueError("transit-to-natal zero-Aries-parts samples require non-empty natal_positions")
            source_vectors.append(
                zero_aries_parts_harmonic_vector(
                    source_positions=sample_payload["transit_positions"],
                    target_positions=sample_payload["natal_positions"],
                    parts_policy=resolved_policy.parts_policy,
                    vector_policy=resolved_policy.point_set_policy,
                )
            )
        elif resolved_policy.trace_family is HarmogramTraceFamily.DIRECTED_TO_NATAL_ZERO_ARIES_PARTS:
            if not isinstance(sample_payload, dict):
                raise ValueError("directed-to-natal zero-Aries-parts samples require relational position sets")
            if not isinstance(sample_payload.get("directed_positions"), list) or not sample_payload["directed_positions"]:
                raise ValueError("directed-to-natal zero-Aries-parts samples require non-empty directed_positions")
            if not isinstance(sample_payload.get("natal_positions"), list) or not sample_payload["natal_positions"]:
                raise ValueError("directed-to-natal zero-Aries-parts samples require non-empty natal_positions")
            source_vectors.append(
                zero_aries_parts_harmonic_vector(
                    source_positions=sample_payload["directed_positions"],
                    target_positions=sample_payload["natal_positions"],
                    parts_policy=resolved_policy.parts_policy,
                    vector_policy=resolved_policy.point_set_policy,
                )
            )
        elif resolved_policy.trace_family is HarmogramTraceFamily.PROGRESSED_TO_NATAL_ZERO_ARIES_PARTS:
            if not isinstance(sample_payload, dict):
                raise ValueError("progressed-to-natal zero-Aries-parts samples require relational position sets")
            if not isinstance(sample_payload.get("progressed_positions"), list) or not sample_payload["progressed_positions"]:
                raise ValueError("progressed-to-natal zero-Aries-parts samples require non-empty progressed_positions")
            if not isinstance(sample_payload.get("natal_positions"), list) or not sample_payload["natal_positions"]:
                raise ValueError("progressed-to-natal zero-Aries-parts samples require non-empty natal_positions")
            source_vectors.append(
                zero_aries_parts_harmonic_vector(
                    source_positions=sample_payload["progressed_positions"],
                    target_positions=sample_payload["natal_positions"],
                    parts_policy=resolved_policy.parts_policy,
                    vector_policy=resolved_policy.point_set_policy,
                )
            )
        else:
            raise ValueError("unsupported harmogram trace family")
    series_items: list[HarmogramTraceSeries] = []
    for harmonic_number in resolved_harmonics:
        intensity = intensity_function_spectrum(harmonic_number, policy=resolved_policy.intensity_policy)
        trace_samples: list[HarmogramTraceSample] = []
        for sample_index, ((sample_time, _), source_vector) in enumerate(zip(normalized_samples, source_vectors)):
            projection = project_harmogram_strength(source_vector, intensity)
            trace_samples.append(
                HarmogramTraceSample(
                    sample_index=sample_index,
                    sample_time=sample_time,
                    source_vector=source_vector,
                    projection=projection,
                    total_strength=projection.total_strength,
                )
            )
        series_items.append(
            HarmogramTraceSeries(
                harmonic_number=harmonic_number,
                intensity_spectrum=intensity,
                samples=tuple(trace_samples),
            )
        )
    return HarmogramTrace(
        policy=resolved_policy,
        interval_start=sample_times[0],
        interval_stop=sample_times[-1],
        sample_times=sample_times,
        series=tuple(series_items),
    )
