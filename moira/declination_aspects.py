"""First-class declination aspects on the celestial sphere.

Longitude aspects measure separation around the ecliptic.  This module owns
the independent equatorial-declination domain: parallels, contra-parallels,
their admission policy, and their instantaneous temporal motion.

Declination supplies a second angular dimension, not full Cartesian spatial
geometry.  Every public computation therefore preserves the caller-declared
reference frame and timescale and makes no claim about radial distance.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import math
from typing import Mapping

from ._aspect_types import (
    AspectClassification,
    AspectDomain,
    AspectFamily,
    AspectTier,
)


class DeclinationAspectKind(str, Enum):
    """The two admitted signed-declination relationships."""

    PARALLEL = "Parallel"
    CONTRA_PARALLEL = "Contra-Parallel"


class DeclinationHemispherePolicy(str, Enum):
    """Hemisphere doctrine used to distinguish the two relationships."""

    STRICT_SIGNED = (
        "parallel_same_nonzero_hemisphere_contra_opposite_nonzero_hemispheres"
    )


class DeclinationEquatorPolicy(str, Enum):
    """Doctrine for points lying exactly on the celestial equator."""

    PAIRED_EQUATORIAL_PARALLEL = (
        "two_equatorial_points_parallel_one_equatorial_point_unclassified"
    )


class DeclinationMotionState(str, Enum):
    """Instantaneous temporal state of one declination relationship."""

    APPLYING = "applying"
    EXACT = "exact"
    SEPARATING = "separating"
    STATIONARY = "stationary"
    INDETERMINATE = "indeterminate"


@dataclass(frozen=True, slots=True)
class DeclinationAspectPolicy:
    """Explicit admission and motion tolerances for declination aspects.

    ``orb`` admits both parallels and contra-parallels.  Exactness takes
    precedence over motion state.  ``rate_tolerance_deg_per_day`` describes a
    stalled *relative declination error*; an individual body may have zero
    declination rate while the relationship still applies or separates.
    """

    orb: float = 1.0
    exact_tolerance_deg: float = 1e-9
    rate_tolerance_deg_per_day: float = 1e-12
    hemisphere_policy: DeclinationHemispherePolicy = (
        DeclinationHemispherePolicy.STRICT_SIGNED
    )
    equator_policy: DeclinationEquatorPolicy = (
        DeclinationEquatorPolicy.PAIRED_EQUATORIAL_PARALLEL
    )

    def __post_init__(self) -> None:
        for field_name, value in (
            ("orb", self.orb),
            ("exact_tolerance_deg", self.exact_tolerance_deg),
            ("rate_tolerance_deg_per_day", self.rate_tolerance_deg_per_day),
        ):
            parsed = _finite_number(field_name, value)
            if parsed < 0.0:
                raise ValueError(f"{field_name} must be non-negative")
            object.__setattr__(self, field_name, parsed)
        if not isinstance(self.hemisphere_policy, DeclinationHemispherePolicy):
            raise ValueError("hemisphere_policy must be a DeclinationHemispherePolicy")
        if not isinstance(self.equator_policy, DeclinationEquatorPolicy):
            raise ValueError("equator_policy must be a DeclinationEquatorPolicy")


_PARALLEL_CLASSIFICATION = AspectClassification(
    domain=AspectDomain.DECLINATION,
    tier=AspectTier.MAJOR,
    family=AspectFamily.DECLINATION,
)

_CONTRA_PARALLEL_CLASSIFICATION = AspectClassification(
    domain=AspectDomain.DECLINATION,
    tier=AspectTier.MAJOR,
    family=AspectFamily.DECLINATION,
)


@dataclass(frozen=True, slots=True)
class DeclinationAspect:
    """One admitted parallel or contra-parallel between two named points."""

    body1: str
    body2: str
    aspect: str
    dec1: float
    dec2: float
    orb: float
    allowed_orb: float
    classification: AspectClassification | None = None

    @property
    def is_parallel(self) -> bool:
        """Whether this vessel represents a parallel."""

        return self.aspect == DeclinationAspectKind.PARALLEL.value

    @property
    def is_contra_parallel(self) -> bool:
        """Whether this vessel represents a contra-parallel."""

        return self.aspect == DeclinationAspectKind.CONTRA_PARALLEL.value

    @property
    def orb_surplus(self) -> float:
        """Remaining headroom inside the admitted orb."""

        return self.allowed_orb - self.orb

    def __repr__(self) -> str:
        return (
            f"{self.body1} {self.aspect} {self.body2}  "
            f"(orb {self.orb:+.2f}°) [{self.aspect}]"
        )


@dataclass(frozen=True, slots=True)
class DeclinationAspectAnalysis:
    """Immutable analysis of caller-supplied equatorial declinations."""

    positions: tuple[tuple[str, float], ...]
    aspects: tuple[DeclinationAspect, ...]
    orb: float
    reference_frame: str
    timescale: str
    provenance: str = "caller_supplied_declinations"

    @property
    def declinations(self) -> dict[str, float]:
        """Normalized declinations in deterministic point-name order."""

        return dict(self.positions)

    @property
    def point_count(self) -> int:
        """Number of supplied points."""

        return len(self.positions)

    @property
    def aspect_count(self) -> int:
        """Number of admitted declination relationships."""

        return len(self.aspects)


@dataclass(frozen=True, slots=True)
class DeclinationAspectMotionWitness:
    """Immutable signed-error witness for instantaneous declination motion."""

    body1: str
    body2: str
    aspect: DeclinationAspectKind
    declination1_deg: float
    declination2_deg: float
    speed1_deg_per_day: float | None
    speed2_deg_per_day: float | None
    signed_error_deg: float
    relative_speed_deg_per_day: float | None
    orb_deg: float
    orb_rate_deg_per_day: float | None
    allowed_orb_deg: float
    within_orb: bool
    state: DeclinationMotionState
    relative_motion_stalled: bool | None
    exact_tolerance_deg: float
    rate_tolerance_deg_per_day: float
    hemisphere_policy: DeclinationHemispherePolicy
    equator_policy: DeclinationEquatorPolicy
    classification: AspectClassification
    reference_frame: str
    timescale: str
    provenance: str = "caller_supplied_declinations_and_optional_rates"
    evaluation_scope: str = "instantaneous_no_event_search"


def _finite_number(name: str, value: object) -> float:
    if isinstance(value, bool):
        raise ValueError(f"{name} must be a finite number")
    try:
        parsed = float(value)  # type: ignore[arg-type]
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{name} must be a finite number") from exc
    if not math.isfinite(parsed):
        raise ValueError(f"{name} must be a finite number")
    return parsed


def _normalized_declinations(values: Mapping[str, float]) -> dict[str, float]:
    if not isinstance(values, Mapping):
        raise ValueError("declinations must be a mapping of point names to degrees")
    normalized: dict[str, float] = {}
    for name, value in values.items():
        if not isinstance(name, str) or not name or name != name.strip():
            raise ValueError(
                "declination point names must be non-empty trimmed strings"
            )
        parsed = _finite_number(f"declination for {name!r}", value)
        if not -90.0 <= parsed <= 90.0:
            raise ValueError(
                f"declination for {name!r} must lie in [-90.0, 90.0]"
            )
        normalized[name] = parsed
    return normalized


def _required_text(name: str, value: object) -> str:
    if not isinstance(value, str) or not value or value != value.strip():
        raise ValueError(f"{name} must be a non-empty trimmed string")
    return value


def _kind(value: DeclinationAspectKind | str) -> DeclinationAspectKind:
    if isinstance(value, DeclinationAspectKind):
        return value
    try:
        return DeclinationAspectKind(value)
    except (TypeError, ValueError) as exc:
        raise ValueError("aspect must be 'Parallel' or 'Contra-Parallel'") from exc


def _hemisphere_eligible(
    kind: DeclinationAspectKind,
    declination1: float,
    declination2: float,
) -> bool:
    both_equatorial = declination1 == 0.0 and declination2 == 0.0
    if kind is DeclinationAspectKind.PARALLEL:
        return declination1 * declination2 > 0.0 or both_equatorial
    return declination1 * declination2 < 0.0


def find_declination_aspects(
    declinations: Mapping[str, float],
    orb: float = 1.0,
    policy: DeclinationAspectPolicy | None = None,
) -> list[DeclinationAspect]:
    """Find parallels and contra-parallels under explicit hemisphere doctrine."""

    resolved_policy = policy or DeclinationAspectPolicy(orb=orb)
    if not isinstance(resolved_policy, DeclinationAspectPolicy):
        raise ValueError("policy must be a DeclinationAspectPolicy")
    normalized = _normalized_declinations(declinations)
    bodies = list(normalized)
    results: list[DeclinationAspect] = []

    for index, body1 in enumerate(bodies):
        for body2 in bodies[index + 1 :]:
            declination1 = normalized[body1]
            declination2 = normalized[body2]
            parallel_orb = abs(declination1 - declination2)
            if (
                _hemisphere_eligible(
                    DeclinationAspectKind.PARALLEL,
                    declination1,
                    declination2,
                )
                and parallel_orb <= resolved_policy.orb
            ):
                results.append(
                    DeclinationAspect(
                        body1=body1,
                        body2=body2,
                        aspect=DeclinationAspectKind.PARALLEL.value,
                        dec1=declination1,
                        dec2=declination2,
                        orb=parallel_orb,
                        allowed_orb=resolved_policy.orb,
                        classification=_PARALLEL_CLASSIFICATION,
                    )
                )

            contra_orb = abs(declination1 + declination2)
            if (
                _hemisphere_eligible(
                    DeclinationAspectKind.CONTRA_PARALLEL,
                    declination1,
                    declination2,
                )
                and contra_orb <= resolved_policy.orb
            ):
                results.append(
                    DeclinationAspect(
                        body1=body1,
                        body2=body2,
                        aspect=DeclinationAspectKind.CONTRA_PARALLEL.value,
                        dec1=declination1,
                        dec2=declination2,
                        orb=contra_orb,
                        allowed_orb=resolved_policy.orb,
                        classification=_CONTRA_PARALLEL_CLASSIFICATION,
                    )
                )

    results.sort(key=lambda aspect: aspect.orb)
    return results


def declination_aspects_from_declinations(
    declinations: Mapping[str, float],
    *,
    reference_frame: str,
    timescale: str,
    orb: float = 1.0,
    policy: DeclinationAspectPolicy | None = None,
) -> DeclinationAspectAnalysis:
    """Analyze caller-supplied declinations with explicit coordinate provenance."""

    resolved_policy = policy or DeclinationAspectPolicy(orb=orb)
    if not isinstance(resolved_policy, DeclinationAspectPolicy):
        raise ValueError("policy must be a DeclinationAspectPolicy")
    frame = _required_text("reference_frame", reference_frame)
    scale = _required_text("timescale", timescale)
    normalized = _normalized_declinations(declinations)
    if len(normalized) < 2:
        raise ValueError("at least two declination points are required")
    ordered = dict(sorted(normalized.items()))
    aspects = find_declination_aspects(ordered, policy=resolved_policy)
    return DeclinationAspectAnalysis(
        positions=tuple(ordered.items()),
        aspects=tuple(aspects),
        orb=resolved_policy.orb,
        reference_frame=frame,
        timescale=scale,
    )


def declination_aspect_motion_witness(
    body1: str,
    declination1_deg: float,
    body2: str,
    declination2_deg: float,
    aspect: DeclinationAspectKind | str,
    *,
    speed1_deg_per_day: float | None = None,
    speed2_deg_per_day: float | None = None,
    orb: float = 1.0,
    exact_tolerance_deg: float = 1e-9,
    rate_tolerance_deg_per_day: float = 1e-12,
    reference_frame: str,
    timescale: str,
    policy: DeclinationAspectPolicy | None = None,
) -> DeclinationAspectMotionWitness:
    """Classify instantaneous applying or separating declination motion.

    For a parallel the signed error is ``dec1 - dec2`` and its rate is
    ``speed1 - speed2``.  For a contra-parallel they are ``dec1 + dec2`` and
    ``speed1 + speed2``.  Away from exactness, multiplying the error-rate by
    the sign of the error gives the rate of the absolute orb.

    This is an instantaneous witness, not proof that the relationship will
    perfect before a later reversal.  Missing speeds produce ``indeterminate``.
    """

    name1 = _required_text("body1", body1)
    name2 = _required_text("body2", body2)
    if name1 == name2:
        raise ValueError("body1 and body2 must identify distinct points")
    frame = _required_text("reference_frame", reference_frame)
    scale = _required_text("timescale", timescale)
    selected_kind = _kind(aspect)
    declination1 = _finite_number("declination1_deg", declination1_deg)
    declination2 = _finite_number("declination2_deg", declination2_deg)
    for field_name, value in (
        ("declination1_deg", declination1),
        ("declination2_deg", declination2),
    ):
        if not -90.0 <= value <= 90.0:
            raise ValueError(f"{field_name} must lie in [-90.0, 90.0]")
    if not _hemisphere_eligible(selected_kind, declination1, declination2):
        raise ValueError(
            f"{selected_kind.value} is not eligible for the supplied hemispheres"
        )

    speed1 = (
        None
        if speed1_deg_per_day is None
        else _finite_number("speed1_deg_per_day", speed1_deg_per_day)
    )
    speed2 = (
        None
        if speed2_deg_per_day is None
        else _finite_number("speed2_deg_per_day", speed2_deg_per_day)
    )
    resolved_policy = policy or DeclinationAspectPolicy(
        orb=orb,
        exact_tolerance_deg=exact_tolerance_deg,
        rate_tolerance_deg_per_day=rate_tolerance_deg_per_day,
    )
    if not isinstance(resolved_policy, DeclinationAspectPolicy):
        raise ValueError("policy must be a DeclinationAspectPolicy")

    if selected_kind is DeclinationAspectKind.PARALLEL:
        signed_error = declination1 - declination2
        relative_speed = (
            None if speed1 is None or speed2 is None else speed1 - speed2
        )
        classification = _PARALLEL_CLASSIFICATION
    else:
        signed_error = declination1 + declination2
        relative_speed = (
            None if speed1 is None or speed2 is None else speed1 + speed2
        )
        classification = _CONTRA_PARALLEL_CLASSIFICATION

    orb_deg = abs(signed_error)
    is_exact = orb_deg <= resolved_policy.exact_tolerance_deg
    relative_motion_stalled = (
        None
        if relative_speed is None
        else abs(relative_speed) <= resolved_policy.rate_tolerance_deg_per_day
    )
    orb_rate = (
        None
        if relative_speed is None or is_exact
        else math.copysign(1.0, signed_error) * relative_speed
    )
    if is_exact:
        state = DeclinationMotionState.EXACT
    elif relative_speed is None:
        state = DeclinationMotionState.INDETERMINATE
    elif relative_motion_stalled:
        state = DeclinationMotionState.STATIONARY
    elif orb_rate is not None and orb_rate < 0.0:
        state = DeclinationMotionState.APPLYING
    else:
        state = DeclinationMotionState.SEPARATING

    return DeclinationAspectMotionWitness(
        body1=name1,
        body2=name2,
        aspect=selected_kind,
        declination1_deg=declination1,
        declination2_deg=declination2,
        speed1_deg_per_day=speed1,
        speed2_deg_per_day=speed2,
        signed_error_deg=signed_error,
        relative_speed_deg_per_day=relative_speed,
        orb_deg=orb_deg,
        orb_rate_deg_per_day=orb_rate,
        allowed_orb_deg=resolved_policy.orb,
        within_orb=orb_deg <= resolved_policy.orb,
        state=state,
        relative_motion_stalled=relative_motion_stalled,
        exact_tolerance_deg=resolved_policy.exact_tolerance_deg,
        rate_tolerance_deg_per_day=resolved_policy.rate_tolerance_deg_per_day,
        hemisphere_policy=resolved_policy.hemisphere_policy,
        equator_policy=resolved_policy.equator_policy,
        classification=classification,
        reference_frame=frame,
        timescale=scale,
    )


__all__ = [
    "DeclinationAspect",
    "DeclinationAspectAnalysis",
    "DeclinationAspectKind",
    "DeclinationAspectMotionWitness",
    "DeclinationAspectPolicy",
    "DeclinationEquatorPolicy",
    "DeclinationHemispherePolicy",
    "DeclinationMotionState",
    "declination_aspect_motion_witness",
    "declination_aspects_from_declinations",
    "find_declination_aspects",
]
