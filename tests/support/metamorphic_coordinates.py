"""Reviewed observations and predicates for coordinate metamorphic tests."""

from __future__ import annotations

from dataclasses import dataclass
import math
from numbers import Real

from moira.coordinates import (
    ecliptic_to_equatorial,
    equatorial_to_ecliptic,
    normalize_degrees,
)
from support.metamorphic import require_relation
from support.numeric_assertions import (
    circular_residual_degrees,
    vector_angular_separation_degrees,
)


COORDINATE_SPHERE_RELATION_ID = (
    "MOIRA-COORD-ECLIPTIC-EQUATORIAL-SPHERE-INVERSE-V1"
)
LONGITUDE_QUOTIENT_RELATION_ID = "MOIRA-COORD-LONGITUDE-QUOTIENT-V1"
BASELINE_MUTANT_ID = "unmutated-production-observation"


@dataclass(frozen=True, slots=True)
class SphericalInverseObservation:
    """One bidirectional public-transform observation on the unit sphere."""

    ecliptic_residual_deg: float
    equatorial_residual_deg: float
    output_longitudes_deg: tuple[float, ...]
    output_latitudes_deg: tuple[float, ...]

    @property
    def maximum_residual_deg(self) -> float:
        return max(self.ecliptic_residual_deg, self.equatorial_residual_deg)


@dataclass(frozen=True, slots=True)
class LongitudeQuotientObservation:
    """One normalization, idempotence, and periodicity observation."""

    normalized_deg: float
    renormalized_deg: float
    shifted_normalized_deg: float
    periodic_residual_deg: float


def _finite_real(value: object, *, role: str) -> float:
    if isinstance(value, bool) or not isinstance(value, Real):
        raise TypeError(f"{role} must be a non-boolean real number")
    converted = float(value)
    if not math.isfinite(converted):
        raise ValueError(f"{role} must be finite")
    return converted


def _latitude(value: object, *, role: str) -> float:
    converted = _finite_real(value, role=role)
    if not -90.0 <= converted <= 90.0:
        raise ValueError(f"{role} must be in [-90, 90] degrees")
    return converted


def _obliquity(value: object) -> float:
    converted = _finite_real(value, role="obliquity")
    if not -30.0 <= converted <= 30.0:
        raise ValueError("obliquity must be in the reviewed [-30, 30] degree domain")
    return converted


def spherical_unit_vector(
    longitude_deg: float,
    latitude_deg: float,
) -> tuple[float, float, float]:
    """Materialize one spherical direction in a right-handed Cartesian basis."""

    longitude = math.radians(_finite_real(longitude_deg, role="longitude"))
    latitude = math.radians(_latitude(latitude_deg, role="latitude"))
    cos_latitude = math.cos(latitude)
    return (
        cos_latitude * math.cos(longitude),
        cos_latitude * math.sin(longitude),
        math.sin(latitude),
    )


def observe_spherical_inverse(
    *,
    ecliptic_longitude_deg: float,
    ecliptic_latitude_deg: float,
    equatorial_ra_deg: float,
    equatorial_declination_deg: float,
    obliquity_deg: float,
    recovered_ecliptic_latitude_bias_deg: float = 0.0,
) -> SphericalInverseObservation:
    """Observe both directions of the orthogonal x-axis rotation covenant.

    The optional bias is applied only after both production transforms return.
    It exists solely for a finite, in-domain predicate-sensitivity canary.
    """

    ecliptic_longitude = _finite_real(
        ecliptic_longitude_deg,
        role="ecliptic longitude",
    )
    ecliptic_latitude = _latitude(
        ecliptic_latitude_deg,
        role="ecliptic latitude",
    )
    equatorial_ra = _finite_real(equatorial_ra_deg, role="right ascension")
    equatorial_declination = _latitude(
        equatorial_declination_deg,
        role="declination",
    )
    obliquity = _obliquity(obliquity_deg)
    bias = _finite_real(
        recovered_ecliptic_latitude_bias_deg,
        role="recovered ecliptic latitude bias",
    )

    recovered_ra, recovered_declination = ecliptic_to_equatorial(
        ecliptic_longitude,
        ecliptic_latitude,
        obliquity,
    )
    recovered_longitude, recovered_latitude = equatorial_to_ecliptic(
        recovered_ra,
        recovered_declination,
        obliquity,
    )
    recovered_latitude += bias
    _latitude(recovered_latitude, role="mutated recovered ecliptic latitude")

    recovered_ecliptic_longitude, recovered_ecliptic_latitude = (
        equatorial_to_ecliptic(
            equatorial_ra,
            equatorial_declination,
            obliquity,
        )
    )
    round_trip_ra, round_trip_declination = ecliptic_to_equatorial(
        recovered_ecliptic_longitude,
        recovered_ecliptic_latitude,
        obliquity,
    )

    ecliptic_residual = vector_angular_separation_degrees(
        spherical_unit_vector(ecliptic_longitude, ecliptic_latitude),
        spherical_unit_vector(recovered_longitude, recovered_latitude),
    )
    equatorial_residual = vector_angular_separation_degrees(
        spherical_unit_vector(equatorial_ra, equatorial_declination),
        spherical_unit_vector(round_trip_ra, round_trip_declination),
    )
    return SphericalInverseObservation(
        ecliptic_residual_deg=ecliptic_residual,
        equatorial_residual_deg=equatorial_residual,
        output_longitudes_deg=(
            recovered_ra,
            recovered_longitude,
            recovered_ecliptic_longitude,
            round_trip_ra,
        ),
        output_latitudes_deg=(
            recovered_declination,
            recovered_latitude,
            recovered_ecliptic_latitude,
            round_trip_declination,
        ),
    )


def assert_spherical_inverse(
    observation: SphericalInverseObservation,
    *,
    limit_deg: float,
    mutant_id: str = BASELINE_MUTANT_ID,
) -> None:
    """Apply the one reviewed predicate to production and canary observations."""

    limit = _finite_real(limit_deg, role="spherical inverse limit")
    if limit < 0.0:
        raise ValueError("spherical inverse limit must be nonnegative")
    for longitude in observation.output_longitudes_deg:
        require_relation(
            math.isfinite(longitude) and 0.0 <= longitude < 360.0,
            relation_id=COORDINATE_SPHERE_RELATION_ID,
            mutant_id=mutant_id,
            metric="canonical output longitude upper bound",
            observed=longitude,
            limit=math.nextafter(360.0, -math.inf),
        )
    for latitude in observation.output_latitudes_deg:
        require_relation(
            math.isfinite(latitude) and -90.0 <= latitude <= 90.0,
            relation_id=COORDINATE_SPHERE_RELATION_ID,
            mutant_id=mutant_id,
            metric="absolute output latitude",
            observed=abs(latitude),
            limit=90.0,
        )
    require_relation(
        observation.maximum_residual_deg <= limit,
        relation_id=COORDINATE_SPHERE_RELATION_ID,
        mutant_id=mutant_id,
        metric="maximum unit-vector angular separation",
        observed=observation.maximum_residual_deg,
        limit=limit,
    )


def observe_longitude_quotient(
    angle_deg: float,
    period_shift: int,
    *,
    canonical_zero_to_360_mutant: bool = False,
) -> LongitudeQuotientObservation:
    """Observe the half-open representative of the longitude quotient."""

    angle = _finite_real(angle_deg, role="longitude angle")
    if isinstance(period_shift, bool) or not isinstance(period_shift, int):
        raise TypeError("period_shift must be an integer")
    if not -16 <= period_shift <= 16:
        raise ValueError("period_shift must be in the reviewed [-16, 16] domain")

    normalized = normalize_degrees(angle)
    renormalized = normalize_degrees(normalized)
    shifted_normalized = normalize_degrees(angle + 360.0 * period_shift)
    if canonical_zero_to_360_mutant and normalized == 0.0:
        normalized = 360.0
    return LongitudeQuotientObservation(
        normalized_deg=normalized,
        renormalized_deg=renormalized,
        shifted_normalized_deg=shifted_normalized,
        periodic_residual_deg=circular_residual_degrees(
            normalized,
            shifted_normalized,
        ),
    )


def assert_longitude_quotient(
    observation: LongitudeQuotientObservation,
    *,
    limit_deg: float,
    mutant_id: str = BASELINE_MUTANT_ID,
) -> None:
    """Apply the canonical, idempotent, and periodic quotient predicate."""

    limit = _finite_real(limit_deg, role="longitude periodicity limit")
    if limit < 0.0:
        raise ValueError("longitude periodicity limit must be nonnegative")
    for value in (
        observation.normalized_deg,
        observation.renormalized_deg,
        observation.shifted_normalized_deg,
    ):
        require_relation(
            math.isfinite(value) and 0.0 <= value < 360.0,
            relation_id=LONGITUDE_QUOTIENT_RELATION_ID,
            mutant_id=mutant_id,
            metric="canonical longitude upper bound",
            observed=value,
            limit=math.nextafter(360.0, -math.inf),
        )
    require_relation(
        observation.renormalized_deg == observation.normalized_deg,
        relation_id=LONGITUDE_QUOTIENT_RELATION_ID,
        mutant_id=mutant_id,
        metric="idempotence residual",
        observed=circular_residual_degrees(
            observation.renormalized_deg,
            observation.normalized_deg,
        ),
        limit=0.0,
    )
    if observation.normalized_deg == 0.0:
        require_relation(
            math.copysign(1.0, observation.normalized_deg) == 1.0,
            relation_id=LONGITUDE_QUOTIENT_RELATION_ID,
            mutant_id=mutant_id,
            metric="negative-zero indicator",
            observed=(
                0.0
                if math.copysign(1.0, observation.normalized_deg) == 1.0
                else 1.0
            ),
            limit=0.0,
        )
    require_relation(
        observation.periodic_residual_deg <= limit,
        relation_id=LONGITUDE_QUOTIENT_RELATION_ID,
        mutant_id=mutant_id,
        metric="circular period-shift residual",
        observed=observation.periodic_residual_deg,
        limit=limit,
    )


__all__ = [
    "BASELINE_MUTANT_ID",
    "COORDINATE_SPHERE_RELATION_ID",
    "LONGITUDE_QUOTIENT_RELATION_ID",
    "LongitudeQuotientObservation",
    "SphericalInverseObservation",
    "assert_longitude_quotient",
    "assert_spherical_inverse",
    "observe_longitude_quotient",
    "observe_spherical_inverse",
    "spherical_unit_vector",
]
