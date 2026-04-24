"""
Moira — Harmogram Research Tools
Governs analytical and comparison functions for harmogram research, including dominant harmonic analysis and spectrum comparison utilities.

Boundary: owns research and analysis functions for harmogram data. Delegates core computations to compute module and data structures to models.

Import-time side effects: None

External dependencies:
    - harmograms.models for data structure definitions

Public surface:
    dominant_harmonic_contributors, compare_intensity_spectra, compare_trace_series
"""

from .models import (
    HarmogramDominantTerm,
    HarmogramProjection,
    HarmogramTraceSeries,
    HarmogramTraceSeriesComparison,
    HarmogramTraceSeriesComparisonSample,
    IntensityFunctionSpectrum,
    IntensitySpectrumComparison,
    IntensitySpectrumComparisonTerm,
)


def dominant_harmonic_contributors(
    projection: HarmogramProjection,
    *,
    limit: int | None = None,
) -> tuple[HarmogramDominantTerm, ...]:
    if limit is not None and limit <= 0:
        raise ValueError("limit must be positive when provided")
    ranked = sorted(
        (
            HarmogramDominantTerm(
                harmonic=term.harmonic,
                absolute_contribution=abs(term.signed_contribution),
                signed_contribution=term.signed_contribution,
            )
            for term in projection.terms
        ),
        key=lambda item: (-item.absolute_contribution, item.harmonic),
    )
    return tuple(ranked if limit is None else ranked[:limit])


def compare_intensity_spectra(
    left: IntensityFunctionSpectrum,
    right: IntensityFunctionSpectrum,
) -> IntensitySpectrumComparison:
    if left.harmonic_number != right.harmonic_number:
        raise ValueError("left and right intensity spectra must share the same harmonic_number")
    if left.policy.harmonic_domain != right.policy.harmonic_domain:
        raise ValueError("left and right intensity spectra must share the same harmonic domain")
    terms: list[IntensitySpectrumComparisonTerm] = []
    max_absolute_delta = 0.0
    for harmonic in left.policy.harmonic_domain.harmonics:
        left_component = left.get_component(harmonic)
        right_component = right.get_component(harmonic)
        amplitude_delta = right_component.amplitude - left_component.amplitude
        max_absolute_delta = max(max_absolute_delta, abs(amplitude_delta))
        terms.append(
            IntensitySpectrumComparisonTerm(
                harmonic=harmonic,
                left_amplitude=left_component.amplitude,
                right_amplitude=right_component.amplitude,
                amplitude_delta=amplitude_delta,
            )
        )
    return IntensitySpectrumComparison(left=left, right=right, max_absolute_delta=max_absolute_delta, terms=tuple(terms))


def compare_trace_series(
    left: HarmogramTraceSeries,
    right: HarmogramTraceSeries,
) -> HarmogramTraceSeriesComparison:
    if left.harmonic_number != right.harmonic_number:
        raise ValueError("left and right trace series must share the same harmonic_number")
    left_times = tuple(sample.sample_time for sample in left.samples)
    right_times = tuple(sample.sample_time for sample in right.samples)
    if left_times != right_times:
        raise ValueError("left and right trace series must share the same sample times")
    samples: list[HarmogramTraceSeriesComparisonSample] = []
    max_absolute_delta = 0.0
    for sample_index, (left_sample, right_sample) in enumerate(zip(left.samples, right.samples)):
        delta = right_sample.total_strength - left_sample.total_strength
        max_absolute_delta = max(max_absolute_delta, abs(delta))
        samples.append(
            HarmogramTraceSeriesComparisonSample(
                sample_index=sample_index,
                sample_time=left_sample.sample_time,
                left_strength=left_sample.total_strength,
                right_strength=right_sample.total_strength,
                delta=delta,
            )
        )
    return HarmogramTraceSeriesComparison(left=left, right=right, max_absolute_delta=max_absolute_delta, samples=tuple(samples))
