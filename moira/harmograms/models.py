from __future__ import annotations

import math
from dataclasses import dataclass, field
from enum import StrEnum


class HarmonicVectorNormalizationMode(StrEnum):
    RAW_SUM = "raw_sum"
    MEAN_RESULTANT = "mean_resultant"


class ZeroAriesPairConstructionMode(StrEnum):
    ORDERED = "ordered"
    UNORDERED = "unordered"


class SelfPairMode(StrEnum):
    INCLUDE = "include"
    EXCLUDE = "exclude"


class HarmogramIntensityFamily(StrEnum):
    COSINE_BELL_HARMONIC_ASPECTS = "cosine_bell_harmonic_aspects"
    TOP_HAT_HARMONIC_ASPECTS = "top_hat_harmonic_aspects"
    TRIANGULAR_HARMONIC_ASPECTS = "triangular_harmonic_aspects"
    GAUSSIAN_HARMONIC_ASPECTS = "gaussian_harmonic_aspects"


class HarmogramOrbMode(StrEnum):
    COSINE_BELL = "cosine_bell"
    TOP_HAT = "top_hat"
    TRIANGULAR = "triangular"
    GAUSSIAN = "gaussian"


class GaussianWidthParameterMode(StrEnum):
    SIGMA = "sigma"
    FWHM = "fwhm"


class HarmogramOrbScalingMode(StrEnum):
    EQUATED_TO_HARMONIC_ONE = "equated_to_harmonic_one"


class HarmogramSymmetryMode(StrEnum):
    STAR_SYMMETRIC = "star_symmetric"
    CONJUNCTION_EXCLUDED = "conjunction_excluded"


class IntensityNormalizationMode(StrEnum):
    PEAK_ONE = "peak_one"


class IntensitySpectrumRealizationMode(StrEnum):
    NUMERICAL_TRUNCATED = "numerical_truncated"


class HarmogramProjectionRealizationMode(StrEnum):
    EXACT_ALGEBRAIC_IDENTITY = "exact_algebraic_identity"
    FINITE_CLOSED_FORM = "finite_closed_form"
    NUMERICAL_TRUNCATED = "numerical_truncated"


class HarmogramSamplingMode(StrEnum):
    EXPLICIT_FIXED_STEP = "explicit_fixed_step"


class HarmogramOutputMode(StrEnum):
    SINGLE_HARMONIC = "single_harmonic"
    MULTI_HARMONIC_FAMILY = "multi_harmonic_family"


class HarmogramChartDomain(StrEnum):
    STATIC_CHART_STRENGTH = "static_chart_strength"
    DYNAMIC_SKY_ONLY_TRACE = "dynamic_sky_only_trace"
    TRANSIT_TO_NATAL_TRACE = "transit_to_natal_trace"
    DIRECTED_OR_PROGRESSED_TRACE = "directed_or_progressed_trace"


class HarmogramTraceFamily(StrEnum):
    DYNAMIC_ZERO_ARIES_PARTS = "dynamic_zero_aries_parts"
    TRANSIT_TO_NATAL_ZERO_ARIES_PARTS = "transit_to_natal_zero_aries_parts"
    DIRECTED_TO_NATAL_ZERO_ARIES_PARTS = "directed_to_natal_zero_aries_parts"
    PROGRESSED_TO_NATAL_ZERO_ARIES_PARTS = "progressed_to_natal_zero_aries_parts"


@dataclass(frozen=True, slots=True)
class HarmonicDomain:
    harmonic_start: int = 1
    harmonic_stop: int = 12

    def __post_init__(self) -> None:
        if self.harmonic_start <= 0:
            raise ValueError("harmonic domain harmonic_start must be positive")
        if self.harmonic_stop < self.harmonic_start:
            raise ValueError("harmonic domain harmonic_stop must be >= harmonic_start")

    @property
    def harmonics(self) -> tuple[int, ...]:
        return tuple(range(self.harmonic_start, self.harmonic_stop + 1))


@dataclass(frozen=True, slots=True)
class PointSetHarmonicVectorPolicy:
    normalization_mode: HarmonicVectorNormalizationMode = HarmonicVectorNormalizationMode.MEAN_RESULTANT
    harmonic_domain: HarmonicDomain = field(default_factory=HarmonicDomain)


@dataclass(frozen=True, slots=True)
class ZeroAriesPartsPolicy:
    pair_construction_mode: ZeroAriesPairConstructionMode = ZeroAriesPairConstructionMode.ORDERED
    self_pair_mode: SelfPairMode = SelfPairMode.INCLUDE


@dataclass(frozen=True, slots=True)
class HarmogramIntensityPolicy:
    family: HarmogramIntensityFamily = HarmogramIntensityFamily.COSINE_BELL_HARMONIC_ASPECTS
    include_conjunction: bool = True
    orb_mode: HarmogramOrbMode = HarmogramOrbMode.COSINE_BELL
    orb_scaling_mode: HarmogramOrbScalingMode = HarmogramOrbScalingMode.EQUATED_TO_HARMONIC_ONE
    symmetry_mode: HarmogramSymmetryMode = HarmogramSymmetryMode.STAR_SYMMETRIC
    normalization_mode: IntensityNormalizationMode = IntensityNormalizationMode.PEAK_ONE
    harmonic_domain: HarmonicDomain = field(default_factory=HarmonicDomain)
    orb_width_deg: float = 24.0
    gaussian_width_parameter_mode: GaussianWidthParameterMode = GaussianWidthParameterMode.FWHM
    gaussian_width_deg: float | None = None
    sample_count: int = 4096

    def __post_init__(self) -> None:
        if self.orb_width_deg <= 0.0 or not math.isfinite(self.orb_width_deg):
            raise ValueError("intensity policy orb_width_deg must be finite and positive")
        if self.sample_count < 256:
            raise ValueError("intensity policy sample_count must be at least 256")
        if self.symmetry_mode is HarmogramSymmetryMode.STAR_SYMMETRIC and not self.include_conjunction:
            raise ValueError("star-symmetric intensity policy requires include_conjunction=True")
        if self.symmetry_mode is HarmogramSymmetryMode.CONJUNCTION_EXCLUDED and self.include_conjunction:
            raise ValueError("conjunction-excluded intensity policy requires include_conjunction=False")
        expected_orb_mode = {
            HarmogramIntensityFamily.COSINE_BELL_HARMONIC_ASPECTS: HarmogramOrbMode.COSINE_BELL,
            HarmogramIntensityFamily.TOP_HAT_HARMONIC_ASPECTS: HarmogramOrbMode.TOP_HAT,
            HarmogramIntensityFamily.TRIANGULAR_HARMONIC_ASPECTS: HarmogramOrbMode.TRIANGULAR,
            HarmogramIntensityFamily.GAUSSIAN_HARMONIC_ASPECTS: HarmogramOrbMode.GAUSSIAN,
        }[self.family]
        if self.orb_mode is not expected_orb_mode:
            raise ValueError("intensity policy orb_mode must match the admitted intensity family")
        if self.family is HarmogramIntensityFamily.GAUSSIAN_HARMONIC_ASPECTS:
            if self.gaussian_width_deg is None or self.gaussian_width_deg <= 0.0 or not math.isfinite(self.gaussian_width_deg):
                raise ValueError("gaussian intensity policy gaussian_width_deg must be finite and positive")
        elif self.gaussian_width_deg is not None:
            raise ValueError("gaussian_width_deg is only valid for gaussian intensity families")


@dataclass(frozen=True, slots=True)
class HarmogramSamplingPolicy:
    sampling_mode: HarmogramSamplingMode = HarmogramSamplingMode.EXPLICIT_FIXED_STEP
    sample_count: int | None = None

    def __post_init__(self) -> None:
        if self.sample_count is not None and self.sample_count <= 0:
            raise ValueError("harmogram sampling policy sample_count must be positive when provided")


@dataclass(frozen=True, slots=True)
class HarmogramPolicy:
    point_set_policy: PointSetHarmonicVectorPolicy = field(default_factory=PointSetHarmonicVectorPolicy)
    parts_policy: ZeroAriesPartsPolicy = field(default_factory=ZeroAriesPartsPolicy)
    intensity_policy: HarmogramIntensityPolicy = field(default_factory=HarmogramIntensityPolicy)
    sampling_policy: HarmogramSamplingPolicy = field(default_factory=HarmogramSamplingPolicy)
    output_mode: HarmogramOutputMode = HarmogramOutputMode.MULTI_HARMONIC_FAMILY
    chart_domain: HarmogramChartDomain = HarmogramChartDomain.DYNAMIC_SKY_ONLY_TRACE
    trace_family: HarmogramTraceFamily = HarmogramTraceFamily.DYNAMIC_ZERO_ARIES_PARTS

    def __post_init__(self) -> None:
        if self.trace_family is HarmogramTraceFamily.DYNAMIC_ZERO_ARIES_PARTS:
            if self.chart_domain is not HarmogramChartDomain.DYNAMIC_SKY_ONLY_TRACE:
                raise ValueError("dynamic zero-Aries-parts traces require chart_domain='dynamic_sky_only_trace'")
        elif self.trace_family is HarmogramTraceFamily.TRANSIT_TO_NATAL_ZERO_ARIES_PARTS:
            if self.chart_domain is not HarmogramChartDomain.TRANSIT_TO_NATAL_TRACE:
                raise ValueError("transit-to-natal zero-Aries-parts traces require chart_domain='transit_to_natal_trace'")
        elif self.trace_family in (
            HarmogramTraceFamily.DIRECTED_TO_NATAL_ZERO_ARIES_PARTS,
            HarmogramTraceFamily.PROGRESSED_TO_NATAL_ZERO_ARIES_PARTS,
        ):
            if self.chart_domain is not HarmogramChartDomain.DIRECTED_OR_PROGRESSED_TRACE:
                raise ValueError("directed/progressed zero-Aries-parts traces require chart_domain='directed_or_progressed_trace'")
        if self.point_set_policy.harmonic_domain != self.intensity_policy.harmonic_domain:
            raise ValueError("harmogram policy point_set_policy and intensity_policy must share the same harmonic domain")


@dataclass(frozen=True, slots=True)
class HarmonicVectorComponent:
    harmonic: int
    amplitude: float
    phase_deg: float

    def __post_init__(self) -> None:
        if self.harmonic < 1:
            raise ValueError("harmonic vector component harmonic must be >= 1")
        if not math.isfinite(self.amplitude) or self.amplitude < 0.0:
            raise ValueError("harmonic vector component amplitude must be finite and non-negative")
        if not math.isfinite(self.phase_deg) or not 0.0 <= self.phase_deg < 360.0:
            raise ValueError("harmonic vector component phase_deg must be finite and in [0, 360)")

    @property
    def amplitude_squared(self) -> float:
        return self.amplitude * self.amplitude


@dataclass(frozen=True, slots=True)
class IntensitySpectrumComponent:
    harmonic: int
    amplitude: float
    phase_deg: float

    def __post_init__(self) -> None:
        if self.harmonic < 1:
            raise ValueError("intensity spectrum component harmonic must be >= 1")
        if not math.isfinite(self.amplitude) or self.amplitude < 0.0:
            raise ValueError("intensity spectrum component amplitude must be finite and non-negative")
        if not math.isfinite(self.phase_deg) or not 0.0 <= self.phase_deg < 360.0:
            raise ValueError("intensity spectrum component phase_deg must be finite and in [0, 360)")


@dataclass(frozen=True, slots=True)
class PointSetHarmonicVector:
    policy: PointSetHarmonicVectorPolicy
    body_names: tuple[str, ...]
    point_count: int
    harmonic_zero_amplitude: float
    components: tuple[HarmonicVectorComponent, ...] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        from .helpers import _validate_component_domain

        _validate_component_domain(self.policy.harmonic_domain, self.components)
        if self.point_count <= 0:
            raise ValueError("point-set harmonic vector point_count must be positive")
        if len(self.body_names) != self.point_count:
            raise ValueError("point-set harmonic vector body_names must align with point_count")
        if len(set(self.body_names)) != len(self.body_names):
            raise ValueError("point-set harmonic vector body_names must be unique")
        expected_zero = (
            float(self.point_count)
            if self.policy.normalization_mode is HarmonicVectorNormalizationMode.RAW_SUM
            else 1.0
        )
        if abs(self.harmonic_zero_amplitude - expected_zero) > 1.0e-12:
            raise ValueError("point-set harmonic vector harmonic_zero_amplitude must match the active normalization mode")

    def get_component(self, harmonic: int) -> HarmonicVectorComponent:
        index = harmonic - self.policy.harmonic_domain.harmonic_start
        if index < 0 or index >= len(self.components):
            raise KeyError("harmonic vector component not found")
        return self.components[index]


@dataclass(frozen=True, slots=True)
class ZeroAriesPart:
    source_name: str
    target_name: str
    longitude_deg: float

    def __post_init__(self) -> None:
        if not self.source_name or not self.target_name:
            raise ValueError("zero-Aries part names must be non-empty")
        if not math.isfinite(self.longitude_deg) or not 0.0 <= self.longitude_deg < 360.0:
            raise ValueError("zero-Aries part longitude_deg must be finite and in [0, 360)")


@dataclass(frozen=True, slots=True)
class ZeroAriesPartsSet:
    policy: ZeroAriesPartsPolicy
    source_body_names: tuple[str, ...]
    target_body_names: tuple[str, ...]
    parts: tuple[ZeroAriesPart, ...] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        if not self.source_body_names:
            raise ValueError("zero-Aries parts set source_body_names must be non-empty")
        if len(set(self.source_body_names)) != len(self.source_body_names):
            raise ValueError("zero-Aries parts set source_body_names must be unique")
        if not self.target_body_names:
            raise ValueError("zero-Aries parts set target_body_names must be non-empty")
        if len(set(self.target_body_names)) != len(self.target_body_names):
            raise ValueError("zero-Aries parts set target_body_names must be unique")

    @property
    def source_point_count(self) -> int:
        return len(self.source_body_names)

    @property
    def target_point_count(self) -> int:
        return len(self.target_body_names)

    @property
    def parts_count(self) -> int:
        return len(self.parts)


@dataclass(frozen=True, slots=True)
class ZeroAriesPartsHarmonicVector:
    vector_policy: PointSetHarmonicVectorPolicy
    parts_policy: ZeroAriesPartsPolicy
    source_body_names: tuple[str, ...]
    target_body_names: tuple[str, ...]
    parts_count: int
    harmonic_zero_amplitude: float
    components: tuple[HarmonicVectorComponent, ...] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        from .helpers import _validate_component_domain

        _validate_component_domain(self.vector_policy.harmonic_domain, self.components)
        if not self.source_body_names:
            raise ValueError("zero-Aries parts harmonic vector source_body_names must be non-empty")
        if len(set(self.source_body_names)) != len(self.source_body_names):
            raise ValueError("zero-Aries parts harmonic vector source_body_names must be unique")
        if not self.target_body_names:
            raise ValueError("zero-Aries parts harmonic vector target_body_names must be non-empty")
        if len(set(self.target_body_names)) != len(self.target_body_names):
            raise ValueError("zero-Aries parts harmonic vector target_body_names must be unique")
        if self.parts_count <= 0:
            raise ValueError("zero-Aries parts harmonic vector parts_count must be positive")
        expected_zero = (
            float(self.parts_count)
            if self.vector_policy.normalization_mode is HarmonicVectorNormalizationMode.RAW_SUM
            else 1.0
        )
        if abs(self.harmonic_zero_amplitude - expected_zero) > 1.0e-12:
            raise ValueError("zero-Aries parts harmonic vector harmonic_zero_amplitude must match the active normalization mode")

    def get_component(self, harmonic: int) -> HarmonicVectorComponent:
        index = harmonic - self.vector_policy.harmonic_domain.harmonic_start
        if index < 0 or index >= len(self.components):
            raise KeyError("harmonic vector component not found")
        return self.components[index]


@dataclass(frozen=True, slots=True)
class IntensityFunctionSpectrum:
    policy: HarmogramIntensityPolicy
    harmonic_number: int
    realization_mode: IntensitySpectrumRealizationMode
    harmonic_zero_amplitude: float
    components: tuple[IntensitySpectrumComponent, ...] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        if self.harmonic_number <= 0:
            raise ValueError("intensity function spectrum harmonic_number must be positive")
        actual_harmonics = tuple(component.harmonic for component in self.components)
        if actual_harmonics != self.policy.harmonic_domain.harmonics:
            raise ValueError("intensity function spectrum components must align exactly with the admitted harmonic domain")
        if not math.isfinite(self.harmonic_zero_amplitude) or self.harmonic_zero_amplitude < 0.0:
            raise ValueError("intensity function spectrum harmonic_zero_amplitude must be finite and non-negative")

    def get_component(self, harmonic: int) -> IntensitySpectrumComponent:
        index = harmonic - self.policy.harmonic_domain.harmonic_start
        if index < 0 or index >= len(self.components):
            raise KeyError("intensity spectrum component not found")
        return self.components[index]


@dataclass(frozen=True, slots=True)
class HarmogramProjectionTerm:
    harmonic: int
    source_amplitude: float
    source_phase_deg: float
    intensity_amplitude: float
    intensity_phase_deg: float
    signed_contribution: float

    def __post_init__(self) -> None:
        if self.harmonic < 1:
            raise ValueError("harmogram projection term harmonic must be >= 1")
        for field_name in ("source_amplitude", "source_phase_deg", "intensity_amplitude", "intensity_phase_deg", "signed_contribution"):
            value = getattr(self, field_name)
            if not math.isfinite(value):
                raise ValueError(f"harmogram projection term {field_name} must be finite")
        if self.source_amplitude < 0.0:
            raise ValueError("harmogram projection term source_amplitude must be non-negative")
        if self.intensity_amplitude < 0.0:
            raise ValueError("harmogram projection term intensity_amplitude must be non-negative")
        if not 0.0 <= self.source_phase_deg < 360.0:
            raise ValueError("harmogram projection term source_phase_deg must be in [0, 360)")
        if not 0.0 <= self.intensity_phase_deg < 360.0:
            raise ValueError("harmogram projection term intensity_phase_deg must be in [0, 360)")


@dataclass(frozen=True, slots=True)
class HarmogramProjection:
    source_vector: PointSetHarmonicVector | ZeroAriesPartsHarmonicVector
    intensity_spectrum: IntensityFunctionSpectrum
    normalization_mode: HarmonicVectorNormalizationMode
    realization_mode: HarmogramProjectionRealizationMode
    harmonic_zero_contribution: float
    total_strength: float
    terms: tuple[HarmogramProjectionTerm, ...] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        from .helpers import _source_harmonic_domain, _source_normalization_mode

        source_domain = _source_harmonic_domain(self.source_vector)
        if source_domain != self.intensity_spectrum.policy.harmonic_domain:
            raise ValueError("harmogram projection source and intensity spectra must share the same harmonic domain")
        if self.normalization_mode is not _source_normalization_mode(self.source_vector):
            raise ValueError("harmogram projection normalization_mode must match the source vector")
        actual_harmonics = tuple(term.harmonic for term in self.terms)
        if actual_harmonics != source_domain.harmonics:
            raise ValueError("harmogram projection terms must align exactly with the admitted harmonic domain")
        if not math.isfinite(self.harmonic_zero_contribution):
            raise ValueError("harmogram projection harmonic_zero_contribution must be finite")
        if not math.isfinite(self.total_strength):
            raise ValueError("harmogram projection total_strength must be finite")

    def get_term(self, harmonic: int) -> HarmogramProjectionTerm:
        from .helpers import _source_harmonic_domain

        index = harmonic - _source_harmonic_domain(self.source_vector).harmonic_start
        if index < 0 or index >= len(self.terms):
            raise KeyError("harmogram projection term not found")
        return self.terms[index]


@dataclass(frozen=True, slots=True)
class HarmogramDominantTerm:
    harmonic: int
    absolute_contribution: float
    signed_contribution: float

    def __post_init__(self) -> None:
        if self.harmonic < 1:
            raise ValueError("harmogram dominant term harmonic must be >= 1")
        if not math.isfinite(self.absolute_contribution) or self.absolute_contribution < 0.0:
            raise ValueError("harmogram dominant term absolute_contribution must be finite and non-negative")
        if not math.isfinite(self.signed_contribution):
            raise ValueError("harmogram dominant term signed_contribution must be finite")


@dataclass(frozen=True, slots=True)
class IntensitySpectrumComparisonTerm:
    harmonic: int
    left_amplitude: float
    right_amplitude: float
    amplitude_delta: float

    def __post_init__(self) -> None:
        if self.harmonic < 1:
            raise ValueError("intensity spectrum comparison term harmonic must be >= 1")
        for field_name in ("left_amplitude", "right_amplitude", "amplitude_delta"):
            if not math.isfinite(getattr(self, field_name)):
                raise ValueError(f"intensity spectrum comparison term {field_name} must be finite")
        if self.left_amplitude < 0.0 or self.right_amplitude < 0.0:
            raise ValueError("intensity spectrum comparison term amplitudes must be non-negative")


@dataclass(frozen=True, slots=True)
class IntensitySpectrumComparison:
    left: IntensityFunctionSpectrum
    right: IntensityFunctionSpectrum
    max_absolute_delta: float
    terms: tuple[IntensitySpectrumComparisonTerm, ...] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        if self.left.harmonic_number != self.right.harmonic_number:
            raise ValueError("intensity spectrum comparison requires matching harmonic_number")
        if self.left.policy.harmonic_domain != self.right.policy.harmonic_domain:
            raise ValueError("intensity spectrum comparison requires matching harmonic domains")
        if not math.isfinite(self.max_absolute_delta) or self.max_absolute_delta < 0.0:
            raise ValueError("intensity spectrum comparison max_absolute_delta must be finite and non-negative")


@dataclass(frozen=True, slots=True)
class HarmogramTraceSeriesComparisonSample:
    sample_index: int
    sample_time: float
    left_strength: float
    right_strength: float
    delta: float

    def __post_init__(self) -> None:
        if self.sample_index < 0:
            raise ValueError("harmogram trace series comparison sample sample_index must be non-negative")
        for field_name in ("sample_time", "left_strength", "right_strength", "delta"):
            if not math.isfinite(getattr(self, field_name)):
                raise ValueError(f"harmogram trace series comparison sample {field_name} must be finite")


@dataclass(frozen=True, slots=True)
class HarmogramTraceSeriesComparison:
    left: HarmogramTraceSeries
    right: HarmogramTraceSeries
    max_absolute_delta: float
    samples: tuple[HarmogramTraceSeriesComparisonSample, ...] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        if self.left.harmonic_number != self.right.harmonic_number:
            raise ValueError("harmogram trace series comparison requires matching harmonic_number")
        if not math.isfinite(self.max_absolute_delta) or self.max_absolute_delta < 0.0:
            raise ValueError("harmogram trace series comparison max_absolute_delta must be finite and non-negative")


@dataclass(frozen=True, slots=True)
class HarmogramTraceSample:
    sample_index: int
    sample_time: float
    source_vector: ZeroAriesPartsHarmonicVector
    projection: HarmogramProjection
    total_strength: float

    def __post_init__(self) -> None:
        if self.sample_index < 0:
            raise ValueError("harmogram trace sample sample_index must be non-negative")
        if not math.isfinite(self.sample_time):
            raise ValueError("harmogram trace sample sample_time must be finite")
        if self.projection.source_vector is not self.source_vector:
            raise ValueError("harmogram trace sample projection must point to the stored source_vector")
        if abs(self.total_strength - self.projection.total_strength) > 1.0e-12:
            raise ValueError("harmogram trace sample total_strength must match the projection total_strength")


@dataclass(frozen=True, slots=True)
class HarmogramTraceSeries:
    harmonic_number: int
    intensity_spectrum: IntensityFunctionSpectrum
    samples: tuple[HarmogramTraceSample, ...] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        if self.harmonic_number <= 0:
            raise ValueError("harmogram trace series harmonic_number must be positive")
        if self.intensity_spectrum.harmonic_number != self.harmonic_number:
            raise ValueError("harmogram trace series intensity_spectrum must match harmonic_number")
        for sample in self.samples:
            if sample.projection.intensity_spectrum is not self.intensity_spectrum:
                raise ValueError("harmogram trace series samples must share the series intensity_spectrum")

    @property
    def strengths(self) -> tuple[float, ...]:
        return tuple(sample.total_strength for sample in self.samples)


@dataclass(frozen=True, slots=True)
class HarmogramTrace:
    policy: HarmogramPolicy
    interval_start: float
    interval_stop: float
    sample_times: tuple[float, ...]
    series: tuple[HarmogramTraceSeries, ...] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        if not self.sample_times:
            raise ValueError("harmogram trace sample_times must be non-empty")
        if not math.isfinite(self.interval_start) or not math.isfinite(self.interval_stop):
            raise ValueError("harmogram trace interval bounds must be finite")
        if self.interval_start > self.interval_stop:
            raise ValueError("harmogram trace interval_start must be <= interval_stop")
        if self.sample_times[0] != self.interval_start or self.sample_times[-1] != self.interval_stop:
            raise ValueError("harmogram trace interval bounds must agree with the first and last sample time")
        if any(b <= a for a, b in zip(self.sample_times, self.sample_times[1:])):
            raise ValueError("harmogram trace sample_times must be strictly increasing")
        if self.policy.sampling_policy.sample_count is not None and len(self.sample_times) != self.policy.sampling_policy.sample_count:
            raise ValueError("harmogram trace sample_times must match the declared sampling policy sample_count")
        if self.policy.output_mode is HarmogramOutputMode.SINGLE_HARMONIC and len(self.series) != 1:
            raise ValueError("single-harmonic traces must contain exactly one series")
        for trace_series in self.series:
            if tuple(sample.sample_time for sample in trace_series.samples) != self.sample_times:
                raise ValueError("each harmogram trace series must align exactly with trace sample_times")

    def get_series(self, harmonic_number: int) -> HarmogramTraceSeries:
        for trace_series in self.series:
            if trace_series.harmonic_number == harmonic_number:
                return trace_series
        raise KeyError("harmogram trace series not found")
