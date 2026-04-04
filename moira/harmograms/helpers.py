from __future__ import annotations

import math

from .models import (
    GaussianWidthParameterMode,
    HarmogramIntensityPolicy,
    HarmogramOrbMode,
    HarmogramOrbScalingMode,
    HarmonicDomain,
    HarmonicVectorComponent,
    HarmonicVectorNormalizationMode,
    PointSetHarmonicVector,
    ZeroAriesPartsHarmonicVector,
)


def _normalize_angle_deg(angle_deg: float) -> float:
    normalized = angle_deg % 360.0
    if abs(normalized - 360.0) < 1.0e-12:
        return 0.0
    return normalized


def _signed_smallest_angle_deg(angle_deg: float) -> float:
    normalized = _normalize_angle_deg(angle_deg)
    if normalized >= 180.0:
        normalized -= 360.0
    return normalized


def _normalize_positions(positions: list[dict]) -> list[dict[str, float | str]]:
    if not isinstance(positions, list) or not positions:
        raise ValueError("positions must be a non-empty list of dictionaries")

    normalized: list[dict[str, float | str]] = []
    seen_names: set[str] = set()
    for index, pos in enumerate(positions):
        if not isinstance(pos, dict):
            raise ValueError(f"positions[{index}] must be a dictionary")
        name = pos.get("name")
        if not isinstance(name, str) or not name.strip():
            raise ValueError(f"positions[{index}].name must be a non-empty string")
        normalized_name = name.strip()
        if normalized_name in seen_names:
            raise ValueError(f"positions contains duplicate entry for {normalized_name!r}")
        seen_names.add(normalized_name)
        try:
            degree = float(pos.get("degree"))
        except (TypeError, ValueError):
            raise ValueError(f"positions[{index}].degree must be a real number") from None
        if not math.isfinite(degree):
            raise ValueError(f"positions[{index}].degree must be finite")
        normalized.append({"name": normalized_name, "degree": _normalize_angle_deg(degree)})
    return normalized


def _validate_component_domain(domain: HarmonicDomain, components: tuple[HarmonicVectorComponent, ...]) -> None:
    actual_harmonics = tuple(component.harmonic for component in components)
    if actual_harmonics != domain.harmonics:
        raise ValueError("harmonic vector components must align exactly with the admitted harmonic domain")


def _source_harmonic_domain(source_vector: PointSetHarmonicVector | ZeroAriesPartsHarmonicVector) -> HarmonicDomain:
    if isinstance(source_vector, PointSetHarmonicVector):
        return source_vector.policy.harmonic_domain
    return source_vector.vector_policy.harmonic_domain


def _source_normalization_mode(
    source_vector: PointSetHarmonicVector | ZeroAriesPartsHarmonicVector,
) -> HarmonicVectorNormalizationMode:
    if isinstance(source_vector, PointSetHarmonicVector):
        return source_vector.policy.normalization_mode
    return source_vector.vector_policy.normalization_mode


def _component_to_complex(amplitude: float, phase_deg: float) -> complex:
    angle = math.radians(phase_deg)
    return amplitude * complex(math.cos(angle), math.sin(angle))


def _normalize_trace_samples(samples: list[dict]) -> tuple[tuple[float, object], ...]:
    if not isinstance(samples, list) or not samples:
        raise ValueError("samples must be a non-empty list of dictionaries")

    normalized: list[tuple[float, object]] = []
    previous_time: float | None = None
    for index, sample in enumerate(samples):
        if not isinstance(sample, dict):
            raise ValueError(f"samples[{index}] must be a dictionary")
        try:
            sample_time = float(sample.get("time"))
        except (TypeError, ValueError):
            raise ValueError(f"samples[{index}].time must be a real number") from None
        if not math.isfinite(sample_time):
            raise ValueError(f"samples[{index}].time must be finite")
        if previous_time is not None and sample_time <= previous_time:
            raise ValueError("samples must be strictly increasing by time")
        if "positions" in sample:
            positions = sample.get("positions")
            if not isinstance(positions, list) or not positions:
                raise ValueError(f"samples[{index}].positions must be a non-empty list")
            normalized.append((sample_time, positions))
        else:
            payload = {key: value for key, value in sample.items() if key != "time"}
            if not payload:
                raise ValueError(f"samples[{index}] must contain positions or relational position sets")
            normalized.append((sample_time, payload))
        previous_time = sample_time
    return tuple(normalized)


def _peak_centers_deg(harmonic_number: int, policy: HarmogramIntensityPolicy) -> tuple[float, ...]:
    step = 360.0 / harmonic_number
    if policy.include_conjunction:
        return tuple(index * step for index in range(harmonic_number))
    return tuple(index * step for index in range(1, harmonic_number))


def _peak_half_width_deg(harmonic_number: int, policy: HarmogramIntensityPolicy) -> float:
    if policy.orb_scaling_mode is HarmogramOrbScalingMode.EQUATED_TO_HARMONIC_ONE:
        return policy.orb_width_deg / harmonic_number
    raise ValueError("unsupported intensity policy orb scaling mode")


def _gaussian_sigma_deg(harmonic_number: int, policy: HarmogramIntensityPolicy) -> float:
    if policy.gaussian_width_deg is None:
        raise ValueError("gaussian intensity policy requires gaussian_width_deg")
    width_deg = policy.gaussian_width_deg / harmonic_number
    if policy.gaussian_width_parameter_mode is GaussianWidthParameterMode.SIGMA:
        return width_deg
    return width_deg / (2.0 * math.sqrt(2.0 * math.log(2.0)))


def _intensity_at_angle_deg(angle_deg: float, harmonic_number: int, policy: HarmogramIntensityPolicy) -> float:
    centers_deg = _peak_centers_deg(harmonic_number, policy)
    half_width_deg = _peak_half_width_deg(harmonic_number, policy)
    if not centers_deg:
        return 0.0

    best = 0.0
    for center_deg in centers_deg:
        delta = abs(_signed_smallest_angle_deg(angle_deg - center_deg))
        if delta > half_width_deg:
            continue
        if policy.orb_mode is HarmogramOrbMode.COSINE_BELL:
            value = 0.5 * (1.0 + math.cos(math.pi * delta / half_width_deg))
        elif policy.orb_mode is HarmogramOrbMode.TOP_HAT:
            value = 1.0
        elif policy.orb_mode is HarmogramOrbMode.TRIANGULAR:
            value = 1.0 - (delta / half_width_deg)
        elif policy.orb_mode is HarmogramOrbMode.GAUSSIAN:
            sigma_deg = _gaussian_sigma_deg(harmonic_number, policy)
            value = math.exp(-0.5 * (delta / sigma_deg) ** 2)
        else:
            raise ValueError("unsupported intensity policy orb mode")
        if value > best:
            best = value
    return best
