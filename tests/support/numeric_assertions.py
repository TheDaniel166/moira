"""Unit-aware and semantics-aware numeric assertions for scientific tests."""

from __future__ import annotations

import math
from collections.abc import Iterable
from dataclasses import dataclass
from enum import Enum
from itertools import islice
from numbers import Real


class NumericSemantics(Enum):
    """How a numerical residual is formed."""

    LINEAR = "linear"
    CIRCULAR = "circular"
    VECTOR_ANGLE = "vector-angle"
    EVENT_RESIDUAL = "event-residual"


class Unit(Enum):
    """Units admitted by the shared assertion layer."""

    DEGREES = "deg"
    AU = "AU"
    KILOMETRES = "km"
    DAYS = "day"
    SECONDS = "s"
    DIMENSIONLESS = "1"


@dataclass(frozen=True, slots=True)
class ToleranceContract:
    """Named, reviewable ownership of one comparison tolerance."""

    name: str
    semantics: NumericSemantics
    unit: Unit
    absolute: float
    basis: str
    relative: float | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.name, str) or not self.name.strip():
            raise ValueError("tolerance name must be a nonblank string.")
        if not isinstance(self.semantics, NumericSemantics):
            raise TypeError("semantics must be a NumericSemantics value.")
        if not isinstance(self.unit, Unit):
            raise TypeError("unit must be a Unit value.")
        _validate_nonnegative_tolerance(self.absolute, field_name="absolute")
        if self.relative is not None:
            _validate_nonnegative_tolerance(self.relative, field_name="relative")
            if self.semantics is not NumericSemantics.LINEAR:
                raise ValueError(
                    "relative tolerance is admitted only for linear semantics."
                )
        if not isinstance(self.basis, str) or not self.basis.strip():
            raise ValueError("tolerance basis must be a nonblank string.")


def _validate_nonnegative_tolerance(value: object, *, field_name: str) -> None:
    if isinstance(value, bool):
        raise TypeError(f"{field_name} tolerance must not be boolean.")
    if not isinstance(value, Real):
        raise TypeError(f"{field_name} tolerance must be a real number.")
    if not math.isfinite(float(value)) or value < 0:
        raise ValueError(f"{field_name} tolerance must be finite and nonnegative.")


def _finite_real(value: object, *, role: str) -> float:
    if isinstance(value, bool):
        raise TypeError(f"{role} must be a real number, not a boolean.")
    if not isinstance(value, Real):
        raise TypeError(f"{role} must be a real number; got {type(value).__name__}.")
    try:
        converted = float(value)
    except (OverflowError, ValueError) as exc:
        raise ValueError(f"{role} must be representable as a finite float.") from exc
    if not math.isfinite(converted):
        raise ValueError(f"{role} must be finite; got {value!r}.")
    return converted


def _require_contract(
    tolerance: ToleranceContract,
    *,
    semantics: NumericSemantics,
    unit: Unit | None,
) -> None:
    if not isinstance(tolerance, ToleranceContract):
        raise TypeError("tolerance must be a ToleranceContract.")
    if tolerance.semantics is not semantics:
        raise ValueError(
            f"{tolerance.name!r} has {tolerance.semantics.value} semantics; "
            f"{semantics.value} semantics are required."
        )
    if unit is not None and tolerance.unit is not unit:
        raise ValueError(
            f"{tolerance.name!r} has unit {tolerance.unit.value}; "
            f"unit {unit.value} is required."
        )


def _linear_threshold(
    actual: float,
    expected: float,
    tolerance: ToleranceContract,
) -> float:
    threshold = float(tolerance.absolute)
    if tolerance.relative is not None:
        relative_threshold = float(tolerance.relative) * max(
            abs(actual),
            abs(expected),
        )
        threshold = max(threshold, relative_threshold)
    return threshold


def _raise_residual_failure(
    *,
    tolerance: ToleranceContract,
    residual: float,
    threshold: float,
    relation: str,
) -> None:
    raise AssertionError(
        f"{tolerance.name}: {relation} residual {residual:.17g} "
        f"{tolerance.unit.value} exceeds tolerance {threshold:.17g} "
        f"{tolerance.unit.value}; basis: {tolerance.basis}"
    )


def _assert_linear(
    actual: object,
    expected: object,
    *,
    tolerance: ToleranceContract,
    unit: Unit,
) -> None:
    _require_contract(
        tolerance,
        semantics=NumericSemantics.LINEAR,
        unit=unit,
    )
    actual_value = _finite_real(actual, role="actual")
    expected_value = _finite_real(expected, role="expected")
    residual = abs(actual_value - expected_value)
    threshold = _linear_threshold(actual_value, expected_value, tolerance)
    if residual > threshold:
        _raise_residual_failure(
            tolerance=tolerance,
            residual=residual,
            threshold=threshold,
            relation="linear",
        )


def circular_residual_degrees(actual: object, expected: object) -> float:
    """Return the absolute shortest-arc residual in degrees."""

    actual_value = _finite_real(actual, role="actual angle")
    expected_value = _finite_real(expected, role="expected angle")
    actual_wrapped = actual_value % 360.0
    expected_wrapped = expected_value % 360.0
    residual = abs((actual_wrapped - expected_wrapped + 180.0) % 360.0 - 180.0)
    if not math.isfinite(residual):
        raise ValueError("circular residual must remain finite.")
    return residual


def assert_circular_degrees(
    actual: object,
    expected: object,
    *,
    tolerance: ToleranceContract,
) -> None:
    """Assert equality on a periodic 360-degree domain."""

    _require_contract(
        tolerance,
        semantics=NumericSemantics.CIRCULAR,
        unit=Unit.DEGREES,
    )
    residual = circular_residual_degrees(actual, expected)
    threshold = float(tolerance.absolute)
    if residual > threshold:
        _raise_residual_failure(
            tolerance=tolerance,
            residual=residual,
            threshold=threshold,
            relation="shortest-arc",
        )


def _normalized_vector(
    vector: Iterable[object],
    *,
    role: str,
) -> tuple[float, float, float]:
    try:
        components = tuple(islice(vector, 4))
    except TypeError as exc:
        raise TypeError(f"{role} must be an iterable with three components.") from exc
    if len(components) != 3:
        raise ValueError(f"{role} must contain exactly three components.")
    x, y, z = (
        _finite_real(component, role=f"{role}[{index}]")
        for index, component in enumerate(components)
    )
    scale = max(abs(x), abs(y), abs(z))
    if scale == 0.0:
        raise ValueError(f"{role} must not be the zero vector.")
    scaled_x, scaled_y, scaled_z = x / scale, y / scale, z / scale
    norm = math.hypot(scaled_x, scaled_y, scaled_z)
    return scaled_x / norm, scaled_y / norm, scaled_z / norm


def vector_angular_separation_degrees(
    first: Iterable[object],
    second: Iterable[object],
) -> float:
    """Return stable angular separation using ``atan2(|a×b|, a·b)``."""

    ax, ay, az = _normalized_vector(first, role="first vector")
    bx, by, bz = _normalized_vector(second, role="second vector")
    cross_x = ay * bz - az * by
    cross_y = az * bx - ax * bz
    cross_z = ax * by - ay * bx
    cross_norm = math.hypot(cross_x, cross_y, cross_z)
    dot = max(-1.0, min(1.0, ax * bx + ay * by + az * bz))
    return math.degrees(math.atan2(cross_norm, dot))


def assert_vector_angular_separation(
    actual: Iterable[object],
    expected: Iterable[object],
    *,
    tolerance: ToleranceContract,
) -> None:
    """Assert that two nonzero vectors represent the same direction."""

    _require_contract(
        tolerance,
        semantics=NumericSemantics.VECTOR_ANGLE,
        unit=Unit.DEGREES,
    )
    residual = vector_angular_separation_degrees(actual, expected)
    threshold = float(tolerance.absolute)
    if residual > threshold:
        _raise_residual_failure(
            tolerance=tolerance,
            residual=residual,
            threshold=threshold,
            relation="vector-angle",
        )


def assert_scalar_degrees(
    actual: object,
    expected: object,
    *,
    tolerance: ToleranceContract,
) -> None:
    """Assert a non-periodic scalar measured in degrees."""

    _assert_linear(actual, expected, tolerance=tolerance, unit=Unit.DEGREES)


def assert_au(
    actual: object,
    expected: object,
    *,
    tolerance: ToleranceContract,
) -> None:
    """Assert a linear distance measured in astronomical units."""

    _assert_linear(actual, expected, tolerance=tolerance, unit=Unit.AU)


def assert_kilometres(
    actual: object,
    expected: object,
    *,
    tolerance: ToleranceContract,
) -> None:
    """Assert a linear distance measured in kilometres."""

    _assert_linear(actual, expected, tolerance=tolerance, unit=Unit.KILOMETRES)


def assert_days(
    actual: object,
    expected: object,
    *,
    tolerance: ToleranceContract,
) -> None:
    """Assert a linear interval measured in days."""

    _assert_linear(actual, expected, tolerance=tolerance, unit=Unit.DAYS)


def assert_seconds(
    actual: object,
    expected: object,
    *,
    tolerance: ToleranceContract,
) -> None:
    """Assert a linear interval measured in seconds."""

    _assert_linear(actual, expected, tolerance=tolerance, unit=Unit.SECONDS)


def assert_ratio(
    actual: object,
    expected: object,
    *,
    tolerance: ToleranceContract,
) -> None:
    """Assert a dimensionless linear ratio."""

    _assert_linear(actual, expected, tolerance=tolerance, unit=Unit.DIMENSIONLESS)


def assert_event_residual(
    residual: object,
    *,
    tolerance: ToleranceContract,
) -> None:
    """Assert that a signed event-function residual is sufficiently near zero."""

    _require_contract(
        tolerance,
        semantics=NumericSemantics.EVENT_RESIDUAL,
        unit=None,
    )
    residual_value = abs(_finite_real(residual, role="event residual"))
    threshold = float(tolerance.absolute)
    if residual_value > threshold:
        _raise_residual_failure(
            tolerance=tolerance,
            residual=residual_value,
            threshold=threshold,
            relation="event-function",
        )


def assert_canonical_longitude_degrees(
    value: object,
    *,
    label: str = "longitude",
) -> None:
    """Assert a finite, non-boolean longitude in the half-open domain [0, 360)."""

    longitude = _finite_real(value, role=label)
    if not 0.0 <= longitude < 360.0:
        raise AssertionError(f"{label} {longitude!r} is outside [0, 360).")
